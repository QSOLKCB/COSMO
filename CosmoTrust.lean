import Lean.Compiler.ModPkgExt
import Lean.Elab.Command
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

/-- Declaration kinds that cannot belong to the trusted project package. -/
private def declarationKindViolation? (info : ConstantInfo) : Option String :=
  match info with
  | .axiomInfo _ => some "project-generated axiom declaration"
  | .opaqueInfo _ => some "project opaque declaration"
  | _ => none

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

/--
Audit named declarations semantically in Lean's environment.

This does not depend on their source spelling. A declaration emitted by a macro
or command elaborator is inspected exactly like a declaration written directly.
-/
meta def auditNamedDeclarations
    (scope : String) (declarations : Array Name) : CommandElabM Unit := do
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
        logInfo m!"TRUST-AUDIT {declName}: allowed foundations [{renderNames allowed}]"

  if failures.isEmpty then
    logInfo m!"COSMO semantic trust audit passed for {declarations.size} declaration(s) in {scope}."
  else
    for failure in failures do
      logError m!"{failure}"
    throwError m!"COSMO semantic trust audit failed with {failures.size} finding(s) in {scope}."

/--
Discover the Lake package from an imported anchor module, then audit every
imported declaration built by that package. This automatically covers generated
declarations and future project modules in the same Lake package.
-/
meta def auditImportedPackageFrom (anchorModule : Name) : CommandElabM Unit := do
  let env ← getEnv
  let some moduleIdx := env.getModuleIdx? anchorModule
    | throwError m!"COSMO semantic trust audit cannot find imported module {anchorModule}."
  let some packageId := env.getModulePackageByIdx? moduleIdx
    | throwError m!"COSMO semantic trust audit found no Lake package for {anchorModule}."
  auditNamedDeclarations
    s!"Lake package {packageId} (anchored at {anchorModule})"
    (importedPackageDeclarations env packageId)

end CosmoTrust
