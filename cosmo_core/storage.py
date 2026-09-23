"""Strict deterministic storage pipeline for COSMO Phase B5.

The authoritative cube state is the Phase B4 TriadicLattice. Its 512 ternary
cells serialize as one byte per trit, then pass through the Phase B2 SECDED and
strict A/C/G/T codecs:

    cube -> bytes -> SECDED -> ACGT -> corruption -> SECDED recovery -> bytes -> cube

SHA-256 authenticates recovered content; it is not used for error correction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from string import ascii_letters, digits
from typing import Final

from .dna import bytes_to_dna, dna_to_bytes
from .ecc import SecdedDecodeResult, secded_decode, secded_encode
from .integrity import sha256_hex
from .triadic import LATTICE_SIZE, TriadicLattice

STORAGE_SCHEMA: Final[str] = "COSMO-STORAGE-B5-1"
RECOVERY_SCHEMA: Final[str] = "COSMO-STORAGE-RECOVERY-B5-1"
FASTA_PREFIX: Final[str] = "COSMO_SYNTHETIC_STORAGE_V1"
FASTA_LINE_WIDTH: Final[int] = 80
FASTA_ECC_LABEL: Final[str] = "SECDED-8-4-4"
_LABEL_CHARACTERS: Final[frozenset[str]] = frozenset(
    ascii_letters + digits + "._-"
)


class StorageIntegrityError(ValueError):
    """Raised when recovered bytes do not match the bound payload identity."""


@dataclass(frozen=True)
class DnaBitFlip:
    """One exact encoded-bit corruption inside the A/C/G/T artifact."""

    codeword_index: int
    bit_index: int

    def __post_init__(self) -> None:
        if (
            type(self.codeword_index) is not int
            or self.codeword_index < 0
        ):
            raise ValueError("codeword_index must be a non-negative integer")
        if (
            type(self.bit_index) is not int
            or not 0 <= self.bit_index < 8
        ):
            raise ValueError("bit_index must be an integer in range 0..7")


def _validate_label(label: object) -> str:
    if (
        not isinstance(label, str)
        or not 1 <= len(label) <= 64
        or any(character not in _LABEL_CHARACTERS for character in label)
    ):
        raise ValueError(
            "storage label must be 1..64 ASCII letters, digits, '.', '_' or '-'"
        )
    return label


def _validate_sha256(digest: object, label: str) -> str:
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")
    return digest


def _dna_sha256(sequence: str) -> str:
    return sha256_hex(sequence.encode("ascii"))


def cube_to_bytes(cube: TriadicLattice) -> bytes:
    """Serialize the canonical B4 cube as one byte per ternary cell."""
    if not isinstance(cube, TriadicLattice):
        raise ValueError("cube must be a TriadicLattice")
    return bytes(cube.cells)


def bytes_to_cube(payload: bytes) -> TriadicLattice:
    """Decode canonical cube bytes, rejecting malformed or non-ternary data."""
    if type(payload) is not bytes:
        raise ValueError("cube payload must be immutable bytes")
    if len(payload) != LATTICE_SIZE:
        raise ValueError(
            f"cube payload must contain exactly {LATTICE_SIZE} bytes"
        )
    if any(value not in (0, 1, 2) for value in payload):
        raise ValueError("cube payload contains a non-ternary cell value")
    return TriadicLattice(tuple(payload))


def render_synthetic_fasta(label: str, sequence: str) -> str:
    """Render the canonical explicitly synthetic FASTA representation."""
    exact_label = _validate_label(label)
    if not isinstance(sequence, str) or not sequence:
        raise ValueError("DNA sequence must be a non-empty string")
    dna_to_bytes(sequence)

    header = (
        f">{FASTA_PREFIX}|label={exact_label}|alphabet=ACGT|"
        f"ecc={FASTA_ECC_LABEL}"
    )
    lines = [
        sequence[index : index + FASTA_LINE_WIDTH]
        for index in range(0, len(sequence), FASTA_LINE_WIDTH)
    ]
    return header + "\n" + "\n".join(lines) + "\n"


def parse_synthetic_fasta(document: str) -> tuple[str, str]:
    """Parse only the canonical synthetic FASTA format emitted by this module."""
    if not isinstance(document, str) or not document.endswith("\n"):
        raise ValueError("synthetic FASTA must be a newline-terminated string")
    if "\r" in document:
        raise ValueError("synthetic FASTA must use LF line endings")

    lines = document.splitlines()
    if len(lines) < 2:
        raise ValueError("synthetic FASTA must contain a header and sequence")

    expected_prefix = f">{FASTA_PREFIX}|label="
    header = lines[0]
    if not header.startswith(expected_prefix):
        raise ValueError("synthetic FASTA header is invalid")

    suffix = f"|alphabet=ACGT|ecc={FASTA_ECC_LABEL}"
    if not header.endswith(suffix):
        raise ValueError("synthetic FASTA codec metadata is invalid")

    label = header[len(expected_prefix) : -len(suffix)]
    exact_label = _validate_label(label)

    data_lines = lines[1:]
    if any(not line for line in data_lines):
        raise ValueError("synthetic FASTA sequence lines must not be empty")
    if any(
        len(line) != FASTA_LINE_WIDTH
        for line in data_lines[:-1]
    ):
        raise ValueError("synthetic FASTA line wrapping is non-canonical")
    if not 1 <= len(data_lines[-1]) <= FASTA_LINE_WIDTH:
        raise ValueError("synthetic FASTA final sequence line is invalid")

    sequence = "".join(data_lines)
    dna_to_bytes(sequence)

    if render_synthetic_fasta(exact_label, sequence) != document:
        raise ValueError("synthetic FASTA is not in canonical form")
    return exact_label, sequence


@dataclass(frozen=True)
class StorageArtifact:
    """Immutable canonical encoded storage artifact."""

    label: str
    payload_size: int
    payload_sha256: str
    ecc_sha256: str
    dna_sha256: str
    dna: str
    fasta: str
    schema: str = field(default=STORAGE_SCHEMA, init=False)

    def __post_init__(self) -> None:
        exact_label = _validate_label(self.label)
        if (
            type(self.payload_size) is not int
            or self.payload_size <= 0
        ):
            raise ValueError("payload_size must be a positive integer")

        payload_digest = _validate_sha256(
            self.payload_sha256,
            "payload_sha256",
        )
        ecc_digest = _validate_sha256(self.ecc_sha256, "ecc_sha256")
        dna_digest = _validate_sha256(self.dna_sha256, "dna_sha256")

        if not isinstance(self.dna, str) or not self.dna:
            raise ValueError("dna must be a non-empty string")

        encoded = dna_to_bytes(self.dna)
        if len(encoded) != self.payload_size * 2:
            raise ValueError("DNA/ECC length does not match payload_size")
        if sha256_hex(encoded) != ecc_digest:
            raise ValueError("ecc_sha256 does not match encoded bytes")
        if _dna_sha256(self.dna) != dna_digest:
            raise ValueError("dna_sha256 does not match DNA sequence")

        decoded = secded_decode(encoded)
        if (
            decoded.corrected_codewords != 0
            or decoded.overall_parity_corrections != 0
        ):
            raise ValueError("canonical storage artifact must contain clean ECC")
        if len(decoded.data) != self.payload_size:
            raise ValueError("decoded payload length does not match payload_size")
        if sha256_hex(decoded.data) != payload_digest:
            raise ValueError("payload_sha256 does not match decoded payload")
        if secded_encode(decoded.data) != encoded:
            raise ValueError("storage artifact ECC is not canonical")

        expected_fasta = render_synthetic_fasta(exact_label, self.dna)
        if self.fasta != expected_fasta:
            raise ValueError("fasta does not match canonical synthetic FASTA")


@dataclass(frozen=True)
class StorageRecoveryResult:
    """Recovered payload plus ECC and integrity evidence."""

    payload: bytes
    source_payload_sha256: str
    received_dna_sha256: str
    recovered_payload_sha256: str
    corrected_codewords: int
    overall_parity_corrections: int
    integrity_verified: bool
    schema: str = field(default=RECOVERY_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if type(self.payload) is not bytes or not self.payload:
            raise ValueError("recovered payload must be non-empty bytes")
        source_digest = _validate_sha256(
            self.source_payload_sha256,
            "source_payload_sha256",
        )
        _validate_sha256(self.received_dna_sha256, "received_dna_sha256")
        recovered_digest = _validate_sha256(
            self.recovered_payload_sha256,
            "recovered_payload_sha256",
        )
        for label, value in (
            ("corrected_codewords", self.corrected_codewords),
            ("overall_parity_corrections", self.overall_parity_corrections),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")
        if self.integrity_verified is not True:
            raise ValueError("successful recovery must have verified integrity")
        if sha256_hex(self.payload) != recovered_digest:
            raise ValueError("recovered_payload_sha256 does not match payload")
        if source_digest != recovered_digest:
            raise ValueError("successful recovery must match source payload identity")


@dataclass(frozen=True)
class CubeStorageRecovery:
    """Recovered authoritative cube plus the underlying storage receipt."""

    cube: TriadicLattice
    storage: StorageRecoveryResult

    def __post_init__(self) -> None:
        if cube_to_bytes(self.cube) != self.storage.payload:
            raise ValueError("recovered cube does not match storage payload")


def encode_payload_storage(
    payload: bytes,
    *,
    label: str,
) -> StorageArtifact:
    """Encode immutable bytes through SECDED, A/C/G/T and synthetic FASTA."""
    if type(payload) is not bytes or not payload:
        raise ValueError("storage payload must be non-empty immutable bytes")
    exact_label = _validate_label(label)

    encoded = secded_encode(payload)
    dna = bytes_to_dna(encoded)
    fasta = render_synthetic_fasta(exact_label, dna)
    return StorageArtifact(
        label=exact_label,
        payload_size=len(payload),
        payload_sha256=sha256_hex(payload),
        ecc_sha256=sha256_hex(encoded),
        dna_sha256=_dna_sha256(dna),
        dna=dna,
        fasta=fasta,
    )


def encode_cube_storage(
    cube: TriadicLattice,
    *,
    label: str = "triadic-cube",
) -> StorageArtifact:
    """Encode the authoritative Phase B4 cube into the B5 storage artifact."""
    return encode_payload_storage(cube_to_bytes(cube), label=label)


def flip_encoded_bits_in_dna(
    sequence: str,
    flips: tuple[DnaBitFlip, ...],
) -> str:
    """Apply exact bit flips to SECDED codewords while staying in A/C/G/T form."""
    if not isinstance(flips, tuple) or not flips:
        raise ValueError("flips must be a non-empty immutable tuple")
    if any(not isinstance(flip, DnaBitFlip) for flip in flips):
        raise ValueError("every corruption entry must be DnaBitFlip")

    encoded = bytearray(dna_to_bytes(sequence))
    seen: set[tuple[int, int]] = set()

    for flip in flips:
        key = (flip.codeword_index, flip.bit_index)
        if key in seen:
            raise ValueError("duplicate bit flips are not canonical corruption input")
        seen.add(key)
        if flip.codeword_index >= len(encoded):
            raise ValueError("codeword_index is outside the encoded payload")
        encoded[flip.codeword_index] ^= 1 << flip.bit_index

    return bytes_to_dna(bytes(encoded))


def flip_encoded_bit_in_dna(
    sequence: str,
    codeword_index: int,
    bit_index: int,
) -> str:
    """Convenience wrapper for one exact encoded-bit corruption."""
    return flip_encoded_bits_in_dna(
        sequence,
        (DnaBitFlip(codeword_index, bit_index),),
    )


def corrupt_synthetic_fasta_bits(
    document: str,
    flips: tuple[DnaBitFlip, ...],
) -> str:
    """Apply exact encoded-bit corruption to a canonical synthetic FASTA."""
    label, sequence = parse_synthetic_fasta(document)
    corrupted = flip_encoded_bits_in_dna(sequence, flips)
    return render_synthetic_fasta(label, corrupted)


def _decode_and_verify(
    artifact: StorageArtifact,
    received_dna: str,
) -> tuple[SecdedDecodeResult, str]:
    if not isinstance(artifact, StorageArtifact):
        raise ValueError("artifact must be a StorageArtifact")
    if not isinstance(received_dna, str) or not received_dna:
        raise ValueError("received_dna must be a non-empty string")

    encoded = dna_to_bytes(received_dna)
    if len(encoded) != artifact.payload_size * 2:
        raise ValueError("received DNA length does not match storage artifact")

    decoded = secded_decode(encoded)
    if len(decoded.data) != artifact.payload_size:
        raise ValueError("recovered payload length does not match storage artifact")

    recovered_digest = sha256_hex(decoded.data)
    if recovered_digest != artifact.payload_sha256:
        raise StorageIntegrityError(
            "ECC completed but recovered payload failed SHA-256 integrity"
        )
    return decoded, recovered_digest


def recover_payload_storage(
    artifact: StorageArtifact,
    *,
    received_dna: str | None = None,
) -> StorageRecoveryResult:
    """Recover bytes and require SHA-256 identity after ECC decoding."""
    sequence = artifact.dna if received_dna is None else received_dna
    decoded, recovered_digest = _decode_and_verify(artifact, sequence)

    return StorageRecoveryResult(
        payload=decoded.data,
        source_payload_sha256=artifact.payload_sha256,
        received_dna_sha256=_dna_sha256(sequence),
        recovered_payload_sha256=recovered_digest,
        corrected_codewords=decoded.corrected_codewords,
        overall_parity_corrections=decoded.overall_parity_corrections,
        integrity_verified=True,
    )


def recover_payload_from_fasta(
    artifact: StorageArtifact,
    document: str,
) -> StorageRecoveryResult:
    """Recover payload from canonical synthetic FASTA."""
    label, sequence = parse_synthetic_fasta(document)
    if label != artifact.label:
        raise ValueError("synthetic FASTA label does not match storage artifact")
    return recover_payload_storage(artifact, received_dna=sequence)


def recover_cube_storage(
    artifact: StorageArtifact,
    *,
    received_dna: str | None = None,
) -> CubeStorageRecovery:
    """Recover the authoritative Phase B4 cube from the B5 storage pipeline."""
    storage = recover_payload_storage(artifact, received_dna=received_dna)
    cube = bytes_to_cube(storage.payload)
    return CubeStorageRecovery(cube=cube, storage=storage)


def recover_cube_from_fasta(
    artifact: StorageArtifact,
    document: str,
) -> CubeStorageRecovery:
    """Recover the authoritative cube from canonical synthetic FASTA."""
    storage = recover_payload_from_fasta(artifact, document)
    cube = bytes_to_cube(storage.payload)
    return CubeStorageRecovery(cube=cube, storage=storage)
