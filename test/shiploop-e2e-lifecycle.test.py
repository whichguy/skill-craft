#!/usr/bin/env python3
"""No-model checks for the E2E harness's resource lifecycle (test/shiploop_e2e/lifecycle.py; SPEC "The resource lifecycle",
build step 7; R19 and R20 of the final verdict).

Build step 7 is done when, by script-run checks: a conflicting lease is refused; crash-and-retry cleanup works without
touching unrelated processes (a decoy with the orphan's very command line must survive); the evidence survives cleanup.

Every process a test signals is one it started: the in-process tests refuse any group signal outside them (``guard``), and the
harness subprocess sees an empty listener table (a fake ``lsof`` first on PATH). Leases live in each test's own folder
(``SHIPLOOP_E2E_LEASES``), and the runs root is the test's folder, so no other session's run or lease can change a result.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(HERE))
import delivery  # noqa: E402
import lifecycle  # noqa: E402
import listeners  # noqa: E402
import run  # noqa: E402

# A Claude-shaped fake host. FAKE_MODE: done (the hello product, committed, and a done run), hang-active (an active run, then
# sleeps), leave-in-group (ends at once, leaving a worker in its own process group). Every mode but done starts that worker, as a
# host's background command is, and FAKE_LOG.sessions / FAKE_LOG.children name what it started.
FAKE_CLAUDE = f"""#!{sys.executable}
import json, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
argv = sys.argv[1:]
with open(os.environ["FAKE_LOG"] + ".sessions", "a") as log:
    log.write(json.dumps({{"pid": os.getpid(), "argv": argv}}) + "\\n")
plugin = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else None
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model", "claude_code_version": "0.0.1-fake",
                  "slash_commands": ["skill-craft:shiploop"],
                  "plugins": [{{"name": "skill-craft", "path": plugin}}] if plugin else []}}), flush=True)
print(json.dumps({{"type": "assistant", "message": {{"content": [{{"type": "tool_use", "name": "Bash",
                  "input": {{"command": f"python3 {{plugin}}/skills/shiploop/scripts/shiploop next"}}}}]}}}}), flush=True)
mode = os.environ.get("FAKE_MODE", "done")
if mode == "done":
    Path("hello.py").write_text('print("Hello, world!")\\n')
    Path("test_hello.py").write_text(
        "import subprocess, sys, unittest\\n"
        "class T(unittest.TestCase):\\n"
        "    def test_it(self):\\n"
        "        out = subprocess.run([sys.executable, 'hello.py'], capture_output=True, text=True).stdout\\n"
        "        self.assertEqual(out.strip(), 'Hello, world!')\\n")
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "done", "planning_review": "stage"}})
    Path(".shiploop/report.html").write_text("<html></html>")
    Path(".gitignore").write_text(".shiploop/\\n")
    ident = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
    if not Path(".git").exists():
        subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", *ident, "commit", "-q", "-m", "product"], check=True)
else:
    if mode == "hang-active":
        Path(".shiploop").mkdir(exist_ok=True)
        store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
    worker = subprocess.Popen(["sleep", "300"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(os.environ["FAKE_LOG"] + ".children", "a") as log:
        log.write(f"{{worker.pid}}\\n")
    if mode == "hang-active":
        time.sleep(600)
print(json.dumps({{"type": "result", "subtype": "success", "num_turns": 1, "total_cost_usd": 0.0, "result": "done"}}))
"""

# A process that holds leases until it is killed: argv[1] is a ready file, the rest are keys. It prints nothing.
HOLDER = (
    "import json, os, sys, time\n"
    f"sys.path.insert(0, {str(HERE)!r})\n"
    "import lifecycle\n"
    "lease = lifecycle.take(sys.argv[2:], {'pid': os.getpid(), 'case': 'holder-case', 'output': '/runs/holder-output'})\n"
    "open(sys.argv[1], 'w').write('held')\n"
    "time.sleep(300)\n")


def alive(pid: int) -> bool:
    """Running, and not a zombie (a killed child of this test stays one until it is reaped)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(state) and not state.startswith("Z")


def kill_group(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, signal.SIGKILL)


def gone(pid: int, seconds: float = 8.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return False


def wait_for(path: Path, seconds: float = 30.0) -> str:
    end = time.time() + seconds
    while time.time() < end:
        if path.exists() and path.read_text().strip():
            return path.read_text()
        time.sleep(0.05)
    raise AssertionError(f"{path} never appeared")


class LifecycleCase(unittest.TestCase):
    """A private folder for the test's runs, leases and runs root, and a record of every process group it starts."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.leases = self.tmp / "leases"
        patched = mock.patch.dict(os.environ, {lifecycle.LEASES_ENV: str(self.leases), "SHIPLOOP_E2E_RUNS_ROOT": str(self.tmp),
                                               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                               "SHIPLOOP_PROGRESS": "off"})
        patched.start()
        self.addCleanup(patched.stop)
        self.spawned: set[int] = set()

    def spawn(self, argv: list[str], **kw) -> subprocess.Popen:
        """A process of the test's own, leading its own group, killed (whole group) when the test ends."""
        proc = subprocess.Popen(argv, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, **kw)
        self.spawned.add(proc.pid)
        self.addCleanup(self.end, proc)
        return proc

    @staticmethod
    def end(proc: subprocess.Popen) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()

    def guard(self) -> None:
        """Refuse any group signal the code under test sends outside the groups this test started (the 2026-10-08 incident: a
        mutant of a selector signalled the machine's own listeners)."""
        real = lifecycle._signal_group

        def guarded(pgid: int, number: int) -> None:
            if pgid not in self.spawned:
                raise AssertionError(f"signalled group {pgid}, which this test did not start")
            real(pgid, number)

        patch = mock.patch.object(lifecycle, "_signal_group", guarded)
        patch.start()
        self.addCleanup(patch.stop)

    def run_folder(self, name: str) -> Path:
        out = self.tmp / name
        (out / "work").mkdir(parents=True)
        (out / "invocation.json").write_text(json.dumps({"case": "hello", "host": "claude"}))
        return out

    def hold(self, *keys: str) -> subprocess.Popen:
        """Another harness, in a process of its own, holding ``keys``."""
        ready = self.tmp / f"held-{len(self.spawned)}"
        proc = self.spawn([sys.executable, "-c", HOLDER, str(ready), *keys], env=dict(os.environ))
        wait_for(ready)
        return proc


class LeaseTest(LifecycleCase):
    def test_different_prefixes_on_one_org_cannot_overlap_but_another_org_can(self):
        first_keys = lifecycle.lease_keys({"kind": "salesforce", "org": "de", "prefix": "RunA"})
        second_keys = lifecycle.lease_keys({"kind": "salesforce", "org": "de", "prefix": "RunB"})
        first = lifecycle.take(first_keys, {"pid": os.getpid(), "case": "first"})
        self.addCleanup(first.close)
        with self.assertRaises(lifecycle.Refused):
            unexpected = lifecycle.take(second_keys, {"pid": os.getpid(), "case": "second"})
            self.addCleanup(unexpected.close)
        other = lifecycle.take(lifecycle.lease_keys({"kind": "salesforce", "org": "other", "prefix": "RunB"}),
                               {"pid": os.getpid(), "case": "other"})
        self.addCleanup(other.close)
        first.close()
        following = lifecycle.take(second_keys, {"pid": os.getpid(), "case": "following"})
        following.close()

    def test_a_conflicting_lease_is_refused_naming_its_holder_and_is_free_once_the_holder_dies(self):
        holder = self.hold("platform-salesforce-de-SLChess")
        with self.assertRaises(lifecycle.Refused) as refused:
            lifecycle.take(["platform-salesforce-de-SLChess"], {"pid": os.getpid(), "case": "mine"})
        message = str(refused.exception)
        self.assertIn("platform-salesforce-de-SLChess is leased by the harness of /runs/holder-output", message)
        self.assertIn(f"pid {holder.pid}", message)
        self.assertIn("case holder-case", message)
        # SIGKILL gives the holder no chance to run anything: the kernel gives the lease back.
        os.killpg(holder.pid, signal.SIGKILL)
        holder.wait()
        lease = lifecycle.take(["platform-salesforce-de-SLChess"], {"pid": os.getpid(), "case": "mine"})
        self.assertEqual(lease.keys, ["platform-salesforce-de-SLChess"])
        lease.close()

    def test_a_lease_is_all_or_none(self):
        self.hold("port-3000")
        with self.assertRaises(lifecycle.Refused):
            lifecycle.take(["platform-salesforce-de-SLChess", "port-3000"], {"pid": os.getpid(), "case": "mine"})
        # The key that was free is not kept: another run takes it at once.
        other = self.hold("platform-salesforce-de-SLChess")
        self.assertIsNone(other.poll(), "the platform lease was given back when the port was refused")

    def test_two_leases_in_one_process_conflict_too(self):
        # Suite cases run in threads of one harness: each lease is its own open file, so they exclude each other.
        first = lifecycle.take(["port-3000"], {"pid": os.getpid(), "case": "a"})
        self.addCleanup(first.close)
        with self.assertRaises(lifecycle.Refused):
            lifecycle.take(["port-3000"], {"pid": os.getpid(), "case": "b"})

    def test_a_lease_given_back_leaves_nothing_in_the_state_home(self):
        state = self.tmp / "state"
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(state)}):
            os.environ.pop(lifecycle.LEASES_ENV)
            self.assertEqual(lifecycle.leases_dir(), state / "shiploop-e2e" / "leases")
            lease = lifecycle.take(["port-3000", "platform-x"], {"pid": os.getpid(), "case": "a"})
            self.assertEqual(sorted(path.name for path in lifecycle.leases_dir().iterdir()), ["platform-x.lock", "port-3000.lock"])
            lease.close()
            # run_suites fails a suite that leaves anything in its private state home (empty folders included).
            self.assertEqual(list(state.iterdir()), [])

    def test_a_declared_port_something_listens_on_is_refused(self):
        if shutil.which("lsof") is None:
            self.skipTest("lsof is not installed: the port check is then a note, not a refusal")
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen()
            port = server.getsockname()[1]
            with self.assertRaises(lifecycle.Refused) as refused:
                lifecycle.take([f"port-{port}"], {"pid": os.getpid(), "case": "mine"}, ports=[port])
            self.assertIn(f"port {port} is in use by pid {os.getpid()}", str(refused.exception))
        self.assertFalse((self.leases / f"port-{port}.lock").exists(), "the refused attempt gave its lease back")

    def test_the_keys_are_the_platform_state_and_the_declared_ports(self):
        self.assertEqual(lifecycle.lease_keys({"kind": "salesforce", "org": "de", "prefix": "SLChess"}, [3000, 3000]),
                         ["platform-salesforce-de", "platform-salesforce-de-SLChess", "port-3000"])
        self.assertEqual(lifecycle.lease_keys(None, []), [])
        self.assertEqual(run.case_quality("battleship-scoring").get("refuse_ports"), [3000], "a follow-on inherits the ports")


class StopTest(LifecycleCase):
    def setUp(self):
        super().setUp()
        self.guard()

    def group_row(self, out: Path, proc: subprocess.Popen, role: str = "host", **change) -> dict:
        leader = lifecycle.table([proc.pid])[proc.pid]
        return lifecycle.record(out, "group", id=f"{proc.pid}@test", pgid=proc.pid, role=role, leader={**leader, **change})

    def test_a_recorded_group_is_stopped_whole_and_a_second_cleanup_changes_nothing(self):
        out = self.run_folder("case")
        leader = self.spawn(["sh", "-c", "sleep 300 & sleep 300; wait"])
        time.sleep(0.3)
        members = [row["pid"] for row in lifecycle.table().values() if row["pgid"] == leader.pid]
        self.assertGreaterEqual(len(members), 2)
        self.group_row(out, leader)
        found = lifecycle.cleanup(out)
        self.assertEqual([item["pgid"] for item in found["stopped"]], [leader.pid], found)
        self.assertTrue(all(gone(pid) for pid in members))
        ledger = lifecycle.rows(out)
        again = lifecycle.cleanup(out)
        self.assertEqual({key: value for key, value in again.items() if value and key != "observed"}, {})
        self.assertEqual(lifecycle.rows(out), ledger, "an idempotent cleanup adds no row")

    def test_a_pid_that_now_names_another_process_is_never_signalled(self):
        out = self.run_folder("case")
        decoy = self.spawn(["sleep", "300"])
        self.group_row(out, decoy, started="Thu Jan  1 00:00:00 2026")  # the leader recorded was started at another time
        found = lifecycle.cleanup(out)
        self.assertEqual([item["pgid"] for item in found["reused"]], [decoy.pid], found)
        self.assertTrue(alive(decoy.pid))
        self.assertEqual(lifecycle.open_groups(out), [], "recorded as ended, so it is never looked at again")

    def test_a_group_whose_leader_was_never_seen_is_listed_not_signalled(self):
        out = self.run_folder("case")
        decoy = self.spawn(["sleep", "300"])
        lifecycle.record(out, "group", id="x", pgid=decoy.pid, role="host", leader=None, reason="ps could not run")
        found = lifecycle.cleanup(out)
        self.assertEqual([item["pgid"] for item in found["unverified"]], [decoy.pid], found)
        self.assertTrue(alive(decoy.pid))

    def test_an_orphaned_progress_observer_is_adopted_by_its_record_and_a_lookalike_is_left_alone(self):
        out = self.run_folder("case")
        run_dir = out / ".shiploop-runs" / "work-1" / "run"
        run_dir.mkdir(parents=True)

        def orphan(instance: str) -> int:
            """An observer-shaped process whose starter has exited, as shiploop_progress.start leaves it: its own session, and
            the run directory and instance id on its command line."""
            script = ("import subprocess, sys\n"
                      "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)', '--run-dir', sys.argv[1], "
                      "'--watch', '--instance', sys.argv[2]], start_new_session=True, stdin=subprocess.DEVNULL, "
                      "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                      "print(p.pid)\n")
            pid = int(subprocess.run([sys.executable, "-c", script, str(run_dir), instance], capture_output=True, text=True,
                                     check=True).stdout)
            self.spawned.add(pid)
            self.addCleanup(kill_group, pid)
            return pid

        try:
            observer = orphan("instance-a")
            lookalike = orphan("instance-b")
        except subprocess.CalledProcessError as exc:
            self.fail(exc.stderr)
        if lifecycle.table([observer])[observer]["ppid"] != 1:
            self.skipTest("an orphan is reparented to a subreaper here, not to pid 1")
        # A record whose pid now names another observer of the same run directory (a stale record, a reused pid) adopts nothing.
        (run_dir / lifecycle.OBSERVER_RECORD).write_text(json.dumps({"instance": "instance-a", "pid": lookalike}))
        self.assertEqual(lifecycle.cleanup(out)["stopped"], [])
        self.assertTrue(alive(lookalike))
        (run_dir / lifecycle.OBSERVER_RECORD).write_text(json.dumps({"instance": "instance-a", "pid": observer}))
        found = lifecycle.cleanup(out)
        self.assertEqual([(item["role"], item["pgid"]) for item in found["stopped"]], [("observer", observer)], found)
        self.assertTrue(gone(observer))
        self.assertTrue(alive(lookalike), "same command, another instance id: not this run's observer")


class EvidenceTest(LifecycleCase):
    def delivered(self, name: str) -> Path:
        """A run folder with a committed delivery, its snapshot recorded in result.json and its logs."""
        out = self.run_folder(name)
        work = out / "work"
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        (work / "hello.py").write_text('print("Hello, world!")\n')
        subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(work), "-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-q", "-m",
                        "product"], check=True)
        before = delivery.capture(work, out)
        (out / "result.json").write_text(json.dumps({"case": "hello", "pass": True, "delivery": {"before": before}}))
        for name_ in lifecycle.LOGS:
            (out / name_).write_text("{}\n")
        (out / "home").mkdir()
        return out

    def test_disposal_keeps_the_records_and_the_delivery_reproduces_from_the_bundle(self):
        out = self.delivered("case")
        head = json.loads((out / "result.json").read_text())["delivery"]["before"]["head"]
        records = {path.name: path.read_bytes() for path in out.iterdir() if path.is_file()}
        found = lifecycle.dispose(out)
        self.assertTrue(found["disposed"], found)
        self.assertEqual(sorted(found["removed"]), ["home", "work"])
        self.assertFalse((out / "work").exists())
        for name, data in records.items():
            if name != lifecycle.LEDGER:
                self.assertEqual((out / name).read_bytes(), data, f"{name} survives disposal unchanged")
        restored = delivery.restore(out, self.tmp / "restored", head)
        self.assertEqual((restored / "hello.py").read_text(), 'print("Hello, world!")\n')
        self.assertEqual(lifecycle.dispose(out)["removed"], [], "disposal is idempotent")

    def test_disposal_is_refused_without_a_bundle_that_holds_the_head(self):
        out = self.delivered("case")
        (out / "delivery" / "work.bundle").unlink()
        found = lifecycle.dispose(out)
        self.assertFalse(found["disposed"])
        self.assertIn("delivery/work.bundle", found["missing"])
        self.assertTrue((out / "work" / "hello.py").is_file(), "nothing removed")

    def test_disposal_is_refused_while_a_recorded_group_is_alive_or_a_harness_holds_the_case(self):
        out = self.delivered("case")
        host = self.spawn(["sleep", "300"])
        leader = lifecycle.table([host.pid])[host.pid]
        lifecycle.record(out, "group", id="h", pgid=host.pid, role="host", leader=leader)
        self.assertIn("alive", lifecycle.dispose(out)["refused"])
        lock = listeners.hold_case(out)
        self.addCleanup(lock.close)
        self.assertIn("holds", lifecycle.dispose(out)["refused"])
        self.assertTrue((out / "work").is_dir())


class HarnessCase(LifecycleCase):
    """run.py with the fake Claude host and a plugin build of the test's own."""

    def setUp(self):
        super().setUp()
        self.fake = self.tmp / "claude"
        self.fake.write_text(FAKE_CLAUDE)
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)
        self.plugin = self.tmp / "build" / "plugins" / "skill-craft"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        cli = self.plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        cli.parent.mkdir(parents=True)
        cli.write_text("")
        self.log = self.tmp / "fake-log"
        self.baselines = self.tmp / "baseline-rows.jsonl"  # never the committed file
        tools = self.tmp / "tools"
        tools.mkdir()
        (tools / "lsof").write_text("#!/bin/sh\nexit 1\n")  # an empty listener table: no machine listener changes a run
        (tools / "lsof").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{tools}{os.pathsep}{os.environ['PATH']}", FAKE_LOG=str(self.log))
        # No case here starts a real browser: battleship declares the browser need, and this machine may have one.
        browser = mock.patch.object(run.environment, "autodetect_browser", return_value=None)
        browser.start()
        self.addCleanup(browser.stop)
        patched = mock.patch.dict(os.environ, {"PATH": self.env["PATH"], "FAKE_LOG": str(self.log)})
        patched.start()
        self.addCleanup(patched.stop)
        self.addCleanup(self.kill_started)

    def argv(self, out: Path, *extra: str) -> list[str]:
        return ["--host", "claude", "--backend", "anthropic", "--claude-bin", str(self.fake), "--output", str(out), "--plugin-dir", str(self.plugin),
                "--baseline", str(self.baselines), "--quiet", *extra]

    def main(self, *argv: str, mode: str = "done") -> tuple[int, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.dict(os.environ, {"FAKE_MODE": mode}):
            code = run.main(list(argv))
        return code, printed.getvalue()

    def sessions(self) -> list[dict]:
        path = Path(str(self.log) + ".sessions")
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def children(self) -> list[int]:
        path = Path(str(self.log) + ".children")
        return [int(line) for line in path.read_text().split()] if path.exists() else []

    def kill_started(self) -> None:
        """Every host and worker the fake started, whatever the code under test did (each sleeps at most 600 s)."""
        for pid in [entry["pid"] for entry in self.sessions()] + self.children():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)


class ThroughMainTest(HarnessCase):
    def test_a_launch_beside_a_held_lease_is_refused_before_its_folder_or_host_exists(self):
        self.hold("port-3000")
        out = self.tmp / "battleship"
        with self.assertRaises(lifecycle.Refused) as refused:
            self.main(*self.argv(out, "--case", "battleship"))
        self.assertIn("port-3000 is leased by the harness of /runs/holder-output", str(refused.exception))
        self.assertFalse(out.exists())
        self.assertEqual(self.sessions(), [], "no host started")

    def test_a_run_records_its_resources_and_gives_its_leases_back(self):
        out = self.tmp / "battleship"
        code, printed = self.main(*self.argv(out, "--case", "battleship"))
        result = json.loads((out / "result.json").read_text())
        resources = result["resources"]
        self.assertEqual(resources["leases"], ["port-3000"])
        self.assertTrue(resources["disk"]["ok"])
        self.assertEqual(resources["contention"]["live_runs"], [])
        kinds = [row["kind"] for row in lifecycle.rows(out)]
        for kind in ("lease", "group", "ended", "released", "directories"):
            self.assertIn(kind, kinds)
        directories = next(row for row in lifecycle.rows(out) if row["kind"] == "directories")["directories"]
        self.assertIn("work", [entry["path"] for entry in directories])
        claude = [entry for entry in directories if entry.get("outside_output")]
        self.assertEqual(len(claude), 1)
        self.assertTrue(claude[0]["path"].endswith("-work"), claude)
        self.assertFalse(self.leases.exists() and any(self.leases.iterdir()), "every lease was given back")

    def test_a_session_that_ends_takes_what_it_left_in_its_group_with_it(self):
        self.guard()
        decoy = self.spawn(["sleep", "300"])
        out = self.tmp / "hello"
        self.main(*self.argv(out), mode="leave-in-group")
        [worker] = self.children()
        self.assertTrue(gone(worker), "the worker in the host's group ended with its session")
        self.assertTrue(alive(decoy.pid))
        ended = [row for row in lifecycle.rows(out) if row["kind"] == "ended" and row.get("role") == "host"]
        self.assertEqual([entry["pid"] for entry in ended[0]["left_in_group"]], [worker])

    def test_an_orphan_and_a_low_disk_refuse_a_launch(self):
        orphan_out = self.run_folder("crashed")
        host = self.spawn(["sleep", "300"])
        lifecycle.record(orphan_out, "group", id="h", pgid=host.pid, role="host", leader=lifecycle.table([host.pid])[host.pid])
        out = self.tmp / "hello"
        with self.assertRaises(lifecycle.Refused) as refused:
            self.main(*self.argv(out))
        self.assertIn(f"pid {host.pid} (host", str(refused.exception))
        self.assertIn(f"cleanup {orphan_out}", str(refused.exception))
        self.assertFalse(out.exists())
        os.killpg(host.pid, signal.SIGKILL)
        host.wait()
        with mock.patch.object(lifecycle, "HEADROOM_PER_RUN", 1 << 62), self.assertRaises(lifecycle.Refused) as low:
            self.main(*self.argv(out))
        self.assertIn("headroom", str(low.exception))
        self.assertFalse(out.exists())

    def test_a_suite_records_a_refused_case_and_runs_the_others(self):
        suites = self.tmp / "suites.json"
        suites.write_text(json.dumps({"pair": {"styles": [], "cases": ["hello", "battleship"]}}))
        self.hold("port-3000")
        base = self.tmp / "suite"
        with mock.patch.object(run, "SUITES", suites):
            code, printed = self.main("--suite", "pair", "--serial", *self.argv(base))
        rows = json.loads((base / "suite-result.json").read_text())["cases"]
        by_case = {row["case"]: row for row in rows}
        self.assertTrue(by_case["hello"]["pass"], by_case)
        self.assertIn("port-3000 is leased", by_case["battleship"]["refused"])
        self.assertEqual(code, 1)


class CrashAndRetryTest(HarnessCase):
    """The harness as a task runner meets it: killed with SIGKILL while its host works, then run again."""

    def harness(self, *argv: str, mode: str) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, str(HERE / "run.py"), *argv], env=dict(self.env, FAKE_MODE=mode),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.end_harness, proc)
        return proc

    @staticmethod
    def end_harness(proc: subprocess.Popen) -> None:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        proc.wait()
        if proc.stdout and not proc.stdout.closed:
            proc.stdout.close()

    def test_a_retry_stops_the_killed_harness_s_host_by_its_identity_and_a_decoy_with_its_command_line_survives(self):
        out = self.tmp / "case"
        first = self.harness(*self.argv(out, "--timeout", "120"), mode="hang-active")
        wait_for(Path(str(self.log) + ".children"))
        [session] = self.sessions()
        host = session["pid"]
        [worker] = self.children()
        # The decoy: the same program with the very argv the host got, started by the test in a session of its own.
        decoy_log = self.tmp / "decoy-log"
        decoy_work = self.tmp / "decoy-work"
        decoy_work.mkdir()
        decoy = self.spawn([str(self.fake), *session["argv"]], cwd=decoy_work,
                           env=dict(self.env, FAKE_MODE="hang-active", FAKE_LOG=str(decoy_log)))
        [decoy_worker] = [int(line) for line in wait_for(Path(str(decoy_log) + ".children")).split()]
        self.assertEqual(lifecycle.table([decoy.pid])[decoy.pid]["command"], lifecycle.table([host])[host]["command"])

        first.kill()  # SIGKILL: no handler runs, the lock is dropped, the host works on as an orphan
        first.communicate()
        self.assertTrue(alive(host) and alive(worker), "a SIGKILLed harness leaves its host running")
        self.assertFalse(listeners.case_alive(out))
        files_before = {path.relative_to(out).as_posix() for path in out.rglob("*")}

        # Another launch under the same runs root is refused while the orphan lives, and names the remedy.
        with self.assertRaises(lifecycle.Refused) as refused:
            self.main(*self.argv(self.tmp / "other"))
        self.assertIn(f"pid {host} (host", str(refused.exception))
        self.assertNotIn(f"pid {decoy.pid} ", str(refused.exception))

        # The retry: cleanup first, by recorded identity, then a fresh session finishes the run.
        retry = self.harness("--resume-run", str(out), "--claude-bin", str(self.fake), "--quiet", "--timeout", "120",
                             "--baseline", str(self.baselines), mode="done")
        printed, _ = retry.communicate(timeout=180)
        self.assertTrue(gone(host) and gone(worker), printed)
        self.assertTrue(alive(decoy.pid) and alive(decoy_worker), "nothing the run did not start is touched")
        result = json.loads((out / "result.json").read_text())
        stopped = result["resources"]["cleanup"]["before_resume"]["stopped"]
        self.assertEqual([(item["role"], item["pgid"]) for item in stopped], [("host", host)], printed)
        self.assertTrue(result["pass"], printed)
        files_after = {path.relative_to(out).as_posix() for path in out.rglob("*")}
        self.assertEqual(files_before - files_after, set(), "the cleanup deleted nothing")

        # A cleanup run alone afterwards finds nothing left: it is idempotent.
        ledger = lifecycle.rows(out)
        alone = subprocess.run([sys.executable, str(HERE / "lifecycle.py"), "cleanup", str(out)], env=self.env, capture_output=True,
                               text=True, timeout=60)
        self.assertEqual(alone.returncode, 0, alone.stdout + alone.stderr)
        self.assertEqual(json.loads(alone.stdout)["stopped"], [])
        self.assertEqual(lifecycle.rows(out), ledger)

        # The evidence survives: disposal removes the heavy folders only, and the delivery reproduces from its bundle.
        disposed = subprocess.run([sys.executable, str(HERE / "lifecycle.py"), "dispose", str(out)], env=self.env,
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(disposed.returncode, 0, disposed.stdout + disposed.stderr)
        self.assertFalse((out / "work").exists())
        for name in ("result.json", "invocation.json", *lifecycle.LOGS, "delivery/work.bundle"):
            self.assertTrue((out / name).is_file(), name)
        restored = delivery.restore(out, self.tmp / "restored", result["delivery"]["before"]["head"])
        self.assertEqual(subprocess.run([sys.executable, "hello.py"], cwd=restored, capture_output=True, text=True).stdout,
                         "Hello, world!\n")


if __name__ == "__main__":
    unittest.main()
