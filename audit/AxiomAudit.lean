import CosmoTrust
import cosmovirus

/--
Audit every declaration emitted by the COSMO Lake package, including private,
generated, auxiliary, theorem, and definition declarations. The package is
discovered from the imported `cosmovirus` module rather than from a maintained
list of theorem names.
-/
run_cmd CosmoTrust.auditImportedPackageFrom `cosmovirus
