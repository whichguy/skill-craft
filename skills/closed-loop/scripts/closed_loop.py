#!/usr/bin/env python3
"""closed_loop.py: the orchestrator of the closed-loop skill.

A campaign improves a *subject* by running it on cases, grading the runs, finding fixes, trying them and repeating until a
script-checked certificate says nothing material is left in a named scope, then widening the scope when it is stuck. Everything
specific to a subject lives in an adapter manifest (closed-loop-adapter/1): pinned argument lists this script calls and whose JSON
it reads. This script never calls a model; the operator (a model) reads what it prints and does one step at a time.

Every verb prints one JSON object on stdout. Exit 0 ok, 1 a check or readiness gate did not pass, 2 error, 3 identity mismatch.

  adapter-check --manifest M                       validate a manifest (shape, pinned argument lists, execution boundary)
  init          --manifest M --campaign D --workspace W --cases A,B [--budget seconds=3600,turns=400] [--quiet-window K]
  ratify        --campaign D --yes-owner-approved [--note TEXT]   record the owner's approval of the execution boundary
  readiness     --manifest M [--campaign D] [--workspace W] [--require-start]   claim states and the claims they allow
  status        --campaign D [--no-certificate]    scope, quota, last iteration, certificate
  next          --campaign D                       print the next action without doing it
  step          --campaign D                       do the next action: start or poll a step, open a scope, add a task, or stop
  task          --campaign D add --kind K --text T [--needs-owner] | done --id I [--result JSON] [--approve]
  unknown       --campaign D add --text T [--inside-claim] | resolve --index N   record what is not known (C7 reads it)
  approve       --campaign D --case ID --yes-owner-approved [--note TEXT]   allow an owner-gated case and reopen
  check         --campaign D --clause C1..C7 [--expect-sha SHA]    one certificate check (an until-loop exit check)
  certificate   --campaign D                       all seven checks: converged, or incomplete with reasons
  coverage      --campaign D                       what the scope covers, what it does not, which cases could widen it
  contract      --campaign D --kind scope|readiness [--out FILE]   an until-loop contract with script-owned exit checks
  report        --campaign D                       write report.md and report.json for the owner

Campaign folder: campaign.json (closed-loop-campaign/1, written atomically under campaign.lock), journal.md (append-only, one
entry per iteration), runs/<step key>/ (what the adapter writes), report.md, report.json.

Adapter protocol (closed-loop-adapter/1). The manifest's `commands` hold argument lists for these verbs; each prints one JSON
object. CLOSED_LOOP_WORKSPACE names the subject's working directory; only PATH and `execution.env_allow` names reach the child.
  cases     -> {"cases": [{"id", "dimensions": {name: value}, "cost", "requires": [...], "hosted": bool}]}
  records   -> {"records": [{"id", "title", "material", "target": "subject"|"adapter", "status", "evidence", "reopen_when",
                             "cases": [...]}]}
  identity  -> {"scoring": token, "build": token}
  probe ID  -> {"state", "evidence"}                               (readiness claims)
  step start --key K --scope S --cases A,B --mode iterate|sweep --base TIP --out DIR -> {"handle", "status", "iteration"?}
       (idempotent on K: a second start with the same key returns the same handle and launches nothing)
  step poll --handle H   -> {"status": "running"|"done"|"failed"|"cancelled", "iteration"?, "error"?}
  step cancel --handle H -> {"status": "cancelled"}
  An `iteration` object carries: build_before, build_after, scoring, cases {id: {ran, floors_met, baseline}}, review/judge
  {valid, complete}, discoveries [{id, material, repeat}], candidate {id, hash, outcome} or null, invalid [...], cleanup
  {verified, receipt}, tier {green, build}, acceptance {candidate, evidence} or null, consumed {key: amount}.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

CAMPAIGN_SCHEMA = "closed-loop-campaign/1"
ADAPTER_SCHEMA = "closed-loop-adapter/1"
SCRIPT = Path(__file__).resolve()
CAPABILITIES = ("read-only", "writes-worktree", "hosted")
EVAL_CLASSES = ("scripted", "scripted+judge", "judge-only")
REQUIRED_VERBS = ("cases", "records", "identity", "step")
KNOWN_VERBS = REQUIRED_VERBS + ("probe",)
CLAUSES = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
CLAUSE_TEXT = {
    "C1": "Every material in-scope record is resolved with evidence; a deferred, owner-held or unresolved material record keeps "
          "the scope incomplete.",
    "C2": "The last K iterations at this scope, build and scoring identity were quiet: valid complete reviews, no material "
          "discovery, no candidate pending.",
    "C3": "Every scope case meets its floors on the current build against a comparable baseline.",
    "C4": "Every dimension value the scope declares has a run on the current build, and every catalog value outside it is listed "
          "as not covered.",
    "C5": "The campaign's runs were cleaned up with positive evidence, and a green quick-tier receipt exists for the current "
          "build.",
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
RESOLVED_WITH_EVIDENCE = ("dropped", "refuted", "rejected")
ACTIONABLE_STATUSES = ("open", "admitted", "promoted", "undecided")
EXIT_OK, EXIT_NOT_READY, EXIT_ERROR, EXIT_IDENTITY = 0, 1, 2, 3


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
    if not isinstance(subject, dict) or not str(subject.get("name") or "").strip():
        errors.append("subject.name is required")
    execution = m.get("execution")
    if not isinstance(execution, dict):
        errors.append("execution (the execution boundary) is required")
    else:
        if execution.get("capability") not in CAPABILITIES:
            errors.append("execution.capability must be one of " + ", ".join(CAPABILITIES))
        env = execution.get("env_allow", [])
        if not (isinstance(env, list) and all(isinstance(name, str) and name for name in env)):
            errors.append("execution.env_allow must be a list of environment variable names")
        if execution.get("cleanup") is not None:
            errors += argv_errors("execution.cleanup", execution["cleanup"])
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
    if not (isinstance(dims, list) and all(isinstance(name, str) and name for name in dims)):
        errors.append("dimensions must be a list of dimension names")
    window = m.get("quiet_window", 2)
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
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


def boundary_hash(manifest: dict) -> str:
    """What the owner ratifies: every command, the execution boundary, the authority lists and the claims."""
    keys = ("commands", "execution", "authority", "claims", "evaluation_class")
    return sha256_text(canonical({key: manifest.get(key) for key in keys}))


def call_adapter(manifest: dict, manifest_dir: Path, verb: str, args=(), workspace=None, campaign=None, timeout=None) -> dict:
    """Run one adapter verb as a pinned argument list in the controlled environment and return its JSON object."""
    commands = manifest["commands"]
    if verb not in commands:
        raise LoopError(f"the adapter has no {verb} command")
    argv = list(commands[verb]) + [str(arg) for arg in args]
    execution = manifest["execution"]
    env = {"PATH": os.environ.get("PATH", os.defpath)}
    for name in execution.get("env_allow", []):
        if name in os.environ:
            env[name] = os.environ[name]
    if workspace:
        env["CLOSED_LOOP_WORKSPACE"] = str(workspace)
    if campaign:
        env["CLOSED_LOOP_CAMPAIGN"] = str(campaign)
    cwd = (manifest_dir / execution.get("cwd", ".")).resolve()
    try:
        done = subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout, check=False)
    except OSError as error:
        raise LoopError(f"adapter {verb} could not start ({argv[0]}): {error.strerror}") from None
    except subprocess.TimeoutExpired:
        raise LoopError(f"adapter {verb} did not finish within {timeout} s") from None
    if done.returncode != 0:
        raise LoopError(f"adapter {verb} exited {done.returncode}: {(done.stderr or done.stdout).strip()[-400:]}")
    try:
        out = json.loads(done.stdout)
    except ValueError:
        raise LoopError(f"adapter {verb} printed no JSON object: {done.stdout.strip()[:200]!r}") from None
    if not isinstance(out, dict):
        raise LoopError(f"adapter {verb} must print a JSON object")
    return out


# -------------------------------------------------------------------------------------------------------------------- state

@contextlib.contextmanager
def locked(campaign_dir: Path):
    campaign_dir.mkdir(parents=True, exist_ok=True)
    with open(campaign_dir / "campaign.lock", "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
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

    def __init__(self, campaign_dir) -> None:
        self.dir = Path(campaign_dir).resolve()
        self.state = load_state(self.dir)
        self.manifest, self.manifest_path = load_manifest(self.state["manifest"]["path"])
        if sha256_file(self.manifest_path) != self.state["manifest"]["sha256"]:
            raise LoopError("the adapter manifest changed since init: its identity differs, start a new campaign")
        self.facts_cache: dict = {}

    def call(self, verb: str, args=()) -> dict:
        return call_adapter(self.manifest, self.manifest_path.parent, verb, args,
                            workspace=self.state["workspace"], campaign=self.dir)

    def save(self) -> None:
        save_state(self.dir, self.state)

    def event(self, what: str, **fields) -> None:
        self.state["events"].append({"at": now(), "event": what, **fields})

    @property
    def identity(self) -> str:
        return sha256_text(self.state["manifest"]["sha256"] + script_sha() + boundary_hash(self.manifest))[:16]

    def scope(self) -> dict:
        return next(item for item in self.state["scopes"] if item["id"] == self.state["scope"])


class Facts:
    """Adapter queries a certificate needs, fetched once each per command."""

    def __init__(self, camp: Campaign) -> None:
        self.camp = camp
        self._records = self._catalog = self._identity = None

    @property
    def records(self) -> list:
        if self._records is None:
            out = self.camp.call("records").get("records")
            if not isinstance(out, list):
                raise LoopError('adapter records must print {"records": [...]}')
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
            self._identity = self.camp.call("identity")
        return self._identity


def load_catalog(camp: Campaign) -> dict:
    cases = camp.call("cases").get("cases")
    if not isinstance(cases, list) or not cases:
        raise LoopError('adapter cases must print {"cases": [...]} with at least one case')
    catalog = {}
    for case in cases:
        if not isinstance(case, dict) or not str(case.get("id") or ""):
            raise LoopError("every adapter case needs an id")
        catalog[case["id"]] = case
    return catalog


def case_values(case: dict, dims: list) -> set:
    found = case.get("dimensions") or {}
    return {f"{name}={found[name]}" for name in dims if name in found}


def open_scope(camp: Campaign, scope_id: str, cases: list, reason: str, sweep: bool, catalog: dict) -> dict:
    dims = camp.manifest.get("dimensions", [])
    inside = set()
    for case_id in cases:
        inside |= case_values(catalog[case_id], dims)
    everything = set()
    for case in catalog.values():
        everything |= case_values(case, dims)
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
        if not key or number <= 0:
            raise LoopError(f"budget {part!r} needs a name and a positive amount")
        budget[key] = int(number) if number == int(number) else number
    return budget


def quota_status(state: dict) -> dict:
    budget, used = state.get("budget") or {}, state.get("consumed") or {}
    over = sorted(key for key, limit in budget.items() if used.get(key, 0) >= limit)
    return {"budget": budget, "consumed": used, "exhausted": bool(over), "over": over}


# ------------------------------------------------------------------------------------------------------------- iterations

def derive_iteration(state: dict, key: str, step: dict, facts: dict) -> dict:
    """The orchestrator's own record of one finished step: what the adapter reported, and whether it was quiet."""
    facts = facts or {}
    review, judge = facts.get("review") or {}, facts.get("judge") or {}
    cases = facts.get("cases") or {}
    invalid = [str(item) for item in (facts.get("invalid") or [])]
    discoveries = facts.get("discoveries") or []
    candidate = facts.get("candidate")
    reasons = []
    if not (review.get("valid") and review.get("complete")):
        reasons.append("the review was not valid and complete")
    if not (judge.get("valid") and judge.get("complete")):
        reasons.append("the judge was not valid and complete")
    if invalid:
        reasons.append("invalid or incomplete evidence was recorded")
    if any(item.get("material") for item in discoveries):
        reasons.append("a material discovery, new or repeated")
    if candidate:
        reasons.append("a candidate outcome is present")
    if not cases or not all(item.get("ran") and item.get("floors_met") for item in cases.values()):
        reasons.append("a scope case did not run or missed its floors")
    return {
        "index": len(state["iterations"]) + 1, "key": key, "scope": step["scope"], "mode": step["mode"],
        "ended": now(), "build_before": facts.get("build_before", step.get("base")), "build_after": facts.get("build_after"),
        "scoring": facts.get("scoring"), "cases": cases, "review": review, "judge": judge, "discoveries": discoveries,
        "candidate": candidate, "invalid": invalid, "cleanup": facts.get("cleanup") or {}, "tier": facts.get("tier") or {},
        "acceptance": facts.get("acceptance"), "consumed": facts.get("consumed") or {},
        "quiet": not reasons, "quiet_reasons": reasons,
    }


def window(state: dict) -> list:
    """The trailing iterations that ran on the current build at the current scope and scoring identity."""
    iterations = state["iterations"]
    if not iterations:
        return []
    last = iterations[-1]
    out = []
    for item in reversed(iterations):
        if (item["scope"], item["scoring"], item["build_before"]) == (last["scope"], last["scoring"], last["build_after"]):
            out.append(item)
        else:
            break
    return list(reversed(out))


def stale_reason(camp: Campaign, facts: Facts):
    """Why the last iteration no longer describes the subject, or None."""
    iterations = camp.state["iterations"]
    if not iterations:
        return None
    last, now_identity = iterations[-1], facts.identity
    if now_identity.get("build") != last["build_after"]:
        return f"the subject's build is now {now_identity.get('build')!r}, the last iteration left {last['build_after']!r}"
    if now_identity.get("scoring") != last["scoring"]:
        return f"the scoring identity is now {now_identity.get('scoring')!r}, the last iteration used {last['scoring']!r}"
    return None


# ---------------------------------------------------------------------------------------------------------- the seven checks

def verdict(clause: str, reasons: list, **detail) -> dict:
    return {"id": clause, "pass": not reasons, "reasons": reasons, "detail": detail}


def check_c1(camp: Campaign, facts: Facts) -> dict:
    scope_cases = set(camp.scope()["cases"])
    blocking, actionable, owner_gated, outside, adapter_backlog = [], [], [], [], []
    for rec in facts.records:
        if rec.get("target", "subject") == "adapter":
            adapter_backlog.append(rec.get("id"))
            continue
        if not rec.get("material"):
            continue
        related = rec.get("cases")
        if related and not (set(related) & scope_cases):
            outside.append(rec.get("id"))
            continue
        status = rec.get("status")
        if status == "verified" or (status in RESOLVED_WITH_EVIDENCE and rec.get("evidence")):
            continue
        blocking.append({"id": rec.get("id"), "status": status, "reopen_when": rec.get("reopen_when")})
        (actionable if status in ACTIONABLE_STATUSES else owner_gated).append(rec.get("id"))
    reasons = [f"{item['id']} is {item['status']}: a material record keeps the scope incomplete" for item in blocking]
    return verdict("C1", reasons, blocking=blocking, actionable=actionable, owner_gated=owner_gated,
                   outside_scope=outside, adapter_backlog=adapter_backlog)


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
        ran = [item["cases"][case_id] for item in win if case_id in item["cases"] and item["cases"][case_id].get("ran")]
        if not ran:
            reasons.append(f"{case_id} has no run on the current build")
            continue
        latest = ran[-1]
        if not latest.get("floors_met"):
            reasons.append(f"{case_id} missed its floors on the current build")
        if latest.get("baseline") != "comparable":
            reasons.append(f"{case_id} has no comparable baseline (baseline is {latest.get('baseline')!r}): unknown blocks")
    return verdict("C3", reasons)


def check_c4(camp: Campaign, facts: Facts) -> dict:
    scope = camp.scope()
    dims = camp.manifest.get("dimensions", [])
    reasons = []
    ran_values = set()
    for item in window(camp.state):
        for case_id, result in item["cases"].items():
            if result.get("ran") and case_id in facts.catalog:
                ran_values |= case_values(facts.catalog[case_id], dims)
    for value in scope["values"]:
        if value not in ran_values:
            reasons.append(f"{value} is declared by the scope but has no run on the current build")
    everything = set()
    for case in facts.catalog.values():
        everything |= case_values(case, dims)
    for value in sorted(everything - set(scope["values"])):
        if value not in scope["not_covered"]:
            reasons.append(f"{value} is neither covered nor listed as not covered")
    return verdict("C4", reasons, not_covered=scope["not_covered"])


def check_c5(camp: Campaign, facts: Facts) -> dict:
    iterations = camp.state["iterations"]
    if not iterations:
        return verdict("C5", ["no iteration has run, so there is no cleanup or quick-tier receipt"])
    last = iterations[-1]
    reasons = []
    if not (last["cleanup"].get("verified") and last["cleanup"].get("receipt")):
        reasons.append("no positive cleanup evidence: absence of leftovers is not evidence")
    tier = last["tier"]
    if not tier.get("green"):
        reasons.append("no green quick-tier receipt")
    elif tier.get("build") != last["build_after"]:
        reasons.append(f"the quick-tier receipt is for build {tier.get('build')!r}, not {last['build_after']!r}")
    return verdict("C5", reasons)


def check_c6(camp: Campaign, facts: Facts) -> dict:
    reasons, promoted = [], []
    for item in camp.state["iterations"]:
        candidate = item.get("candidate")
        if candidate and candidate.get("outcome") == "PROMOTE":
            promoted.append(candidate.get("hash"))
            acceptance = item.get("acceptance") or {}
            if acceptance.get("candidate") != candidate.get("hash") or not acceptance.get("evidence"):
                reasons.append(f"iteration {item['index']} promoted {candidate.get('hash')!r} without acceptance evidence for it")
    return verdict("C6", reasons, promoted=promoted, note=None if promoted else "no candidate")


def check_c7(camp: Campaign, facts: Facts) -> dict:
    k = camp.state["quiet_window"]
    reasons = []
    win = window(camp.state)
    if not camp.state["iterations"]:
        reasons.append("no iteration has run")
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
    return {
        "status": "converged" if not reasons else "incomplete", "reasons": reasons, "checks": checks,
        "binds": {"scope": camp.state["scope"], "build": last.get("build_after"), "scoring": last.get("scoring"),
                  "campaign_identity": camp.identity,
                  "candidates": checks["C6"]["detail"].get("promoted", [])},
    }


# --------------------------------------------------------------------------------------------------- stuck modes and widening

def owner_gated_case(camp: Campaign, case: dict) -> bool:
    if case["id"] in camp.state.get("approved_cases", []):
        return False
    gated = set(camp.manifest.get("authority", {}).get("owner_only_requires", []))
    needs = set(case.get("requires") or [])
    if case.get("hosted"):
        needs.add("hosted")
    return bool(needs & gated)


def widening_candidates(camp: Campaign, facts: Facts) -> tuple:
    """(allowed, gated): catalog cases outside the scope that cover a value the scope lacks, cheapest first."""
    dims = camp.manifest.get("dimensions", [])
    scope = camp.scope()
    have = set(scope["values"])
    allowed, gated = [], []
    for case in facts.catalog.values():
        if case["id"] in scope["cases"]:
            continue
        fresh = case_values(case, dims) - have
        if not fresh:
            continue
        item = {"id": case["id"], "cost": case.get("cost", 1), "covers": sorted(fresh)}
        (gated if owner_gated_case(camp, case) else allowed).append(item)
    order = (lambda item: (item["cost"], -len(item["covers"]), item["id"]))
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


def start_action(camp: Campaign) -> dict:
    state = camp.state
    scope = camp.scope()
    # A failed step becomes its own invalid iteration, so a retry has the next index and therefore a new key; the same key is
    # only ever recomputed after a crash, which is exactly when the adapter must recognise it and launch nothing.
    key = f"{state['id']}-{scope['id']}-{len(state['iterations']) + 1}"
    return {"action": "start", "key": key, "scope": scope["id"], "cases": scope["cases"],
            "mode": "sweep" if scope["sweep_pending"] else "iterate", "base": state["tip"]}


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
    if not any(task.get("kind") == "hunt" for task in state["tasks"]):
        return {"action": "new_task", "task": {
            "kind": "hunt", "needs_owner": False,
            "text": "The catalog is fully covered by this scope. Run the blind-spot hunter (prompts/blind-spot-hunter.md): name "
                    "what this evaluation could not see and propose cases or probes that would expose it. Record each proposal "
                    "with `task done --result`; a new case enters only after it runs and is sensitive."}}
    return {"action": "stop", "status": "converged", "rung": "E5", **base,
            "reason": "the declared catalog is covered and the blind-spot hunt is recorded; this is not a claim that no "
                      "material problem remains outside what the evaluation can see"}


def plan_next(camp: Campaign) -> dict:
    """The next action, computed without changing anything."""
    state = camp.state
    if state.get("stop"):
        return {"action": "stop", **state["stop"]}
    for key, step in state["steps"].items():
        if step["status"] == "running":
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
        tried = [task for task in state["tasks"] if task.get("kind") == "diagnose" and task["status"] == "done"
                 and task.get("stall_at", 0) > last_promote]
        if len(tried) >= 2:
            return {"action": "stop", "status": "incomplete", "binds": cert["binds"],
                    "reason": "stalled: two diagnoses since the last promoted candidate did not unblock the work; the owner "
                              "should decide the next investigation"}
    if mode["mode"] == "stalled" and not any(task.get("stall_at") == len(state["iterations"]) for task in state["tasks"]):
        return {"action": "new_task", "task": {
            "kind": "diagnose", "needs_owner": False, "stall_at": len(state["iterations"]),
            "text": "Two iterations in a row produced no promoted candidate while material work remains. Diagnose before "
                    "widening: read the failing runs' upstream records, run the real case to the stage and stop it, or ask one "
                    "advisor the stuck question (rung E0). Record what you found with `task done --result`."}}
    return start_action(camp)


# ------------------------------------------------------------------------------------------------------------ doing a step

def journal(camp: Campaign, rec: dict) -> None:
    line = (f"- iteration {rec['index']} ({rec['scope']}, {rec['mode']}): {'quiet' if rec['quiet'] else 'not quiet'}; "
            f"{len(rec['discoveries'])} discoveries; candidate {(rec['candidate'] or {}).get('outcome', 'none')}; "
            f"build {rec['build_before']} -> {rec['build_after']}; consumed {json.dumps(rec['consumed'], sort_keys=True)}\n")
    with open(camp.dir / "journal.md", "a") as handle:
        handle.write(line)


def finish_step(camp: Campaign, key: str, facts: dict) -> dict:
    state = camp.state
    step = state["steps"][key]
    rec = derive_iteration(state, key, step, facts)
    state["iterations"].append(rec)
    state["tip"] = rec["build_after"]
    for name, amount in rec["consumed"].items():
        state["consumed"][name] = state["consumed"].get(name, 0) + amount
    step["status"], step["iteration"] = "done", rec["index"]
    scope = camp.scope()
    if step["mode"] == "sweep":
        scope["sweep_pending"] = False
    journal(camp, rec)
    return rec


def apply_action(camp: Campaign, act: dict) -> dict:
    state = camp.state
    kind = act["action"]
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
        out_dir = camp.dir / "runs" / act["key"]
        out_dir.mkdir(parents=True, exist_ok=True)
        reply = camp.call("step", ["start", "--key", act["key"], "--scope", act["scope"], "--cases", ",".join(act["cases"]),
                                   "--mode", act["mode"], "--base", act["base"] or "", "--out", out_dir])
        state["steps"][act["key"]] = {"handle": reply.get("handle"), "status": "running", "started": now(), "scope": act["scope"],
                                      "mode": act["mode"], "base": act["base"], "index": len(state["iterations"]) + 1}
        if not reply.get("handle"):
            raise LoopError("adapter step start returned no handle")
        if reply.get("status") == "done":
            return {"action": "start", "key": act["key"], "iteration": finish_step(camp, act["key"], reply.get("iteration"))["index"]}
        return {"action": "start", "key": act["key"], "handle": reply["handle"], "status": "running"}
    if kind == "poll":
        reply = camp.call("step", ["poll", "--handle", act["handle"]])
        status = reply.get("status")
        step = state["steps"][act["key"]]
        if status == "running":
            return {"action": "poll", "key": act["key"], "status": "running"}
        if status == "done":
            rec = finish_step(camp, act["key"], reply.get("iteration"))
            return {"action": "poll", "key": act["key"], "status": "done", "iteration": rec["index"], "quiet": rec["quiet"]}
        step["status"], step["error"] = "failed", str(reply.get("error") or status or "the step failed")
        facts = dict(reply.get("iteration") or {})
        facts["invalid"] = list(facts.get("invalid") or []) + ["step failed: " + step["error"]]
        rec = derive_iteration(state, act["key"], step, facts)
        state["iterations"].append(rec)
        state["tip"] = rec["build_after"] or state["tip"]
        journal(camp, rec)
        return {"action": "poll", "key": act["key"], "status": "failed", "error": step["error"]}
    raise LoopError(f"unknown action {kind!r}")


# ------------------------------------------------------------------------------------------------------------------ report

def write_report(camp: Campaign) -> dict:
    state = camp.state
    facts = Facts(camp)
    cert = certificate(camp, facts) if state["iterations"] else {"status": "incomplete", "reasons": ["no iteration has run"],
                                                                  "checks": {}, "binds": {}}
    c1 = (cert["checks"].get("C1") or {}).get("detail", {})
    stop = state.get("stop") or {}
    campaign_status = stop.get("status") or ("converged" if cert["status"] == "converged" else "incomplete")
    out = {
        "schema": "closed-loop-report/1", "at": now(), "subject": state["subject"], "scope": state["scope"],
        "scope_cases": camp.scope()["cases"], "scope_certificate": cert["status"], "campaign_status": campaign_status,
        "stop": stop or None, "binds": cert["binds"], "reasons": cert["reasons"],
        "unresolved": c1.get("blocking", []), "adapter_backlog": c1.get("adapter_backlog", []),
        "outside_scope": c1.get("outside_scope", []), "not_covered": camp.scope()["not_covered"],
        "unknowns": [item for item in state["unknowns"] if not item.get("resolved")], "quota": quota_status(state),
        "iterations": len(state["iterations"]),
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
    spent = (f"- consumed {json.dumps(out['quota']['consumed'], sort_keys=True)} of budget "
             f"{json.dumps(out['quota']['budget'], sort_keys=True)}")
    lines += ["## Quota", "", spent, f"- iterations: {out['iterations']}", ""]
    (camp.dir / "report.md").write_text("\n".join(lines))
    (camp.dir / "report.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


# ------------------------------------------------------------------------------------------------------------------ contract

def check_command(camp: Campaign, clause: str, sha: str) -> str:
    return shlex.join([sys.executable, str(SCRIPT), "check", "--campaign", str(camp.dir), "--clause", clause,
                       "--expect-sha", sha])


def build_contract(camp: Campaign, kind: str) -> dict:
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
        "environment": f"{sys.executable} {SCRIPT}; adapter manifest {camp.manifest_path}; campaign folder {camp.dir}. Call the "
                       "adapter only through this script. Script sha256 " + sha + "; campaign identity " + camp.identity + ".",
        "resources": [{"purpose": "campaign state", "locator": str(camp.dir / "campaign.json")},
                      {"purpose": "adapter manifest", "locator": str(camp.manifest_path)},
                      {"purpose": "orchestrator script", "locator": str(SCRIPT)}],
    }
    if kind == "readiness":
        command = shlex.join([sys.executable, str(SCRIPT), "readiness", "--manifest", str(camp.manifest_path), "--campaign",
                              str(camp.dir), "--require-start"])
        clause = "The start rule holds: a case runs, a measure scores and the improvement stage is bounded."
        return {
            "workspace": state["workspace"],
            "work": "Define and validate the missing adapter slots: read `readiness`, have the definer propose only what is "
                    "missing, obtain the owner's ratification of the execution boundary, then validate each claim by script.",
            "exit_condition": clause, "repeat_condition": "Another pass is allowed while a proposal is unvalidated and fixable; "
            "stop incomplete when the owner's ratification, authority or a resource is needed.",
            "required_trivial_reviews": 0,
            "exit_checks": [{"id": "R-START", "clause": clause, "command": command}], "context": context}
    if kind != "scope":
        raise LoopError("contract --kind must be scope or readiness")
    exit_condition = (f"Scope {scope['id']} is converged on the current build: " + " ".join(CLAUSE_TEXT[c] for c in CLAUSES)
                      + " Report satisfied only after every frozen check passed after the iteration's last change.")
    return {
        "workspace": state["workspace"],
        "work": f"Run one closed-loop iteration at scope {scope['id']}: run `{SCRIPT.name} step --campaign {camp.dir}` until a "
                "step finishes (poll while one runs; do any open task it prints), then run `status` and apply the campaign "
                "checkpoint: read the whole backlog, reconcile related findings, and choose the smallest discriminating next "
                "investigation.",
        "exit_condition": exit_condition,
        "repeat_condition": "Another iteration is allowed while `step` reports start, poll, task or widen; stop incomplete when it "
                            "reports a stop, the budget is used, or an owner decision is needed.",
        "required_trivial_reviews": 0,
        "exit_checks": [{"id": clause, "clause": CLAUSE_TEXT[clause], "command": check_command(camp, clause, sha)}
                        for clause in CLAUSES],
        "context": context}


# ----------------------------------------------------------------------------------------------------------------- readiness

def claim_states(manifest: dict, camp, workspace, ratified: bool) -> dict:
    out = {}
    for claim, meta in manifest.get("claims", {}).items():
        ladder = CLAIM_LADDERS[claim.split(":")[0]]
        entry = {"state": ladder[0], "effect": meta["effect"], "evidence": None}
        if meta["effect"] == "effectful" and not ratified:
            entry["evidence"] = "not run: the execution boundary is not ratified (an effectful probe runs commands)"
        else:
            reply = call_adapter(manifest, camp["manifest_dir"], "probe", [claim], workspace=workspace, campaign=camp["dir"])
            if reply.get("state") not in ladder:
                raise LoopError(f"probe {claim} returned state {reply.get('state')!r}; allowed: {', '.join(ladder)}")
            entry["state"], entry["evidence"] = reply["state"], reply.get("evidence")
        out[claim] = entry
    return out


def readiness_report(manifest: dict, manifest_dir: Path, workspace, campaign_dir, ratified: bool) -> dict:
    claims = claim_states(manifest, {"manifest_dir": manifest_dir, "dir": campaign_dir}, workspace, ratified)

    def reached(kind: str, state: str) -> bool:
        return any(claim.split(":")[0] == kind and entry["state"] == state for claim, entry in claims.items())

    blocked = []
    for kind, state in (("cases.runs", "runs"), ("grading.scores", "scores"), ("improver.bounded", "bounded")):
        if not reached(kind, state):
            blocked.append(f"no {kind} claim has reached {state!r}")
    allowed = []
    if not blocked:
        allowed.append("efficiency under a stated tolerance, labelled 'stated, not measured'")
        klass = manifest.get("evaluation_class", "scripted")
        if klass == "judge-only":
            allowed.append("model-judged quality, labelled with the recorded judge reliability (promotion is the owner's policy)")
        for claim, entry in claims.items():
            kind, _, name = claim.partition(":")
            if kind == "grading.sensitive" and entry["state"] == "sensitive":
                allowed.append(f"quality claims about {name}")
            if kind == "grading.calibrated" and entry["state"] == "calibrated":
                allowed.append(f"measured efficiency on profile {name}")
        if not any(item.startswith("quality claims") for item in allowed):
            allowed.append("no quality claim is allowed yet: sensitivity is unknown for every property")
    return {"claims": claims, "start_ok": not blocked, "blocked": blocked, "allowed_claims": allowed,
            "boundary_sha256": boundary_hash(manifest), "ratified": ratified,
            "note": "invocable proves plumbing only, never improvement quality"}


# --------------------------------------------------------------------------------------------------------------------- verbs

def require_owner(args) -> None:
    if not args.yes_owner_approved:
        raise LoopError("this is the owner's decision: ask the owner, then pass --yes-owner-approved")


def cmd_adapter_check(args) -> tuple:
    manifest, path = load_manifest(args.manifest)
    return EXIT_OK, {"ok": True, "manifest": str(path), "sha256": sha256_file(path), "boundary_sha256": boundary_hash(manifest),
                     "subject": manifest["subject"]["name"], "capability": manifest["execution"]["capability"]}


def cmd_init(args) -> tuple:
    manifest, path = load_manifest(args.manifest)
    campaign_dir = Path(args.campaign).resolve()
    if (campaign_dir / "campaign.json").exists():
        raise LoopError(f"{campaign_dir / 'campaign.json'} already exists: a campaign is never re-initialised in place")
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise LoopError(f"workspace {workspace} is not a directory")
    cases = [item for item in args.cases.split(",") if item]
    if not cases:
        raise LoopError("--cases needs at least one case id for the first scope")
    with locked(campaign_dir):
        created = now()
        state = {
            "schema": CAMPAIGN_SCHEMA, "id": sha256_text(sha256_file(path) + created)[:10], "subject": manifest["subject"]["name"],
            "created": created, "updated": created, "workspace": str(workspace),
            "manifest": {"path": str(path), "sha256": sha256_file(path), "boundary_sha256": boundary_hash(manifest)},
            "ratification": None, "budget": parse_budget(args.budget), "consumed": {},
            "quiet_window": args.quiet_window or manifest.get("quiet_window", 2), "scopes": [], "scope": "S0", "tip": None,
            "iterations": [], "steps": {}, "tasks": [], "unknowns": [], "approved_cases": [], "events": [], "stop": None}
        camp = Campaign.__new__(Campaign)
        camp.dir, camp.state, camp.manifest, camp.manifest_path, camp.facts_cache = campaign_dir, state, manifest, path, {}
        catalog = load_catalog(camp)
        missing = [item for item in cases if item not in catalog]
        if missing:
            raise LoopError("not in the adapter's catalog: " + ", ".join(missing))
        identity = camp.call("identity")
        state["tip"] = identity.get("build")
        state["scopes"].append(open_scope(camp, "S0", cases, "start", False, catalog))
        camp.event("init", scope="S0", cases=cases)
        camp.save()
    return EXIT_OK, {"ok": True, "campaign": str(campaign_dir), "id": state["id"], "scope": state["scopes"][0],
                     "identity": camp.identity, "tip": state["tip"]}


def cmd_ratify(args) -> tuple:
    require_owner(args)
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        camp = Campaign(campaign_dir)
        camp.state["ratification"] = {"boundary_sha256": boundary_hash(camp.manifest), "at": now(), "note": args.note or ""}
        camp.event("ratify", boundary_sha256=camp.state["ratification"]["boundary_sha256"])
        camp.save()
    return EXIT_OK, {"ok": True, "ratified": camp.state["ratification"]}


def cmd_readiness(args) -> tuple:
    manifest, path = load_manifest(args.manifest)
    ratified, workspace, campaign_dir = False, args.workspace, None
    if args.campaign:
        camp = Campaign(args.campaign)
        campaign_dir, workspace = camp.dir, workspace or camp.state["workspace"]
        ratification = camp.state.get("ratification")
        ratified = bool(ratification and ratification["boundary_sha256"] == boundary_hash(manifest))
    report = readiness_report(manifest, path.parent, workspace, campaign_dir, ratified)
    return (EXIT_OK if (report["start_ok"] or not args.require_start) else EXIT_NOT_READY), report


def cmd_status(args) -> tuple:
    camp = Campaign(args.campaign)
    state = camp.state
    out = {"subject": state["subject"], "scope": camp.scope(), "tip": state["tip"], "iterations": len(state["iterations"]),
           "quota": quota_status(state), "stop": state.get("stop"), "open_tasks": [t for t in state["tasks"] if t["status"] == "open"],
           "ratified": bool(state.get("ratification")), "identity": camp.identity}
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
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        camp = Campaign(campaign_dir)
        result = apply_action(camp, plan_next(camp))
        camp.save()
    return EXIT_OK, result


def cmd_task(args) -> tuple:
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        camp = Campaign(campaign_dir)
        tasks = camp.state["tasks"]
        if args.task_verb == "add":
            task = {"id": f"T{len(tasks) + 1}", "kind": args.kind, "text": args.text, "needs_owner": args.needs_owner,
                    "status": "open", "opened": now()}
            tasks.append(task)
            camp.event("task", id=task["id"], kind=task["kind"])
            result = {"ok": True, "task": task}
        else:
            task = next((item for item in tasks if item["id"] == args.id), None)
            if task is None:
                raise LoopError(f"no task {args.id}")
            if task["status"] != "open":
                raise LoopError(f"task {args.id} is already {task['status']}")
            if task.get("needs_owner") and not args.approve:
                raise LoopError(f"task {args.id} needs the owner's approval: ask, then pass --approve")
            try:
                recorded = json.loads(args.result) if args.result else None
            except ValueError as error:
                raise LoopError(f"--result is not JSON: {error}") from None
            task.update(status="done", result=recorded, closed=now())
            camp.event("task-done", id=task["id"])
            result = {"ok": True, "task": task}
        camp.save()
    return EXIT_OK, result


def cmd_unknown(args) -> tuple:
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        camp = Campaign(campaign_dir)
        unknowns = camp.state["unknowns"]
        if args.unknown_verb == "add":
            if not (args.text or "").strip():
                raise LoopError("--text names what is not known")
            unknowns.append({"text": args.text, "inside_claim": args.inside_claim, "opened": now(), "resolved": None})
            camp.event("unknown", index=len(unknowns) - 1, inside_claim=args.inside_claim)
        else:
            if args.index is None or not 0 <= args.index < len(unknowns):
                raise LoopError("--index names an existing unknown (see status)")
            unknowns[args.index]["resolved"] = now()
            camp.event("unknown-resolved", index=args.index)
        camp.save()
    return EXIT_OK, {"ok": True, "unknowns": unknowns}


def cmd_approve(args) -> tuple:
    require_owner(args)
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        camp = Campaign(campaign_dir)
        if args.case not in load_catalog(camp):
            raise LoopError(f"{args.case} is not in the adapter's catalog")
        approved = camp.state.setdefault("approved_cases", [])
        if args.case not in approved:
            approved.append(args.case)
        reopened = bool(camp.state.get("stop") and camp.state["stop"].get("owner_gated_cases"))
        if reopened:
            camp.state["stop"] = None
        camp.event("approve", case=args.case, note=args.note or "", reopened=reopened)
        camp.save()
    return EXIT_OK, {"ok": True, "approved": approved, "reopened": reopened}


def cmd_check(args) -> tuple:
    if args.clause not in CLAUSES:
        raise LoopError("--clause must be one of " + ", ".join(CLAUSES))
    sha = script_sha()
    if args.expect_sha and args.expect_sha != sha:
        return EXIT_IDENTITY, {"clause": args.clause, "pass": False, "reasons": [
            f"the check script changed since this contract was frozen (expected {args.expect_sha[:12]}, running {sha[:12]})"],
            "script_sha256": sha}
    camp = Campaign(args.campaign)
    result = CHECKS[args.clause](camp, Facts(camp))
    result.update(script_sha256=sha, campaign_identity=camp.identity, clause=args.clause)
    return (EXIT_OK if result["pass"] else EXIT_NOT_READY), result


def cmd_certificate(args) -> tuple:
    camp = Campaign(args.campaign)
    cert = certificate(camp, Facts(camp))
    return (EXIT_OK if cert["status"] == "converged" else EXIT_NOT_READY), cert


def cmd_coverage(args) -> tuple:
    camp = Campaign(args.campaign)
    facts = Facts(camp)
    allowed, gated = widening_candidates(camp, facts)
    scope = camp.scope()
    return EXIT_OK, {"scope": scope["id"], "cases": scope["cases"], "values": scope["values"], "not_covered": scope["not_covered"],
                     "widening_candidates": allowed, "owner_gated": gated}


def cmd_contract(args) -> tuple:
    contract = build_contract(Campaign(args.campaign), args.kind)
    if args.out:
        Path(args.out).write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    return EXIT_OK, contract


def cmd_report(args) -> tuple:
    campaign_dir = Path(args.campaign).resolve()
    with locked(campaign_dir):
        camp = Campaign(campaign_dir)
        out = write_report(camp)
        camp.save()
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
    add("adapter-check", cmd_adapter_check, ("--manifest", {"required": True}))
    add("init", cmd_init, ("--manifest", {"required": True}), campaign, ("--workspace", {"required": True}),
        ("--cases", {"required": True}), ("--budget", {"default": ""}), ("--quiet-window", {"type": int}))
    add("ratify", cmd_ratify, campaign, owner, ("--note", {}))
    add("readiness", cmd_readiness, ("--manifest", {"required": True}), ("--campaign", {}), ("--workspace", {}),
        ("--require-start", {"action": "store_true"}))
    add("status", cmd_status, campaign, ("--no-certificate", {"action": "store_true"}))
    add("next", cmd_next, campaign)
    add("step", cmd_step, campaign)
    task = add("task", cmd_task, campaign)
    task.add_argument("task_verb", choices=("add", "done"))
    for flag, options in (("--kind", {}), ("--text", {}), ("--needs-owner", {"action": "store_true"}), ("--id", {}),
                          ("--result", {}), ("--approve", {"action": "store_true"})):
        task.add_argument(flag, **options)
    unknown = add("unknown", cmd_unknown, campaign)
    unknown.add_argument("unknown_verb", choices=("add", "resolve"))
    unknown.add_argument("--text")
    unknown.add_argument("--inside-claim", action="store_true")
    unknown.add_argument("--index", type=int)
    add("approve", cmd_approve, campaign, ("--case", {"required": True}), owner, ("--note", {}))
    add("check", cmd_check, campaign, ("--clause", {"required": True}), ("--expect-sha", {}))
    add("certificate", cmd_certificate, campaign)
    add("coverage", cmd_coverage, campaign)
    add("contract", cmd_contract, campaign, ("--kind", {"required": True, "choices": ("scope", "readiness")}), ("--out", {}))
    add("report", cmd_report, campaign)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, out = args.handler(args)
    except LoopError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return EXIT_ERROR
    print(json.dumps(out, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
