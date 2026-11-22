#!/usr/bin/env python3
"""The medium brownfield case pair: `ticket-assignment` on fixtures/node-tickets and its follow-on `ticket-escalation` (D7 of
docs/shiploop-brownfield-baseline-design-2026-10-28.md, "a medium brownfield case with a follow-on run"), and `ticket-import`
on the same base, whose deciding facts only running settles (XI of docs/experiments/experiment-route-20261031/README.md). No
model is called.

SPEC "A brownfield case" asks each case's calibration: the base fails every fail-to-pass check and passes every pass-to-pass
check and the pristine suite; the reference passes every check and the pristine suite; each targeted defect fails exactly the
checks its defect reads; an independently written alternative passes everything. The follow-on starts from the first run's
delivery, so its base is the first case's reference. These tests grade every variant of
test/fixtures/quality/reference_ticket_assignment.py, reference_ticket_escalation.py and reference_ticket_import.py with:

* the held-out acceptance (checks/ticket_assignment_accept.py, checks/ticket_escalation_accept.py,
  checks/ticket_import_accept.py) through
  ``quality.acceptance``, as a run's quality phase calls it, the delivered copy (``quality.Product``) included;
* the base's pristine tests (checks/base_tests.py pristine node-tickets).

Then the cases' own checks through ``run.run_checks`` (the follow-on's with $PRIOR_WORK and its retention checks), the catalog
entries, the fixture, the ground-truth table, and one fake-host run of the first case through ``run.main``.

The variants are graded side by side, a thread each (``quality.free_port`` never hands out a port twice), and the pristine
runs start only after every acceptance run has ended, so no server of the base's own tests takes a port handed to a product.
"""

from __future__ import annotations

import concurrent.futures
import functools
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test" / "fixtures" / "quality"))


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The fake hosts and the harness cases of the main harness suite; only classes defined in this file are tests of this file.
e2e = _load("shiploop_e2e_main_tests", "shiploop-e2e.test.py")
fixture_process = _load("fixture_process", "fixture_process.py")
run = e2e.run

import boundary  # noqa: E402
import brownfield  # noqa: E402
import quality  # noqa: E402
import reference_ticket_assignment as first  # noqa: E402
import reference_ticket_escalation as second  # noqa: E402
import reference_ticket_import as third  # noqa: E402
import scorecard  # noqa: E402

CASES = json.loads(run.CASES.read_text())
FIXTURE = brownfield.FIXTURES / "node-tickets"
BASE_TESTS = run.HERE / "checks" / "base_tests.py"
GROUND_TRUTH = ROOT / "docs" / "experiments" / "brownfield-baseline-20261028" / "ground-truth" / "node-tickets-expected.md"
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
# Threads that grade variants side by side: most of a variant's time is spent waiting on its servers and its worker.
POOL = min(16, max(4, 2 * (os.cpu_count() or 2)))
# A result that disagrees with what its variant declares is graded again, alone, until a grade agrees, at most this many more times (the last stands).
REGRADES = 3


class Case:
    """One case of the pair: its catalog entry, its builder and what each of its variants must fail."""

    def __init__(self, name: str, builder, expected: dict, pristine: set):
        self.name, self.builder, self.entry = name, builder, CASES[name]
        self.block = self.entry["quality"]["acceptance"]
        self.ids = [item["id"] for item in self.block["checks"]]
        self.fail_to_pass = {item["id"] for item in self.block["checks"] if item["grade"] == "fail-to-pass"}
        self.pass_to_pass = {item["id"] for item in self.block["checks"] if item["grade"] == "pass-to-pass"}
        self.expected = {"base": self.fail_to_pass, "reference": set(), "alternative": set(), **expected}
        self.pristine = pristine  # the variants the base's pristine tests reject


ASSIGNMENT = Case("ticket-assignment", first, {
    "filter-or": {"filters-combine"},
    "filter-after-page": {"assignee-filter-pages"},
    "no-envelope": {"assignee-validation", "assign-state-and-missing"},
    "conflict-as-invalid": {"assign-state-and-missing"},
    "closed-assignable": {"assign-state-and-missing"},
    "notify-inline": {"assignee-notified"},
    "notify-no-template": {"assignee-notified"},
    "notify-key-per-ticket": {"assignee-notified"},
    "notify-requester": {"assignee-notified"},
    "audit-bypassed": {"assign-audited"},
    "actor-ignored": {"assign-audited"},
    "same-agent-not-noop": {"assign-same-agent-noop"},
    "memory-only-assignee": {"assignee-persists", "old-tickets-unassigned", "cli-shows-assignee"},
    "old-data-refused": {"old-data-loads", "old-tickets-unassigned"},
    "old-assignee-undefined": {"old-tickets-unassigned"},
    "raw-column-inserted": {"cli-raw-columns"},
    "cli-no-assignee": {"cli-shows-assignee"},
    # The unassign of a closed ticket is refused as invalid before its state is read: a 400 where 409 is due.
    "no-unassign": {"assign-and-unassign", "assign-state-and-missing", "assign-audited"},
    "empty-filter-ignored": {"assignee-filter", "old-tickets-unassigned"},
    "name-limit-off-by-one": {"assignee-validation"},
    # The command line lists through the store too, so it loses the assignee with the listing.
    "listing-hides-assignee": {"assign-and-unassign", "cli-shows-assignee"},
    "update-rejects-resolved": {"ticket-lifecycle-unchanged"},
    "default-limit-changed": {"listing-unchanged"},
    "resolved-template-replaced": {"notifications-unchanged"},
    "audit-not-saved": {"restart-keeps-state"},
    "backoff-linear": set(),
    "validate-renamed": set(),
}, pristine={"default-limit-changed", "resolved-template-replaced", "audit-not-saved", "backoff-linear", "validate-renamed"})

ESCALATION = Case("ticket-escalation", second, {
    "reassign-same-allowed": {"reassign-validation"},
    "reassign-plain-errors": {"reassign-validation"},
    "reassign-moves-resolved": {"reassign-moves"},
    "reassign-unordered": {"reassign-moves"},
    "reassign-unaudited": {"reassign-audited"},
    "reassign-no-notify": {"reassign-notifies"},
    "escalation-also-in-request": {"worker-off-is-quiet"},
    "escalation-own-timer": {"worker-off-is-quiet"},
    "escalation-in-memory": {"escalation-at-most-once"},
    "escalation-repeats": {"escalation-at-most-once"},
    "escalation-includes-assigned": {"escalation-rules"},
    "escalation-includes-in-progress": {"escalation-rules"},
    "escalation-minutes-as-seconds": {"escalation-rules"},
    "escalation-default-oncall": {"escalation-notifies-oncall"},
    "filter-or-again": {"assignment-listing-kept"},
    "assignment-notify-dropped": {"assignment-notified-kept"},
    "raw-column-moved": {"cli-raw-columns-kept"},
    # Tickets saved without their assignee load as not unassigned (undefined), so they are never escalated either.
    "assignee-lost-on-restart": {"assignment-persists-kept", "escalation-rules", "escalation-at-most-once"},
    "unassign-broken": {"assignment-kept"},
    "update-rejects-resolved": {"existing-api-kept"},
    "outbox-enqueue-renamed": set(),
}, pristine={"outbox-enqueue-renamed"})

IMPORT = Case("ticket-import", third, {
    "save-per-ticket": {"import-5000-in-time"},
    "default-body-limit": {"import-5000-in-time"},
    "global-limit-raised": set(),
    "partial-import": {"import-all-or-none"},
    # The index is read by both checks that refuse an import.
    "one-based-index": {"import-all-or-none", "import-validates-like-create"},
    "silent-import": {"import-notifies"},
    "unaudited-import": {"import-audited"},
    "unsaved-import": {"import-persists"},
    "loose-items": {"import-validates-like-create"},
    "default-priority-low": {"import-creates-in-order"},
    "update-rejects-resolved": {"ticket-lifecycle-unchanged"},
    "default-limit-changed": {"listing-unchanged"},
    "resolved-template-replaced": {"notifications-unchanged"},
    "audit-not-saved": {"restart-keeps-state"},
    "raw-column-moved": {"cli-raw-columns"},
    "old-data-refused": {"old-data-loads"},
}, pristine={"global-limit-raised", "default-limit-changed", "resolved-template-replaced", "audit-not-saved", "old-data-refused"})

GRADED_CASES = (ASSIGNMENT, ESCALATION, IMPORT)

needs_node = unittest.skipUnless(shutil.which("node"), "the deliveries are Node: this class needs node on PATH")
needs_lsof = unittest.skipUnless(shutil.which("node") and shutil.which("lsof"),
                                 "the cases' HTTP checks run through serve.py, which needs node and lsof")


def committed(folder: Path) -> Path:
    """The folder as a delivery: a repository with its files committed, as a run leaves work/."""
    env = {**os.environ, **GIT_ENV}
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "d"]):
        subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True, env=env)
    return folder


def base_tests(delivery: Path, subcommand: str, timeout: float = 600) -> subprocess.CompletedProcess:
    return fixture_process.run_owned([sys.executable, str(BASE_TESTS), subcommand, "node-tickets"],
                                     cwd=delivery, timeout=timeout)


@unittest.skipUnless(os.name == "posix", "owned-process regression needs POSIX process identities")
class BaseTestsProcessOwnershipTest(unittest.TestCase):
    @staticmethod
    def process_identity(pid: int):
        try:
            done = subprocess.run(["ps", "-p", str(pid), "-o", "stat=", "-o", "lstart=", "-o", "command="],
                                  capture_output=True, text=True, timeout=2, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise fixture_process.CleanupError(f"cannot inspect owned worker {pid}") from error
        if done.stderr.strip():
            raise fixture_process.CleanupError(f"cannot inspect owned worker {pid}: {done.stderr.strip()}")
        if done.returncode:
            # ps returns 1 with no output for an absent PID. Confirm that case;
            # a live or permission-uncertain PID is not evidence of exit.
            if done.returncode == 1 and not done.stdout.strip():
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    return None
                except OSError as error:
                    raise fixture_process.CleanupError(f"cannot confirm owned worker {pid} absent") from error
            raise fixture_process.CleanupError(f"cannot inspect owned worker {pid}: ps rc {done.returncode}")
        fields = done.stdout.strip().split(None, 1)
        if len(fields) != 2:
            raise fixture_process.CleanupError(f"cannot parse owned worker {pid} identity")
        return fields

    def owned_worker_alive(self, record: dict) -> bool:
        observed = self.process_identity(record["pid"])
        return bool(observed and observed[1] == record["identity"] and not observed[0].startswith("Z"))

    def cleanup_owned_worker(self, record_file: Path) -> None:
        # Registered before base_tests launches anything. Never signal by name,
        # process group, ancestry alone, or a PID whose start/command changed.
        if not record_file.exists():
            return
        record = json.loads(record_file.read_text())
        if self.owned_worker_alive(record):
            try:
                os.kill(record["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 5
        while self.owned_worker_alive(record) and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(self.owned_worker_alive(record), "test fallback cleanup failed")

    @staticmethod
    def cleanup_control(control: subprocess.Popen) -> None:
        if control.poll() is None:
            control.kill()
        control.wait(timeout=5)
        control.stdout.close()

    def assert_owned_worker_stopped(self, returncode: int, subcommand: str) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        delivery = Path(folder.name)
        record_file = delivery / "owned-worker.json"
        self.addCleanup(self.cleanup_owned_worker, record_file)
        worker = (
            "import json,os,signal,subprocess,sys\n"
            "identity=subprocess.run(['ps','-p',str(os.getpid()),'-o','stat=','-o','lstart=','-o','command='],"
            "capture_output=True,text=True,check=True).stdout.strip().split(None,1)[1]\n"
            "with open(sys.argv[1], 'w') as f: json.dump({'pid':os.getpid(),'identity':identity},f)\n"
            "print('worker-ready',flush=True)\n"
            "os.close(1)\n"
            "signal.pause()\n"
        )
        helper = delivery / "base-helper.py"
        helper.write_text(
            "import select,subprocess,sys\n"
            f"worker=subprocess.Popen([sys.executable,'-B','-c',{worker!r},{str(record_file)!r}],"
            "stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)\n"
            "try:\n"
            "    assert select.select([worker.stdout],[],[],10)[0], 'worker readiness timed out'\n"
            "    assert worker.stdout.readline() == 'worker-ready\\n'\n"
            "except BaseException:\n"
            "    worker.kill(); worker.wait(); raise\n"
            "finally:\n"
            "    worker.stdout.close()\n"
            "print('original-stdout')\n"
            "print('original-stderr',file=sys.stderr)\n"
            f"sys.exit({returncode})\n"
        )
        control = subprocess.Popen(
            [sys.executable, "-B", "-c", "import signal; print('control-ready',flush=True); signal.pause()"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.addCleanup(self.cleanup_control, control)
        self.assertTrue(select.select([control.stdout], [], [], 10)[0], "control readiness timed out")
        self.assertEqual(control.stdout.readline(), "control-ready\n")
        with mock.patch.dict(globals(), BASE_TESTS=helper):
            done = base_tests(delivery, subcommand)
        self.assertEqual(done.returncode, returncode)
        self.assertEqual(done.stdout, "original-stdout\n")
        self.assertEqual(done.stderr, "original-stderr\n")
        self.assertEqual(done.args, [sys.executable, str(helper), subcommand, "node-tickets"])
        self.assertIsNone(control.poll(), "unrelated control process was stopped")
        self.assertTrue(record_file.exists(), "worker must acknowledge readiness before helper exits")
        record = json.loads(record_file.read_text())
        self.assertFalse(self.owned_worker_alive(record), "base_tests returned while its owned worker was still alive")

    def test_success_stops_owned_worker_and_preserves_result(self) -> None:
        self.assert_owned_worker_stopped(0, "suite")

    def test_nonzero_stops_owned_worker_and_preserves_result(self) -> None:
        self.assert_owned_worker_stopped(23, "pristine")

    def owned_fixture(self, *, ignore_term=False, retain_pipes=False, wait=False, node=False):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        delivery = Path(folder.name)
        record = delivery / "worker.json"
        self.addCleanup(self.cleanup_owned_worker, record)
        group_record = delivery / "owned-group"
        self.addCleanup(self.cleanup_fixture_group, group_record)
        helper = delivery / "helper.py"
        if node:
            # Real node --test runner and test worker, without a network server.
            test_file = delivery / "worker.test.cjs"
            test_file.write_text(
                "const fs = require('node:fs');\n"
                "process.on('SIGTERM', () => {});\n"
                f"fs.writeFileSync({json.dumps(str(delivery / 'node-pid.tmp'))}, String(process.pid));\n"
                f"fs.renameSync({json.dumps(str(delivery / 'node-pid.tmp'))}, {json.dumps(str(delivery / 'node-pid'))});\n"
                "setInterval(() => {}, 1000);\n")
            launch = f"[{shutil.which('node')!r}, '--test', {str(test_file)!r}]"
            ready = (
                "deadline=time.monotonic()+10\n"
                f"while not os.path.exists({str(delivery / 'node-pid')!r}):\n"
                "    assert worker.poll() is None, 'node exited before readiness'\n"
                "    assert time.monotonic()<deadline, 'node readiness timed out'\n"
                "    time.sleep(0.01)\n"
                f"pid=int(open({str(delivery / 'node-pid')!r}).read())\n"
                "identity=subprocess.run(['ps','-p',str(pid),'-o','stat=','-o','lstart=','-o','command='],"
                "capture_output=True,text=True,check=True).stdout.strip().split(None,1)[1]\n"
                f"with open({str(record)!r},'w') as f: json.dump(dict(pid=pid,identity=identity),f)\n")
        else:
            worker = (
                "import os,signal\n"
                + ("signal.signal(signal.SIGTERM,signal.SIG_IGN)\n" if ignore_term else "")
                + "print('worker-ready',flush=True)\n"
                + ("" if retain_pipes else "os.close(1); os.close(2)\n")
                + "signal.pause()\n")
            launch = f"[sys.executable,'-B','-c',{worker!r}]"
            ready = (
                "assert select.select([worker.stdout],[],[],10)[0], 'readiness timed out'\n"
                "assert worker.stdout.readline() == 'worker-ready\\n'\n"
                "pid=worker.pid\n"
                "identity=subprocess.run(['ps','-p',str(pid),'-o','stat=','-o','lstart=','-o','command='],"
                "capture_output=True,text=True,check=True).stdout.strip().split(None,1)[1]\n"
                f"with open({str(record)!r},'w') as f: json.dump(dict(pid=pid,identity=identity),f)\n")
        helper.write_text(
            "import json,os,select,signal,subprocess,sys,time\n"
            "assert os.getpgrp()==os.getpid(), 'fixture requires its own group'\n"
            f"with open({str(group_record)!r},'w') as f: f.write(str(os.getpgrp()))\n"
            f"worker=subprocess.Popen({launch},stdout=subprocess.PIPE,"
            f"stderr={'None' if retain_pipes else 'subprocess.DEVNULL'},text=True)\n"
            + ready
            + "print('helper-ready',flush=True)\n"
            + ("signal.pause()\n" if wait else ""))
        return delivery, helper, record

    @staticmethod
    def cleanup_fixture_group(record):
        # The helper records its newly created group before spawning workers.
        # This fallback also owns the Node runner if a readiness assertion fails.
        if record.exists():
            pgid = int(record.read_text())
            if pgid == os.getpgrp():
                raise AssertionError("refusing cleanup of the test parent's group")
            fixture_process.stop_group(pgid)

    def assert_fixture_stopped(self, record):
        self.assertTrue(record.exists(), "fixture must acknowledge readiness")
        self.assertFalse(self.owned_worker_alive(json.loads(record.read_text())), "owned worker remains live")

    @staticmethod
    def cleanup_launched(child):
        try:
            fixture_process.stop_group(child.pid)
            child.wait(timeout=2)
        finally:
            child.stdout.close()
            child.stderr.close()

    def test_term_ignoring_worker_requires_kill_after_leader_exit(self):
        delivery, helper, record = self.owned_fixture(ignore_term=True)
        with mock.patch.dict(globals(), BASE_TESTS=helper):
            done = base_tests(delivery, "suite")
        self.assertEqual((done.returncode, done.stdout), (0, "helper-ready\n"))
        self.assert_fixture_stopped(record)

    def test_timeout_preserves_timeout_and_stops_descendants(self):
        delivery, helper, record = self.owned_fixture(ignore_term=True, wait=True)
        with mock.patch.dict(globals(), BASE_TESTS=helper):
            # Start the deadline only after an explicit readiness handshake.
            original = fixture_process.subprocess.Popen

            def launch(argv, **kwargs):
                child = original(argv, **kwargs)
                if argv[0] == sys.executable:
                    self.addCleanup(self.cleanup_launched, child)
                    self.assertTrue(select.select([child.stdout], [], [], 10)[0])
                    self.assertEqual(child.stdout.readline(), "helper-ready\n")
                return child

            with mock.patch.object(fixture_process.subprocess, "Popen", launch):
                started = time.monotonic()
                with self.assertRaises(subprocess.TimeoutExpired) as caught:
                    base_tests(delivery, "suite", timeout=0.1)
        self.assertEqual(caught.exception.timeout, 0.1)
        self.assertLess(time.monotonic() - started, 10)
        self.assert_fixture_stopped(record)

    def test_retained_outer_pipes_after_leader_exit_are_drained(self):
        # stderr inherits the outer pipe independently of readiness stdout.
        delivery, helper, record = self.owned_fixture(ignore_term=True, retain_pipes=True)
        started = time.monotonic()
        with mock.patch.dict(globals(), BASE_TESTS=helper):
            done = base_tests(delivery, "pristine", timeout=5)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(done.returncode, 0)
        self.assert_fixture_stopped(record)

    def test_exception_and_interruption_after_launch_cleanup_before_propagation(self):
        for error in (RuntimeError("injected communicate failure"), KeyboardInterrupt()):
            with self.subTest(exception=type(error).__name__):
                delivery, helper, record = self.owned_fixture(ignore_term=True, wait=True)
                original = fixture_process.subprocess.Popen

                def launch(argv, **kwargs):
                    child = original(argv, **kwargs)
                    if argv[0] == sys.executable:
                        self.addCleanup(self.cleanup_launched, child)
                        self.assertTrue(select.select([child.stdout], [], [], 10)[0])
                        self.assertEqual(child.stdout.readline(), "helper-ready\n")
                        communicate = child.communicate

                        def interrupted(*args, **kw):
                            child.communicate = communicate
                            raise error

                        child.communicate = interrupted
                    return child

                with mock.patch.dict(globals(), BASE_TESTS=helper), mock.patch.object(
                        fixture_process.subprocess, "Popen", launch):
                    with self.assertRaises(type(error)) as caught:
                        base_tests(delivery, "suite")
                self.assertIs(caught.exception, error)
                self.assert_fixture_stopped(record)

    @needs_node
    def test_actual_node_test_worker_stopped_after_helper_exits(self):
        delivery, helper, record = self.owned_fixture(node=True)
        with mock.patch.dict(globals(), BASE_TESTS=helper):
            done = base_tests(delivery, "suite")
        self.assertEqual((done.returncode, done.stdout), (0, "helper-ready\n"))
        self.assert_fixture_stopped(record)

    @needs_node
    def test_the_real_check_stopped_by_its_owner_stops_the_node_run_it_started(self):
        """The check gives each `node --test` a session of its own, so that it can stop a hung run whole. That takes the run
        out of the group this wrapper owns: stopped by its owner while a run hangs, the check must stop that run on its way
        out, because the owner's signal reaches the check alone."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        delivery = Path(folder.name)
        record = delivery / "worker.json"
        self.addCleanup(self.cleanup_owned_worker, record)
        group_record = delivery / "owned-group"
        self.addCleanup(self.cleanup_fixture_group, group_record)
        ready = delivery / "node-pid"
        (delivery / "test").mkdir()
        (delivery / "test" / "leaves-a-server.test.js").write_text(
            "const fs = require('node:fs');\n"
            "const http = require('node:http');\n"
            "const test = require('node:test');\n"
            "http.createServer(() => {}).listen(0, '127.0.0.1', () => {\n"
            f"  fs.writeFileSync({json.dumps(str(delivery / 'node-pid.tmp'))}, String(process.pid));\n"
            f"  fs.renameSync({json.dumps(str(delivery / 'node-pid.tmp'))}, {json.dumps(str(ready))});\n"
            "});\n"
            "test('passes and leaves its server listening', () => {});\n")
        check = [sys.executable, str(BASE_TESTS), "suite", "node-base"]  # the small base: its own tests take under a second
        original = fixture_process.subprocess.Popen

        def launch(argv, **kwargs):
            child = original(argv, **kwargs)
            if argv == check:
                self.addCleanup(self.cleanup_launched, child)
                # The owner's deadline starts only once the delivery's run hangs: the base's own tests run first.
                deadline = time.monotonic() + 120
                while not ready.exists():
                    self.assertIsNone(child.poll(), "the check ended before the delivery's run started")
                    self.assertLess(time.monotonic(), deadline, "the delivery's run did not start")
                    time.sleep(0.05)
                pid = int(ready.read_text())
                group_record.write_text(str(os.getpgid(pid)))
                record.write_text(json.dumps({"pid": pid, "identity": self.process_identity(pid)[1]}))
            return child

        with mock.patch.object(fixture_process.subprocess, "Popen", launch):
            with self.assertRaises(subprocess.TimeoutExpired):
                fixture_process.run_owned(check, cwd=delivery, timeout=0.1)
        worker = json.loads(record.read_text())
        deadline = time.monotonic() + 10
        while self.owned_worker_alive(worker) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assert_fixture_stopped(record)

    def test_launch_failure_never_signals_a_group(self):
        with mock.patch.object(fixture_process.subprocess, "Popen", side_effect=OSError("launch failed")), \
                mock.patch.object(fixture_process.os, "killpg") as kill:
            with self.assertRaisesRegex(OSError, "launch failed"):
                base_tests(ROOT, "suite")
        kill.assert_not_called()

    def test_already_gone_and_zombie_only_group_cleanup_is_idempotent(self):
        for state in ("", "123 123 Z\n"):
            with self.subTest(state=state), mock.patch.object(fixture_process.subprocess, "run", return_value=
                    subprocess.CompletedProcess([], 0, state, "")), mock.patch.object(fixture_process.os, "killpg") as kill:
                fixture_process.stop_group(123)
                fixture_process.stop_group(123)
                kill.assert_not_called()

    def test_permission_error_with_live_workers_reports_uncertainty(self):
        with mock.patch.object(fixture_process, "live_members", return_value=[123]), \
                mock.patch.object(fixture_process.os, "killpg", side_effect=PermissionError("denied")), \
                mock.patch.object(fixture_process.time, "monotonic", side_effect=range(20)):
            with self.assertRaisesRegex(fixture_process.CleanupError, "still live.*denied"):
                fixture_process.stop_group(123)

    def test_process_state_inspection_failure_is_not_success(self):
        with mock.patch.object(fixture_process.subprocess, "run", return_value=
                subprocess.CompletedProcess([], 1, "", "")):
            with self.assertRaisesRegex(fixture_process.CleanupError, "cannot inspect"):
                fixture_process.stop_group(123)

    def test_permission_error_is_accepted_only_after_observed_exit(self):
        with mock.patch.object(fixture_process, "live_members", side_effect=[[123], []]), \
                mock.patch.object(fixture_process.os, "killpg", side_effect=PermissionError("denied")):
            fixture_process.stop_group(123)

    def test_inspection_failure_still_terminates_and_reaps_direct_child(self):
        original = fixture_process.subprocess.Popen
        launched = []

        def launch(argv, **kwargs):
            child = original(argv, **kwargs)
            # Register immediately, before even readiness can fail. unittest runs
            # this only after both patches below have restored the real helpers.
            self.addCleanup(self.cleanup_launched, child)
            launched.append(child)
            self.assertTrue(select.select([child.stdout], [], [], 10)[0],
                            "direct child readiness timed out")
            self.assertEqual(child.stdout.readline(), "helper-ready\n")
            return child

        argv = [sys.executable, "-B", "-c",
                "import signal; print('helper-ready',flush=True); signal.pause()"]
        with mock.patch.object(fixture_process.subprocess, "Popen", launch), \
                mock.patch.object(fixture_process, "stop_group", side_effect=
                                  fixture_process.CleanupError("cannot inspect owned process group")):
            # run_owned starts its 0.1-second deadline after launch returns,
            # therefore after the explicit handshake, without a startup sleep.
            with self.assertRaisesRegex(fixture_process.CleanupError, "cannot inspect") as caught:
                fixture_process.run_owned(argv, cwd=ROOT, timeout=0.1)
        self.assertIsInstance(caught.exception.__context__, subprocess.TimeoutExpired)
        self.assertEqual(len(launched), 1)
        # Do not poll/wait/communicate here: returncode must already have been
        # populated by run_owned's own reaping, before fallback cleanup runs.
        self.assertIsNotNone(launched[0].returncode,
                             "run_owned left its direct child alive or unreaped")
        self.assertLess(launched[0].returncode, 0, "sleeping direct child was not terminated")

    def test_identity_query_failure_is_loud_for_live_or_permission_uncertain_worker(self):
        record = {"pid": os.getpid(), "identity": "recorded-worker-identity"}
        for diagnostic, liveness_error in (("ps: inspection error", None),
                                            ("", PermissionError("liveness denied"))):
            with self.subTest(diagnostic=diagnostic, liveness_error=liveness_error), \
                    mock.patch.object(subprocess, "run", return_value=
                                      subprocess.CompletedProcess([], 1, "", diagnostic)), \
                    mock.patch.object(os, "kill", return_value=None, side_effect=liveness_error):
                # kill(pid, 0), if used to disambiguate absence, is fully mocked:
                # success means known-live; permission denial means uncertainty.
                with self.assertRaises(fixture_process.CleanupError):
                    self.owned_worker_alive(record)

    def test_identity_query_confirmed_absence_is_not_alive(self):
        record = {"pid": os.getpid(), "identity": "recorded-worker-identity"}
        with mock.patch.object(subprocess, "run", return_value=
                               subprocess.CompletedProcess([], 1, "", "")), \
                mock.patch.object(os, "kill", side_effect=ProcessLookupError("gone")):
            self.assertFalse(self.owned_worker_alive(record))


def failing(done: subprocess.CompletedProcess) -> str:
    """What a base_tests.py run printed: its return code, its FAIL line and the end of its error output."""
    return f"rc {done.returncode}: {done.stdout.strip()[-1500:]} {done.stderr.strip()[-1500:]}"


def suite_wanted(case: Case, variant: str) -> bool:
    """Whether a test reads the delivery's own suite: the base, the deliveries and the defects that edit the base's tests."""
    return variant in ("base", "reference", "alternative") or variant in case.builder.EDITS_BASE_TESTS


def agrees(case: Case, variant: str, kind: str, result) -> bool:
    """Whether a graded result is the one the variant declares: its failed held-out checks, its pristine verdict, or its own
    suite's (which only a base case's base fails: it adds no test)."""
    if kind == "accepted":
        return bool(result.get("observed")) and {row["id"] for row in result["checks"] if not row["pass"]} == case.expected[variant]
    if kind == "pristine":
        return (result.returncode != 0) == (variant in case.pristine)
    if case is not ESCALATION and variant == "base":
        return result.returncode != 0 and "no more than the base's" in result.stdout
    return (result.returncode != 0) == (case is not ESCALATION and variant == "base")


def settle(result, agrees_now, grade_again, regrades: int = REGRADES):
    """Grade a result that disagrees again, alone, until a grade agrees or the regrades are used: (the grade that stands, how many
    times it was graded again, whether the first regrade disagreed too). ``agrees_now(grade)`` says whether a grade is the one the
    variant declares; ``grade_again()`` grades once more."""
    for done in range(1, regrades + 1):
        result = grade_again()
        if agrees_now(result):
            return result, done, done > 1
    return result, regrades, True


def agreed(flags, expected, grade_again):
    """The pass flags of a check list: as they are when they are the declared ones, else graded again, alone, until they are (``settle``)."""
    return flags if flags == expected else settle(flags, lambda grade: grade == expected, grade_again)[0]


@functools.cache
def graded() -> dict:
    """Every variant of both cases built, committed and graded: {"deliveries", "accepted", "pristine", "suite", "groups",
    "regraded", "repeated"}, each keyed by (case name, variant). The acceptance runs side by side first, the longest first (a base
    waits out each bounded wait for what it lacks, and the follow-on's variants run more checks); the node --test runs follow, side by
    side.

    A result that disagrees with what its variant declares is graded again, alone, until a grade agrees (``settle``): ``regraded``
    names the results that needed it and ``repeated`` those whose first regrade disagreed too. A defect disagrees every time. What
    does not is the machine. The base's own tests start a server on a random port, and on a machine that other work also uses a
    request can reach another project's server that holds the same port number (it is answered with that project's JSON,
    ``{"game":"g"}`` where a ticket was expected) or one that resets it ("socket hang up"). The probes of 2026-11-01 saw 32 of 928
    concurrent ``node --test`` runs end that way, 19 in a reset and 13 in a wrong answer, and 0 to 8 results per execution of this
    suite disagree the first time (docs/experiments/brownfield-flake-20261101/). It does not repeat: the same result disagreeing
    twice in a row is a variant or a check that wavers, and that is what ``repeated`` counts."""
    tmp = Path(tempfile.mkdtemp(prefix="brownfield-tickets-"))
    unittest.addModuleCleanup(shutil.rmtree, tmp, True)
    jobs = sorted(((case, variant) for case in GRADED_CASES for variant in case.builder.VARIANTS),
                  key=lambda job: (job[1] != "base", job[0] is not ESCALATION))
    groups: set = set()

    def build(job):
        case, variant = job
        return (case.name, variant), committed(case.builder.build(tmp / case.name / variant, variant))

    with concurrent.futures.ThreadPoolExecutor(POOL) as pool:
        deliveries = dict(pool.map(build, jobs))

        def accept(job):
            case, variant = job
            return (case.name, variant), quality.acceptance(deliveries[case.name, variant], case.block, groups=groups,
                                                            stop=lambda: None, logs=tmp / "logs" / case.name / variant,
                                                            ports=case.entry["quality"]["refuse_ports"])

        accepted = dict(pool.map(accept, jobs))
        runs = [(job, kind) for job in jobs for kind in ("pristine", "suite") if kind == "pristine" or suite_wanted(*job)]
        ran = dict(pool.map(lambda run_: ((run_[1], run_[0][0].name, run_[0][1]),
                                          base_tests(deliveries[run_[0][0].name, run_[0][1]], run_[1])), runs))
    results = {"accepted": accepted, "pristine": {key[1:]: done for key, done in ran.items() if key[0] == "pristine"},
               "suite": {key[1:]: done for key, done in ran.items() if key[0] == "suite"}}
    by_name = {case.name: case for case in GRADED_CASES}
    regraded, repeated = [], []
    for kind, graded_kind in results.items():
        for (name, variant), result in list(graded_kind.items()):
            case = by_name[name]
            if agrees(case, variant, kind, result):
                continue
            regraded.append((kind, name, variant))
            final, _, again = settle(result, lambda grade: agrees(case, variant, kind, grade),
                                     lambda: accept((case, variant))[1] if kind == "accepted" else base_tests(deliveries[name, variant], kind))
            graded_kind[name, variant] = final
            if again:
                repeated.append((kind, name, variant))
    return {"deliveries": deliveries, "groups": groups, "regraded": regraded, "repeated": repeated, **results}


class SettleTest(unittest.TestCase):
    """Regrading a result that disagrees: alone, bounded, and it stops at the first grade that agrees."""

    @staticmethod
    def graders(*grades):
        calls = []

        def again():
            calls.append(len(calls))
            return grades[len(calls) - 1]
        return again, calls

    def test_a_first_regrade_that_agrees_stands_and_is_not_a_repeat(self):
        again, calls = self.graders("ok")
        self.assertEqual(settle("bad", lambda grade: grade == "ok", again), ("ok", 1, False))
        self.assertEqual(len(calls), 1)

    def test_a_second_disagreement_is_a_repeat_and_the_first_grade_after_it_that_agrees_stands(self):
        again, calls = self.graders("bad again", "ok", "never read")
        self.assertEqual(settle("bad", lambda grade: grade == "ok", again), ("ok", 2, True))
        self.assertEqual(len(calls), 2, "grading stops at the first grade that agrees")

    def test_a_result_that_never_agrees_is_graded_exactly_the_regrades_again_and_the_last_grade_stands(self):
        again, calls = self.graders("b1", "b2", "b3", "never read")
        self.assertEqual(settle("b0", lambda grade: False, again), ("b3", REGRADES, True))
        self.assertEqual(len(calls), REGRADES)

    def test_one_regrade_is_enough_for_a_collision_and_a_defect_costs_every_regrade(self):
        # The cost of the rule: a variant that really disagrees is graded REGRADES more times, and only then does the suite say so.
        again, calls = self.graders(*["bad"] * REGRADES)
        final, done, repeated = settle("bad", lambda grade: grade == "ok", again)
        self.assertEqual((final, done, repeated, len(calls)), ("bad", REGRADES, True, REGRADES))

    def test_flags_that_are_the_declared_ones_are_not_graded_again(self):
        again, calls = self.graders()
        self.assertEqual(agreed([False, True, False], [False, True, False], again), [False, True, False])
        self.assertEqual(calls, [])

    def test_a_middle_check_that_a_foreign_server_failed_is_graded_again_and_the_agreeing_flags_stand(self):
        # The run through the harness failed the base's own node tests (the second check) once; the flags graded again agree.
        again, calls = self.graders([False, True, False])
        self.assertEqual(agreed([False, False, False], [False, True, False], again), [False, True, False])
        self.assertEqual(len(calls), 1)

    def test_a_middle_check_that_really_fails_is_still_reported_after_every_regrade(self):
        again, calls = self.graders(*[[False, False, False]] * REGRADES)
        self.assertEqual(agreed([False, False, False], [False, True, False], again), [False, False, False])
        self.assertEqual(len(calls), REGRADES)


class SuiteAgreementTest(unittest.TestCase):
    """A base's expected missing-tests failure must be distinguishable from an unrelated suite failure."""

    @staticmethod
    def result(returncode: int, stdout: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")

    @staticmethod
    def graders(*grades):
        calls = []

        def again():
            calls.append(len(calls))
            return grades[len(calls) - 1]
        return again, calls

    def test_assignment_and_import_base_suite_requires_the_known_missing_tests_failure(self):
        expected = self.result(1, "FAIL: the delivery's own node --test passes 117 tests, no more than the base's 117")
        unrelated = self.result(1, "FAIL: the delivery's own node --test: 116 pass, 1 fail (rc 1); failing: restart")
        for case in (ASSIGNMENT, IMPORT):
            with self.subTest(case=case.name):
                self.assertTrue(agrees(case, "base", "suite", expected))
                self.assertFalse(agrees(case, "base", "suite", unrelated))

    def test_assignment_and_import_base_suite_pass_does_not_agree_with_the_missing_tests_failure(self):
        unexpected_pass = self.result(0, "no more than the base's 117")
        for case in (ASSIGNMENT, IMPORT):
            with self.subTest(case=case.name):
                self.assertFalse(agrees(case, "base", "suite", unexpected_pass))

    def test_escalation_base_and_nonbase_suite_cases_still_require_success(self):
        success = self.result(0)
        failure = self.result(1, "FAIL: unrelated test failure")
        cases = ((case, variant) for case in GRADED_CASES for variant in case.builder.VARIANTS
                 if not (case is not ESCALATION and variant == "base"))
        for case, variant in cases:
            with self.subTest(case=case.name, variant=variant):
                self.assertTrue(agrees(case, variant, "suite", success))
                self.assertFalse(agrees(case, variant, "suite", failure))

    def test_an_unrelated_base_suite_failure_stays_disagreeing_after_bounded_settle(self):
        unrelated = self.result(1, "FAIL: the delivery's own node --test: 116 pass, 1 fail (rc 1); failing: restart")
        again, calls = self.graders(*[unrelated] * REGRADES)
        final, done, repeated = settle(unrelated, lambda grade: agrees(ASSIGNMENT, "base", "suite", grade), again)
        self.assertEqual((final.returncode, done, repeated, len(calls)), (1, REGRADES, True, REGRADES))


class CaseDeclarationTest(unittest.TestCase):
    """The catalog entries: the pin, the follow-on, the grades and the held-out files."""

    def test_the_declared_ids_are_exactly_each_modules_checks_with_a_grade_and_a_source_and_the_existing_behaviour_first(self):
        for case in GRADED_CASES:
            with self.subTest(case=case.name):
                self.assertEqual(case.ids, list(quality.load_checks(case.block["module"], quality.HERE / "checks").CHECKS))
                for item in case.block["checks"]:
                    self.assertIn(item["grade"], ("fail-to-pass", "pass-to-pass"), item["id"])
                    self.assertTrue(item["source"].strip(), f"{item['id']} quotes what it reads")
                count = len(case.pass_to_pass)
                self.assertEqual(set(case.ids[:count]), case.pass_to_pass, "the existing behaviour is checked first")
                self.assertEqual(case.entry["quality"]["refuse_ports"], [4180])

    def test_the_pin_is_the_fixtures_digest_and_resolves(self):
        self.assertEqual(ASSIGNMENT.entry["base"]["fixture"], "node-tickets")
        self.assertEqual(brownfield.digest(FIXTURE), ASSIGNMENT.entry["base"]["digest"],
                         "a change to fixtures/node-tickets is a change to this case: update the pin with it")
        self.assertEqual(brownfield.resolve(ASSIGNMENT.entry), FIXTURE)

    def test_the_follow_on_runs_the_first_cases_checks_again_and_retention_and_starts_from_no_base(self):
        name, _prompt, checks, follows = run.load_case(run.parser().parse_args(["--case", "ticket-escalation"]))
        self.assertEqual((name, follows), ("ticket-escalation", "ticket-assignment"))
        self.assertEqual(checks, ASSIGNMENT.entry["checks"] + ESCALATION.entry["checks"] + ESCALATION.entry["retention"])
        self.assertTrue(all("PRIOR_WORK" in check for check in ESCALATION.entry["retention"]))
        self.assertNotIn("base", ESCALATION.entry, "a follow-on starts from the followed run's checkout")
        self.assertEqual(run.case_quality("ticket-escalation")["acceptance"]["module"], "ticket_escalation_accept")
        self.assertTrue(ESCALATION.entry.get("retention_source"))

    def test_the_acceptance_modules_and_the_references_are_held_out(self):
        held = boundary.held_out_files(CASES)
        markers = quality.held_out_markers([case.block for case in GRADED_CASES])
        for path in ("test/shiploop_e2e/checks/ticket_assignment_accept.py", "test/shiploop_e2e/checks/ticket_escalation_accept.py",
                     "test/shiploop_e2e/checks/ticket_import_accept.py", "test/fixtures/quality/reference_ticket_assignment.py",
                     "test/fixtures/quality/reference_ticket_escalation.py", "test/fixtures/quality/reference_ticket_import.py"):
            with self.subTest(path=path):
                self.assertIn(path, held)
                self.assertIn(Path(path).stem, markers)

    def test_the_prompts_name_none_of_the_latent_facts(self):
        # What the base keeps in its documents and code, which the requests depend on and leave unnamed.
        for case in GRADED_CASES:
            prompt = case.entry["prompt"].lower()
            for word in ("audit", "outbox", "envelope", "409", "cursor", "data_file", "--raw", "weekly", "worker_interval",
                         "x-actor", "decision", "max_body", "65536", "rewrit", "data file"):
                with self.subTest(case=case.name, word=word):
                    self.assertNotIn(word, prompt)

    def test_the_style_is_left_out_of_breadth_by_name(self):
        breadth = json.loads(run.SUITES.read_text())["breadth"]
        self.assertNotIn("brownfield", breadth["styles"])
        for case in GRADED_CASES:
            self.assertEqual(case.entry["style"], "brownfield")
        self.assertIn("ticket-assignment", breadth["not_covered"]["brownfield"])

    def test_the_scorecard_requires_both_cases_acceptance(self):
        for case in GRADED_CASES:
            with self.subTest(case=case.name):
                self.assertTrue(scorecard.requires_acceptance(case.name))
                unmeasured: dict = {}
                result = {"case": case.name, "pass": True, "quality": {"acceptance": {"observed": False, "reason": "r"}}}
                self.assertEqual(scorecard.accuracy(result, unmeasured)["floor"], scorecard.UNOBSERVED)


class BaseFixtureTest(unittest.TestCase):
    """fixtures/node-tickets: an ordinary team's service of the size D7 asks for, which never names the harness."""

    def files(self) -> list[Path]:
        return brownfield.base_files(FIXTURE)

    def test_it_never_names_the_harness_or_what_is_planted(self):
        pattern = re.compile(r"shiploop|e2e|held.out|calibrat|planted|latent|fail-to-pass|pass-to-pass|\bai\b|llm", re.I)
        found = [f"{path.relative_to(FIXTURE)}: {match.group(0)}" for path in self.files()
                 for match in [pattern.search(path.read_text())] if match]
        self.assertEqual(found, [])

    def test_it_is_medium_sized(self):
        lines = {path: len(path.read_text().splitlines()) for path in self.files()}
        source = sum(n for path, n in lines.items() if path.suffix == ".js" and path.relative_to(FIXTURE).parts[0] != "test")
        tests = sum(n for path, n in lines.items() if path.relative_to(FIXTURE).parts[0] == "test")
        self.assertTrue(1500 <= source <= 2500, f"{source} lines of source")
        self.assertTrue(3000 <= sum(lines.values()) <= 4500, f"{sum(lines.values())} lines in all")
        self.assertGreater(tests, 1000)

    def test_its_decision_records_include_a_superseded_one_and_a_template_that_is_not_a_decision(self):
        records = sorted(path.name for path in (FIXTURE / "docs" / "decisions").glob("0*.md"))
        self.assertEqual(len(records), 8)
        self.assertIn("Status: Superseded by", (FIXTURE / "docs/decisions/0003-offset-pagination.md").read_text())
        self.assertTrue((FIXTURE / "docs/decisions/template.md").is_file())

    def test_the_ground_truth_names_every_check_and_every_decision_record(self):
        table = GROUND_TRUTH.read_text()
        for case in GRADED_CASES:
            for ident in case.ids:
                with self.subTest(check=ident):
                    self.assertIn(f"`{ident}`", table)
        for record in (FIXTURE / "docs" / "decisions").glob("*.md"):
            with self.subTest(record=record.name):
                self.assertIn(record.name, table)


# A preload for `node --test`: one line, "family address", for every server that starts listening, appended to $LISTEN_LOG.
LISTEN_RECORDER = """'use strict';
const fs = require('node:fs');
const net = require('node:net');
const listen = net.Server.prototype.listen;
net.Server.prototype.listen = function recorded(...args) {
  this.once('listening', () => {
    const address = this.address();
    if (address && typeof address === 'object') fs.appendFileSync(process.env.LISTEN_LOG, `${address.family} ${address.address}\\n`);
  });
  return listen.apply(this, args);
};
"""


@needs_node
class FixtureAddressTest(unittest.TestCase):
    """The ticket fixtures' own tests start their service on 127.0.0.1, the address their client calls.

    A service that listens on every address can be given a port number that another program on the machine already holds on
    127.0.0.1, and a call to 127.0.0.1 then reaches that program: the test fails on a dropped call, takes a JSON answer for the
    service's, or never ends on any other answer. Measured on 2026-11-22 with the service on every address as 20 of 1,600 runs
    of the base's tests that failed or never ended, against 0 of 1,600 with it on 127.0.0.1
    (docs/experiments/sdlc-structure-20261119/evidence/port-mixup.txt)."""

    def test_every_server_the_fixtures_own_tests_start_listens_on_the_address_their_client_calls(self):
        for name in ("node-tickets", "node-tickets-assigned"):
            with self.subTest(fixture=name), tempfile.TemporaryDirectory(prefix="fixture-address-") as raw:
                copy, recorder, log = Path(raw) / "copy", Path(raw) / "record_listens.js", Path(raw) / "listens.txt"
                shutil.copytree(brownfield.FIXTURES / name, copy)
                recorder.write_text(LISTEN_RECORDER)
                log.write_text("")
                with mock.patch.dict(os.environ, {"LISTEN_LOG": str(log), "NODE_OPTIONS": f'--require "{recorder}"'}):
                    done = fixture_process.run_owned(["node", "--test"], cwd=copy, timeout=120)
                self.assertEqual(done.returncode, 0, (done.stdout + done.stderr)[-1500:])
                listens = log.read_text().splitlines()
                self.assertTrue(listens, "the fixture's tests started no server")
                self.assertEqual(sorted(set(listens)), ["IPv4 127.0.0.1"])


@needs_node
class CalibrationTest(unittest.TestCase):
    """Every variant of both cases, graded by the held-out checks and the base's pristine tests."""

    @classmethod
    def setUpClass(cls):
        cls.graded = graded()

    def failed(self, case: Case, variant: str) -> set:
        block = self.graded["accepted"][case.name, variant]
        self.assertTrue(block["observed"], block)
        return {row["id"] for row in block["checks"] if not row["pass"]}

    def notes(self, case: Case, variant: str) -> dict:
        return {row["id"]: row["note"] for row in self.graded["accepted"][case.name, variant].get("checks", []) if not row["pass"]}

    def test_each_base_fails_every_fail_to_pass_check_and_passes_the_pass_to_pass_ones_and_its_pristine_tests(self):
        for case in GRADED_CASES:
            with self.subTest(case=case.name):
                self.assertEqual(self.failed(case, "base"), case.fail_to_pass, self.notes(case, "base"))
                pristine = self.graded["pristine"][case.name, "base"]
                self.assertEqual(pristine.returncode, 0, pristine.stdout)
                self.assertIn("117 of 117 tests", pristine.stdout)

    def test_the_references_and_the_alternatives_pass_every_check_and_the_pristine_tests(self):
        for case in GRADED_CASES:
            for variant in ("reference", "alternative"):
                with self.subTest(case=case.name, variant=variant):
                    self.assertEqual(self.failed(case, variant), set(), self.notes(case, variant))
                    pristine = self.graded["pristine"][case.name, variant]
                    self.assertEqual(pristine.returncode, 0, pristine.stdout)

    def test_a_grade_that_disagrees_twice_in_a_row_is_rare(self):
        # A collision with another project's server is the machine's and does not repeat (``regraded`` counts those, and the machine sets
        # their number: 0 to 8 an execution on a busy host). The same result disagreeing again on its first regrade is a variant or a check
        # that wavers: more than a few of them is what this guard is for.
        self.assertLessEqual(len(self.graded["repeated"]), 4,
                             {"repeated": self.graded["repeated"], "first_grades_that_disagreed": len(self.graded["regraded"])})

    def test_each_variant_fails_exactly_the_checks_its_defect_reads(self):
        for case in GRADED_CASES:
            self.assertEqual(set(case.expected), set(case.builder.VARIANTS))
            for variant, expected in case.expected.items():
                with self.subTest(case=case.name, variant=variant):
                    self.assertEqual(self.failed(case, variant), expected, self.notes(case, variant))
                    pristine = self.graded["pristine"][case.name, variant]
                    self.assertEqual(pristine.returncode != 0, variant in case.pristine, failing(pristine))
        self.assertEqual(set(), self.graded["groups"], "every server the checks started was ended")

    def test_every_check_is_failed_by_some_defect_and_every_defect_by_some_check(self):
        for case in GRADED_CASES:
            with self.subTest(case=case.name):
                defects = list(case.builder.DEFECTS)
                caught = set().union(*(case.expected[variant] for variant in defects))
                self.assertEqual(caught, set(case.ids), "a check no defect fails could never fail")
                unseen = [variant for variant in defects if not case.expected[variant] and variant not in case.pristine]
                self.assertEqual(unseen, [], "a defect neither the held-out checks nor the pristine tests fail would go unnoticed")

    def test_the_pass_to_pass_checks_see_what_the_bases_own_tests_do_not(self):
        # A regression of existing behaviour the base's tests leave untested: only a held-out pass-to-pass check sees it.
        for case in GRADED_CASES:
            with self.subTest(case=case.name):
                self.assertTrue(case.expected["update-rejects-resolved"] <= case.pass_to_pass)
                self.assertNotIn("update-rejects-resolved", case.pristine)

    def test_the_defects_that_edit_the_bases_tests_pass_their_own_suite_and_fail_the_pristine_one(self):
        for case in GRADED_CASES:
            for variant, test_file in case.builder.EDITS_BASE_TESTS.items():
                with self.subTest(case=case.name, variant=variant):
                    delivery = self.graded["deliveries"][case.name, variant]
                    self.assertNotEqual((delivery / test_file).read_bytes(), (FIXTURE / test_file).read_bytes())
                    own = self.graded["suite"][case.name, variant]
                    self.assertEqual(own.returncode, 0, own.stdout)
                    self.assertIn("FAIL: the base's pristine tests against the delivered source",
                                  self.graded["pristine"][case.name, variant].stdout)

    def test_the_planted_defect_is_the_bases_own_listing_filter(self):
        # The base lists a ticket that matches any one filter; the request's "every filter" needs it fixed, and never names it.
        line = "  return given.some(([field, value]) => ticket[field] === value);\n"
        self.assertIn(line, (FIXTURE / "src/tickets/query.js").read_text())
        for case, variant in ((ASSIGNMENT, "filter-or"), (ESCALATION, "filter-or-again")):
            with self.subTest(variant=variant):
                self.assertIn(line, (self.graded["deliveries"][case.name, variant] / "src/tickets/query.js").read_text())
        self.assertNotIn(line, (self.graded["deliveries"][ASSIGNMENT.name, "reference"] / "src/tickets/query.js").read_text())

    def test_the_suite_check_asks_for_new_tests_beside_the_bases(self):
        for case in (ASSIGNMENT, IMPORT):
            self.assertIn("no more than the base's 117", self.graded["suite"][case.name, "base"].stdout)
        self.assertEqual(self.graded["suite"][ESCALATION.name, "base"].returncode, 0, "the first run added tests of its own")
        for case in GRADED_CASES:
            for variant in ("reference", "alternative"):
                with self.subTest(case=case.name, variant=variant):
                    own = self.graded["suite"][case.name, variant]
                    self.assertEqual(own.returncode, 0, own.stdout)

    def test_an_edit_that_no_longer_applies_fails_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            for builder in (first, second, third):
                with self.subTest(builder=builder.__name__), \
                        mock.patch.dict(builder.DEFECTS, {"stale": [("src/server.js", "no such text", "x")]}), \
                        mock.patch.object(builder, "VARIANTS", (*builder.VARIANTS, "stale")):
                    with self.assertRaisesRegex(ValueError, "occurs 0 times"):
                        builder.build(Path(tmp) / builder.__name__, "stale")


SPEC_BEFORE = "# Spec\n\n## R-1 Ticket assignment\n\nPUT /tickets/:id/assignee assigns a ticket.\n\n## R-2 The assignee filter\n"
SPEC_AFTER = SPEC_BEFORE + "\n## R-3 Bulk reassignment\n\n## R-4 Escalation of urgent tickets to ONCALL\n"


@needs_lsof
class CaseChecksTest(unittest.TestCase):
    """The cases' own checks, run as the harness runs them after a delivery (run.run_checks)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        e2e.isolate_git(self)

    def checks(self, work: Path, checks: list[str], prior: Path | None = None) -> list[bool]:
        env = {"PRIOR_WORK": str(prior)} if prior else None
        return [row["pass"] for row in run.run_checks(work, checks, timeout=180, env=env)]

    def expect(self, work: Path, checks: list[str], expected: list[bool], prior: Path | None = None) -> list[bool]:
        """The verdicts of ``checks`` on ``work``, graded again, alone, until they are ``expected`` (``settle``); what stands is returned. These
        checks start the product's server and node's own tests on ports that other work on the machine may hold, as the graded results do."""
        got = self.checks(work, checks, prior)
        return got if got == expected else settle(got, lambda grade: grade == expected, lambda: self.checks(work, checks, prior))[0]

    def test_the_first_cases_base_fails_the_suite_and_http_checks_and_its_deliveries_pass_all(self):
        for variant, expected in (("base", [False, True, False]), ("reference", [True, True, True]),
                                  ("alternative", [True, True, True])):
            with self.subTest(variant=variant):
                work = committed(first.build(self.tmp / variant, variant))
                self.assertEqual(self.expect(work, ASSIGNMENT.entry["checks"], expected), expected)

    def delivery(self, name: str, builder, variant: str, spec: str) -> Path:
        work = builder.build(self.tmp / name, variant)
        (work / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
        (work / "docs" / "shiploop" / "spec.md").write_text(spec)
        return committed(work)

    def test_the_follow_on_passes_its_regression_feature_and_retention_checks_only_when_it_builds_on_the_first_run(self):
        prior = self.delivery("prior", first, "reference", SPEC_BEFORE)
        checks = ASSIGNMENT.entry["checks"] + ESCALATION.entry["checks"] + ESCALATION.entry["retention"]
        for variant in ("reference", "alternative"):
            with self.subTest(variant=variant):
                work = self.delivery(variant, second, variant, SPEC_AFTER)
                self.assertEqual(self.expect(work, checks, [True] * len(checks), prior), [True] * len(checks))
        unchanged = self.delivery("unchanged", second, "base", SPEC_BEFORE)
        expected_unchanged = [True, True, True, False, False, True, True, False, False]
        self.assertEqual(self.expect(unchanged, checks, expected_unchanged, prior), expected_unchanged,
                         "the first run's delivery as it was: regression passes, the new feature, the tests and the spec do not")
        lost = self.delivery("lost", second, "reference", SPEC_AFTER.replace("## R-2 The assignee filter\n", ""))
        (lost / "docs" / "operations.md").unlink()
        expected_lost = [False, True, True, False]
        self.assertEqual(self.expect(lost, ESCALATION.entry["retention"], expected_lost, prior), expected_lost,
                         "a file of the first run deleted and a requirement ID dropped")


@needs_lsof
class ThroughMainTest(e2e.CaseRunCase):
    """One fake-host run of the first case: the host starts in the committed base, the run is counted from it, and the quality
    phase grades the delivery fail-to-pass. The fake product adds hello.py and changes nothing of the base, so it is the base."""

    def setUp(self):
        super().setUp()
        e2e.isolate_git(self)

    def test_the_host_starts_in_the_base_and_the_delivery_is_graded_from_it(self):
        with mock.patch.object(run, "review_export", return_value="review export: fake"):
            code, result, _printed, out = self.case_main("ticket-assignment", "--case", "ticket-assignment")
        self.assertEqual(code, 1, "the unchanged base fails its new-feature checks")
        self.assertEqual(result["base"]["fixture"], "node-tickets")
        self.assertEqual(json.loads((out / "invocation.json").read_text())["base"], result["base"])
        self.assertEqual(result["committed"]["start_head"], result["base"]["start_head"])
        # The second check runs the base's own node tests, on ports that other work on the machine may hold, as the graded results do:
        # flags that are not the declared ones are graded again, alone, until they are (CaseChecksTest.expect does the same for a built delivery).
        again = lambda: [row["pass"] for row in run.run_checks(out / "work", ASSIGNMENT.entry["checks"], timeout=180)]  # noqa: E731
        self.assertEqual(agreed([check["pass"] for check in result["checks"]], [False, True, False], again), [False, True, False])
        acceptance = result["quality"]["acceptance"]
        self.assertTrue(acceptance["observed"], acceptance)
        self.assertEqual({row["id"] for row in acceptance["checks"] if not row["pass"]}, ASSIGNMENT.fail_to_pass)
        card = scorecard.score(out)
        self.assertEqual(card["accuracy"]["floor"], scorecard.FAIL)
        self.assertTrue(card["accuracy"]["acceptance_required"])




import contextlib


class BrownfieldSocketCleanupTest(unittest.TestCase):
    """Exact loaded delegation instances, real HTTP keepalive, and owner-scoped closure."""

    @contextlib.contextmanager
    def server(self):
        import http.server
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def do_GET(self):
                body = b'{"owned": true}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()

            def log_message(self, *args):
                pass

        class Server(http.server.ThreadingHTTPServer):
            daemon_threads = False
            block_on_close = False

            def __init__(self):
                self.accepted = 0
                self.workers = []
                super().__init__(("127.0.0.1", 0), Handler)

            def get_request(self):
                client, address = super().get_request()
                self.accepted += 1
                return client, address

            def process_request_thread(self, request, address):
                self.workers.append(threading.current_thread())
                super().process_request_thread(request, address)

        server = Server()
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02))
        thread.start()
        try:
            yield server, f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            for worker in server.workers:
                worker.join(3)
            self.assertFalse(thread.is_alive(), "test-owned HTTP listener did not stop")
            self.assertFalse(any(t.is_alive() for t in server.workers), "test-owned HTTP handler did not stop")

    def test_actual_four_module_aliases_close_only_their_own_thread_and_base_pool(self):
        import threading
        modules = [quality.load_checks(name, quality.HERE / "checks") for name in (
            "ticket_assignment_accept", "ticket_import_accept", "ticket_escalation_accept", "ticket_sla_accept")]
        owners = [modules[0], modules[1].A, modules[2].A, modules[3].E.A]
        self.assertIs(modules[3].A, modules[3].E.A)
        self.assertEqual(len({id(owner) for owner in owners}), 4, "each loader must retain its exact helper instance")
        separate = quality.load_checks("ticket_assignment_accept", quality.HERE / "checks")
        with self.server() as (server, base), self.server() as (_other_server, other):
            key = (threading.get_ident(), base)
            other_key = (threading.get_ident(), other)
            sockets, other_sockets = [], []
            try:
                for owner in owners:
                    self.assertEqual(owner.call(base, "GET", "/"), (200, {"owned": True}))
                    client = owner._connections[key]
                    sock, fd = client.sock, client.sock.fileno()
                    self.assertGreaterEqual(fd, 0)
                    self.assertEqual(owner.call(base, "GET", "/"), (200, {"owned": True}))
                    self.assertIs(owner._connections[key], client)
                    self.assertIs(client.sock, sock)
                    self.assertEqual(client.sock.fileno(), fd)
                    sockets.append(sock)
                    self.assertEqual(owner.call(other, "GET", "/")[0], 200)
                    other_sockets.append(owner._connections[other_key].sock)
                self.assertEqual(server.accepted, 4, "two GETs per owner must use exactly one connection each")
                self.assertEqual(separate.call(base, "GET", "/")[0], 200)
                separate_socket = separate._connections[key].sock
                for index, (module, owner, sock) in enumerate(zip(modules, owners, sockets)):
                    with self.subTest(module=module.__name__, owner=id(owner), fd=sock.fileno()):
                        cleanup = getattr(module, "cleanup", None)
                        if callable(cleanup):
                            cleanup(base)
                        # Exercise live unrelated controls before the expected RED closure assertion.
                        for live_owner, live_socket in zip(owners[index + 1:], sockets[index + 1:]):
                            self.assertEqual(live_owner.call(base, "GET", "/")[0], 200)
                            self.assertIs(live_owner._connections[key].sock, live_socket)
                        for other_owner, other_socket in zip(owners, other_sockets):
                            self.assertEqual(other_owner.call(other, "GET", "/")[0], 200)
                            self.assertIs(other_owner._connections[other_key].sock, other_socket)
                        self.assertEqual(separate.call(base, "GET", "/")[0], 200)
                        self.assertIs(separate._connections[key].sock, separate_socket)
                        self.assertEqual(sock.fileno(), -1, "real module cleanup must close its actual helper's retained socket")
                        self.assertNotIn(key, owner._connections, "real module cleanup must remove its actual pool entry")
                        self.assertTrue(callable(cleanup), "acceptance module must export its optional cleanup hook")
            finally:
                # Fallbacks own all created pools, including old-source runs with no public hook.
                for owner in owners + [separate]:
                    owner.hang_up(base)
                    owner.hang_up(other)
                self.assertTrue(all(sock.fileno() == -1 for sock in sockets + other_sockets))
                for owner in owners + [separate]:
                    self.assertNotIn(key, owner._connections)
                    self.assertNotIn(other_key, owner._connections)


if __name__ == "__main__":
    unittest.main()
