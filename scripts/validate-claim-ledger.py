#!/usr/bin/env python3
"""Validate the Phase D COSMO claim ledger and canonical Markdown index."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Never, cast

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "claim-ledger.json"
INDEX_PATH = ROOT / "CLAIM-LEDGER.md"

CLASSES = ("FORMAL", "COMPUTATIONAL", "SCIENTIFIC", "HYPOTHESIS", "SYMBOLIC")
CLAIM_ID = re.compile(r"COSMO-D-[0-9]{3}$")
SOURCE_ID = re.compile(r"SRC-[A-Z0-9][A-Z0-9._-]*$")
IDENTIFIER_PATTERNS: dict[str, re.Pattern[str]] = {
    "PMID": re.compile(r"[1-9][0-9]{0,7}$"),
    "PMCID": re.compile(r"PMC[1-9][0-9]*$"),
    "DOI": re.compile(r"10\.[0-9]{4,9}/[^\s]+$"),
    "RefSeq": re.compile(r"[A-Z]{2}_[0-9]+\.[0-9]+$"),
    "year": re.compile(r"(?:19|20)[0-9]{2}$"),
}
ALLOWED_STATUSES: dict[str, frozenset[str]] = {
    "FORMAL": frozenset({"SUPPORTED"}),
    "COMPUTATIONAL": frozenset({"SUPPORTED"}),
    "SCIENTIFIC": frozenset({"SUPPORTED", "SUPPORTED_WITH_SCOPE"}),
    "HYPOTHESIS": frozenset({"PROPOSED"}),
    "SYMBOLIC": frozenset({"PROJECT_DEFINED"}),
}


class DuplicateJsonKeyError(ValueError):
    """Raised when canonical JSON contains the same object key twice."""


def fail(message: str) -> Never:
    raise SystemExit(f"claim-ledger validation failed: {message}")


def reject_duplicate_object_pairs(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Build one JSON object while rejecting duplicate member names."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def parse_json_text(text: str) -> dict[str, Any]:
    """Parse canonical ledger JSON without last-key-wins ambiguity."""
    try:
        raw: object = json.loads(
            text,
            object_pairs_hook=reject_duplicate_object_pairs,
        )
    except (json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        fail(f"invalid canonical JSON: {exc}")
    if not isinstance(raw, dict):
        fail("ledger root must be an object")
    return cast(dict[str, Any], raw)


def load_json() -> dict[str, Any]:
    try:
        text = LEDGER_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"cannot read canonical JSON: {exc}")
    return parse_json_text(text)


def require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be a non-empty string")
    return value


def require_inline_string(value: object, label: str) -> str:
    """Require text that cannot create new Markdown lines/blocks."""
    text = require_string(value, label)
    if any(character in text for character in ("\n", "\r", "\u2028", "\u2029")):
        fail(f"{label} must be single-line text")
    if any(ord(character) < 32 for character in text):
        fail(f"{label} may not contain ASCII control characters")
    return text


def validate_identifiers(source_id: str, identifiers: object) -> dict[str, str]:
    """Validate typed accession/article identifiers used by Phase D sources."""
    if not isinstance(identifiers, dict):
        fail(f"{source_id} identifiers must be an object")

    validated: dict[str, str] = {}
    for key, value in identifiers.items():
        if not isinstance(key, str):
            fail(f"{source_id} identifier names must be strings")
        if key not in IDENTIFIER_PATTERNS:
            fail(f"{source_id} uses unsupported identifier type {key!r}")
        exact_value = require_inline_string(
            value,
            f"{source_id} identifier {key}",
        )
        if IDENTIFIER_PATTERNS[key].fullmatch(exact_value) is None:
            fail(
                f"{source_id} identifier {key} has invalid syntax: "
                f"{exact_value!r}"
            )
        validated[key] = exact_value
    return validated


def validate_repository_path(path_text: str, claim_id: str) -> Path:
    """Resolve a provenance path and prove it stays inside the repository."""
    relative = Path(path_text)
    if relative.is_absolute():
        fail(f"{claim_id} provenance path must be repository-relative")
    if ".." in relative.parts:
        fail(f"{claim_id} provenance path may not contain '..'")

    root = ROOT.resolve()
    try:
        resolved = (ROOT / relative).resolve(strict=True)
    except OSError as exc:
        fail(f"{claim_id} provenance path {path_text!r} unreadable: {exc}")

    try:
        resolved.relative_to(root)
    except ValueError:
        fail(f"{claim_id} provenance path escapes repository root")

    if not resolved.is_file():
        fail(f"{claim_id} provenance path {path_text!r} is not a file")
    return resolved


def validate_provenance(claim_id: str, entries: object) -> None:
    if not isinstance(entries, list) or not entries:
        fail(f"{claim_id} must have repository provenance")
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            fail(f"{claim_id} provenance[{index}] must be an object")
        path_text = require_inline_string(
            item.get("path"),
            f"{claim_id} provenance path",
        )
        anchor = require_inline_string(
            item.get("anchor"),
            f"{claim_id} provenance anchor",
        )
        require_inline_string(
            item.get("role"),
            f"{claim_id} provenance role",
        )
        path = validate_repository_path(path_text, claim_id)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fail(f"{claim_id} provenance path {path_text!r} unreadable: {exc}")
        if anchor not in text:
            fail(f"{claim_id} anchor {anchor!r} not found in {path_text}")


def _source_identifier_text(identifiers: dict[str, str]) -> str:
    if not identifiers:
        return "none"
    return ", ".join(
        f"{key}={identifiers[key]}"
        for key in sorted(identifiers)
    )


def _claim_sources_text(sources: list[str]) -> str:
    return ", ".join(sources) if sources else "none"


def render_index(ledger: dict[str, Any]) -> str:
    """Render the one canonical human-readable ledger from canonical JSON."""
    schema = require_inline_string(ledger.get("schema"), "schema")
    raw_sources = ledger.get("sources")
    raw_claims = ledger.get("claims")
    if not isinstance(raw_sources, list) or not isinstance(raw_claims, list):
        fail("sources and claims must be arrays")

    lines = [
        "# COSMO Claim Ledger",
        "",
        "> Generated canonically from `claims/claim-ledger.json`. "
        "Do not hand-edit this file independently.",
        "",
        f"**Schema:** `{schema}`",
        "",
        "## Evidence classes",
        "",
    ]
    for evidence_class in CLASSES:
        lines.append(f"- **{evidence_class}**")
    lines.extend(["", "## Scientific source registry", ""])

    for source in raw_sources:
        if not isinstance(source, dict):
            fail("source entries must be objects")
        source_id = require_inline_string(source.get("id"), "source id")
        kind = require_inline_string(source.get("kind"), f"{source_id} kind")
        title = require_inline_string(source.get("title"), f"{source_id} title")
        url = require_inline_string(source.get("url"), f"{source_id} url")
        identifiers = validate_identifiers(source_id, source.get("identifiers"))

        lines.extend(
            [
                f"### {source_id}",
                "",
                f"- **Kind:** `{kind}`",
                f"- **Title:** {title}",
                f"- **Identifiers:** {_source_identifier_text(identifiers)}",
                f"- **URL:** {url}",
                "",
            ]
        )

    lines.extend(["## Claims", ""])
    for claim in raw_claims:
        if not isinstance(claim, dict):
            fail("claim entries must be objects")
        claim_id = require_inline_string(claim.get("id"), "claim id")
        evidence_class = require_inline_string(
            claim.get("class"),
            f"{claim_id} class",
        )
        status = require_inline_string(
            claim.get("status"),
            f"{claim_id} status",
        )
        statement = require_inline_string(
            claim.get("statement"),
            f"{claim_id} statement",
        )
        boundary = require_inline_string(
            claim.get("boundary"),
            f"{claim_id} boundary",
        )

        sources_obj = claim.get("sources")
        if not isinstance(sources_obj, list) or any(
            not isinstance(source_id, str) for source_id in sources_obj
        ):
            fail(f"{claim_id} sources must be a string array")
        claim_sources = [
            require_inline_string(
                source_id,
                f"{claim_id} source reference",
            )
            for source_id in cast(list[str], sources_obj)
        ]

        lines.extend(
            [
                f"### {claim_id} — {evidence_class}",
                "",
                f"- **Status:** `{status}`",
                f"- **Statement:** {statement}",
                f"- **Sources:** {_claim_sources_text(claim_sources)}",
                f"- **Boundary:** {boundary}",
            ]
        )

        empirical_status = claim.get("empirical_status")
        if empirical_status is not None:
            exact_empirical_status = require_inline_string(
                empirical_status,
                f"{claim_id} empirical_status",
            )
            lines.append(
                f"- **Empirical status:** `{exact_empirical_status}`"
            )

        falsification = claim.get("falsification")
        if falsification is not None:
            lines.append(
                "- **Falsification:** "
                + require_inline_string(
                    falsification,
                    f"{claim_id} falsification",
                )
            )

        provenance = claim.get("provenance")
        if not isinstance(provenance, list) or not provenance:
            fail(f"{claim_id} must have repository provenance")
        lines.append("- **Repository provenance:**")
        for item in provenance:
            if not isinstance(item, dict):
                fail(f"{claim_id} provenance entries must be objects")
            path_text = require_inline_string(
                item.get("path"),
                f"{claim_id} provenance path",
            )
            anchor = require_inline_string(
                item.get("anchor"),
                f"{claim_id} provenance anchor",
            )
            role = require_inline_string(
                item.get("role"),
                f"{claim_id} provenance role",
            )
            lines.append(
                f"  - `{path_text}` — `{anchor}` (`{role}`)"
            )
        lines.append("")

    lines.extend(
        [
            "## Governance",
            "",
            "1. New cross-domain public-facing claims require a stable "
            "`COSMO-D-###` ID.",
            "2. **SCIENTIFIC** claims require external source records.",
            "3. **HYPOTHESIS** claims must remain `PROPOSED` and include "
            "explicit falsification criteria.",
            "4. **SYMBOLIC** claims require `empirical_status = NON_EMPIRICAL`.",
            "5. **FORMAL** and **COMPUTATIONAL** claims require reviewed "
            "repository provenance.",
            "6. A source about one domain does not validate a cross-domain bridge.",
            "7. This Markdown file must exactly match the canonical JSON rendering.",
            "",
        ]
    )
    return "\n".join(lines)


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
        source_id = require_inline_string(source.get("id"), "source id")
        if SOURCE_ID.fullmatch(source_id) is None:
            fail(f"invalid source id {source_id!r}")
        if source_id in source_ids:
            fail(f"duplicate source id {source_id}")
        source_ids.add(source_id)
        require_inline_string(source.get("kind"), f"{source_id} kind")
        require_inline_string(source.get("title"), f"{source_id} title")
        url = require_inline_string(source.get("url"), f"{source_id} url")
        if not url.startswith("https://"):
            fail(f"{source_id} must use https")
        validate_identifiers(source_id, source.get("identifiers"))

    claim_ids: set[str] = set()
    previous_number = 0
    for claim in claims:
        if not isinstance(claim, dict):
            fail("claim entries must be objects")
        claim_id = require_inline_string(claim.get("id"), "claim id")
        if CLAIM_ID.fullmatch(claim_id) is None:
            fail(f"invalid claim id {claim_id!r}")
        number = int(claim_id.rsplit("-", 1)[1])
        if number <= previous_number:
            fail("claim IDs must be strictly increasing")
        previous_number = number
        if claim_id in claim_ids:
            fail(f"duplicate claim id {claim_id}")
        claim_ids.add(claim_id)

        evidence_class = require_inline_string(
            claim.get("class"),
            f"{claim_id} class",
        )
        if evidence_class not in CLASSES:
            fail(f"{claim_id} has invalid evidence class")
        status = require_inline_string(
            claim.get("status"),
            f"{claim_id} status",
        )
        allowed = ALLOWED_STATUSES[evidence_class]
        if status not in allowed:
            fail(
                f"{claim_id} status {status!r} is invalid for "
                f"{evidence_class}; allowed={sorted(allowed)}"
            )

        require_inline_string(
            claim.get("statement"),
            f"{claim_id} statement",
        )
        require_inline_string(
            claim.get("boundary"),
            f"{claim_id} boundary",
        )
        validate_provenance(claim_id, claim.get("provenance"))

        source_list = claim.get("sources")
        if not isinstance(source_list, list) or any(
            not isinstance(source_id, str) for source_id in source_list
        ):
            fail(f"{claim_id} sources must be a string array")
        validated_sources = [
            require_inline_string(
                source_id,
                f"{claim_id} source reference",
            )
            for source_id in cast(list[str], source_list)
        ]
        if len(validated_sources) != len(set(validated_sources)):
            fail(f"{claim_id} repeats a source")
        unknown = set(validated_sources) - source_ids
        if unknown:
            fail(f"{claim_id} references unknown sources: {sorted(unknown)}")

        falsification = claim.get("falsification")
        if evidence_class == "SCIENTIFIC" and not validated_sources:
            fail(f"{claim_id} SCIENTIFIC claim requires an external source")
        if evidence_class == "HYPOTHESIS":
            require_inline_string(
                falsification,
                f"{claim_id} falsification",
            )
        elif falsification is not None:
            fail(f"{claim_id} non-hypothesis falsification must be null")

        empirical_status = claim.get("empirical_status")
        if evidence_class == "SYMBOLIC":
            if empirical_status != "NON_EMPIRICAL":
                fail(
                    f"{claim_id} SYMBOLIC claim requires "
                    "empirical_status='NON_EMPIRICAL'"
                )
        elif empirical_status is not None:
            fail(
                f"{claim_id} non-SYMBOLIC claim may not set empirical_status"
            )

    try:
        index_text = INDEX_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"cannot read canonical Markdown index: {exc}")
    expected_index = render_index(ledger)
    if index_text != expected_index:
        fail(
            "CLAIM-LEDGER.md differs from canonical JSON rendering; "
            "regenerate it from claims/claim-ledger.json"
        )

    print(
        f"claim ledger valid: {len(claims)} claims, "
        f"{len(sources)} external sources, schema={ledger['schema']}"
    )


if __name__ == "__main__":
    validate()
