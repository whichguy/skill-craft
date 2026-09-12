#!/usr/bin/env python3
"""Acceptance and record tests for ShipLoop's per-step planning loops.

The loop has deliberately separate Markdown receipts from the product step
receipt.  Tests here first lock the durable record contract; public-CLI walks
below exercise the same records across fresh subprocesses.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_step_planning as step_planning  # noqa: E402
import shiploop_store as store  # noqa: E402


def load_action_walk_fixture():
    """Reuse the real-CLI fixture without making the test directory a package."""
    path = ROOT / "test" / "shiploop-action-walk.test.py"
    loader = importlib.machinery.SourceFileLoader("shiploop_step_plan_walk", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module.ShipLoopActionWalkFixture


ActionWalkFixture = load_action_walk_fixture()


class StepPlanningRecordTests(unittest.TestCase):
    """Small pure-record checks for the Markdown-authoritative loop contract."""

    PLAN_BODY = (
        "# Step plan\n\n"
        "Use the inspected exact-output fixture and its current dependency.\n"
    )

    @staticmethod
    def context(*, suffix: str = "a") -> dict[str, str]:
        digest = suffix * 64
        return {
            "step_sha256": digest,
            "dependency_sha256": digest,
            "enclosing_review_sha256": digest,
            "worktree": "/tmp/shiploop-step-plan-worktree",
            "git_baseline": "b" * 40,
            "committed_tree_sha256": digest,
            "worktree_fingerprint": digest,
            "status_sha256": digest,
            "spec_sha256": digest,
            "environment_sha256": digest,
            "behavior_sha256": digest,
            "plan_sha256": digest,
            "knowledge_sha256": digest,
        }

    def new_receipt(self, *, route: str = "initial") -> dict:
        loop = step_planning.loop_id(
            "run_01", "S1", route, "run_01-S1-I1" if route == "improve" else None
        )
        return step_planning.new_receipt(
            loop=loop,
            step_id="S1",
            route=route,
            return_stage="improve-apply" if route == "improve" else "implement",
            body=self.PLAN_BODY,
            context=self.context(),
        )

    @staticmethod
    def finding(
        finding_id: str = "F-001", *, severity: str = "material", category: str = "edge-condition"
    ) -> dict[str, str]:
        return {
            "id": finding_id,
            "severity": severity,
            "category": category,
            "summary": "The exact-output boundary requires an explicit empty-input case.",
        }

    def test_initial_and_improve_routes_have_distinct_bound_receipts(self) -> None:
        initial = self.new_receipt()
        improve = self.new_receipt(route="improve")

        self.assertEqual(initial["route"], "initial")
        self.assertEqual(initial["return_stage"], "implement")
        self.assertEqual(improve["route"], "improve")
        self.assertEqual(improve["return_stage"], "improve-apply")
        self.assertNotEqual(initial["loop_id"], improve["loop_id"])
        self.assertEqual(initial["completed_passes"], [])
        self.assertEqual(initial["current_pass"]["number"], 1)

    def test_real_timestamp_run_id_and_exact_pass_cursor_are_accepted(self) -> None:
        run_id = "20260912T012900Z-192c6d00"
        loop = step_planning.loop_id(run_id, "S1", "initial")
        receipt = step_planning.new_receipt(
            loop=loop,
            step_id="S1",
            route="initial",
            return_stage="implement",
            body="# Step plan\n\nInspect the real fixture before implementation.",
            context=self.context(),
        )
        self.assertEqual(loop, f"{run_id}-S1-initial")
        self.assertEqual(receipt["current_pass"]["id"], f"{loop}-E1-P1")

        with tempfile.TemporaryDirectory(prefix="shiploop-step-plan-cursor-") as raw:
            root = Path(raw)
            candidate = root / receipt["candidate_path"]
            candidate.parent.mkdir(parents=True)
            candidate.write_text(
                "# Step plan\n\nInspect the real fixture before implementation.\n",
                encoding="utf-8",
            )
            receipt["current_pass"]["id"] = f"{loop}-E99-P99"
            with self.assertRaises(step_planning.StepPlanningError):
                step_planning.assert_receipt(root, receipt)

    def test_review_keeps_old_open_findings_and_rejects_severity_downgrade(self) -> None:
        receipt = self.new_receipt()
        step_planning.apply_review(receipt, [self.finding()])
        old_ledger = receipt["ledger_sha256"]

        # A later review cannot make an old risk disappear merely by omitting it.
        step_planning.apply_review(receipt, [])
        self.assertEqual(step_planning.open_ids(receipt), {"F-001"})
        self.assertEqual(receipt["ledger_sha256"], old_ledger)

        with self.assertRaises(step_planning.StepPlanningError):
            step_planning.apply_review(
                receipt, [self.finding("F-001", severity="trivial")]
            )

    def test_revise_requires_every_open_finding_and_records_concrete_resolution(self) -> None:
        receipt = self.new_receipt()
        step_planning.apply_review(
            receipt, [self.finding("F-001"), self.finding("F-002", severity="trivial")]
        )

        with self.assertRaises(step_planning.StepPlanningError):
            step_planning.check_addresses(receipt, ["F-001"])
        addresses = step_planning.check_addresses(receipt, ["F-001", "F-002"])
        resolved = step_planning.resolve_findings(
            receipt,
            [
                {
                    "id": "F-001",
                    "evidence": "Candidate adds the empty-input expected-outcome case.",
                },
                {
                    "id": "F-002",
                    "evidence": "Candidate names the README example update decision.",
                },
            ],
            addresses,
        )
        self.assertEqual(resolved, ["F-001", "F-002"])
        self.assertTrue(step_planning.all_clear(receipt))
        self.assertEqual(
            receipt["findings"][0]["resolved_pass"], receipt["current_pass"]["id"]
        )

    def test_material_scope_or_behavior_findings_cannot_be_closed_by_a_step_plan_revise(self) -> None:
        receipt = self.new_receipt()
        step_planning.apply_review(
            receipt, [self.finding("F-SCOPE", category="scope")]
        )
        addresses = step_planning.check_addresses(receipt, ["F-SCOPE"])

        with self.assertRaisesRegex(
            step_planning.StepPlanningError, "broader-plan decision"
        ):
            step_planning.resolve_findings(
                receipt,
                [
                    {
                        "id": "F-SCOPE",
                        "evidence": "This candidate cannot authorize broader scope.",
                    }
                ],
                addresses,
            )
        self.assertEqual(step_planning.open_ids(receipt), {"F-SCOPE"})

    def test_material_scope_or_behavior_finding_cannot_be_reclassified_in_a_later_review(self) -> None:
        receipt = self.new_receipt()
        step_planning.apply_review(
            receipt, [self.finding("F-SCOPE", category="scope")]
        )

        with self.assertRaisesRegex(
            step_planning.StepPlanningError, "cannot recategorize"
        ):
            step_planning.apply_review(
                receipt,
                [self.finding("F-SCOPE", category="implementation")],
            )
        self.assertEqual(receipt["findings"][0]["category"], "scope")
        self.assertEqual(receipt["findings"][0]["status"], "open")

    def test_context_and_coverage_require_the_full_bounded_rubric(self) -> None:
        coverage = {
            key: f"Reviewed {key} against the durable step and current worktree."
            for key in step_planning.RUBRIC
        }
        context_evidence = {
            key: f"Durable {key} evidence was inspected from the bounded context."
            for key in step_planning.CONTEXT_EVIDENCE
        }
        self.assertEqual(step_planning.check_coverage_review(coverage), coverage)
        normalized = step_planning.check_context_evidence(context_evidence)
        self.assertEqual(set(normalized), set(step_planning.CONTEXT_EVIDENCE))

        coverage.pop("documentation")
        with self.assertRaises(step_planning.StepPlanningError):
            step_planning.check_coverage_review(coverage)
        context_evidence.pop("dependencies")
        with self.assertRaises(step_planning.StepPlanningError):
            step_planning.check_context_evidence(context_evidence)

    def test_receipt_binds_candidate_context_and_current_pass_to_markdown_bytes(self) -> None:
        receipt = self.new_receipt()
        with tempfile.TemporaryDirectory(prefix="shiploop-step-plan-record-") as raw:
            root = Path(raw)
            candidate = root / receipt["candidate_path"]
            candidate.parent.mkdir(parents=True)
            candidate.write_text(self.PLAN_BODY, encoding="utf-8")
            self.assertEqual(step_planning.assert_receipt(root, receipt), receipt)

            candidate.write_text("# Drift\n\nThis was not written by revise.\n", encoding="utf-8")
            with self.assertRaises(step_planning.StepPlanningError):
                step_planning.assert_receipt(root, receipt)

    def test_repair_epoch_rebinds_context_without_erasing_completed_passes(self) -> None:
        receipt = self.new_receipt()
        completed = dict(receipt["current_pass"])
        completed.update(
            verified=True,
            outcome="trivial",
            commit="c" * 40,
        )
        receipt["completed_passes"].append(completed)
        step_planning.rebind_after_repair(receipt, self.context(suffix="d"))

        self.assertEqual(receipt["epoch"], 2)
        self.assertEqual(receipt["pass"], 1)
        self.assertEqual(len(receipt["completed_passes"]), 1)
        self.assertEqual(receipt["current_pass"]["epoch"], 2)
        self.assertNotEqual(
            receipt["current_pass"]["context_sha256"], completed["context_sha256"]
        )

    def test_certificate_requires_two_verified_trivial_passes_before_any_handoff(self) -> None:
        receipt = self.new_receipt()
        with self.assertRaises(step_planning.StepPlanningError):
            step_planning.certificate(
                receipt,
                final_check_action="A1",
                final_check_sha256="f" * 64,
                audit_head="b" * 40,
            )

        first = dict(receipt["current_pass"])
        first.update(verified=True, outcome="trivial", commit="a" * 40)
        receipt["completed_passes"].append(first)
        step_planning.start_next_pass(receipt, self.context(suffix="b"))
        second = dict(receipt["current_pass"])
        second.update(verified=True, outcome="trivial", commit="c" * 40)
        receipt["completed_passes"].append(second)
        certificate = step_planning.certificate(
            receipt,
            final_check_action="A1",
            final_check_sha256="f" * 64,
            audit_head="b" * 40,
        )
        self.assertEqual(certificate["final_pass_id"], second["id"])
        self.assertEqual(certificate["final_check_action"], "A1")

    def test_completed_passes_are_exactly_ordered_before_the_current_cursor(self) -> None:
        receipt = self.new_receipt()
        first = dict(receipt["current_pass"])
        first.update(verified=True, outcome="trivial", commit="a" * 40)
        receipt["completed_passes"].append(first)
        step_planning.start_next_pass(receipt, self.context(suffix="b"))
        second = dict(receipt["current_pass"])
        second.update(verified=True, outcome="trivial", commit="b" * 40)
        receipt["completed_passes"].append(second)
        step_planning.start_next_pass(receipt, self.context(suffix="c"))

        with tempfile.TemporaryDirectory(prefix="shiploop-step-plan-order-") as raw:
            root = Path(raw)
            candidate = root / receipt["candidate_path"]
            candidate.parent.mkdir(parents=True)
            candidate.write_text(self.PLAN_BODY, encoding="utf-8")
            for completed in receipt["completed_passes"]:
                archive = root / step_planning.pass_name(
                    receipt["loop_id"], completed["id"]
                )
                archive.parent.mkdir(parents=True, exist_ok=True)
                archive.write_text(
                    store.dumps(completed, "ShipLoop completed step-plan pass"),
                    encoding="utf-8",
                )
            self.assertEqual(step_planning.assert_receipt(root, receipt), receipt)
            receipt["completed_passes"].reverse()
            with self.assertRaises(step_planning.StepPlanningError):
                step_planning.assert_receipt(root, receipt)

    def test_completed_and_abandoned_archives_are_exact_byte_bound_evidence(self) -> None:
        """A receipt cannot be replayed against altered pass archive Markdown."""
        receipt = self.new_receipt()
        completed = dict(receipt["current_pass"])
        completed.update(verified=True, outcome="trivial", commit="a" * 40)
        receipt["completed_passes"].append(completed)
        step_planning.start_next_pass(receipt, self.context(suffix="b"))

        with tempfile.TemporaryDirectory(prefix="shiploop-step-plan-archive-") as raw:
            root = Path(raw)
            candidate = root / receipt["candidate_path"]
            candidate.parent.mkdir(parents=True)
            candidate.write_text(self.PLAN_BODY, encoding="utf-8")
            completed_path = root / step_planning.pass_name(
                receipt["loop_id"], completed["id"]
            )
            completed_path.parent.mkdir(parents=True)
            completed_path.write_text(
                store.dumps(completed, "ShipLoop completed step-plan pass"),
                encoding="utf-8",
            )
            self.assertEqual(step_planning.assert_receipt(root, receipt), receipt)

            # Same semantic payload under a different Markdown rendering is
            # still tampering: exact archive bytes are part of the receipt.
            completed_path.write_text(
                store.dumps(completed, "A misleading archive heading"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                step_planning.StepPlanningError, "archive does not match"
            ):
                step_planning.assert_receipt(root, receipt)

            completed_path.write_text(
                store.dumps(completed, "ShipLoop completed step-plan pass"),
                encoding="utf-8",
            )
            abandoned = dict(receipt["current_pass"])
            abandoned.update(
                status="abandoned",
                reason="The durable fixture intentionally interrupted this pass.",
            )
            receipt["abandoned_passes"].append(abandoned)
            step_planning.rebind_after_repair(receipt, self.context(suffix="c"))
            abandoned_path = root / step_planning.abandoned_name(
                receipt["loop_id"], abandoned["id"]
            )
            abandoned_path.parent.mkdir(parents=True)
            abandoned_path.write_text(
                store.dumps(abandoned, "ShipLoop abandoned step-plan pass"),
                encoding="utf-8",
            )
            self.assertEqual(step_planning.assert_receipt(root, receipt), receipt)

            abandoned_path.write_text("# Tampered abandoned archive\n", encoding="utf-8")
            with self.assertRaisesRegex(
                step_planning.StepPlanningError, "archive does not match|archive is missing"
            ):
                step_planning.assert_receipt(root, receipt)


class StepPlanningCliTests(ActionWalkFixture):
    """Fresh-process checks for allocation and nested Improve routing."""

    def test_initial_step_plan_is_repeatable_cold_and_gates_implementation(self):
        self.bootstrap_to_first_step_plan()
        initial_action = self.action_id()
        first_packet = self.cli("next").stdout
        second_packet = self.cli("next").stdout
        self.assertEqual(self.action_id(), initial_action)
        self.assertIn("step-plan", first_packet)
        self.assertIn("--section step-context", first_packet)
        self.assertIn("--section step-context", second_packet)
        self.assertIn("unit", first_packet)
        self.assertIn("mock/fake", first_packet)
        self.assertIn("end-to-end", first_packet)
        self.assertLess(len(first_packet), 12000)

        # A staged product edit exists before the first plan pass and must not
        # be swallowed by the audit-only planning commit.
        worktree = self.worktree("S1")
        staged = "preserved-staged-product-note.txt"
        (worktree / staged).write_text("preserve this staged product edit\n", encoding="utf-8")
        self.git("add", staged, cwd=worktree)
        self.start_step_plan("S1")
        review_action = self.action_id()

        cold_packet = self.cli("next").stdout
        self.assertIn("--section step-plan", cold_packet)
        self.assertIn("--section step-context", cold_packet)
        self.assertIn("History index", cold_packet)
        self.assertIn("Knowledge pages:", cold_packet)
        self.assertLess(len(cold_packet), 14000)
        context = self.cli(
            "context", "--section", "step-context", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn("direct_suppliers", context)
        self.assertIn("direct_consumers", context)
        self.assertIn("environment_sha256", context)
        compact_plan = self.cli(
            "context", "--section", "step-plan", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn("Current step-plan candidate", compact_plan)
        self.assertIn("completed_passes", compact_plan)
        self.assertNotIn("improve_cycles", compact_plan)
        # The planned case is durable Markdown, not an assertion supplied only
        # in the current host turn.  A cold context must expose its exact ID
        # and expected observable outcome before implementation begins.
        self.assertIn("TC-S1-exact", compact_plan)
        self.assertIn("Expected outcome:", compact_plan)
        self.assertIn(self.product_for("S1"), compact_plan)

        incomplete_review = {
            "summary": "This deliberately incomplete review has no current history or knowledge acknowledgement.",
            "findings": [],
            "coverage_review": self.step_plan_coverage(),
            "context_evidence": self.step_plan_context_evidence("S1"),
            "test_review": "The candidate must still bind an exact expected output.",
            "learnings": "A review cannot be accepted without its current durable evidence.",
            "knowledge_read": {"revision": 0, "digest": "wrong", "scope": ["S1"]},
        }
        rejected, _ = self.complete(
            incomplete_review,
            action_id=review_action,
            code=2,
            label="step-plan-missing-history-and-knowledge",
        )
        self.assertIn("knowledge", rejected.stderr.lower())
        self.assertEqual(self.action_id(), review_action)
        incomplete_review["knowledge_read"] = self.read_knowledge("S1")
        rejected, _ = self.complete(
            incomplete_review,
            action_id=review_action,
            code=2,
            label="step-plan-missing-history",
        )
        self.assertIn("history", rejected.stderr.lower())
        self.assertEqual(self.action_id(), review_action)

        first, second, third, receipt = self.converge_step_plan(
            "S1", material_first=True, staged_product_path=staged
        )
        self.assertIsNotNone(third)
        self.assertEqual(
            [row["outcome"] for row in receipt["completed_passes"]],
            ["material", "trivial", "trivial"],
        )
        self.assertEqual(len(set(row["commit"] for row in receipt["completed_passes"])), 3)
        self.assertTrue((worktree / staged).exists())
        self.assertIn(staged, self.git("diff", "--cached", "--name-only", cwd=worktree))
        self.assertTrue(
            (self.run_dir / step_planning.certificate_name(receipt["loop_id"])).is_file()
        )

        # Keep the staged-edit assertion above, then unstage it so the actual
        # implementation commit remains scoped to the declared fixture files.
        self.git("reset", "--", staged, cwd=worktree)
        (worktree / staged).unlink()
        implement_packet = self.cli("next").stdout
        self.assertIn("Stage: implement", implement_packet)
        self.assertIn("--section step-plan", implement_packet)
        self.write_implementation("S1")
        implementation_action = self.action_id()
        self.verify_current(self.manifest_for("S1"), label="initial-plan-implementation-checks")
        _, implementation_draft = self.complete(
            {
                "summary": "The legitimate product edit and its fresh checks advance only after the finalized plan proof.",
                "test_review": "Post-code learning: authored manifest check T-S1 exact-output test passed in the selected local environment; mock/fake and end-to-end are not applicable to this local fixture.",
            },
            action_id=implementation_action,
            label="initial-plan-implementation-complete",
        )
        self.assertEqual(self.state()["stage"], "review")
        implementation_result = self.run_dir / "results" / f"{implementation_action}.md"
        self.assertTrue(implementation_result.is_file())
        accepted_result = implementation_result.read_text(encoding="utf-8")
        self.assertIn(
            "Post-code learning: authored manifest check T-S1",
            accepted_result,
        )
        # The inbox is only a submission transport.  A cold step-context must
        # reconstruct the accepted initial test note from results/<action>.md,
        # whose digest is bound in completed_actions, after the inbox is gone.
        implementation_draft_path = Path(implementation_draft)
        self.assertTrue(implementation_draft_path.is_file())
        implementation_draft_path.unlink()
        self.assertFalse(implementation_draft_path.exists())
        cold_context = self.cli(
            "context", "--section", "step-context", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn("implementation_test_record", cold_context)
        self.assertIn(implementation_action, cold_context)
        self.assertIn(f"results/{implementation_action}.md", cold_context)
        self.assertIn("historical host-reported notes", cold_context)
        self.assertIn("Post-code learning: authored manifest check T-S1", cold_context)
        # Re-enter through the cold packet after completion: it must describe
        # the code-learning refinement/review handoff, rather than relying on
        # the previous implementation conversation.
        post_code_packet = self.cli("next").stdout
        self.assertIn("code learnings", post_code_packet)
        self.assertIn("--section step-plan", post_code_packet)
        self.assertIn("unit", post_code_packet)
        self.assertIn("mock/fake", post_code_packet)
        self.assertIn("end-to-end", post_code_packet)
        implementation_result.write_text(
            accepted_result.replace(
                "Post-code learning: authored manifest check T-S1",
                "Post-code learning: tampered manifest check T-S1",
            ),
            encoding="utf-8",
        )
        rejected = self.cli(
            "context", "--section", "step-context", "--offset", "0", "--limit", "8000", code=2
        )
        self.assertIn("digest mismatch", rejected.stderr)
        implementation_result.write_text(accepted_result, encoding="utf-8")
        self.assertNotEqual(first["commit"], second["commit"])

    def test_finalized_plan_artifacts_are_required_by_actual_implementation_completion(self):
        self.bootstrap_to_first_implementation()
        receipt = self.step_plan_receipt("S1")
        candidate = self.run_dir / receipt["candidate_path"]
        receipt_path = self.run_dir / step_planning.receipt_name(receipt["loop_id"])
        certificate_path = self.run_dir / step_planning.certificate_name(receipt["loop_id"])
        backups = {
            candidate: candidate.read_bytes(),
            receipt_path: receipt_path.read_bytes(),
            certificate_path: certificate_path.read_bytes(),
        }

        self.write_implementation("S1")
        action = self.action_id()
        self.verify_current(self.manifest_for("S1"), label="proof-corruption-implementation-checks")
        result = {
            "summary": "Attempt completion with corrupted prior step-plan proof.",
            "test_review": "The implementation checks themselves passed but the prerequisite proof must remain intact.",
        }
        cases = (
            (candidate, b"# Corrupted candidate\n"),
            (receipt_path, b"# Corrupted receipt\n"),
            (certificate_path, b"# Corrupted certificate\n"),
        )
        for path, broken in cases:
            with self.subTest(path=path.name):
                path.write_bytes(broken)
                blocked, _ = self.complete(
                    result,
                    action_id=action,
                    code=2,
                    label=f"corrupt-{path.name}",
                )
                self.assertIn("step-plan", blocked.stderr)
                self.assertEqual(self.state()["stage"], "implement")
                path.write_bytes(backups[path])

        self.complete(result, action_id=action, label="restored-proof-implementation")
        self.assertEqual(self.state()["stage"], "review")

    def test_improve_plan_is_a_second_bound_loop_and_carries_parent_learnings(self):
        self.bootstrap_to_first_implementation()
        initial_plan = self.step_plan_receipt("S1")
        initial_pass_id = initial_plan["current_pass"]["id"]
        self.start_step("S1", exercise_failed_and_stale=False)
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        review = {
            "summary": "The enclosing review creates a trivial finding for the nested plan gate.",
            "findings": [
                {
                    "severity": "trivial",
                    "summary": "Document the exact-output test's expected outcome in the plan candidate.",
                }
            ],
            "test_review": "The current exact-output and syntax checks remain the execution evidence.",
            "learnings": "Every enclosing review finding must be visible to the cold nested planning pass.",
            "knowledge_read": self.read_knowledge("S1"),
        }
        self.complete(review, action_id=review_action, label="nested-plan-parent-review")
        self.assertEqual(self.state()["stage"], "improve-plan")
        draft_packet = self.cli("next").stdout
        self.assertIn("Stage: improve-plan", draft_packet)
        self.assertIn("--section step-context", draft_packet)
        self.assertIn("post-code", draft_packet)
        self.assertIn("unit", draft_packet)
        self.assertIn("mock/fake", draft_packet)
        self.assertIn("end-to-end", draft_packet)
        self.assertNotIn("Current candidate/pass:", draft_packet)
        prior_plan = self.cli(
            "context", "--section", "step-plan", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn("# Previous finalized step-plan candidate", prior_plan)
        self.assertIn(initial_pass_id, prior_plan)
        parent_context = self.cli(
            "context", "--section", "step-context", "--offset", "0", "--limit", "8000"
        ).stdout
        parent_ids = sorted(set(re.findall(r"PARENT-[0-9a-f]{16}", parent_context)))
        self.assertEqual(len(parent_ids), 1)
        self.assertIn("enclosing_review_sha256", parent_context)

        blocked, _ = self.complete(
            {
                "summary": "A candidate that omits the parent finding must not begin the nested loop.",
                "body": self.step_plan_candidate("S1", "missing parent ids"),
            },
            code=2,
            label="nested-plan-missing-parent-id",
        )
        self.assertIn(parent_ids[0], blocked.stderr)
        self.assertEqual(self.state()["stage"], "improve-plan")

        self.start_step_plan("S1")
        nested_receipt = self.step_plan_receipt("S1")
        nested_plan = self.cli(
            "context", "--section", "step-plan", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn("# Current step-plan candidate", nested_plan)
        self.assertIn(nested_receipt["current_pass"]["id"], nested_plan)
        self.assertNotIn(initial_pass_id, nested_plan)
        nested_iteration = self.cli(
            "context", "--section", "iteration", "--offset", "0", "--limit", "8000"
        ).stdout
        self.assertIn(nested_receipt["current_pass"]["id"], nested_iteration)
        self.assertIn("# Current step-plan pass", nested_iteration)
        self.assertNotIn("# Current iteration", nested_iteration)

        first, second, _third, receipt = self.converge_step_plan("S1")
        self.assertEqual(receipt["route"], "improve")
        self.assertEqual(self.state()["stage"], "improve-apply")
        improve_apply_packet = self.cli("next").stdout
        self.assertIn("Stage: improve-apply", improve_apply_packet)
        self.assertIn("post-code", improve_apply_packet)
        self.assertIn("unit", improve_apply_packet)
        self.assertIn("mock/fake", improve_apply_packet)
        self.assertIn("end-to-end", improve_apply_packet)
        iteration = self.receipt("S1")["iteration"]
        self.assertEqual(iteration["step_plan"]["loop_id"], receipt["loop_id"])
        self.assertTrue(iteration["plan_learnings"])
        candidate = (self.run_dir / receipt["candidate_path"]).read_text(encoding="utf-8")
        self.assertTrue(all(parent_id in candidate for parent_id in parent_ids))
        self.assertNotEqual(first["commit"], second["commit"])

    def test_step_plan_repair_archives_a_drifted_pass_and_rebinds_a_new_epoch(self):
        self.bootstrap_to_first_step_plan()
        self.start_step_plan("S1")
        action = self.action_id()
        worktree = self.worktree("S1")
        (worktree / "step-plan-drift.txt").write_text("changed after plan draft\n", encoding="utf-8")
        before = self.step_plan_receipt("S1")
        rejected, _ = self.complete(
            {
                "summary": "A stale worktree context cannot be reviewed as though it were the draft context.",
                "findings": [],
                "coverage_review": self.step_plan_coverage(),
                "context_evidence": self.step_plan_context_evidence("S1"),
                "test_review": "No current check can certify the drifted plan context.",
                "learnings": "Context drift requires explicit repair and a new epoch.",
                "knowledge_read": self.read_knowledge("S1"),
            },
            action_id=action,
            code=2,
            label="step-plan-drifted-review",
        )
        self.assertIn("context changed", rejected.stderr)
        self.cli("repair", "--action", action, "--reason", "Fixture worktree changed after the plan draft.")
        repaired = self.step_plan_receipt("S1")
        self.assertEqual(repaired["epoch"], before["epoch"] + 1)
        self.assertEqual(len(repaired["abandoned_passes"]), 1)
        self.assertEqual(self.state()["stage"], "step-plan-review")

    def test_material_scope_finding_requires_explicit_disposition_before_fresh_review(self):
        self.bootstrap_to_first_step_plan()
        self.start_step_plan("S1")
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        self.complete(
            {
                "summary": "The review identifies a material scope change that requires an authorized broader-plan decision.",
                "findings": [
                    {
                        "id": "SP-SCOPE",
                        "severity": "material",
                        "category": "scope",
                        "summary": "The requested extra artifact would broaden the frozen dependency sequence.",
                    }
                ],
                "coverage_review": self.step_plan_coverage(),
                "context_evidence": self.step_plan_context_evidence("S1"),
                "test_review": "The current exact-output case does not authorize an additional artifact.",
                "learnings": "A material scope finding must pause for an explicit broader-plan decision.",
                "knowledge_read": self.read_knowledge("S1"),
            },
            action_id=review_action,
            label="step-plan-material-scope-review",
        )
        before = self.state()
        self.assertEqual(before["stage"], "step-plan-disposition")
        self.assertIn("broader-plan", before["paused"])
        disposition_action = before["action"]["id"]
        receipt_before = self.step_plan_receipt("S1")
        candidate = self.run_dir / receipt_before["candidate_path"]
        candidate_before = candidate.read_bytes()

        # Resume permits only the durable disposition action.  It neither
        # clears the finding nor returns the host to ordinary plan revision.
        self.cli("resume")
        after_resume = self.state()
        self.assertEqual(after_resume["action"], before["action"])
        self.assertEqual(after_resume["stage"], "step-plan-disposition")
        self.assertNotIn("paused", after_resume)

        blocked, _ = self.complete(
            {
                "summary": "A local candidate must not clear the broader-plan finding.",
                "disposition": "no-contract-change",
                "body": self.step_plan_candidate("S1", "invalid scope bypass"),
                "resolutions": [
                    {
                        "id": "SP-SCOPE",
                        "evidence": "A local plan text cannot authorize a frozen-scope change.",
                    }
                ],
            },
            action_id=disposition_action,
            code=2,
            label="step-plan-scope-bypass-revise",
        )
        self.assertIn("cannot edit the candidate", blocked.stderr)
        after_revise = self.state()
        self.assertEqual(after_revise["action"], before["action"])
        self.assertEqual(after_revise["stage"], "step-plan-disposition")
        self.assertEqual(candidate.read_bytes(), candidate_before)

        # Repair is permitted only after resume, but it must retain the scope
        # blocker and return to the same explicit disposition—not ordinary
        # candidate revision.
        self.cli(
            "repair",
            "--action",
            disposition_action,
            "--reason",
            "The fixture deliberately restarts the scoped disposition pass.",
        )
        after_repair = self.state()
        self.assertEqual(after_repair["stage"], "step-plan-disposition")
        self.assertIn("broader-plan", after_repair["paused"])
        self.assertNotEqual(after_repair["action"], before["action"])
        repaired_receipt = self.step_plan_receipt("S1")
        self.assertEqual(repaired_receipt["epoch"], receipt_before["epoch"] + 1)
        self.assertEqual(len(repaired_receipt["abandoned_passes"]), 1)
        self.assertEqual(candidate.read_bytes(), candidate_before)

        self.cli("resume")
        resumed_disposition_action = self.action_id()
        self.assertNotEqual(resumed_disposition_action, disposition_action)
        self.assertEqual(self.state()["stage"], "step-plan-disposition")

        self.complete(
            {
                "summary": "The investigated finding is a false-positive classification; the approved contract is unchanged.",
                "disposition": "no-contract-change",
                "resolutions": [
                    {
                        "id": "SP-SCOPE",
                        "evidence": "The frozen step output and dependency sequence already exclude the suggested extra artifact.",
                    }
                ],
            },
            action_id=resumed_disposition_action,
            label="step-plan-no-contract-change-disposition",
        )
        after_disposition = self.state()
        self.assertEqual(after_disposition["stage"], "step-plan-review")
        self.assertNotEqual(after_disposition["action"], before["action"])
        receipt_after = self.step_plan_receipt("S1")
        self.assertEqual(receipt_after["epoch"], receipt_before["epoch"] + 2)
        self.assertEqual(len(receipt_after["abandoned_passes"]), 2)
        self.assertEqual(candidate.read_bytes(), candidate_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
