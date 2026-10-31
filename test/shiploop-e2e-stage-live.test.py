#!/usr/bin/env python3
"""The stage suite's live tier, one sample (test/shiploop_e2e/stage_suite/stage_live.py; docs/plans/shiploop-stage-suite.md), with a
fake host and no model.

The fake host is a script that stands in for the model, as the fake of test/shiploop-e2e-slice.test.py does: it reads the opening
prompt for the CLI and the run directory, runs the real CLI's `next` (so the packet is issued, traced and archived), lays a
reference output over the execution checkout, submits the result with the navigator's own API, and then keeps running as a model
would. Only the stop at acceptance ends it. The tests run real ShipLoop builds (about a second each) on the node-base fixture.

- The stop: ``accepted_reached`` for every outcome (done, send-back, blocked, add-work), for a park at the Improve stage, for a run
  that is paused or halted, for another action's rows and for a state that could not be read; a fake that sleeps for two minutes is
  ended by the poll long before its timeout and its process is gone; an Improve park (a scenario at step-plan) ends the host with
  the producer's result as the sample's result; a fake that accepts two stages before the poll is an overshoot.
- The grade: a fake that does the right thing passes (P1 caught, C1 and C2 held, value 1.0); one that reports done and leaves E1
  broken fails with P1 not caught and value 2/3; one that sends back where the scenario wants a send-back passes, and where it
  wants a fix it is accepted with the wrong outcome; a host that does nothing records its process verdict, holds no control by
  doing nothing and does not crash; the grade is reproduced from the files alone (also from a copied folder) and a tampered export
  changes it.
- The sessions: a resumable host that ends before acceptance is resumed; one that never moves the run is resumed no more than
  ``run.RESUME_STALL`` times; one that cannot be resumed ends the sample with its status recorded.
- The snapshot: tracked and untracked files that git does not ignore, no ``.git``, no run evidence, a symlink never followed, a
  file below a link left out, a deleted file absent, an export written once.
- The refusals, before anything starts: a ref or a plugin whose navigator has no ``accept_effects``, a host on Ollama that is not
  ready, a plugin_dir with a ref, a stage the engine settles by script. Nothing is written outside the sample folder, no credential
  of the host's environment is written into it, and the sample holds its case lock while the host runs.
- The digest boundary: the module is outside the evaluator digest and the qualification snapshot.
- An operator's stop (SIGTERM or the stop file) that arrives while the stop waits for the accepting command's lock leaves the
  sample "not run" with the half-finished tree unexported; a host whose plugin install failed starts nothing; a regrade refuses
  a folder that was never finished (no export, no export-error.txt, no result) or whose harness lock is held; the abandon
  watchdog bounds a sample after an operator stop as it does after a timeout; a detached progress observer and the recorded
  hosts are ended on the normal path, before the export.
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS / "stage_suite"))
sys.path.insert(0, str(HARNESS))
import boundary  # noqa: E402
import lifecycle  # noqa: E402
import listeners  # noqa: E402
import packets  # noqa: E402
import run  # noqa: E402
import sessionlog  # noqa: E402
import stage_build as sb  # noqa: E402
import stage_live as live  # noqa: E402
import stage_report  # noqa: E402
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402

SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "SHIPLOOP_PROGRESS": "off",
           "SHIPLOOP_KEEPALIVE": "off"}
SECRET = "sk-test-credential-0123456789"  # in the fake host's environment only: it must reach no file of a sample
POLL = 0.3  # seconds between looks at the run (run.POLL_SECONDS is 2)
BROKEN = "validate-existing/broken-works-small-fix"
WRONG_CHECK = "validate-existing/wrong-check"

# The shipped scenarios check a sample with `node -e` / `node --test`: without node a graded sample fails for a reason that does
# not mention node, so the classes (and tests) that grade one say what they need.
needs_node = unittest.skipUnless(shutil.which("node"), "this test grades a sample of a shipped scenario with `node -e` / `node --test` "
                                 "and needs node on PATH (install node to run it); the tests on synthetic scenarios still run")

# argv: the scripts folder, a JSON config, the opening prompt, the session id to resume ("" for a first session). The prompt names
# the CLI and the run directory, as the harness's seed prompt does; the fake reads them from it.
FAKE_HOST = textwrap.dedent('''
    import json, os, re, shutil, subprocess, sys, time
    from pathlib import Path
    scripts, config, prompt, resumed = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]

    def leave_escapee():
        escapee = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True,
                                   stdin=subprocess.DEVNULL)
        Path(config["escapee"]).write_text(str(escapee.pid))

    if config.get("escapee") and config.get("escapee_before_next"):
        # The timeout fixture needs its pipe holder before slow imports or CLI setup can consume the deadline.
        leave_escapee()
    sys.path.insert(0, scripts)
    import shiploop_navigator as nav, shiploop_store as store
    found = re.search(r'python3 "([^"]+)" next --run-dir "([^"]+)"', prompt)
    cli, run_dir = Path(found.group(1)), Path(found.group(2))
    if config.get("pid_file"):
        Path(config["pid_file"]).write_text(str(os.getpid()))
    if config.get("session"):
        print(json.dumps({"type": "system", "subtype": "init", "sessionId": config["session"]}), flush=True)
    if config["mode"] == "exit" or (config["mode"] == "act-when-resumed" and not resumed):
        sys.exit(0)
    if config.get("before_next_delay"):
        time.sleep(config["before_next_delay"])
    printed = subprocess.run([sys.executable, str(cli), "next", f"--run-dir={run_dir}"], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL).stdout
    state = store.read_record(run_dir / "state.md")
    action = nav.current_action(state)["id"]
    reference = Path(config["reference"]) if config.get("reference") else None
    worktree = run_dir.parent / "worktree"
    result = config.get("result")
    if reference is not None:
        if (reference / "tree").is_dir():
            shutil.copytree(reference / "tree", worktree, dirs_exist_ok=True)
        for line in ((reference / "deleted.txt").read_text().split() if (reference / "deleted.txt").exists() else []):
            (worktree / line).unlink()
        result = result or json.loads((reference / "result.json").read_text())
    if config.get("escapee") and not config.get("escapee_before_next"):
        leave_escapee()  # other fixtures still create it after reading the packet
    if config.get("stop_file"):  # an operator asks for the run to end
        (run_dir.parents[2] / "stop").write_text("stop\\n")
    if result is not None and config.get("effects_delay"):
        # What a real `complete` does: under the run lock, the save and then the effects after it (here a slow knowledge close
        # that writes a file into the checkout). The state is saved first, so a poll that lands in the delay sees the action accepted.
        import fcntl, types
        before = state
        after = nav.apply(before, action, result)

        def slow_close(b, a, root):
            time.sleep(config["effects_delay"])
            (worktree / "docs" / "shiploop").mkdir(parents=True, exist_ok=True)
            (worktree / "docs" / "shiploop" / "EFFECT.md").write_text("knowledge close ran\\n")

        nav._knowledge_close = slow_close
        lock = os.open(str(run_dir / ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        nav.accept_effects(types.SimpleNamespace(PACKAGE_ROOT=Path(scripts).parent), run_dir, before, after, action_id=action)
        fcntl.flock(lock, fcntl.LOCK_UN)
    elif result is not None:
        state = nav.apply(state, action, result)
        for _ in range(config.get("extra_stages", 0)):  # a model that goes on before the poll looks: no save in between
            state = nav.apply(state, nav.current_action(state)["id"], {"outcome": "done", "summary": "Fake host overrun"})
        if config.get("redo_result"):  # sent back, and goes on to redo the stage it was sent back to (an Improve stage parks first)
            again = nav.current_action(state)["id"]
            state = nav.apply(state, again, config["redo_result"])
            if state["active_improve"] is not None:
                state = nav.finish_improve(state, again, {"summary": "Fake host Improve receipt"})
        nav.save(run_dir, state)
    time.sleep(config.get("linger", 120))  # a model would go on to the next packet; only the stop ends this
''')


class FakeHost:
    """The host interface of hosts.Host over the script above. ``configs`` is one config per launch (the last repeats)."""

    name, model, effort, skill = "fake", "fake-model", None, "skill-craft:shiploop"
    marketplace = False
    backend = None

    def __init__(self, folder: Path, configs: list[dict], *, resumable: bool = False, backend: str | None = None,
                 install: dict | None = None, progress: bool = False):
        self.script = Path(folder) / "fake_host.py"
        self.script.write_text(FAKE_HOST)
        self.configs, self.resumable, self.backend = configs, resumable, backend
        self.install, self.progress = install, progress  # install: what install_plugin reports (None: Claude's, loaded from argv)
        self.launches: list[dict] = []
        self.calls: list[str] = []
        self.lock_held: list[bool] = []
        self.out: Path | None = None

    def env(self, home: Path) -> dict:
        self.calls.append("env")
        self.out = Path(home).parent
        env = {**GIT_ENV, "FAKE_API_KEY": SECRET}
        if self.progress:  # ShipLoop's progress observer is left on: `next` starts a detached one, as it does for a real model
            env.pop("SHIPLOOP_PROGRESS")
        return env

    def invoke(self, skill: str, prompt: str) -> str:
        return f"/{skill} {prompt}"

    def argv(self, *, prompt, prompt_file, cwd, model, effort, permission_mode, max_turns, max_budget_usd=None,
             plugin_dir=None, resume=None) -> list[str]:
        self.lock_held.append(listeners.case_alive(self.out))
        config = self.configs[min(len(self.launches), len(self.configs) - 1)]
        self.launches.append({"resume": resume, "prompt": prompt, "model": model, "cwd": str(cwd), "plugin_dir": plugin_dir,
                              "permission_mode": permission_mode})
        return [sys.executable, str(self.script), str(SCRIPTS), json.dumps(config), prompt, resume or ""]

    def install_plugin(self, env: dict, plugin_dir: Path):
        self.calls.append("install_plugin")
        return self.install

    def plugin_cli(self, home: Path):
        return None

    def translator(self):
        return lambda raw: [raw]


def plugin_dir(folder: Path) -> Path:
    """A plugin folder whose ShipLoop is this checkout's (the way the slice tests do it): no package build."""
    plugin = Path(folder) / "plugin"
    (plugin / "skills").mkdir(parents=True)
    (plugin / "skills" / "shiploop").symlink_to(ROOT / "skills" / "shiploop")
    return plugin


def ps_field(pid: int, field: str) -> str:
    """One field of ``ps`` for ``pid`` ("" when ps lists none): the same on Linux and macOS, unlike /proc."""
    done = subprocess.run(["ps", "-o", f"{field}=", "-p", str(pid)], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=30)
    return done.stdout.strip()


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return not ps_field(pid, "stat").startswith("Z")  # a zombie is a process that ended and was not reaped; it runs nothing


class LiveCase(unittest.TestCase):
    """A temporary folder, a plugin, a short poll, and ``sample`` to run one sample in a new folder of it."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="stage-live-")
        cls.tmp = Path(cls.temp.name).resolve()
        cls.plugin = plugin_dir(cls.tmp)
        cls.poll = mock.patch.object(run, "POLL_SECONDS", POLL)
        cls.poll.start()
        cls.count = 0

    @classmethod
    def tearDownClass(cls):
        cls.poll.stop()
        cls.temp.cleanup()

    @classmethod
    def sample(cls, scenario: str, configs: list[dict], *, resumable: bool = False, cases_dir: Path | None = None,
               timeout: float | None = 120, before=None, **options) -> tuple[dict, Path, FakeHost, float]:
        """(the result, the sample folder, the fake host, the seconds it took) of one sample of ``scenario``. ``before(folder)``
        is called with the sample's folder just before it starts (a test arms a watcher with it)."""
        cls.count += 1
        box = cls.tmp / f"box{cls.count}"
        box.mkdir()
        host = FakeHost(box, configs, resumable=resumable, backend=options.pop("backend", None), install=options.pop("install", None),
                        progress=options.pop("progress", False))
        sc = sb.load(scenario, cases_dir)
        if before is not None:
            before(box / "sample" / "1")
        started = time.monotonic()
        result = live.run_sample(sc, box / "sample" / "1", host=host, plugin_dir=options.pop("plugin_dir", cls.plugin),
                                 timeout=timeout, **options)
        return result, box / "sample" / "1", host, time.monotonic() - started


def reference(scenario: str, name: str) -> str:
    return str(sb.load(scenario).dir / "reference" / name)


# ----------------------------------------------------------------------------------------------------------------- the stop

def row(action: str, stage: str = "validate-existing", outcome: str = "done") -> dict:
    return {"stage": stage, "outcome": outcome, "summary": "x", "workitem": "W1", "action": action}


class AcceptedReached(unittest.TestCase):
    def state(self, **fields) -> dict:
        return {"status": "active", "history": [row("seed-1", "test-spec")], "active_improve": None, "accepted": {}, **fields}

    def test_a_run_still_waiting_for_the_action_is_not_reached(self):
        self.assertFalse(live.accepted_reached(self.state(), "A"))

    def test_the_action_accepted_with_any_outcome_is_reached(self):
        for outcome in ("done", "send-back", "blocked", "add-work"):
            with self.subTest(outcome=outcome):
                state = self.state(history=[row("seed-1", "test-spec"), row("A", outcome=outcome)])
                self.assertTrue(live.accepted_reached(state, "A"))

    def test_a_run_parked_at_the_improve_stage_of_the_action_is_reached(self):
        state = self.state(active_improve={"action_id": "A", "stage": "step-plan", "seed_result": {"outcome": "done"}})
        self.assertTrue(live.accepted_reached(state, "A"))

    def test_another_actions_rows_and_another_actions_improve_child_are_not(self):
        state = self.state(history=[row("seed-1", "test-spec"), row("B", "implement")],
                           active_improve={"action_id": "B", "stage": "implement", "seed_result": {"outcome": "done"}})
        self.assertFalse(live.accepted_reached(state, "A"))

    def test_a_run_that_is_not_active_is_reached_whatever_its_history(self):
        for status in ("paused", "halted", "blocked", "done"):
            with self.subTest(status=status):
                self.assertTrue(live.accepted_reached(self.state(status=status), "A"))

    def test_a_state_that_could_not_be_read_is_not_a_stop(self):
        for state in (None, "", [], 3):
            with self.subTest(state=state):
                self.assertFalse(live.accepted_reached(state, "A"))

    def test_the_result_is_the_accepted_one_or_the_parked_producer_result(self):
        accepted = {"outcome": "send-back"}
        parked = {"outcome": "done", "summary": "p"}
        self.assertEqual(live.seeded_result(self.state(accepted={"A": accepted}), "A"), (accepted, "accepted"))
        child = {"action_id": "A", "stage": "step-plan", "seed_result": parked}
        self.assertEqual(live.seeded_result(self.state(active_improve=child), "A"), (parked, "parked"))
        self.assertEqual(live.seeded_result(self.state(active_improve=child), "B"), (None, None))
        self.assertEqual(live.seeded_result(None, "A"), (None, None))


# --------------------------------------------------------------------------------------------------------- a good sample

@needs_node
class GoodSample(LiveCase):
    """The fake does what the scenario asks (reference/good) and goes on sleeping for two minutes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pid_file = cls.tmp / "good.pid"
        cls.result, cls.out, cls.host, cls.seconds = cls.sample(
            BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good"), "pid_file": str(cls.pid_file)}], timeout=300)

    def test_a_fake_that_does_the_right_thing_passes_with_every_id_caught_or_held(self):
        r = self.result
        self.assertEqual(r["verdicts"], {"process": True, "accepted": True, "no_overshoot": True, "oracle": True}, r["checks"])
        self.assertEqual((r["caught"], r["held"]), ({"P1": True}, {"C1": True, "C2": True}))
        self.assertEqual((r["value"], r["pass"]), (1.0, True))
        self.assertEqual((r["outcome"], r["result_source"], r["overshoot"], r["regraded"]), ("done", "accepted", [], False))
        self.assertEqual(json.loads((self.out / "stage-result.json").read_text()), r)

    def test_the_stop_ended_the_fake_that_would_have_kept_going_long_before_the_timeout(self):
        self.assertEqual([s["status"] for s in self.result["sessions"]], ["stage-complete"])
        self.assertLess(self.seconds, 100, "the fake sleeps for 120 s and the timeout is 300 s: the poll ended it")
        self.assertFalse(pid_alive(int(self.pid_file.read_text())), "the host's process is gone")
        ended = sessionlog.read(self.out)
        self.assertEqual([(s["kind"], s["reason"], s["end"]["status"]) for s in ended], [("first", "stage", "interrupted")])

    def test_the_result_names_who_ran_what(self):
        r = self.result
        self.assertEqual((r["scenario"], r["stage"], r["sample"], r["host"], r["model"]), (BROKEN, "validate-existing", 1, "fake", "fake-model"))
        self.assertEqual(r["seeded"]["stage"], "validate-existing")
        self.assertEqual(r["action_id"], r["seeded"]["action"])
        self.assertEqual(set(r["versions"]), {"plugin_version", "shiploop_version", "plugin_sha256"})
        self.assertEqual((r["ref"], r["overlay"]), (None, None))
        self.assertEqual(self.host.launches[0]["model"], "fake-model")
        self.assertEqual(self.host.launches[0]["cwd"], str(self.out / "work"), "the host runs in the product repository")

    def test_the_sample_folder_holds_the_exports_the_packet_archive_and_the_records(self):
        for name in ("seed-export", "export", "invocation.json", "stage-result.json", "events.jsonl", "sessions.jsonl",
                     "transcript.md", "drive.json", "work", ".shiploop-runs/seed/run/state.md", ".harness-lock"):
            self.assertTrue((self.out / name).exists(), name)
        self.assertEqual(list(self.out.glob("*.partial")), [])
        action = self.result["action_id"]
        self.assertTrue(list((self.out / packets.ARCHIVE / action).glob("*.md")), "the packet the host was handed is archived")

    def test_the_seed_export_is_the_seed_and_the_export_holds_the_fix(self):
        seed = (self.out / "seed-export" / "src" / "strings.js").read_text()
        end = (self.out / "export" / "src" / "strings.js").read_text()
        self.assertIn("|| !text", seed)
        self.assertNotIn("|| !text", end)
        for tree in ("seed-export", "export"):
            names = {p.relative_to(self.out / tree).as_posix() for p in (self.out / tree).rglob("*") if p.is_file()}
            self.assertIn("src/paginate.js", names)
            self.assertIn("docs/shiploop/spec.md", names, "the knowledge home is part of the tree")
            self.assertFalse([n for n in names if n.startswith(".git/") or ".shiploop-improve" in n], tree)

    def test_the_bundle_is_rebuilt_from_the_files_alone(self):
        bundle = live.collect_bundle(sb.load(BROKEN), self.out)
        self.assertEqual(bundle.result["outcome"], "done")
        self.assertEqual((bundle.tree, bundle.seed_tree), (self.out / "export", self.out / "seed-export"))
        self.assertEqual((bundle.issued, bundle.settled), (True, False))
        self.assertEqual(bundle.current_stage, "implement", "the run moved on from the seeded stage")
        self.assertIn("E1", bundle.packet)
        self.assertIn("E1 works", bundle.packet_head)
        first = next(r for r in bundle.trace if r.get("kind") == "packet" and r.get("action") == self.result["action_id"])
        if not first.get("whole"):  # the print was cut short: the head is what was printed, not the packet file
            self.assertNotEqual(bundle.packet_head, bundle.packet)
            self.assertEqual(bundle.packet_head, (bundle.run_dir / first["head_file"]).read_text(errors="replace"))
        self.assertTrue(any(r.get("kind") == "packet" for r in bundle.trace))
        self.assertEqual(bundle.run_dir, self.out / ".shiploop-runs" / "seed" / "run")

    def test_the_grade_is_reproduced_from_the_files_also_in_a_copied_folder(self):
        """Regrades copies, never the shared folder: a regrade rewrites stage-result.json (``regraded`` true), which the tests that
        compare the folder with the first grade must not see, whatever order the tests run in."""
        before = dict(self.result)
        first = self.tmp / "regraded-good"
        shutil.copytree(self.out, first, symlinks=True)
        again = live.grade_sample(sb.load(BROKEN), first)
        for key in ("verdicts", "caught", "held", "value", "pass", "outcome", "sessions", "overshoot", "result_source", "seeded", "versions"):
            self.assertEqual(again[key], before[key], key)
        self.assertEqual([c["pass"] for c in again["checks"]], [c["pass"] for c in before["checks"]])
        self.assertTrue(again["regraded"])
        self.assertFalse(json.loads((self.out / "stage-result.json").read_text())["regraded"], "the shared folder was not regraded")
        copied = self.tmp / "copied-good"
        shutil.copytree(self.out, copied, symlinks=True)
        moved = live.grade_sample(sb.load(BROKEN), copied)
        self.assertEqual((moved["verdicts"], moved["caught"], moved["held"], moved["value"]),
                         (before["verdicts"], before["caught"], before["held"], before["value"]))
        self.assertEqual(moved["output"], str(copied))

    def test_a_tampered_export_changes_the_grade(self):
        copied = self.tmp / "tampered"
        shutil.copytree(self.out, copied, symlinks=True)
        broken = (copied / "seed-export" / "src" / "strings.js").read_text()
        (copied / "export" / "src" / "strings.js").write_text(broken)
        redone = live.grade_sample(sb.load(BROKEN), copied)
        self.assertEqual((redone["caught"], redone["pass"]), ({"P1": False}, False))
        self.assertLess(redone["value"], 1.0)
        self.assertTrue(redone["verdicts"]["accepted"], "the run is as it was: only the tree differs")
        shutil.rmtree(copied / "export")
        redone = live.grade_sample(sb.load(BROKEN), copied)
        self.assertEqual(redone["held"], {"C1": False, "C2": False}, "a missing tree fails every check that reads it")
        self.assertFalse(redone["tree"])

    def test_a_folder_of_another_scenario_or_with_no_invocation_cannot_be_graded(self):
        with self.assertRaisesRegex(live.SampleError, "not of validate-existing/wrong-check"):
            live.grade_sample(sb.load(WRONG_CHECK), self.out)
        empty = self.tmp / "empty-sample"
        empty.mkdir()
        with self.assertRaisesRegex(live.SampleError, "invocation.json"):
            live.grade_sample(sb.load(BROKEN), empty)

    def test_nothing_is_written_outside_the_sample_and_no_credential_into_it(self):
        box = self.out.parent.parent
        self.assertEqual(sorted(p.name for p in box.iterdir()), ["fake_host.py", "sample"])
        self.assertEqual([p.name for p in self.out.parent.iterdir()], ["1"])
        leaked = [str(p) for p in self.out.rglob("*") if p.is_file() and not p.is_symlink() and SECRET.encode() in p.read_bytes()]
        self.assertEqual(leaked, [])
        self.assertNotIn(SECRET, json.dumps(self.result))

    def test_the_sample_holds_its_case_lock_while_the_host_runs_and_drops_it_after(self):
        self.assertEqual(self.host.lock_held, [True])
        self.assertFalse(listeners.case_alive(self.out))

    def test_the_host_is_started_after_the_seed_export_and_the_installs(self):
        self.assertEqual(self.host.calls, ["env", "install_plugin"])
        self.assertTrue((self.out / "seed-export").is_dir())
        self.assertEqual(len(self.host.launches), 1)
        self.assertIn("/skill-craft:shiploop A ShipLoop run for the request below is already active", self.host.launches[0]["prompt"])
        self.assertIn("before validate-existing without doing them", self.host.launches[0]["prompt"])


# ----------------------------------------------------------------------------------------------- a wrong sample, the build

@needs_node
class WrongSample(LiveCase):
    """The fake reports done and leaves E1 broken (reference/bad-not-fixed). The plugin is the package build of this checkout."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.result, cls.out, cls.host, cls.seconds = cls.sample(
            BROKEN, [{"mode": "act", "reference": reference(BROKEN, "bad-not-fixed")}], plugin_dir=None, timeout=120)

    def test_a_fake_that_leaves_e1_broken_but_reports_done_fails_with_p1_not_caught(self):
        r = self.result
        self.assertEqual((r["caught"], r["held"]), ({"P1": False}, {"C1": True, "C2": True}))
        self.assertEqual(r["verdicts"], {"process": True, "accepted": True, "no_overshoot": True, "oracle": False})
        self.assertEqual((r["pass"], round(r["value"], 3)), (False, round(2 / 3, 3)))
        failed = [c for c in r["checks"] if not c["pass"]]
        self.assertTrue(failed and all(c["proves"] == "P1" for c in failed), failed)

    def test_the_default_plugin_is_a_build_of_this_checkout_and_its_identity_is_recorded(self):
        self.assertTrue((self.out / "build" / "plugins" / "skill-craft" / "skills" / "shiploop").is_dir())
        self.assertRegex(self.result["versions"]["plugin_sha256"], r"^[0-9a-f]{12}$")
        self.assertTrue(self.result["versions"]["shiploop_version"])
        self.assertEqual(self.host.launches[0]["plugin_dir"], self.out / "build" / "plugins" / "skill-craft")


# --------------------------------------------------------------------------------------------------------- other outcomes

class Outcomes(LiveCase):
    def test_a_send_back_where_the_scenario_wants_one_is_accepted_with_the_right_outcome_and_passes(self):
        result, out, _, _ = self.sample(WRONG_CHECK, [{"mode": "act", "reference": reference(WRONG_CHECK, "good")}])
        self.assertEqual((result["outcome"], result["verdicts"]["accepted"], result["verdicts"]["process"]), ("send-back", True, True))
        self.assertEqual((result["pass"], result["value"]), (True, 1.0), result["checks"])
        state = store.read_record(out / ".shiploop-runs" / "seed" / "run" / "state.md")
        self.assertEqual(nav.current_stage(state), "step-plan", "the run was sent back and the host was ended there")

    def test_a_send_back_where_the_scenario_wants_a_fix_is_accepted_with_the_wrong_outcome(self):
        result, _, _, _ = self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "bad-send-back")}])
        self.assertEqual((result["outcome"], result["verdicts"]["accepted"]), ("send-back", True))
        self.assertEqual((result["caught"], result["pass"]), ({"P1": False}, False))

    def test_a_blocked_result_ends_the_host_too(self):
        blocked = {"outcome": "blocked", "summary": "Waiting for the owner.", "awaiting": {"kind": "answer", "question": "Which format?"}}
        result, _, _, seconds = self.sample(BROKEN, [{"mode": "act", "result": blocked}], timeout=300)
        self.assertEqual((result["outcome"], result["run_status"], result["verdicts"]["process"]), ("blocked", "blocked", True),
                         result)
        self.assertLess(seconds, 100)

    @needs_node
    def test_a_host_that_accepts_two_stages_before_the_poll_looks_overshoots(self):
        good = reference(BROKEN, "good")
        result, _, _, _ = self.sample(BROKEN, [{"mode": "act", "reference": good, "extra_stages": 1}])
        self.assertEqual(result["overshoot"], ["implement"])
        self.assertEqual((result["verdicts"]["no_overshoot"], result["verdicts"]["accepted"], result["verdicts"]["process"]),
                         (False, True, True))
        self.assertEqual((result["caught"], result["pass"]), ({"P1": True}, False), "the oracle reads the seeded action only")
        self.assertEqual(result["value"], 1.0)


    def test_a_host_sent_back_that_redoes_an_earlier_stage_before_it_is_ended_overshoots(self):
        good = reference(WRONG_CHECK, "good")
        plan = {"outcome": "done", "summary": "Plan again.", "paths": ["src/**"], "test_commands": [], "follows": [],
                "test_commands_na": "No test commands.",
                "steps": [{"id": "S1", "task": "Make the planned change.", "paths": ["src/**"], "skills": [], "proof": "true"}]}
        result, _, _, _ = self.sample(WRONG_CHECK, [{"mode": "act", "reference": good, "redo_result": plan}])
        self.assertEqual(result["outcome"], "send-back")
        self.assertEqual(result["overshoot"], ["step-plan"], "step-plan is before validate-existing: only the position says so")
        self.assertFalse(result["verdicts"]["no_overshoot"])
        self.assertEqual((result["caught"], result["pass"]), ({"P1": True}, False))


class Overshoot(unittest.TestCase):
    def history(self, *rows) -> dict:
        return {"history": [row(action, stage, outcome) for action, stage, outcome in rows]}

    def test_a_later_stage_and_any_row_after_the_seeded_one_count_once_each(self):
        state = self.history(("a1", "test-spec", "done"), ("A", "validate-existing", "send-back"), ("a3", "step-plan", "done"),
                             ("a4", "test-spec", "done"), ("a5", "implement", "done"), ("a6", "implement", "done"))
        self.assertEqual(live.overshoot(state, "validate-existing", "A"), ["step-plan", "test-spec", "implement"])

    def test_nothing_after_the_seeded_row_is_no_overshoot(self):
        state = self.history(("a1", "test-spec", "done"), ("A", "validate-existing", "done"))
        self.assertEqual(live.overshoot(state, "validate-existing", "A"), [])

    def test_a_park_has_no_row_of_its_own_so_only_a_later_stage_counts(self):
        state = self.history(("a1", "test-spec", "done"), ("a2", "implement", "done"))
        self.assertEqual(live.overshoot(state, "step-plan", "A"), ["test-spec", "implement"])
        self.assertEqual(live.overshoot(None, "step-plan", "A"), [])


class PacketHead(unittest.TestCase):
    """The head is what `shiploop next` printed: the kept head when the print was cut short, else the packet text."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="stage-live-head-")
        self.addCleanup(temp.cleanup)
        self.run_dir = Path(temp.name).resolve() / "run"
        (self.run_dir / "packets" / "sent").mkdir(parents=True)
        (self.run_dir / "packets" / "sent" / "full.md").write_text("THE WHOLE PACKET")
        (self.run_dir / "packets" / "sent" / "head.md").write_text("THE PRINTED HEAD")
        (Path(temp.name) / "outside.md").write_text("OUTSIDE")

    def packet(self, **fields) -> dict:
        return {"kind": "packet", "action": "A", "whole": False, "file": "packets/sent/full.md", **fields}

    def test_a_cut_print_reads_the_head_file(self):
        trace = [self.packet(head_file="packets/sent/head.md")]
        self.assertEqual(live._first_head(self.run_dir, trace, "A"), "THE PRINTED HEAD")

    def test_a_whole_print_reads_the_packet_text(self):
        self.assertEqual(live._first_head(self.run_dir, [self.packet(whole=True, head_file=None)], "A"), "THE WHOLE PACKET")

    def test_the_first_print_of_the_action_wins_and_another_actions_rows_do_not_count(self):
        trace = [self.packet(action="B"), self.packet(head_file="packets/sent/head.md"), self.packet(whole=True)]
        self.assertEqual(live._first_head(self.run_dir, trace, "A"), "THE PRINTED HEAD")
        self.assertIsNone(live._first_head(self.run_dir, trace, "C"))
        self.assertIsNone(live._first_head(self.run_dir, None, "A"))

    def test_a_path_that_leaves_the_run_directory_is_not_read(self):
        self.assertIsNone(live._first_head(self.run_dir, [self.packet(file="../outside.md")], "A"))


# ----------------------------------------------------------------------------------------------------------------- the settle

class RunLockProbe(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="stage-live-lock-")
        self.addCleanup(temp.cleanup)
        self.run_dir = Path(temp.name).resolve()
        self.out = self.run_dir / "out"
        self.out.mkdir()

    def hold(self) -> int:
        descriptor = os.open(str(self.run_dir / ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        self.addCleanup(lambda: os.close(descriptor) if descriptor else None)
        return descriptor

    def test_no_lock_file_or_a_lock_nobody_holds_is_free_and_the_probe_creates_nothing(self):
        self.assertTrue(live.run_lock_free(self.run_dir))
        self.assertFalse((self.run_dir / ".lock").exists())
        (self.run_dir / ".lock").write_text("")
        self.assertTrue(live.run_lock_free(self.run_dir))
        self.assertTrue(live.run_lock_free(self.run_dir), "the probe let go of what it took")

    def test_a_held_lock_is_not_free_until_it_is_released(self):
        descriptor = self.hold()
        self.assertFalse(live.run_lock_free(self.run_dir))
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        self.assertTrue(live.run_lock_free(self.run_dir))

    def test_settle_returns_when_the_lock_is_let_go_and_says_how_long_it_waited(self):
        descriptor = self.hold()
        threading.Timer(1.0, lambda: fcntl.flock(descriptor, fcntl.LOCK_UN)).start()
        got = live.settle(self.run_dir, self.out)
        self.assertTrue(got["settled"])
        self.assertGreaterEqual(got["waited"], 0.8)

    def test_settle_gives_up_after_its_limit_and_says_why(self):
        self.hold()
        got = live.settle(self.run_dir, self.out, seconds=0.5)
        self.assertEqual((got["settled"], got["why"] is not None and "still held the run lock" in got["why"]), (False, True))

    def test_settle_does_not_wait_for_a_run_an_operator_is_ending(self):
        self.hold()
        (self.out / "stop").write_text("")
        started = time.monotonic()
        got = live.settle(self.run_dir, self.out, seconds=60)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual((got["settled"], got["why"]), (False, "the run was stopped"))

    def test_settle_says_stopped_with_the_lock_free_too_when_the_stop_file_is_there(self):
        """A SIGTERM's handler kills the host, which lets the lock go: the wait may read as settled although the effects are not
        known to be whole, so the guard looks before the lock does (and not only while the lock is held)."""
        self.assertTrue(live.run_lock_free(self.run_dir))
        (self.out / "stop").write_text("")
        got = live.settle(self.run_dir, self.out, seconds=60)
        self.assertEqual((got["settled"], got["why"]), (False, "the run was stopped"))

    def test_settle_says_stopped_with_the_lock_free_too_when_the_harness_was_terminated(self):
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        self.assertTrue(live.run_lock_free(self.run_dir))
        run.TERMINATION.set()
        got = live.settle(self.run_dir, self.out, seconds=60)
        self.assertEqual((got["settled"], got["why"]), (False, "the run was stopped"))
        self.assertTrue(live.told_to_end(self.out))


@needs_node
class Settle(LiveCase):
    def test_the_stop_waits_for_the_accepting_command_so_the_export_holds_its_effects(self):
        """The fake saves the state, and its knowledge close (3 s, under the run lock) writes docs/shiploop/EFFECT.md after the
        save. The poll sees the action accepted at once; the host is ended only after the effect is there."""
        result, out, _, seconds = self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good"), "effects_delay": 3}],
                                              timeout=300)
        worktree = out / ".shiploop-runs" / "seed" / "worktree"
        self.assertTrue((worktree / "docs" / "shiploop" / "EFFECT.md").is_file())
        self.assertTrue((out / "export" / "docs" / "shiploop" / "EFFECT.md").is_file(), "the effect is in the stage's output tree")
        self.assertEqual([s["status"] for s in result["sessions"]], ["stage-complete"])
        self.assertEqual(len(result["settles"]), 1)
        self.assertTrue(result["settles"][0]["settled"], result["settles"])
        self.assertGreaterEqual(result["settles"][0]["waited"], 1.0, "the stop waited for the command")
        self.assertEqual((result["verdicts"]["no_overshoot"], result["pass"]), (True, True), result["checks"])
        self.assertLess(seconds, 100)

    def test_a_command_that_holds_the_lock_longer_than_the_limit_is_waited_for_no_longer_and_the_sample_says_so(self):
        with mock.patch.object(live, "SETTLE_SECONDS", 1):
            result, out, _, _ = self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good"), "effects_delay": 6}],
                                            timeout=300)
        self.assertFalse(result["settles"][0]["settled"])
        self.assertIn("still held the run lock", result["settles"][0]["why"])
        self.assertEqual([s["status"] for s in result["sessions"]], ["stage-complete"])
        self.assertEqual(json.loads((out / "drive.json").read_text())["settles"], result["settles"])


# ---------------------------------------------------------------------------------------------------------- an operator's stop

@needs_node
class Stopped(LiveCase):
    def run_stopped(self, config: dict) -> tuple[Path, FakeHost]:
        type(self).count += 1
        box = self.tmp / f"stopped{self.count}"
        box.mkdir()
        host = FakeHost(box, [config])
        with self.assertRaisesRegex(live.SampleStopped, r"ended before it accepted the seeded action: stopped by .*/stop"):
            live.run_sample(sb.load(BROKEN), box / "sample" / "1", host=host, plugin_dir=self.plugin, timeout=120)
        return box / "sample" / "1", host

    def test_a_sample_the_operator_ends_is_not_graded_and_counts_as_not_run(self):
        out, host = self.run_stopped({"mode": "wait", "stop_file": True})
        self.assertFalse((out / "stage-result.json").exists(), "nothing was measured")
        self.assertIn("SampleStopped", (out / "error.txt").read_text())
        self.assertFalse((out / "stop").exists(), "the stop file is consumed")
        self.assertEqual(sessionlog.read(out)[-1]["end"]["status"], "stopped")
        read = stage_report.read_sample(out)
        self.assertFalse(read["graded"])
        self.assertIn("SampleStopped", read["reason"])
        self.assertEqual(len(host.launches), 1, "a stopped host is not resumed")

    def test_such_a_folder_cannot_be_graded_later(self):
        out, _ = self.run_stopped({"mode": "wait", "stop_file": True})
        with self.assertRaisesRegex(live.SampleError, "was not run to the end.*SampleStopped.*nothing to grade"):
            live.grade_sample(sb.load(BROKEN), out)
        self.assertFalse((out / "stage-result.json").exists())

    def test_a_folder_that_has_an_export_is_graded_whatever_error_txt_says(self):
        result, out, _, _ = self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good")}])
        (out / "error.txt").write_text("a stale note\n")
        (out / "stage-result.json").unlink()
        self.assertTrue(live.grade_sample(sb.load(BROKEN), out)["pass"])


@needs_node
class StoppedWhileSettling(LiveCase):
    """The poll saw the seeded action accepted, and the stop is waiting for the accepting command's run lock (the fake's slow
    knowledge close, 8 s, under the lock) when the operator ends the run: a SIGTERM to the harness (what its handler does:
    run.terminate) or the stop file. Nothing was finished, so the half-done tree is not exported and not graded: the sample is
    "not run" (SampleStopped), as one stopped at any other moment."""
    DELAY = 8

    def stopped_during_the_wait(self, act) -> tuple[Path, float]:
        """Run a sample whose stop is waiting for the lock, call ``act(folder)`` from a watcher 0.5 s after the wait began, and
        return the folder and the seconds the sample took; the sample must raise SampleStopped."""
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        entered, folder = threading.Event(), {}
        real = live.settle

        def settle(*args, **kwargs):
            entered.set()
            return real(*args, **kwargs)

        def before(out: Path) -> None:
            folder["out"] = out

            def watch() -> None:
                if entered.wait(120):
                    time.sleep(0.5)
                    act(out)

            threading.Thread(target=watch, daemon=True, name="stage-live-test-watch").start()

        started = time.monotonic()
        with mock.patch.object(live, "settle", settle), self.assertRaises(live.SampleStopped) as caught:
            self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good"), "effects_delay": self.DELAY}], timeout=300,
                        before=before)
        self.assertTrue(entered.is_set(), "the operator ended the run while the stop was waiting for the lock")
        self.caught = str(caught.exception)
        return folder["out"], time.monotonic() - started

    def assertNotRun(self, out: Path, seconds: float, why: str) -> None:
        self.assertIn(why, self.caught)
        self.assertFalse((out / "stage-result.json").exists(), "nothing was measured, so nothing is graded")
        self.assertFalse((out / "export").exists(), "the half-finished tree is not exported")
        self.assertIn("SampleStopped", (out / "error.txt").read_text())
        self.assertEqual(sessionlog.read(out)[-1]["end"]["status"], "stopped")
        self.assertLess(seconds, self.DELAY + 30)
        read = stage_report.read_sample(out)
        self.assertFalse(read["graded"])
        self.assertIn("SampleStopped", read["reason"])

    def test_a_sigterm_while_the_stop_waits_for_the_accepting_command_leaves_the_sample_not_run(self):
        out, seconds = self.stopped_during_the_wait(lambda folder: run.terminate("SIGTERM"))
        self.assertNotRun(out, seconds, "terminated by SIGTERM")
        self.assertFalse([row for row in json.loads((out / "drive.json").read_text())["settles"] if row["settled"]])

    def test_the_stop_file_while_the_stop_waits_for_the_accepting_command_leaves_the_sample_not_run(self):
        out, seconds = self.stopped_during_the_wait(lambda folder: (folder / "stop").write_text("stop\n"))
        self.assertNotRun(out, seconds, "stopped by")
        self.assertFalse((out / "stop").exists(), "the stop file is consumed")
        self.assertFalse((out / "work" / "docs" / "shiploop" / "EFFECT.md").exists())

    def test_a_stop_that_lands_after_the_wait_read_as_settled_is_not_a_stop_at_acceptance_either(self):
        """The wait came back settled (the lock was let go), and the operator's SIGTERM arrives before the stop is declared:
        ``stop_when`` checks again, says no, and run.launch reports "stopped". Without that second look the half-known tree
        would be exported and graded."""
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        real = live.settle
        answers: list = []

        def settle(*args, **kwargs):
            got = real(*args, **kwargs)
            answers.append(got)
            run.TERMINATED_BY.append("SIGTERM")
            run.TERMINATION.set()  # after the wait, not during it
            return got

        with mock.patch.object(live, "settle", settle), self.assertRaises(live.SampleStopped) as caught:
            self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good")}], timeout=300)
        self.assertTrue(answers and answers[0]["settled"], "the wait itself read as settled")
        self.assertIn("terminated by SIGTERM", str(caught.exception))


class Unfinished(LiveCase):
    """grade_sample refuses a folder that was not run to the end, not only one with an error.txt: a sample that is still running,
    or whose harness was killed (SIGKILL leaves no error.txt), has no export, no export-error.txt and no result."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.result, cls.out, cls.host, _ = cls.sample(BROKEN, [{"mode": "exit"}])  # graded, with an export; the host does nothing

    def copy(self, name: str) -> Path:
        copied = self.tmp / name
        shutil.copytree(self.out, copied, symlinks=True)
        return copied

    @needs_node
    def test_a_folder_with_no_export_no_export_error_and_no_result_is_refused_as_not_finished(self):
        copied = self.copy("unfinished")
        shutil.rmtree(copied / "export")
        (copied / "stage-result.json").unlink()
        self.assertFalse((copied / "error.txt").exists())
        with self.assertRaisesRegex(live.SampleError, "has no export, no export-error.txt and no stage-result.json.*still running.*killed"):
            live.grade_sample(sb.load(BROKEN), copied)
        self.assertFalse((copied / "stage-result.json").exists(), "a refused grade writes nothing")

    @needs_node
    def test_a_folder_whose_export_failed_is_graded_and_its_tree_is_missing(self):
        copied = self.copy("export-failed")
        shutil.rmtree(copied / "export")
        (copied / "stage-result.json").unlink()
        (copied / "export-error.txt").write_text("git ls-files failed\n")
        graded = live.grade_sample(sb.load(BROKEN), copied)
        self.assertEqual((graded["tree"], graded["pass"]), (False, False))

    @needs_node
    def test_a_folder_whose_harness_lock_is_held_is_refused_until_it_is_let_go(self):
        copied = self.copy("running")
        handle = listeners.hold_case(copied)
        self.assertIsNotNone(handle, "the test holds the sample's harness lock, as a running sample does")
        try:
            with self.assertRaisesRegex(live.SampleError, "harness.*still running"):
                live.grade_sample(sb.load(BROKEN), copied)
        finally:
            handle.close()
        self.assertIn("verdicts", live.grade_sample(sb.load(BROKEN), copied))


# --------------------------------------------------------------------------------------------- a process the host leaves behind

@needs_node
class Escapee(LiveCase):
    """The host leaves a process in a session of its own that holds the host's output open: the group kill cannot reach it, and
    run.launch waits for the output to close. The drive abandons the launch (the watchdog) so the sample still ends and is graded."""

    def setUp(self):
        patches = [mock.patch.object(live, "WATCHDOG_SECONDS", 2), mock.patch.object(live, "STOP_GRACE_SECONDS", 2)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        type(self).count += 1
        self.pid_file = self.tmp / f"escapee{self.count}.pid"

    def release(self) -> None:
        """Kill the escapee and let the abandoned launch thread finish before the temporary folder goes."""
        if self.pid_file.exists():
            try:
                os.kill(int(self.pid_file.read_text()), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass
        for thread in threading.enumerate():
            if thread.name == "stage-live-launch":
                thread.join(20)

    def test_the_stop_is_not_held_up_for_two_minutes_by_a_process_outside_the_hosts_group(self):
        self.addCleanup(self.release)
        result, out, _, seconds = self.sample(
            BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good"), "escapee": str(self.pid_file)}], timeout=300)
        self.assertLess(seconds, 60, "the escapee sleeps for 120 s")
        self.assertTrue(pid_alive(int(self.pid_file.read_text())), "it is in no group of ours and is left alone")
        self.assertEqual([s["status"] for s in result["sessions"]], ["stage-complete"])
        self.assertTrue(result["abandoned"])
        self.assertEqual((result["verdicts"]["process"], result["pass"]), (True, True), result["checks"])

    def test_the_timeout_is_a_bound_on_the_sample_even_then(self):
        self.addCleanup(self.release)
        result, _, _, seconds = self.sample(
            BROKEN, [{"mode": "wait", "escapee": str(self.pid_file), "linger": 120,
                      "escapee_before_next": True, "before_next_delay": 8}], timeout=3)
        self.assertLess(seconds, 60)
        self.assertTrue(self.pid_file.exists(), "the escaped pipe holder must exist before the host times out")
        self.assertTrue(pid_alive(int(self.pid_file.read_text())))
        self.assertEqual([s["status"] for s in result["sessions"]], ["timeout"])
        self.assertTrue(result["abandoned"])
        self.assertEqual((result["verdicts"]["process"], result["verdicts"]["accepted"], result["pass"]), (False, False, False))

    def stopped_with_an_escapee(self, config: dict, act=None) -> tuple[Path, float, str]:
        """A sample (timeout 30 s, grace 2 s) whose host leaves an escapee, ended by the operator: the stop file the fake writes
        (``config`` has ``stop_file``) or ``act(folder)`` 1.5 s after the escapee exists. Returns the folder, the seconds the
        sample took and the SampleStopped message."""
        self.addCleanup(self.release)
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)

        def before(out: Path) -> None:
            def watch() -> None:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline and not (self.pid_file.exists() and self.pid_file.read_text()):
                    time.sleep(0.1)
                time.sleep(1.5)
                act(out)

            if act is not None:
                threading.Thread(target=watch, daemon=True, name="stage-live-test-watch").start()

        started = time.monotonic()
        with self.assertRaises(live.SampleStopped) as caught:
            self.sample(BROKEN, [{"mode": "wait", "escapee": str(self.pid_file), "linger": 120, **config}], timeout=30, before=before)
        out = self.tmp / f"box{self.count}" / "sample" / "1"
        return out, time.monotonic() - started, str(caught.exception)

    def test_the_stop_file_bounds_the_sample_by_the_stop_grace_and_not_by_the_timeout(self):
        out, seconds, why = self.stopped_with_an_escapee({"stop_file": True})
        self.assertLess(seconds, 20, "the timeout is 30 s and the grace 2 s: the stop file started the grace clock")
        self.assertIn("stopped by", why)
        self.assertTrue(json.loads((out / "drive.json").read_text())["abandoned"])
        self.assertFalse((out / "stage-result.json").exists())
        self.assertFalse((out / "stop").exists())

    def test_a_sigterm_bounds_the_sample_by_the_stop_grace_and_not_by_the_timeout(self):
        out, seconds, why = self.stopped_with_an_escapee({}, act=lambda folder: run.terminate("SIGTERM"))
        self.assertLess(seconds, 20, "the timeout is 30 s and the grace 2 s: the signal started the grace clock")
        self.assertIn("terminated by SIGTERM", why)
        self.assertTrue(json.loads((out / "drive.json").read_text())["abandoned"])
        self.assertEqual(sessionlog.read(out)[-1]["end"]["status"], "stopped")
        self.assertFalse((out / "stage-result.json").exists())


class Watchdog(unittest.TestCase):
    def test_the_watchdog_outlasts_the_wait_for_the_accepting_command(self):
        """The stop waits for the lock inside the poll, after the deadline may have passed (launch cannot look at the clock
        meanwhile); a watchdog shorter than that wait would abandon a sample that is settling and call it a timeout."""
        self.assertGreater(live.WATCHDOG_SECONDS, live.SETTLE_SECONDS)
        self.assertGreater(live.STOP_GRACE_SECONDS, 0)

    def test_the_parents_hard_limit_leaves_the_sample_its_watchdog_and_the_build(self):
        import stages
        self.assertGreater(stages.SAMPLE_GRACE_SECONDS, live.WATCHDOG_SECONDS + live.SETTLE_SECONDS)


@needs_node
class EndedOnTheNormalPath(LiveCase):
    """run.py ends what the run's ledger records and the detached progress observer before it exports and grades; so does the
    sample, on the path where nothing went wrong, with ShipLoop's progress left on."""

    def test_a_detached_progress_observer_and_the_recorded_hosts_are_ended_before_the_export(self):
        seen: dict = {}
        real = live.snapshot

        def spy(worktree, target):
            if Path(target).name == live.EXPORT:
                record = Path(target).parent / ".shiploop-runs" / "seed" / "run" / "progress-observer.json"
                seen["pid"] = json.loads(record.read_text())["pid"] if record.is_file() else None
                seen["alive"] = bool(seen["pid"]) and pid_alive(seen["pid"])
                seen["open"] = lifecycle.open_groups(Path(target).parent)
            return real(worktree, target)

        with mock.patch.object(live, "snapshot", spy):
            result, out, _, _ = self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good")}], progress=True)
        record = out / ".shiploop-runs" / "seed" / "run" / "progress-observer.json"
        self.assertTrue(record.is_file(), "the fake host's `next` started ShipLoop's observer (progress is on)")
        pid = json.loads(record.read_text())["pid"]
        self.addCleanup(lambda: pid_alive(pid) and os.kill(pid, signal.SIGKILL))
        self.assertEqual(seen["pid"], pid)
        self.assertFalse(seen["alive"], "the observer was ended before the tree was exported")
        self.assertEqual(seen["open"], [], "every group the ledger holds was ended before the export")
        self.assertFalse(pid_alive(pid), "and it is still gone")
        self.assertEqual(lifecycle.open_groups(out), [])
        roles = {row.get("role") for row in lifecycle.rows(out) if row.get("kind") == "ended"}
        self.assertEqual(roles, {"host", "observer"})
        self.assertTrue(result["pass"], result["checks"])

    def test_the_ledger_is_swept_when_the_sample_ends_in_an_error_too(self):
        """The cleanup is in a finally: a stop that raises (SampleStopped) leaves no recorded group alive either."""
        seen: dict = {}
        real = lifecycle.cleanup

        def spy(folder):
            seen.setdefault("folders", []).append(Path(folder))
            return real(folder)

        with mock.patch.object(lifecycle, "cleanup", spy), mock.patch.object(live.run, "write_transcript", side_effect=RuntimeError("boom")):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                self.sample(BROKEN, [{"mode": "act", "reference": reference(BROKEN, "good")}], progress=True)
        self.assertEqual(len(seen.get("folders", [])), 1, "the cleanup ran once, on the way out")
        out = seen["folders"][0]
        pid = json.loads((out / ".shiploop-runs" / "seed" / "run" / "progress-observer.json").read_text())["pid"]
        self.addCleanup(lambda: pid_alive(pid) and os.kill(pid, signal.SIGKILL))
        self.assertFalse(pid_alive(pid))


class ImprovePark(LiveCase):
    """A scenario at step-plan, a stage with an Improve review: the host's result parks the run, and that ends the host."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = cls.tmp / "cases"
        folder = cls.cases / "step-plan" / "park"
        folder.mkdir(parents=True)
        (folder / "scenario.json").write_text(json.dumps({
            "stage": "step-plan", "about": "A step plan whose Improve review follows.", "tiers": ["render", "live"],
            "fixture": "node-base", "request_from": "node-fix-bug",
            "planted": [{"id": "P1", "what": "the producer's result is done", "signature": "x"}],
            "controls": [{"id": "C1", "what": "nothing but the knowledge home changes"}],
            "oracle": [{"proves": "P1", "outcome": ["done"]}, {"proves": "C1", "changed_only": ["docs/shiploop/**"]}]}))
        plan = {"outcome": "done", "summary": "Plan.", "paths": ["src/**"], "test_commands": [], "follows": [],
                "test_commands_na": "No test commands.",
                "steps": [{"id": "S1", "task": "Make the planned change.", "paths": ["src/**"], "skills": [], "proof": "true"}]}
        cls.result, cls.out, cls.host, cls.seconds = cls.sample(
            "step-plan/park", [{"mode": "act", "result": plan}], cases_dir=cls.cases, timeout=300)

    def test_the_run_parks_at_the_improve_stage_and_that_ends_the_host(self):
        r = self.result
        state = store.read_record(self.out / ".shiploop-runs" / "seed" / "run" / "state.md")
        self.assertEqual(state["active_improve"]["action_id"], r["action_id"])
        self.assertNotIn(r["action_id"], state["accepted"], "parked, not accepted")
        self.assertTrue(live.accepted_reached(state, r["action_id"]))
        self.assertEqual([s["status"] for s in r["sessions"]], ["stage-complete"])
        self.assertLess(self.seconds, 100)

    def test_the_parked_producer_result_is_the_samples_result(self):
        r = self.result
        self.assertEqual((r["result_source"], r["outcome"], r["verdicts"]["accepted"]), ("parked", "done", True))
        self.assertEqual((r["caught"], r["held"], r["pass"]), ({"P1": True}, {"C1": True}, True), r["checks"])


# ---------------------------------------------------------------------------------------------------------------- sessions

@needs_node
class Sessions(LiveCase):
    def test_a_host_that_exits_at_once_without_acting_is_recorded_and_nothing_crashes(self):
        result, out, host, _ = self.sample(BROKEN, [{"mode": "exit"}])
        self.assertEqual([s["status"] for s in result["sessions"]], ["exited"])
        self.assertEqual(result["verdicts"], {"process": False, "accepted": False, "no_overshoot": True, "oracle": False})
        self.assertEqual((result["pass"], result["value"], result["outcome"], result["result_source"]), (False, 0.0, None, None))
        self.assertEqual((result["caught"], result["held"]), ({"P1": False}, {"C1": False, "C2": False}),
                         "a host that delivered nothing holds no control by doing nothing")
        self.assertEqual(result["resume_stop"], "the host cannot be resumed")
        self.assertEqual(len(host.launches), 1)
        self.assertTrue((out / "export").is_dir() and (out / "stage-result.json").is_file())

    def test_an_install_the_host_reports_as_passed_starts_the_host(self):
        result, _, host, _ = self.sample(BROKEN, [{"mode": "exit"}], install={"pass": True, "loaded": ["skill-craft"]})
        self.assertEqual((len(host.launches), host.calls), (1, ["env", "install_plugin"]))
        self.assertEqual(result["plugin"], {"pass": True, "loaded": ["skill-craft"]})

    def test_a_resumable_host_that_ends_before_acceptance_is_resumed_and_the_sample_completes(self):
        configs = [{"mode": "act-when-resumed", "session": "fake-session-1", "reference": reference(BROKEN, "good")}]
        result, out, host, _ = self.sample(BROKEN, configs, resumable=True, timeout=300)
        self.assertEqual([s["status"] for s in result["sessions"]], ["exited", "stage-complete"])
        self.assertEqual([s["kind"] for s in result["sessions"]], ["first", "continued"])
        self.assertEqual([launch["resume"] for launch in host.launches], [None, "fake-session-1"])
        self.assertIn("This session ended while the ShipLoop run was still active", host.launches[1]["prompt"])
        self.assertEqual((result["resumes"], result["resume_stop"], result["pass"]), (1, None, True))
        self.assertEqual([s["resumed_session"] for s in sessionlog.read(out)], [None, "fake-session-1"])

    def test_a_resumable_host_that_never_moves_the_run_is_resumed_no_more_than_the_stall_limit(self):
        result, _, host, _ = self.sample(BROKEN, [{"mode": "exit", "session": "s"}], resumable=True, timeout=600)
        self.assertEqual((result["resumes"], len(host.launches)), (run.RESUME_STALL, 1 + run.RESUME_STALL))
        self.assertRegex(result["resume_stop"], rf"{run.RESUME_STALL} resumed sessions in a row moved ShipLoop nowhere")
        self.assertFalse(result["verdicts"]["accepted"])

    def test_a_resume_needs_more_of_the_timeout_than_the_minimum(self):
        result, _, host, _ = self.sample(BROKEN, [{"mode": "exit", "session": "s"}], resumable=True, timeout=30)
        self.assertEqual((len(host.launches), result["resume_stop"]), (1, "the timeout is spent"))

    def test_a_host_that_ends_with_the_run_no_longer_active_is_not_resumed(self):
        blocked = {"outcome": "blocked", "summary": "Waiting for the owner.", "awaiting": {"kind": "answer", "question": "Which format?"}}
        result, _, host, _ = self.sample(BROKEN, [{"mode": "act", "result": blocked, "linger": 0}], resumable=True, timeout=300)
        self.assertEqual(len(host.launches), 1)
        self.assertEqual([s["status"] for s in result["sessions"]], ["stage-complete"], "it ended by itself with the action accepted")
        self.assertTrue(result["verdicts"]["process"])


# ---------------------------------------------------------------------------------------------------------------- snapshot

GIT_SECONDS = 60  # a local git command


def git(folder: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], check=True,
                   capture_output=True, env=GIT_ENV, stdin=subprocess.DEVNULL, timeout=GIT_SECONDS)


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="stage-live-snap-")
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name).resolve()
        self.tree = self.tmp / "tree"
        (self.tree / "src").mkdir(parents=True)
        (self.tree / "src" / "a.js").write_text("a\n")
        (self.tree / "src" / "gone.js").write_text("gone\n")
        (self.tree / "run.sh").write_text("#!/bin/sh\n")
        (self.tree / "run.sh").chmod(0o755)
        (self.tree / ".gitignore").write_text("node_modules/\n")
        git(self.tree, "init", "-q")
        git(self.tree, "add", "-A")
        git(self.tree, "commit", "-qm", "base")

    def names(self, folder: Path) -> set[str]:
        return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() or p.is_symlink()}

    def test_tracked_and_untracked_files_that_git_does_not_ignore_are_exported_and_nothing_else(self):
        (self.tree / "src" / "new.js").write_text("new\n")
        (self.tree / "node_modules").mkdir()
        (self.tree / "node_modules" / "x.js").write_text("ignored\n")
        (self.tree / ".shiploop-improve").mkdir()
        (self.tree / ".shiploop-improve" / "evidence.md").write_text("evidence\n")
        (self.tree / "src" / "__pycache__").mkdir()
        (self.tree / "src" / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\0")
        (self.tree / "src" / "gone.js").unlink()
        (self.tree / "src" / "a.js").write_text("changed\n")
        counts = live.snapshot(self.tree, self.tmp / "export")
        self.assertEqual(self.names(self.tmp / "export"), {".gitignore", "run.sh", "src/a.js", "src/new.js"})
        self.assertEqual((self.tmp / "export" / "src" / "a.js").read_text(), "changed\n")
        self.assertTrue(os.access(self.tmp / "export" / "run.sh", os.X_OK), "the executable bit is kept")
        self.assertEqual((counts["files"], counts["links"], counts["skipped"]), (4, 0, []))
        self.assertFalse((self.tmp / "export" / ".git").exists())
        self.assertFalse((self.tmp / "export.partial").exists())

    def test_shiploops_run_folders_are_left_out_and_a_stale_partial_export_is_cleared(self):
        (self.tree / ".shiploop-runs" / "seed" / "run").mkdir(parents=True)
        (self.tree / ".shiploop-runs" / "seed" / "run" / "state.md").write_text("state\n")
        stale = self.tmp / "export.partial"
        stale.mkdir()
        (stale / "left-by-a-killed-export.txt").write_text("stale\n")
        live.snapshot(self.tree, self.tmp / "export")
        self.assertEqual(self.names(self.tmp / "export"), {".gitignore", "run.sh", "src/a.js", "src/gone.js"})
        self.assertFalse(stale.exists(), "the leftover of an earlier killed export is gone")

    def test_a_symlink_is_copied_as_a_link_and_never_followed(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret\n")
        (self.tree / "leak").symlink_to(outside / "secret.txt")
        (self.tree / "dirleak").symlink_to(outside)
        live.snapshot(self.tree, self.tmp / "export")
        export = self.tmp / "export"
        self.assertEqual(os.readlink(export / "leak"), str(outside / "secret.txt"))
        self.assertTrue((export / "dirleak").is_symlink())
        self.assertNotIn("secret.txt", {p.name for p in export.rglob("*") if p.is_file() and not p.is_symlink()})
        self.assertEqual(list(outside.iterdir()), [outside / "secret.txt"], "nothing was written through a link")

    def test_a_tracked_file_below_a_folder_that_became_a_link_is_left_out_and_never_read_through_it(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "a.js").write_text("OUTSIDE\n")
        shutil.rmtree(self.tree / "src")
        (self.tree / "src").symlink_to(outside)
        counts = live.snapshot(self.tree, self.tmp / "export")
        export = self.tmp / "export"
        self.assertTrue((export / "src").is_symlink())
        self.assertNotIn("OUTSIDE", "".join(p.read_text() for p in export.rglob("*") if p.is_file() and not p.is_symlink()))
        self.assertIn("src/a.js", counts["skipped"])

    def test_a_worktree_git_cannot_read_is_an_error_and_no_export_is_left(self):
        shutil.rmtree(self.tree / ".git")
        with self.assertRaises(live.SnapshotError):
            live.snapshot(self.tree, self.tmp / "export")
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["tree"])
        with self.assertRaises(live.SnapshotError):
            live.snapshot(self.tmp / "missing", self.tmp / "export")

    def test_an_export_is_written_once(self):
        live.snapshot(self.tree, self.tmp / "export")
        with self.assertRaises(FileExistsError):
            live.snapshot(self.tree, self.tmp / "export")


# ---------------------------------------------------------------------------------------------------------------- refusals

class Refusals(LiveCase):
    def refused(self, pattern: str, scenario: str = BROKEN, configs: list[dict] | None = None, installed: bool = False,
                **options) -> FakeHost:
        box = self.tmp / f"refused{len(list(self.tmp.glob('refused*')))}"
        box.mkdir()
        host = FakeHost(box, configs or [{"mode": "exit"}], backend=options.pop("backend", None), install=options.pop("install", None))
        options.setdefault("plugin_dir", self.plugin)
        with self.assertRaisesRegex(SystemExit, pattern):
            cases = options.pop("cases_dir", None)
            live.run_sample(sb.load(scenario, cases), box / "sample" / "1", host=host, timeout=60, **options)
        self.assertEqual(host.launches, [], "no host was started")
        self.assertEqual("install_plugin" in host.calls, installed)
        return host

    def old_commit(self) -> str | None:
        done = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H", "-n", "40", "--", "skills/shiploop/scripts/shiploop_navigator.py"],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=GIT_SECONDS)
        for commit in done.stdout.split():
            text = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:skills/shiploop/scripts/shiploop_navigator.py"],
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=GIT_SECONDS).stdout
            if text and "def accept_effects" not in text:
                return commit
        return None

    def test_a_ref_whose_navigator_has_no_accept_effects_is_refused_before_anything_is_built_or_launched(self):
        commit = self.old_commit()
        if commit is None:
            self.skipTest("this clone holds no commit from before the seed seam")
        host = self.refused(r"has no accept_effects in its navigator.*docs/plans/shiploop-stage-suite.md.*Nothing was started",
                            ref=commit, plugin_dir=None)
        self.assertEqual(host.calls, [], "not even the host's environment was made")
        self.assertEqual([p.name for p in host.script.parent.iterdir()], ["fake_host.py"], "no sample folder and no build")

    def scratch_repo(self, navigator: str | None) -> Path:
        """A git repository of its own with one commit whose ShipLoop navigator is ``navigator`` (no navigator file for None), so
        the refusal of a ref without the seam is proven whatever the depth of this clone."""
        folder = self.tmp / f"scratch-repo{len(list(self.tmp.glob('scratch-repo*')))}"
        scripts = folder / live.SCRIPTS
        scripts.mkdir(parents=True)
        (scripts / "other.py").write_text("x = 1\n")
        if navigator is not None:
            (scripts / "shiploop_navigator.py").write_text(navigator)
        git(folder, "init", "-q")
        git(folder, "add", "-A")
        git(folder, "commit", "-qm", "scratch")
        return folder

    def test_a_ref_without_the_seam_is_refused_in_a_repository_of_its_own_whatever_the_clone_depth(self):
        with mock.patch.object(live.overlays, "ROOT", self.scratch_repo("def other():\n    pass\n")):
            gap = live.ref_seam_gap("HEAD")
        self.assertRegex(gap, r"has no accept_effects in its navigator.*docs/plans/shiploop-stage-suite.md")
        with mock.patch.object(live.overlays, "ROOT", self.scratch_repo("def accept_effects(core, root):\n    pass\n")):
            self.assertEqual(live.ref_seam_gap("HEAD"), "")
        with mock.patch.object(live.overlays, "ROOT", self.scratch_repo("def broken(:\n")):
            self.assertIn("does not parse", live.ref_seam_gap("HEAD"))
        with mock.patch.object(live.overlays, "ROOT", self.scratch_repo(None)):
            self.assertIn("has no skills/shiploop/scripts/shiploop_navigator.py", live.ref_seam_gap("HEAD"))

    def test_a_git_that_cannot_answer_in_time_is_a_gap_and_not_a_hang(self):
        real = subprocess.run

        def slow(argv, *args, **kwargs):
            if argv[:1] == ["git"] and "show" in argv:
                self.assertEqual(kwargs.get("stdin"), subprocess.DEVNULL)
                self.assertTrue(kwargs.get("timeout"), "git show has a timeout")
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return real(argv, *args, **kwargs)

        with mock.patch.object(live.subprocess, "run", slow):
            self.assertIn("git show of its navigator failed (TimeoutExpired)", live.ref_seam_gap("HEAD"))

    def test_the_seam_check_reads_a_ref_and_a_plugin_alike(self):
        self.assertEqual(live.ref_seam_gap("HEAD"), "")
        self.assertEqual(live.seam_gap(SCRIPTS), "")
        with self.assertRaises(SystemExit):
            live.ref_seam_gap("no-such-ref-anywhere")
        old = self.tmp / "old-plugin"
        scripts = old / live.SCRIPTS
        scripts.mkdir(parents=True)
        text = (SCRIPTS / "shiploop_navigator.py").read_text().replace("def accept_effects(", "def accept_effects_renamed(")
        (scripts / "shiploop_navigator.py").write_text(text)
        self.assertIn("has no accept_effects", live.seam_gap(scripts))
        self.assertIn("cannot be read", live.seam_gap(self.tmp / "nowhere"))

    def test_a_plugin_whose_navigator_has_no_accept_effects_is_refused_before_the_host_installs_it(self):
        old = self.tmp / "old-plugin-2"
        scripts = old / live.SCRIPTS
        shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
        path = scripts / "shiploop_navigator.py"
        path.write_text(path.read_text().replace("def accept_effects(", "def accept_effects_renamed("))
        host = self.refused(r"has no accept_effects.*Nothing was started", plugin_dir=old)
        self.assertEqual(host.calls, ["env"])
        self.assertFalse((self.tmp / host.script.parent.name / "sample" / "1" / "sessions.jsonl").exists())

    def test_a_refused_sample_leaves_why_and_no_result_for_the_report_to_count(self):
        old = self.tmp / "old-plugin-3"
        shutil.copytree(SCRIPTS, old / live.SCRIPTS, ignore=shutil.ignore_patterns("__pycache__"))
        path = old / live.SCRIPTS / "shiploop_navigator.py"
        path.write_text(path.read_text().replace("def accept_effects(", "def accept_effects_renamed("))
        host = self.refused("has no accept_effects", plugin_dir=old)
        sample = self.tmp / host.script.parent.name / "sample" / "1"
        self.assertIn("has no accept_effects", (sample / "error.txt").read_text())
        self.assertFalse((sample / "stage-result.json").exists())

    def test_a_host_on_ollama_that_is_not_ready_is_refused_and_so_is_a_spend_cap(self):
        with mock.patch.object(live.hosts, "ollama_ready", return_value="the Ollama server at http://x does not answer (down)"):
            host = self.refused(r"--backend ollama: the Ollama server at http://x does not answer.*Nothing was started", backend="ollama")
            self.assertEqual(host.calls, [])
        with mock.patch.object(live.hosts, "ollama_ready", return_value=None):
            self.refused(r"--max-budget-usd is not with --backend ollama", backend="ollama", max_budget_usd=1.0)
        self.assertEqual(live.host_gap(FakeHost(self.tmp, [{}]), "m"), "")

    def test_a_host_whose_plugin_install_failed_starts_nothing(self):
        """slice.py and run.py both call run.require_installed after the install: a Codex or Grok host that did not enable the
        build would run the model without the ShipLoop under test."""
        failed = {"pass": False, "loaded": [], "output": "marketplace add failed"}
        host = self.refused(r"did not install the plugin build.*\(loaded: no plugin\).*no host is started.*marketplace add failed",
                            installed=True, install=failed)
        self.assertEqual(host.calls, ["env", "install_plugin"])
        sample = self.tmp / host.script.parent.name / "sample" / "1"
        self.assertIn("did not install the plugin build", (sample / "error.txt").read_text())
        for name in ("seed-export", "sessions.jsonl", "invocation.json", ".shiploop-runs", "stage-result.json"):
            self.assertFalse((sample / name).exists(), f"{name}: nothing was built or started")

    def test_a_plugin_dir_does_not_take_a_ref_or_an_overlay(self):
        self.refused(r"--ref and --overlay build their own plugin", ref="HEAD")
        self.refused(r"--ref and --overlay build their own plugin", overlay=self.tmp / "o.json")

    @needs_node
    def test_a_stage_the_engine_settles_by_script_has_no_packet_for_a_model_to_follow(self):
        cases = self.tmp / "settled-cases"
        source = sb.load(BROKEN)
        target = cases / "validate-existing" / "settled"
        shutil.copytree(source.dir, target)
        repaired = (source.dir / "reference" / "good" / "tree" / "src" / "strings.js").read_text()
        (target / "repo" / "src").mkdir(parents=True, exist_ok=True)
        (target / "repo" / "src" / "strings.js").write_text(repaired)
        data = json.loads((target / "scenario.json").read_text())
        data["tiers"] = ["verify", "live"]
        (target / "scenario.json").write_text(json.dumps(data))
        host = self.refused(r"settled validate-existing by script.*Nothing was started", scenario="validate-existing/settled",
                            installed=True, cases_dir=cases)
        self.assertEqual(host.calls, ["env", "install_plugin"])


# --------------------------------------------------------------------------------------------------------------- boundary

class Boundary(unittest.TestCase):
    def test_the_live_module_is_outside_the_evaluator_digest_and_the_qualification_snapshot(self):
        module = HARNESS / "stage_suite" / "stage_live.py"
        self.assertTrue(module.is_file())
        evaluator, graded = set(boundary.evaluator_files(HARNESS)), set(boundary.oracle_files(HARNESS))
        self.assertNotIn(module, evaluator)
        self.assertNotIn(module, graded)
        self.assertFalse(any(path.parent.name in ("stage_suite", "stage_cases") for path in evaluator | graded))
        snapshot_files = boundary.qualification_snapshot(HARNESS)["files"]
        self.assertFalse([name for name in snapshot_files if "/stage_suite/" in name or "/stage_cases/" in name])
        self.assertFalse([name for name in snapshot_files if name.startswith("test/shiploop-e2e-stage")])
        self.assertFalse(boundary.candidate_path("test/shiploop_e2e/stage_suite/stage_live.py"))
        self.assertFalse(boundary.candidate_path("test/shiploop-e2e-stage-live.test.py"))

    def test_adding_the_module_leaves_the_digest_where_it_was(self):
        with tempfile.TemporaryDirectory(prefix="stage-live-boundary-") as temp:
            harness = Path(temp) / "shiploop_e2e"
            (harness / "checks").mkdir(parents=True)
            for name, text in {"run.py": "x = 1\n", "checks/c.py": "y = 2\n", "SPEC.md": "s\n"}.items():
                (harness / name).write_text(text)
            before = boundary.fingerprint(harness, None)
            (harness / "stage_suite").mkdir()
            (harness / "stage_suite" / "stage_live.py").write_text("z = 3\n")
            self.assertEqual(boundary.fingerprint(harness, None), before)

    def test_the_source_imports_the_harness_libraries_without_copying_them_and_the_harness_top_level_has_no_stage_file(self):
        text = (HARNESS / "stage_suite" / "stage_live.py").read_text()
        for used in ("run.launch(", "step_slice.overshoot_after(", "step_slice.read_state(", "stage_oracle.run_checks(",
                     "stage_oracle.verdict(", "sb.build(", "packets.archive_packets(", "sessionlog.start(", "listeners.hold_case("):
            self.assertIn(used, text)
        for copied in ("def overshoot_after", "def read_state", "def launch", "def archive_packets", "def run_checks"):
            self.assertNotIn(copied, text)
        self.assertFalse([p.name for p in HARNESS.iterdir() if p.is_file() and p.name.startswith("stage")])


if __name__ == "__main__":
    unittest.main()
