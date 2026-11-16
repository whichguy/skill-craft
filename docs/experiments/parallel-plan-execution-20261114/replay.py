#!/usr/bin/env python3
"""replay.py: the states and the seeding of E18, the paired fix-versus-redo replay (README Amendment A15, journal entry E18).

Apparatus for docs/experiments/parallel-plan-execution-20261114. E17 compared the two recovery rules between unpaired launches. This freezes one failed
integration of an E17 trial, the registered one per host, as a **state**, and starts a fresh trial from it under one rule, so the rule is the only
thing that differs between two trials of a pair.

A state (``real-repo/replay-states/<host>/``) holds
  state.bundle        a git bundle of exactly two refs: ``main`` at the commit main had when the integration failed (the base, the teammate's landing and the
                      two other features), and the failed attempt's branch: nothing from later in the E17 trial, so a worker cannot find a later solution
  ledger.prefix.jsonl the E17 ledger up to and including the ``retry`` event that offered the failed step again (verbatim, as exported)
  state.json          where it came from, the commits, the conflicting paths, the hashes

  replay.py freeze --raw ROOT [--host H]   write the states from E17's raw trial folders (the rule is STATES below)
  replay.py check [--host H] [--raw ROOT]  no model call: the states reproduce their failure and carry nothing from later; both rules seed and open the right
                                           workspace; the launcher path runs with the stand-in host; with --raw a known-good repair (the tree E17's own repair
                                           produced) passes the whole pipeline, the oracle too, and a repair that adds nothing is called invalid (the controls)
  replay.py show [--host H]                the states in one table
  replay.py diagnose TRIAL...              after the timed trials: a trial whose re-test did not end gets its kept candidate run three times on its own
  replay.py hung TRIAL                     exit 0 when the oracle left the tree unjudged (a whole-tree check that never ended in its tries): score_replay.sh then scores it again
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dagkit  # noqa: E402
import ticketfix  # noqa: E402

STATE_ROOT = HERE / "real-repo" / "replay-states"
RULES = ("fix", "redo")
HOSTS = ("claude", "grok", "codex")
# The registered rule: each host's valid qp trial of E17, its last failed integration (its last ``retry`` event). Whatever failed there was the last of
# the three features to be integrated, so main already held the landing and the other two features and the whole oracle applies to the repaired tree.
SOURCES = {"claude": "e17-claude-qp", "grok": "e17-grok-qp", "codex": "e17-codex-qp"}
RETEST = "npm test --silent"
RETEST_TIMEOUT = 60   # E17's kit waited 300 s for a re-test that never ends; a normal one takes 1 to 3 s, and one that does not end is run again (README A15)
MAX_ATTEMPTS = 4


def git(cwd, *args) -> tuple[int, str]:
    return ticketfix.git(cwd, *args)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ freeze

def freeze(host: str, raw_root: Path, dest_root: Path = STATE_ROOT) -> Path:
    """Write the state of ``host`` from E17's raw trial folder. Refuses anything that does not hold up: the failure must reproduce from the bundle alone."""
    src = Path(raw_root) / SOURCES[host]
    raw_repo = src / "work" / "repo"
    events = dagkit.Run(src / "work" / "run").events()
    retries = [i for i, e in enumerate(events) if e["kind"] == "retry"]
    if not retries:
        raise SystemExit(f"{SOURCES[host]} has no failed integration")
    cut = retries[-1]
    retry = events[cut]
    detail = retry["detail"]
    step, branch, cause = retry["step"], detail["from_branch"], detail["cause"]
    if cause != "conflict":
        raise SystemExit(f"the last failure of {SOURCES[host]} is a {cause}; the registered states are conflicts")
    prefix = events[:cut + 1]
    merged = [e for e in prefix if e["kind"] == "merged"]
    landed = next((e for e in prefix if e["kind"] == "landed"), None)
    if landed is None or not landed["detail"].get("ok"):
        raise SystemExit(f"{SOURCES[host]} has no clean landing before the failure")
    main_commit = merged[-1]["detail"]["commit"] if merged else landed["detail"]["head"]
    later = next((e for e in events[cut + 1:] if e["kind"] == "merged"), None)
    if later is not None and later["detail"].get("before") != main_commit:
        raise SystemExit(f"main was {later['detail'].get('before')} at the next merge, not {main_commit}: the cut is not a state of main")
    done_before = sorted({e["step"] for e in merged})
    plan = json.loads((src / "work" / "plan.json").read_text())
    others = sorted(s["id"] for s in plan["steps"] if s["id"] != step)
    if done_before != others:
        raise SystemExit(f"main held {done_before} at the failure, not the other two features {others}")
    failed_commit = git(raw_repo, "rev-parse", f"refs/heads/{branch}")[1].strip()
    root = git(raw_repo, "rev-list", "--max-parents=0", main_commit)[1].split()[0]
    dest = Path(dest_root) / host
    if dest.exists():
        raise SystemExit(f"{dest} exists; the states are frozen once")
    dest.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "r"
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(raw_repo), str(scratch)], check=True, capture_output=True)
        git(scratch, "update-ref", "refs/heads/main", main_commit)
        git(scratch, "update-ref", f"refs/heads/{branch}", failed_commit)
        rc, out = git(scratch, "bundle", "create", str(dest / "state.bundle"), "main", branch)
        if rc != 0:
            raise SystemExit("the bundle could not be made: " + out.strip())
    with open(dest / "ledger.prefix.jsonl", "w") as handle:
        for e in prefix:
            handle.write(json.dumps(e, separators=(",", ":")) + "\n")
    state = {"host": host, "source_trial": SOURCES[host], "step": step, "failed_attempt": detail["attempt"] - 1, "next_attempt": detail["attempt"],
             "branch": branch, "main_commit": main_commit, "failed_commit": failed_commit, "root_commit": root, "cause": cause, "paths": sorted(detail["paths"]),
             "main_holds": done_before, "retry_event_seq": retry["seq"], "prefix_events": len(prefix),
             "plan_sha": json.loads((src / "work" / "run" / "meta.json").read_text())["plan_sha"],
             "bundle_sha256": sha256(dest / "state.bundle"), "prefix_sha256": sha256(dest / "ledger.prefix.jsonl"),
             "e17_next_attempt_seconds": None, "known_answer_branch": None}
    later_start = next((e for e in events[cut + 1:] if e["kind"] == "start" and e["step"] == step), None)
    later_end = next((e for e in events[cut + 1:] if e["kind"] == "end" and e["step"] == step), None)
    if later_start and later_end:   # what E17's own repair of this failure took (the unpaired number this replay answers)
        state["e17_next_attempt_seconds"] = round(later_end["ts"] - later_start["ts"], 1)
        state["known_answer_branch"] = f"w-{step}-{detail['attempt']}"
    (dest / "state.json").write_text(json.dumps(state, indent=1) + "\n")
    return dest


# ------------------------------------------------------------------ seed

E17_PATH = re.compile(r"/Users/dadleet/e17-runs-\d+/e17-[a-z]+-[a-z0-9]+/")   # where E17's raw trial folders are: the repaired solutions sit under them, and a worker can read any path


def scrub(value):
    """The agent-visible ledger without any path into E17's raw trials (review R11: the failed re-tests' output in the Codex prefix named them). The frozen prefix stays verbatim."""
    if isinstance(value, str):
        return E17_PATH.sub("<E17 trial>/", value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value

def load_state(state_dir: Path) -> dict:
    state = json.loads((Path(state_dir) / "state.json").read_text())
    for name, key in (("state.bundle", "bundle_sha256"), ("ledger.prefix.jsonl", "prefix_sha256")):
        if sha256(Path(state_dir) / name) != state[key]:
            raise SystemExit(f"{state_dir}/{name} does not match state.json: the state was changed after it was frozen")
    return state


def seed(state_dir: Path, trial: Path, rule: str, kit: Path, plan_path: Path) -> dict:
    """Make ``trial/work`` (repo, run, kit) and ``trial/oracle`` as they were at the failure, with the kit set to ``rule`` for the retry of the failed step.
    Returns the state. The repo holds main at the failed integration's main and the failed attempt's branch and nothing else; the ledger is E17's, verbatim up
    to the failure (its workspace paths point into this trial, where those directories do not exist), then one ``replay_seed`` event."""
    if rule not in RULES:
        raise SystemExit(f"rule must be one of {RULES}")
    state = load_state(state_dir)
    state_dir, trial = Path(state_dir), Path(trial)
    work, repo, run_dir = trial / "work", trial / "work" / "repo", trial / "work" / "run"
    plan_text = Path(plan_path).read_text()
    if dagkit._sha(plan_text) != state["plan_sha"]:
        raise SystemExit("the plan is not the one E17 ran: its hash differs from the state's")
    subprocess.run(["git", "init", "-q", "-b", "unborn", str(repo)], check=True, capture_output=True)
    rc, out = git(repo, "fetch", "-q", str(state_dir / "state.bundle"), "refs/heads/*:refs/heads/*")
    if rc != 0:
        raise SystemExit("the bundle does not unpack: " + out.strip())
    git(repo, "checkout", "-q", "main")
    git(repo, "branch", "-q", "-D", "unborn")
    if git(repo, "rev-parse", "HEAD")[1].strip() != state["main_commit"] or git(repo, "rev-parse", f"refs/heads/{state['branch']}")[1].strip() != state["failed_commit"]:
        raise SystemExit("the unpacked repository is not at the state's commits")
    (trial / "oracle").mkdir(parents=True, exist_ok=True)
    shutil.copy(ticketfix.REAL / "landing.patch", trial / "oracle" / "landing.patch")
    ticketfix.base_after_landing(trial / "oracle" / "base-after-landing")
    init = [sys.executable, str(kit), "init", "--plan", str(plan_path), "--run", str(run_dir), "--settle", "0", "--retest", RETEST, "--on-failure", rule,
            "--max-attempts", str(MAX_ATTEMPTS), "--retest-timeout", str(RETEST_TIMEOUT), "--retest-reruns-hang", "--land", str(trial / "oracle" / "landing.patch"), "--land-message", ticketfix.LANDING_MESSAGE,
            "--repo", str(repo), "--workspace", "isolated"]
    subprocess.run(init, check=True, stdout=subprocess.DEVNULL)
    prefix = [json.loads(line) for line in (state_dir / "ledger.prefix.jsonl").read_text().splitlines() if line.strip()]
    events = []
    for e in prefix:
        e = json.loads(json.dumps(e))
        d = e["detail"]
        if e["kind"] == "init":
            d.update(repo=str(repo), land=str(trial / "oracle" / "landing.patch"), on_failure=rule, seeded_from=f"E17 {state['host']} qp")
        elif e["kind"] == "workspace" and d.get("path"):
            d["path"] = str(work / "ws" / f"{e['step']}-{d.get('attempt')}")   # E17's directories are not this trial's: nothing here to look at
        elif e["kind"] == "retry" and e["seq"] == state["retry_event_seq"]:
            d["mode"] = rule
        events.append(scrub(e))
    if events[-1]["kind"] != "retry" or events[-1]["detail"].get("mode") != rule:
        raise SystemExit("the seeded ledger does not end with the retry under the rule")
    text = "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events)
    if "e17-runs" in text or "e17-" in re.sub(r"<E17 trial>/", "", text):
        raise SystemExit("the seeded ledger still names an E17 raw trial folder")
    (run_dir / "ledger.jsonl").write_text(text)
    done = {}
    for e in events:   # the output of every step as the ledger last recorded it (the failed step's is its failed attempt's, replaced when it completes)
        if e["kind"] == "end":
            done[e["step"]] = e
    for step_id, e in done.items():
        (run_dir / "out" / f"{step_id}.json").write_text(json.dumps({"step": step_id, "inputs": {}, "result": e["detail"].get("result"), "sha": e["detail"]["sha"]}))
    run = dagkit.Run(run_dir)
    with run.locked():
        run.append("replay_seed", None, state=state["host"], rule=rule, source=f"E17 {state['host']} qp", failed_step=state["step"], failed_attempt=state["failed_attempt"],
                   main=state["main_commit"], failed=state["failed_commit"], paths=state["paths"], bundle_sha256=state["bundle_sha256"])
    return state


# ------------------------------------------------------------------ check (no model call)

class Report:
    def __init__(self) -> None:
        self.rows = []

    def add(self, name: str, ok: bool, note: str = "") -> None:
        self.rows.append((name, ok, note))
        print(f"  {'ok ' if ok else 'OFF'} {name}" + (f"  ({note})" if note else ""))


def kit_json(kit: Path, run_dir: Path, *args) -> dict:
    done = subprocess.run([sys.executable, str(kit), *args, "--run", str(run_dir)], capture_output=True, text=True)
    return json.loads(done.stdout)


def check_state(host: str, rep: Report, raw_root: Path | None) -> None:
    state_dir = STATE_ROOT / host
    state = load_state(state_dir)
    prefix = [json.loads(line) for line in (state_dir / "ledger.prefix.jsonl").read_text().splitlines() if line.strip()]
    rep.add(f"{host}: the ledger prefix ends with the retry of {state['step']} attempt {state['next_attempt']}",
            prefix[-1]["kind"] == "retry" and prefix[-1]["step"] == state["step"] and prefix[-1]["detail"]["attempt"] == state["next_attempt"])
    # the bundle: two refs, nothing later
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "r"
        subprocess.run(["git", "init", "-q", "-b", "unborn", str(repo)], check=True, capture_output=True)
        git(repo, "fetch", "-q", str(state_dir / "state.bundle"), "refs/heads/*:refs/heads/*")
        refs = sorted(git(repo, "for-each-ref", "--format=%(refname)")[1].split())
        rep.add(f"{host}: the bundle holds exactly main and {state['branch']}", refs == sorted(["refs/heads/main", f"refs/heads/{state['branch']}"]), str(refs))
        everything = set(git(repo, "rev-list", "--all")[1].split())
        reachable = set(git(repo, "rev-list", state["main_commit"], state["failed_commit"])[1].split())
        rep.add(f"{host}: every commit in it is in main's or the failed branch's history", everything == reachable, f"{len(everything)} commits")
        merged_commits = [e["detail"]["commit"] for e in prefix if e["kind"] == "merged"]
        rep.add(f"{host}: the landing and every merge of the prefix are in main's history",
                all(git(repo, "merge-base", "--is-ancestor", c, state["main_commit"])[0] == 0 for c in merged_commits + [next(e for e in prefix if e["kind"] == "landed")["detail"]["head"]]))
        git(repo, "checkout", "-q", "--detach", state["main_commit"])
        rc, _ = git(repo, "merge", "--no-commit", "--no-ff", state["failed_commit"])
        unmerged = sorted(n for n in git(repo, "diff", "--name-only", "--diff-filter=U")[1].split() if n)
        git(repo, "merge", "--abort")
        rep.add(f"{host}: merging the failed branch into main conflicts in the paths E17 logged", rc != 0 and unmerged == state["paths"], ", ".join(unmerged))
    # seed under both rules, open the recovery workspace the way a worker's begin does
    for rule in RULES:
        with tempfile.TemporaryDirectory() as tmp:
            trial = Path(tmp) / "t"
            trial.mkdir()
            kit, plan_path = trial / "work" / "dagkit.py", trial / "work" / "plan.json"
            (trial / "work").mkdir()
            shutil.copy(HERE / "dagkit.py", kit)
            shutil.copy(HERE / "plans" / "tickets3.json", plan_path)
            seed(state_dir, trial, rule, kit, plan_path)
            run_dir = trial / "work" / "run"
            seeded_text = (run_dir / "ledger.jsonl").read_text() + "".join(f.read_text(errors="replace") for f in (run_dir / "out").glob("*.json")) + (run_dir / "meta.json").read_text()
            rep.add(f"{host}/{rule}: nothing a worker can read in the run directory names an E17 raw trial folder or its trial", "e17-" not in seeded_text and "e17-runs" not in seeded_text)
            ready = kit_json(kit, run_dir, "ready", "--claim", "--capacity", "1")
            rep.add(f"{host}/{rule}: the kit offers exactly {state['step']} again and the other two features are done and merged",
                    ready["ready"] == [state["step"]] and sorted(ready["done"]) == sorted(state["main_holds"]) and not ready["failed"] and not ready["complete"], json.dumps(ready["ready"]))
            begun = subprocess.run([sys.executable, str(kit), "begin", "--run", str(run_dir), "--step", state["step"]], capture_output=True, text=True).stdout
            events = dagkit.Run(run_dir).events()
            ws = [e for e in events if e["kind"] == "workspace" and e["step"] == state["step"]][-1]["detail"]
            wsdir = Path(ws["path"])
            rep.add(f"{host}/{rule}: the workspace is attempt {state['next_attempt']}", ws["attempt"] == state["next_attempt"] and wsdir.is_dir())
            markers = sorted(n for n in git(wsdir, "diff", "--name-only", "--diff-filter=U")[1].split() if n)
            if rule == "fix":
                rep.add(f"{host}/fix: the workspace is the failed branch with main merged in, markers in the logged paths", bool(ws.get("fix")) and markers == state["paths"]
                        and "Do not start over" in begun and git(wsdir, "merge-base", "--is-ancestor", state["failed_commit"], "HEAD")[0] == 0, ", ".join(markers))
            else:
                rep.add(f"{host}/redo: the workspace is main as it is, clean, and the failed branch's work is not in it", not ws.get("fix") and not markers
                        and git(wsdir, "rev-parse", "HEAD")[1].strip() == state["main_commit"] and git(wsdir, "status", "--short")[1].strip() == ""
                        and "keep what is there and make your change on top of it" in begun and "Do not start over" not in begun)
            rep.add(f"{host}/{rule}: the task text is the same request", state["step"] in begun and ticketfix.case_prompt(dict(ticketfix.FEATURES)[state["step"]])[:60] in begun)
            # the repository has nothing but the state's history and the one new branch
            branches = sorted(git(trial / "work" / "repo", "for-each-ref", "--format=%(refname:short)", "refs/heads")[1].split())
            expected = sorted(["main", state["branch"], f"w-{state['step']}-{state['next_attempt']}"])
            rep.add(f"{host}/{rule}: the repository's branches are main, the failed branch and the new attempt's", branches == expected, ", ".join(branches))
            if raw_root is not None and state.get("known_answer_branch"):
                known_answer(host, rule, state, Path(raw_root), trial, kit, run_dir, wsdir, rep)
            subprocess.run(["git", "-C", str(trial / "work" / "repo"), "worktree", "prune"], capture_output=True)


def known_answer(host: str, rule: str, state: dict, raw_root: Path, trial: Path, kit: Path, run_dir: Path, wsdir: Path, rep: Report) -> None:
    """The tree E17's own repair produced goes through the recovery workspace, the kit's merge and re-test, verify and the oracle: a correct repair must come out valid."""
    raw_repo = raw_root / state["source_trial"] / "work" / "repo"
    good = git(raw_repo, "rev-parse", f"refs/heads/{state['known_answer_branch']}")[1].strip()
    if not good:
        rep.add(f"{host}/{rule}: known-answer branch {state['known_answer_branch']} found in the raw trial", False)
        return
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "k"
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(raw_repo), str(tree)], check=True, capture_output=True)
        git(tree, "checkout", "-q", "--detach", good)
        for path in list(wsdir.iterdir()):
            if path.name != ".git":
                shutil.rmtree(path) if path.is_dir() else path.unlink()
        for path in tree.iterdir():
            if path.name != ".git":
                (shutil.copytree if path.is_dir() else shutil.copy2)(path, wsdir / path.name)
    done = subprocess.run([sys.executable, str(kit), "complete", "--run", str(run_dir), "--step", state["step"], "--result", '{"answer": 1, "method": "known answer"}'],
                          capture_output=True, text=True)
    rep.add(f"{host}/{rule}: complete accepts the known-good repair", done.returncode == 0, done.stdout.strip()[:80])
    ready = kit_json(kit, run_dir, "ready", "--claim", "--capacity", "1")
    events = dagkit.Run(run_dir).events()
    merged = [e for e in events if e["kind"] == "merged" and e["step"] == state["step"] and e["seq"] > next(x["seq"] for x in events if x["kind"] == "replay_seed")]
    rep.add(f"{host}/{rule}: the kit merges it cleanly and the re-test is green", bool(merged) and ready["complete"], f"merged in {merged[0]['detail']['seconds'] if merged else '-'} s")
    verdict = subprocess.run([sys.executable, str(kit), "verify", "--run", str(run_dir)], capture_output=True, text=True).stdout.strip()
    rep.add(f"{host}/{rule}: verify says OK", verdict.startswith("VERIFY OK"), verdict[:60])
    meta = json.loads((run_dir / "meta.json").read_text())
    oracle = ticketfix.evaluate(trial, meta, dagkit.Run(run_dir).events(), candidates=False)
    rep.add(f"{host}/{rule}: the oracle calls the repaired tree valid", oracle["valid"] is True,
            f"features {oracle['features_ok']}, whole tree {oracle['whole_tree_ok']}, interactions {oracle['interactions_ok']}")


def negative_control(host: str, rep: Report) -> None:
    """The oracle must be able to fail here: a worker that does nothing but add a file leaves main as it was, which merges and passes the project's own tests,
    and the oracle must call the tree invalid and name the failed step's feature (the re-test alone cannot see it)."""
    state = load_state(STATE_ROOT / host)
    with tempfile.TemporaryDirectory() as tmp:
        trial = Path(tmp) / "t"
        (trial / "work").mkdir(parents=True)
        kit, plan_path = trial / "work" / "dagkit.py", trial / "work" / "plan.json"
        shutil.copy(HERE / "dagkit.py", kit)
        shutil.copy(HERE / "plans" / "tickets3.json", plan_path)
        seed(STATE_ROOT / host, trial, "redo", kit, plan_path)
        run_dir = trial / "work" / "run"
        kit_json(kit, run_dir, "ready", "--claim", "--capacity", "1")
        subprocess.run([sys.executable, str(kit), "begin", "--run", str(run_dir), "--step", state["step"]], capture_output=True, text=True)
        wsdir = Path([e for e in dagkit.Run(run_dir).events() if e["kind"] == "workspace"][-1]["detail"]["path"])
        (wsdir / "src" / "zz_nothing.js").write_text("'use strict';\nmodule.exports = {};\n")
        done = subprocess.run([sys.executable, str(kit), "complete", "--run", str(run_dir), "--step", state["step"], "--result", '{"answer": 1, "method": "nothing"}'],
                              capture_output=True, text=True)
        kit_json(kit, run_dir, "ready", "--claim", "--capacity", "1")
        meta = json.loads((run_dir / "meta.json").read_text())
        oracle = ticketfix.evaluate(trial, meta, dagkit.Run(run_dir).events(), candidates=False)
        # due times' `off` check is also a composition check against the base with assignment (A14): a tree that lacks assignment can fail it, so with T1 missing T3 may fail too
        allowed = {"T3"} if state["step"] == "T1" else set()
        rep.add(f"{host}: negative control: a repair that adds nothing is merged green and the oracle calls it invalid, naming {state['step']}",
                done.returncode == 0 and oracle["valid"] is False and oracle["features_ok"].get(state["step"]) is False
                and all(v or k in allowed for k, v in oracle["features_ok"].items() if k != state["step"]), f"features {oracle['features_ok']}")


def check_timeout(rep: Report) -> None:
    """A host that does not end is stopped at the trial's timeout with everything it started, and the launcher goes on to score (review R11: a PermissionError on macOS crashed it once)."""
    import launch
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sleeping = f"sleep {7000 + os.getpid() % 1000}"
        began = time.time()
        res = launch.run_host(["sh", "-c", f"{sleeping}; echo never"], tmp, dict(os.environ), tmp / "events.jsonl", tmp / "err.txt", 2)
        left = subprocess.run(["pgrep", "-f", sleeping], capture_output=True, text=True).stdout.split()
        rep.add("the launcher stops a host that does not end at the trial's timeout, with everything it started, and carries on",
                res["status"] == "timeout" and not left and time.time() - began < 30 and bool(res.get("load_series")), f"status {res['status']}, left {left}, {time.time() - began:.0f} s")


def check_launcher(host: str, rep: Report) -> None:
    """The launcher path with the stand-in host (fakehost.py): a seeded trial runs end to end through launch.py and the scorer (the oracle deferred), under both rules."""
    state = load_state(STATE_ROOT / host)
    for rule in RULES:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / f"t-{rule}"
            done = subprocess.run([sys.executable, str(HERE / "launch.py"), "--host", host, "--binary", str(HERE / "fakehost.py"), "--plan", "tickets3", "--arm", "A3s",
                                   "--workspace", "isolated", "--seed-state", str(STATE_ROOT / host), "--seed-rule", rule, "--timeout", "300", "--out", str(out)],
                                  capture_output=True, text=True, env=dict(os.environ, PPE_DEFER_ORACLE="1"))
            if done.returncode != 0 or not (out / "score.json").is_file():
                rep.add(f"{host}/{rule}: launch.py ran the seeded trial with the stand-in host", False, (done.stdout + done.stderr).strip()[-200:])
                continue
            m = json.loads((out / "score.json").read_text())
            inv = json.loads((out / "invocation.json").read_text())
            events = dagkit.Run(out / "work" / "run").events()
            seeded_at = next(e["seq"] for e in events if e["kind"] == "replay_seed")
            after = [e for e in events if e["seq"] > seeded_at]
            ws = [e["detail"] for e in after if e["kind"] == "workspace"]
            merged = [e for e in after if e["kind"] == "merged"]
            rep.add(f"{host}/{rule}: launch.py runs the seeded trial through the scorer (verify OK, faithful final report, one recovery merged)",
                    m.get("verify") == "OK" and m.get("fidelity_ok") is True and m.get("final_answer_ok") is True and len(merged) == 1 and merged[0]["step"] == state["step"]
                    and len(ws) == 1 and bool(ws[0].get("fix")) == (rule == "fix"),
                    f"verify {m.get('verify')} ({str(m.get('verify_line'))[:160]}), merged {[e['step'] for e in merged]}, workspaces {len(ws)}, retests {[(e['detail'].get('rc'), e['detail'].get('seconds')) for e in after if e['kind'] == 'retest']}")
            rep.add(f"{host}/{rule}: the invocation records the seed and the rule", (inv.get("replay") or {}).get("rule") == rule and inv.get("on_failure") == rule
                    and (inv.get("replay") or {}).get("bundle_sha256") == state["bundle_sha256"] and inv.get("land") is False)


def cmd_check(args) -> int:
    os.environ["PPE_RERUN_HANG"] = "1"   # the oracle runs as score_replay.sh runs it
    rep = Report()
    print("== launcher")
    check_timeout(rep)
    for host in ([args.host] if args.host else HOSTS):
        print(f"== {host}")
        check_state(host, rep, Path(args.raw) if args.raw else None)
        if args.raw:   # the controls run the oracle, about a minute each: with the known-good repairs they are the same pass
            negative_control(host, rep)
        check_launcher(host, rep)
    bad = [n for n, ok, _ in rep.rows if not ok]
    print(f"\n{len(rep.rows)} cells, {len(bad)} off")
    return 1 if bad else 0


def cmd_freeze(args) -> int:
    for host in ([args.host] if args.host else HOSTS):
        print(freeze(host, Path(args.raw)))
    return 0


def cmd_diagnose(args) -> int:
    """After the timed trials: for each trial whose re-test did not end (a ``retest`` event with rc 124), run the candidate tree the kit kept (``refs/candidates``) on its own three times
    with the tests' own command and say whether it hangs by itself. The draw stays as it is (review R11: the cause of a hang is not known, so it is not an apparatus fault)."""
    bad = 0
    for trial in map(Path, args.trials):
        events = dagkit.Run(trial / "work" / "run").events()
        hung = [e for e in events if e["kind"] == "retest" and e["detail"].get("rc") == 124]
        refs = git(trial / "work" / "repo", "for-each-ref", "--format=%(refname) %(objectname)", "refs/candidates")[1].split("\n")
        print(f"{trial.name}: {len(hung)} re-test(s) that did not end; candidate refs: {[r.split()[0] for r in refs if r.strip()] or 'none'}")
        for ref in (r.split() for r in refs if r.strip()):
            with tempfile.TemporaryDirectory() as tmp:
                tree = Path(tmp) / "c"
                subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(trial / "work" / "repo"), str(tree)], check=True, capture_output=True)
                git(tree, "checkout", "-q", "--detach", ref[1])
                results = [dagkit._run_tests(shlex.split(RETEST), tree, RETEST_TIMEOUT)[0] for _ in range(3)]
                print(f"  {ref[0]}: three runs on their own gave exit codes {results} (124 = did not end)")
                bad += sum(1 for r in results if r == 124)
    return 1 if bad else 0


def cmd_hung(args) -> int:
    """Exit 0 when the trial's oracle left the tree unjudged: a whole-tree check whose output still shows ``(rc None)`` (the delivery's tests did not end in any of the oracle's tries)."""
    score = json.loads((Path(args.trial) / "score.json").read_text())
    rows = (((score.get("write") or {}).get("oracle") or {}).get("whole_tree")) or []
    return 0 if any("(rc None)" in (r.get("output") or "") for r in rows if not r.get("pass")) else 1


def cmd_show(args) -> int:
    print(f"{'host':<7}{'source':<16}{'failed':<8}{'attempt':>8}{'main':>10}{'branch':>11}  paths (E17's own repair of it took)")
    for host in ([args.host] if args.host else HOSTS):
        s = load_state(STATE_ROOT / host)
        print(f"{host:<7}{s['source_trial']:<16}{s['step']:<8}{s['failed_attempt']:>8}{s['main_commit'][:8]:>10}{s['failed_commit'][:8]:>11}  {', '.join(s['paths'])} ({s['e17_next_attempt_seconds']} s)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("freeze", cmd_freeze), ("check", cmd_check), ("show", cmd_show), ("diagnose", cmd_diagnose), ("hung", cmd_hung)):
        p = sub.add_parser(name)
        if name == "hung":
            p.add_argument("trial", help="a scored trial folder")
        elif name == "diagnose":
            p.add_argument("trials", nargs="+", help="trial folders")
        else:
            p.add_argument("--host", choices=HOSTS)
        if name in ("freeze", "check"):
            p.add_argument("--raw", required=name == "freeze", help="the folder that holds E17's raw trial folders")
        p.set_defaults(fn=fn)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
