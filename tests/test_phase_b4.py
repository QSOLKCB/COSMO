import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import cosmo_core.triadic as triadic_module

from cosmo_core import (
    LATTICE_SIZE,
    MAX_PARALLEL_WORKERS,
    DEFAULT_TRIADIC_RULE,
    RecoveryStatus,
    TernaryRepetitionCode,
    TriadicCodebook,
    TriadicLattice,
    TriadicMask,
    TriadicRule,
    analyze_stability,
    canonical_neighbor_table,
    corrupt_codeword,
    encode_lattice,
    generate_neighbor_table_reference,
    lattice_coordinates,
    lattice_index,
    loop_closure,
    neighbor_indices_reference,
    recover_lattice,
    runtime_cpu_capacity,
    state_entropy,
    step_parallel,
    step_scalar,
    triadic_digit_mask,
)


class TriadicLatticeIdentityTests(unittest.TestCase):
    def test_seeded_initialization_is_replayable_and_bound_to_seed(self) -> None:
        zero_seed = TriadicLattice.seeded(0)
        replay = TriadicLattice.seeded(0)
        other = TriadicLattice.seeded(1)

        self.assertEqual(zero_seed, replay)
        self.assertNotEqual(zero_seed, other)
        self.assertEqual(zero_seed.state_counts(), (173, 183, 156))
        self.assertEqual(
            zero_seed.sha256(),
            "2ba2a34b1dde358045011fbe4dc9dce0"
            "4da9f56ff34f2eec774486218bb7a6eb",
        )

    def test_seed_validation_fails_closed(self) -> None:
        for invalid in (cast(Any, True), cast(Any, -1), cast(Any, 1 << 64)):
            with self.subTest(seed=invalid):
                with self.assertRaises(ValueError):
                    TriadicLattice.seeded(invalid)

    def test_lattice_state_is_immutable_and_strictly_ternary(self) -> None:
        with self.assertRaises(ValueError):
            TriadicLattice(cast(Any, [0] * LATTICE_SIZE))
        with self.assertRaises(ValueError):
            TriadicLattice((0,) * (LATTICE_SIZE - 1))
        with self.assertRaises(ValueError):
            TriadicLattice((0,) * (LATTICE_SIZE - 1) + (3,))
        with self.assertRaises(ValueError):
            TriadicLattice((0,) * (LATTICE_SIZE - 1) + (cast(Any, True),))

    def test_coordinate_index_round_trip_is_complete(self) -> None:
        for index in range(LATTICE_SIZE):
            coordinate = lattice_coordinates(index)
            self.assertEqual(lattice_index(*coordinate), index)

    def test_periodic_neighbor_table_matches_reference_and_is_reused(self) -> None:
        reference = generate_neighbor_table_reference()
        cached = canonical_neighbor_table()

        self.assertEqual(cached, reference)
        self.assertIs(cached, canonical_neighbor_table())
        self.assertEqual(
            neighbor_indices_reference(0),
            (448, 64, 56, 8, 7, 1),
        )

        for index, neighbours in enumerate(cached):
            self.assertEqual(len(neighbours), 6)
            self.assertEqual(len(set(neighbours)), 6)
            for neighbour in neighbours:
                self.assertIn(index, cached[neighbour])


class TriadicMaskAndUpdateTests(unittest.TestCase):
    def test_triadic_digit_mask_has_stable_identity(self) -> None:
        mask = triadic_digit_mask(depth=2, phase=0)

        self.assertEqual(mask.kind, "ternary-digit-residue")
        self.assertEqual(mask.values.count(0), 170)
        self.assertEqual(mask.values.count(1), 171)
        self.assertEqual(mask.values.count(2), 171)
        self.assertEqual(
            mask.sha256(),
            "789519a500faa60c95d3df52d37ffc45"
            "4804054cc92459c7ffc8e234eb40c676",
        )

        shifted = triadic_digit_mask(depth=2, phase=1)
        self.assertEqual(
            shifted.values,
            tuple((value + 1) % 3 for value in mask.values),
        )

    def test_rule_and_mask_validation_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            TriadicRule(center_weight=3)
        with self.assertRaises(ValueError):
            TriadicRule(neighbor_weight=cast(Any, True))
        with self.assertRaises(ValueError):
            triadic_digit_mask(depth=0)
        with self.assertRaises(ValueError):
            triadic_digit_mask(phase=3)
        with self.assertRaises(ValueError):
            TriadicMask(
                values=(0,) * LATTICE_SIZE,
                kind="",
                depth=2,
                phase=0,
            )

    def test_scalar_update_has_stable_reference_identity(self) -> None:
        initial = TriadicLattice.seeded(0)
        next_state = step_scalar(initial)

        self.assertEqual(
            next_state.sha256(),
            "a8eef51d23fc9331aa024e5932181f10"
            "9f4afec1b0381696da6222538e4824da",
        )
        self.assertEqual(next_state.state_counts(), (157, 179, 176))
        self.assertEqual(step_scalar(TriadicLattice.zero()), TriadicLattice.zero())

    def test_mask_changes_the_deterministic_transition(self) -> None:
        initial = TriadicLattice.seeded(7)
        without_mask = step_scalar(initial)
        with_mask = step_scalar(initial, mask=triadic_digit_mask())

        self.assertNotEqual(without_mask, with_mask)
        self.assertEqual(
            with_mask,
            step_scalar(initial, mask=triadic_digit_mask()),
        )


class BoundedParallelTests(unittest.TestCase):
    def test_parallel_equals_scalar_for_multiple_worker_requests(self) -> None:
        initial = TriadicLattice.seeded(42)
        mask = triadic_digit_mask(depth=2, phase=2)
        scalar = step_scalar(initial, mask=mask)

        for requested in (1, 2, 4, 7):
            with self.subTest(requested=requested):
                result = step_parallel(
                    initial,
                    requested,
                    mask=mask,
                )
                self.assertEqual(result.lattice, scalar)
                self.assertEqual(result.requested_workers, requested)
                self.assertGreaterEqual(result.host_logical_cpus, 1)
                self.assertGreaterEqual(result.worker_capacity, 1)
                self.assertLessEqual(
                    result.worker_capacity,
                    min(result.host_logical_cpus, MAX_PARALLEL_WORKERS),
                )
                self.assertGreaterEqual(result.effective_workers, 1)
                self.assertLessEqual(result.effective_workers, requested)
                self.assertGreaterEqual(result.observed_worker_threads, 1)
                self.assertLessEqual(
                    result.observed_worker_threads,
                    result.effective_workers,
                )
                self.assertEqual(len(result.partitions), result.effective_workers)
                self.assertEqual(result.partitions[0][0], 0)
                self.assertEqual(result.partitions[-1][1], LATTICE_SIZE)
                self.assertEqual(
                    result.partitions,
                    step_parallel(
                        initial,
                        requested,
                        mask=mask,
                    ).partitions,
                )

    def test_parallel_multi_step_state_matches_scalar_reference(self) -> None:
        scalar = TriadicLattice.seeded(99)
        parallel = scalar
        mask = triadic_digit_mask(depth=1, phase=1)

        for _ in range(4):
            scalar = step_scalar(scalar, mask=mask)
            parallel = step_parallel(
                parallel,
                requested_workers=7,
                mask=mask,
            ).lattice
            self.assertEqual(parallel, scalar)

    def test_cgroup_v2_quota_caps_default_worker_pool(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory)
            (root / "cpu.max").write_text(
                "200000 100000\n",
                encoding="utf-8",
            )
            proc_cgroup = root / "proc-self-cgroup"
            proc_cgroup.write_text("0::/\n", encoding="utf-8")

            self.assertEqual(
                triadic_module._cgroup_cpu_capacity(
                    cgroup_root=root,
                    proc_cgroup=proc_cgroup,
                ),
                2,
            )

        with (
            patch("cosmo_core.triadic.os.cpu_count", return_value=3),
            patch(
                "cosmo_core.triadic._affinity_cpu_capacity",
                return_value=3,
            ),
            patch(
                "cosmo_core.triadic._cgroup_cpu_capacity",
                return_value=2,
            ),
        ):
            result = step_parallel(
                TriadicLattice.zero(),
                requested_workers=32,
            )

        self.assertEqual(result.host_logical_cpus, 3)
        self.assertEqual(result.worker_capacity, 2)
        self.assertEqual(result.effective_workers, 2)

    def test_runtime_capacity_respects_process_affinity(self) -> None:
        with (
            patch("cosmo_core.triadic.os.cpu_count", return_value=8),
            patch(
                "cosmo_core.triadic._affinity_cpu_capacity",
                return_value=2,
            ),
            patch(
                "cosmo_core.triadic._cgroup_cpu_capacity",
                return_value=None,
            ),
        ):
            self.assertEqual(runtime_cpu_capacity(), 2)

    def test_worker_capacity_can_only_reduce_parallelism(self) -> None:
        result = step_parallel(
            TriadicLattice.seeded(3),
            requested_workers=7,
            worker_capacity=2,
        )
        self.assertLessEqual(result.worker_capacity, 2)
        self.assertLessEqual(result.effective_workers, 2)

    def test_invalid_worker_requests_fail_closed(self) -> None:
        lattice = TriadicLattice.zero()
        for invalid in (cast(Any, 0), cast(Any, -1), cast(Any, True)):
            with self.subTest(requested=invalid):
                with self.assertRaises(ValueError):
                    step_parallel(lattice, invalid)

        with self.assertRaises(ValueError):
            step_parallel(lattice, 2, worker_capacity=0)


class RecoveryModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.code = TernaryRepetitionCode()

    def test_codebook_protocol_and_explicit_syndrome(self) -> None:
        self.assertIsInstance(self.code, TriadicCodebook)
        self.assertEqual(self.code.block_length, 3)
        self.assertEqual(self.code.syndrome((0, 0, 0)), (0, 0))
        self.assertEqual(self.code.syndrome((0, 1, 0)), (1, 0))

    def test_every_single_trit_corruption_is_corrected(self) -> None:
        for symbol in (0, 1, 2):
            clean = self.code.encode(symbol)
            self.assertEqual(self.code.recover(clean).status, RecoveryStatus.CLEAN)
            for index in range(3):
                for delta in (1, 2):
                    with self.subTest(symbol=symbol, index=index, delta=delta):
                        corrupted = corrupt_codeword(clean, index, delta)
                        result = self.code.recover(corrupted)
                        self.assertEqual(result.status, RecoveryStatus.CORRECTED)
                        self.assertEqual(result.symbol, symbol)
                        self.assertEqual(result.corrected_indices, (index,))
                        self.assertEqual(result.recovery_passes, 1)

    def test_all_distinct_codeword_is_detected_as_uncorrectable(self) -> None:
        result = self.code.recover((0, 1, 2))
        self.assertEqual(result.status, RecoveryStatus.UNCORRECTABLE)
        self.assertIsNone(result.symbol)
        self.assertIsNone(result.recovery_passes)

    def test_full_lattice_single_error_recovery(self) -> None:
        lattice = TriadicLattice.seeded(11)
        encoded = list(encode_lattice(lattice, self.code))
        corrupted_blocks = (0, 17, 255, 511)

        for block_index in corrupted_blocks:
            encoded[block_index] = corrupt_codeword(
                encoded[block_index],
                block_index % 3,
                1 + (block_index % 2),
            )

        report = recover_lattice(tuple(encoded), self.code)
        self.assertEqual(report.recovered, lattice)
        self.assertEqual(report.corrected_blocks, corrupted_blocks)
        self.assertEqual(report.uncorrectable_blocks, ())
        self.assertEqual(report.max_recovery_passes, 1)

    def test_uncorrectable_block_prevents_false_lattice_recovery(self) -> None:
        lattice = TriadicLattice.seeded(12)
        encoded = list(encode_lattice(lattice, self.code))
        encoded[9] = (0, 1, 2)

        report = recover_lattice(tuple(encoded), self.code)
        self.assertIsNone(report.recovered)
        self.assertEqual(report.uncorrectable_blocks, (9,))
        self.assertIsNone(report.max_recovery_passes)

    def test_mutable_or_malformed_recovery_inputs_are_rejected(self) -> None:
        lattice = TriadicLattice.zero()
        encoded = encode_lattice(lattice, self.code)

        with self.assertRaises(ValueError):
            recover_lattice(cast(Any, list(encoded)), self.code)
        with self.assertRaises(ValueError):
            self.code.recover(cast(Any, [0, 0, 0]))
        with self.assertRaises(ValueError):
            corrupt_codeword((0, 0, 0), 3)


class DynamicsDiagnosticsTests(unittest.TestCase):
    def test_loop_closure_detects_exact_two_cycle(self) -> None:
        lattice = TriadicLattice.seeded(5)
        toggle = TriadicRule(
            center_weight=2,
            neighbor_weight=0,
            bias=0,
        )

        one_step = loop_closure(lattice, 1, toggle)
        two_steps = loop_closure(lattice, 2, toggle)

        self.assertFalse(one_step.closed)
        self.assertGreater(one_step.distance, 0)
        self.assertTrue(two_steps.closed)
        self.assertEqual(two_steps.distance, 0)
        self.assertEqual(two_steps.initial_sha256, two_steps.final_sha256)

    def test_stability_distinguishes_fixed_point_and_two_cycle(self) -> None:
        fixed = analyze_stability(
            TriadicLattice.zero(),
            max_steps=2,
        )
        self.assertTrue(fixed.cycle_detected)
        self.assertTrue(fixed.converged)
        self.assertEqual(fixed.transient_length, 0)
        self.assertEqual(fixed.cycle_length, 1)

        toggle = TriadicRule(
            center_weight=2,
            neighbor_weight=0,
            bias=0,
        )
        cycle = analyze_stability(
            TriadicLattice.seeded(5),
            max_steps=2,
            rule=toggle,
        )
        self.assertTrue(cycle.cycle_detected)
        self.assertFalse(cycle.converged)
        self.assertEqual(cycle.transient_length, 0)
        self.assertEqual(cycle.cycle_length, 2)

    def test_entropy_is_population_diagnostic_not_state_identity(self) -> None:
        self.assertEqual(state_entropy(TriadicLattice.zero()), 0.0)

        entropy = state_entropy(TriadicLattice.seeded(0))
        self.assertGreater(entropy, 0.0)
        self.assertLessEqual(entropy, 1.0)


if __name__ == "__main__":
    unittest.main()
