# Known Limitations

This file is part of COSMO's trust boundary. A green build means the checked code satisfies the statements encoded in that build. It does **not** upgrade symbolic labels into empirical evidence.

## Formal model

- `CosmoLayer` is currently a six-constructor finite type. Its constructor names do not formalize E8, SiS2, HPV16, or archaeological objects themselves.
- `psiEquation` is a legacy four-function composition. It does not match the six-generator category-theory cycle one-for-one. That reconstruction is intentionally deferred to PR C.
- The category-theory paper is a design sketch. Its retract, natural-transformation, endofunctor, and periodicity claims are not yet Lean theorems.
- `phiFloorQuantized` encodes the Lucas parity rule used by the project. PR A proves the concrete integer results needed by the baseline, but does not yet formalize the real-analysis theorem relating the definition to `Real.floor` for every exponent.
- `diagApplyFloat` is executable only. No theorem assumes unrestricted floating-point arithmetic behaves as an exact ring.

## Data and symbolic mappings

- The represented Dragon Seed payload contains 8 bytes, hence 64 bits. `101` is currently a project mnemonic, not represented payload length.
- The value 1621 is not derived from the payload and is therefore not a checksum. It is retained as a declared symbolic invariant.
- Cuneiform strings are project-defined symbolic annotations. They are not a formal decipherment or historical transliteration result.

## Scientific interpretation

- Formal verification establishes implications inside the model, not correspondence between model labels and the physical world.
- Cross-domain E8, quasicrystal, SiS2, HPV16, SEER, and Sumerian relationships require independent domain evidence and, where presented as hypotheses, explicit falsification conditions.
- The repository's bundled historical source documents include claims and terminology that the September 2026 audits identified as inaccurate or unsupported. They remain archived as project inputs and are not the authority for the corrected computational baseline.

## Generated documents

The checked-in LaTeX/PDF publication artifacts predate PR A and may retain pre-baseline terminology or claims. Source/document parity will be addressed in the publication/reproducibility phase. Until then, prefer the current Lean/Python source, `README.md`, and this limitation record when there is a conflict.
