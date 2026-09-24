# Known Limitations

This file is part of COSMO's trust boundary. A green build means the checked code satisfies the statements encoded in that build. It does **not** upgrade symbolic labels into empirical evidence.

## Formal model

- Phase C makes `CosmoLayer` the authoritative six-state discrete cycle in Lean and mirrors it as `CosmoState` in Python. The proofs establish only finite-state transition, periodicity, and reachability properties; constructor names do not formalize the corresponding scientific objects.
- `psiEquation` is no longer the legacy four-function composition. It is retained as a compatibility-facing name for exactly one application of the authoritative Lean `cosmoStep`.
- Phase B3 provides an exact **Python computational** E8 root/Weyl model, but the `E8Symmetry` state is not yet linked to that model by a Lean theorem; SiS2 and HPV16 labels likewise remain project vocabulary rather than formalized domain objects.
- The category-theory paper remains a design sketch. Phase C supplies the state-machine authority it must consume, but retract, natural-transformation, free-category, endofunctor, and categorical six-step equivalence claims remain Phase E work.
- `phiFloorQuantized` encodes the Lucas parity rule used by the project. PR A proves the concrete integer results needed by the baseline, but does not yet formalize the real-analysis theorem relating the definition to `Real.floor` for every exponent.
- `diagApplyFloat` is executable only. No theorem assumes unrestricted floating-point arithmetic behaves as an exact ring.

## Exact E8 computational boundary

- Phase B3 represents E8 roots in doubled integer coordinates and validates the standard 240-root system, exact rank 8, norm-2 structure, lattice membership, and Weyl-reflection invariants computationally in Python.
- The canonical root table is bound to an uncached reference generator and a reviewed SHA-256 identity. That is deterministic computational evidence, not a substitute for a future Lean formalization of the E8 construction.
- Weyl reflections operate only on vectors satisfying the exact E8-lattice predicate used by the B3 model. The module does not claim that arbitrary COSMO symbolic state is an E8 lattice vector.
- The existence of an exact E8 mathematical core does not establish any physical, biological, archaeological, or cosmological correspondence for other COSMO labels.

## Triadic lattice experimental boundary

- Phase B4 is a deterministic finite-state computation over an 8×8×8 ternary lattice. It is not a model or demonstration of physical quantum hardware, qutrit devices, or error correction on quantum systems.
- Seeded initialization uses a stateless deterministic integer mixer for replay, not a physical or cryptographic randomness claim.
- The optional ternary-digit mask is a discrete base-3 residue texture. No fractal dimension, 3-adic physical mechanism, or empirical scaling law is claimed.
- The parallel path uses bounded CPython worker threads and records observed thread use separately from requested/effective configuration. No speedup or true multicore-execution claim is made without separate benchmark evidence.
- Normalized entropy is a state-population diagnostic only. Phase B4 introduces no spectral/physical interpretation because no justified spectral observable has been selected.
- The repetition-code recovery model corrects one altered trit per three-symbol codeword. More severe corruption is outside its documented correction capability.
- Loop closure and cycle/convergence metrics describe the chosen deterministic transition rule only; they are not evidence of physical stability or recurrence.

## Data and symbolic mappings

- The represented Dragon Seed payload contains 8 bytes, hence 64 bits. `101` is currently a project mnemonic, not represented payload length.
- The value 1621 is not derived from the payload and is therefore not a checksum. It is retained as a declared symbolic invariant.
- Cuneiform strings are project-defined symbolic annotations. They are not a formal decipherment or historical transliteration result.

## Deterministic codec boundary

- Phase B5 closes the computational `cube -> bytes -> ECC -> ACGT -> corruption -> ECC correction -> bytes -> cube` contract for the Phase B4 `TriadicLattice`. The cube serialization is one byte per ternary cell and is a software storage representation, not a physical Rubik's Cube encoding claim.
- The extended Hamming SECDED codec uses independent `(8, 4, 4)` codewords. It corrects one flipped bit per codeword and detects every two-bit error per codeword; it makes no correction/detection guarantee for higher-weight corruption.
- SHA-256 is an integrity/authentication layer, not ECC. It can reject a higher-weight corruption that SECDED miscorrects into the wrong payload, but it does not make that corruption correctable.
- The strict `A/C/G/T` mapping and synthetic FASTA output are deterministic storage alphabets/containers only. They are not biological models or claims about DNA synthesis, sequencing, mutation, storage density, or laboratory error rates.
- B5's corruption helpers model exact encoded-bit flips while preserving valid ACGT text. They do not claim that physical DNA base substitutions have the same bit-error distribution.
- MIDI/audio visualization remains outside the deterministic storage core.
- Experiment manifests and storage receipts bind the exact bytes supplied or recovered. They do not independently authenticate external provenance or scientific validity.

## Phase D claim/provenance boundary

- `claims/claim-ledger.json` is the Phase D authority for evidence class and provenance; `CLAIM-LEDGER.md` is its reviewed human index. A green ledger validator means the repository satisfies the encoded classification rules, not that every externally sourced claim has been independently replicated by COSMO.
- **SCIENTIFIC** entries report what cited external sources support. They do not transfer scientific authority to a cross-domain bridge merely because the component domains are individually real.
- Spin(8) triality is established mathematical context, but the current triality↔HPV capsid mapping is classified **SYMBOLIC**. No biological mechanism is claimed.
- Ambient-pressure SiS2 structure is externally sourced scientific context; `SiS2Substrate` and “life-code” readings remain **SYMBOLIC** project vocabulary.
- HPV16 RefSeq `NC_001526.4`, E6/E7 biology, and scoped p16-marker usage are external biomedical context. They do not validate `HPV16Layer` as a biomedical state transition.
- Cuneiform annotations and cosmological/Ouroboros readings are **SYMBOLIC**, not archaeological decipherment or empirical cosmology.
- A **HYPOTHESIS** entry must retain explicit falsification criteria. No hypothesis may be promoted to SCIENTIFIC or COMPUTATIONAL merely because a suggestive analogy or numerical match is found.
- The repository's bundled historical source documents include claims and terminology that the September 2026 audits identified as inaccurate or unsupported. They remain archived as provenance inputs and are not the authority for the corrected ledger.

## Generated documents

The checked-in LaTeX/PDF publication artifacts predate PR A and may retain pre-baseline terminology or claims. Source/document parity will be addressed in the publication/reproducibility phase. Until then, prefer the current Lean/Python source, `README.md`, and this limitation record when there is a conflict.
