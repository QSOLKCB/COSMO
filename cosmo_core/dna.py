"""Strict deterministic byte <-> DNA alphabet conversion."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

_BITS_TO_BASE: Final[tuple[str, str, str, str]] = ("A", "C", "G", "T")
_BASE_TO_BITS: Final[Mapping[str, int]] = MappingProxyType(
    {"A": 0, "C": 1, "G": 2, "T": 3}
)


def bytes_to_dna(data: bytes) -> str:
    """Encode bytes using ``00=A, 01=C, 10=G, 11=T``."""
    return "".join(
        _BITS_TO_BASE[(value >> shift) & 0b11]
        for value in data
        for shift in (6, 4, 2, 0)
    )


def dna_to_bytes(sequence: str) -> bytes:
    """Decode a strict uppercase A/C/G/T sequence into bytes.

    Lowercase letters, whitespace and all non-ACGT symbols are rejected rather
    than normalized or silently coerced.
    """
    if len(sequence) % 4 != 0:
        raise ValueError("DNA sequence length must be a multiple of 4")

    values: list[int] = []
    for index, base in enumerate(sequence):
        try:
            values.append(_BASE_TO_BITS[base])
        except KeyError as exc:
            raise ValueError(
                f"invalid DNA symbol {base!r} at index {index}"
            ) from exc

    out = bytearray()
    for index in range(0, len(values), 4):
        value = (
            (values[index] << 6)
            | (values[index + 1] << 4)
            | (values[index + 2] << 2)
            | values[index + 3]
        )
        out.append(value)
    return bytes(out)
