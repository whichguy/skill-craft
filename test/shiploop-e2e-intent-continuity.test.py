#!/usr/bin/env python3
"""Fail-first calibration for the independent intent-continuity oracle."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "test" / "shiploop_e2e" / "checks" / "intent_continuity.py"
CASES = ROOT / "test" / "shiploop_e2e" / "cases.json"
LOG_DIR = os.environ.get("SHIPLOOP_INTENT_ORACLE_LOG_DIR")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "--all"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", message], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return git(repo, "rev-parse", "HEAD")


def tree(repo: Path, head: str) -> str:
    return git(repo, "rev-parse", f"{head}^{{tree}}")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, raw: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if isinstance(raw, bytes) else raw.encode("utf-8"))


def capture_runtime_baseline(work: Path) -> dict[str, Any]:
    producer = ROOT / "test" / "shiploop_e2e" / "improve_runtime.py"
    spec = importlib.util.spec_from_file_location("fixture_improve_runtime", producer)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Improve runtime baseline producer is unavailable: {producer}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.capture_baseline(work)


def fenced(payload: dict[str, Any]) -> str:
    return "# Fixture record\n\n```shiploop-state\n" + json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n```\n"


def source_fingerprint(head: str, working_tree: str) -> dict[str, Any]:
    return {"head": head, "working_tree": working_tree, "tracked_tree": working_tree}


def return_receipt(head: str, result_tree: str, before: dict[str, Any],
                   *, previous: dict[str, Any] | None = None,
                   kind: str = "fast-forward-merge") -> dict[str, Any]:
    tree_key = "tree" if kind == "fast-forward-merge" else "working_tree"
    receipt = {
        "schema": "shiploop-workspace-return-receipt",
        "version": 1,
        "status": "returned",
        "kind": kind,
        "source_before": before,
        "expected_source": {"head": head, tree_key: result_tree, "branch": "main"},
        "source_extra_paths": [],
    }
    if previous is not None:
        receipt["previous_receipt"] = previous
    return receipt


class Fixture:
    """A small real Git history with the current-spec records the oracle reads."""

    def __init__(self, root: Path, mode: str, *, follow_on: bool,
                 early_promotion: bool = False, single_return: bool = False,
                 empty_follow_up: bool = False,
                 candidate: bytes | None = None, final_kind: str = "fast-forward-merge",
                 state_version: int = 12, capture_runtime_baseline_before_init: bool = False,
                 prepared_runtime_root: bool = False, ancestor_git_before_product: bool = False):
        self.root = root.resolve()
        self.mode = mode
        self.state_version = state_version
        self.output = self.root
        self.output.mkdir(parents=True)
        if ancestor_git_before_product:
            subprocess.run(["git", "-C", str(self.output), "init", "--quiet", "--initial-branch=main"], check=True)
            git(self.output, "config", "user.name", "Intent Ancestor")
            git(self.output, "config", "user.email", "ancestor@example.invalid")
            write(self.output / "ancestor-context.txt", "Ancestor repository context.\n")
            commit(self.output, "ancestor baseline")
        self.product = self.output / "product"
        self.product.mkdir()
        self.improve_runtime_baseline = None
        if prepared_runtime_root:
            (self.product / ".shiploop-improve").mkdir()
        if capture_runtime_baseline_before_init:
            self.improve_runtime_baseline = capture_runtime_baseline(self.product)
        subprocess.run(["git", "-C", str(self.product), "init", "--quiet", "--initial-branch=main"], check=True)
        git(self.product, "config", "user.name", "Intent Fixture")
        git(self.product, "config", "user.email", "intent@example.invalid")
        write(self.product / "README.md", "Intent continuity fixture.\n")

        self.prior = {
            "spec": b"# Earlier spec\n\nR-1: preserve the old result.\n",
            "architecture": b"# Earlier architecture\n\nAD-1: stable boundary.\n",
            "environment": b"# Earlier environment\n\nPython 3.\n",
        } if follow_on else {"spec": None, "architecture": None, "environment": None}
        for name, (source, _snapshot) in self._snapshot_paths().items():
            raw = self.prior[name]
            if raw is not None:
                write(self.product / source, raw)
        self.start_head = commit(self.product, "source baseline")
        self.start_tree = tree(self.product, self.start_head)

        self.candidate = candidate if candidate is not None else (
            b"# Current spec\n\nR-1: preserve the old result.\nR-2: add the accepted request.\n")
        no_change_return = (mode == "worktree" and single_return and final_kind == "no-change-return"
                            and self.candidate == self.prior["spec"])
        if mode == "worktree":
            if not no_change_return:
                write(self.product / "src/users.py", "# returned product change\n")
            if early_promotion or (single_return and not no_change_return):
                write(self.product / "docs/shiploop/spec.md", self.candidate)
        else:
            write(self.product / "docs/shiploop/spec.md", self.candidate)
        self.first_return_head = (self.start_head if no_change_return
                                  else commit(self.product, "return product change"))
        self.first_return_tree = tree(self.product, self.first_return_head)
        if mode == "worktree" and single_return:
            self.final_head = self.first_return_head
            self.final_tree = self.first_return_tree
        elif mode == "worktree" and empty_follow_up:
            self.final_head = self.first_return_head
            self.final_tree = self.first_return_tree
        elif mode == "worktree":
            if not early_promotion:
                write(self.product / "docs/shiploop/spec.md", self.candidate)
            write(self.product / "docs/shiploop/notes.md", "# Learning\n\nKeep the accepted intent.\n")
            if final_kind == "fast-forward-merge":
                self.final_head = commit(self.product, "ShipLoop knowledge follow-up")
                self.final_tree = tree(self.product, self.final_head)
            else:
                subprocess.run(["git", "-C", str(self.product), "add", "--all"], check=True)
                self.final_head = self.first_return_head
                self.final_tree = git(self.product, "write-tree")
        else:
            self.final_head = self.first_return_head
            self.final_tree = tree(self.product, self.final_head)

        if mode == "worktree":
            self.workspace = self.output / ".shiploop-runs" / "fixture"
            self.workspace.mkdir(parents=True)
            self.run = self.workspace / "run"
            self.worktree = self.workspace / "worktree"
            subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(self.product), str(self.worktree)], check=True)
            git(self.worktree, "config", "user.name", "Intent Fixture")
            git(self.worktree, "config", "user.email", "intent@example.invalid")
            write(self.workspace / "workspace.md", fenced({
                "schema": "shiploop-workspace", "version": 1, "status": "returned",
                "source_repo": str(self.product), "worktree": str(self.worktree), "run_dir": str(self.run),
                "initial_fingerprint": {"head": self.start_head, "working_tree": self.start_tree,
                                         "tracked_tree": self.start_tree, "branch": "main"},
            }))
            if single_return:
                self.receipt = return_receipt(
                    self.final_head, self.final_tree,
                    source_fingerprint(self.start_head, self.start_tree), kind=final_kind)
            else:
                prior_receipt = return_receipt(
                    self.first_return_head, self.first_return_tree,
                    source_fingerprint(self.start_head, self.start_tree))
                self.receipt = return_receipt(
                    self.final_head, self.final_tree,
                    prior_receipt["expected_source"], previous=prior_receipt, kind=final_kind)
            # A linked execution worktree already holds the candidate during this return.
            write(self.worktree / "docs/shiploop/spec.md", self.candidate)
            write(self.worktree / "docs/shiploop/notes.md", "# Learning\n\nKeep the accepted intent.\n")
            write(self.workspace / "return-receipt.md", fenced(self.receipt))
        else:
            self.workspace = None
            self.worktree = self.product
            self.run = self.output / "run"
            self.receipt = None

        self.run.mkdir(parents=True)
        write(self.output / "shiploop-run.json", json.dumps({"run_dir": str(self.run)}))
        invocation = {"case": "fixture", "cwd": str(self.product),
                      "follow_on": {"start_head": self.start_head} if follow_on else None}
        write(self.output / "invocation.json", json.dumps(invocation))
        write(self.output / "metrics.json", json.dumps({"fixture": True}))
        self._write_state()
        # result.json is intentionally absent: the host result may not yet have been written.

    @staticmethod
    def _snapshot_paths() -> dict[str, tuple[str, str]]:
        return {
            "spec": ("docs/shiploop/spec.md", "spec/prior-spec.md"),
            "architecture": ("docs/shiploop/architecture.md", "spec/prior-architecture.md"),
            "environment": ("docs/shiploop/environment.md", "spec/prior-environment.md"),
        }

    def _write_state(self) -> None:
        repo = self.worktree if self.mode == "worktree" else self.product
        snapshot_meta: dict[str, dict[str, Any]] = {}
        for name, (_source, snapshot) in self._snapshot_paths().items():
            raw = self.prior[name]
            snapshot_meta[name] = {"path": snapshot, "present": raw is not None,
                                   "sha256": sha(raw) if raw is not None else None}
            if self.state_version == 12 and raw is not None:
                write(self.run / snapshot, raw)
        run_id, improve, handoff = "fixture-run", "I-spec", "H-terminal"
        current_hash = sha(self.candidate)
        prior_spec = self.prior["spec"]
        prior_hash = sha(prior_spec) if prior_spec is not None else sha(b"")
        state = {
            "version": self.state_version, "run_id": run_id, "repo": str(repo),
            "status": "done",
            "accepted": {
                improve: {"outcome": "done", "summary": "Current spec accepted."},
                handoff: {"outcome": "done", "summary": "Terminal handoff accepted."},
            },
            "improve_results": {improve: {"runtime_phase": "complete"}},
            "history": [
                {"action": improve, "stage": "spec", "outcome": "done"},
                {"action": handoff, "stage": "handoff", "outcome": "done"},
            ],
        }
        if self.state_version == 12:
            state["spec_root"] = str(self.run)
            write(self.run / "current-spec.md", self.candidate)
        write(self.run / "state.md", fenced(state))
        if self.state_version == 11:
            return
        binding = {
            "schema": "shiploop-current-spec", "version": 1, "run_id": run_id,
            "repo": str(repo), "root": str(self.run), "candidate": "current-spec.md",
            "candidate_initial_sha256": prior_hash, "snapshots": snapshot_meta,
        }
        write(self.run / "spec/binding.md", fenced(binding))
        reviewed = {"schema": "shiploop-spec-reviewed-v1", "run_id": run_id, "repo": str(repo),
                    "root": str(self.run), "action": improve, "sha256": current_hash}
        write(self.run / "spec/reviewed.md", fenced(reviewed))
        promotion = {
            "schema": "shiploop-spec-promotion", "version": 1, "status": "promoted",
            "run_id": run_id, "repo": str(repo), "root": str(self.run),
            "handoff_action": handoff, "aggregate": "docs/shiploop/spec.md",
            "candidate": "current-spec.md", "candidate_sha256": current_hash,
            "current_sha256": current_hash, "prior_sha256": prior_hash,
            "prior_present": prior_spec is not None, "summary": "Exact reviewed candidate promoted.",
        }
        write(self.run / "spec/promotion.md", fenced(promotion))

class IntentContinuityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def fixture(self, mode: str, *, follow_on: bool = False, early_promotion: bool = False,
                single_return: bool = False, empty_follow_up: bool = False,
                candidate: bytes | None = None,
                final_kind: str = "fast-forward-merge", state_version: int = 12,
                capture_runtime_baseline_before_init: bool = False,
                prepared_runtime_root: bool = False, ancestor_git_before_product: bool = False) -> Fixture:
        return Fixture(self.root / ("case-" + str(len(list(self.root.iterdir())))), mode,
                       follow_on=follow_on, early_promotion=early_promotion,
                       single_return=single_return, empty_follow_up=empty_follow_up,
                       candidate=candidate, final_kind=final_kind, state_version=state_version,
                       capture_runtime_baseline_before_init=capture_runtime_baseline_before_init,
                       prepared_runtime_root=prepared_runtime_root,
                       ancestor_git_before_product=ancestor_git_before_product)

    def run_oracle(self, fixture: Fixture, mode: str, label: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run([sys.executable, str(ORACLE), "--mode", mode], cwd=fixture.product,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if LOG_DIR:
            destination = Path(LOG_DIR)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / (label + ".stdout.json")).write_text(proc.stdout, encoding="utf-8")
            (destination / (label + ".stderr.log")).write_text(proc.stderr, encoding="utf-8")
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"oracle did not emit JSON: {exc}; stdout={proc.stdout!r}; stderr={proc.stderr!r}")
        return proc.returncode, result

    def run_outcome(self, fixture: Fixture, mode: str, label: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run([sys.executable, str(ORACLE), "--mode", mode, "--assessment", "outcome"],
                              cwd=fixture.product, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, check=False)
        if LOG_DIR:
            destination = Path(LOG_DIR)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / (label + ".stdout.json")).write_text(proc.stdout, encoding="utf-8")
            (destination / (label + ".stderr.log")).write_text(proc.stderr, encoding="utf-8")
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"outcome assessment did not emit JSON: {exc}; stdout={proc.stdout!r}; stderr={proc.stderr!r}")
        return proc.returncode, result

    def assert_outcome(self, fixture: Fixture, mode: str, label: str, status: str) -> dict[str, Any]:
        code, result = self.run_outcome(fixture, mode, label)
        self.assertEqual(code, 0 if status == "PASS" else 1, result)
        self.assertEqual(result["machine_evidence_status"], status)
        self.assertEqual(result["semantic_outcome"], "UNKNOWN")
        return result

    def assert_rejected(self, fixture: Fixture, mode: str, label: str, message: str) -> None:
        code, result = self.run_oracle(fixture, mode, label)
        self.assertEqual(code, 1, result)
        self.assertFalse(result["pass"])
        combined = json.dumps(result)
        self.assertIn(message, combined)

    def test_reference_good_direct_new_root_passes_without_result_json(self) -> None:
        fixture = self.fixture("direct")
        code, result = self.run_oracle(fixture, "direct", "direct-good")
        self.assertEqual(code, 0, result)
        self.assertTrue(result["pass"])
        self.assertFalse((fixture.output / "result.json").exists())
        self.assertTrue(any(finding["check"] == "direct-execution" for finding in result["findings"]))

    def test_reference_good_worktree_follow_on_observes_knowledge_only_final_return(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        code, result = self.run_oracle(fixture, "worktree", "worktree-good")
        self.assertEqual(code, 0, result)
        self.assertTrue(result["pass"])
        self.assertFalse((fixture.output / "result.json").exists())
        finding = next(item for item in result["findings"] if item["check"] == "worktree-return-chain")
        self.assertEqual(finding["observed"]["receipts"], 2)
        self.assertEqual(finding["observed"]["follow_up_paths"],
                         ["docs/shiploop/notes.md", "docs/shiploop/spec.md"])

    def test_outcome_accepts_v11_with_one_final_return_and_no_v12_records(self) -> None:
        fixture = self.fixture("worktree", follow_on=True, single_return=True, state_version=11)
        invocation_path = fixture.output / "invocation.json"
        invocation = json.loads(invocation_path.read_text())
        invocation["follow_on"] = None
        invocation["seeded"] = {"start_head": fixture.start_head}
        write(invocation_path, json.dumps(invocation))
        self.assertFalse((fixture.run / "spec/binding.md").exists())
        self.assertFalse((fixture.run / "current-spec.md").exists())
        result = self.assert_outcome(fixture, "worktree", "outcome-v11-final-only", "PASS")
        self.assertEqual(result["diagnostics"]["review_scope"]["state_version"], 11)
        self.assertEqual(len(result["diagnostics"]["returns"]), 1)
        comparison = result["diagnostics"]["final_aggregate_comparison"]
        self.assertEqual(comparison["current_spec_comparison_status"], "UNKNOWN")
        self.assertIsNone(comparison["matches_current_spec"])
        self.assertEqual(comparison["diagnostic_diff_paths"], [])

    def test_outcome_accepts_valid_v12_return_chain(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        invocation_path = fixture.output / "invocation.json"
        invocation = json.loads(invocation_path.read_text())
        invocation["follow_on"] = None
        invocation["base"] = {"start_head": fixture.start_head}
        write(invocation_path, json.dumps(invocation))
        self.assertFalse((fixture.output / "result.json").exists())
        result = self.assert_outcome(fixture, "worktree", "outcome-v12-valid", "PASS")
        self.assertEqual(result["diagnostics"]["prior_source"], "invocation start_head")
        self.assertEqual(result["diagnostics"]["review_scope"]["review"]["action"], "I-spec")
        comparison = result["diagnostics"]["final_aggregate_comparison"]
        self.assertTrue(comparison["matches_reviewed"])
        self.assertEqual(comparison["current_spec_comparison_status"], "MATCH")

    def test_outcome_reports_later_final_status_amendment_as_diagnostic(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        amended = fixture.candidate + b"\nVerification completed after the reviewed candidate.\n"
        write(fixture.run / "current-spec.md", amended)
        write(fixture.product / "docs/shiploop/spec.md", amended)
        final_head = commit(fixture.product, "record truthful final status")
        final_tree = tree(fixture.product, final_head)
        assert fixture.receipt is not None
        fixture.receipt["expected_source"] = {"head": final_head, "tree": final_tree, "branch": "main"}
        write(fixture.workspace / "return-receipt.md", fenced(fixture.receipt))
        result = self.assert_outcome(fixture, "worktree", "outcome-final-amendment", "PASS")
        comparison = result["diagnostics"]["final_aggregate_comparison"]
        self.assertTrue(comparison["matches_current_spec"])
        self.assertFalse(comparison["matches_reviewed"])
        self.assertFalse(comparison["matches_promotion"])
        self.assertEqual(comparison["diagnostic_diff_paths"], ["docs/shiploop/spec.md"])
        self.assertEqual(result["diagnostics"]["review_scope"]["review"]["as_of"],
                         "accepted current-spec bytes at the reviewed Improve")

    def test_outcome_rejects_foreign_state_repo_binding(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        state_path = fixture.run / "state.md"
        state = json.loads(state_path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        state["repo"] = str(fixture.product)
        write(state_path, fenced(state))
        self.assert_outcome(fixture, "worktree", "outcome-foreign-state-repo", "FAIL")

    def test_outcome_rejects_declared_false_v12_binding(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        path = fixture.run / "spec/binding.md"
        binding = json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        binding["repo"] = str(fixture.product)
        write(path, fenced(binding))
        self.assert_outcome(fixture, "worktree", "outcome-false-v12-binding", "FAIL")

    def test_outcome_rejects_early_return_that_changes_prior_aggregate(self) -> None:
        fixture = self.fixture("worktree", follow_on=True, early_promotion=True)
        self.assert_outcome(fixture, "worktree", "outcome-early-prior-change", "FAIL")

    def test_outcome_rejects_final_receipt_tree_not_delivered_tree(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        assert fixture.receipt is not None
        fixture.receipt["expected_source"]["tree"] = fixture.first_return_tree
        write(fixture.workspace / "return-receipt.md", fenced(fixture.receipt))
        self.assert_outcome(fixture, "worktree", "outcome-final-tree-mismatch", "FAIL")

    def test_outcome_unknown_when_worktree_return_chronology_is_absent(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        (fixture.workspace / "return-receipt.md").unlink()
        self.assert_outcome(fixture, "worktree", "outcome-missing-chronology", "UNKNOWN")

    def test_outcome_reports_extra_direct_workspace_claims_without_failing(self) -> None:
        fixture = self.fixture("direct", follow_on=True)
        write(fixture.output / "workspace.md", fenced({"status": "returned"}))
        result = self.assert_outcome(fixture, "direct", "outcome-direct-extra-workspace", "PASS")
        extra = result["diagnostics"]["extra_direct_records"]
        workspace = next(record for record in extra if record["path"] == "workspace.md")
        self.assertTrue(workspace["present"])
        self.assertEqual(workspace["claims"], {"status": "returned"})

    def test_outcome_accepts_real_prelaunch_baseline_with_empty_prepared_root(self) -> None:
        fixture = self.fixture("direct", capture_runtime_baseline_before_init=True,
                               prepared_runtime_root=True)
        baseline = fixture.improve_runtime_baseline
        self.assertIsInstance(baseline, dict)
        self.assertFalse(baseline["git_observed"])
        self.assertEqual(baseline["git_mode"], "non-git")
        self.assertFalse(baseline["root_absent"])
        invocation_path = fixture.output / "invocation.json"
        invocation = json.loads(invocation_path.read_text())
        invocation["improve_runtime_baseline"] = baseline
        write(invocation_path, json.dumps(invocation))
        result = self.assert_outcome(fixture, "direct", "outcome-direct-prepared-root", "PASS")
        observed = result["diagnostics"]["fresh_workspace_baseline"]
        self.assertEqual(observed["git_mode"], "non-git")
        self.assertFalse(observed["git_observed"])
        self.assertFalse(observed["runtime_root_absent_at_prelaunch"])
        self.assertEqual(observed["runtime_root_current"],
                         {"present": True, "kind": "directory", "entries": []})

    def test_outcome_accepts_direct_follow_on_without_workspace_wrappers(self) -> None:
        fixture = self.fixture("direct", follow_on=True)
        result = self.assert_outcome(fixture, "direct", "outcome-direct-follow-on", "PASS")
        self.assertEqual(result["diagnostics"]["prior_source"], "invocation start_head")
        self.assertEqual(result["diagnostics"]["returns"][0]["diff_paths"], ["docs/shiploop/spec.md"])

    def test_outcome_rejects_direct_aggregate_not_committed_at_head(self) -> None:
        fixture = self.fixture("direct", follow_on=True)
        write(fixture.product / "docs/shiploop/spec.md", fixture.candidate + b"\nUncommitted change.\n")
        result = self.assert_outcome(fixture, "direct", "outcome-direct-uncommitted-aggregate", "FAIL")
        self.assertEqual(result["findings"][-1]["check"], "direct-delivery")

    def test_outcome_reports_tracked_paths_without_fabricating_fresh_prior_diff(self) -> None:
        fixture = self.fixture("direct", capture_runtime_baseline_before_init=True,
                               ancestor_git_before_product=True)
        baseline = fixture.improve_runtime_baseline
        self.assertIsInstance(baseline, dict)
        self.assertTrue(baseline["git_observed"])
        self.assertEqual(baseline["git_mode"], "git")
        self.assertEqual(baseline["git_toplevel"], str(fixture.output))
        self.assertIsNotNone(baseline["git_head"])
        invocation_path = fixture.output / "invocation.json"
        invocation = json.loads(invocation_path.read_text())
        invocation["improve_runtime_baseline"] = baseline
        write(invocation_path, json.dumps(invocation))

        result = self.assert_outcome(fixture, "direct", "outcome-direct-fresh-paths", "PASS")
        direct = result["diagnostics"]["returns"][0]
        self.assertIn("docs/shiploop/spec.md", direct["created_tracked_paths"])
        self.assertNotIn("diff_paths", direct)
        self.assertTrue(result["diagnostics"]["fresh_workspace_baseline"]["ancestor_head_is_not_selected_baseline"])

    def test_single_no_change_return_matches_prior_without_follow_up(self) -> None:
        candidate = b"# Earlier spec\n\nR-1: preserve the old result.\n"
        fixture = self.fixture("worktree", follow_on=True, single_return=True,
                               candidate=candidate, final_kind="no-change-return")
        code, result = self.run_oracle(fixture, "worktree", "single-no-change-return")
        self.assertEqual(code, 0, result)
        finding = next(item for item in result["findings"] if item["check"] == "worktree-return-chain")
        self.assertEqual(finding["observed"]["receipts"], 1)
        self.assertEqual(finding["observed"]["follow_up_paths"], [])

    def test_no_change_follow_up_can_leave_prior_and_candidate_bytes_equal(self) -> None:
        candidate = b"# Earlier spec\n\nR-1: preserve the old result.\n"
        fixture = self.fixture("worktree", follow_on=True, empty_follow_up=True,
                               candidate=candidate, final_kind="no-change-return")
        code, result = self.run_oracle(fixture, "worktree", "empty-no-change-follow-up")
        self.assertEqual(code, 0, result)
        finding = next(item for item in result["findings"] if item["check"] == "worktree-return-chain")
        self.assertEqual(finding["observed"]["receipts"], 2)
        self.assertEqual(finding["observed"]["follow_up_paths"], [])

    def test_single_final_return_can_cover_changed_candidate_without_follow_up(self) -> None:
        fixture = self.fixture("worktree", follow_on=True, single_return=True)
        self.assertNotEqual(fixture.candidate, fixture.prior["spec"])
        code, result = self.run_oracle(fixture, "worktree", "single-changed-final-return")
        self.assertEqual(code, 0, result)
        finding = next(item for item in result["findings"] if item["check"] == "worktree-return-chain")
        self.assertEqual(finding["observed"]["receipts"], 1)
        self.assertEqual(finding["observed"]["follow_up_paths"], [])

    def test_working_tree_return_uses_the_runtime_working_tree_field(self) -> None:
        fixture = self.fixture("worktree", follow_on=True, final_kind="working-tree-return")
        code, result = self.run_oracle(fixture, "worktree", "worktree-working-tree-good")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["findings"][-1]["check"], "worktree-return-chain")

    def test_new_root_worktree_preserves_absence_until_final_return(self) -> None:
        fixture = self.fixture("worktree")
        code, result = self.run_oracle(fixture, "worktree", "worktree-absent-prior")
        self.assertEqual(code, 0, result)
        self.assertTrue(result["pass"])

    def test_wrong_follow_on_initial_candidate_digest_fails(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        path = fixture.run / "spec/binding.md"
        binding = json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        binding["candidate_initial_sha256"] = "0" * 64
        write(path, fenced(binding))
        self.assert_rejected(fixture, "worktree", "wrong-initial-candidate", "initial candidate digest")

    def test_aggregate_promoted_in_an_earlier_return_fails(self) -> None:
        fixture = self.fixture("worktree", follow_on=True, early_promotion=True)
        self.assert_rejected(fixture, "worktree", "early-aggregate-return",
                             "does not preserve the exact prior aggregate bytes")

    def test_wrong_reviewed_digest_fails(self) -> None:
        fixture = self.fixture("direct")
        path = fixture.run / "spec/reviewed.md"
        review = json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        review["sha256"] = "0" * 64
        write(path, fenced(review))
        self.assert_rejected(fixture, "direct", "wrong-reviewed-digest", "reviewed.md does not bind")

    def test_early_aggregate_without_terminal_promotion_fails(self) -> None:
        fixture = self.fixture("direct")
        path = fixture.run / "spec/promotion.md"
        record = json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        record["status"] = "pending"
        write(path, fenced(record))
        self.assert_rejected(fixture, "direct", "early-aggregate-promotion", "promotion.md is not")

    def test_missing_terminal_promotion_fails(self) -> None:
        fixture = self.fixture("direct")
        (fixture.run / "spec/promotion.md").unlink()
        self.assert_rejected(fixture, "direct", "missing-final-promotion", "terminal spec promotion is missing")

    def test_wrong_prior_snapshot_digest_source_fails(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        path = fixture.run / "spec/prior-spec.md"
        write(path, b"# substituted prior\n")
        binding_path = fixture.run / "spec/binding.md"
        binding = json.loads(binding_path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        binding["snapshots"]["spec"]["sha256"] = sha(path.read_bytes())
        binding["candidate_initial_sha256"] = sha(path.read_bytes())
        write(binding_path, fenced(binding))
        self.assert_rejected(fixture, "worktree", "wrong-prior-snapshot", "prior spec snapshot differs")

    def test_absent_follow_on_snapshot_must_also_match_source_git(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        path = fixture.run / "spec/prior-architecture.md"
        path.unlink()
        binding_path = fixture.run / "spec/binding.md"
        binding = json.loads(binding_path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        binding["snapshots"]["architecture"] = {
            "path": "spec/prior-architecture.md", "present": False, "sha256": None,
        }
        write(binding_path, fenced(binding))
        self.assert_rejected(fixture, "worktree", "wrong-absent-prior-snapshot",
                             "prior architecture snapshot differs")

    def test_foreign_run_binding_fails(self) -> None:
        fixture = self.fixture("direct")
        path = fixture.run / "spec/binding.md"
        binding = json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        binding["run_id"] = "foreign-run"
        write(path, fenced(binding))
        self.assert_rejected(fixture, "direct", "foreign-run-binding", "binding identity")

    def test_unrelated_final_worktree_return_fails(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        write(fixture.product / "src/unrelated.py", "# unrelated product change\n")
        fixture.final_head = commit(fixture.product, "unrelated final return")
        fixture.final_tree = tree(fixture.product, fixture.final_head)
        receipt = fixture.receipt
        assert receipt is not None
        receipt["expected_source"] = {"head": fixture.final_head, "tree": fixture.final_tree, "branch": "main"}
        write(fixture.workspace / "return-receipt.md", fenced(receipt))
        self.assert_rejected(fixture, "worktree", "unrelated-final-return", "not an observed knowledge-only")

    def test_stale_final_return_does_not_cover_promoted_candidate(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        receipt = fixture.receipt
        assert receipt is not None
        receipt["expected_source"]["tree"] = fixture.first_return_tree
        write(fixture.workspace / "return-receipt.md", fenced(receipt))
        self.assert_rejected(fixture, "worktree", "stale-final-return",
                             "does not preserve the exact promoted candidate bytes")

    def test_final_return_source_before_must_match_previous_return(self) -> None:
        fixture = self.fixture("worktree", follow_on=True)
        receipt = fixture.receipt
        assert receipt is not None
        receipt["source_before"] = source_fingerprint(fixture.start_head, fixture.start_tree)
        write(fixture.workspace / "return-receipt.md", fenced(receipt))
        self.assert_rejected(fixture, "worktree", "broken-return-continuity",
                             "source_before does not match its previous returned tree")

    def test_old_state_format_fails_clearly(self) -> None:
        fixture = self.fixture("direct")
        path = fixture.run / "state.md"
        state = json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])
        state["version"] = 11
        write(path, fenced(state))
        self.assert_rejected(fixture, "direct", "old-state-format", "lacks intent-continuity capability")

    def test_direct_mode_rejects_fabricated_workspace_return(self) -> None:
        fixture = self.fixture("direct")
        write(fixture.output / "return-receipt.md", fenced({"status": "returned"}))
        self.assert_rejected(fixture, "direct", "direct-fabricated-return", "fabricated workspace evidence")

    def test_symlinked_selected_state_fails_closed(self) -> None:
        fixture = self.fixture("direct")
        state = fixture.run / "state.md"
        replacement = fixture.run / "state.saved"
        state.rename(replacement)
        try:
            state.symlink_to(replacement)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        self.assert_rejected(fixture, "direct", "symlink-state", "symlink is not allowed")

    def test_selected_run_symlink_fails_closed(self) -> None:
        fixture = self.fixture("direct")
        saved = fixture.output / "saved-run"
        fixture.run.rename(saved)
        try:
            fixture.run.symlink_to(saved, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        self.assert_rejected(fixture, "direct", "symlink-run-dir", "non-symlink directory")

    def test_selected_run_outside_output_and_product_is_rejected(self) -> None:
        fixture = self.fixture("direct")
        foreign = fixture.output.parent / (fixture.output.name + "-foreign-run")
        foreign.mkdir()
        write(fixture.output / "shiploop-run.json", json.dumps({"run_dir": str(foreign)}))
        self.assert_rejected(fixture, "direct", "foreign-run-path", "contained by the output directory")

    def test_catalog_cases_reuse_calibrated_casefold_oracle(self) -> None:
        current = json.loads(CASES.read_text(encoding="utf-8"))

        continuity = current["user-intent-continuity"]
        self.assertEqual(continuity["follows"], "user-teams")
        self.assertTrue(any('intent_continuity.py" --mode worktree' in check for check in continuity["checks"]))
        acceptance = continuity["quality"]["acceptance"]
        self.assertEqual(acceptance["module"], "user_team_casefold_accept")
        self.assertEqual(acceptance["checks"][-2]["id"], "team-response-spelling-preserved")
        self.assertIn('intent_continuity.py" --mode direct', current["csv-intent-direct"]["checks"][-1])

        spec = importlib.util.spec_from_file_location(
            "intent_oracle_casefold", ROOT / "test/shiploop_e2e/checks/user_team_casefold_accept.py")
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        ids = [row["id"] for row in acceptance["checks"]]
        self.assertEqual(ids, list(module.CHECKS))
        self.assertEqual(module.RETIRED_STRICT_IDS,
                         {"team-filter-case-sensitive", "summary-team-case-sensitive"})
        self.assertFalse(module.RETIRED_STRICT_IDS.intersection(ids))


if __name__ == "__main__":
    unittest.main()
