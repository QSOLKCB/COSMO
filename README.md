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
- Project Lean warnings are treated as errors, so parsed `sorry` / `admit` admissions cannot survive as non-fatal build warnings even inside context-sensitive interpolation syntax.
- Project-authored `sorry`, `admit`, direct `sorryAx`, custom Lean `axiom` / `constant` declarations, all project `opaque` declarations, `native_decide`, direct `Lean.ofReduceBool` trust, and direct kernel-check bypasses are rejected by the trusted-core policy.
- The lexical trust scanner handles identifier-bang executable interpolation expressions, quoted trusted-base names, Lean identifier suffixes, raw and character literals, and symlinked `.lean` modules.
- CI builds only in a disposable workspace under an unprivileged `cosmobuild` identity that cannot modify the reviewed checkout or its trust programs.
- After compilation, all build-owned processes are terminated, tracked source is compared against the reviewed commit, and the project artifact tree is made root-owned and read-only.
- `scripts/prepare-lean-audit.py` parses the frozen Lake manifest, includes tracked local path packages, discovers every project-controlled `.olean`, rejects symlinked package/output paths and module shadowing, and derives a deterministic direct `LEAN_PATH`.
- The pinned `leanchecker` replays every captured project module through the kernel.
- The protected semantic runner is compiled from reviewed source, frozen read-only, and invoked directly with `lean`. It does **not** execute `lake`, `lake env`, project `lakefile.lean`, or imported project `initialize` actions under audit privileges.
- The semantic runner audits every declaration emitted by the captured project modules, rejects axiom-like and opaque declaration kinds, and checks transitive dependencies against the explicit allow-list `propext`, `Classical.choice`, and `Quot.sound`.
- CI synthesizes both a generated axiom and a malformed unchecked theorem and requires the semantic audit and kernel replay to reject them.
- Arithmetic decision proofs use kernel reduction (`decide`) rather than native-evaluator proof shortcuts.
- The Lucas-number computation proves `L_101 = 1281597540372340914251`.
- `L_101 mod 256 = 75` and the project quantization gives `floor(phi^101) mod 256 = 75`.
- `phiFloorMod` requires a proof that its modulus is positive, matching the Python API's rejection of zero modulus.
- The represented Dragon Seed payload is **8 bytes / 64 bits**.
- The arithmetic byte sum is **1512**.
- `1621` is retained only as a **declared symbolic invariant**, not a checksum.
- The exact DIAG `(1, -2, 1)` constant and affine identities are proved over integers.
- The Float DIAG function remains executable but is not presented as a universal algebraic theorem.

The ban on project `opaque` declarations is intentionally conservative for this baseline. It closes both source-written and generated opaque declaration paths without asking the lightweight source lexer to distinguish bodyless from bodyful syntax. A future need for legitimate opacity should be introduced with an explicit trust-policy change and semantic audit coverage.

## Repository map

| Path | Purpose |
|---|---|
| `COSMO.lean` | Aggregate root for the current COSMO library |
| `cosmovirus.lean` | Machine-checked discrete core |
| `CosmoTrust.lean` | Semantic environment audit and non-initializing protected runner |
| `cosmovirus.py` | Deterministic Python mirror |
| `tests/` | Python regression tests |
| `scripts/check-lean-trust.sh` | Fast lexical preflight for forbidden Lean source constructs |
| `scripts/prepare-lean-audit.py` | Frozen manifest, artifact, symlink, and local-package audit layout validation |
| `scripts/run-lean-integrity-ci.sh` | Isolated build, kernel replay, protected semantic audit, and negative fixtures |
| `audit/AxiomAudit.lean` | Local package-audit convenience entry point |
| `audit/AUDIT-RESOLUTION.md` | Disposition of the September 2026 audit findings |
| `KNOWN_LIMITATIONS.md` | Explicit trust and scope boundaries |
| `cosmovirus.tex` | Formal/symbolic specification source |
| `cosmovirus_cattheory.tex` | Category-theory design sketch |
| `Sources.zip` | Historical source/interpretive material supplied to the project |

The bundled source PDFs and prebuilt PDFs predate this integrity baseline. Treat them as historical inputs until the later documentation/publication pass regenerates them from the corrected source of truth.

## Build the Lean core locally

Install `elan`, then from the repository root:

```bash
lake build
./scripts/check-lean-trust.sh
lake env leanchecker COSMO CosmoTrust cosmovirus
lake env lean audit/AxiomAudit.lean
```

These commands are useful local checks. The authoritative CI boundary is stronger: it performs the build under a separate identity, freezes and inventories the resulting artifact graph, and runs direct non-Lake kernel and semantic audits against that frozen graph. `scripts/run-lean-integrity-ci.sh` expects the GitHub Actions environment and `sudo`; it is not intended as the ordinary local developer command.

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
