#!/usr/bin/env python3
"""No-model tests for the experimental bounded review runner."""
from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("generalized_discovery_review_runner_under_test", HERE / "review_runner.py")
assert SPEC and SPEC.loader
review_runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_runner)


class ReviewRunnerTest(unittest.TestCase):
    def run_code(
        self,
        root: Path,
        code: str,
        *,
        timeout_seconds: float = 2.0,
        hard_deadline_epoch: float | None = None,
        output_name: str = "review",
    ) -> tuple[dict[str, object], Path]:
        output = root / output_name
        result = review_runner.run_bounded(
            [sys.executable, "-c", code],
            root,
            output,
            timeout_seconds,
            hard_deadline_epoch,
        )
        return result, output

    def test_quick_success_captures_streams_without_returning_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result, output = self.run_code(
                root,
                "import sys; print('review' + chr(32) + 'output'); "
                "print('diag' + 'nostic', file=sys.stderr)",
            )
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["success"])
            self.assertEqual(result["exit_code"], 0)
            self.assertIsNone(result["reason"])
            self.assertIn("launched_at_utc", result)
            self.assertIn("finished_at_utc", result)
            self.assertGreaterEqual(result["elapsed_monotonic_seconds"], 0)
            self.assertEqual((output / "stdout.log").read_text(encoding="utf-8"), "review output\n")
            self.assertEqual((output / "stderr.log").read_text(encoding="utf-8"), "diagnostic\n")
            persisted = json.loads((output / "result.json").read_text(encoding="utf-8"))
            self.assertNotIn("review output", json.dumps(persisted))
            self.assertNotIn("diagnostic", json.dumps(persisted))
            self.assertEqual(persisted, result)

    def test_nonzero_exit_is_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, _ = self.run_code(Path(temporary), "import sys; sys.exit(7)")
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["success"])
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["reason"], "nonzero_exit")

    def test_stalled_child_is_timed_out_with_bounded_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            started = time.monotonic()
            result, _ = self.run_code(Path(temporary), "import time; time.sleep(5)", timeout_seconds=0.12)
            elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "timeout")
        self.assertLess(elapsed, 1.2)
        self.assertTrue(result["cleanup"]["term_sent"])
        self.assertGreaterEqual(result["cleanup"]["additional_elapsed_monotonic_seconds"], 0)

    def test_hard_deadline_clamps_the_relative_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            deadline = time.time() + 0.12
            started = time.monotonic()
            result, _ = self.run_code(
                Path(temporary),
                "import time; time.sleep(5)",
                timeout_seconds=2,
                hard_deadline_epoch=deadline,
            )
            elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "hard_deadline")
        self.assertLessEqual(result["effective_timeout_seconds"], 0.12)
        self.assertLess(elapsed, 1.2)

    @unittest.skipUnless(os.name == "posix", "SIGTERM handling is POSIX-specific")
    def test_term_resistant_child_uses_the_finite_kill_reserve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            started = time.monotonic()
            result, _ = self.run_code(
                Path(temporary),
                "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(5)",
                timeout_seconds=0.1,
            )
            elapsed = time.monotonic() - started
        self.assertEqual(result["reason"], "timeout")
        self.assertTrue(result["cleanup"]["term_sent"])
        self.assertTrue(result["cleanup"]["kill_sent"])
        self.assertEqual(result["cleanup"]["outcome"], "killed")
        self.assertGreaterEqual(result["cleanup"]["additional_elapsed_monotonic_seconds"], 0.25)
        self.assertLess(elapsed, 1.5)

    def test_interrupt_persists_failed_cleanup_receipt_before_reraising(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "interrupted"
            original_sleep = time.sleep
            calls = 0

            def interrupt_first_poll(seconds: float) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise KeyboardInterrupt
                original_sleep(seconds)

            with mock.patch.object(review_runner.time, "sleep", side_effect=interrupt_first_poll):
                with self.assertRaises(KeyboardInterrupt):
                    review_runner.run_bounded(
                        [sys.executable, "-c", "import time; time.sleep(5)"],
                        root,
                        output,
                        1,
                    )
            receipt = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["launched"])
        self.assertEqual(receipt["status"], "failed")
        self.assertFalse(receipt["success"])
        self.assertEqual(receipt["reason"], "runner_interrupted")
        self.assertEqual(receipt["exit_code"], -15)
        self.assertTrue(receipt["cleanup"]["term_sent"])
        self.assertFalse(receipt["cleanup"]["group_alive_after_cleanup"])

    @unittest.skipUnless(os.name == "posix", "process-group cleanup is POSIX-specific")
    def test_parent_exit_does_not_leave_same_group_descendant_running(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "descendant-survived"
            descendant = (
                "from pathlib import Path; import time; time.sleep(0.6); "
                f"Path({str(marker)!r}).write_text('survived', encoding='utf-8')"
            )
            parent = (
                "import subprocess, sys; "
                f"subprocess.Popen([sys.executable, '-c', {descendant!r}])"
            )
            result, _ = self.run_code(root, parent)
            time.sleep(0.8)
            self.assertFalse(marker.exists())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "descendants_active_after_parent_exit")
        self.assertTrue(result["cleanup"]["term_sent"])
        self.assertIn(result["cleanup"]["outcome"], {"terminated", "killed"})

    def test_expired_deadline_is_recorded_without_launching(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "should-not-exist"
            code = f"from pathlib import Path; Path({str(marker)!r}).write_text('launched')"
            result, output = self.run_code(
                root,
                code,
                hard_deadline_epoch=time.time() - 1,
            )
            self.assertEqual(result["status"], "not_started")
            self.assertEqual(result["reason"], "hard_deadline_expired_before_launch")
            self.assertFalse(result["launched"])
            self.assertIsNone(result["pid"])
            self.assertFalse(marker.exists())
            self.assertTrue((output / "result.json").is_file())
            self.assertFalse((output / "stdout.log").exists())

    def test_existing_output_directory_is_refused_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "review"
            output.mkdir()
            sentinel = output / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "must be new"):
                review_runner.run_bounded([sys.executable, "-c", "print('unused')"], root, output, 1)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertFalse((output / "result.json").exists())

    def test_malformed_limits_are_rejected_before_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for value in (0, -1, math.inf, -math.inf, math.nan, True, "1"):
                with self.subTest(value=value):
                    output = root / f"output-{str(value).replace('-', 'neg').replace('.', '_')}"
                    with self.assertRaisesRegex(ValueError, "timeout_seconds"):
                        review_runner.run_bounded([sys.executable, "-c", "print('unused')"], root, output, value)
                    self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, "hard_deadline_epoch"):
                review_runner.run_bounded(
                    [sys.executable, "-c", "print('unused')"], root, root / "bad-deadline", 1, math.nan
                )

    def test_spawn_failure_is_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = review_runner.run_bounded(
                ["/definitely/not/a-reviewer-command"], root, root / "spawn-failure", 1
            )
            self.assertEqual(result["status"], "not_started")
            self.assertFalse(result["success"])
            self.assertEqual(result["reason"], "spawn_failure")
            self.assertFalse(result["launched"])
            self.assertTrue((root / "spawn-failure" / "result.json").is_file())

    def test_cli_accepts_command_remainder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "cli-output"
            prompt = root / "prompt.md"
            prompt.write_text("cli-only-stream\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "review_runner.py"),
                    "--cwd",
                    str(root),
                    "--output-dir",
                    str(output),
                    "--timeout-seconds",
                    "1",
                    "--stdin-file",
                    str(prompt),
                    "--",
                    sys.executable,
                    "-c",
                    "import sys; print(sys.stdin.read(), end='')",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "success")
            self.assertNotIn("cli-only-stream", completed.stdout)
            self.assertEqual((output / "stdout.log").read_text(encoding="utf-8"), "cli-only-stream\n")


if __name__ == "__main__":
    unittest.main()
