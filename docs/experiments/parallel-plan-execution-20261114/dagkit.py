#!/usr/bin/env python3
"""dagkit: the ledger and the synthetic work unit of the parallel-plan-execution probes.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README); it is not ShipLoop code and no
skill uses it. Every arm calls it through the host's own shell tool, so each command is a visible host tool call. The
ledger (``RUN/ledger.jsonl``, one JSON object per line) is the ground truth for when each step ran.

  dagkit.py init     --plan PLAN.json --run RUN [--settle SECONDS] [--repo DIR --workspace shared|isolated]
  dagkit.py settle   --run RUN --step ID     task steps with --settle: a slow verification (a sleep) the agent runs before it reports;
                                             it stands for a slow test suite or build and is the dial for how long a task takes
  dagkit.py ready    --run RUN [--claim [--capacity N]]
                     one JSON line: ready, deferred, claimed, running, done, failed, blocked, waiting, complete, capacity,
                     claimed_age_s. With --claim the ready steps are claimed (at most N minus the claimed and running ones
                     when --capacity is given); the rest are "deferred" and are offered again on a later call
  dagkit.py release  --run RUN --step ID     give back a claim whose sub-agent never started (a failed launch)
  dagkit.py run      --run RUN --step ID     refuses (exit 3) a premature, repeated, unknown or unsound-input start;
                                             else works, then logs end (or fail for an injected fault)
  dagkit.py begin    --run RUN --step ID     task steps (README Amendment A5): refuses like run; else logs start and prints the
                                             step's task and the exact complete command; a fresh agent does the work in between
  dagkit.py complete --run RUN --step ID --result JSON
                                             the callback: records the agent's outcome ({"answer": integer, ...}) and logs end
  dagkit.py outcome  --run RUN --step ID     prints a completed step's result, so a dependent step reads it from the script
  dagkit.py verify   --run RUN               VERIFY OK | PARTIAL | FAIL, from the ledger, the plan and the hash chain
  dagkit.py timeline --run RUN               the ledger in order, with seconds from the first event

Write plans (README Amendment A10): with --repo and --workspace the task steps edit files in a git repository. ``shared`` hands every
task the repository itself. ``isolated`` gives each attempt of each task its own git worktree on its own branch (created by ``begin``,
committed by ``complete``, which refuses an empty change and notes any file outside the task's declared ``paths``); ``ready`` first
merges every completed branch into main in completion order, so a dependent task starts only from merged work. A merge that conflicts is
aborted and logged and the task is offered again from the updated main (a retry), at most MAX_ATTEMPTS attempts, then it fails (mergefail).
Events: workspace, commit, merged, conflict, retry, mergefail.

A step's work is a sleep of the step's declared seconds, then an output file whose hash chains the hashes of the
steps it depends on, so a step that ran on a missing or stale input cannot produce a valid chain; ``run`` reads each
predecessor's output file and refuses to start when it does not match the ledger. ``PPE_TIME_SCALE`` (tests only) scales
the sleeps and is written into every start event, so a scaled trial is never mistaken for a live one. Exit codes: 0 done,
1 a step failed (an injected fault) or verify failed, 2 verify partial, 3 refused. Every refusal is logged with a
``category``: premature, duplicate, unknown, prerequisite-failed or input-invalid.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCALE = float(os.environ.get("PPE_TIME_SCALE", "1"))
SCHEMA = "ppe-ledger/v1"
MAX_ATTEMPTS = 3
GIT = ["git", "-c", "user.name=ppe", "-c", "user.email=ppe@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]


def _at(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + f".{int((ts % 1) * 1000):03d}Z"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _git(cwd, *args) -> tuple[int, str]:
    done = subprocess.run(GIT + ["-C", str(cwd)] + list(args), capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


class Run:
    """One run directory: plan.json, meta.json, ledger.jsonl, ledger.lock and out/."""

    def __init__(self, path):
        self.dir = Path(path)
        self.ledger = self.dir / "ledger.jsonl"
        self.lock = self.dir / "ledger.lock"

    def plan(self) -> dict:
        return json.loads((self.dir / "plan.json").read_text())

    def meta(self) -> dict:
        return json.loads((self.dir / "meta.json").read_text())

    def events(self) -> list[dict]:
        if not self.ledger.is_file():
            return []
        return [json.loads(line) for line in self.ledger.read_text().splitlines() if line.strip()]

    @contextlib.contextmanager
    def locked(self):
        with open(self.lock, "a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def append(self, kind: str, step: str | None = None, **detail) -> dict:
        """Append one event; call only while holding ``locked()`` so ``seq`` is a total order."""
        ts = time.time()
        event = {"seq": len(self.events()) + 1, "ts": round(ts, 3), "at": _at(ts), "kind": kind, "step": step,
                 "pid": os.getpid(), "ppid": os.getppid(), "detail": detail}
        with open(self.ledger, "a") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event


def out_hash(plan_sha: str, step: str, inputs: dict) -> str:
    return _sha(f"{plan_sha}|{step}|{json.dumps(inputs, sort_keys=True)}")


def derive(plan: dict, events: list[dict]) -> dict:
    """The state of every step from the ledger alone."""
    state = {s["id"]: {"state": "pending", "claimed": False, "claim_ts": None, "starts": 0, "terminals": 0, "start": None,
                       "end": None, "start_seq": None, "end_seq": None, "sha": None, "attempt": 1, "merged": False, "conflicts": 0}
             for s in plan["steps"]}
    for event in events:
        step = event.get("step")
        if step not in state:
            continue
        item, kind = state[step], event["kind"]
        if kind == "claim":
            item["claimed"], item["claim_ts"] = True, event["ts"]
        elif kind == "release":
            item["claimed"], item["claim_ts"] = False, None
        elif kind == "start":
            item["starts"] += 1
            if item["start"] is None:
                item["start"], item["start_seq"] = event["ts"], event["seq"]
            if item["state"] == "pending":
                item["state"] = "running"
        elif kind == "end":
            item.update(state="done", end=event["ts"], end_seq=event["seq"], sha=event["detail"].get("sha"))
            item["terminals"] += 1
        elif kind == "fail":
            item.update(state="failed", end=event["ts"], end_seq=event["seq"])
            item["terminals"] += 1
        elif kind == "mergefail":   # the attempts are used up: the step's completed work could not be merged (no second terminal event)
            item.update(state="failed", end=event["ts"], end_seq=event["seq"])
        elif kind == "merged":
            item["merged"] = True
        elif kind == "conflict":
            item["conflicts"] += 1
        elif kind == "retry":   # a conflicting attempt is forgotten: the step is offered again, from a clean state, as the next attempt
            item.update(state="pending", claimed=False, claim_ts=None, starts=0, terminals=0, start=None, end=None, start_seq=None, end_seq=None,
                        sha=None, merged=False)
            item["attempt"] += 1
    for s in plan["steps"]:  # deps name earlier steps only, so one pass settles the blocked ones
        if state[s["id"]]["state"] == "pending" and any(state[d]["state"] in ("failed", "blocked") for d in s["deps"]):
            state[s["id"]]["state"] = "blocked"
    return state


def classify(plan: dict, state: dict, capacity: int | None = None, require_merged: bool = False) -> dict:
    """Groups of steps; ``capacity`` limits how many ready steps are offered (None offers them all); ``require_merged`` (isolated write
    runs) makes a dependent wait for its dependencies' branches to be merged, not just completed."""
    groups = {name: [] for name in ("ready", "deferred", "claimed", "running", "done", "failed", "blocked", "waiting")}
    offered = []
    for s in plan["steps"]:
        item = state[s["id"]]
        if item["state"] == "done":
            groups["done"].append(s["id"])
        elif item["state"] in ("failed", "running", "blocked"):
            groups[item["state"]].append(s["id"])
        elif item["claimed"]:
            groups["claimed"].append(s["id"])
        elif all(state[d]["state"] == "done" and (state[d]["merged"] or not require_merged) for d in s["deps"]):
            offered.append(s["id"])
        else:
            groups["waiting"].append(s["id"])
    slots = len(offered) if capacity is None else max(0, capacity - len(groups["claimed"]) - len(groups["running"]))
    groups["ready"], groups["deferred"] = offered[:slots], offered[slots:]
    groups["complete"] = not (groups["ready"] or groups["deferred"] or groups["claimed"] or groups["running"] or groups["waiting"]
                              or (require_merged and not all(state[i]["merged"] for i in groups["done"])))
    return groups


def check_plan(plan: dict) -> None:
    seen: set = set()
    for s in plan["steps"]:
        if s["id"] in seen or any(d not in seen for d in s["deps"]):
            raise SystemExit(f"plan invalid at {s['id']}: ids must be unique and deps must name earlier steps")
        kit = s.get("kit", {})
        if kit.get("mode") != "task" and not isinstance(kit.get("seconds"), (int, float)):
            raise SystemExit(f"plan invalid at {s['id']}: kit.seconds is required (or kit.mode \"task\")")
        seen.add(s["id"])


def cmd_init(args) -> int:
    run = Run(args.run)
    plan_text = Path(args.plan).read_text()
    plan = json.loads(plan_text)
    check_plan(plan)
    if bool(args.repo) != bool(args.workspace):
        raise SystemExit("--repo and --workspace go together")
    if args.repo and not (Path(args.repo) / ".git").exists():
        raise SystemExit(f"--repo {args.repo} is not a git repository")
    run.dir.mkdir(parents=True, exist_ok=False)
    (run.dir / "out").mkdir()
    (run.dir / "plan.json").write_text(plan_text)
    meta = {"schema": SCHEMA, "plan_sha": _sha(plan_text), "plan": plan.get("name"), "scale": SCALE, "settle": float(args.settle or 0)}
    if args.repo:
        meta.update(repo=str(Path(args.repo).resolve()), workspace=args.workspace, max_attempts=MAX_ATTEMPTS)
    (run.dir / "meta.json").write_text(json.dumps(meta, indent=1))
    with run.locked():
        run.append("init", None, plan=plan.get("name"), steps=[s["id"] for s in plan["steps"]], scale=SCALE, settle=float(args.settle or 0),
                   workspace=args.workspace, repo=meta.get("repo"))
    print(f"INIT {plan.get('name')} steps={len(plan['steps'])} run={run.dir}")
    return 0


def _workspace_of(run: Run, step_id: str) -> dict | None:
    """The latest workspace event of a step: {path, branch, base, mode, attempt, seconds}."""
    found = [e["detail"] for e in run.events() if e["kind"] == "workspace" and e["step"] == step_id]
    return found[-1] if found else None


def _merge_pending(run: Run, plan: dict, meta: dict) -> tuple[list, list]:
    """Under the lock: merge each completed, unmerged step's branch into main, in completion order. A conflict is aborted and logged, and the
    step is offered again (retry) or, after MAX_ATTEMPTS, fails. Returns (the steps merged, the steps that conflicted) of this call."""
    repo = Path(meta["repo"])
    merged_now, conflicted_now = [], []
    while True:
        state = derive(plan, run.events())
        todo = sorted((i for i in state if state[i]["state"] == "done" and not state[i]["merged"]), key=lambda i: state[i]["end_seq"])
        if not todo:
            return merged_now, conflicted_now
        step = todo[0]
        ws = _workspace_of(run, step)
        began = time.time()
        rc, _ = _git(repo, "merge", "--no-ff", "--no-edit", "-m", f"merge {step}", ws["branch"])
        seconds = round(time.time() - began, 3)
        if rc == 0:
            run.append("merged", step, seconds=seconds, branch=ws["branch"], attempt=state[step]["attempt"])
            merged_now.append(step)
            continue
        _, names = _git(repo, "diff", "--name-only", "--diff-filter=U")
        paths = sorted(n for n in names.split() if n)
        _git(repo, "merge", "--abort")
        run.append("conflict", step, paths=paths, seconds=seconds, attempt=state[step]["attempt"], branch=ws["branch"])
        conflicted_now.append(step)
        if state[step]["attempt"] < meta.get("max_attempts", MAX_ATTEMPTS):
            run.append("retry", step, attempt=state[step]["attempt"] + 1, reason="merge conflict in " + ", ".join(paths))
        else:
            run.append("mergefail", step, reason=f"merge conflict after {state[step]['attempt']} attempts in " + ", ".join(paths))


def cmd_ready(args) -> int:
    run = Run(args.run)
    with run.locked():
        plan, meta = run.plan(), run.meta()
        isolated = meta.get("workspace") == "isolated"
        merged_now, conflicted_now = _merge_pending(run, plan, meta) if isolated else ([], [])
        state = derive(plan, run.events())
        groups = classify(plan, state, args.capacity if args.claim else None, require_merged=isolated)
        now = time.time()
        if args.claim:
            for step in groups["ready"]:
                run.append("claim", step)
        printed = {key: groups[key] for key in ("ready", "deferred", "claimed", "running", "done", "failed", "blocked", "waiting")}
        printed["complete"] = groups["complete"]
        printed["capacity"] = args.capacity if args.claim else None
        printed["claimed_age_s"] = {i: round(now - state[i]["claim_ts"], 1) for i in groups["claimed"] if state[i]["claim_ts"]}
        if isolated:
            printed["merged_now"], printed["conflicted_now"] = merged_now, conflicted_now
        run.append("ready", None, result=printed, claim=bool(args.claim))
    print(json.dumps(printed, separators=(",", ":")))
    return 0


def cmd_release(args) -> int:
    run = Run(args.run)
    with run.locked():
        plan = run.plan()
        state = derive(plan, run.events())
        item = state.get(args.step)
        if item is None or not item["claimed"] or item["starts"]:
            reason = "unknown step" if item is None else "it is not a claim that never started"
            run.append("refused", args.step, reason=reason, command="release", category="unknown" if item is None else "duplicate")
            print(f"NOT RELEASED {args.step}: {reason}")
            return 3
        run.append("release", args.step)
    print(f"RELEASED {args.step}")
    return 0


def _refuse(run: Run, step_id: str, category: str, reasons: list, command: str = "run") -> int:
    run.append("refused", step_id, reason="; ".join(reasons), command=command, category=category)
    print(f"REFUSED {step_id}: " + "; ".join(reasons))
    return 3


def _admit(run: Run, plan: dict, step_id: str, command: str):
    """Under the lock: ((step, inputs), None) when the step may start now, else (None, exit code) after logging the refusal."""
    steps = {s["id"]: s for s in plan["steps"]}
    if step_id not in steps:
        return None, _refuse(run, step_id, "unknown", ["not a step of this plan"], command)
    step = steps[step_id]
    is_task = step.get("kit", {}).get("mode") == "task"
    if is_task != (command == "begin"):
        return None, _refuse(run, step_id, "wrong-command",
                             ["this step is a task: use begin and complete" if is_task else "this step is a timed unit: use run"], command)
    state = derive(plan, run.events())
    if state[step_id]["starts"]:
        return None, _refuse(run, step_id, "duplicate", ["it already started; each step runs once"], command)
    need_merged = run.meta().get("workspace") == "isolated"
    unfinished = [d for d in step["deps"] if state[d]["state"] != "done" or (need_merged and not state[d]["merged"])]
    if unfinished:
        category = "prerequisite-failed" if any(state[d]["state"] in ("failed", "blocked") for d in unfinished) else "premature"
        return None, _refuse(run, step_id, category, ["its dependencies have not finished OK: "
                                                      + ", ".join(f"{d} ({state[d]['state']}{'' if state[d]['merged'] or not need_merged else ', not merged'})" for d in unfinished)], command)
    inputs = {d: state[d]["sha"] for d in step["deps"]}
    for d, sha in inputs.items():
        target = run.dir / "out" / f"{d}.json"
        written = json.loads(target.read_text()).get("sha") if target.is_file() else None
        if written != sha:
            return None, _refuse(run, step_id, "input-invalid", [f"the output file of {d} does not match the ledger"], command)
    return (step, inputs), None


def cmd_run(args) -> int:
    run, step_id = Run(args.run), args.step
    with run.locked():
        plan, meta = run.plan(), run.meta()
        admitted, code = _admit(run, plan, step_id, "run")
        if code is not None:
            return code
        step, inputs = admitted
        run.append("start", step_id, deps=inputs, seconds=step["kit"]["seconds"], scale=SCALE)
    began = time.time()
    time.sleep(step["kit"]["seconds"] * SCALE)
    actual = round(time.time() - began, 3)
    if step["kit"].get("fail"):
        with run.locked():
            run.append("fail", step_id, reason="injected failure", seconds=actual)
        print(f"STEP {step_id} FAILED (injected failure); steps that depend on it must not run")
        return 1
    sha = out_hash(meta["plan_sha"], step_id, inputs)
    target = run.dir / "out" / f"{step_id}.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps({"step": step_id, "inputs": inputs, "sha": sha}))
    os.replace(tmp, target)
    with run.locked():
        run.append("end", step_id, sha=sha, seconds=actual)
    print(f"STEP {step_id} OK sha={sha[:12]} seconds={actual} (finished; do not run it again)")
    return 0


def _open_workspace(run: Run, meta: dict, step_id: str, attempt: int) -> Path:
    repo = Path(meta["repo"])
    began = time.time()
    if meta["workspace"] == "shared":
        run.append("workspace", step_id, path=str(repo), branch=None, base=None, mode="shared", seconds=0.0, attempt=attempt)
        return repo
    path = run.dir.parent / "ws" / f"{step_id}-{attempt}"
    branch = f"w-{step_id}-{attempt}"
    base = _git(repo, "rev-parse", "HEAD")[1].strip()
    rc, out = _git(repo, "worktree", "add", "-q", "-b", branch, str(path), base)
    if rc != 0:
        raise SystemExit(f"the workspace of {step_id} could not be created: {out.strip()}")
    run.append("workspace", step_id, path=str(path), branch=branch, base=base, mode="isolated", seconds=round(time.time() - began, 3), attempt=attempt)
    return path


def _close_workspace(run: Run, meta: dict, step: dict, step_id: str):
    """Under the lock, at complete: (category, reasons) to refuse, or None after logging the commit event."""
    ws = _workspace_of(run, step_id)
    if ws is None:
        return "not-started", ["no workspace was opened for this step"]
    declared = list(step.get("paths", []))
    if ws["mode"] == "shared":
        missing = [p for p in declared if not (Path(meta["repo"]) / p).exists()]
        if missing:
            return "missing-output", ["declared files are missing: " + ", ".join(missing)]
        run.append("commit", step_id, mode="shared", files=declared, scope_notes=[], seconds=0.0, attempt=ws["attempt"])
        return None
    began = time.time()
    path = Path(ws["path"])
    _git(path, "add", "-A")
    rc, _ = _git(path, "commit", "-q", "-m", f"{step_id} attempt {ws['attempt']}")
    if rc != 0:
        return "empty", ["there is nothing to commit: a write task must change files in its workspace"]
    files = sorted(n for n in _git(path, "diff", "--name-only", ws["base"], "HEAD")[1].split() if n)
    run.append("commit", step_id, mode="isolated", files=files, scope_notes=[f for f in files if f not in declared],
               seconds=round(time.time() - began, 3), attempt=ws["attempt"])
    return None


def cmd_begin(args) -> int:
    run, step_id = Run(args.run), args.step
    note, ws_path = "", None
    with run.locked():
        plan, meta = run.plan(), run.meta()
        admitted, code = _admit(run, plan, step_id, "begin")
        if code is not None:
            return code
        step, inputs = admitted
        run.append("start", step_id, deps=inputs, mode="task", scale=SCALE)
        if meta.get("workspace"):
            attempt = derive(plan, run.events())[step_id]["attempt"]
            ws_path = _open_workspace(run, meta, step_id, attempt)
            if attempt > 1:
                last = [e for e in run.events() if e["kind"] == "conflict" and e["step"] == step_id][-1]
                note = ("\n\nNOTE: an earlier attempt of this task conflicted with work that was already merged, in: " + ", ".join(last["detail"]["paths"])
                        + ". Your workspace already contains everything merged so far: keep what is there and make your change on top of it.")
    kit = str(Path(__file__).resolve())
    text = (step["task"].replace("{evidence}", str(run.dir.parent / "evidence")).replace("{run}", str(run.dir)).replace("{kit}", kit)
            .replace("{ws}", str(ws_path or "")) + note)
    settle = run.meta().get("settle", 0)
    if settle:
        text += (f"\n\nBefore you report, run this command: it stands for the project's slow verification, takes about {settle:g} seconds, "
                 f"and you must let it finish and not skip it:\n  python3 {kit} settle --run {run.dir} --step {step_id}")
    ws_line = f"\n\nWorkspace (work only inside it): {ws_path}" if ws_path else ""
    print(f"STEP {step_id} BEGUN. You are a fresh agent; this is your whole task. Do only this.\n\n{text}{ws_line}\n\n"
          "When you have the answer, report it by running exactly this command, with your integer in place of N and one short "
          "line in place of METHOD:\n"
          f"  python3 {kit} complete --run {run.dir} --step {step_id} --result '{{\"answer\": N, \"method\": \"METHOD\"}}'\n"
          "Then reply with the one line that command prints. Do not run begin again.")
    return 0


def cmd_complete(args) -> int:
    run, step_id = Run(args.run), args.step
    try:
        result = json.loads(args.result)
    except ValueError:
        result = None
    with run.locked():
        plan, meta = run.plan(), run.meta()
        steps = {s["id"]: s for s in plan["steps"]}
        if step_id not in steps:
            return _refuse(run, step_id, "unknown", ["not a step of this plan"], "complete")
        item = derive(plan, run.events())[step_id]
        if not item["starts"]:
            return _refuse(run, step_id, "not-started", ["it was never begun"], "complete")
        if item["terminals"]:
            return _refuse(run, step_id, "duplicate", ["it already has its outcome"], "complete")
        if meta.get("settle") and not any(e["kind"] == "settled" and e["step"] == step_id for e in run.events()):
            return _refuse(run, step_id, "not-settled", [f"run the settle command first and let it finish: python3 {Path(__file__).resolve()} settle --run {run.dir} --step {step_id}"], "complete")
        if not isinstance(result, dict) or not isinstance(result.get("answer"), int) or isinstance(result.get("answer"), bool):
            return _refuse(run, step_id, "bad-result", ["the result must be a JSON object with an integer answer"], "complete")
        if meta.get("workspace"):
            refusal = _close_workspace(run, meta, steps[step_id], step_id)
            if refusal:
                return _refuse(run, step_id, refusal[0], refusal[1], "complete")
        state = derive(plan, run.events())
        inputs = {d: state[d]["sha"] for d in steps[step_id]["deps"]}
        sha = out_hash(meta["plan_sha"], step_id, {**inputs, "_result": result})
        target = run.dir / "out" / f"{step_id}.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps({"step": step_id, "inputs": inputs, "result": result, "sha": sha}))
        os.replace(tmp, target)
        run.append("end", step_id, sha=sha, result=result)
    print(f"RECORDED {step_id} answer={result['answer']} (finished; do not report it again)")
    return 0


def cmd_settle(args) -> int:
    run, step_id = Run(args.run), args.step
    with run.locked():
        plan, meta = run.plan(), run.meta()
        steps = {s["id"]: s for s in plan["steps"]}
        if step_id not in steps:
            return _refuse(run, step_id, "unknown", ["not a step of this plan"], "settle")
        item = derive(plan, run.events())[step_id]
        done = [e for e in run.events() if e["kind"] == "settled" and e["step"] == step_id]
        if not item["starts"] or item["terminals"]:
            return _refuse(run, step_id, "not-started", ["settle runs between begin and complete"], "settle")
        if done:
            return _refuse(run, step_id, "duplicate", ["it already settled"], "settle")
        seconds = float(meta.get("settle", 0))
        run.append("settle", step_id, seconds=seconds, scale=SCALE)
    time.sleep(seconds * SCALE)
    with run.locked():
        run.append("settled", step_id, seconds=seconds, scale=SCALE)
    print(f"SETTLED {step_id} after {seconds:g} s; now report your outcome")
    return 0


def cmd_outcome(args) -> int:
    run, step_id = Run(args.run), args.step
    with run.locked():
        plan = run.plan()
        state = derive(plan, run.events())
        if step_id not in state or state[step_id]["state"] != "done":
            return _refuse(run, step_id, "premature", [f"{step_id} has no outcome yet"], "outcome")
        rec = json.loads((run.dir / "out" / f"{step_id}.json").read_text())
    print(json.dumps({"step": step_id, "result": rec.get("result")}, separators=(",", ":")))
    return 0


def verdict(run: Run) -> tuple[str, str]:
    """(OK|PARTIAL|FAIL, the one line) recomputed from one consistent snapshot of the ledger, the plan and the outputs."""
    with run.locked():
        plan_text = (run.dir / "plan.json").read_text()
        meta, events = run.meta(), run.events()
        outputs = {p.stem: p.read_text() for p in (run.dir / "out").glob("*.json")}
    plan = json.loads(plan_text)
    state = derive(plan, events)
    problems = []
    if _sha(plan_text) != meta["plan_sha"]:
        problems.append("plan.json changed since init")
    for s in plan["steps"]:
        step, item = s["id"], state[s["id"]]
        if item["starts"] > 1:
            problems.append(f"{step} started {item['starts']} times")
        if item["terminals"] > 1:
            problems.append(f"{step} has {item['terminals']} terminal events")
        if item["starts"] == 0 and item["terminals"]:
            problems.append(f"{step} ended without a start")
        if item["state"] == "running":
            problems.append(f"{step} started and never ended")
        for d in s["deps"]:
            if item["start_seq"] is None:
                continue
            if state[d]["end_seq"] is None or item["start_seq"] < state[d]["end_seq"]:
                problems.append(f"{step} started before {d} ended")
            elif state[d]["state"] != "done":
                problems.append(f"{step} started after {d}, which did not end OK")
        if item["state"] == "done":
            record = json.loads(outputs[step]) if step in outputs else {}
            inputs = {d: state[d]["sha"] for d in s["deps"]}
            expect = out_hash(meta["plan_sha"], step, {**inputs, "_result": record.get("result")} if s.get("kit", {}).get("mode") == "task" else inputs)
            written = record.get("sha")
            if written != expect or item["sha"] != expect:
                problems.append(f"{step} output does not chain from its dependencies")
    if meta.get("repo"):
        for s in plan["steps"]:
            if state[s["id"]]["state"] != "done":
                continue
            if meta.get("workspace") == "isolated" and not state[s["id"]]["merged"]:
                problems.append(f"{s['id']} completed but was never merged")
            for declared in s.get("paths", []):
                if not (Path(meta["repo"]) / declared).exists():
                    problems.append(f"{s['id']}: the declared file {declared} is missing from the final tree")
    ok = [s["id"] for s in plan["steps"] if state[s["id"]]["state"] == "done"]
    failed = [s["id"] for s in plan["steps"] if state[s["id"]]["state"] == "failed"]
    not_run = [s["id"] for s in plan["steps"] if state[s["id"]]["state"] in ("blocked", "pending")]
    if problems:
        return "FAIL", "VERIFY FAIL " + "; ".join(problems)
    if len(ok) == len(plan["steps"]):
        root = _sha("|".join(state[s["id"]]["sha"] for s in plan["steps"]))[:12]
        return "OK", f"VERIFY OK steps={len(ok)} chain={root}"
    return "PARTIAL", "VERIFY PARTIAL ok=" + ",".join(ok) + " failed=" + ",".join(failed) + " not_run=" + ",".join(not_run)


def cmd_verify(args) -> int:
    run = Run(args.run)
    kind, line = verdict(run)
    with run.locked():
        run.append("verify", None, verdict=kind, line=line)
    print(line)
    return {"OK": 0, "PARTIAL": 2, "FAIL": 1}[kind]


def cmd_timeline(args) -> int:
    events = Run(args.run).events()
    t0 = events[0]["ts"] if events else 0.0
    for e in events:
        extra = {k: v for k, v in e["detail"].items() if k in ("reason", "sha", "seconds", "line", "deps", "category", "paths", "scope_notes", "branch", "attempt") or k == "result"}
        print(f"+{e['ts'] - t0:8.3f}s  #{e['seq']:<3} {e['kind']:<8} {e['step'] or '-':<4} pid={e['pid']} {json.dumps(extra, separators=(',', ':')) if extra else ''}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("init", cmd_init), ("ready", cmd_ready), ("release", cmd_release), ("run", cmd_run), ("begin", cmd_begin),
                     ("complete", cmd_complete), ("outcome", cmd_outcome), ("settle", cmd_settle), ("verify", cmd_verify),
                     ("timeline", cmd_timeline)):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True)
        if name == "init":
            p.add_argument("--plan", required=True)
            p.add_argument("--settle", type=float, default=0.0)
            p.add_argument("--repo")
            p.add_argument("--workspace", choices=("shared", "isolated"))
        if name == "ready":
            p.add_argument("--claim", action="store_true")
            p.add_argument("--capacity", type=int, default=None)
        if name in ("run", "release", "begin", "complete", "outcome", "settle"):
            p.add_argument("--step", required=True)
        if name == "complete":
            p.add_argument("--result", required=True)
        p.set_defaults(fn=fn)
    args = parser.parse_args(argv)
    if args.cmd == "ready" and args.capacity is not None and not args.claim:
        parser.error("--capacity applies with --claim")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
