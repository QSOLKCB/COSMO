# COSMO Roadmap

This roadmap defines the post-baseline development path for COSMO and adopts the immutable **QSOL OPT v1.0.0** release as the normative optimization catalog for future implementation work.

OPT release: https://github.com/QSOLKCB/OPT/releases/tag/v1.0.0

The governing rule is simple:

> **Correctness outranks speed.**

An optimization is acceptable only when it preserves the relevant formal, deterministic, numerical, scientific, or evidentiary contract. Cache hits, benchmark numbers, worker counts, or faster wall times are never substitutes for proof or validation.

## Current baseline: PR A

PR A establishes COSMO's reproducible formal-integrity baseline before higher-level reconstruction begins.

Target guarantees include:

- pinned Lean and Mathlib identities;
- warnings-as-errors for project Lean;
- lexical rejection of admitted proofs and disallowed trust shortcuts;
- isolated project compilation under an unprivileged identity;
- immutable pre-build dependency-manifest trust input;
- post-build source and artifact integrity checks;
- complete project-module discovery, including tracked local Lake packages;
- symlink and module-shadow rejection;
- direct kernel replay with `leanchecker`;
- direct, non-Lake, non-initializing semantic auditing;
- generated-axiom and unchecked-theorem negative fixtures;
- deterministic Python regression, strict typing, and bytecode checks.

PR A should remain focused on integrity. Performance work that is not required to close correctness or trust findings belongs in later PRs.

---

## Phase B1 — OPT-LEAN-001 verified dependency reuse

**Primary optimization record:** `OPT-LEAN-001 — Trust-Preserving Lean Dependency Reuse`

Goal: reduce routine Lean CI wall time without weakening the protected audit boundary.

### Planned work

1. Split dependency reuse into two independently identified cache classes:
   - verified dependency **source state**;
   - verified dependency **compiled artifacts**.
2. Bind source-cache identity to at least:
   - cache schema;
   - runner OS and architecture;
   - Lean distribution identity;
   - `lean-toolchain` identity;
   - dependency declaration identity;
   - immutable `lake-manifest.json` identity.
3. Purge generated dependency `.lake` state before source verification.
4. Verify dependency source revisions and tracked bytes/modes against the pinned source graph.
5. Authenticate compiled dependency artifacts against a reviewed canonical per-file SHA-256 receipt and expected artifact count.
6. Never let a cache authenticate itself. The authoritative receipt anchor must live in reviewed repository source.
7. Delete COSMO's own `.lake/build` before every routine project rebuild.
8. Rebuild the complete current COSMO source against verified dependencies.
9. Run the same protected kernel replay and semantic audit after the rebuild.
10. Maintain a separate cold-trust reconstruction lane for release-grade claims.

### Validation contract

- cached dependency source identity must be verified before use;
- cached compiled artifacts must match the reviewed canonical receipt;
- COSMO project outputs must always be rebuilt from the current reviewed source;
- every current project module must still pass kernel replay and semantic auditing;
- any identity, receipt, source, artifact-count, or trust mismatch fails closed.

### Measurement rule

Record routine and cold-trust timings separately. Do not call a verified-cache run a cold reconstruction, and do not transfer GEO-REASON timing numbers as COSMO targets without re-measurement.

---

## Phase B2 — canonical deterministic computational core

**Primary optimization records:** `OPT-PY-001`, `OPT-INV-001`

Goal: create a single deterministic source of truth for COSMO's reusable arithmetic, encoding, lattice, and geometry primitives.

### Planned modules

- canonical constants and data definitions;
- explicit separation of golden ratio and quarter-turn notation;
- deterministic Lucas / phi-floor utilities;
- payload and checksum/invariant semantics;
- corrected Hamming/SECDED encoding and recovery;
- strict DNA alphabet conversion with invalid-input rejection;
- deterministic integrity digest support;
- experiment manifests binding seed, parameters, inputs, and output hashes.

### OPT-PY-001 application

- use the smallest fixtures that still exercise each invariant;
- eliminate repeated deterministic lookup construction;
- cache only pure immutable intermediates;
- keep caches bounded and explicitly keyed;
- reduce regression sweep cardinality only when assertion coverage is preserved;
- use deterministic early exits only where result equivalence is established.

### OPT-INV-001 application

Reuse computation only after the relevant equivalence or invariant has been established. Preserve a reference path for validation whenever optimized reuse could hide divergence.

---

## Phase B3 — exact E8 and Weyl core

**Primary optimization record:** `OPT-INV-001`

Goal: replace symbolic references to E8 with an explicit mathematical representation suitable for Python/Lean parity.

### Planned work

- generate the full 240-root E8 root system exactly;
- verify rank 8 and norm-2 root structure;
- represent integer and half-integer root families explicitly;
- implement Weyl reflections
  `s_alpha(x) = x - <x, alpha> alpha`;
- prove or test reflection involution, norm preservation, hyperplane behavior, and lattice preservation;
- retain deterministic canonical ordering of roots and reflections;
- reuse precomputed root tables only when their identity is bound to the canonical generator and validation path.

---

## Phase B4 — triadic 8x8x8 lattice and recovery experiments

**Primary optimization records:** `OPT-PAR-001`, `OPT-INV-001`

Goal: build the deterministic triadic lattice as a computational experiment without overstating it as physical quantum hardware.

### Planned work

- 8x8x8 deterministic lattice;
- ternary states `{0, 1, 2}` or an explicitly documented equivalent representation;
- seeded initialization and replay;
- deterministic local updates;
- optional 3-adic / fractal masks;
- explicit syndrome and recovery model;
- generic codebook/recovery interface;
- loop-closure diagnostics such as `D_n(x) = ||T^n(x) - x||^2`;
- stability diagnostics such as convergence, entropy, recovery time, and spectral summaries where justified.

### OPT-PAR-001 application

- retain a scalar/reference implementation;
- parallelize only independent units of work;
- bound worker count against runner capacity;
- restore canonical result ordering before comparison or hashing;
- verify scalar/parallel equivalence across multiple worker counts;
- record requested and observed parallelism separately;
- constrain nested parallel runtimes where necessary to prevent oversubscription.

---

## Phase B5 — storage / DNA / ECC round-trip contract

**Primary optimization records:** `OPT-PY-001`, `OPT-INV-001`

Goal: turn the experimental Rubik/DNA storage idea into a strict deterministic codec.

### Core invariant

`cube -> bytes -> ECC -> ACGT -> corruption -> ECC correction -> bytes -> cube`

The round trip must recover the original state for every corruption pattern covered by the selected code's documented correction capability.

### Planned work

- replace the legacy broken Hamming decoder mapping;
- prefer an extended Hamming SECDED contract where appropriate;
- reject invalid DNA symbols rather than silently coercing them;
- distinguish checksum/integrity roles from ECC roles;
- retain synthetic FASTA labeling;
- keep MIDI/audio visualization outside the deterministic storage core;
- add exhaustive small-domain corruption tests where computationally practical.

---

## Phase C — authoritative six-state COSMO dynamics

Goal: replace the legacy finite-state composition with one explicit six-state transition system.

Planned state cycle:

1. `E8Symmetry`
2. `PhiScaled`
3. `SiS2Substrate`
4. `TrialityBranch`
5. `HPV16Layer`
6. `OuroborosLoop`
7. return to `E8Symmetry`

### Planned work

- define one authoritative one-step transition function;
- prove six applications return to the starting state where intended;
- prove orbit/reachability properties;
- expose typed transition witnesses where useful;
- derive every later categorical presentation from this canonical transition system rather than maintaining parallel semantics.

Optimization is secondary here. The transition semantics must stabilize first.

---

## Phase D — claim ledger and scientific provenance

Goal: make every cross-domain statement auditable by evidence class.

### Planned work

- maintain FORMAL / COMPUTATIONAL / SCIENTIFIC / HYPOTHESIS / SYMBOLIC separation;
- add a claim ledger with identifiers and provenance;
- correct E8, Spin(8), SiS2, HPV/p16, archaeological, and cosmological language to match source strength;
- distinguish speculative mappings from established mechanisms;
- record accession/version identifiers where applicable;
- retain symbolic and artistic material when clearly labelled as such.

No optimization may collapse these epistemic distinctions.

---

## Phase E — category-theory formalization

Goal: derive the categorical view from the stabilized six-state dynamics.

### Planned work

- use Mathlib CategoryTheory where appropriate;
- construct the free category generated by the six-state graph;
- distinguish a nontrivial loop in the free category from a quotient/presentation that imposes loop identity;
- define rotation/endofunctor structure;
- prove the appropriate six-step equivalence or isomorphism only under the explicit presentation assumptions that justify it.

---

## Phase F — publication and provenance hardening

Goal: freeze a publication-grade reproducible COSMO record.

### Planned work

- regenerate PDFs from corrected sources;
- bind releases to immutable tags;
- capture Lean/Python environment metadata;
- publish machine-readable validation receipts;
- distinguish routine verified-cache CI from cold-trust release reconstruction;
- archive benchmark context with runner, OS, CPU/toolchain data when performance evidence is claimed;
- create DOI-ready metadata and provenance records where appropriate.

---

## Optional experimental layer — OPT-DSP-001

**Primary optimization record:** `OPT-DSP-001 — Control-Rate, Sparse and Vectorized DSP`

Audio-reactive and sonification features should remain optional consumers of deterministic COSMO state.

Applicable techniques include:

- separate control-rate updates from audio-rate synthesis;
- sparse rather than dense coupling where the model permits it;
- compute shared intermediates once;
- vectorize block synthesis;
- keep visualization/MIDI/audio timing outside the proof and storage semantics;
- never promote an implementation-level DSP optimization into a scientific-performance claim without measurement.

---

## Optimization governance

Every optimization PR should state:

1. the OPT record(s) being applied;
2. the invariant or contract that must remain unchanged;
3. the reference path used for comparison;
4. the exact benchmark environment if performance is measured;
5. before/after timing scope and repetition count;
6. rollback triggers;
7. any new cache, parallelism, or trust assumption introduced.

### Global rollback rule

Rollback or disable an optimization if it causes any unexpected change in:

- theorem meaning or trust dependencies;
- deterministic outputs;
- public API semantics;
- numerical invariants;
- scientific/evidentiary classification;
- scalar/reference equivalence;
- artifact provenance;
- test isolation;
- bounded resource behavior.

A faster wrong result is not an optimization.

---

## Normative optimization source

Future COSMO optimization work should cite and follow the immutable OPT v1.0.0 catalog unless a later explicitly adopted immutable OPT release supersedes it:

https://github.com/QSOLKCB/OPT/releases/tag/v1.0.0

Relevant initial records:

- `OPT-LEAN-001` — Trust-Preserving Lean Dependency Reuse
- `OPT-PY-001` — Deterministic Test Execution
- `OPT-INV-001` — Invariant-Driven Computation Reuse
- `OPT-PAR-001` — Bounded Deterministic Parallel Execution
- `OPT-DSP-001` — Control-Rate, Sparse and Vectorized DSP
