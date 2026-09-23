"""Payload measurement and integrity semantics."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import DECLARED_SYMBOLIC_INVARIANT
from .integrity import sha256_hex


@dataclass(frozen=True)
class PayloadFacts:
    """Deterministic measurements of a payload.

    ``declared_symbolic_invariant`` is intentionally separate from the byte
    sum and SHA-256 digest because it is not derived from payload bytes.
    """

    bit_length: int
    byte_sum: int
    declared_symbolic_invariant: int
    sha256: str


def payload_bit_length(data: bytes) -> int:
    """Return the represented payload length in bits."""
    return len(data) * 8


def payload_byte_sum(data: bytes) -> int:
    """Return the arithmetic sum of the payload bytes."""
    return sum(data)


def payload_facts(data: bytes) -> PayloadFacts:
    """Return canonical deterministic measurements for ``data``."""
    return PayloadFacts(
        bit_length=payload_bit_length(data),
        byte_sum=payload_byte_sum(data),
        declared_symbolic_invariant=DECLARED_SYMBOLIC_INVARIANT,
        sha256=sha256_hex(data),
    )
