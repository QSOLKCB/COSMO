"""Deterministic triadic 8x8x8 lattice experiments for COSMO Phase B4.

This module is a computational experiment over ternary states {0, 1, 2}. It
does not model or claim physical quantum hardware.

The scalar path is the correctness reference. The parallel path reads only the
immutable prior state, partitions cells deterministically, restores canonical
index order before constructing output, and records requested/configured/
observed worker information separately.
"""

from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from threading import get_ident
from typing import Final, Protocol, TypeGuard, runtime_checkable

from .integrity import sha256_hex

LATTICE_EDGE: Final[int] = 8
LATTICE_SIZE: Final[int] = LATTICE_EDGE**3
TRIADIC_STATES: Final[tuple[int, int, int]] = (0, 1, 2)
MAX_PARALLEL_WORKERS: Final[int] = 32
_UINT64_MASK: Final[int] = (1 << 64) - 1
_SPLITMIX_GAMMA: Final[int] = 0x9E3779B97F4A7C15
_ZERO_MASK: Final[tuple[int, ...]] = (0,) * LATTICE_SIZE

TriadicStateTuple = tuple[int, ...]
Codeword = tuple[int, ...]


def _is_plain_int(value: object) -> TypeGuard[int]:
    return type(value) is int


def _require_non_negative_int(value: object, label: str) -> int:
    if not _is_plain_int(value) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _require_triadic_state(value: object, label: str = "state") -> int:
    if not _is_plain_int(value) or value not in TRIADIC_STATES:
        raise ValueError(f"{label} must be one of {TRIADIC_STATES}")
    return value


def _require_cells(cells: object, label: str = "cells") -> TriadicStateTuple:
    if not isinstance(cells, tuple) or len(cells) != LATTICE_SIZE:
        raise ValueError(
            f"{label} must be an immutable tuple of {LATTICE_SIZE} ternary states"
        )
    if any(not _is_plain_int(value) or value not in TRIADIC_STATES for value in cells):
        raise ValueError(f"{label} contains a non-ternary state")
    return cells


def _quota_capacity(quota: int, period: int) -> int | None:
    """Convert a cgroup CPU quota/period pair to whole-worker capacity."""
    if quota < 0:
        return None
    if quota == 0 or period <= 0:
        return 1
    return max(1, quota // period)


def _parse_cgroup_v2_cpu_max(text: str) -> int | None:
    """Parse one cgroup-v2 cpu.max value conservatively."""
    fields = text.split()
    if len(fields) != 2:
        return 1
    quota_text, period_text = fields
    if quota_text == "max":
        try:
            period = int(period_text)
        except ValueError:
            return 1
        return None if period > 0 else 1
    try:
        quota = int(quota_text)
        period = int(period_text)
    except ValueError:
        return 1
    return _quota_capacity(quota, period)


def _parse_proc_cgroup(text: str) -> tuple[str | None, str | None]:
    """Return current-process v2 and v1-CPU cgroup paths."""
    v2_path: str | None = None
    v1_cpu_path: str | None = None
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        hierarchy, controllers, path = parts
        if hierarchy == "0" and controllers == "":
            v2_path = path
        elif "cpu" in controllers.split(","):
            v1_cpu_path = path
    return v2_path, v1_cpu_path


def _ancestor_paths(root: Path, relative: str | None) -> tuple[Path, ...]:
    """Return current cgroup directory and visible ancestors under root."""
    if relative is None:
        return (root,)
    current = root.joinpath(*Path(relative).parts[1:])
    try:
        current.relative_to(root)
    except ValueError:
        return (root,)

    paths: list[Path] = []
    while True:
        paths.append(current)
        if current == root:
            break
        current = current.parent
    return tuple(paths)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _cgroup_cpu_capacity(
    *,
    cgroup_root: Path = Path("/sys/fs/cgroup"),
    proc_cgroup: Path = Path("/proc/self/cgroup"),
) -> int | None:
    """Return the tightest visible Linux cgroup CPU quota, if any.

    Both cgroup v2 and common cgroup v1 CPU-controller layouts are supported.
    Hierarchical ancestors are checked because an unlimited child can still be
    constrained by a parent quota.
    """
    proc_text = _read_text(proc_cgroup)
    v2_relative, v1_relative = _parse_proc_cgroup(proc_text or "")

    capacities: list[int] = []

    for directory in _ancestor_paths(cgroup_root, v2_relative):
        cpu_max = _read_text(directory / "cpu.max")
        if cpu_max is None:
            continue
        parsed = _parse_cgroup_v2_cpu_max(cpu_max)
        if parsed is not None:
            capacities.append(parsed)

    for controller_name in ("cpu", "cpu,cpuacct"):
        controller_root = cgroup_root / controller_name
        for directory in _ancestor_paths(controller_root, v1_relative):
            quota_text = _read_text(directory / "cpu.cfs_quota_us")
            period_text = _read_text(directory / "cpu.cfs_period_us")
            if quota_text is None or period_text is None:
                continue
            try:
                quota = int(quota_text.strip())
                period = int(period_text.strip())
            except ValueError:
                capacities.append(1)
                continue
            parsed = _quota_capacity(quota, period)
            if parsed is not None:
                capacities.append(parsed)

    return min(capacities) if capacities else None


def _affinity_cpu_capacity() -> int | None:
    """Return the process CPU-affinity capacity when the platform exposes it."""
    get_affinity = getattr(os, "sched_getaffinity", None)
    if get_affinity is None:
        return None
    try:
        capacity = len(get_affinity(0))
    except (OSError, TypeError):
        return None
    return max(1, capacity)


def runtime_cpu_capacity() -> int:
    """Return conservative worker capacity for the current runtime.

    Capacity is bounded by host-visible CPUs, process affinity, Linux cgroup
    quota when available, and COSMO's hard worker limit.
    """
    host_cpus = os.cpu_count() or 1
    capacities = [host_cpus, MAX_PARALLEL_WORKERS]

    affinity_capacity = _affinity_cpu_capacity()
    if affinity_capacity is not None:
        capacities.append(affinity_capacity)

    quota_capacity = _cgroup_cpu_capacity()
    if quota_capacity is not None:
        capacities.append(quota_capacity)

    return max(1, min(capacities))


def _splitmix64(value: int) -> int:
    """Return one deterministic SplitMix64 output for an unsigned input."""
    z = (value + _SPLITMIX_GAMMA) & _UINT64_MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _UINT64_MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _UINT64_MASK
    return (z ^ (z >> 31)) & _UINT64_MASK


@dataclass(frozen=True)
class TriadicLattice:
    """Immutable 8x8x8 ternary lattice in canonical flattened index order."""

    cells: TriadicStateTuple

    def __post_init__(self) -> None:
        _require_cells(self.cells)

    @classmethod
    def zero(cls) -> "TriadicLattice":
        """Return the all-zero fixed-point lattice."""
        return cls((0,) * LATTICE_SIZE)

    @classmethod
    def seeded(cls, seed: int) -> "TriadicLattice":
        """Return deterministic stateless seeded initialization.

        The seed is interpreted as an unsigned 64-bit integer. Every cell is
        derived independently from the seed and canonical cell index, avoiding
        any shared mutable RNG stream.
        """
        if not _is_plain_int(seed) or seed < 0 or seed > _UINT64_MASK:
            raise ValueError("seed must be an unsigned 64-bit integer")

        cells = tuple(
            _splitmix64(
                (seed + index * _SPLITMIX_GAMMA) & _UINT64_MASK
            )
            % 3
            for index in range(LATTICE_SIZE)
        )
        return cls(cells)

    def sha256(self) -> str:
        """Return SHA-256 over the canonical one-byte-per-trit representation."""
        return sha256_hex(bytes(self.cells))

    def state_counts(self) -> tuple[int, int, int]:
        """Return counts of states 0, 1 and 2."""
        counts = tuple(self.cells.count(state) for state in TRIADIC_STATES)
        return counts[0], counts[1], counts[2]


@dataclass(frozen=True)
class TriadicMask:
    """Immutable additive ternary update mask."""

    values: TriadicStateTuple
    kind: str
    depth: int
    phase: int

    def __post_init__(self) -> None:
        _require_cells(self.values, "mask values")
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("mask kind must be a non-empty string")
        if not _is_plain_int(self.depth) or not 1 <= self.depth <= 2:
            raise ValueError("mask depth must be 1 or 2")
        _require_triadic_state(self.phase, "mask phase")

    def sha256(self) -> str:
        """Return SHA-256 over the canonical mask values."""
        return sha256_hex(bytes(self.values))


@dataclass(frozen=True)
class TriadicRule:
    """Deterministic local rule evaluated modulo 3."""

    center_weight: int = 1
    neighbor_weight: int = 1
    bias: int = 0

    def __post_init__(self) -> None:
        _require_triadic_state(self.center_weight, "center_weight")
        _require_triadic_state(self.neighbor_weight, "neighbor_weight")
        _require_triadic_state(self.bias, "bias")


DEFAULT_TRIADIC_RULE: Final[TriadicRule] = TriadicRule()


@dataclass(frozen=True)
class ParallelStepResult:
    """One deterministic parallel step plus worker evidence."""

    lattice: TriadicLattice
    requested_workers: int
    host_logical_cpus: int
    worker_capacity: int
    effective_workers: int
    observed_worker_threads: int
    partitions: tuple[tuple[int, int], ...]
    backend: str = field(default="ThreadPoolExecutor", init=False)


@dataclass(frozen=True)
class LoopClosureReport:
    """Exact discrete loop-closure diagnostic D_n(x)."""

    steps: int
    distance: int
    closed: bool
    initial_sha256: str
    final_sha256: str


@dataclass(frozen=True)
class StabilityReport:
    """Deterministic cycle/convergence and entropy diagnostics."""

    steps_examined: int
    cycle_detected: bool
    converged: bool
    transient_length: int | None
    cycle_length: int | None
    initial_entropy: float
    terminal_entropy: float
    terminal_sha256: str


class RecoveryStatus(str, Enum):
    """Outcome of one codeword recovery attempt."""

    CLEAN = "clean"
    CORRECTED = "corrected"
    UNCORRECTABLE = "uncorrectable"


@dataclass(frozen=True)
class RecoveryResult:
    """Result of decoding/recovering one ternary codeword."""

    status: RecoveryStatus
    symbol: int | None
    syndrome: tuple[int, ...]
    corrected_indices: tuple[int, ...]
    recovery_passes: int | None


@dataclass(frozen=True)
class LatticeRecoveryReport:
    """Recovery evidence for a complete encoded lattice."""

    recovered: TriadicLattice | None
    corrected_blocks: tuple[int, ...]
    uncorrectable_blocks: tuple[int, ...]
    syndromes: tuple[tuple[int, ...], ...]
    max_recovery_passes: int | None


@runtime_checkable
class TriadicCodebook(Protocol):
    """Generic ternary codebook/recovery interface."""

    @property
    def block_length(self) -> int:
        """Return encoded symbols per source trit."""
        ...

    def encode(self, symbol: int) -> Codeword:
        """Encode one source trit."""
        ...

    def syndrome(self, block: Codeword) -> tuple[int, ...]:
        """Return deterministic syndrome coordinates."""
        ...

    def recover(self, block: Codeword) -> RecoveryResult:
        """Recover one source trit or report an uncorrectable codeword."""
        ...


@dataclass(frozen=True)
class TernaryRepetitionCode:
    """Length-3 ternary repetition code.

    The documented correction capability is one altered trit per 3-symbol
    codeword. An all-distinct codeword is detected as uncorrectable. Patterns
    with two equal altered symbols lie outside the claimed correction model.
    """

    block_length: int = field(default=3, init=False)

    @staticmethod
    def _require_block(block: object) -> Codeword:
        if not isinstance(block, tuple) or len(block) != 3:
            raise ValueError("repetition codeword must be an immutable length-3 tuple")
        for index, value in enumerate(block):
            _require_triadic_state(value, f"codeword[{index}]")
        return block

    def encode(self, symbol: int) -> Codeword:
        exact = _require_triadic_state(symbol, "symbol")
        return (exact, exact, exact)

    def syndrome(self, block: Codeword) -> tuple[int, ...]:
        exact = self._require_block(block)
        return (
            (exact[1] - exact[0]) % 3,
            (exact[2] - exact[0]) % 3,
        )

    def recover(self, block: Codeword) -> RecoveryResult:
        exact = self._require_block(block)
        syndrome = self.syndrome(exact)
        counts = tuple(exact.count(state) for state in TRIADIC_STATES)

        if 3 in counts:
            symbol = counts.index(3)
            return RecoveryResult(
                status=RecoveryStatus.CLEAN,
                symbol=symbol,
                syndrome=syndrome,
                corrected_indices=(),
                recovery_passes=0,
            )

        if 2 in counts:
            symbol = counts.index(2)
            corrected = tuple(
                index for index, value in enumerate(exact) if value != symbol
            )
            return RecoveryResult(
                status=RecoveryStatus.CORRECTED,
                symbol=symbol,
                syndrome=syndrome,
                corrected_indices=corrected,
                recovery_passes=1,
            )

        return RecoveryResult(
            status=RecoveryStatus.UNCORRECTABLE,
            symbol=None,
            syndrome=syndrome,
            corrected_indices=(),
            recovery_passes=None,
        )


def lattice_index(x: int, y: int, z: int) -> int:
    """Map canonical coordinates to one flattened index."""
    coordinates = (x, y, z)
    for value in coordinates:
        if not _is_plain_int(value) or not 0 <= value < LATTICE_EDGE:
            raise ValueError("lattice coordinates must be integers in range 0..7")
    return (x * LATTICE_EDGE + y) * LATTICE_EDGE + z


def lattice_coordinates(index: int) -> tuple[int, int, int]:
    """Map one canonical flattened index to (x, y, z)."""
    if not _is_plain_int(index) or not 0 <= index < LATTICE_SIZE:
        raise ValueError(f"lattice index must be in range 0..{LATTICE_SIZE - 1}")
    x, remainder = divmod(index, LATTICE_EDGE * LATTICE_EDGE)
    y, z = divmod(remainder, LATTICE_EDGE)
    return x, y, z


def neighbor_indices_reference(index: int) -> tuple[int, ...]:
    """Return the six periodic von-Neumann neighbours of one cell."""
    x, y, z = lattice_coordinates(index)
    points = (
        ((x - 1) % LATTICE_EDGE, y, z),
        ((x + 1) % LATTICE_EDGE, y, z),
        (x, (y - 1) % LATTICE_EDGE, z),
        (x, (y + 1) % LATTICE_EDGE, z),
        (x, y, (z - 1) % LATTICE_EDGE),
        (x, y, (z + 1) % LATTICE_EDGE),
    )
    return tuple(lattice_index(*point) for point in points)


def generate_neighbor_table_reference() -> tuple[tuple[int, ...], ...]:
    """Generate the immutable 512-entry topology table without cache reuse."""
    return tuple(
        neighbor_indices_reference(index) for index in range(LATTICE_SIZE)
    )


@lru_cache(maxsize=1)
def canonical_neighbor_table() -> tuple[tuple[int, ...], ...]:
    """Return the immutable topology table used by optimized update paths."""
    return generate_neighbor_table_reference()


def _ternary_digit_sum(value: int, depth: int) -> int:
    total = 0
    remaining = value
    for _ in range(depth):
        remaining, digit = divmod(remaining, 3)
        total += digit
    return total


def triadic_digit_mask(depth: int = 2, phase: int = 0) -> TriadicMask:
    """Return a deterministic 3-adic-style digit-residue mask.

    The mask uses the low-order base-3 digits of each coordinate. This is a
    discrete computational texture; no fractal dimension or physical meaning is
    asserted.
    """
    if not _is_plain_int(depth) or not 1 <= depth <= 2:
        raise ValueError("depth must be 1 or 2 for coordinates 0..7")
    exact_phase = _require_triadic_state(phase, "phase")

    values = []
    for index in range(LATTICE_SIZE):
        x, y, z = lattice_coordinates(index)
        residue = (
            _ternary_digit_sum(x, depth)
            + _ternary_digit_sum(y, depth)
            + _ternary_digit_sum(z, depth)
            + exact_phase
        ) % 3
        values.append(residue)

    return TriadicMask(
        values=tuple(values),
        kind="ternary-digit-residue",
        depth=depth,
        phase=exact_phase,
    )


def _update_cell(
    lattice: TriadicLattice,
    index: int,
    rule: TriadicRule,
    mask_values: TriadicStateTuple,
) -> int:
    neighbours = canonical_neighbor_table()[index]
    neighbour_sum = sum(lattice.cells[neighbour] for neighbour in neighbours)
    return (
        rule.center_weight * lattice.cells[index]
        + rule.neighbor_weight * neighbour_sum
        + rule.bias
        + mask_values[index]
    ) % 3


def step_scalar(
    lattice: TriadicLattice,
    rule: TriadicRule = DEFAULT_TRIADIC_RULE,
    mask: TriadicMask | None = None,
) -> TriadicLattice:
    """Apply one deterministic synchronous scalar/reference update."""
    mask_values = _ZERO_MASK if mask is None else mask.values
    cells = tuple(
        _update_cell(lattice, index, rule, mask_values)
        for index in range(LATTICE_SIZE)
    )
    return TriadicLattice(cells)


def _partition_ranges(
    size: int,
    workers: int,
) -> tuple[tuple[int, int], ...]:
    quotient, remainder = divmod(size, workers)
    partitions = []
    start = 0
    for worker_index in range(workers):
        width = quotient + (1 if worker_index < remainder else 0)
        stop = start + width
        partitions.append((start, stop))
        start = stop
    return tuple(partitions)


def _worker_capacity(
    requested_workers: int,
    worker_capacity: int | None,
) -> tuple[int, int, int]:
    if not _is_plain_int(requested_workers) or requested_workers <= 0:
        raise ValueError("requested_workers must be a positive integer")

    host_cpus = os.cpu_count() or 1
    configured_capacity = runtime_cpu_capacity()
    if worker_capacity is not None:
        if not _is_plain_int(worker_capacity) or worker_capacity <= 0:
            raise ValueError("worker_capacity must be a positive integer")
        configured_capacity = min(configured_capacity, worker_capacity)

    effective = min(
        requested_workers,
        configured_capacity,
        LATTICE_SIZE,
    )
    return host_cpus, configured_capacity, effective


def step_parallel(
    lattice: TriadicLattice,
    requested_workers: int,
    rule: TriadicRule = DEFAULT_TRIADIC_RULE,
    mask: TriadicMask | None = None,
    *,
    worker_capacity: int | None = None,
) -> ParallelStepResult:
    """Apply one deterministic bounded parallel update.

    Python threads are used as an implementation mechanism. The returned
    observed thread count is execution evidence only; this function makes no
    multicore speedup claim.
    """
    host_cpus, configured_capacity, effective_workers = _worker_capacity(
        requested_workers,
        worker_capacity,
    )
    partitions = _partition_ranges(LATTICE_SIZE, effective_workers)
    mask_values = _ZERO_MASK if mask is None else mask.values

    def run_partition(start: int, stop: int) -> tuple[int, tuple[int, ...], int]:
        values = tuple(
            _update_cell(lattice, index, rule, mask_values)
            for index in range(start, stop)
        )
        return start, values, get_ident()

    completed: list[tuple[int, tuple[int, ...], int]] = []
    with ThreadPoolExecutor(
        max_workers=effective_workers,
        thread_name_prefix="cosmo-b4",
    ) as executor:
        futures = [
            executor.submit(run_partition, start, stop)
            for start, stop in partitions
        ]
        for future in futures:
            completed.append(future.result())

    completed.sort(key=lambda item: item[0])
    merged = tuple(
        value
        for _start, values, _thread_id in completed
        for value in values
    )
    observed_threads = len({thread_id for _start, _values, thread_id in completed})

    return ParallelStepResult(
        lattice=TriadicLattice(merged),
        requested_workers=requested_workers,
        host_logical_cpus=host_cpus,
        worker_capacity=configured_capacity,
        effective_workers=effective_workers,
        observed_worker_threads=observed_threads,
        partitions=partitions,
    )


def iterate_scalar(
    lattice: TriadicLattice,
    steps: int,
    rule: TriadicRule = DEFAULT_TRIADIC_RULE,
    mask: TriadicMask | None = None,
) -> TriadicLattice:
    """Apply the scalar reference transition a fixed number of times."""
    exact_steps = _require_non_negative_int(steps, "steps")
    current = lattice
    for _ in range(exact_steps):
        current = step_scalar(current, rule, mask)
    return current


def loop_closure_distance(
    left: TriadicLattice,
    right: TriadicLattice,
) -> int:
    """Return exact D(x,y) = sum_i (x_i - y_i)^2."""
    return sum(
        (left_value - right_value) ** 2
        for left_value, right_value in zip(
            left.cells,
            right.cells,
            strict=True,
        )
    )


def loop_closure(
    lattice: TriadicLattice,
    steps: int,
    rule: TriadicRule = DEFAULT_TRIADIC_RULE,
    mask: TriadicMask | None = None,
) -> LoopClosureReport:
    """Compute D_n(x) = ||T^n(x) - x||^2 for the scalar reference path."""
    final = iterate_scalar(lattice, steps, rule, mask)
    distance = loop_closure_distance(lattice, final)
    return LoopClosureReport(
        steps=steps,
        distance=distance,
        closed=distance == 0,
        initial_sha256=lattice.sha256(),
        final_sha256=final.sha256(),
    )


def state_entropy(lattice: TriadicLattice) -> float:
    """Return normalized Shannon entropy over the three state populations."""
    entropy = 0.0
    for count in lattice.state_counts():
        if count == 0:
            continue
        probability = count / LATTICE_SIZE
        entropy -= probability * math.log(probability, 3)
    return entropy


def analyze_stability(
    lattice: TriadicLattice,
    max_steps: int,
    rule: TriadicRule = DEFAULT_TRIADIC_RULE,
    mask: TriadicMask | None = None,
) -> StabilityReport:
    """Detect the first exact repeated state up to max_steps."""
    exact_max_steps = _require_non_negative_int(max_steps, "max_steps")
    initial_entropy = state_entropy(lattice)
    seen: dict[TriadicStateTuple, int] = {lattice.cells: 0}
    current = lattice

    for step in range(1, exact_max_steps + 1):
        current = step_scalar(current, rule, mask)
        previous = seen.get(current.cells)
        if previous is not None:
            cycle_length = step - previous
            return StabilityReport(
                steps_examined=step,
                cycle_detected=True,
                converged=cycle_length == 1,
                transient_length=previous,
                cycle_length=cycle_length,
                initial_entropy=initial_entropy,
                terminal_entropy=state_entropy(current),
                terminal_sha256=current.sha256(),
            )
        seen[current.cells] = step

    return StabilityReport(
        steps_examined=exact_max_steps,
        cycle_detected=False,
        converged=False,
        transient_length=None,
        cycle_length=None,
        initial_entropy=initial_entropy,
        terminal_entropy=state_entropy(current),
        terminal_sha256=current.sha256(),
    )


def encode_lattice(
    lattice: TriadicLattice,
    codebook: TriadicCodebook,
) -> tuple[Codeword, ...]:
    """Encode every lattice trit using a generic codebook."""
    return tuple(codebook.encode(symbol) for symbol in lattice.cells)


def corrupt_codeword(
    block: Codeword,
    index: int,
    delta: int = 1,
) -> Codeword:
    """Return one deterministic ternary corruption of a codeword."""
    if not isinstance(block, tuple) or not block:
        raise ValueError("codeword must be a non-empty immutable tuple")
    for offset, value in enumerate(block):
        _require_triadic_state(value, f"codeword[{offset}]")
    if not _is_plain_int(index) or not 0 <= index < len(block):
        raise ValueError("codeword corruption index is out of range")
    if not _is_plain_int(delta) or delta not in (1, 2):
        raise ValueError("ternary corruption delta must be 1 or 2")

    mutable = list(block)
    mutable[index] = (mutable[index] + delta) % 3
    return tuple(mutable)


def recover_lattice(
    blocks: tuple[Codeword, ...],
    codebook: TriadicCodebook,
) -> LatticeRecoveryReport:
    """Recover one complete lattice from immutable encoded codewords."""
    if not isinstance(blocks, tuple) or len(blocks) != LATTICE_SIZE:
        raise ValueError(
            f"blocks must be an immutable tuple of {LATTICE_SIZE} codewords"
        )

    symbols: list[int] = []
    corrected_blocks: list[int] = []
    uncorrectable_blocks: list[int] = []
    syndromes: list[tuple[int, ...]] = []
    recovery_passes: list[int] = []

    for block_index, block in enumerate(blocks):
        result = codebook.recover(block)
        syndromes.append(result.syndrome)

        if result.status is RecoveryStatus.UNCORRECTABLE:
            uncorrectable_blocks.append(block_index)
            continue

        if result.symbol is None:
            raise ArithmeticError("recoverable codeword returned no symbol")
        symbols.append(result.symbol)

        if result.status is RecoveryStatus.CORRECTED:
            corrected_blocks.append(block_index)
        if result.recovery_passes is not None:
            recovery_passes.append(result.recovery_passes)

    recovered: TriadicLattice | None
    max_passes: int | None
    if uncorrectable_blocks:
        recovered = None
        max_passes = None
    else:
        if len(symbols) != LATTICE_SIZE:
            raise ArithmeticError("recovery produced an incomplete lattice")
        recovered = TriadicLattice(tuple(symbols))
        max_passes = max(recovery_passes, default=0)

    return LatticeRecoveryReport(
        recovered=recovered,
        corrected_blocks=tuple(corrected_blocks),
        uncorrectable_blocks=tuple(uncorrectable_blocks),
        syndromes=tuple(syndromes),
        max_recovery_passes=max_passes,
    )
