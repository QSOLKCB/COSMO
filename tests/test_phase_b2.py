import math
import sys
import unittest
from pathlib import Path
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cosmo_core import (
    ArtifactDigest,
    DECLARED_SYMBOLIC_INVARIANT,
    DRAGON_SEED,
    GOLDEN_RATIO,
    QUARTER_TURN_RADIANS,
    ExperimentManifest,
    UncorrectableECCError,
    bytes_to_dna,
    decode_codeword,
    dna_to_bytes,
    encode_nibble,
    lucas,
    payload_facts,
    phi_floor_integer,
    phi_floor_modulo,
    secded_decode,
    secded_encode,
    sha256_hex,
)


class CanonicalArithmeticTests(unittest.TestCase):
    def test_named_constants_do_not_conflate_phi_and_quarter_turn(self) -> None:
        self.assertEqual(GOLDEN_RATIO, 1.618_033_988_749_895)
        self.assertEqual(QUARTER_TURN_RADIANS, math.pi / 2.0)
        self.assertNotEqual(GOLDEN_RATIO, QUARTER_TURN_RADIANS)

    def test_lucas_and_phi_floor_reference_values(self) -> None:
        self.assertEqual(lucas(101), 1281597540372340914251)
        self.assertEqual(phi_floor_integer(0), 1)
        self.assertEqual(phi_floor_integer(1), 1)
        self.assertEqual(phi_floor_integer(2), 2)
        self.assertEqual(phi_floor_modulo(101, 256), 75)

    def test_phi_floor_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            lucas(-1)
        with self.assertRaises(ValueError):
            phi_floor_integer(-1)
        with self.assertRaises(ValueError):
            phi_floor_modulo(1, 0)


class PayloadIntegrityTests(unittest.TestCase):
    def test_dragon_seed_facts_are_bound_to_bytes(self) -> None:
        facts = payload_facts(DRAGON_SEED)
        self.assertEqual(facts.bit_length, 64)
        self.assertEqual(facts.byte_sum, 1512)
        self.assertEqual(
            facts.declared_symbolic_invariant,
            DECLARED_SYMBOLIC_INVARIANT,
        )
        self.assertEqual(
            facts.sha256,
            "a986bc2ca561bbc9b3947ac55103a58e7c11817321c31e08a5b30f8055b1c652",
        )
        self.assertNotEqual(facts.byte_sum, facts.declared_symbolic_invariant)

    def test_sha256_known_answer(self) -> None:
        self.assertEqual(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223"
            "b00361a396177a9cb410ff61f20015ad",
        )


class SecdedTests(unittest.TestCase):
    def test_all_nibbles_round_trip(self) -> None:
        for nibble in range(16):
            result = decode_codeword(encode_nibble(nibble))
            self.assertEqual(result.nibble, nibble)
            self.assertFalse(result.corrected)

    def test_every_single_bit_error_is_corrected_for_every_nibble(self) -> None:
        for nibble in range(16):
            codeword = encode_nibble(nibble)
            for bit in range(8):
                result = decode_codeword(codeword ^ (1 << bit))
                self.assertEqual(result.nibble, nibble)
                self.assertTrue(result.corrected)
                self.assertEqual(result.overall_parity_only, bit == 7)

    def test_every_double_bit_error_is_detected_for_every_nibble(self) -> None:
        for nibble in range(16):
            codeword = encode_nibble(nibble)
            for first in range(8):
                for second in range(first + 1, 8):
                    with self.assertRaises(UncorrectableECCError):
                        decode_codeword(codeword ^ (1 << first) ^ (1 << second))

    def test_byte_payload_round_trip_and_correction_metadata(self) -> None:
        payload = bytes(range(256))
        encoded = bytearray(secded_encode(payload))
        clean = secded_decode(bytes(encoded))
        self.assertEqual(clean.data, payload)
        self.assertEqual(clean.corrected_codewords, 0)

        for index in range(len(encoded)):
            encoded[index] ^= 1 << (index % 8)

        corrected = secded_decode(bytes(encoded))
        self.assertEqual(corrected.data, payload)
        self.assertEqual(corrected.corrected_codewords, len(encoded))

    def test_invalid_ecc_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            encode_nibble(16)
        with self.assertRaises(ValueError):
            decode_codeword(256)
        with self.assertRaises(ValueError):
            secded_decode(b"\x00")


class DnaCodecTests(unittest.TestCase):
    def test_all_byte_values_round_trip(self) -> None:
        payload = bytes(range(256))
        dna = bytes_to_dna(payload)
        self.assertEqual(len(dna), len(payload) * 4)
        self.assertEqual(dna_to_bytes(dna), payload)

    def test_mapping_is_explicit_and_stable(self) -> None:
        self.assertEqual(bytes_to_dna(b"\x1b"), "ACGT")
        self.assertEqual(dna_to_bytes("ACGT"), b"\x1b")

    def test_invalid_symbols_and_lengths_fail_closed(self) -> None:
        for invalid in ("ACGN", "acgt", "ACG ", "ACG"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    dna_to_bytes(invalid)


class ExperimentManifestTests(unittest.TestCase):
    def _manifest(
        self,
        *,
        seed: int = 7,
        output: bytes = b"result",
    ) -> ExperimentManifest:
        return ExperimentManifest.from_parts(
            seed=seed,
            parameters={"beta": 2, "alpha": 1, "mode": "reference"},
            inputs={"z.bin": b"z", "a.bin": b"a"},
            outputs={"result.bin": output},
        )

    def test_mapping_insertion_order_does_not_change_manifest_identity(self) -> None:
        left = self._manifest()
        right = ExperimentManifest.from_parts(
            seed=7,
            parameters={"mode": "reference", "alpha": 1, "beta": 2},
            inputs={"a.bin": b"a", "z.bin": b"z"},
            outputs={"result.bin": b"result"},
        )
        self.assertEqual(left.canonical_bytes(), right.canonical_bytes())
        self.assertEqual(left.sha256(), right.sha256())

    def test_seed_and_output_bytes_are_bound_into_identity(self) -> None:
        baseline = self._manifest()
        self.assertNotEqual(baseline.sha256(), self._manifest(seed=8).sha256())
        self.assertNotEqual(
            baseline.sha256(),
            self._manifest(output=b"changed").sha256(),
        )


    def test_artifact_digest_rejects_untyped_schema_values(self) -> None:
        digest = "0" * 64

        with self.assertRaises(ValueError):
            ArtifactDigest(cast(Any, 123), 1, digest)
        with self.assertRaises(ValueError):
            ArtifactDigest("artifact.bin", cast(Any, 1.5), digest)
        with self.assertRaises(ValueError):
            ArtifactDigest("artifact.bin", cast(Any, True), digest)
        with self.assertRaises(ValueError):
            ArtifactDigest("artifact.bin", 1, cast(Any, 123))

    def test_manifest_rejects_non_integer_seed_types(self) -> None:
        for invalid_seed in (
            cast(Any, 1.5),
            cast(Any, "1"),
            cast(Any, True),
        ):
            with self.subTest(seed=invalid_seed):
                with self.assertRaises(ValueError):
                    ExperimentManifest.from_parts(
                        seed=invalid_seed,
                        parameters={},
                        inputs={},
                        outputs={},
                    )

    def test_manifest_rejects_mutable_or_non_scalar_parameters(self) -> None:
        mutable_list = cast(Any, ["mutable"])
        mutable_dict = cast(Any, {"mutable": True})

        for invalid_value in (mutable_list, mutable_dict):
            with self.subTest(value=invalid_value):
                with self.assertRaises(ValueError):
                    ExperimentManifest(
                        seed=1,
                        parameters=(("bad", invalid_value),),
                        inputs=(),
                        outputs=(),
                    )

    def test_manifest_rejects_non_string_parameter_names(self) -> None:
        with self.assertRaises(ValueError):
            ExperimentManifest(
                seed=1,
                parameters=((cast(Any, 123), "value"),),
                inputs=(),
                outputs=(),
            )

    def test_manifest_accepts_all_documented_scalar_parameter_types(self) -> None:
        manifest = ExperimentManifest.from_parts(
            seed=1,
            parameters={
                "string": "value",
                "integer": 2,
                "float": 2.5,
                "boolean": True,
                "null": None,
            },
            inputs={},
            outputs={},
        )
        self.assertEqual(
            dict(manifest.parameters),
            {
                "boolean": True,
                "float": 2.5,
                "integer": 2,
                "null": None,
                "string": "value",
            },
        )

    def test_manifest_rejects_non_finite_float_parameters(self) -> None:
        with self.assertRaises(ValueError):
            ExperimentManifest.from_parts(
                seed=1,
                parameters={"bad": float("nan")},
                inputs={},
                outputs={},
            )

    def test_manifest_rejects_negative_or_boolean_seed(self) -> None:
        with self.assertRaises(ValueError):
            ExperimentManifest.from_parts(
                seed=-1,
                parameters={},
                inputs={},
                outputs={},
            )
        with self.assertRaises(ValueError):
            ExperimentManifest.from_parts(
                seed=True,
                parameters={},
                inputs={},
                outputs={},
            )


if __name__ == "__main__":
    unittest.main()
