#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic computational core for the COSMO symbolic framework.

This module intentionally separates executable arithmetic from the project's
symbolic and interpretive layer.  The functions below establish only the
computations they perform; they do not establish physical, biomedical,
archaeological, or cosmological claims.

Author  : Cosmovirus Formalization Project
License : MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

PHI: float = 1.618_033_988_749_894_848_204_586_834_365_638_117_720
PENTAGON_SEED: int = 0b101  # 5
DECLARED_SYMBOLIC_INVARIANT: int = 1621


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
    """Executable representation of the COSMO Dragon Seed payload.

    The stored payload is exactly eight bytes (64 bits). ``101`` is retained as
    a project mnemonic for the surrounding symbolic loop; it is not a claim
    that this object stores 101 bits.
    """

    strand: bytes = field(
        default_factory=lambda: bytes(
            (0xB7, 0xBA, 0xBE, 0xFF, 0xD6, 0xE5, 0xAA, 0x55)
        )
    )

    byte_labels: tuple[str, ...] = (
        "AN",
        "KI",
        "EN.KI",
        "DIGIR",
        "SI.SI",
        "E2",
        "ZU",
        "UR",
    )

    cuneiform_table: dict[int, tuple[str, str]] = field(
        default_factory=lambda: {
            0xB7: ("AN", "sky / heaven god"),
            0xBA: ("KI", "earth"),
            0xBE: ("EN.KI", "lord of the earth / waters"),
            0xFF: ("DIGIR", "divine determinative marker"),
            0xD6: ("SI.SI", "dragon seed"),
            0xE5: ("E2", "house / temple"),
            0xAA: ("ZU", "knowledge / to know"),
            0x55: ("UR", "dog / watchman"),
        }
    )

    def phi_power(self, n: int) -> float:
        """Return the floating-point approximation ``PHI ** n``."""
        return PHI**n

    @staticmethod
    def _lucas(n: int) -> int:
        """Return the n-th Lucas number for ``n >= 0``."""
        if n < 0:
            raise ValueError("Lucas index must be non-negative")
        a, b = 2, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    @classmethod
    def phi_floor_integer(cls, n: int) -> int:
        """Return ``floor(phi**n)`` for a non-negative integer exponent.

        The implementation uses the exact Lucas-number parity identity:

        * n = 0: floor(phi^0) = 1
        * odd n > 0: floor(phi^n) = L_n
        * even n > 0: floor(phi^n) = L_n - 1
        """
        if n < 0:
            raise ValueError("phi_floor_integer requires n >= 0")
        if n == 0:
            return 1
        lucas = cls._lucas(n)
        return lucas if n % 2 == 1 else lucas - 1

    @classmethod
    def phi_floor_modulo(cls, n: int, mod: int = 256) -> int:
        """Return ``floor(phi**n) % mod`` using exact integer arithmetic."""
        if mod <= 0:
            raise ValueError("modulus must be positive")
        return cls.phi_floor_integer(n) % mod

    def declared_symbolic_invariant(self) -> int:
        """Return the project-declared symbolic invariant ``1621``.

        This value is intentionally not called a checksum because it is not
        derived from the stored payload and therefore cannot detect mutation.
        """
        return DECLARED_SYMBOLIC_INVARIANT

    def byte_sum(self) -> int:
        """Return the arithmetic sum of the eight payload bytes."""
        return sum(self.strand)

    def payload_bit_length(self) -> int:
        """Return the represented payload length in bits."""
        return 8 * len(self.strand)

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
        if len(seq) < 3:
            raise ValueError("diag_operator requires at least 3 elements")
        return [
            seq[i - 1] - 2.0 * seq[i] + seq[i + 1]
            for i in range(1, len(seq) - 1)
        ]

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
