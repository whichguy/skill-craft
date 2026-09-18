#!/usr/bin/env python3
"""Hermetic regression for separately-sessioned child cleanup."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capture  # noqa: E402
import run  # noqa: E402


def running(pid: int) -> bool:
    """A zombie still accepts kill(0), so ask the OS for a non-zombie state."""
    completed = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    state = completed.stdout.strip()
    return bool(state) and not state.startswith("Z")


def stopped(pid: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not running(pid):
            return True
        time.sleep(0.05)
    return not running(pid)


class TimeoutDescendantCleanupTest(unittest.TestCase):
    def test_detached_descendant_is_cleaned_but_unrelated_sleeper_survives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child_record = root / "child.json"
            unrelated = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True,
            )
            code = (
                "import json, os, subprocess, sys, time; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], start_new_session=True); "
                f"open({str(child_record)!r},'w').write(json.dumps({{'pid':child.pid,'pgid':os.getpgid(child.pid)}})); "
                "time.sleep(30)"
            )
            try:
                started = time.monotonic()
                result = capture.capture_process(
                    [sys.executable, "-c", code], root, root / "capture", 0.5,
                    before_stop=run._owned_descendant_cleanup,
                )
                elapsed = time.monotonic() - started
                child = json.loads(child_record.read_text(encoding="utf-8"))
                self.assertTrue(result["timed_out"])
                self.assertLess(elapsed, 5.0, result)
                cleanup = result["group_termination"]["descendant_cleanup"]
                self.assertTrue(cleanup["attempted"])
                self.assertIn(cleanup["receipt"]["status"], {"signals-sent-stop-unverified", "partial-signal-errors"})
                self.assertIn(child["pgid"], [row["pgid"] for row in cleanup["receipt"]["candidates"]])
                self.assertTrue(stopped(child["pid"]))
                self.assertTrue(running(unrelated.pid))
            finally:
                if child_record.exists():
                    child = json.loads(child_record.read_text(encoding="utf-8"))
                    if running(child["pid"]) and os.getpgid(child["pid"]) == child["pgid"]:
                        os.killpg(child["pgid"], signal.SIGKILL)
                if running(unrelated.pid):
                    os.killpg(unrelated.pid, signal.SIGKILL)
                unrelated.wait(timeout=5)

    def test_parent_exit_with_detached_pipe_holder_returns_bounded_and_reports_ancestry_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child_record = root / "orphan.json"
            code = (
                "import json, os, subprocess, sys; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'], start_new_session=True); "
                f"record=open({str(child_record)!r},'w'); json.dump({{'pid':child.pid,'pgid':os.getpgid(child.pid)}},record); record.flush(); "
                "os._exit(0)"
            )
            try:
                started = time.monotonic()
                result = capture.capture_process(
                    [sys.executable, "-c", code], root, root / "capture", 2.0,
                    before_stop=run._owned_descendant_cleanup,
                )
                elapsed = time.monotonic() - started
                child = json.loads(child_record.read_text(encoding="utf-8"))
                self.assertLess(elapsed, 5.0, result)
                self.assertEqual(result["termination_reason"], "descendant_pipe_holders")
                cleanup = result["group_termination"]["descendant_cleanup"]["receipt"]
                self.assertEqual(cleanup["status"], "ancestry-unavailable-root-missing")
                self.assertTrue(running(child["pid"]))
            finally:
                if child_record.exists():
                    child = json.loads(child_record.read_text(encoding="utf-8"))
                    if running(child["pid"]) and os.getpgid(child["pid"]) == child["pgid"]:
                        os.killpg(child["pgid"], signal.SIGKILL)

    def test_identity_mismatch_does_not_signal_a_reused_group_leader(self) -> None:
        before = {
            100: {"pid": 100, "ppid": 1, "pgid": 100, "started": "old root"},
            200: {"pid": 200, "ppid": 100, "pgid": 200, "started": "owned child"},
        }
        changed = {**before, 200: {"pid": 200, "ppid": 100, "pgid": 200, "started": "reused pid"}}
        with (
            mock.patch.object(run, "_process_snapshot", side_effect=[(before, None), (changed, None), (changed, None)]),
            mock.patch.object(run.os, "getpgid", return_value=100),
            mock.patch.object(run.os, "getpgrp", return_value=999),
            mock.patch.object(run.os, "killpg") as killpg,
        ):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "identity-unverified")
        self.assertIn({"pgid": 200, "signal": "TERM", "status": "identity-changed"}, receipt["signals"])
        killpg.assert_not_called()

    def test_root_and_shared_groups_are_never_signalled(self) -> None:
        rows = {
            100: {"pid": 100, "ppid": 1, "pgid": 100, "started": "root"},
            200: {"pid": 200, "ppid": 100, "pgid": 100, "started": "same root group"},
            300: {"pid": 300, "ppid": 100, "pgid": 900, "started": "shared caller group"},
        }
        with (
            mock.patch.object(run, "_process_snapshot", side_effect=[(rows, None), (rows, None), (rows, None)]),
            mock.patch.object(run.os, "getpgid", return_value=100),
            mock.patch.object(run.os, "getpgrp", return_value=900),
            mock.patch.object(run.os, "killpg") as killpg,
        ):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "no-detached-descendants")
        self.assertEqual(receipt["candidates"], [])
        killpg.assert_not_called()

    def test_missing_root_is_ancestry_unavailable_not_completed(self) -> None:
        with mock.patch.object(run.os, "getpgid", side_effect=ProcessLookupError):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "ancestry-unavailable-root-missing")
        self.assertEqual(receipt["signals"], [])

    def test_nonzero_process_snapshot_is_an_error(self) -> None:
        with mock.patch.object(run.subprocess, "run", return_value=SimpleNamespace(returncode=9, stdout="")):
            rows, error = run._process_snapshot(0.1)
        self.assertEqual(rows, {})
        self.assertEqual(error, "ps-exit-9")

    def test_cleanup_budget_records_remaining_groups_without_late_signals(self) -> None:
        rows = {
            100: {"pid": 100, "ppid": 1, "pgid": 100, "started": "root"},
            200: {"pid": 200, "ppid": 100, "pgid": 200, "started": "child 1"},
            300: {"pid": 300, "ppid": 100, "pgid": 300, "started": "child 2"},
        }
        with (
            mock.patch.object(run, "_process_snapshot", side_effect=[(rows, None), (rows, None)]),
            mock.patch.object(run.os, "getpgid", return_value=100),
            mock.patch.object(run.os, "getpgrp", return_value=999),
            mock.patch.object(run.os, "killpg") as killpg,
            mock.patch.object(run.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0]),
        ):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "partial-budget-exhausted")
        self.assertEqual(receipt["signals"], [])
        self.assertEqual(
            receipt["unattempted"],
            [
                {"pgid": 300, "phase": "TERM", "reason": "budget-exhausted"},
                {"pgid": 200, "phase": "TERM", "reason": "budget-exhausted"},
            ],
        )
        killpg.assert_not_called()

    def test_before_kill_snapshot_budget_expiry_records_kill_remainder(self) -> None:
        rows = {
            100: {"pid": 100, "ppid": 1, "pgid": 100, "started": "root"},
            200: {"pid": 200, "ppid": 100, "pgid": 200, "started": "child"},
        }
        with (
            mock.patch.object(run, "_process_snapshot", side_effect=[(rows, None), (rows, None)]),
            mock.patch.object(run.os, "getpgid", return_value=100),
            mock.patch.object(run.os, "getpgrp", return_value=999),
            mock.patch.object(run.os, "killpg") as killpg,
            mock.patch.object(run.time, "sleep"),
            mock.patch.object(run.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 0.0, 0.5, 1.0]),
        ):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "partial-budget-exhausted")
        self.assertEqual(receipt["signals"], [{"pgid": 200, "signal": "TERM", "status": "sent"}])
        self.assertEqual(receipt["unattempted"], [{"pgid": 200, "phase": "KILL", "reason": "budget-exhausted"}])
        killpg.assert_called_once_with(200, signal.SIGTERM)

    def test_kill_phase_budget_expiry_is_partial_after_successful_term(self) -> None:
        rows = {
            100: {"pid": 100, "ppid": 1, "pgid": 100, "started": "root"},
            200: {"pid": 200, "ppid": 100, "pgid": 200, "started": "child"},
        }
        with (
            mock.patch.object(run, "_process_snapshot", side_effect=[(rows, None), (rows, None), (rows, None)]),
            mock.patch.object(run.os, "getpgid", return_value=100),
            mock.patch.object(run.os, "getpgrp", return_value=999),
            mock.patch.object(run.os, "killpg") as killpg,
            mock.patch.object(run.time, "sleep"),
            mock.patch.object(run.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 1.0]),
        ):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "partial-budget-exhausted")
        self.assertEqual(receipt["signals"], [{"pgid": 200, "signal": "TERM", "status": "sent"}])
        self.assertEqual(receipt["unattempted"], [{"pgid": 200, "phase": "KILL", "reason": "budget-exhausted"}])
        killpg.assert_called_once_with(200, signal.SIGTERM)

    def test_signal_permission_error_is_partial_not_completed(self) -> None:
        rows = {
            100: {"pid": 100, "ppid": 1, "pgid": 100, "started": "root"},
            200: {"pid": 200, "ppid": 100, "pgid": 200, "started": "child"},
        }
        with (
            mock.patch.object(run, "_process_snapshot", side_effect=[(rows, None), (rows, None), (rows, None)]),
            mock.patch.object(run.os, "getpgid", return_value=100),
            mock.patch.object(run.os, "getpgrp", return_value=999),
            mock.patch.object(run.os, "killpg", side_effect=PermissionError),
        ):
            receipt = run._owned_descendant_cleanup(SimpleNamespace(pid=100))
        self.assertEqual(receipt["status"], "partial-signal-errors")
        self.assertEqual(
            receipt["signals"],
            [
                {"pgid": 200, "signal": "TERM", "status": "PermissionError"},
                {"pgid": 200, "signal": "KILL", "status": "PermissionError"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
