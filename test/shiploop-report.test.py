#!/usr/bin/env python3
"""Focused, offline acceptance tests for the derived ShipLoop achievement report."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_store as store  # noqa: E402
from shiploop_report import render_report  # noqa: E402


class ShipLoopReportTests(unittest.TestCase):
    """The report must remain a safe, deterministic derived view of Markdown."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-report-")
        self.run_dir = Path(self.temp.name) / ".shiploop"
        self.run_dir.mkdir()
        self.write_complete_run()

    def tearDown(self):
        self.temp.cleanup()

    def record(self, relative, value, title="Fixture record"):
        path = self.run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        store.write_record(path, value, title=title)
        return path

    def read(self, relative):
        return store.read_record(self.run_dir / relative)

    @staticmethod
    def result_digest(value):
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def write_complete_run(self):
        """Minimal terminal shape the protocol integration must make available."""
        quality_action = "report-fixture-quality-check"
        quality_result = {
            "summary": "Quality check result is host-reported; compact checks are separate evidence.",
            "test_review": "Both declared cases are covered.",
        }
        state = {
            "version": 3,
            "run_id": "report-fixture",
            "revision": 12,
            "phase": "done",
            "stage": "done",
            "action": {"id": "report-fixture-terminal", "stage": "done"},
            "outer_check_action": quality_action,
            "completed_actions": {quality_action: self.result_digest(quality_result)},
            # The renderer must never echo host-local artifact paths.
            "artifacts": {"handoff_md": "/private/tmp/report-fixture/handoff.md"},
        }
        history = [
            {
                "event": "complete:quality",
                "action": {"id": "report-fixture-quality-check", "stage": "quality"},
                "revision": 10,
            },
            {
                "event": "complete:handoff",
                "action": {"id": "report-fixture-terminal", "stage": "done"},
                "revision": 12,
            },
        ]
        lifecycle = {
            "acceptance": [
                "The report fixture exposes its expected outcome.",
                "The report fixture shows machine verification.",
            ],
            "quality": True,
        }
        dag = {
            "goal": "The report fixture completes safely.",
            "initial_state": ["fixture ready"],
            "unresolved": [],
            "steps": [
                {
                    "id": "S1",
                    "statement": "Create the fixture output.",
                    "produces": ["fixture output"],
                    "contract": {
                        "objective": "Create the fixture output.",
                        "ready": [],
                        "done": [
                            {
                                "id": "D-FIXTURE-001",
                                "condition": "The fixture output is present.",
                                "produces": ["fixture output"],
                                "evidence_method": "Review the fixture check record.",
                                "completion": "integrated",
                            }
                        ],
                        "tests": [
                            {
                                "id": "T-FIXTURE-001",
                                "produces": ["fixture output"],
                                "expected_outcome": "The fixture output is exactly present.",
                                "surface": "integration",
                                "evidence_method": "Run the fixture check.",
                            }
                        ],
                        "documentation": [],
                    },
                }
            ],
        }
        receipt = {
            "id": "S1",
            "status": "complete",
            "produces": ["fixture output"],
            "improve_cycles": [
                {
                    "outcome": "material",
                    "primary_commit": "b" * 40,
                    "review": {"learnings": "First review found a real gap."},
                    "applied": {"learnings": "The gap received a checked fix."},
                },
                {
                    "outcome": "trivial",
                    "primary_commit": "c" * 40,
                    "review": {"learnings": "Second review was narrowly clean."},
                },
            ],
            "plan_review": {
                "plan_decision": "revise",
                "plan_reason": "A later step needs a clearer dependency.",
            },
            "done_evidence": {
                "done": [
                    {
                        "id": "D-FIXTURE-001",
                        "observed": "Fixture output is present after the checked merge.",
                    }
                ],
                "tests": [
                    {
                        "id": "T-FIXTURE-001",
                        "observed_outcome": "Fixture check observed the exact expected output.",
                    }
                ],
            },
        }
        manifest = {
            "checks": [
                {
                    "id": "lint",
                    "kind": "lint",
                    "argv": ["python", "-B", "lint_fixture.py"],
                    "acceptance": [],
                },
                {
                    "id": "acceptance",
                    "kind": "test",
                    "argv": ["python", "-B", "test_fixture.py"],
                    "acceptance": list(lifecycle["acceptance"]),
                },
            ]
        }
        passed_rows = [
            {
                "id": "lint",
                "kind": "lint",
                "argv": ["python", "-B", "lint_fixture.py"],
                "acceptance": [],
                "status": "passed",
                "exit": 0,
                "duration_ms": 7,
                "log_path": "/private/tmp/report-fixture/logs/lint.log",
                "stdout_log": "/private/tmp/report-fixture/logs/lint.stdout.log",
                "stderr_log": "/private/tmp/report-fixture/logs/lint.stderr.log",
                "log_paths": {
                    "stdout": "/private/tmp/report-fixture/logs/lint.stdout.log",
                    "stderr": "/private/tmp/report-fixture/logs/lint.stderr.log",
                },
            },
            {
                "id": "acceptance",
                "kind": "test",
                "argv": ["python", "-B", "test_fixture.py"],
                "acceptance": list(lifecycle["acceptance"]),
                "status": "passed",
                "exit": 0,
                "duration_ms": 12,
                "log_path": "/private/tmp/report-fixture/logs/acceptance.log",
                "stdout_log": "/private/tmp/report-fixture/logs/acceptance.stdout.log",
                "stderr_log": "/private/tmp/report-fixture/logs/acceptance.stderr.log",
                "log_paths": {
                    "stdout": "/private/tmp/report-fixture/logs/acceptance.stdout.log",
                    "stderr": "/private/tmp/report-fixture/logs/acceptance.stderr.log",
                },
            },
        ]
        final_check = {
            "manifest": manifest,
            "results": {
                "action": quality_action,
                "action_id": quality_action,
                "all_passed": True,
                "content_changed": False,
                "before_fingerprint": "e" * 64,
                "after_fingerprint": "e" * 64,
                "before": "e" * 64,
                "after": "e" * 64,
                "manifest_digest": "f" * 64,
                "checks": passed_rows,
            },
            "reason": "Final quality verification.",
        }
        failed_attempt = copy.deepcopy(final_check)
        failed_attempt["results"]["all_passed"] = False
        failed_attempt["results"]["checks"][1]["status"] = "failed"
        failed_attempt["results"]["checks"][1]["exit"] = 1
        self.record("state.md", state, "ShipLoop state")
        self.record("history.md", history, "ShipLoop history")
        self.record("lifecycle.md", lifecycle, "ShipLoop lifecycle")
        self.record("backchain/plan.md", dag, "ShipLoop dependency sequence")
        self.record("steps/S1.md", receipt, "ShipLoop step receipt")
        self.record(
            "quality.md",
            {
                "summary": "Quality evidence covers both declared fixture outcomes.",
                "test_review": "The final evidence records expected and observed results.",
                "quality_review": "The fixture only claims its declared local surface.",
            },
            "Outer acceptance and integration checks",
        )
        self.record(
            f"results/{quality_action}.md",
            quality_result,
            "ShipLoop result quality",
        )
        self.record(
            "handoff.md",
            {
                "summary": "Fixture delivery is ready for human handoff review.",
                "journal": [],
            },
            "ShipLoop final handoff",
        )
        self.record(
            "shiploop-improvements.md",
            [
                {
                    "title": "Keep compact verification evidence",
                    "impact": "A cold reader can see what ran without importing logs.",
                    "proposal": "Keep checks structured and report logs only by existence.",
                    "test_idea": "Render a safe report from a completed fixture.",
                    "status": "proposed",
                }
            ],
            "ShipLoop improvement proposals",
        )
        self.record(
            "checks/report-fixture-quality-check.md",
            final_check,
            "ShipLoop checks",
        )
        self.record(
            "check-attempts/report-fixture-quality-check-first.md",
            failed_attempt,
            "ShipLoop checks attempt",
        )

    def test_stable_completed_report_covers_authoritative_evidence(self):
        first_html, first_meta = render_report(self.run_dir)
        second_html, second_meta = render_report(self.run_dir)

        self.assertEqual(first_html, second_html)
        self.assertEqual(first_meta, second_meta)
        self.assertEqual(first_meta["outcome"], "complete")
        self.assertTrue(first_meta["evidence_complete"])
        self.assertRegex(first_meta["source_digest"], r"^[0-9a-f]{64}$")
        self.assertIn('data-outcome="complete"', first_html)
        self.assertIn('data-source-digest="' + first_meta["source_digest"], first_html)
        for heading in (
            "Actual sequence",
            "Required and achieved outputs",
            "Test evidence",
            "Learning commits",
            "Broader-plan changes",
            "ShipLoop improvement proposals",
            "Derived report — not authoritative state",
        ):
            self.assertIn(heading, first_html)
        self.assertIn("Machine-verified", first_html)
        self.assertIn("Host-reported", first_html)
        self.assertIn("Expected", first_html)
        self.assertIn("Observed", first_html)
        self.assertIn("Retry", first_html)
        self.assertIn("D-FIXTURE-001", first_html)
        self.assertIn("T-FIXTURE-001", first_html)
        self.assertNotIn("/private/tmp/report-fixture", first_html)
        self.assertNotIn("lint_fixture.py", first_html)

        # Root stores report binding metadata in state.md after rendering.  It
        # must not change a subsequent report or recursively alter its digest.
        state = self.read("state.md")
        state["report"] = {
            "path": "report.html",
            "sha256": "d" * 64,
            "source_digest": first_meta["source_digest"],
            "outcome": "complete",
            "evidence_complete": True,
        }
        self.record("state.md", state, "ShipLoop state")
        bound_html, bound_meta = render_report(self.run_dir)
        self.assertEqual(bound_html, first_html)
        self.assertEqual(bound_meta, first_meta)

    def test_specialized_pass_receipts_add_learning_commits_without_candidates(self):
        """New convergence loops expose bounded learnings, not their draft bodies."""
        planning_archive = "planning/research-iterations/fixture-research-E1-I1.md"
        self.record(
            "objectives/fixture-objective.md",
            {
                "loop_id": "fixture-objective",
                "kind": "planning",
                "completed_passes": [
                    {
                        "id": "fixture-objective-E1-P1",
                        "outcome": "material",
                        "commit": "d" * 40,
                        "review": {"learnings": "Objective review learning."},
                        "plan": {"learnings": "Objective plan learning."},
                        "apply": {
                            "learnings": "Objective apply learning.",
                            "candidate": "PRIVATE-OBJECTIVE-CANDIDATE",
                        },
                    }
                ],
            },
            "ShipLoop objective receipt",
        )
        self.record(
            "step-planning/fixture-step-plan.md",
            {
                "loop_id": "fixture-step-plan",
                "step_id": "S1",
                "completed_passes": [
                    {
                        "id": "fixture-step-plan-E1-P1",
                        "outcome": "trivial",
                        "commit": "e" * 40,
                        "review": {"learnings": "Step-plan review learning."},
                        "revise": {"learnings": "Step-plan revise learning."},
                        "body": "PRIVATE-STEP-PLAN-BODY",
                    }
                ],
            },
            "ShipLoop step-plan receipt",
        )
        self.record(
            "planning/research.md",
            {
                "kind": "research",
                "completed_iterations": [
                    {
                        "id": "fixture-research-E1-I1",
                        "path": planning_archive,
                        "outcome": "trivial",
                        "verified": True,
                        "commit": "f" * 40,
                    }
                ],
            },
            "ShipLoop research planning receipt",
        )
        self.record(
            planning_archive,
            {
                "id": "fixture-research-E1-I1",
                "outcome": "trivial",
                "primary_commit": "f" * 40,
                "review": {"learnings": "Research review learning."},
                "applied": {"learnings": "Research apply learning."},
                "body": "PRIVATE-PLANNING-BODY",
            },
            "ShipLoop completed planning iteration",
        )
        candidate = self.run_dir / "objectives" / "fixture-objective" / "candidate.md"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("PRIVATE-OBJECTIVE-CANDIDATE", encoding="utf-8")

        rendered, metadata = render_report(self.run_dir)

        self.assertEqual(metadata["outcome"], "complete")
        self.assertTrue(metadata["evidence_complete"])
        for learning in (
            "Objective review learning.",
            "Objective plan learning.",
            "Objective apply learning.",
            "Step-plan review learning.",
            "Step-plan revise learning.",
            "Research review learning.",
            "Research apply learning.",
        ):
            self.assertIn(learning, rendered)
        self.assertIn("Objective planning (fixture-objective)", rendered)
        self.assertIn("Step plan S1 (fixture-step-plan)", rendered)
        self.assertIn("Planning research / fixture-research-E1-I1", rendered)
        self.assertIn("Wide table — scroll horizontally to view all columns.", rendered)
        self.assertIn("objectives/fixture-objective.md", metadata["sources"])
        self.assertIn("step-planning/fixture-step-plan.md", metadata["sources"])
        self.assertIn(planning_archive, metadata["sources"])
        self.assertNotIn("PRIVATE-OBJECTIVE-CANDIDATE", rendered)
        self.assertNotIn("PRIVATE-STEP-PLAN-BODY", rendered)
        self.assertNotIn("PRIVATE-PLANNING-BODY", rendered)
        self.assertNotIn(
            "objectives/fixture-objective/candidate.md", metadata["sources"]
        )

        (self.run_dir / planning_archive).unlink()
        _, missing_metadata = render_report(self.run_dir)
        self.assertEqual(missing_metadata["outcome"], "unfinished")
        self.assertIn(planning_archive, "\n".join(missing_metadata["evidence_errors"]))

    def test_referenced_planning_archive_does_not_follow_symlinked_parent(self):
        archive = "planning/research-iterations/fixture-research-E1-I1.md"
        self.record(
            "planning/research.md",
            {
                "kind": "research",
                "completed_iterations": [
                    {
                        "id": "fixture-research-E1-I1",
                        "path": archive,
                        "outcome": "trivial",
                        "verified": True,
                        "commit": "f" * 40,
                    }
                ],
            },
            "ShipLoop research planning receipt",
        )
        outside = Path(self.temp.name) / "outside-planning-archive"
        outside.mkdir()
        store.write_record(
            outside / "fixture-research-E1-I1.md",
            {
                "id": "fixture-research-E1-I1",
                "primary_commit": "f" * 40,
                "outcome": "trivial",
                "review": {"learnings": "OUTSIDE-ARCHIVE-SECRET"},
            },
            title="Outside archive",
        )
        (self.run_dir / "planning" / "research-iterations").symlink_to(
            outside, target_is_directory=True
        )

        rendered, metadata = render_report(self.run_dir)

        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertIn("unsafe symlinked path", "\n".join(metadata["evidence_errors"]))
        self.assertNotIn("OUTSIDE-ARCHIVE-SECRET", rendered)

    def test_escapes_untrusted_text_and_only_emits_safe_internal_hrefs(self):
        handoff = self.read("handoff.md")
        handoff["summary"] = (
            '<script>alert("x")</script> [attack](javascript:alert(1)) '
            "[path](/private/tmp/secret) token=secret-value"
        )
        self.record("handoff.md", handoff, "ShipLoop final handoff")

        rendered, metadata = render_report(self.run_dir)

        self.assertEqual(metadata["outcome"], "complete")
        lowered = rendered.lower()
        self.assertNotIn("<script", lowered)
        self.assertIn("&lt;script&gt;", lowered)
        self.assertNotIn("javascript:", lowered)
        self.assertNotIn("/private/tmp/secret", rendered)
        self.assertNotIn("secret-value", rendered)
        for href in re.findall(r'href="([^"]*)"', rendered):
            self.assertTrue(href.startswith("#"), href)

    def test_missing_or_corrupt_evidence_never_reports_green(self):
        (self.run_dir / "checks/report-fixture-quality-check.md").unlink()
        rendered, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertFalse(metadata["evidence_complete"])
        self.assertTrue(metadata["evidence_errors"])
        self.assertIn('data-outcome="unfinished"', rendered)
        self.assertIn("Evidence incomplete", rendered)

        self.write_complete_run()
        (self.run_dir / "history.md").write_text(
            "# corrupt\n\nnot a record\n", encoding="utf-8"
        )
        rendered, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertFalse(metadata["evidence_complete"])
        self.assertIn("history.md", "\n".join(metadata["evidence_errors"]))
        self.assertIn("Evidence incomplete", rendered)

    def test_halted_or_failed_terminal_data_is_not_success(self):
        halted = self.read("state.md")
        halted.update(
            phase="implement",
            stage="halted",
            action={"id": "report-fixture-halt", "stage": "halted"},
        )
        self.record("state.md", halted, "ShipLoop state")
        rendered, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertFalse(metadata["evidence_complete"])
        self.assertIn("Unfinished", rendered)

        self.write_complete_run()
        check = self.read("checks/report-fixture-quality-check.md")
        check["results"]["all_passed"] = False
        check["results"]["checks"][1]["status"] = "failed"
        check["results"]["checks"][1]["exit"] = 1
        self.record("checks/report-fixture-quality-check.md", check, "ShipLoop checks")
        rendered, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertFalse(metadata["evidence_complete"])
        self.assertIn("Unfinished", rendered)

    def test_final_check_binding_and_log_metadata_must_be_complete(self):
        check = self.read("checks/report-fixture-quality-check.md")
        check["results"]["action_id"] = "other-action"
        self.record("checks/report-fixture-quality-check.md", check, "ShipLoop checks")
        rendered, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertFalse(metadata["evidence_complete"])
        self.assertIn(
            "result action does not match final action",
            "\n".join(metadata["evidence_errors"]),
        )
        self.assertIn("Verification unavailable", rendered)
        self.assertNotIn("Machine-verified", rendered)

        self.write_complete_run()
        check = self.read("checks/report-fixture-quality-check.md")
        check["results"]["checks"][0].pop("stdout_log")
        self.record("checks/report-fixture-quality-check.md", check, "ShipLoop checks")
        rendered, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertFalse(metadata["evidence_complete"])
        self.assertIn(
            "log metadata is unavailable", "\n".join(metadata["evidence_errors"])
        )
        self.assertIn("Unavailable; raw logs were not read or exported", rendered)

        self.write_complete_run()
        result = self.read("results/report-fixture-quality-check.md")
        result["summary"] = "Tampered result text."
        self.record(
            "results/report-fixture-quality-check.md",
            result,
            "ShipLoop result quality",
        )
        _, metadata = render_report(self.run_dir)
        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertIn(
            "completed-action fingerprint", "\n".join(metadata["evidence_errors"])
        )

    def test_effective_overrides_bind_terminal_render_without_disk_mutation(self):
        pending = self.read("state.md")
        pending.update(
            phase="residual",
            stage="handoff",
            action={"id": "report-fixture-handoff", "stage": "handoff"},
        )
        self.record("state.md", pending, "ShipLoop state")
        pending_html, pending_meta = render_report(self.run_dir)
        self.assertEqual(pending_meta["outcome"], "unfinished")

        final_state = dict(pending)
        final_result = {"summary": "Prospective final result."}
        completed_actions = dict(pending["completed_actions"])
        completed_actions["report-fixture-handoff"] = self.result_digest(final_result)
        final_state.update(
            phase="done",
            stage="done",
            action={"id": "report-fixture-terminal", "stage": "done"},
            completed_actions=completed_actions,
            last_completion={
                "action": "report-fixture-handoff",
                "stage": "handoff",
                "result_digest": self.result_digest(final_result),
            },
        )
        final_history = self.read("history.md") + [
            {
                "event": "complete:handoff",
                "action": {"id": "report-fixture-terminal", "stage": "done"},
                "revision": 12,
            }
        ]
        overrides = {
            "state.md": store.dumps(final_state, "ShipLoop state"),
            "history.md": store.dumps(final_history, "ShipLoop history"),
            "handoff.md": store.dumps(
                {"summary": "Prospective terminal handoff.", "journal": []},
                "ShipLoop final handoff",
            ),
            "results/report-fixture-handoff.md": store.dumps(
                final_result, "ShipLoop result handoff"
            ),
            "shiploop-improvements.md": store.dumps(
                self.read("shiploop-improvements.md"), "ShipLoop improvement proposals"
            ),
        }
        final_html, final_meta = render_report(self.run_dir, overrides=overrides)
        self.assertEqual(final_meta["outcome"], "complete")
        self.assertTrue(final_meta["evidence_complete"])
        self.assertNotEqual(pending_html, final_html)
        self.assertEqual(self.read("state.md")["stage"], "handoff")
        self.assertIn("results/report-fixture-handoff.md", final_meta["sources"])


if __name__ == "__main__":
    unittest.main()
