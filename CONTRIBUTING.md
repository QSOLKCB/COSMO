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

The trusted core rejects project-authored `sorry`, `admit`, direct `sorryAx`, custom `axiom` or `constant` declarations, all project `opaque` declarations, `native_decide`, and direct `Lean.ofReduceBool` trust. Arithmetic decision proofs should use kernel reduction (`decide`) or another proof-producing tactic. CI also checks exported theorem dependencies against the reviewed allow-list `propext`, `Classical.choice`, and `Quot.sound`.

`lake build` runs the COSMO package with Lean's `warningAsError` option enabled. This is a compiler-level backstop: if Lean parses a synthetic-sorry warning from any executable syntax, including context-sensitive interpolation forms, the build fails even if that syntax is outside the lightweight lexical scanner's model.

The trust scanner separately treats executable identifier-bang interpolation expressions as code (covering built-ins such as `s!`, `m!`, `f!`, `v!` and project macros with the same lexical shape), recognizes Lean identifier suffixes such as `'`, `?`, and `!`, masks ordinary and raw string literals correctly, preserves dangerous quoted trusted-base names for inspection, and scans `.lean` symlinks as source modules.

The current baseline intentionally forbids `opaque` declarations altogether rather than attempting to distinguish bodyless axiom-like opaque declarations from bodyful opaque definitions in a lightweight lexer. If a future formalization genuinely needs an opaque definition, propose a reviewed trust-policy change together with semantic audit coverage.

If a future theorem requires assumptions, make them explicit in the theorem statement or propose a reviewed axiom-policy change rather than hiding the dependency.

## Python changes

```bash
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
mypy --strict cosmovirus.py tests/test_cosmovirus.py
```

Derived numeric constants should be tested or generated rather than copied without a provenance path.

## Cross-domain claims

Scientific claims should identify a primary or authoritative source. A new hypothesis should state what mapping is proposed and what observation would count against it. Symbolic material is welcome when it is clearly labelled as symbolic.
