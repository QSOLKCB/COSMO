# COSMO Claim Ledger

**Schema:** `COSMO-CLAIMS-D-1`

This ledger is the Phase D authority for classifying cross-domain statements. The machine-readable source is `claims/claim-ledger.json`; CI validates both files together.

## Evidence classes

- **FORMAL** — kernel-checked consequences of reviewed Lean definitions.
- **COMPUTATIONAL** — deterministic results of reviewed executable code and regression tests.
- **SCIENTIFIC** — externally sourced scholarly/database statements, stated no more strongly than the cited source supports.
- **HYPOTHESIS** — testable proposals that must include an explicit falsification protocol.
- **SYMBOLIC** — project-defined artistic, mythological, mnemonic, or interpretive mappings with no empirical force.

A claim may have external context sources without changing its class. In particular, a symbolic mapping does not become scientific merely because one of its component nouns has scientific literature.

## Scientific source registry

- **SRC-E8-MATHWORLD** — Wolfram MathWorld, *Gosset Polytope*; documents the 240 vertices/roots of the E8 root polytope.
- **SRC-SPIN8-PTEP-2021** — PTEP 2021 article; states the Spin(8) triality (S_3) outer automorphism and permutation of the three 8-dimensional representations.
- **SRC-SIS2-PMID-25590815** — PMID **25590815**, DOI **10.1021/ic501825r**; describes ambient-pressure SiS2 as orthorhombic chains of distorted edge-sharing SiS4 tetrahedra.
- **SRC-HPV16-REFSEQ** — NCBI RefSeq **NC_001526.4**, human papillomavirus type 16 complete genome.
- **SRC-HPV16-E6E7-PMID-17645777** — PMID **17645777**, PMCID **PMC11158331**; review of high-risk HPV E6/E7 carcinogenesis mechanisms.
- **SRC-HPV-P16-PMC8409095** — PMCID **PMC8409095**; review discussing p16 as a surrogate marker and its limitations relative to direct viral transcription evidence.

## Claims

### FORMAL

- **COSMO-D-001** — Six authoritative state transitions return every `CosmoLayer` to itself. Authority: Lean theorem `six_step_periodic`.
- **COSMO-D-002** — Every authoritative layer reaches every other layer within one six-state orbit. Authority: Lean theorem `every_layer_reachable`.

### COMPUTATIONAL

- **COSMO-D-003** — Phase B3 deterministically constructs and validates the 240-root E8 table, rank 8 and norm-2 structure, with reviewed identity binding.
- **COSMO-D-014** — Phase B5 recovers the original `TriadicLattice` through the documented software ECC/ACGT round trip for corruption patterns inside the selected SECDED capability.

### SCIENTIFIC

- **COSMO-D-004** — Spin(8) triality has an (S_3) outer automorphism action permuting the vector and two spinor eight-dimensional representations. This does **not** imply a capsid/HPV mechanism.
- **COSMO-D-005** — Ambient-pressure SiS2 is orthorhombic and contains chains of distorted edge-sharing SiS4 tetrahedra. This does **not** establish a biological “life-code” substrate.
- **COSMO-D-006** — HPV16 reference genome provenance in this ledger: NCBI RefSeq **NC_001526.4**.
- **COSMO-D-007** — High-risk HPV E6/E7 have established carcinogenesis roles involving p53 and pRb/E2F control. These facts do **not** define COSMO's transitions.
- **COSMO-D-008** — p16 immunohistochemistry is a context-dependent surrogate marker; p16 positivity is not equivalent to direct evidence of active HPV16 E6/E7 transcription.

### HYPOTHESIS

- **COSMO-D-012** — A future quantitatively specified triality-to-HPV/capsid mapping may be tested for predictive value. It currently has **no positive result**. Falsification requires preregistered mapping, observable, data split, metric, controls, and threshold.

### SYMBOLIC

- **COSMO-D-009** — Cuneiform annotations are project-defined symbols, not archaeological decipherment or translation.
- **COSMO-D-010** — “Cosmic symmetry”, “life-code”, “infected reality”, and Ouroboros self-causation are symbolic/interpretive vocabulary.
- **COSMO-D-011** — The current triality ↔ HPV capsid branching association is symbolic, not an established biological mechanism.
- **COSMO-D-013** — `SiS2Substrate` is a project state label; the SiS2 literature does not establish a biological substrate role.

## Governance

1. New cross-domain public-facing claims must receive a stable `COSMO-D-###` ID before being promoted as Phase D authoritative language.
2. **SCIENTIFIC** claims require at least one external source entry.
3. **HYPOTHESIS** claims require an explicit falsification protocol and may not be phrased as established mechanisms.
4. **SYMBOLIC** claims must state their non-empirical boundary.
5. **FORMAL** and **COMPUTATIONAL** claims must point to reviewed repository evidence.
6. A source about one domain does not validate a cross-domain bridge.
7. Historical PDFs and archived source material remain provenance inputs, not authorities over the ledger.
