#!/usr/bin/env python3
"""Regression coverage for explicit recovery of an unlanded merge intent."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_store as store  # noqa: E402


def load_core():
    loader = importlib.machinery.SourceFileLoader("shiploop_merge_recovery_core", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("could not load ShipLoop core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


CORE = load_core()


class MergeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-merge-recovery-")
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        self.git("init", "-q")
        self.git("config", "user.name", "ShipLoop Merge Recovery")
        self.git("config", "user.email", "shiploop-merge-recovery@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        (self.repo / "shared.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "shared.txt")
        self.git("commit", "-m", "baseline")
        self.run_dir = self.repo / ".shiploop"
        self.cli("init", "--repo", str(self.repo), "--prompt", "Recover one merge")
        self.install_merge_fixture()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, cwd=None, code=0):
        process = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process.stdout.strip()

    def cli(self, *args, code=0):
        process = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process

    def state(self):
        return store.read_record(self.run_dir / "state.md")

    def receipt(self):
        return store.read_record(self.run_dir / "steps" / "S1.md")

    def durable_snapshot(self):
        paths = [
            self.run_dir / "state.md",
            self.run_dir / "steps" / "S1.md",
            self.run_dir / "history.md",
            self.run_dir
            / "merge-recoveries"
            / f"{self.state()['action']['id']}.md",
        ]
        return {
            str(path.relative_to(self.run_dir)): (
                path.read_bytes() if path.is_file() else None
            )
            for path in paths
        }

    def install_merge_fixture(self):
        state = self.state()
        base = self.git("rev-parse", "HEAD")
        run_id = state["run_id"]
        branch = f"shiploop/{run_id}/S1"
        worktree = (
            Path(state["repo_root"]) / ".worktrees" / "shiploop" / run_id / "S1"
        )
        worktree.parent.mkdir(parents=True)
        self.git("worktree", "add", "-b", branch, str(worktree), base)
        (worktree / "shared.txt").write_text("step branch\n", encoding="utf-8")
        self.git("add", "shared.txt", cwd=worktree)
        self.git("commit", "-m", "step output", cwd=worktree)
        target = self.git("rev-parse", "HEAD", cwd=worktree)

        self.contract_integration_ready = {
            "envelope": {
                "version": 1,
                "phase": "merge",
                "contract_sha256": "a" * 64,
                "verify_action": f"{run_id}-final-verify",
                "head": target,
                "environment_identity": "b" * 64,
                "artifact_identity": "c" * 64,
            },
            "validated_receipt": {
                "discharged": {
                    "done": ["D-001"],
                    "tests": ["T-001"],
                    "documentation": ["DOC-001"],
                },
                "status": "done-evidence-certified",
                "all_required_done_discharged": True,
                "integration_assertion_required": True,
                "fully_closed": False,
            },
        }

        (self.repo / "shared.txt").write_text("session change\n", encoding="utf-8")
        self.git("add", "shared.txt")
        self.git("commit", "-m", "independent session change")

        state.update(
            phase="implement",
            stage="merge",
            active_step="S1",
            action={"id": f"{run_id}-merge-recover", "stage": "merge"},
        )
        receipt = {
            "id": "S1",
            "run_id": run_id,
            "status": "running",
            "branch": branch,
            "worktree": str(worktree),
            "base_sha": base,
            "merge_target": target,
            "final_head": target,
            "contract_integration_ready": self.contract_integration_ready,
            "improve_cycles": [],
            "iteration": {"id": f"{run_id}-S1-I1", "previous_sha": target},
        }
        store.write_record(self.run_dir / "steps" / "S1.md", receipt)
        store.write_record(self.run_dir / "state.md", state)

    def test_requires_explicit_git_reconciliation_then_restarts_review(self):
        action = self.state()["action"]["id"]
        self.git("merge", "--no-ff", "--no-edit", self.receipt()["branch"], code=1)
        state_before = (self.run_dir / "state.md").read_bytes()

        blocked = self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "A merge conflict must be explicitly aborted before the step can be repaired.",
            code=2,
        )
        self.assertIn("Git merge is in progress", blocked.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before)

        self.git("merge", "--abort")
        ordinary_repair = self.cli(
            "repair",
            "--action",
            action,
            "--reason",
            "Ordinary repair must remain unavailable after merge intent.",
            code=2,
        )
        self.assertIn("merge already started", ordinary_repair.stderr)
        recovered = self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "The explicitly aborted merge must restart the material review cycle.",
        )
        self.assertIn("Stage: review", recovered.stdout)
        state = self.state()
        receipt = self.receipt()
        self.assertEqual((state["phase"], state["stage"], state["active_step"]), ("implement", "review", "S1"))
        self.assertNotIn("merge_target", receipt)
        self.assertEqual(receipt["branch"], f"shiploop/{state['run_id']}/S1")
        self.assertTrue(Path(receipt["worktree"]).is_dir())
        self.assertEqual(receipt["improve_cycles"][-1]["kind"], "merge-recovery-checkpoint")
        self.assertEqual(receipt["improve_cycles"][-1]["outcome"], "material")
        recovery = store.read_record(self.run_dir / "merge-recoveries" / f"{action}.md")
        self.assertEqual(recovery["merge_target"], self.git("rev-parse", receipt["branch"]))
        self.assertEqual(
            receipt["last_merge_recovery"]["contract_integration_ready"],
            self.contract_integration_ready,
        )
        self.assertEqual(
            recovery["contract_integration_ready"], self.contract_integration_ready
        )
        self.assertNotIn("contract_integration_ready", receipt)
        history = store.read_record(self.run_dir / "history.md")
        self.assertEqual(history[-1]["event"], "merge-recover")

    def test_stale_action_preserves_the_durable_snapshot(self):
        snapshot = self.durable_snapshot()
        blocked = self.cli(
            "merge-recover",
            "--action",
            "stale-action",
            "--reason",
            "A stale callback must not rewrite the merge intent.",
            code=2,
        )
        self.assertIn("stale action ID", blocked.stderr)
        self.assertEqual(self.durable_snapshot(), snapshot)

    def test_dirty_session_preserves_the_durable_snapshot(self):
        (self.repo / "session-uncommitted.txt").write_text(
            "operator work\n", encoding="utf-8"
        )
        action = self.state()["action"]["id"]
        snapshot = self.durable_snapshot()
        blocked = self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "The session checkout must be clean before recovery.",
            code=2,
        )
        self.assertIn("session checkout has changes", blocked.stderr)
        self.assertEqual(self.durable_snapshot(), snapshot)

    def test_dirty_worktree_preserves_the_durable_snapshot(self):
        receipt = self.receipt()
        (Path(receipt["worktree"]) / "worktree-uncommitted.txt").write_text(
            "operator work\n", encoding="utf-8"
        )
        action = self.state()["action"]["id"]
        snapshot = self.durable_snapshot()
        blocked = self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "The active worktree must be clean before recovery.",
            code=2,
        )
        self.assertIn("worktree changed after merge intent", blocked.stderr)
        self.assertEqual(self.durable_snapshot(), snapshot)

    def test_paused_merge_recovery_keeps_the_pause_and_prints_no_callback(self):
        pause_reason = "Await explicit operator direction before another review pass."
        self.cli("pause", "--reason", pause_reason)
        action = self.state()["action"]["id"]

        recovered = self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "The clean, unlanded merge intent needs another material review pass.",
        )

        state = self.state()
        self.assertEqual(state["stage"], "review")
        self.assertEqual(state["paused"], pause_reason)
        self.assertIn("No completion callback is valid while paused.", recovered.stdout)
        self.assertNotIn("Call this when done:", recovered.stdout)

    def test_refuses_an_already_integrated_target(self):
        action = self.state()["action"]["id"]
        target = self.receipt()["merge_target"]
        self.git("reset", "--hard", target)
        blocked = self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "An integrated target must not be restarted as unlanded work.",
            code=2,
        )
        self.assertIn("already integrated", blocked.stderr)
        self.assertIn("merge_target", self.receipt())

    def test_accepts_an_explicitly_reconciled_descendant_branch(self):
        action = self.state()["action"]["id"]
        receipt = self.receipt()
        session_head = self.git("rev-parse", "HEAD")
        self.git("merge", "--no-ff", "--no-edit", session_head, cwd=Path(receipt["worktree"]), code=1)
        (Path(receipt["worktree"]) / "shared.txt").write_text(
            "reconciled by operator\n", encoding="utf-8"
        )
        self.git("add", "shared.txt", cwd=Path(receipt["worktree"]))
        self.git("commit", "-m", "reconcile session baseline", cwd=Path(receipt["worktree"]))
        branch_head = self.git("rev-parse", "HEAD", cwd=Path(receipt["worktree"]))
        self.assertNotEqual(branch_head, receipt["merge_target"])

        self.cli(
            "merge-recover",
            "--action",
            action,
            "--reason",
            "The operator reconciled the session baseline before restarting review.",
        )
        recovered = self.receipt()
        self.assertEqual(recovered["last_merge_recovery"]["branch_head"], branch_head)
        self.assertEqual(recovered["improve_cycles"][-1]["outcome"], "material")


if __name__ == "__main__":
    unittest.main()
