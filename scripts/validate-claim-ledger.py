#!/usr/bin/env python3
"""Validate the Phase D COSMO claim ledger and its human-readable index."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "claim-ledger.json"
INDEX_PATH = ROOT / "CLAIM-LEDGER.md"

CLASSES = ("FORMAL", "COMPUTATIONAL", "SCIENTIFIC", "HYPOTHESIS", "SYMBOLIC")
CLAIM_ID = re.compile(r"COSMO-D-[0-9]{3}$")
SOURCE_ID = re.compile(r"SRC-[A-Z0-9][A-Z0-9._-]*$")


def fail(message: str) -> None:
    raise SystemExit(f"claim-ledger validation failed: {message}")


def load_json() -> dict[str, Any]:
    try:
        raw = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read canonical JSON: {exc}")
    if not isinstance(raw, dict):
        fail("ledger root must be an object")
    return raw


def require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def validate_provenance(claim_id: str, entries: object) -> None:
    if not isinstance(entries, list) or not entries:
        fail(f"{claim_id} must have repository provenance")
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            fail(f"{claim_id} provenance[{index}] must be an object")
        path_text = require_string(item.get("path"), f"{claim_id} provenance path")
        anchor = require_string(item.get("anchor"), f"{claim_id} provenance anchor")
        require_string(item.get("role"), f"{claim_id} provenance role")
        path = ROOT / path_text
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fail(f"{claim_id} provenance path {path_text!r} unreadable: {exc}")
        if anchor not in text:
            fail(f"{claim_id} anchor {anchor!r} not found in {path_text}")


def validate() -> None:
    ledger = load_json()
    if ledger.get("schema") != "COSMO-CLAIMS-D-1":
        fail("unexpected schema")
    if ledger.get("evidence_classes") != list(CLASSES):
        fail("evidence class order or membership changed")

    sources = ledger.get("sources")
    claims = ledger.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        fail("sources and claims must be arrays")

    source_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            fail("source entries must be objects")
        source_id = require_string(source.get("id"), "source id")
        if SOURCE_ID.fullmatch(source_id) is None:
            fail(f"invalid source id {source_id!r}")
        if source_id in source_ids:
            fail(f"duplicate source id {source_id}")
        source_ids.add(source_id)
        require_string(source.get("kind"), f"{source_id} kind")
        require_string(source.get("title"), f"{source_id} title")
        url = require_string(source.get("url"), f"{source_id} url")
        if not url.startswith("https://"):
            fail(f"{source_id} must use https")
        identifiers = source.get("identifiers")
        if not isinstance(identifiers, dict):
            fail(f"{source_id} identifiers must be an object")
        if any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or not key
            or not value
            for key, value in identifiers.items()
        ):
            fail(f"{source_id} identifiers must map non-empty strings to strings")

    index_text = INDEX_PATH.read_text(encoding="utf-8")
    claim_ids: set[str] = set()
    previous_number = 0
    for claim in claims:
        if not isinstance(claim, dict):
            fail("claim entries must be objects")
        claim_id = require_string(claim.get("id"), "claim id")
        if CLAIM_ID.fullmatch(claim_id) is None:
            fail(f"invalid claim id {claim_id!r}")
        number = int(claim_id.rsplit("-", 1)[1])
        if number <= previous_number:
            fail("claim IDs must be strictly increasing")
        previous_number = number
        if claim_id in claim_ids:
            fail(f"duplicate claim id {claim_id}")
        claim_ids.add(claim_id)

        evidence_class = claim.get("class")
        if evidence_class not in CLASSES:
            fail(f"{claim_id} has invalid evidence class")
        require_string(claim.get("status"), f"{claim_id} status")
        require_string(claim.get("statement"), f"{claim_id} statement")
        boundary = require_string(claim.get("boundary"), f"{claim_id} boundary")
        validate_provenance(claim_id, claim.get("provenance"))

        source_list = claim.get("sources")
        if not isinstance(source_list, list) or any(
            not isinstance(source_id, str) for source_id in source_list
        ):
            fail(f"{claim_id} sources must be a string array")
        if len(source_list) != len(set(source_list)):
            fail(f"{claim_id} repeats a source")
        unknown = set(source_list) - source_ids
        if unknown:
            fail(f"{claim_id} references unknown sources: {sorted(unknown)}")

        falsification = claim.get("falsification")
        if evidence_class == "SCIENTIFIC" and not source_list:
            fail(f"{claim_id} SCIENTIFIC claim requires an external source")
        if evidence_class in {"FORMAL", "COMPUTATIONAL"} and falsification is not None:
            fail(f"{claim_id} {evidence_class} claim must not use hypothesis falsification")
        if evidence_class == "HYPOTHESIS":
            require_string(falsification, f"{claim_id} falsification")
            if claim.get("status") == "SUPPORTED":
                fail(f"{claim_id} hypothesis may not be marked SUPPORTED")
        elif falsification is not None:
            fail(f"{claim_id} non-hypothesis falsification must be null")
        if evidence_class == "SYMBOLIC" and "not" not in boundary.lower():
            fail(f"{claim_id} SYMBOLIC boundary must explicitly say what is not claimed")

        if f"**{claim_id}**" not in index_text:
            fail(f"{claim_id} missing from CLAIM-LEDGER.md")

    documented = set(re.findall(r"\*\*(COSMO-D-[0-9]{3})\*\*", index_text))
    if documented != claim_ids:
        fail(
            "CLAIM-LEDGER.md claim IDs differ from canonical JSON: "
            f"extra={sorted(documented - claim_ids)} missing={sorted(claim_ids - documented)}"
        )

    print(
        f"claim ledger valid: {len(claims)} claims, "
        f"{len(sources)} external sources, schema={ledger['schema']}"
    )


if __name__ == "__main__":
    validate()
