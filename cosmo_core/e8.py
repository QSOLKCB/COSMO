"""Exact E8 roots and Weyl reflections for COSMO Phase B3.

Coordinates are stored in doubled form: an integer tuple ``v`` represents the
mathematical vector ``v / 2``. This keeps both E8 root families and every Weyl
reflection on the E8 lattice exact without floating-point arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product
from typing import Final, TypeAlias, TypeGuard

from .integrity import canonical_json_bytes, sha256_hex

ScaledVector: TypeAlias = tuple[int, ...]

E8_DIMENSION: Final[int] = 8
E8_ROOT_COUNT: Final[int] = 240
E8_INTEGER_ROOT_COUNT: Final[int] = 112
E8_HALF_INTEGER_ROOT_COUNT: Final[int] = 128
E8_ROOT_TABLE_SHA256: Final[str] = (
    "f6e7675c180edb41ea1c47705d7b14daeed7e08f3791dbdf1fc0c55ef156b662"
)


class E8RootFamily(str, Enum):
    """The two exact coordinate families in the E8 root system."""

    INTEGER = "integer"
    HALF_INTEGER = "half-integer"


@dataclass(frozen=True)
class E8RootSystemReport:
    """Validated structural identity of one canonical E8 root table."""

    root_count: int
    integer_root_count: int
    half_integer_root_count: int
    rank: int
    sha256: str


@dataclass(frozen=True)
class WeylReflection:
    """One Weyl reflection, canonically identified by its E8 root."""

    root: ScaledVector

    def __post_init__(self) -> None:
        if not is_e8_root(self.root):
            raise ValueError("Weyl reflection root must be an E8 root")

    def apply(self, vector: ScaledVector) -> ScaledVector:
        """Apply this reflection to one E8 lattice vector."""
        return weyl_reflect(vector, self.root)


def is_scaled_vector(value: object) -> TypeGuard[ScaledVector]:
    """Return whether ``value`` is an exact doubled-coordinate 8-vector."""
    return (
        isinstance(value, tuple)
        and len(value) == E8_DIMENSION
        and all(type(coordinate) is int for coordinate in value)
    )


def _require_scaled_vector(value: object, label: str) -> ScaledVector:
    if not is_scaled_vector(value):
        raise ValueError(
            f"{label} must be an immutable {E8_DIMENSION}-tuple of integers"
        )
    return value


def generate_e8_integer_roots_reference() -> tuple[ScaledVector, ...]:
    """Generate the 112 roots with two ``±1`` coordinates.

    Doubled-coordinate representation therefore uses two ``±2`` entries and
    six zero entries.
    """
    roots: list[ScaledVector] = []
    for first, second in combinations(range(E8_DIMENSION), 2):
        for first_sign, second_sign in product((-2, 2), repeat=2):
            coordinates = [0] * E8_DIMENSION
            coordinates[first] = first_sign
            coordinates[second] = second_sign
            roots.append(tuple(coordinates))
    return tuple(sorted(roots))


def generate_e8_half_integer_roots_reference() -> tuple[ScaledVector, ...]:
    """Generate the 128 half-integer roots exactly.

    In doubled coordinates every entry is ``±1`` and the number of negative
    signs is even.
    """
    roots = [
        tuple(signs)
        for signs in product((-1, 1), repeat=E8_DIMENSION)
        if sum(sign < 0 for sign in signs) % 2 == 0
    ]
    return tuple(sorted(roots))


def generate_e8_roots_reference() -> tuple[ScaledVector, ...]:
    """Generate all 240 E8 roots without cache reuse."""
    roots = (
        generate_e8_integer_roots_reference()
        + generate_e8_half_integer_roots_reference()
    )
    return tuple(sorted(roots))


def root_family(root: object) -> E8RootFamily | None:
    """Return the exact E8 family of ``root``, or ``None`` if it is not a root."""
    if not is_scaled_vector(root):
        return None

    nonzero = [coordinate for coordinate in root if coordinate != 0]
    if (
        len(nonzero) == 2
        and all(abs(coordinate) == 2 for coordinate in nonzero)
    ):
        return E8RootFamily.INTEGER

    if (
        all(abs(coordinate) == 1 for coordinate in root)
        and sum(coordinate < 0 for coordinate in root) % 2 == 0
    ):
        return E8RootFamily.HALF_INTEGER

    return None


def is_e8_root(root: object) -> bool:
    """Return whether ``root`` is one of the 240 exact E8 roots."""
    return root_family(root) is not None


def is_e8_lattice_vector(vector: object) -> bool:
    """Return whether a doubled-coordinate vector belongs to the E8 lattice.

    In doubled coordinates all eight entries have the same parity and their
    sum is divisible by four.
    """
    if not is_scaled_vector(vector):
        return False
    parity = vector[0] & 1
    return (
        all((coordinate & 1) == parity for coordinate in vector)
        and sum(vector) % 4 == 0
    )


def dot_product(left: ScaledVector, right: ScaledVector) -> Fraction:
    """Return the exact mathematical dot product of two doubled vectors."""
    lhs = _require_scaled_vector(left, "left vector")
    rhs = _require_scaled_vector(right, "right vector")
    return Fraction(sum(a * b for a, b in zip(lhs, rhs, strict=True)), 4)


def norm_squared(vector: ScaledVector) -> Fraction:
    """Return the exact squared Euclidean norm of a doubled vector."""
    exact = _require_scaled_vector(vector, "vector")
    return Fraction(sum(coordinate * coordinate for coordinate in exact), 4)


def exact_rank(vectors: tuple[ScaledVector, ...]) -> int:
    """Return exact row rank over the rationals."""
    if not isinstance(vectors, tuple):
        raise ValueError("vectors must be an immutable tuple")

    matrix: list[list[Fraction]] = []
    for vector in vectors:
        exact = _require_scaled_vector(vector, "rank vector")
        matrix.append([Fraction(coordinate) for coordinate in exact])

    if not matrix:
        return 0

    row_count = len(matrix)
    rank = 0
    for column in range(E8_DIMENSION):
        pivot = next(
            (
                row
                for row in range(rank, row_count)
                if matrix[row][column] != 0
            ),
            None,
        )
        if pivot is None:
            continue

        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        pivot_value = matrix[rank][column]

        for row in range(rank + 1, row_count):
            if matrix[row][column] == 0:
                continue
            factor = matrix[row][column] / pivot_value
            for offset in range(column, E8_DIMENSION):
                matrix[row][offset] -= factor * matrix[rank][offset]

        rank += 1
        if rank == E8_DIMENSION:
            break

    return rank


def e8_root_table_sha256(roots: tuple[ScaledVector, ...]) -> str:
    """Hash the canonical doubled-coordinate root table."""
    if not isinstance(roots, tuple):
        raise ValueError("root table must be an immutable tuple")
    canonical = []
    for root in roots:
        exact = _require_scaled_vector(root, "root")
        canonical.append(list(exact))
    return sha256_hex(canonical_json_bytes(canonical))


def validate_e8_root_system(
    roots: tuple[ScaledVector, ...],
) -> E8RootSystemReport:
    """Validate the complete canonical E8 root-system contract."""
    if not isinstance(roots, tuple):
        raise ValueError("root table must be an immutable tuple")
    if len(roots) != E8_ROOT_COUNT:
        raise ValueError(f"E8 root table must contain {E8_ROOT_COUNT} roots")
    if roots != tuple(sorted(roots)):
        raise ValueError("E8 roots must use canonical lexicographic ordering")
    if len(set(roots)) != E8_ROOT_COUNT:
        raise ValueError("E8 roots must be unique")

    families = [root_family(root) for root in roots]
    if any(family is None for family in families):
        raise ValueError("root table contains a non-E8 vector")

    integer_count = sum(
        family is E8RootFamily.INTEGER for family in families
    )
    half_integer_count = sum(
        family is E8RootFamily.HALF_INTEGER for families in families
    )
    if integer_count != E8_INTEGER_ROOT_COUNT:
        raise ValueError("unexpected E8 integer-family root count")
    if half_integer_count != E8_HALF_INTEGER_ROOT_COUNT:
        raise ValueError("unexpected E8 half-integer-family root count")

    if any(norm_squared(root) != 2 for root in roots):
        raise ValueError("every E8 root must have squared norm 2")
    if any(not is_e8_lattice_vector(root) for root in roots):
        raise ValueError("every E8 root must lie in the E8 lattice")

    root_set = set(roots)
    if any(
        tuple(-coordinate for coordinate in root) not in root_set
        for root in roots
    ):
        raise ValueError("E8 root table must be closed under negation")

    rank = exact_rank(roots)
    if rank != E8_DIMENSION:
        raise ValueError(f"E8 root table must have rank {E8_DIMENSION}")

    digest = e8_root_table_sha256(roots)
    if digest != E8_ROOT_TABLE_SHA256:
        raise ValueError("E8 root table does not match reviewed canonical identity")

    return E8RootSystemReport(
        root_count=len(roots),
        integer_root_count=integer_count,
        half_integer_root_count=half_integer_count,
        rank=rank,
        sha256=digest,
    )


@lru_cache(maxsize=1)
def canonical_e8_roots() -> tuple[ScaledVector, ...]:
    """Return the validated immutable canonical E8 root table."""
    roots = generate_e8_roots_reference()
    validate_e8_root_system(roots)
    return roots


@lru_cache(maxsize=1)
def canonical_weyl_reflections() -> tuple[WeylReflection, ...]:
    """Return reflections in the same canonical order as the E8 roots."""
    return tuple(WeylReflection(root) for root in canonical_e8_roots())


def weyl_reflect(vector: ScaledVector, root: ScaledVector) -> ScaledVector:
    """Apply ``s_alpha(x) = x - <x, alpha> alpha`` exactly on the E8 lattice."""
    exact_vector = _require_scaled_vector(vector, "vector")
    exact_root = _require_scaled_vector(root, "root")

    if not is_e8_lattice_vector(exact_vector):
        raise ValueError("vector must belong to the E8 lattice")
    if not is_e8_root(exact_root):
        raise ValueError("reflection root must be an E8 root")

    dot_numerator = sum(
        coordinate * root_coordinate
        for coordinate, root_coordinate in zip(
            exact_vector,
            exact_root,
            strict=True,
        )
    )
    if dot_numerator % 4 != 0:
        raise ArithmeticError("E8 lattice/root pairing was unexpectedly non-integral")

    coefficient = dot_numerator // 4
    reflected = tuple(
        coordinate - coefficient * root_coordinate
        for coordinate, root_coordinate in zip(
            exact_vector,
            exact_root,
            strict=True,
        )
    )

    if not is_e8_lattice_vector(reflected):
        raise ArithmeticError("Weyl reflection escaped the E8 lattice")
    return reflected