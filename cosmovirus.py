#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility-facing executable mirror for the COSMO symbolic framework.

The reusable deterministic arithmetic, payload, ECC, DNA, integrity, and
manifest primitives live in :mod:`cosmo_core`. This module retains the
historical ``CosmoBit101`` surface and demonstration entry point.

The executable code establishes only the computations it performs; it does not
establish physical, biomedical, archaeological, or cosmological claims.

Author  : Cosmovirus Formalization Project
License : MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from cosmo_core import (
    BYTE_LABELS,
    CUNEIFORM_TABLE,
    DECLARED_SYMBOLIC_INVARIANT as DECLARED_SYMBOLIC_INVARIANT,
    DRAGON_SEED,
    GOLDEN_RATIO,
    PENTAGON_SEED as PENTAGON_SEED,
    lucas,
    payload_bit_length,
    payload_byte_sum,
    phi_floor_integer,
    phi_floor_modulo,
    phi_power_approx,
    second_difference,
)

PHI: float = GOLDEN_RATIO


class DecodedByte(TypedDict):
    """Structured symbolic annotation of one payload byte."""

    index: int
    binary: str
    hex: str
    decimal: int
    cuneiform: str
    description: str


@dataclass
class CosmoBit101:
    """Executable representation of the COSMO Dragon Seed payload."""

    strand: bytes = DRAGON_SEED
    byte_labels: tuple[str, ...] = BYTE_LABELS
    cuneiform_table: dict[int, tuple[str, str]] = field(
        default_factory=lambda: dict(CUNEIFORM_TABLE)
    )

    def phi_power(self, n: int) -> float:
        """Return the floating-point approximation ``PHI ** n``."""
        return phi_power_approx(n)

    @staticmethod
    def _lucas(n: int) -> int:
        """Return the n-th Lucas number for ``n >= 0``."""
        return lucas(n)

    @classmethod
    def phi_floor_integer(cls, n: int) -> int:
        """Return ``floor(phi**n)`` for a non-negative integer exponent."""
        return phi_floor_integer(n)

    @classmethod
    def phi_floor_modulo(cls, n: int, mod: int = 256) -> int:
        """Return ``floor(phi**n) % mod`` using exact integer arithmetic."""
        return phi_floor_modulo(n, mod)

    def declared_symbolic_invariant(self) -> int:
        """Return the project-declared symbolic invariant ``1621``."""
        return DECLARED_SYMBOLIC_INVARIANT

    def byte_sum(self) -> int:
        """Return the arithmetic sum of the eight payload bytes."""
        return payload_byte_sum(self.strand)

    def payload_bit_length(self) -> int:
        """Return the represented payload length in bits."""
        return payload_bit_length(self.strand)

    def cuneiform_lookup(self, byte_val: int) -> str:
        """Return the project-defined symbolic sign annotation for a byte."""
        sign, _gloss = self.cuneiform_table.get(byte_val, ("?", "unknown"))
        return sign

    def decode(self) -> list[DecodedByte]:
        """Return the payload plus its project-defined symbolic annotations."""
        out: list[DecodedByte] = []
        for i, b in enumerate(self.strand):
            sign, gloss = self.cuneiform_table.get(b, ("?", "unknown"))
            out.append(
                DecodedByte(
                    index=i,
                    binary=format(b, "08b"),
                    hex=f"0x{b:02X}",
                    decimal=b,
                    cuneiform=sign,
                    description=gloss,
                )
            )
        return out

    @staticmethod
    def diag_operator(seq: list[float]) -> list[float]:
        """Apply the ``(1, -2, 1)`` discrete second-difference stencil."""
        return second_difference(seq)

    def ouroboros_iterate(self, n: int, start: int = PENTAGON_SEED) -> list[int]:
        """Iterate ``x[k+1] = x[k] + 75 (mod 256)`` for ``n`` steps."""
        if n < 0:
            raise ValueError("iteration count must be non-negative")
        step = self.phi_floor_modulo(101, 256)
        trajectory = [start % 256]
        for _ in range(n):
            trajectory.append((trajectory[-1] + step) % 256)
        return trajectory

    def __repr__(self) -> str:
        return (
            f"CosmoBit101(strand={self.strand!r}, "
            f"declared_symbolic_invariant={self.declared_symbolic_invariant()})"
        )

    def __str__(self) -> str:
        hexes = " ".join(f"0x{b:02X}" for b in self.strand)
        signs = " ".join(self.cuneiform_lookup(b) for b in self.strand)
        return (
            "COSMO Dragon Seed payload\n"
            f"  bytes     : {hexes}\n"
            f"  bits      : {self.payload_bit_length()}\n"
            f"  annotations: {signs}\n"
            f"  invariant : {self.declared_symbolic_invariant()} (declared symbolic value)"
        )


def _demo() -> None:
    cosmo = CosmoBit101()
    print("=" * 66)
    print("  COSMO deterministic computational core")
    print("=" * 66)
    print(cosmo)

    print("\n--- golden-ratio arithmetic ---")
    for n in (1, 2, 5, 10, 101):
        print(f"  phi^{n:<3} ~= {cosmo.phi_power(n):.6e}")
    print(f"  L_101                    = {cosmo._lucas(101)}")
    print(f"  floor(phi^101) mod 256   = {cosmo.phi_floor_modulo(101)}")

    print("\n--- payload invariants ---")
    print(f"  payload bits             = {cosmo.payload_bit_length()}")
    print(f"  raw byte sum             = {cosmo.byte_sum()}")
    print(f"  declared symbolic value  = {cosmo.declared_symbolic_invariant()}")

    print("\n--- DIAG ---")
    ramp = [1.0, 2.0, 3.0, 4.0, 5.0]
    print(f"  linear ramp -> {cosmo.diag_operator(ramp)}")

    print("\n--- modular iteration ---")
    print(f"  trajectory -> {cosmo.ouroboros_iterate(5)}")


if __name__ == "__main__":
    _demo()
