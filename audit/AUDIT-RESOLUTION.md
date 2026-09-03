# September 2026 Audit Resolution

This record converts the two supplied COSMO audit reports into an implementation decision log. Audit findings are treated as review inputs, not axioms. Where the reports disagree, the repository records the chosen resolution explicitly.

## Status vocabulary

- **ACCEPTED**: finding is confirmed and addressed in PR A.
- **ACCEPTED / DEFERRED**: finding is confirmed, but the structural fix belongs in a later planned PR.
- **MODIFIED**: the underlying concern is valid, but the proposed correction in the audit is not fully correct.
- **REJECTED / ALREADY RESOLVED**: the finding does not apply to the current `main` branch.

## PR A dispositions

| Finding | Resolution | PR A action |
|---|---|---|
| No reproducible Lake project/toolchain pin | **ACCEPTED** | Add `lean-toolchain`, `lakefile.lean`, exact Mathlib revision and CI. |
| Project contains a Lean `sorry` | **ACCEPTED** | Remove the universal Float theorem; CI rejects project `sorry` and `sorryAx`. |
| No axiom-dependency inspection | **ACCEPTED** | Add `audit/AxiomAudit.lean` and CI output. |
| `phi^101 mod 256 = 173` | **ACCEPTED** | Correct computational baseline to 75. |
| `floor(phi^101) mod 256 = 74` | **MODIFIED** | For odd positive 101, the project quantization equals `L_101`, hence residue 75. |
| Existing `phi_mod` represents floor(phi^n) for all n | **ACCEPTED** | Replace with parity-aware `phiFloorQuantized` / `phiFloorMod`. |
| Dragon payload is 101 bits | **ACCEPTED** | Prove/list 8 bytes and 64 represented bits; retain 101 only as a legacy mnemonic. |
| 1621 is a checksum of the bytes | **ACCEPTED** | Rename to `declaredSymbolicInvariant`; prove byte sum is 1512 and distinct. |
| Universal Float DIAG theorem should be proved | **MODIFIED** | Remove it as a theorem target. Keep Float execution and prove exact integer identities instead. |
| Current Psi implementation matches the six-layer categorical cycle | **ACCEPTED / DEFERRED** | Mark `psiEquation` legacy; reconstruct one authoritative six-state system in PR C. |
| Category retract/natural-transformation/endofunctor claims are fully formal | **ACCEPTED / DEFERRED** | Document as unformalized design targets; implement after the state-machine reconstruction. |
| README is inadequate | **ACCEPTED** | Replace with build instructions, trust boundary, claim classes and verified baseline. |
| No CI/test harness | **ACCEPTED** | Add Lean and Python CI, unit tests, static typing and compile checks. |
| MPL-2.0 / MIT license conflict | **REJECTED / ALREADY RESOLVED** | Current `main` already uses MIT and matches the Python header. |

## Deliberately not implemented in PR A

The following audit recommendations are valid work but would make the baseline PR too broad:

1. full six-state typed transition reconstruction;
2. formal Mathlib category construction;
3. formal E8 root-system or Spin(8) triality development;
4. canonical claim/source dataset generation across Lean, Python and LaTeX;
5. external scientific bibliography and claim-by-claim citation rewrite;
6. falsification protocols for cross-domain hypotheses;
7. regeneration of all PDFs and graphical assets.

Those remain downstream work. PR A exists to make subsequent changes land on a trustworthy, reproducible floor rather than continuing to build on ambiguous arithmetic and proof boundaries.
