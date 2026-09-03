import unittest

from cosmovirus import CosmoBit101, DECLARED_SYMBOLIC_INVARIANT


class CosmovirusCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cosmo = CosmoBit101()

    def test_lucas_101_exact(self) -> None:
        self.assertEqual(
            self.cosmo._lucas(101),
            1281597540372340914251,
        )

    def test_phi_floor_quantization(self) -> None:
        self.assertEqual(self.cosmo.phi_floor_integer(0), 1)
        self.assertEqual(self.cosmo.phi_floor_integer(1), 1)
        self.assertEqual(self.cosmo.phi_floor_integer(2), 2)
        self.assertEqual(self.cosmo.phi_floor_modulo(101, 256), 75)

    def test_phi_floor_quantization_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            self.cosmo.phi_floor_integer(-1)
        with self.assertRaises(ValueError):
            self.cosmo.phi_floor_modulo(101, 0)

    def test_payload_size_and_sum(self) -> None:
        self.assertEqual(len(self.cosmo.strand), 8)
        self.assertEqual(self.cosmo.payload_bit_length(), 64)
        self.assertEqual(self.cosmo.byte_sum(), 1512)

    def test_declared_symbolic_invariant_is_not_byte_sum(self) -> None:
        self.assertEqual(self.cosmo.declared_symbolic_invariant(), 1621)
        self.assertEqual(DECLARED_SYMBOLIC_INVARIANT, 1621)
        self.assertNotEqual(
            self.cosmo.declared_symbolic_invariant(),
            self.cosmo.byte_sum(),
        )

    def test_diag_annihilates_linear_ramp(self) -> None:
        self.assertEqual(
            self.cosmo.diag_operator([1.0, 2.0, 3.0, 4.0, 5.0]),
            [0.0, 0.0, 0.0],
        )

    def test_diag_rejects_short_input(self) -> None:
        with self.assertRaises(ValueError):
            self.cosmo.diag_operator([1.0, 2.0])

    def test_ouroboros_iteration_uses_verified_step(self) -> None:
        self.assertEqual(
            self.cosmo.ouroboros_iterate(5),
            [5, 80, 155, 230, 49, 124],
        )
        with self.assertRaises(ValueError):
            self.cosmo.ouroboros_iterate(-1)


if __name__ == "__main__":
    unittest.main()
