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

Before opening a PR:

```bash
lake build
./scripts/check-lean-trust.sh
lake env lean audit/AxiomAudit.lean
```

The trusted core rejects project-authored `sorry`, `admit`, direct `sorryAx`, custom `axiom` or `constant` declarations, all project `opaque` declarations, `native_decide`, and direct `Lean.ofReduceBool` trust. Arithmetic decision proofs should use kernel reduction (`decide`) or another proof-producing tactic.

`lake build` runs the COSMO package with Lean's `warningAsError` option enabled. This is a compiler-level backstop: if Lean parses a synthetic-sorry warning from any executable syntax, including context-sensitive interpolation forms, the build fails even if that syntax is outside the lightweight lexical scanner's model.

The source preflight separately treats executable identifier-bang interpolation expressions as code (covering built-ins such as `s!`, `m!`, `f!`, `v!` and project macros with the same lexical shape), recognizes Lean identifier suffixes such as `'`, `?`, and `!`, masks ordinary and raw string literals correctly, preserves dangerous quoted trusted-base names for inspection, and scans `.lean` symlinks as source modules.

Source scanning is not the final trust decision. `CosmoTrust.lean` examines Lean's elaborated environment after compilation, discovers every declaration emitted by the COSMO Lake package, rejects forbidden declaration kinds, and checks the transitive dependencies of every declaration against the reviewed foundation allow-list `propext`, `Classical.choice`, and `Quot.sound`. This includes private, auxiliary, macro-generated, and command-elaborator-generated declarations, so adding a theorem to a maintained audit list is no longer required.

CI also builds an intentional `Declaration.axiomDecl` fixture and requires the semantic audit to fail. Changes to macros, elaborators, package roots, or the trust audit must preserve that negative regression test.

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
