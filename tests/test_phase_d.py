import json
import runpy
from copy import deepcopy
import subprocess
import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

LEDGER_PATH = REPOSITORY_ROOT / "claims" / "claim-ledger.json"
INDEX_PATH = REPOSITORY_ROOT / "CLAIM-LEDGER.md"
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts" / "validate-claim-ledger.py"


class PhaseDClaimLedgerTests(unittest.TestCase):
    def load_ledger(self) -> dict[str, Any]:
        raw: object = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(raw, dict)
        return cast(dict[str, Any], raw)

    def load_validator_namespace(self) -> dict[str, Any]:
        return runpy.run_path(
            str(VALIDATOR_PATH),
            run_name="claim_validator_test",
        )

    def test_validator_accepts_reviewed_ledger(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("claim ledger valid:", completed.stdout)

    def test_all_five_evidence_classes_are_present(self) -> None:
        classes = {claim["class"] for claim in self.load_ledger()["claims"]}
        self.assertEqual(
            classes,
            {"FORMAL", "COMPUTATIONAL", "SCIENTIFIC", "HYPOTHESIS", "SYMBOLIC"},
        )

    def test_scientific_claims_have_external_sources(self) -> None:
        ledger = self.load_ledger()
        for claim in ledger["claims"]:
            if claim["class"] == "SCIENTIFIC":
                with self.subTest(claim=claim["id"]):
                    self.assertTrue(claim["sources"])

    def test_hypotheses_are_proposed_and_falsifiable(self) -> None:
        ledger = self.load_ledger()
        hypotheses = [
            claim for claim in ledger["claims"]
            if claim["class"] == "HYPOTHESIS"
        ]
        self.assertTrue(hypotheses)
        for claim in hypotheses:
            with self.subTest(claim=claim["id"]):
                self.assertEqual(claim["status"], "PROPOSED")
                self.assertTrue(claim["falsification"])

    def test_symbolic_claims_have_structured_non_empirical_status(self) -> None:
        ledger = self.load_ledger()
        for claim in ledger["claims"]:
            if claim["class"] == "SYMBOLIC":
                with self.subTest(claim=claim["id"]):
                    self.assertEqual(
                        claim.get("empirical_status"),
                        "NON_EMPIRICAL",
                    )

    def test_provenance_paths_cannot_escape_repository(self) -> None:
        namespace = self.load_validator_namespace()
        validate_path = cast(
            Callable[[str, str], Path],
            namespace["validate_repository_path"],
        )

        for path_text in (
            "/etc/os-release",
            "../outside.txt",
            "claims/../README.md",
        ):
            with self.subTest(path=path_text):
                with self.assertRaises(SystemExit):
                    validate_path(path_text, "COSMO-D-999")

    def test_markdown_is_exact_canonical_json_rendering(self) -> None:
        namespace = self.load_validator_namespace()
        render_index = cast(
            Callable[[dict[str, Any]], str],
            namespace["render_index"],
        )
        self.assertEqual(
            INDEX_PATH.read_text(encoding="utf-8"),
            render_index(self.load_ledger()),
        )


    def test_identifier_syntax_rejects_malformed_values(self) -> None:
        namespace = self.load_validator_namespace()
        validate_identifiers = cast(
            Callable[[str, object], dict[str, str]],
            namespace["validate_identifiers"],
        )

        bad_sets = (
            {"PMID": "not-a-pmid"},
            {"PMCID": "   "},
            {"DOI": "10.bad/doi"},
            {"RefSeq": "NC_001526"},
            {"year": "20X1"},
        )
        for identifiers in bad_sets:
            with self.subTest(identifiers=identifiers):
                with self.assertRaises(SystemExit):
                    validate_identifiers("SRC-TEST", identifiers)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        namespace = self.load_validator_namespace()
        parse_json_text = cast(
            Callable[[str], dict[str, Any]],
            namespace["parse_json_text"],
        )
        ambiguous = (
            '{"id":"COSMO-D-012","status":"SUPPORTED",'
            '"status":"PROPOSED"}'
        )
        with self.assertRaises(SystemExit):
            parse_json_text(ambiguous)

    def test_markdown_rendered_fields_must_be_single_line(self) -> None:
        namespace = self.load_validator_namespace()
        require_inline_string = cast(
            Callable[[object, str], str],
            namespace["require_inline_string"],
        )
        injected = (
            "Legitimate claim text\n\n"
            "### COSMO-D-999 — SCIENTIFIC\n"
            "- **Status:** `SUPPORTED`"
        )
        with self.assertRaises(SystemExit):
            require_inline_string(injected, "claim statement")

    def test_p16_provenance_anchor_is_claim_specific(self) -> None:
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-008"
        )
        self.assertEqual(
            claim["provenance"][0]["anchor"],
            "COSMO-D-008",
        )

    def test_raw_html_is_escaped_in_canonical_markdown(self) -> None:
        namespace = self.load_validator_namespace()
        render_index = cast(
            Callable[[dict[str, Any]], str],
            namespace["render_index"],
        )
        ledger = deepcopy(self.load_ledger())
        ledger["claims"][0]["statement"] = "<!--"

        rendered = render_index(ledger)
        self.assertNotIn("<!--", rendered)
        self.assertIn("&lt;!--", rendered)

    def test_source_url_requires_https_authority(self) -> None:
        namespace = self.load_validator_namespace()
        validate_source_url = cast(
            Callable[[str, object], Any],
            namespace["validate_source_url"],
        )
        with self.assertRaises(SystemExit):
            validate_source_url("SRC-TEST", "https://")

    def test_source_identifiers_must_match_canonical_url(self) -> None:
        namespace = self.load_validator_namespace()
        validate_identifier_urls = cast(
            Callable[[str, dict[str, str], object], dict[str, str]],
            namespace["validate_identifier_urls"],
        )
        with self.assertRaises(SystemExit):
            validate_identifier_urls(
                "SRC-TEST",
                {"PMCID": "PMC11158332"},
                {
                    "PMCID": (
                        "https://pmc.ncbi.nlm.nih.gov/articles/"
                        "PMC11158331/"
                    )
                },
            )

    def test_d010_provenance_anchor_is_claim_specific(self) -> None:
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-010"
        )
        self.assertEqual(
            claim["provenance"][0]["anchor"],
            "COSMO-D-010",
        )

    def test_hypothesis_falsification_is_structured_and_substantive(self) -> None:
        namespace = self.load_validator_namespace()
        validate_falsification = cast(
            Callable[[str, object], dict[str, Any]],
            namespace["validate_falsification"],
        )
        with self.assertRaises(SystemExit):
            validate_falsification(
                "COSMO-D-999",
                {
                    "protocol": "TBD",
                    "rejection_condition": (
                        "Reject if the declared evaluation threshold is not met."
                    ),
                    "controls": [
                        "Matched baseline model",
                        "Held-out evaluation set",
                    ],
                },
            )

        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-012"
        )
        result = validate_falsification(
            claim["id"],
            claim["falsification"],
        )
        self.assertEqual(
            set(result),
            {"protocol", "rejection_condition", "controls"},
        )
        self.assertGreaterEqual(len(result["controls"]), 2)

    def test_formal_claim_rejects_non_kernel_provenance_role(self) -> None:
        namespace = self.load_validator_namespace()
        validate_provenance = cast(
            Callable[[str, str, object], set[str]],
            namespace["validate_provenance"],
        )
        with self.assertRaises(SystemExit):
            validate_provenance(
                "COSMO-D-999",
                "FORMAL",
                [
                    {
                        "path": "README.md",
                        "anchor": "Phase D claim ledger",
                        "role": "project_note",
                    }
                ],
            )

    def test_source_kind_rejects_project_notes(self) -> None:
        namespace = self.load_validator_namespace()
        validate_source_kind = cast(
            Callable[[str, object], str],
            namespace["validate_source_kind"],
        )
        with self.assertRaises(SystemExit):
            validate_source_kind("SRC-TEST", "project_note")

    def test_multi_accession_sources_bind_each_identifier(self) -> None:
        namespace = self.load_validator_namespace()
        validate_identifier_urls = cast(
            Callable[[str, dict[str, str], object], dict[str, str]],
            namespace["validate_identifier_urls"],
        )
        with self.assertRaises(SystemExit):
            validate_identifier_urls(
                "SRC-TEST",
                {
                    "PMID": "17645778",
                    "PMCID": "PMC11158331",
                },
                {
                    "PMID": "https://pubmed.ncbi.nlm.nih.gov/17645777/",
                    "PMCID": (
                        "https://pmc.ncbi.nlm.nih.gov/articles/"
                        "PMC11158331/"
                    ),
                },
            )

    def test_formal_provenance_requires_actual_lean_theorem(self) -> None:
        namespace = self.load_validator_namespace()
        validate_provenance = cast(
            Callable[[str, str, object], set[str]],
            namespace["validate_provenance"],
        )
        with self.assertRaises(SystemExit):
            validate_provenance(
                "COSMO-D-999",
                "FORMAL",
                [
                    {
                        "path": "README.md",
                        "anchor": "Phase D claim ledger",
                        "role": "kernel_checked_theorem",
                    }
                ],
            )

    def test_formal_anchor_ignores_commented_lean_declarations(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        commented_sources = (
            (
                "/-\n"
                "theorem six_step_periodic : True := by trivial\n"
                "-/\n"
            ),
            "-- theorem six_step_periodic : True := by trivial\n",
            (
                "/- outer comment\n"
                "/- nested comment -/\n"
                "theorem six_step_periodic : True := by trivial\n"
                "-/\n"
            ),
        )
        for source in commented_sources:
            with self.subTest(source=source):
                with self.assertRaises(SystemExit):
                    validate_formal_target(
                        "COSMO-D-999",
                        "CosmoFormal.lean",
                        "theorem six_step_periodic",
                        source,
                    )

    def test_scientific_claim_rejects_unrelated_domain_source(self) -> None:
        namespace = self.load_validator_namespace()
        validate_scientific_sources = cast(
            Callable[
                [str, str, list[str], dict[str, str], dict[str, str]],
                None,
            ],
            namespace["validate_scientific_sources"],
        )
        with self.assertRaises(SystemExit):
            validate_scientific_sources(
                "COSMO-D-007",
                "biomedicine",
                ["SRC-E8-MATHWORLD"],
                {"SRC-E8-MATHWORLD": "scholarly_reference"},
                {"SRC-E8-MATHWORLD": "mathematics"},
            )

    def test_public_cross_domain_assertion_requires_claim_id(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, set[str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_ids = {
            claim["id"] for claim in self.load_ledger()["claims"]
        }
        unsupported = (
            "Spin(8) triality biologically causes HPV16 capsid assembly."
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                unsupported,
                claim_ids,
            )

        governed = (
            "COSMO-D-011 records that Spin(8) triality causes HPV16 "
            "capsid assembly only as a claim subject to its ledger class."
        )
        validate_public_claim_text(
            "README.md",
            governed,
            claim_ids,
        )

    def test_public_negation_only_suppresses_its_own_assertion(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, set[str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_ids = {
            claim["id"] for claim in self.load_ledger()["claims"]
        }

        for unsupported in (
            (
                "Spin(8) does not describe normal virology. "
                "Spin(8) triality causes HPV16 capsid assembly."
            ),
            (
                "Spin(8) does not describe normal virology, but "
                "Spin(8) triality causes HPV16 capsid assembly."
            ),
        ):
            with self.subTest(text=unsupported):
                with self.assertRaises(SystemExit):
                    validate_public_claim_text(
                        "README.md",
                        unsupported,
                        claim_ids,
                    )

        validate_public_claim_text(
            "README.md",
            "Spin(8) triality does not cause HPV16 capsid assembly.",
            claim_ids,
        )

    def test_hpv16_reference_accession_is_versioned(self) -> None:
        ledger = self.load_ledger()
        source = next(
            source for source in ledger["sources"]
            if source["id"] == "SRC-HPV16-REFSEQ"
        )
        self.assertEqual(source["identifiers"]["RefSeq"], "NC_001526.4")

    def test_sis2_source_has_stable_article_identifiers(self) -> None:
        ledger = self.load_ledger()
        source = next(
            source for source in ledger["sources"]
            if source["id"] == "SRC-SIS2-PMID-25590815"
        )
        self.assertEqual(source["identifiers"]["PMID"], "25590815")
        self.assertEqual(source["identifiers"]["DOI"], "10.1021/ic501825r")


if __name__ == "__main__":
    unittest.main()
