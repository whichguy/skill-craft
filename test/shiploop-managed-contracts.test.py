#!/usr/bin/env python3
"""Focused protocol regressions for managed local-SDLC evidence.

These tests deliberately exercise the protocol adapters around the pure SDLC
validators.  They use a small real Git worktree and durable Markdown records
where the adapter binds mutable files or prior results; only unrelated
step-plan and managed-child machinery is patched at those seams.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_protocol as protocol  # noqa: E402
import shiploop_sdlc as sdlc  # noqa: E402
import shiploop_store as store  # noqa: E402


EXPECTED_OUTCOME = "The exported CSV field is quoted and parses as the original label."
SELECTOR = "test/test_csv.py::test_quotes_commas"
TEST_PATH = "test/test_csv.py"
TEST_CHECK = "T-CSV-001"


class RealGitCore:
    """Small core surface used by the managed protocol helpers under test."""

    def __init__(
        self,
        step: dict,
        env: dict[str, str],
        *,
        dag: dict | None = None,
        receipts: dict[str, dict] | None = None,
    ) -> None:
        self.step = deepcopy(step)
        self.env = env
        self.dag = deepcopy(dag) if dag is not None else {"steps": [self.step]}
        self.receipts = deepcopy(receipts) if receipts is not None else {}

    def steps_by_id(self, _root: Path) -> dict[str, dict]:
        return {self.step["id"]: deepcopy(self.step)}

    def load_dag(self, _root: Path) -> dict:
        return deepcopy(self.dag)

    def load_receipt(self, _root: Path, step_id: str) -> dict | None:
        value = self.receipts.get(step_id)
        return deepcopy(value) if value is not None else None

    @staticmethod
    def produces_texts(produces: object) -> list[str] | None:
        if isinstance(produces, str) and produces.strip():
            return [produces.strip()]
        if isinstance(produces, list) and all(isinstance(item, str) and item.strip() for item in produces):
            return [item.strip() for item in produces]
        return None

    def git_run(self, worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(worktree), *args],
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )


def coverage(*, blocked: bool = False) -> list[dict[str, str]]:
    return [
        {
            "surface": "unit",
            "disposition": "required-but-blocked" if blocked else "selected",
            "reason": (
                "The local Python fixture is unavailable until its test dependency is restored."
                if blocked
                else "The deterministic CSV boundary has a direct local assertion."
            ),
        },
        {
            "surface": "mock_fake",
            "disposition": "not-applicable",
            "reason": "The selected CSV formatter has no collaborator boundary.",
        },
        {
            "surface": "integration",
            "disposition": "not-applicable",
            "reason": "The selected local formatter has no service integration.",
        },
        {
            "surface": "end_to_end",
            "disposition": "not-applicable",
            "reason": "The selected formatter has no end-user journey.",
        },
        {
            "surface": "browser_service_api",
            "disposition": "not-applicable",
            "reason": "The selected formatter exposes no browser or API boundary.",
        },
    ]


def local_plan(*, case_id: str = "CASE-CSV-001", blocked: bool = False) -> dict:
    return {
        "cases": [
            {
                "case_id": case_id,
                "contract_id": TEST_CHECK,
                "requirement": "CSV records with commas must remain one field after export.",
                "inputs": ["A record whose label contains a comma."],
                "expected_outcome": EXPECTED_OUTCOME,
                "test_selectors": [SELECTOR],
                "check_ids": [TEST_CHECK],
                "environment": "Local Python test environment with the repository parser.",
                "fixture": "A temporary CSV output file with one comma-containing label.",
            }
        ],
        "coverage": coverage(blocked=blocked),
    }


def refinement() -> dict:
    return {
        "cases": [
            {
                "case_id": "CASE-CSV-001",
                "disposition": "authored",
                "test_paths": [TEST_PATH],
                "check_ids": [TEST_CHECK],
                "coverage": "The test executes the planned CSV comma escaping boundary.",
                "oracle": {"decision": "unchanged"},
            }
        ]
    }


def direct_bindings() -> dict:
    return {
        "bindings": [
            {
                "check_id": TEST_CHECK,
                "argv": ["python3", "-m", "pytest", SELECTOR],
                "case_ids": ["CASE-CSV-001"],
                "selectors": [SELECTOR],
                "selection": {
                    "mode": "direct",
                    "evidence": "The selected command names the planned test selector directly.",
                },
            }
        ]
    }


def suite_bindings() -> dict:
    return {
        "bindings": [
            {
                "check_id": TEST_CHECK,
                "argv": ["python3", "-m", "pytest"],
                "case_ids": ["CASE-CSV-001"],
                "selectors": [SELECTOR],
                "selection": {
                    "mode": "suite",
                    "evidence": "The repository suite discovery selects the authored CSV test path.",
                    "evidence_path": "pyproject.toml",
                },
            }
        ]
    }


class ManagedContractProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-managed-contracts-")
        base = Path(self.temp.name)
        self.run = base / "run"
        self.run.mkdir()
        self.worktree = base / "repo"
        self.worktree.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q")
        self.git("config", "user.name", "Managed contract fixture")
        self.git("config", "user.email", "managed-contract@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        (self.worktree / "test").mkdir()
        (self.worktree / TEST_PATH).write_text(
            "def test_quotes_commas():\n    assert True\n",
            encoding="utf-8",
        )
        (self.worktree / "pyproject.toml").write_text(
            "# Suite discovery includes test/test_csv.py\n",
            encoding="utf-8",
        )
        release_notes = self.worktree / "docs" / "release notes.md"
        release_notes.parent.mkdir()
        release_notes.write_text("Initial release notes.\n", encoding="utf-8")
        obsolete = self.worktree / "assets" / "obsolete.bin"
        obsolete.parent.mkdir()
        obsolete.write_bytes(b"\x00old-binary\xff\n")
        skill = self.worktree / "skills" / "csv-helper"
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: csv-helper\ndescription: Run the local CSV helper.\n---\n# CSV helper\n",
            encoding="utf-8",
        )
        (skill / "scripts" / "demo.py").write_text("print('csv helper')\n", encoding="utf-8")
        (self.worktree / "README.md").write_text(
            "# Fixture\n\n[CSV helper](skills/csv-helper/SKILL.md)\n",
            encoding="utf-8",
        )
        self.git("add", ".")
        self.git("commit", "-qm", "baseline managed contract fixture")
        self.step = {
            "id": "S1",
            "produces": ["CSV export result"],
            "contract": {"tests": [{"id": TEST_CHECK, "expected_outcome": EXPECTED_OUTCOME}]},
        }
        self.core = RealGitCore(self.step, self.env)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.worktree), *args],
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def _manifest(self, *, argv: list[str], extra_checks: list[dict] | None = None) -> dict:
        return {
            "checks": [
                {"id": TEST_CHECK, "kind": "test", "argv": argv, "acceptance": []},
                *(extra_checks or []),
            ]
        }

    def _execution_iteration(self, *, bindings: dict, extra_paths: tuple[str, ...] = ()) -> dict:
        paths = (TEST_PATH, *extra_paths)
        return {
            "test_refinement": {
                "result": refinement(),
                "bindings": bindings,
                "plan_sha256": protocol.digest(local_plan()),
                "test_files": {
                    path: hashlib.sha256((self.worktree / path).read_bytes()).hexdigest()
                    for path in paths
                },
            }
        }

    def _validate_test_execution(self, iteration: dict, manifest: dict) -> None:
        protocol.managed_validate_test_execution(
            self.core,
            self.run,
            {},
            {"worktree": str(self.worktree), "sdlc": {"test_plan": local_plan()}},
            iteration,
            {"manifest": manifest},
        )

    def _skill_validation(self) -> dict:
        return {
            "decision": "created",
            "rationale": "The repeated local CSV procedure needs a discoverable repository skill.",
            "entrypoint": "skills/csv-helper/SKILL.md",
            "index": "README.md",
            "executable_examples": [
                {
                    "path": "skills/csv-helper/scripts/demo.py",
                    "check_id": "CHECK-CSV-HELPER",
                    "purpose": "The helper example is selected by its concrete repository check.",
                }
            ],
            "failure_recovery": "Report malformed CSV input and preserve the source for correction.",
            "host_limitations": "The helper documents only local repository behavior and has no remote authority.",
        }

    def _release_core(self, receipt: dict):
        class ReleaseCore:
            @staticmethod
            def load_dag(_root: Path) -> dict:
                return {"steps": [{"id": "S1"}]}

            @staticmethod
            def load_receipt(_root: Path, step_id: str) -> dict | None:
                return deepcopy(receipt) if step_id == "S1" else None

        return ReleaseCore()

    def _release_state(self) -> dict:
        return {
            protocol.improve_bridge.MARKER: protocol.improve_bridge.VERSION,
            "repo_root": str(self.worktree),
        }

    def test_managed_test_plan_stores_frozen_outcome_and_preserves_case_matrix(self) -> None:
        receipt: dict = {"id": "S1", "worktree": str(self.worktree)}
        accepted = protocol.managed_test_plan(self.core, self.run, {}, receipt, local_plan())
        self.assertEqual(receipt["sdlc"]["test_plan"], accepted)
        self.assertEqual(accepted["cases"][0]["expected_outcome"], EXPECTED_OUTCOME)
        self.assertEqual(receipt["sdlc"]["baseline_identity"]["revision"], self.git("rev-parse", "HEAD"))

        replacement = local_plan(case_id="CASE-CSV-002")
        with self.assertRaisesRegex(sdlc.SdlcError, "missing required case IDs"):
            protocol.managed_test_plan(
                self.core,
                self.run,
                {},
                receipt,
                replacement,
                preserve_cases=True,
            )

        changed_outcome = local_plan()
        changed_outcome["cases"][0]["expected_outcome"] = "The formatter emits a single CSV field."
        with self.assertRaisesRegex(protocol.ProtocolError, "retain frozen expected outcome"):
            protocol.managed_test_plan(
                self.core,
                self.run,
                {},
                {"id": "S1", "worktree": str(self.worktree)},
                changed_outcome,
            )

        with self.assertRaisesRegex(protocol.ProtocolError, "test surface is blocked"):
            protocol.managed_test_plan(
                self.core,
                self.run,
                {},
                {"id": "S1", "worktree": str(self.worktree)},
                local_plan(blocked=True),
            )

    def test_managed_product_impact_uses_real_blob_deltas_without_narrowing_known_obligations(self) -> None:
        receipt = {
            "id": "S1",
            "worktree": str(self.worktree),
            "sdlc": {},
            "iteration": {
                "documentation": {
                    "documentation": {"paths": ["docs/release notes.md"]},
                    "reusable_skill": {"paths": ["skills/csv-helper/SKILL.md"]},
                }
            },
        }
        protocol.managed_test_plan(self.core, self.run, {}, receipt, local_plan())
        baseline = deepcopy(receipt["sdlc"]["baseline_identity"])
        notes = self.worktree / "docs" / "release notes.md"
        obsolete = self.worktree / "assets" / "obsolete.bin"
        prior_notes = notes.read_bytes()
        prior_binary = obsolete.read_bytes()
        notes.write_text("Updated release notes after the CSV correction.\n", encoding="utf-8")
        obsolete.unlink()
        self.git("add", "-A")
        self.git("commit", "-qm", "change release notes and remove obsolete binary")
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "2")

        peer_receipt = {
            "status": "complete",
            "sdlc": {"test_plan": {"cases": [{"case_id": "CASE-PEER-001"}]}},
            "iteration": {
                "documentation": {
                    "documentation": {"paths": ["docs/peer.md"]},
                    "reusable_skill": {"paths": ["skills/peer/SKILL.md"]},
                }
            },
        }
        dag = {
            "steps": [{"id": "S1"}, {"id": "S2"}],
            "system_tests": {
                "cases": [
                    {
                        "id": "SYS-PRE-001",
                        "phase": "pre_deployment",
                        "requirement": "The assembled CSV export remains readable.",
                        "expected_outcome": "The assembled product parses the exported CSV correctly.",
                        "environment": "Local assembled-product fixture.",
                        "prerequisites": [],
                        "test_step": "SYS1",
                        "test_id": "T-SYS-001",
                        "deployment_step": None,
                    }
                ]
            },
        }
        impact_core = RealGitCore(self.step, self.env, dag=dag, receipts={"S2": peer_receipt})
        impact = protocol.managed_product_impact(impact_core, self.run, {}, receipt)

        self.assertEqual(receipt["sdlc"]["baseline_identity"], baseline)
        self.assertEqual(impact["certainty"], "uncertain")
        self.assertEqual(
            impact["changes"]["artifacts"],
            [
                {
                    "path": "assets/obsolete.bin",
                    "before_sha256": hashlib.sha256(prior_binary).hexdigest(),
                    "after_sha256": None,
                },
                {
                    "path": "docs/release notes.md",
                    "before_sha256": hashlib.sha256(prior_notes).hexdigest(),
                    "after_sha256": hashlib.sha256(notes.read_bytes()).hexdigest(),
                },
            ],
        )
        self.assertEqual(impact["changes"]["contracts"], [TEST_CHECK])
        self.assertEqual(impact["changes"]["produces"], ["CSV export result"])
        self.assertEqual(
            impact["affected"],
            {
                "local_cases": ["CASE-CSV-001", "CASE-PEER-001"],
                "system_cases": ["SYS-PRE-001"],
                "documentation": ["docs/peer.md", "docs/release notes.md"],
                "skills": ["skills/csv-helper/SKILL.md", "skills/peer/SKILL.md"],
            },
        )

    def _iteration_plan_fixture(self) -> tuple[dict, dict]:
        action = "apply-001"
        result_action = "plan-result-001"
        plan_result = {"summary": "The review retained current coverage, context, and prerequisites."}
        store.write_record(self.run / "results" / f"{result_action}.md", plan_result, title="Plan result")
        candidate_path = "candidates/iteration-plan.md"
        candidate = self.run / candidate_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("SP-FINDING-001 is covered by the iteration plan.\n", encoding="utf-8")
        check_action = "plan-check-001"
        check_path = self.run / "checks" / f"{check_action}.md"
        check_path.parent.mkdir(parents=True, exist_ok=True)
        check_path.write_text("checked iteration plan\n", encoding="utf-8")
        plan_record = {
            "result_action": result_action,
            "result_sha256": protocol.digest(plan_result),
            "coverage_review": {"T-CSV-001": "The frozen outcome remains explicitly covered."},
            "context_evidence": {"history": "Current reviewed history was read before planning."},
            "prerequisites": ["The local CSV test fixture is present."],
        }
        proof = {
            "apply_action": action,
            "plan_record_sha256": protocol.digest(plan_record),
            "loop_id": "SP-LOOP-001",
            "context_sha256": "c" * 64,
            "candidate_sha256": "d" * 64,
            "check_action": check_action,
            "check_sha256": hashlib.sha256(check_path.read_bytes()).hexdigest(),
        }
        state = {
            "action": {"id": action},
            "completed_actions": {result_action: plan_record["result_sha256"]},
        }
        receipt = {
            "id": "S1",
            "worktree": str(self.worktree),
            "iteration": {
                "managed_plan": proof,
                "plan_record": plan_record,
                "previous_sha": self.git("rev-parse", "HEAD"),
            },
        }
        return state, receipt

    def _validate_iteration_plan(self, state: dict, receipt: dict) -> None:
        proof = receipt["iteration"]["managed_plan"]
        managed_receipt = {
            "route": "improve",
            "context_sha256": proof["context_sha256"],
            "candidate_sha256": proof["candidate_sha256"],
            "candidate_path": "candidates/iteration-plan.md",
        }
        with (
            patch.object(protocol, "step_plan_receipt", return_value=(proof["loop_id"], managed_receipt)),
            patch.object(protocol, "step_plan_check_record", return_value=None),
            patch.object(protocol, "step_plan_require_parent_coverage", return_value=None),
        ):
            protocol.managed_iteration_plan_proof(self.core, self.run, state, receipt)

    def test_iteration_plan_proof_rejects_mutated_plan_record_and_saved_result(self) -> None:
        state, receipt = self._iteration_plan_fixture()
        self._validate_iteration_plan(state, receipt)

        for field, changed in (
            ("coverage_review", {"T-CSV-001": "A different coverage assertion."}),
            ("context_evidence", {"history": "A different context snapshot."}),
            ("prerequisites", ["A different prerequisite."]),
        ):
            with self.subTest(field=field):
                altered = deepcopy(receipt)
                altered["iteration"]["plan_record"][field] = changed
                with self.assertRaisesRegex(protocol.ProtocolError, "coverage/context/prerequisite evidence changed"):
                    self._validate_iteration_plan(deepcopy(state), altered)

        result_action = receipt["iteration"]["plan_record"]["result_action"]
        store.write_record(
            self.run / "results" / f"{result_action}.md",
            {"summary": "The stored plan result was altered after approval."},
            title="Altered plan result",
        )
        with self.assertRaisesRegex(protocol.ProtocolError, "iteration plan result is missing or stale"):
            self._validate_iteration_plan(state, receipt)

    def test_verify_rejects_correct_test_id_rebound_to_an_unrelated_command(self) -> None:
        iteration = self._execution_iteration(bindings=direct_bindings())
        unrelated_manifest = self._manifest(
            argv=["python3", "-m", "pytest", "test/test_csv.py::test_unrelated"]
        )
        with self.assertRaisesRegex(sdlc.SdlcError, "exactly match the current manifest command"):
            self._validate_test_execution(iteration, unrelated_manifest)

    def test_verify_rejects_stale_suite_discovery_evidence(self) -> None:
        iteration = self._execution_iteration(bindings=suite_bindings(), extra_paths=("pyproject.toml",))
        (self.worktree / "pyproject.toml").write_text(
            "# Changed suite discovery still includes test/test_csv.py\n",
            encoding="utf-8",
        )
        suite_manifest = self._manifest(argv=["python3", "-m", "pytest"])
        with self.assertRaisesRegex(protocol.ProtocolError, "test files changed after authoring evidence"):
            self._validate_test_execution(iteration, suite_manifest)

    def test_verify_rejects_skill_example_check_that_omits_its_example_path(self) -> None:
        iteration = self._execution_iteration(bindings=direct_bindings())
        iteration["skill_validation"] = {"result": self._skill_validation()}
        manifest = self._manifest(
            argv=["python3", "-m", "pytest", SELECTOR],
            extra_checks=[
                {
                    "id": "CHECK-CSV-HELPER",
                    "kind": "test",
                    "argv": ["python3", "-m", "pytest", SELECTOR],
                    "acceptance": [],
                }
            ],
        )
        with self.assertRaisesRegex(protocol.ProtocolError, "skill example check must execute"):
            self._validate_test_execution(iteration, manifest)

    def test_release_evidence_rejects_missing_selected_local_test_command(self) -> None:
        receipt = {
            "status": "complete",
            "sdlc": {"test_plan": local_plan()},
            "iteration": self._execution_iteration(bindings=direct_bindings()),
        }
        missing_selected_command = {
            "checks": [
                {
                    "id": "CHECK-OTHER",
                    "kind": "test",
                    "argv": ["python3", "-m", "pytest", "test/test_other.py"],
                    "acceptance": [],
                }
            ]
        }
        with self.assertRaisesRegex(sdlc.SdlcError, "absent from the current manifest"):
            protocol.managed_release_test_evidence(
                self._release_core(receipt),
                self.run,
                self._release_state(),
                {"manifest": missing_selected_command},
            )

    def test_release_evidence_accepts_exact_local_and_skill_example_commands(self) -> None:
        iteration = self._execution_iteration(bindings=direct_bindings())
        iteration["skill_validation"] = {"result": self._skill_validation()}
        receipt = {
            "status": "complete",
            "sdlc": {"test_plan": local_plan()},
            "iteration": iteration,
        }
        manifest = self._manifest(
            argv=["python3", "-m", "pytest", SELECTOR],
            extra_checks=[
                {
                    "id": "CHECK-CSV-HELPER",
                    "kind": "test",
                    "argv": ["python3", "skills/csv-helper/scripts/demo.py"],
                    "acceptance": [],
                }
            ],
        )
        protocol.managed_release_test_evidence(
            self._release_core(receipt),
            self.run,
            self._release_state(),
            {"manifest": manifest},
        )

    def test_release_retains_skill_examples_after_later_iterations(self) -> None:
        selected = self._skill_validation()
        receipt = {
            "status": "complete",
            "sdlc": {"test_plan": local_plan()},
            "improve_cycles": [
                {"skill_validation": {"result": selected}},
                {"skill_validation": {"result": deepcopy(selected)}},
                {},
            ],
            "iteration": self._execution_iteration(bindings=direct_bindings()),
        }
        core = self._release_core(receipt)
        state = self._release_state()
        manifest = self._manifest(argv=["python3", "-m", "pytest", SELECTOR])
        with self.assertRaisesRegex(sdlc.SdlcError, "check"):
            protocol.managed_release_test_evidence(core, self.run, state, {"manifest": manifest})
        manifest["checks"].append({
            "id": "CHECK-CSV-HELPER", "kind": "test",
            "argv": ["python3", "skills/csv-helper/scripts/demo.py"], "acceptance": [],
        })
        protocol.managed_release_test_evidence(core, self.run, state, {"manifest": manifest})
        context = protocol.managed_release_context(core, self.run, state)
        self.assertEqual(context[0]["retained_skill_validations"], [selected])

    def test_commit_transports_present_independent_review_evidence(self) -> None:
        action = "commit-001"
        review_ref = "reviews/independent.md"
        review_path = self.run / review_ref
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text("Independent reviewer approved the local contract evidence.\n", encoding="utf-8")
        store.write_record(
            self.run / "steps" / "S1.md",
            {"improve_cycles": [{"check_action": "verify-001"}]},
            title="Managed receipt",
        )
        store.write_record(
            self.run / "results" / f"{action}.md",
            {"independent_review": {"status": "performed", "evidence_ref": review_ref}},
            title="Commit result",
        )
        captured: list[dict] = []

        class CommitCore:
            @staticmethod
            def improve_until_passes(_receipt: dict) -> list[dict]:
                return [
                    {
                        "id": "I-001",
                        "outcome": "trivial",
                        "verified": True,
                        "commit": "a" * 40,
                        "evidence_ref": "steps/S1.md",
                    }
                ]

        state = {"active_step": "S1"}
        with (
            patch.object(protocol.improve_bridge, "packet_metadata", return_value={"binding_sha256": "b" * 64}),
            patch.object(protocol.improve_bridge, "set_evidence", side_effect=lambda _state, event: captured.append(event)),
        ):
            protocol.managed_completion_evidence(CommitCore(), self.run, state, "commit", action, {})

        self.assertEqual(len(captured), 1)
        event = captured[0]
        self.assertEqual(event["completed_pass"]["independent_review"], {"status": "performed", "evidence_ref": review_ref})
        self.assertIn(review_ref, event["evidence_refs"])


if __name__ == "__main__":
    unittest.main()
