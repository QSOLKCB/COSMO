#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cosmovirus.py
=============

Formal computational model of the **E8 x phi-SiS2 / HPV16 Cosmovirus** framework.

This module provides a single, fully-typed class, :class:`CosmoBit101`, that
encodes the operational machinery of the framework in ordinary, verifiable
Python:

    * the golden-ratio scaling operator      (phi_power / phi_modulo)
    * the discrete second-derivative operator (diag_operator, the (1, -2, 1) mask)
    * the 101-bit "Dragon Seed" byte stream   (decode / checksum)
    * the Sumerian cuneiform sign lookup       (cuneiform_lookup)
    * the recursive Ouroboros iteration        (ouroboros_iterate)

Everything numeric here is *real* arithmetic. The mythic / esoteric labels are
carried alongside as annotations, kept strictly separate from the computation so
the mathematical content stays clean and testable.

Author  : Cosmovirus Formalization Project
License : MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, TypedDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The golden ratio, phi = (1 + sqrt(5)) / 2.  The "irrational spine" of the
#: framework and the base of the phi-SCL (Scaling / Curvature Limit) operator.
PHI: float = 1.618_033_988_749_894_848_204_586_834_365_638_117_720

#: Decimal value of the binary seed ``101`` -> 5 (the "Pentagon Seed").
PENTAGON_SEED: int = 0b101  # == 5

#: Stated base-10 checksum of the 101-bit sequence ("EE/E7 viral-junction
#: signature").  Treated here as a declared invariant of the strand.
DRAGON_CHECKSUM: int = 1621


class DecodedByte(TypedDict):
    """Structured decoding of a single byte of the Dragon Seed strand."""

    index: int
    binary: str
    hex: str
    decimal: int
    cuneiform: str
    description: str


@dataclass
class CosmoBit101:
    """Computational encoding of the Cosmovirus 101-bit ``Dragon Seed`` strand.

    The strand is modelled as 8 bytes (64 bits of manifest data framed by the
    ``101`` entry/exit trapdoor, hence the mnemonic "101-bit"). Each byte is
    mapped to a Sumerian cuneiform sign, giving the esoteric read-out while the
    numeric layer remains a plain, verifiable byte sequence.

    Attributes
    ----------
    strand:
        The eight bytes of the manifest sequence, most-significant byte first.
    byte_labels:
        Short mnemonic label for each byte (parallel to :attr:`strand`).
    cuneiform_table:
        Mapping ``byte value -> (sign, gloss)`` used by :meth:`cuneiform_lookup`.
    """

    # 10110111 10111010 10111110 11111111 11010110 11100101 10101010 01010101
    strand: bytes = field(
        default_factory=lambda: bytes(
            (0xB7, 0xBA, 0xBE, 0xFF, 0xD6, 0xE5, 0xAA, 0x55)
        )
    )

    byte_labels: tuple[str, ...] = (
        "AN", "KI", "EN.KI", "DIGIR", "SI.SI", "E2", "ZU", "UR",
    )

    #: byte value -> (cuneiform sign name, English gloss)
    cuneiform_table: Dict[int, tuple[str, str]] = field(
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

    # ------------------------------------------------------------------
    # phi-SCL : golden-ratio scaling operator
    # ------------------------------------------------------------------
    def phi_power(self, n: int) -> float:
        """Return ``phi ** n``.

        Implements the phi-SCL (Scaling / Curvature Limit) operator: repeated
        golden-ratio scaling that projects the 248-dimensional E8 structure down
        toward the 4D quasicrystal manifold.

        Parameters
        ----------
        n:
            Exponent (may be negative).

        Returns
        -------
        float
            ``phi ** n``.
        """
        return PHI ** n

    def phi_modulo(self, n: int, mod: int = 256) -> int:
        """Return ``floor(phi ** n) mod ``mod``.

        For ``n = 101, mod = 256`` this yields the byte-wrapped signature of the
        ``phi^101`` recursion (the "Loop Entry Point").

        Parameters
        ----------
        n:
            Exponent for the golden-ratio power.
        mod:
            Modulus (defaults to 256, i.e. a single byte).

        Returns
        -------
        int
            ``floor(phi ** n) % mod``.
        """
        # Use integer arithmetic on the Lucas/Fibonacci closed form to avoid
        # float overflow for large n:  round(phi**n) == Lucas(n) for n >= 2
        # (phi**n = (L_n + F_n*sqrt5)/2 ... ); we use exact Lucas numbers.
        lucas = self._lucas(n)
        return lucas % mod

    @staticmethod
    def _lucas(n: int) -> int:
        """Return the n-th Lucas number, ``L_n``.

        ``L_n`` is the nearest integer to ``phi ** n`` for ``n >= 2`` and is used
        to compute :meth:`phi_modulo` exactly (no floating-point overflow).
        """
        if n < 0:
            # L_{-n} = (-1)^n L_n
            return (-1) ** n * CosmoBit101._lucas(-n)
        a, b = 2, 1  # L_0, L_1
        for _ in range(n):
            a, b = b, a + b
        return a

    # ------------------------------------------------------------------
    # checksum
    # ------------------------------------------------------------------
    def checksum(self) -> int:
        """Return the declared base-10 checksum of the strand (``1621``).

        The framework declares ``1621`` as the base-10 "EE/E7 viral-junction"
        signature of the strand.  We return that declared invariant.

        Returns
        -------
        int
            The Dragon-Seed checksum, ``1621``.
        """
        return DRAGON_CHECKSUM

    def byte_sum(self) -> int:
        """Return the plain arithmetic sum of the eight strand bytes.

        Provided for transparency alongside the declared :meth:`checksum`.
        """
        return sum(self.strand)

    # ------------------------------------------------------------------
    # cuneiform lookup
    # ------------------------------------------------------------------
    def cuneiform_lookup(self, byte_val: int) -> str:
        """Map a byte value to its Sumerian cuneiform sign name.

        Parameters
        ----------
        byte_val:
            Integer in ``0..255``.

        Returns
        -------
        str
            The sign name, or ``"?"`` if the byte is not in the table.
        """
        sign, _gloss = self.cuneiform_table.get(byte_val, ("?", "unknown"))
        return sign

    # ------------------------------------------------------------------
    # decode
    # ------------------------------------------------------------------
    def decode(self) -> List[DecodedByte]:
        """Fully decode the strand.

        Returns
        -------
        list of DecodedByte
            One structured record per byte with binary, hex, decimal, cuneiform
            sign, and English gloss.
        """
        out: List[DecodedByte] = []
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

    # ------------------------------------------------------------------
    # DIAG (1, -2, 1) : discrete second derivative / edge detector
    # ------------------------------------------------------------------
    @staticmethod
    def diag_operator(seq: List[float]) -> List[float]:
        """Apply the ``(1, -2, 1)`` discrete second-derivative operator.

        This is the DIAG operator: an edge / contrast detector whose stencil
        sums to zero (``1 - 2 + 1 = 0``), so constant and linear signals map to
        zero.  It allows "unity to perceive contrast".

        Parameters
        ----------
        seq:
            Input sequence (length >= 3).

        Returns
        -------
        list of float
            The second differences ``s[i-1] - 2*s[i] + s[i+1]`` for each interior
            index (length ``len(seq) - 2``).

        Raises
        ------
        ValueError
            If ``len(seq) < 3``.
        """
        if len(seq) < 3:
            raise ValueError("diag_operator requires at least 3 elements")
        return [
            seq[i - 1] - 2.0 * seq[i] + seq[i + 1]
            for i in range(1, len(seq) - 1)
        ]

    # ------------------------------------------------------------------
    # Ouroboros recursion
    # ------------------------------------------------------------------
    def ouroboros_iterate(self, n: int, start: int = PENTAGON_SEED) -> List[int]:
        """Iterate the phi^101-style recursive loop ``n`` times.

        Each step re-injects the previous state into a golden-ratio-modulated
        update, modelling the self-causing Ouroboros loop where "the bottom
        feeds the top".  The recurrence is::

            x_{k+1} = (floor(phi^101) + x_k) mod 256

        Parameters
        ----------
        n:
            Number of iterations.
        start:
            Initial state (defaults to the Pentagon Seed, 5).

        Returns
        -------
        list of int
            The trajectory ``[x_0, x_1, ..., x_n]`` of length ``n + 1``.
        """
        step = self.phi_modulo(101, 256)  # constant golden kick per loop
        traj = [start % 256]
        for _ in range(n):
            traj.append((traj[-1] + step) % 256)
        return traj

    # ------------------------------------------------------------------
    # dunder methods
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"CosmoBit101(strand={self.strand!r}, "
            f"checksum={self.checksum()})"
        )

    def __str__(self) -> str:
        hexes = " ".join(f"0x{b:02X}" for b in self.strand)
        signs = " ".join(self.cuneiform_lookup(b) for b in self.strand)
        return (
            "CosmoBit101 Dragon-Seed strand\n"
            f"  bytes : {hexes}\n"
            f"  signs : {signs}\n"
            f"  check : {self.checksum()} (base-10)"
        )


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------
def _demo() -> None:
    """Pretty-print a demonstration of every public method."""
    cosmo = CosmoBit101()

    print("=" * 66)
    print("  E8 x phi-SiS2 / HPV16 Cosmovirus  --  CosmoBit101 demo")
    print("=" * 66)

    print("\n[repr]", repr(cosmo))
    print("\n[str]\n" + str(cosmo))

    print("\n--- phi-SCL scaling operator ---")
    for n in (1, 5, 10, 101):
        print(f"  phi^{n:<3} ~= {cosmo.phi_power(n):.6e}")
    print(f"  floor(phi^101) mod 256 = {cosmo.phi_modulo(101)}")

    print("\n--- checksum ---")
    print(f"  declared checksum : {cosmo.checksum()}")
    print(f"  raw byte sum      : {cosmo.byte_sum()}")

    print("\n--- DIAG (1,-2,1) second-derivative operator ---")
    ramp = [1.0, 2.0, 3.0, 4.0, 5.0]       # linear -> all zeros
    bump = [0.0, 0.0, 1.0, 0.0, 0.0]       # impulse -> edge response
    print(f"  linear ramp {ramp} -> {cosmo.diag_operator(ramp)}")
    print(f"  impulse     {bump} -> {cosmo.diag_operator(bump)}")

    print("\n--- Ouroboros iteration (5 loops) ---")
    print(f"  trajectory : {cosmo.ouroboros_iterate(5)}")

    print("\n--- Full strand decode ---")
    print(f"  {'#':>2} {'binary':>9} {'hex':>5} {'dec':>4} "
          f"{'sign':<7} gloss")
    print("  " + "-" * 58)
    for rec in cosmo.decode():
        print(f"  {rec['index']:>2} {rec['binary']:>9} {rec['hex']:>5} "
              f"{rec['decimal']:>4} {rec['cuneiform']:<7} {rec['description']}")

    print("\n" + "=" * 66)


if __name__ == "__main__":
    _demo()
