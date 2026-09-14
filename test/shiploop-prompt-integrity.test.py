#!/usr/bin/env python3
"""Regression coverage for ShipLoop's frozen original-prompt pair."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))


class PromptIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-prompt-integrity-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run_dir = self.repo / ".shiploop"
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(
                ROOT / "test/fixtures/shiploop/backchain-leaf"
            ),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Prompt Integrity Test")
        self.git("config", "user.email", "prompt-integrity@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def cli(self, *args, code=0):
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def cli_bytes(self, *args, code=0):
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(
            result.returncode,
            code,
            result.stdout.decode("utf-8", "replace")
            + result.stderr.decode("utf-8", "replace"),
        )
        return result

    def init(self, prompt="Build the exact requested behavior"):
        self.cli(
            "init", "--repo", str(self.repo), "--execution-mode", "managed",
            "--prompt", prompt,
        )
        return prompt

    @staticmethod
    def read_record(path):
        import shiploop_store

        return shiploop_store.read_record(path)

    def state(self):
        return self.read_record(self.run_dir / "state.md")

    def record(self, name, value):
        import shiploop_store

        path = self.root / name
        shiploop_store.write_record(path, value)
        return str(path)

    def snapshot(self):
        return {
            name: (self.run_dir / name).read_bytes()
            for name in ("state.md", "history.md", "prompt.md")
            if (self.run_dir / name).exists() or (self.run_dir / name).is_symlink()
        }

    def assert_refused_without_reconciliation(self, *args):
        before = self.snapshot()
        result = self.cli(*args, code=2)
        self.assertIn("saved prompt", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before["state.md"])
        self.assertEqual((self.run_dir / "history.md").read_bytes(), before["history.md"])
        return result

    def test_tampered_fresh_prompt_blocks_packet_context_status_and_init_again(self):
        prompt = self.init("Original request must remain stable")
        (self.run_dir / "prompt.md").write_bytes(b"Tampered sidecar only\n")

        for command in (
            ("init", "--repo", str(self.repo), "--prompt", prompt),
            ("next",),
            ("status",),
            ("context", "--section", "prompt"),
        ):
            with self.subTest(command=command[0]):
                self.assert_refused_without_reconciliation(*command)

    def test_state_only_prompt_tamper_is_not_reconciled_from_prompt_md(self):
        self.init("Original request must remain stable")
        import shiploop_store

        state = self.state()
        state["prompt"] = "Tampered authoritative state only"
        shiploop_store.write_record(self.run_dir / "state.md", state)

        self.assert_refused_without_reconciliation("next")
        self.assert_refused_without_reconciliation("context", "--section", "prompt")

    def test_missing_and_linked_prompt_are_refused_without_mutating_the_run(self):
        self.init()
        prompt_path = self.run_dir / "prompt.md"
        prompt_path.unlink()
        self.assert_refused_without_reconciliation("status")

        prompt_path.write_text("Build the exact requested behavior\n", encoding="utf-8")
        outside = self.root / "outside-prompt.md"
        outside.write_text("Build the exact requested behavior\n", encoding="utf-8")
        prompt_path.unlink()
        prompt_path.symlink_to(outside)
        self.assert_refused_without_reconciliation("context", "--section", "prompt")

    def test_matching_hardlinked_prompt_is_refused_without_touching_its_alias(self):
        self.init()
        prompt_path = self.run_dir / "prompt.md"
        alias = self.root / "prompt-alias.md"
        os.link(prompt_path, alias)
        before_alias = alias.read_bytes()
        before_stat = alias.stat()

        result = self.assert_refused_without_reconciliation("status")

        self.assertIn("single-link", result.stderr)
        self.assertEqual(alias.read_bytes(), before_alias)
        after_stat = alias.stat()
        self.assertEqual(
            (after_stat.st_dev, after_stat.st_ino, after_stat.st_nlink, after_stat.st_mtime_ns),
            (
                before_stat.st_dev,
                before_stat.st_ino,
                before_stat.st_nlink,
                before_stat.st_mtime_ns,
            ),
        )

    def test_oversized_prompt_is_rejected_before_any_payload_read(self):
        prompt = self.init()
        state = self.state()
        prompt_path = self.run_dir / "prompt.md"
        prompt_path.write_bytes((prompt + "\n").encode("utf-8") + b"surplus")
        before = self.snapshot()

        import shiploop_protocol

        with patch.object(
            shiploop_protocol.os,
            "read",
            side_effect=AssertionError("oversized prompt must not be read"),
        ):
            with self.assertRaisesRegex(
                shiploop_protocol.ProtocolError,
                "saved prompt differs from authoritative state",
            ):
                shiploop_protocol.validate_settled_prompt(self.run_dir, state)

        self.assertEqual(self.snapshot(), before)
        self.assert_refused_without_reconciliation("status")

    def test_fresh_prompt_round_trips_literal_bytes_including_crlf_unicode_and_lf(self):
        prompt = "First line\r\nUnicode: Ω\r\nTrailing spaces:   \nIntentional LF\n"
        self.init(prompt)
        expected = (prompt + "\n").encode("utf-8")

        self.assertEqual((self.run_dir / "prompt.md").read_bytes(), expected)
        self.assertEqual(self.state()["prompt"], prompt)
        self.cli("next")
        context = self.cli_bytes("context", "--section", "prompt")
        self.assertIn(expected, context.stdout)

    def test_valid_pending_recovery_finishes_before_prompt_integrity_validation(self):
        import shiploop_store

        self.init("Before interrupted transaction")
        recovered_prompt = "After interrupted transaction\r\nΩ"
        recovered = self.state()
        recovered["prompt"] = recovered_prompt

        def crash_after_prompt(phase, index):
            if phase == "after-target" and index == 1:
                raise RuntimeError("simulated interruption after prompt write")

        with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
            shiploop_store.transaction(
                self.run_dir,
                {
                    "prompt.md": recovered_prompt + "\n",
                    "state.md": shiploop_store.dumps(recovered, "ShipLoop state"),
                },
                fault=crash_after_prompt,
            )
        self.assertTrue((self.run_dir / "transaction.md").is_file())

        self.cli("status")

        self.assertFalse((self.run_dir / "transaction.md").exists())
        self.assertEqual(self.state()["prompt"], recovered_prompt)
        self.assertEqual(
            (self.run_dir / "prompt.md").read_bytes(),
            (recovered_prompt + "\n").encode("utf-8"),
        )

    def test_migration_keeps_recovered_literal_bytes_and_unrecoverable_diagnostics(self):
        legacy_prompt = "Legacy CRLF\r\nUnicode: Ω\r\nIntentional LF\n"
        self.run_dir.mkdir()
        legacy = {
            "version": 2,
            "run_id": "legacy-prompt-integrity",
            "phase": "intake",
            "repo_root": str(self.repo),
            "prompt": legacy_prompt,
        }
        (self.run_dir / "state.json").write_text(json.dumps(legacy), encoding="utf-8")
        (self.run_dir / "prompt.md").write_bytes(legacy_prompt.encode("utf-8"))

        self.cli("migrate")

        self.assertEqual((self.run_dir / "prompt.md").read_bytes(), legacy_prompt.encode("utf-8"))
        self.assertEqual(self.state()["prompt"], legacy_prompt)
        self.assertIn(
            legacy_prompt.encode("utf-8"),
            self.cli_bytes("context", "--section", "prompt").stdout,
        )
        self.cli("status")

        other = self.repo / ".shiploop-unrecoverable"
        other.mkdir()
        missing = dict(legacy, run_id="legacy-unrecoverable")
        missing.pop("prompt")
        (other / "state.json").write_text(json.dumps(missing), encoding="utf-8")
        self.cli("migrate", "--run-dir", str(other))
        state = self.read_record(other / "state.md")
        self.assertEqual(state["prompt_recovery"]["status"], "unrecoverable")
        self.assertFalse((other / "prompt.md").exists())
        self.cli("status", "--run-dir", str(other))
        self.cli("context", "--run-dir", str(other), "--section", "prompt")

    def test_tampered_prompt_blocks_done_replay_and_mutators_before_history_changes(self):
        self.init()
        action = self.state()["action"]["id"]
        result = self.record(
            "ready.md", {"summary": "ready", "baseline": "committed-head"}
        )

        self.cli("complete", "--action", action, "--result", result)
        (self.run_dir / "prompt.md").write_bytes(b"Tampered after completion\n")
        self.assert_refused_without_reconciliation(
            "done", "--action", action, "--result", result
        )

        for command in (
            ("pause", "--reason", "must not persist while prompt is tampered"),
            ("resume",),
            ("halt", "--reason", "must not persist while prompt is tampered"),
        ):
            with self.subTest(command=command[0]):
                self.assert_refused_without_reconciliation(*command)

    def test_convenience_entrypoints_reject_prompt_drift_before_transition(self):
        self.init()
        action = self.state()["action"]["id"]
        result = self.record("wrapper.md", {"summary": "ready", "baseline": "committed-head"})
        (self.run_dir / "prompt.md").write_bytes(b"Changed outside the run transaction\n")
        before = self.snapshot()
        for name, extra in (
            ("shiploop-next", []),
            ("shiploop-complete", ["--action", action, "--result", result]),
        ):
            with self.subTest(entrypoint=name):
                call = subprocess.run(
                    [sys.executable, str(SCRIPTS / name), "--run-dir", str(self.run_dir), *extra],
                    cwd=self.repo, env=self.env, capture_output=True, text=True,
                )
                self.assertEqual(call.returncode, 2, call.stdout + call.stderr)
                self.assertIn("saved prompt", call.stderr)
                self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
