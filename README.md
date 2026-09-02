# COSMO

**COSMO / Cosmovirus Formalization** is a symbolic-computational research project that turns an interdisciplinary mapping into explicit data, executable functions, and machine-checkable mathematical statements.

The repository deliberately separates what is **proved or computed** from what is **scientifically sourced**, **hypothesized**, or **symbolically interpreted**. Lean compilation proves consequences of Lean definitions. It does not prove that symbolic labels correspond to physical, biomedical, archaeological, or cosmological mechanisms.

## Evidence and claim classes

| Class | Meaning | Repository language |
|---|---|---|
| **FORMAL** | Kernel-checked mathematical consequence | “Lean proves …” |
| **COMPUTATIONAL** | Deterministic program output | “The program computes …” |
| **SCIENTIFIC** | Claim supported by external scientific literature | “The literature reports …” |
| **HYPOTHESIS** | Testable cross-domain proposal not yet validated | “COSMO hypothesizes …” |
| **SYMBOLIC** | Artistic, mythological, or interpretive mapping | “COSMO symbolically associates …” |

The current Lean/Python core is intentionally narrow. The six COSMO layer names remain project vocabulary, while the code proves only the finite-state and arithmetic facts explicitly stated in the source.

## Verified baseline

PR A establishes the first reproducible integrity baseline:

- Lean 4 is pinned to **v4.33.1**.
- Mathlib is pinned to commit `0df444a360eaa60ab8c11dca51a86af692955474` (tag `v4.33.1`).
- project Lean warnings are treated as errors, so parsed `sorry` / `admit` admissions cannot survive as non-fatal build warnings even inside context-sensitive interpolation syntax;
- project-authored `sorry`, `admit`, direct `sorryAx`, custom Lean `axiom` / `constant` declarations, all project `opaque` declarations, `native_decide`, and direct `Lean.ofReduceBool` trust are rejected by the trusted-core policy;
- the trust scanner handles identifier-bang executable interpolation expressions (including `s!`, `m!`, `f!`, `v!` and project-defined macros with the same lexical shape), quoted trusted-base names, Lean identifier suffixes, raw string literals, and symlinked `.lean` modules;
- exported theorem axiom dependencies are printed in CI and checked against the explicit allow-list `propext`, `Classical.choice`, and `Quot.sound`;
- arithmetic decision proofs use kernel reduction (`decide`) rather than native-evaluator proof shortcuts;
- the Lucas-number computation proves `L_101 = 1281597540372340914251`;
- `L_101 mod 256 = 75` and the project quantization gives `floor(phi^101) mod 256 = 75`;
- `phiFloorMod` requires a proof that its modulus is positive, matching the Python API's rejection of zero modulus;
- the represented Dragon Seed payload is **8 bytes / 64 bits**;
- the arithmetic byte sum is **1512**;
- `1621` is retained only as a **declared symbolic invariant**, not a checksum;
- the exact DIAG `(1, -2, 1)` constant and affine identities are proved over integers;
- the Float DIAG function remains executable but is not presented as a universal algebraic theorem.

The ban on project `opaque` declarations is intentionally conservative for this baseline. It closes the bodyless-opaque axiom-like declaration path without asking the lightweight source lexer to distinguish bodyless from bodyful opaque syntax. A future need for legitimate opacity should be introduced with an explicit trust-policy change and semantic audit coverage.

## Repository map

| Path | Purpose |
|---|---|
| `cosmovirus.lean` | Machine-checked discrete core |
| `cosmovirus.py` | Deterministic Python mirror |
| `tests/` | Python regression tests |
| `audit/AxiomAudit.lean` | Lean axiom-dependency report |
| `audit/AUDIT-RESOLUTION.md` | Disposition of the September 2026 audit findings |
| `KNOWN_LIMITATIONS.md` | Explicit trust and scope boundaries |
| `cosmovirus.tex` | Formal/symbolic specification source |
| `cosmovirus_cattheory.tex` | Category-theory design sketch |
| `Sources.zip` | Historical source/interpretive material supplied to the project |

The bundled source PDFs and prebuilt PDFs predate this integrity baseline. Treat them as historical inputs until the later documentation/publication pass regenerates them from the corrected source of truth.

## Build the Lean core

Install `elan`, then from the repository root:

```bash
lake build
./scripts/check-lean-trust.sh
lake env lean audit/AxiomAudit.lean
```

The pinned `lean-toolchain` and exact Mathlib revision define the formal build environment. The Lake package enables `warningAsError`, so a project warning is a build failure rather than advisory output.

## Run the Python checks

The runtime module has no third-party dependency.

```bash
python -m unittest discover -s tests -v
python -m compileall -q cosmovirus.py tests
```

For the CI-equivalent static check:

```bash
python -m pip install -r requirements-dev.txt
mypy --strict cosmovirus.py tests/test_cosmovirus.py
```

## Current design status

The present `psiEquation` is explicitly marked **legacy**. It is a four-function finite-state composition and is not yet identical to the six-generator cycle described by the category-theory document. The planned next architecture pass will define a single authoritative six-state transition system and derive the categorical view from it.

See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) before interpreting any cross-domain COSMO mapping as an empirical claim.

## License

MIT. See [`LICENSE`](LICENSE).
