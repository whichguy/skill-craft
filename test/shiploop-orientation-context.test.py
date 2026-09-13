#!/usr/bin/env python3
"""Focused provenance and supporting-response tests for ShipLoop packets."""

from __future__ import annotations

import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_objectives as objectives  # noqa: E402
import shiploop_planning as planning  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_step_planning as step_planning  # noqa: E402
import shiploop_store as store  # noqa: E402


class OrientationContextTests(unittest.TestCase):
    """Keep display provenance verified without giving it transition authority."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-orientation-")
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def objective_context() -> dict[str, str]:
        return {
            "git_baseline": "a" * 40,
            "committed_tree_sha256": "b" * 40,
            "worktree_fingerprint": "c" * 64,
            "status_sha256": "d" * 64,
            "spec_sha256": "e" * 64,
            "environment_sha256": "f" * 64,
            "behavior_sha256": "1" * 64,
            "plan_sha256": "2" * 64,
            "knowledge_sha256": "3" * 64,
        }

    def step_context(self) -> dict[str, str]:
        return {
            "step_sha256": "a" * 64,
            "dependency_sha256": "b" * 64,
            "enclosing_review_sha256": "c" * 64,
            "worktree": str(self.root.resolve()),
            "git_baseline": "d" * 40,
            "committed_tree_sha256": "e" * 64,
            "worktree_fingerprint": "f" * 64,
            "status_sha256": "1" * 64,
            "spec_sha256": "2" * 64,
            "environment_sha256": "3" * 64,
            "behavior_sha256": "4" * 64,
            "plan_sha256": "5" * 64,
            "knowledge_sha256": "6" * 64,
        }

    def objective_fixture(self, *, include_origin: bool = True) -> tuple[dict, dict, dict]:
        action = "accepted-approach"
        result = {
            "summary": "The initial approach is a candidate, not a quality verdict.",
            "body": "# Approach\n\nInspect supplied input before implementation.\n",
        }
        candidate_body = store.dumps(result, "ShipLoop approach objective candidate")
        loop = objectives.loop_id("20260913T010203Z-a1b2c3d4", "approach")
        kwargs = {}
        if include_origin:
            kwargs["origin"] = {
                "action_id": action,
                "result_sha256": protocol.digest(result),
                "candidate_sha256": objectives.candidate_identity(candidate_body),
            }
        receipt = objectives.new_receipt(
            loop=loop,
            kind="approach",
            base_stage="approach",
            candidate_body=candidate_body,
            context=self.objective_context(),
            **kwargs,
        )
        candidate_path = self.root / receipt["candidate_path"]
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(candidate_body, encoding="utf-8")
        store.write_record(self.root / objectives.receipt_name(loop), receipt)
        store.write_record(self.root / "results" / f"{action}.md", result)
        state = {
            "objective_protocol_version": objectives.VERSION,
            "stage": "objective-review",
            "phase": "intake",
            "action": {"id": "objective-review-current"},
            "completed_actions": {action: protocol.digest(result)},
            "objective": {
                "loop_id": loop,
                "kind": "approach",
                "base_stage": "approach",
                "receipt": objectives.receipt_name(loop),
                "candidate": objectives.candidate_name(loop),
                "status": "active",
            },
        }
        return state, receipt, result

    def test_objective_orientation_distinguishes_origin_first_assessment_and_changed_candidate(self) -> None:
        state, receipt, _ = self.objective_fixture()

        first = protocol.packet_orientation(self.root, state)["quality"]
        self.assertEqual(first["continuity"], "same-loop")
        self.assertEqual(first["initial_candidate"]["action_id"], "accepted-approach")
        self.assertEqual(first["initial_candidate"]["path"], "results/accepted-approach.md")
        self.assertEqual(first["assessment"]["status"], "not-yet-assessed")
        self.assertEqual(first["current_candidate"]["path"], receipt["candidate_path"])

        review_action = "objective-review-first"
        review = {
            "summary": "The first review found a material missing-input edge condition.",
            "findings": [],
        }
        store.write_record(self.root / "results" / f"{review_action}.md", review)
        state["completed_actions"][review_action] = protocol.digest(review)
        receipt["first_assessment"] = {
            "action_id": review_action,
            "result_sha256": protocol.digest(review),
            "candidate_sha256": receipt["candidate_sha256"],
            "epoch": receipt["epoch"],
        }
        receipt["identity_sha256"] = objectives.identity(receipt)
        changed_candidate = store.dumps(
            {
                "summary": "The revised approach now rejects missing input.",
                "body": "# Approach\n\nReject absent input before implementation.\n",
            },
            "ShipLoop approach objective candidate",
        )
        objectives.replace_candidate(receipt, changed_candidate)
        (self.root / receipt["candidate_path"]).write_text(
            changed_candidate, encoding="utf-8"
        )
        store.write_record(self.root / objectives.receipt_name(receipt["loop_id"]), receipt)

        later = protocol.packet_orientation(self.root, state)["quality"]
        assessment = later["assessment"]
        self.assertEqual(assessment["status"], "recorded")
        self.assertEqual(assessment["action_id"], review_action)
        self.assertEqual(assessment["path"], f"results/{review_action}.md")
        self.assertFalse(assessment["current_candidate_matches"])
        self.assertNotEqual(
            later["initial_candidate"]["candidate_sha256"],
            later["current_candidate"]["digest"],
        )

    def test_legacy_or_tampered_origin_never_becomes_invented_provenance(self) -> None:
        state, _, _ = self.objective_fixture(include_origin=False)
        legacy = protocol.packet_orientation(self.root, state)["quality"]
        self.assertIsNone(legacy["initial_candidate"])
        self.assertEqual(legacy["assessment"]["status"], "unavailable")
        self.assertIn("legacy", legacy["reason"])

        state, _, _ = self.objective_fixture(include_origin=True)
        state["completed_actions"]["accepted-approach"] = "0" * 64
        with self.assertRaisesRegex(protocol.ProtocolError, "digest mismatch"):
            protocol.packet_orientation(self.root, state)

    def test_initial_step_plan_has_no_baseline_until_its_draft_creates_one(self) -> None:
        """Only the fresh draft stage may lack a step-plan receipt."""
        run_id, step_id = "20260913T010203Z-a1b2c3d4", "S1"
        repo = self.root / "repo"
        worktree = repo / ".worktrees" / "shiploop" / run_id / step_id
        store.write_record(
            self.root / "steps" / f"{step_id}.md",
            {
                "id": step_id,
                "run_id": run_id,
                "worktree": str(worktree),
                "branch": f"shiploop/{run_id}/{step_id}",
                "base_sha": "a" * 40,
            },
        )
        state = {
            "run_id": run_id,
            "repo_root": str(repo),
            "phase": "implement",
            "stage": "step-plan",
            "action": {"id": "step-plan-current"},
            "active_step": step_id,
        }

        fresh = protocol.packet_orientation(self.root, state)
        self.assertIsNone(fresh["quality"])

        state["stage"] = "step-plan-review"
        with self.assertRaisesRegex(
            protocol.ProtocolError, "active step has no bound step-plan loop"
        ):
            protocol.packet_orientation(self.root, state)

    def test_planning_and_step_plan_project_bound_origins_and_repair_history(self) -> None:
        planning_action = "behavior-draft"
        planning_result = {"summary": "Behavior candidate", "body": "# Behavior\n\nReject absent input.\n"}
        (self.root / "behavior.md").write_text(planning_result["body"], encoding="utf-8")
        candidate = planning.candidate_identity(self.root, "behavior")
        planning_receipt = planning.new_receipt(
            root=self.root,
            state={"run_id": "20260913T010203Z-a1b2c3d4", "planning_epoch": 1},
            kind="behavior",
            git_baseline="a" * 40,
            product_fingerprint="b" * 64,
            candidate=candidate,
            origin={
                "action_id": planning_action,
                "result_sha256": protocol.digest(planning_result),
                "candidate_sha256": candidate["candidate_sha256"],
            },
        )
        planning_review_action = "behavior-review-one"
        planning_review = {"summary": "Initial behavior review."}
        planning.record_first_assessment(
            planning_receipt,
            {
                "action_id": planning_review_action,
                "result_sha256": protocol.digest(planning_review),
                "candidate_sha256": candidate["candidate_sha256"],
                "epoch": 1,
            },
        )
        store.write_record(self.root / "planning" / "behavior.md", planning_receipt)
        store.write_record(self.root / "results" / f"{planning_action}.md", planning_result)
        store.write_record(
            self.root / "results" / f"{planning_review_action}.md", planning_review
        )
        planning_state = {
            "planning_protocol_version": planning.PROTOCOL_VERSION,
            "stage": "behavior-review",
            "phase": "validate-spec",
            "action": {"id": planning_review_action},
            "completed_actions": {
                planning_action: protocol.digest(planning_result),
                planning_review_action: protocol.digest(planning_review),
            },
        }
        planning_quality = protocol.packet_orientation(self.root, planning_state)["quality"]
        self.assertEqual(planning_quality["initial_candidate"]["action_id"], planning_action)
        self.assertEqual(planning_quality["current_candidate"]["kind"], "candidate-set")
        self.assertEqual(planning_quality["current_candidate"]["paths"], ["behavior.md"])
        self.assertTrue(planning_quality["assessment"]["current_candidate_matches"])

        step_action = "step-plan-draft"
        step_result = {"summary": "Step-plan candidate", "body": "# Step plan\n\nWrite a bounded test first.\n"}
        run_id, step_id = "20260913T010203Z-a1b2c3d4", "S1"
        loop = step_planning.loop_id(run_id, step_id, "initial")
        step_receipt = step_planning.new_receipt(
            loop=loop,
            step_id=step_id,
            route="initial",
            return_stage="implement",
            body=step_result["body"],
            context=self.step_context(),
            origin={
                "action_id": step_action,
                "result_sha256": protocol.digest(step_result),
                "candidate_sha256": step_planning.candidate_identity(step_result["body"]),
            },
        )
        step_review_action = "step-plan-review-one"
        step_review = {"summary": "Initial step-plan review."}
        step_planning.record_first_assessment(
            step_receipt,
            {
                "action_id": step_review_action,
                "result_sha256": protocol.digest(step_review),
                "candidate_sha256": step_receipt["candidate_sha256"],
                "epoch": 1,
            },
        )
        candidate_path = self.root / step_receipt["candidate_path"]
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(step_result["body"], encoding="utf-8")
        store.write_record(self.root / step_planning.receipt_name(loop), step_receipt)
        store.write_record(self.root / "results" / f"{step_action}.md", step_result)
        store.write_record(self.root / "results" / f"{step_review_action}.md", step_review)
        repo = self.root / "repo"
        worktree = repo / ".worktrees" / "shiploop" / run_id / step_id
        worktree.mkdir(parents=True)
        record = {
            "id": step_id,
            "run_id": run_id,
            "worktree": str(worktree),
            "branch": f"shiploop/{run_id}/{step_id}",
            "base_sha": "a" * 40,
            "step_plan": {
                "loop_id": loop,
                "receipt": step_planning.receipt_name(loop),
                "candidate": step_receipt["candidate_path"],
                "status": "active",
            },
        }
        store.write_record(self.root / "steps" / f"{step_id}.md", record)
        step_state = {
            "step_planning_protocol_version": step_planning.VERSION,
            "stage": "step-plan-review",
            "phase": "implement",
            "action": {"id": step_review_action},
            "active_step": step_id,
            "run_id": run_id,
            "repo_root": str(repo),
            "completed_actions": {
                step_action: protocol.digest(step_result),
                step_review_action: protocol.digest(step_review),
            },
        }
        step_quality = protocol.packet_orientation(self.root, step_state)["quality"]
        self.assertEqual(step_quality["initial_candidate"]["action_id"], step_action)
        self.assertTrue(step_quality["assessment"]["current_candidate_matches"])

        step_planning.rebind_after_repair(step_receipt, self.step_context())
        store.write_record(self.root / step_planning.receipt_name(loop), step_receipt)
        repaired = protocol.packet_orientation(self.root, step_state)["quality"]
        self.assertEqual(repaired["assessment"]["status"], "recorded")
        self.assertFalse(repaired["assessment"]["current_candidate_matches"])

        # A legacy/repaired receipt may lack this new locator.  Its next
        # review must remain unknown rather than being relabeled as first.
        step_receipt.pop("first_assessment")
        step_planning._sync_identity(step_receipt)
        store.write_record(self.root / step_planning.receipt_name(loop), step_receipt)
        unknown_after_repair = protocol.packet_orientation(self.root, step_state)["quality"]
        self.assertEqual(unknown_after_repair["assessment"]["status"], "unavailable")
        self.assertIn("do not relabel", unknown_after_repair["reason"])

    def test_receipt_provenance_is_strict_and_legacy_removal_breaks_identity(self) -> None:
        removed_state, removed_receipt, _ = self.objective_fixture()
        removed_receipt.pop("origin")
        store.write_record(
            self.root / removed_state["objective"]["receipt"], removed_receipt
        )
        with self.assertRaisesRegex(protocol.ProtocolError, "identity mismatch"):
            protocol.packet_orientation(self.root, removed_state)

        state, receipt, result = self.objective_fixture()
        origin = dict(receipt["origin"], unexpected="no")
        with self.assertRaisesRegex(objectives.ObjectiveError, "origin keys"):
            objectives.new_receipt(
                loop=objectives.loop_id("20260913T010203Z-a1b2c3d4", "approach"),
                kind="approach",
                base_stage="approach",
                candidate_body=store.dumps(result, "ShipLoop approach objective candidate"),
                context=self.objective_context(),
                origin=origin,
            )
        with self.assertRaisesRegex(objectives.ObjectiveError, "epoch is invalid"):
            objectives.record_first_assessment(
                receipt,
                {
                    "action_id": "first-review",
                    "result_sha256": "f" * 64,
                    "candidate_sha256": receipt["candidate_sha256"],
                    "epoch": True,
                },
            )
        objectives.record_first_assessment(
            receipt,
            {
                "action_id": "first-review",
                "result_sha256": "f" * 64,
                "candidate_sha256": receipt["candidate_sha256"],
                "epoch": 1,
            },
        )
        receipt.pop("origin")
        receipt["identity_sha256"] = objectives.identity(receipt)
        store.write_record(self.root / state["objective"]["receipt"], receipt)
        with self.assertRaisesRegex(protocol.ProtocolError, "requires origin provenance"):
            protocol.packet_orientation(self.root, state)

        state, receipt, _ = self.objective_fixture()
        receipt["first_assessment"] = {
            "action_id": "first-review",
            "result_sha256": "f" * 64,
            "candidate_sha256": "0" * 64,
            "epoch": 1,
        }
        receipt["identity_sha256"] = objectives.identity(receipt)
        store.write_record(self.root / state["objective"]["receipt"], receipt)
        with self.assertRaisesRegex(protocol.ProtocolError, "does not bind the origin candidate"):
            protocol.packet_orientation(self.root, state)

    def test_context_keeps_legacy_header_and_marks_it_as_supporting_data(self) -> None:
        repo = self.root / "repo"
        repo.mkdir()
        env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(ROOT / "test/fixtures/shiploop/backchain-leaf"),
        )
        for args in (
            ("init", "-q"),
            ("config", "user.name", "Orientation Test"),
            ("config", "user.email", "orientation@example.invalid"),
            ("config", "commit.gpgsign", "false"),
            ("config", "core.hooksPath", "/dev/null"),
            ("commit", "--allow-empty", "-qm", "baseline"),
        ):
            result = subprocess.run(
                ["git", "-C", str(repo), *args], text=True, capture_output=True, env=env
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        run_dir = repo / ".shiploop"
        started = subprocess.run(
            [sys.executable, str(CLI), "init", "--repo", str(repo), "--prompt", "Inspect a bounded fixture."],
            cwd=repo,
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        state_before = (run_dir / "state.md").read_bytes()
        response = subprocess.run(
            [sys.executable, str(CLI), "context", "--run-dir", str(run_dir), "--section", "prompt"],
            cwd=repo,
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(response.returncode, 0, response.stdout + response.stderr)
        self.assertRegex(
            response.stdout.splitlines()[0],
            r"^Context prompt; digest [0-9a-f]{64}; characters 0:\d+/\d+$",
        )
        self.assertIn("Supporting response:", response.stdout)
        self.assertIn("does not assign a new action", response.stdout)
        self.assertIn("does not prove overall completion", response.stdout)
        self.assertIn("Safe return:", response.stdout)
        self.assertEqual((run_dir / "state.md").read_bytes(), state_before)

    def test_failed_request_describes_durable_cursor_recovery(self) -> None:
        """A rejected submission cannot choose a next action from local memory."""
        fixture_class = runpy.run_path(
            str(ROOT / "test" / "shiploop-packets.test.py")
        )["PacketTests"]
        fixture = fixture_class()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.cli(
            "init",
            "--repo",
            str(fixture.repo),
            "--run-dir",
            str(fixture.run_dir),
            "--prompt=Build a bounded local fixture.",
        )
        action_id = fixture.state()["action"]["id"]
        rejected = fixture.cli(
            "done",
            "--action",
            action_id,
            "--result",
            fixture.result("invalid-preflight.md", {"summary": "Baseline omitted."}),
            code=2,
        )

        self.assertIn("ShipLoop blocked:", rejected.stderr)
        self.assertIn(
            f"Recover the current durable action: python3 {CLI} next --run-dir {fixture.run_dir}",
            rejected.stderr,
        )
        self.assertIn(
            "no in-memory result, candidate, or rejected artifact is trusted",
            rejected.stderr,
        )
        self.assertIn(
            "safely available durable orientation",
            rejected.stderr,
        )
        self.assertIn("Broader purpose: unavailable in this failure response", rejected.stderr)

    def test_quality_baseline_reader_is_allowlisted_paged_and_digest_bound(self) -> None:
        fixture_class = runpy.run_path(
            str(ROOT / "test" / "shiploop-packets.test.py")
        )["PacketTests"]
        fixture = fixture_class()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.cli(
            "init",
            "--repo",
            str(fixture.repo),
            "--run-dir",
            str(fixture.run_dir),
            "--prompt=Build a local CSV summary CLI; do not fabricate missing input.",
        )

        def complete(value: dict) -> None:
            action_id = fixture.state()["action"]["id"]
            fixture.cli(
                "done",
                "--action",
                action_id,
                "--result",
                fixture.result(action_id + ".md", value),
            )

        complete({"summary": "Baseline inspected; owner input is absent.", "baseline": "committed-head"})
        origin_action = fixture.state()["action"]["id"]
        origin_result = {
            "summary": "Approach candidate; input-dependent quality is unassessed.",
            "body": "# Approach\n\nInspect owner CSV before planning outputs.\n",
        }
        origin_path = fixture.result("orientation-origin.md", origin_result)
        fixture.cli("done", "--action", origin_action, "--result", origin_path)

        before = (fixture.run_dir / "state.md").read_bytes()
        first = fixture.cli(
            "context",
            "--run-dir",
            str(fixture.run_dir),
            "--section",
            "quality-baseline",
            "--limit",
            "80",
        ).stdout
        header = first.splitlines()[0]
        match = re.fullmatch(
            r"Context quality-baseline; digest ([0-9a-f]{64}); characters 0:(\d+)/(\d+)",
            header,
        )
        self.assertIsNotNone(match)
        self.assertIn("Supporting response:", first)
        self.assertEqual((fixture.run_dir / "state.md").read_bytes(), before)
        assert match is not None
        page_end, total = int(match.group(2)), int(match.group(3))
        self.assertLess(page_end, total)
        continued = fixture.cli(
            "context",
            "--run-dir",
            str(fixture.run_dir),
            "--section",
            "quality-baseline",
            "--offset",
            str(page_end),
            "--limit",
            "4000",
            "--digest",
            match.group(1),
        ).stdout
        self.assertIn("origin/initial output", continued)
        self.assertIn(origin_result["summary"], continued)
        self.assertIn("not-yet-assessed", continued)

        review_action = fixture.state()["action"]["id"]
        fixture.cli(
            "history",
            "--run-dir",
            str(fixture.run_dir),
            "--action",
            review_action,
            "--limit",
            "7",
            "--skip",
            "0",
            "--full",
        )
        review_result = {
            "summary": "The first review found an absent-input edge condition.",
            "findings": [
                {
                    "id": "F-INPUT",
                    "severity": "material",
                    "category": "edge-condition",
                    "summary": "Specify absent-input behavior.",
                }
            ],
            "assessment": {
                key: "Inspected the current approach and recorded the input gap."
                for key in objectives.ASSESSMENT_KEYS
            },
            "history_assessment": "Read the full baseline commit.",
            "test_review": "Expected absent-input behavior needs a test.",
            "learnings": "An absent owner fixture is not observed application behavior.",
        }
        fixture.cli(
            "done",
            "--action",
            review_action,
            "--result",
            fixture.result("orientation-review.md", review_result),
        )
        assessed = fixture.cli(
            "context",
            "--run-dir",
            str(fixture.run_dir),
            "--section",
            "quality-baseline",
            "--limit",
            "4000",
        ).stdout
        self.assertIn("first recorded assessment", assessed)
        self.assertIn(review_result["summary"], assessed)
        self.assertIn(review_action, assessed)

        receipt = store.read_record(fixture.run_dir / fixture.state()["objective"]["receipt"])
        bound_path = fixture.run_dir / receipt["origin"]["action_id"]
        self.assertFalse(bound_path.exists(), "quality reader must use results/<action>.md")
        store.write_record(
            fixture.run_dir / "results" / f"{origin_action}.md",
            dict(origin_result, summary="Tampered after acceptance."),
        )
        rejected = fixture.cli(
            "context",
            "--run-dir",
            str(fixture.run_dir),
            "--section",
            "quality-baseline",
            code=2,
        )
        self.assertIn("digest mismatch", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
