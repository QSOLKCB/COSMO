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

    def test_implementation_provenance_requires_executable_project_source(self) -> None:
        namespace = self.load_validator_namespace()
        validate_implementation = cast(
            Callable[[str, str, str, str], None],
            namespace["validate_computational_implementation_target"],
        )
        with self.assertRaises(SystemExit):
            validate_implementation(
                "COSMO-D-003",
                "README.md",
                "def validate_e8_root_system",
                "Phase B3\n",
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

    def test_reviewed_claim_definition_rejects_id_repurposing(self) -> None:
        namespace = self.load_validator_namespace()
        validate_definition = cast(
            Callable[[str, str, str], None],
            namespace["validate_reviewed_claim_definition"],
        )
        ledger = self.load_ledger()
        claim = next(
            claim for claim in ledger["claims"]
            if claim["id"] == "COSMO-D-003"
        )
        validate_definition(
            claim["id"],
            claim["class"],
            claim["statement"],
        )
        with self.assertRaises(SystemExit):
            validate_definition(
                "COSMO-D-003",
                "SYMBOLIC",
                "Unrelated symbolic replacement.",
            )

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

    def test_public_document_discovery_includes_new_root_documents(self) -> None:
        namespace = self.load_validator_namespace()
        discover_paths = cast(
            Callable[[Path], tuple[str, ...]],
            namespace["discover_public_governed_paths"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("readme\n", encoding="utf-8")
            (root / "NEW_PUBLIC.md").write_text(
                "Spin(8) triality causes HPV16 capsid assembly.\n",
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
                    "NEW_PUBLIC.md",
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
