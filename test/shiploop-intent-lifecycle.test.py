#!/usr/bin/env python3
"""Run-level spec binding, current-consumer selection, and refusal coverage."""

from __future__ import annotations

import difflib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "test"))

import shiploop_current_spec as current_spec  # noqa: E402
import shiploop_expectations as expectations  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_primary as primary  # noqa: E402
import shiploop_store as store  # noqa: E402


COMMITTED_SPEC = (
    "# Product\n\n## Requirements\n\n### R-1. Existing behavior\nCommitted baseline.\n"
).encode("utf-8")
DIRTY_SPEC = (
    "# Product\r\n\r\n## Requirements\r\n\r\n### R-1. Existing behavior\r\n"
    "Retain the in-progress behavior. Café stays exact.\r\n"
).encode("utf-8")
CURRENT_SPEC = DIRTY_SPEC + (
    "\r\n### R-2. Requested addition\r\nAdd the incoming outcome.\r\n"
).encode("utf-8")
COMMITTED_ARCHITECTURE = b"# Architecture\n\nAD-1: committed direction\n"
DIRTY_ARCHITECTURE = "# Architecture\r\n\r\nAD-1: dirty direction\r\n"
COMMITTED_ENVIRONMENT = b"# Environment\n\nCommands: old\n"
DIRTY_ENVIRONMENT = "# Environment\r\n\r\nCommands: updated locally\r\n"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout


def tree_bytes(root: Path) -> dict[str, bytes]:
    """The run's files except lock contents, which the CLI opens for each command."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file() and path.name != ".lock"}


class IntentLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.git_environment = mock.patch.dict(
            os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        )
        self.git_environment.start()
        self.addCleanup(self.git_environment.stop)
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-intent-lifecycle-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.repo = self.make_repo(self.base / "repo")
        self.run = self.base / "run"
        self.run.mkdir()
        self.state = self.create_saved_run(self.repo, self.run)

    @staticmethod
    def make_repo(repo: Path) -> Path:
        home = repo / knowledge.HOME
        home.mkdir(parents=True)
        (home / "spec.md").write_bytes(COMMITTED_SPEC)
        (home / "architecture.md").write_bytes(COMMITTED_ARCHITECTURE)
        (home / "environment.md").write_bytes(COMMITTED_ENVIRONMENT)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "intent-lifecycle@example.invalid")
        git(repo, "config", "user.name", "ShipLoop lifecycle test")
        git(repo, "config", "commit.gpgsign", "false")
        git(repo, "add", "docs/shiploop")
        git(repo, "commit", "-qm", "committed aggregate baseline")
        (home / "spec.md").write_bytes(DIRTY_SPEC)
        (home / "architecture.md").write_text(DIRTY_ARCHITECTURE, encoding="utf-8")
        (home / "environment.md").write_text(DIRTY_ENVIRONMENT, encoding="utf-8")
        return repo

    @staticmethod
    def create_saved_run(repo: Path, run: Path) -> dict:
        state = navigator.new_state(str(repo.resolve()), "Keep prior intent and add R-2.")
        navigator.save(run, state)
        return store.read_record(run / "state.md")

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(CLI), *args], cwd=self.repo,
                              capture_output=True, text=True, timeout=45)

    def cli_init(self, run: Path) -> subprocess.CompletedProcess[str]:
        run.mkdir()
        return self.cli("init", "--repo", str(self.repo), "--run-dir", str(run),
                        "--prompt=Keep existing intent and add the requested outcome.")

    def test_first_save_binds_exact_dirty_prior_bytes_and_candidate(self) -> None:
        spec_file = self.repo / knowledge.HOME / "spec.md"
        architecture_file = self.repo / knowledge.HOME / "architecture.md"
        environment_file = self.repo / knowledge.HOME / "environment.md"

        self.assertEqual(self.state["spec_root"], str(self.run.resolve()))
        self.assertEqual(current_spec.path(self.state).read_bytes(), DIRTY_SPEC)
        self.assertEqual(current_spec.prior_text(self.state).encode("utf-8"), DIRTY_SPEC)
        self.assertEqual(current_spec.prior_snapshot(self.state, "architecture"), DIRTY_ARCHITECTURE)
        self.assertEqual(current_spec.prior_snapshot(self.state, "environment"), DIRTY_ENVIRONMENT)
        self.assertEqual(spec_file.read_bytes(), DIRTY_SPEC)
        self.assertEqual(architecture_file.read_bytes().decode("utf-8"), DIRTY_ARCHITECTURE)
        self.assertEqual(environment_file.read_bytes().decode("utf-8"), DIRTY_ENVIRONMENT)
        current_spec.assert_binding(self.run, self.state)

        current_spec.path(self.state).write_bytes(CURRENT_SPEC)
        navigator.save(self.run, self.state)

        self.assertEqual(current_spec.path(self.state).read_bytes(), CURRENT_SPEC)
        self.assertEqual(spec_file.read_bytes(), DIRTY_SPEC)

    def test_current_spec_parsers_and_primary_step_plan_gates_ignore_stale_aggregate(self) -> None:
        candidate = current_spec.path(self.state)
        candidate.write_bytes(CURRENT_SPEC)
        navigator.save(self.run, self.state)
        state = store.read_record(self.run / "state.md")

        current_entries = knowledge.entries(state, "spec.md")
        aggregate_entries = knowledge.entries(self.repo, "spec.md")
        self.assertEqual(set(current_entries), {"R-1", "R-2"})
        self.assertEqual(set(aggregate_entries), {"R-1"})
        hint = expectations.requirement_ids_text(state, "stale aggregate label")
        self.assertIn(str(candidate), hint)
        self.assertIn("R-2", hint)
        primary.check_spec(state, "spec", {"outcome": "done", "primary": ["R-2"]})

        state["accepted"]["SpecAccepted"] = {"outcome": "done", "primary": ["R-2"]}
        state["history"].append({"action": "SpecAccepted", "stage": "spec", "workitem": None, "outcome": "done"})
        primary.check_queue(state, "plan", {
            "outcome": "done", "work_items": [{"id": "W1", "title": "new requirement", "follows": ["R-2"]}],
        })

        step_plan = {
            "outcome": "done",
            "steps": [{"id": "S1"}],
            "criteria": [{"id": "C1", "text": "Implement the requested R-2 outcome."}],
            "test_commands": [{"suite": "focused", "ids": ["test-new-outcome"], "criteria": ["C1"]}],
        }
        state["work_items"] = [{"id": "W1", "title": "new requirement"}]
        state["work_index"] = 0
        state["accepted"]["StepPlanAccepted"] = step_plan
        state["history"].append({"action": "StepPlanAccepted", "stage": "step-plan",
                                 "workitem": "W1", "outcome": "done"})
        skeleton = expectations.case_skeleton(state)
        self.assertEqual(skeleton[0]["requirement"], "R-2")
        case = {"id": "test-new-outcome", "criterion": "C1", "requirement": "R-2",
                "oracle": "requested behavior appears", "red": "fails before implementation",
                "green": "passes after implementation"}
        self.assertIsNone(expectations.check_test_cases(self.run, state, {"test_cases": [case]}))

    def test_diff_uses_dirty_start_snapshot_not_git_head(self) -> None:
        self.assertEqual(knowledge.spec_diff(self.run, self.state), "")
        current_spec.path(self.state).write_bytes(CURRENT_SPEC)

        actual = knowledge.spec_diff(self.run, self.state)
        expected = "diff --git a/RUN/current-spec.md b/RUN/current-spec.md\n" + "".join(
            difflib.unified_diff(DIRTY_SPEC.decode("utf-8").splitlines(keepends=True),
                                 CURRENT_SPEC.decode("utf-8").splitlines(keepends=True),
                                 fromfile="prior/spec.md", tofile="RUN/current-spec.md")
        )
        self.assertEqual(actual, expected)
        self.assertNotIn("Committed baseline", actual)

    def test_accepted_step_baseline_survives_candidate_edits_and_ordinary_saves(self) -> None:
        action = "PlanAccepted"
        writes = current_spec.step_snapshot_writes(self.state, action)
        store.transaction(self.run, writes)

        current_spec.path(self.state).write_bytes(CURRENT_SPEC)
        navigator.save(self.run, self.state)
        state = store.read_record(self.run / "state.md")
        state["revision"] += 1
        current_spec.path(state).write_bytes(CURRENT_SPEC + b"\r\n### R-3. Later\r\nLater edit.\r\n")
        navigator.save(self.run, state)

        self.assertEqual(current_spec.step_baseline(state, action).encode("utf-8"), DIRTY_SPEC)
        self.assertEqual(current_spec.step_snapshot_writes(state, action), {})
        self.assertEqual((self.repo / knowledge.HOME / "spec.md").read_bytes(), DIRTY_SPEC)

    def test_pure_snapshot_attaches_only_its_existing_run_binding_without_reseeding(self) -> None:
        from copy import deepcopy
        unbound = deepcopy(self.state)
        unbound["spec_root"] = ""
        current_spec.path(self.state).write_bytes(CURRENT_SPEC)
        navigator.save(self.run, unbound)
        self.assertEqual(unbound["spec_root"], str(self.run.resolve()))
        self.assertEqual(current_spec.path(unbound).read_bytes(), CURRENT_SPEC)
        self.assertEqual(current_spec.prior_text(unbound).encode("utf-8"), DIRTY_SPEC)
        before = tree_bytes(self.run)
        other = navigator.new_state(str(self.repo.resolve()), "A separate request.")
        with self.assertRaisesRegex(navigator.NavigatorError, "refusing to reseed"):
            navigator.save(self.run, other)
        self.assertEqual(tree_bytes(self.run), before)

    def test_ids_first_accepted_in_this_run_survive_later_candidate_edits(self) -> None:
        # A trusted synthetic accepted event exercises the snapshot mechanism;
        # this unit does not assert a model authored or reviewed product intent.
        current_spec.path(self.state).write_bytes(CURRENT_SPEC)
        action = navigator.current_action(self.state)["id"]
        after = navigator.apply(self.state, action, {"outcome": "done", "summary": "Synthetic accepted event."})
        navigator.save(self.run, after)
        self.assertEqual(current_spec.accepted_text(after).encode("utf-8"), CURRENT_SPEC)
        current_spec.path(after).write_bytes(DIRTY_SPEC)
        self.assertIn("R-2", knowledge.check(after, "plan"))
        # An edit alone and an ordinary save never bless that removal.
        navigator.save(self.run, after)
        self.assertEqual(current_spec.accepted_text(after).encode("utf-8"), CURRENT_SPEC)

    def test_cli_refuses_v11_state_without_mutating_saved_artifacts(self) -> None:
        run = self.base / "v11-run"
        initialized = self.cli_init(run)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        state = store.read_record(run / "state.md")
        self.assertEqual(state["spec_root"], str(run.resolve()))
        state["version"] = 11
        state.pop("spec_root")
        store.atomic_write_text(run / "state.md", store.dumps(state, "ShipLoop navigator state"))
        before = tree_bytes(run)
        prior_spec = (self.repo / knowledge.HOME / "spec.md").read_bytes()

        refused = self.cli("next", "--run-dir", str(run))

        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("prior intent cannot be reconstructed safely", refused.stderr)
        self.assertEqual(tree_bytes(run), before)
        self.assertEqual((self.repo / knowledge.HOME / "spec.md").read_bytes(), prior_spec)

    def test_cli_refuses_missing_candidate_without_reseeding_or_mutation(self) -> None:
        run = self.base / "missing-candidate-run"
        initialized = self.cli_init(run)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        candidate = run / current_spec.CANDIDATE
        prior_spec = (self.repo / knowledge.HOME / "spec.md").read_bytes()
        candidate.unlink()
        before = tree_bytes(run)

        refused = self.cli("next", "--run-dir", str(run))

        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn(current_spec.CANDIDATE, refused.stderr)
        self.assertEqual(tree_bytes(run), before)
        self.assertFalse(candidate.exists())
        self.assertEqual((self.repo / knowledge.HOME / "spec.md").read_bytes(), prior_spec)


if __name__ == "__main__":
    unittest.main()
