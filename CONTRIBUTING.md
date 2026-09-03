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

`lake build` runs the COSMO package with Lean's `warningAsError` option enabled. This is a compiler-level backstop: if Lean parses a synthetic-sorry warning from executable syntax, the build fails even when that syntax is outside the lightweight lexical scanner's model.

The source preflight treats executable identifier-bang interpolation expressions as code, recognizes Lean identifier suffixes, masks ordinary, raw, and character literals correctly, preserves dangerous quoted trusted-base names for inspection, and scans `.lean` symlinks as source modules.

Local commands are not the complete protected boundary. GitHub Actions archives the reviewed commit into a disposable workspace and executes `lake build` under an unprivileged `cosmobuild` identity that cannot write the reviewed checkout. Once compilation ends, CI terminates that identity's processes, verifies every tracked file against the reviewed source, and freezes the artifact tree root-owned and read-only.

The protected audit then:

1. parses the frozen `lake-manifest.json`, including tracked local `path` packages;
2. discovers every project-controlled `.olean` output rather than assuming one package root;
3. rejects symlinked package/output paths, symlinked `.olean` files, and project module shadowing;
4. runs the pinned `leanchecker` directly over every captured project module;
5. compiles the reviewed semantic runner without importing project modules, then freezes it read-only;
6. invokes `lean` directly with a derived frozen `LEAN_PATH`, never `lake` or `lake env` under audit privileges;
7. loads captured project modules with `Lean.withImportModules` without project initializers;
8. rejects axiom-like or opaque declaration kinds and any transitive dependency outside `propext`, `Classical.choice`, and `Quot.sound`.

CI also builds intentional generated-axiom and unchecked-malformed-theorem fixtures, then requires the semantic audit and kernel replay to reject them. Changes to macros, elaborators, package roots, local path dependencies, artifact layout, or trust tooling must preserve those negative tests.

The current baseline intentionally forbids `opaque` declarations altogether. If a future formalization genuinely needs an opaque definition, propose a reviewed trust-policy change together with semantic audit coverage.

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
