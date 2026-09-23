"""Canonical deterministic experiment manifests."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from .integrity import canonical_json_bytes, sha256_hex

ManifestScalar = str | int | float | bool | None


@dataclass(frozen=True)
class ArtifactDigest:
    """Name, byte size and SHA-256 identity of one experiment artifact."""

    name: str
    size: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("artifact name must not be empty")
        if self.size < 0:
            raise ValueError("artifact size must be non-negative")
        if len(self.sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.sha256
        ):
            raise ValueError("artifact SHA-256 must be 64 lowercase hex characters")

    @classmethod
    def from_bytes(cls, name: str, data: bytes) -> "ArtifactDigest":
        """Build an artifact identity from immutable bytes."""
        return cls(name=name, size=len(data), sha256=sha256_hex(data))

    def as_dict(self) -> dict[str, object]:
        """Return the canonical JSON object representation."""
        return {"name": self.name, "sha256": self.sha256, "size": self.size}


@dataclass(frozen=True)
class ExperimentManifest:
    """Seed/parameter/input/output binding for one deterministic experiment."""

    seed: int
    parameters: tuple[tuple[str, ManifestScalar], ...]
    inputs: tuple[ArtifactDigest, ...]
    outputs: tuple[ArtifactDigest, ...]
    schema: str = field(
        default="COSMO-EXPERIMENT-MANIFEST-1",
        init=False,
    )

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")

        parameter_names = [name for name, _value in self.parameters]
        if any(not name for name in parameter_names):
            raise ValueError("parameter names must not be empty")
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError("parameter names must be unique")

        for _name, value in self.parameters:
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("manifest float parameters must be finite")

        self._validate_artifact_names(self.inputs, "input")
        self._validate_artifact_names(self.outputs, "output")

    @staticmethod
    def _validate_artifact_names(
        artifacts: tuple[ArtifactDigest, ...],
        role: str,
    ) -> None:
        names = [artifact.name for artifact in artifacts]
        if len(set(names)) != len(names):
            raise ValueError(f"{role} artifact names must be unique")

    @classmethod
    def from_parts(
        cls,
        *,
        seed: int,
        parameters: Mapping[str, ManifestScalar],
        inputs: Mapping[str, bytes],
        outputs: Mapping[str, bytes],
    ) -> "ExperimentManifest":
        """Construct a manifest while canonicalizing all mapping order."""
        parameter_items = tuple(sorted(parameters.items()))
        input_artifacts = tuple(
            ArtifactDigest.from_bytes(name, inputs[name])
            for name in sorted(inputs)
        )
        output_artifacts = tuple(
            ArtifactDigest.from_bytes(name, outputs[name])
            for name in sorted(outputs)
        )
        return cls(
            seed=seed,
            parameters=parameter_items,
            inputs=input_artifacts,
            outputs=output_artifacts,
        )

    def as_dict(self) -> dict[str, object]:
        """Return canonical structured manifest data."""
        return {
            "inputs": [
                artifact.as_dict()
                for artifact in sorted(self.inputs, key=lambda item: item.name)
            ],
            "outputs": [
                artifact.as_dict()
                for artifact in sorted(self.outputs, key=lambda item: item.name)
            ],
            "parameters": {
                name: value for name, value in sorted(self.parameters)
            },
            "schema": self.schema,
            "seed": self.seed,
        }

    def canonical_bytes(self) -> bytes:
        """Return deterministic canonical JSON bytes."""
        return canonical_json_bytes(self.as_dict())

    def sha256(self) -> str:
        """Return the SHA-256 identity of the canonical manifest bytes."""
        return sha256_hex(self.canonical_bytes())
