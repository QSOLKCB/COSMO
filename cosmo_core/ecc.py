"""Extended Hamming SECDED codec for deterministic COSMO payloads.

Each four-bit nibble is encoded as one extended Hamming (8, 4, 4) codeword.
A byte therefore expands to two codewords, high nibble first.

The decoder corrects one flipped bit per codeword and detects every two-bit
error per codeword. Errors beyond that documented capability are not claimed
to be detectable or correctable.
"""

from __future__ import annotations

from dataclasses import dataclass


class UncorrectableECCError(ValueError):
    """Raised when a SECDED codeword contains a detected multi-bit error."""


@dataclass(frozen=True)
class CodewordDecodeResult:
    """Decoded nibble and correction metadata for one codeword."""

    nibble: int
    corrected: bool
    overall_parity_only: bool


@dataclass(frozen=True)
class SecdedDecodeResult:
    """Decoded byte payload plus aggregate correction metadata."""

    data: bytes
    corrected_codewords: int
    overall_parity_corrections: int


_DATA_POSITIONS = (3, 5, 6, 7)
_PARITY_POSITIONS = (1, 2, 4)


def encode_nibble(nibble: int) -> int:
    """Encode one 4-bit value as an extended Hamming (8, 4, 4) codeword."""
    if not 0 <= nibble <= 0x0F:
        raise ValueError("nibble must be in range 0..15")

    bits = [0] * 9
    for source_bit, position in enumerate(_DATA_POSITIONS):
        bits[position] = (nibble >> source_bit) & 1

    for parity_position in _PARITY_POSITIONS:
        parity = 0
        for position in range(1, 8):
            if position & parity_position:
                parity ^= bits[position]
        bits[parity_position] = parity

    overall = 0
    for position in range(1, 8):
        overall ^= bits[position]
    bits[8] = overall

    codeword = 0
    for position in range(1, 9):
        codeword |= bits[position] << (position - 1)
    return codeword


def decode_codeword(codeword: int) -> CodewordDecodeResult:
    """Decode one SECDED codeword, correcting at most one flipped bit."""
    if not 0 <= codeword <= 0xFF:
        raise ValueError("codeword must be in range 0..255")

    bits = [0] * 9
    for position in range(1, 9):
        bits[position] = (codeword >> (position - 1)) & 1

    syndrome = 0
    for parity_position in _PARITY_POSITIONS:
        parity = 0
        for position in range(1, 8):
            if position & parity_position:
                parity ^= bits[position]
        if parity:
            syndrome |= parity_position

    overall = 0
    for position in range(1, 9):
        overall ^= bits[position]

    corrected = False
    overall_parity_only = False

    if syndrome != 0 and overall == 1:
        bits[syndrome] ^= 1
        corrected = True
    elif syndrome == 0 and overall == 1:
        bits[8] ^= 1
        corrected = True
        overall_parity_only = True
    elif syndrome != 0 and overall == 0:
        raise UncorrectableECCError(
            f"detected uncorrectable SECDED error with syndrome {syndrome}"
        )

    nibble = 0
    for target_bit, position in enumerate(_DATA_POSITIONS):
        nibble |= bits[position] << target_bit

    return CodewordDecodeResult(
        nibble=nibble,
        corrected=corrected,
        overall_parity_only=overall_parity_only,
    )


def secded_encode(data: bytes) -> bytes:
    """Encode bytes as high-nibble/low-nibble SECDED codewords."""
    out = bytearray()
    for value in data:
        out.append(encode_nibble(value >> 4))
        out.append(encode_nibble(value & 0x0F))
    return bytes(out)


def secded_decode(encoded: bytes) -> SecdedDecodeResult:
    """Decode SECDED codewords and return correction metadata."""
    if len(encoded) % 2 != 0:
        raise ValueError("encoded SECDED payload length must be even")

    decoded = bytearray()
    corrected_codewords = 0
    overall_parity_corrections = 0

    for index in range(0, len(encoded), 2):
        high = decode_codeword(encoded[index])
        low = decode_codeword(encoded[index + 1])
        decoded.append((high.nibble << 4) | low.nibble)

        for result in (high, low):
            corrected_codewords += int(result.corrected)
            overall_parity_corrections += int(result.overall_parity_only)

    return SecdedDecodeResult(
        data=bytes(decoded),
        corrected_codewords=corrected_codewords,
        overall_parity_corrections=overall_parity_corrections,
    )
