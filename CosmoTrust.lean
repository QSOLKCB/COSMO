import Lean.Compiler.ModPkgExt
import Lean.CoreM
import Lean.Elab.Command
import Lean.Environment
import Lean.Replay
import Lean.Util.CollectAxioms

open Lean Meta Elab Command

namespace CosmoTrust

/-- Foundations permitted by the COSMO formal trust policy. -/
private def isAllowedFoundation (name : Name) : Bool :=
  name == ``propext ||
    name == ``Classical.choice ||
    name == ``Quot.sound

private def renderNames (names : Array Name) : String :=
  String.intercalate ", " (names.toList.map Name.toString)

/-- Declaration kinds that cannot belong to a trusted project module. -/
private def declarationKindViolation? (info : ConstantInfo) : Option String :=
  match info with
  | .axiomInfo _ => some "project-generated axiom declaration"
  | .opaqueInfo _ => some "project opaque declaration"
  | _ => none

/-- All imported declarations emitted by one module. -/
private def importedModuleDeclarations
    (env : Environment) (moduleIdx : ModuleIdx) : Array Name :=
  env.constants.toList.foldl (init := (#[] : Array Name)) fun declarations entry =>
    let declName := entry.1
    if env.getModuleIdxFor? declName == some moduleIdx then
      declarations.push declName
    else
      declarations

/-- All imported declarations whose module was built by `packageId`. -/
private def importedPackageDeclarations
    (env : Environment) (packageId : PkgId) : Array Name :=
  env.constants.toList.foldl (init := (#[] : Array Name)) fun declarations entry =>
    let declName := entry.1
    match env.getModuleIdxFor? declName with
    | some moduleIdx =>
        if env.getModulePackageByIdx? moduleIdx == some packageId then
          declarations.push declName
        else
          declarations
    | none => declarations

/-- Audit declarations in the current kernel environment. -/
private def auditNamedDeclarationsCore
    (scope : String) (declarations : Array Name) : CoreM Nat := do
  let env ← getEnv
  if declarations.isEmpty then
    throwError m!"COSMO semantic trust audit selected no declarations for {scope}."

  let mut failures : Array String := #[]
  for declName in declarations do
    match env.find? declName with
    | none =>
        failures := failures.push
          s!"{declName}: declaration disappeared during semantic trust audit"
    | some info =>
        match declarationKindViolation? info with
        | some reason =>
            failures := failures.push s!"{declName}: {reason}"
        | none => pure ()

        let used ← Lean.collectAxioms declName
        let unexpected := used.filter fun name => !isAllowedFoundation name
        unless unexpected.isEmpty do
          failures := failures.push
            s!"{declName}: unexpected axiom dependencies [{renderNames unexpected}]"

        let allowed := used.filter isAllowedFoundation
        IO.println
          s!"TRUST-AUDIT {declName}: allowed foundations [{renderNames allowed}]"

  if failures.isEmpty then
    IO.println
      s!"COSMO semantic trust audit passed for {declarations.size} declaration(s) in {scope}."
  else
    for failure in failures do
      IO.eprintln failure
    throwError
      m!"COSMO semantic trust audit failed with {failures.size} finding(s) in {scope}."

  return declarations.size

/-- Audit every declaration emitted by the supplied imported modules. -/
private def auditImportedModulesCore (modules : Array Name) : CoreM Nat := do
  if modules.isEmpty then
    throwError "COSMO semantic trust audit received no project modules."

  let env ← getEnv
  let mut declarationCount := 0
  for moduleName in modules do
    let some moduleIdx := env.getModuleIdx? moduleName
      | throwError m!"COSMO semantic trust audit cannot find imported module {moduleName}."
    let declarations := importedModuleDeclarations env moduleIdx
    if declarations.isEmpty then
      IO.println s!"TRUST-AUDIT {moduleName}: module emits no declarations"
    else
      declarationCount := declarationCount +
        (← auditNamedDeclarationsCore s!"module {moduleName}" declarations)

  if declarationCount == 0 then
    throwError "COSMO semantic trust audit found no declarations in the captured modules."
  return declarationCount

/--
Audit every package represented by the supplied imported modules.

This command is retained for local interactive use where Lake environment
extensions are loaded normally. Protected CI uses the module-index audit above,
which does not require project package extensions or execute initializers.
-/
private def auditImportedPackagesCore
    (anchorModules : Array Name) : CoreM (Nat × Nat) := do
  if anchorModules.isEmpty then
    throwError "COSMO semantic trust audit received no project modules."

  let env ← getEnv
  let mut packageIds : Array PkgId := #[]
  for anchorModule in anchorModules do
    let some moduleIdx := env.getModuleIdx? anchorModule
      | throwError m!"COSMO semantic trust audit cannot find imported module {anchorModule}."
    let some packageId := env.getModulePackageByIdx? moduleIdx
      | throwError m!"COSMO semantic trust audit found no Lake package for {anchorModule}."
    unless packageIds.contains packageId do
      packageIds := packageIds.push packageId

  let mut declarationCount := 0
  for packageId in packageIds do
    let declarations := importedPackageDeclarations env packageId
    declarationCount := declarationCount +
      (← auditNamedDeclarationsCore s!"Lake package {packageId}" declarations)

  return (packageIds.size, declarationCount)

/--
Audit named declarations semantically in Lean's elaborated environment.

This command remains available for focused negative regression fixtures.
-/
meta def auditNamedDeclarations
    (scope : String) (declarations : Array Name) : CommandElabM Unit := do
  discard <| liftCoreM <| auditNamedDeclarationsCore scope declarations

/-- Audit all Lake packages represented by the supplied imported modules. -/
meta def auditImportedPackagesFrom
    (anchorModules : Array Name) : CommandElabM Unit := do
  discard <| liftCoreM <| auditImportedPackagesCore anchorModules

/-- Backwards-compatible one-package audit command. -/
meta def auditImportedPackageFrom (anchorModule : Name) : CommandElabM Unit :=
  auditImportedPackagesFrom #[anchorModule]

/--
Replay one frozen module using the same kernel replay mechanism used by the
pinned `leanchecker` executable. The module's imports are reconstructed first,
then every constant emitted by the target module is replayed through the kernel.
-/
private unsafe def replayModule (moduleName : Name) : IO Unit := do
  let olean ← findOLean moduleName
  unless (← olean.pathExists) do
    throw <| IO.userError s!"object file '{olean}' of module {moduleName} does not exist"

  let mut files := #[olean]
  let serverFile := OLeanLevel.server.adjustFileName olean
  if ← serverFile.pathExists then
    files := files.push serverFile
    let privateFile := OLeanLevel.private.adjustFileName olean
    if ← privateFile.pathExists then
      files := files.push privateFile

  let parts ← readModuleDataParts files
  if h : parts.size = 0 then
    throw <| IO.userError s!"failed to read module data for {moduleName}"
  else
    let (moduleData, _) := parts[0]
    let (_, state) ← importModulesCore moduleData.imports |>.run
    let env ← finalizeImport state moduleData.imports {} 0 false false (isModule := true)
    let mut constants := {}
    for name in parts[parts.size - 1].1.constNames,
        info in parts[parts.size - 1].1.constants do
      constants := constants.insert name info
    let replayed ← env.replay constants
    replayed.freeRegions

/--
Resolve one absolute `.olean` path to Lean's exact module `Name`.

`searchModuleNameOfFileName` preserves quoted/name components using Lean's own
artifact/search-path semantics. We additionally require `findOLean` to resolve
that `Name` back to the exact same real file. A project artifact that shadows a
trusted toolchain or dependency module therefore fails before replay/auditing.
-/
private unsafe def moduleNameForArtifact
    (searchPath : SearchPath) (artifactText : String) : IO Name := do
  let artifact : System.FilePath := ⟨artifactText⟩
  let artifactReal ← IO.FS.realPath artifact
  let some moduleName ← searchModuleNameOfFileName artifactReal searchPath
    | throw <| IO.userError s!"cannot derive Lean module name from {artifactReal}"
  let resolved ← findOLean moduleName
  let resolvedReal ← IO.FS.realPath resolved
  unless resolvedReal == artifactReal do
    throw <| IO.userError
      s!"project module {moduleName} is shadowed: expected {artifactReal}, resolved {resolvedReal}"
  return moduleName

private def runProtectedAudit
    (env : Environment) (modules : Array Name) : IO Unit :=
  Core.CoreM.toIO'
    (ctx := { fileName := "cosmo-protected-audit", fileMap := default })
    (s := { env }) do
      let declarationCount ← auditImportedModulesCore modules
      IO.println
        s!"COSMO_PROTECTED_AUDIT_COMPLETE modules={modules.size} declarations={declarationCount} kernel_replay=verified project_initializers=not_executed"

private def pathWithin (path root : System.FilePath) : Bool :=
  let pathText := path.normalize.toString
  let rootText := root.normalize.toString
  pathText == rootText || pathText.startsWith (rootText ++ "/")

/--
Validate the actual dependency environment materialized before any COSMO module
is compiled.

The complete imported environment is replayed into a fresh kernel environment,
matching `leanchecker --fresh` semantics and catching malformed unchecked
proofs. Any axiom declaration whose defining module resolves outside the pinned
Lean toolchain is rejected. Dependencies may use toolchain foundations, but may
not introduce their own axioms.
-/
private unsafe def verifyDependencyEnvironment
    (toolchainRootText : String) (roots : Array Name) : IO Unit := do
  if roots.isEmpty then
    throw <| IO.userError "dependency verification requires at least one root module"
  let toolchainRoot ← IO.FS.realPath ⟨toolchainRootText⟩
  let imports := roots.map fun moduleName =>
    { module := moduleName : Lean.Import }
  Lean.withImportModules imports {} fun env => do
    let replayed ← (← mkEmptyEnvironment).replay env.constants.map₁
    replayed.freeRegions

    let mut unexpected : Array String := #[]
    let mut importedAxiomCount := 0
    for (declName, info) in env.constants.toList do
      match info with
      | .axiomInfo _ =>
          match env.getModuleIdxFor? declName with
          | none => pure ()
          | some moduleIdx =>
              let some moduleName := env.allImportedModuleNames[moduleIdx.toNat]?
                | throw <| IO.userError
                    s!"cannot resolve defining module for imported axiom {declName}"
              let moduleFile ← findOLean moduleName
              let moduleReal ← IO.FS.realPath moduleFile
              unless pathWithin moduleReal toolchainRoot do
                importedAxiomCount := importedAxiomCount + 1
                unexpected := unexpected.push
                  s!"{declName} from dependency module {moduleName} ({moduleReal})"
      | _ => pure ()

    unless unexpected.isEmpty do
      for finding in unexpected do
        IO.eprintln s!"DEPENDENCY-TRUST {finding}"
      throw <| IO.userError
        s!"dependency environment introduced {unexpected.size} axiom declaration(s)"

    IO.println
      s!"COSMO_DEPENDENCY_AUDIT_COMPLETE roots={roots.size} declarations={env.constants.toList.length} kernel_replay=verified dependency_axioms={importedAxiomCount}"

/--
Kernel-replay frozen project artifacts, then load and semantically audit their
exact modules without executing imported project `initialize` actions.

Project mode CLI arguments are absolute `.olean` paths, not dotted module-name
strings. This avoids lossy `String.toName` conversion for valid names such as
`Foo.«Bar.Baz»` and binds each audited name back to the exact captured artifact.

Dependency mode is:

`--dependency <pinned-toolchain-lib> <root-module> [<root-module> ...]`
-/
unsafe def _root_.main (args : List String) : IO Unit := do
  initSearchPath (← findSysroot)
  match args with
  | "--dependency" :: toolchainRoot :: rootTexts =>
      let roots := rootTexts.toArray.map String.toName
      verifyDependencyEnvironment toolchainRoot roots
  | artifactTexts =>
      if artifactTexts.isEmpty then
        throw <| IO.userError "COSMO protected audit requires at least one .olean artifact."
      let searchPath ← searchPathRef.get
      let mut modules : Array Name := #[]
      for artifact in artifactTexts do
        let moduleName ← moduleNameForArtifact searchPath artifact
        unless modules.contains moduleName do
          modules := modules.push moduleName

      for moduleName in modules do
        replayModule moduleName

      let imports := modules.map fun moduleName =>
        { module := moduleName : Lean.Import }
      Lean.withImportModules imports {} fun env =>
        runProtectedAudit env modules

end CosmoTrust
