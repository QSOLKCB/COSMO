#!/usr/bin/env python3
"""Validate the Phase D COSMO claim ledger and canonical Markdown index."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Never, cast
from urllib.parse import SplitResult, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "claim-ledger.json"
INDEX_PATH = ROOT / "CLAIM-LEDGER.md"

CLASSES = ("FORMAL", "COMPUTATIONAL", "SCIENTIFIC", "HYPOTHESIS", "SYMBOLIC")
CLAIM_ID = re.compile(r"COSMO-D-[0-9]{3}$")
CLAIM_ID_SEARCH = re.compile(r"\bCOSMO-D-[0-9]{3}\b")
SOURCE_ID = re.compile(r"SRC-[A-Z0-9][A-Z0-9._-]*$")
LEAN_THEOREM_ANCHOR = re.compile(r"theorem ([A-Za-z_][A-Za-z0-9_']*)$")
IDENTIFIER_PATTERNS: dict[str, re.Pattern[str]] = {
    "PMID": re.compile(r"[1-9][0-9]{0,7}$"),
    "PMCID": re.compile(r"PMC[1-9][0-9]*$"),
    "DOI": re.compile(r"10\.[0-9]{4,9}/[^\s]+$"),
    "RefSeq": re.compile(r"[A-Z]{2}_[0-9]+\.[0-9]+$"),
    "year": re.compile(r"(?:19|20)[0-9]{2}$"),
}
URL_BOUND_IDENTIFIERS = frozenset({"PMID", "PMCID", "DOI", "RefSeq"})
ALLOWED_STATUSES: dict[str, frozenset[str]] = {
    "FORMAL": frozenset({"SUPPORTED"}),
    "COMPUTATIONAL": frozenset({"SUPPORTED"}),
    "SCIENTIFIC": frozenset({"SUPPORTED", "SUPPORTED_WITH_SCOPE"}),
    "HYPOTHESIS": frozenset({"PROPOSED"}),
    "SYMBOLIC": frozenset({"PROJECT_DEFINED"}),
}
ALLOWED_SOURCE_KINDS = frozenset(
    {
        "scholarly_reference",
        "scholarly_article",
        "peer_reviewed_article",
        "peer_reviewed_review",
        "official_database",
    }
)
ALLOWED_SOURCE_DOMAINS = frozenset(
    {
        "mathematics",
        "materials_science",
        "biomedicine",
    }
)
ALLOWED_PROVENANCE_ROLES: dict[str, frozenset[str]] = {
    "FORMAL": frozenset({"kernel_checked_theorem"}),
    "COMPUTATIONAL": frozenset({"implementation", "regression"}),
    "SCIENTIFIC": frozenset({"documented_context", "provenance_record"}),
    "HYPOTHESIS": frozenset({"hypothesis_definition"}),
    "SYMBOLIC": frozenset(
        {
            "project_definition",
            "scope_boundary",
            "symbolic_section",
            "historical_symbolic_mapping",
            "state_label",
        }
    ),
}
PLACEHOLDER_TEXT = frozenset(
    {
        "tbd",
        "todo",
        "n/a",
        "na",
        "none",
        "unknown",
        "placeholder",
        "later",
    }
)
PUBLIC_GOVERNED_PATHS = (
    "README.md",
    "KNOWN_LIMITATIONS.md",
    "cosmovirus.tex",
    "cosmovirus_cattheory.tex",
)
PUBLIC_DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "mathematics": re.compile(
        r"\b(?:Spin\(8\)|triality|E8|E_8|Weyl)\b",
        re.IGNORECASE,
    ),
    "biomedicine": re.compile(
        r"\b(?:HPV16|HPV|capsid|E6|E7|p16)\b",
        re.IGNORECASE,
    ),
    "materials_science": re.compile(
        r"\b(?:SiS2|SiS_2|silicon disulfide)\b",
        re.IGNORECASE,
    ),
    "archaeology": re.compile(
        r"\b(?:Sumerian|cuneiform|archaeolog(?:y|ical))\b",
        re.IGNORECASE,
    ),
    "cosmology": re.compile(
        r"\b(?:cosmic|cosmology|Ouroboros)\b",
        re.IGNORECASE,
    ),
}
PUBLIC_ASSERTION_RE = re.compile(
    r"\b(?:causes?|caused|drives?|driven|produces?|produced|"
    r"determines?|determined|explains?|explained|proves?|proved|"
    r"demonstrates?|demonstrated|establishes?|established|"
    r"validates?|validated|predicts?|predicted|induces?|induced|"
    r"mechanism|corresponds?\s+to|maps?\s+to|is\s+responsible\s+for)\b",
    re.IGNORECASE,
)
PUBLIC_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|cannot|can't|does\s+not|do\s+not|"
    r"is\s+not|are\s+not|without)\b",
    re.IGNORECASE,
)


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


def require_substantive_inline(
    value: object,
    label: str,
    *,
    minimum_length: int = 24,
) -> str:
    """Reject placeholders where the governance contract requires real criteria."""
    text = require_inline_string(value, label)
    if text.strip().lower() in PLACEHOLDER_TEXT:
        fail(f"{label} may not be a placeholder")
    if len(text.strip()) < minimum_length:
        fail(f"{label} must contain substantive criteria")
    return text


def markdown_text(value: str) -> str:
    """Escape raw HTML metacharacters while retaining visible Markdown text."""
    return html.escape(value, quote=False)


def markdown_code(value: str) -> str:
    """Escape a value before interpolation into a Markdown code span."""
    return markdown_text(value).replace("`", "&#96;")


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


def validate_source_kind(source_id: str, kind: object) -> str:
    """Restrict source registry entries to scholarly/database evidence kinds."""
    exact_kind = require_inline_string(kind, f"{source_id} kind")
    if exact_kind not in ALLOWED_SOURCE_KINDS:
        fail(
            f"{source_id} source kind {exact_kind!r} is not an allowed "
            "scholarly/database kind"
        )
    return exact_kind


def validate_source_domain(source_id: str, domain: object) -> str:
    """Require one controlled scientific domain for each external source."""
    exact_domain = require_inline_string(domain, f"{source_id} domain")
    if exact_domain not in ALLOWED_SOURCE_DOMAINS:
        fail(f"{source_id} has unsupported source domain {exact_domain!r}")
    return exact_domain


def validate_source_url(source_id: str, value: object) -> SplitResult:
    """Require an absolute navigable HTTPS source URL without credentials."""
    url = require_inline_string(value, f"{source_id} url")
    if any(character.isspace() for character in url):
        fail(f"{source_id} URL may not contain whitespace")
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as exc:
        fail(f"{source_id} has malformed URL: {exc}")
    if parsed.scheme != "https" or not parsed.hostname:
        fail(f"{source_id} must use an absolute HTTPS URL with a hostname")
    if parsed.username is not None or parsed.password is not None:
        fail(f"{source_id} URL may not contain userinfo")
    return parsed


def canonical_identifier_url(identifier_type: str, value: str) -> str:
    """Return the canonical URL representation for a URL-bound identifier."""
    if identifier_type == "PMID":
        return f"https://pubmed.ncbi.nlm.nih.gov/{value}/"
    if identifier_type == "PMCID":
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{value}/"
    if identifier_type == "RefSeq":
        return f"https://www.ncbi.nlm.nih.gov/nuccore/{value}"
    if identifier_type == "DOI":
        return f"https://doi.org/{value}"
    raise AssertionError(f"identifier type {identifier_type!r} is not URL-bound")


def validate_identifier_urls(
    source_id: str,
    identifiers: dict[str, str],
    value: object,
) -> dict[str, str]:
    """Independently bind every accession/article identifier to its canonical URL."""
    expected_keys = set(identifiers) & URL_BOUND_IDENTIFIERS
    if not expected_keys:
        if value not in (None, {}):
            fail(f"{source_id} may not define identifier_urls without URL-bound IDs")
        return {}

    if not isinstance(value, dict):
        fail(f"{source_id} identifier_urls must be an object")
    if set(value) != expected_keys:
        fail(
            f"{source_id} identifier_urls keys must exactly match "
            f"{sorted(expected_keys)}"
        )

    validated: dict[str, str] = {}
    for identifier_type in sorted(expected_keys):
        identifier_value = identifiers[identifier_type]
        url = require_inline_string(
            value.get(identifier_type),
            f"{source_id} identifier URL {identifier_type}",
        )
        parsed = validate_source_url(source_id, url)
        expected = canonical_identifier_url(identifier_type, identifier_value)
        if parsed.geturl() != expected:
            fail(
                f"{source_id} {identifier_type} {identifier_value} is not "
                f"bound to canonical URL {expected!r}"
            )
        validated[identifier_type] = url
    return validated


def validate_primary_source_url(
    source_id: str,
    parsed: SplitResult,
    identifier_urls: dict[str, str],
) -> None:
    """Require the source's primary URL to be one of its bound identifier URLs."""
    if not identifier_urls:
        return
    primary = parsed.geturl()
    if primary not in set(identifier_urls.values()):
        fail(
            f"{source_id} primary URL must match one canonical identifier URL"
        )


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


def validate_formal_provenance_target(
    claim_id: str,
    path_text: str,
    anchor: str,
    text: str,
) -> None:
    """Bind kernel_checked_theorem role to an actual Lean theorem declaration."""
    if not path_text.endswith(".lean"):
        fail(f"{claim_id} FORMAL provenance must point to a .lean source file")
    match = LEAN_THEOREM_ANCHOR.fullmatch(anchor)
    if match is None:
        fail(
            f"{claim_id} FORMAL anchor must have form 'theorem <name>'"
        )
    theorem_name = re.escape(match.group(1))
    declaration = re.compile(
        rf"(?m)^\s*theorem\s+{theorem_name}\b"
    )
    if declaration.search(text) is None:
        fail(
            f"{claim_id} FORMAL anchor does not identify a Lean theorem "
            f"declaration in {path_text}"
        )


def validate_provenance(
    claim_id: str,
    evidence_class: str,
    entries: object,
) -> set[str]:
    """Validate repository evidence and enforce class-appropriate roles."""
    if not isinstance(entries, list) or not entries:
        fail(f"{claim_id} must have repository provenance")

    allowed_roles = ALLOWED_PROVENANCE_ROLES[evidence_class]
    roles: set[str] = set()
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
        role = require_inline_string(
            item.get("role"),
            f"{claim_id} provenance role",
        )
        if role not in allowed_roles:
            fail(
                f"{claim_id} provenance role {role!r} is invalid for "
                f"{evidence_class}"
            )
        roles.add(role)

        path = validate_repository_path(path_text, claim_id)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fail(f"{claim_id} provenance path {path_text!r} unreadable: {exc}")
        if anchor not in text:
            fail(f"{claim_id} anchor {anchor!r} not found in {path_text}")
        if evidence_class == "FORMAL":
            validate_formal_provenance_target(
                claim_id,
                path_text,
                anchor,
                text,
            )

    if evidence_class == "FORMAL" and "kernel_checked_theorem" not in roles:
        fail(f"{claim_id} FORMAL claim requires kernel-checked theorem evidence")
    if evidence_class == "COMPUTATIONAL":
        required = {"implementation", "regression"}
        if not required.issubset(roles):
            fail(
                f"{claim_id} COMPUTATIONAL claim requires implementation "
                "and regression provenance"
            )
    return roles


def validate_falsification(
    claim_id: str,
    value: object,
) -> dict[str, Any]:
    """Require structured, substantive falsification criteria."""
    if not isinstance(value, dict):
        fail(f"{claim_id} falsification must be a structured object")

    expected_keys = {"protocol", "rejection_condition", "controls"}
    if set(value) != expected_keys:
        fail(
            f"{claim_id} falsification keys must be "
            f"{sorted(expected_keys)}"
        )

    protocol = require_substantive_inline(
        value.get("protocol"),
        f"{claim_id} falsification protocol",
        minimum_length=40,
    )
    rejection_condition = require_substantive_inline(
        value.get("rejection_condition"),
        f"{claim_id} falsification rejection_condition",
        minimum_length=40,
    )
    controls_obj = value.get("controls")
    if not isinstance(controls_obj, list) or len(controls_obj) < 2:
        fail(f"{claim_id} falsification requires at least two controls")
    controls = [
        require_substantive_inline(
            control,
            f"{claim_id} falsification control",
            minimum_length=12,
        )
        for control in controls_obj
    ]
    if len(controls) != len(set(controls)):
        fail(f"{claim_id} falsification controls must be unique")

    return {
        "protocol": protocol,
        "rejection_condition": rejection_condition,
        "controls": controls,
    }


def _source_identifier_text(identifiers: dict[str, str]) -> str:
    if not identifiers:
        return "none"
    return ", ".join(
        f"{markdown_text(key)}={markdown_text(identifiers[key])}"
        for key in sorted(identifiers)
    )


def _identifier_url_text(identifier_urls: dict[str, str]) -> str:
    if not identifier_urls:
        return "none"
    return "; ".join(
        f"{markdown_text(key)}={markdown_text(identifier_urls[key])}"
        for key in sorted(identifier_urls)
    )


def _claim_sources_text(sources: list[str]) -> str:
    return ", ".join(markdown_text(source) for source in sources) if sources else "none"


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
        f"**Schema:** `{markdown_code(schema)}`",
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
        kind = validate_source_kind(source_id, source.get("kind"))
        domain = validate_source_domain(source_id, source.get("domain"))
        title = require_inline_string(source.get("title"), f"{source_id} title")
        url = require_inline_string(source.get("url"), f"{source_id} url")
        parsed = validate_source_url(source_id, url)
        identifiers = validate_identifiers(source_id, source.get("identifiers"))
        identifier_urls = validate_identifier_urls(
            source_id,
            identifiers,
            source.get("identifier_urls"),
        )
        validate_primary_source_url(source_id, parsed, identifier_urls)

        lines.extend(
            [
                f"### {markdown_text(source_id)}",
                "",
                f"- **Kind:** `{markdown_code(kind)}`",
                f"- **Domain:** `{markdown_code(domain)}`",
                f"- **Title:** {markdown_text(title)}",
                f"- **Identifiers:** {_source_identifier_text(identifiers)}",
                f"- **Identifier URLs:** {_identifier_url_text(identifier_urls)}",
                f"- **URL:** {markdown_text(url)}",
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

        lines.extend(
            [
                f"### {markdown_text(claim_id)} — {markdown_text(evidence_class)}",
                "",
                f"- **Status:** `{markdown_code(status)}`",
                f"- **Statement:** {markdown_text(statement)}",
            ]
        )

        domain = claim.get("domain")
        if domain is not None:
            exact_domain = require_inline_string(domain, f"{claim_id} domain")
            lines.append(f"- **Domain:** `{markdown_code(exact_domain)}`")

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
                f"- **Sources:** {_claim_sources_text(claim_sources)}",
                f"- **Boundary:** {markdown_text(boundary)}",
            ]
        )

        empirical_status = claim.get("empirical_status")
        if empirical_status is not None:
            exact_empirical_status = require_inline_string(
                empirical_status,
                f"{claim_id} empirical_status",
            )
            lines.append(
                f"- **Empirical status:** `{markdown_code(exact_empirical_status)}`"
            )

        falsification = claim.get("falsification")
        if falsification is not None:
            structured = validate_falsification(claim_id, falsification)
            lines.extend(
                [
                    "- **Falsification protocol:** "
                    + markdown_text(cast(str, structured["protocol"])),
                    "- **Rejection condition:** "
                    + markdown_text(
                        cast(str, structured["rejection_condition"])
                    ),
                    "- **Controls:** "
                    + "; ".join(
                        markdown_text(control)
                        for control in cast(list[str], structured["controls"])
                    ),
                ]
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
                f"  - `{markdown_code(path_text)}` — "
                f"`{markdown_code(anchor)}` "
                f"(`{markdown_code(role)}`)"
            )
        lines.append("")

    lines.extend(
        [
            "## Governance",
            "",
            "1. New cross-domain public-facing claims require a stable "
            "`COSMO-D-###` ID.",
            "2. **SCIENTIFIC** claims require external source records from "
            "the same controlled scientific domain.",
            "3. **HYPOTHESIS** claims must remain `PROPOSED` and include "
            "structured falsification criteria.",
            "4. **SYMBOLIC** claims require `empirical_status = NON_EMPIRICAL`.",
            "5. **FORMAL** and **COMPUTATIONAL** claims require reviewed, "
            "class-appropriate repository provenance.",
            "6. Multi-accession source records must independently bind every "
            "URL-addressable identifier.",
            "7. Positive public cross-domain causal/mechanistic assertions "
            "must carry a ledger claim ID.",
            "8. This Markdown file must exactly match the canonical JSON rendering.",
            "",
        ]
    )
    return "\n".join(lines)


def paragraph_domains(text: str) -> set[str]:
    """Return controlled semantic domains named in one public paragraph."""
    return {
        domain
        for domain, pattern in PUBLIC_DOMAIN_PATTERNS.items()
        if pattern.search(text) is not None
    }


def validate_public_claim_text(
    path_text: str,
    text: str,
    claim_ids: set[str],
) -> None:
    """Reject unledgered positive cross-domain causal/mechanistic assertions."""
    paragraphs = re.split(r"\n\s*\n", text)
    for paragraph_number, paragraph in enumerate(paragraphs, start=1):
        compact = " ".join(paragraph.split())
        if not compact:
            continue
        if (
            "\\begin{tabular}" in paragraph
            or "\\begin{longtable}" in paragraph
            or "```" in paragraph
            or compact.startswith("|")
        ):
            continue
        domains = paragraph_domains(compact)
        if len(domains) < 2:
            continue
        if PUBLIC_ASSERTION_RE.search(compact) is None:
            continue
        if PUBLIC_NEGATION_RE.search(compact) is not None:
            continue
        present_ids = set(CLAIM_ID_SEARCH.findall(compact))
        if not present_ids:
            fail(
                f"{path_text} paragraph {paragraph_number} contains an "
                "unledgered positive cross-domain assertion involving "
                f"{sorted(domains)}"
            )
        unknown = present_ids - claim_ids
        if unknown:
            fail(
                f"{path_text} paragraph {paragraph_number} references "
                f"unknown claim IDs {sorted(unknown)}"
            )


def validate_scientific_sources(
    claim_id: str,
    claim_domain: str,
    source_ids: list[str],
    source_kinds: dict[str, str],
    source_domains: dict[str, str],
) -> None:
    """Require scholarly sources from the same controlled scientific domain."""
    if not source_ids:
        fail(f"{claim_id} SCIENTIFIC claim requires an external source")
    for source_id in source_ids:
        if source_kinds[source_id] not in ALLOWED_SOURCE_KINDS:
            fail(
                f"{claim_id} SCIENTIFIC claim uses non-scholarly "
                f"source {source_id}"
            )
        if source_domains[source_id] != claim_domain:
            fail(
                f"{claim_id} SCIENTIFIC domain {claim_domain!r} "
                f"does not match source {source_id} domain "
                f"{source_domains[source_id]!r}"
            )


def validate_public_documents(claim_ids: set[str]) -> None:
    """Apply the public cross-domain claim-ID guard to governed documents."""
    for path_text in PUBLIC_GOVERNED_PATHS:
        path = ROOT / path_text
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fail(f"cannot read governed public document {path_text}: {exc}")
        validate_public_claim_text(path_text, text, claim_ids)


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
    source_kinds: dict[str, str] = {}
    source_domains: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, dict):
            fail("source entries must be objects")
        source_id = require_inline_string(source.get("id"), "source id")
        if SOURCE_ID.fullmatch(source_id) is None:
            fail(f"invalid source id {source_id!r}")
        if source_id in source_ids:
            fail(f"duplicate source id {source_id}")
        source_ids.add(source_id)

        kind = validate_source_kind(source_id, source.get("kind"))
        source_kinds[source_id] = kind
        domain = validate_source_domain(source_id, source.get("domain"))
        source_domains[source_id] = domain
        require_inline_string(source.get("title"), f"{source_id} title")
        parsed = validate_source_url(source_id, source.get("url"))
        identifiers = validate_identifiers(source_id, source.get("identifiers"))
        identifier_urls = validate_identifier_urls(
            source_id,
            identifiers,
            source.get("identifier_urls"),
        )
        validate_primary_source_url(source_id, parsed, identifier_urls)

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
        validate_provenance(
            claim_id,
            evidence_class,
            claim.get("provenance"),
        )

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
        domain = claim.get("domain")
        if evidence_class == "SCIENTIFIC":
            claim_domain = validate_source_domain(claim_id, domain)
            validate_scientific_sources(
                claim_id,
                claim_domain,
                validated_sources,
                source_kinds,
                source_domains,
            )
        elif domain is not None:
            fail(f"{claim_id} non-SCIENTIFIC claim may not set domain")

        if evidence_class == "HYPOTHESIS":
            validate_falsification(claim_id, falsification)
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

    validate_public_documents(claim_ids)

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
