#!/usr/bin/env python3
"""Focused migration coverage for legacy prompt recovery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))


class MigrationPromptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-migration-prompt-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(
                ROOT / "test/fixtures/shiploop/backchain-leaf"
            ),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Migration Prompt Test")
        self.git("config", "user.email", "migration-prompt@example.invalid")
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

    def legacy_state(self, run_dir, prompt_marker=..., run_id=...):
        state = {
            "version": 2,
            "run_id": (
                f"legacy-{run_dir.name.lstrip('.')}" if run_id is ... else run_id
            ),
            "phase": "intake",
            "repo_root": str(self.repo),
        }
        if prompt_marker is not ...:
            state["prompt"] = prompt_marker
        run_dir.mkdir()
        (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
        return state

    def test_migrate_rejects_unsafe_legacy_run_ids_before_writes(self):
        invalid_run_ids = (
            None,
            False,
            17,
            "",
            "../escape",
            "legacy/with/slash",
            "legacy with spaces",
            "-legacy",
            "_legacy",
            "a" * 149,
        )
        migrated_artifacts = (
            "state.md",
            "migration.md",
            "run.md",
            "history.md",
            "prompt.md",
            "shiploop-improvements.md",
            "legacy-backup",
        )
        for index, run_id in enumerate(invalid_run_ids):
            with self.subTest(run_id=run_id):
                run_dir = self.repo / f".shiploop-invalid-run-id-{index}"
                old = self.legacy_state(run_dir, "preserve me", run_id=run_id)
                original_state = (run_dir / "state.json").read_bytes()

                result = self.cli("migrate", "--run-dir", str(run_dir), code=2)

                self.assertIn("unsafe legacy run ID", result.stderr)
                self.assertEqual((run_dir / "state.json").read_bytes(), original_state)
                self.assertEqual(
                    json.loads((run_dir / "state.json").read_text(encoding="utf-8")),
                    old,
                )
                for relative in migrated_artifacts:
                    self.assertFalse(
                        (run_dir / relative).exists(),
                        f"migration created {relative} for malformed run ID {run_id!r}",
                    )

    @staticmethod
    def read_record(path):
        import shiploop_store

        return shiploop_store.read_record(path)

    def test_migrate_recovers_exact_nonempty_prompt_for_a_cold_retrieval(self):
        run_dir = self.repo / ".shiploop"
        prompt = "  Preserve this exact prompt.  \nUnicode: Ω\nTrailing spaces:   "
        old = self.legacy_state(run_dir, prompt)

        self.cli("migrate", "--run-dir", str(run_dir))

        expected_recovery = {
            "status": "recovered-from-state",
            "source": "state.prompt",
            "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
        state = self.read_record(run_dir / "state.md")
        migration = self.read_record(run_dir / "migration.md")
        self.assertEqual((run_dir / "prompt.md").read_text(encoding="utf-8"), prompt)
        self.assertEqual(state["prompt"], prompt)
        self.assertEqual(state["prompt_recovery"], expected_recovery)
        self.assertEqual(migration["prompt_recovery"], expected_recovery)
        self.assertEqual(
            state["artifacts"]["prompt"], str(run_dir.resolve() / "prompt.md")
        )
        self.assertEqual(
            json.loads((run_dir / "legacy-backup/state.json").read_text()), old
        )

        # This is a fresh CLI process: it can retrieve the durable prompt
        # without relying on the migration command's process memory.
        cold = self.cli(
            "context",
            "--run-dir",
            str(run_dir),
            "--section",
            "prompt",
            "--offset",
            "0",
            "--limit",
            "4000",
        )
        self.assertIn(prompt, cold.stdout)

    def test_migrate_marks_unusable_legacy_prompts_and_blocks_advancement(self):
        cases = {
            "missing": ...,
            "empty": "   \n\t",
            "non-string": {"not": "a prompt"},
        }
        for reason, prompt_marker in cases.items():
            with self.subTest(reason=reason):
                run_dir = self.repo / f".shiploop-{reason}"
                old = self.legacy_state(run_dir, prompt_marker)

                migrated = self.cli("migrate", "--run-dir", str(run_dir))
                expected_recovery = {
                    "status": "unrecoverable",
                    "source": "state.prompt",
                    "reason": reason,
                }
                state = self.read_record(run_dir / "state.md")
                migration = self.read_record(run_dir / "migration.md")
                self.assertNotIn("prompt", state)
                self.assertEqual(state["prompt_recovery"], expected_recovery)
                self.assertEqual(migration["prompt_recovery"], expected_recovery)
                self.assertNotIn("prompt", state["artifacts"])
                self.assertFalse((run_dir / "prompt.md").exists())
                self.assertIn("Do not resume", state["paused"])
                self.assertIn("No completion callback is valid while paused.", migrated.stdout)
                self.assertNotIn(" resume --run-dir ", migrated.stdout)
                self.assertIn("status --run-dir", migrated.stdout)
                self.assertEqual(
                    json.loads((run_dir / "legacy-backup/state.json").read_text()), old
                )

                before = (run_dir / "state.md").read_bytes()
                status = self.cli("status", "--run-dir", str(run_dir))
                self.assertIn("Legacy state.prompt is unrecoverable", status.stdout)
                self.assertIn("Do not resume", status.stdout)
                self.assertNotIn(" resume --run-dir ", status.stdout)
                self.assertEqual((run_dir / "state.md").read_bytes(), before)

                context = self.cli(
                    "context",
                    "--run-dir",
                    str(run_dir),
                    "--section",
                    "prompt",
                    "--offset",
                    "0",
                    "--limit",
                    "4000",
                )
                self.assertIn("prompt_recovery", context.stdout)
                self.assertIn("unrecoverable", context.stdout)
                self.assertEqual((run_dir / "state.md").read_bytes(), before)

                blocked = self.cli("next", "--run-dir", str(run_dir), code=2)
                self.assertIn("legacy prompt is unrecoverable", blocked.stderr)
                self.assertIn("seek user direction", blocked.stderr)
                self.assertIn("start a new scoped run", blocked.stderr)
                self.assertIn("status --run-dir", blocked.stderr)
                self.assertIn("safely available durable orientation", blocked.stderr)
                self.assertNotIn("rehydrates the current assignment and purpose", blocked.stderr)
                self.assertNotIn("next --run-dir", blocked.stderr)
                self.assertEqual((run_dir / "state.md").read_bytes(), before)

                resumed = self.cli("resume", "--run-dir", str(run_dir), code=2)
                self.assertIn("legacy prompt is unrecoverable", resumed.stderr)
                self.assertEqual((run_dir / "state.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
