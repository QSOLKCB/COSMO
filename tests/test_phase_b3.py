import sys
import unittest
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cosmo_core import (
    E8_HALF_INTEGER_ROOT_COUNT,
    E8_INTEGER_ROOT_COUNT,
    E8_ROOT_COUNT,
    E8_ROOT_TABLE_SHA256,
    E8RootFamily,
    ScaledVector,
    canonical_e8_roots,
    canonical_weyl_reflections,
    dot_product,
    e8_root_table_sha256,
    exact_rank,
    generate_e8_half_integer_roots_reference,
    generate_e8_integer_roots_reference,
    generate_e8_roots_reference,
    is_e8_lattice_vector,
    is_e8_root,
    norm_squared,
    root_family,
    validate_e8_root_system,
    weyl_reflect,
)


class ExactE8RootTests(unittest.TestCase):
    def test_explicit_root_families_have_expected_cardinality(self) -> None:
        integer_roots = generate_e8_integer_roots_reference()
        half_integer_roots = generate_e8_half_integer_roots_reference()

        self.assertEqual(len(integer_roots), E8_INTEGER_ROOT_COUNT)
        self.assertEqual(len(half_integer_roots), E8_HALF_INTEGER_ROOT_COUNT)
        self.assertTrue(
            all(
                root_family(root) is E8RootFamily.INTEGER
                for root in integer_roots
            )
        )
        self.assertTrue(
            all(
                root_family(root) is E8RootFamily.HALF_INTEGER
                for root in half_integer_roots
            )
        )

    def test_canonical_root_table_identity_and_order(self) -> None:
        roots = canonical_e8_roots()
        reference = generate_e8_roots_reference()

        self.assertEqual(roots, reference)
        self.assertIs(roots, canonical_e8_roots())
        self.assertEqual(len(roots), E8_ROOT_COUNT)
        self.assertEqual(len(set(roots)), E8_ROOT_COUNT)
        self.assertEqual(roots, tuple(sorted(roots)))
        self.assertEqual(
            E8_ROOT_TABLE_SHA256,
            "f6e7675c180edb41ea1c47705d7b14da"
            "eed7e08f3791dbdf1fc0c55ef156b662",
        )
        self.assertEqual(e8_root_table_sha256(roots), E8_ROOT_TABLE_SHA256)

    def test_root_system_report_has_rank_eight_and_norm_two(self) -> None:
        roots = canonical_e8_roots()
        report = validate_e8_root_system(roots)

        self.assertEqual(report.root_count, 240)
        self.assertEqual(report.integer_root_count, 112)
        self.assertEqual(report.half_integer_root_count, 128)
        self.assertEqual(report.rank, 8)
        self.assertEqual(report.sha256, E8_ROOT_TABLE_SHA256)
        self.assertEqual(exact_rank(roots), 8)
        self.assertTrue(all(norm_squared(root) == Fraction(2) for root in roots))
        self.assertTrue(all(is_e8_lattice_vector(root) for root in roots))

    def test_reflections_are_canonically_ordered_by_root(self) -> None:
        roots = canonical_e8_roots()
        reflections = canonical_weyl_reflections()

        self.assertEqual(len(reflections), len(roots))
        self.assertEqual(
            tuple(reflection.root for reflection in reflections),
            roots,
        )
        self.assertIs(reflections, canonical_weyl_reflections())


class WeylReflectionTests(unittest.TestCase):
    def test_all_root_reflections_preserve_root_system_norm_and_involution(
        self,
    ) -> None:
        roots = canonical_e8_roots()
        root_set = set(roots)

        for mirror in roots:
            for vector in roots:
                reflected = weyl_reflect(vector, mirror)
                if reflected not in root_set:
                    self.fail(
                        f"reflection escaped root system: {vector=} {mirror=}"
                    )
                self.assertEqual(norm_squared(reflected), Fraction(2))
                self.assertEqual(
                    weyl_reflect(reflected, mirror),
                    vector,
                )

    def test_reflection_sends_mirror_root_to_its_negative(self) -> None:
        for root in canonical_e8_roots():
            self.assertEqual(
                weyl_reflect(root, root),
                tuple(-coordinate for coordinate in root),
            )

    def test_hyperplane_vectors_are_fixed(self) -> None:
        roots = canonical_e8_roots()
        checked = 0

        for mirror in roots:
            for vector in roots:
                if dot_product(vector, mirror) != 0:
                    continue
                self.assertEqual(weyl_reflect(vector, mirror), vector)
                checked += 1

        self.assertGreater(checked, 0)

    def test_lattice_preservation_beyond_roots(self) -> None:
        roots = canonical_e8_roots()
        samples: set[ScaledVector] = {(0,) * 8}
        for left in roots[:24]:
            for right in roots[:24]:
                samples.add(
                    tuple(
                        a + b
                        for a, b in zip(left, right, strict=True)
                    )
                )

        mirrors = roots[::17]
        for vector in sorted(samples):
            self.assertTrue(is_e8_lattice_vector(vector))
            for mirror in mirrors:
                reflected = weyl_reflect(vector, mirror)
                self.assertTrue(is_e8_lattice_vector(reflected))
                self.assertEqual(norm_squared(reflected), norm_squared(vector))

    def test_exact_dot_products_use_rationals_not_float(self) -> None:
        roots = canonical_e8_roots()
        self.assertEqual(dot_product(roots[0], roots[0]), Fraction(2))
        value = dot_product(roots[0], roots[-1])
        self.assertIsInstance(value, Fraction)

    def test_invalid_vectors_and_roots_fail_closed(self) -> None:
        root = canonical_e8_roots()[0]

        self.assertFalse(is_e8_root((0,) * 8))
        self.assertFalse(is_e8_lattice_vector((1, 0, 0, 0, 0, 0, 0, 0)))
        with self.assertRaises(ValueError):
            weyl_reflect(cast(Any, [0] * 8), root)
        with self.assertRaises(ValueError):
            weyl_reflect((0,) * 8, cast(Any, (0,) * 8))
        with self.assertRaises(ValueError):
            exact_rank(cast(Any, [root]))


if __name__ == "__main__":
    unittest.main()
