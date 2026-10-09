#!/usr/bin/env python3
"""No-model checks for the E2E harness records of 2026-10-09: the environment, the product at stop, the outcome class and the
resume defaults (SPEC: "A record of the machine, of the product at stop or of the ending is not a verdict", "A resume continues the
run's own driver").

Fake hosts and a fake browser stand in for the real ones, so nothing here starts a model, a host CLI or a real browser.  No test
reads the machine's process table (the base case patches the observer), binds a fixed port or signals a process it did not start:
the probe's own tests wrap ``os.killpg`` and fail on any group that is not a fake browser's own.  The fixtures under
test/fixtures/e2e-environment/ are compact extracts of the saved runs of 2026-10-07 and 2026-10-08 (see extract.py there).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test" / "fixtures" / "e2e-environment"
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import run  # noqa: E402


def load_base():
    """test/shiploop-e2e.test.py as a module, for its fake hosts and base cases.  It is held as `base` and never imported
    by name into this namespace, so unittest does not collect its test classes a second time."""
    path = ROOT / "test" / "shiploop-e2e.test.py"
    spec = importlib.util.spec_from_file_location("shiploop_e2e_base_tests", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = load_base()


class QuietHarnessCase(base.PrintedCase):
    """A harness case with git isolated, and no real browser reachable by autodetection."""

    def setUp(self):
        super().setUp()
        base.isolate_git(self)
        environment = sys.modules.get("environment")
        if environment is not None and hasattr(environment, "autodetect_browser"):
            patch = mock.patch.object(environment, "autodetect_browser", return_value=None)
            patch.start()
            self.addCleanup(patch.stop)

    def blocked_workspace(self, out: Path, *, worktree_files: dict | None = None, state: dict | None = None) -> Path:
        """An engine that blocked itself out of band, beside a worktree holding `worktree_files`."""
        shutil.rmtree(out / "work" / ".shiploop", ignore_errors=True)
        workspace = out / ".shiploop-runs" / "w1"
        (workspace / "run").mkdir(parents=True)
        run.store.write_record(workspace / "run" / "state.md",
                               state or {"status": "blocked", "stage": "test-refine", "status_reason": "access: waiting"})
        if worktree_files is not None:
            (workspace / "worktree").mkdir()
            for name, text in worktree_files.items():
                (workspace / "worktree" / name).write_text(text)
        return workspace

    def first_run(self, *extra: str) -> Path:
        """A Grok run whose first session ended without a ShipLoop state and was not resumed: the base of a regrade."""
        code, result, _ = self.invoke_printed("grok", "nothing", "--max-resumes", "0", *extra)
        return Path(result["output"])

    def grade_only(self, out: Path, *extra: str) -> tuple[int, dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out), "--grade-only",
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()


class ProductAtStopTest(QuietHarnessCase):
    """The case checks run against ShipLoop's unreturned worktree: information only, labelled, with return codes."""

    CHECKS = ("--check", "test -f product.txt", "--check", "grep -q good product.txt")

    def blocked_run(self, files: dict | None, *extra: str) -> tuple[Path, dict, str]:
        out = self.first_run("--prompt", "build it", *self.CHECKS)
        self.blocked_workspace(out, worktree_files=files)
        self.log.unlink(missing_ok=True)
        code, result, printed = self.grade_only(out, *extra)
        self.assertEqual(code, 1)
        return out, result, printed

    def test_checks_run_against_the_unreturned_worktree_and_are_recorded_with_their_return_codes(self):
        _, result, _ = self.blocked_run({"product.txt": "bad\n"})
        stop = result["product_at_stop"]
        self.assertTrue(stop["information_only"])
        self.assertTrue(stop["ran"])
        self.assertEqual(stop["engine"], {"status": "blocked", "stage": "test-refine"})
        self.assertTrue(stop["worktree"].endswith("/.shiploop-runs/w1/worktree"))
        self.assertEqual([(c["command"], c["pass"], c["returncode"], c["timed_out"]) for c in stop["checks"]],
                         [("test -f product.txt", True, 0, False), ("grep -q good product.txt", False, 1, False)])
        self.assertEqual((stop["passed"], stop["failed"], stop["timed_out"], stop["total"]), (1, 1, 0, 2))
        self.assertNotIn("output", stop["checks"][0], "a passing check keeps no output")
        self.assertIn("output", stop["checks"][1])

    def test_the_run_is_not_given_a_verdict_by_it_and_the_old_key_is_gone(self):
        _, result, _ = self.blocked_run({"product.txt": "good\n"})
        self.assertEqual(result["product_at_stop"]["passed"], 2)  # every check passes in the worktree ...
        self.assertFalse(result["pass"])  # ... and the run still does not pass (SPEC S-11)
        self.assertEqual([c["pass"] for c in result["checks"]], [False, False])  # work/ holds no product
        self.assertNotIn("worktree_checks", result["shiploop"])

    def test_a_check_that_times_out_is_timed_out_and_not_a_product_failure(self):
        with mock.patch.object(run, "PRODUCT_AT_STOP_TIMEOUT", 1):
            out = self.first_run("--prompt", "build it", "--check", "test -f product.txt && exec sleep 20")
            self.blocked_workspace(out, worktree_files={"product.txt": "x\n"})
            start = time.time()
            _, result, _ = self.grade_only(out)
        self.assertLess(time.time() - start, 15, "the check was stopped at its timeout")
        stop = result["product_at_stop"]
        (check,) = stop["checks"]
        self.assertEqual((check["pass"], check["returncode"], check["timed_out"]), (False, None, True))
        self.assertEqual((stop["passed"], stop["failed"], stop["timed_out"], stop["total"]), (0, 0, 1, 1))

    def test_no_worktree_is_a_measured_not_run_with_its_reason(self):
        _, result, _ = self.blocked_run(None)
        self.assertEqual(result["product_at_stop"], {
            "information_only": True, "ran": False, "reason": "no worktree directory under the run's workspace",
            "engine": {"status": "blocked", "stage": "test-refine"}})

    def test_a_run_with_no_shiploop_state_says_so_not_that_a_worktree_is_missing(self):
        code, result, _ = self.invoke_printed("grok", "nothing", "--max-resumes", "0", "--prompt", "build it", *self.CHECKS)
        self.assertEqual(code, 1)
        self.assertEqual(result["product_at_stop"]["reason"], "no ShipLoop state.md under the output directory")
        self.assertFalse(result["product_at_stop"]["ran"])
        self.assertEqual(result["product_at_stop"]["engine"], {"status": "unknown", "stage": "unknown"})

    def test_a_case_with_no_checks_has_nothing_to_run(self):
        out = self.first_run("--prompt", "build it")
        self.blocked_workspace(out, worktree_files={})
        _, result, _ = self.grade_only(out)
        self.assertEqual(result["product_at_stop"]["reason"], "the case declares no checks")

    def test_a_run_that_passed_has_no_product_at_stop(self):
        code, result, _ = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertNotIn("product_at_stop", result)

    def test_the_printed_report_labels_it_information_only_with_the_engine_position(self):
        _, _, printed = self.blocked_run({"product.txt": "bad\n"})
        line = next(ln for ln in printed.splitlines() if "product at stop" in ln)
        self.assertIn("information only", line)
        self.assertIn("1/2", line)
        self.assertIn("blocked at test-refine", line)

    def test_the_follow_on_environment_reaches_the_checks(self):
        shiploop = {"pass": False, "worktree": str(self.tmp)}
        stop = run.product_at_stop(shiploop, {"status": "blocked", "stage": "x"},
                                   ['test -d "$PRIOR_WORK"'], {"PRIOR_WORK": str(self.tmp)})
        self.assertEqual((stop["passed"], stop["total"]), (1, 1))

    def test_a_computation_that_raises_is_recorded_and_changes_nothing(self):
        out = self.first_run("--prompt", "build it", *self.CHECKS)
        self.blocked_workspace(out, worktree_files={"product.txt": "x\n"})
        with mock.patch.object(run, "product_at_stop", side_effect=RuntimeError("boom")):
            code, result, _ = self.grade_only(out)
        self.assertEqual(code, 1)
        self.assertFalse(result["product_at_stop"]["ran"])
        self.assertIn("boom", result["product_at_stop"]["reason"])


if __name__ == "__main__":
    unittest.main()
