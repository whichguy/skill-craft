#!/usr/bin/env python3
"""Focused pure-model tests for managed ShipLoop SDLC records."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_sdlc as sdlc  # noqa: E402


def coverage() -> list[dict[str, str]]:
    return [
        {
            "surface": "unit",
            "disposition": "selected",
            "reason": "The deterministic serializer has direct boundary assertions.",
        },
        {
            "surface": "mock_fake",
            "disposition": "not-applicable",
            "reason": "The selected serializer has no collaborator boundary.",
        },
        {
            "surface": "integration",
            "disposition": "not-applicable",
            "reason": "The selected local contract has no service integration.",
        },
        {
            "surface": "end_to_end",
            "disposition": "not-applicable",
            "reason": "The selected local contract has no end-user journey.",
        },
        {
            "surface": "browser_service_api",
            "disposition": "not-applicable",
            "reason": "The selected local contract exposes no browser or API boundary.",
        },
    ]


def case(case_id: str = "CASE-CSV-001", contract_id: str = "T-CSV-001") -> dict:
    return {
        "case_id": case_id,
        "contract_id": contract_id,
        "requirement": "CSV records with commas must remain one field after export.",
        "inputs": ["A record whose label contains a comma."],
        "expected_outcome": "The exported CSV field is quoted and parses as the original label.",
        "test_selectors": ["test/test_csv.py::test_quotes_commas"],
        "check_ids": ["T-CSV-001"],
        "environment": "Local Python test environment with the repository parser.",
        "fixture": "A temporary CSV output file with one comma-containing label.",
    }


def plan(*cases: dict) -> dict:
    return {"cases": list(cases or (case(),)), "coverage": coverage()}


def manifest(*, argv: list[str] | None = None, kind: str = "test") -> dict:
    return {
        "checks": [
            {
                "id": "T-CSV-001",
                "kind": kind,
                "argv": argv or ["python3", "-m", "pytest", "test/test_csv.py::test_quotes_commas"],
                "acceptance": [],
            },
            {
                "id": "CHECK-LINT",
                "kind": "lint",
                "argv": ["python3", "-m", "ruff", "check", "test"],
                "acceptance": [],
            },
        ]
    }


def bindings(*, selection: dict | None = None, argv: list[str] | None = None) -> dict:
    return {
        "bindings": [
            {
                "check_id": "T-CSV-001",
                "argv": argv or ["python3", "-m", "pytest", "test/test_csv.py::test_quotes_commas"],
                "case_ids": ["CASE-CSV-001"],
                "selectors": ["test/test_csv.py::test_quotes_commas"],
                "selection": selection
                or {"mode": "direct", "evidence": "The test command names the planned selector directly."},
            }
        ]
    }


class ManagedSdlcTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-sdlc-")
        self.repo = Path(self.tmp.name)
        test = self.repo / "test"
        test.mkdir()
        (test / "test_csv.py").write_text("def test_quotes_commas():\n    assert True\n", encoding="utf-8")
        (self.repo / "pyproject.toml").write_text(
            "# Selected suite discovery includes test/test_csv.py\n",
            encoding="utf-8",
        )
        skill = self.repo / "skills" / "csv-helper"
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: csv-helper\ndescription: Run the repository CSV helper.\n---\n# CSV helper\n",
            encoding="utf-8",
        )
        (skill / "scripts" / "demo.py").write_text("print('csv helper')\n", encoding="utf-8")
        (self.repo / "README.md").write_text(
            "# Fixture\n\n[CSV helper](skills/csv-helper/SKILL.md)\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def refinement(self, *, oracle: dict | None = None, disposition: str = "authored") -> dict:
        row = {
            "case_id": "CASE-CSV-001",
            "disposition": disposition,
            "test_paths": ["test/test_csv.py"],
            "check_ids": ["T-CSV-001"],
            "coverage": "The test exercises the planned comma escaping boundary.",
            "oracle": oracle or {"decision": "unchanged"},
        }
        if disposition == "reused":
            row["adequacy_reason"] = "The existing test has the exact planned input and independent assertion."
        return {"cases": [row]}

    def skill(self, *, decision: str = "created") -> dict:
        return {
            "decision": decision,
            "rationale": "The repeated repository CSV operation needs one discoverable local procedure.",
            "entrypoint": "skills/csv-helper/SKILL.md",
            "index": "README.md",
            "executable_examples": [
                {
                    "path": "skills/csv-helper/scripts/demo.py",
                    "check_id": "CHECK-CSV-HELPER",
                    "purpose": "The helper example exercises the documented local command path.",
                }
            ],
            "failure_recovery": "Report malformed input and preserve the original CSV for correction.",
            "host_limitations": "The procedure only documents local repository behavior and grants no remote authority.",
        }

    def test_local_plan_is_idempotent_and_exposes_references(self) -> None:
        raw = plan()
        normalized = sdlc.validate_local_test_plan(
            raw,
            required_contract_ids=("T-CSV-001",),
            check_ids=("T-CSV-001", "CHECK-LINT"),
        )
        self.assertEqual(normalized, raw)
        self.assertEqual(sdlc.validate_local_test_plan(normalized), normalized)
        refs = sdlc.test_plan_references(normalized)
        self.assertEqual(refs["case_ids"], ["CASE-CSV-001"])
        self.assertEqual(refs["contract_ids"], ["T-CSV-001"])
        self.assertEqual(refs["check_ids"], ["T-CSV-001"])
        self.assertEqual(refs["test_paths"], ["test/test_csv.py"])

    def test_missing_required_case_or_contract_is_rejected(self) -> None:
        with self.assertRaisesRegex(sdlc.SdlcError, "missing required contract IDs"):
            sdlc.validate_local_test_plan(plan(), required_contract_ids=("T-MISSING-001",))
        with self.assertRaisesRegex(sdlc.SdlcError, "missing required case IDs"):
            sdlc.validate_local_test_plan(plan(), required_case_ids=("CASE-MISSING-001",))

    def test_multiple_cases_can_cover_one_contract_but_case_ids_are_unique(self) -> None:
        extra = case("CASE-CSV-002", "T-CSV-001")
        extra["inputs"] = ["A record whose label contains a quote and comma."]
        extra["expected_outcome"] = "The exported CSV escapes the quote and parses as the original label."
        accepted = sdlc.validate_local_test_plan(plan(case(), extra), required_contract_ids=("T-CSV-001",))
        self.assertEqual([row["contract_id"] for row in accepted["cases"]], ["T-CSV-001", "T-CSV-001"])
        duplicate = plan(case(), deepcopy(case()))
        with self.assertRaisesRegex(sdlc.SdlcError, "case IDs must not duplicate"):
            sdlc.validate_local_test_plan(duplicate)

    def test_unsafe_test_selector_and_unknown_pass_flag_are_rejected(self) -> None:
        unsafe = plan()
        unsafe["cases"][0]["test_selectors"] = ["../outside/test_csv.py::test_quotes_commas"]
        with self.assertRaisesRegex(sdlc.SdlcError, "repo-relative"):
            sdlc.validate_local_test_plan(unsafe)
        placeholder = plan()
        placeholder["cases"][0]["expected_outcome"] = "TBD"
        with self.assertRaisesRegex(sdlc.SdlcError, "placeholder"):
            sdlc.validate_local_test_plan(placeholder)
        missing_check = plan()
        with self.assertRaisesRegex(sdlc.SdlcError, "absent from the supplied manifest"):
            sdlc.validate_local_test_plan(missing_check, check_ids=("CHECK-LINT",))
        flagged = plan()
        flagged["passed"] = True
        with self.assertRaisesRegex(sdlc.SdlcError, "unexpected schema"):
            sdlc.validate_local_test_plan(flagged)

    def test_refinement_covers_every_planned_case_with_existing_test_and_manifest_id(self) -> None:
        accepted = sdlc.validate_test_refinement(
            self.refinement(),
            plan(),
            self.repo,
            check_ids=("T-CSV-001",),
        )
        self.assertEqual(accepted["cases"][0]["test_paths"], ["test/test_csv.py"])
        refs = sdlc.test_refinement_references(self.refinement(), plan(), self.repo)
        self.assertEqual(refs["check_ids"], ["T-CSV-001"])
        missing = {"cases": []}
        with self.assertRaisesRegex(sdlc.SdlcError, "must be a nonempty list"):
            sdlc.validate_test_refinement(missing, plan(), self.repo)
        second = case("CASE-CSV-002", "T-CSV-001")
        second["inputs"] = ["A record whose label contains a quote and comma."]
        second["expected_outcome"] = "The exported CSV escapes the quote and parses as the original label."
        with self.assertRaisesRegex(sdlc.SdlcError, "cover every planned case"):
            sdlc.validate_test_refinement(self.refinement(), plan(case(), second), self.repo)
        unsafe = self.refinement()
        unsafe["cases"][0]["test_paths"] = ["../outside/test_csv.py"]
        with self.assertRaisesRegex(sdlc.SdlcError, "repo-relative"):
            sdlc.validate_test_refinement(unsafe, plan(), self.repo)

    def test_oracle_weakening_and_unjustified_correction_are_rejected(self) -> None:
        weakened = self.refinement(
            oracle={
                "decision": "corrected",
                "old_expected_outcome": case()["expected_outcome"],
                "new_expected_outcome": case()["inputs"][0],
                "basis": "The frozen requirement defines a different observable output.",
                "preserved_coverage": "The same parser boundary remains selected.",
            }
        )
        with self.assertRaisesRegex(sdlc.SdlcError, "remain independent"):
            sdlc.validate_test_refinement(weakened, plan(), self.repo)
        ungrounded = self.refinement(
            oracle={
                "decision": "corrected",
                "old_expected_outcome": case()["expected_outcome"],
                "new_expected_outcome": "The escaped field preserves the label after a second parser round trip.",
                "preserved_coverage": "The same parser boundary remains selected.",
            }
        )
        with self.assertRaisesRegex(sdlc.SdlcError, "corrected has an unexpected schema"):
            sdlc.validate_test_refinement(ungrounded, plan(), self.repo)

    def test_reused_test_requires_an_adequacy_reason(self) -> None:
        valid = sdlc.validate_test_refinement(self.refinement(disposition="reused"), plan(), self.repo)
        self.assertEqual(valid["cases"][0]["disposition"], "reused")
        incomplete = self.refinement(disposition="reused")
        del incomplete["cases"][0]["adequacy_reason"]
        with self.assertRaisesRegex(sdlc.SdlcError, "unexpected schema"):
            sdlc.validate_test_refinement(incomplete, plan(), self.repo)

    def test_test_bindings_preserve_case_selector_check_and_exact_manifest_argv(self) -> None:
        normalized = sdlc.validate_test_bindings(
            bindings(),
            plan(),
            self.refinement(),
            self.repo,
            manifest=manifest(),
        )
        self.assertEqual(normalized, bindings())
        refs = sdlc.test_binding_references(
            bindings(), plan(), self.refinement(), self.repo, manifest=manifest()
        )
        self.assertEqual(refs["check_ids"], ["T-CSV-001"])
        self.assertEqual(refs["test_paths"], ["test/test_csv.py"])
        self.assertEqual(
            refs["argv_by_check"]["T-CSV-001"],
            ["python3", "-m", "pytest", "test/test_csv.py::test_quotes_commas"],
        )

    def test_test_bindings_reject_wrong_command_omitted_selector_and_wrong_check_kind(self) -> None:
        wrong_command = bindings(
            argv=["python3", "-m", "pytest", "test/test_other.py::test_quotes_commas"]
        )
        with self.assertRaisesRegex(sdlc.SdlcError, "exactly match the current manifest command"):
            sdlc.validate_test_bindings(wrong_command, plan(), self.refinement(), self.repo, manifest=manifest())

        extended = plan()
        extended["cases"][0]["test_selectors"].append("test/test_csv.py::test_quote_comma_combo")
        with self.assertRaisesRegex(sdlc.SdlcError, "cover every planned selector"):
            sdlc.validate_test_bindings(bindings(), extended, self.refinement(), self.repo, manifest=manifest())

        with self.assertRaisesRegex(sdlc.SdlcError, "must name a test check"):
            sdlc.validate_test_bindings(bindings(), plan(), self.refinement(), self.repo, manifest=manifest(kind="lint"))

        rebound = bindings()
        rebound["bindings"].append(deepcopy(rebound["bindings"][0]))
        with self.assertRaisesRegex(sdlc.SdlcError, "must not repeat a check ID"):
            sdlc.validate_test_bindings(rebound, plan(), self.refinement(), self.repo, manifest=manifest())

    def test_suite_binding_needs_existing_evidence_that_names_the_selected_path(self) -> None:
        suite = bindings(
            argv=["python3", "-m", "pytest"],
            selection={
                "mode": "suite",
                "evidence": "The local pytest discovery configuration selects the recorded test path.",
                "evidence_path": "pyproject.toml",
            },
        )
        suite_manifest = manifest(argv=["python3", "-m", "pytest"])
        normalized = sdlc.validate_test_bindings(suite, plan(), self.refinement(), self.repo, manifest=suite_manifest)
        self.assertEqual(normalized["bindings"][0]["selection"]["evidence_path"], "pyproject.toml")
        refs = sdlc.test_binding_references(suite, plan(), self.refinement(), self.repo, manifest=suite_manifest)
        self.assertEqual(refs["suite_evidence_paths"], ["pyproject.toml"])
        (self.repo / "pyproject.toml").write_text("# Generic local configuration\n", encoding="utf-8")
        with self.assertRaisesRegex(sdlc.SdlcError, "must identify every selected"):
            sdlc.validate_test_bindings(suite, plan(), self.refinement(), self.repo, manifest=suite_manifest)

    def test_skill_requires_actual_entrypoint_index_and_executable_example(self) -> None:
        normalized = sdlc.validate_skill_validation(self.skill(), self.repo, check_ids=("CHECK-CSV-HELPER",))
        self.assertEqual(normalized["entrypoint"], "skills/csv-helper/SKILL.md")
        refs = sdlc.skill_validation_references(self.skill(), self.repo)
        self.assertEqual(refs["check_ids"], ["CHECK-CSV-HELPER"])
        missing_examples = self.skill()
        missing_examples["executable_examples"] = []
        with self.assertRaisesRegex(sdlc.SdlcError, "executable_examples must be a nonempty list"):
            sdlc.validate_skill_validation(missing_examples, self.repo)
        escaped = self.skill()
        escaped["entrypoint"] = "../outside/SKILL.md"
        with self.assertRaisesRegex(sdlc.SdlcError, "repo-relative"):
            sdlc.validate_skill_validation(escaped, self.repo)
        (self.repo / "skills" / "csv-helper" / "SKILL.md").write_text(
            "---\nname: csv-helper\ndescription: >-\n---\n# CSV helper\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(sdlc.SdlcError, "meaningful description"):
            sdlc.validate_skill_validation(self.skill(), self.repo)

    def test_justified_reuse_and_not_needed_do_not_require_installation(self) -> None:
        reused = sdlc.validate_skill_validation(self.skill(decision="reused"), self.repo)
        self.assertEqual(reused["decision"], "reused")
        not_needed = sdlc.validate_skill_validation(
            {
                "decision": "not-needed",
                "rationale": "This one-off correction has no reusable repository procedure.",
            },
            self.repo,
        )
        self.assertEqual(not_needed["decision"], "not-needed")
        install_flag = self.skill()
        install_flag["install"] = True
        with self.assertRaisesRegex(sdlc.SdlcError, "unexpected schema"):
            sdlc.validate_skill_validation(install_flag, self.repo)

    def test_catalog_has_exactly_the_flat_nodes_and_explicit_flags(self) -> None:
        catalog = sdlc.sdlc_node_catalog()
        self.assertEqual(len(catalog), 36)
        self.assertEqual([row["id"] for row in catalog], [f"N{number:02d}" for number in range(1, 37)])
        self.assertEqual(
            [row["id"] for row in catalog if row["improve"]],
            ["N03", "N05", "N07", "N11", "N19", "N21", "N24", "N28", "N30", "N35"],
        )
        self.assertEqual(
            [row["id"] for row in catalog if row["conditional"]],
            ["N17", "N26", "N32"],
        )
        self.assertEqual(sdlc.validate_sdlc_node_catalog(catalog), catalog)
        broken = deepcopy(catalog)
        broken[10]["improve"] = False
        with self.assertRaisesRegex(sdlc.SdlcError, "differs from the stable"):
            sdlc.validate_sdlc_node_catalog(broken)
        packet = sdlc.stage_responsibility("local_test_plan")
        self.assertEqual(packet["node_id"], "N10")
        self.assertFalse(packet["improve"])
        self.assertTrue(sdlc.stage_responsibility("N11")["improve"])
        self.assertEqual(sdlc.stage_responsibility("improve-plan")["node_id"], "N11")
        self.assertEqual(sdlc.stage_responsibility("test-refine")["node_id"], "N14")
        self.assertEqual(sdlc.stage_responsibility("research-finalize")["node_id"], "N03")
        self.assertEqual(sdlc.stage_responsibility("objective-review", base_stage="quality")["node_id"], "N31")
        self.assertEqual(sdlc.stage_responsibility("quality")["node_id"], "N31")


    def test_parked_managed_profiles_retain_their_sdlc_role(self) -> None:
        phases = {
            "research": "research-review", "behavior": "behavior-review",
            "spec": "spec-review", "objective": "objective-review",
            "step-plan": "step-plan-review", "product": "review",
        }
        for profile, phase in phases.items():
            with self.subTest(profile=profile):
                self.assertEqual(
                    sdlc.stage_responsibility("managed-improve", profile=profile),
                    sdlc.stage_responsibility(phase),
                )
        self.assertEqual(sdlc.stage_responsibility(
            "managed-improve", profile="objective", base_stage="quality")["node_id"], "N31")
        for profile in (None, "unknown", []):
            with self.assertRaisesRegex(sdlc.SdlcError, "requires a known profile"):
                sdlc.stage_responsibility("managed-improve", profile=profile)
        self.assertEqual(len(sdlc.sdlc_node_catalog()), 36)


if __name__ == "__main__":
    unittest.main()
