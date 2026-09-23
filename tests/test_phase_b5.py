import sys
import unittest
from itertools import combinations
from pathlib import Path
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cosmo_core import (
    DnaBitFlip,
    FASTA_LINE_WIDTH,
    StorageArtifact,
    StorageIntegrityError,
    TriadicLattice,
    UncorrectableECCError,
    bytes_to_cube,
    corrupt_synthetic_fasta_bits,
    cube_to_bytes,
    encode_cube_storage,
    encode_payload_storage,
    flip_encoded_bit_in_dna,
    flip_encoded_bits_in_dna,
    parse_synthetic_fasta,
    recover_cube_from_fasta,
    recover_cube_storage,
    recover_payload_from_fasta,
    recover_payload_storage,
    render_synthetic_fasta,
)


class CubeSerializationTests(unittest.TestCase):
    def test_cube_bytes_round_trip_is_exact(self) -> None:
        cube = TriadicLattice.seeded(0)
        payload = cube_to_bytes(cube)

        self.assertEqual(len(payload), 512)
        self.assertEqual(bytes_to_cube(payload), cube)
        self.assertEqual(
            cube.sha256(),
            "2ba2a34b1dde358045011fbe4dc9dce0"
            "4da9f56ff34f2eec774486218bb7a6eb",
        )

    def test_cube_payload_rejects_wrong_shape_and_non_ternary_values(self) -> None:
        with self.assertRaises(ValueError):
            bytes_to_cube(cast(Any, bytearray(512)))
        with self.assertRaises(ValueError):
            bytes_to_cube(b"\x00" * 511)
        with self.assertRaises(ValueError):
            bytes_to_cube(b"\x00" * 511 + b"\x03")
        with self.assertRaises(ValueError):
            cube_to_bytes(cast(Any, object()))


class SyntheticFastaTests(unittest.TestCase):
    def test_canonical_fasta_round_trip_and_wrapping(self) -> None:
        artifact = encode_payload_storage(
            bytes(range(64)),
            label="fixture-64",
        )
        label, sequence = parse_synthetic_fasta(artifact.fasta)

        self.assertEqual(label, "fixture-64")
        self.assertEqual(sequence, artifact.dna)

        lines = artifact.fasta.splitlines()
        self.assertTrue(lines[0].startswith(">COSMO_SYNTHETIC_STORAGE_V1|"))
        for line in lines[1:-1]:
            self.assertEqual(len(line), FASTA_LINE_WIDTH)
        self.assertLessEqual(len(lines[-1]), FASTA_LINE_WIDTH)

    def test_fasta_rejects_noncanonical_or_invalid_dna(self) -> None:
        artifact = encode_payload_storage(b"abc", label="abc")

        with self.assertRaises(ValueError):
            parse_synthetic_fasta(artifact.fasta.rstrip("\n"))
        with self.assertRaises(ValueError):
            parse_synthetic_fasta(artifact.fasta.replace("alphabet=ACGT", "alphabet=DNA"))
        with self.assertRaises(ValueError):
            parse_synthetic_fasta(artifact.fasta.replace("A", "N", 1))
        with self.assertRaises(ValueError):
            render_synthetic_fasta("bad label", artifact.dna)

    def test_fasta_label_is_bound_to_artifact(self) -> None:
        artifact = encode_payload_storage(b"abc", label="abc")
        wrong = render_synthetic_fasta("other", artifact.dna)

        with self.assertRaises(ValueError):
            recover_payload_from_fasta(artifact, wrong)


class StorageArtifactTests(unittest.TestCase):
    def test_seed_zero_cube_has_stable_storage_identity(self) -> None:
        artifact = encode_cube_storage(
            TriadicLattice.seeded(0),
            label="seed-0",
        )

        self.assertEqual(artifact.payload_size, 512)
        self.assertEqual(
            artifact.payload_sha256,
            "2ba2a34b1dde358045011fbe4dc9dce0"
            "4da9f56ff34f2eec774486218bb7a6eb",
        )
        self.assertEqual(
            artifact.ecc_sha256,
            "2be07b5508b379c43912d9b853dad558"
            "ec2e9c89b0343b388047ab06c2505f3c",
        )
        self.assertEqual(
            artifact.dna_sha256,
            "3df2e0a473defda6695f2a9f57c98114"
            "fe9f2162c9c0c25af326466bda708be4",
        )
        self.assertEqual(len(artifact.dna), 4096)

    def test_direct_artifact_construction_rejects_unbound_identity(self) -> None:
        valid = encode_payload_storage(b"abc", label="abc")

        with self.assertRaises(ValueError):
            StorageArtifact(
                label=valid.label,
                payload_size=valid.payload_size,
                payload_sha256="0" * 64,
                ecc_sha256=valid.ecc_sha256,
                dna_sha256=valid.dna_sha256,
                dna=valid.dna,
                fasta=valid.fasta,
            )

    def test_empty_payload_and_bad_label_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            encode_payload_storage(b"", label="empty")
        with self.assertRaises(ValueError):
            encode_payload_storage(b"x", label="")


class IntegratedRecoveryTests(unittest.TestCase):
    def test_clean_cube_round_trip_through_full_pipeline(self) -> None:
        cube = TriadicLattice.seeded(7)
        artifact = encode_cube_storage(cube, label="cube-7")

        recovered = recover_cube_storage(artifact)
        self.assertEqual(recovered.cube, cube)
        self.assertEqual(recovered.storage.corrected_codewords, 0)
        self.assertEqual(recovered.storage.overall_parity_corrections, 0)
        self.assertTrue(recovered.storage.integrity_verified)

        from_fasta = recover_cube_from_fasta(artifact, artifact.fasta)
        self.assertEqual(from_fasta, recovered)

    def test_full_cube_recovers_one_bit_error_in_every_codeword(self) -> None:
        cube = TriadicLattice.seeded(11)
        artifact = encode_cube_storage(cube, label="dense-supported")
        codeword_count = artifact.payload_size * 2

        flips = tuple(
            DnaBitFlip(
                codeword_index=index,
                bit_index=index % 8,
            )
            for index in range(codeword_count)
        )
        corrupted = flip_encoded_bits_in_dna(artifact.dna, flips)
        recovered = recover_cube_storage(
            artifact,
            received_dna=corrupted,
        )

        self.assertEqual(recovered.cube, cube)
        self.assertEqual(
            recovered.storage.corrected_codewords,
            codeword_count,
        )

    def test_corruption_can_be_applied_at_fasta_layer(self) -> None:
        cube = TriadicLattice.seeded(5)
        artifact = encode_cube_storage(cube, label="fasta-corruption")
        corrupted_fasta = corrupt_synthetic_fasta_bits(
            artifact.fasta,
            (DnaBitFlip(3, 4),),
        )

        recovered = recover_cube_from_fasta(
            artifact,
            corrupted_fasta,
        )
        self.assertEqual(recovered.cube, cube)
        self.assertEqual(recovered.storage.corrected_codewords, 1)

    def test_all_byte_values_all_single_bit_positions_recover(self) -> None:
        for value in range(256):
            artifact = encode_payload_storage(
                bytes([value]),
                label=f"byte-{value}",
            )
            for codeword_index in (0, 1):
                for bit_index in range(8):
                    with self.subTest(
                        value=value,
                        codeword=codeword_index,
                        bit=bit_index,
                    ):
                        corrupted = flip_encoded_bit_in_dna(
                            artifact.dna,
                            codeword_index,
                            bit_index,
                        )
                        recovered = recover_payload_storage(
                            artifact,
                            received_dna=corrupted,
                        )
                        self.assertEqual(
                            recovered.payload,
                            bytes([value]),
                        )
                        self.assertEqual(
                            recovered.corrected_codewords,
                            1,
                        )

    def test_every_double_bit_pair_in_one_codeword_is_detected(self) -> None:
        for nibble in range(16):
            artifact = encode_payload_storage(
                bytes([nibble << 4]),
                label=f"nibble-{nibble}",
            )
            for first, second in combinations(range(8), 2):
                with self.subTest(
                    nibble=nibble,
                    first=first,
                    second=second,
                ):
                    corrupted = flip_encoded_bits_in_dna(
                        artifact.dna,
                        (
                            DnaBitFlip(0, first),
                            DnaBitFlip(0, second),
                        ),
                    )
                    with self.assertRaises(UncorrectableECCError):
                        recover_payload_storage(
                            artifact,
                            received_dna=corrupted,
                        )

    def test_sha256_catches_triple_bit_miscorrection(self) -> None:
        artifact = encode_payload_storage(b"\x00", label="triple")
        corrupted = flip_encoded_bits_in_dna(
            artifact.dna,
            (
                DnaBitFlip(0, 0),
                DnaBitFlip(0, 1),
                DnaBitFlip(0, 2),
            ),
        )

        with self.assertRaises(StorageIntegrityError):
            recover_payload_storage(
                artifact,
                received_dna=corrupted,
            )

    def test_invalid_dna_fails_before_ecc_recovery(self) -> None:
        artifact = encode_payload_storage(b"abc", label="invalid-dna")

        with self.assertRaises(ValueError):
            recover_payload_storage(
                artifact,
                received_dna=artifact.dna[:-1] + "N",
            )
        with self.assertRaises(ValueError):
            recover_payload_storage(
                artifact,
                received_dna=artifact.dna[:-4],
            )


class CorruptionInputTests(unittest.TestCase):
    def test_duplicate_or_out_of_range_flips_are_rejected(self) -> None:
        artifact = encode_payload_storage(b"x", label="flip-validation")

        with self.assertRaises(ValueError):
            flip_encoded_bits_in_dna(
                artifact.dna,
                (
                    DnaBitFlip(0, 0),
                    DnaBitFlip(0, 0),
                ),
            )
        with self.assertRaises(ValueError):
            flip_encoded_bits_in_dna(
                artifact.dna,
                (DnaBitFlip(99, 0),),
            )
        with self.assertRaises(ValueError):
            flip_encoded_bits_in_dna(
                artifact.dna,
                cast(Any, [DnaBitFlip(0, 0)]),
            )


if __name__ == "__main__":
    unittest.main()
