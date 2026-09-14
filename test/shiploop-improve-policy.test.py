#!/usr/bin/env python3
"""Frozen Improve-policy coverage for ShipLoop's product inner loop."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
REFS = ROOT / "skills" / "shiploop" / "references"
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"
SYNC = ROOT / "scripts" / "sync-shiploop-improve-policy.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_action_walk_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_improve_policy_action_fixture", str(ACTION_WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {ACTION_WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


ACTION = load_action_walk_fixture()

import shiploop_improve_policy as policy  # noqa: E402
import shiploop_packets as packets  # noqa: E402


class ImprovePolicyHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-improve-policy-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def package_copy(self, name: str) -> Path:
        target = self.root / name
        target.mkdir()
        for filename in (policy.SOURCE_FILE, policy.PIN_FILE):
            shutil.copyfile(REFS / filename, target / filename)
        return target

    def test_pinned_package_initializes_a_precise_markdown_binding(self) -> None:
        binding, body = policy.load_package(REFS)
        self.assertEqual(
            binding,
            {
                "version": 1,
                "policy_id": policy.POLICY_ID,
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            },
        )
        self.assertEqual(policy.validate_binding({}), None)
        for malformed in (
            None,
            {"version": 1, "policy_id": policy.POLICY_ID},
            {**binding, "extra": True},
            {**binding, "version": True},
            {**binding, "sha256": "A" * 64},
        ):
            with self.subTest(marker=malformed):
                with self.assertRaises(policy.ImprovePolicyError):
                    policy.validate_binding({"improve_policy": malformed})

        state = {"run_id": "fixture"}
        writes = {"existing.md": "preserved"}
        self.assertIsNone(policy.initialize(REFS, state, writes))
        self.assertEqual(state["improve_policy"], binding)
        self.assertEqual(writes, {"existing.md": "preserved", policy.RUN_FILE: body})
        self.assertFalse((self.root / policy.RUN_FILE).exists())

        copied = self.package_copy("mismatched-package")
        source = copied / policy.SOURCE_FILE
        source.write_bytes(source.read_bytes() + b"\nTampered policy bytes.\n")
        with self.assertRaises(policy.ImprovePolicyError):
            policy.load_package(copied)

    def test_bound_snapshot_is_frozen_legacy_safe_and_fail_closed(self) -> None:
        binding, body = policy.load_package(REFS)
        run = self.root / "run"
        run.mkdir()
        snapshot = run / policy.RUN_FILE
        snapshot.write_text(body, encoding="utf-8")
        state = {"improve_policy": dict(binding)}

        # A saved policy is deliberately independent of an installed package.
        with patch.object(policy, "load_package", side_effect=AssertionError("ambient package read")):
            self.assertEqual(policy.bound_path(run, state), snapshot)
        self.assertIsNone(policy.bound_path(run, {}))

        snapshot.unlink()
        with self.assertRaises(policy.ImprovePolicyError):
            policy.bound_path(run, state)

        old_body = (
            "# Improve review policy\n\n"
            f"Policy ID: {policy.POLICY_ID}\n\n"
            "This is an older valid v1 snapshot.\n"
        )
        old_binding = {
            "version": 1,
            "policy_id": policy.POLICY_ID,
            "sha256": hashlib.sha256(old_body.encode("utf-8")).hexdigest(),
        }
        snapshot.write_text(old_body, encoding="utf-8")
        with patch.object(policy, "load_package", side_effect=AssertionError("ambient package read")):
            self.assertEqual(
                policy.bound_path(run, {"improve_policy": old_binding}), snapshot
            )

        snapshot.write_bytes(b"# Improve review policy\n\nPolicy ID: " + policy.POLICY_ID.encode("ascii") + b"\n\xff")
        invalid_utf8 = {
            **old_binding,
            "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        }
        with self.assertRaisesRegex(policy.ImprovePolicyError, "UTF-8"):
            policy.bound_path(run, {"improve_policy": invalid_utf8})

        oversized = (
            "# Improve review policy\n\n"
            f"Policy ID: {policy.POLICY_ID}\n\n"
            + "x" * policy.MAX_BYTES
        )
        snapshot.write_text(oversized, encoding="utf-8")
        oversized_binding = {
            **old_binding,
            "sha256": hashlib.sha256(oversized.encode("utf-8")).hexdigest(),
        }
        with self.assertRaisesRegex(policy.ImprovePolicyError, "exceeds"):
            policy.bound_path(run, {"improve_policy": oversized_binding})

        snapshot.write_text(body, encoding="utf-8")
        alias = self.root / "snapshot-alias.md"
        os.link(snapshot, alias)
        with self.assertRaisesRegex(policy.ImprovePolicyError, "single-link"):
            policy.bound_path(run, state)


class ImprovePolicyPacketScopeTests(unittest.TestCase):
    def test_only_product_improve_stages_receive_the_frozen_cycle(self) -> None:
        frozen = "FROZEN-IMPROVE-POLICY-CYCLE"
        api = {
            "planning": SimpleNamespace(
                is_planning_stage=lambda stage: stage
                in {"research", "research-review"}
            ),
            "is_step_plan_stage": lambda stage: stage
            in {"step-plan", "step-plan-review"},
        }
        for stage in policy.PRODUCT_STAGES:
            with self.subTest(product_stage=stage):
                lifecycle = packets._stage_lifecycle(
                    stage, {"improve_policy_cycle": frozen}, api, history_limit=7
                )
                self.assertEqual(lifecycle[0], frozen)

        for stage in (
            "implement",
            "research",
            "research-review",
            "step-plan",
            "step-plan-review",
            "quality",
        ):
            with self.subTest(unscoped_stage=stage):
                lifecycle = packets._stage_lifecycle(
                    stage, {"improve_policy_cycle": frozen}, api, history_limit=7
                )
                self.assertNotIn(frozen, "\n".join(lifecycle))


class ImprovePolicyActionWalkTests(ACTION.ShipLoopActionWalkFixture):
    """One real-CLI product walk, with packet reads at every owned stage."""

    def setUp(self) -> None:
        super().setUp()
        self.policy_packets: dict[str, str] = {}
        self.rejected_old_primary = False

    def capture_policy_packet(self) -> None:
        state = self.state()
        stage = state["stage"]
        if stage not in policy.PRODUCT_STAGES:
            return
        snapshot = self.run_dir / policy.RUN_FILE
        before = self.authoritative_snapshot("steps/S1.md")
        before_policy = snapshot.read_bytes()
        packet = self.cli("next", "--run-dir", str(self.run_dir), cwd=self.root).stdout
        self.assert_authority_unchanged(before, "steps/S1.md")
        self.assertEqual(snapshot.read_bytes(), before_policy)
        binding = policy.validate_binding(state)
        self.assertIsNotNone(binding)
        assert binding is not None
        self.assertIn(str(snapshot), packet)
        self.assertIn(binding["sha256"], packet)
        self.assertIn("Execution mode: ShipLoop-managed.", packet)
        self.assertIn("Owner overrides:", packet)
        self.assertIn("EVERY iteration", packet)
        self.policy_packets[stage] = packet

    def complete(self, *args, **kwargs):
        self.capture_policy_packet()
        if self.state()["stage"] == "commit" and not self.rejected_old_primary:
            self.rejected_old_primary = True
            before = self.authoritative_snapshot("steps/S1.md")
            stale = self.receipt("S1")["iteration"]["previous_sha"]
            rejected, _ = super().complete(
                {"summary": "An earlier commit cannot substitute for this iteration's primary.",
                 "commit": stale}, code=2, label="policy-stale-primary",
            )
            self.assertIn("commit", rejected.stderr.lower())
            self.assert_authority_unchanged(before, "steps/S1.md")
        return super().complete(*args, **kwargs)

    def test_real_walk_keeps_one_frozen_policy_and_rejects_drift_before_mutation(self) -> None:
        self.bootstrap_to_first_implementation()
        initial = self.state()
        snapshot = self.run_dir / policy.RUN_FILE
        binding = policy.validate_binding(initial)
        self.assertIsNotNone(binding)
        assert binding is not None
        body = snapshot.read_text(encoding="utf-8")
        self.assertEqual(
            binding["sha256"], hashlib.sha256(body.encode("utf-8")).hexdigest()
        )
        self.assertEqual(policy.bound_path(self.run_dir, initial), snapshot)

        # This fixture option exercises the stale implementation receipt path.
        self.start_step("S1", exercise_failed_and_stale=True)
        self.assertEqual(self.state()["stage"], "review")
        before_blocked = self.authoritative_snapshot("steps/S1.md")
        blocked_result = self.record("policy-missing-done", {"summary": "blocked"})
        snapshot.unlink()
        blocked = self.cli(
            "done", "--action", self.action_id(), "--result", blocked_result, code=2
        )
        self.assertIn("Blocked: Improve policy", blocked.stdout)
        self.assert_authority_unchanged(before_blocked, "steps/S1.md")
        blocked = self.cli("next", code=2)
        self.assertIn("Blocked: Improve policy", blocked.stdout)
        self.assertIn("No completion callback is valid", blocked.stdout)
        self.assert_authority_unchanged(before_blocked, "steps/S1.md")

        snapshot.write_text(body + "\nTampered after initialization.\n", encoding="utf-8")
        blocked = self.cli(
            "done", "--action", self.action_id(), "--result", blocked_result, code=2
        )
        self.assertIn("Blocked: Improve policy", blocked.stdout)
        status = self.cli("status")
        self.assertIn("Blocked: Improve policy", status.stdout)
        self.assert_authority_unchanged(before_blocked, "steps/S1.md")
        self.cli("pause", "--reason", "Restore the frozen Improve policy snapshot.")
        snapshot.write_text(body, encoding="utf-8")
        self.cli("resume")
        self.assertEqual(self.state()["stage"], "review")

        # The first completion also probes rejection of an older primary SHA.
        # Each no-change cycle still records its own valid audit commit.
        self.run_improve_iteration("S1", material=False)
        self.run_improve_iteration("S1", material=True)
        self.run_improve_iteration("S1", material=False)
        self.run_improve_iteration("S1", material=False)
        receipt = self.receipt("S1")
        self.assertEqual(
            [row["outcome"] for row in receipt["improve_cycles"]],
            ["trivial", "material", "trivial", "trivial"],
        )
        self.assertEqual(self.state()["stage"], "final-verify")

        final_action = self.action_id()
        self.assertFalse((self.run_dir / "checks" / f"{final_action}.md").exists())
        before_final = self.authoritative_snapshot("steps/S1.md")
        rejected, _ = self.complete(
            {
                "summary": "A final result cannot replace the required fresh final check.",
                "done_evidence": self.done_evidence("S1"),
            },
            action_id=final_action,
            code=2,
            label="policy-missing-final-check",
        )
        self.assertIn(f"checks/{final_action}.md", rejected.stderr)
        self.assert_authority_unchanged(before_final, "steps/S1.md")

        self.verify_current(self.manifest_for("S1"), label="policy-final-checks")
        worktree = self.worktree("S1")
        source = worktree / "s1.py"
        original = source.read_text(encoding="utf-8")
        source.write_text(original + "# unreviewed transient change\n", encoding="utf-8")
        rejected, _ = self.complete(
            {
                "summary": "A stale final receipt cannot certify a changed worktree.",
                "done_evidence": self.done_evidence("S1"),
            },
            action_id=final_action,
            code=2,
            label="policy-stale-final-check",
        )
        self.assertIn("uncommitted", rejected.stderr)
        source.write_text(original, encoding="utf-8")
        self.assertEqual(self.git("status", "--porcelain", cwd=worktree), "")
        self.complete(
            {
                "summary": "Fresh final checks passed after the two required trivial passes.",
                "done_evidence": self.done_evidence("S1"),
            },
            action_id=final_action,
            label="policy-final-verify",
        )
        self.assertEqual(self.state()["stage"], "post-inner")
        self.converge_objective(
            {
                "summary": "No broader dependency or test strategy change is needed.",
                "plan_decision": "no-change",
                "plan_reason": "The frozen policy supplements the product loop without changing this fixture's dependency plan.",
                "journal": [],
            },
            label="policy-post-inner",
        )
        self.assertEqual(self.state()["stage"], "merge")
        self.complete(
            {"summary": "Merge the converged policy-bound step into the session checkout."},
            label="policy-merge",
        )
        self.assertEqual(set(self.policy_packets), set(policy.PRODUCT_STAGES))
        self.assertTrue(self.rejected_old_primary)
        self.assertFalse((self.repo / ".until-loop").exists())
        self.assertFalse((self.run_dir / ".until-loop").exists())
        self.assertFalse((self.run_dir / "state.json").exists())

        before_resume = self.authoritative_snapshot("steps/S1.md")
        before_policy = snapshot.read_bytes()
        self.cli("init", "--repo", str(self.repo), "--prompt", "resume fixture")
        self.assert_authority_unchanged(before_resume, "steps/S1.md")
        self.assertEqual(snapshot.read_bytes(), before_policy)

        # Terminal recovery remains available even if a later non-product
        # packet cannot use the policy snapshot.
        snapshot.write_text(body + "\nTampered after the product walk.\n", encoding="utf-8")
        self.cli("halt", "--reason", "End the fixture after policy-drift coverage.")
        self.assertEqual(self.state()["stage"], "halted")


class ImprovePolicyPackagingTests(unittest.TestCase):
    def test_mismatched_upstream_is_refused_before_the_vendored_copy_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-improve-upstream-") as raw:
            upstream = Path(raw) / "Improve"
            source = upstream / "references" / "review-policy.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "# Improve review policy\n\n"
                f"Policy ID: {policy.POLICY_ID}\n\n"
                "Unreviewed upstream bytes.\n",
                encoding="utf-8",
            )
            destination = REFS / policy.SOURCE_FILE
            before = destination.read_bytes()
            result = subprocess.run(
                [sys.executable, str(SYNC), "--source", str(upstream), "--write"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("Improve policy sync blocked", result.stderr)
            self.assertEqual(destination.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
