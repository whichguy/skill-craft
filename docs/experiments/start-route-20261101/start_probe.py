#!/usr/bin/env python3
"""Start-route probe, driven through the E2E harness: which ShipLoop start command does a fresh Codex session run first?

Each trial is one `test/shiploop_e2e/run.py` run on the harness's Codex host (gpt-6.1-terra, xhigh: owner, 2026-11-01),
with one plugin build (an arm: the published package, or the package with one wording edit in the skill card, passed as
--plugin-dir) and one request (a --prompt or a --case). The harness builds the throwaway profile, installs the plugin,
runs `codex exec`, and records the run folder as for any E2E run. This driver only watches the run's events.jsonl and,
the moment the model issues its first ShipLoop start command (`workspace start`, the isolated entry, or `init`, the
direct entry), creates <run>/stop, the harness's own way to end a host on purpose. That command is the outcome, so no
run is built and nothing else is attempted. No platform is declared, so no org is touched: the profile holds no login.

    python3 -I start_probe.py plan  --out plan.json
    python3 -I start_probe.py smoke --arm C --stimulus sf-ui --out DIR     # one unscored trial, printed in full
    python3 -I start_probe.py run   --plan plan.json --out DIR --jobs 4    # scored; resumes from DIR/results.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN_PY = ROOT / "test" / "shiploop_e2e" / "run.py"

# The harness's own defaults for each host (hosts.py); --host picks one. Claude runs on its own models (--backend anthropic),
# never the Ollama default.
HOSTS = {"codex": {"model": "gpt-6.1-terra", "effort": "xhigh", "args": []},
         "claude": {"model": "claude-sonnet-5-5", "effort": None, "args": ["--backend", "anthropic"]},
         "grok": {"model": "grok-4.7", "effort": "medium", "args": []}}
HOST = "codex"
MODEL, EFFORT = HOSTS[HOST]["model"], HOSTS[HOST]["effort"]


def use_host(name: str) -> None:
    global HOST, MODEL, EFFORT
    HOST, MODEL, EFFORT = name, HOSTS[name]["model"], HOSTS[name]["effort"]


HOST_TIMEOUT_SECONDS = 240   # the harness ends a host that never starts ShipLoop; the driver's own stop usually comes first
HARD_LIMIT_SECONDS = 420     # the driver kills a run folder's process group when the harness itself has not exited
STOP_GRACE_SECONDS = 120     # after the stop file, the harness is given this long to write its records
MAX_INVALID_STREAK = 6        # invalid attempts in a row that stop the whole batch
MAX_ATTEMPTS = 3             # a slot is retried only when its trial was invalid (infrastructure), never for its outcome
ARMS = ("C", "T1", "T2", "GOLD", "G")
# stimulus -> selector for run.py. sf-ui is the prompt of the failing run, byte for byte; hello is the smoke case (an empty
# directory, no "current directory" wording); repo is a brownfield case that declares no port (an existing Git repository;
# user-listing was the first choice and was dropped: it leases the machine-wide port 3000). The last three ask for an
# in-place or non-Git run explicitly, where `init` is the right first command (stimuli/*.txt).
SELECTORS = {"sf-ui": ["--prompt-file"], "hello": ["--case", "hello"], "repo": ["--case", "ticket-assignment-tests"],
             "inplace-hello": ["--prompt-file"], "nogit-hello": ["--prompt-file"], "inplace-sf": ["--prompt-file"]}
# a plan set: which cards run, and how many sessions per card for each request
PLAN_SETS = {"start": {"arms": ("C", "T1", "T2"), "counts": {"sf-ui": 40, "hello": 10, "repo": 10}},
             "inplace": {"arms": ("C", "T2"), "counts": {"inplace-hello": 16, "nogit-hello": 16, "inplace-sf": 16}},
             "hosts": {"arms": ("C", "T2"), "counts": {"sf-ui": 16, "repo": 8, "inplace-hello": 12, "nogit-hello": 12}},
             # the guard probe: what a session does after `init` is refused in an empty non-Git folder (a dict gives each arm its own count)
             "guard": {"arms": ("GOLD", "G"), "counts": {"sf-ui": {"GOLD": 60, "G": 20}, "inplace-hello": {"G": 12},
                                                         "nogit-hello": {"G": 12}}}}
SEED = 20261101
ARMS_FILE = HERE / "arms.json"   # --arms picks another; the replication uses arms-r2.json
PACKAGE_ROOT = ROOT              # --package-root: where the plugin package and marketplace file the arms are cut from live
EFFECT_STOP = False              # --effect-stop: the harness ends the host once a run exists (--stop-after-start); route read from disk
REFUSED = re.compile(r"blocked: /[^\"]*? is an empty folder that is not a Git repository")   # the guard's refusal, as rendered

# A start is the ShipLoop CLI invoked with the verb `workspace start` or `init`, written as a shell command, with the
# CLI in a variable, or as a Python subprocess argument list. A reader command that mentions the words is not a start.
SHELL_START = re.compile(r"(?:scripts/shiploop|\$\{?CLI\}?)['\"]?\s+(workspace\s+start|init)\b")
# In a python -c one-liner inside a double-quoted shell command the quotes arrive backslash-escaped (\"workspace\",\"start\").
PY_START = re.compile(r"""\[[^\]]*?\\*['"](workspace\\*['"]\s*,\s*\\*['"]start|init)\\*['"]""", re.DOTALL)
BOOTSTRAP = re.compile(r"\bgit\s+(init|config|commit)\b")
PLUGIN_PATH = "plugins/cache/whichguy/skill-craft"


def detect_start(cmd: str) -> str | None:
    """`workspace` for the isolated entry, `direct` for init, None when the command is not a ShipLoop start."""
    if "shiploop" not in cmd or ("--repo" not in cmd and "--prompt" not in cmd):
        return None   # `init --help` and `workspace start --help` read the verb; a start carries the repository or the request
    match = SHELL_START.search(cmd)
    if match is None and "scripts/shiploop" in cmd and ("subprocess" in cmd or "execv" in cmd):
        match = PY_START.search(cmd)
    if match is None:
        return None
    return "workspace" if match.group(1).startswith("workspace") else "direct"


def make_plan(seed: int = SEED, plan_set: str = "start") -> list[dict]:
    chosen = PLAN_SETS[plan_set]
    slots = []
    for stimulus, count in chosen["counts"].items():
        per_arm = count if isinstance(count, dict) else {arm: count for arm in chosen["arms"]}
        slots += [{"stimulus": stimulus, "arm": a, "i": i} for a, n in per_arm.items() for i in range(1, n + 1)]
    random.Random(seed).shuffle(slots)
    for number, slot in enumerate(slots, 1):
        slot["slot"] = number
    return slots


def build_arm(arm: str, edits: list, dest: Path) -> str:
    """A marketplace root holding the repository's published plugin package with the arm's exact text edits."""
    if dest.exists():
        shutil.rmtree(dest)
    (dest / ".agents" / "plugins").mkdir(parents=True)
    shutil.copy2(PACKAGE_ROOT / ".agents" / "plugins" / "marketplace.json", dest / ".agents" / "plugins" / "marketplace.json")
    shutil.copytree(PACKAGE_ROOT / "plugins" / "skill-craft", dest / "plugins" / "skill-craft", symlinks=True)
    card = dest / "plugins" / "skill-craft" / "skills" / "shiploop" / "SKILL.md"
    text = card.read_text()
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"arm {arm}: the text to replace occurs {text.count(old)} times, not once")
        text = text.replace(old, new)
    card.write_text(text)
    git = ["git", "-c", "user.name=probe", "-c", "user.email=probe@example.invalid"]
    subprocess.run(git + ["init", "-q", "-b", "main"], cwd=dest, check=True)
    subprocess.run(git + ["add", "-A"], cwd=dest, check=True)
    subprocess.run(git + ["commit", "-q", "-m", f"probe arm {arm}"], cwd=dest, check=True)
    return hashlib.sha256(card.read_bytes()).hexdigest()[:12]


def commands_of(event: dict) -> list[str]:
    """The shell commands an event carries: a tool_call event (Grok's stream, and Codex's translated into it) holds one, a
    Claude assistant event holds one per Bash tool_use block."""
    if event.get("type") == "tool_call":
        command = (event.get("rawInput") or {}).get("command")
        if isinstance(command, list):
            command = " ".join(map(str, command))
        return [command] if isinstance(command, str) else []
    if event.get("type") == "assistant":
        blocks = (event.get("message") or {}).get("content") or []
        return [blk["input"]["command"] for blk in blocks
                if isinstance(blk, dict) and blk.get("type") == "tool_use" and isinstance((blk.get("input") or {}).get("command"), str)]
    return []


def scan(events_path: Path) -> dict:
    """Read a run's events.jsonl: the commands before the first start, and that start."""
    found: dict = {"start": "none", "start_command": None, "event_n": None, "commands": [], "messages": []}
    if not events_path.is_file():
        return found
    with events_path.open(errors="replace") as fh:
        for number, line in enumerate(fh, 1):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "text" and len(found["messages"]) < 4:
                found["messages"].append(str(event.get("data"))[:240])
            for command in commands_of(event):
                start = detect_start(command)
                if start:
                    found.update(start=start, start_command=command[:400], event_n=number)
                    return found
                found["commands"].append(command)
    return found


def starts_in(events_path: Path) -> dict:
    """Every ShipLoop start command of a session in order (route, and whether it carried --in-place), and whether the guard
    refused an `init` (its refusal as rendered, so a read of the source that holds the same words does not count)."""
    starts: list[dict] = []
    refused = False
    if events_path.is_file():
        with events_path.open(errors="replace") as fh:
            for line in fh:
                if REFUSED.search(line):
                    refused = True
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    for command in commands_of(event):
                        route = detect_start(command)
                        if route:
                            starts.append({"route": route, "in_place": "--in-place" in command})
    return {"starts": starts, "refused": refused}


def reap(trial: Path) -> None:
    """Kill anything still running that names the trial folder. A start command spawns a progress observer that can outlive
    the harness; the harness then refuses every later launch as long as such an orphan lives."""
    listing = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True, check=False).stdout
    for line in listing.splitlines():
        pid, _, command = line.strip().partition(" ")
        if str(trial) in command and pid.isdigit() and int(pid) != os.getpid():
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass


def stop_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except OSError:
        pass


def effects(trial: Path) -> dict:
    """What the start left on disk, read before the folders are removed: an independent check on the route read from the
    command. `workspace start` writes a workspace.md beside the run and turns an empty folder into a Git repository;
    `init` writes a state.md and does neither. Absent when the start command was stopped before it wrote anything."""
    def outside_home(found) -> list[str]:
        return sorted(str(f.relative_to(trial)) for f in found if "home" not in f.relative_to(trial).parts)

    workspace = outside_home(trial.rglob("workspace.md"))
    state = outside_home(trial.rglob("state.md"))
    route = "workspace" if workspace else "direct" if state else "none"
    return {"effect_route": route, "effect": {"work_is_git": (trial / "work" / ".git").exists(),
                                              "workspace_md": workspace[:2], "state_md": state[:2]}}


def installed_cards(trial: Path, result: dict) -> list[Path]:
    """The skill card the host loaded: Codex's plugin cache, Grok's installed plugins, or (Claude, which loads --plugin-dir in
    place) the plugin directory the harness recorded."""
    home = trial / "home"
    found = sorted((home / ".codex" / "plugins" / "cache" / "whichguy" / "skill-craft").glob("*/skills/shiploop/SKILL.md"))
    found += sorted((home / ".grok" / "installed-plugins").glob("skill-craft*/skills/shiploop/SKILL.md"))
    if not found:
        for loaded in (result.get("plugin") or {}).get("loaded") or []:
            card = Path(str(loaded).split()[-1]) / "skills" / "shiploop" / "SKILL.md"
            if card.is_file():
                found.append(card)
    return found


def run_trial(slot: dict, attempt: int, out: Path, expected: dict) -> dict:
    arm, stimulus = slot["arm"], slot["stimulus"]
    trial = out / "trials" / f"{slot['slot']:03d}-{arm}-{stimulus}-{slot['i']:02d}-a{attempt}"
    if trial.exists():
        shutil.rmtree(trial)
    trial.parent.mkdir(parents=True, exist_ok=True)
    row = {"slot": slot["slot"], "attempt": attempt, "stimulus": stimulus, "arm": arm, "i": slot["i"],
           "host": HOST, "model": MODEL, "effort": EFFORT, "start": "none", "end": None, "error": None, "valid": False,
           "card_sha256": expected["card_sha256"][arm], "pre_start": [], "start_command": None,
           "skill_seen": False, "read_run_start": False, "self_bootstrap": False,
           "start_dir": "git-repository" if stimulus == "repo" else "empty-not-git",
           "event_n": None, "seconds_to_start": None, "messages": [], "run_dir": str(trial)}
    selector = SELECTORS[stimulus]
    if selector == ["--prompt-file"]:
        selector = ["--prompt", (HERE / "stimuli" / f"{stimulus}.txt").read_text()]
    build = (["--source", "marketplace"] if arm == "PUB"   # the published build, as a user installs it
             else ["--plugin-dir", str(out / "arms" / arm / "root" / "plugins" / "skill-craft")])
    argv = [sys.executable, str(RUN_PY), *selector, "--host", HOST, "--model", MODEL,
            *(["--effort", EFFORT] if EFFORT else []), *HOSTS[HOST]["args"],
            *build, "--output", str(trial), *(["--stop-after-start"] if EFFECT_STOP else []),
            "--timeout", str(HOST_TIMEOUT_SECONDS), "--quiet", "--baseline", str(out / "baselines-probe.jsonl")]
    started = time.monotonic()
    proc = None
    try:
        log = (out / "trials" / f"{trial.name}.log").open("wb")
        # A brownfield case declares a fixed port, which the harness leases machine-wide, so another session's run holds
        # it and refuses ours. These trials end before the model has written anything, let alone served on that port,
        # so each gets a private lease folder (the harness's own SHIPLOOP_E2E_LEASES) and neither blocks nor is blocked.
        env = dict(os.environ)
        if stimulus == "repo":
            env["SHIPLOOP_E2E_LEASES"] = str(out / "leases" / trial.name)
        proc = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=env, start_new_session=True)
        stopped_at = None
        while proc.poll() is None:
            time.sleep(1.0)
            now = time.monotonic()
            if (not EFFECT_STOP and stopped_at is None and (trial / "events.jsonl").is_file()
                    and scan(trial / "events.jsonl")["start"] != "none"):
                row["seconds_to_start"] = round(now - started, 1)
                (trial / "stop").touch()
                stopped_at = now
            if (stopped_at is not None and now - stopped_at > STOP_GRACE_SECONDS) or now - started > HARD_LIMIT_SECONDS:
                stop_group(proc)
                row["driver_killed"] = True
                break
        proc.wait(timeout=20)
        found = scan(trial / "events.jsonl")
        row.update(start=found["start"], start_command=found["start_command"], event_n=found["event_n"],
                   messages=found["messages"])
        commands = found["commands"]
        row["pre_start"] = [c[:200] for c in commands[:14]]
        row["skill_seen"] = any(PLUGIN_PATH in c or "shiploop" in c for c in commands) or row["start"] != "none"
        row["read_run_start"] = any("run-start.md" in c for c in commands)
        row["self_bootstrap"] = any(BOOTSTRAP.search(c) for c in commands)
        try:
            invocation = json.loads((trial / "invocation.json").read_text())
            result = json.loads((trial / "result.json").read_text()) if (trial / "result.json").is_file() else {}
        except (OSError, ValueError) as exc:
            row["error"] = f"no run record: {exc}"
            return row
        if EFFECT_STOP:
            row.update(starts_in(trial / "events.jsonl"))
            row["final_route"] = result.get("start_route")   # read from the disk by the harness: workspace, direct, or None
        installed = installed_cards(trial, result)
        sha = hashlib.sha256(installed[0].read_bytes()).hexdigest()[:12] if len(installed) == 1 else None
        row["installed_card_sha256"] = sha
        row["host_record"] = [invocation.get("host"), invocation.get("model"), invocation.get("effort")]
        row["plugin_verdict"] = (result.get("plugin") or {}).get("pass")
        if row["host_record"] != [HOST, MODEL, EFFORT]:
            row["error"] = f"the harness ran {row['host_record']}"
        elif sha != expected["card_sha256"][arm]:
            row["error"] = f"the installed card ({sha}) is not the arm's card"
        elif row["start"] != "none":
            row["end"] = "start"
        elif row.get("driver_killed"):
            row["end"] = "killed"
        else:
            row["end"] = "timeout" if (result.get("process") or {}).get("status") == "timeout" else "turn-ended"
        row["valid"] = row["error"] is None and (row["start"] != "none" or (row["skill_seen"] and row["end"] is not None))
        return row
    except Exception as exc:  # noqa: BLE001  an infrastructure fault: the slot is retried, the fault is kept in the row
        row["error"] = f"{type(exc).__name__}: {exc}"[:300]
        return row
    finally:
        if proc is not None and proc.poll() is None:
            stop_group(proc)
        row["seconds"] = round(time.monotonic() - started, 1)
        time.sleep(2)   # let a start command that was running when the stop file appeared finish spawning
        reap(trial)
        row.update(effects(trial))
        for heavy in ("home", "work", "platform"):
            shutil.rmtree(trial / heavy, ignore_errors=True)
        trial.mkdir(parents=True, exist_ok=True)
        (trial / "trial.json").write_text(json.dumps(row, indent=1) + "\n")


def reclassify(out: Path) -> None:
    """Re-read every stored trial's events.jsonl with the current detector; a valid row whose start does not read the same
    is superseded by an invalid row (same attempt number), so the slot is run again. Nothing else in a row is rewritten."""
    results_path = out / "results.jsonl"
    rows = [json.loads(line) for line in results_path.read_text().splitlines() if line.strip()]
    last: dict[int, dict] = {}
    for row in rows:
        last[row["slot"]] = row
    changed = []
    for slot, row in sorted(last.items()):
        if not row["valid"] or row["start"] == "none":
            continue
        found = scan(Path(row["run_dir"]) / "events.jsonl")
        if (found["start"], found["event_n"]) != (row["start"], row["event_n"]):
            changed.append((slot, row["arm"], row["stimulus"], row["start"], found["start"]))
            with results_path.open("a") as fh:
                fh.write(json.dumps({**row, "valid": False, "start": "none", "superseded": True,
                                     "error": "superseded: the stored start was a help request, not a start"}) + "\n")
    print(f"{sum(r['valid'] and r['start'] != 'none' for r in last.values())} stored starts re-read; superseded: {changed or 'none'}")


def rescan(out: Path, apply: bool) -> None:
    """Re-read every valid trial's whole events.jsonl with the current detector. A row that read `none` but whose session
    did run a start (the session was never stopped, so it ran on to the timeout) is rewritten with that start; a row whose
    recorded start no longer matches is only reported. Without --apply nothing is written."""
    results_path = out / "results.jsonl"
    rows = [json.loads(line) for line in results_path.read_text().splitlines() if line.strip()]
    last: dict[int, dict] = {}
    for row in rows:
        last[row["slot"]] = row
    found_new, differ, same = [], [], 0
    for slot, row in sorted(last.items()):
        if not row["valid"]:
            continue
        found = scan(Path(row["run_dir"]) / "events.jsonl")
        if row["start"] == "none" and found["start"] != "none":
            found_new.append((slot, row["arm"], row["stimulus"], found["start"], found["event_n"]))
            if apply:
                with results_path.open("a") as fh:
                    fh.write(json.dumps({**row, "start": found["start"], "start_command": found["start_command"],
                                         "event_n": found["event_n"], "end": "start", "seconds_to_start": None,
                                         "rescanned": True}) + "\n")
        elif (found["start"], found["event_n"]) != (row["start"], row["event_n"]):
            differ.append((slot, row["arm"], row["stimulus"], row["start"], row["event_n"], found["start"], found["event_n"]))
        else:
            same += 1
    print(f"unchanged: {same}; none -> a start: {found_new or 'none'}; changed otherwise: {differ or 'none'}"
          + ("" if apply else "  (dry run: nothing written)"))


def run_confirm(out: Path, count: int, jobs: int) -> None:
    """Fresh published confirmation: the Salesforce request on the published marketplace build (arm PUB), no plugin-dir."""
    out.mkdir(parents=True, exist_ok=True)
    card = ROOT / "plugins" / "skill-craft" / "skills" / "shiploop" / "SKILL.md"
    expected = {"card_sha256": {"PUB": hashlib.sha256(card.read_bytes()).hexdigest()[:12]}}
    results_path = out / "confirm.jsonl"
    lock = threading.Lock()

    def work(i: int) -> None:
        slot = {"slot": i, "arm": "PUB", "stimulus": "sf-ui", "i": i}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            row = run_trial(slot, attempt, out, expected)
            with lock, results_path.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            print(f"confirm {i:2d} a{attempt} -> {row['start']:9s} valid={row['valid']} {row['seconds']}s {row['error'] or ''}",
                  flush=True)
            if row["valid"]:
                return

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(work, range(1, count + 1)))


def prepare(out: Path, wanted: tuple = ARMS) -> dict:
    arms = json.loads(ARMS_FILE.read_text())
    return {"card_sha256": {arm: build_arm(arm, arms[arm], out / "arms" / arm / "root") for arm in wanted}}


def run_all(plan: list[dict], out: Path, jobs: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    expected = prepare(out, tuple(sorted({s["arm"] for s in plan})))
    results_path = out / "results.jsonl"
    done: dict[int, int] = {}   # slot -> its highest attempt number, or 99 while its last row is valid
    if results_path.is_file():
        for line in results_path.read_text().splitlines():
            row = json.loads(line)
            done[row["slot"]] = 99 if row["valid"] else max(done.get(row["slot"], 0) % 99, row["attempt"])
    lock = threading.Lock()
    abort = threading.Event()
    streak = [0]   # consecutive invalid attempts; a fault the driver cannot absorb stops the run (fix it, restart clean)

    def work(slot: dict) -> None:
        first = done.get(slot["slot"], 0) + 1   # attempts are numbered across launches; each launch makes at most MAX_ATTEMPTS
        for attempt in range(first, first + MAX_ATTEMPTS):
            if abort.is_set():
                return
            row = run_trial(slot, attempt, out, expected)
            with lock, results_path.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
                streak[0] = 0 if row["valid"] else streak[0] + 1
                if streak[0] >= MAX_INVALID_STREAK:
                    abort.set()
            print(f"slot {slot['slot']:3d} {slot['arm']:2s} {slot['stimulus']:6s} a{attempt} -> {row['start']:9s} "
                  f"valid={row['valid']} {row['seconds']}s {row['error'] or ''}", flush=True)
            if row["valid"]:
                return

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(work, [s for s in plan if done.get(s["slot"], 0) < 99]))
    if abort.is_set():
        print(f"ABORTED: {MAX_INVALID_STREAK} invalid attempts in a row; fix the cause and restart the batch from scratch", flush=True)
        raise SystemExit(3)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--set", dest="plan_set", default="start", choices=tuple(PLAN_SETS))
    p = sub.add_parser("smoke")
    p.add_argument("--host", default="codex", choices=tuple(HOSTS))
    p.add_argument("--arms", default=None)
    p.add_argument("--arm", default="C", choices=ARMS)
    p.add_argument("--package-root", default=None)
    p.add_argument("--effect-stop", action="store_true")
    p.add_argument("--stimulus", default="sf-ui", choices=tuple(SELECTORS))
    p.add_argument("--out", required=True)
    p = sub.add_parser("confirm")
    p.add_argument("--out", required=True)
    p.add_argument("--count", type=int, default=12)
    p.add_argument("--jobs", type=int, default=4)
    p = sub.add_parser("reclassify")
    p.add_argument("--out", required=True)
    p = sub.add_parser("rescan")
    p.add_argument("--out", required=True)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("--host", default="codex", choices=tuple(HOSTS))
    p.add_argument("--arms", default=None)
    p.add_argument("--plan", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--package-root", default=None, help="cut the arms from this tree's plugins/skill-craft (a build-packages.py output)")
    p.add_argument("--effect-stop", action="store_true", help="the harness ends each host at its first run (--stop-after-start)")
    args = ap.parse_args()
    if getattr(args, "arms", None):
        global ARMS_FILE
        ARMS_FILE = Path(args.arms).resolve()
    if getattr(args, "package_root", None):
        global PACKAGE_ROOT
        PACKAGE_ROOT = Path(args.package_root).resolve()
    if getattr(args, "effect_stop", False):
        global EFFECT_STOP
        EFFECT_STOP = True
    if getattr(args, "host", None):
        use_host(args.host)
    if args.cmd == "plan":
        Path(args.out).write_text(json.dumps(make_plan(args.seed, args.plan_set), indent=1) + "\n")
        print(f"{len(make_plan(args.seed, args.plan_set))} slots, set {args.plan_set}, seed {args.seed} -> {args.out}")
    elif args.cmd == "smoke":
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        expected = prepare(out, (args.arm,))
        print(json.dumps(run_trial({"slot": 0, "arm": args.arm, "stimulus": args.stimulus, "i": 0}, 1, out, expected),
                         indent=1))
    elif args.cmd == "confirm":
        run_confirm(Path(args.out), args.count, args.jobs)
    elif args.cmd == "reclassify":
        reclassify(Path(args.out))
    elif args.cmd == "rescan":
        rescan(Path(args.out), args.apply)
    else:
        run_all(json.loads(Path(args.plan).read_text()), Path(args.out), args.jobs)


if __name__ == "__main__":
    main()
