"""Pure deterministic arithmetic used by COSMO."""

from __future__ import annotations

from collections.abc import Sequence

from .constants import GOLDEN_RATIO


def phi_power_approx(n: int) -> float:
    """Return the floating-point approximation ``GOLDEN_RATIO ** n``."""
    return GOLDEN_RATIO**n


def lucas(n: int) -> int:
    """Return the n-th Lucas number for ``n >= 0``."""
    if n < 0:
        raise ValueError("Lucas index must be non-negative")
    a, b = 2, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def phi_floor_integer(n: int) -> int:
    """Return ``floor(phi**n)`` for a non-negative integer exponent.

    This uses the exact Lucas-number parity identity rather than floating-point
    exponentiation.
    """
    if n < 0:
        raise ValueError("phi_floor_integer requires n >= 0")
    if n == 0:
        return 1
    value = lucas(n)
    return value if n % 2 == 1 else value - 1


def phi_floor_modulo(n: int, mod: int = 256) -> int:
    """Return ``floor(phi**n) % mod`` using exact integer arithmetic."""
    if mod <= 0:
        raise ValueError("modulus must be positive")
    return phi_floor_integer(n) % mod


def second_difference(seq: Sequence[float]) -> list[float]:
    """Apply the exact ``(1, -2, 1)`` discrete second-difference stencil."""
    if len(seq) < 3:
        raise ValueError("second_difference requires at least 3 elements")
    return [
        seq[i - 1] - 2.0 * seq[i] + seq[i + 1]
        for i in range(1, len(seq) - 1)
    ]
