# COSMO Claim Ledger

> Generated canonically from `claims/claim-ledger.json`. Do not hand-edit this file independently.

**Schema:** `COSMO-CLAIMS-D-1`

## Evidence classes

- **FORMAL**
- **COMPUTATIONAL**
- **SCIENTIFIC**
- **HYPOTHESIS**
- **SYMBOLIC**

## Scientific source registry

### SRC-E8-MATHWORLD

- **Kind:** `scholarly_reference`
- **Domain:** `mathematics`
- **Title:** Gosset Polytope — E8 root polytope
- **Identifiers:** none
- **Identifier URLs:** none
- **URL:** https://mathworld.wolfram.com/GossetPolytope.html

### SRC-SPIN8-PTEP-2021

- **Kind:** `scholarly_article`
- **Domain:** `mathematics`
- **Title:** Vertex operator superalgebra/sigma model correspondences: The four-torus case
- **Identifiers:** year=2021
- **Identifier URLs:** none
- **URL:** https://academic.oup.com/ptep/article/2021/8/08B102/6353037

### SRC-SIS2-PMID-25590815

- **Kind:** `peer_reviewed_article`
- **Domain:** `materials_science`
- **Title:** Two high-pressure phases of SiS2 as missing links between the extremes of only edge-sharing and only corner-sharing tetrahedra
- **Identifiers:** DOI=10.1021/ic501825r, PMID=25590815
- **Identifier URLs:** DOI=https://doi.org/10.1021/ic501825r; PMID=https://pubmed.ncbi.nlm.nih.gov/25590815/
- **URL:** https://pubmed.ncbi.nlm.nih.gov/25590815/

### SRC-HPV16-REFSEQ

- **Kind:** `official_database`
- **Domain:** `biomedicine`
- **Title:** Human papillomavirus type 16, complete genome
- **Identifiers:** RefSeq=NC_001526.4
- **Identifier URLs:** RefSeq=https://www.ncbi.nlm.nih.gov/nuccore/NC_001526.4
- **URL:** https://www.ncbi.nlm.nih.gov/nuccore/NC_001526.4

### SRC-HPV16-E6E7-PMID-17645777

- **Kind:** `peer_reviewed_review`
- **Domain:** `biomedicine`
- **Title:** Basic mechanisms of high-risk human papillomavirus-induced carcinogenesis: Roles of E6 and E7 proteins
- **Identifiers:** PMCID=PMC11158331, PMID=17645777
- **Identifier URLs:** PMCID=https://pmc.ncbi.nlm.nih.gov/articles/PMC11158331/; PMID=https://pubmed.ncbi.nlm.nih.gov/17645777/
- **URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11158331/

### SRC-HPV-P16-PMC8409095

- **Kind:** `peer_reviewed_review`
- **Domain:** `biomedicine`
- **Title:** Biology of HPV Mediated Carcinogenesis and Tumor Progression
- **Identifiers:** PMCID=PMC8409095
- **Identifier URLs:** PMCID=https://pmc.ncbi.nlm.nih.gov/articles/PMC8409095/
- **URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC8409095/

## Claims

### COSMO-D-001 — FORMAL

- **Status:** `SUPPORTED`
- **Statement:** For every CosmoLayer, six applications of the authoritative Lean transition return the layer to itself.
- **Sources:** none
- **Boundary:** This is a theorem about the finite state machine only; it is not a physical periodicity claim.
- **Repository provenance:**
  - `cosmovirus.lean` — `theorem six_step_periodic (layer : CosmoLayer) : psiIterate 6 layer = layer := by` (`kernel_checked_theorem`)

### COSMO-D-002 — FORMAL

- **Status:** `SUPPORTED`
- **Statement:** Every authoritative COSMO layer reaches every other layer within one complete six-state orbit.
- **Sources:** none
- **Boundary:** Reachability is defined inside the project state machine.
- **Repository provenance:**
  - `cosmovirus.lean` — `theorem every_layer_reachable (source target : CosmoLayer) : ReachesWithinCycle source target := by` (`kernel_checked_theorem`)

### COSMO-D-003 — COMPUTATIONAL

- **Status:** `SUPPORTED`
- **Statement:** The Phase B3 Python reference generator deterministically constructs 240 unique E8 roots with rank 8 and squared norm 2, and the canonical table is bound to a reviewed SHA-256.
- **Sources:** SRC-E8-MATHWORLD
- **Boundary:** This is deterministic computational evidence; the local Lean core does not yet formalize the E8 root construction.
- **Repository provenance:**
  - `cosmo_core/e8.py` — `def validate_e8_root_system` (`implementation`)
  - `tests/test_phase_b3.py` — `test_root_system_report_has_rank_eight_and_norm_two` (`regression`)

### COSMO-D-004 — SCIENTIFIC

- **Status:** `SUPPORTED`
- **Statement:** Spin(8) has triality symmetry with an S3 outer automorphism action that permutes its vector and two spinor eight-dimensional representations.
- **Domain:** `mathematics`
- **Sources:** SRC-SPIN8-PTEP-2021
- **Boundary:** This mathematical fact does not establish a mechanism connecting Spin(8) triality to HPV, capsids, SiS2, or cosmology.
- **Repository provenance:**
  - `cosmovirus.tex` — `COSMO-D-004` (`documented_context`)

### COSMO-D-005 — SCIENTIFIC

- **Status:** `SUPPORTED`
- **Statement:** The ambient-pressure phase of SiS2 is orthorhombic and contains chains of distorted edge-sharing SiS4 tetrahedra.
- **Domain:** `materials_science`
- **Sources:** SRC-SIS2-PMID-25590815
- **Boundary:** This crystallographic fact does not support COSMO's symbolic substrate or life-code interpretation.
- **Repository provenance:**
  - `cosmovirus.tex` — `COSMO-D-005` (`documented_context`)

### COSMO-D-006 — SCIENTIFIC

- **Status:** `SUPPORTED`
- **Statement:** The NCBI reference sequence used for human papillomavirus type 16 in this ledger is RefSeq NC_001526.4.
- **Domain:** `biomedicine`
- **Sources:** SRC-HPV16-REFSEQ
- **Boundary:** The accession identifies a reference genome; it does not validate COSMO's state-machine use of the HPV16Layer label.
- **Repository provenance:**
  - `CLAIM-LEDGER.md` — `NC_001526.4` (`provenance_record`)

### COSMO-D-007 — SCIENTIFIC

- **Status:** `SUPPORTED`
- **Statement:** High-risk HPV E6 and E7 proteins are established carcinogenesis factors; E6 promotes p53 degradation and E7 disrupts pRb/E2F control.
- **Domain:** `biomedicine`
- **Sources:** SRC-HPV16-E6E7-PMID-17645777
- **Boundary:** This biomedical mechanism is external scientific context and is not a mechanism for COSMO transitions.
- **Repository provenance:**
  - `cosmovirus.tex` — `COSMO-D-007` (`documented_context`)

### COSMO-D-008 — SCIENTIFIC

- **Status:** `SUPPORTED_WITH_SCOPE`
- **Statement:** p16 immunohistochemistry is used as a surrogate marker for HPV-associated disease in some clinical contexts, but p16 positivity is not identical to direct evidence of active E6/E7 transcription.
- **Domain:** `biomedicine`
- **Sources:** SRC-HPV-P16-PMC8409095
- **Boundary:** COSMO must not equate a generic p16-positive label with HPV16 infection or active viral transcription.
- **Repository provenance:**
  - `cosmovirus.tex` — `COSMO-D-008` (`documented_context`)

### COSMO-D-009 — SYMBOLIC

- **Status:** `PROJECT_DEFINED`
- **Statement:** The byte-to-cuneiform labels in COSMO are project-defined symbolic annotations.
- **Sources:** none
- **Boundary:** They are not a decipherment, transliteration, translation, archaeological attribution, or historical sentence.
- **Empirical status:** `NON_EMPIRICAL`
- **Repository provenance:**
  - `cosmovirus.lean` — `def cuneiformAnnotation` (`project_definition`)
  - `KNOWN_LIMITATIONS.md` — `Cuneiform strings are project-defined symbolic annotations` (`scope_boundary`)

### COSMO-D-010 — SYMBOLIC

- **Status:** `PROJECT_DEFINED`
- **Statement:** COSMO's language of undivided cosmic symmetry, life-code substrate, infected reality, and Ouroboros self-causation is symbolic/interpretive vocabulary.
- **Sources:** none
- **Boundary:** These phrases are not empirical cosmology, materials science, virology, or causal-mechanism claims.
- **Empirical status:** `NON_EMPIRICAL`
- **Repository provenance:**
  - `cosmovirus.tex` — `COSMO-D-010` (`symbolic_section`)

### COSMO-D-011 — SYMBOLIC

- **Status:** `PROJECT_DEFINED`
- **Statement:** The association of Spin(8) triality with HPV capsid branching or trimerization is a symbolic cross-domain association in the current repository.
- **Sources:** none
- **Boundary:** The repository does not claim an established biological mechanism connecting Spin(8) triality to HPV capsid assembly.
- **Empirical status:** `NON_EMPIRICAL`
- **Repository provenance:**
  - `cosmovirus.tex` — `capsid` (`historical_symbolic_mapping`)

### COSMO-D-012 — HYPOTHESIS

- **Status:** `PROPOSED`
- **Statement:** A future quantitatively specified mapping from triality-derived features to an HPV/capsid observable could be tested for predictive value against matched controls.
- **Sources:** none
- **Boundary:** No such predictive result is currently claimed.
- **Falsification protocol:** Pre-register the triality-derived mapping, target observable, dataset split, evaluation metric, matched baselines, and decision threshold before evaluating held-out data.
- **Rejection condition:** Reject the hypothesis if held-out performance fails the predeclared threshold or is not distinguishable from the matched control baselines.
- **Controls:** Matched baseline models fixed before held-out evaluation; Held-out data excluded from mapping and threshold selection
- **Repository provenance:**
  - `CLAIM-LEDGER.md` — `COSMO-D-012` (`hypothesis_definition`)

### COSMO-D-013 — SYMBOLIC

- **Status:** `PROJECT_DEFINED`
- **Statement:** The use of SiS2Substrate as a COSMO state name is symbolic project vocabulary rather than evidence that silicon disulfide is a biological life-code substrate.
- **Sources:** SRC-SIS2-PMID-25590815
- **Boundary:** The scientific source does not establish a biological substrate role; it supports SiS2 crystal-structure facts only.
- **Empirical status:** `NON_EMPIRICAL`
- **Repository provenance:**
  - `cosmovirus.lean` — `SiS2Substrate` (`state_label`)

### COSMO-D-014 — COMPUTATIONAL

- **Status:** `SUPPORTED`
- **Statement:** Within the documented SECDED capability, the Phase B5 software storage pipeline deterministically recovers the original TriadicLattice through bytes, ECC, ACGT, corruption, correction, bytes, and cube reconstruction.
- **Sources:** none
- **Boundary:** This is a software codec result, not a laboratory DNA-storage or physical Rubik's Cube claim.
- **Repository provenance:**
  - `cosmo_core/storage.py` — `def recover_cube_storage` (`implementation`)
  - `tests/test_phase_b5.py` — `test_full_cube_recovers_one_bit_error_in_every_codeword` (`regression`)

## Governance

1. New cross-domain public-facing claims require a stable `COSMO-D-###` ID.
2. **SCIENTIFIC** claims require external source records from the same controlled scientific domain.
3. **HYPOTHESIS** claims must remain `PROPOSED` and include structured falsification criteria.
4. **SYMBOLIC** claims require `empirical_status = NON_EMPIRICAL`.
5. **FORMAL** and **COMPUTATIONAL** claims require reviewed, class-appropriate repository provenance.
6. Multi-accession source records must independently bind every URL-addressable identifier.
7. Positive public cross-domain causal/mechanistic assertions must carry a ledger claim ID.
8. This Markdown file must exactly match the canonical JSON rendering.
