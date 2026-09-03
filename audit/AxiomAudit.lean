import COSMO

/-
Local audit entry point for the canonical `COSMO` aggregate root.

The authoritative CI audit does not assume this is the only root. After the
isolated Lake build, CI enumerates every project `.olean`, imports every built
module into a generated audit module, and then applies the same package-wide
semantic declaration audit. Adding another configured root therefore adds it
to the CI import set automatically rather than leaving its declarations absent
from `env.constants`.
-/
run_cmd CosmoTrust.auditImportedPackageFrom `COSMO