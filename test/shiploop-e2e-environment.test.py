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
                os.killpg(proc.pid, signal.SIGKILL) if os.getpgid(proc.pid) == proc.pid else None
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
note(argv=argv, url=url, kind=kind, mode=mode, home=os.environ.get("HOME"))
if mode == "silent":
    time.sleep(30)
if mode == "crash":
    print("no display", file=sys.stderr)
    sys.exit(3)
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

    def launches(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def _end_browsers(self) -> None:
        """Whatever fake browser the code under test left, by the pid it logged and only if it still leads its group."""
        for entry in self.launches():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                if os.getpgid(entry["pid"]) == entry["pid"]:
                    os.killpg(entry["pid"], signal.SIGKILL)

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
        self.assertLess(elapsed, 4.0, "both kinds were probed together, each in a session of its own")
        for entry in self.launches():
            self.assertFalse(self.alive(entry["pid"]))

    def test_a_browser_that_dies_without_output_is_not_a_title_and_its_exit_code_is_kept(self):
        with mock.patch.dict(os.environ, {"FAKE_BROWSER_MODE": "crash"}):
            record = self.probe()
        target = record["http"]
        self.assertEqual((target["title_seen"], target["exited"], target["returncode"], target["killed"]), (False, True, 3, False))

    def test_the_probe_signals_only_the_group_it_started_and_a_bystander_is_left_alone(self):
        bystander = self.start_bystander()
        own = os.getpgrp()
        real, signalled, stray = os.killpg, [], []

        def guarded(group, number):
            if number == 0:
                return real(group, number)  # asking whether a group is empty signals nothing
            signalled.append(group)
            if group == own or group not in {entry["pgid"] for entry in self.launches()}:
                stray.append(group)  # recorded and not sent: a wrong group is never really signalled
                return None
            return real(group, number)

        with mock.patch.object(os, "killpg", guarded):
            self.probe()
        self.assertEqual(stray, [], "a group that is not a fake browser's own was signalled")
        self.assertTrue(signalled, "a lingering browser was stopped through its group")
        self.assertIsNone(bystander.poll(), "a process the probe did not start was not touched")
        self.assertTrue(self.alive(bystander.pid))

    def test_the_browser_runs_with_a_throwaway_profile_and_the_hygiene_flags(self):
        self.probe()
        launches = self.launches()
        self.assertEqual(sorted(entry["kind"] for entry in launches), ["file", "http"])
        for entry in launches:
            argv = entry["argv"]
            profile = next(arg.split("=", 1)[1] for arg in argv if arg.startswith("--user-data-dir="))
            self.assertTrue(os.path.realpath(profile).startswith(os.path.realpath(tempfile.gettempdir())), profile)
            self.assertFalse(Path(profile).exists(), "the throwaway profile is removed")
            for flag in ("--headless=new", "--dump-dom", "--disable-background-networking", "--disable-default-apps",
                         "--disable-component-update", "--disable-sync"):
                self.assertIn(flag, argv)
            self.assertEqual(argv[-1], entry["url"])

    def test_both_stand_ins_serve_the_page_whose_title_the_record_looks_for(self):
        record = self.probe()
        urls = {entry["kind"]: entry["url"] for entry in self.launches()}
        self.assertTrue(urls["file"].startswith("file://"))
        self.assertRegex(urls["http"], r"^http://127\.0\.0\.1:\d+/")
        self.assertTrue(record["file"]["title_seen"] and record["http"]["title_seen"])

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
        self.assertIn("launched before the record existed", restated["reason"])
        last = json.loads((out / "invocation-resume-claude-1791508003.json").read_text())
        last["environment"] = {"observed": True, "at": "2026-10-09T16:00:00Z"}
        (out / "invocation-resume-claude-1791508003.json").write_text(json.dumps(last))
        self.assertEqual(self.environment.restated_start(out)["at"], "2026-10-09T16:00:00Z")

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


if __name__ == "__main__":
    unittest.main()
