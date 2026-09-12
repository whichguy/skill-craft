#!/usr/bin/env python3
"""Immutable seven-body history policy coverage for ShipLoop review gates."""

from __future__ import annotations

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

import shiploop_evidence as evidence  # noqa: E402
import shiploop_history_policy as history_policy  # noqa: E402
import shiploop_objectives as objectives  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


NEW_RUN = {"history_policy": {"version": 2, "required_limit": 7}}


class GitCore:
    """Minimal real-Git adapter for protocol helper tests."""

    @staticmethod
    def git_run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True
        )


class HistoryPolicyResolverTests(unittest.TestCase):
    def test_absent_marker_retains_a_fresh_legacy_policy_copy(self) -> None:
        first = history_policy.resolve({})
        first["required_limit"] = 1
        self.assertEqual(history_policy.resolve({}), {"version": 1, "required_limit": 10})
        self.assertEqual(history_policy.required_limit({}), 10)

    def test_exact_v2_marker_selects_seven(self) -> None:
        self.assertEqual(history_policy.resolve(NEW_RUN), {"version": 2, "required_limit": 7})
        self.assertEqual(history_policy.required_limit(NEW_RUN), 7)

    def test_unknown_or_malformed_marker_fails_closed(self) -> None:
        invalid_markers = (
            None,
            {"version": 2},
            {"version": 2, "required_limit": 7, "extra": True},
            {"version": True, "required_limit": 7},
            {"version": 2, "required_limit": True},
            {"version": 1, "required_limit": 10},
            {"version": 2, "required_limit": 10},
        )
        for marker in invalid_markers:
            with self.subTest(marker=marker):
                with self.assertRaises(history_policy.HistoryPolicyError):
                    history_policy.resolve({"history_policy": marker})


class HistoryPolicyCliTests(unittest.TestCase):
    def test_unknown_marker_blocks_an_existing_run_before_status_can_proceed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-history-policy-cli-") as raw:
            root = Path(raw)
            repo = root / "repo"
            run = repo / ".shiploop"
            repo.mkdir()
            env = dict(
                os.environ,
                PYTHONDONTWRITEBYTECODE="1",
                SHIPLOOP_BACKCHAIN_ROOT=str(
                    ROOT / "test/fixtures/shiploop/backchain-leaf"
                ),
            )
            for args in (
                ("init", "-q"),
                ("config", "user.name", "History Policy CLI Test"),
                ("config", "user.email", "history-policy-cli@example.invalid"),
                ("commit", "--allow-empty", "-qm", "baseline"),
            ):
                process = subprocess.run(
                    ["git", "-C", str(repo), *args],
                    capture_output=True,
                    text=True,
                    env=env,
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            initialized = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "init",
                    "--repo",
                    str(repo),
                    "--run-dir",
                    str(run),
                    "--prompt",
                    "Exercise the immutable history policy.",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            state = store.read_record(run / "state.md")
            state["history_policy"] = {"version": 2, "required_limit": 10}
            store.write_record(run / "state.md", state, title="ShipLoop state")
            before = (run / "state.md").read_bytes()
            rejected = subprocess.run(
                [sys.executable, str(CLI), "status", "--run-dir", str(run)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
            self.assertIn("history policy is unsupported", rejected.stderr)
            self.assertEqual((run / "state.md").read_bytes(), before)


class HistoryPolicyReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-history-policy-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run = self.repo / ".shiploop"
        self.run.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q")
        self.git("config", "user.name", "History Policy Test")
        self.git("config", "user.email", "history-policy@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        for number in range(10):
            self.git("commit", "--allow-empty", "-qm", f"history policy {number}")

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def record_pages(
        self, iteration: dict, state: dict, *, count: int, prefix: str
    ) -> None:
        for skip in range(count):
            rows = evidence.history(self.repo, 1, skip)
            relative = f"history-pages/{prefix}-{skip}.md"
            protocol.record_full_history_page(
                iteration,
                rows,
                head=self.head(),
                skip=skip,
                limit=1,
                archive_path=relative,
                state=state,
            )
            path = self.run / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                store.dumps(rows, "Git history — full commit bodies"), encoding="utf-8"
            )

    def test_new_policy_binds_seven_for_planning_step_plan_and_inner_review(self) -> None:
        for family in ("planning", "step-plan", "inner-loop"):
            with self.subTest(family=family):
                iteration: dict = {}
                self.record_pages(iteration, NEW_RUN, count=7, prefix=family)
                self.assertEqual(iteration["history_policy"], NEW_RUN["history_policy"])
                self.assertEqual(iteration["history"]["required_limit"], 7)
                protocol.require_full_history(
                    GitCore(),
                    self.run,
                    iteration,
                    self.repo,
                    label=f"{family} review",
                    state=NEW_RUN,
                )

    def test_generic_objective_binds_and_requires_seven_current_bodies(self) -> None:
        receipt = {"current_pass": {}}
        rows = evidence.history(self.repo, 7, 0)
        objectives.record_history(
            receipt, rows, head=self.head(), skip=0, state=NEW_RUN
        )
        self.assertEqual(receipt["current_pass"]["history_policy"], NEW_RUN["history_policy"])
        self.assertEqual(receipt["current_pass"]["history"]["required_limit"], 7)
        objectives.assert_history(receipt, rows, head=self.head(), state=NEW_RUN)

    def test_partial_or_stale_new_receipts_do_not_satisfy_seven_body_review(self) -> None:
        iteration: dict = {}
        self.record_pages(iteration, NEW_RUN, count=6, prefix="partial")
        with self.assertRaisesRegex(protocol.ProtocolError, "latest 7 full commit bodies"):
            protocol.require_full_history(
                GitCore(), self.run, iteration, self.repo, label="planning review", state=NEW_RUN
            )

        self.record_pages(iteration, NEW_RUN, count=7, prefix="partial")
        iteration["history"]["required_limit"] = 10
        with self.assertRaisesRegex(protocol.ProtocolError, "latest 7 full commit bodies"):
            protocol.require_full_history(
                GitCore(), self.run, iteration, self.repo, label="planning review", state=NEW_RUN
            )

        iteration["history_policy"]["required_limit"] = 10
        with self.assertRaises(history_policy.HistoryPolicyError):
            protocol.require_full_history(
                GitCore(), self.run, iteration, self.repo, label="planning review", state=NEW_RUN
            )

    def test_legacy_ten_body_receipt_remains_valid_and_cannot_upgrade_mid_run(self) -> None:
        legacy_iteration: dict = {}
        self.record_pages(legacy_iteration, {}, count=10, prefix="legacy")
        self.assertNotIn("history_policy", legacy_iteration)
        self.assertEqual(legacy_iteration["history"]["required_limit"], 10)
        protocol.require_full_history(
            GitCore(),
            self.run,
            legacy_iteration,
            self.repo,
            label="legacy planning review",
            state={},
        )
        with self.assertRaises(history_policy.HistoryPolicyError):
            protocol.require_full_history(
                GitCore(),
                self.run,
                legacy_iteration,
                self.repo,
                label="upgraded planning review",
                state=NEW_RUN,
            )


if __name__ == "__main__":
    unittest.main()
