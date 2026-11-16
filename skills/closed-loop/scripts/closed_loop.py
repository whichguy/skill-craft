#!/usr/bin/env python3
"""closed_loop.py: the orchestrator of the closed-loop skill.

A campaign improves a *subject* by running it on cases, grading the runs, finding fixes, trying them and repeating until a
script-checked certificate says nothing material is left in a named scope, then widening the scope when it is stuck. Everything
specific to a subject lives in an adapter manifest (closed-loop-adapter/1): pinned argument lists this script calls and whose JSON
it reads. This script never calls a model; the operator (a model) reads what it prints and does one step at a time.

Every verb prints one JSON object on stdout. Exit 0 ok, 1 a check, readiness or authority gate did not pass, 2 error, 3 identity
mismatch.

  adapter-check --manifest M [--proposal P]        validate a manifest (shape, pinned argument lists, execution boundary) and
                                                   a definer proposal (slots, evidence, no grader among the candidate paths)
  init          --manifest M --campaign D --workspace W --cases A,B --budget seconds=3600,turns=400 [--quiet-window K]
                [--approve-case ID --yes-owner-approved]
  ratify        --campaign D --yes-owner-approved [--note TEXT]   record the owner's approval of the execution boundary
  readiness     --manifest M [--campaign D] [--workspace W] [--require-start]   claim states and the claims they allow
  status        --campaign D [--no-certificate]    scope, quota, readiness, last iteration, certificate
  next          --campaign D                       print the next action without doing it
  step          --campaign D                       do the next action: start or poll a step, open a scope, add a task, or stop
  task          --campaign D add --kind K --text T [--needs-owner] | done --id I [--result JSON] [--consumed JSON] [--approve]
  unknown       --campaign D add --text T [--inside-claim] | resolve --index N --evidence TEXT   record what is not known (C7 reads it)
  approve       --campaign D --case ID --yes-owner-approved [--note TEXT]   allow an owner-gated case and reopen
  reopen        --campaign D --yes-owner-approved [--budget k=v,...] [--note TEXT]   clear a stop the owner has resolved
  cancel        --campaign D --key K               cancel a running step
  cleanup       --campaign D                       run the adapter's owned cleanup for every unverified run
  check         --campaign D --clause C1..C7 [--expect-sha SHA] [--expect-scope S] [--expect-identity ID]   one check
  certificate   --campaign D                       all seven checks: converged, or incomplete with reasons
  coverage      --campaign D                       what the scope covers, what it does not, which cases could widen it
  contract      --campaign D [--out FILE]          an until-loop contract with script-owned exit checks for the current scope
  report        --campaign D                       write report.md and report.json for the owner

Campaign folder D (a small Git repo, so the Until Loop can fingerprint every state change): campaign.json
(closed-loop-campaign/1, atomic, under campaign.lock), journal.md (append-only, one entry per iteration), report.md, report.json.
Bulky files go in the sibling folder D.work: runs/<step key>/ (what the adapter writes), and the Until Loop's own state, contracts
and receipts, which must stay outside D.

Adapter protocol (closed-loop-adapter/1). The manifest's `commands` hold argument lists for these verbs; each prints one JSON
object. CLOSED_LOOP_WORKSPACE names the subject's working directory; only PATH and `execution.env_allow` names reach the child.
  cases     -> {"cases": [{"id", "dimensions": {name: value}, "cost", "requires": [...], "hosted": bool}]}
  records   -> {"records": [{"id", "title", "material", "target": "subject"|"adapter", "status", "evidence", "reopen_when",
                             "cases": [...]}]}
  identity  -> {"scoring": token, "build": token}
  probe ID  -> {"state", "evidence", "consumed"?}                  (readiness claims)
  step start --key K --scope S --cases A,B --mode iterate|sweep --base TIP --out DIR -> {"handle", "status", "iteration"?}
       (idempotent on K: a second start with the same key returns the same handle and launches nothing)
  step poll --handle H   -> {"status": "running"|"done"|"failed"|"cancelled", "iteration"?, "error"?}
  step cancel --handle H -> {"status": "cancelled"}
  execution.cleanup + --keys K1,K2 -> {"verified": bool, "receipt": str}
  An `iteration` object carries: build_before, build_after, scoring, cases {id: {ran, floors_met, baseline}} for exactly the
  requested cases, review/judge {valid, complete}, discoveries [{id, material, repeat}], candidate {id, hash, outcome} or null,
  invalid [...], cleanup {verified, receipt}, tier {green, build}, acceptance {candidate, evidence} or null, consumed {key: amount}.
  Evidence of any other shape is rejected: the step is recorded as failed, never as a quiet iteration.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import secrets
import shlex
import signal
import subprocess
import sys
import tempfile
import time

CAMPAIGN_SCHEMA = "closed-loop-campaign/1"
ADAPTER_SCHEMA = "closed-loop-adapter/1"
DEFINER_SCHEMA = "closed-loop-definer/1"
SLOT_NAMES = ("mission", "cases", "steps", "evaluation", "improvement", "authority", "records")
SLOT_STATUSES = ("found", "proposed", "unknown")
SCRIPT = Path(__file__).resolve()
CAPABILITIES = ("read-only", "writes-worktree", "hosted")
EVAL_CLASSES = ("scripted", "scripted+judge", "judge-only")
REQUIRED_VERBS = ("cases", "records", "identity", "step")
KNOWN_VERBS = REQUIRED_VERBS + ("probe",)
CLAUSES = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
CLAUSE_TEXT = {
    "C1": "Every material in-scope record is resolved with evidence (a deferred, owner-held or unresolved material record keeps "
          "the scope incomplete), and no task is open.",
    "C2": "The last K iterations at this scope, build and scoring identity were quiet: valid complete reviews, no material "
          "discovery, no candidate pending.",
    "C3": "Every scope case meets its floors on the current build against a comparable baseline.",
    "C4": "Every dimension value and declared combination the scope covers has a run on the current build, and every catalog value "
          "outside it is listed as not covered.",
    "C5": "Every run the campaign started was cleaned up with positive evidence, and a green quick-tier receipt exists for the "
          "current build.",
    "C6": "A promoted candidate's acceptance evidence names the same candidate; with nothing promoted there is no candidate to "
          "accept.",
    "C7": "No invalid, incomplete or missing evidence in the quiet window, and no unknown inside the scope's claim.",
}
CLAIM_LADDERS = {
    "cases.runs": ("declared", "runs"),
    "grading.scores": ("declared", "scores"),
    "grading.sensitive": ("unknown", "sensitive"),
    "grading.calibrated": ("unmeasured", "calibrated"),
    "improver.bounded": ("declared", "bounded"),
    "improver.invocable": ("declared", "invocable"),
}
RESOLVED_STATUSES = ("verified", "dropped", "refuted", "rejected")
ACTIONABLE_STATUSES = ("open", "admitted", "promoted", "undecided")
BASELINES = ("comparable", "none", "unknown")
OUTCOMES = ("PROMOTE", "DROP", "UNDECIDED")
HUNT_DISPOSITIONS = ("rejected", "deferred-to-owner", "added-as-task")
PROGRESS_STOP = 3
DEFAULT_TIMEOUT = 3600
DEFAULT_STEP_TIMEOUT = 21600
FINGERPRINT_EXCLUDES = (".shiploop-improve", ".shiploop", ".until-loop", ".git")  # what the Until Loop's fingerprint leaves out
GIT_TIMEOUT = 60
LOCK_WAIT_SECONDS = 30
EXIT_OK, EXIT_NOT_READY, EXIT_ERROR, EXIT_IDENTITY = 0, 1, 2, 3
FAILED_CALLS = {"seconds": 0.0}  # wall time of adapter calls that failed during this command; session() charges it to the quota


class LoopError(Exception):
    """A refusal or a failure the operator should read; main() prints it and exits 2."""


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def script_sha() -> str:
    return sha256_file(SCRIPT)


def is_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_amount(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


# ---------------------------------------------------------------------------------------------------------------- manifest

def argv_errors(label: str, argv) -> list:
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        return [f"{label} must be a non-empty argument list of strings (no shell strings)"]
    if any(ch.isspace() for ch in argv[0]):
        return [f"{label}[0] contains whitespace: pass the program and each argument as separate items"]
    return []


def validate_manifest(m) -> list:
    if not isinstance(m, dict):
        return ["the manifest must be a JSON object"]
    errors = []
    if m.get("contract") != ADAPTER_SCHEMA:
        errors.append(f"contract must be {ADAPTER_SCHEMA}")
    subject = m.get("subject")
    if not isinstance(subject, dict) or not is_text(subject.get("name")):
        errors.append("subject.name is required")
    execution = m.get("execution")
    if not isinstance(execution, dict):
        errors.append("execution (the execution boundary) is required")
    else:
        if execution.get("capability") not in CAPABILITIES:
            errors.append("execution.capability must be one of " + ", ".join(CAPABILITIES))
        env = execution.get("env_allow", [])
        if not (isinstance(env, list) and all(is_text(name) for name in env)):
            errors.append("execution.env_allow must be a list of environment variable names")
        if execution.get("cleanup") is not None:
            errors += argv_errors("execution.cleanup", execution["cleanup"])
        pin = execution.get("pin", [])
        if not (isinstance(pin, list) and all(is_text(item) for item in pin)):
            errors.append("execution.pin must be a list of file or folder paths the boundary hash covers")
        timeout = execution.get("timeout_seconds", DEFAULT_TIMEOUT)
        if not is_amount(timeout) or timeout <= 0:
            errors.append("execution.timeout_seconds must be a positive number")
        step_timeout = execution.get("step_timeout_seconds", DEFAULT_STEP_TIMEOUT)
        if not is_amount(step_timeout) or step_timeout <= 0:
            errors.append("execution.step_timeout_seconds must be a positive number")
    commands = m.get("commands")
    if not isinstance(commands, dict):
        errors.append("commands is required")
    else:
        for verb in REQUIRED_VERBS:
            if verb not in commands:
                errors.append(f"commands.{verb} is required")
        for verb, argv in commands.items():
            if verb not in KNOWN_VERBS:
                errors.append(f"commands.{verb} is not a known verb ({', '.join(KNOWN_VERBS)})")
            else:
                errors += argv_errors(f"commands.{verb}", argv)
    claims = m.get("claims", {})
    if not isinstance(claims, dict):
        errors.append("claims must be an object of claim id to {effect}")
    else:
        for claim, meta in claims.items():
            if claim.split(":")[0] not in CLAIM_LADDERS:
                errors.append(f"claim {claim!r} has an unknown kind; kinds: {', '.join(CLAIM_LADDERS)}")
            if not isinstance(meta, dict) or meta.get("effect") not in ("read-only", "effectful"):
                errors.append(f"claim {claim!r} needs effect read-only or effectful")
        if claims and "probe" not in (commands or {}):
            errors.append("claims are declared but commands.probe is missing")
    dims = m.get("dimensions", [])
    if not (isinstance(dims, list) and all(is_text(name) for name in dims)):
        errors.append("dimensions must be a list of dimension names")
        dims = []
    combos = m.get("combinations", [])
    if not (isinstance(combos, list) and all(isinstance(combo, list) and len(combo) >= 2 and all(name in dims for name in combo)
                                            for combo in combos)):
        errors.append("combinations must be lists of at least two declared dimension names")
    window_size = m.get("quiet_window", 2)
    if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size < 1:
        errors.append("quiet_window must be an integer of at least 1")
    klass = m.get("evaluation_class", "scripted")
    if klass not in EVAL_CLASSES:
        errors.append("evaluation_class must be one of " + ", ".join(EVAL_CLASSES))
    if klass == "judge-only" and not isinstance(m.get("judge_reliability"), dict):
        errors.append("a judge-only evaluation_class needs judge_reliability recorded (kappa and noise)")
    authority = m.get("authority", {})
    if not isinstance(authority, dict) or not all(isinstance(authority.get(key, []), list)
                                                  for key in ("routine", "owner_only", "owner_only_requires")):
        errors.append("authority needs list values for routine, owner_only and owner_only_requires")
    return errors


def load_manifest(path) -> tuple:
    manifest_path = Path(path).resolve()
    try:
        manifest = json.loads(manifest_path.read_text())
    except OSError as error:
        raise LoopError(f"cannot read the manifest {manifest_path}: {error.strerror}") from None
    except ValueError as error:
        raise LoopError(f"the manifest {manifest_path} is not JSON: {error}") from None
    errors = validate_manifest(manifest)
    if errors:
        raise LoopError("invalid adapter manifest: " + "; ".join(errors))
    return manifest, manifest_path


def pin_digest(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    if path.is_dir():
        rows = [(item.relative_to(path).as_posix(), sha256_file(item)) for item in sorted(path.rglob("*"))
                if item.is_file() and "__pycache__" not in item.parts and ".git" not in item.parts]
        return sha256_text(canonical(rows))
    raise LoopError(f"pinned path {path} does not exist")


def boundary_hash(manifest: dict, manifest_dir: Path) -> str:
    """What the owner ratifies: every command, the execution boundary, the authority lists, the claims, and the content of every
    pinned adapter or evaluator file."""
    keys = ("commands", "execution", "authority", "claims", "evaluation_class", "combinations")
    body = {key: manifest.get(key) for key in keys}
    body["pins"] = {item: pin_digest(Path(manifest_dir) / item) for item in manifest["execution"].get("pin", [])}
    return sha256_text(canonical(body))


def run_argv(manifest: dict, manifest_dir: Path, argv: list, label: str, workspace=None, campaign=None) -> dict:
    """Run one pinned argument list in the controlled environment and return the JSON object it prints. A failed call still costs
    the time it took: that is recorded so a hanging adapter cannot be retried for free."""
    started = time.monotonic()
    try:
        return run_argv_once(manifest, manifest_dir, argv, label, workspace, campaign)
    except LoopError:
        FAILED_CALLS["seconds"] += time.monotonic() - started
        raise


def kill_group(process) -> None:
    """Kill a timed-out adapter call with everything it started, then collect what is left without waiting on a pipe a
    daemonised grandchild might still hold."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        for stream in (process.stdout, process.stderr):
            stream.close()
        process.poll()


def run_argv_once(manifest: dict, manifest_dir: Path, argv: list, label: str, workspace, campaign) -> dict:
    execution = manifest["execution"]
    env = {"PATH": os.environ.get("PATH", os.defpath)}
    for name in execution.get("env_allow", []):
        if name in os.environ:
            env[name] = os.environ[name]
    if workspace:
        env["CLOSED_LOOP_WORKSPACE"] = str(workspace)
    if campaign:
        env["CLOSED_LOOP_CAMPAIGN"] = str(campaign)
    cwd = (Path(manifest_dir) / execution.get("cwd", ".")).resolve()
    timeout = execution.get("timeout_seconds", DEFAULT_TIMEOUT)
    try:
        # Its own session, so a timeout can kill the whole process group and not only the program the argument list names: a
        # grandchild holding the output pipe would otherwise keep the call, and the campaign lock, waiting long after the timeout.
        process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
    except OSError as error:
        raise LoopError(f"adapter {label} could not start ({argv[0]}): {error.strerror}") from None
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(process)
        raise LoopError(f"adapter {label} did not finish within {timeout} s (execution.timeout_seconds); its process group was "
                        "killed") from None
    if process.returncode != 0:
        raise LoopError(f"adapter {label} exited {process.returncode}: {(stderr or stdout).strip()[-400:]}")
    try:
        out = json.loads(stdout)
    except ValueError:
        raise LoopError(f"adapter {label} printed no JSON object: {stdout.strip()[:200]!r}") from None
    if not isinstance(out, dict):
        raise LoopError(f"adapter {label} must print a JSON object")
    return out


def call_adapter(manifest: dict, manifest_dir: Path, verb: str, args=(), workspace=None, campaign=None) -> dict:
    if verb not in manifest["commands"]:
        raise LoopError(f"the adapter has no {verb} command")
    argv = list(manifest["commands"][verb]) + [str(arg) for arg in args]
    return run_argv(manifest, manifest_dir, argv, verb, workspace, campaign)


# -------------------------------------------------------------------------------------------------------------------- state

STATE_KEYS = {"id": str, "subject": str, "workspace": str, "manifest": dict, "budget": dict, "consumed": dict, "scopes": list,
              "scope": str, "iterations": list, "steps": dict, "tasks": list, "unknowns": list, "approved_cases": list,
              "events": list, "start_failures": dict, "poll_failures": dict, "launch_intents": dict, "cleaned_launches": dict}
ITERATION_TEXT = ("key", "scope", "mode", "scoring", "build_before", "build_after")
ITERATION_DICTS = ("cases", "review", "judge", "cleanup", "tier", "consumed")


def validate_state(state) -> None:
    def need(condition, why):
        if not condition:
            raise LoopError("campaign state is malformed: " + why)

    need(isinstance(state, dict), "it is not an object")
    for key, kind in STATE_KEYS.items():
        need(isinstance(state.get(key), kind), f"{key} must be a {kind.__name__}")
    window_size = state.get("quiet_window")
    need(isinstance(window_size, int) and not isinstance(window_size, bool) and window_size >= 1,
         "quiet_window must be an integer of at least 1")
    need(state["budget"] and all(is_amount(value) and value > 0 for value in state["budget"].values()),
         "budget must name at least one positive limit")
    need(all(is_amount(value) for value in state["consumed"].values()), "consumed must hold non-negative numbers")
    for scope in state["scopes"]:
        need(isinstance(scope, dict) and is_text(scope.get("id")) and isinstance(scope.get("cases"), list) and scope["cases"]
             and isinstance(scope.get("values"), list) and isinstance(scope.get("not_covered"), dict)
             and isinstance(scope.get("sweep_pending"), bool), "a scope is missing a field")
    need(state["scope"] in {scope["id"] for scope in state["scopes"]}, "the current scope is not in scopes")
    for item in state["iterations"]:
        need(isinstance(item, dict), "an iteration is not an object")
        need(all(is_text(item.get(key)) for key in ITERATION_TEXT), "an iteration lacks a scope, key, mode or identity")
        need(all(isinstance(item.get(key), dict) for key in ITERATION_DICTS), "an iteration lacks a results object")
        need(isinstance(item.get("quiet"), bool) and isinstance(item.get("invalid"), list)
             and isinstance(item.get("discoveries"), list) and isinstance(item.get("index"), int), "an iteration is malformed")
        if item.get("failed") is True:
            need(item["quiet"] is False and item["invalid"], f"iteration {item['index']} failed, so it must be invalid and never quiet")
        else:
            facts = iteration_facts(item)
            problems = validate_facts(facts, item.get("requested") or [])
            need(not problems, f"iteration {item['index']} holds malformed evidence: " + "; ".join(problems[:2]))
            need(item["quiet"] == (not quiet_reasons(facts, item["invalid"])),
                 f"iteration {item['index']}'s quiet flag does not follow from its evidence")
    for step in state["steps"].values():
        need(isinstance(step, dict) and is_text(step.get("status")) and isinstance(step.get("cases"), list),
             "a step record is malformed")
        if step["status"] == "running":
            need(is_amount(step.get("started_epoch")), "a running step lacks its start time")
    for task in state["tasks"]:
        need(isinstance(task, dict) and is_text(task.get("id")) and is_text(task.get("kind")) and is_text(task.get("status")),
             "a task is malformed")
    need(all(isinstance(item, dict) for item in state["unknowns"]), "an unknown is malformed")
    need(all(isinstance(value, dict) and is_text(value.get("base")) for value in state["launch_intents"].values()),
         "a launch intent is malformed")
    need(all(isinstance(value, list) for value in state["start_failures"].values())
         and all(isinstance(value, list) for value in state["poll_failures"].values()), "a failure list is malformed")
    need(all(is_text(value) for value in state["cleaned_launches"].values()), "a cleaned launch lacks its receipt")


@contextlib.contextmanager
def locked(campaign_dir: Path, create: bool = False):
    if create:
        campaign_dir.mkdir(parents=True, exist_ok=True)
    elif not campaign_dir.is_dir():
        raise LoopError(f"no campaign folder {campaign_dir}: run init (a campaign folder is never created by another verb)")
    with open(campaign_dir / "campaign.lock", "a") as handle:
        waited = 0.0
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if waited >= LOCK_WAIT_SECONDS:
                    raise LoopError(f"another closed_loop command has held the campaign lock for {LOCK_WAIT_SECONDS:g} s: wait for "
                                    "it, or look for a hung adapter call (execution.timeout_seconds bounds one)") from None
                time.sleep(0.05)
                waited += 0.05
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_state(campaign_dir: Path) -> dict:
    path = campaign_dir / "campaign.json"
    if not path.is_file():
        raise LoopError(f"no campaign state at {path}: run init (state is never recreated silently)")
    try:
        state = json.loads(path.read_text())
    except ValueError as error:
        raise LoopError(f"campaign state {path} is unreadable ({error}); refusing to replace it") from None
    if not isinstance(state, dict) or state.get("schema") != CAMPAIGN_SCHEMA:
        raise LoopError(f"campaign state {path} is not a {CAMPAIGN_SCHEMA} file; refusing to use it")
    validate_state(state)
    return state


def save_state(campaign_dir: Path, state: dict) -> None:
    state["updated"] = now()
    path = campaign_dir / "campaign.json"
    tmp = campaign_dir / "campaign.json.tmp"
    with open(tmp, "w") as handle:
        handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


class Campaign:
    """A loaded campaign: its folder, state, adapter manifest and the adapter calls that use them."""

    def __init__(self, campaign_dir, state=None, manifest=None, manifest_path=None) -> None:
        self.dir = Path(campaign_dir).resolve()
        self.state = state if state is not None else load_state(self.dir)
        if manifest is None:
            manifest, manifest_path = load_manifest(self.state["manifest"]["path"])
            changed = (sha256_file(manifest_path) != self.state["manifest"]["sha256"]
                       or boundary_hash(manifest, manifest_path.parent) != self.state["manifest"]["boundary_sha256"])
            if changed:
                raise LoopError("the adapter manifest, its commands or a pinned file changed since init: its identity differs, "
                                "start a new campaign")
        self.manifest, self.manifest_path = manifest, manifest_path
        check_state_against_manifest(self.state, self.manifest)
        self.catalog = None  # the adapter's case catalog, fetched once per command

    def call(self, verb: str, args=()) -> dict:
        return call_adapter(self.manifest, self.manifest_path.parent, verb, args, workspace=self.state["workspace"],
                            campaign=self.dir)

    def save(self) -> None:
        save_state(self.dir, self.state)

    def event(self, what: str, **fields) -> None:
        self.state["events"].append({"at": now(), "event": what, **fields})

    @property
    def boundary(self) -> str:
        return boundary_hash(self.manifest, self.manifest_path.parent)

    @property
    def identity(self) -> str:
        return sha256_text(self.state["manifest"]["sha256"] + script_sha() + self.state["manifest"]["boundary_sha256"])[:16]

    @property
    def work_dir(self) -> Path:
        return self.dir.parent / (self.dir.name + ".work")

    def scope(self) -> dict:
        return next(item for item in self.state["scopes"] if item["id"] == self.state["scope"])


class Facts:
    """Adapter queries a certificate needs, fetched once each per command and checked for shape."""

    def __init__(self, camp: Campaign) -> None:
        self.camp = camp
        self._records = self._catalog = self._identity = None

    @property
    def records(self) -> list:
        if self._records is None:
            out = self.camp.call("records").get("records")
            if not isinstance(out, list) or not all(
                    isinstance(rec, dict) and is_text(rec.get("id")) and is_text(rec.get("status"))
                    and isinstance(rec.get("material"), bool) and rec.get("target") in (None, "subject", "adapter")
                    and (rec.get("cases") is None or (isinstance(rec["cases"], list) and all(is_text(c) for c in rec["cases"])))
                    for rec in out):
                raise LoopError('adapter records must print {"records": [{"id", "status", "material": bool, "target"?: subject|adapter, '
                                '"cases"?: [case ids], ...}]}')
            self._records = out
        return self._records

    @property
    def catalog(self) -> dict:
        if self._catalog is None:
            self._catalog = load_catalog(self.camp)
        return self._catalog

    @property
    def identity(self) -> dict:
        if self._identity is None:
            out = self.camp.call("identity")
            if not (is_text(out.get("build")) and is_text(out.get("scoring"))):
                raise LoopError("adapter identity must print non-empty text for build and scoring")
            self._identity = out
        return self._identity


def load_catalog(camp: Campaign) -> dict:
    if camp.catalog is not None:
        return camp.catalog
    cases = camp.call("cases").get("cases")
    if not isinstance(cases, list) or not cases:
        raise LoopError('adapter cases must print {"cases": [...]} with at least one case')
    catalog = {}
    for case in cases:
        if not isinstance(case, dict) or not is_text(case.get("id")):
            raise LoopError("every adapter case needs an id")
        if case["id"] in catalog:
            raise LoopError(f"the adapter lists case {case['id']} twice")
        if not isinstance(case.get("dimensions", {}), dict) or not isinstance(case.get("requires", []), list) \
                or not isinstance(case.get("hosted", False), bool) or not is_amount(case.get("cost", 1)):
            raise LoopError(f"case {case['id']} needs dimensions {{}}, requires [], hosted bool and a non-negative cost")
        catalog[case["id"]] = case
    camp.catalog = catalog
    return catalog


def case_values(case: dict, dims: list, combos: list) -> set:
    found = case.get("dimensions") or {}
    values = {f"{name}={found[name]}" for name in dims if name in found}
    for combo in combos:
        if all(name in found for name in combo):
            values.add("&".join(f"{name}={found[name]}" for name in combo))
    return values


def open_scope(camp: Campaign, scope_id: str, cases: list, reason: str, sweep: bool, catalog: dict) -> dict:
    dims, combos = camp.manifest.get("dimensions", []), camp.manifest.get("combinations", [])
    inside = set()
    for case_id in cases:
        inside |= case_values(catalog[case_id], dims, combos)
    everything = set()
    for case in catalog.values():
        everything |= case_values(case, dims, combos)
    listed = dict(camp.manifest.get("not_covered", {}))
    not_covered = {value: listed.get(value, "outside this scope: a widening candidate") for value in sorted(everything - inside)}
    return {"id": scope_id, "cases": list(cases), "values": sorted(inside), "not_covered": not_covered,
            "opened_iteration": len(camp.state["iterations"]), "opened": now(), "reason": reason, "sweep_pending": sweep}


def parse_budget(text) -> dict:
    budget = {}
    for part in filter(None, (text or "").split(",")):
        key, _, value = part.partition("=")
        try:
            number = float(value)
        except ValueError:
            raise LoopError(f"budget {part!r} must look like seconds=3600") from None
        if not key or not math.isfinite(number) or number <= 0:
            raise LoopError(f"budget {part!r} needs a name and a positive amount")
        budget[key] = int(number) if number == int(number) else number
    return budget


def over_budget(budget: dict, used: dict) -> list:
    return sorted(key for key, limit in budget.items() if used.get(key, 0) >= limit)


def running_seconds(state: dict) -> float:
    """Wall time that steps still in flight have spent; the adapter reports their cost only when they finish."""
    return sum(max(0.0, time.time() - step["started_epoch"]) for step in state.get("steps", {}).values()
               if step.get("status") == "running" and is_amount(step.get("started_epoch")))


def used_amounts(state: dict) -> dict:
    used = dict(state.get("consumed") or {})
    running = running_seconds(state)
    if running:
        used["seconds"] = used.get("seconds", 0) + running  # `seconds` is wall-clock: a run in flight counts as it runs
    return used


def quota_status(state: dict) -> dict:
    budget, used = state.get("budget") or {}, used_amounts(state)
    over = over_budget(budget, used)
    return {"budget": budget, "consumed": state.get("consumed") or {}, "running_seconds": round(running_seconds(state), 3),
            "exhausted": bool(over), "over": over}


def add_consumed(state: dict, amounts) -> None:
    if isinstance(amounts, dict):
        for name, amount in amounts.items():
            if is_amount(amount):
                state["consumed"][name] = state["consumed"].get(name, 0) + amount


# -------------------------------------------------------------------------------------------------------------- iterations

def validate_facts(facts, requested: list) -> list:
    """Why an adapter's iteration report cannot be trusted as evidence, or an empty list."""
    if not isinstance(facts, dict):
        return ["the iteration is not a JSON object"]
    errors = []
    for key in ("build_before", "build_after", "scoring"):
        if not is_text(facts.get(key)):
            errors.append(f"{key} must be non-empty text")
    cases = facts.get("cases")
    if not isinstance(cases, dict):
        errors.append("cases must be an object")
    else:
        missing, extra = sorted(set(requested) - set(cases)), sorted(set(cases) - set(requested))
        if missing:
            errors.append("no result for requested cases: " + ", ".join(missing))
        if extra:
            errors.append("results for cases that were not requested: " + ", ".join(extra))
        for case_id, result in cases.items():
            if not (isinstance(result, dict) and isinstance(result.get("ran"), bool) and isinstance(result.get("floors_met"), bool)
                    and result.get("baseline") in BASELINES):
                errors.append(f"case {case_id} needs boolean ran and floors_met and a baseline of {', '.join(BASELINES)}")
    for key in ("review", "judge"):
        part = facts.get(key)
        if not (isinstance(part, dict) and isinstance(part.get("valid"), bool) and isinstance(part.get("complete"), bool)):
            errors.append(f"{key} needs boolean valid and complete")
    discoveries = facts.get("discoveries")
    if not (isinstance(discoveries, list) and all(isinstance(item, dict) and is_text(item.get("id"))
                                                  and isinstance(item.get("material"), bool) for item in discoveries)):
        errors.append("discoveries must be a list of {id, material: bool}")
    candidate = facts.get("candidate")
    if candidate is not None and not (isinstance(candidate, dict) and is_text(candidate.get("id")) and is_text(candidate.get("hash"))
                                      and candidate.get("outcome") in OUTCOMES):
        errors.append("candidate must be null or {id, hash, outcome: " + "|".join(OUTCOMES) + "}")
    if not (isinstance(facts.get("invalid"), list) and all(isinstance(item, str) for item in facts["invalid"])):
        errors.append("invalid must be a list of text")
    if is_text(facts.get("build_before")) and is_text(facts.get("build_after")):
        changed = facts["build_after"] != facts["build_before"]
        promoted = isinstance(candidate, dict) and candidate.get("outcome") == "PROMOTE"
        if promoted and not changed:
            errors.append("a promoted candidate must change the build, and this one left it unchanged")
        if changed and not promoted:
            errors.append("the build changed without a promoted candidate: only a promotion may move it")
    cleanup = facts.get("cleanup")
    if not (isinstance(cleanup, dict) and isinstance(cleanup.get("verified"), bool)
            and (not cleanup["verified"] or is_text(cleanup.get("receipt")))):
        errors.append("cleanup needs boolean verified and, when verified, a receipt")
    tier = facts.get("tier")
    if not (isinstance(tier, dict) and isinstance(tier.get("green"), bool) and is_text(tier.get("build"))):
        errors.append("tier needs boolean green and the build it covers")
    acceptance = facts.get("acceptance")
    if acceptance is not None and not (isinstance(acceptance, dict) and is_text(acceptance.get("candidate"))
                                       and is_text(acceptance.get("evidence"))):
        errors.append("acceptance must be null or {candidate, evidence}")
    consumed = facts.get("consumed")
    if not (isinstance(consumed, dict) and all(is_amount(value) for value in consumed.values())):
        errors.append("consumed must hold finite non-negative numbers")
    return errors


def quiet_reasons(facts: dict, invalid: list) -> list:
    """Why a finished step is not a quiet iteration; empty when it is. Used when a step finishes and again when state is loaded."""
    reasons = []
    review, judge, cases = facts["review"], facts["judge"], facts["cases"]
    if not (review["valid"] and review["complete"]):
        reasons.append("the review was not valid and complete")
    if not (judge["valid"] and judge["complete"]):
        reasons.append("the judge was not valid and complete")
    if invalid:
        reasons.append("invalid or incomplete evidence was recorded")
    if any(item["material"] for item in facts["discoveries"]):
        reasons.append("a material discovery, new or repeated")
    if facts["candidate"]:
        reasons.append("a candidate outcome is present")
    if not all(item["ran"] and item["floors_met"] for item in cases.values()):
        reasons.append("a scope case did not run or missed its floors")
    return reasons


def iteration_facts(item: dict) -> dict:
    """The part of a recorded iteration that the adapter reported, in the shape validate_facts reads."""
    return {key: item.get(key) for key in ("build_before", "build_after", "scoring", "cases", "review", "judge", "discoveries",
                                           "candidate", "invalid", "cleanup", "tier", "acceptance", "consumed")}


def derive_iteration(state: dict, key: str, step: dict, facts: dict) -> dict:
    """The orchestrator's own record of one finished step: what the adapter reported, and whether it was quiet."""
    invalid = list(facts["invalid"])
    if step.get("base") and facts["build_before"] != step["base"]:
        invalid.append(f"the iteration ran on build {facts['build_before']} but the base was {step['base']}")
    reasons = quiet_reasons(facts, invalid)
    review, judge, cases = facts["review"], facts["judge"], facts["cases"]
    return {
        "index": len(state["iterations"]) + 1, "key": key, "scope": step["scope"], "mode": step["mode"], "ended": now(),
        "requested": list(step["cases"]), "build_before": facts["build_before"], "build_after": facts["build_after"],
        "scoring": facts["scoring"], "cases": cases, "review": review, "judge": judge, "discoveries": facts["discoveries"],
        "candidate": facts["candidate"], "invalid": invalid, "cleanup": facts["cleanup"], "tier": facts["tier"],
        "acceptance": facts["acceptance"], "consumed": facts["consumed"], "quiet": not reasons, "quiet_reasons": reasons,
        "failed": False}


def failed_iteration(state: dict, key: str, step: dict, error: str, reported) -> dict:
    """A step that failed, was cancelled or reported evidence that cannot be trusted: an invalid, never-quiet iteration."""
    last = state["iterations"][-1] if state["iterations"] else None
    base = step.get("base") or state.get("tip") or "unknown"
    consumed = reported.get("consumed") if isinstance(reported, dict) else None
    return {
        "index": len(state["iterations"]) + 1, "key": key, "scope": step["scope"], "mode": step["mode"], "ended": now(),
        "requested": list(step["cases"]), "build_before": base, "build_after": base,
        "scoring": last["scoring"] if last else "unknown", "cases": {}, "review": {}, "judge": {}, "discoveries": [],
        "candidate": None, "invalid": [error], "cleanup": {}, "tier": {}, "acceptance": None,
        "consumed": {name: amount for name, amount in (consumed or {}).items() if is_amount(amount)} if isinstance(consumed, dict)
        else {}, "quiet": False, "quiet_reasons": ["the step failed: " + error], "failed": True}


def window(state: dict) -> list:
    """The trailing iterations at the *active* scope that ran on the current build and scoring identity."""
    out, newest = [], None
    for item in reversed(state["iterations"]):
        if item["scope"] != state["scope"]:
            break
        newest = newest or item
        if item["scoring"] != newest["scoring"] or item["build_before"] != newest["build_after"]:
            break
        out.append(item)
    return list(reversed(out))


def stale_reason(camp: Campaign, facts: Facts):
    """Why the last iteration no longer describes the subject, or None."""
    iterations = camp.state["iterations"]
    if not iterations:
        return None
    last, current = iterations[-1], facts.identity
    if current["build"] != last["build_after"]:
        return f"the subject's build is now {current['build']!r}, the last iteration left {last['build_after']!r}"
    if current["scoring"] != last["scoring"]:
        return f"the scoring identity is now {current['scoring']!r}, the last iteration used {last['scoring']!r}"
    return None


def regression_reason(state: dict):
    """A case that met its floors before a promoted candidate and misses them on the build it produced."""
    iterations = state["iterations"]
    if len(iterations) < 2:
        return None
    last, prev = iterations[-1], iterations[-2]
    if last["failed"] or prev["failed"] or (last["scope"], last["scoring"]) != (prev["scope"], prev["scoring"]):
        return None
    if prev["build_before"] == prev["build_after"] or last["build_before"] != prev["build_after"]:
        return None
    for case_id, result in last["cases"].items():
        before = prev["cases"].get(case_id)
        if before and before.get("floors_met") and not result.get("floors_met"):
            return (f"metric regression: {case_id} met its floors before candidate {(prev['candidate'] or {}).get('id')} and "
                    f"misses them on build {last['build_before']}; halt, nothing is reverted")
    return None


def no_progress_run(state: dict) -> int:
    """Trailing iterations at this scope with no quiet pass, no promotion and no finished task since."""
    floor = max([task.get("done_after", 0) for task in state["tasks"] if task["status"] == "done"] or [0])
    run = 0
    for item in reversed(state["iterations"]):
        if item["scope"] != state["scope"] or item["index"] <= floor:
            break
        if item["quiet"] or (item.get("candidate") or {}).get("outcome") == "PROMOTE":
            break
        run += 1
    return run


# ---------------------------------------------------------------------------------------------------------- the seven checks

def verdict(clause: str, reasons: list, **detail) -> dict:
    return {"id": clause, "pass": not reasons, "reasons": reasons, "detail": detail}


def check_c1(camp: Campaign, facts: Facts) -> dict:
    scope_cases = set(camp.scope()["cases"])
    blocking, actionable, owner_gated, outside, adapter_backlog = [], [], [], [], []
    for rec in facts.records:
        if rec.get("target", "subject") == "adapter":
            adapter_backlog.append(rec["id"])
            continue
        if not rec["material"]:
            continue
        related = rec.get("cases")
        if related and not (set(related) & scope_cases):
            outside.append(rec["id"])
            continue
        status = rec["status"]
        if status in RESOLVED_STATUSES and is_text(rec.get("evidence")):
            continue
        blocking.append({"id": rec["id"], "status": status, "reopen_when": rec.get("reopen_when")})
        (actionable if status in ACTIONABLE_STATUSES else owner_gated).append(rec["id"])
    reasons = [f"{item['id']} is {item['status']}: a material record keeps the scope incomplete" for item in blocking]
    open_tasks = [task for task in camp.state["tasks"] if task["status"] == "open"]
    reasons += [f"task {task['id']} ({task['kind']}) is open: the work it names is not done" for task in open_tasks]
    return verdict("C1", reasons, blocking=blocking, actionable=actionable, owner_gated=owner_gated,
                   outside_scope=outside, adapter_backlog=adapter_backlog, open_tasks=[task["id"] for task in open_tasks])


def check_c2(camp: Campaign, facts: Facts) -> dict:
    k = camp.state["quiet_window"]
    reasons = []
    stale = stale_reason(camp, facts)
    if stale:
        reasons.append("stale: " + stale)
    win = window(camp.state)
    if len(win) < k:
        reasons.append(f"only {len(win)} iteration(s) ran on the current build at this scope; the quiet window needs {k}")
    else:
        for item in win[-k:]:
            if not item["quiet"]:
                reasons.append(f"iteration {item['index']} was not quiet: " + "; ".join(item["quiet_reasons"]))
    return verdict("C2", reasons, window=[item["index"] for item in win], k=k)


def check_c3(camp: Campaign, facts: Facts) -> dict:
    reasons = []
    stale = stale_reason(camp, facts)
    if stale:
        reasons.append("stale: " + stale)
    win = window(camp.state)
    for case_id in camp.scope()["cases"]:
        ran = [item["cases"][case_id] for item in win if case_id in item["cases"] and item["cases"][case_id]["ran"]]
        if not ran:
            reasons.append(f"{case_id} has no run on the current build")
            continue
        latest = ran[-1]
        if not latest["floors_met"]:
            reasons.append(f"{case_id} missed its floors on the current build")
        if latest["baseline"] != "comparable":
            reasons.append(f"{case_id} has no comparable baseline (baseline is {latest['baseline']!r}): unknown blocks")
    return verdict("C3", reasons)


def check_c4(camp: Campaign, facts: Facts) -> dict:
    scope = camp.scope()
    dims, combos = camp.manifest.get("dimensions", []), camp.manifest.get("combinations", [])
    reasons, ran_values = [], set()
    for item in window(camp.state):
        for case_id, result in item["cases"].items():
            if result["ran"] and case_id in facts.catalog:
                ran_values |= case_values(facts.catalog[case_id], dims, combos)
    for value in scope["values"]:
        if value not in ran_values:
            reasons.append(f"{value} is declared by the scope but has no run on the current build")
    everything = set()
    for case in facts.catalog.values():
        everything |= case_values(case, dims, combos)
    for value in sorted(everything - set(scope["values"])):
        if value not in scope["not_covered"]:
            reasons.append(f"{value} is neither covered nor listed as not covered")
    return verdict("C4", reasons, not_covered=scope["not_covered"])


def check_c5(camp: Campaign, facts: Facts) -> dict:
    state = camp.state
    reasons = []
    for key, step in state["steps"].items():
        if step["status"] == "running":
            reasons.append(f"step {key} is still running: its outcome and its cleanup are not known")
    for key in state["launch_intents"]:
        if key not in state["cleaned_launches"]:
            reasons.append(f"the adapter may have launched step {key} without the campaign recording it: run cleanup")
    iterations = state["iterations"]
    if not iterations:
        return verdict("C5", reasons + ["no iteration has run, so there is no cleanup or quick-tier receipt"])
    for item in iterations:
        if not (item["cleanup"].get("verified") and is_text(item["cleanup"].get("receipt"))):
            reasons.append(f"iteration {item['index']} has no positive cleanup evidence: absence of leftovers is not evidence "
                           "(run cleanup)")
    last = iterations[-1]
    if not last["tier"].get("green"):
        reasons.append("no green quick-tier receipt for the last iteration")
    elif last["tier"].get("build") != last["build_after"]:
        reasons.append(f"the quick-tier receipt is for build {last['tier'].get('build')!r}, not {last['build_after']!r}")
    return verdict("C5", reasons)


def check_c6(camp: Campaign, facts: Facts) -> dict:
    reasons, promoted = [], []
    for item in camp.state["iterations"]:
        candidate = item.get("candidate")
        if candidate and candidate["outcome"] == "PROMOTE":
            promoted.append(candidate["hash"])
            acceptance = item.get("acceptance") or {}
            if acceptance.get("candidate") != candidate["hash"] or not is_text(acceptance.get("evidence")):
                reasons.append(f"iteration {item['index']} promoted {candidate['hash']!r} without acceptance evidence for it")
    return verdict("C6", reasons, promoted=promoted, note=None if promoted else "no candidate")


def check_c7(camp: Campaign, facts: Facts) -> dict:
    k = camp.state["quiet_window"]
    reasons = []
    readiness = camp.state.get("readiness")
    if not (readiness and readiness.get("boundary_sha256") == camp.boundary and readiness.get("start_ok")):
        reasons.append("the latest readiness does not show the start rule for this boundary: run readiness --campaign --require-start")
    win = window(camp.state)
    if not win:
        reasons.append("no iteration has run at this scope on the current build")
    for item in win[-k:]:
        if item["invalid"]:
            reasons.append(f"iteration {item['index']} recorded invalid or incomplete evidence: " + "; ".join(item["invalid"]))
        if not (item["review"].get("valid") and item["review"].get("complete") and item["judge"].get("valid")
                and item["judge"].get("complete")):
            reasons.append(f"iteration {item['index']} has an invalid or incomplete review or judge")
    for unknown in camp.state["unknowns"]:
        if unknown.get("inside_claim") and not unknown.get("resolved"):
            reasons.append("an unknown lies inside the scope's claim: " + str(unknown.get("text")))
    return verdict("C7", reasons)


CHECKS = {"C1": check_c1, "C2": check_c2, "C3": check_c3, "C4": check_c4, "C5": check_c5, "C6": check_c6, "C7": check_c7}


def certificate(camp: Campaign, facts: Facts) -> dict:
    checks = {clause: CHECKS[clause](camp, facts) for clause in CLAUSES}
    reasons = [f"{clause}: {why}" for clause, item in checks.items() for why in item["reasons"]]
    iterations = camp.state["iterations"]
    last = iterations[-1] if iterations else {}
    readiness = camp.state.get("readiness")
    allowed = (readiness or {}).get("allowed_claims", [])
    note = None if readiness else "readiness is not recorded: no quality claim is allowed"
    if readiness and readiness.get("scoring") != facts.identity["scoring"]:
        allowed = []
        note = (f"readiness was proven under scoring identity {readiness.get('scoring')!r} and the evaluator is now "
                f"{facts.identity['scoring']!r}: rerun readiness; no quality claim is allowed until then")
    return {
        "status": "converged" if not reasons else "incomplete", "reasons": reasons, "checks": checks,
        "binds": {"scope": camp.state["scope"], "build": last.get("build_after"), "scoring": last.get("scoring"),
                  "campaign_identity": camp.identity, "candidates": checks["C6"]["detail"].get("promoted", [])},
        "claims": {"recorded": bool(readiness), "allowed": allowed, "note": note},
        "quota": quota_status(camp.state)}


# --------------------------------------------------------------------------------------------------- stuck modes and widening

def owner_gated_case(camp: Campaign, case: dict) -> bool:
    if case["id"] in camp.state.get("approved_cases", []):
        return False
    gated = set(camp.manifest.get("authority", {}).get("owner_only_requires", []))
    needs = set(case.get("requires") or [])
    if case.get("hosted"):
        needs.add("hosted")
    return bool(needs & gated)


def authority_problem(camp: Campaign, cases: list):
    """Why nothing may run yet, or None: the boundary, the readiness evidence and every selected case need the owner."""
    state = camp.state
    ratification = state.get("ratification")
    if not (ratification and ratification["boundary_sha256"] == camp.boundary):
        return "the execution boundary is not ratified: ask the owner, then ratify (nothing runs before that)"
    readiness = state.get("readiness")
    if not (readiness and readiness.get("boundary_sha256") == camp.boundary and readiness.get("start_ok")):
        return "readiness has not shown the start rule for this boundary: run readiness --campaign --require-start"
    catalog = load_catalog(camp)
    gated = [case_id for case_id in cases if case_id in catalog and owner_gated_case(camp, catalog[case_id])]
    if gated:
        return "owner-gated cases need approve --case ID --yes-owner-approved: " + ", ".join(gated)
    return None


def widening_candidates(camp: Campaign, facts: Facts) -> tuple:
    """(allowed, gated): catalog cases outside the scope that cover a value the scope lacks, cheapest first."""
    dims, combos = camp.manifest.get("dimensions", []), camp.manifest.get("combinations", [])
    scope = camp.scope()
    have = set(scope["values"])
    allowed, gated = [], []
    for case in facts.catalog.values():
        if case["id"] in scope["cases"]:
            continue
        fresh = case_values(case, dims, combos) - have
        if not fresh:
            continue
        item = {"id": case["id"], "cost": case.get("cost", 1), "covers": sorted(fresh)}
        (gated if owner_gated_case(camp, case) else allowed).append(item)

    def order(item):  # cheapest first, then the case that covers the most uncovered values, then the id
        return item["cost"], -len(item["covers"]), item["id"]

    return sorted(allowed, key=order), sorted(gated, key=order)


def analyze(camp: Campaign, facts: Facts, cert: dict) -> dict:
    """Which of the stuck modes this campaign is in, from the persisted iteration records."""
    state = camp.state
    c1 = cert["checks"]["C1"]["detail"]
    recent = [item for item in state["iterations"] if item["scope"] == state["scope"]][-2:]
    no_promote = len(recent) == 2 and not any((item.get("candidate") or {}).get("outcome") == "PROMOTE" for item in recent)
    if cert["status"] == "converged":
        return {"mode": "converged"}
    if not c1["actionable"] and c1["owner_gated"]:
        return {"mode": "blocked", "reason": "owner decisions are needed before any further investigation: "
                + ", ".join(c1["owner_gated"])}
    unexplained = not cert["checks"]["C3"]["pass"] and not c1["blocking"] and bool(state["iterations"])
    if (c1["actionable"] or unexplained) and no_promote and not stale_reason(camp, facts):
        return {"mode": "stalled"}
    return {"mode": "active"}


def start_action(camp: Campaign, facts=None) -> dict:
    state = camp.state
    scope = camp.scope()
    # A failed step becomes its own invalid iteration, so a retry has the next index and therefore a new key; the same key is
    # only ever recomputed after a crash, which is exactly when the adapter must recognise it and launch nothing.
    key = f"{state['id']}-{scope['id']}-{len(state['iterations']) + 1}"
    errors = state["start_failures"].get(key, [])
    if len(errors) >= 3 and len(set(errors[-3:])) == 1:
        return {"action": "stop", "status": "incomplete",
                "reason": f"the adapter failed to start step {key} three times with the same error: {errors[-1]}"}
    problem = authority_problem(camp, scope["cases"])
    if problem:
        return {"action": "blocked", "reason": problem}
    # The step starts from the subject as it is now: a change made outside the campaign (the owner edited it while reviewing the
    # boundary) is recorded when the step starts, instead of making the adapter's first report look like a base mismatch.
    intent = state["launch_intents"].get(key)  # written before the adapter was called: a replay starts from the same base
    return {"action": "start", "key": key, "scope": scope["id"], "cases": scope["cases"],
            "mode": "sweep" if scope["sweep_pending"] else "iterate",
            "base": intent["base"] if intent else (facts or Facts(camp)).identity["build"]}


def hunt_findings(state: dict) -> list:
    """Blind spots from completed hunt tasks whose latest disposition is not a rejection with a reason. A later hunt may supersede
    an earlier finding only by naming the same blind spot and rejecting it; a clean hunt does not clear what an earlier one found."""
    latest = {}
    for task in state["tasks"]:  # chronological: a later hunt that names the same blind spot supersedes the earlier finding
        if task["kind"] == "hunt" and task["status"] == "done":
            for spot in ((task.get("result") or {}).get("blind_spots") or []):
                latest[" ".join(str(spot.get("what")).split()).lower()] = spot
    return [f"{spot.get('what')} ({spot.get('disposition')})" for spot in latest.values() if spot.get("disposition") != "rejected"]


def completion_problems(camp: Campaign, cert: dict) -> list:
    """Why the campaign may not be called converged right now. One predicate for both ends of a converged stop: when it is created
    and every time it is read (next, report). The scope certificate already holds running steps (C5) and open tasks (C1)."""
    problems = list(cert["reasons"])
    problems += [f"a blind spot has no rejection: {item}" for item in hunt_findings(camp.state)]
    quota = quota_status(camp.state)
    if quota["exhausted"]:
        problems.append("budget used: " + ", ".join(quota["over"]))
    return problems


def decide_widen(camp: Campaign, facts: Facts, cert: dict) -> dict:
    """The scope is converged: widen it by rule, or stop with a report. Escalation never claims global exhaustion."""
    allowed, gated = widening_candidates(camp, facts)
    state = camp.state
    base = {"scope_certificate": "converged", "binds": cert["binds"]}
    if allowed:
        pick = allowed[0]
        return {"action": "widen", "add_cases": [pick["id"]], "covers": pick["covers"], "rung": "E1",
                "reason": f"the scope is converged; {pick['id']} is the cheapest case that covers {', '.join(pick['covers'])}"}
    if gated:
        return {"action": "stop", "status": "incomplete", "rung": "E5", **base,
                "reason": "an owner decision is needed to widen: " + ", ".join(
                    f"{item['id']} (covers {', '.join(item['covers'])})" for item in gated),
                "owner_gated_cases": [item["id"] for item in gated]}
    if not any(task["kind"] == "hunt" for task in state["tasks"]):
        return {"action": "new_task", "task": {
            "kind": "hunt", "needs_owner": False,
            "text": "The catalog is fully covered by this scope. Run the blind-spot hunter (prompts/blind-spot-hunter.md): name "
                    "what this evaluation could not see. Close the task with `task done --result` holding "
                    '{"blind_spots": [{"what", "disposition": "rejected|deferred-to-owner|added-as-task", "reason"}]}: every '
                    "blind spot needs a disposition, and only a rejection with a reason lets the campaign converge."}}
    unresolved = hunt_findings(state)
    if unresolved:
        return {"action": "stop", "status": "incomplete", "rung": "E3", **base,
                "reason": "the blind-spot hunt left findings without a rejection: " + "; ".join(unresolved)}
    return {"action": "stop", "status": "converged", "rung": "E5", **base,
            "reason": "the declared catalog is covered and the blind-spot hunt is recorded; this is not a claim that no "
                      "material problem remains outside what the evaluation can see"}


def plan_next(camp: Campaign) -> dict:
    """The next action, computed without changing anything."""
    state = camp.state
    stop = state.get("stop")
    if stop:
        if stop.get("status") == "converged":
            current = certificate(camp, Facts(camp))
            problems = completion_problems(camp, current)
            if problems:
                return {"action": "stop", "status": "incomplete", "binds": current["binds"],
                        "reason": "the earlier converged stop is stale: " + "; ".join(problems[:4])}
        return {"action": "stop", **stop}
    for key, step in state["steps"].items():
        if step["status"] == "running":
            quota, elapsed = quota_status(state), time.time() - step["started_epoch"]
            step_limit = camp.manifest["execution"].get("step_timeout_seconds", DEFAULT_STEP_TIMEOUT)
            errors = state["poll_failures"].get(key, [])
            if quota["exhausted"]:
                return {"action": "stop", "status": "incomplete", "quota": quota,
                        "reason": f"budget used ({', '.join(quota['over'])}) while step {key} is still running: cancel it and run "
                                  "cleanup, or have the owner reopen with a larger budget to let it finish"}
            if elapsed > step_limit:
                return {"action": "stop", "status": "incomplete",
                        "reason": f"step {key} has run for {round(elapsed)} s, over execution.step_timeout_seconds ({step_limit:g}): "
                                  "cancel it and run cleanup"}
            if len(errors) >= 3 and len(set(errors[-3:])) == 1:
                return {"action": "stop", "status": "incomplete",
                        "reason": f"the adapter failed to poll step {key} 3 time(s) with the same error: {errors[-1]}; the step is "
                                  "still running, so cancel it and run cleanup"}
            return {"action": "poll", "key": key, "handle": step["handle"]}
    for task in state["tasks"]:
        if task["status"] == "open":
            return {"action": "task", "task": task}
    quota = quota_status(state)
    if quota["exhausted"]:
        return {"action": "stop", "status": "incomplete", "reason": "budget used: " + ", ".join(quota["over"]), "quota": quota}
    failures = [item["error"] for item in state["steps"].values() if item["status"] == "failed"]
    if len(failures) >= 3 and len(set(failures[-3:])) == 1:
        return {"action": "stop", "status": "incomplete", "reason": "the same step error three times: " + failures[-1]}
    regression = regression_reason(state)
    if regression and state.get("regression_ack") != len(state["iterations"]):
        return {"action": "stop", "status": "incomplete", "reason": regression}
    if no_progress_run(state) >= PROGRESS_STOP:
        return {"action": "stop", "status": "incomplete",
                "reason": f"{PROGRESS_STOP} iterations without progress: none was quiet, promoted a candidate or followed a "
                          "finished task"}
    if not state["iterations"]:
        return start_action(camp)
    facts = Facts(camp)
    cert = certificate(camp, facts)
    mode = analyze(camp, facts, cert)
    if mode["mode"] == "converged":
        return decide_widen(camp, facts, cert)
    if mode["mode"] == "blocked":
        return {"action": "stop", "status": "incomplete", "reason": mode["reason"], "binds": cert["binds"]}
    if mode["mode"] == "stalled":
        last_promote = max([item["index"] for item in state["iterations"]
                            if (item.get("candidate") or {}).get("outcome") == "PROMOTE"] or [0])
        tried = [task for task in state["tasks"] if task["kind"] == "diagnose" and task["status"] == "done"
                 and task.get("stall_at", 0) > last_promote]
        if len(tried) >= 2:
            return {"action": "stop", "status": "incomplete", "binds": cert["binds"],
                    "reason": "stalled: two diagnoses since the last promoted candidate did not unblock the work; the owner "
                              "should decide the next investigation"}
        if not any(task.get("stall_at") == len(state["iterations"]) for task in state["tasks"]):
            return {"action": "new_task", "task": {
                "kind": "diagnose", "needs_owner": False, "stall_at": len(state["iterations"]),
                "text": "Two iterations in a row produced no promoted candidate while material work remains. Diagnose before "
                        "widening: read the failing runs' upstream records, run the real case to the stage and stop it, or ask "
                        "one advisor the stuck question (rung E0). Record what you found with `task done --result`."}}
    return start_action(camp, facts)


# ------------------------------------------------------------------------------------------------------------ doing a step

def journal(camp: Campaign, rec: dict) -> None:
    """Append one line per iteration; idempotent on the step key, so a crash between the append and the save cannot duplicate it."""
    path = camp.dir / "journal.md"
    marker = f"[key={rec['key']}]"
    if path.is_file() and marker in path.read_text():
        return
    line = (f"- iteration {rec['index']} ({rec['scope']}, {rec['mode']}) {marker}: {'quiet' if rec['quiet'] else 'not quiet'}"
            f"{'; FAILED' if rec['failed'] else ''}; {len(rec['discoveries'])} discoveries; candidate "
            f"{(rec['candidate'] or {}).get('outcome', 'none')}; build {rec['build_before']} -> {rec['build_after']}; consumed "
            f"{json.dumps(rec['consumed'], sort_keys=True)}\n")
    with open(path, "a") as handle:
        handle.write(line)


def record_iteration(camp: Campaign, key: str, rec: dict, status: str, error=None) -> dict:
    state = camp.state
    step = state["steps"][key]
    if is_amount(step.get("started_epoch")):
        elapsed = max(0.0, time.time() - step["started_epoch"])
        if elapsed > rec["consumed"].get("seconds", 0):
            # While it ran, its wall time counted against the budget; ending it (done, failed or cancelled) must not erase that.
            rec["consumed"] = {**rec["consumed"], "seconds": round(elapsed, 3)}
    state["iterations"].append(rec)
    state["tip"] = rec["build_after"]
    add_consumed(state, rec["consumed"])
    step["status"], step["iteration"] = status, rec["index"]
    if error:
        step["error"] = error
    if status == "done" and step["mode"] == "sweep":
        camp.scope()["sweep_pending"] = False
    journal(camp, rec)
    return rec


def finish_step(camp: Campaign, key: str, facts) -> dict:
    step = camp.state["steps"][key]
    errors = validate_facts(facts, step["cases"])
    if errors:
        error = "malformed adapter evidence: " + "; ".join(errors[:3])
        return record_iteration(camp, key, failed_iteration(camp.state, key, step, error, facts), "failed", error)
    return record_iteration(camp, key, derive_iteration(camp.state, key, step, facts), "done")


def fail_step(camp: Campaign, key: str, status: str, error: str, reported) -> dict:
    step = camp.state["steps"][key]
    return record_iteration(camp, key, failed_iteration(camp.state, key, step, error, reported), status, error)


def apply_action(camp: Campaign, act: dict) -> dict:
    state = camp.state
    kind = act["action"]
    if kind == "blocked":
        return act
    if kind == "stop":
        stop = {key: value for key, value in act.items() if key != "action"}
        stop["at"] = now()
        state["stop"] = stop
        camp.event("stop", **{k: v for k, v in stop.items() if k in ("status", "reason", "rung")})
        write_report(camp)
        return {"action": "stop", **stop, "report": str(camp.dir / "report.md")}
    if kind == "task":
        return act
    if kind == "new_task":
        task = dict(act["task"], id=f"T{len(state['tasks']) + 1}", status="open", opened=now())
        state["tasks"].append(task)
        camp.event("task", id=task["id"], kind=task["kind"])
        return {"action": "task", "task": task}
    if kind == "widen":
        facts = Facts(camp)
        cases = list(camp.scope()["cases"]) + act["add_cases"]
        scope_id = f"S{len(state['scopes'])}"
        state["scopes"].append(open_scope(camp, scope_id, cases, act["reason"], True, facts.catalog))
        state["scope"] = scope_id
        camp.event("widen", scope=scope_id, added=act["add_cases"], rung=act["rung"])
        return {"action": "widen", "scope": scope_id, "cases": cases, "covers": act["covers"], "reason": act["reason"],
                "first_iteration": "a baseline sweep: the new cases run on the current build with no improver"}
    if kind == "start":
        problem = authority_problem(camp, act["cases"])
        if problem:
            return {"action": "blocked", "reason": problem}
        changed = False
        if act["key"] not in state["launch_intents"]:
            if act["base"] != state["tip"]:
                camp.event("subject-changed-outside", expected=state["tip"], found=act["base"])
                state["tip"] = act["base"]
            # Write-ahead: if this process dies after the adapter launches the run, the replay recomputes the same key and starts
            # from this base (the run may already have changed the subject), and the run is accounted for until cleanup covers it.
            state["launch_intents"][act["key"]] = {"base": act["base"], "scope": act["scope"], "cases": list(act["cases"]),
                                                   "mode": act["mode"], "at": now()}
            changed = True
        if state["cleaned_launches"].pop(act["key"], None) is not None:
            changed = True  # this attempt may launch the run again: an earlier cleanup of the key no longer covers it
        if changed:
            camp.save()  # before the adapter is called, so a kill during the call cannot leave a stale receipt behind
        out_dir = camp.work_dir / "runs" / act["key"]
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            reply = camp.call("step", ["start", "--key", act["key"], "--scope", act["scope"], "--cases", ",".join(act["cases"]),
                                       "--mode", act["mode"], "--base", act["base"] or "", "--out", out_dir])
            if not is_text(reply.get("handle")) or reply.get("status") not in ("running", "done"):
                raise LoopError("adapter step start must print a handle and a status of running or done")
        except LoopError as error:
            # The adapter may have launched the run before it failed to answer, so a retry keeps this key (it is recomputed from
            # the unchanged iteration count) and the adapter recognises it. The failure is counted so the retries end.
            state["start_failures"].setdefault(act["key"], []).append(str(error))
            camp.event("start-failed", key=act["key"], error=str(error)[:200])
            camp.save()
            raise
        state["steps"][act["key"]] = {"handle": reply["handle"], "status": "running", "started": now(), "started_epoch": time.time(),
                                      "scope": act["scope"], "mode": act["mode"], "base": act["base"],
                                      "index": len(state["iterations"]) + 1, "cases": list(act["cases"])}
        state["launch_intents"].pop(act["key"], None)
        if reply["status"] == "done":
            return {"action": "start", "key": act["key"], "iteration": finish_step(camp, act["key"], reply.get("iteration"))["index"]}
        return {"action": "start", "key": act["key"], "handle": reply["handle"], "status": "running"}
    if kind == "poll":
        try:
            reply = camp.call("step", ["poll", "--handle", act["handle"]])
        except LoopError as error:
            state["poll_failures"].setdefault(act["key"], []).append(str(error))
            camp.event("poll-failed", key=act["key"], error=str(error)[:200])
            camp.save()
            raise
        state["poll_failures"].pop(act["key"], None)  # a poll that answers ends the run of failures
        status = reply.get("status")
        if status == "running":
            return {"action": "poll", "key": act["key"], "status": "running"}
        if status == "done":
            rec = finish_step(camp, act["key"], reply.get("iteration"))
            return {"action": "poll", "key": act["key"], "status": "done" if not rec["failed"] else "failed",
                    "iteration": rec["index"], "quiet": rec["quiet"], **({"error": rec["invalid"][0]} if rec["failed"] else {})}
        error = str(reply.get("error") or status or "the step failed")
        fail_step(camp, act["key"], "failed" if status != "cancelled" else "cancelled", error, reply.get("iteration"))
        return {"action": "poll", "key": act["key"], "status": "failed", "error": error}
    raise LoopError(f"unknown action {kind!r}")


# ------------------------------------------------------------------------------------------------------------------ report

def write_report(camp: Campaign) -> dict:
    state = camp.state
    nothing = {"checks": {}, "binds": {}, "claims": {"allowed": [], "note": None}}
    try:
        cert = certificate(camp, Facts(camp)) if state["iterations"] else dict(nothing, status="incomplete",
                                                                                reasons=["no iteration has run"])
    except LoopError as error:  # a stop caused by a broken adapter must still be recorded and reported
        cert = dict(nothing, status="unavailable", reasons=[f"the adapter could not be queried for this report: {error}"])
    c1 = (cert["checks"].get("C1") or {}).get("detail", {})
    stop = state.get("stop") or {}
    problems = completion_problems(camp, cert)
    campaign_status = "in progress"
    if stop:
        campaign_status = stop.get("status", "incomplete")
        if campaign_status == "converged" and problems:
            campaign_status = "incomplete"  # the stop is stale: the evidence changed, or work or spending was added, after it
    out = {
        "schema": "closed-loop-report/1", "at": now(), "subject": state["subject"], "scope": state["scope"],
        "scope_cases": camp.scope()["cases"], "scope_certificate": cert["status"], "campaign_status": campaign_status,
        "stop": stop or None, "binds": cert["binds"], "reasons": problems,
        "unresolved": c1.get("blocking", []), "adapter_backlog": c1.get("adapter_backlog", []),
        "outside_scope": c1.get("outside_scope", []), "not_covered": camp.scope()["not_covered"],
        "unknowns": [item for item in state["unknowns"] if not item.get("resolved")], "quota": quota_status(state),
        "resolved_unknowns": [{"text": item["text"], "resolution": item.get("resolution"), "resolved": item["resolved"]}
                              for item in state["unknowns"] if item.get("resolved")],
        "iterations": len(state["iterations"]), "allowed_claims": cert["claims"]["allowed"],
        "claims_note": cert["claims"]["note"],
        "scopes": [{"id": s["id"], "cases": s["cases"], "reason": s["reason"]} for s in state["scopes"]],
    }
    headline = (f"**Campaign status: {campaign_status}.** Scope {state['scope']} ({', '.join(out['scope_cases'])}) certificate: "
                f"{cert['status']}.")
    caveat = ("A certificate covers one named scope on one build as graded by one evaluator; it is not a claim that no material "
              "problem remains elsewhere.")
    lines = [f"# Closed-loop report: {state['subject']}", "", headline, "", caveat, ""]
    if stop:
        lines += [f"Stopped at rung {stop.get('rung', '-')}: {stop.get('reason')}", ""]
    if out["reasons"]:
        lines += ["## Why not converged", ""] + [f"- {item}" for item in out["reasons"]] + [""]
    if out["unresolved"]:
        lines += ["## Unresolved material records", ""] + [
            f"- {item['id']} ({item['status']}); reopen when: {item.get('reopen_when') or 'not stated'}"
            for item in out["unresolved"]] + [""]
    if out["not_covered"]:
        lines += ["## Not covered by this scope", ""] + [f"- {value}: {why}" for value, why in out["not_covered"].items()] + [""]
    if out["adapter_backlog"]:
        lines += ["## Adapter backlog (outside a subject certificate)", ""] + [f"- {item}" for item in out["adapter_backlog"]] + [""]
    if out["unknowns"]:
        lines += ["## Unresolved unknowns", ""] + [
            f"- {item['text']}{' (inside the claim)' if item.get('inside_claim') else ''}" for item in out["unknowns"]] + [""]
    if out["resolved_unknowns"]:
        lines += ["## Resolved unknowns (what answered each)", ""] + [
            f"- {item['text']}: {item['resolution']}" for item in out["resolved_unknowns"]] + [""]
    claims = out["allowed_claims"] or [out["claims_note"] or "none"]
    lines += ["## What this certificate may claim", ""] + [f"- {item}" for item in claims] + [""]
    spent = (f"- consumed {json.dumps(out['quota']['consumed'], sort_keys=True)} of budget "
             f"{json.dumps(out['quota']['budget'], sort_keys=True)}")
    lines += ["## Quota", "", spent, f"- iterations: {out['iterations']}"]
    if out["quota"]["exhausted"]:
        lines.append(f"- budget exhausted: {', '.join(out['quota']['over'])} (the budget is checked before each step, so the "
                     "last step may have overshot it)")
    lines.append("")
    (camp.dir / "report.md").write_text("\n".join(lines))
    (camp.dir / "report.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


# ------------------------------------------------------------------------------------------------------------------ contract

def check_command(camp: Campaign, clause: str, sha: str) -> str:
    return shlex.join([sys.executable, str(SCRIPT), "check", "--campaign", str(camp.dir), "--clause", clause,
                       "--expect-sha", sha, "--expect-scope", camp.state["scope"], "--expect-identity", camp.identity])


def build_contract(camp: Campaign) -> dict:
    """The Until Loop contract for the current scope. Its workspace is the campaign folder, a Git repo that holds only campaign
    state, so the runtime's freshness check sees every change to the evidence the checks read."""
    state, sha = camp.state, script_sha()
    scope = camp.scope()
    authority = camp.manifest.get("authority", {})
    quota = quota_status(state)
    context = {
        "request": f"Run a closed-loop campaign on {state['subject']}: improve it by running cases, grading, trying fixes and "
                   "repeating, and report convergence only within the named scope.",
        "scope": f"Scope {scope['id']}: cases {', '.join(scope['cases'])}; not covered: "
                 + (", ".join(scope["not_covered"]) or "nothing listed"),
        "authority": "Routine: " + "; ".join(authority.get("routine", [])) + ". Owner only: "
                     + "; ".join(authority.get("owner_only", [])) + ". Budget " + json.dumps(quota["budget"], sort_keys=True)
                     + "; ratified: " + str(bool(state.get("ratification"))) + ". A script stop is not convergence.",
        "environment": f"{sys.executable} {SCRIPT}; adapter manifest {camp.manifest_path}; campaign folder {camp.dir} (the "
                       f"workspace); subject workspace {state['workspace']}; bulky files in {camp.work_dir}. Call the adapter "
                       f"only through this script. Script sha256 {sha}; campaign identity {camp.identity}.",
        "resources": [{"purpose": "campaign state", "locator": str(camp.dir / "campaign.json")},
                      {"purpose": "adapter manifest", "locator": str(camp.manifest_path)},
                      {"purpose": "orchestrator script", "locator": str(SCRIPT)}],
    }
    exit_condition = (f"Scope {scope['id']} is converged on the current build: " + " ".join(CLAUSE_TEXT[c] for c in CLAUSES)
                      + " Report satisfied only after every frozen check passed after the iteration's last change, and never "
                        "when `step` printed a stop.")
    return {
        "workspace": str(camp.dir),
        "work": f"Run one closed-loop iteration at scope {scope['id']}: run `{SCRIPT.name} step --campaign {camp.dir}` until a "
                "step finishes (poll while one runs; do any open task it prints), then run `status` and apply the campaign "
                "checkpoint: read the whole backlog, reconcile related findings, and choose the smallest discriminating next "
                "investigation.",
        "exit_condition": exit_condition,
        "repeat_condition": "Another iteration is allowed while `step` reports start, poll, task or widen; stop incomplete when it "
                            "reports a stop or blocked, the budget is used, or an owner decision is needed.",
        "required_trivial_reviews": 0,
        "exit_checks": [{"id": clause, "clause": CLAUSE_TEXT[clause], "command": check_command(camp, clause, sha)}
                        for clause in CLAUSES],
        "context": context}


# ----------------------------------------------------------------------------------------------------------------- readiness

def claim_states(manifest: dict, manifest_dir: Path, workspace, campaign_dir, ratified: bool, guard=None) -> tuple:
    """Run the probes this boundary allows. `guard(spent)` is called before each probe and raises when the budget is used; a failure
    carries what the finished probes cost as `error.consumed`, so the caller can still charge it."""
    out, consumed = {}, {}
    try:
        for claim, meta in manifest.get("claims", {}).items():
            ladder = CLAIM_LADDERS[claim.split(":")[0]]
            entry = {"state": ladder[0], "effect": meta["effect"], "evidence": None}
            if meta["effect"] == "effectful" and not ratified:
                entry["evidence"] = "not run: the execution boundary is not ratified (an effectful probe runs commands)"
            else:
                if guard:
                    guard(consumed)
                reply = call_adapter(manifest, manifest_dir, "probe", [claim], workspace=workspace, campaign=campaign_dir)
                for name, amount in (reply.get("consumed") or {}).items():
                    if is_amount(amount):
                        consumed[name] = consumed.get(name, 0) + amount
                if reply.get("state") not in ladder:
                    raise LoopError(f"probe {claim} returned state {reply.get('state')!r}; allowed: {', '.join(ladder)}")
                if reply["state"] != ladder[0] and not is_text(reply.get("evidence")):
                    raise LoopError(f"probe {claim} reported {reply['state']!r} without evidence: a claim is proven only by what "
                                    "the probe shows")
                entry["state"], entry["evidence"] = reply["state"], reply.get("evidence")
            out[claim] = entry
    except LoopError as error:
        error.consumed = dict(consumed)
        raise
    return out, consumed


def derive_readiness(manifest: dict, states: dict) -> tuple:
    """(blocked, allowed_claims) from each claim's state: whether the start rule holds, and what the proven claims allow."""
    def reached(kind: str, state: str) -> bool:
        return any(claim.split(":")[0] == kind and value == state for claim, value in states.items())

    blocked = []
    for kind, state in (("cases.runs", "runs"), ("grading.scores", "scores"), ("improver.bounded", "bounded")):
        if not reached(kind, state):
            blocked.append(f"no {kind} claim has reached {state!r}")
    allowed = []
    if not blocked:
        allowed.append("efficiency under a stated tolerance, labelled 'stated, not measured'")
        if manifest.get("evaluation_class", "scripted") == "judge-only":
            allowed.append("model-judged quality, labelled with the recorded judge reliability (promotion is the owner's policy)")
        for claim, value in sorted(states.items()):  # canonical: the saved state sorts its keys, so insertion order must not matter
            kind, _, name = claim.partition(":")
            if kind == "grading.sensitive" and value == "sensitive":
                allowed.append(f"quality claims about {name}")
            if kind == "grading.calibrated" and value == "calibrated":
                allowed.append(f"measured efficiency on profile {name}")
        if not any(item.startswith("quality claims") for item in allowed):
            allowed.append("no quality claim is allowed yet: sensitivity is unknown for every property")
    return blocked, allowed


def check_state_against_manifest(state: dict, manifest: dict) -> None:
    """Saved facts that depend on the manifest must still follow from it: runs imply a ratification of this boundary, and the
    recorded readiness must follow from its own claims (a hand-edited or half-written record does not stand)."""
    def need(condition, why):
        if not condition:
            raise LoopError("campaign state is malformed: " + why)

    if state["iterations"] or state["steps"] or state["launch_intents"]:
        ratification = state.get("ratification")
        need(isinstance(ratification, dict) and ratification.get("boundary_sha256") == state["manifest"]["boundary_sha256"],
             "runs are recorded without a ratification of this boundary")
    readiness = state.get("readiness")
    if readiness is None:
        return
    need(isinstance(readiness, dict) and is_text(readiness.get("boundary_sha256")) and is_text(readiness.get("scoring"))
         and isinstance(readiness.get("start_ok"), bool) and isinstance(readiness.get("blocked"), list)
         and isinstance(readiness.get("allowed_claims"), list) and isinstance(readiness.get("claims"), dict),
         "the recorded readiness has the wrong shape")
    claims = readiness["claims"]
    if not claims and readiness["start_ok"] is False:
        return  # a refresh that began and did not finish: it proves nothing, and it withdrew the result before it
    need(set(claims) == set(manifest.get("claims", {})), "the recorded readiness does not cover exactly the manifest's claims")
    states = {}
    for claim, entry in claims.items():
        ladder = CLAIM_LADDERS[claim.split(":")[0]]
        need(isinstance(entry, dict) and entry.get("state") in ladder, f"the recorded state of {claim} is not on its ladder")
        need(entry["state"] == ladder[0] or is_text(entry.get("evidence")), f"the recorded claim {claim} is proven without evidence")
        states[claim] = entry["state"]
    blocked, allowed = derive_readiness(manifest, states)
    need(readiness["blocked"] == blocked and readiness["allowed_claims"] == allowed and readiness["start_ok"] == (not blocked),
         "the recorded readiness does not follow from its claims")


def readiness_report(manifest: dict, manifest_dir: Path, workspace, campaign_dir, ratified: bool, guard=None) -> tuple:
    claims, consumed = claim_states(manifest, manifest_dir, workspace, campaign_dir, ratified, guard)
    blocked, allowed = derive_readiness(manifest, {claim: entry["state"] for claim, entry in claims.items()})
    report = {"claims": claims, "start_ok": not blocked, "blocked": blocked, "allowed_claims": allowed,
              "boundary_sha256": boundary_hash(manifest, manifest_dir), "ratified": ratified,
              "note": "invocable proves plumbing only, never improvement quality"}
    return report, consumed


# --------------------------------------------------------------------------------------------------------------------- verbs

def require_owner(args) -> None:
    if not args.yes_owner_approved:
        raise LoopError("this is the owner's decision: ask the owner, then pass --yes-owner-approved")


@contextlib.contextmanager
def session(args):
    """Lock the campaign, load it, yield it and save it when the command finishes. A command that fails still charges the wall
    time its failed adapter calls took, on the state as last saved, so a hanging adapter is not retried for free."""
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        FAILED_CALLS["seconds"] = 0.0
        camp = Campaign(campaign_dir)
        try:
            yield camp
        except LoopError:
            spent = round(FAILED_CALLS["seconds"], 3)
            if spent > 0:
                fresh = load_state(campaign_dir)
                if running_seconds(fresh) == 0:  # with a step running, this wall time is already counted as that step's own
                    add_consumed(fresh, {"seconds": spent})
                fresh["events"].append({"at": now(), "event": "failed-calls", "seconds": spent})
                save_state(campaign_dir, fresh)
            raise
        camp.save()


SLOT_VALUE_TYPES = {"mission": list, "cases": list, "steps": dict, "evaluation": dict, "improvement": dict, "authority": dict,
                    "records": dict}


def path_escapes(item: str) -> bool:
    """A proposal's paths are relative to the subject's root; an absolute path or one that climbs out is not comparable."""
    return item.startswith("/") or ".." in posixpath.normpath(item or ".").split("/")


def path_overlap(first: str, second: str) -> bool:
    """True when one path is the other or inside it; the root (".") contains everything."""
    first, second = posixpath.normpath(first or "."), posixpath.normpath(second or ".")
    return "." in (first, second) or first == second or first.startswith(second + "/") or second.startswith(first + "/")


def pinned_relative(manifest: dict, manifest_dir, manifest_name) -> list:
    """The manifest's own file and its pinned adapter or grader paths, relative to the manifest's folder (the subject's root)."""
    root = Path(manifest_dir).resolve()
    out = [manifest_name] if manifest_name else []
    for item in manifest["execution"].get("pin", []):
        try:
            out.append((root / item).resolve().relative_to(root).as_posix())
        except ValueError:
            pass  # pinned outside the subject: nothing in the subject can overlap it
    return out


def validate_proposal(proposal, manifest=None, manifest_dir=None, manifest_name=None) -> list:
    """Why a definer proposal cannot be used, or an empty list: the wrapper's shape, evidence for every found slot, and no
    grader, check or withheld path in the improver's candidate set."""
    if not isinstance(proposal, dict) or proposal.get("contract") != DEFINER_SCHEMA:
        return [f"the proposal must be a JSON object with contract {DEFINER_SCHEMA}"]
    errors = []
    slots = proposal.get("slots")
    if not isinstance(slots, dict) or set(slots) != set(SLOT_NAMES):
        return [f"slots must be exactly: {', '.join(SLOT_NAMES)}"]
    for name, slot in slots.items():
        if not isinstance(slot, dict) or slot.get("status") not in SLOT_STATUSES:
            errors.append(f"slot {name} needs a status of {', '.join(SLOT_STATUSES)}")
            continue
        evidence = slot.get("evidence")
        if evidence is not None and not (isinstance(evidence, list) and all(is_text(item) for item in evidence)):
            errors.append(f"slot {name} evidence must be a list of non-blank text")
        elif slot["status"] == "found" and not evidence:
            errors.append(f"slot {name} is found without evidence: cite a file and symbol, or call it proposed or unknown")
        if slot["status"] != "unknown" and not (isinstance(slot.get("value"), SLOT_VALUE_TYPES[name]) and slot["value"]):
            errors.append(f"slot {name} is {slot['status']} but its value is not a non-empty {SLOT_VALUE_TYPES[name].__name__}")
    improvement = slots["improvement"].get("value") if isinstance(slots.get("improvement"), dict) else None
    if isinstance(improvement, dict):
        candidates = improvement.get("candidate_paths") or []
        protected = (improvement.get("evaluator_paths") or []) + (improvement.get("withheld_paths") or [])
        if manifest and manifest_dir:
            protected = protected + pinned_relative(manifest, manifest_dir, manifest_name)
        if not all(isinstance(item, str) for item in candidates + protected):
            errors.append("improvement paths must be text")
        elif any(path_escapes(item) for item in candidates + protected):
            errors.append("improvement paths must be relative to the subject's root and stay inside it (no leading '/', no '..')")
        else:
            for item in candidates:
                clash = [other for other in protected if path_overlap(item, other)]
                if clash:
                    errors.append(f"candidate path {item!r} overlaps an evaluator, withheld or pinned adapter path "
                                  f"({', '.join(clash)}): the improver may never change what grades it")
    for key in ("risks", "needs_owner", "unknowns"):
        if not isinstance(proposal.get(key), list):
            errors.append(f"{key} must be a list (an empty list is valid)")
    if manifest and not errors:
        evaluation, authority = slots["evaluation"].get("value"), slots["authority"].get("value")
        if isinstance(evaluation, dict) and evaluation.get("evaluation_class") not in (None, manifest.get("evaluation_class", "scripted")):
            errors.append("the proposal's evaluation_class is not the manifest's: the owner would ratify one and read the other")
        if isinstance(authority, dict) and set(authority.get("owner_only_requires") or []) != set(
                manifest.get("authority", {}).get("owner_only_requires", [])):
            errors.append("the proposal's owner_only_requires is not the manifest's: the gate the owner reads must be the one enforced")
        if manifest["execution"]["capability"] == "hosted" and not proposal.get("needs_owner"):
            errors.append("a hosted capability needs at least one needs_owner entry saying what the owner must approve")
    return errors


STATE_FILES = (".gitignore", "campaign.json", "campaign.lock", "journal.md", "report.md", "report.json")


FSMONITOR_BUILTIN = ("true", "false", "yes", "no", "on", "off", "1", "0")  # core.fsmonitor values that are not a hook command


def fingerprint_problem(campaign_dir: Path):
    """Why the Until Loop's Git-tree fingerprint would not hold this folder's state now, or after the next change, or None. The
    fingerprint is `git add -A` into a private copy of the real index followed by `git write-tree`. This does the same, requires
    that it works, requires that nothing can freeze or rewrite a state file (an assume-unchanged or skip-worktree flag, a Git
    filter, a file-system monitor hook), and requires that each state file's staged content is what `git add` makes of it. A
    snapshot that merely matches today would miss a flag or a static filter that hides tomorrow's change."""
    base_env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")

    def git(*args, env=None):
        try:
            return subprocess.run(["git", "-C", str(campaign_dir), *args], capture_output=True, text=True, check=False,
                                  stdin=subprocess.DEVNULL, env=env or base_env, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as error:
            return error

    def failed(done) -> bool:
        return isinstance(done, Exception) or done.returncode != 0

    def why(done) -> str:
        if isinstance(done, subprocess.TimeoutExpired):
            return f"it did not answer within {GIT_TIMEOUT:g} s"
        return str(done) if isinstance(done, Exception) else (done.stderr or done.stdout).strip()[-200:]

    located = git("rev-parse", "--git-path", "index")
    if failed(located):
        return f"git cannot read the campaign folder, so the Until Loop could not fingerprint it ({why(located)})"
    listed = git("ls-files", "-v")
    if failed(listed):
        return f"git cannot list the campaign folder's index ({why(listed)})"
    flagged = [line[2:] or line for line in listed.stdout.splitlines() if line and line[0] != "H"]
    if flagged:
        return ("the campaign folder's Git index has entries flagged assume-unchanged or skip-worktree, or unmerged (" +
                ", ".join(flagged) + "): a later change to such a file can be invisible to the Until Loop's fingerprint even "
                "while it matches now; clear each flag with its own `git update-index --no-assume-unchanged FILE` or "
                "`git update-index --no-skip-worktree FILE` (one mode per command), or unstage the file with `git rm --cached "
                "FILE`, or resolve the merge")
    attributes = git("check-attr", "filter", "--", *STATE_FILES)
    if failed(attributes):
        return f"git cannot read the attributes of the campaign folder ({why(attributes)})"
    filtered = [line.split(":")[0] for line in attributes.stdout.splitlines()
                if line.rsplit(": ", 1)[-1].strip() not in ("unspecified", "unset")]
    if filtered:
        return ("a Git filter applies to " + ", ".join(filtered) + ": a filter can rewrite what the fingerprint holds (for "
                "example to a saved copy), so a later change would not show; remove the .gitattributes or git config rule")
    monitor = git("config", "--get", "core.fsmonitor")
    if not isinstance(monitor, Exception) and monitor.returncode == 0 and monitor.stdout.strip() \
            and monitor.stdout.strip().lower() not in FSMONITOR_BUILTIN:
        return (f"core.fsmonitor names a hook ({monitor.stdout.strip()[:80]}): a hook decides which files Git re-reads, so it "
                "can hide a change from the fingerprint; use Git's built-in monitor or none")
    real_index = Path(located.stdout.strip())
    if not real_index.is_absolute():
        real_index = Path(campaign_dir) / real_index
    try:
        handle, index = tempfile.mkstemp(prefix="closed-loop-tree-", suffix=".index")
        os.close(handle)
    except OSError as error:
        return f"the Git fingerprint cannot be checked: no temporary file could be made ({error})"
    try:
        try:
            if real_index.is_file():
                Path(index).write_bytes(real_index.read_bytes())
            else:
                os.unlink(index)
        except OSError as error:
            return f"the Git fingerprint cannot be checked: the index could not be copied ({error})"
        env = dict(base_env, GIT_INDEX_FILE=index)
        excludes = [":(exclude,glob)**/" + part + "/**" for part in FINGERPRINT_EXCLUDES]
        excludes += [":(exclude,glob)**/innerloop-*.json", ":(exclude,glob)**/innerloop-*.json.lock"]
        added = git("add", "-A", "--", ".", *excludes, env=env)
        if failed(added):
            return f"git cannot fingerprint the campaign folder ({why(added)})"
        present = [name for name in STATE_FILES if (Path(campaign_dir) / name).is_file()]
        staged = git("ls-files", "-s", "--", *present, env=env)
        raw = git("hash-object", "--", *present)  # with the path's filters: the same conversion `git add` applies (autocrlf, eol)
        if failed(staged) or failed(raw):
            return f"git cannot show what the fingerprint holds ({why(staged if failed(staged) else raw)})"
        held = {}
        for line in staged.stdout.splitlines():
            meta, _, name = line.partition("\t")
            held[name] = meta.split()[1]
        hashes = raw.stdout.split()  # one per path, in order (zip's strict= needs Python 3.10; the floor is 3.9)
        own = {name: hashes[number] for number, name in enumerate(present) if number < len(hashes)}
        hidden = [name for name in present if held.get(name) != own.get(name)]
        if hidden:
            return ("the Until Loop's Git fingerprint does not hold the current content of " + ", ".join(hidden) + " (an ignore "
                    "rule or a file-system monitor): a stale satisfied report could complete, so no check passes until the "
                    "campaign folder is visible to it; restore the folder's .gitignore and clear the rule")
        tree = git("write-tree", env=env)  # the runtime records no fingerprint at all when this fails, and then skips freshness
        if failed(tree) or not tree.stdout.strip():
            return f"git cannot write the fingerprint tree, so the Until Loop would record none ({why(tree)})"
    finally:
        if os.path.exists(index):
            os.unlink(index)
    return None


def cmd_adapter_check(args) -> tuple:
    manifest, path = load_manifest(args.manifest)
    out = {"ok": True, "manifest": str(path), "sha256": sha256_file(path),
           "boundary_sha256": boundary_hash(manifest, path.parent), "subject": manifest["subject"]["name"],
           "capability": manifest["execution"]["capability"]}
    if args.proposal:
        try:
            proposal = json.loads(Path(args.proposal).read_text())
        except (OSError, ValueError) as error:
            raise LoopError(f"cannot read the proposal {args.proposal}: {error}") from None
        errors = validate_proposal(proposal, manifest, path.parent, path.name)
        if errors:
            raise LoopError("invalid definer proposal: " + "; ".join(errors))
        out["proposal"] = {"ok": True, "unknown_slots": sorted(name for name, slot in proposal["slots"].items()
                                                              if slot["status"] == "unknown")}
    return EXIT_OK, out


def cmd_init(args) -> tuple:
    manifest, path = load_manifest(args.manifest)
    campaign_dir = Path(args.campaign).resolve()
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise LoopError(f"workspace {workspace} is not a directory")
    if campaign_dir == workspace or workspace in campaign_dir.parents or campaign_dir in workspace.parents:
        raise LoopError("the campaign folder and the subject workspace must be separate folders, neither inside the other: the "
                        "campaign folder is the Until Loop's workspace and holds only campaign state")
    cases = [item for item in args.cases.split(",") if item]
    if not cases:
        raise LoopError("--cases needs at least one case id for the first scope")
    budget = parse_budget(args.budget)
    if not budget:
        raise LoopError("a campaign needs a budget: pass --budget seconds=3600,turns=400 (the owner's number, or a default the "
                        "owner confirmed); every autonomous loop carries a real quota")
    window_size = args.quiet_window if args.quiet_window is not None else manifest.get("quiet_window", 2)
    if window_size < 1:
        raise LoopError("--quiet-window must be at least 1")
    approved = [item for item in (args.approve_case or "").split(",") if item]
    if approved:
        require_owner(args)
    with locked(campaign_dir, create=True):
        if (campaign_dir / "campaign.json").exists():
            raise LoopError(f"{campaign_dir / 'campaign.json'} already exists: a campaign is never re-initialised in place")
        created = now()
        state = {
            "schema": CAMPAIGN_SCHEMA, "id": secrets.token_hex(5), "subject": manifest["subject"]["name"], "created": created,
            "updated": created, "workspace": str(workspace),
            "manifest": {"path": str(path), "sha256": sha256_file(path), "boundary_sha256": boundary_hash(manifest, path.parent)},
            "ratification": None, "readiness": None, "budget": budget, "consumed": {}, "quiet_window": window_size,
            "scopes": [], "scope": "S0", "tip": None, "iterations": [], "steps": {}, "tasks": [], "unknowns": [],
            "approved_cases": approved, "events": [], "stop": None, "regression_ack": None, "start_failures": {},
            "poll_failures": {}, "launch_intents": {}, "cleaned_launches": {}}
        camp = Campaign(campaign_dir, state=state, manifest=manifest, manifest_path=path)
        catalog = load_catalog(camp)
        missing = [item for item in cases if item not in catalog]
        if missing:
            raise LoopError("not in the adapter's catalog: " + ", ".join(missing))
        gated = [item for item in cases if owner_gated_case(camp, catalog[item])]
        if gated:
            raise LoopError("owner-gated cases need --approve-case with --yes-owner-approved: " + ", ".join(gated))
        identity = Facts(camp).identity
        state["tip"] = identity["build"]
        state["scopes"].append(open_scope(camp, "S0", cases, "start", False, catalog))
        git = subprocess.run(["git", "init", "-q", str(campaign_dir)], capture_output=True, text=True, check=False)
        if git.returncode != 0:
            raise LoopError("git is required: the campaign folder is the Until Loop workspace and its freshness is a Git tree "
                            f"({git.stderr.strip()[-200:]})")
        # Nothing in this folder may be ignored: the Until Loop fingerprints it with `git add -A`. A rule here outranks
        # .git/info/exclude and the user's global excludes, which would otherwise hide the state from the fingerprint.
        (campaign_dir / ".gitignore").write_text("# closed-loop: nothing in this folder is ignored; the Until Loop fingerprints "
                                                 "it with `git add -A`\n!*\n")
        camp.event("init", scope="S0", cases=cases)
        camp.save()
    return EXIT_OK, {"ok": True, "campaign": str(campaign_dir), "id": state["id"], "scope": state["scopes"][0],
                     "identity": camp.identity, "tip": state["tip"], "work_dir": str(camp.work_dir)}


def cmd_ratify(args) -> tuple:
    require_owner(args)
    with session(args) as camp:
        camp.state["ratification"] = {"boundary_sha256": camp.boundary, "at": now(), "note": args.note or ""}
        camp.event("ratify", boundary_sha256=camp.boundary)
    return EXIT_OK, {"ok": True, "ratified": camp.state["ratification"]}


def cmd_readiness(args) -> tuple:
    manifest, path = load_manifest(args.manifest)
    if not args.campaign:
        report, _ = readiness_report(manifest, path.parent, args.workspace, None, False)
        return (EXIT_OK if (report["start_ok"] or not args.require_start) else EXIT_NOT_READY), report
    with session(args) as camp:
        if camp.manifest_path != path:
            raise LoopError("--manifest is not this campaign's adapter manifest")
        if args.workspace and Path(args.workspace).resolve() != Path(camp.state["workspace"]).resolve():
            raise LoopError(f"--workspace {args.workspace} is not this campaign's workspace ({camp.state['workspace']}): readiness "
                            "proves claims about the subject the campaign improves, so it cannot be proven elsewhere")
        ratification = camp.state.get("ratification")
        ratified = bool(ratification and ratification["boundary_sha256"] == camp.boundary)
        scoring = Facts(camp).identity["scoring"]  # the evaluator these claims are proven under
        # A refresh withdraws the previous result before it probes: if it fails or is interrupted, the old pass must not stand.
        camp.state["readiness"] = {"at": now(), "boundary_sha256": camp.boundary, "scoring": scoring, "start_ok": False,
                                   "blocked": ["a readiness refresh began and has not finished"], "allowed_claims": [], "claims": {}}
        camp.save()

        def guard(spent):
            used = used_amounts(camp.state)
            for name, amount in spent.items():
                used[name] = used.get(name, 0) + amount
            over = over_budget(camp.state["budget"], used)
            if over:
                raise LoopError("budget used: " + ", ".join(over) + "; readiness stops before the next probe (only the owner "
                                "raises the budget: reopen --budget)")

        try:
            report, consumed = readiness_report(camp.manifest, path.parent, camp.state["workspace"], camp.dir, ratified, guard)
        except LoopError as error:
            add_consumed(camp.state, getattr(error, "consumed", {}))
            camp.save()  # the probes that ran cost what they cost, though the readiness did not finish
            raise
        add_consumed(camp.state, consumed)
        camp.state["readiness"] = {"at": now(), "boundary_sha256": report["boundary_sha256"], "scoring": scoring,
                                   "start_ok": report["start_ok"], "blocked": report["blocked"],
                                   "allowed_claims": report["allowed_claims"],
                                   "claims": {claim: {"state": entry["state"], "evidence": entry["evidence"]}
                                              for claim, entry in report["claims"].items()}}
    return (EXIT_OK if (report["start_ok"] or not args.require_start) else EXIT_NOT_READY), report


def cmd_status(args) -> tuple:
    camp = Campaign(args.campaign)
    state = camp.state
    out = {"subject": state["subject"], "scope": camp.scope(), "tip": state["tip"], "iterations": len(state["iterations"]),
           "quota": quota_status(state), "stop": state.get("stop"), "ratified": bool(state.get("ratification")),
           "open_tasks": [task for task in state["tasks"] if task["status"] == "open"], "identity": camp.identity,
           "readiness": state.get("readiness"), "unknowns": [item for item in state["unknowns"] if not item.get("resolved")]}
    if state["iterations"]:
        last = state["iterations"][-1]
        out["last_iteration"] = {key: last[key] for key in ("index", "scope", "mode", "quiet", "quiet_reasons", "build_after")}
    if not args.no_certificate and state["iterations"]:
        cert = certificate(camp, Facts(camp))
        out["certificate"] = {"status": cert["status"], "reasons": cert["reasons"]}
    return EXIT_OK, out


def cmd_next(args) -> tuple:
    return EXIT_OK, plan_next(Campaign(args.campaign))


def cmd_step(args) -> tuple:
    with session(args) as camp:
        result = apply_action(camp, plan_next(camp))
    return (EXIT_NOT_READY if result["action"] == "blocked" else EXIT_OK), result


def check_hunt_result(result) -> None:
    spots = result.get("blind_spots") if isinstance(result, dict) else None
    if not isinstance(spots, list):
        raise LoopError('a hunt task closes with --result \'{"blind_spots": [...]}\' (an empty list is valid)')
    for spot in spots:
        if not (isinstance(spot, dict) and is_text(spot.get("what")) and spot.get("disposition") in HUNT_DISPOSITIONS):
            raise LoopError("every blind spot needs what and a disposition of " + ", ".join(HUNT_DISPOSITIONS))
        if spot["disposition"] == "rejected" and not is_text(spot.get("reason")):
            raise LoopError("a rejected blind spot needs a reason")


def cmd_task(args) -> tuple:
    with session(args) as camp:
        tasks = camp.state["tasks"]
        if args.task_verb == "add":
            task = {"id": f"T{len(tasks) + 1}", "kind": args.kind, "text": args.text, "needs_owner": args.needs_owner,
                    "status": "open", "opened": now()}
            if not is_text(args.kind) or not is_text(args.text):
                raise LoopError("--kind and --text are required")
            tasks.append(task)
            camp.event("task", id=task["id"], kind=task["kind"])
        else:
            task = next((item for item in tasks if item["id"] == args.id), None)
            if task is None:
                raise LoopError(f"no task {args.id}")
            if task["status"] != "open":
                raise LoopError(f"task {args.id} is already {task['status']}")
            if task.get("needs_owner") and not args.approve:
                raise LoopError(f"task {args.id} needs the owner's approval before it is done, not only before it is closed: "
                                "ask, do it only after they approve, then pass --approve")
            try:
                recorded = json.loads(args.result) if args.result else None
                spent = json.loads(args.consumed) if args.consumed else None
            except ValueError as error:
                raise LoopError(f"--result and --consumed must be JSON: {error}") from None
            if task["kind"] == "hunt":
                check_hunt_result(recorded)
            if spent is not None and not (isinstance(spent, dict) and all(is_amount(value) for value in spent.values())):
                raise LoopError("--consumed must be an object of non-negative numbers")
            add_consumed(camp.state, spent)
            task.update(status="done", result=recorded, closed=now(), done_after=len(camp.state["iterations"]))
            camp.event("task-done", id=task["id"])
    return EXIT_OK, {"ok": True, "task": task}


def cmd_unknown(args) -> tuple:
    with session(args) as camp:
        unknowns = camp.state["unknowns"]
        if args.unknown_verb == "add":
            if not is_text(args.text):
                raise LoopError("--text names what is not known")
            unknowns.append({"text": args.text, "inside_claim": args.inside_claim, "opened": now(), "resolved": None})
            camp.event("unknown", index=len(unknowns) - 1, inside_claim=args.inside_claim)
        else:
            if args.index is None or not 0 <= args.index < len(unknowns):
                raise LoopError("--index names an existing unknown (see status)")
            if not is_text(args.evidence):
                raise LoopError("--evidence says what answered the unknown: resolving one is an attestation the report will quote")
            unknowns[args.index].update(resolved=now(), resolution=args.evidence)
            camp.event("unknown-resolved", index=args.index)
    return EXIT_OK, {"ok": True, "unknowns": unknowns}


def cmd_approve(args) -> tuple:
    require_owner(args)
    with session(args) as camp:
        if args.case not in load_catalog(camp):
            raise LoopError(f"{args.case} is not in the adapter's catalog")
        approved = camp.state.setdefault("approved_cases", [])
        if args.case not in approved:
            approved.append(args.case)
        reopened = bool(camp.state.get("stop") and camp.state["stop"].get("owner_gated_cases"))
        if reopened:
            camp.state["stop"] = None
        camp.event("approve", case=args.case, note=args.note or "", reopened=reopened)
    return EXIT_OK, {"ok": True, "approved": approved, "reopened": reopened}


def cmd_reopen(args) -> tuple:
    require_owner(args)
    with session(args) as camp:
        if args.budget:
            budget = parse_budget(args.budget)
            used = camp.state["consumed"]
            if any(key in used and limit <= used[key] for key, limit in budget.items()):
                raise LoopError("a new budget must exceed what is already consumed (the quota is aggregate)")
            camp.state["budget"] = {**camp.state["budget"], **budget}
        stop = camp.state.get("stop")
        camp.state["stop"] = None
        camp.state["regression_ack"] = len(camp.state["iterations"])
        camp.event("reopen", note=args.note or "", cleared=(stop or {}).get("reason"))
    return EXIT_OK, {"ok": True, "cleared": stop, "budget": camp.state["budget"]}


def cmd_cancel(args) -> tuple:
    with session(args) as camp:
        step = camp.state["steps"].get(args.key)
        if not step or step["status"] != "running":
            raise LoopError(f"no running step {args.key}")
        reply = camp.call("step", ["cancel", "--handle", step["handle"]])
        if reply.get("status") != "cancelled":
            raise LoopError(f"the adapter did not acknowledge the cancellation (it answered {json.dumps(reply)[:200]}): the step "
                            "is still recorded as running")
        rec = fail_step(camp, args.key, "cancelled", "the step was cancelled by the operator", None)
    return EXIT_OK, {"ok": True, "cancelled": args.key, "iteration": rec["index"], "next": "run cleanup before any certificate"}


def cmd_cleanup(args) -> tuple:
    with session(args) as camp:
        argv = camp.manifest["execution"].get("cleanup")
        if not argv:
            raise LoopError("the manifest declares no execution.cleanup")
        ratification = camp.state.get("ratification")
        if not (ratification and ratification["boundary_sha256"] == camp.boundary):
            raise LoopError("cleanup is an adapter command and the owner has not ratified the boundary that names it: ratify first "
                            "(nothing runs before that)")
        pending = [item for item in camp.state["iterations"]
                   if not (item["cleanup"].get("verified") and is_text(item["cleanup"].get("receipt")))]
        uncertain = [key for key in camp.state["launch_intents"] if key not in camp.state["cleaned_launches"]]
        keys = [item["key"] for item in pending] + uncertain
        if not keys:
            return EXIT_OK, {"ok": True, "covered": [], "receipt": None, "note": "no run lacks cleanup evidence, so nothing was run"}
        reply = run_argv(camp.manifest, camp.manifest_path.parent, list(argv) + ["--keys", ",".join(keys)], "cleanup",
                         workspace=camp.state["workspace"], campaign=camp.dir)
        if not (reply.get("verified") is True and is_text(reply.get("receipt"))):
            raise LoopError("the adapter's cleanup did not report verified with a receipt: " + json.dumps(reply)[:200])
        for item in pending:
            item["cleanup"] = {"verified": True, "receipt": reply["receipt"], "by": "cleanup"}
        for key in uncertain:
            camp.state["cleaned_launches"][key] = reply["receipt"]
        camp.event("cleanup", keys=keys, receipt=reply["receipt"])
    return EXIT_OK, {"ok": True, "covered": keys, "receipt": reply["receipt"]}


def cmd_check(args) -> tuple:
    if args.clause not in CLAUSES:
        raise LoopError("--clause must be one of " + ", ".join(CLAUSES))
    sha = script_sha()
    if args.expect_sha and args.expect_sha != sha:
        return EXIT_IDENTITY, {"clause": args.clause, "pass": False, "script_sha256": sha, "reasons": [
            f"the check script changed since this contract was frozen (expected {args.expect_sha[:12]}, running {sha[:12]})"]}
    camp = Campaign(args.campaign)
    if args.expect_scope and camp.state["scope"] != args.expect_scope:
        return EXIT_IDENTITY, {"clause": args.clause, "pass": False, "script_sha256": sha, "reasons": [
            f"this contract is for scope {args.expect_scope} but the campaign is at scope {camp.state['scope']}: open a new contract"]}
    if args.expect_identity and camp.identity != args.expect_identity:
        return EXIT_IDENTITY, {"clause": args.clause, "pass": False, "script_sha256": sha, "reasons": [
            "this contract is for another campaign identity"]}
    problem = fingerprint_problem(camp.dir)
    if problem:
        raise LoopError(problem)
    result = CHECKS[args.clause](camp, Facts(camp))
    result.update(script_sha256=sha, campaign_identity=camp.identity, clause=args.clause)
    return (EXIT_OK if result["pass"] else EXIT_NOT_READY), result


def cmd_certificate(args) -> tuple:
    camp = Campaign(args.campaign)
    cert = certificate(camp, Facts(camp))
    return (EXIT_OK if cert["status"] == "converged" else EXIT_NOT_READY), cert


def cmd_coverage(args) -> tuple:
    camp = Campaign(args.campaign)
    allowed, gated = widening_candidates(camp, Facts(camp))
    scope = camp.scope()
    return EXIT_OK, {"scope": scope["id"], "cases": scope["cases"], "values": scope["values"], "not_covered": scope["not_covered"],
                     "widening_candidates": allowed, "owner_gated": gated}


def cmd_contract(args) -> tuple:
    camp = Campaign(args.campaign)
    problem = fingerprint_problem(camp.dir)
    if problem:
        raise LoopError(problem)
    contract = build_contract(camp)
    if args.out:
        Path(args.out).write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    return EXIT_OK, contract


def cmd_report(args) -> tuple:
    with session(args) as camp:
        out = write_report(camp)
    return EXIT_OK, out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    verbs = parser.add_subparsers(dest="verb", required=True)

    def add(name, handler, *flags):
        sub = verbs.add_parser(name)
        sub.set_defaults(handler=handler)
        for flag, options in flags:
            sub.add_argument(flag, **options)
        return sub

    campaign = ("--campaign", {"required": True})
    owner = ("--yes-owner-approved", {"action": "store_true"})
    add("adapter-check", cmd_adapter_check, ("--manifest", {"required": True}), ("--proposal", {}))
    add("init", cmd_init, ("--manifest", {"required": True}), campaign, ("--workspace", {"required": True}),
        ("--cases", {"required": True}), ("--budget", {"default": ""}), ("--quiet-window", {"type": int}),
        ("--approve-case", {}), owner)
    add("ratify", cmd_ratify, campaign, owner, ("--note", {}))
    add("readiness", cmd_readiness, ("--manifest", {"required": True}), ("--campaign", {}), ("--workspace", {}),
        ("--require-start", {"action": "store_true"}))
    add("status", cmd_status, campaign, ("--no-certificate", {"action": "store_true"}))
    add("next", cmd_next, campaign)
    add("step", cmd_step, campaign)
    task = add("task", cmd_task, campaign)
    task.add_argument("task_verb", choices=("add", "done"))
    for flag, options in (("--kind", {}), ("--text", {}), ("--needs-owner", {"action": "store_true"}), ("--id", {}),
                          ("--result", {}), ("--consumed", {}), ("--approve", {"action": "store_true"})):
        task.add_argument(flag, **options)
    unknown = add("unknown", cmd_unknown, campaign)
    unknown.add_argument("unknown_verb", choices=("add", "resolve"))
    unknown.add_argument("--text")
    unknown.add_argument("--inside-claim", action="store_true")
    unknown.add_argument("--index", type=int)
    unknown.add_argument("--evidence")
    add("approve", cmd_approve, campaign, ("--case", {"required": True}), owner, ("--note", {}))
    add("reopen", cmd_reopen, campaign, owner, ("--budget", {}), ("--note", {}))
    add("cancel", cmd_cancel, campaign, ("--key", {"required": True}))
    add("cleanup", cmd_cleanup, campaign)
    add("check", cmd_check, campaign, ("--clause", {"required": True}), ("--expect-sha", {}), ("--expect-scope", {}),
        ("--expect-identity", {}))
    add("certificate", cmd_certificate, campaign)
    add("coverage", cmd_coverage, campaign)
    add("contract", cmd_contract, campaign, ("--out", {}))
    add("report", cmd_report, campaign)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, out = args.handler(args)
    except LoopError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return EXIT_ERROR
    except OSError as error:
        print(json.dumps({"error": f"file system error ({type(error).__name__}: {error})"}), file=sys.stderr)
        return EXIT_ERROR
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
        if os.environ.get("CLOSED_LOOP_DEBUG"):
            raise
        print(json.dumps({"error": f"malformed state or adapter output ({type(error).__name__}: {error}); set CLOSED_LOOP_DEBUG "
                                   "for the traceback"}), file=sys.stderr)
        return EXIT_ERROR
    print(json.dumps(out, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
