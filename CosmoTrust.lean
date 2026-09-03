import Lean.Compiler.ModPkgExt
import Lean.CoreM
import Lean.Elab.Command
import Lean.Environment
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

private def runProtectedAudit
    (env : Environment) (modules : Array Name) : IO Unit :=
  Core.CoreM.toIO'
    (ctx := { fileName := "cosmo-protected-audit", fileMap := default })
    (s := { env }) do
      let declarationCount ← auditImportedModulesCore modules
      IO.println
        s!"COSMO_PROTECTED_AUDIT_COMPLETE modules={modules.size} declarations={declarationCount} project_initializers=not_executed"

/--
Load frozen project modules without executing their `initialize` actions, then
audit every declaration emitted by exactly those captured modules.
-/
unsafe def _root_.main (args : List String) : IO Unit := do
  let modules := args.toArray.map String.toName
  if modules.isEmpty then
    throw <| IO.userError "COSMO protected audit requires at least one module name."
  let imports := modules.map fun moduleName =>
    { module := moduleName : Lean.Import }
  Lean.withImportModules imports {} fun env =>
    runProtectedAudit env modules

end CosmoTrust
