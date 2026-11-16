#!/usr/bin/env python3
"""The facade's derivations against the REAL E2E loop, with fake hosts. No model is called.

The step tests (test/shiploop-e2e-adapter-steps.test.py) use a stand-in engine, so they can only check the facade against the facade's
idea of the harness's files. This test runs the harness's own `iterate.py --qualify --iterations 1` through the facade's `step start` on a
copy of this repository, with one fake `codex` (test/fixtures/closed-loop-adapter/fake_codex.py) answering every role, and reads what the
real loop wrote: the run folders, `LOOP.md`, the review and judge verdicts, the real scorecard and strict-outcome function, the real
baseline rows and the real comparability predicate (`run.row_matches`), the real cycle's `cycle-result.json` and epoch events, the kept
candidate ref and the real lifecycle ledgers. The fake hosts score `fidelity: unobserved`, so a case misses its floors and a cycle decides
UNDECIDED; that is the correct reading of those runs, and a promotion cannot be reached here (the step tests cover it).

About 2 minutes. Run: python3 -B test/shiploop-e2e-adapter-engine.test.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
FACADE = HARNESS / "adapter" / "facade.py"
FIXTURES = ROOT / "test" / "fixtures" / "closed-loop-adapter"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


facade = load("shiploop_facade_engine_test", FACADE)
closed_loop = load("closed_loop_script_engine_test", ROOT / "skills" / "closed-loop" / "scripts" / "closed_loop.py")
CONFIG = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
STATE: dict = {}


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", str(repo), *CONFIG, *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {done.stderr}")
    return done.stdout.strip()


def build_real_source(folder: Path):
    """The tracked files the loop needs (the harness, the skills, the build scripts and the catalog), with an empty ledger and baseline
    file so what the loop selects and compares is what the test put there. About 1,500 files."""
    src = folder / "src"
    src.mkdir()
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "gc.auto", "0")
    git(src, "config", "maintenance.auto", "false")
    listed = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "test/shiploop_e2e", "skills", "agents", "catalog", "scripts", "README.md",
                             "LICENSE", ".gitattributes"], capture_output=True, check=True).stdout.split(b"\0")
    for raw in listed:
        if not raw:
            continue
        name = raw.decode()
        source = ROOT / name
        if source.is_file() and not source.is_symlink():
            (src / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, src / name)
    (src / ".gitignore").write_text(".claude/worktrees/\n__pycache__/\n")
    (src / facade.LEDGER_REL).write_text("")
    (src / facade.BASELINES_REL).write_text("")
    (src / "test" / "run-all.sh").write_text("#!/bin/sh\nexit ${FAKE_TIER_EXIT:-0}\n")  # the quick tier is the repository's own suite: a stand-in
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "base")
    return src, git(src, "rev-parse", "HEAD")


def setUpModule():
    folder = Path(tempfile.mkdtemp(prefix="shiploop-adapter-engine-")).resolve()
    STATE["folder"] = folder
    STATE["src"], STATE["base"] = build_real_source(folder)
    bin_dir = folder / "bin"
    bin_dir.mkdir()
    shutil.copy2(FIXTURES / "fake_codex.py", bin_dir / "codex")
    (bin_dir / "lsof").write_text("#!/bin/sh\nexit 1\n")
    for name in ("codex", "lsof"):
        (bin_dir / name).chmod((bin_dir / name).stat().st_mode | stat.S_IXUSR)
    broken = folder / "broken-bin"  # a host that cannot start: the negative control for the probe that runs a case
    broken.mkdir()
    shutil.copy2(bin_dir / "lsof", broken / "lsof")
    (broken / "codex").write_text("#!/bin/sh\nexit 1\n")
    (broken / "codex").chmod((broken / "codex").stat().st_mode | stat.S_IXUSR)
    STATE["broken_bin"] = broken
    for name in ("codex-home", "home", "state", "leases"):
        (folder / name).mkdir()
    (folder / "codex-home" / "auth.json").write_text("{}")
    # The real loop commits its learnings with the caller's git identity (the owner's home has one). Without one, git
    # guesses user@hostname, which it refuses when the hostname has no dot, so this home carries its own.
    (folder / "home" / ".gitconfig").write_text("[user]\n\tname = Test\n\temail = test@example.invalid\n[commit]\n\tgpgsign = false\n")
    STATE["bin"] = bin_dir


def tearDownModule():
    shutil.rmtree(STATE["folder"], ignore_errors=True)


class RealEngineTests(unittest.TestCase):
    def setUp(self):
        folder = STATE["folder"]
        self.folder = Path(tempfile.mkdtemp(prefix="case-", dir=folder)).resolve()
        self.x = self.folder / "x"
        self.work = self.folder / "work"
        setup = subprocess.run([sys.executable, "-B", str(FACADE), "setup", "--workspace", str(self.x), "--base", STATE["base"], "--source",
                                str(STATE["src"])], capture_output=True, text=True, check=False)
        self.assertEqual(setup.returncode, 0, setup.stderr)
        self.layout = facade.Layout(self.x)
        self.log = self.folder / "fake-log"
        self.addCleanup(self.stop_everything)

    def env(self, **extra):
        folder = STATE["folder"]
        return {"PATH": f"{STATE['bin']}:{os.environ['PATH']}", "HOME": str(folder / "home"), "CODEX_HOME": str(folder / "codex-home"),
                "XDG_STATE_HOME": str(folder / "state"), "SHIPLOOP_E2E_LEASES": str(folder / "leases"), "SHIPLOOP_PROGRESS": "off",
                "PYTHONDONTWRITEBYTECODE": "1", "CLOSED_LOOP_WORKSPACE": str(self.x), "FAKE_LOG": str(self.log),
                "FAKE_STORE_DIR": str(self.x / "skills" / "shiploop" / "scripts"), **extra}

    def cli(self, *args, **extra):
        done = subprocess.run([sys.executable, "-B", str(FACADE), *args], capture_output=True, text=True, env=self.env(**extra), check=False)
        self.assertEqual(done.returncode, 0, f"facade {' '.join(args)}: {done.stderr}")
        return json.loads(done.stdout)

    def start(self, key, cases, mode="iterate", **extra):
        return self.cli("step", "--host", "codex", "--model", "fake-model", "--effort", "high", "--tolerance", "0.25", "--attempts", "1",
                        "--parallel", "1", "start", "--key", key, "--scope", "s1", "--cases", ",".join(cases), "--mode", mode, "--base",
                        self.cli("identity")["build"], "--out", str(self.work / "runs" / key), **extra)

    def finish(self, key, timeout=420.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            reply = self.cli("step", "poll", "--handle", key)
            if reply["status"] != "running":
                return reply
            time.sleep(1.0)
        raise AssertionError(f"step {key} did not finish in {timeout} s")

    def stop_everything(self):
        if self.layout.steps.is_dir():
            keys = [path.stem for path in sorted(self.layout.steps.glob("*.json"))]
            if keys:
                subprocess.run([sys.executable, "-B", str(FACADE), "cleanup", "--keys", ",".join(keys)], capture_output=True, text=True,
                               env=self.env(), check=False)

    def valid(self, reply, cases):
        self.assertEqual(reply["status"], "done", reply)
        self.assertEqual(closed_loop.validate_facts(reply["iteration"], cases), [], reply["iteration"])
        return reply["iteration"]

    def test_a_quiet_exploration_then_a_second_one_compared_with_the_first_row(self):
        self.start("s1", ["hello"], FAKE_NO_DISCOVERY="1")
        first = self.valid(self.finish("s1"), ["hello"])
        self.assertEqual(first["cases"]["hello"]["ran"], True, "the real result.json says the skill was invoked from the build under test")
        self.assertEqual(first["cases"]["hello"]["floors_met"], False, "fake hosts leave fidelity unobserved, so the strict outcome is not met")
        self.assertEqual(first["cases"]["hello"]["baseline"], "none", "a run is not compared with its own row")
        self.assertEqual((first["review"], first["judge"]), ({"valid": True, "complete": True}, {"valid": True, "complete": True}))
        self.assertEqual((first["discoveries"], first["candidate"], first["acceptance"]), ([], None, None))
        self.assertEqual(first["build_after"], first["build_before"])
        self.assertTrue(first["cleanup"]["verified"], first["cleanup"])
        self.assertEqual(first["invalid"], [], first["invalid"])
        self.assertEqual(first["consumed"]["runs"], 1)
        record = json.loads((self.layout.steps / "s1.json").read_text())
        self.assertEqual(record["invocations"][0]["loop"]["stop"], "no admitted learning record after exploring")
        self.assertEqual(git(self.x, "status", "--porcelain"), "", "the clone is clean: the baseline row the run appended was captured and restored")
        history = facade.lines_of(self.layout.baselines_file.read_text())
        self.assertEqual(len(history), 1)
        self.assertEqual(json.loads(history[0])["case"], "hello")
        self.assertEqual(git(self.x, "show", f"HEAD:{facade.BASELINES_REL}"), "")
        self.start("s2", ["hello"], FAKE_NO_DISCOVERY="1")
        second = self.valid(self.finish("s2"), ["hello"])
        self.assertEqual(second["cases"]["hello"]["baseline"], "comparable", "the harness's own predicate accepts the first step's real row")
        self.assertEqual(second["build_before"], first["build_after"])

    def test_an_exploration_that_finds_something_goes_on_to_a_cycle_the_facade_reports(self):
        self.start("s1", ["hello", "csv-report"])
        reply = self.finish("s1")
        it = self.valid(reply, ["hello", "csv-report"])
        record = json.loads((self.layout.steps / "s1.json").read_text())
        first = record["invocations"][0]
        self.assertEqual(first["generality"], "csv-report", "the facade picked the other-style case of the scope")
        self.assertTrue(first["loop"]["explored"] and first["cycle_ran"])
        self.assertEqual([item["id"] for item in it["discoveries"]], [first["loop"]["cycle"]])
        self.assertEqual([item["material"] for item in it["discoveries"]], [True])
        self.assertFalse(it["discoveries"][0]["repeat"])
        self.assertIn(it["candidate"]["outcome"], ("UNDECIDED", "DROP"), it["candidate"])
        refs = git(self.x, "for-each-ref", "--format=%(objectname)", "refs/shiploop-loop/")
        self.assertEqual(it["candidate"]["hash"], refs, "the candidate is the commit the cycle kept under refs/shiploop-loop")
        self.assertEqual(it["build_after"], it["build_before"], "a candidate that is not promoted leaves the build alone")
        self.assertEqual(it["cases"]["csv-report"], {"ran": False, "floors_met": False, "baseline": "none"}, "a cycle ends the step")
        self.assertEqual(it["cases"]["hello"]["ran"], True)
        self.assertIsNone(it["acceptance"])
        self.assertTrue(it["review"]["valid"] and it["review"]["complete"], it["review"])
        self.assertTrue(it["judge"]["valid"] and it["judge"]["complete"], it["judge"])
        self.assertTrue(it["cleanup"]["verified"], it["cleanup"])
        self.assertEqual(self.engine_calls_with("improver"), 1)
        history = facade.lines_of(self.layout.baselines_file.read_text())
        self.assertEqual(len(history), 5, "the exploration's row from X's file and the four attempts' rows from the epoch's")
        by_id = {item["id"]: item for item in self.cli("records")["records"]}
        self.assertIn(first["loop"]["cycle"], by_id)
        self.assertEqual(self.cli("identity")["build"], it["build_after"])
        out = self.work / "runs" / "s1" / "inv-1"
        epoch = out / "cycle-1" / "epoch"
        harness = self.x / "test" / "shiploop_e2e"
        counted = subprocess.run([sys.executable, "-B", "-c", "import json, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport epoch\n"
                                  "state = epoch.state(Path(sys.argv[2]))\nwanted = {a['id'] for a in state['decision']['result']['attempts']}\n"
                                  "print(json.dumps(sorted(a['id'] for a in state['attempts'] if a['status'] == 'reviewed' and a['id'] in wanted)))",
                                  str(harness), str(epoch)], capture_output=True, text=True, check=True, cwd=str(harness))
        reviewed = json.loads(counted.stdout.strip().splitlines()[-1])
        found = facade.epoch_evidence(self.layout, out)
        self.assertEqual((found["unreadable"], found["invalid_evidence"]), (None, []), found)
        self.assertEqual(len(found["receipts"]), len(reviewed), "the facade's reviewed attempts are the ones the harness's own epoch.state counts")
        # A sealed run whose evidence changes after it was recorded: the harness calls it invalid_evidence, and so does the facade.
        sealed = epoch / "runs" / reviewed[0] / "result.json"
        sealed.write_text(sealed.read_text() + "\n")
        changed = facade.epoch_evidence(self.layout, out)
        self.assertEqual(changed["invalid_evidence"], [reviewed[0]], changed)
        self.assertEqual(len(changed["receipts"]), len(reviewed) - 1)

    def probe(self, claim, *flags, **extra):
        return self.cli("probe", "--host", "codex", "--model", "fake-model", "--effort", "high", *flags, claim, **extra)

    def test_the_runs_and_scores_probes_prove_a_real_run_and_fail_closed_without_one(self):
        before = self.probe("grading.scores")
        self.assertEqual(before["state"], "declared", before)
        runs = self.probe("cases.runs:hello", FAKE_NO_DISCOVERY="1")
        self.assertEqual(runs["state"], "runs", runs)
        self.assertEqual(runs["consumed"]["runs"], 1)
        for words in ("the skill was invoked from the build under test", "lifecycle cleanup", "is verified"):
            self.assertIn(words, runs["evidence"])
        scores = self.probe("grading.scores")
        self.assertEqual(scores["state"], "scores", scores)
        self.assertIn("twice with identical output", scores["evidence"])
        self.assertIn('"fidelity"', scores["evidence"], "the three floors are on the card (fake hosts leave fidelity unobserved)")
        self.assertEqual(git(self.x, "status", "--porcelain"), "", "a probe writes in a clone under the state folder, never in X")
        self.assertEqual(git(self.x, "rev-parse", "HEAD"), STATE["base"])

    def test_a_host_that_cannot_start_leaves_cases_runs_declared(self):
        path = f"{STATE['broken_bin']}:{os.environ['PATH']}"  # the owner's real codex may be on PATH further along: the broken one comes first
        runs = self.probe("cases.runs:hello", PATH=path)
        self.assertEqual(runs["state"], "declared", runs)
        self.assertIn("did not prove it runs", runs["evidence"])
        self.assertEqual(self.probe("grading.scores")["state"], "declared", "a run that did not prove itself is not a stored real run")

    def test_the_orchestrator_drives_a_smoke_campaign_through_the_facade(self):
        """The dress rehearsal of the first real campaign, with fake hosts: init, ratify, readiness (every probe), then steps, until the
        orchestrator has recorded an iteration it accepted; then its cleanup, status and certificate verbs."""
        manifest = json.loads((HARNESS / "adapter" / "adapter.json").read_text())
        manifest["execution"]["pin"] = [str(FACADE), str(HARNESS / "adapter" / "allowlist.json")]
        manifest["execution"]["cwd"] = str(self.folder)
        manifest["execution"]["env_allow"] = sorted({*manifest["execution"]["env_allow"], "FAKE_LOG", "FAKE_STORE_DIR", "FAKE_NO_DISCOVERY",
                                                     "SHIPLOOP_E2E_LEASES", "SHIPLOOP_PROGRESS", "FAKE_TIER_EXIT"})
        for name in ("cases", "records", "identity", "step", "probe"):
            manifest["commands"][name][1] = str(FACADE)
        manifest["execution"]["cleanup"][1] = str(FACADE)
        path = self.folder / "adapter.json"
        path.write_text(json.dumps(manifest, indent=2))
        campaign = self.folder / "campaign"

        def loop(*args, ok=(0,), **extra):
            done = subprocess.run([sys.executable, "-B", str(ROOT / "skills" / "closed-loop" / "scripts" / "closed_loop.py"), *args],
                                  capture_output=True, text=True, env=self.env(**extra), check=False)
            self.assertIn(done.returncode, ok, f"closed_loop.py {' '.join(args)} exited {done.returncode}: {done.stdout[-600:]} {done.stderr[-300:]}")
            return json.loads(done.stdout)
        loop("init", "--manifest", str(path), "--campaign", str(campaign), "--workspace", str(self.x), "--cases", "hello",
             "--budget", "seconds=3600,runs=50", "--quiet-window", "1")
        loop("ratify", "--campaign", str(campaign), "--yes-owner-approved", "--note", "rehearsal: the test plays the owner")
        ready = loop("readiness", "--manifest", str(path), "--campaign", str(campaign), "--workspace", str(self.x), "--require-start",
                     FAKE_NO_DISCOVERY="1")
        states = {claim: entry["state"] for claim, entry in ready["claims"].items()}
        self.assertEqual(states, {"cases.runs:hello": "runs", "grading.scores": "scores", "improver.bounded": "bounded",
                                  "grading.calibrated:codex/gpt-6.1-terra/high": "unmeasured"})
        self.assertTrue(ready["start_ok"], ready)
        self.assertIn("no quality claim is allowed yet", " ".join(ready["allowed_claims"]))
        actions = []
        for _ in range(60):
            moved = loop("step", "--campaign", str(campaign), ok=(0, 1), FAKE_NO_DISCOVERY="1")
            actions.append(moved["action"])
            if moved["action"] in ("blocked", "stop") or loop("status", "--campaign", str(campaign), "--no-certificate")["iterations"]:
                break
            time.sleep(1.0)
        status = loop("status", "--campaign", str(campaign), "--no-certificate")
        self.assertEqual(status["iterations"], 1, (actions, status))
        last = status["last_iteration"]
        self.assertFalse(last.get("failed"), last)
        self.assertIn("a scope case did not run or missed its floors", last["quiet_reasons"], "fake hosts leave fidelity unobserved: not quiet, and said so")
        self.assertNotIn("the review was not valid and complete", last["quiet_reasons"])
        cleaned = loop("cleanup", "--campaign", str(campaign))
        self.assertTrue(cleaned["ok"], cleaned)
        certificate = loop("certificate", "--campaign", str(campaign), ok=(0, 1))
        self.assertEqual(certificate["status"], "incomplete", "fake hosts leave fidelity unobserved: the scope cannot converge on them")
        self.assertTrue(any("floors" in reason for reason in certificate["reasons"]), certificate["reasons"])
        self.assertEqual(sorted(certificate["checks"]), ["C1", "C2", "C3", "C4", "C5", "C6", "C7"])


    def engine_calls_with(self, role):
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        return sum(1 for row in rows if row.get("role") == role)


if __name__ == "__main__":
    unittest.main()
