# Known Limitations

This file is part of COSMO's trust boundary. A green build means the checked code satisfies the statements encoded in that build. It does **not** upgrade symbolic labels into empirical evidence.

## Formal model

- `CosmoLayer` is currently a six-constructor finite type. Phase B3 now provides an exact **Python computational** E8 root/Weyl model, but the `E8Symmetry` constructor is not yet linked to that model by a Lean theorem; SiS2, HPV16, and archaeological labels likewise remain names rather than formalized domain objects.
- `psiEquation` is a legacy four-function composition. It does not match the six-generator category-theory cycle one-for-one. That reconstruction is intentionally deferred to PR C.
- The category-theory paper is a design sketch. Its retract, natural-transformation, endofunctor, and periodicity claims are not yet Lean theorems.
- `phiFloorQuantized` encodes the Lucas parity rule used by the project. PR A proves the concrete integer results needed by the baseline, but does not yet formalize the real-analysis theorem relating the definition to `Real.floor` for every exponent.
- `diagApplyFloat` is executable only. No theorem assumes unrestricted floating-point arithmetic behaves as an exact ring.

## Exact E8 computational boundary

- Phase B3 represents E8 roots in doubled integer coordinates and validates the standard 240-root system, exact rank 8, norm-2 structure, lattice membership, and Weyl-reflection invariants computationally in Python.
- The canonical root table is bound to an uncached reference generator and a reviewed SHA-256 identity. That is deterministic computational evidence, not a substitute for a future Lean formalization of the E8 construction.
- Weyl reflections operate only on vectors satisfying the exact E8-lattice predicate used by the B3 model. The module does not claim that arbitrary COSMO symbolic state is an E8 lattice vector.
- The existence of an exact E8 mathematical core does not establish any physical, biological, archaeological, or cosmological correspondence for other COSMO labels.

## Data and symbolic mappings

- The represented Dragon Seed payload contains 8 bytes, hence 64 bits. `101` is currently a project mnemonic, not represented payload length.
- The value 1621 is not derived from the payload and is therefore not a checksum. It is retained as a declared symbolic invariant.
- Cuneiform strings are project-defined symbolic annotations. They are not a formal decipherment or historical transliteration result.

## Deterministic codec boundary

- Phase B2's extended Hamming SECDED codec uses independent `(8, 4, 4)` codewords. It corrects one flipped bit per codeword and detects every two-bit error per codeword; it makes no correction/detection guarantee for higher-weight corruption.
- The strict `A/C/G/T` mapping is a deterministic storage alphabet, not a biological model or claim about DNA synthesis, sequencing, mutation, or error rates.
- Phase B2 provides reusable ECC and DNA primitives only. The full `cube -> bytes -> ECC -> ACGT -> corruption -> ECC correction -> bytes -> cube` storage contract remains Phase B5 work.
- Experiment manifests bind the exact bytes supplied to the manifest constructor. They do not independently authenticate the external provenance or scientific validity of those bytes.

## Scientific interpretation

- Formal verification establishes implications inside the model, not correspondence between model labels and the physical world.
- Cross-domain E8, quasicrystal, SiS2, HPV16, SEER, and Sumerian relationships require independent domain evidence and, where presented as hypotheses, explicit falsification conditions.
- The repository's bundled historical source documents include claims and terminology that the September 2026 audits identified as inaccurate or unsupported. They remain archived as project inputs and are not the authority for the corrected computational baseline.

## Generated documents

The checked-in LaTeX/PDF publication artifacts predate PR A and may retain pre-baseline terminology or claims. Source/document parity will be addressed in the publication/reproducibility phase. Until then, prefer the current Lean/Python source, `README.md`, and this limitation record when there is a conflict.
