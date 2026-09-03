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
- The project imports only the Lean `omega` tactic and Mathlib `Ring` tactic surface it currently needs rather than the umbrella `Mathlib` module.
- Project Lean warnings are treated as errors, so parsed `sorry` / `admit` admissions cannot survive as non-fatal warnings even inside context-sensitive interpolation syntax.
- Project-authored `sorry`, `admit`, direct `sorryAx`, custom Lean `axiom` / `constant` declarations, all project `opaque` declarations, `native_decide`, direct `Lean.ofReduceBool` trust, and direct kernel-check bypasses are rejected by the trusted-core policy.
- The lexical trust scanner handles identifier-bang executable interpolation expressions, quoted trusted-base names, Lean identifier suffixes, raw and character literals, and symlinked `.lean` modules.
- CI materializes a disposable workspace under an unprivileged `cosmobuild` identity that cannot modify the reviewed checkout or its trust programs.
- Lake is used only before project compilation to regenerate the pinned dependency manifest and materialize dependency artifacts. PR A deliberately rejects local Lake `path` packages rather than recursively trusting mutable nested manifests.
- After dependency resolution, all build-owned processes are terminated and the manifest, dependency sources, and dependency artifacts are made root-owned and read-only.
- CI records a deterministic run-local receipt over every dependency build artifact before project compilation and requires the complete 130,468-file set to remain byte-identical afterward. The receipt is immutability evidence for that run, not a self-authenticating provenance claim.
- COSMO's reviewed library modules are then compiled directly with the pinned `lean` binary and `warningAsError`, in dependency order, into the only project-owned writable output directory. Lake is not invoked while project modules are executing.
- `scripts/prepare-lean-audit.py` discovers every captured project `.olean`, rejects symlinked or non-standard proof outputs, rejects hidden/custom `.olean` trees, preserves Lean module-name round trips, and derives a deterministic direct `LEAN_PATH` whose search order is pinned toolchain, frozen dependencies, then project outputs.
- The reviewed semantic runner is compiled before project modules are loaded, with only the pinned Lean toolchain visible, then frozen root-owned and read-only.
- From the finished project module headers, the runner derives the exact external dependency roots COSMO actually imports. That dependency closure is replayed into a fresh kernel environment and may not introduce axioms outside the pinned Lean toolchain.
- Every captured COSMO module is then kernel-replayed and every declaration it emits is semantically audited without executing imported project `initialize` actions.
- The semantic audit rejects axiom-like and opaque project declaration kinds and checks transitive dependencies against the explicit allow-list `propext`, `Classical.choice`, and `Quot.sound`.
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

The ban on local Lake `path` packages is also deliberate for PR A. Supporting them safely requires reviewed recursive configuration provenance. Until that policy exists, introducing one is a hard CI failure rather than a silent expansion of the trusted project surface.

## Repository map

| Path | Purpose |
|---|---|
| `COSMO.lean` | Aggregate root for the current COSMO library |
| `cosmovirus.lean` | Machine-checked discrete core |
| `CosmoTrust.lean` | Semantic environment audit, dependency-closure replay, and non-initializing protected runner |
| `cosmovirus.py` | Deterministic Python mirror |
| `tests/` | Python regression tests |
| `scripts/check-lean-trust.sh` | Fast lexical preflight for forbidden Lean source constructs |
| `scripts/prepare-lean-audit.py` | Frozen manifest, artifact, symlink, path-package, and import-layout validation |
| `scripts/verify-lean-dependency-artifacts.py` | Run-local dependency artifact receipt and immutability verification |
| `scripts/run-lean-integrity-ci.sh` | Isolated dependency resolution, direct project compilation, kernel replay, semantic audit, and negative fixtures |
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

These commands are useful local checks. The authoritative CI boundary is stronger: it resolves dependencies before project execution, freezes and fingerprints them, directly compiles the reviewed COSMO modules with the pinned Lean binary, derives the actual external dependency closure from the resulting module headers, and performs direct non-Lake kernel and semantic audits against the frozen graph. `scripts/run-lean-integrity-ci.sh` expects the GitHub Actions environment and `sudo`; it is not intended as the ordinary local developer command.

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
