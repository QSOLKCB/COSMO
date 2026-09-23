import json
import runpy
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
        return cast(
            dict[str, Any],
            runpy.run_path(str(VALIDATOR_PATH), run_name="claim_validator_test"),
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
