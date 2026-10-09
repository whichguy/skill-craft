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
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "test" / "fixtures" / "e2e-environment"
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import run  # noqa: E402

# The real group signal, kept before any test wraps it: the cleanups end what a test started with this, never with a wrapper.
REAL_KILLPG = os.killpg


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

    def test_the_follow_on_environment_reaches_the_product_at_stop_checks_through_main(self):
        prior = self.tmp / "prior"
        (prior / "work").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(prior / "work")], check=True)
        (prior / "work" / "prior.txt").write_text("kept\n")
        (prior / "result.json").write_text(json.dumps({"case": "hello", "pass": True}))
        out = self.first_run("--continue-from", str(prior), "--prompt", "Add a feature.",
                             "--check", 'test -f "$PRIOR_WORK/prior.txt"')
        self.blocked_workspace(out, worktree_files={})
        _, result, _ = self.grade_only(out)
        stop = result["product_at_stop"]
        self.assertEqual((stop["passed"], stop["total"]), (1, 1), "the check sees $PRIOR_WORK in the worktree run too")

    def test_a_computation_that_raises_is_recorded_and_changes_nothing(self):
        out = self.first_run("--prompt", "build it", *self.CHECKS)
        self.blocked_workspace(out, worktree_files={"product.txt": "x\n"})
        with mock.patch.object(run, "product_at_stop", side_effect=RuntimeError("boom")):
            code, result, _ = self.grade_only(out)
        self.assertEqual(code, 1)
        self.assertFalse(result["product_at_stop"]["ran"])
        self.assertIn("boom", result["product_at_stop"]["reason"])


def import_environment():
    """test/shiploop_e2e/environment.py, imported where it is used so a missing module fails only the tests about it."""
    import environment
    return environment


class OwnProcesses:
    """Mixin: a test that starts processes ends exactly those, and no others, whatever the code under test did."""

    def setUp(self):
        super().setUp()
        self._started: list[subprocess.Popen] = []
        self.addCleanup(self._end_started)

    def start_bystander(self) -> subprocess.Popen:
        """A process in a session of its own that the code under test has no business signalling (it ends itself in 25 s)."""
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(25)"], start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._started.append(proc)
        return proc

    def _end_started(self) -> None:
        for proc in self._started:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                REAL_KILLPG(proc.pid, signal.SIGKILL) if os.getpgid(proc.pid) == proc.pid else None
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)


# A fake browser: `--version` prints a version; otherwise it loads the URL it is given (a file: path or a loopback http page,
# as --dump-dom does), prints the page, and behaves as FAKE_BROWSER_MODE says. It logs its argv and group, and ends itself
# by SIGALRM after 25 s, so nothing a failing test leaves outlives the test by more than that.
FAKE_BROWSER = f"""#!{sys.executable}
import json, os, signal, sys, time
signal.alarm(25)
argv = sys.argv[1:]
def note(**kw):
    if os.environ.get("FAKE_BROWSER_LOG"):
        with open(os.environ["FAKE_BROWSER_LOG"], "a") as log:
            log.write(json.dumps(dict(kw, pid=os.getpid(), pgid=os.getpgrp())) + "\\n")
if argv == ["--version"]:
    print("Fake Browser 1.2.3")
    sys.exit(0)
url = argv[-1]
kind = "file" if url.startswith("file:") else "http"
mode = os.environ.get("FAKE_BROWSER_MODE_" + kind.upper()) or os.environ.get("FAKE_BROWSER_MODE", "linger")
note(argv=argv, url=url, kind=kind, mode=mode, home=os.environ.get("HOME"), t=time.time())
if mode == "silent":
    time.sleep(30)
if mode == "crash":
    print("no display", file=sys.stderr)
    sys.exit(3)
if mode == "escape":
    # A helper that left the browser's group and still holds its output open, as a detached crash reporter could.
    import subprocess
    child = subprocess.Popen([sys.executable, "-c", "import signal, time; signal.alarm(8); time.sleep(30)"],
                             start_new_session=True, stdin=subprocess.DEVNULL, stdout=sys.stdout)
    note(child=child.pid)
if kind == "file":
    from urllib.parse import unquote, urlparse
    page = open(unquote(urlparse(url).path)).read()
else:
    import urllib.request
    page = urllib.request.build_opener(urllib.request.ProxyHandler({{}})).open(url, timeout=5).read().decode()
print(page, flush=True)
if mode == "linger":
    time.sleep(30)
if mode == "slow-exit":
    time.sleep(0.5)
sys.exit(0)
"""


class BrowserFixture(OwnProcesses):
    """A fake browser on disk and its log; the groups it leaves are ended after the test."""

    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.browser = self.dir / "fake-browser"
        self.browser.write_text(FAKE_BROWSER)
        self.browser.chmod(self.browser.stat().st_mode | stat.S_IXUSR)
        self.log = self.dir / "browser-log.jsonl"
        patched = mock.patch.dict(os.environ, {"FAKE_BROWSER_LOG": str(self.log)})
        patched.start()
        self.addCleanup(patched.stop)
        self.addCleanup(self._end_browsers)
        self.environment = import_environment()
        # Every test of the probe runs with the group signal guarded: a group that is not a fake browser's own (or is this
        # test process's) is recorded and never sent, and the test fails on it afterwards.
        self.signalled, self.stray, self.started = [], [], set()
        real_popen = subprocess.Popen

        def recording_popen(*args, **kw):
            """Notes the pid of each fake browser the code under test starts (before the fake has written its log line)."""
            made = real_popen(*args, **kw)
            argv = args[0] if args else kw.get("args")
            if isinstance(argv, list) and argv and argv[0] == str(self.browser) and "--dump-dom" in argv:
                self.started.add(made.pid)
            return made

        def guarded(group, number):
            if number == 0:
                return REAL_KILLPG(group, number)  # asking whether a group is empty signals nothing
            self.signalled.append(group)
            own = self.started | {entry["pgid"] for entry in self.launches()}
            if group == os.getpgrp() or group not in own:
                self.stray.append(group)
                return None
            return REAL_KILLPG(group, number)

        popen_patch = mock.patch.object(subprocess, "Popen", recording_popen)
        guard = mock.patch.object(os, "killpg", guarded)
        popen_patch.start()
        guard.start()
        self.addCleanup(self._no_stray_signal)
        self.addCleanup(guard.stop)
        self.addCleanup(popen_patch.stop)

    def _no_stray_signal(self) -> None:
        self.assertEqual(self.stray, [], "a group that is not a fake browser's own was signalled")

    def launches(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def _end_browsers(self) -> None:
        """Whatever fake browser the code under test left, by the pid it logged and only if it still leads its group."""
        for entry in self.launches():
            for pid in (entry["pid"], entry.get("child")):
                with contextlib.suppress(ProcessLookupError, PermissionError, TypeError):
                    if os.getpgid(pid) == pid:
                        REAL_KILLPG(pid, signal.SIGKILL)

    def alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True


class BrowserProbeTest(BrowserFixture, unittest.TestCase):
    """SPEC: the browser capability record. Success is the page title read from the browser's output, not its exit."""

    def probe(self, **kw) -> dict:
        return self.environment.browser_record(str(self.browser), ceiling=kw.pop("ceiling", 4.0), grace=kw.pop("grace", 0.3), **kw)

    def test_the_title_is_the_evidence_and_a_browser_that_lingers_after_printing_it_is_recorded_as_such(self):
        start = time.monotonic()
        record = self.probe()
        elapsed = time.monotonic() - start
        self.assertTrue(record["declared"] and record["probed"])
        for kind in ("file", "http"):
            with self.subTest(kind=kind):
                target = record[kind]
                self.assertTrue(target["title_seen"], target)
                self.assertFalse(target["exited"])
                self.assertTrue(target["lingered"])
                self.assertTrue(target["killed"])
                self.assertLess(target["output_s"], 2.0)
                self.assertTrue(target["group_empty"])
        self.assertLess(elapsed, 3.0, "the probe stopped at the title plus the grace, not at the ceiling")
        for entry in self.launches():
            self.assertFalse(self.alive(entry["pid"]), "the lingering browser was stopped")

    def test_a_browser_that_prints_the_title_and_exits_by_itself_is_not_killed_or_called_lingering(self):
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "exit"}):
            record = self.probe()
        for kind in ("file", "http"):
            target = record[kind]
            self.assertEqual((target["title_seen"], target["exited"], target["lingered"], target["killed"], target["returncode"]),
                             (True, True, False, False, 0), kind)

    def test_a_browser_that_exits_within_the_grace_is_not_killed_and_one_that_outlasts_it_is(self):
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "slow-exit"}):
            patient = self.probe(grace=3.0)
            impatient = self.probe(grace=0.1)
        for kind in ("file", "http"):
            self.assertEqual((patient[kind]["exited"], patient[kind]["lingered"], patient[kind]["killed"]), (True, False, False), kind)
            self.assertEqual((impatient[kind]["exited"], impatient[kind]["lingered"], impatient[kind]["killed"]),
                             (False, True, True), kind)

    def test_a_browser_that_loads_the_file_and_hangs_on_loopback_is_recorded_per_kind(self):
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE_FILE": "linger", "FAKE_BROWSER_MODE_HTTP": "silent"}):
            start = time.monotonic()
            record = self.probe(ceiling=1.5)
            elapsed = time.monotonic() - start
        self.assertTrue(record["file"]["title_seen"])
        http = record["http"]
        self.assertEqual((http["title_seen"], http["output_s"], http["exited"], http["lingered"], http["killed"]),
                         (False, None, False, False, True))
        self.assertGreaterEqual(elapsed, 1.4, "a launch that never prints is waited for up to the ceiling")
        self.assertLess(elapsed, 5.0)
        for entry in self.launches():
            self.assertFalse(self.alive(entry["pid"]))

    def test_the_two_kinds_are_probed_one_after_the_other_so_each_browser_runs_beside_no_other_probe_browser(self):
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "silent"}):
            start = time.monotonic()
            record = self.probe(ceiling=1.5)
            elapsed = time.monotonic() - start
        first, second = sorted(self.launches(), key=lambda entry: entry["t"])
        self.assertEqual((first["kind"], second["kind"]), ("file", "http"))
        self.assertGreaterEqual(second["t"] - first["t"], 1.4, "the second browser started after the first had been waited for")
        self.assertGreaterEqual(elapsed, 2.9)
        self.assertFalse(record["file"]["title_seen"] or record["http"]["title_seen"])
        self.assertTrue(record["file"]["killed"] and record["http"]["killed"])

    def test_a_helper_that_left_the_group_and_keeps_the_output_open_does_not_hang_the_probe(self):
        # Closing a pipe that a thread is still reading blocks until the pipe closes: with this helper holding it for 8 s,
        # a probe that closes it at the end would take 8 s, before the host has even started.
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "escape"}):
            start = time.monotonic()
            record = self.probe()
            elapsed = time.monotonic() - start
        self.assertLess(elapsed, 6.0)
        for kind in ("file", "http"):
            self.assertTrue(record[kind]["title_seen"], kind)
            self.assertTrue(record[kind]["group_empty"], "the helper is not in the browser's group, and the group is empty")

    def test_a_browser_that_dies_without_output_is_not_a_title_and_its_exit_code_is_kept(self):
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "crash"}):
            record = self.probe()
        target = record["http"]
        self.assertEqual((target["title_seen"], target["exited"], target["returncode"], target["killed"]), (False, True, 3, False))

    def test_the_probe_signals_only_the_group_it_started_and_a_bystander_is_left_alone(self):
        bystander = self.start_bystander()
        self.probe()
        self.assertTrue(self.signalled, "a lingering browser was stopped through its group")
        self.assertEqual(self.stray, [], "every group signalled was a fake browser's own")
        self.assertIsNone(bystander.poll(), "a process the probe did not start was not touched")
        self.assertTrue(self.alive(bystander.pid))

    def test_a_guard_that_sees_a_wrong_group_records_it_and_sends_nothing(self):
        # The guard itself: a mutant that signals a group the probe did not start is caught by the fixture, not by luck.
        bystander = self.start_bystander()
        os.killpg(os.getpgid(bystander.pid), signal.SIGKILL)  # the wrapper: this group is not a fake browser's
        self.assertEqual(self.stray, [os.getpgid(bystander.pid)])
        self.assertTrue(self.alive(bystander.pid), "a stray signal is recorded and not sent")
        self.stray.clear()

    def test_the_browser_runs_with_a_throwaway_profile_and_the_hygiene_flags(self):
        self.probe()
        launches = self.launches()
        self.assertEqual(sorted(entry["kind"] for entry in launches), ["file", "http"])
        for entry in launches:
            argv = entry["argv"]
            profile = next(arg.split("=", 1)[1] for arg in argv if arg.startswith("--user-data-dir="))
            self.assertTrue(os.path.realpath(profile).startswith(os.path.realpath(tempfile.gettempdir())), profile)
            self.assertFalse(Path(profile).exists(), "the throwaway profile is removed")
            for flag in ("--headless=new", "--disable-gpu", "--no-first-run", "--dump-dom", "--disable-background-networking",
                         "--disable-default-apps", "--disable-component-update", "--disable-sync"):
                self.assertIn(flag, argv)
            self.assertEqual(argv[-1], entry["url"])

    def test_both_stand_ins_serve_the_page_whose_title_the_record_looks_for(self):
        record = self.probe()
        urls = {entry["kind"]: entry["url"] for entry in self.launches()}
        self.assertTrue(urls["file"].startswith("file://"))
        self.assertRegex(urls["http"], r"^http://127\.0\.0\.1:\d+/")
        self.assertTrue(record["file"]["title_seen"] and record["http"]["title_seen"])

    def test_the_stand_in_asks_the_system_for_its_port(self):
        asked = []
        real = self.environment.http.server.ThreadingHTTPServer

        class Recording(real):
            def __init__(inner, address, *args, **kw):
                asked.append(address)
                super().__init__(address, *args, **kw)

        with mock.patch.object(self.environment.http.server, "ThreadingHTTPServer", Recording):
            self.probe()
        self.assertEqual(asked, [("127.0.0.1", 0)], "a loopback listener on a port the system chooses, never a fixed one")

    def test_the_record_says_the_three_times_it_used(self):
        record = self.probe(ceiling=3.5, grace=0.4)
        self.assertEqual((record["ceiling_seconds"], record["grace_seconds"]), (3.5, 0.4))
        self.assertEqual(record["empty_seconds"], self.environment.EMPTY_SECONDS)
        self.assertEqual((record["file"]["interrupted"], record["http"]["interrupted"]), (False, False))

    def test_group_empty_is_what_the_group_check_says_after_the_stop(self):
        with mock.patch.object(self.environment, "EMPTY_SECONDS", 0.3), \
                mock.patch.object(self.environment, "_group_alive", return_value=True):
            stuck = self.probe()
        self.assertEqual((stuck["file"]["group_empty"], stuck["http"]["group_empty"]), (False, False))
        with mock.patch.object(self.environment, "_group_alive", return_value=False):
            gone = self.probe()
        self.assertEqual((gone["file"]["group_empty"], gone["http"]["group_empty"]), (True, True))

    def test_the_reader_thread_ends_and_the_pipe_is_closed_even_when_a_helper_holds_the_output_open(self):
        threads, procs = [], []
        real_thread, real_popen = self.environment.threading.Thread, self.environment.subprocess.Popen

        def thread(*args, **kw):
            made = real_thread(*args, **kw)
            threads.append(made)
            return made

        def popen(*args, **kw):
            made = real_popen(*args, **kw)
            procs.append(made)
            return made

        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "escape"}), \
                mock.patch.object(self.environment.threading, "Thread", thread), \
                mock.patch.object(self.environment.subprocess, "Popen", popen):
            self.probe()
        browsers = [made for made in procs if made.args[0] == str(self.browser) and "--dump-dom" in made.args]
        self.assertEqual(len(browsers), 2)
        self.assertTrue(all(made.stdout.closed for made in browsers), "the pipe was closed")
        self.assertFalse(any(made.is_alive() for made in threads), "no reader thread was left running")

    def test_a_probe_that_cannot_confirm_its_group_still_ends_the_browser(self):
        with mock.patch.object(self.environment.os, "getpgid", side_effect=PermissionError("denied")):
            record = self.probe()
        self.assertTrue(record["probed"], record)
        self.assertEqual(len(self.started), 2)
        for pid in self.started:
            self.assertFalse(self.alive(pid), "the browser was ended by its pid when its group could not be confirmed")
        self.assertTrue(record["file"]["killed"])

    def test_the_harness_ending_its_live_hosts_ends_a_probe_browser_too(self):
        result = {}
        url = (self.dir / "page.html").as_uri()

        def probe():
            result["record"] = self.environment.probe_target(str(self.browser), url, "token", 8.0, 0.3)

        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "silent"}):
            worker = threading.Thread(target=probe)
            worker.start()
            for _ in range(100):
                if self.launches():
                    break
                time.sleep(0.05)
            self.assertTrue(self.launches(), "the browser started")
            start = time.monotonic()
            run.end_live_hosts()  # what a SIGTERM to the harness and the exit-time hook both do
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertLess(time.monotonic() - start, 4.0, "the probe did not wait out its 8 s ceiling")
        self.assertFalse(self.alive(self.launches()[0]["pid"]))
        self.assertFalse(self.environment.LIVE_PROBE_GROUPS, "a finished probe leaves nothing registered")

    def test_a_probe_told_to_stop_during_the_grace_ends_the_browser_and_does_not_call_it_lingering(self):
        stop = threading.Event()
        threading.Timer(0.8, stop.set).start()
        # A browser that prints the title and lingers, with a 3 s grace the stop request cuts short.
        with self.environment.StandIn() as page:
            start = time.monotonic()
            record = self.environment.probe_target(str(self.browser), page.file_url, page.token, 4.0, 3.0, stop.is_set)
            elapsed = time.monotonic() - start
        self.assertTrue(record["title_seen"])
        self.assertTrue(record["interrupted"])
        self.assertFalse(record["lingered"], "a browser stopped by the harness did not outlast the grace")
        self.assertLess(elapsed, 2.5, "the 3 s grace was cut short")
        for pid in self.started:
            self.assertFalse(self.alive(pid))

    def test_an_exception_while_the_probe_waits_still_ends_the_browser_and_removes_its_files(self):
        def boom():
            raise RuntimeError("the wait failed")

        before = set(Path(tempfile.gettempdir()).glob("e2e-browser-profile-*"))
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "silent"}):
            with self.assertRaises(RuntimeError):
                self.environment.probe_target(str(self.browser), (self.dir / "page.html").as_uri(), "token", 8.0, 0.3, boom)
        self.assertEqual(len(self.started), 1)
        for pid in self.started:
            self.assertFalse(self.alive(pid), "the browser was ended by the probe's finally")
        self.assertFalse(self.environment.LIVE_PROBE_GROUPS)
        self.assertEqual(set(Path(tempfile.gettempdir()).glob("e2e-browser-profile-*")), before, "the throwaway profile was removed")

    def test_a_probe_told_to_stop_ends_the_browser_at_once_and_skips_the_target_after_it(self):
        stop = threading.Event()
        threading.Timer(0.5, stop.set).start()
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "silent"}):
            start = time.monotonic()
            record = self.probe(ceiling=6.0, should_stop=stop.is_set)
            elapsed = time.monotonic() - start
        self.assertLess(elapsed, 3.0)
        self.assertTrue(record["file"]["interrupted"])
        self.assertEqual(record["http"]["probed"], False)
        self.assertIn("told to end", record["http"]["reason"])
        self.assertEqual(len(self.started), 1, "the second browser was never started")
        for pid in self.started:
            self.assertFalse(self.alive(pid))

    def test_the_stand_in_server_is_closed_after_the_probe_and_after_a_failure(self):
        made = []

        class Recording(self.environment.StandIn):
            def __enter__(inner):
                made.append(inner)
                return super().__enter__()

        with mock.patch.object(self.environment, "StandIn", Recording):
            self.probe()
            self.assertEqual(len(made), 1)
            self.assertEqual(made[0].server.socket.fileno(), -1, "the listener is closed")
            with mock.patch.object(self.environment, "probe_target", side_effect=RuntimeError("boom")):
                record = self.probe()
        self.assertEqual(made[1].server.socket.fileno(), -1, "closed in finally, even when a part raised")
        self.assertFalse(record["probed"])
        self.assertIn("boom", record["reason"])

    def test_the_version_is_read_from_the_browser_itself(self):
        self.assertEqual(self.probe()["version"], "Fake Browser 1.2.3")

    def test_a_browser_that_is_not_there_is_absent_and_never_a_pass(self):
        record = self.environment.browser_record(str(self.dir / "no-such-browser"), ceiling=1, grace=0.1)
        self.assertEqual((record["declared"], record["probed"]), (True, False))
        self.assertIn("no browser binary", record["reason"])
        self.assertNotIn("file", record)
        with mock.patch.object(self.environment, "autodetect_browser", return_value=None):
            self.assertFalse(self.environment.browser_record(None, ceiling=1, grace=0.1)["probed"])
        self.assertEqual(self.launches(), [])

    def test_an_undeclared_browser_is_not_probed_and_says_so(self):
        record = self.environment.start_record(display_hold=False, needs=(), browser_bin=str(self.browser))
        self.assertEqual(record["browser"], {"declared": False, "probed": False,
                                             "reason": "no case or --need declares a browser"})
        self.assertEqual(self.launches(), [], "no browser was started")

    def test_a_declared_browser_is_probed_by_the_start_record(self):
        record = self.environment.start_record(display_hold=True, needs=("browser",), browser_bin=str(self.browser))
        self.assertTrue(record["browser"]["probed"])
        self.assertTrue(record["browser"]["file"]["title_seen"])

    def test_the_two_times_are_ceilings_and_say_so(self):
        source = (ROOT / "test" / "shiploop_e2e" / "environment.py").read_text()
        self.assertIn("a ceiling, not a tuning value", " ".join(source.split()))


class GroupKillTest(OwnProcesses, unittest.TestCase):
    """listeners.end_group, the harness's one group kill (batch 1011 integration): a group is signalled only while its number is
    still its leader's (a running leader that leads its group, or an exited leader not yet reaped), never after a reap. Every
    process here is this test's own child; the signal is recorded through a wrapper that passes it on to the real one."""

    def setUp(self):
        super().setUp()
        import listeners
        self.listeners = listeners
        self.dir = Path(tempfile.mkdtemp(prefix="e2e-group-kill-"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.sent: list[tuple[int, int]] = []

        def recording(group, number):
            if number:
                self.sent.append((group, number))
            return REAL_KILLPG(group, number)

        patched = mock.patch.object(os, "killpg", recording)
        patched.start()
        self.addCleanup(patched.stop)

    def leader(self, script: str, own_session: bool = True) -> tuple[subprocess.Popen, int | None]:
        """A shell running ``script``; a background member it starts writes its pid to a file (None when it starts none)."""
        note = self.dir / f"member-{len(self._started)}"
        proc = subprocess.Popen(["/bin/sh", "-c", script.replace("NOTE", str(note))], start_new_session=own_session,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._started.append(proc)
        if "NOTE" not in script:
            return proc, None
        for _ in range(100):
            if note.exists() and note.read_text().strip():
                return proc, int(note.read_text())
            time.sleep(0.05)
        self.fail("the group member did not start")

    @staticmethod
    def gone(pid: int) -> bool:
        for _ in range(60):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.05)
        return False

    def test_a_running_leader_of_its_own_group_has_the_whole_group_ended(self):
        proc, member = self.leader("sleep 20 & echo $! > NOTE; wait")
        self.assertTrue(self.listeners.end_group(proc.pid))
        self.assertEqual(proc.wait(timeout=5), -signal.SIGKILL)
        self.assertEqual(self.sent, [(proc.pid, signal.SIGKILL)])
        self.assertTrue(self.gone(member), "the member the leader started shares its group and was ended with it")

    def test_an_exited_leader_that_is_not_yet_reaped_still_has_its_group_ended(self):
        # The leader is a zombie that keeps its pid, so the number cannot be someone else's yet, and what it left shares the group.
        # (On macOS getpgid raises for such a zombie while killpg still reaches the group: the leader check is for a running one.)
        proc, member = self.leader("sleep 20 & echo $! > NOTE; exit 0")
        for _ in range(100):
            if os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT):
                break
            time.sleep(0.05)
        self.assertIsNone(proc.returncode, "not reaped")
        self.assertTrue(self.listeners.end_group(proc.pid))
        self.assertTrue(self.gone(member))
        self.assertEqual(proc.wait(timeout=5), 0, "the leader's own exit status is kept")

    def test_a_reaped_leader_is_never_signalled(self):
        proc, _ = self.leader("exit 0")
        proc.wait(timeout=5)
        self.assertFalse(self.listeners.end_group(proc.pid))
        self.assertEqual(self.sent, [], "after a reap the number may be another group's")

    def test_a_running_child_that_does_not_lead_its_own_group_is_never_signalled(self):
        proc, _ = self.leader("sleep 20", own_session=False)  # in this test's own group
        try:
            self.assertFalse(self.listeners.end_group(proc.pid))
            self.assertEqual(self.sent, [])
            self.assertIsNone(proc.poll())
        finally:
            proc.kill()
            proc.wait(timeout=5)

    def test_a_process_that_is_not_this_process_s_child_is_never_signalled(self):
        self.assertFalse(self.listeners.end_group(os.getppid()))
        self.assertEqual(self.sent, [])

    def test_every_group_kill_in_the_harness_is_this_one(self):
        # S-12, one implementation: outside listeners.py a harness module may ask whether a group is empty (signal 0), never send.
        for path in sorted((ROOT / "test" / "shiploop_e2e").glob("*.py")):
            if path.name == "listeners.py":
                continue
            for call in re.findall(r"killpg\(([^()]*(?:\([^()]*\))?[^()]*)\)", path.read_text()):
                with self.subTest(module=path.name, call=call):
                    self.assertTrue(call.replace(" ", "").endswith(",0"), f"{path.name} sends a group signal itself: {call}")
        self.assertFalse(hasattr(run, "kill_group"), "run ends its hosts through listeners.end_group")
        self.assertFalse(hasattr(import_environment(), "_signal_group"), "the probe ends its browser through listeners.end_group")

    def test_the_harness_s_callers_end_their_groups_through_it(self):
        ended = []
        with mock.patch.object(self.listeners, "end_group", side_effect=lambda pid: ended.append(pid) or False), \
                mock.patch.object(run, "LIVE_HOST_GROUPS", {101}), \
                mock.patch.object(import_environment(), "LIVE_PROBE_GROUPS", {202}):
            run.end_live_hosts()
        self.assertEqual(sorted(ended), [101, 202])
        import hosts
        calls = []
        real = self.listeners.end_group
        with mock.patch.object(self.listeners, "end_group", side_effect=lambda pid: calls.append(pid) or real(pid)):
            done = hosts.run_agent(["/bin/sh", "-c", "sleep 20 & wait"], self.dir, dict(os.environ), self.dir / "events.jsonl",
                                   self.dir / "stderr.txt", timeout=1)
        self.assertEqual(done["status"], "timeout")
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.sent, [(calls[0], signal.SIGKILL)])


class ToolsAndMachineTest(OwnProcesses, unittest.TestCase):
    """The tool versions the model's shell sees, and the machine at the start and at the end."""

    def setUp(self):
        super().setUp()
        self.environment = import_environment()
        saved = self.environment._TOOLS  # read once per process: a test that reads them starts from nothing read
        self.addCleanup(setattr, self.environment, "_TOOLS", saved)
        self.environment._TOOLS = None
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.bin = Path(tmp.name)
        patched = mock.patch.dict(os.environ, {"PATH": str(self.bin)})
        patched.start()
        self.addCleanup(patched.stop)

    def tool(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(f"#!{sys.executable}\nimport sys\n{body}\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def test_a_version_is_the_first_stdout_line_and_the_tool_runs_with_standard_input_closed(self):
        # The tool reads its input first: it answers only if it sees end of file at once (SPEC S-14: nothing waits on a person).
        self.tool("node", "sys.stdin.read()\nprint('v99.1.0')\nprint('second line')")
        self.tool("git", "sys.stdin.read()\nprint('git version 9.9.9')")
        with mock.patch.object(self.environment.subprocess, "run", wraps=subprocess.run) as spy:
            versions, unread = self.environment.read_tools()
        self.assertEqual((versions["node"], versions["git"]), ("v99.1.0", "git version 9.9.9"))
        self.assertTrue(spy.call_args_list and all(call.kwargs["stdin"] is subprocess.DEVNULL for call in spy.call_args_list))

    def test_a_tool_that_is_missing_is_null_with_its_reason_and_never_an_empty_string(self):
        self.tool("node", "print('v1')")
        versions, unread = self.environment.read_tools()
        self.assertIsNone(versions["python3"])
        self.assertEqual(unread["python3"], "not found on PATH")
        self.assertNotIn("node", unread)

    def test_a_tool_that_hangs_or_fails_is_null_with_a_reason(self):
        self.tool("node", "import time\ntime.sleep(20)")
        self.tool("git", "print('boom', file=sys.stderr)\nsys.exit(4)")
        self.tool("python3", "sys.exit(0)")  # exits 0 and prints nothing
        with mock.patch.object(self.environment, "TOOL_TIMEOUT", 0.5):
            versions, unread = self.environment.read_tools()
        self.assertEqual(versions, {"node": None, "python3": None, "git": None})
        self.assertIn("timed out", unread["node"])
        self.assertEqual(unread["git"], "--version exited 4")
        self.assertEqual(unread["python3"], "--version printed nothing on stdout")

    def test_the_versions_are_read_once_per_process(self):
        calls = []

        def counting():
            calls.append(1)
            return {"node": "v1", "python3": "Python 3", "git": "git version 2"}, {}

        saved = self.environment._TOOLS
        self.addCleanup(setattr, self.environment, "_TOOLS", saved)
        self.environment._TOOLS = None
        with mock.patch.object(self.environment, "read_tools", counting):
            first = self.environment.start_record(display_hold=False)
            second = self.environment.start_record(display_hold=False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(first["tools"], second["tools"])

    def test_the_start_record_has_the_machine_the_display_hold_and_says_what_it_could_not_read(self):
        record = self.environment.start_record(display_hold=True)
        self.assertEqual(record["observed"], True)
        self.assertRegex(record["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIs(record["display_hold"], True)
        self.assertIsInstance(record["cpus"], int)
        self.assertEqual(len(record["loadavg"]), 3)
        self.assertEqual(set(record["tools"]), {"node", "python3", "git"})
        self.assertEqual(set(record["unread"]), {"node", "python3", "git"}, "this PATH holds none of the three")
        self.assertEqual(record["browser"], {"declared": False, "probed": False,
                                             "reason": "no case or --need declares a browser"})

    def test_a_machine_that_will_not_say_is_null_with_the_reason_and_not_zero(self):
        with mock.patch.object(os, "getloadavg", side_effect=OSError("not here")), \
                mock.patch.object(os, "cpu_count", return_value=None):
            record = self.environment.end_record()
        self.assertEqual((record["cpus"], record["loadavg"]), (None, None))
        self.assertIn("not here", record["unread"]["loadavg"])
        self.assertIn("cpu_count", record["unread"]["cpus"])

    def test_the_end_record_reads_the_machine_again_and_not_the_tools(self):
        record = self.environment.end_record()
        self.assertNotIn("tools", record)
        self.assertEqual(record["unread"], {})
        self.assertEqual(len(record["loadavg"]), 3)

    def test_the_display_hold_has_one_decider_keep_awake(self):
        with mock.patch.object(run.sys, "platform", "darwin"), \
                mock.patch.object(run.shutil, "which", return_value="/usr/bin/caffeinate"):
            self.assertTrue(run.display_held())
        with mock.patch.object(run.sys, "platform", "linux"):
            self.assertFalse(run.display_held())


class OverlapTest(unittest.TestCase):
    """Which neighbouring runs were running while this one was: from the first and last timeline.jsonl stamps, read-only."""

    def setUp(self):
        self.environment = import_environment()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.parent = Path(tmp.name)

    def write_run(self, name: str, first: float, last: float, hosts=("claude",), case="custom", tail: str = "") -> Path:
        folder = self.parent / name
        folder.mkdir()
        stamps = [first, first + (last - first) / 3, first + 2 * (last - first) / 3, last]
        (folder / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate(stamps)) + tail)
        for number, host in enumerate(hosts):
            file = "invocation.json" if number == 0 else f"invocation-resume-{host}-{1000 + number}.json"
            (folder / file).write_text(json.dumps({"case": case, "host": host, "versions": {}}))
        return folder

    def entries(self, record: dict) -> dict:
        return {entry["folder"]: entry for entry in record["runs"]}

    def test_a_neighbour_that_began_before_and_one_that_began_after_this_run_both_overlap_it(self):
        me = self.write_run("me", 1000, 2000)
        self.write_run("early", 500, 1500, case="a")
        self.write_run("late", 1600, 3000, hosts=("grok",), case="b")
        record = self.environment.overlap(me)
        self.assertTrue(record["observed"])
        found = self.entries(record)
        self.assertEqual(sorted(found), ["early", "late"])
        self.assertEqual((found["early"]["overlapped_seconds"], found["early"]["started_offset_seconds"]), (500.0, -500.0))
        self.assertEqual((found["late"]["overlapped_seconds"], found["late"]["started_offset_seconds"]), (400.0, 600.0))
        self.assertEqual((found["late"]["case"], found["late"]["hosts"]), ("b", ["grok"]))
        # The case a count taken when the run starts gets wrong: only one neighbour was running at 1000.
        self.assertEqual(sum(entry["started_offset_seconds"] <= 0 for entry in record["runs"]), 1)
        self.assertEqual(len(record["runs"]), 2)

    def test_a_neighbour_that_ended_before_or_began_after_this_run_is_not_listed_and_none_is_an_empty_list(self):
        me = self.write_run("me", 1000, 2000)
        self.write_run("before", 100, 900)
        self.write_run("after", 2100, 3000)
        self.write_run("touching", 2000, 2500)  # no seconds in common
        record = self.environment.overlap(me)
        self.assertEqual(record["runs"], [], "looked at three neighbours and none overlapped: an empty list, not unknown")
        self.assertEqual(record["siblings_read"], 3)

    def test_the_basis_says_what_the_seconds_are_and_are_not(self):
        basis = self.environment.overlap(self.write_run("me", 1000, 2000))["basis"]
        for phrase in ("host events only", "pause between sessions", "setup before the first event", "checks and reap after the last",
                       "neither an upper nor a lower bound"):
            self.assertIn(phrase, " ".join(basis.split()))

    def test_a_run_whose_stamps_are_one_instant_inside_a_neighbours_span_overlaps_it_for_zero_seconds(self):
        me = self.write_run("me", 1500, 1500)
        self.write_run("wide", 1000, 2000)
        self.write_run("ends-as-it-starts", 1000, 1500)
        record = self.environment.overlap(me)
        self.assertEqual([(e["folder"], e["overlapped_seconds"]) for e in record["runs"]], [("wide", 0.0)])

    def test_a_folder_with_no_readable_timeline_is_not_a_neighbour_and_a_half_written_last_line_is_skipped(self):
        me = self.write_run("me", 1000, 2000)
        (self.parent / "plain-folder").mkdir()
        (self.parent / "stray-file.log").write_text("x")
        broken = self.parent / "broken"
        broken.mkdir()
        (broken / "timeline.jsonl").write_text("not json\n")
        self.write_run("growing", 1500, 1800, tail='{"line": 9, "t": 19')  # the host is writing it right now
        record = self.environment.overlap(me)
        self.assertEqual([entry["folder"] for entry in record["runs"]], ["growing"])
        self.assertEqual(record["runs"][0]["overlapped_seconds"], 300.0)
        self.assertEqual(record["siblings_read"], 1)

    def test_a_neighbour_that_two_hosts_worked_on_names_both_in_launch_order(self):
        me = self.write_run("me", 1000, 2000)
        self.write_run("mixed", 900, 1100, hosts=("grok", "claude"))
        self.assertEqual(self.entries(self.environment.overlap(me))["mixed"]["hosts"], ["grok", "claude"])

    def test_a_run_with_no_readable_timeline_of_its_own_is_unobserved_and_says_why(self):
        me = self.parent / "me"
        me.mkdir()
        self.write_run("other", 1, 5)
        record = self.environment.overlap(me)
        self.assertEqual(record["observed"], False)
        self.assertIn("timeline.jsonl", record["reason"])
        self.assertNotIn("runs", record)

    def test_a_neighbour_whose_timeline_cannot_be_read_is_named_and_never_silently_dropped(self):
        me = self.write_run("me", 1000, 2000)
        (self.parent / "a-directory" / "timeline.jsonl").mkdir(parents=True)
        for name, text in (("non-numeric", '{"line": 0, "t": "soon"}\n'),
                           ("not-a-number", '{"line": 0, "t": NaN}\n{"line": 1, "t": NaN}\n'),
                           ("infinite", '{"line": 0, "t": 1e999}\n{"line": 1, "t": -1e999}\n')):
            (self.parent / name).mkdir()
            (self.parent / name / "timeline.jsonl").write_text(text)
        self.write_run("backwards", 1800, 1200)  # its first stamp is after its last: not a span
        (self.parent / "not-yet").mkdir()  # a folder with no timeline yet is not seen (a documented limit)
        self.write_run("fine", 1500, 1800)
        record = self.environment.overlap(me)
        self.assertEqual(record["siblings_unreadable"], ["a-directory", "backwards", "infinite", "non-numeric", "not-a-number"])
        self.assertEqual(record["siblings_read"], 1)
        self.assertEqual([entry["folder"] for entry in record["runs"]], ["fine"])
        json.dumps(record, allow_nan=False)  # no NaN or infinity reaches result.json

    def test_a_stamp_that_is_not_a_finite_time_is_skipped_like_a_half_written_line(self):
        # The span is read by the one span reader, metrics.span (batch 1011 integration; it was environment.span).
        import metrics
        path = self.parent / "t.jsonl"
        path.write_text('{"line": 0, "t": 1500}\n{"line": 1, "t": NaN}\n{"line": 2, "t": 1e999}\n')
        self.assertEqual(metrics.span(path), {"started": 1500.0, "ended": 1500.0}, "NaN and infinity are not the span's end")

    def test_a_neighbour_whose_launch_records_cannot_be_read_has_unknown_hosts_with_the_reason(self):
        me = self.write_run("me", 1000, 2000)
        self.write_run("intact", 1500, 1800, hosts=("grok", "claude"), case="x")
        broken = self.write_run("broken", 1500, 1800)
        (broken / "invocation.json").write_text('{"case": "custom", "ho')
        (self.write_run("none", 1500, 1800) / "invocation.json").unlink()
        partial = self.write_run("partial", 1500, 1800, hosts=("grok", "claude"))
        (partial / "invocation-resume-claude-1001.json").write_text('{"case": "custom", "ho')
        found = self.entries(self.environment.overlap(me))
        self.assertEqual((found["intact"]["hosts"], found["intact"]["hosts_reason"]), (["grok", "claude"], None))
        for name in ("broken", "partial"):
            self.assertIsNone(found[name]["hosts"], name)
            self.assertIn("could not be read", found[name]["hosts_reason"], name)
        self.assertIsNone(found["none"]["hosts"])
        self.assertIn("no launch record", found["none"]["hosts_reason"])

    def test_reading_the_neighbours_changes_nothing_in_them(self):
        me = self.write_run("me", 1000, 2000)
        other = self.write_run("other", 1500, 2500)
        before = {path.name: path.stat().st_mtime_ns for folder in (me, other) for path in folder.iterdir()}
        listing = sorted(path.name for path in other.iterdir())
        self.environment.overlap(me)
        self.assertEqual({path.name: path.stat().st_mtime_ns for folder in (me, other) for path in folder.iterdir()}, before)
        self.assertEqual(sorted(path.name for path in other.iterdir()), listing, "no lock file or other mark was left in a neighbour")

    def test_the_nine_round_runs_of_2026_10_08_all_overlapped_and_three_saw_it_begin_after_their_own_start(self):
        # Compact extracts of the saved runs (the first and last timeline stamps are what the reader looks at).
        shutil.copytree(FIXTURES / "rounds", self.parent / "20261008")
        parent = self.parent / "20261008"
        names = sorted(path.name for path in parent.iterdir())
        self.assertEqual(len(names), 9)
        records = {name: self.environment.overlap(parent / name) for name in names}
        self.assertTrue(all(record["observed"] and record["runs"] for record in records.values()), "all 9 overlapped another run")
        late = {name for name, record in records.items() if any(e["started_offset_seconds"] > 1 for e in record["runs"])}
        self.assertEqual(late, {"r1-battleship-grok-none", "r1-battleship-sonnet", "r3-battleship-grok-none"})
        # The overlap a start-time count would have recorded as 0 or 1: r1 Grok met r1 Checkers 280 s after it began.
        grok = self.entries(records["r1-battleship-grok-none"])
        self.assertAlmostEqual(grok["r1-checkers-sonnet"]["started_offset_seconds"], 280.4, places=1)
        self.assertAlmostEqual(grok["r1-checkers-sonnet"]["overlapped_seconds"], 787.0, delta=1.0)
        self.assertEqual(grok["r1-battleship-sonnet"]["hosts"], ["claude"])
        r3 = self.entries(records["r3-battleship-grok-none"])
        self.assertAlmostEqual(r3["r3-checkers-sonnet"]["started_offset_seconds"], 763.3, places=1)
        self.assertEqual(records["r3-checkers-sonnet"]["runs"][0]["folder"], "r3-battleship-grok-none",
                         "the later Checkers run overlapped the Grok run it killed")
        # The r2 trio started within a second of each other: nothing began later.
        self.assertTrue(all(e["started_offset_seconds"] < 1 for e in records["r2-battleship-grok-none"]["runs"]))


class LaunchRecordsTest(unittest.TestCase):
    """hosts_used and the per-launch entries, read through runrecord (one reader), from the launch records of a run."""

    def setUp(self):
        self.environment = import_environment()

    def r2(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / "r2-battleship-grok-none"
        shutil.copytree(FIXTURES / "rounds" / "r2-battleship-grok-none", out)
        return out

    def test_the_mixed_host_run_names_both_hosts_though_its_result_says_grok(self):
        # r2-battleship-grok-none: Grok started it, Claude Sonnet finished it (visits 31 to 52), a regrade then restated Grok.
        out = self.r2()
        entries = self.environment.launch_environments(out)
        self.assertEqual([(e["launch"], e["host"], e["model"]) for e in entries],
                         [("invocation.json", "grok", "grok-4.7"),
                          ("invocation-resume-claude-1791508003.json", "claude", "claude-sonnet-5-5")])
        block = self.environment.result_block(out, {"observed": False, "reason": "t"}, {"observed": False, "reason": "t"})
        self.assertEqual(block["hosts_used"], ["grok", "claude"])
        self.assertTrue(block["mixed_host"])
        self.assertEqual(len(block["environments"]), 2, "the regrade started no host and is not a launch")

    def test_an_old_launch_record_has_no_environment_and_no_host_build_and_says_null(self):
        entry = self.environment.launch_environments(self.r2())[0]
        self.assertIsNone(entry["environment"])
        self.assertIsNone(entry["host_build"])
        self.assertEqual(entry["effort"], "medium")

    def test_the_host_build_and_environment_a_launch_recorded_are_passed_through_not_probed(self):
        out = self.r2()
        record = json.loads((out / "invocation.json").read_text())
        record.update(host_build="grok 1.0.50 (c58f321264ba)", environment={"observed": True, "at": "2026-10-09T15:20:01Z"})
        (out / "invocation.json").write_text(json.dumps(record))
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("no process is started to read a host build")):
            entry = self.environment.launch_environments(out)[0]
        self.assertEqual(entry["host_build"], "grok 1.0.50 (c58f321264ba)")
        self.assertEqual(entry["environment"]["at"], "2026-10-09T15:20:01Z")

    def test_a_regrade_restates_the_last_launchs_start_and_says_so_when_there_is_none(self):
        out = self.r2()
        restated = self.environment.restated_start(out)
        self.assertEqual(restated["observed"], False)
        self.assertIn("has no environment", restated["reason"])
        last = json.loads((out / "invocation-resume-claude-1791508003.json").read_text())
        last["environment"] = {"observed": True, "at": "2026-10-09T16:00:00Z"}
        (out / "invocation-resume-claude-1791508003.json").write_text(json.dumps(last))
        self.assertEqual(self.environment.restated_start(out)["at"], "2026-10-09T16:00:00Z")

    def test_a_launch_record_that_cannot_be_read_makes_the_hosts_unknown_and_is_named(self):
        out = self.r2()
        name = "invocation-resume-claude-1791508003.json"
        (out / name).write_text('{"case": "custom", "host": "cla')  # a record cut off mid-write
        block = self.environment.result_block(out, {"observed": True}, {"observed": True})
        for key in ("hosts_used", "mixed_host"):
            self.assertEqual(block[key]["observed"], False, key)
            self.assertIn(name, block[key]["reason"])
        self.assertEqual(block["launches_unreadable"], [name])
        self.assertEqual([entry["launch"] for entry in block["environments"]], ["invocation.json"])
        intact = self.environment.result_block(self.r2(), {"observed": True}, {"observed": True})
        self.assertEqual((intact["launches_unreadable"], intact["hosts_used"]), ([], ["grok", "claude"]))

    def test_unreadable_names_a_launch_record_that_exists_and_cannot_be_read_as_a_record(self):
        import runrecord
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        self.assertEqual(runrecord.unreadable(out), [], "a folder with no launch record has none that cannot be read")
        (out / "invocation.json").mkdir()
        (out / "invocation-resume-grok-5.json").write_text("[1]")
        (out / "invocation-resume-grok-6.json").write_text("{bad")
        (out / "invocation-resume-grok-7.json").write_text(json.dumps({"host": "grok", "versions": {}}))
        (out / "invocation-other.json").write_text("{bad")  # not a launch record's name
        (out / "invocation-resume-grok-later.json").write_text("{bad")  # matches the glob, not the name a launch record has
        self.assertEqual(runrecord.unreadable(out), ["invocation.json", "invocation-resume-grok-5.json", "invocation-resume-grok-6.json"])

    def test_a_null_host_build_or_environment_says_why(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)

        def record(name, **kw):
            (out / name).write_text(json.dumps({"case": "c", "host": kw.pop("host"), "versions": {}, **kw}))

        record("invocation.json", host="grok")
        record("invocation-resume-claude-1001.json", host="claude")
        record("invocation-resume-grok-1002.json", host="grok", host_build=None, environment="oops")
        record("invocation-resume-grok-1003.json", host="grok", host_build="grok 1.0.50 (c58f321264ba)", environment={"observed": True})
        old, claude, nulled, whole = self.environment.launch_environments(out)
        self.assertIn("predates", old["host_build_reason"])
        self.assertIn("no environment", old["environment_reason"])
        self.assertIn("Claude", claude["host_build_reason"])
        self.assertIn("claude_code_version", claude["host_build_reason"])
        self.assertIn("null", nulled["host_build_reason"])
        self.assertIn("not a record", nulled["environment_reason"])
        self.assertEqual((whole["host_build"], whole["host_build_reason"], whole["environment_reason"]),
                         ("grok 1.0.50 (c58f321264ba)", None, None))
        record("invocation-resume-claude-1004.json", host="claude", host_build="2.1.295")
        self.assertIsNone(self.environment.launch_environments(out)[-1]["host_build_reason"], "a Claude launch that recorded a build")

    def test_a_start_that_cannot_be_restated_says_what_is_true_about_the_record(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        (out / "invocation.json").write_text(json.dumps({"host": "grok", "versions": {}}))
        self.assertIn("has no environment", self.environment.restated_start(out)["reason"])
        (out / "invocation.json").write_text(json.dumps({"host": "grok", "versions": {}, "environment": "oops"}))
        self.assertIn("not a record", self.environment.restated_start(out)["reason"])
        self.assertNotIn("launched before", self.environment.restated_start(out)["reason"])

    def test_a_part_that_cannot_be_read_is_unobserved_and_the_others_stand(self):
        out = self.r2()
        with mock.patch.object(self.environment, "overlap", side_effect=RuntimeError("no listing")):
            block = self.environment.result_block(out, {"observed": True}, {"observed": True})
        self.assertEqual(block["overlap"], {"observed": False, "reason": "no listing"})
        self.assertEqual(block["hosts_used"], ["grok", "claude"])


class EnvironmentThroughMainTest(QuietHarnessCase):
    """run.main writes the environment into every launch record and result.json, on every host, and it decides nothing."""

    def setUp(self):
        super().setUp()
        self.environment = import_environment()
        saved = self.environment._TOOLS
        self.addCleanup(setattr, self.environment, "_TOOLS", saved)
        self.environment._TOOLS = ({"node": "v99.0.0", "python3": "Python 9.9.9", "git": "git version 9.9.9"}, {})
        self.browser = self.tmp / "fake-browser"
        self.browser.write_text(FAKE_BROWSER)
        self.browser.chmod(self.browser.stat().st_mode | stat.S_IXUSR)
        self.browser_log = self.tmp / "browser-log.jsonl"
        patched = mock.patch.dict(os.environ, {"FAKE_BROWSER_LOG": str(self.browser_log)})
        patched.start()
        self.addCleanup(patched.stop)
        self.addCleanup(self.end_browsers)

    def end_browsers(self) -> None:
        for line in self.browser_log.read_text().splitlines() if self.browser_log.exists() else []:
            with contextlib.suppress(ValueError, KeyError, ProcessLookupError, PermissionError):
                pid = json.loads(line)["pid"]
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)

    def browser_launches(self) -> list[dict]:
        return [json.loads(line) for line in self.browser_log.read_text().splitlines()] if self.browser_log.exists() else []

    def use_cases(self, cases: dict) -> None:
        path = self.tmp / "cases.json"
        path.write_text(json.dumps(cases))
        saved, run.CASES = run.CASES, path
        self.addCleanup(setattr, run, "CASES", saved)

    def test_the_start_record_is_in_the_launch_record_and_the_whole_block_is_in_result_json_on_every_host(self):
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                code, result, printed = self.invoke_printed(host, "done")
                self.assertEqual(code, 0, result)
                out = Path(result["output"])
                launch = json.loads((out / "invocation.json").read_text())
                self.assertEqual(launch["needs"], [])
                start = launch["environment"]
                self.assertEqual(start["tools"], {"node": "v99.0.0", "python3": "Python 9.9.9", "git": "git version 9.9.9"})
                self.assertIsInstance(start["cpus"], int)
                self.assertIn(start["display_hold"], (True, False))
                block = result["environment"]
                self.assertEqual(block["start"], start)
                self.assertTrue(block["end"]["observed"])
                self.assertNotIn("tools", block["end"])
                self.assertEqual((block["hosts_used"], block["mixed_host"]), ([host], False))
                self.assertEqual([(e["launch"], e["host"], e["environment"]) for e in block["environments"]],
                                 [("invocation.json", host, start)])
                self.assertTrue(block["overlap"]["observed"])
                self.assertEqual(block["overlap"]["runs"], [])

    def test_the_display_hold_is_what_keep_awake_decides(self):
        with mock.patch.object(run, "display_held", return_value=True):
            _, result, _ = self.invoke_printed("grok", "done")
        self.assertIs(result["environment"]["start"]["display_hold"], True)
        with mock.patch.object(run, "display_held", return_value=False):
            _, result, _ = self.invoke_printed("grok", "done")
        self.assertIs(result["environment"]["start"]["display_hold"], False)

    def test_a_run_started_beside_a_neighbour_records_the_overlap_with_its_hosts_and_seconds(self):
        now = time.time()
        neighbour = self.tmp / "neighbour"
        neighbour.mkdir()
        (neighbour / "timeline.jsonl").write_text(
            "".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate((now - 60, now + 600))))
        (neighbour / "invocation.json").write_text(json.dumps({"case": "other", "host": "codex", "versions": {}}))
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        (entry,) = result["environment"]["overlap"]["runs"]
        self.assertEqual((entry["folder"], entry["case"], entry["hosts"]), ("neighbour", "other", ["codex"]))
        self.assertLess(entry["started_offset_seconds"], 0, "it was already running when this run began")
        self.assertEqual(entry["overlapped_seconds"], 0.0, "a fake host's events all arrive in one instant, inside the neighbour's span")
        self.assertIn("overlap", next(line for line in printed.splitlines() if line.startswith("  environment") and "overlap" in line))

    def test_a_declared_need_reaches_the_probe_from_the_case_and_from_the_flag_and_an_undeclared_one_starts_no_browser(self):
        self.use_cases({"page": {"style": "s", "prompt": "p", "checks": [], "checks_source": "t", "needs": ["browser"],
                                 "needs_source": "the request says a page"},
                        "plain": {"style": "s", "prompt": "p", "checks": [], "checks_source": "t"}})
        with mock.patch.object(self.environment, "TITLE_CEILING_SECONDS", 3.0), mock.patch.object(self.environment, "GRACE_SECONDS", 0.2):
            _, plain, _ = self.invoke_printed("grok", "done", "--case", "plain", "--browser-bin", str(self.browser))
            self.assertEqual(self.browser_launches(), [], "no browser was started for a case that declares none")
            self.assertEqual(plain["environment"]["start"]["browser"]["declared"], False)
            _, page, _ = self.invoke_printed("grok", "done", "--case", "page", "--browser-bin", str(self.browser))
            self.assertTrue(page["environment"]["start"]["browser"]["probed"])
            self.assertEqual(json.loads((Path(page["output"]) / "invocation.json").read_text())["needs"], ["browser"])
            first = len(self.browser_launches())
            _, flagged, _ = self.invoke_printed("grok", "done", "--prompt", "build it", "--need", "browser",
                                                "--browser-bin", str(self.browser))
            self.assertTrue(flagged["environment"]["start"]["browser"]["probed"])
            self.assertGreater(len(self.browser_launches()), first)

    def test_a_harness_told_to_end_during_the_probe_ends_the_browser_at_once_and_the_run_reads_stopped(self):
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        timer = threading.Timer(0.5, run.terminate, ("SIGTERM",))
        self.addCleanup(timer.cancel)
        with mock.patch.object(self.environment, "TITLE_CEILING_SECONDS", 4.0), \
                mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "silent"}):
            timer.start()
            start = time.monotonic()
            code, result, printed = self.invoke_printed("grok", "done", "--prompt", "p", "--need", "browser",
                                                        "--browser-bin", str(self.browser))
            elapsed = time.monotonic() - start
        self.assertLess(elapsed, 3.0, "the probe did not wait out its 4 s ceiling")
        self.assertEqual(result["process"]["status"], "stopped")
        browser = result["environment"]["start"]["browser"]
        self.assertTrue(browser["file"]["interrupted"])
        self.assertFalse(browser["http"]["probed"])
        for entry in self.browser_launches():
            with self.assertRaises(ProcessLookupError):
                os.kill(entry["pid"], 0)

    def resume_all(self, out: Path, *extra: str) -> dict:
        """A resume that names no host, every host's binary a fake, the run kept active."""
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
                    "shiploop_version": None, "unreleased": [], "ci": "success"}
        os.environ["FAKE_MODE"] = "stuck"
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--grok-bin", str(self.fakes["grok"]), "--claude-bin", str(self.fakes["claude"]),
                      "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                      "--baseline", str(self.baselines), "--max-resumes", "0", *extra])
        return json.loads((out / "result.json").read_text())

    def test_the_needs_a_launch_declared_carry_to_each_later_launch_and_are_probed_again(self):
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        with mock.patch.object(self.environment, "TITLE_CEILING_SECONDS", 3.0), mock.patch.object(self.environment, "GRACE_SECONDS", 0.2):
            _, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0", "--prompt", "p")
            out = Path(first["output"])
            self.assertEqual(self.browser_launches(), [], "the first launch declared no need")
            self.resume_all(out, "--need", "browser", "--browser-bin", str(self.browser))
            self.assertEqual(len(self.browser_launches()), 2, "a resume that declares the need probes the browser")
            self.resume_all(out, "--browser-bin", str(self.browser))  # declares nothing itself
        records = [json.loads(path.read_text()) for path in sorted(out.glob("invocation-resume-grok-*.json"))]
        self.assertEqual([record["needs"] for record in records], [["browser"], ["browser"]], "the last launch's needs carry on")
        self.assertTrue(records[1]["environment"]["browser"]["probed"])
        self.assertEqual(len(self.browser_launches()), 4, "and the later resume probes again")

    def test_an_unknown_need_is_refused_by_the_parser(self):
        self.assertEqual(run.parser().parse_args(["--need", "browser"]).need, ["browser"])
        self.assertEqual(run.parser().parse_args([]).need, [])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            run.parser().parse_args(["--need", "gpu"])

    def test_the_browser_line_is_printed_before_the_host_starts(self):
        with mock.patch.object(self.environment, "TITLE_CEILING_SECONDS", 3.0), mock.patch.object(self.environment, "GRACE_SECONDS", 0.2):
            _, _, printed = self.invoke_printed("grok", "done", "--prompt", "p", "--need", "browser", "--browser-bin", str(self.browser))
        line = next(ln for ln in printed.splitlines() if ln.startswith("  environment") and "browser" in ln)
        self.assertLess(printed.index(line), printed.index("tool  run_terminal_command"))
        self.assertIn("title", line)

    def test_a_custom_prompt_that_declares_no_need_says_so(self):
        _, _, printed = self.invoke_printed("grok", "done", "--prompt", "build it")
        self.assertIn("declares no need by itself", printed)
        self.assertIn("--need browser", printed)
        _, _, quiet_case = self.invoke_printed("grok", "done")
        self.assertNotIn("declares no need", quiet_case, "a named case speaks for itself")

    def test_a_browser_that_hangs_or_a_probe_that_raises_never_changes_a_verdict_or_the_exit_code(self):
        with mock.patch.object(self.environment, "TITLE_CEILING_SECONDS", 1.0), mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "silent"}):
            code, result, _ = self.invoke_printed("grok", "done", "--prompt", "p", "--need", "browser", "--browser-bin", str(self.browser))
        self.assertEqual(code, 0, result)
        self.assertFalse(result["environment"]["start"]["browser"]["http"]["title_seen"])
        with mock.patch.object(self.environment, "start_record", side_effect=RuntimeError("boom")):
            code, result, _ = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["environment"]["start"]["observed"], False)
        self.assertIn("boom", result["environment"]["start"]["reason"])
        with mock.patch.object(self.environment, "overlap", side_effect=RuntimeError("no listing")), \
                mock.patch.object(self.environment, "end_record", side_effect=RuntimeError("no load")):
            code, result, _ = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["environment"]["overlap"], {"observed": False, "reason": "no listing"})
        self.assertEqual(result["environment"]["end"]["observed"], False)

    def test_a_regrade_restates_every_launch_starts_no_probe_and_says_the_end_was_not_observed(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0", "--prompt", "p")
        out = Path(first["output"])
        recorded = json.loads((out / "invocation.json").read_text())["environment"]
        run.store.write_record(out / "work" / ".shiploop" / "state.md", {"status": "blocked", "stage": "x"})
        with mock.patch.object(self.environment, "browser_record", side_effect=AssertionError("a regrade probes nothing")), \
                mock.patch.object(self.environment, "start_record", side_effect=AssertionError("a regrade reads no start")):
            _, result, _ = self.grade_only(out)
        block = result["environment"]
        self.assertEqual(block["start"], recorded)
        self.assertEqual(block["end"], {"observed": False, "reason": "regraded: the end of the run was not observed"})
        self.assertEqual([e["launch"] for e in block["environments"]], ["invocation.json"],
                         "the regrade's own record started no host, so it is not a launch")
        regrade_record = json.loads(next(out.glob("invocation-resume-*.json")).read_text())
        self.assertEqual(regrade_record["environment"], {"observed": False, "reason": "regraded: no host was launched"})
        self.assertEqual(self.browser_launches(), [])


class StandaloneProbeTest(BrowserFixture, unittest.TestCase):
    """python3 environment.py --need browser, the calibration command, is a program a person or a task stops."""

    def start(self, tmpdir: Path) -> subprocess.Popen:
        env = dict(os.environ, TMPDIR=str(tmpdir), FAKE_BROWSER_MODE="silent")
        proc = subprocess.Popen([sys.executable, str(ROOT / "test" / "shiploop_e2e" / "environment.py"), "--need", "browser",
                                 "--browser-bin", str(self.browser)], env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        self._started.append(proc)
        for _ in range(200):
            if self.launches():
                break
            time.sleep(0.05)
        self.assertTrue(self.launches(), "the browser started")
        return proc

    def test_a_sigterm_to_the_standalone_command_ends_the_browser_and_removes_its_files(self):
        tmpdir = self.dir / "tmp"
        tmpdir.mkdir()
        proc = self.start(tmpdir)
        time.sleep(0.5)
        proc.send_signal(signal.SIGTERM)  # the command this test started
        proc.wait(timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        for entry in self.launches():
            self.assertFalse(self.alive(entry["pid"]), "the browser the command started was ended")
        self.assertEqual(sorted(path.name for path in tmpdir.iterdir()), [], "its profile and stand-in files were removed")

    def test_a_sighup_to_the_standalone_command_does_the_same(self):
        tmpdir = self.dir / "tmp"
        tmpdir.mkdir()
        proc = self.start(tmpdir)
        proc.send_signal(signal.SIGHUP)
        proc.wait(timeout=15)
        for entry in self.launches():
            self.assertFalse(self.alive(entry["pid"]))
        self.assertEqual(sorted(path.name for path in tmpdir.iterdir()), [])


class CasesNeedTest(unittest.TestCase):
    def test_every_case_with_needs_names_its_source_and_only_known_needs(self):
        environment = import_environment()
        cases = json.loads(run.CASES.read_text())
        declared = {name: case["needs"] for name, case in cases.items() if "needs" in case}
        self.assertTrue(declared, "the cases that serve a page declare the browser")
        for name, needs in declared.items():
            with self.subTest(case=name):
                self.assertTrue(set(needs) <= set(environment.NEEDS))
                self.assertTrue(cases[name].get("needs_source"), "a need names the request that implies it")
        self.assertEqual(sorted(declared), ["battleship", "battleship-scoring", "checkers"])


def facts(**kw) -> dict:
    """A termination block as run.termination_facts writes it, with the engine finished and the host exited, unless told."""
    block = {"process_status": "exited", "returncode": 0, "sessions": 1, "resumes": 0, "session_stops": ["success"],
             "resume_stop": "host is not resumable", "engine_status": "done", "engine_stage": "done",
             "engine_unaccepted_stage": None, "engine_status_reason": None, "engine_blocked_by": None,
             "engine_awaiting_kind": None, "engine_awaiting_no_default": None}
    block.update(kw)
    return block


class OutcomeClassTest(unittest.TestCase):
    """SPEC: outcome_class is a pure function of termination and pass: PASS, FAILED, BLOCKED, STOPPED, or null with a basis."""

    def cls(self, passed: bool, **kw) -> tuple:
        return run.outcome_class(passed, facts(**kw))

    def test_the_classes_are_exactly_these_and_nothing_adds_an_environment_overlay(self):
        self.assertEqual(run.OUTCOME_CLASSES, ("PASS", "FAILED", "BLOCKED", "STOPPED"))

    def test_a_run_that_passed_is_pass_whatever_the_rest_says(self):
        self.assertEqual(self.cls(True)[0], "PASS")
        self.assertEqual(self.cls(True, process_status="stopped", engine_status="active")[0], "PASS")

    def test_an_engine_that_reached_done_with_a_failing_verdict_is_failed(self):
        cls, basis = self.cls(False)
        self.assertEqual(cls, "FAILED")
        self.assertIn("done", basis)

    def test_a_host_that_ended_on_its_own_with_the_engine_still_active_is_failed(self):
        for stop in ("host is not resumable", "no host session id to resume"):
            with self.subTest(resume_stop=stop):
                cls, basis = self.cls(False, engine_status="active", engine_stage="implement", resume_stop=stop,
                                      process_status="failed", returncode=1)
                self.assertEqual(cls, "FAILED")
                self.assertIn(stop, basis)

    def test_a_host_that_wrote_no_state_and_ended_on_its_own_is_failed(self):
        self.assertEqual(self.cls(False, engine_status="unknown", engine_stage="unknown", resume_stop="host is not resumable")[0],
                         "FAILED")

    def test_a_blocked_engine_is_blocked_and_names_what_it_recorded(self):
        cls, basis = self.cls(False, engine_status="blocked", engine_stage="system-test-author", resume_stop="ShipLoop run is blocked",
                              engine_blocked_by="access", engine_awaiting_kind="answer", engine_awaiting_no_default=True)
        self.assertEqual(cls, "BLOCKED")
        for text in ("blocked at system-test-author", "by access", "answer", "no default"):
            self.assertIn(text, basis)

    def test_a_blocked_engine_without_a_stated_default_or_without_awaiting_or_without_a_record_is_still_blocked(self):
        cases = {"by user, awaiting, no default stated": dict(engine_blocked_by="user", engine_awaiting_kind="present",
                                                               engine_awaiting_no_default=False),
                 "external, no person awaited": dict(engine_blocked_by="external"),
                 "no accepted blocked result in the state (an old state)": dict()}
        for label, kw in cases.items():
            with self.subTest(label):
                cls, basis = self.cls(False, engine_status="blocked", engine_stage="test-refine",
                                      resume_stop="ShipLoop run is blocked", **kw)
                self.assertEqual(cls, "BLOCKED")
        self.assertIn("no blocked result", self.cls(False, engine_status="blocked", engine_stage="x")[1])
        self.assertIn("external", self.cls(False, engine_status="blocked", engine_blocked_by="external")[1])
        self.assertIn("gives no reason", self.cls(False, engine_status="blocked", engine_blocked_by="user",
                                                  engine_awaiting_kind="answer", engine_awaiting_no_default=False)[1])

    def test_a_paused_engine_awaits_resume_as_a_blocked_one_does_and_names_no_blocker(self):
        cls, basis = self.cls(False, engine_status="paused", engine_stage="implement", engine_status_reason="user asked",
                              resume_stop="ShipLoop run is paused")
        self.assertEqual(cls, "BLOCKED")
        self.assertIn("paused at implement", basis)
        self.assertIn("no blocked result", basis)

    def test_a_halted_engine_is_terminal_and_unfinished_so_it_is_failed(self):
        cls, basis = self.cls(False, engine_status="halted", engine_stage="implement", engine_status_reason="cannot continue",
                              resume_stop="ShipLoop run is halted")
        self.assertEqual(cls, "FAILED")
        self.assertIn("halted at implement", basis)
        self.assertIn("cannot continue", basis)

    def test_a_run_the_harness_ended_is_stopped(self):
        cases = {"the stop file": dict(process_status="stopped", resume_stop="stopped by /out/stop"),
                 "a SIGTERM": dict(process_status="stopped", resume_stop="terminated by SIGTERM"),
                 "the deadline killed the host": dict(process_status="timeout", returncode=-9, resume_stop="run deadline spent"),
                 "the deadline killed a host that is never resumed": dict(process_status="timeout", returncode=-9,
                                                                          resume_stop="host is not resumable"),
                 "the deadline was spent between sessions": dict(resume_stop="run deadline spent"),
                 "the resume budget was spent": dict(resume_stop="resume budget spent (20)")}
        for label, kw in cases.items():
            with self.subTest(label):
                self.assertEqual(self.cls(False, engine_status="active", engine_stage="implement", **kw)[0], "STOPPED")

    def test_a_host_session_that_ended_on_the_cap_the_harness_gave_it_is_stopped_on_every_host(self):
        # --max-turns and --max-budget-usd are the harness's own limits: the host ending on them is the harness ending the run,
        # whether or not the host can be resumed (Claude cannot; Grok is resumed until its budget is spent).
        caps = {"claude turns": run.metrics.session_stop({"type": "result", "subtype": "error_max_turns", "is_error": True,
                                                          "num_turns": 10000}),
                "claude budget": run.metrics.session_stop({"type": "result", "subtype": "error_max_budget_usd", "is_error": True}),
                "grok turns": run.metrics.session_stop({"type": "end", "stopReason": {"kind": "max_turns"}})}
        for label, stop in caps.items():
            for resume_stop in ("host is not resumable", "no host session id to resume"):
                with self.subTest(label, resume_stop=resume_stop):
                    cls, basis = self.cls(False, engine_status="active", engine_stage="implement", resume_stop=resume_stop,
                                          process_status="failed", returncode=1, session_stops=["cancelled", stop])
                    self.assertEqual(cls, "STOPPED")
                    self.assertIn("cap", basis)
        # An API failure, an empty turn and a crash are the host's own ending: FAILED. Only the last session counts.
        api = run.metrics.session_stop({"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error"})
        for stops in ([api], ["unknown"], [caps["claude turns"], "cancelled"]):
            with self.subTest(stops=stops):
                self.assertEqual(self.cls(False, engine_status="active", resume_stop="host is not resumable",
                                          process_status="failed", session_stops=stops)[0], "FAILED")

    def test_a_requested_stop_after_the_engine_blocked_does_not_turn_the_block_into_a_stop(self):
        self.assertEqual(self.cls(False, engine_status="blocked", process_status="stopped", resume_stop="stopped by /out/stop")[0],
                         "BLOCKED")

    def test_a_regrade_that_observed_nothing_is_unknown_with_a_basis(self):
        cls, basis = self.cls(False, process_status=run.NOT_OBSERVED, returncode=None, sessions=0, session_stops=[],
                              resume_stop="not evaluated (regraded)", engine_status="active", engine_stage="implement",
                              regraded=True)
        self.assertEqual((cls, "no host ran" in basis), (None, True))

    def test_a_regrade_reads_the_engine_as_it_is_now_and_the_ending_as_it_was_recorded(self):
        earlier = facts(process_status="stopped", engine_status="active", resume_stop="stopped by /out/stop", regraded=True)
        self.assertEqual(run.outcome_class(False, dict(earlier, engine_status_at_regrade="active"))[0], "STOPPED")
        self.assertEqual(run.outcome_class(False, dict(earlier, engine_status_at_regrade="blocked"))[0], "BLOCKED")
        self.assertEqual(run.outcome_class(False, dict(earlier, engine_status_at_regrade="done"))[0], "FAILED")

    def test_an_ending_the_classifier_does_not_know_is_unknown_and_names_it_never_failed_by_default(self):
        cls, basis = self.cls(False, engine_status="active", resume_stop="something new")
        self.assertEqual(cls, None)
        self.assertIn("something new", basis)

    def test_a_block_with_nothing_in_it_does_not_raise(self):
        self.assertEqual(run.outcome_class(False, {})[0], None)
        self.assertEqual(run.outcome_class(True, {})[0], "PASS")

    def test_the_input_is_not_changed(self):
        block = facts(engine_status="blocked", engine_blocked_by="access")
        before = json.loads(json.dumps(block))
        run.outcome_class(False, block)
        self.assertEqual(block, before)

    def test_every_engine_status_and_every_process_status_gets_a_class_or_a_stated_unknown(self):
        import shiploop_navigator
        statuses = sorted(shiploop_navigator._STATUSES) + ["unknown"]
        self.assertEqual(set(statuses) - {"unknown"}, {"active", "paused", "blocked", "halted", "done"},
                         "the engine has a status this classifier was not written for")
        processes = ["exited", "failed", "timeout", "stopped", "unknown", run.NOT_OBSERVED]
        stops = [stop for stop, _ in run.RESUME_STOP_CLASSES] + ["ShipLoop run is blocked", "not evaluated (regraded)", "unknown"]
        for engine in statuses:
            for process in processes:
                for stop in stops:
                    with self.subTest(engine=engine, process=process, resume_stop=stop):
                        cls, basis = run.outcome_class(False, facts(engine_status=engine, process_status=process,
                                                                    resume_stop=stop))
                        self.assertIn(cls, (*run.OUTCOME_CLASSES, None))
                        self.assertNotEqual(cls, "PASS")
                        self.assertTrue(basis and isinstance(basis, str))

    def test_every_resume_stop_the_harness_can_write_is_known_to_the_classifier(self):
        """resume_stop is built from several strings in run.py (some with a variable in them), so it is read from the source:
        a new one must be given a class, or the classifier would call it unknown."""
        import ast
        tree = ast.parse((ROOT / "test" / "shiploop_e2e" / "run.py").read_text())
        found: set[str] = set()

        def heads(node):
            """The fixed text each string a value can be begins with (an f-string: up to its first variable)."""
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                yield node.value
            elif isinstance(node, ast.JoinedStr) and node.values and isinstance(node.values[0], ast.Constant):
                yield node.values[0].value
            elif isinstance(node, ast.IfExp):
                yield from heads(node.body)
                yield from heads(node.orelse)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "resume_stop" for t in node.targets):
                found.update(heads(node.value))
            if isinstance(node, ast.FunctionDef) and node.name == "stop_cause":
                for ret in ast.walk(node):
                    if isinstance(ret, ast.Return):
                        found.update(heads(ret.value))
        found.discard("")
        self.assertGreaterEqual(len(found), 7, found)
        known = tuple(prefix for prefix, _ in run.RESUME_STOP_CLASSES)
        engine_decides = ("ShipLoop run is ", "not evaluated (regraded)")
        for text in sorted(found):
            with self.subTest(resume_stop=text):
                self.assertTrue(text.startswith(known + engine_decides), f"resume_stop {text!r} has no class in run.RESUME_STOP_CLASSES")


class LearningsOutcomeLineTest(unittest.TestCase):
    def message(self, result: dict) -> str:
        import iterate
        verdict = dict(base.LearningsTest.VERDICT, actionable=[])
        return iterate.learnings_message(2, iterate.argparse.Namespace(case="battleship"), "0123456789ab", result, verdict, [])

    def test_the_learnings_message_says_how_the_run_ended_where_the_result_has_a_class(self):
        result = dict(base.LearningsTest.RESULT, outcome_class="BLOCKED", outcome_basis="engine blocked at x by access")
        self.assertIn("- ended as: BLOCKED (engine blocked at x by access)", self.message(result))
        unknown = dict(base.LearningsTest.RESULT, outcome_class=None, outcome_basis="no host ran")
        self.assertIn("- ended as: unknown (no host ran)", self.message(unknown))
        self.assertNotIn("ended as", self.message(base.LearningsTest.RESULT), "a result written before the class has none")


class RecordedOutcomeClassTest(unittest.TestCase):
    """The 11 recorded results of 2026-10-07 and 2026-10-08, and the engine states of the three that did not pass."""

    EXPECTED = {"v1230-battleship-grok-none": "BLOCKED", "r1-battleship-grok-none": "BLOCKED", "r3-battleship-grok-none": "STOPPED"}

    def recorded(self) -> dict:
        return {path.stem: json.loads(path.read_text()) for path in sorted((FIXTURES / "recorded").glob("*/*.json"))}

    def test_only_the_three_grok_runs_that_did_not_pass_have_another_class_and_the_rest_pass(self):
        records = self.recorded()
        self.assertEqual(len(records), 11)
        for name, record in records.items():
            with self.subTest(run=name):
                cls, _ = run.outcome_class(record["pass"], record["termination"])
                self.assertEqual(cls, self.EXPECTED.get(name, "PASS"))

    def test_the_two_blocked_runs_are_blocked_whether_or_not_their_old_record_has_the_blocked_detail(self):
        # Their results predate the detail: the class is BLOCKED and says no blocked result was read.
        for name in ("v1230-battleship-grok-none", "r1-battleship-grok-none"):
            record = self.recorded()[name]
            self.assertNotIn("engine_blocked_by", record["termination"])
            cls, basis = run.outcome_class(record["pass"], record["termination"])
            self.assertEqual(cls, "BLOCKED")
            self.assertIn("no blocked result", basis)

    def test_the_engine_states_give_the_blocked_detail_the_old_records_lack(self):
        want = {"v1230-battleship-grok-none": ("access", "present", True), "r1-battleship-grok-none": ("access", "answer", True),
                "r3-battleship-grok-none": (None, None, None)}
        records = self.recorded()
        for name, (by, kind, no_default) in want.items():
            with self.subTest(run=name):
                engine = run.metrics.engine_state(FIXTURES / "engine" / name)
                self.assertTrue(engine, "the extract holds a readable state.md")
                process = records[name]["process"]
                t = run.termination_facts(process, engine, records[name]["termination"]["resume_stop"])
                self.assertEqual((t["engine_blocked_by"], t["engine_awaiting_kind"], t["engine_awaiting_no_default"]),
                                 (by, kind, no_default))
                cls, basis = run.outcome_class(records[name]["pass"], t)
                self.assertEqual(cls, self.EXPECTED[name])
        blocked = run.termination_facts(records["r1-battleship-grok-none"]["process"],
                                        run.metrics.engine_state(FIXTURES / "engine" / "r1-battleship-grok-none"), "ShipLoop run is blocked")
        self.assertIn("by access", run.outcome_class(False, blocked)[1])

    def test_the_detail_is_read_only_while_the_engine_is_blocked_and_says_when_no_default_was_stated(self):
        # metrics.blocked_detail is the one reader of the blocked detail (the fidelity record can call it too).
        detail = run.metrics.blocked_detail
        history = [{"action": "a1", "outcome": "blocked", "stage": "x"}]
        accepted = {"a1": {"outcome": "blocked", "blocked_by": "user", "awaiting": {"kind": "answer", "question": "q"}}}
        blocked = detail({"status": "blocked", "history": history, "accepted": accepted})
        self.assertEqual(blocked, {"blocked_by": "user", "awaiting_kind": "answer", "awaiting_no_default": False})
        spaces = {"a1": {"outcome": "blocked", "blocked_by": "user", "awaiting": {"kind": "answer", "no_default": "  "}}}
        self.assertIs(detail({"status": "blocked", "history": history, "accepted": spaces})["awaiting_no_default"], False)
        # The block was answered and the run went on: the last history entry still says blocked, but the engine is active.
        self.assertEqual(detail({"status": "active", "history": history, "accepted": accepted}), {key: None for key in blocked})
        # A blocked engine whose last accepted action was not the blocked one (its record is some earlier block's).
        self.assertEqual(detail({"status": "blocked", "history": [{"action": "a1", "outcome": "done"}], "accepted": accepted}),
                         {key: None for key in blocked})
        external = detail({"status": "blocked", "history": history,
                           "accepted": {"a1": {"outcome": "blocked", "blocked_by": "external"}}})
        self.assertEqual(external, {"blocked_by": "external", "awaiting_kind": None, "awaiting_no_default": None})
        for garbage in ({}, {"status": "blocked"}, {"status": "blocked", "history": "x", "accepted": []},
                        {"status": "blocked", "history": [1], "accepted": {"a1": 1}}):
            self.assertEqual(detail(garbage), {key: None for key in blocked}, garbage)

    def test_termination_carries_the_shared_readers_detail_under_the_engine_prefix(self):
        history = [{"action": "a1", "outcome": "blocked", "stage": "x"}]
        engine = {"status": "blocked", "stage": "x", "history": history,
                  "accepted": {"a1": {"outcome": "blocked", "blocked_by": "access",
                                      "awaiting": {"kind": "present", "no_default": "d"}}}}
        t = run.termination_facts({"status": "exited", "sessions": []}, engine, "ShipLoop run is blocked")
        self.assertEqual({k: v for k, v in t.items() if k.startswith("engine_awaiting") or k == "engine_blocked_by"},
                         {"engine_blocked_by": "access", "engine_awaiting_kind": "present", "engine_awaiting_no_default": True})
        self.assertFalse(hasattr(run, "blocked_detail"), "one reader: the function lives in metrics.py")

    def test_a_state_with_no_accepted_record_gives_none_and_not_a_parsed_guess(self):
        engine = {"status": "blocked", "stage": "x", "status_reason": "access: waiting for a person",
                  "history": [{"action": "a1", "outcome": "blocked", "stage": "x"}]}
        t = run.termination_facts({"status": "exited", "sessions": []}, engine, "ShipLoop run is blocked")
        self.assertEqual((t["engine_blocked_by"], t["engine_awaiting_kind"], t["engine_awaiting_no_default"]), (None, None, None))
        # An active or finished engine has no blocked detail either.
        active = run.termination_facts({"status": "exited", "sessions": []}, {"status": "active"}, "x")
        self.assertEqual((active["engine_blocked_by"], active["engine_awaiting_kind"], active["engine_awaiting_no_default"]),
                         (None, None, None))


# A fake Grok that ends its session with the engine blocked on a person, as a real run does at a stage that needs one: the
# state the engine accepted (a blocked result naming who can unblock it, awaiting an answer with a stated reason). It is the
# base fake with one more mode, so the arguments, the plugin install and the session log are the base fake's own.
BLOCKING_GROK_ANCHOR = 'if mode == "done" or (mode == "resume" and resumed):'
BLOCKING_GROK = base.FAKE_GROK.replace(BLOCKING_GROK_ANCHOR, '''if mode == "blocked":
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {"status": "blocked", "stage": "system-test-author",
        "status_reason": "access: no browser is connected",
        "history": [{"action": "a1", "outcome": "blocked", "stage": "system-test-author"}],
        "accepted": {"a1": {"outcome": "blocked", "blocked_by": "access", "headline": "needs a browser",
                            "awaiting": {"kind": "answer", "question": "How should it proceed?",
                                         "no_default": "nothing else can proceed without a browser"}}}})
elif mode == "done" or (mode == "resume" and resumed):''', 1)


class OutcomeClassThroughMainTest(QuietHarnessCase):
    """run.main writes the class and its basis into result.json, the baseline row and the printed report; it decides nothing."""

    def setUp(self):
        super().setUp()
        self.assertIn(BLOCKING_GROK_ANCHOR, base.FAKE_GROK, "the base fake changed: the blocking mode needs a new anchor")
        self.blocking = self.tmp / "grok-blocking"
        self.blocking.write_text(BLOCKING_GROK)
        self.blocking.chmod(self.blocking.stat().st_mode | stat.S_IXUSR)

    def sessions(self) -> list[dict]:
        path = Path(str(self.log) + ".sessions")
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_a_run_that_passed_is_pass_on_every_host_and_is_in_the_baseline_row_and_the_report(self):
        for host in ("claude", "grok", "codex"):
            with self.subTest(host=host):
                code, result, printed = self.invoke_printed(host, "done")
                self.assertEqual(code, 0, result)
                self.assertEqual((result["outcome_class"], result["outcome_basis"]), ("PASS", "every verdict passed"))
                self.assertNotIn("outcome_class", self.last_row(), "the class is in result.json only")
                self.assertIn("  outcome   PASS", printed)

    def test_a_requested_stop_is_stopped_and_its_header_and_exit_code_are_unchanged(self):
        code, result, printed = self.invoke_printed("grok", "stuck-stop", "--max-resumes", "3")
        self.assertEqual(code, 1)
        self.assertEqual(result["outcome_class"], "STOPPED")
        self.assertIn("stopped by", result["outcome_basis"])
        self.assertTrue(printed.splitlines()[next(i for i, ln in enumerate(printed.splitlines()) if ln.startswith("STOPPED  shiploop e2e"))])

    def test_a_spent_resume_budget_is_stopped_and_a_host_that_gave_up_is_failed(self):
        _, spent, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "1")
        self.assertEqual((spent["outcome_class"], spent["termination"]["resume_stop"]), ("STOPPED", "resume budget spent (1)"))
        _, anonymous, _ = self.invoke_printed("grok", "anon")
        self.assertEqual((anonymous["outcome_class"], anonymous["termination"]["resume_stop"]), ("FAILED", "no host session id to resume"))
        _, errored, _ = self.invoke_printed("claude", "api-error")
        self.assertEqual(errored["outcome_class"], "FAILED")

    def test_a_blocked_run_is_blocked_with_the_detail_the_engine_recorded_and_is_neither_resumed_nor_answered(self):
        code, result, printed = self.invoke_printed("grok", "blocked", "--grok-bin", str(self.blocking))
        self.assertEqual(code, 1)
        self.assertFalse(result["pass"])
        self.assertEqual(result["outcome_class"], "BLOCKED")
        t = result["termination"]
        self.assertEqual((t["engine_blocked_by"], t["engine_awaiting_kind"], t["engine_awaiting_no_default"]), ("access", "answer", True))
        self.assertEqual(t["resume_stop"], "ShipLoop run is blocked")
        self.assertEqual(len(self.sessions()), 1, "one host session: a blocked run is never resumed as if answered (SPEC S-14)")
        self.assertFalse((Path(result["output"]) / "stop").exists())
        self.assertTrue((Path(result["output"]) / "mismatch.md").is_file(), "the class does not excuse the failure")
        for text in ("blocked at system-test-author by access", "answer", "no default"):
            self.assertIn(text, result["outcome_basis"])
        self.assertIn("  outcome   BLOCKED", printed)
        self.assertNotIn("outcome_class", self.last_row(), "the class is in result.json only")
        self.assertEqual(self.last_row()["termination"], t)

    def test_a_regrade_of_a_blocked_run_is_blocked_and_starts_no_host(self):
        out = self.first_run()
        self.blocked_workspace(out, state={
            "status": "blocked", "stage": "x", "history": [{"action": "a1", "outcome": "blocked", "stage": "x"}],
            "accepted": {"a1": {"outcome": "blocked", "blocked_by": "user", "awaiting": {"kind": "present", "steps": ["s"],
                                                                                        "report": "r", "no_default": "d"}}}})
        before = len(self.sessions())
        code, result, _ = self.grade_only(out)
        self.assertEqual(result["outcome_class"], "BLOCKED")
        self.assertIn("by user", result["outcome_basis"])
        self.assertEqual(len(self.sessions()), before, "no host was started")

    def test_a_regrade_keeps_the_ending_it_recorded_and_one_that_observed_nothing_is_unknown(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        self.assertEqual(first["outcome_class"], "STOPPED")
        _, kept, _ = self.grade_only(out)
        self.assertTrue(kept["termination"]["regraded"])
        self.assertEqual(kept["outcome_class"], "STOPPED", "the original ending, read against the engine as it is")
        (out / "result.json").unlink()
        _, unknown, printed = self.grade_only(out)
        self.assertIsNone(unknown["outcome_class"])
        self.assertIn("no host ran", unknown["outcome_basis"])
        self.assertIn("  outcome   unknown", printed)

    def test_a_class_that_cannot_be_computed_is_null_with_the_reason_and_changes_nothing(self):
        with mock.patch.object(run, "outcome_class", side_effect=RuntimeError("boom")):
            code, result, _ = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertTrue(result["pass"])
        self.assertIsNone(result["outcome_class"])
        self.assertIn("boom", result["outcome_basis"])


class ResumeDefaultsTest(QuietHarnessCase):
    """--resume-run continues the run's own driver; it does not default to Claude, and a host change is deliberate."""

    def setUp(self):
        super().setUp()
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
                    "shiploop_version": None, "unreleased": [], "ci": "success"}
        patched = mock.patch.object(run, "released_versions", return_value=released)
        patched.start()
        self.addCleanup(patched.stop)

    def stopped(self, *extra: str) -> Path:
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0", *extra)
        self.assertEqual(first["shiploop"]["status"], "active")
        return Path(first["output"])

    def resume(self, out: Path, *extra: str, mode: str = "done") -> tuple[int, dict, str]:
        """A resume that names no host: every host's binary is a fake, so whichever one is chosen is safe to start."""
        os.environ["FAKE_MODE"] = mode
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--grok-bin", str(self.fakes["grok"]), "--claude-bin", str(self.fakes["claude"]),
                             "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines), "--max-resumes", "0", *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def launches(self, out: Path) -> list[tuple[str, str, str | None, str | None]]:
        return [(name, record["host"], record["model"], record["effort"]) for name, record in run.runrecord.launches(out)]

    def test_a_resume_that_names_no_host_continues_on_the_host_the_run_was_launched_on(self):
        out = self.stopped()
        code, result, printed = self.resume(out)
        self.assertEqual(result["host"], "grok")
        self.assertEqual([host for _, host, _, _ in self.launches(out)], ["grok", "grok"])
        self.assertIn("This session ended while the ShipLoop run was still active", self.seen()["prompt"])
        self.assertIn("continuing on grok (grok-4.7, medium)", printed)
        self.assertEqual(result["environment"]["hosts_used"], ["grok"])

    def test_model_and_effort_come_from_the_runs_own_record_and_an_explicit_one_wins(self):
        out = self.stopped("--model", "my-model", "--effort", "high")
        code, result, _ = self.resume(out)
        self.assertEqual((result["model"], result["effort"]), ("my-model", "high"))
        self.assertEqual(self.launches(out)[1][2:], ("my-model", "high"))
        os.environ.pop("FAKE_MODE", None)
        out = self.stopped("--model", "my-model", "--effort", "high")
        _, result, _ = self.resume(out, "--model", "other-model", "--effort", "low")
        self.assertEqual((result["model"], result["effort"]), ("other-model", "low"))

    def test_a_host_that_differs_is_refused_naming_both_and_nothing_starts(self):
        out = self.stopped()
        result_before = (out / "result.json").read_text()
        sessions = len(self.sessions())
        with self.assertRaises(SystemExit) as raised:
            self.resume(out, "--host", "claude")
        message = str(raised.exception)
        for text in ("grok", "claude", "--allow-host-change", "mixed-host"):
            self.assertIn(text, message)
        self.assertEqual(len(self.sessions()), sessions, "no host was started")
        self.assertEqual((out / "result.json").read_text(), result_before)
        self.assertEqual(len(self.launches(out)), 1, "no launch record was written")

    def sessions(self) -> list:
        path = Path(str(self.log) + ".sessions")
        return path.read_text().splitlines() if path.exists() else []

    def test_the_deliberate_flag_finishes_the_run_on_the_named_host_as_a_mixed_host_run(self):
        out = self.stopped("--model", "my-model", "--effort", "high")
        code, result, printed = self.resume(out, "--host", "claude", "--allow-host-change")
        self.assertEqual([(host, model) for _, host, model, _ in self.launches(out)],
                         [("grok", "my-model"), ("claude", "claude-sonnet-5-5")],
                         "the recorded model belongs to the host that recorded it")
        block = result["environment"]
        self.assertEqual((block["hosts_used"], block["mixed_host"]), (["grok", "claude"], True))
        self.assertEqual(len(block["environments"]), 2)
        self.assertEqual(result["host"], "claude")
        self.assertIn("MIXED HOST: grok, claude", printed)
        self.assertIn("--allow-host-change", printed)

    def test_naming_the_recorded_host_is_not_a_change_and_a_mixed_run_continues_on_the_host_that_last_ran_it(self):
        out = self.stopped()
        code, result, _ = self.resume(out, "--host", "grok")
        out = self.stopped()
        self.resume(out, "--host", "claude", "--allow-host-change", mode="active")  # claude leaves it active
        code, result, printed = self.resume(out)  # no host: the one that last ran it, not the first and not Claude by default
        self.assertEqual([host for _, host, _, _ in self.launches(out)], ["grok", "claude", "claude"])
        self.assertIn("continuing on claude", printed)

    def test_a_regrade_restates_the_identity_of_the_last_launch_not_the_result_an_earlier_regrade_wrote(self):
        # r2-battleship-grok-none: Grok started it, Claude finished it, and a regrade left result.json saying Grok beside a
        # Claude-finished run (its header read host=grok, its metrics said Claude 2.1.294, its environment said mixed).
        out = self.stopped("--model", "my-model", "--effort", "high")
        self.resume(out, "--host", "claude", "--allow-host-change")
        saved = json.loads((out / "result.json").read_text())
        saved.update(host="grok", model="grok-4.7", effort="medium")
        (out / "result.json").write_text(json.dumps(saved))
        code, regraded, printed = self.resume(out, "--grade-only")
        self.assertEqual((regraded["host"], regraded["model"]), ("claude", "claude-sonnet-5-5"))
        self.assertEqual(regraded["resumed_run"]["from_host"], "claude")
        self.assertTrue(regraded["environment"]["mixed_host"])
        header = next(ln for ln in printed.splitlines() if " shiploop e2e case=" in ln and ln.split()[0] in ("PASS", "FAIL", "STOPPED"))
        self.assertIn("host=claude", header)
        self.assertIn("MIXED HOST", printed)
        self.assertEqual(self.launches(out)[-1][1], "claude", "the regrade started no host and is not a launch")

    def test_a_launch_record_is_never_overwritten_by_another_launch_that_began_in_the_same_second(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        now = int(time.time())
        with mock.patch.object(run.time, "time", return_value=float(now)):
            self.assertEqual(run.launch_stamp(out, "claude"), now)
            (out / f"invocation-resume-claude-{now}.json").write_text("{}")
            self.assertEqual(run.launch_stamp(out, "claude"), now + 1, "the record of the launch before is kept")
            (out / f"resume-claude-{now + 1}.txt").write_text("a prompt")
            self.assertEqual(run.launch_stamp(out, "claude"), now + 2, "so is a prompt file")
            self.assertEqual(run.launch_stamp(out, "grok"), now, "another host's names are its own")

    def test_a_regrade_in_the_same_second_as_the_launch_it_follows_leaves_that_launch_on_record(self):
        out = self.stopped()
        self.resume(out, "--host", "claude", "--allow-host-change")
        names = sorted(path.name for path in out.glob("invocation-resume-*.json"))
        self.resume(out, "--grade-only")  # no pause: the second may well be the same
        self.assertTrue(set(names) <= {path.name for path in out.glob("invocation-resume-*.json")})
        self.assertEqual([host for _, host, _, _ in self.launches(out)], ["grok", "claude"], "the regrade is not a launch")

    def test_a_resume_of_a_mixed_run_names_the_last_launch_as_where_it_resumed_from(self):
        out = self.stopped()
        self.resume(out, "--host", "claude", "--allow-host-change", mode="active")
        _, result, _ = self.resume(out)
        self.assertEqual((result["resumed_run"]["from_host"], result["resumed_run"]["from_model"]), ("claude", "claude-sonnet-5-5"))

    def test_the_refusal_names_the_recorded_host_and_the_requested_one_and_is_honest_about_a_run_that_already_is_mixed(self):
        out = self.stopped()
        with self.assertRaises(SystemExit) as raised:
            self.resume(out, "--host", "claude")
        text = str(raised.exception)
        for phrase in ("last launched on grok", "--host claude would finish it", "would become a mixed-host run", "--allow-host-change"):
            self.assertIn(phrase, text)
        self.assertNotIn("already", text)
        self.resume(out, "--host", "claude", "--allow-host-change", mode="active")
        with self.assertRaises(SystemExit) as raised:
            self.resume(out, "--host", "grok")
        text = str(raised.exception)
        for phrase in ("last launched on claude", "already is a mixed-host run", "hosts so far: grok, claude", "--host grok"):
            self.assertIn(phrase, text)
        self.assertNotIn("would become", text)

    def test_a_model_or_effort_that_differs_from_the_recorded_one_is_printed_and_an_unchanged_one_is_not(self):
        out = self.stopped("--model", "my-model", "--effort", "high")
        _, _, printed = self.resume(out, "--model", "other-model", "--effort", "low")
        self.assertIn("model other-model (the last launch used my-model)", printed)
        self.assertIn("effort low (the last launch used high)", printed)
        out = self.stopped("--model", "my-model", "--effort", "high")
        _, _, quiet = self.resume(out)
        self.assertNotIn("the last launch used", quiet)

    def test_a_regrade_still_restates_the_recorded_identity_whatever_the_flags_say(self):
        out = self.stopped()
        self.blocked_workspace(out)
        before = len(self.sessions())
        code, result, printed = self.resume(out, "--host", "claude", "--model", "other")
        self.assertEqual((result["host"], result["model"]), ("grok", "grok-4.7"))
        self.assertIn("regrade: no host starts", printed)
        self.assertEqual(len(self.sessions()), before)


if __name__ == "__main__":
    unittest.main()
