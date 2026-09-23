/-
  cosmovirus.lean
  ===============

  Machine-checked discrete core for COSMO.

  Trust boundary:
  * declarations in this file establish only the mathematics/computation stated;
  * symbolic labels are project vocabulary, not empirical claims;
  * physical, biomedical, archaeological, and cosmological interpretations are
    outside Lean's proof boundary.
-/

import Lean.Elab.Tactic.Omega
import Mathlib.Tactic.Ring

namespace Cosmovirus

/-! ## 1. Golden-ratio quantization via Lucas numbers -/

/-- Floating-point approximation retained only for executable display. -/
def phiApprox : Float := 1.6180339887498948482

/-- Repeated floating-point multiplication by the project phi approximation. -/
def phiPowApprox : Nat → Float
  | 0 => 1.0
  | n + 1 => phiApprox * phiPowApprox n

/-- The n-th Lucas number, with L₀ = 2 and L₁ = 1. -/
def lucas (n : Nat) : Nat :=
  let rec go : Nat → Nat → Nat → Nat
    | 0, a, _ => a
    | k + 1, a, b => go k b (a + b)
  go n 2 1

/--
Exact integer quantization used by COSMO for non-negative exponents.

For the golden ratio φ:
* floor(φ^0) = 1;
* for odd n > 0, floor(φ^n) = L_n;
* for even n > 0, floor(φ^n) = L_n - 1.

This definition encodes that parity rule.  A later formal-analysis phase may
prove the real-number identity connecting it to `Real.floor`.
-/
def phiFloorQuantized (n : Nat) : Nat :=
  if n = 0 then
    1
  else if n % 2 = 0 then
    lucas n - 1
  else
    lucas n

/--
Modular reduction of the exact quantized integer.

The proof argument makes the mathematical precondition explicit and keeps the
Lean API aligned with the Python implementation, which rejects a zero modulus.
-/
def phiFloorMod (n m : Nat) (_hm : 0 < m) : Nat :=
  phiFloorQuantized n % m

theorem lucas_101_value : lucas 101 = 1281597540372340914251 := by
  decide

theorem lucas_101_mod_256 : lucas 101 % 256 = 75 := by
  decide

theorem phi_floor_101_mod_256 : phiFloorMod 101 256 (by decide) = 75 := by
  decide

/-! ## 2. DIAG (1, -2, 1) discrete second difference -/

structure DiagOperator where
  c₀ : Int := 1
  c₁ : Int := -2
  c₂ : Int := 1
  deriving Repr, DecidableEq

/-- Canonical second-difference stencil. -/
def diag : DiagOperator := {}

theorem diag_coeff_sum : diag.c₀ + diag.c₁ + diag.c₂ = 0 := by
  decide

/-- Exact integer second difference. -/
def diagApplyInt (a b c : Int) : Int :=
  a - 2 * b + c

/-- A constant signal is annihilated exactly by the second difference. -/
theorem diag_const_zero (a : Int) : diagApplyInt a a a = 0 := by
  unfold diagApplyInt
  omega

/-- Every affine integer triple `(a, a+d, a+2d)` is annihilated. -/
theorem diag_affine_zero (a d : Int) :
    diagApplyInt a (a + d) (a + 2 * d) = 0 := by
  unfold diagApplyInt
  ring

/-- Floating-point implementation, intentionally not promoted to a universal theorem. -/
def diagApplyFloat (a b c : Float) : Float :=
  a - 2.0 * b + c

/-! ## 3. Symbolic state labels -/

/--
Six project-defined state labels.  Constructor names retain COSMO vocabulary;
they do not by themselves formalize the corresponding scientific objects.
-/
inductive CosmoLayer where
  | E8Symmetry
  | PhiScaled
  | SiS2Substrate
  | TrialityBranch
  | HPV16Layer
  | OuroborosLoop
  deriving Repr, DecidableEq

open CosmoLayer

/-- Legacy helper retained for compatibility; it is not the Phase C authority. -/
def sclProjection : CosmoLayer → CosmoLayer
  | E8Symmetry => PhiScaled
  | other => other

/-- Legacy helper retained for compatibility; it is not the Phase C authority. -/
def trialityRotation : CosmoLayer → CosmoLayer
  | PhiScaled => SiS2Substrate
  | SiS2Substrate => TrialityBranch
  | other => other

/-- Legacy helper retained for compatibility; it is not the Phase C authority. -/
def infection : CosmoLayer → CosmoLayer
  | TrialityBranch => HPV16Layer
  | other => other

/-- Legacy helper retained for compatibility; it is not the Phase C authority. -/
def ouroboros : CosmoLayer → CosmoLayer
  | HPV16Layer => OuroborosLoop
  | OuroborosLoop => E8Symmetry
  | other => other

/-! ## 4. Dragon Seed payload -/

/-- Eight-byte payload.  The represented data length is 64 bits. -/
structure Strand101 where
  b0 : UInt8 := 0xB7
  b1 : UInt8 := 0xBA
  b2 : UInt8 := 0xBE
  b3 : UInt8 := 0xFF
  b4 : UInt8 := 0xD6
  b5 : UInt8 := 0xE5
  b6 : UInt8 := 0xAA
  b7 : UInt8 := 0x55
  deriving Repr, DecidableEq

/-- Canonical project payload.  `101` is retained in the type name as legacy mnemonic. -/
def dragonSeed : Strand101 := {}

def Strand101.toList (s : Strand101) : List UInt8 :=
  [s.b0, s.b1, s.b2, s.b3, s.b4, s.b5, s.b6, s.b7]

/-- Arithmetic sum of the represented payload bytes. -/
def dragonSeedByteSum : Nat :=
  dragonSeed.toList.foldl (fun acc b => acc + b.toNat) 0

/-- Project-declared symbolic value.  It is not derived from the payload bytes. -/
def declaredSymbolicInvariant : Nat := 1621

theorem dragon_seed_length : dragonSeed.toList.length = 8 := by
  decide

theorem dragon_seed_bit_length : 8 * dragonSeed.toList.length = 64 := by
  decide

theorem dragon_seed_byte_sum : dragonSeedByteSum = 1512 := by
  decide

theorem declared_invariant_ne_byte_sum :
    declaredSymbolicInvariant ≠ dragonSeedByteSum := by
  decide

/-- Project-defined symbolic sign annotation by byte position. -/
def cuneiformAnnotation (i : Fin 8) : String :=
  match i.val with
  | 0 => "AN"
  | 1 => "KI"
  | 2 => "EN.KI"
  | 3 => "DIGIR"
  | 4 => "SI.SI"
  | 5 => "E2"
  | 6 => "ZU"
  | 7 => "UR"
  | _ => "?"

/-! ## 5. Authoritative six-state COSMO dynamics -/

/--
The single authoritative one-step transition for Phase C.

The constructor names are project vocabulary only.  This transition function
formalizes the discrete cycle, not the scientific objects suggested by labels.
-/
def cosmoStep : CosmoLayer → CosmoLayer
  | E8Symmetry => PhiScaled
  | PhiScaled => SiS2Substrate
  | SiS2Substrate => TrialityBranch
  | TrialityBranch => HPV16Layer
  | HPV16Layer => OuroborosLoop
  | OuroborosLoop => E8Symmetry

/--
Compatibility-facing name retained from the baseline.  From Phase C onward,
Psi is exactly one application of the authoritative six-state transition.
-/
def psiEquation (layer : CosmoLayer) : CosmoLayer :=
  cosmoStep layer

/-- Iterate the authoritative transition exactly n times. -/
def psiIterate : Nat → CosmoLayer → CosmoLayer
  | 0, l => l
  | n + 1, l => psiIterate n (cosmoStep l)

/-- Typed evidence for the six and only six allowed one-step transitions. -/
inductive Transition : CosmoLayer → CosmoLayer → Prop where
  | e8ToPhi : Transition E8Symmetry PhiScaled
  | phiToSubstrate : Transition PhiScaled SiS2Substrate
  | substrateToTriality : Transition SiS2Substrate TrialityBranch
  | trialityToHPV16 : Transition TrialityBranch HPV16Layer
  | hpv16ToOuroboros : Transition HPV16Layer OuroborosLoop
  | ouroborosToE8 : Transition OuroborosLoop E8Symmetry

/-- Every authoritative one-step computation has a typed transition witness. -/
theorem transition_witness (layer : CosmoLayer) :
    Transition layer (cosmoStep layer) := by
  cases layer with
  | E8Symmetry => exact Transition.e8ToPhi
  | PhiScaled => exact Transition.phiToSubstrate
  | SiS2Substrate => exact Transition.substrateToTriality
  | TrialityBranch => exact Transition.trialityToHPV16
  | HPV16Layer => exact Transition.hpv16ToOuroboros
  | OuroborosLoop => exact Transition.ouroborosToE8

/-- Six authoritative steps return every state to itself. -/
theorem six_step_periodic (layer : CosmoLayer) :
    psiIterate 6 layer = layer := by
  cases layer <;> rfl

/-- No state closes early after one through five positive steps. -/
theorem first_five_not_periodic (layer : CosmoLayer) :
    psiIterate 1 layer ≠ layer ∧
    psiIterate 2 layer ≠ layer ∧
    psiIterate 3 layer ≠ layer ∧
    psiIterate 4 layer ≠ layer ∧
    psiIterate 5 layer ≠ layer := by
  cases layer <;> decide

/-- Reachability inside one complete six-state orbit. -/
def ReachesWithinCycle (source target : CosmoLayer) : Prop :=
  psiIterate 0 source = target ∨
  psiIterate 1 source = target ∨
  psiIterate 2 source = target ∨
  psiIterate 3 source = target ∨
  psiIterate 4 source = target ∨
  psiIterate 5 source = target

/-- Every state reaches every other state within one complete six-state orbit. -/
theorem every_layer_reachable (source target : CosmoLayer) :
    ReachesWithinCycle source target := by
  cases source <;> cases target <;>
    simp [ReachesWithinCycle, psiIterate, cosmoStep]

/-- Canonical roadmap order for one complete orbit from E8Symmetry. -/
def canonicalOrbit : List CosmoLayer :=
  [E8Symmetry, PhiScaled, SiS2Substrate, TrialityBranch, HPV16Layer, OuroborosLoop]

theorem canonical_orbit_matches_iterates :
    canonicalOrbit =
      List.ofFn (fun n : Fin 6 => psiIterate n.val E8Symmetry) := by
  decide

theorem canonical_orbit_nodup : canonicalOrbit.Nodup := by
  decide

/-- The loop-labelled state advances back to the E8-labelled state. -/
theorem ouroboros_loop_back : cosmoStep OuroborosLoop = E8Symmetry := by
  rfl

/-- The HPV16-labelled state advances into the loop-labelled state. -/
theorem hpv16_enters_loop : cosmoStep HPV16Layer = OuroborosLoop := by
  rfl

/-- The legacy scaling helper remains identity outside E8Symmetry. -/
theorem scl_idempotent (l : CosmoLayer) (h : l ≠ E8Symmetry) :
    sclProjection l = l := by
  cases l <;> first | rfl | exact absurd rfl h

end Cosmovirus
