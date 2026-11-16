#!/usr/bin/env python3
"""The ShipLoop adapter's facade for closed-loop (plan: docs/closed-loop-phase2-plan-2026-11-15.md, version 3).

closed_loop.py runs this one program behind every adapter command (`cases`, `records`, `identity`, `probe`, `step`, `cleanup`). It
drives the E2E harness's own qualified loop (`iterate.py --qualify --iterations 1`) from an **evaluator clone** X, and reads what the
harness wrote. It edits no scoring file, so the harness's scoring identity is unchanged (plan, section 3.2).

Layout. X is a private clone of the repository, detached at a base commit B (a released commit, 2.42.0 or later); everything this
program keeps lives beside it in `<X>.facade/` (never inside X, so X stays clean): the tip ref's records, the campaign's baseline
history, one record per step, the probes' scratch clones. The loop's tip lives in X's own ref `refs/closed-loop/tip`; absent, it is B.

Queries (`cases`, `records`, `identity`) read Git objects and X's harness files and write nothing. A step runs in a detached worker,
writes a durable intent first and publishes the new tip last, in two phases (plan 3.2, items 5 to 7).

Harness code is never imported here: a small bridge process runs the few harness functions that are needed (the qualification
snapshot, `candidate_path`, the ledger fold, the baseline predicate) from X, so a test can point it at any checkout.

Python 3.9 floor. Standard library only.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

SCHEMA = "closed-loop-shiploop-facade/1"
TIP_REF = "refs/closed-loop/tip"
MIN_BASE_VERSION = (2, 42, 0)  # 2.42.0 is the release in which new ShipLoop runs call no Backchain child (SPEC S-10)
HERE = Path(__file__).resolve().parent
ALLOWLIST = HERE / "allowlist.json"
KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
MATERIAL_WORDS = ("material", "high")  # learning_records.MATERIAL; the bridge returns the live value and a test compares them


class FacadeError(Exception):
    """A refusal or failure with a message the orchestrator will show (stderr, exit 2)."""


# ----------------------------------------------------------------------------------------------------------- small helpers

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(obj: dict) -> None:
    print(json.dumps(obj, sort_keys=True))


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default
    except ValueError as error:
        raise FacadeError(f"{path} is not valid JSON: {error}") from None


def write_json(path: Path, value) -> None:
    """Durable and atomic: a reader sees the old file or the new one, and the new one survives a power cut."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w") as out:
            out.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise
    directory = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def git(repo, *args, check: bool = True, input_text: str | None = None) -> str:
    """Run Git in `repo` with no prompts, no pager and the user's own configuration; return stdout without the final newline."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat", GIT_OPTIONAL_LOCKS="0")
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, input=input_text, env=env, check=False)
    if check and done.returncode != 0:
        raise FacadeError(f"git {' '.join(args[:3])} failed ({done.returncode}): {(done.stderr or done.stdout).strip()[-300:]}")
    return done.stdout.rstrip("\n") if done.returncode == 0 else ""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def check_key(key: str) -> str:
    if not isinstance(key, str) or not KEY.match(key):
        raise FacadeError(f"step key {key!r} is not usable as a file name (letters, digits, dot, dash, underscore)")
    return key


# ------------------------------------------------------------------------------------------------------------------ layout

class Layout:
    """Where everything is, from the evaluator clone's path alone."""

    def __init__(self, workspace) -> None:
        self.x = Path(workspace).resolve()
        self.state = self.x.parent / (self.x.name + ".facade")
        self.harness = self.x / "test" / "shiploop_e2e"
        self.steps = self.state / "steps"
        self.probes = self.state / "probes"
        self.chain_file = self.state / "chain.json"
        self.baselines_file = self.state / "baselines.jsonl"
        self.locks = self.state / "locks"
        self.tiers = self.state / "tier"

    def step_file(self, key: str) -> Path:
        return self.steps / (check_key(key) + ".json")

    def lock_file(self, key: str) -> Path:
        return self.locks / (check_key(key) + ".lock")

    def tier_file(self, build: str) -> Path:
        return self.tiers / (check_key(build) + ".json")

    def chain(self) -> dict:
        chain = read_json(self.chain_file)
        if not isinstance(chain, dict) or chain.get("schema") != SCHEMA or not chain.get("base"):
            raise FacadeError(f"{self.x} was not set up by this facade (no {self.chain_file}): run `facade.py setup` first")
        return chain


def layout_from_env(workspace=None) -> Layout:
    given = workspace or os.environ.get("CLOSED_LOOP_WORKSPACE")
    if not given:
        raise FacadeError("CLOSED_LOOP_WORKSPACE is not set: the orchestrator passes the evaluator clone's path there")
    layout = Layout(given)
    if not layout.x.is_dir():
        raise FacadeError(f"the evaluator clone {layout.x} does not exist: run `facade.py setup` first")
    layout.chain()  # refuses a folder this facade did not set up, with the instruction to run setup
    return layout


def published_tip(layout: Layout) -> str:
    """The loop tip every query reads: the tip ref in X, else the base commit."""
    tip = git(layout.x, "rev-parse", "--verify", "-q", TIP_REF, check=False)
    return tip or layout.chain()["base"]


# ----------------------------------------------------------------------------------------------------------------- bridge

BRIDGE = r'''
import json, sys
from pathlib import Path
harness, op = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, str(harness))
payload = json.load(sys.stdin)
if op == "snapshot":
    import boundary
    out = {"sha256": boundary.qualification_snapshot(harness, None)["sha256"]}
elif op == "candidate_paths":
    import boundary
    out = {"candidate": [p for p in payload["paths"] if boundary.candidate_path(p)]}
elif op == "ledger":
    import learning_records as lr
    path = Path(payload["path"])
    folded = lr.current(path)
    out = {"material_words": list(lr.MATERIAL), "rows": len(lr.rows(path)), "records": [
        {key: state.get(key) for key in ("record", "status", "target", "materiality", "confidence", "exposure", "title",
                                         "reason", "reopen_when", "decision", "verdict", "epoch", "first_at", "last_at")}
        | {"cases": sorted({s["case"] for s in state.get("sources", []) if isinstance(s, dict) and isinstance(s.get("case"), str)})}
        for _, state in sorted(folded.items())]}
elif op == "rows":
    import learning_records as lr
    out = {"rows": lr.rows(Path(payload["path"])), "material_words": list(lr.MATERIAL)}
elif op == "select_plan":
    import learning_records as lr
    path, case = Path(payload["path"]), payload["case"]
    offered = lr.select(path, case, None)
    sources = set(lr._source_cases(lr.current(path)[offered])) if offered else {case}
    pick = next((other for other in payload["candidates"] if other not in sources), None)
    out = {"generality": pick, "offered": lr.select(path, case, pick), "sources": sorted(sources)}
elif op == "run_card":
    import promotion, scorecard
    card = scorecard.score(Path(payload["run"]))
    strict, failures = promotion._strict_outcome(card, list(payload.get("floors") or promotion.DEFAULT_FLOORS))
    out = {"strict": strict, "failures": failures, "floors": card.get("floors"), "validity": card.get("validity")}
elif op == "baseline_match":
    import run as runner
    rows = []
    for line in payload["lines"]:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    out = {"matches": [sum(1 for row in rows if runner.row_matches(
        row, query["case"], query.get("source"), query.get("host"), query.get("model"), query.get("effort"),
        query.get("planning_review"), query.get("prompt_sha256")) is None) for query in payload["queries"]]}
elif op == "scoring_digest":
    import spread
    catalog = json.loads((harness / "cases.json").read_text())
    out = {"sha256": spread.scoring_digest({name: catalog[name] for name in payload["cases"]}, harness)["sha256"]}
else:
    raise SystemExit("unknown bridge operation " + op)
print("\n@@bridge@@" + json.dumps(out))
'''


def bridge(layout: Layout, op: str, payload: dict | None = None, harness: Path | None = None) -> dict:
    """Run one harness function in a fresh interpreter from X's harness folder and return its JSON answer."""
    folder = harness or layout.harness
    if not (folder / "boundary.py").is_file():
        raise FacadeError(f"no harness at {folder}")
    done = subprocess.run([sys.executable, "-B", "-c", BRIDGE, str(folder), op], input=json.dumps(payload or {}),
                          capture_output=True, text=True, cwd=str(folder), check=False,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if done.returncode != 0:
        raise FacadeError(f"harness bridge {op} failed ({done.returncode}): {(done.stderr or done.stdout).strip()[-400:]}")
    try:
        return json.loads(done.stdout.rsplit("@@bridge@@", 1)[-1])
    except ValueError:
        raise FacadeError(f"harness bridge {op} printed no JSON: {done.stdout.strip()[-200:]!r}") from None


# ---------------------------------------------------------------------------------------------------- identity: build token

def tree_entries(layout: Layout, rev: str) -> list:
    """(mode, oid, path) for every tracked file at `rev`, from Git objects only."""
    raw = subprocess.run(["git", "-C", str(layout.x), "ls-tree", "-r", "--full-tree", "-z", rev], capture_output=True, check=False)
    if raw.returncode != 0:
        raise FacadeError(f"cannot list {rev}: {raw.stderr.decode(errors='replace').strip()[-200:]}")
    entries = []
    for chunk in raw.stdout.split(b"\0"):
        if not chunk:
            continue
        meta, _, path = chunk.partition(b"\t")
        mode, _kind, oid = meta.decode().split()
        entries.append((mode, oid, path.decode()))
    return entries


def build_token(layout: Layout, rev: str) -> str:
    """A digest over the exact candidate set at `rev` (plan 3.2 item 4): the (mode, path, blob id) of every tracked file the improver
    may change under `boundary.candidate_path`. Learning commits move the commit without changing it. Several candidate prefixes are
    filename patterns (`test/shiploop-`), not folders, so the harness's own predicate decides each path."""
    entries = tree_entries(layout, rev)
    chosen = set(bridge(layout, "candidate_paths", {"paths": [path for _, _, path in entries]})["candidate"])
    rows = sorted((mode, path, oid) for mode, oid, path in entries if path in chosen)
    return "b-" + hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()[:24]


def scoring_token(layout: Layout) -> str:
    """The evaluator's identity as the harness computes it, from X's harness files (the same at every tip)."""
    return bridge(layout, "snapshot")["sha256"]


# -------------------------------------------------------------------------------------------------------------- the catalog

def load_allowlist(layout: Layout) -> dict:
    """The cases a campaign may use, with the costs the owner ratified (the file is pinned by the manifest), each checked against the
    base commit's catalog: a case the harness no longer has, or whose style changed, is refused."""
    allowed = read_json(ALLOWLIST)
    if not isinstance(allowed, dict) or not isinstance(allowed.get("cases"), dict) or not allowed["cases"]:
        raise FacadeError(f"{ALLOWLIST} must hold {{\"cases\": {{id: {{style, cost}}}}}}")
    base = layout.chain()["base"]
    try:
        catalog = json.loads(git(layout.x, "show", f"{base}:test/shiploop_e2e/cases.json"))
    except ValueError:
        raise FacadeError("the base commit's cases.json is not JSON") from None
    cases = {}
    for case_id, meta in sorted(allowed["cases"].items()):
        entry = catalog.get(case_id)
        if not isinstance(entry, dict):
            raise FacadeError(f"allowlisted case {case_id} is not in the base commit's catalog")
        if entry.get("style") != meta.get("style"):
            raise FacadeError(f"allowlisted case {case_id} has style {meta.get('style')!r} but the catalog says {entry.get('style')!r}")
        cost = meta.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
            raise FacadeError(f"allowlisted case {case_id} needs a non-negative cost (median minutes)")
        cases[case_id] = {"id": case_id, "dimensions": {"style": meta["style"]}, "cost": cost, "requires": [], "hosted": False}
    return cases


# ----------------------------------------------------------------------------------------------------------------- records

# The ledger's folded statuses as closed-loop's statuses (plan 3.5). `admitted` is conditional on the scope; see map_record.
RESOLVED = {"verified": "verified", "refuted": "refuted", "no_effect": "dropped", "rejected": "rejected"}


def scope_cases(campaign=None) -> list:
    """The cases of the campaign's current scope, read (never written) from campaign.json; empty when there is no campaign yet."""
    folder = campaign or os.environ.get("CLOSED_LOOP_CAMPAIGN")
    if not folder:
        return []
    state = read_json(Path(folder) / "campaign.json", {})
    if not isinstance(state, dict):
        return []
    for scope in state.get("scopes", []):
        if isinstance(scope, dict) and scope.get("id") == state.get("scope"):
            return [case for case in scope.get("cases", []) if isinstance(case, str)]
    return []


def map_record(state: dict, scope: list, material_words=MATERIAL_WORDS) -> dict:
    """One folded ledger record as the orchestrator's record. Resolved statuses carry the verdict's reason as evidence; an `admitted`
    record is actionable only when the harness could offer it for an exposing case in the current scope (a record found on other
    cases, or held as a confirmation case, would send the orchestrator into steps that explore instead of qualify)."""
    status = state["status"]
    cases = list(state.get("cases") or [])
    material = state.get("materiality") in material_words
    target = "adapter" if state.get("target") == "harness" else "subject"
    mapped, evidence = None, None
    if status in RESOLVED:
        mapped = RESOLVED[status]
        evidence = state.get("reason") or (f"epoch {state['epoch']}" if state.get("epoch") else None)
        if not evidence:  # a resolution nobody can show is not one: the record stays with its owner
            mapped, evidence = "owner", None
    elif status == "admitted":
        eligible = (material and state.get("exposure") != "confirmation" and state.get("target", "shiploop") == "shiploop"
                    and (not cases or bool(set(cases) & set(scope))))
        mapped = "admitted" if eligible else "owner"
    elif status == "deferred":
        mapped = "deferred"
    elif status == "in_candidate":
        mapped = "unknown"
    else:  # open, owner, unexplained_gain and anything the harness adds later: waits for the owner
        mapped = "owner"
    out = {"id": state["record"], "title": state.get("title") or state["record"], "material": bool(material), "target": target,
           "status": mapped, "evidence": evidence, "reopen_when": state.get("reopen_when"), "cases": cases}
    out["engine_status"] = status
    return out


def read_ledger_at(layout: Layout, rev: str, into: Path) -> Path:
    """Write the ledger as it is at `rev` into a temporary file (queries never check anything out) and return its path."""
    blob = git(layout.x, "show", f"{rev}:test/shiploop_e2e/learning-records.jsonl", check=False)
    into.write_text(blob + ("\n" if blob else ""))
    return into


def fold_ledger(layout: Layout, rev: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="facade-ledger-") as folder:
        path = read_ledger_at(layout, rev, Path(folder) / "learning-records.jsonl")
        return bridge(layout, "ledger", {"path": str(path)})


# ---------------------------------------------------------------------------------------------------------------- commands

def cmd_cases(args) -> dict:
    layout = layout_from_env()
    return {"cases": list(load_allowlist(layout).values())}


def cmd_identity(args) -> dict:
    layout = layout_from_env()
    return {"scoring": scoring_token(layout), "build": build_token(layout, published_tip(layout))}


def cmd_records(args) -> dict:
    layout = layout_from_env()
    folded = fold_ledger(layout, published_tip(layout))
    scope = scope_cases()
    return {"records": [map_record(state, scope, tuple(folded["material_words"])) for state in folded["records"]]}


def version_tuple(text: str) -> tuple:
    parts = re.findall(r"\d+", str(text))[:3]
    return tuple(int(part) for part in parts) + (0,) * (3 - len(parts))


def cmd_setup(args) -> dict:
    """Create the evaluator clone X at the base commit and its state folder. Run by the operator before `closed_loop.py init`."""
    source = Path(args.source or HERE.parents[2]).resolve()
    x = Path(args.workspace).resolve()
    if x.exists() and any(x.iterdir()):
        raise FacadeError(f"{x} exists and is not empty: setup never reuses a folder")
    if not (source / ".git").exists():
        raise FacadeError(f"{source} is not a Git checkout")
    base = git(source, "rev-parse", "--verify", f"{args.base}^{{commit}}")
    version = git(source, "show", f"{base}:catalog/skill-craft-plugin.json", check=False)
    try:
        released = json.loads(version)["version"]
    except (ValueError, KeyError, TypeError):
        raise FacadeError(f"{base} has no catalog/skill-craft-plugin.json version: the base must be a released commit") from None
    if version_tuple(released) < MIN_BASE_VERSION:
        raise FacadeError(f"the base {base[:12]} is skill-craft {released}; the minimum is {'.'.join(map(str, MIN_BASE_VERSION))} "
                          "(new ShipLoop runs call no Backchain child from 2.42.0)")
    x.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):
        # A source that is repacking at this moment can lose an object between the clone and the checkout ("unable to read
        # tree"); one retry from a clean folder is the cure the 2026-11-01 load-flake notes found.
        try:
            cloned = subprocess.run(["git", "clone", "--local", "--no-checkout", "-q", str(source), str(x)], capture_output=True,
                                    text=True, check=False)
            if cloned.returncode != 0:
                raise FacadeError(f"git clone of {source} into {x} failed ({cloned.returncode}): {cloned.stderr.strip()[-300:]}")
            git(x, "config", "gc.auto", "0")  # X is the campaign's own: no background maintenance races the harness's Git use
            git(x, "config", "maintenance.auto", "false")
            git(x, "checkout", "-q", "--detach", base)
            break
        except FacadeError:
            shutil.rmtree(x, ignore_errors=True)
            if attempt == 2:
                raise
            time.sleep(2)
    for ref_name in git(x, "for-each-ref", "--format=%(refname)", "refs/shiploop-loop").splitlines():
        git(x, "update-ref", "-d", ref_name)  # the clone starts with no other session's loop refs (plan row 10)
    layout = Layout(x)
    layout.state.mkdir(parents=True, exist_ok=True)
    write_json(layout.chain_file, {"schema": SCHEMA, "base": base, "released": released, "source": str(source), "created": now(),
                                   "workspace": str(x)})
    layout.baselines_file.write_text("")
    return {"ok": True, "workspace": str(x), "state": str(layout.state), "base": base, "released": released}


# ------------------------------------------------------------------------------------------------------------------ processes

PS_ENV = {"LC_ALL": "C", "LANG": "C"}  # `lstart` is compared as text, so its format must not follow the user's locale
GRACE_SECONDS, FORCE_SECONDS, POLL_SECONDS = 8.0, 4.0, 0.1  # a group gets this long after SIGTERM, then after SIGKILL, to end


def ps_rows(pids=None) -> dict:
    """pid -> {pid, ppid, pgid, started, command} from ps. `started` is the creation time ps prints: with the pid it names one
    process, because a recycled pid has another start time."""
    command = ["ps", "-ww", "-o", "pid=,ppid=,pgid=,lstart=,command="]
    command += ["-p", ",".join(str(pid) for pid in pids)] if pids else ["-ax"]
    done = subprocess.run(command, capture_output=True, text=True, env=dict(os.environ, **PS_ENV), check=False)
    if done.returncode not in (0, 1):  # 1 is "nothing matched" for -p
        raise FacadeError(f"ps failed ({done.returncode}): {done.stderr.strip()[-200:]}")
    rows = {}
    for line in done.stdout.splitlines():
        parts = line.split(None, 8)  # pid ppid pgid, then lstart's five words, then the command
        if len(parts) < 8 or not all(part.isdigit() for part in parts[:3]):
            continue
        rows[int(parts[0])] = {"pid": int(parts[0]), "ppid": int(parts[1]), "pgid": int(parts[2]), "started": " ".join(parts[3:8]),
                               "command": parts[8] if len(parts) > 8 else ""}
    return rows


def identity_of(pid: int) -> dict | None:
    row = ps_rows([pid]).get(pid)
    return None if row is None else {"pid": pid, "pgid": row["pgid"], "started": row["started"]}


def descendants(table: dict, root: int) -> list:
    """The rows of every process below `root` by parent links, `root` aside. A child that started its own session is still found
    while the processes between it and `root` are alive, which is why a cancel takes this snapshot before it signals anything."""
    children: dict = {}
    for row in table.values():
        children.setdefault(row["ppid"], []).append(row)
    found, queue, seen = [], [root], {root}
    while queue:
        for row in children.get(queue.pop(), []):
            if row["pid"] not in seen:
                seen.add(row["pid"])
                found.append(row)
                queue.append(row["pid"])
    return found


def protected_pids(table: dict) -> set:
    """This process and its ancestors: never signalled, whatever a record says."""
    found, pid = set(), os.getpid()
    while pid in table and pid not in found and pid > 1:
        found.add(pid)
        pid = table[pid]["ppid"]
    return found


def stop_group(ident: dict) -> tuple:
    """End the process group a recorded worker led, only if it is still that group: ``(how, detail)`` with ``how`` one of
    ``stopped`` (``ended_by`` SIGTERM or SIGKILL), ``survived``, ``gone`` (no member), ``reused`` (the leader's pid now names another
    process: not signalled) or ``protected`` (the group holds this process or an ancestor). A group number is not reused while the
    group has a member, so a leader that is gone with members left means they are the worker's own descendants."""
    pgid = ident["pgid"]
    table = ps_rows()
    members = [row for row in table.values() if row["pgid"] == pgid]
    if not members:
        return "gone", {}
    guarded = protected_pids(table)
    if pgid <= 1 or any(row["pid"] in guarded for row in members):
        return "protected", {"members": [row["pid"] for row in members]}
    leader = table.get(ident["pid"])
    if leader is not None and leader["started"] != ident["started"]:
        return "reused", {"now": {"pid": leader["pid"], "command": leader["command"][:200]}}
    for name, number, wait in (("SIGTERM", signal.SIGTERM, GRACE_SECONDS), ("SIGKILL", signal.SIGKILL, FORCE_SECONDS)):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, number)
        end = time.monotonic() + wait
        while time.monotonic() < end:
            time.sleep(POLL_SECONDS)
            if not any(row["pgid"] == pgid for row in ps_rows().values()):
                return "stopped", {"ended_by": name, "members": len(members)}
    return "survived", {"members": [row["pid"] for row in ps_rows().values() if row["pgid"] == pgid]}


def stop_processes(rows: list) -> list:
    """SIGTERM, then SIGKILL, every process of a snapshot that still has its recorded pid and start time; the survivors' rows.
    Used for the model sessions a cancel finds below the worker, which the harness starts in sessions of their own."""
    def live() -> list:
        table = ps_rows([row["pid"] for row in rows]) if rows else {}
        guarded = protected_pids(ps_rows())
        return [row for row in rows if table.get(row["pid"], {}).get("started") == row["started"] and row["pid"] not in guarded]

    for number, wait in ((signal.SIGTERM, GRACE_SECONDS), (signal.SIGKILL, FORCE_SECONDS)):
        todo = live()
        if not todo:
            return []
        for row in todo:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(row["pid"], number)
        end = time.monotonic() + wait
        while time.monotonic() < end and live():
            time.sleep(POLL_SECONDS)
    return live()


# ---------------------------------------------------------------------------------------------------------- step records, locks

STEP_SCHEMA = "closed-loop-shiploop-step/1"
LIVE = ("starting", "running")
BASELINES_REL = "test/shiploop_e2e/baselines.jsonl"
LEDGER_REL = "test/shiploop_e2e/learning-records.jsonl"
OK_STOPS = ("reached --iterations", "no admitted learning record after exploring")  # the loop's two ordinary ends for one iteration
TIER_COMMAND = ["bash", "test/run-all.sh", "--group", "quick", "--changed-from"]


def load_step(layout: Layout, key: str):
    rec = read_json(layout.step_file(key))
    if rec is not None and rec.get("schema") != STEP_SCHEMA:
        raise FacadeError(f"{layout.step_file(key)} is not a step record of this facade")
    return rec


def save_step(layout: Layout, rec: dict) -> None:
    write_json(layout.step_file(rec["key"]), rec)


class WorkerLock:
    """The liveness signal of a step: its worker holds an exclusive lock on a file for as long as it lives, and the operating system
    releases it when the worker ends however it ends (a SIGKILL included), so no pid reuse or stale file can fake a live worker."""

    def __init__(self, path) -> None:
        self.path, self.fd = Path(path), None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self.fd = fd
        return True

    def release(self) -> None:
        if self.fd is not None:
            with contextlib.suppress(OSError):
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
            self.fd = None


def worker_alive(layout: Layout, key: str) -> bool:
    lock = WorkerLock(layout.lock_file(key))
    if lock.acquire():
        lock.release()
        return False
    return True


def live_keys(layout: Layout) -> list:
    """Keys of the steps whose worker is alive now."""
    if not layout.steps.is_dir():
        return []
    found = []
    for path in sorted(layout.steps.glob("*.json")):
        rec = read_json(path, {})
        if rec.get("state") in LIVE + ("prepared",) and worker_alive(layout, path.stem):
            found.append(path.stem)
    return found


# ---------------------------------------------------------------------------------------------------- the evaluator clone, X

def x_dirty(layout: Layout) -> list:
    """Paths `git status` shows in X (ignored files are not shown)."""
    done = subprocess.run(["git", "-C", str(layout.x), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                          capture_output=True, text=True, check=False, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if done.returncode != 0:
        raise FacadeError(f"git status in {layout.x} failed: {done.stderr.strip()[-200:]}")
    return [entry[3:] for entry in done.stdout.split("\0") if entry]


def position(layout: Layout, tip: str) -> None:
    git(layout.x, "checkout", "-q", "--detach", tip)


def restore_x(layout: Layout) -> list:
    """Put X back as its commit has it and return what else than the baseline file had changed (the harness appends one row per run to
    the tracked baseline file in the checkout that runs it; the rows are captured before this is called)."""
    dirty = x_dirty(layout)
    stray = [path for path in dirty if path != BASELINES_REL]
    if BASELINES_REL in dirty:
        git(layout.x, "checkout", "-q", "--", BASELINES_REL)
    if stray:
        git(layout.x, "checkout", "-q", "--", ".")
        git(layout.x, "clean", "-fdq")
    return stray


def lines_of(text: str) -> list:
    return [line for line in text.splitlines() if line.strip()]


def capture_baselines(layout: Layout, rec: dict) -> int:
    """Copy the baseline rows the step's invocations wrote, from both places they land (X's tracked file, and every epoch's own
    `baselines.jsonl` under the step's output), into the campaign's history and into the step's own list, once each; the count of
    new rows. Plan 3.2 item 2: the comparison of a later run with this one needs rows from both."""
    head = lines_of(git(layout.x, "show", f"HEAD:{BASELINES_REL}", check=False))
    path = layout.x / BASELINES_REL
    current = lines_of(path.read_text()) if path.is_file() else []
    added = current[len(head):] if current[:len(head)] == head else [line for line in current if line not in set(head)]
    out = Path(rec["out"])
    for epoch_file in sorted(out.rglob("baselines.jsonl")):
        added += lines_of(epoch_file.read_text())
    known = set(lines_of(layout.baselines_file.read_text())) if layout.baselines_file.is_file() else set()
    fresh = [line for line in dict.fromkeys(added) if line not in known]
    if fresh:
        for target in (layout.baselines_file, out / "baselines-captured.jsonl"):
            with open(target, "a") as handle:
                handle.write("".join(line + "\n" for line in fresh))
                handle.flush()
                os.fsync(handle.fileno())
    return len(fresh)


def worktrees(layout: Layout) -> list:
    """The linked worktrees of X as {path, branch, head}; X itself is not listed."""
    raw = git(layout.x, "worktree", "list", "--porcelain")
    found, current = [], {}
    for line in raw.splitlines() + [""]:
        if not line.strip():
            if current.get("path") and Path(current["path"]).resolve() != layout.x:
                found.append(current)
            current = {}
        elif line.startswith("worktree "):
            current["path"] = line[9:]
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].removeprefix("refs/heads/")
    return found


def salvage(layout: Layout, rec: dict, tree: dict) -> dict:
    """Everything a killed or failed invocation left in one loop worktree, copied out before the worktree is removed: its status, the
    staged and the unstaged changes as patches, every changed or untracked file as it is, the ledger as the worktree has it, and its
    branch since the tip as a bundle. A plain `git diff` would miss rows that were staged, then removed from the file, or never added."""
    path = Path(tree["path"])
    dest = Path(rec["out"]) / "salvage" / path.name
    dest.mkdir(parents=True, exist_ok=True)
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all", check=False)
    (dest / "status.txt").write_text(status + "\n")
    (dest / "staged.diff").write_text(git(path, "diff", "--cached", "--binary", check=False) + "\n")
    (dest / "unstaged.diff").write_text(git(path, "diff", "--binary", check=False) + "\n")
    for line in status.splitlines():
        name = line[3:].split(" -> ")[-1].strip('"')
        source = path / name
        if source.is_file():
            (dest / "files" / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest / "files" / name, follow_symlinks=False)
    ledger = path / LEDGER_REL
    held = lines_of(ledger.read_text()) if ledger.is_file() else []
    if ledger.is_file():
        shutil.copy2(ledger, dest / "learning-records.jsonl")
    before = lines_of(git(layout.x, "show", f"{rec['tip_from']}:{LEDGER_REL}", check=False))
    commits = 0
    if tree.get("branch") and git(layout.x, "rev-parse", "--verify", "-q", f"refs/heads/{tree['branch']}", check=False):
        commits = int(git(layout.x, "rev-list", "--count", f"{rec['tip_from']}..refs/heads/{tree['branch']}", check=False) or 0)
        if commits:
            git(layout.x, "bundle", "create", str(dest / "branch.bundle"), f"{rec['tip_from']}..refs/heads/{tree['branch']}", check=False)
    return {"path": str(dest), "worktree": str(path), "branch": tree.get("branch"), "changed_paths": len(status.splitlines()),
            "commits": commits, "ledger_rows": max(0, len(held) - len(before))}


def remove_worktrees(layout: Layout) -> list:
    """Remove X's linked worktrees (their branches stay: a promoted candidate lives on one, and a kept candidate has its ref)."""
    removed = []
    for tree in worktrees(layout):
        git(layout.x, "worktree", "remove", "--force", "--force", tree["path"], check=False)
        removed.append(tree["path"])
    git(layout.x, "worktree", "prune", check=False)
    return removed

# ------------------------------------------------------------------------------------------------------------ cleanup and receipts

def run_folders(out: Path) -> list:
    """Every run folder under `out` (one holding an invocation.json), found without descending into a run folder."""
    found = []
    for here, folders, files in os.walk(out):
        if "invocation.json" in files:
            found.append(Path(here))
            folders[:] = []
    return sorted(found)


def run_lifecycle(layout: Layout, folder: Path) -> dict:
    """The harness's own cleanup for one run folder, as its command line prints it. Without a result the folder is not observed."""
    try:
        done = subprocess.run([sys.executable, "-B", str(layout.harness / "lifecycle.py"), "cleanup", str(folder)], capture_output=True,
                              text=True, timeout=300, cwd=str(layout.harness), check=False,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        return {"observed": False, "reason": "lifecycle.py cleanup did not finish in 300 seconds", "exit": None}
    try:
        result = json.loads(done.stdout)
        if not isinstance(result, dict):
            raise ValueError
    except ValueError:
        result = {"observed": False, "reason": (done.stderr or done.stdout).strip()[-300:] or "no output"}
    result["exit"] = done.returncode
    return result


def lifecycle_problems(result: dict) -> list:
    """What makes one cleanup result not a proof of nothing left: not observed, or a group that survived, whose leader could not be
    verified (its members were left alone) or that held this process or an ancestor. The CLI exits 0 for the last two."""
    problems = [] if result.get("observed") else ["not observed: " + str(result.get("reason"))]
    for kind in ("survived", "unverified", "protected"):
        if result.get(kind):
            problems.append(f"{len(result[kind])} group(s) {kind}")
    return problems


def lifecycle_cleanup(layout: Layout, rec: dict) -> tuple:
    """Run the harness's lifecycle cleanup over every run folder of the step and keep the FIRST result per folder: a second cleanup
    is idempotent and would hide what the first one stopped. Returns (verified, receipt text)."""
    stored = rec.setdefault("cleanup", {}).setdefault("folders", {})
    problems, stopped, folders = [], 0, run_folders(Path(rec["out"]))
    for folder in folders:
        fresh = run_lifecycle(layout, folder)
        entry = stored.setdefault(str(folder), {"first": fresh})
        entry["latest"] = fresh
        for label in ("first", "latest"):
            problems += [f"{folder.name}: {text}" for text in lifecycle_problems(entry[label])]
        stopped += len(entry["first"].get("stopped") or [])
    problems = list(dict.fromkeys(problems))
    receipt = (f"lifecycle.py cleanup over {len(folders)} run folder(s): {stopped} group(s) stopped"
               + (f"; problems: {'; '.join(problems)}" if problems else "; none survived, none unverified, none protected"))
    return (not problems), receipt


# --------------------------------------------------------------------------------------------------------- one engine invocation

def parse_loop(text: str) -> dict:
    """The few facts LOOP.md carries that nothing else does: the worktree and branch, whether an exploration and a cycle took place
    and the cycle's record, and the stop line. Everything else is read from JSON (the engine rewords its prose)."""
    found = {"worktree": None, "branch": None, "explored": False, "cycle": None, "stop": None}
    for line in text.splitlines():
        header = re.match(r"^- worktree (.+), branch (\S+)$", line)
        if header:
            found["worktree"], found["branch"] = header.group(1), header.group(2)
        elif line.startswith("## Exploration "):
            found["explored"] = True
        elif line.startswith("## Cycle "):
            found["cycle"] = line.partition(": ")[2].strip() or "unknown"
        elif line.startswith("- stopped: "):
            found["stop"] = line[len("- stopped: "):].strip()
    return found


def engine_argv(layout: Layout, rec: dict, inv: dict) -> list:
    profile = rec["profile"]
    argv = [sys.executable, "-B", str(layout.harness / "iterate.py"), "--qualify", "--iterations", "1", "--case", inv["case"]]
    if inv.get("generality"):
        argv += ["--generality-case", inv["generality"]]
    for flag in ("host", "model", "effort"):
        if profile.get(flag):
            argv += [f"--{flag}", str(profile[flag])]
    if profile.get("calibration"):
        argv += ["--calibration", str(profile["calibration"])]
    else:
        argv += ["--tolerance", str(profile.get("tolerance")), "--attempts", str(profile.get("attempts"))]
    if profile.get("parallel"):
        argv += ["--parallel", str(profile["parallel"])]
    argv += list(profile.get("engine_args") or [])
    return argv + ["--output", inv["out"]]


def other_style_cases(layout: Layout, cases: list, case: str) -> list:
    allowed = load_allowlist(layout)
    mine = allowed[case]["dimensions"]["style"]
    return [other for other in sorted(cases) if other != case and other in allowed and allowed[other]["dimensions"]["style"] != mine]


def plan_invocation(layout: Layout, rec: dict, case: str, tip: str) -> dict:
    """What the engine will do from `tip` for `case`: the generality case to pass (the first other-style case of the scope that is not
    among the offered record's source cases; none means a single-style claim) and the record the engine's own `select` will offer, or
    None when it will explore first. The same function the loop calls, on the ledger at the tip."""
    with tempfile.TemporaryDirectory(prefix="facade-plan-") as folder:
        path = read_ledger_at(layout, tip, Path(folder) / "learning-records.jsonl")
        return bridge(layout, "select_plan", {"path": str(path), "case": case, "candidates": other_style_cases(layout, rec["cases"], case)})


def ledger_rows_at(layout: Layout, rev: str) -> list:
    with tempfile.TemporaryDirectory(prefix="facade-rows-") as folder:
        path = read_ledger_at(layout, rev, Path(folder) / "learning-records.jsonl")
        return bridge(layout, "rows", {"path": str(path)})["rows"]


def run_invocation(layout: Layout, rec: dict, inv: dict) -> None:
    """One `iterate.py --qualify --iterations 1` from X, positioned at the tip the previous invocation left. It runs in the worker's own
    process group (a group kill ends the worker and the engine together); its model sessions are in sessions of their own, which the
    lifecycle cleanup and a cancel's process snapshot reach. Fills `inv`, or raises FacadeError."""
    if restore_x(layout):
        raise FacadeError("the evaluator clone had uncommitted paths before an invocation")
    position(layout, inv["tip_before"])
    out = Path(inv["out"])
    # SHIPLOOP_E2E_RUNS_ROOT is removed, never set: with it, a sealed attempt binds every run under the named folder as its neighbour,
    # other sessions' runs included (commit 8493c5b9fc3b4fa6bac67588521e90912ff71592, the full-cycle kit), and without it a run's
    # neighbours are the folders beside it in its own epoch or invocation.
    env = {name: value for name, value in os.environ.items() if name != "SHIPLOOP_E2E_RUNS_ROOT"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    argv = engine_argv(layout, rec, inv)
    inv.update(state="running", argv=argv, started_at=now())
    save_step(layout, rec)
    with open(out.parent / (out.name + ".log"), "ab") as log:
        process = subprocess.Popen(argv, cwd=str(layout.x), env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        inv["engine_pid"] = process.pid
        save_step(layout, rec)
        try:
            code = process.wait()
        except BaseException:
            process.kill()  # the worker is being unwound: the engine does not outlive it
            raise
    inv.update(exit=code, ended_at=now())
    capture_baselines(layout, rec)
    inv["invalid"] = []
    stray = restore_x(layout)
    if stray:
        inv["invalid"].append("the evaluator clone changed during the run (restored): " + ", ".join(stray[:5]))
    if code != 0:
        inv["state"] = "failed"
        raise FacadeError(f"the engine exited {code} on {inv['case']}: see {out.parent / (out.name + '.log')}")
    journal = out / "LOOP.md"
    loop = parse_loop(journal.read_text()) if journal.is_file() else parse_loop("")
    inv["loop"] = loop
    if not loop["branch"] or not loop["stop"]:
        inv["state"] = "failed"
        raise FacadeError(f"the engine's loop journal {journal} names no branch or no stop: the loop did not end normally")
    tip_after = git(layout.x, "rev-parse", "--verify", "-q", f"refs/heads/{loop['branch']}", check=False)
    continues = bool(tip_after) and subprocess.run(["git", "-C", str(layout.x), "merge-base", "--is-ancestor", inv["tip_before"], tip_after],
                                                    capture_output=True, check=False).returncode == 0
    if not continues:
        inv["state"] = "failed"
        raise FacadeError(f"the loop branch {loop['branch']} does not continue from the tip {inv['tip_before'][:12]}")
    if loop["worktree"] and Path(loop["worktree"]).is_dir() and git(Path(loop["worktree"]), "status", "--porcelain", check=False):
        inv["state"] = "failed"
        raise FacadeError(f"the loop worktree {loop['worktree']} was left with uncommitted changes")
    inv.update(tip_after=tip_after, build_after=build_token(layout, tip_after))
    inv["promoted"] = inv["build_after"] != inv["build_before"]
    if not loop["stop"].startswith(OK_STOPS):
        inv["invalid"].append(f"the loop stopped for another reason than finishing its iteration: {loop['stop'][:200]}")
    inv["cycle_ran"] = (out / "cycle-1").is_dir()
    inv["state"] = "done"


def run_tier(layout: Layout, rec: dict, inv: dict) -> dict:
    """The quick tier on a promoted candidate, in the loop worktree (plan 3.4: `tier`); the receipt is kept per build, so an iteration
    that leaves the build unchanged can carry the last green one."""
    worktree = Path(inv["loop"]["worktree"])
    log = Path(rec["out"]) / f"tier-{inv['n']}.log"
    started = time.time()
    with open(log, "w") as handle:
        done = subprocess.run(TIER_COMMAND + [inv["tip_before"]], cwd=str(worktree), stdout=handle, stderr=subprocess.STDOUT, check=False)
    receipt = {"green": done.returncode == 0, "build": inv["build_after"], "exit": done.returncode, "at": now(),
               "seconds": round(time.time() - started, 1), "command": " ".join(TIER_COMMAND + [inv["tip_before"][:12]]), "log": str(log)}
    write_json(layout.tier_file(inv["build_after"]), receipt)
    return receipt


# ---------------------------------------------------------------------------------------------------------------- the derivations

def read_optional(path: Path):
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return value


def validity_status(document) -> str:
    return ((document or {}).get("validity") or {}).get("status") if isinstance(document, dict) else None


def run_summary(layout: Layout, run_dir: Path) -> dict:
    """What the facts need of one run folder: whether the skill ran from the build under test, and the harness's own strict outcome."""
    result = read_optional(run_dir / "result.json")
    if not isinstance(result, dict):
        return {"dir": str(run_dir), "ok": False, "why": "no readable result.json"}
    ran = (result.get("invoked") or {}).get("pass") is True and (result.get("plugin") or {}).get("pass") is True
    card = bridge(layout, "run_card", {"run": str(run_dir)})
    attribution = ((card.get("validity") or {}).get("attribution") or {})
    return {"dir": str(run_dir), "ok": True, "ran": ran, "strict": card.get("strict"), "failures": card.get("failures"),
            "attribution_valid": attribution.get("valid"), "attribution_why": attribution.get("why"),
            "key": {name: result.get(name) for name in ("case", "host", "model", "effort", "source", "prompt_sha256")}}


def epoch_evidence(out: Path) -> dict:
    """A cycle's epoch as the harness recorded it: the decision event's attempts (their strict outcomes, as promotion computed them),
    the review receipts, and the count of reviews that ended incomplete."""
    events = []
    try:
        events = [json.loads(line) for line in lines_of((out / "cycle-1" / "epoch" / "events.jsonl").read_text())]
    except (OSError, ValueError):
        pass
    decision = next((event.get("result") for event in events if event.get("kind") == "decision"), None)
    receipts = []
    for event in events:
        if event.get("kind") == "reviewed":
            receipts.append(read_optional(out / "cycle-1" / "epoch" / str(event.get("receipt"))))
    return {"decision": decision, "receipts": receipts, "incomplete": sum(1 for event in events if event.get("kind") == "review_incomplete"),
            "expected": len((decision or {}).get("attempts") or [])}


def candidate_ref(layout: Layout, inv: dict, record: str) -> str | None:
    """The candidate commit of a cycle that did not promote: the newest ref `refs/shiploop-loop/<loop>/<record>[-N]` the cycle kept."""
    loop = inv["loop"]["branch"].removeprefix("auto/")
    refs = git(layout.x, "for-each-ref", "--format=%(refname) %(objectname)", f"refs/shiploop-loop/{loop}/{record}", f"refs/shiploop-loop/{loop}/{record}-*",
               check=False).splitlines()
    return refs[-1].split()[1] if refs else None


def invocation_evidence(layout: Layout, rec: dict, inv: dict) -> dict:
    """One invocation's facts: the runs that stand for its case on the build the step ends with, the review and judge outcomes, the
    cycle's candidate. Everything is read from JSON and Git; a source that is missing makes the fact false, never true."""
    out = Path(inv["out"])
    found = {"case": inv["case"], "runs": [], "reviews": [], "judges": [], "invalid": list(inv.get("invalid") or []), "candidate": None,
             "acceptance": None}
    explore_run = out / "explore-1" / "run"
    if inv["loop"]["explored"]:
        found["exploration"] = str(explore_run)
        review, verdict = read_optional(explore_run / "review.json"), read_optional(explore_run / "review-judge" / "verdict.json")
        qualified = bool(((review or {}).get("validity") or {}).get("discovery_qualified"))
        found["reviews"].append({"valid": validity_status(review) == "valid" and qualified, "complete": review is not None})
        found["judges"].append({"valid": validity_status(verdict) == "valid", "complete": verdict is not None})
        if review is not None and not qualified:
            detail = ((review.get("validity") or {}).get("reason") or validity_status(review) or "unknown")
            found["invalid"].append(f"INVALID_REVIEW on {inv['case']}: no discovery-qualified review ({str(detail)[:160]})")
    epoch = epoch_evidence(out) if inv["cycle_ran"] else None
    decision = (epoch or {}).get("decision") or {}
    cycle = read_optional(out / "cycle-1" / "cycle-result.json") if inv["cycle_ran"] else None
    if epoch is not None:
        for receipt in epoch["receipts"]:
            found["reviews"].append({"valid": validity_status((receipt or {}).get("review")) == "valid", "complete": receipt is not None})
            found["judges"].append({"valid": validity_status((receipt or {}).get("judge")) == "valid", "complete": receipt is not None})
        if epoch["incomplete"] or len(epoch["receipts"]) < epoch["expected"]:
            found["reviews"].append({"valid": False, "complete": False})
    # the runs that stand for the case on the build the step ends with
    if inv["promoted"]:
        arm = "candidate"
    elif not inv["loop"]["explored"]:
        arm = "control"
    else:
        arm = None
    if arm:
        for attempt in decision.get("attempts") or []:
            if attempt.get("arm") == arm and attempt.get("case") == inv["case"]:
                run_dir = out / "cycle-1" / "epoch" / "runs" / str(attempt.get("id"))
                summary = run_summary(layout, run_dir) if run_dir.is_dir() else {"dir": str(run_dir), "ok": False, "why": "no run folder"}
                summary["strict"] = True if attempt.get("outcome") == "success" and attempt.get("evidence_valid") else False
                found["runs"].append(summary)
    elif inv["loop"]["explored"]:
        found["runs"].append(run_summary(layout, explore_run))
    # the cycle's candidate
    if cycle is not None or inv["cycle_ran"]:
        outcome = (cycle or {}).get("decision")
        record = inv["loop"]["cycle"]
        if outcome == "PROMOTE" and inv["promoted"]:
            hash_ = git(layout.x, "rev-parse", "--verify", "-q", f"{(cycle or {}).get('learnings_commit') or inv['tip_after']}^", check=False)
            found["candidate"] = {"id": record, "hash": hash_ or inv["tip_after"], "outcome": "PROMOTE"}
        elif outcome in ("DROP", "UNDECIDED"):
            hash_ = candidate_ref(layout, inv, record)
            if hash_:
                found["candidate"] = {"id": record, "hash": hash_, "outcome": outcome}
            else:
                found["invalid"].append(f"the cycle for {record} decided {outcome} but kept no candidate ref")
        elif outcome in ("NO_CANDIDATE", "REJECTED_AT_PURPOSE", "NO_PREDICTION", "REFUSED"):
            hash_ = candidate_ref(layout, inv, record)
            if hash_:
                found["candidate"] = {"id": record, "hash": hash_, "outcome": "DROP"}
            else:
                found["invalid"].append(f"the cycle for {record} ended {outcome} with no candidate commit: no candidate is reported")
        else:
            found["invalid"].append(f"the cycle for {record} reported {outcome or 'no result'}, which is not an outcome this facade reads "
                                    "(attempts may be unsealed: reconcile them, never retry)")
            found["unreconciled"] = True
        if outcome == "PROMOTE" and not inv["promoted"]:
            found["invalid"].append("the cycle reported PROMOTE but the build did not change")
        if inv["promoted"] and outcome != "PROMOTE":
            found["invalid"].append(f"the build changed but the cycle reported {outcome}")
        if inv["promoted"]:
            lines = []
            for name, sides in sorted(((cycle or {}).get("cases") or {}).items()):
                side = (sides or {}).get("candidate") or {}
                lines.append(f"{name}: candidate {side.get('successes')}/{side.get('attempts')} successes")
            style = (f"a confirmation case of another style ({inv['generality']}) took part" if inv.get("generality")
                     else "single-style claim: no confirmation case of another style took part")
            found["acceptance"] = {"candidate": found["candidate"]["hash"] if found["candidate"] else inv["tip_after"],
                                   "evidence": "; ".join(lines + [style, "decision " + str(outcome)])}
    return found


def run_key(row: dict) -> tuple:
    return tuple(row.get(name) for name in ("case", "source", "host", "model", "effort", "planning_review", "prompt_sha256"))


def baseline_status(layout: Layout, rec: dict, runs: list) -> str:
    """`comparable` when every run that stands for the case has an earlier row the harness's one predicate (run.row_matches, S-12)
    accepts, `none` when one has none, `unknown` when a run's own row cannot be found (an unfinished run writes none). The earlier
    rows are the base commit's baseline file and the campaign's captured history, minus this step's own rows (plan 3.4)."""
    if not runs:
        return "none"
    out = Path(rec["out"])
    mine = lines_of((out / "baselines-captured.jsonl").read_text()) if (out / "baselines-captured.jsonl").is_file() else []
    own_rows = []
    for line in mine:
        with contextlib.suppress(ValueError):
            row = json.loads(line)
            if isinstance(row, dict):
                own_rows.append(row)
    base = lines_of(git(layout.x, "show", f"{rec['tip_from']}:{BASELINES_REL}", check=False))
    history = lines_of(layout.baselines_file.read_text()) if layout.baselines_file.is_file() else []
    excluded = set(mine)
    earlier = [line for line in dict.fromkeys(base + history) if line not in excluded]
    queries = []
    for run in runs:
        row = next((candidate for candidate in own_rows if candidate.get("output")
                    and os.path.realpath(candidate["output"]) == os.path.realpath(run["dir"])), None)
        if row is None:
            return "unknown"
        queries.append({"case": row.get("case"), "source": row.get("source"), "host": row.get("host"), "model": row.get("model"),
                        "effort": row.get("effort"), "planning_review": row.get("planning_review"), "prompt_sha256": row.get("prompt_sha256")})
    matches = bridge(layout, "baseline_match", {"lines": earlier, "queries": queries})["matches"]
    return "comparable" if all(count > 0 for count in matches) else "none"


def derive_iteration(layout: Layout, rec: dict) -> dict:
    """The orchestrator's `iteration` for a finished step (plan 3.4), without `cleanup` and `consumed`, which the caller adds. A fact
    that cannot be read is false or the step fails; no fact is ever filled in to look quiet."""
    done = [inv for inv in rec["invocations"] if inv["state"] == "done"]
    evidence = [invocation_evidence(layout, rec, inv) for inv in done]
    final_tip = done[-1]["tip_after"] if done else rec["tip_from"]
    invalid = [text for item in evidence for text in item["invalid"]]
    cases = {}
    for case in rec["cases"]:
        item = next((entry for entry in evidence if entry["case"] == case), None)
        runs = item["runs"] if item else []
        for run in runs:
            if run.get("attribution_valid") is False:
                invalid.append(f"{case}: the harness could not attribute {Path(run['dir']).name} to the build under test: "
                               f"{run.get('attribution_why')}")
        usable = bool(runs) and all(run.get("ok") for run in runs)
        cases[case] = {"ran": usable and all(run.get("ran") for run in runs),
                       "floors_met": usable and all(run.get("strict") is True for run in runs),
                       "baseline": baseline_status(layout, rec, runs) if usable else "none"}
        for run in runs:
            if not run.get("ok"):
                invalid.append(f"{case}: {Path(run['dir']).name} has no usable result ({run.get('why')})")
    reviews = [part for item in evidence for part in item["reviews"]]
    judges = [part for item in evidence for part in item["judges"]]
    review = {"valid": bool(reviews) and all(part["valid"] for part in reviews), "complete": bool(reviews) and all(part["complete"] for part in reviews)}
    judge = {"valid": bool(judges) and all(part["valid"] for part in judges), "complete": bool(judges) and all(part["complete"] for part in judges)}
    before, after = ledger_rows_at(layout, rec["tip_from"]), ledger_rows_at(layout, final_tip)
    if after[:len(before)] != before:
        invalid.append("the ledger at the new tip is not an append-only continuation of the published one")
    folded = fold_ledger(layout, final_tip)
    material = {state["record"]: state.get("materiality") in folded["material_words"] for state in folded["records"]}
    seen, discoveries = {row.get("record") for row in before}, []
    for row in after[len(before):]:
        if row.get("event") == "opened":
            discoveries.append({"id": row["record"], "material": bool(material.get(row["record"])), "repeat": row["record"] in seen})
            seen.add(row["record"])
    build_after = done[-1]["build_after"] if done else rec["build_before"]
    scoring = scoring_token(layout)
    if scoring != rec["scoring_before"]:
        invalid.append(f"the scoring identity changed during the step: {rec['scoring_before'][:12]} then {scoring[:12]}")
    receipt = read_optional(layout.tier_file(build_after))
    tier = {"green": bool(isinstance(receipt, dict) and receipt.get("green") is True and receipt.get("build") == build_after), "build": build_after}
    return {"build_before": rec["build_before"], "build_after": build_after, "scoring": scoring, "cases": cases, "review": review, "judge": judge,
            "discoveries": discoveries, "candidate": next((item["candidate"] for item in evidence if item["candidate"]), None),
            "invalid": invalid, "tier": tier, "acceptance": next((item["acceptance"] for item in evidence if item["acceptance"]), None),
            "unreconciled": any(item.get("unreconciled") for item in evidence)}


# ----------------------------------------------------------------------------------------------------------- one step, in the worker

def finish_record(layout: Layout, rec: dict) -> None:
    """The step's record also goes beside its artifacts, for whoever reads the run folder later."""
    with contextlib.suppress(OSError):
        write_json(Path(rec["out"]) / "step.json", rec)


def count_runs(rec: dict) -> int:
    return len(run_folders(Path(rec["out"])))


def settle(layout: Layout, rec: dict, state: str, reason: str) -> None:
    """The one path for a step that ends without publishing a tip (failed, cancelled, or a worker that vanished): capture the baseline
    rows its runs wrote, archive whatever its engines left in loop worktrees (before anything is removed), remove the worktrees, put X
    back at the published tip, run the lifecycle cleanup, and write the record. Each part is guarded: the record is always written."""
    notes = []
    with contextlib.suppress(OSError, FacadeError):
        capture_baselines(layout, rec)
    archives = []
    try:
        for tree in worktrees(layout):
            archives.append(salvage(layout, rec, tree))
        remove_worktrees(layout)
    except (OSError, FacadeError) as error:
        notes.append(f"worktree salvage failed: {error}")
    with contextlib.suppress(OSError, FacadeError):
        restore_x(layout)
        position(layout, published_tip(layout))
    try:
        verified, receipt = lifecycle_cleanup(layout, rec)
    except (OSError, FacadeError) as error:
        verified, receipt = False, f"lifecycle cleanup failed: {error}"
    held = [item for item in archives if item["ledger_rows"] or item["commits"] or item["changed_paths"]]
    text = reason + "".join(f"; archive {item['path']} ({item['ledger_rows']} ledger row(s), {item['commits']} commit(s), "
                            f"{item['changed_paths']} changed path(s))" for item in held) + "".join(f"; {note}" for note in notes)
    if not verified:
        text += f"; cleanup: {receipt}"
    started = rec.get("started_epoch") or rec["created_epoch"]
    rec.update(state=state, ended_at=now(), error=text, archives=archives,
               consumed={"seconds": round(max(0.0, time.time() - started), 1), "runs": count_runs(rec)})
    save_step(layout, rec)
    finish_record(layout, rec)


def run_step(layout: Layout, rec: dict) -> None:
    """The invocations in order, each from the tip the one before left; at most one cycle per step (a cycle ends it, the rest are
    `ran: false`); then the facts, the cleanup, the two-phase publication of the new tip."""
    tip, stop = rec["tip_from"], None
    for number, case in enumerate(rec["cases"], 1):
        inv = {"n": number, "case": case, "state": "pending", "out": str(Path(rec["out"]) / f"inv-{number}"), "tip_before": tip,
               "build_before": build_token(layout, tip)}
        rec["invocations"].append(inv)
        if stop:
            inv.update(state="skipped", skip_reason=stop)
            save_step(layout, rec)
            continue
        plan = plan_invocation(layout, rec, case, tip)
        inv.update(generality=plan["generality"], offered=plan["offered"])
        if rec["mode"] == "sweep" and plan["offered"]:
            inv.update(state="skipped", skip_reason=f"record {plan['offered']} is offered for {case}, and a sweep does not run the improver")
            save_step(layout, rec)
            continue
        run_invocation(layout, rec, inv)
        tip = inv["tip_after"]
        if inv["promoted"]:
            inv["tier"] = run_tier(layout, rec, inv)
        if inv["cycle_ran"]:
            stop = f"the cycle on {case} ended this step: a step reports at most one candidate, and the build may have changed"
        save_step(layout, rec)
    facts = derive_iteration(layout, rec)
    removed = remove_worktrees(layout)
    verified, receipt = lifecycle_cleanup(layout, rec)
    leftover = worktrees(layout)
    if leftover:
        verified = False
    unreconciled = facts.pop("unreconciled")
    facts["cleanup"] = {"verified": bool(verified and not unreconciled and not leftover),
                        "receipt": receipt + f"; {len(removed)} loop worktree(s) removed, {len(leftover)} left"
                        + ("; attempts of a cycle may be unsealed" if unreconciled else "")}
    facts["consumed"] = {"seconds": round(time.time() - rec["started_epoch"], 1), "runs": count_runs(rec)}
    rec["iteration"] = facts
    rec["prepared"] = {"tip_from": rec["tip_from"], "tip_to": tip}
    rec["state"] = "prepared"
    save_step(layout, rec)  # phase one: the result and the tip it moves to are durable before the tip moves
    publish(layout, rec)


def publish(layout: Layout, rec: dict) -> None:
    """Phase two, repeatable: move the tip ref from the step's start tip to its result, only from that value. The ref already at the
    result means an earlier attempt finished the move; any other value is refused and reported (plan 3.2 item 7)."""
    prepared = rec["prepared"]
    ref = git(layout.x, "rev-parse", "--verify", "-q", TIP_REF, check=False)
    current = ref or layout.chain()["base"]
    if current != prepared["tip_to"]:
        if current != prepared["tip_from"]:
            raise FacadeError(f"the tip is {current[:12]}, neither {prepared['tip_from'][:12]} (before step {rec['key']}) nor "
                              f"{prepared['tip_to'][:12]} (its result): the tip was not moved")
        try:
            git(layout.x, "update-ref", TIP_REF, prepared["tip_to"], ref or "0" * 40)
        except FacadeError:
            if git(layout.x, "rev-parse", "--verify", "-q", TIP_REF, check=False) != prepared["tip_to"]:
                raise  # not a lost race to the same move: report it
    rec.update(state="published", ended_at=now())
    save_step(layout, rec)
    finish_record(layout, rec)


def worker_main(layout: Layout, key: str) -> int:
    """The detached process behind one step. Its lock is the proof it is alive; a record that is not `starting` is never resumed (a
    step that was running when its worker died is redone, plan 3.2 item 8)."""
    lock = WorkerLock(layout.lock_file(key))
    if not lock.acquire():
        return 0
    try:
        rec = load_step(layout, key)
        if rec is None or rec["state"] != "starting":
            return 0
        rec.update(state="running", worker=identity_of(os.getpid()), started_at=now(), started_epoch=time.time())
        save_step(layout, rec)
        try:
            run_step(layout, rec)
        except FacadeError as error:
            if rec["state"] != "prepared":
                settle(layout, rec, "failed", str(error))
            else:
                raise
        except Exception:  # noqa: BLE001 - whatever else went wrong is the step's failure, with its traceback
            settle(layout, rec, "failed", "unexpected error: " + traceback.format_exc()[-1500:])
    finally:
        lock.release()
    return 0


# ----------------------------------------------------------------------------------------------------------- the step verbs

BOOT_GRACE_SECONDS = 10.0  # a worker just spawned may not hold its lock yet; a step is not called lost before this has passed


def spawn_worker(layout: Layout, rec: dict) -> None:
    log = open(Path(rec["out"]) / "worker.log", "ab")
    try:
        subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "worker", "--key", rec["key"]], cwd=str(layout.state),
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, close_fds=True,
                         env=dict(os.environ, CLOSED_LOOP_WORKSPACE=str(layout.x), PYTHONDONTWRITEBYTECODE="1"))
    finally:
        log.close()


def tail(path: Path, size: int = 400) -> str:
    try:
        return Path(path).read_text(errors="replace")[-size:].strip()
    except OSError:
        return ""


def worker_group(table: dict, worker) -> list:
    """The processes of the worker's group, unless the worker's pid now names another process (then the group is not ours)."""
    if worker is None:
        return []
    leader = table.get(worker["pid"])
    if leader is not None and leader["started"] != worker["started"]:
        return []
    return [row for row in table.values() if row["pgid"] == worker["pgid"]]


def kill_step(layout: Layout, rec: dict) -> dict:
    """End a live step: snapshot what runs below the worker (the model sessions the harness starts in sessions of their own are found
    through parent links only while their parents live, so this comes first), stop the worker's group (the worker and the engine), then
    those sessions. The lifecycle cleanup that follows (`settle`) handles the run hosts the harness recorded."""
    worker = rec.get("worker")
    table = ps_rows()
    members = worker_group(table, worker)  # a worker that died alone leaves its engine in the group: the snapshot starts from them too
    below: dict = {}
    for member in members:
        for row in descendants(table, member["pid"]):
            below[row["pid"]] = row
    extra = [row for row in below.values() if row["pgid"] != worker["pgid"]]
    how, detail = stop_group(worker) if worker else ("gone", {})
    survivors = stop_processes(extra)
    return {"group": how, "detail": detail, "sessions": len(extra), "survivors": [row["pid"] for row in survivors], "at": now()}


def advance(layout: Layout, rec: dict) -> dict:
    """Move a step along whatever its worker left and answer as `poll` does; safe to repeat."""
    rec = load_step(layout, rec["key"]) or rec
    state = rec["state"]
    if state in LIVE:
        if worker_alive(layout, rec["key"]):
            return {"status": "running"}
        if state == "starting":
            if time.time() - rec["created_epoch"] < BOOT_GRACE_SECONDS:
                return {"status": "running"}
            spawn_worker(layout, rec)  # the intent is durable and nothing ran: begin it
            return {"status": "running"}
        if rec.get("worker"):
            rec["kill"] = kill_step(layout, rec)  # a worker that died alone leaves its engine in the group
        settle(layout, rec, "failed", "the step's worker ended without a result (killed or crashed): " + tail(Path(rec["out"]) / "worker.log"))
        state = rec["state"]
    if state == "prepared":
        if worker_alive(layout, rec["key"]):
            return {"status": "running"}  # the worker is finishing: while it lives, it alone moves the tip
        try:
            publish(layout, rec)
        except FacadeError as error:
            rec = load_step(layout, rec["key"])
            if rec["state"] == "prepared":
                settle(layout, rec, "failed", str(error))
        state = rec["state"]
    if state == "published":
        return {"status": "done", "iteration": rec["iteration"]}
    return {"status": state, "error": rec.get("error"), "iteration": {"consumed": rec.get("consumed") or {"seconds": 0.0, "runs": 0}}}


def step_start(layout: Layout, args) -> dict:
    key = check_key(args.key)
    rec = load_step(layout, key)
    if rec is not None:  # idempotent on the key: the same handle, nothing launched twice
        return {"handle": key, **advance(layout, rec)}
    cases = [case for case in args.cases.split(",") if case]
    if not cases or len(set(cases)) != len(cases):
        raise FacadeError("--cases must name at least one case, each once")
    allowed = load_allowlist(layout)
    unknown = [case for case in cases if case not in allowed]
    if unknown:
        raise FacadeError("not in the allowlist: " + ", ".join(unknown))
    if args.mode not in ("iterate", "sweep"):
        raise FacadeError("--mode must be iterate or sweep")
    out = Path(args.out).expanduser().resolve()
    if out == layout.x or layout.x in out.parents or layout.state in (out, *out.parents):
        raise FacadeError(f"--out {out} must be outside the evaluator clone and its state folder")
    if out.exists() and any(out.iterdir()):
        raise FacadeError(f"--out {out} is not empty: a step writes into a folder of its own")
    tip = published_tip(layout)
    build = build_token(layout, tip)
    if args.base != build:
        raise FacadeError(f"the published build is {build}, not the requested base {args.base}: the build moved since the step was planned")
    busy = live_keys(layout)
    if busy:
        raise FacadeError(f"step {busy[0]} is still running in this workspace: one step at a time")
    dirty = x_dirty(layout)
    if dirty:
        raise FacadeError("the evaluator clone has uncommitted paths: " + ", ".join(dirty[:5]))
    out.mkdir(parents=True, exist_ok=True)
    profile = {name: getattr(args, name, None) for name in ("host", "model", "effort", "calibration", "tolerance", "attempts", "parallel")}
    profile["engine_args"] = list(getattr(args, "engine_arg", None) or [])
    rec = {"schema": STEP_SCHEMA, "key": key, "scope": args.scope, "cases": cases, "mode": args.mode, "base": args.base, "out": str(out),
           "profile": profile, "tip_from": tip, "build_before": build, "scoring_before": scoring_token(layout), "state": "starting",
           "created_at": now(), "created_epoch": time.time(), "worker": None, "invocations": [], "iteration": None, "prepared": None,
           "error": None}
    save_step(layout, rec)  # the write-ahead intent: from here a replay of this start finds it
    spawn_worker(layout, rec)
    return {"handle": key, "status": "running"}


def step_poll(layout: Layout, args) -> dict:
    rec = load_step(layout, check_key(args.handle))
    if rec is None:
        raise FacadeError(f"no step with handle {args.handle}")
    return advance(layout, rec)


def step_cancel(layout: Layout, args) -> dict:
    rec = load_step(layout, check_key(args.handle))
    if rec is None:
        raise FacadeError(f"no step with handle {args.handle}")
    if rec["state"] in LIVE:
        killed = kill_step(layout, rec)
        rec = load_step(layout, rec["key"])  # the worker may have finished first: then the step is simply done (never save a stale copy over it)
        if rec["state"] in LIVE:
            rec["kill"] = killed
            settle(layout, rec, "cancelled", "cancelled by the operator")
    return advance(layout, rec)


def cmd_step(args) -> dict:
    layout = layout_from_env()
    return {"start": step_start, "poll": step_poll, "cancel": step_cancel}[args.action](layout, args)


def cmd_cleanup(args) -> dict:
    """`execution.cleanup --keys K1,K2`: end what the named steps may have left and prove it. A step whose worker is still alive (a
    launch whose handle was lost can only be ended here) is stopped first; then the harness's own cleanup runs over each run folder."""
    layout = layout_from_env()
    verified, parts = True, []
    for key in [item for item in args.keys.split(",") if item]:
        rec = load_step(layout, check_key(key))
        if rec is None:
            parts.append(f"{key}: no step record, so this facade launched nothing for it")
            continue
        if rec["state"] in LIVE:
            if worker_alive(layout, key) or rec.get("worker"):
                rec["kill"] = kill_step(layout, rec)
            settle(layout, rec, "cancelled", "ended by cleanup")
        ok, receipt = lifecycle_cleanup(layout, rec)
        save_step(layout, rec)
        verified = verified and ok and not worktrees(layout)
        parts.append(f"{key} ({rec['state']}): {receipt}")
    return {"verified": bool(verified), "receipt": " | ".join(parts) or "no step named"}


def cmd_worker(args) -> dict:
    layout = layout_from_env()
    worker_main(layout, check_key(args.key))
    return {"ok": True}


# ------------------------------------------------------------------------------------------------------------- command line

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="verb", required=True)
    setup = sub.add_parser("setup", help="create the evaluator clone X at a released base commit (run once, before init)")
    setup.add_argument("--workspace", required=True)
    setup.add_argument("--base", required=True, help="a released commit of skill-craft, 2.42.0 or later")
    setup.add_argument("--source", help="the repository to clone (default: the checkout this program is in)")
    sub.add_parser("cases")
    sub.add_parser("records")
    sub.add_parser("identity")
    step = sub.add_parser("step", help="start, poll or cancel one step; the profile flags come first (they are pinned in the manifest)")
    step.add_argument("--host")
    step.add_argument("--model")
    step.add_argument("--effort")
    step.add_argument("--calibration", help="spread.py's report of an A/A epoch (the measured basis)")
    step.add_argument("--tolerance", type=float, help="without --calibration: the stated relative efficiency tolerance")
    step.add_argument("--attempts", type=int, help="without --calibration: the stated attempts per arm")
    step.add_argument("--parallel", type=int, help="attempts run at once")
    step.add_argument("--engine-arg", action="append", help="an extra argument for iterate.py, verbatim (repeatable)")
    actions = step.add_subparsers(dest="action", required=True)
    start = actions.add_parser("start")
    start.add_argument("--key", required=True)
    start.add_argument("--scope", required=True)
    start.add_argument("--cases", required=True)
    start.add_argument("--mode", required=True)
    start.add_argument("--base", required=True)
    start.add_argument("--out", required=True)
    for name in ("poll", "cancel"):
        actions.add_parser(name).add_argument("--handle", required=True)
    cleanup = sub.add_parser("cleanup", help="end what the named steps may have left and prove it")
    cleanup.add_argument("--keys", required=True)
    worker = sub.add_parser("worker", help="internal: the detached process behind one step")
    worker.add_argument("--key", required=True)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"setup": cmd_setup, "cases": cmd_cases, "records": cmd_records, "identity": cmd_identity, "step": cmd_step,
                "cleanup": cmd_cleanup, "worker": cmd_worker}
    try:
        emit(handlers[args.verb](args))
    except FacadeError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
