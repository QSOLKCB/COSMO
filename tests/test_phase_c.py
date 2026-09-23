import sys
import unittest
from pathlib import Path
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cosmo_core import (
    CANONICAL_COSMO_ORBIT,
    CosmoState,
    TransitionKind,
    TransitionWitness,
    canonical_orbit,
    cosmo_step,
    iterate_cosmo_state,
    reaches_within_cycle,
    steps_to_reach,
    transition_kind,
    transition_path,
    transition_witness,
)


class AuthoritativeCosmoDynamicsTests(unittest.TestCase):
    def test_canonical_state_vocabulary_and_order(self) -> None:
        self.assertEqual(
            CANONICAL_COSMO_ORBIT,
            (
                CosmoState.E8Symmetry,
                CosmoState.PhiScaled,
                CosmoState.SiS2Substrate,
                CosmoState.TrialityBranch,
                CosmoState.HPV16Layer,
                CosmoState.OuroborosLoop,
            ),
        )
        self.assertEqual(
            tuple(state.value for state in CANONICAL_COSMO_ORBIT),
            (
                "E8Symmetry",
                "PhiScaled",
                "SiS2Substrate",
                "TrialityBranch",
                "HPV16Layer",
                "OuroborosLoop",
            ),
        )

    def test_one_step_transition_is_exact(self) -> None:
        expected = (
            CosmoState.PhiScaled,
            CosmoState.SiS2Substrate,
            CosmoState.TrialityBranch,
            CosmoState.HPV16Layer,
            CosmoState.OuroborosLoop,
            CosmoState.E8Symmetry,
        )
        self.assertEqual(
            tuple(cosmo_step(state) for state in CANONICAL_COSMO_ORBIT),
            expected,
        )

    def test_six_steps_return_every_state_to_itself(self) -> None:
        for state in CANONICAL_COSMO_ORBIT:
            with self.subTest(state=state):
                self.assertIs(iterate_cosmo_state(state, 6), state)

    def test_six_is_the_minimal_positive_period_for_every_state(self) -> None:
        for state in CANONICAL_COSMO_ORBIT:
            for steps in range(1, 6):
                with self.subTest(state=state, steps=steps):
                    self.assertIsNot(iterate_cosmo_state(state, steps), state)

    def test_every_source_reaches_every_target_uniquely_within_one_cycle(self) -> None:
        for source in CANONICAL_COSMO_ORBIT:
            orbit = canonical_orbit(source)
            self.assertEqual(len(orbit), 6)
            self.assertEqual(len(set(orbit)), 6)

            for target in CANONICAL_COSMO_ORBIT:
                with self.subTest(source=source, target=target):
                    steps = steps_to_reach(source, target)
                    self.assertGreaterEqual(steps, 0)
                    self.assertLess(steps, 6)
                    self.assertIs(iterate_cosmo_state(source, steps), target)
                    self.assertTrue(reaches_within_cycle(source, target))
                    self.assertEqual(
                        sum(
                            iterate_cosmo_state(source, candidate) is target
                            for candidate in range(6)
                        ),
                        1,
                    )

    def test_canonical_orbit_from_e8_matches_authoritative_order(self) -> None:
        self.assertEqual(canonical_orbit(), CANONICAL_COSMO_ORBIT)

    def test_transition_witnesses_are_typed_and_continuous(self) -> None:
        expected_kinds = (
            TransitionKind.PHI_SCALE,
            TransitionKind.SUBSTRATE,
            TransitionKind.TRIALITY,
            TransitionKind.HPV16,
            TransitionKind.OUROBOROS,
            TransitionKind.LOOP_BACK,
        )

        witnesses = tuple(
            transition_witness(state)
            for state in CANONICAL_COSMO_ORBIT
        )
        self.assertEqual(
            tuple(witness.kind for witness in witnesses),
            expected_kinds,
        )

        path = transition_path(CosmoState.E8Symmetry, 6)
        self.assertEqual(path, witnesses)
        for left, right in zip(path, path[1:], strict=True):
            self.assertIs(left.target, right.source)
        self.assertIs(path[-1].target, CosmoState.E8Symmetry)

    def test_transition_kind_matches_source(self) -> None:
        self.assertEqual(
            tuple(transition_kind(state) for state in CANONICAL_COSMO_ORBIT),
            (
                TransitionKind.PHI_SCALE,
                TransitionKind.SUBSTRATE,
                TransitionKind.TRIALITY,
                TransitionKind.HPV16,
                TransitionKind.OUROBOROS,
                TransitionKind.LOOP_BACK,
            ),
        )

    def test_invalid_typed_witness_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TransitionWitness(
                source=CosmoState.E8Symmetry,
                target=CosmoState.SiS2Substrate,
                kind=TransitionKind.PHI_SCALE,
            )
        with self.assertRaises(ValueError):
            TransitionWitness(
                source=CosmoState.E8Symmetry,
                target=CosmoState.PhiScaled,
                kind=TransitionKind.LOOP_BACK,
            )

    def test_invalid_state_and_step_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            cosmo_step(cast(Any, "E8Symmetry"))
        with self.assertRaises(ValueError):
            iterate_cosmo_state(CosmoState.E8Symmetry, cast(Any, True))
        with self.assertRaises(ValueError):
            iterate_cosmo_state(CosmoState.E8Symmetry, -1)
        with self.assertRaises(ValueError):
            steps_to_reach(
                cast(Any, "E8Symmetry"),
                CosmoState.PhiScaled,
            )


if __name__ == "__main__":
    unittest.main()
