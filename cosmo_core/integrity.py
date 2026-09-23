"""Canonical byte and JSON integrity helpers."""

from __future__ import annotations

import hashlib
import json


def sha256_hex(data: bytes) -> str:
    """Return the lowercase SHA-256 hex digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON-compatible data to the COSMO canonical byte form."""
    text = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return text.encode("utf-8")
