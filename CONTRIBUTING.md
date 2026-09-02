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

Project-authored `sorry` and custom `axiom` declarations are not accepted in the trusted core. If a future theorem requires assumptions, make the assumptions explicit in the theorem statement or propose a reviewed axiom-policy change rather than hiding the dependency.

## Python changes

```bash
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
mypy --strict cosmovirus.py tests/test_cosmovirus.py
```

Derived numeric constants should be tested or generated rather than copied without a provenance path.

## Cross-domain claims

Scientific claims should identify a primary or authoritative source. A new hypothesis should state what mapping is proposed and what observation would count against it. Symbolic material is welcome when it is clearly labelled as symbolic.
