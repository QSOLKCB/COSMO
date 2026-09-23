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
- CI records a deterministic run-local receipt over every dependency build artifact before project compilation and requires the complete dependency set to remain byte-identical afterward. The receipt is immutability evidence for that run, not a self-authenticating provenance claim.
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

The ban on local Lake `path` packages is also deliberate for the current protected boundary. Supporting them safely requires reviewed recursive configuration provenance. Until that policy exists, introducing one is a hard CI failure rather than a silent expansion of the trusted project surface.

## Phase B1 verified dependency reuse

Phase B1 applies immutable QSOL OPT v1.0.0 record `OPT-LEAN-001` without changing the theorem or audit contract.

The routine GitHub Actions lane separates dependency reuse into two independently authenticated cache classes:

- **source state**, verified against the frozen manifest revisions, tracked Git bytes/modes, worktree closure, and hardened Git metadata rules; and
- **compiled dependency artifacts**, verified against the reviewed external anchor in `audit/lean-dependency-anchor.json`.

A cache key is never proof authority. The complete current COSMO module set is rebuilt from reviewed source after dependency state has been authenticated and frozen. `scripts/run-lean-verified-reuse-ci.sh` is the protected routine runner used by `.github/workflows/ci.yml`.

`.github/workflows/lean-cold-trust.yml` is the separate no-cache reconstruction lane. Pull-request executions validate the cold path; only a successful manual dispatch is intended to support a release-grade statement that the dependency graph was reconstructed from pinned source on that exact run. See [`LEAN-CACHE-POLICY.md`](LEAN-CACHE-POLICY.md) for the normative evidence boundary.

## Phase B2 canonical deterministic core

Phase B2 applies immutable QSOL OPT v1.0.0 records `OPT-PY-001` and `OPT-INV-001` to the reusable Python computation layer.

The `cosmo_core/` package is now the canonical runtime source for:

- immutable constants, including distinct `GOLDEN_RATIO` and `QUARTER_TURN_RADIANS` names;
- exact Lucas / phi-floor integer arithmetic;
- Dragon Seed payload measurements and SHA-256 identity;
- extended Hamming SECDED `(8, 4, 4)` nibble codewords with single-bit correction and double-bit detection;
- strict uppercase `A/C/G/T` byte encoding with invalid-symbol rejection;
- canonical JSON bytes and SHA-256 integrity helpers; and
- experiment manifests that bind a non-negative seed, scalar parameters, input byte identities, and output byte identities.

`cosmovirus.py` remains the compatibility-facing executable wrapper and delegates its deterministic arithmetic and payload operations to `cosmo_core` rather than maintaining a second implementation.

The SECDED layer claims only its documented codeword capability. The full storage experiment and corruption/recovery round-trip remain Phase B5 work.

## Phase B3 exact E8 and Weyl core

Phase B3 applies immutable QSOL OPT v1.0.0 record `OPT-INV-001` to the first explicit E8 mathematical representation in COSMO.

`cosmo_core/e8.py` uses **doubled integer coordinates**: an integer tuple `v` represents the mathematical vector `v / 2`. This keeps the complete root system and Weyl action exact:

- 112 integer-family roots with two `±2` doubled coordinates;
- 128 half-integer-family roots with eight `±1` doubled coordinates and an even number of negative signs;
- 240 unique roots in deterministic lexicographic order;
- exact rank 8 and squared norm 2 validation using rational arithmetic;
- exact E8-lattice membership in doubled coordinates;
- Weyl reflections `s_alpha(x) = x - <x, alpha> alpha`;
- root-system closure, reflection involution, norm preservation, hyperplane fixed points, and lattice preservation checks;
- one immutable cached canonical root/reflection table, accepted only after regeneration through the uncached reference path; and
- reviewed canonical root-table SHA-256 `f6e7675c180edb41ea1c47705d7b14daeed7e08f3791dbdf1fc0c55ef156b662`.

The canonical Weyl-reflection order is exactly the canonical root order. No floating-point geometry is used by the B3 E8 core.

## Phase B4 deterministic triadic lattice and recovery

Phase B4 applies immutable QSOL OPT v1.0.0 records `OPT-PAR-001` and `OPT-INV-001` to a strictly computational 8×8×8 ternary lattice.

`cosmo_core/triadic.py` provides:

- immutable 512-cell states over `{0, 1, 2}`;
- stateless SplitMix64-derived seeded initialization with replayable SHA-256 identity;
- periodic six-neighbour synchronous local updates;
- an uncached topology reference generator plus one immutable cached neighbour table;
- optional base-3 digit-residue masks, explicitly treated as computational textures rather than physical/fractal claims;
- exact loop-closure distance `D_n(x) = ||T^n(x) - x||^2`;
- exact repeat/cycle detection plus normalized state-population entropy;
- a generic ternary codebook/recovery protocol;
- a concrete length-3 ternary repetition code with one-trit correction capability and explicit uncorrectable syndromes; and
- full-lattice recovery receipts recording corrected blocks, uncorrectable blocks, syndromes, and discrete recovery passes.

The scalar update is authoritative. The bounded parallel path reads only the immutable prior state, uses deterministic contiguous partitions, restores canonical cell order before output construction, caps workers against conservative runtime capacity (host CPU count, process affinity, Linux cgroup quota when visible, and a hard bound), and records requested, configured/effective, and actually observed worker-thread counts separately. Python threads are an execution mechanism only; this phase makes no multicore speedup claim.

## Phase B5 storage / DNA / ECC round-trip contract

Phase B5 applies immutable QSOL OPT v1.0.0 records `OPT-PY-001` and `OPT-INV-001` to the storage path and closes the roadmap invariant:

`cube -> bytes -> ECC -> ACGT -> corruption -> ECC correction -> bytes -> cube`

The authoritative cube is the Phase B4 `TriadicLattice`. Its 512 cells serialize canonically as 512 bytes, one byte per ternary state `0/1/2`. `cosmo_core/storage.py` then composes the already-validated B2 primitives:

- extended Hamming SECDED `(8,4,4)`, two codewords per payload byte;
- strict uppercase `A/C/G/T` conversion with no normalization or coercion;
- exact encoded-bit corruption applied while retaining valid ACGT representation;
- SHA-256 binding of source payload, clean ECC bytes, and clean DNA artifact;
- post-ECC SHA-256 verification so higher-weight SECDED miscorrections cannot silently become successful storage recovery;
- canonical, explicitly synthetic FASTA labels and 80-column wrapping; and
- immutable recovery receipts recording corrected codewords and overall-parity corrections.

The clean seed-0 cube is regression-bound to:

- payload SHA-256 `2ba2a34b1dde358045011fbe4dc9dce04da9f56ff34f2eec774486218bb7a6eb`;
- ECC SHA-256 `2be07b5508b379c43912d9b853dad558ec2e9c89b0343b388047ab06c2505f3c`; and
- DNA SHA-256 `3df2e0a473defda6695f2a9f57c98114fe9f2162c9c0c25af326466bda708be4`.

ECC and integrity have distinct roles: SECDED performs correction/detection; SHA-256 authenticates the recovered bytes. Synthetic FASTA is a deterministic storage container only, not a biological sequence claim.

## Repository map

| Path | Purpose |
|---|---|
| `COSMO.lean` | Aggregate root for the current COSMO library |
| `cosmovirus.lean` | Machine-checked discrete core |
| `CosmoTrust.lean` | Semantic environment audit, dependency-closure replay, and non-initializing protected runner |
| `cosmo_core/` | Canonical deterministic Python arithmetic, payload, ECC, DNA, integrity, manifest, and exact E8/Weyl primitives |
| `cosmo_core/e8.py` | Exact doubled-coordinate E8 roots, lattice predicates, canonical identity, and Weyl reflections |
| `cosmo_core/triadic.py` | Deterministic 8×8×8 ternary lattice, bounded parallel updates, diagnostics, and recovery model |
| `cosmo_core/storage.py` | B5 cube/bytes/SECDED/ACGT/synthetic-FASTA round-trip and integrity receipts |
| `cosmovirus.py` | Compatibility-facing Python mirror backed by `cosmo_core` |
| `tests/` | Python regression tests covering B2 codecs, B3 roots/reflections, B4 lattice/recovery, and B5 storage corruption contracts |
| `scripts/check-lean-trust.sh` | Fast lexical preflight for forbidden Lean source constructs |
| `scripts/prepare-lean-audit.py` | Frozen manifest, artifact, symlink, path-package, and import-layout validation |
| `scripts/verify-lean-source-state.py` | Hardened Git dependency-source identity and source-cache receipt verification |
| `scripts/verify-lean-dependency-artifacts.py` | Reviewed dependency-artifact anchor plus run-local immutability receipts |
| `scripts/run-lean-verified-reuse-ci.sh` | Authoritative protected routine B1 rebuild, kernel replay, semantic audit, and negative fixtures |
| `scripts/run-lean-integrity-ci.sh` | Historical PR-A integrity runner retained for baseline provenance, not the active B1 CI entry point |
| `.github/workflows/ci.yml` | Routine verified-reuse CI orchestration |
| `.github/workflows/lean-cold-trust.yml` | No-cache cold reconstruction and validation lane |
| `LEAN-CACHE-POLICY.md` | Normative B1 cache, trust, evidence, and rollback policy |
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

These commands are useful local checks. The authoritative routine CI boundary is stronger: `.github/workflows/ci.yml` independently verifies dependency source and compiled-artifact identities, freezes them, then invokes `scripts/run-lean-verified-reuse-ci.sh` to directly compile the reviewed COSMO modules with the pinned Lean binary, derive the actual external dependency closure from the resulting module headers, and perform direct non-Lake kernel and semantic audits against the frozen graph. The protected runner expects the GitHub Actions isolation environment and `sudo`; it is not an ordinary local developer command.

For release-grade dependency reconstruction, use the separately documented manual cold-trust workflow rather than describing a verified-cache run as a cold build.

## Run the Python checks

The runtime module has no third-party dependency.

```bash
python -m unittest discover -s tests -v
(cd tests && python test_cosmovirus.py)
(cd tests && python test_phase_b2.py)
(cd tests && python test_phase_b3.py)
(cd tests && python test_phase_b4.py)
(cd tests && python test_phase_b5.py)
python -m compileall -q cosmo_core cosmovirus.py tests
```

The direct test invocation is supported as well as discovery, so the regression suite can be run from inside the `tests/` directory without installing COSMO as a package.

For the CI-equivalent static check:

```bash
python -m pip install -r requirements-dev.txt
mypy --strict cosmo_core cosmovirus.py tests/test_cosmovirus.py tests/test_phase_b2.py tests/test_phase_b3.py tests/test_phase_b4.py tests/test_phase_b5.py
```

## Current design status

The present `psiEquation` is explicitly marked **legacy**. It is a four-function finite-state composition and is not yet identical to the six-generator cycle described by the category-theory document. Phase C will replace it with the authoritative six-state transition system after the intervening deterministic E8, lattice, and storage phases.

See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) before interpreting any cross-domain COSMO mapping as an empirical claim.

## License

MIT. See [`LICENSE`](LICENSE).
