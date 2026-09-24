#!/usr/bin/env python3
"""Validate the Phase D COSMO claim ledger and canonical Markdown index."""

from __future__ import annotations

import ast
import html
import ipaddress
import json
import re
import runpy
import subprocess
import unittest
from pathlib import Path
from typing import Any, Never, cast
from urllib.parse import SplitResult, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "claims" / "claim-ledger.json"
INDEX_PATH = ROOT / "CLAIM-LEDGER.md"
PROTECTED_LEAN_COMPILE_SCRIPT = ROOT / "scripts" / "run-lean-verified-reuse-ci.sh"

CLASSES = ("FORMAL", "COMPUTATIONAL", "SCIENTIFIC", "HYPOTHESIS", "SYMBOLIC")
CLAIM_ID = re.compile(r"COSMO-D-[0-9]{3}$")
CLAIM_ID_SEARCH = re.compile(r"\bCOSMO-D-[0-9]{3}\b")
SOURCE_ID = re.compile(r"SRC-[A-Z0-9][A-Z0-9._-]*$")
LEAN_THEOREM_ANCHOR = re.compile(
    r"theorem ([A-Za-z_][A-Za-z0-9_']*)\b.+:=\s*by$"
)
PUBLIC_CROSS_DOMAIN_GOVERNING_CLASSES = frozenset({"HYPOTHESIS", "SYMBOLIC"})
IDENTIFIER_PATTERNS: dict[str, re.Pattern[str]] = {
    "PMID": re.compile(r"[1-9][0-9]{0,7}$"),
    "PMCID": re.compile(r"PMC[1-9][0-9]*$"),
    "DOI": re.compile(r"10\.[0-9]{4,9}/[^\s]+$"),
    "RefSeq": re.compile(r"[A-Z]{2}_[0-9]+\.[0-9]+$"),
    "year": re.compile(r"(?:19|20)[0-9]{2}$"),
}
URL_BOUND_IDENTIFIERS = frozenset({"PMID", "PMCID", "DOI", "RefSeq"})
PINNED_SCIENTIFIC_CLAIM_SOURCES: dict[str, tuple[str, ...]] = {
    "COSMO-D-004": ("SRC-SPIN8-PTEP-2021",),
    "COSMO-D-005": ("SRC-SIS2-PMID-25590815",),
    "COSMO-D-006": ("SRC-HPV16-REFSEQ",),
    "COSMO-D-007": ("SRC-HPV16-E6E7-PMID-17645777",),
    "COSMO-D-008": ("SRC-HPV-P16-PMC8409095",),
}
PINNED_REVIEWED_SCIENTIFIC_STATEMENTS: dict[str, str] = {
    "COSMO-D-004": (
        "Spin(8) has triality symmetry with an S3 outer automorphism action "
        "that permutes its vector and two spinor eight-dimensional representations."
    ),
    "COSMO-D-005": (
        "The ambient-pressure phase of SiS2 is orthorhombic and contains chains "
        "of distorted edge-sharing SiS4 tetrahedra."
    ),
    "COSMO-D-006": (
        "The NCBI reference sequence used for human papillomavirus type 16 in "
        "this ledger is RefSeq NC_001526.4."
    ),
    "COSMO-D-007": (
        "High-risk HPV E6 and E7 proteins are established carcinogenesis factors; "
        "E6 promotes p53 degradation and E7 disrupts pRb/E2F control."
    ),
    "COSMO-D-008": (
        "p16 immunohistochemistry is used as a surrogate marker for HPV-associated "
        "disease in some clinical contexts, but p16 positivity is not identical to "
        "direct evidence of active E6/E7 transcription."
    ),
}
PINNED_REVIEWED_CLAIM_RECORDS: dict[str, dict[str, Any]] = cast(
    dict[str, dict[str, Any]],
    json.loads(
        r'''{
  "COSMO-D-001": {
    "id": "COSMO-D-001",
    "class": "FORMAL",
    "status": "SUPPORTED",
    "statement": "For every CosmoLayer, six applications of the authoritative Lean transition return the layer to itself.",
    "provenance": [
      {
        "path": "cosmovirus.lean",
        "anchor": "theorem six_step_periodic (layer : CosmoLayer) : psiIterate 6 layer = layer := by",
        "role": "kernel_checked_theorem"
      }
    ],
    "sources": [],
    "falsification": null,
    "boundary": "This is a theorem about the finite state machine only; it is not a physical periodicity claim."
  },
  "COSMO-D-002": {
    "id": "COSMO-D-002",
    "class": "FORMAL",
    "status": "SUPPORTED",
    "statement": "Every authoritative COSMO layer reaches every other layer within one complete six-state orbit.",
    "provenance": [
      {
        "path": "cosmovirus.lean",
        "anchor": "theorem every_layer_reachable (source target : CosmoLayer) : ReachesWithinCycle source target := by",
        "role": "kernel_checked_theorem"
      }
    ],
    "sources": [],
    "falsification": null,
    "boundary": "Reachability is defined inside the project state machine."
  },
  "COSMO-D-003": {
    "id": "COSMO-D-003",
    "class": "COMPUTATIONAL",
    "status": "SUPPORTED",
    "statement": "The Phase B3 Python reference generator deterministically constructs 240 unique E8 roots with rank 8 and squared norm 2, and the canonical table is bound to a reviewed SHA-256.",
    "provenance": [
      {
        "path": "cosmo_core/e8.py",
        "anchor": "def validate_e8_root_system",
        "role": "implementation"
      },
      {
        "path": "tests/test_phase_b3.py",
        "anchor": "test_root_system_report_has_rank_eight_and_norm_two",
        "role": "regression"
      }
    ],
    "sources": [
      "SRC-E8-MATHWORLD"
    ],
    "falsification": null,
    "boundary": "This is deterministic computational evidence; the local Lean core does not yet formalize the E8 root construction."
  },
  "COSMO-D-004": {
    "id": "COSMO-D-004",
    "class": "SCIENTIFIC",
    "status": "SUPPORTED",
    "statement": "Spin(8) has triality symmetry with an S3 outer automorphism action that permutes its vector and two spinor eight-dimensional representations.",
    "provenance": [
      {
        "path": "cosmovirus.tex",
        "anchor": "COSMO-D-004",
        "role": "documented_context"
      }
    ],
    "sources": [
      "SRC-SPIN8-PTEP-2021"
    ],
    "falsification": null,
    "boundary": "This mathematical fact does not establish a mechanism connecting Spin(8) triality to HPV, capsids, SiS2, or cosmology.",
    "domain": "mathematics"
  },
  "COSMO-D-005": {
    "id": "COSMO-D-005",
    "class": "SCIENTIFIC",
    "status": "SUPPORTED",
    "statement": "The ambient-pressure phase of SiS2 is orthorhombic and contains chains of distorted edge-sharing SiS4 tetrahedra.",
    "provenance": [
      {
        "path": "cosmovirus.tex",
        "anchor": "COSMO-D-005",
        "role": "documented_context"
      }
    ],
    "sources": [
      "SRC-SIS2-PMID-25590815"
    ],
    "falsification": null,
    "boundary": "This crystallographic fact does not support COSMO's symbolic substrate or life-code interpretation.",
    "domain": "materials_science"
  },
  "COSMO-D-006": {
    "id": "COSMO-D-006",
    "class": "SCIENTIFIC",
    "status": "SUPPORTED",
    "statement": "The NCBI reference sequence used for human papillomavirus type 16 in this ledger is RefSeq NC_001526.4.",
    "provenance": [
      {
        "path": "CLAIM-LEDGER.md",
        "anchor": "NC_001526.4",
        "role": "provenance_record"
      }
    ],
    "sources": [
      "SRC-HPV16-REFSEQ"
    ],
    "falsification": null,
    "boundary": "The accession identifies a reference genome; it does not validate COSMO's state-machine use of the HPV16Layer label.",
    "domain": "biomedicine"
  },
  "COSMO-D-007": {
    "id": "COSMO-D-007",
    "class": "SCIENTIFIC",
    "status": "SUPPORTED",
    "statement": "High-risk HPV E6 and E7 proteins are established carcinogenesis factors; E6 promotes p53 degradation and E7 disrupts pRb/E2F control.",
    "provenance": [
      {
        "path": "cosmovirus.tex",
        "anchor": "COSMO-D-007",
        "role": "documented_context"
      }
    ],
    "sources": [
      "SRC-HPV16-E6E7-PMID-17645777"
    ],
    "falsification": null,
    "boundary": "This biomedical mechanism is external scientific context and is not a mechanism for COSMO transitions.",
    "domain": "biomedicine"
  },
  "COSMO-D-008": {
    "id": "COSMO-D-008",
    "class": "SCIENTIFIC",
    "status": "SUPPORTED_WITH_SCOPE",
    "statement": "p16 immunohistochemistry is used as a surrogate marker for HPV-associated disease in some clinical contexts, but p16 positivity is not identical to direct evidence of active E6/E7 transcription.",
    "provenance": [
      {
        "path": "cosmovirus.tex",
        "anchor": "COSMO-D-008",
        "role": "documented_context"
      }
    ],
    "sources": [
      "SRC-HPV-P16-PMC8409095"
    ],
    "falsification": null,
    "boundary": "COSMO must not equate a generic p16-positive label with HPV16 infection or active viral transcription.",
    "domain": "biomedicine"
  },
  "COSMO-D-009": {
    "id": "COSMO-D-009",
    "class": "SYMBOLIC",
    "status": "PROJECT_DEFINED",
    "statement": "The byte-to-cuneiform labels in COSMO are project-defined symbolic annotations.",
    "provenance": [
      {
        "path": "cosmovirus.lean",
        "anchor": "def cuneiformAnnotation",
        "role": "project_definition"
      },
      {
        "path": "KNOWN_LIMITATIONS.md",
        "anchor": "Cuneiform strings are project-defined symbolic annotations",
        "role": "scope_boundary"
      }
    ],
    "sources": [],
    "falsification": null,
    "boundary": "They are not a decipherment, transliteration, translation, archaeological attribution, or historical sentence.",
    "empirical_status": "NON_EMPIRICAL"
  },
  "COSMO-D-010": {
    "id": "COSMO-D-010",
    "class": "SYMBOLIC",
    "status": "PROJECT_DEFINED",
    "statement": "COSMO's language of undivided cosmic symmetry, life-code substrate, infected reality, and Ouroboros self-causation is symbolic/interpretive vocabulary.",
    "provenance": [
      {
        "path": "cosmovirus.tex",
        "anchor": "COSMO-D-010",
        "role": "symbolic_section"
      }
    ],
    "sources": [],
    "falsification": null,
    "boundary": "These phrases are not empirical cosmology, materials science, virology, or causal-mechanism claims.",
    "empirical_status": "NON_EMPIRICAL"
  },
  "COSMO-D-011": {
    "id": "COSMO-D-011",
    "class": "SYMBOLIC",
    "status": "PROJECT_DEFINED",
    "statement": "The association of Spin(8) triality with HPV capsid branching or trimerization is a symbolic cross-domain association in the current repository.",
    "provenance": [
      {
        "path": "cosmovirus.tex",
        "anchor": "capsid",
        "role": "historical_symbolic_mapping"
      }
    ],
    "sources": [],
    "falsification": null,
    "boundary": "The repository does not claim an established biological mechanism connecting Spin(8) triality to HPV capsid assembly.",
    "empirical_status": "NON_EMPIRICAL"
  },
  "COSMO-D-012": {
    "id": "COSMO-D-012",
    "class": "HYPOTHESIS",
    "status": "PROPOSED",
    "statement": "A future quantitatively specified mapping from triality-derived features to an HPV/capsid observable could be tested for predictive value against matched controls.",
    "provenance": [
      {
        "path": "CLAIM-LEDGER.md",
        "anchor": "COSMO-D-012",
        "role": "hypothesis_definition"
      }
    ],
    "sources": [],
    "falsification": {
      "protocol": "Pre-register the triality-derived mapping, target observable, dataset split, evaluation metric, matched baselines, and decision threshold before evaluating held-out data.",
      "rejection_condition": "Reject the hypothesis if held-out performance fails the predeclared threshold or is not distinguishable from the matched control baselines.",
      "controls": [
        "Matched baseline models fixed before held-out evaluation",
        "Held-out data excluded from mapping and threshold selection"
      ]
    },
    "boundary": "No such predictive result is currently claimed."
  },
  "COSMO-D-013": {
    "id": "COSMO-D-013",
    "class": "SYMBOLIC",
    "status": "PROJECT_DEFINED",
    "statement": "The use of SiS2Substrate as a COSMO state name is symbolic project vocabulary rather than evidence that silicon disulfide is a biological life-code substrate.",
    "provenance": [
      {
        "path": "cosmovirus.lean",
        "anchor": "SiS2Substrate",
        "role": "state_label"
      }
    ],
    "sources": [
      "SRC-SIS2-PMID-25590815"
    ],
    "falsification": null,
    "boundary": "The scientific source does not establish a biological substrate role; it supports SiS2 crystal-structure facts only.",
    "empirical_status": "NON_EMPIRICAL"
  },
  "COSMO-D-014": {
    "id": "COSMO-D-014",
    "class": "COMPUTATIONAL",
    "status": "SUPPORTED",
    "statement": "Within the documented SECDED capability, the Phase B5 software storage pipeline deterministically recovers the original TriadicLattice through bytes, ECC, ACGT, corruption, correction, bytes, and cube reconstruction.",
    "provenance": [
      {
        "path": "cosmo_core/storage.py",
        "anchor": "def recover_cube_storage",
        "role": "implementation"
      },
      {
        "path": "tests/test_phase_b5.py",
        "anchor": "test_full_cube_recovers_one_bit_error_in_every_codeword",
        "role": "regression"
      }
    ],
    "sources": [],
    "falsification": null,
    "boundary": "This is a software codec result, not a laboratory DNA-storage or physical Rubik's Cube claim."
  }
}'''
    ),
)
PINNED_REVIEWED_CLAIM_IDS = tuple(PINNED_REVIEWED_CLAIM_RECORDS)
PINNED_FORMAL_PROVENANCE: dict[str, tuple[str, str]] = {
    "COSMO-D-001": (
        "cosmovirus.lean",
        "theorem six_step_periodic (layer : CosmoLayer) : "
        "psiIterate 6 layer = layer := by",
    ),
    "COSMO-D-002": (
        "cosmovirus.lean",
        "theorem every_layer_reachable (source target : CosmoLayer) : "
        "ReachesWithinCycle source target := by",
    ),
}
PINNED_REVIEWED_SOURCE_RECORDS: dict[str, tuple[str, str, str, str]] = {
    "SRC-E8-MATHWORLD": (
        "scholarly_reference",
        "Gosset Polytope — E8 root polytope",
        "https://mathworld.wolfram.com/GossetPolytope.html",
        "mathematics",
    ),
    "SRC-SPIN8-PTEP-2021": (
        "scholarly_article",
        "Vertex operator superalgebra/sigma model correspondences: The four-torus case",
        "https://academic.oup.com/ptep/article/2021/8/08B102/6353037",
        "mathematics",
    ),
    "SRC-SIS2-PMID-25590815": (
        "peer_reviewed_article",
        "Two high-pressure phases of SiS2 as missing links between the extremes of only edge-sharing and only corner-sharing tetrahedra",
        "https://pubmed.ncbi.nlm.nih.gov/25590815/",
        "materials_science",
    ),
    "SRC-HPV16-REFSEQ": (
        "official_database",
        "Human papillomavirus type 16, complete genome",
        "https://www.ncbi.nlm.nih.gov/nuccore/NC_001526.4",
        "biomedicine",
    ),
    "SRC-HPV16-E6E7-PMID-17645777": (
        "peer_reviewed_review",
        "Basic mechanisms of high-risk human papillomavirus-induced carcinogenesis: Roles of E6 and E7 proteins",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC11158331/",
        "biomedicine",
    ),
    "SRC-HPV-P16-PMC8409095": (
        "peer_reviewed_review",
        "Biology of HPV Mediated Carcinogenesis and Tumor Progression",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC8409095/",
        "biomedicine",
    ),
}
PINNED_REVIEWED_SOURCE_IDENTIFIERS: dict[str, dict[str, str]] = {
    "SRC-E8-MATHWORLD": {},
    "SRC-SPIN8-PTEP-2021": {
        "year": "2021",
    },
    "SRC-SIS2-PMID-25590815": {
        "PMID": "25590815",
        "DOI": "10.1021/ic501825r",
    },
    "SRC-HPV16-E6E7-PMID-17645777": {
        "PMID": "17645777",
        "PMCID": "PMC11158331",
    },
    "SRC-HPV16-REFSEQ": {
        "RefSeq": "NC_001526.4",
    },
    "SRC-HPV-P16-PMC8409095": {
        "PMCID": "PMC8409095",
    },
}
PYTHON_DEF_ANCHOR = re.compile(r"def ([A-Za-z_][A-Za-z0-9_]*)$")
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
PLACEHOLDER_FILLER_TOKENS = frozenset(
    {
        "a",
        "condition",
        "control",
        "criterion",
        "criteria",
        "field",
        "four",
        "here",
        "item",
        "n",
        "one",
        "protocol",
        "test",
        "text",
        "three",
        "two",
        "value",
    }
)
PUBLIC_GOVERNED_SUFFIXES = frozenset({".md", ".tex"})
PUBLIC_DISCOVERY_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".lake",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "build",
        "dist",
        "site-packages",
    }
)
LATEX_PUBLIC_MACROS: dict[str, str] = {
    r"\TRI": "triality",
    r"\HPV": "HPV16",
    r"\SiS": "SiS2",
    r"\EEs": "E8",
    r"\Ouro": "Ouroboros",
}
PUBLIC_DOMAIN_PATTERNS: dict[str, re.Pattern[str]] = {
    "mathematics": re.compile(
        r"(?:(?<!\w)Spin\(8\)(?!\w)|\b(?:triality|E8|E_8|Weyl)\b)",
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
PUBLIC_ENTITY_PATTERNS: dict[str, re.Pattern[str]] = {
    "spin8": re.compile(r"(?<!\w)Spin\(8\)(?!\w)", re.IGNORECASE),
    "triality": re.compile(r"\btriality\b", re.IGNORECASE),
    "e8": re.compile(r"\b(?:E8|E_8)\b", re.IGNORECASE),
    "weyl": re.compile(r"\bWeyl\b", re.IGNORECASE),
    "hpv": re.compile(r"\b(?:HPV16|HPV)\b", re.IGNORECASE),
    "capsid": re.compile(r"\bcapsid\b", re.IGNORECASE),
    "e6": re.compile(r"\bE6\b", re.IGNORECASE),
    "e7": re.compile(r"\bE7\b", re.IGNORECASE),
    "p16": re.compile(r"\bp16\b", re.IGNORECASE),
    "sis2": re.compile(
        r"\b(?:SiS2|SiS_2|silicon disulfide)\b",
        re.IGNORECASE,
    ),
    "cuneiform": re.compile(r"\bcuneiform\b", re.IGNORECASE),
    "sumerian": re.compile(r"\bSumerian\b", re.IGNORECASE),
    "archaeology": re.compile(r"\barchaeolog(?:y|ical)\b", re.IGNORECASE),
    "cosmology": re.compile(r"\b(?:cosmic|cosmology)\b", re.IGNORECASE),
    "ouroboros": re.compile(r"\bOuroboros\b", re.IGNORECASE),
}
PUBLIC_ASSERTION_RE = re.compile(
    r"\b(?:causes?|caused|drives?|driven|produces?|produced|"
    r"determines?|determined|explains?|explained|proves?|proved|"
    r"demonstrates?|demonstrated|establishes?|established|"
    r"validates?|validated|predicts?|predicted|induces?|induced|"
    r"triggers?|triggered|promotes?|promoted|mediates?|mediated|"
    r"enables?|enabled|controls?(?!\s*:)|controlled|regulates?|regulated|"
    r"modulates?|modulated|governs?|governed|influences?|influenced|"
    r"leads?\s+to|results?\s+in|gives?\s+rise\s+to|"
    r"contributes?\s+to|corresponds?\s+to|maps?\s+to|"
    r"is\s+(?:an?\s+|the\s+)?mechanism\s+(?:for|of|behind)|"
    r"mechanism\s+(?:connects?|links?|drives?|causes?)|"
    r"is\s+responsible\s+for)\b",
    re.IGNORECASE,
)
PUBLIC_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|cannot|can't|does\s+not|do\s+not|"
    r"is\s+not|are\s+not|without)\b",
    re.IGNORECASE,
)


class DuplicateJsonKeyError(ValueError):
    """Raised when canonical JSON contains the same object key twice."""


class NonStandardJsonConstantError(ValueError):
    """Raised when Python's permissive JSON parser sees NaN/Infinity."""


def reject_nonstandard_json_constant(value: str) -> Never:
    """Reject constants forbidden by RFC 8259 JSON."""
    raise NonStandardJsonConstantError(
        f"non-standard JSON constant {value!r}"
    )


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
            parse_constant=reject_nonstandard_json_constant,
        )
    except (
        json.JSONDecodeError,
        DuplicateJsonKeyError,
        NonStandardJsonConstantError,
    ) as exc:
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


def is_placeholder_only_text(text: str) -> bool:
    """Detect repeated/decorated placeholder prose, not only one exact token."""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    if not normalized:
        return True
    placeholder_tokens = {
        "tbd",
        "todo",
        "na",
        "none",
        "unknown",
        "placeholder",
        "later",
    }
    allowed = placeholder_tokens | PLACEHOLDER_FILLER_TOKENS
    tokens = normalized.split()
    return all(token in allowed or token.isdigit() for token in tokens)


def require_substantive_inline(
    value: object,
    label: str,
    *,
    minimum_length: int = 24,
) -> str:
    """Reject placeholders where the governance contract requires real criteria."""
    text = require_inline_string(value, label)
    if text.strip().lower() in PLACEHOLDER_TEXT or is_placeholder_only_text(text):
        fail(f"{label} may not be a placeholder")
    if len(text.strip()) < minimum_length:
        fail(f"{label} must contain substantive criteria")
    return text


def markdown_text(value: str) -> str:
    """Escape HTML and active inline-Markdown delimiters in visible text."""
    escaped = html.escape(value, quote=False)
    replacements = {
        "\\": "&#92;",
        "`": "&#96;",
        "*": "&#42;",
        "[": "&#91;",
        "]": "&#93;",
        "!": "&#33;",
    }
    return "".join(replacements.get(character, character) for character in escaped)


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
    validate_source_hostname(source_id, parsed.hostname)
    if parsed.username is not None or parsed.password is not None:
        fail(f"{source_id} URL may not contain userinfo")
    return parsed


def validate_source_hostname(source_id: str, hostname: str) -> None:
    """Require a valid IP literal or DNS hostname for external source URLs."""
    try:
        ipaddress.ip_address(hostname)
        return
    except ValueError:
        pass

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        fail(f"{source_id} hostname is not valid IDNA: {exc}")

    if (
        not ascii_hostname
        or len(ascii_hostname) > 253
        or ascii_hostname.startswith(".")
        or ascii_hostname.endswith(".")
    ):
        fail(f"{source_id} has invalid DNS hostname {hostname!r}")

    label_pattern = re.compile(
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    )
    labels = ascii_hostname.split(".")
    if len(labels) < 2 or any(
        label_pattern.fullmatch(label) is None for label in labels
    ):
        fail(f"{source_id} has invalid DNS hostname {hostname!r}")


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


def validate_reviewed_source_record(
    source_id: str,
    kind: str,
    title: str,
    url: str,
    domain: str,
) -> None:
    """Bind each reviewed source ID to its exact reviewed record."""
    expected = PINNED_REVIEWED_SOURCE_RECORDS.get(source_id)
    if expected is None:
        fail(f"{source_id} lacks a reviewed source-record binding")
    actual = (kind, title, url, domain)
    if actual != expected:
        fail(
            f"{source_id} source record does not match reviewed identity"
        )


def validate_reviewed_source_identity(
    source_id: str,
    identifiers: dict[str, str],
) -> None:
    """Bind every reviewed identifier, including non-URL metadata, to its source."""
    expected = PINNED_REVIEWED_SOURCE_IDENTIFIERS.get(source_id)
    if expected is None:
        fail(f"{source_id} lacks a reviewed identifier binding")
    if identifiers != expected:
        fail(
            f"{source_id} identifiers do not match the reviewed source "
            f"identity: expected {expected!r}"
        )


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


def strip_lean_comments(text: str) -> str:
    """Remove Lean comments and string contents while preserving line structure."""
    result: list[str] = []
    index = 0
    block_depth = 0
    in_string = False

    while index < len(text):
        if block_depth:
            if text.startswith("/-", index):
                result.extend((" ", " "))
                block_depth += 1
                index += 2
                continue
            if text.startswith("-/", index):
                result.extend((" ", " "))
                block_depth -= 1
                index += 2
                continue

            character = text[index]
            result.append("\n" if character == "\n" else " ")
            index += 1
            continue

        character = text[index]
        if in_string:
            result.append("\n" if character == "\n" else " ")
            if character == "\\" and index + 1 < len(text):
                escaped = text[index + 1]
                result.append("\n" if escaped == "\n" else " ")
                index += 2
                continue
            if character == '"':
                in_string = False
            index += 1
            continue

        if text.startswith("--", index):
            result.extend((" ", " "))
            index += 2
            while index < len(text) and text[index] != "\n":
                result.append(" ")
                index += 1
            continue

        if text.startswith("/-", index):
            result.extend((" ", " "))
            block_depth = 1
            index += 2
            continue

        if character == '"':
            result.append(" ")
            in_string = True
        else:
            result.append(character)
        index += 1

    return "".join(result)


def protected_lean_sources() -> set[str]:
    """Execute the protected runner's source-inventory mode."""
    try:
        completed = subprocess.run(
            [
                "bash",
                str(PROTECTED_LEAN_COMPILE_SCRIPT),
                "--print-project-sources",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        fail(f"cannot execute protected Lean source inventory: {exc}")

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        fail(
            "protected Lean source inventory failed"
            + (f": {detail}" if detail else "")
        )

    sources = {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    }
    if not sources:
        fail("protected Lean source inventory returned no project modules")
    for source in sources:
        relative = Path(source)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.suffix != ".lean"
            or len(relative.parts) != 1
        ):
            fail(f"protected Lean source inventory contains invalid path {source!r}")
    return sources


def normalize_lean_declaration(text: str) -> str:
    """Normalize insignificant whitespace for one Lean declaration anchor."""
    return " ".join(text.split())


def validate_formal_provenance_target(
    claim_id: str,
    path_text: str,
    anchor: str,
    text: str,
) -> None:
    """Bind FORMAL evidence to an exact theorem in the protected Lean closure."""
    expected = PINNED_FORMAL_PROVENANCE.get(claim_id)
    if expected is not None and (path_text, anchor) != expected:
        fail(
            f"{claim_id} FORMAL provenance does not match its reviewed theorem"
        )
    if not path_text.endswith(".lean"):
        fail(f"{claim_id} FORMAL provenance must point to a .lean source file")
    if path_text not in protected_lean_sources():
        fail(
            f"{claim_id} FORMAL provenance {path_text!r} is not compiled "
            "by the protected Lean integrity pipeline"
        )
    if LEAN_THEOREM_ANCHOR.fullmatch(anchor) is None:
        fail(
            f"{claim_id} FORMAL anchor must contain the complete theorem "
            "declaration through ':= by'"
        )
    comment_free_text = strip_lean_comments(text)
    normalized_source = normalize_lean_declaration(comment_free_text)
    normalized_anchor = normalize_lean_declaration(anchor)
    if normalized_anchor not in normalized_source:
        fail(
            f"{claim_id} FORMAL anchor does not identify the exact Lean "
            f"theorem proposition in {path_text}"
        )


class _YieldFinder(ast.NodeVisitor):
    """Detect yield in one function body without descending into nested functions."""

    def __init__(self) -> None:
        self.found = False

    def visit_Yield(self, node: ast.Yield) -> None:
        self.found = True

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self.found = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def function_contains_yield(node: ast.FunctionDef) -> bool:
    finder = _YieldFinder()
    for statement in node.body:
        finder.visit(statement)
    return finder.found


def locate_unittest_regression(
    claim_id: str,
    path_text: str,
    anchor: str,
    text: str,
) -> tuple[str, ast.FunctionDef]:
    """Locate exactly one synchronous, non-generator unittest method."""
    if not path_text.startswith("tests/") or not Path(path_text).name.startswith("test_"):
        fail(
            f"{claim_id} regression provenance must point to a tests/test_*.py file"
        )
    if not anchor.startswith("test_"):
        fail(f"{claim_id} regression anchor must name a unittest test method")
    try:
        tree = ast.parse(text, filename=path_text)
    except SyntaxError as exc:
        fail(f"{claim_id} regression source {path_text} is invalid Python: {exc}")

    matches: list[tuple[str, ast.FunctionDef]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if isinstance(member, ast.AsyncFunctionDef) and member.name == anchor:
                fail(
                    f"{claim_id} regression anchor {anchor!r} may not be async; "
                    "Phase D requires a synchronously executed unittest method"
                )
            if isinstance(member, ast.FunctionDef) and member.name == anchor:
                if function_contains_yield(member):
                    fail(
                        f"{claim_id} regression anchor {anchor!r} may not be "
                        "a generator; its body must execute synchronously"
                    )
                matches.append((node.name, member))
    if len(matches) != 1:
        fail(
            f"{claim_id} regression anchor {anchor!r} must identify exactly "
            f"one unittest method in {path_text}"
        )
    return matches[0]


def _implementation_module_name(path_text: str) -> str:
    relative = Path(path_text)
    return ".".join(relative.with_suffix("").parts)


def _package_reexports_function(
    module_name: str,
    function_name: str,
) -> bool:
    package_path = ROOT / "cosmo_core" / "__init__.py"
    try:
        tree = ast.parse(
            package_path.read_text(encoding="utf-8"),
            filename=str(package_path),
        )
    except (OSError, UnicodeError, SyntaxError) as exc:
        fail(f"cannot inspect cosmo_core re-exports: {exc}")

    expected_module = module_name.removeprefix("cosmo_core.")
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level != 1 or node.module != expected_module:
            continue
        if any(alias.name == function_name for alias in node.names):
            return True
    return False


def _regression_import_binding(
    regression_tree: ast.Module,
    module_name: str,
    function_name: str,
) -> str | None:
    """Return the actual local name bound to the reviewed implementation import."""
    for node in regression_tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 0:
            continue
        module_matches = node.module == module_name
        if node.module == "cosmo_core":
            module_matches = _package_reexports_function(
                module_name,
                function_name,
            )
        if not module_matches:
            continue
        for alias in node.names:
            if alias.name == function_name:
                return alias.asname or alias.name
    return None


class _CallFinder(ast.NodeVisitor):
    """Find one target call without descending into nested functions."""

    def __init__(self, function_name: str) -> None:
        self.function_name = function_name
        self.found = False

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == self.function_name:
            self.found = True
            return
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def _statement_calls_function(
    statement: ast.stmt,
    function_name: str,
) -> bool:
    finder = _CallFinder(function_name)
    finder.visit(statement)
    return finder.found


def _module_boolean_constants(module: ast.Module) -> dict[str, bool]:
    """Collect simple module booleans only when they have one stable assignment."""
    values: dict[str, bool] = {}
    invalid: set[str] = set()

    def record(name: str, value: ast.expr | None) -> None:
        if (
            name in invalid
            or name in values
            or not isinstance(value, ast.Constant)
            or not isinstance(value.value, bool)
        ):
            invalid.add(name)
            values.pop(name, None)
            return
        values[name] = value.value

    for statement in module.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    record(target.id, statement.value)
        elif isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target,
            ast.Name,
        ):
            record(statement.target.id, statement.value)
        elif isinstance(statement, ast.AugAssign) and isinstance(
            statement.target,
            ast.Name,
        ):
            invalid.add(statement.target.id)
            values.pop(statement.target.id, None)
    return values


def _static_boolean_value(
    expression: ast.expr,
    module_constants: dict[str, bool],
) -> bool | None:
    if isinstance(expression, ast.Constant) and isinstance(expression.value, bool):
        return expression.value
    if isinstance(expression, ast.Name):
        return module_constants.get(expression.id)
    if isinstance(expression, ast.UnaryOp) and isinstance(expression.op, ast.Not):
        operand = _static_boolean_value(expression.operand, module_constants)
        return None if operand is None else not operand
    if isinstance(expression, ast.BoolOp):
        values = [
            _static_boolean_value(value, module_constants)
            for value in expression.values
        ]
        if isinstance(expression.op, ast.And):
            if any(value is False for value in values):
                return False
            if all(value is True for value in values):
                return True
        elif isinstance(expression.op, ast.Or):
            if any(value is True for value in values):
                return True
            if all(value is False for value in values):
                return False
        return None
    if (
        isinstance(expression, ast.Compare)
        and len(expression.ops) == 1
        and len(expression.comparators) == 1
    ):
        left = _static_boolean_value(expression.left, module_constants)
        right = _static_boolean_value(
            expression.comparators[0],
            module_constants,
        )
        if left is None or right is None:
            return None
        operator = expression.ops[0]
        if isinstance(operator, (ast.Is, ast.Eq)):
            return left == right
        if isinstance(operator, (ast.IsNot, ast.NotEq)):
            return left != right
    return None


def _static_iterable_has_items(expression: ast.expr) -> bool | None:
    """Resolve obviously empty/non-empty literal iterables used by for-loops."""
    if isinstance(expression, (ast.List, ast.Tuple, ast.Set)):
        return bool(expression.elts)
    if isinstance(expression, ast.Dict):
        return bool(expression.keys)
    if isinstance(expression, ast.Constant) and isinstance(
        expression.value,
        (str, bytes),
    ):
        return bool(expression.value)
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "range"
        and not expression.keywords
        and 1 <= len(expression.args) <= 3
        and all(
            isinstance(arg, ast.Constant)
            and isinstance(arg.value, int)
            and not isinstance(arg.value, bool)
            for arg in expression.args
        )
    ):
        integer_args = [
            cast(int, cast(ast.Constant, arg).value)
            for arg in expression.args
        ]
        return bool(range(*integer_args))
    return None


def _reachable_statements_call_function(
    statements: list[ast.stmt],
    function_name: str,
    module_constants: dict[str, bool],
) -> bool:
    for statement in statements:
        if isinstance(statement, (ast.Return, ast.Raise)):
            return False

        if isinstance(statement, ast.If):
            condition = _static_boolean_value(
                statement.test,
                module_constants,
            )
            if condition is not None:
                branch = statement.body if condition else statement.orelse
                if _reachable_statements_call_function(
                    branch,
                    function_name,
                    module_constants,
                ):
                    return True
            else:
                if _reachable_statements_call_function(
                    statement.body,
                    function_name,
                    module_constants,
                ):
                    return True
                if _reachable_statements_call_function(
                    statement.orelse,
                    function_name,
                    module_constants,
                ):
                    return True
            continue

        if isinstance(statement, ast.While):
            condition = _static_boolean_value(
                statement.test,
                module_constants,
            )
            if condition is False:
                if _reachable_statements_call_function(
                    statement.orelse,
                    function_name,
                    module_constants,
                ):
                    return True
                continue
            if _reachable_statements_call_function(
                statement.body,
                function_name,
                module_constants,
            ):
                return True
            if condition is None and _reachable_statements_call_function(
                statement.orelse,
                function_name,
                module_constants,
            ):
                return True
            continue

        if isinstance(statement, (ast.For, ast.AsyncFor)):
            has_items = _static_iterable_has_items(statement.iter)
            if has_items is False:
                if _reachable_statements_call_function(
                    statement.orelse,
                    function_name,
                    module_constants,
                ):
                    return True
                continue
            if _reachable_statements_call_function(
                statement.body,
                function_name,
                module_constants,
            ):
                return True
            if _reachable_statements_call_function(
                statement.orelse,
                function_name,
                module_constants,
            ):
                return True
            continue

        if _statement_calls_function(statement, function_name):
            return True
    return False


def _regression_calls_function(
    method: ast.FunctionDef,
    function_name: str,
    module_constants: dict[str, bool],
) -> bool:
    return _reachable_statements_call_function(
        method.body,
        function_name,
        module_constants,
    )


def validate_computational_evidence_connection(
    claim_id: str,
    implementation_path: str,
    implementation_anchor: str,
    regression_path: str,
    regression_anchor: str,
    regression_text: str,
) -> None:
    """Prove the claimed regression imports and calls the declared implementation."""
    match = PYTHON_DEF_ANCHOR.fullmatch(implementation_anchor)
    if match is None:
        fail(f"{claim_id} implementation anchor is malformed")
    function_name = match.group(1)
    module_name = _implementation_module_name(implementation_path)

    try:
        regression_tree = ast.parse(
            regression_text,
            filename=regression_path,
        )
    except SyntaxError as exc:
        fail(f"{claim_id} regression source {regression_path} is invalid Python: {exc}")

    class_name, method = locate_unittest_regression(
        claim_id,
        regression_path,
        regression_anchor,
        regression_text,
    )
    imported_binding = _regression_import_binding(
        regression_tree,
        module_name,
        function_name,
    )
    if imported_binding is None:
        fail(
            f"{claim_id} regression {regression_path}:{class_name}.{regression_anchor} "
            f"does not import {function_name} from declared implementation "
            f"{implementation_path}"
        )
    module_constants = _module_boolean_constants(regression_tree)
    if not _regression_calls_function(
        method,
        imported_binding,
        module_constants,
    ):
        fail(
            f"{claim_id} regression {regression_path}:{class_name}.{regression_anchor} "
            f"does not call imported implementation binding {imported_binding}"
        )


def validate_computational_implementation_target(
    claim_id: str,
    path_text: str,
    anchor: str,
    text: str,
) -> None:
    """Bind implementation provenance to executable project Python source."""
    if not path_text.startswith("cosmo_core/") or not path_text.endswith(".py"):
        fail(
            f"{claim_id} implementation provenance must point to "
            "cosmo_core/*.py executable source"
        )
    match = PYTHON_DEF_ANCHOR.fullmatch(anchor)
    if match is None:
        fail(
            f"{claim_id} implementation anchor must have form 'def <name>'"
        )
    try:
        tree = ast.parse(text, filename=path_text)
    except SyntaxError as exc:
        fail(f"{claim_id} implementation source {path_text} is invalid Python: {exc}")

    function_name = match.group(1)
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    async_matches = [
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    ]
    if async_matches:
        fail(
            f"{claim_id} implementation anchor {anchor!r} resolves to async "
            "code; Phase D implementation evidence must be synchronous"
        )
    if len(matches) != 1:
        fail(
            f"{claim_id} implementation anchor {anchor!r} must identify "
            f"exactly one top-level function in {path_text}"
        )


def validate_computational_regression_target(
    claim_id: str,
    path_text: str,
    anchor: str,
    path: Path,
    text: str,
) -> None:
    """Execute the exact unittest method claimed as computational evidence."""
    class_name, _method = locate_unittest_regression(
        claim_id,
        path_text,
        anchor,
        text,
    )
    try:
        namespace = runpy.run_path(
            str(path),
            run_name=f"_cosmo_claim_regression_{claim_id.replace('-', '_')}",
        )
    except Exception as exc:
        fail(
            f"{claim_id} cannot load regression evidence {path_text}: "
            f"{type(exc).__name__}: {exc}"
        )

    case_type = namespace.get(class_name)
    if not isinstance(case_type, type) or not issubclass(case_type, unittest.TestCase):
        fail(
            f"{claim_id} regression class {class_name!r} is not a unittest.TestCase"
        )
    case = case_type(anchor)
    result = unittest.TestResult()
    case.run(result)

    if result.testsRun != 1:
        fail(
            f"{claim_id} regression evidence {path_text}:{anchor} did not "
            "execute exactly once"
        )
    if result.skipped:
        fail(
            f"{claim_id} regression evidence {path_text}:{anchor} is skipped"
        )
    if result.expectedFailures:
        fail(
            f"{claim_id} regression evidence {path_text}:{anchor} is marked "
            "as an expected failure"
        )
    if result.failures or result.errors or result.unexpectedSuccesses:
        details = result.failures + result.errors
        rendered = details[0][1].splitlines()[-1] if details else "unexpected success"
        fail(
            f"{claim_id} regression evidence {path_text}:{anchor} did not pass: "
            f"{rendered}"
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
    implementation_evidence: tuple[str, str] | None = None
    regression_evidence: tuple[str, str, str] | None = None
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
        if evidence_class == "FORMAL":
            validate_formal_provenance_target(
                claim_id,
                path_text,
                anchor,
                text,
            )
        else:
            if anchor not in text:
                fail(f"{claim_id} anchor {anchor!r} not found in {path_text}")
            if evidence_class == "COMPUTATIONAL" and role == "implementation":
                validate_computational_implementation_target(
                    claim_id,
                    path_text,
                    anchor,
                    text,
                )
                implementation_evidence = (path_text, anchor)
            if evidence_class == "COMPUTATIONAL" and role == "regression":
                validate_computational_regression_target(
                    claim_id,
                    path_text,
                    anchor,
                    path,
                    text,
                )
                regression_evidence = (path_text, anchor, text)

    if evidence_class == "FORMAL" and "kernel_checked_theorem" not in roles:
        fail(f"{claim_id} FORMAL claim requires kernel-checked theorem evidence")
    if evidence_class == "COMPUTATIONAL":
        required = {"implementation", "regression"}
        if not required.issubset(roles):
            fail(
                f"{claim_id} COMPUTATIONAL claim requires implementation "
                "and regression provenance"
            )
        if implementation_evidence is None or regression_evidence is None:
            fail(
                f"{claim_id} COMPUTATIONAL claim evidence could not be linked"
            )
        validate_computational_evidence_connection(
            claim_id,
            implementation_evidence[0],
            implementation_evidence[1],
            regression_evidence[0],
            regression_evidence[1],
            regression_evidence[2],
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
        source_domain = validate_source_domain(source_id, source.get("domain"))
        title = require_inline_string(source.get("title"), f"{source_id} title")
        url = require_inline_string(source.get("url"), f"{source_id} url")
        validate_reviewed_source_record(
            source_id,
            kind,
            title,
            url,
            source_domain,
        )
        parsed = validate_source_url(source_id, url)
        identifiers = validate_identifiers(source_id, source.get("identifiers"))
        validate_reviewed_source_identity(source_id, identifiers)
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
                f"- **Domain:** `{markdown_code(source_domain)}`",
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

        raw_claim_domain = claim.get("domain")
        if raw_claim_domain is not None:
            exact_domain = require_inline_string(
                raw_claim_domain,
                f"{claim_id} domain",
            )
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


def public_entities(text: str) -> set[str]:
    """Return controlled public entities/concepts named in text."""
    return {
        entity
        for entity, pattern in PUBLIC_ENTITY_PATTERNS.items()
        if pattern.search(text) is not None
    }


def public_claim_semantics() -> dict[str, tuple[set[str], set[str]]]:
    """Build semantic signatures from reviewed claim records when available."""
    ledger = load_json()
    raw_claims = ledger.get("claims")
    if not isinstance(raw_claims, list):
        fail("claims must be an array")

    result: dict[str, tuple[set[str], set[str]]] = {}
    for claim in raw_claims:
        if not isinstance(claim, dict):
            fail("claim entries must be objects")
        claim_id = require_inline_string(claim.get("id"), "claim id")
        semantic_claim = PINNED_REVIEWED_CLAIM_RECORDS.get(claim_id, claim)
        statement = require_inline_string(
            semantic_claim.get("statement"),
            f"{claim_id} statement",
        )
        boundary = require_inline_string(
            semantic_claim.get("boundary"),
            f"{claim_id} boundary",
        )
        combined = statement + " " + boundary
        result[claim_id] = (
            paragraph_domains(combined),
            public_entities(combined),
        )
    return result


def paragraph_domains(text: str) -> set[str]:
    """Return controlled semantic domains named in one public paragraph."""
    return {
        domain
        for domain, pattern in PUBLIC_DOMAIN_PATTERNS.items()
        if pattern.search(text) is not None
    }


def public_assertion_clause(
    text: str,
    assertion: re.Match[str],
) -> str:
    """Return the proposition containing one assertion predicate."""
    left_boundary = 0
    for boundary in re.finditer(
        r"(?:[.!?;,|&]|\b(?:but|however|yet|although|though|while|whereas)\b)",
        text[:assertion.start()],
        re.IGNORECASE,
    ):
        left_boundary = boundary.end()

    right_match = re.search(
        r"(?:[.!?;,|&]|\b(?:but|however|yet|although|though|while|whereas)\b)",
        text[assertion.end():],
        re.IGNORECASE,
    )
    if right_match is None:
        right_boundary = len(text)
    else:
        right_boundary = assertion.end() + right_match.start()

    return text[left_boundary:right_boundary]


def public_assertion_binding_scope(
    text: str,
    assertion: re.Match[str],
) -> str:
    """Return the punctuation-bounded proposition used to bind a claim ID."""
    left_boundary = 0
    for boundary in re.finditer(
        r"(?:[.!?;,|]|\b(?:but|however|yet|although|though|while|whereas)\b)",
        text[:assertion.start()],
        re.IGNORECASE,
    ):
        left_boundary = boundary.end()

    right_match = re.search(
        r"(?:[.!?;,|]|\b(?:but|however|yet)\b)",
        text[assertion.end():],
        re.IGNORECASE,
    )
    if right_match is None:
        right_boundary = len(text)
    else:
        right_boundary = assertion.end() + right_match.start()
    return text[left_boundary:right_boundary]


def public_assertion_is_negated(
    text: str,
    assertion: re.Match[str],
) -> bool:
    """Return whether negation locally governs the assertion predicate."""
    prefix_start = 0
    for boundary in re.finditer(
        r"(?:[.!?;,|]|\b(?:and|but|however|yet|although|though|while|whereas)\b)",
        text[:assertion.start()],
        re.IGNORECASE,
    ):
        prefix_start = boundary.end()
    predicate_prefix = text[prefix_start:assertion.start()]
    predicate_prefix = re.sub(
        r"\bnot\s+only\b",
        "only",
        predicate_prefix,
        flags=re.IGNORECASE,
    )
    if PUBLIC_NEGATION_RE.search(predicate_prefix) is not None:
        return True

    suffix = text[assertion.end():]
    suffix_boundary = re.search(
        r"(?:[.!?;,|]|\b(?:and|but|however|yet|although|though|while|whereas)\b)",
        suffix,
        re.IGNORECASE,
    )
    if suffix_boundary is not None:
        suffix = suffix[:suffix_boundary.start()]
    return re.match(
        r"^\s*(?:no|never|without|not(?!\s+only\b))\b",
        suffix,
        re.IGNORECASE,
    ) is not None


def _blank_non_newlines(value: str) -> str:
    """Replace comment content with spaces while preserving line structure."""
    return "".join("\n" if character == "\n" else " " for character in value)


def strip_markdown_indented_code_blocks(text: str) -> str:
    """Blank four-space/tab-indented Markdown code lines."""
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("    ") or line.startswith("\t"):
            lines.append(_blank_non_newlines(line))
        else:
            lines.append(line)
    return "".join(lines)


def strip_markdown_link_destinations(text: str) -> str:
    """Preserve visible labels while removing inline Markdown destinations."""
    return re.sub(
        r"(!?)\[([^\]]*)\]\((?:\\.|[^()])*\)",
        lambda match: match.group(2),
        text,
    )


def normalize_markdown_visible_text(text: str) -> str:
    """Approximate rendered Markdown text for semantic matching."""
    text = re.sub(
        r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*?)?\s*/?>",
        "",
        text,
    )
    text = re.sub(
        r"\\([\\`*_{}\[\]()#+\-.!|>~])",
        r"\1",
        text,
    )
    return re.sub(r"(?:\*\*|__|~~|\*|_)", "", text)


def split_public_rendered_blocks(path_text: str, text: str) -> list[str]:
    """Keep Markdown list items separate when binding claim IDs to assertions."""
    if path_text.endswith(".md"):
        text = re.sub(
            r"(?m)^(?= {0,3}(?:[-+*]|[0-9]+[.)])\s+)",
            "\n\n",
            text,
        )
    return re.split(r"\n\s*\n", text)


def strip_markdown_fenced_blocks(text: str) -> str:
    """Blank fenced code blocks without discarding adjacent rendered prose."""
    lines: list[str] = []
    fence_character: str | None = None
    fence_length = 0

    for line in text.splitlines(keepends=True):
        if fence_character is None:
            match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
            if match is None:
                lines.append(line)
                continue
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            lines.append(_blank_non_newlines(line))
            continue

        lines.append(_blank_non_newlines(line))
        closing = re.match(
            rf"^ {{0,3}}{re.escape(fence_character)}{{{fence_length},}}\s*$",
            line.rstrip("\n"),
        )
        if closing is not None:
            fence_character = None
            fence_length = 0

    return "".join(lines)


def strip_public_nonrendered_comments(path_text: str, text: str) -> str:
    """Remove non-rendered comments/code before public-claim scanning."""
    text = re.sub(
        r"<!--[\s\S]*?(?:-->|$)",
        lambda match: _blank_non_newlines(match.group(0)),
        text,
    )
    if path_text.endswith(".md"):
        text = strip_markdown_fenced_blocks(text)
        text = strip_markdown_indented_code_blocks(text)
        text = strip_markdown_link_destinations(text)
    if not path_text.endswith(".tex"):
        return text

    for macro, expansion in LATEX_PUBLIC_MACROS.items():
        text = re.sub(
            re.escape(macro) + r"(?![A-Za-z])",
            expansion,
            text,
        )

    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        comment_start: int | None = None
        for index, character in enumerate(line):
            if character != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                comment_start = index
                break
        if comment_start is None:
            lines.append(line)
            continue
        lines.append(
            line[:comment_start]
            + _blank_non_newlines(line[comment_start:])
        )
    return "".join(lines)


def validate_public_claim_text(
    path_text: str,
    text: str,
    claim_classes: dict[str, str],
) -> None:
    """Require each rendered positive cross-domain assertion to carry its own ID."""
    rendered_text = html.unescape(
        strip_public_nonrendered_comments(path_text, text)
    )
    if path_text.endswith(".md"):
        rendered_text = normalize_markdown_visible_text(rendered_text)
    paragraphs = split_public_rendered_blocks(path_text, rendered_text)
    for paragraph_number, paragraph in enumerate(paragraphs, start=1):
        compact = " ".join(paragraph.split())
        if not compact:
            continue
        paragraph_ids = set(CLAIM_ID_SEARCH.findall(compact))
        unknown_paragraph_ids = paragraph_ids - set(claim_classes)
        if unknown_paragraph_ids:
            fail(
                f"{path_text} paragraph {paragraph_number} references "
                f"unknown claim IDs {sorted(unknown_paragraph_ids)}"
            )
        if len(paragraph_domains(compact)) < 2:
            continue

        for assertion in PUBLIC_ASSERTION_RE.finditer(compact):
            clause = public_assertion_clause(compact, assertion)
            local_domains = paragraph_domains(clause)
            if len(local_domains) < 2:
                continue
            if public_assertion_is_negated(compact, assertion):
                continue

            binding_scope = public_assertion_binding_scope(compact, assertion)
            present_ids = set(CLAIM_ID_SEARCH.findall(binding_scope))
            if not present_ids:
                fail(
                    f"{path_text} paragraph {paragraph_number} contains an "
                    "unledgered positive cross-domain assertion involving "
                    f"{sorted(local_domains)}"
                )
            unknown = present_ids - set(claim_classes)
            if unknown:
                fail(
                    f"{path_text} paragraph {paragraph_number} assertion "
                    f"references unknown claim IDs {sorted(unknown)}"
                )
            semantics = public_claim_semantics()
            local_entities = public_entities(clause)
            governing_ids: set[str] = set()
            for claim_id in present_ids:
                if (
                    claim_classes[claim_id]
                    not in PUBLIC_CROSS_DOMAIN_GOVERNING_CLASSES
                ):
                    continue
                claim_domains, claim_entities = semantics.get(
                    claim_id,
                    (set(), set()),
                )
                entity_overlap = local_entities & claim_entities
                if (
                    local_domains.issubset(claim_domains)
                    and len(entity_overlap) >= min(2, len(local_entities))
                ):
                    governing_ids.add(claim_id)
            if not governing_ids:
                fail(
                    f"{path_text} paragraph {paragraph_number} assertion "
                    f"uses claim IDs {sorted(present_ids)} whose evidence "
                    "classes cannot govern a cross-domain bridge"
                )


def validate_reviewed_scientific_statement(
    claim_id: str,
    statement: str,
) -> None:
    """Bind each reviewed scientific source set to its reviewed proposition."""
    expected = PINNED_REVIEWED_SCIENTIFIC_STATEMENTS.get(claim_id)
    if expected is None:
        fail(f"{claim_id} SCIENTIFIC claim lacks a reviewed statement binding")
    if statement != expected:
        fail(
            f"{claim_id} SCIENTIFIC statement differs from its reviewed "
            "source-bound proposition"
        )


def validate_reviewed_claim_record(
    claim_id: str,
    claim: dict[str, Any],
) -> None:
    """Prevent any field of a reviewed Phase D claim from silently drifting."""
    expected = PINNED_REVIEWED_CLAIM_RECORDS.get(claim_id)
    if expected is None:
        return
    if claim != expected:
        fail(f"{claim_id} differs from its complete reviewed claim record")


def validate_reviewed_claim_inventory(claim_ids: set[str]) -> None:
    """Keep every reviewed Phase D claim present until the pins are reviewed."""
    missing = [
        claim_id
        for claim_id in PINNED_REVIEWED_CLAIM_IDS
        if claim_id not in claim_ids
    ]
    if missing:
        fail(f"reviewed claim inventory is missing {missing}")


def validate_scientific_sources(
    claim_id: str,
    claim_domain: str,
    source_ids: list[str],
    source_kinds: dict[str, str],
    source_domains: dict[str, str],
) -> None:
    """Require the reviewed scholarly source set for each scientific claim."""
    if not source_ids:
        fail(f"{claim_id} SCIENTIFIC claim requires an external source")
    expected_sources = PINNED_SCIENTIFIC_CLAIM_SOURCES.get(claim_id)
    if expected_sources is None:
        fail(
            f"{claim_id} SCIENTIFIC claim lacks a reviewed source binding"
        )
    if tuple(source_ids) != expected_sources:
        fail(
            f"{claim_id} SCIENTIFIC sources must exactly match reviewed "
            f"binding {list(expected_sources)}"
        )
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


def discover_public_governed_paths(root: Path = ROOT) -> tuple[str, ...]:
    """Discover Markdown/LaTeX documents recursively under the repository."""
    paths = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in PUBLIC_GOVERNED_SUFFIXES
            and not (
                set(path.relative_to(root).parts)
                & PUBLIC_DISCOVERY_EXCLUDED_PARTS
            )
        )
    )
    if not paths:
        fail("no public Markdown/LaTeX documents found")
    return paths


def validate_public_documents(claim_classes: dict[str, str]) -> None:
    """Apply the public cross-domain claim-ID guard to discovered documents."""
    for path_text in discover_public_governed_paths():
        path = ROOT / path_text
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fail(f"cannot read governed public document {path_text}: {exc}")
        validate_public_claim_text(path_text, text, claim_classes)


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
        source_domain = validate_source_domain(source_id, source.get("domain"))
        source_domains[source_id] = source_domain
        title = require_inline_string(source.get("title"), f"{source_id} title")
        url = require_inline_string(source.get("url"), f"{source_id} url")
        validate_reviewed_source_record(
            source_id,
            kind,
            title,
            url,
            source_domain,
        )
        parsed = validate_source_url(source_id, url)
        identifiers = validate_identifiers(source_id, source.get("identifiers"))
        validate_reviewed_source_identity(source_id, identifiers)
        identifier_urls = validate_identifier_urls(
            source_id,
            identifiers,
            source.get("identifier_urls"),
        )
        validate_primary_source_url(source_id, parsed, identifier_urls)

    claim_ids: set[str] = set()
    claim_classes: dict[str, str] = {}
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
        validate_reviewed_claim_record(claim_id, claim)

        evidence_class = require_inline_string(
            claim.get("class"),
            f"{claim_id} class",
        )
        if evidence_class not in CLASSES:
            fail(f"{claim_id} has invalid evidence class")
        claim_classes[claim_id] = evidence_class
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

        statement = require_inline_string(
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
        raw_claim_domain = claim.get("domain")
        if evidence_class == "SCIENTIFIC":
            validate_reviewed_scientific_statement(claim_id, statement)
            claim_domain = validate_source_domain(
                claim_id,
                raw_claim_domain,
            )
            validate_scientific_sources(
                claim_id,
                claim_domain,
                validated_sources,
                source_kinds,
                source_domains,
            )
        elif raw_claim_domain is not None:
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

    validate_reviewed_claim_inventory(claim_ids)
    validate_public_documents(claim_classes)

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
