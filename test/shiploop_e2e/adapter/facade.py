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
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
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

    def step_file(self, key: str) -> Path:
        return self.steps / (check_key(key) + ".json")

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
    out = {"rows": lr.rows(Path(payload["path"]))}
elif op == "scoring_digest":
    import spread
    catalog = json.loads((harness / "cases.json").read_text())
    out = {"sha256": spread.scoring_digest({name: catalog[name] for name in payload["cases"]}, harness)["sha256"]}
else:
    raise SystemExit("unknown bridge operation " + op)
print(json.dumps(out))
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
        return json.loads(done.stdout)
    except ValueError:
        raise FacadeError(f"harness bridge {op} printed no JSON: {done.stdout.strip()[:200]!r}") from None


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
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"setup": cmd_setup, "cases": cmd_cases, "records": cmd_records, "identity": cmd_identity}
    try:
        emit(handlers[args.verb](args))
    except FacadeError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
