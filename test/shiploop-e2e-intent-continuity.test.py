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
                 early_promotion: bool = False, final_kind: str = "fast-forward-merge"):
        self.root = root.resolve()
        self.mode = mode
        self.output = self.root
        self.output.mkdir(parents=True)
        self.product = self.output / "product"
        self.product.mkdir()
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

        self.candidate = b"# Current spec\n\nR-1: preserve the old result.\nR-2: add the accepted request.\n"
        if mode == "worktree" and early_promotion:
            write(self.product / "docs/shiploop/spec.md", self.candidate)
        if mode == "worktree":
            write(self.product / "src/users.py", "# returned product change\n")
        else:
            write(self.product / "docs/shiploop/spec.md", self.candidate)
        self.first_return_head = commit(self.product, "return product change")
        self.first_return_tree = tree(self.product, self.first_return_head)
        if mode == "worktree":
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
            }))
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
        invocation = {"case": "fixture", "follow_on": {"start_head": self.start_head} if follow_on else None}
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
            if raw is not None:
                write(self.run / snapshot, raw)
        run_id, improve, handoff = "fixture-run", "I-spec", "H-terminal"
        current_hash = sha(self.candidate)
        prior_spec = self.prior["spec"]
        prior_hash = sha(prior_spec) if prior_spec is not None else sha(b"")
        write(self.run / "current-spec.md", self.candidate)
        state = {
            "version": 12, "run_id": run_id, "repo": str(repo), "spec_root": str(self.run),
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
        write(self.run / "state.md", fenced(state))
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
                final_kind: str = "fast-forward-merge") -> Fixture:
        return Fixture(self.root / ("case-" + str(len(list(self.root.iterdir())))), mode,
                       follow_on=follow_on, early_promotion=early_promotion, final_kind=final_kind)

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
