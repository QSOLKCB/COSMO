"""Canonical immutable constants for the COSMO deterministic core."""

from __future__ import annotations

import math
from types import MappingProxyType
from typing import Final, Mapping

GOLDEN_RATIO: Final[float] = (
    1.618_033_988_749_894_848_204_586_834_365_638_117_720
)
QUARTER_TURN_RADIANS: Final[float] = math.pi / 2.0
PENTAGON_SEED: Final[int] = 0b101
DECLARED_SYMBOLIC_INVARIANT: Final[int] = 1621

DRAGON_SEED: Final[bytes] = bytes(
    (0xB7, 0xBA, 0xBE, 0xFF, 0xD6, 0xE5, 0xAA, 0x55)
)
BYTE_LABELS: Final[tuple[str, ...]] = (
    "AN",
    "KI",
    "EN.KI",
    "DIGIR",
    "SI.SI",
    "E2",
    "ZU",
    "UR",
)

_CUNEIFORM_TABLE: dict[int, tuple[str, str]] = {
    0xB7: ("AN", "sky / heaven god"),
    0xBA: ("KI", "earth"),
    0xBE: ("EN.KI", "lord of the earth / waters"),
    0xFF: ("DIGIR", "divine determinative marker"),
    0xD6: ("SI.SI", "dragon seed"),
    0xE5: ("E2", "house / temple"),
    0xAA: ("ZU", "knowledge / to know"),
    0x55: ("UR", "dog / watchman"),
}
CUNEIFORM_TABLE: Final[Mapping[int, tuple[str, str]]] = MappingProxyType(
    _CUNEIFORM_TABLE
)
