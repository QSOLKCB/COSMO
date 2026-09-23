"""Authoritative six-state COSMO dynamics for Phase C.

The state names are project vocabulary. This module defines only the discrete
transition system and does not establish physical, biomedical, archaeological,
or cosmological correspondence for those labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class CosmoState(str, Enum):
    """The six authoritative COSMO state labels."""

    E8Symmetry = "E8Symmetry"
    PhiScaled = "PhiScaled"
    SiS2Substrate = "SiS2Substrate"
    TrialityBranch = "TrialityBranch"
    HPV16Layer = "HPV16Layer"
    OuroborosLoop = "OuroborosLoop"


class TransitionKind(str, Enum):
    """Canonical label for each directed transition in the six-state cycle."""

    PHI_SCALE = "phi-scale"
    SUBSTRATE = "substrate"
    TRIALITY = "triality"
    HPV16 = "hpv16"
    OUROBOROS = "ouroboros"
    LOOP_BACK = "loop-back"


CANONICAL_COSMO_ORBIT: Final[tuple[CosmoState, ...]] = (
    CosmoState.E8Symmetry,
    CosmoState.PhiScaled,
    CosmoState.SiS2Substrate,
    CosmoState.TrialityBranch,
    CosmoState.HPV16Layer,
    CosmoState.OuroborosLoop,
)


def _require_state(value: object, label: str = "state") -> CosmoState:
    if not isinstance(value, CosmoState):
        raise ValueError(f"{label} must be a CosmoState")
    return value


def _require_non_negative_steps(steps: object) -> int:
    if type(steps) is not int or steps < 0:
        raise ValueError("steps must be a non-negative integer")
    return steps


def cosmo_step(state: CosmoState) -> CosmoState:
    """Advance exactly one step around the authoritative six-state cycle."""
    exact = _require_state(state)

    match exact:
        case CosmoState.E8Symmetry:
            return CosmoState.PhiScaled
        case CosmoState.PhiScaled:
            return CosmoState.SiS2Substrate
        case CosmoState.SiS2Substrate:
            return CosmoState.TrialityBranch
        case CosmoState.TrialityBranch:
            return CosmoState.HPV16Layer
        case CosmoState.HPV16Layer:
            return CosmoState.OuroborosLoop
        case CosmoState.OuroborosLoop:
            return CosmoState.E8Symmetry

    raise AssertionError("unreachable CosmoState match")


def transition_kind(state: CosmoState) -> TransitionKind:
    """Return the canonical transition label leaving the supplied state."""
    exact = _require_state(state)

    match exact:
        case CosmoState.E8Symmetry:
            return TransitionKind.PHI_SCALE
        case CosmoState.PhiScaled:
            return TransitionKind.SUBSTRATE
        case CosmoState.SiS2Substrate:
            return TransitionKind.TRIALITY
        case CosmoState.TrialityBranch:
            return TransitionKind.HPV16
        case CosmoState.HPV16Layer:
            return TransitionKind.OUROBOROS
        case CosmoState.OuroborosLoop:
            return TransitionKind.LOOP_BACK

    raise AssertionError("unreachable CosmoState match")


@dataclass(frozen=True)
class TransitionWitness:
    """Typed evidence for one valid authoritative COSMO transition."""

    source: CosmoState
    target: CosmoState
    kind: TransitionKind

    def __post_init__(self) -> None:
        source = _require_state(self.source, "source")
        target = _require_state(self.target, "target")
        if not isinstance(self.kind, TransitionKind):
            raise ValueError("kind must be a TransitionKind")
        if cosmo_step(source) is not target:
            raise ValueError("target is not the authoritative successor of source")
        if transition_kind(source) is not self.kind:
            raise ValueError("transition kind does not match source")


def transition_witness(state: CosmoState) -> TransitionWitness:
    """Return typed evidence for the one transition leaving the supplied state."""
    source = _require_state(state)
    return TransitionWitness(
        source=source,
        target=cosmo_step(source),
        kind=transition_kind(source),
    )


def iterate_cosmo_state(state: CosmoState, steps: int) -> CosmoState:
    """Advance a non-negative number of steps through the authoritative cycle."""
    current = _require_state(state)
    exact_steps = _require_non_negative_steps(steps)

    for _ in range(exact_steps):
        current = cosmo_step(current)
    return current


def transition_path(
    state: CosmoState,
    steps: int,
) -> tuple[TransitionWitness, ...]:
    """Return the canonical typed transition path of the requested length."""
    current = _require_state(state)
    exact_steps = _require_non_negative_steps(steps)
    path: list[TransitionWitness] = []

    for _ in range(exact_steps):
        witness = transition_witness(current)
        path.append(witness)
        current = witness.target

    return tuple(path)


def canonical_orbit(
    start: CosmoState = CosmoState.E8Symmetry,
) -> tuple[CosmoState, ...]:
    """Return one complete six-state orbit beginning at start."""
    exact_start = _require_state(start)
    return tuple(
        iterate_cosmo_state(exact_start, steps)
        for steps in range(len(CANONICAL_COSMO_ORBIT))
    )


def steps_to_reach(source: CosmoState, target: CosmoState) -> int:
    """Return the unique step count in 0..5 from source to target."""
    exact_source = _require_state(source, "source")
    exact_target = _require_state(target, "target")

    for steps in range(len(CANONICAL_COSMO_ORBIT)):
        if iterate_cosmo_state(exact_source, steps) is exact_target:
            return steps

    raise AssertionError("six-state cycle failed to reach a CosmoState")


def reaches_within_cycle(source: CosmoState, target: CosmoState) -> bool:
    """Return whether target occurs within one six-state orbit of source."""
    steps_to_reach(source, target)
    return True
