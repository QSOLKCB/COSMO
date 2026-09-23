"""Canonical deterministic computational core for COSMO Phase B2."""

from .arithmetic import (
    lucas,
    phi_floor_integer,
    phi_floor_modulo,
    phi_power_approx,
    second_difference,
)
from .constants import (
    BYTE_LABELS,
    CUNEIFORM_TABLE,
    DECLARED_SYMBOLIC_INVARIANT,
    DRAGON_SEED,
    GOLDEN_RATIO,
    PENTAGON_SEED,
    QUARTER_TURN_RADIANS,
)
from .dna import bytes_to_dna, dna_to_bytes
from .ecc import (
    CodewordDecodeResult,
    SecdedDecodeResult,
    UncorrectableECCError,
    decode_codeword,
    encode_nibble,
    secded_decode,
    secded_encode,
)
from .integrity import canonical_json_bytes, sha256_hex
from .manifest import ArtifactDigest, ExperimentManifest, ManifestScalar
from .payload import (
    PayloadFacts,
    payload_bit_length,
    payload_byte_sum,
    payload_facts,
)

__all__ = [
    "ArtifactDigest",
    "BYTE_LABELS",
    "CUNEIFORM_TABLE",
    "CodewordDecodeResult",
    "DECLARED_SYMBOLIC_INVARIANT",
    "DRAGON_SEED",
    "ExperimentManifest",
    "GOLDEN_RATIO",
    "ManifestScalar",
    "PENTAGON_SEED",
    "PayloadFacts",
    "QUARTER_TURN_RADIANS",
    "SecdedDecodeResult",
    "UncorrectableECCError",
    "bytes_to_dna",
    "canonical_json_bytes",
    "decode_codeword",
    "dna_to_bytes",
    "encode_nibble",
    "lucas",
    "payload_bit_length",
    "payload_byte_sum",
    "payload_facts",
    "phi_floor_integer",
    "phi_floor_modulo",
    "phi_power_approx",
    "secded_decode",
    "secded_encode",
    "second_difference",
    "sha256_hex",
]
