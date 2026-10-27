#!/usr/bin/env python3
"""E-EFF1 R2 queue: run the manifest's 16 runs, one scenario's pair at a time, with the launch guard and a log of every event.

    python3 -B r2_queue.py --wait-clear   # only wait for a clear Grok window, then exit 0 (a watcher; no launch)
    python3 -B r2_queue.py                # wait for a clear window, then run ONE pair; start it again for the next pair
    python3 -B r2_queue.py --pairs 8      # as many pairs as given in one go (a background task is killed at about two hours)
    python3 -B r2_queue.py --dry-run      # print the guard and the plan, launch nothing
    python3 -B r2_queue.py --self-test

Run it as a tracked background task. The platform kills a background task after about two hours, and the runs die with it, so one
invocation runs one pair (about 70 to 100 minutes) and exits; start it again for the next pair, and it also resumes a pair that was
killed in the middle: a run with no final result is continued with its own `--resume-run` command (the `resume:` line the
harness printed into r2-logs/<id>.log). State: r2-queue-state.json. Events, one line each: r2-queue-events.log. To stop launching
new pairs, create r2-queue.stop.

The manifest (manifest.json, frozen) is the only source of what runs: ids, argv, working directory, output folders, baselines.
Before every pair the runner checks `freeze_manifest.py --check` (harness files, plugin payload digest, worktree HEAD, schedules,
judge suite), and it does not launch while another session's Grok harness or experiment driver is running. After every run it
reads the run's invocation.json and says whether the plugin digest is the frozen payload's; a run on another build is flagged
invalid. A run whose engine is still `active` after its harness exits is continued, up to three times. Never edit a file the
manifest hashes while this runs (the plan, the schedules, run_totals.py, the harness): the guard would stop the queue.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXP = Path(__file__).resolve().parent
FREE_POLLS = int(os.environ.get("R2_FREE_POLLS", "3"))       # consecutive quiet polls before a pair launches
POLL_SECONDS = int(os.environ.get("R2_POLL_SECONDS", "120"))
RESUMES = 3
FINAL_ENGINE = ("done", "blocked", "halted", "paused")        # anything else is an incomplete run


class Queue:
    def __init__(self, exp: Path = EXP, manifest: Path | None = None):
        self.exp = Path(exp)
        self.manifest_path = manifest or self.exp / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text())
        self.state_path = self.exp / "r2-queue-state.json"
        self.log_path = self.exp / "r2-queue-events.log"
        self.logdir = self.exp / "r2-logs"
        self.stop_path = self.exp / "r2-queue.stop"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"runs": {}}
        self.children: dict[str, subprocess.Popen] = {}
        self.logdir.mkdir(exist_ok=True)

    # -- small helpers ---------------------------------------------------------------------------------------------
    def say(self, text: str) -> None:
        line = time.strftime("%Y-%m-%d %H:%M:%S ") + text
        print(line, flush=True)
        with self.log_path.open("a") as handle:
            handle.write(line + "\n")

    def save(self) -> None:
        temp = self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state, indent=1) + "\n")
        temp.replace(self.state_path)

    def run_state(self, run_id: str) -> dict:
        return self.state["runs"].setdefault(run_id, {"status": "pending", "resumes": 0})

    def pairs(self) -> list[list[dict]]:
        order, groups = [], {}
        for run in self.manifest["runs"]:
            if run["case"] not in groups:
                groups[run["case"]] = []
                order.append(run["case"])
            groups[run["case"]].append(run)
        return [groups[case] for case in order]

    # -- guards ----------------------------------------------------------------------------------------------------
    def guard(self) -> list[str]:
        """Why the manifest's own conditions do not hold (empty: they do)."""
        done = subprocess.run([sys.executable, "-B", str(self.exp / "freeze_manifest.py"), "--check"],
                              capture_output=True, text=True)
        return [] if done.returncode == 0 else ["freeze_manifest.py --check: " + " | ".join(done.stdout.split("\n"))[:400]]

    def foreign_grok(self) -> list[str]:
        """Other sessions' Python harness and driver processes (pid, elapsed, kind, host, case): never a command line's environment."""
        mine = {child.pid for child in self.children.values()} | {os.getpid()}
        pids = subprocess.run(["pgrep", "-f", r"shiploop_e2e/(run|slice)\.py|experiment\.py"], capture_output=True,
                              text=True).stdout.split()
        found = []
        for pid in pids:
            if int(pid) in mine:
                continue
            line = subprocess.run(["ps", "-p", pid, "-o", "etime=,args="], capture_output=True, text=True).stdout.strip()
            match = re.match(r"(\S+)\s+(\S*[Pp]ython\S*)\s+(.*)", line)
            if not match:
                continue  # a shell wrapper: its arguments can carry environment text
            rest = match.group(3)
            host = re.search(r"--host (\w+)", rest)
            case = re.search(r"--case (\S+)", rest)
            kind = "experiment.py" if "experiment.py" in rest else ("slice" if "slice.py" in rest else "run")
            if kind == "experiment.py" or (host and host.group(1) == "grok"):
                found.append(f"pid {pid} {match.group(1)} {kind} grok {case.group(1) if case else '-'}")
        return found

    def wait_for_clear(self) -> bool:
        quiet = 0
        reported = 0.0
        while quiet < FREE_POLLS:
            if self.stop_path.exists():
                return False
            others = self.foreign_grok()
            quiet = quiet + 1 if not others else 0
            if others and time.time() - reported > 1800:
                reported = time.time()
                self.say(f"waiting for Grok: {len(others)} other process(es): " + "; ".join(others[:4]))
            if quiet < FREE_POLLS:
                time.sleep(POLL_SECONDS)
        return True

    # -- running ---------------------------------------------------------------------------------------------------
    def resume_argv(self, run: dict) -> list[str] | None:
        """The harness's own `resume:` line from this run's log, as an argv."""
        log = self.logdir / f"{run['id']}.log"
        if not log.exists():
            return None
        for line in log.read_text(errors="replace").splitlines():
            if line.startswith("resume: "):
                return shlex.split(line[len("resume: "):])
        return None

    def launch(self, run: dict, resume: bool) -> None:
        st = self.run_state(run["id"])
        argv = (self.resume_argv(run) if resume else run["argv"])
        if argv is None:
            self.say(f"{run['id']}: cannot resume (no `resume:` line in its log); stopping the queue for a person to look")
            st["status"] = "stuck"
            self.save()
            raise SystemExit(4)
        log = (self.logdir / f"{run['id']}.log").open("ab")
        log.write(f"\n--- {'resume' if resume else 'launch'} {time.strftime('%F %T')} ---\n".encode())
        log.flush()
        child = subprocess.Popen(argv, cwd=run["cwd"], stdout=log, stderr=subprocess.STDOUT)
        self.children[run["id"]] = child
        st.update(status="running", started=st.get("started") or time.time(), last_launch=time.time())
        if resume:
            st["resumes"] += 1
        self.save()
        self.say(f"{run['id']}: {'resumed' if resume else 'launched'} (pid {child.pid}, attempt {st['resumes'] + 1})")

    def result_facts(self, run: dict) -> dict:
        out = Path(run["output"])
        facts: dict = {"engine": None, "pass": None, "plugin_ok": None}
        try:
            result = json.loads((out / "result.json").read_text())
            facts["engine"] = (result.get("termination") or {}).get("engine_status")
            facts["pass"] = result.get("pass")
        except (OSError, ValueError):
            pass
        try:
            versions = json.loads((out / "invocation.json").read_text()).get("versions") or {}
            facts["plugin_ok"] = versions.get("plugin_sha256") == self.manifest["plugin"]["payload_sha256"]
        except (OSError, ValueError):
            pass
        try:
            sys.path.insert(0, str(self.exp))
            import run_totals
            totals = run_totals.totals(out)
            facts["seconds"], facts["tokens"] = totals.get("seconds"), totals.get("tokens")
        except Exception:  # noqa: BLE001 - reporting only
            pass
        try:
            facts["restarts"] = len(json.loads((out / "effort.json").read_text()).get("restarts", []))
        except (OSError, ValueError):
            pass
        return facts

    def settle(self, run: dict, returncode: int) -> None:
        st = self.run_state(run["id"])
        facts = self.result_facts(run)
        engine = facts.get("engine")
        if engine in FINAL_ENGINE:
            st.update(status="final", returncode=returncode, finished=time.time(), facts=facts)
            note = "" if facts.get("plugin_ok") else "  INVALID: plugin digest is not the frozen payload's"
            self.say(f"{run['id']}: finished exit={returncode} engine={engine} verdicts_pass={facts.get('pass')} "
                     f"seconds={facts.get('seconds')} restarts={facts.get('restarts')} tokens={facts.get('tokens')}{note}")
        elif st["resumes"] < RESUMES:
            st["status"] = "needs-resume"
            self.say(f"{run['id']}: harness exited {returncode} with the engine {engine!r}; it will be continued")
        else:
            st.update(status="final", returncode=returncode, finished=time.time(), facts=facts, incomplete=True)
            self.say(f"{run['id']}: INCOMPLETE after {RESUMES} resumes (engine {engine!r}); recorded as the arm's outcome")
        self.save()

    def run_pair(self, pair: list[dict]) -> None:
        for run in pair:
            st = self.run_state(run["id"])
            if st["status"] == "final":
                continue
            out = Path(run["output"])
            resume = out.exists() and st["status"] in ("running", "needs-resume")
            if (out / "result.json").exists() and st["status"] == "running":
                # the harness finished while no runner was watching
                self.settle(run, 0)
                if self.run_state(run["id"])["status"] == "final":
                    continue
                resume = True
            self.launch(run, resume)
        while True:
            active = {rid: child for rid, child in self.children.items() if child.poll() is None}
            for run in pair:
                child = self.children.get(run["id"])
                if child is not None and child.poll() is not None and self.run_state(run["id"])["status"] == "running":
                    self.settle(run, child.returncode)
                    if self.run_state(run["id"])["status"] == "needs-resume":
                        self.launch(run, True)
            if all(self.run_state(r["id"])["status"] == "final" for r in pair):
                return
            time.sleep(5)

    def main(self, dry_run: bool = False, max_pairs: int | None = None) -> int:
        problems = self.guard()
        pairs = self.pairs()
        self.say(f"R2 queue: {len(self.manifest['runs'])} runs in {len(pairs)} pairs; manifest {self.manifest.get('sha256', '')[:8]}; "
                 f"guard {'OK' if not problems else 'FAILED'}")
        if problems:
            self.say("GUARD FAILED: " + "; ".join(problems))
            return 3
        if dry_run:
            for pair in pairs:
                self.say("would run: " + ", ".join(r["id"] for r in pair))
            self.say("foreign Grok now: " + (" | ".join(self.foreign_grok()) or "none"))
            return 0
        launched = 0
        for index, pair in enumerate(pairs, 1):
            if all(self.run_state(r["id"])["status"] == "final" for r in pair):
                continue
            if max_pairs is not None and launched >= max_pairs:
                self.say(f"pair limit ({max_pairs}) reached: start the queue again for pair {index}")
                return 0
            launched += 1
            if self.stop_path.exists():
                self.say("stop file found: no further pairs")
                return 0
            if not self.wait_for_clear():
                self.say("stop file found while waiting: no further pairs")
                return 0
            problems = self.guard()
            if problems:
                self.say("GUARD FAILED before pair %d: %s" % (index, "; ".join(problems)))
                return 3
            others = self.foreign_grok()
            for run in pair:
                self.run_state(run["id"])["foreign_at_launch"] = others
            self.say(f"pair {index}/{len(pairs)} ({pair[0]['case']}): starting {', '.join(r['id'] for r in pair)}")
            self.run_pair(pair)
            self.say(f"pair {index}/{len(pairs)} ({pair[0]['case']}): done")
        self.say("R2 queue: all pairs final")
        return 0


def self_test() -> int:
    """Fake runs: two scenarios; the second control run first exits incomplete and must be continued with its resume line."""
    tmp = Path(tempfile.mkdtemp(prefix="r2-queue-selftest-"))
    fake = tmp / "fake_run.py"
    fake.write_text('''
import json, sys, time
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--output") + 1] if "--output" in args else args[args.index("--resume-run") + 1])
resume = "--resume-run" in args
out.mkdir(parents=True, exist_ok=True)
print("resume: " + sys.executable + " " + __file__ + " --resume-run " + str(out), flush=True)
time.sleep(1.5)
flaky = out.name == "control-b" and not resume
(out / "invocation.json").write_text(json.dumps({"versions": {"plugin_sha256": "feedface0000"}}))
(out / "effort.json").write_text(json.dumps({"restarts": [1, 2]}))
(out / "result.json").write_text(json.dumps({"pass": True, "termination": {"engine_status": "active" if flaky else "done"}}))
sys.exit(1 if flaky else 0)
''')
    runs = []
    for case in ("a", "b"):
        for arm in ("control", "treatment"):
            out = tmp / "out" / f"{arm}-{case}"
            runs.append({"id": f"{arm}-{case}", "case": case, "arm": arm, "output": str(out), "cwd": str(tmp),
                         "argv": [sys.executable, str(fake), "--output", str(out)]})
    (tmp / "manifest.json").write_text(json.dumps({"sha256": "selftest", "runs": runs, "plugin": {"payload_sha256": "feedface0000"}}))
    (tmp / "freeze_manifest.py").write_text("import sys; sys.exit(0)\n")
    os.environ["R2_FREE_POLLS"] = "1"
    global FREE_POLLS, POLL_SECONDS
    FREE_POLLS, POLL_SECONDS = 1, 1
    first = Queue(tmp)
    first.foreign_grok = lambda: []                      # no other session in the test
    code = first.main(max_pairs=1)                       # one pair per invocation
    state = json.loads((tmp / "r2-queue-state.json").read_text())
    only_a = all(state["runs"].get(f"{a}-a", {}).get("status") == "final" for a in ("control", "treatment")) \
        and "control-b" not in state["runs"]
    second = Queue(tmp)
    second.foreign_grok = lambda: []
    code2 = second.main(max_pairs=1)
    state = json.loads((tmp / "r2-queue-state.json").read_text())
    ok = (only_a and code == 0 and code2 == 0 and all(s["status"] == "final" for s in state["runs"].values())
          and state["runs"]["control-b"]["resumes"] == 1 and state["runs"]["control-a"]["resumes"] == 0
          and all(s["facts"]["plugin_ok"] for s in state["runs"].values()))
    # the pair really overlapped: both launches precede the first finish
    events = (tmp / "r2-queue-events.log").read_text().splitlines()
    launches = [i for i, l in enumerate(events) if "launched" in l]
    finishes = [i for i, l in enumerate(events) if "finished" in l]
    ok = ok and launches[1] < finishes[0] and any("pair limit" in l for l in events)
    again = Queue(tmp)
    again.foreign_grok = lambda: []
    ok = ok and again.main() == 0 and sum("launched" in l or "resumed" in l for l in (tmp / "r2-queue-events.log").read_text().splitlines()) == 5
    # a guard failure stops it
    (tmp / "freeze_manifest.py").write_text("import sys; print('changed since the freeze: x'); sys.exit(1)\n")
    (tmp / "r2-queue-state.json").unlink()
    third = Queue(tmp)
    ok = ok and third.main() == 3
    print("SELF-TEST", "PASS" if ok else "FAIL", "(events in", tmp, ")")
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--wait-clear", action="store_true", help="only wait for a clear Grok window, then exit 0")
    parser.add_argument("--pairs", type=int, default=1, help="pairs to run in this invocation (default 1)")
    args = parser.parse_args()
    if args.self_test:
        sys.exit(self_test())
    queue = Queue()
    if args.wait_clear:
        queue.say("watching for a clear Grok window")
        clear = queue.wait_for_clear()
        queue.say("Grok is clear: no other session's Grok harness or driver for %d polls" % FREE_POLLS if clear else "stop file found")
        sys.exit(0 if clear else 1)
    sys.exit(queue.main(dry_run=args.dry_run, max_pairs=args.pairs))
