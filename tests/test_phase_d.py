import json
import runpy
from copy import deepcopy
import subprocess
import sys
import tempfile
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
            INDEX_PATH.read_bytes(),
            render_index(self.load_ledger()).encode("utf-8"),
        )


    def test_ledger_root_rejects_unreviewed_fields(self) -> None:
        namespace = self.load_validator_namespace()
        validate_fields = cast(
            Callable[[dict[str, Any]], None],
            namespace["validate_ledger_fields"],
        )
        ledger = deepcopy(self.load_ledger())
        validate_fields(ledger)
        ledger["unreviewed_note"] = "Spin(8) causes HPV16 disease."
        with self.assertRaises(SystemExit):
            validate_fields(ledger)

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

    def test_nonstandard_json_constants_are_rejected(self) -> None:
        namespace = self.load_validator_namespace()
        parse_json_text = cast(
            Callable[[str], dict[str, Any]],
            namespace["parse_json_text"],
        )
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaises(SystemExit):
                    parse_json_text(
                        '{"schema":"COSMO-CLAIMS-D-1","extension":'
                        + constant
                        + "}"
                    )

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
        self.assertIn("&lt;&#33;--", rendered)

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

        with self.assertRaises(SystemExit):
            validate_falsification(
                "COSMO-D-999",
                {
                    "protocol": "TBD TBD TBD TBD TBD TBD TBD TBD TBD TBD TBD TBD",
                    "rejection_condition": (
                        "TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO"
                    ),
                    "controls": [
                        "placeholder one",
                        "placeholder two",
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

    def test_identifier_free_reviewed_source_record_is_pinned(self) -> None:
        namespace = self.load_validator_namespace()
        validate_record = cast(
            Callable[[str, str, str, str, str], None],
            namespace["validate_reviewed_source_record"],
        )
        with self.assertRaises(SystemExit):
            validate_record(
                "SRC-SPIN8-PTEP-2021",
                "scholarly_article",
                "Unrelated mathematics article",
                "https://example.com/unrelated",
                "mathematics",
            )
        validate_record(
            "SRC-SPIN8-PTEP-2021",
            "scholarly_article",
            (
                "Vertex operator superalgebra/sigma model correspondences: "
                "The four-torus case"
            ),
            "https://academic.oup.com/ptep/article/2021/8/08B102/6353037",
            "mathematics",
        )

    def test_reviewed_source_record_rejects_unreviewed_fields(self) -> None:
        namespace = self.load_validator_namespace()
        validate_fields = cast(
            Callable[[str, dict[str, Any]], None],
            namespace["validate_reviewed_source_fields"],
        )
        source = deepcopy(self.load_ledger()["sources"][0])
        validate_fields(source["id"], source)
        source["unreviewed_note"] = "Spin(8) causes HPV16 disease."
        with self.assertRaises(SystemExit):
            validate_fields(source["id"], source)

    def test_reviewed_source_identity_pins_non_url_metadata(self) -> None:
        namespace = self.load_validator_namespace()
        validate_identity = cast(
            Callable[[str, dict[str, str]], None],
            namespace["validate_reviewed_source_identity"],
        )
        validate_identity(
            "SRC-SPIN8-PTEP-2021",
            {"year": "2021"},
        )
        with self.assertRaises(SystemExit):
            validate_identity(
                "SRC-SPIN8-PTEP-2021",
                {"year": "1900"},
            )

    def test_multi_accession_crosswalk_rejects_unrelated_article_ids(self) -> None:
        namespace = self.load_validator_namespace()
        validate_crosswalk = cast(
            Callable[[str, dict[str, str]], None],
            namespace["validate_reviewed_source_identity"],
        )
        with self.assertRaises(SystemExit):
            validate_crosswalk(
                "SRC-HPV16-E6E7-PMID-17645777",
                {
                    "PMID": "17645778",
                    "PMCID": "PMC11158331",
                },
            )
        validate_crosswalk(
            "SRC-HPV16-E6E7-PMID-17645777",
            {
                "PMID": "17645777",
                "PMCID": "PMC11158331",
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
                        "cosmovirus.lean",
                        (
                            "theorem six_step_periodic (layer : CosmoLayer) : "
                            "psiIterate 6 layer = layer := by"
                        ),
                        source,
                    )

    def test_formal_anchor_ignores_lean_string_literals(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            'def fakeLedgerEvidence : String := "'
            + anchor
            + '"\n'
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_claim_is_bound_to_its_reviewed_theorem(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        source = (REPOSITORY_ROOT / "cosmovirus.lean").read_text(
            encoding="utf-8"
        )
        wrong_anchor = (
            "theorem every_layer_reachable (source target : CosmoLayer) : "
            "ReachesWithinCycle source target := by"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                wrong_anchor,
                source,
            )

    def test_formal_anchor_ignores_lean_syntax_quotations(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "def fakeQuotedEvidence : Lean.Syntax := "
            "`(command| theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by trivial)\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_anchor_ignores_lean_quoted_identifiers(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "def «theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by» : Nat := 0\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_anchor_must_resolve_in_authoritative_namespace(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "namespace Cosmovirus\n"
            "namespace Decoy\n"
            "inductive CosmoLayer where | only\n"
            "def psiIterate (_n : Nat) (layer : CosmoLayer) := layer\n"
            "theorem six_step_periodic (layer : CosmoLayer) :\n"
            "    psiIterate 6 layer = layer := by rfl\n"
            "end Decoy\n"
            "end Cosmovirus\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_anchor_rejects_section_local_shadowing(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "namespace Cosmovirus\n"
            "section\n"
            "variable (CosmoLayer : Type)\n"
            "variable (psiIterate : Nat -> CosmoLayer -> CosmoLayer)\n"
            "variable (h : forall layer, psiIterate 6 layer = layer)\n"
            "theorem six_step_periodic (layer : CosmoLayer) :\n"
            "    psiIterate 6 layer = layer := by exact h layer\n"
            "end\n"
            "end Cosmovirus\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_anchor_rejects_unicode_named_section_shadowing(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "namespace Cosmovirus\n"
            "section α\n"
            "variable (CosmoLayer : Type)\n"
            "variable (psiIterate : Nat -> CosmoLayer -> CosmoLayer)\n"
            "variable (h : forall layer, psiIterate 6 layer = layer)\n"
            "theorem six_step_periodic (layer : CosmoLayer) :\n"
            "    psiIterate 6 layer = layer := by exact h layer\n"
            "end α\n"
            "end Cosmovirus\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_anchor_rejects_namespace_level_shadowing(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "namespace Cosmovirus\n"
            "variable (CosmoLayer : Type)\n"
            "variable (psiIterate : Nat -> CosmoLayer -> CosmoLayer)\n"
            "variable (h : forall layer, psiIterate 6 layer = layer)\n"
            "theorem six_step_periodic (layer : CosmoLayer) :\n"
            "    psiIterate 6 layer = layer := by exact h layer\n"
            "end Cosmovirus\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_anchor_rejects_included_namespace_hypothesis(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        source = (
            "namespace Cosmovirus\n"
            "inductive CosmoLayer where | only\n"
            "def psiIterate (_n : Nat) (layer : CosmoLayer) := layer\n"
            "variable (periodicityAssumption : forall layer : CosmoLayer, "
            "psiIterate 6 layer = layer)\n"
            "include periodicityAssumption\n"
            "theorem six_step_periodic (layer : CosmoLayer) :\n"
            "    psiIterate 6 layer = layer := by\n"
            "  exact periodicityAssumption layer\n"
            "end Cosmovirus\n"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "cosmovirus.lean",
                anchor,
                source,
            )

    def test_formal_target_must_enter_protected_lean_compile_closure(self) -> None:
        namespace = self.load_validator_namespace()
        validate_formal_target = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_formal_provenance_target"],
        )
        anchor = (
            "theorem six_step_periodic (layer : CosmoLayer) : "
            "psiIterate 6 layer = layer := by"
        )
        with self.assertRaises(SystemExit):
            validate_formal_target(
                "COSMO-D-001",
                "UncompiledEvidence.lean",
                anchor,
                anchor + "\n  trivial\n",
            )

    def test_protected_lean_sources_come_from_executed_inventory(self) -> None:
        namespace = self.load_validator_namespace()
        protected_sources = cast(
            Callable[[], set[str]],
            namespace["protected_lean_sources"],
        )
        self.assertEqual(
            protected_sources(),
            {"CosmoTrust.lean", "cosmovirus.lean", "COSMO.lean"},
        )

        script = (
            REPOSITORY_ROOT / "scripts" / "run-lean-verified-reuse-ci.sh"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "UncompiledEvidence.lean",
            "\n".join(sorted(protected_sources())),
        )
        self.assertIn("PROJECT_LEAN_SOURCES=(", script)

    def test_computational_regression_must_execute_without_skip(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import unittest\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    @unittest.skip('temporarily disabled')\n"
            "    def test_required_regression(self):\n"
            "        self.assertTrue(True)\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )

    def test_regression_loader_rejects_system_exit(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import unittest\n"
            "if __name__.startswith('_cosmo_claim_regression_'):\n"
            "    raise SystemExit(0)\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        self.assertTrue(True)\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit) as raised:
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )
            self.assertNotEqual(raised.exception.code, 0)
            self.assertIn(
                "cannot load regression evidence",
                str(raised.exception),
            )

    def test_regression_rejects_overridden_unittest_dispatch(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
            "    def run(\n"
            "        self, result: unittest.TestResult | None = None\n"
            "    ) -> unittest.TestResult:\n"
            "        if result is None:\n"
            "            result = unittest.TestResult()\n"
            "        result.startTest(self)\n"
            "        result.stopTest(self)\n"
            "        return result\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-003",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )

    def test_regression_rejects_alternate_unittest_dispatch_hook(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
            "    def _callTestMethod(self, method):\n"
            "        return None\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_rejects_module_level_dispatch_mutation(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "setattr(\n"
            "    unittest.TestCase, '_callTestMethod',\n"
            "    lambda self, method: None,\n"
            ")\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_rejects_qualified_dispatch_mutation(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "type.__setattr__(\n"
            "    unittest.TestCase, '_callTestMethod',\n"
            "    lambda self, method: None,\n"
            ")\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_rejects_custom_attribute_lookup_dispatch(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class ExactE8RootTests(unittest.TestCase):\n"
            "    def __getattribute__(self, name: str):\n"
            "        if name == 'run':\n"
            "            def fake_run(result: unittest.TestResult) -> None:\n"
            "                result.startTest(self)\n"
            "                result.addSuccess(self)\n"
            "                result.stopTest(self)\n"
            "            return fake_run\n"
            "        return super().__getattribute__(name)\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_rejects_post_definition_class_dispatch_patch(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "def fake_run(\n"
            "    self: unittest.TestCase,\n"
            "    result: unittest.TestResult | None = None,\n"
            ") -> unittest.TestResult:\n"
            "    if result is None:\n"
            "        result = unittest.TestResult()\n"
            "    result.startTest(self)\n"
            "    result.addSuccess(self)\n"
            "    result.stopTest(self)\n"
            "    return result\n"
            "class ExactE8RootTests(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
            "setattr(ExactE8RootTests, 'run', fake_run)\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_rejects_helper_called_dispatch_mutation(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "def fake_run(\n"
            "    self: unittest.TestCase,\n"
            "    result: unittest.TestResult | None = None,\n"
            ") -> unittest.TestResult:\n"
            "    if result is None:\n"
            "        result = unittest.TestResult()\n"
            "    result.startTest(self)\n"
            "    result.addSuccess(self)\n"
            "    result.stopTest(self)\n"
            "    return result\n"
            "class ExactE8RootTests(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
            "def disable_claimed_test() -> None:\n"
            "    setattr(ExactE8RootTests, 'run', fake_run)\n"
            "disable_claimed_test()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_rejects_inherited_dispatch_override(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class NoDispatch(unittest.TestCase):\n"
            "    def _callTestMethod(self, method) -> None:\n"
            "        return None\n"
            "class RegressionEvidence(NoDispatch):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                source,
            )

    def test_regression_executes_frozen_snapshot_bytes(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        snapshot = (
            "import unittest\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        self.fail('snapshot failure')\n"
        )
        live_rewrite = (
            "import unittest\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        self.assertTrue(True)\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(live_rewrite, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    snapshot,
                )

    def test_regression_executes_frozen_implementation_bytes(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[
                [str, str, str, Path, str, str | None, str | None],
                None,
            ],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import unittest\n"
            "from cosmo_core import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        frozen_implementation = (
            "def validate_e8_root_system(_roots):\n"
            "    raise RuntimeError('frozen implementation failure')\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                    "cosmo_core/e8.py",
                    frozen_implementation,
                )

    def test_regression_completion_marker_cannot_be_spoofed(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import os\n"
            "import unittest\n"
            "print('__COSMO_REGRESSION_OK__', flush=True)\n"
            "os._exit(0)\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        self.fail('never executed')\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )

    def test_regression_execution_isolates_parent_module_mutation(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        import cosmo_core

        original = cosmo_core.recover_cube_storage
        try:
            setattr(
                cosmo_core,
                "recover_cube_storage",
                lambda *_args, **_kwargs: None,
            )
            source = (
                "import unittest\n"
                "from cosmo_core import recover_cube_storage\n"
                "class RegressionEvidence(unittest.TestCase):\n"
                "    def test_required_regression(self) -> None:\n"
                "        self.assertEqual(\n"
                "            recover_cube_storage.__module__,\n"
                "            'cosmo_core.storage',\n"
                "        )\n"
            )
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "test_regression.py"
                path.write_text(source, encoding="utf-8")
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )
        finally:
            setattr(cosmo_core, "recover_cube_storage", original)

    def test_async_regression_methods_are_rejected(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import unittest\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    async def test_required_regression(self):\n"
            "        self.fail('must execute')\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )

    def test_generator_regression_methods_are_rejected(self) -> None:
        namespace = self.load_validator_namespace()
        validate_regression = cast(
            Callable[[str, str, str, Path, str], None],
            namespace["validate_computational_regression_target"],
        )
        source = (
            "import unittest\n"
            "from collections.abc import Iterator\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> Iterator[None]:\n"
            "        yield None\n"
            "        self.fail('generator body executed')\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test_regression.py"
            path.write_text(source, encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate_regression(
                    "COSMO-D-999",
                    "tests/test_regression.py",
                    "test_required_regression",
                    path,
                    source,
                )

    def test_regression_must_exercise_declared_implementation(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        regression_text = (
            REPOSITORY_ROOT / "tests" / "test_phase_b3.py"
        ).read_text(encoding="utf-8")
        validate_connection(
            "COSMO-D-003",
            "cosmo_core/e8.py",
            "def validate_e8_root_system",
            "tests/test_phase_b3.py",
            "test_root_system_report_has_rank_eight_and_norm_two",
            regression_text,
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/fake_evidence.py",
                "def validate_e8_root_system",
                "tests/test_phase_b3.py",
                "test_root_system_report_has_rank_eight_and_norm_two",
                regression_text,
            )

        method_header = (
            "    def test_root_system_report_has_rank_eight_and_norm_two(self) -> None:\n"
        )
        unreachable = regression_text.replace(
            method_header,
            method_header + "        return\n",
            1,
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_phase_b3.py",
                "test_root_system_report_has_rank_eight_and_norm_two",
                unreachable,
            )

        disabled_by_module_constant = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "RUN_CLAIMED_EVIDENCE = False\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        if RUN_CLAIMED_EVIDENCE:\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_module_constant,
            )

        disabled_by_constant_comparison = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "RUN_CLAIMED_EVIDENCE = False\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        if RUN_CLAIMED_EVIDENCE is True:\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_constant_comparison,
            )

        disabled_by_runtime_false_bool = (
            "import unittest\n"
            "from cosmo_core import canonical_e8_roots\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        if bool(0):\n"
            "            validate_e8_root_system(canonical_e8_roots())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_runtime_false_bool,
            )

        disabled_by_while_false = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        while False:\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_while_false,
            )

        disabled_by_runtime_empty_range = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        for _ in range(len(())):\n"
            "            validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_runtime_empty_range,
            )

        disabled_by_empty_for = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        for _ in ():\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_empty_for,
            )

        disabled_by_numeric_false_loop = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        while 0:\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_by_numeric_false_loop,
            )

        disabled_after_break = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        while True:\n"
            "            break\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_after_break,
            )

        disabled_after_selected_break = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        while True:\n"
            "            if True:\n"
            "                break\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003", "cosmo_core/e8.py",
                "def validate_e8_root_system", "tests/test_regression.py",
                "test_required_regression", disabled_after_selected_break,
            )

        disabled_after_selected_return = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        if True:\n"
            "            return\n"
            "        validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003", "cosmo_core/e8.py",
                "def validate_e8_root_system", "tests/test_regression.py",
                "test_required_regression", disabled_after_selected_return,
            )

        disabled_comprehension = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "DISABLED = False\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        _unused = [\n"
            "            validate_e8_root_system(())\n"
            "            for _ in (1,) if DISABLED\n"
            "        ]\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                disabled_comprehension,
            )

        lazy_if_expression = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        _unused = validate_e8_root_system(()) if False else None\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                lazy_if_expression,
            )

        empty_comprehension = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        _unused = [validate_e8_root_system(()) for _ in ()]\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                empty_comprehension,
            )

        unconsumed_generator = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        _unused = (validate_e8_root_system(()) for _ in (1,))\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                unconsumed_generator,
            )

        expected_exception_only = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        with self.assertRaises(ValueError):\n"
            "            validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                expected_exception_only,
            )

        eager_consumed_generator = (
            "import unittest\n"
            "from cosmo_core import canonical_e8_roots\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        tuple(\n"
            "            validate_e8_root_system(canonical_e8_roots())\n"
            "            for _ in range(1)\n"
            "        )\n"
        )
        validate_connection(
            "COSMO-D-999",
            "cosmo_core/e8.py",
            "def validate_e8_root_system",
            "tests/test_regression.py",
            "test_required_regression",
            eager_consumed_generator,
        )

        unreachable_assert_handler = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        try:\n"
            "            assert True\n"
            "        except AssertionError:\n"
            "            validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                unreachable_assert_handler,
            )

        called_helper_mutation = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "def disable_reviewed_validator() -> None:\n"
            "    setattr(\n"
            "        validate_e8_root_system, '__code__',\n"
            "        (lambda *_args: None).__code__,\n"
            "    )\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        disable_reviewed_validator()\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                called_helper_mutation,
            )

        unreachable_match_case = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        match 0:\n"
            "            case 1:\n"
            "                validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                unreachable_match_case,
            )

        qualified_mutated_function = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        object.__setattr__(\n"
            "            validate_e8_root_system, '__code__',\n"
            "            (lambda *_args: None).__code__,\n"
            "        )\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                qualified_mutated_function,
            )

        destructured_function_alias = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        alias, = (validate_e8_root_system,)\n"
            "        setattr(\n"
            "            alias, '__code__',\n"
            "            (lambda *_args: None).__code__,\n"
            "        )\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                destructured_function_alias,
            )

        mutated_function_alias = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        alias = validate_e8_root_system\n"
            "        setattr(\n"
            "            alias, '__code__',\n"
            "            (lambda *_args: None).__code__,\n"
            "        )\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                mutated_function_alias,
            )

        mutated_function_object = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        setattr(\n"
            "            validate_e8_root_system, '__code__',\n"
            "            (lambda *_args: None).__code__,\n"
            "        )\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                mutated_function_object,
            )

        unreachable_handler = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        try:\n"
            "            pass\n"
            "        except Exception:\n"
            "            validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                unreachable_handler,
            )

        unreachable_after_finally_return = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        try:\n"
            "            pass\n"
            "        finally:\n"
            "            return\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                unreachable_after_finally_return,
            )

        unreachable_inside_try = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        try:\n"
            "            return\n"
            "            validate_e8_root_system()\n"
            "        finally:\n"
            "            pass\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                unreachable_inside_try,
            )

        disabled_by_false_literal_comparison = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        if 1 == 2:\n"
            "            validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003", "cosmo_core/e8.py",
                "def validate_e8_root_system", "tests/test_regression.py",
                "test_required_regression", disabled_by_false_literal_comparison,
            )

        rebound_at_module_scope = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "globals().update({\n"
            "    'validate_e8_root_system': lambda *_args: None\n"
            "})\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                rebound_at_module_scope,
            )

        short_circuited_call = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        _unused = False and validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                short_circuited_call,
            )

        rebound_by_setup = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def setUp(self) -> None:\n"
            "        globals()['validate_e8_root_system'] = lambda *_args: None\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                rebound_by_setup,
            )

        condition_call = (
            "import unittest\n"
            "from cosmo_core import canonical_e8_roots\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        if validate_e8_root_system(canonical_e8_roots()) is not None:\n"
            "            pass\n"
        )
        validate_connection(
            "COSMO-D-999",
            "cosmo_core/e8.py",
            "def validate_e8_root_system",
            "tests/test_regression.py",
            "test_required_regression",
            condition_call,
        )

        rebound_by_globals_update = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        globals().update({\n"
            "            'validate_e8_root_system': lambda *_args: None\n"
            "        })\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                rebound_by_globals_update,
            )

        shadowed_by_parameter = (
            "import unittest\n"
            "from collections.abc import Callable\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(\n"
            "        self,\n"
            "        validate_e8_root_system: Callable[..., None] = lambda *_: None,\n"
            "    ) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                shadowed_by_parameter,
            )

        rebound_by_with_target = (
            "import unittest\n"
            "from contextlib import nullcontext\n"
            "from unittest.mock import Mock\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        with nullcontext(Mock()) as validate_e8_root_system:\n"
            "            validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003", "cosmo_core/e8.py",
                "def validate_e8_root_system", "tests/test_regression.py",
                "test_required_regression", rebound_by_with_target,
            )

        fixture_helper_mutation = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "def no_op(*_args):\n"
            "    return None\n"
            "def disable_reviewed_validator() -> None:\n"
            "    setattr(\n"
            "        validate_e8_root_system, '__code__', no_op.__code__\n"
            "    )\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def setUp(self) -> None:\n"
            "        disable_reviewed_validator()\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                fixture_helper_mutation,
            )

        patched_binding = (
            "import unittest\n"
            "from unittest.mock import Mock, patch\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        with patch.dict(globals(), "
            "{'validate_e8_root_system': Mock()}):\n"
            "            validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                patched_binding,
            )

        aliased_import_with_shadow = (
            "import unittest\n"
            "from cosmo_core.e8 import validate_e8_root_system as imported_validate\n"
            "def validate_e8_root_system() -> None:\n"
            "    return None\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system()\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                aliased_import_with_shadow,
            )

    def test_d003_regression_requires_reviewed_report_assertions(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        regression_text = (
            REPOSITORY_ROOT / "tests" / "test_phase_b3.py"
        ).read_text(encoding="utf-8")
        validate_connection(
            "COSMO-D-003",
            "cosmo_core/e8.py",
            "def validate_e8_root_system",
            "tests/test_phase_b3.py",
            "test_root_system_report_has_rank_eight_and_norm_two",
            regression_text,
        )
        start = regression_text.index(
            "        self.assertEqual(report.root_count, 240)\n"
        )
        end = regression_text.index(
            "    def test_reflections_are_canonically_ordered_by_root",
            start,
        )
        weakened = (
            regression_text[:start]
            + "        _ = report\n"
            + regression_text[end:]
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_phase_b3.py",
                "test_root_system_report_has_rank_eight_and_norm_two",
                weakened,
            )

    def test_d014_regression_requires_reviewed_recovery_assertions(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        regression_text = (
            REPOSITORY_ROOT / "tests" / "test_phase_b5.py"
        ).read_text(encoding="utf-8")
        validate_connection(
            "COSMO-D-014",
            "cosmo_core/storage.py",
            "def recover_cube_storage",
            "tests/test_phase_b5.py",
            "test_full_cube_recovers_one_bit_error_in_every_codeword",
            regression_text,
        )

        expected_assertions = (
            "        self.assertEqual(recovered.cube, cube)\n"
            "        self.assertEqual(\n"
            "            recovered.storage.corrected_codewords,\n"
            "            codeword_count,\n"
            "        )\n"
        )
        weakened = regression_text.replace(
            expected_assertions,
            "        _ = recovered\n",
            1,
        )
        self.assertNotEqual(weakened, regression_text)
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-014",
                "cosmo_core/storage.py",
                "def recover_cube_storage",
                "tests/test_phase_b5.py",
                "test_full_cube_recovers_one_bit_error_in_every_codeword",
                weakened,
            )

    def test_d014_assertions_must_bind_to_implementation_return(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        regression_text = (
            REPOSITORY_ROOT / "tests" / "test_phase_b5.py"
        ).read_text(encoding="utf-8")
        fabricated = regression_text.replace(
            "import sys\n",
            "import sys\nfrom types import SimpleNamespace\n",
            1,
        ).replace(
            "        recovered = recover_cube_storage(\n",
            "        _discarded = recover_cube_storage(\n",
            1,
        )
        assertion_anchor = "        self.assertEqual(recovered.cube, cube)\n"
        fabricated = fabricated.replace(
            assertion_anchor,
            (
                "        recovered = SimpleNamespace(\n"
                "            cube=cube,\n"
                "            storage=SimpleNamespace(\n"
                "                corrected_codewords=codeword_count,\n"
                "            ),\n"
                "        )\n"
                + assertion_anchor
            ),
            1,
        )
        self.assertNotEqual(fabricated, regression_text)
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-014",
                "cosmo_core/storage.py",
                "def recover_cube_storage",
                "tests/test_phase_b5.py",
                "test_full_cube_recovers_one_bit_error_in_every_codeword",
                fabricated,
            )

    def test_d014_required_assertions_must_be_reachable(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        regression_text = (
            REPOSITORY_ROOT / "tests" / "test_phase_b5.py"
        ).read_text(encoding="utf-8")
        expected_assertions = (
            "        self.assertEqual(recovered.cube, cube)\n"
            "        self.assertEqual(\n"
            "            recovered.storage.corrected_codewords,\n"
            "            codeword_count,\n"
            "        )\n"
        )
        unreachable = regression_text.replace(
            expected_assertions,
            (
                "        if False:\n"
                "            self.assertEqual(recovered.cube, cube)\n"
                "            self.assertEqual(\n"
                "                recovered.storage.corrected_codewords,\n"
                "                codeword_count,\n"
                "            )\n"
            ),
            1,
        )
        self.assertNotEqual(unreachable, regression_text)
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-014",
                "cosmo_core/storage.py",
                "def recover_cube_storage",
                "tests/test_phase_b5.py",
                "test_full_cube_recovers_one_bit_error_in_every_codeword",
                unreachable,
            )

    def test_d014_assertions_after_selected_return_are_rejected(self) -> None:
        namespace = self.load_validator_namespace()
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        regression_text = (
            REPOSITORY_ROOT / "tests" / "test_phase_b5.py"
        ).read_text(encoding="utf-8")

        required_assertions = (
            "        self.assertEqual(recovered.cube, cube)\n"
            "        self.assertEqual(\n"
            "            recovered.storage.corrected_codewords,\n"
            "            codeword_count,\n"
            "        )\n"
        )
        self.assertEqual(regression_text.count(required_assertions), 1)

        def check_connection(source: str) -> None:
            validate_connection(
                "COSMO-D-014",
                "cosmo_core/storage.py",
                "def recover_cube_storage",
                "tests/test_phase_b5.py",
                "test_full_cube_recovers_one_bit_error_in_every_codeword",
                source,
            )

        check_connection(regression_text)

        exits = {
            "true_branch": (
                "        if True:\n"
                "            return\n"
            ),
            "else_branch": (
                "        if False:\n"
                "            pass\n"
                "        else:\n"
                "            return\n"
            ),
            "nested_selected_branch": (
                "        if True:\n"
                "            if True:\n"
                "                return\n"
            ),
        }
        for label, prefix in exits.items():
            with self.subTest(case=label):
                source = regression_text.replace(
                    required_assertions,
                    prefix + required_assertions,
                    1,
                )
                with self.assertRaisesRegex(
                    SystemExit,
                    "missing assertEqual pairs",
                ):
                    check_connection(source)

        reachable = regression_text.replace(
            required_assertions,
            (
                "        if False:\n"
                "            return\n"
                + required_assertions
            ),
            1,
        )
        check_connection(reachable)

    def test_implementation_provenance_requires_executable_project_source(self) -> None:
        namespace = self.load_validator_namespace()
        validate_implementation = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_computational_implementation_target"],
        )
        validate_connection = cast(
            Callable[[str, str, str, str, str, str], None],
            namespace["validate_computational_evidence_connection"],
        )
        with self.assertRaises(SystemExit):
            validate_implementation(
                "COSMO-D-003",
                "README.md",
                "def validate_e8_root_system",
                "Phase B3\n",
            )

        decorated_regression_class = (
            "import unittest\n"
            "from collections.abc import Callable\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "def replace(\n"
            "    cls: type[unittest.TestCase],\n"
            ") -> type[unittest.TestCase]:\n"
            "    class FakeRegression(unittest.TestCase):\n"
            "        def test_required_regression(self) -> None:\n"
            "            return None\n"
            "    return FakeRegression\n"
            "@replace\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                decorated_regression_class,
            )

        decorated_regression = (
            "import unittest\n"
            "from collections.abc import Callable\n"
            "from cosmo_core.e8 import validate_e8_root_system\n"
            "def replace(function: Callable[..., None]) -> Callable[..., None]:\n"
            "    def fake(self: unittest.TestCase) -> None:\n"
            "        return None\n"
            "    return fake\n"
            "class RegressionEvidence(unittest.TestCase):\n"
            "    @replace\n"
            "    def test_required_regression(self) -> None:\n"
            "        validate_e8_root_system(())\n"
        )
        with self.assertRaises(SystemExit):
            validate_connection(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                "tests/test_regression.py",
                "test_required_regression",
                decorated_regression,
            )

        decorator_replacement = (
            "def replace(function):\n"
            "    def fake() -> None:\n"
            "        return None\n"
            "    return fake\n"
            "@replace\n"
            "def validate_e8_root_system() -> None:\n"
            "    raise AssertionError('reviewed body must execute')\n"
        )
        with self.assertRaises(SystemExit):
            validate_implementation(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                decorator_replacement,
            )

        rebound_export = (
            "def validate_e8_root_system() -> None:\n"
            "    return None\n"
            "def _fake() -> None:\n"
            "    return None\n"
            "validate_e8_root_system = _fake\n"
        )
        with self.assertRaises(SystemExit):
            validate_implementation(
                "COSMO-D-003",
                "cosmo_core/e8.py",
                "def validate_e8_root_system",
                rebound_export,
            )

    def test_scientific_statement_is_bound_to_reviewed_proposition(self) -> None:
        namespace = self.load_validator_namespace()
        validate_statement = cast(
            Callable[[str, str], None],
            namespace["validate_reviewed_scientific_statement"],
        )
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-006"
        )
        validate_statement(claim["id"], claim["statement"])
        with self.assertRaises(SystemExit):
            validate_statement(
                "COSMO-D-006",
                "HPV16 RefSeq NC_001526.4 is a vaccine that cures every cancer.",
            )

    def test_reviewed_claim_record_rejects_any_field_drift(self) -> None:
        namespace = self.load_validator_namespace()
        validate_record = cast(
            Callable[[str, dict[str, Any]], None],
            namespace["validate_reviewed_claim_record"],
        )
        ledger = self.load_ledger()
        computational = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-003"
        )
        validate_record(computational["id"], computational)

        repurposed = deepcopy(computational)
        repurposed["class"] = "SYMBOLIC"
        repurposed["statement"] = "Unrelated symbolic replacement."
        with self.assertRaises(SystemExit):
            validate_record("COSMO-D-003", repurposed)

        symbolic = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-009"
        )
        expanded_boundary = deepcopy(symbolic)
        expanded_boundary["boundary"] = (
            "This symbolic annotation also covers SiS2, HPV16, "
            "and capsid terminology."
        )
        with self.assertRaises(SystemExit):
            validate_record("COSMO-D-009", expanded_boundary)

        unreviewed = deepcopy(symbolic)
        unreviewed["id"] = "COSMO-D-015"
        with self.assertRaises(SystemExit):
            validate_record("COSMO-D-015", unreviewed)

    def test_reviewed_claim_inventory_rejects_deleted_claim(self) -> None:
        namespace = self.load_validator_namespace()
        validate_inventory = cast(
            Callable[[set[str]], None],
            namespace["validate_reviewed_claim_inventory"],
        )
        claim_ids = {claim["id"] for claim in self.load_ledger()["claims"]}
        validate_inventory(claim_ids)
        claim_ids.remove("COSMO-D-003")
        with self.assertRaises(SystemExit):
            validate_inventory(claim_ids)

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

    def test_scientific_claim_requires_its_reviewed_source(self) -> None:
        namespace = self.load_validator_namespace()
        validate_scientific_sources = cast(
            Callable[
                [str, str, list[str], dict[str, str], dict[str, str]],
                None,
            ],
            namespace["validate_scientific_sources"],
        )
        source_kinds = {
            "SRC-HPV16-REFSEQ": "official_database",
            "SRC-HPV-P16-PMC8409095": "peer_reviewed_review",
        }
        source_domains = {
            "SRC-HPV16-REFSEQ": "biomedicine",
            "SRC-HPV-P16-PMC8409095": "biomedicine",
        }
        with self.assertRaises(SystemExit):
            validate_scientific_sources(
                "COSMO-D-006",
                "biomedicine",
                ["SRC-HPV-P16-PMC8409095"],
                source_kinds,
                source_domains,
            )
        validate_scientific_sources(
            "COSMO-D-006",
            "biomedicine",
            ["SRC-HPV16-REFSEQ"],
            source_kinds,
            source_domains,
        )

    def test_documentary_anchor_ignores_latex_comments(self) -> None:
        namespace = self.load_validator_namespace()
        strip_comments = cast(
            Callable[[str, str], str],
            namespace["strip_public_nonrendered_comments"],
        )
        rendered = strip_comments(
            "sample.tex",
            "% COSMO-D-004 supporting passage removed\n",
        )
        self.assertNotIn("COSMO-D-004", rendered)
        disabled = strip_comments(
            "sample.tex",
            "\\iffalse COSMO-D-004\\fi\n",
        )
        self.assertNotIn("COSMO-D-004", disabled)
        visible_else = strip_comments(
            "sample.tex",
            "\\iffalse hidden\\else COSMO-D-004\\fi\n",
        )
        self.assertIn("COSMO-D-004", visible_else)
        label_only = strip_comments(
            "sample.tex",
            "\\label{COSMO-D-004}\n",
        )
        self.assertNotIn("COSMO-D-004", label_only)
        unused_macro = strip_comments(
            "sample.tex",
            (
                "\\newcommand{\\unusedDAnchor}"
                "{capsid branching (COSMO-D-011)}\n"
            ),
        )
        self.assertNotIn(
            "capsid branching (COSMO-D-011)",
            unused_macro,
        )

    def test_d004_provenance_anchor_is_claim_specific(self) -> None:
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-004"
        )
        self.assertEqual(
            claim["provenance"][0]["anchor"],
            "COSMO-D-004",
        )
        source = (REPOSITORY_ROOT / "cosmovirus.tex").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "$8$-dimensional representations "
            "$(\\mathbf{8}_v,\\mathbf{8}_s,\\mathbf{8}_c)$\n"
            "(COSMO-D-004).",
            source,
        )

    def test_d011_provenance_anchor_is_mapping_specific(self) -> None:
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-011"
        )
        self.assertEqual(
            claim["provenance"][0]["anchor"],
            "capsid branching (COSMO-D-011)",
        )
        source = (REPOSITORY_ROOT / "cosmovirus.tex").read_text(
            encoding="utf-8"
        )
        self.assertIn("capsid branching (COSMO-D-011)", source)

    def test_public_cross_domain_assertion_requires_claim_id(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        unsupported = (
            "Spin(8) triality biologically causes HPV16 capsid assembly."
        )
        validate_public_claim_text(
            "sample.md",
            (
                "Spin(8) triality and HPV16 capsid assembly "
                "are established topics."
            ),
            {},
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "Spin(8) triality is fundamental. "
                    "It causes HPV16 capsid assembly."
                ),
                {},
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                unsupported,
                claim_classes,
            )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) triality leads to HPV16 capsid assembly.",
                claim_classes,
            )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) causes HPV16 capsid assembly.",
                claim_classes,
            )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "Spin(8) triality controls the assembly of "
                    "HPV16 capsids."
                ),
                claim_classes,
            )

        validate_public_claim_text(
            "README.md",
            "Spin(8) has triality and HPV16 causes cervical cancer.",
            claim_classes,
        )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) and HPV16 jointly cause capsid assembly.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) triality activates HPV16 capsid assembly.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) triality inhibits HPV16 capsid assembly.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "Spin(8) triality prevents HPV16 capsid assembly.",
                {},
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) triality makes HPV16 capsid assembly happen.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) triality is necessary for HPV16 capsid assembly.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "Spin(8) triality is essential for HPV16 capsid assembly.",
                {},
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "HPV16 capsid assembly depends on Spin(8) triality.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "HPV16 capsid assembly requires Spin(8) triality.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "HPV16 capsid assembly is poorly understood. "
                    "Spin(8) triality determines it."
                ),
                {},
            )
        validate_public_claim_text(
            "sample.md",
            (
                "There is no evidence that Spin(8) triality causes "
                "HPV16 capsid assembly."
            ),
            {},
        )
        validate_public_claim_text(
            "sample.md",
            (
                "There is insufficient evidence that Spin(8) triality causes "
                "HPV16 capsid assembly."
            ),
            {},
        )

        for causal_verb in ("controls", "regulates", "modulates", "governs"):
            with self.subTest(causal_verb=causal_verb):
                with self.assertRaises(SystemExit):
                    validate_public_claim_text(
                        "README.md",
                        (
                            "Spin(8) triality "
                            + causal_verb
                            + " HPV16 capsid assembly."
                        ),
                        claim_classes,
                    )

        for misbound in (
            (
                "COSMO-D-004 documents Spin(8) triality. "
                "Spin(8) triality causes HPV16 capsid assembly."
            ),
            (
                "COSMO-D-004 records that Spin(8) triality causes HPV16 "
                "capsid assembly."
            ),
        ):
            with self.subTest(misbound=misbound):
                with self.assertRaises(SystemExit):
                    validate_public_claim_text(
                        "README.md",
                        misbound,
                        claim_classes,
                    )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "COSMO-D-011: Spin(8) causes HPV E6 degradation.",
                claim_classes,
            )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "COSMO-D-011: Spin(8) triality causes HPV16 capsid assembly.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "COSMO-D-011: This goes beyond a symbolic association: "
                    "Spin(8) triality causes HPV16 capsid assembly."
                ),
                claim_classes,
            )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "COSMO-D-012: Triality causes HPV16 capsid assembly.",
                claim_classes,
            )
        validate_public_claim_text(
            "README.md",
            (
                "COSMO-D-012 proposes that triality could predict "
                "HPV16 capsid assembly."
            ),
            claim_classes,
        )

        governed = (
            "COSMO-D-011 records that Spin(8) triality causes HPV16 "
            "capsid assembly only as a claim subject to its ledger class."
        )
        validate_public_claim_text(
            "README.md",
            governed,
            claim_classes,
        )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "COSMO-D-009: Spin(8) triality causes "
                    "HPV16 capsid assembly."
                ),
                claim_classes,
            )

    def test_public_claim_guard_decodes_character_references(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        encoded = (
            "Spin&#40;8&#41; tria&#108;ity causes "
            "HPV&#49;6 cap&#115;id assembly."
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text("sample.md", encoded, {})

    def test_public_claim_guard_preserves_encoded_html_as_visible_text(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "&lt;script&gt;Spin(8) triality causes "
                    "HPV16 capsid assembly.&lt;/script&gt;"
                ),
                {},
            )

    def test_public_claim_guard_normalizes_markdown_rendering(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                r"Spin\(8\) causes H**PV16** cap**sid** assembly.",
                {},
            )

    def test_public_claim_guard_normalizes_markdown_code_spans(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "Sp`in(8)` tr`iality` ca`uses` "
                "H`PV16` cap`sid` assembly.",
                {},
            )

    def test_public_claim_guard_strips_inline_html_tags(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "Spin(8) tria<em></em>lity causes "
                    "H<em></em>PV16 cap<em></em>sid assembly."
                ),
                claim_classes,
            )

    def test_public_claim_guard_ignores_html_raw_text_payloads(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            (
                '<script type="application/json">'
                '{"note":"Spin(8) triality causes HPV16 capsid assembly."}'
                "</script>"
                "<style>.x{content:'Spin(8) triality causes HPV16 capsid assembly.'}</style>"
            ),
            {},
        )

    def test_public_claim_guard_preserves_html_paragraph_boundaries(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "<p>COSMO-D-012</p>\n"
                    "<p>Spin(8) triality causes HPV16 capsid assembly.</p>"
                ),
                claim_classes,
            )

    def test_public_claim_guard_ignores_hidden_html_subtrees(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            (
                "<div hidden>"
                "Spin(8) triality causes HPV16 capsid assembly."
                "</div>"
            ),
            {},
        )

    def test_public_claim_guard_ignores_css_hidden_html(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    '<span style="display:none">'
                    "COSMO-D-011 symbolic association"
                    "</span> "
                    "Spin(8) triality causes HPV16 capsid assembly."
                ),
                claim_classes,
            )

    def test_public_claim_guard_ignores_template_contents(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "<template>COSMO-D-011 symbolic association</template> "
                    "Spin(8) triality causes HPV16 capsid assembly."
                ),
                claim_classes,
            )

    def test_public_definition_items_do_not_share_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "<dl><dt>COSMO-D-011 symbolic association</dt>"
                    "<dd>Spin(8) triality causes HPV16 capsid assembly.</dd></dl>"
                ),
                claim_classes,
            )

    def test_public_html_table_cells_do_not_share_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "<table><tr>"
                    "<td>COSMO-D-011 symbolic association</td>"
                    "<td>Spin(8) triality causes HPV16 capsid assembly.</td>"
                    "</tr></table>"
                ),
                claim_classes,
            )

    def test_public_claim_guard_handles_quoted_greater_than_in_html(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    'Spin<span title="1 > 0"></span>(8) '
                    'tria<span title="1 > 0"></span>lity causes '
                    'H<span title="1 > 0"></span>PV16 capsid assembly.'
                ),
                claim_classes,
            )

    def test_public_heading_does_not_govern_following_paragraph(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "# COSMO-D-012\n"
                    "Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                claim_classes,
            )

    def test_public_setext_heading_does_not_govern_following_paragraph(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "COSMO-D-012\n============\n"
                "Spin(8) triality causes HPV16 capsid assembly.\n",
                claim_classes,
            )

    def test_public_blockquote_paragraphs_do_not_share_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "> COSMO-D-011\n"
                    ">\n"
                    "> Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                claim_classes,
            )

    def test_public_list_items_do_not_share_claim_binding_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "- COSMO-D-012\n"
                    "- Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                claim_classes,
            )

    def test_public_nested_list_items_do_not_share_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "- COSMO-D-011 records a symbolic association\n"
                    "    - Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                claim_classes,
            )

    def test_public_claim_guard_scans_markdown_table_cells(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "| Claim | Status |\n"
                    "| --- | --- |\n"
                    "| Spin(8) triality causes HPV16 capsid assembly. | open |\n"
                ),
                {},
            )

    def test_public_latex_heading_does_not_govern_following_prose(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    "\\section{Symbolic association COSMO-D-011}\n"
                    "Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                claim_classes,
            )

    def test_public_latex_table_rows_do_not_share_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    "\\begin{tabular}{l}\n"
                    "COSMO-D-011 symbolic association \\\\\n"
                    "Spin(8) triality causes HPV16 capsid assembly. \\\\\n"
                    "\\end{tabular}\n"
                ),
                claim_classes,
            )

    def test_public_latex_list_items_do_not_share_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    "\\begin{itemize}\n"
                    "\\item COSMO-D-011 symbolic association\n"
                    "\\item Spin(8) triality causes HPV16 capsid assembly.\n"
                    "\\end{itemize}\n"
                ),
                claim_classes,
            )

    def test_public_claim_guard_scans_latex_table_cells(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    "\\begin{tabular}{ll}\n"
                    "Spin(8) triality causes HPV16 capsid assembly. & open \\\\n"
                    "\\end{tabular}\n"
                ),
                {},
            )

    def test_public_claim_guard_expands_repository_latex_macros(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                r"\TRI causes \HPV capsid assembly.",
                {},
            )

    def test_public_claim_guard_recognizes_subscripted_hpv16(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                r"$E_{8}$ causes $HPV_{16}$ infection.",
                {},
            )

    def test_public_claim_guard_normalizes_latex_formatting(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    r"Spin(8) tria\textit{lity} causes "
                    r"H\textbf{PV}16 cap\emph{sid} assembly."
                ),
                {},
            )

    def test_public_latex_paragraph_command_splits_claim_scope(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    "COSMO-D-012\\par "
                    "Spin(8) triality causes HPV16 capsid assembly."
                ),
                claim_classes,
            )

    def test_public_claim_guard_ignores_latex_phantom_content(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    r"\phantom{ COSMO-D-011 } Symbolic association "
                    r"Spin(8) triality causes HPV16 capsid assembly."
                ),
                claim_classes,
            )

    def test_public_claim_guard_strips_false_latex_ifnum_branch(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    r"\ifnum0=1 COSMO-D-011 symbolic association\fi "
                    r"Spin(8) triality causes HPV16 capsid assembly."
                ),
                {"COSMO-D-011": "SYMBOLIC"},
            )

    def test_public_claim_guard_expands_parameterized_user_latex_macro(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    r"\newcommand{\bridge}[1]"
                    r"{Spin(8) triality causes HPV16 #1.}"
                    r"\bridge{capsid assembly}"
                ),
                {},
            )

    def test_public_claim_guard_expands_invoked_user_latex_macro(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    r"\newcommand{\bridge}"
                    r"{Spin(8) triality causes HPV16 capsid assembly.}"
                    r"\bridge"
                ),
                {},
            )

    def test_public_claim_guard_normalizes_latex_href_label(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    r"Spin(8) triality ca\href{https://example.org}{uses} "
                    r"HPV16 capsid assembly."
                ),
                {},
            )

    def test_public_claim_guard_normalizes_latex_textcolor(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                r"Spin(8) triality ca\textcolor{red}{uses} HPV16 capsid assembly.",
                {},
            )

    def test_public_claim_guard_normalizes_latex_mbox(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                r"Spin(8) triality ca\mbox{uses} HPV16 capsid assembly.",
                {},
            )

    def test_public_e7_math_context_is_not_biomedical(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "math.md",
            "E8 branching produces E7 representations.",
            {},
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "Spin(8) triality causes E7 protein expression.",
                {},
            )

    def test_public_claim_guard_recognizes_spelled_out_hpv16(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "Spin(8) triality causes human papillomavirus "
                    "type 16 infection."
                ),
                {},
            )

    def test_public_claim_domains_are_proposition_local(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            "Spin(8) is a mathematical group, while HPV16 causes cancer.",
            {},
        )

    def test_public_negation_only_suppresses_its_own_assertion(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
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
            (
                "Although Spin(8) is not biological, Spin(8) triality "
                "causes HPV16 capsid assembly."
            ),
        ):
            with self.subTest(text=unsupported):
                with self.assertRaises(SystemExit):
                    validate_public_claim_text(
                        "README.md",
                        unsupported,
                        claim_classes,
                    )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "There is no doubt that Spin(8) triality causes HPV16 capsid assembly.",
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "Spin(8) triality cannot be ignored because it causes "
                    "HPV16 capsid assembly."
                ),
                claim_classes,
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "No caveat changes the fact that Spin(8) triality "
                    "causes HPV16 capsid assembly."
                ),
                claim_classes,
            )

        validate_public_claim_text(
            "README.md",
            "Spin(8) triality does not cause HPV16 capsid assembly.",
            claim_classes,
        )

        validate_public_claim_text(
            "README.md",
            "Triality causes no HPV16 capsid changes.",
            claim_classes,
        )

        validate_public_claim_text(
            "README.md",
            "Spin(8) triality fails to cause HPV16 capsid assembly.",
            claim_classes,
        )

        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "Spin(8) triality not only causes HPV16 capsid assembly, "
                    "but also promotes p16 expression."
                ),
                claim_classes,
            )

        validate_public_claim_text(
            "README.md",
            (
                "Spin(8) is mathematical context. "
                "HPV16 capsid assembly is biological context. "
                "PR A proves a local integer result."
            ),
            claim_classes,
        )

    def test_public_mechanism_nouns_are_not_causal_by_themselves(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            (
                "The Spin(8) triality mechanism differs from the "
                "HPV16 mechanism."
            ),
            {},
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "Spin(8) triality is the mechanism for HPV16 capsid assembly.",
                {},
            )

    def test_public_claim_scan_ignores_nonrendered_comments(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "cosmovirus.tex",
            "% Triality causes HPV16 capsid assembly.\n",
            {},
        )
        validate_public_claim_text(
            "README.md",
            "<!-- Spin(8) causes HPV16 capsid assembly. -->\n",
            {},
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.tex",
                (
                    "Sp% join\n"
                    "in(8) tria% join\n"
                    "lity ca% join\n"
                    "uses H% join\n"
                    "PV16 cap% join\n"
                    "sid assembly."
                ),
                {},
            )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "Sp<!--x-->in(8) tria<!--x-->lity "
                    "ca<!--x-->uses H<!--x-->PV16 cap<!--x-->sid assembly."
                ),
                {},
            )

    def test_d005_provenance_anchor_is_claim_specific(self) -> None:
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-005"
        )
        self.assertEqual(
            claim["provenance"][0]["anchor"],
            "COSMO-D-005",
        )
        source = (REPOSITORY_ROOT / "cosmovirus.tex").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "edge-sharing $\\mathrm{SiS_4}$ tetrahedra (COSMO-D-005)",
            source,
        )

    def test_public_claim_scan_strips_fences_before_html_comments(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "```text\n"
                    "<!--\n"
                    "```\n\n"
                    "Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                {},
            )

    def test_public_claim_scan_ignores_indented_markdown_code(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            "    Spin(8) triality causes HPV16 capsid assembly.\n",
            {},
        )

    def test_public_claim_scan_preserves_list_continuation_prose(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                (
                    "- Context\n"
                    "    Spin(8) triality causes HPV16 capsid assembly.\n"
                ),
                {},
            )

    def test_public_claim_scan_ignores_markdown_reference_destinations(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            "[ref]: https://example.com/triality-causes-HPV16-capsid\n",
            {},
        )

    def test_public_claim_scan_stops_reference_definition_at_blank_line(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "sample.md",
                "[ref]:\n\nSpin(8) triality causes HPV16 capsid assembly.\n",
                {},
            )

    def test_public_claim_scan_ignores_markdown_link_destinations(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        validate_public_claim_text(
            "sample.md",
            (
                "See [the source]"
                "(https://example.com/triality-causes-HPV16-capsid)."
            ),
            {},
        )

    def test_public_claim_scan_rejects_unknown_ids_without_causality(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        claim_classes = {
            claim["id"]: claim["class"]
            for claim in self.load_ledger()["claims"]
        }
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "See COSMO-D-999 for evidence.",
                claim_classes,
            )

    def test_public_claim_scan_keeps_prose_adjacent_to_fenced_blocks(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                (
                    "Spin(8) triality causes HPV16 capsid assembly.\n"
                    "```text\n"
                    "Spin(8) triality causes HPV16 capsid assembly.\n"
                    "```\n"
                ),
                {},
            )
        validate_public_claim_text(
            "README.md",
            (
                "```text\n"
                "Spin(8) triality causes HPV16 capsid assembly.\n"
                "```\n"
            ),
            {},
        )

    def test_public_claim_guard_detects_enabling_language(self) -> None:
        namespace = self.load_validator_namespace()
        validate_public_claim_text = cast(
            Callable[[str, str, dict[str, str]], None],
            namespace["validate_public_claim_text"],
        )
        with self.assertRaises(SystemExit):
            validate_public_claim_text(
                "README.md",
                "Spin(8) triality enables HPV16 capsid assembly.",
                {},
            )

    def test_single_accession_source_identity_is_pinned(self) -> None:
        namespace = self.load_validator_namespace()
        validate_identity = cast(
            Callable[[str, dict[str, str]], None],
            namespace["validate_reviewed_source_identity"],
        )
        with self.assertRaises(SystemExit):
            validate_identity(
                "SRC-HPV16-REFSEQ",
                {"RefSeq": "NC_001527.1"},
            )
        validate_identity(
            "SRC-HPV16-REFSEQ",
            {"RefSeq": "NC_001526.4"},
        )

    def test_source_url_rejects_invalid_dns_hostname(self) -> None:
        namespace = self.load_validator_namespace()
        validate_source_url = cast(
            Callable[[str, object], Any],
            namespace["validate_source_url"],
        )
        with self.assertRaises(SystemExit):
            validate_source_url("SRC-TEST", "https://.")

    def test_visible_markdown_fields_escape_inline_constructs(self) -> None:
        namespace = self.load_validator_namespace()
        markdown_text = cast(
            Callable[[str], str],
            namespace["markdown_text"],
        )
        rendered = markdown_text(
            "![tracking](https://example.com/pixel)"
        )
        self.assertNotIn("![tracking]", rendered)
        self.assertIn("&#33;&#91;tracking&#93;", rendered)

    def test_provenance_validation_uses_captured_snapshot(self) -> None:
        namespace = self.load_validator_namespace()
        validate_provenance = cast(
            Callable[
                [str, str, object, dict[str, str] | None],
                set[str],
            ],
            namespace["validate_provenance"],
        )
        claim = next(
            claim for claim in self.load_ledger()["claims"]
            if claim["id"] == "COSMO-D-014"
        )
        snapshots = {
            "cosmo_core/storage.py": (
                REPOSITORY_ROOT / "cosmo_core" / "storage.py"
            ).read_text(encoding="utf-8"),
            "tests/test_phase_b5.py": (
                "import unittest\n"
                "class IntegratedRecoveryTests(unittest.TestCase):\n"
                "    def test_full_cube_recovers_one_bit_error_in_every_codeword("
                "self) -> None:\n"
                "        self.fail('unreviewed placeholder')\n"
            ),
        }
        with self.assertRaises(SystemExit):
            validate_provenance(
                "COSMO-D-014",
                "COMPUTATIONAL",
                claim["provenance"],
                snapshots,
            )

    def test_public_document_snapshot_survives_later_deletion(self) -> None:
        namespace = self.load_validator_namespace()
        snapshot_documents = cast(
            Callable[[Path], dict[str, str]],
            namespace["snapshot_public_documents"],
        )
        validate_documents = cast(
            Callable[[dict[str, str], dict[str, str] | None], None],
            namespace["validate_public_documents"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "UNSUPPORTED.md"
            target.write_text(
                "Spin(8) triality causes HPV16 capsid assembly.\n",
                encoding="utf-8",
            )
            snapshot = snapshot_documents(root)
            target.unlink()
            with self.assertRaises(SystemExit):
                validate_documents({}, snapshot)

    def test_public_latex_transclusions_are_scanned(self) -> None:
        namespace = self.load_validator_namespace()
        snapshot_documents = cast(
            Callable[[Path], dict[str, str]],
            namespace["snapshot_public_documents"],
        )
        validate_documents = cast(
            Callable[[dict[str, str], dict[str, str] | None], None],
            namespace["validate_public_documents"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "included-claim.tex").write_text(
                "\\input{bridge.txt}\n",
                encoding="utf-8",
            )
            (root / "bridge.txt").write_text(
                "Spin(8) triality causes HPV16 capsid assembly.\n",
                encoding="utf-8",
            )
            snapshot = snapshot_documents(root)
            self.assertIn(
                "Spin(8) triality causes HPV16 capsid assembly.",
                snapshot["included-claim.tex"],
            )
            with self.assertRaises(SystemExit):
                validate_documents({}, snapshot)

    def test_public_html_documents_are_discovered_and_scanned(self) -> None:
        namespace = self.load_validator_namespace()
        snapshot_documents = cast(
            Callable[[Path], dict[str, str]],
            namespace["snapshot_public_documents"],
        )
        validate_documents = cast(
            Callable[[dict[str, str], dict[str, str] | None], None],
            namespace["validate_public_documents"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "unledgered-public.html"
            target.write_text(
                "<p>Spin(8) triality causes HPV16 capsid assembly.</p>\n",
                encoding="utf-8",
            )
            snapshot = snapshot_documents(root)
            self.assertIn("unledgered-public.html", snapshot)
            with self.assertRaises(SystemExit):
                validate_documents({}, snapshot)

    def test_canonical_index_rejects_noncanonical_line_endings(self) -> None:
        namespace = self.load_validator_namespace()
        render_index = cast(
            Callable[[dict[str, Any]], str],
            namespace["render_index"],
        )
        snapshot_documents = cast(
            Callable[[Path], dict[str, str]],
            namespace["snapshot_public_documents"],
        )
        validate_index = cast(
            Callable[[str, dict[str, Any]], None],
            namespace["validate_canonical_index_text"],
        )

        ledger = self.load_ledger()
        canonical = render_index(ledger).encode("utf-8")
        self.assertIn(b"\n", canonical)
        self.assertNotIn(b"\r", canonical)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            index = root / "CLAIM-LEDGER.md"

            for label, newline in (
                ("LF", b"\n"),
                ("CRLF", b"\r\n"),
                ("CR", b"\r"),
            ):
                with self.subTest(line_endings=label):
                    payload = canonical.replace(b"\n", newline)
                    index.write_bytes(payload)
                    captured = snapshot_documents(root)
                    captured_text = captured["CLAIM-LEDGER.md"]

                    self.assertEqual(
                        captured_text.encode("utf-8"),
                        payload,
                    )
                    if label == "LF":
                        validate_index(captured_text, ledger)
                    else:
                        with self.assertRaisesRegex(
                            SystemExit,
                            "CLAIM-LEDGER.md differs from canonical JSON rendering",
                        ):
                            validate_index(captured_text, ledger)

    def test_public_document_discovery_includes_new_root_documents(self) -> None:
        namespace = self.load_validator_namespace()
        discover_paths = cast(
            Callable[[Path], tuple[str, ...]],
            namespace["discover_public_governed_paths"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("readme\n", encoding="utf-8")
            (root / "EXTRA.markdown").write_text(
                "public markdown\n",
                encoding="utf-8",
            )
            (root / "NEW_PUBLIC.md").write_text(
                "Spin(8) triality causes HPV16 capsid assembly.\n",
                encoding="utf-8",
            )
            (root / "PUBLIC.html").write_text(
                "<p>public html</p>\n",
                encoding="utf-8",
            )
            audit = root / "audit"
            audit.mkdir()
            (audit / "AUDIT-RESOLUTION.md").write_text(
                "Spin(8) triality causes HPV16 capsid assembly.\n",
                encoding="utf-8",
            )
            dependency = (
                root / ".venv" / "lib" / "site-packages" / "review_fixture"
            )
            dependency.mkdir(parents=True)
            (dependency / "README.md").write_text(
                "Spin(8) triality causes HPV16 capsid assembly.\n",
                encoding="utf-8",
            )
            (root / "notes.txt").write_text("not public\n", encoding="utf-8")
            self.assertEqual(
                discover_paths(root),
                (
                    "EXTRA.markdown",
                    "NEW_PUBLIC.md",
                    "PUBLIC.html",
                    "README.md",
                    "audit/AUDIT-RESOLUTION.md",
                ),
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
