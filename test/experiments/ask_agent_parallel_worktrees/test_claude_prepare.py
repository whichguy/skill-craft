"""Disposable fixture-to-Claude preparation checks; no model calls."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import claude_controller
import claude_hooks
import prompts


class ClaudePrepareIntegrationTests(unittest.TestCase):
    def _prepare_case(self, delivery):
        with tempfile.TemporaryDirectory(prefix=f"claude prepare {delivery} ") as temp:
            run = (Path(temp) / f"run with spaces {delivery}").resolve()
            subprocess.run([
                sys.executable, "-B", str(HERE / "fixture.py"), "prepare",
                "--run", str(run), "--workers", "3", "--mode", "parallel",
                "--hold-seconds", "0", "--delivery-mode", delivery,
                "--seed-compact-ignore-controls",
            ], cwd=HERE, check=True, capture_output=True, text=True)
            manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
            prepared = claude_controller.prepare(run)
            operator = run / "operator"
            prompt = (operator / "parent-prompt.txt").read_text(encoding="utf-8")
            self.assertEqual((manifest["workers"], manifest["mode"], manifest["delivery_mode"]),
                             (3, "parallel", delivery))
            self.assertEqual((prepared["workers"], prepared["mode"], prepared["delivery_mode"]),
                             (3, "parallel", delivery))
            self.assertEqual((operator / "claude-common-parent-prompt.txt").read_text(encoding="utf-8"),
                             prompts.make_compact_prompt(run, 3, "parallel", delivery))
            if delivery == "commits":
                command = (
                    f"integrate-batch --run {shlex.quote(str(run))} --delivery-mode commits "
                    "--collected-worker 1 --collected-worker 2 --collected-worker 3"
                )
                self.assertIn(command, prompt)
                self.assertIn("Only the assigned worker may make its task commit", prompt)
            else:
                self.assertIn("finish-ephemeral --run", prompt)
                self.assertIn("NO_INTEGRATION", prompt)
                self.assertIn("must not import, patch, cherry-pick", prompt)
                self.assertIn("After ephemeral finalization", prompt)
            for name in claude_controller.FROZEN_FILES:
                artifact = operator / name
                self.assertTrue(artifact.is_file(), name)
                self.assertEqual(prepared["frozen_files"][name], hashlib.sha256(artifact.read_bytes()).hexdigest())
            for name in claude_controller.COMMON_APPARATUS:
                if name == "probe-fixture.py" and not (HERE / name).is_file():
                    continue
                self.assertTrue((operator / name).is_file(), name)
            settings = json.loads((operator / "claude-native/settings.json").read_text(encoding="utf-8"))
            self.assertEqual(set(settings["hooks"]), set(claude_hooks.HOOK_EVENTS))
            self.assertFalse((operator / "launch.json").exists())
            before = {p.relative_to(operator): p.read_bytes() for p in operator.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(claude_controller.ClaudeControllerError, "preparation attempt already exists"):
                claude_controller.prepare(run)
            after = {p.relative_to(operator): p.read_bytes() for p in operator.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_commits_delivery_prepares_full_claude_apparatus(self):
        self._prepare_case("commits")

    def test_ephemeral_delivery_prepares_full_claude_apparatus(self):
        self._prepare_case("ephemeral")


if __name__ == "__main__":
    unittest.main()
