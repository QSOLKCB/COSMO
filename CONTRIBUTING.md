# Contributing to COSMO

COSMO welcomes mathematical, software, scientific-source, and symbolic contributions, but they must not be blended into one evidence class.

## Required claim classification

When adding or changing a substantive claim, identify it as one of:

- **FORMAL**: machine-checked mathematical consequence;
- **COMPUTATIONAL**: deterministic executable result;
- **SCIENTIFIC**: externally sourced domain statement;
- **HYPOTHESIS**: testable but unvalidated proposal;
- **SYMBOLIC**: artistic, mythological, or interpretive mapping.

A formal theorem about a project-defined label does not automatically establish the label's scientific interpretation.

## Lean changes

Before opening a PR, run the ordinary local checks:

```bash
lake build
./scripts/check-lean-trust.sh
lake env leanchecker COSMO CosmoTrust cosmovirus
lake env lean audit/AxiomAudit.lean
```

The trusted core rejects project-authored `sorry`, `admit`, direct `sorryAx`, custom `axiom` or `constant` declarations, all project `opaque` declarations, `native_decide`, direct `Lean.ofReduceBool` trust, and direct kernel-check bypasses such as `debug.skipKernelTC` or `addDeclWithoutChecking`. Arithmetic decision proofs should use kernel reduction (`decide`) or another proof-producing tactic.

The ordinary local `lake build` runs the COSMO package with Lean's `warningAsError` option enabled. Protected CI applies the same warning policy directly through the pinned `lean` executable, so an admission parsed from executable syntax remains fatal even though Lake is not allowed to manage project compilation inside the protected boundary.

The source preflight treats executable identifier-bang interpolation expressions as code, recognizes Lean identifier suffixes, masks ordinary, raw, and character literals correctly, preserves dangerous quoted trusted-base names for inspection, and scans `.lean` symlinks as source modules.

Local commands are not the complete protected boundary. GitHub Actions archives the reviewed commit into a disposable workspace and uses Lake only to regenerate the pinned dependency configuration before any COSMO project module is compiled. The build identity is then terminated, local Lake `path` packages are rejected, and the manifest plus dependency tree are made root-owned and read-only.

The protected CI path then:

1. records a deterministic run-local receipt over every dependency build artifact before COSMO compilation;
2. compiles the reviewed `CosmoTrust`, `cosmovirus`, and `COSMO` modules directly with the pinned `lean` binary and warnings-as-errors, giving the project identity write access only to the isolated project output directory;
3. requires the dependency receipt and fresh Lake manifest to remain byte-identical after project compilation;
4. verifies every tracked project source path against the reviewed checkout;
5. discovers the exact regular project `.olean` set, rejects symlinked or non-standard output trees, and gives the pinned toolchain priority over dependency and project paths during module resolution;
6. derives the external dependency roots from the direct imports encoded in the compiled project headers rather than from a hand-maintained root list;
7. replays that exact dependency closure into a fresh kernel environment and rejects dependency-introduced axiom declarations outside the pinned Lean toolchain;
8. kernel-replays every captured project module and semantically audits every declaration it emits without executing project initializers;
9. rejects axiom-like or opaque project declaration kinds and any transitive dependency outside `propext`, `Classical.choice`, and `Quot.sound`.

CI also builds intentional generated-axiom and unchecked-malformed-theorem fixtures, then requires the semantic audit and kernel replay to reject them.

PR A intentionally forbids local Lake `path` packages. Supporting them safely requires a reviewed recursive configuration-provenance policy. Do not add a path package by weakening or bypassing this gate; propose the trust-policy change explicitly.

The current baseline also intentionally forbids `opaque` declarations altogether. If a future formalization genuinely needs an opaque definition, propose a reviewed trust-policy change together with semantic audit coverage.

The protected module compilation list mirrors the reviewed `lean_lib` module set in `lakefile.lean`. Adding or removing a configured COSMO module therefore requires updating the protected compilation list in the same change; an unreviewed sibling root must never sit outside kernel replay and semantic auditing.

If a future theorem requires assumptions, make them explicit in the theorem statement or propose a reviewed foundation-policy change rather than hiding the dependency.

## Python changes

```bash
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
mypy --strict cosmovirus.py tests/test_cosmovirus.py
```

Derived numeric constants should be tested or generated rather than copied without a provenance path.

## Cross-domain claims

Scientific claims should identify a primary or authoritative source. A new hypothesis should state what mapping is proposed and what observation would count against it. Symbolic material is welcome when it is clearly labelled as symbolic.
