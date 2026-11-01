#!/usr/bin/env python3
"""Backchain's command line: the deterministic half of a planning run.

The model plans and reviews; this script checks, packages, exports and keeps the books, so that no run has to
write its own bookkeeping code. It never launches a model and never runs a planned step. Standard library only,
Python 3.9+.

Plans:
  check PLAN                  structural check (the seven invariants) and completion; prints a receipt
  package PLAN --out FILE     the plan with recomputed parallel_groups, written atomically; prints a receipt
  export PLAN [--out FILE]    the Plan Dispatcher execution graph (execution-graph/v1) of a complete plan

A planning run (one directory; Until Loop owns the loop, this script owns the records):
  prepare --run DIR --request FILE [--draft FILE] [--caller FILE] [--passes default|one|converge]
                              freeze the inputs, resolve every resource, print what to read and write
  freeze --run DIR            check and package DIR/plan.json and write the Until Loop contract
  record --run DIR --review FILE --exit E --continuation C
                              after a cycle's last edit: record the cycle and write its Until Loop report
  verify --run DIR            the contract's evidence check (read-only)
  finish --run DIR [--review FILE]
                              after the loop ends: write DIR/result.json, {plan, convergence}; a run with a
                              caller packet passes its final review object and gets {plan, review}

Review aids:
  lenses ID...                print only the named technical lens cards (T01 to T42)

Exit codes: 0 ok; 1 the plan or run fails what the command requires; 3 the command could not run (unreadable
input, not JSON, wrong state, bad arguments). A could-not-run is never a finding about the plan.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import backchain_graph as graph  # noqa: E402
import check_preservation as preservation  # noqa: E402

SKILL_ROOT = SCRIPTS.parent
DEFAULT_UNTIL_LOOP = SKILL_ROOT.parent / "improve" / "runtime" / "until-loop" / "ADAPTER.md"
CHECK_SCHEMA = "backchain-check/v1"
RUN_SCHEMA = "backchain-run/v1"
EVIDENCE_SCHEMA = "backchain-evidence/v1"
EXIT_OK = 0
EXIT_FAILS = 1
EXIT_UNAVAILABLE = 3
EXPORT_VALIDATION = ("structurally valid and completionStatus=complete; done strings carry each produce's confirm "
                     "method when the plan declares one; readiness and semantic verification remain dispatcher-owned")

# The review gate (owner decision D1, 2026-11-01): by default the first trivial review completes; a material or
# unresolved review is always followed by a fresh one. A caller selects another gate with a marker line.
GATES = {"default": 1, "one": 0, "converge": 2}
EXIT_CONDITIONS = {
    "default": ("A complete dependency review/fix/check cycle found nothing to repair and changed nothing; no "
                "planning gap remains (future execution blockers may remain as unresolved entries); the structural "
                "check and the domain evidence check pass on the final candidate."),
    # references/convergence.md states this text for the `Backchain passes: one` marker, and ShipLoop's plan
    # packet prints it; test/backchain-toolkit.test.py keeps the three the same.
    "one": ("One complete dependency review/fix/check cycle has run; every finding of that cycle is repaired within "
            "the edit bounds; every `Confirm by` clause on a step this cycle may change meets the planning guide's "
            "Outcomes rule; the printed `backchain-check` is ok on the final candidate and its receipt is cited; "
            "final candidate-specific domain evidence is saved."),
    "converge": ("Two consecutive distinct complete trivial/no-change dependency reviews have run; no planning gap "
                 "remains; the structural check and the domain evidence check pass on the final candidate."),
}
REPEAT_CONDITION = ("Repeat while an authorized in-scope repair or a required distinct review remains. Stop "
                    "incomplete (blocked) when a planning gap no authorized repair can close remains: a missing or "
                    "stale normative source, a necessary repair outside the edit bounds, or a change that needs a "
                    "new binding. There is no pass ceiling.")
# The child's scope as references/convergence.md states it; any further access is what the request and the caller
# grant (adversarial review F8, 2026-11-01: a blanket network ban would block an authorized read of a source).
AUTHORITY = ("Plan only: no commit, push, merge or project execution, and no broadened scope; any other access is "
             "only what the request and the caller packet grant.")
BOUND_LISTS = ("provisional_step_ids", "provisional_edge_keys", "protected_step_ids", "protected_edge_keys",
               "protected_facts", "running_or_completed_step_ids")
CHANGE_CLASSES = ("material", "trivial", "none", "unknown")
EXIT_ASSESSMENTS = ("satisfied", "unsatisfied", "unknown")
CONTINUATIONS = ("allowed", "blocked", "cancelled")

# What a run reads, once each, in this order, by route. Paths are relative to the Backchain skill root. A fresh
# request is planned by direct synthesis, and elaborated only when its dependency review changes something (the
# lean route measured in the 2026-10-16 study); generator.v1.md stays for the checkout's one-shot pipeline.
DRAFTING = (("prompts/direct.v1.md", "synthesize the plan from the request; save it as {run}/draft.json"),
            ("prompts/dependency-review.prompt.md", "review the draft's dependencies; when an answer or inspection "
                                                    "changes a dependency, supplier, step claim or unresolved need, "
                                                    "read 3; otherwise copy {run}/draft.json to {run}/plan.json"),
            ("prompts/elaborator.v1.md", "only when 2 found a change: elaborate the draft with its dependency "
                                         "context; save the plan as {run}/plan.json"))
ELABORATING = (("prompts/dependency-review.prompt.md", "the dependency context of {run}/input/draft.json"),
               ("prompts/elaborator.v1.md", "elaborate {run}/input/draft.json; save the plan as {run}/plan.json"))
REVISING = (("prompts/audit.prompt.md", "audit {run}/input/draft.json against the caller packet"),
            ("prompts/revise.prompt.md", "one bounded revision; save the plan as {run}/plan.json"))
CALLER = (("references/caller-contract.md", "the caller packet {run}/input/caller.json"),)
REVIEWING = (("references/convergence.md", "the review rules each cycle applies"),
             ("prompts/convergence-review.prompt.md", "each cycle's assessment and its JSON"),
             ("references/technical-lenses.md", "the lens screen; print the applicable or uncertain cards with "
                                                "`lenses ID...` and read the relevant sections of "
                                                "references/technical-interactions.md"))


class Unavailable(Exception):
    """The command could not run (input unreadable, not JSON, wrong state for the command): never a finding."""


class Fails(Exception):
    """The plan or run fails what the command requires."""


# ---------------------------------------------------------------- files

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(Path(path).read_bytes())


def read_plan(path: Path) -> Tuple[bytes, Any]:
    """(raw bytes, parsed JSON) of a plan file; Unavailable when it cannot be read or is not JSON."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise Unavailable(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        return data, graph.loads(data)
    except graph.CheckUnavailable as exc:
        raise Unavailable(f"{path}: {exc}") from exc


def read_json(path: Path) -> Any:
    return read_plan(path)[1]


_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def json_text(value: Any) -> str:
    """Two-space JSON with a final newline, writable as UTF-8.

    A plan may hold a lone surrogate (JSON allows the escape, JS strings allow the code unit); like
    JS's well-formed JSON.stringify, it is written back as its ``\\uXXXX`` escape.
    """
    text = json.dumps(value, indent=2, ensure_ascii=False)
    return _LONE_SURROGATE.sub(lambda match: "\\u%04x" % ord(match.group()), text) + "\n"


def write_atomically(path: Path, text: str) -> None:
    """Replace ``path`` in one rename, keeping its mode (a new file is 0644, not mkstemp's private 0600)."""
    path = Path(path)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_once(path: Path, text: str) -> None:
    """Write a record that must never be overwritten."""
    if path.exists():
        raise Unavailable(f"{path} already exists; recorded files are never overwritten")
    write_atomically(path, text)


def locator(path: Path) -> Dict[str, str]:
    return {"path": str(path), "sha256": file_sha256(path)}


# ---------------------------------------------------------------- plans

def packaged_digest(plan: Any) -> str:
    """The identity of a plan's content: the digest of its packaged, canonical (JSON.stringify) form."""
    return sha256(graph.js_stringify(graph.package(plan)).encode("utf-8"))


def check_receipt(data: bytes, plan: Any, where: str) -> Dict[str, Any]:
    """The structural verdict on the packaged plan: what a reader needs to trust or repair it."""
    packaged = graph.package(plan)
    structure = graph.validate_structure(packaged)
    completion = graph.completion_status(packaged, structure)
    return {
        "schema": CHECK_SCHEMA,
        "plan": where,
        "plan_sha256": sha256(data),
        "packaged_sha256": sha256(graph.js_stringify(packaged).encode("utf-8")),
        "ok": structure["ok"],
        "failures": structure["failures"],
        "completion": completion["status"],
        "open_goal_needs": completion["open_goal_needs"],
        "unresolved_count": completion["unresolved_count"],
        "parallel_groups": graph.compute_parallel_groups(packaged),
        "counts": graph.counts(packaged),
        "unconfirmed_produces": graph.unconfirmed_produces(packaged),
    }


def summary(receipt: Dict[str, Any]) -> str:
    counts = receipt["counts"]
    if receipt["ok"]:
        verdict = f"valid, {receipt['completion']}"
    else:
        invariants = sorted({failure["invariant"] for failure in receipt["failures"]})
        verdict = f"invalid on invariant(s) {', '.join(map(str, invariants))}"
    return (f"backchain check: {verdict}; {counts['steps']} steps, {len(receipt['parallel_groups'])} parallel "
            f"group(s), {len(receipt['unconfirmed_produces'])} unconfirmed produce(s)")


def inherited_edges_removed(inherited: Any, candidate: Any) -> List[str]:
    """Input edges of an inherited plan that the candidate no longer has: (step, need, from) triples, compared after
    whitespace normalization. A run may remove an edge it generated; an inherited edge stays."""
    def edges(plan: Any) -> Dict[Tuple[str, str, Any], str]:
        found = {}
        for step in plan.get("steps", []) if isinstance(plan, dict) else []:
            if not isinstance(step, dict) or not isinstance(step.get("inputs"), list):
                continue
            for entry in step["inputs"]:
                if isinstance(entry, dict) and isinstance(entry.get("need"), str):
                    key = (str(step.get("id")), graph.normalize_need_string(entry["need"]), entry.get("from"))
                    found[key] = f"{step.get('id')} <- {entry.get('from') or 'initial_state'}: {entry['need']}"
        return found

    kept = edges(candidate)
    return [text for key, text in edges(inherited).items() if key not in kept]


def edge_key(step_id: Any, source: Any) -> str:
    """A caller edge key, consumer<-supplier; a null-origin edge's supplier is written null."""
    return f"{step_id}<-{'null' if source is None else source}"


def edges_by_key(plan: Any) -> Dict[str, List[str]]:
    """Each consumer<-supplier edge's input objects, canonical and sorted, so any change to an edge shows."""
    found: Dict[str, List[str]] = {}
    for step in plan.get("steps", []) if isinstance(plan, dict) else []:
        if not isinstance(step, dict) or not isinstance(step.get("inputs"), list):
            continue
        for entry in step["inputs"]:
            if isinstance(entry, dict):
                found.setdefault(edge_key(step.get("id"), entry.get("from")), []).append(
                    json.dumps(entry, sort_keys=True))
    return {key: sorted(values) for key, values in found.items()}


def bound_errors(inherited: Any, candidate: Any, bounds: Dict[str, Any]) -> List[str]:
    """Edits outside a caller's edit_bounds (references/caller-contract.md, repair/revise): running, completed and
    protected steps are unchanged; another existing step changes only if provisional; a new step needs
    allow_new_steps; an existing edge changes only if its key is provisional on a provisional consumer, and gains
    inputs only with allow_new_edges; a new edge needs allow_new_edges on a provisional or new consumer; protected
    edges and facts stay."""
    def steps(plan: Any) -> Dict[str, Any]:
        return {s["id"]: s for s in plan.get("steps", []) if isinstance(s, dict) and isinstance(s.get("id"), str)}

    def without_inputs(step: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in step.items() if key != "inputs"}

    old, new = steps(inherited), steps(candidate)
    frozen = set(bounds.get("protected_step_ids") or []) | set(bounds.get("running_or_completed_step_ids") or [])
    provisional = set(bounds.get("provisional_step_ids") or []) - frozen
    errors = []
    for identifier, step in old.items():
        if identifier not in new:
            if identifier not in provisional:
                errors.append(f"step {identifier} removed outside the edit bounds")
        elif identifier in frozen and new[identifier] != step:
            errors.append(f"protected step {identifier} changed")
        elif identifier not in provisional and without_inputs(new[identifier]) != without_inputs(step):
            errors.append(f"step {identifier} changed outside the edit bounds (not provisional)")
    added_steps = [identifier for identifier in new if identifier not in old]
    if added_steps and not bounds.get("allow_new_steps"):
        errors += [f"new step {identifier} without allow_new_steps" for identifier in added_steps]
    protected_edges = set(bounds.get("protected_edge_keys") or [])
    provisional_edges = set(bounds.get("provisional_edge_keys") or []) - protected_edges
    old_edges, new_edges = edges_by_key(inherited), edges_by_key(candidate)
    for key in sorted(set(old_edges) | set(new_edges)):
        before, after = old_edges.get(key, []), new_edges.get(key, [])
        if before == after:
            continue
        consumer = key.split("<-", 1)[0]
        if not before:
            if not bounds.get("allow_new_edges") or (consumer in old and consumer not in provisional):
                errors.append(f"new edge {key} outside the edit bounds")
            continue
        if key in protected_edges or key not in provisional_edges or consumer not in provisional:
            errors.append(f"edge {key} changed outside the edit bounds")
        # Round 2 (F4): rewording or dropping an input of a provisional edge changes that edge, but an edge that ends
        # with more inputs than it had gained new dependencies, which only allow_new_edges grants.
        if len(after) > len(before) and not bounds.get("allow_new_edges"):
            errors.append(f"edge {key} gains an input without allow_new_edges")
    # A protected fact is an accepted fact: the plan must keep one it states in initial_state, but need not state one
    # it never did (pilot, 2026-11-01: requiring "S1 is already complete ..." in initial_state refused a correct repair).
    def facts(plan: Any) -> set:
        return {graph.normalize_need_string(fact) for fact in plan.get("initial_state", [])
                if isinstance(fact, str)} if isinstance(plan, dict) else set()

    stated, kept = facts(inherited), facts(candidate)
    for fact in bounds.get("protected_facts") or []:
        normalized = graph.normalize_need_string(fact) if isinstance(fact, str) else None
        if normalized in stated and normalized not in kept:
            errors.append(f"protected fact removed from initial_state: {fact}")
    return errors


def inherited_ids_removed(inherited: Any, candidate: Any) -> List[str]:
    def ids(plan: Any) -> List[str]:
        steps = plan.get("steps", []) if isinstance(plan, dict) else []
        return [step["id"] for step in steps if isinstance(step, dict) and isinstance(step.get("id"), str)]

    kept = set(ids(candidate))
    return [identifier for identifier in ids(inherited) if identifier not in kept]


# ---------------------------------------------------------------- export (Plan Dispatcher execution-graph/v1)

def done_string(produce: str, confirmation: Optional[Dict[str, Any]]) -> str:
    """A done string carries its confirmation method inline, so an executor reading only contract.done learns it."""
    if not confirmation:
        return produce
    if confirmation["level"] == "unconfirmable":
        return f"{produce}. Confirm by: unconfirmable here — {confirmation['by']}"
    if confirmation["level"] == "inspect":
        return f"{produce}. Confirm by: {confirmation['by']} (inspection is sufficient)"
    return f"{produce}. Confirm by: {confirmation['by']}"


def unique(values: List[Any]) -> List[Any]:
    return list(dict.fromkeys(values))


def export_graph(plan: Any, plan_sha256: str) -> Dict[str, Any]:
    """Plan Dispatcher's execution graph for a structurally valid, complete plan (packaged first).

    Ported from the Backchain checkout's scripts/export-execution-graph.js. That exporter refuses an
    unpackaged plan on invariant 6; this one packages first, so stored parallel_groups never block an export.
    Plan Dispatcher's own ``validate-graph`` remains the executor's acceptance check.
    """
    packaged = graph.package(plan)
    structure = graph.validate_structure(packaged)
    if not structure["ok"]:
        raise Fails("Backchain plan is structurally invalid: " + json.dumps(structure["failures"]))
    completion = graph.completion_status(packaged, structure)
    if completion["status"] != "complete":
        raise Fails("Backchain plan is incomplete: " + json.dumps(
            {"unresolved_count": completion["unresolved_count"], "open_goal_needs": completion["open_goal_needs"]}))
    if not packaged["steps"]:
        raise Fails("Backchain plan has no work to dispatch")
    steps = []
    for step in packaged["steps"]:
        confirmations = {entry["produces"]: entry for entry in step.get("confirm", [])}
        steps.append({
            "id": step["id"],
            "deps": unique([entry["from"] for entry in step["inputs"] if entry["from"] is not None]),
            # Backchain permits repeated condition wording, including one need from different suppliers; the compact
            # condition lists must not collapse the dependencies or the input bindings kept in source.inputs.
            "contract": {
                "task": step["statement"],
                "ready": unique([entry["need"] for entry in step["inputs"]]),
                "done": unique([done_string(produce, confirmations.get(produce)) for produce in step["produces"]]),
            },
        })
    return {
        "version": 1,
        "source": {
            "format": "backchain",
            "plan_sha256": plan_sha256,
            "goal": packaged["goal"],
            "initial_state": packaged["initial_state"],
            "goal_needs": packaged.get("goal_needs", []),
            "inputs": {step["id"]: step["inputs"] for step in packaged["steps"]},
            "validation": EXPORT_VALIDATION,
        },
        "steps": steps,
    }


# ---------------------------------------------------------------- a planning run

class Run:
    """The files of one planning run. Inputs, contract and recorded cycles are written once; plan.json is the
    model's working candidate; evidence.json is the rolling record of every cycle."""

    def __init__(self, directory: Path):
        self.dir = Path(directory).absolute()
        self.input = self.dir / "input"
        self.loop = self.dir / "loop"
        self.cycles = self.dir / "cycles"
        self.meta_path = self.dir / "run.json"
        self.plan = self.dir / "plan.json"
        self.draft = self.dir / "draft.json"
        self.inherited = self.input / "draft.json"
        self.caller = self.input / "caller.json"
        self.request = self.input / "request.md"
        self.contract = self.loop / "contract.json"
        self.baseline = self.loop / "baseline.json"
        self.receipt = self.loop / "receipt.json"
        self.evidence = self.dir / "evidence.json"
        self.result = self.dir / "result.json"

    def meta(self) -> Dict[str, Any]:
        if not self.meta_path.is_file():
            raise Unavailable(f"{self.dir} is not a Backchain run; start one with `prepare`")
        meta = read_json(self.meta_path)
        if not isinstance(meta, dict) or meta.get("schema") != RUN_SCHEMA:
            raise Unavailable(f"{self.meta_path} is not a {RUN_SCHEMA} record; start a new run with `prepare`")
        return meta

    def frozen(self) -> Dict[str, Any]:
        meta = self.meta()
        if "frozen" not in meta or not self.contract.is_file():
            raise Unavailable(f"run {self.dir} is not frozen; write {self.plan} and run `freeze` first")
        return meta

    def recorded(self) -> List[Dict[str, Any]]:
        if not self.evidence.is_file():
            return []
        return read_json(self.evidence)["cycles"]

    def command(self, *args: str) -> str:
        return shlex.join([sys.executable, "-I", "-B", str(Path(__file__).resolve()), *args, "--run", str(self.dir)])


def resolve(relative: str) -> Path:
    path = SKILL_ROOT / relative
    if not path.is_file():
        raise Unavailable(f"MISSING: Backchain resource {path}; reinstall the skill-craft plugin")
    return path


def mode_for(meta: Dict[str, Any]) -> str:
    """Preservation mode against the inherited input: report-only only within a caller's explicit edit bounds."""
    return "source-aware" if meta.get("edit_bounds") else "legacy"


def caller_bounds(run: Run) -> Dict[str, Any]:
    """The caller packet's edit_bounds (prepare checked their shape); empty without them."""
    if not run.caller.is_file():
        return {}
    bounds = read_json(run.caller).get("edit_bounds")
    return bounds if isinstance(bounds, dict) else {}


def inherited_obligations(run: Run, meta: Dict[str, Any], plan: Any) -> Optional[Dict[str, Any]]:
    """What the candidate owes an inherited input plan; None without one. Errors fail; differences need a review
    finding. Legacy elaboration keeps every inherited step ID, input edge and unchanged confirmation; a caller's
    edit_bounds decide instead which inherited steps, edges and facts may change (adversarial review F3,
    2026-11-01: the bounds were bound into the contract but no command enforced them)."""
    if not run.inherited.is_file():
        return None
    inherited = read_json(run.inherited)
    mode = mode_for(meta)
    compared = preservation.compare(inherited, plan, mode)
    errors = list(compared["errors"])
    differences = list(compared["confirmation_differences"])
    removed, missing_ids = inherited_edges_removed(inherited, plan), inherited_ids_removed(inherited, plan)
    if mode == "legacy":
        errors += [f"input edge removed: {edge}" for edge in removed]
        errors += [f"step removed: {identifier}" for identifier in missing_ids]
    else:
        errors += [f"edit bounds: {error}" for error in bound_errors(inherited, plan, caller_bounds(run))]
        differences += [{"kind": "inherited_edge_absent", "edge": edge} for edge in removed]
        differences += [{"kind": "inherited_step_absent", "step_id": identifier} for identifier in missing_ids]
    return {"mode": mode, "errors": [f"inherited draft: {error}" for error in errors], "differences": differences}


def compare_obligations(run: Run, meta: Dict[str, Any], plan: Any) -> Dict[str, Any]:
    """Obligations the candidate must keep. Against the loop baseline: goal_needs exactly, and every confirmation
    difference reported for the review. Against an inherited input: what inherited_obligations says."""
    baseline = read_json(run.baseline)
    generated = preservation.compare(baseline, plan, "source-aware")
    errors = list(generated["errors"])
    differences = list(generated["confirmation_differences"])
    inherited = inherited_obligations(run, meta, plan)
    if inherited is not None:
        errors += inherited["errors"]
        differences += inherited["differences"]
    return {"errors": errors, "differences": differences, "goal_needs_preserved": generated["goal_needs_preserved"],
            "inherited_mode": inherited["mode"] if inherited is not None else None}


def contract_for(run: Run, meta: Dict[str, Any], exit_checks: List[Dict[str, str]]) -> Dict[str, Any]:
    passes = meta["passes"]
    markers = f"Backchain standalone Until Loop binding: {meta['binding_id']}\n"
    if passes != "default":
        markers += f"Backchain passes: {passes}\n"
    record = run.command("record") + " --review <assessment file> --exit <satisfied|unsatisfied|unknown> " \
                                     "--continuation <allowed|blocked|cancelled>"
    if meta.get("edit_bounds"):
        bounds = f"the caller's edit_bounds in {run.caller}"
    elif run.inherited.is_file():
        bounds = (f"every step may change, but the inherited steps of {run.inherited} keep their IDs, input edges "
                  "and confirmations")
    else:
        bounds = "every step may change; this run generated all of them"
    # Round 2 (F5): with a caller's bounds, what they make provisional may go too.
    removable = ("and an inherited one only where the caller's edit bounds make it provisional"
                 if meta.get("edit_bounds") else "never an inherited one")
    work = (f"One complete Backchain dependency review/fix/check cycle of the candidate {run.plan}. Read "
            f"{resolve('prompts/convergence-review.prompt.md')} and perform its assessment against the frozen request "
            f"{run.request}, its sources and the edit bounds: trace backward from every requested outcome and "
            "verification sink, walk the graph forward, screen every lens category and read the cards it marks "
            "applicable or uncertain, check sources and bounds, and review implementable chunks. Repair every "
            f"finding the edit bounds allow by editing {run.plan}; a review may remove an edge or step this run "
            f"generated when it finds it unjustified, {removable}. Save the assessment (the review "
            "prompt's JSON; its candidate_identity is the sha256 of the candidate the cycle began with, which freeze "
            "printed for cycle 1 and each record prints, and last_report.handoff repeats, for the next) to a new "
            f"file, run `{record}`, then the packet's verify_script, then submit the report file that record prints "
            "through done_argv on stdin.")
    inputs = [("original request", run.request), ("inherited draft", run.inherited), ("caller packet", run.caller)]
    resources = [{"purpose": purpose, "locator": str(path)} for purpose, path in inputs if path.is_file()]
    resources += [{"purpose": entry["purpose"], "locator": entry["locator"]} for entry in meta["resources"]]
    resources += [{"purpose": purpose, "locator": str(path)} for purpose, path in (
        ("candidate plan", run.plan), ("loop baseline", run.baseline), ("latest packet (receipt)", run.receipt),
        ("domain evidence", run.evidence), ("result destination", run.result))]
    return {
        "workspace": str(run.dir),
        "work": work,
        "exit_condition": EXIT_CONDITIONS[passes],
        "repeat_condition": REPEAT_CONDITION,
        "required_trivial_reviews": GATES[passes],
        "context": {
            "request": markers + f"Plan-only Backchain dependency review of {run.plan} for the request in "
                                 f"{run.request} (sha256 {meta['inputs']['request']['sha256']}).",
            "scope": (f"Plan only: {run.plan} and new files under {run.dir}. Read-only: {run.input}, {run.loop} and "
                      f"{run.cycles}. Edit bounds: {bounds}."),
            "authority": AUTHORITY,
            "environment": (f"Python {sys.executable}; Backchain's command line {Path(__file__).resolve()}. Each cycle "
                            f"edits {run.plan}, records itself with `record`, runs the packet's verify_script, and "
                            "submits the report record wrote."),
            "resources": resources,
        },
        "exit_checks": exit_checks,
    }


def command_prepare(args: argparse.Namespace) -> int:
    run = Run(args.run)
    if run.dir.exists() and any(run.dir.iterdir()):
        raise Unavailable(f"{run.dir} is not empty; a run directory holds one planning run")
    card = Path(args.until_loop).absolute() if args.until_loop else DEFAULT_UNTIL_LOOP
    runtime = card.parent / "scripts" / "until_loop_ephemeral.py"
    for path, what in ((card, "Until Loop card"), (runtime, "Until Loop runtime")):
        if not path.is_file():
            raise Unavailable(f"MISSING: {what} {path}; name the selected card with --until-loop")
    try:
        request = Path(args.request).read_bytes()
    except OSError as exc:
        raise Unavailable(f"cannot read the request {args.request}: {exc.strerror or exc}") from exc
    draft = read_json(args.draft) if args.draft else None
    caller = read_json(args.caller) if args.caller else None
    for value, name in ((draft, "--draft"), (caller, "--caller")):
        if value is not None and not isinstance(value, dict):
            raise Unavailable(f"{name} is not a JSON object")
    bounds = caller.get("edit_bounds") if caller is not None else None
    if bounds is not None:
        shaped = isinstance(bounds, dict) and all(
            isinstance(bounds.get(key, []), list) and all(isinstance(item, str) for item in bounds.get(key, []))
            for key in BOUND_LISTS) and all(isinstance(bounds.get(key, False), bool)
                                            for key in ("allow_new_steps", "allow_new_edges"))
        if not shaped:
            raise Unavailable("--caller edit_bounds is an object whose " + ", ".join(BOUND_LISTS) + " are lists of "
                              "strings and whose allow_new_steps and allow_new_edges are true or false")
    route ="source-aware" if caller is not None else ("draft" if draft is not None else "fresh")
    reads = list(CALLER if route == "source-aware" else ())
    reads += list(DRAFTING if draft is None else (REVISING if route == "source-aware" else ELABORATING))
    resources = [("Backchain card", "SKILL.md")]
    resources += [(f"Backchain {relative}", relative) for relative, _ in reads + list(REVIEWING)]
    run.dir.mkdir(parents=True, exist_ok=True)
    run.input.mkdir()
    run.loop.mkdir()
    run.cycles.mkdir()
    run.request.write_bytes(request)
    inputs = {"request": locator(run.request)}
    if draft is not None:
        shutil.copyfile(args.draft, run.inherited)
        inputs["draft"] = locator(run.inherited)
    if caller is not None:
        shutil.copyfile(args.caller, run.caller)
        inputs["caller"] = locator(run.caller)
    seen = set()
    resolved = []
    for purpose, relative in resources:
        if relative in seen:
            continue
        seen.add(relative)
        path = resolve(relative)
        resolved.append({"purpose": purpose, "locator": str(path), "sha256": file_sha256(path)})
    resolved += [{"purpose": "Backchain command line", "locator": str(Path(__file__).resolve()),
                  "sha256": file_sha256(Path(__file__).resolve())},
                 {"purpose": "Until Loop card", "locator": str(card), "sha256": file_sha256(card)},
                 {"purpose": "Until Loop runtime", "locator": str(runtime), "sha256": file_sha256(runtime)}]
    meta = {
        "schema": RUN_SCHEMA,
        "binding_id": args.binding or f"backchain-{sha256(request)[:8]}-{secrets.token_hex(3)}",
        "created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "route": route,
        "passes": args.passes,
        "inputs": inputs,
        "edit_bounds": bool(caller and caller.get("edit_bounds") is not None),
        "resources": resolved,
        "until_loop": {"card": str(card), "runtime": str(runtime)},
    }
    write_atomically(run.meta_path, json_text(meta))
    print(f"Backchain run {run.dir} ({route}, passes {args.passes}); binding {meta['binding_id']}")
    print("Read each once, in this order:")
    for number, (relative, text) in enumerate(reads, start=1):
        print(f"  {number}. {SKILL_ROOT / relative}: {text.format(run=run.dir)}")
    target = run.draft if draft is None else run.plan
    print(f"Write {target}" + (f", then {run.plan}" if draft is None else "") + f"; then run: {run.command('freeze')}")
    return EXIT_OK


def command_freeze(args: argparse.Namespace) -> int:
    run = Run(args.run)
    meta = run.meta()
    if run.contract.exists():
        raise Unavailable(f"run {run.dir} is already frozen; a changed candidate or binding needs a new run")
    data, plan = read_plan(run.plan)
    extra = [read_json(path) for path in args.exit_check or ()]
    for check in extra:
        if not isinstance(check, dict) or set(check) != {"id", "clause", "command"}:
            raise Unavailable("an --exit-check file holds one {id, clause, command} object")
    problems = []
    # The draft's obligations survive enrichment: goal_needs exactly, and an unchanged produce keeps its confirmation.
    if run.draft.is_file():
        problems += [f"generated draft: {error}"
                     for error in preservation.compare(read_json(run.draft), plan, "legacy")["errors"]]
    inherited = inherited_obligations(run, meta, plan)
    problems += inherited["errors"] if inherited is not None else []
    packaged = graph.package(plan)
    receipt = check_receipt(data, plan, str(run.plan))
    if not receipt["ok"]:
        problems += [f"invariant {f['invariant']}: {f['message']}" for f in receipt["failures"]]
    if problems:
        print(json_text({"frozen": False, "problems": problems}), end="")
        print(f"backchain freeze: {len(problems)} problem(s); repair {run.plan} and run freeze again",
              file=sys.stderr)
        return EXIT_FAILS
    write_atomically(run.plan, json_text(packaged))
    write_once(run.baseline, json_text(packaged))
    python = shlex.quote(sys.executable)
    cli = shlex.quote(str(Path(__file__).resolve()))
    exit_checks = [
        {"id": "backchain-check", "clause": "The final candidate passes Backchain's structural check.",
         "command": f"{python} -I -B {cli} check {shlex.quote(str(run.plan))}"},
        {"id": "backchain-evidence", "clause": "Final candidate-specific domain evidence is saved.",
         "command": f"{python} -I -B {cli} verify --run {shlex.quote(str(run.dir))}"},
    ] + extra
    contract = contract_for(run, meta, exit_checks)
    write_once(run.contract, json_text(contract))
    meta["frozen"] = {"baseline": locator(run.baseline), "packaged_sha256": packaged_digest(packaged),
                      "contract": locator(run.contract)}
    write_atomically(run.meta_path, json_text(meta))
    runtime = meta["until_loop"]["runtime"]
    print(f"Contract: {run.contract}")
    print(f"Receipt: {run.receipt}")
    print(f"Read {meta['until_loop']['card']} once, then start the loop by its \"Start from a parent-written "
          f"contract\" route:\n  python3 {shlex.quote(runtime)} start --receipt {shlex.quote(str(run.receipt))} "
          f"< {shlex.quote(str(run.contract))}")
    print("Read once for the cycles:")
    for number, (relative, text) in enumerate(REVIEWING, start=1):
        print(f"  {number}. {SKILL_ROOT / relative}: {text}")
    print("Each cycle: review and repair " + str(run.plan) + "; save the assessment JSON; run "
          + run.command("record") + " --review FILE --exit E --continuation C; run the packet's verify_script; "
          "submit the report record wrote through done_argv on stdin. After the loop ends: " + run.command("finish")
          + (" --review FILE (the final review object, references/caller-contract.md)" if run.caller.is_file() else ""))
    print(f"Cycle 1's candidate_identity: {meta['frozen']['baseline']['sha256']}")
    return EXIT_OK


def classify(change_class: str, changed: bool) -> str:
    """The loop classification: a measured fact first. A cycle whose plan changed is non-trivial, whatever the
    assessment says; an unknown assessment is unresolved."""
    if change_class == "unknown":
        return "unresolved"
    return "non-trivial" if changed or change_class == "material" else "trivial"


def reviewed_identity(run: Run, meta: Dict[str, Any], cycles: List[Dict[str, Any]]) -> str:
    """The sha256 of the candidate a new cycle reviews: the last recorded cycle's plan, or the frozen baseline."""
    return cycles[-1]["plan"]["sha256"] if cycles else meta["frozen"]["baseline"]["sha256"]


def review_problems(review: Any, identity: str) -> List[str]:
    """Why an assessment cannot be recorded. It names the candidate it reviewed and what it inspected (adversarial
    review F4, 2026-11-01: a stale or empty assessment was recorded as a qualifying review)."""
    if not isinstance(review, dict):
        return ["the assessment is a JSON object"]
    problems = []
    if review.get("change_class") not in CHANGE_CLASSES:
        problems.append("change_class is one of " + ", ".join(CHANGE_CLASSES))
    if review.get("candidate_identity") != identity:
        problems.append(f"candidate_identity is the sha256 of the candidate this cycle reviewed, {identity} (freeze "
                        "or the previous record printed it)")
    if not isinstance(review.get("findings"), list):
        problems.append("findings is a list")
    # Round 2 (F3): a list of nulls is not a record of inspection. What the checks claim stays the reviewer's word;
    # the blind grading of the plans measures it.
    checks = review.get("checks")
    if not isinstance(checks, list) or not checks or not all(isinstance(c, str) and c.strip() for c in checks):
        problems.append("checks lists what this cycle inspected: at least one non-blank string")
    for key in ("planning_gaps", "execution_blockers"):
        if not isinstance(review.get(key), list) or not all(isinstance(item, str) for item in review.get(key, [])):
            problems.append(f"{key} is a list of strings")
    if "next_action" in review and not isinstance(review["next_action"], str):
        problems.append("next_action is a string")
    return problems


def command_record(args: argparse.Namespace) -> int:
    run = Run(args.run)
    meta = run.frozen()
    review = read_json(args.review)
    cycles = run.recorded()
    # A cycle is one callback of this run's loop: the receipt holds the loop's latest packet, which names the callback.
    if not run.receipt.is_file():
        raise Unavailable(f"no loop packet at {run.receipt}; start the loop with the command freeze printed, then "
                          "record each cycle inside its callback")
    packet = read_json(run.receipt)
    if isinstance(packet, dict) and packet.get("status") != "active":
        raise Unavailable(f"the loop at {run.receipt} has ended ({packet.get('status')}); a cycle is recorded inside "
                          "a callback, so run finish")
    problems = binding_problems(run, meta) + packet_problems(run, packet)
    callback = callback_of(packet)
    if callback is None:
        problems.append("the receipt names no callback number")
    elif callback > 1:
        earlier = [entry for entry in cycles if entry.get("callback") == callback - 1]
        if not earlier or packet.get("last_report") != read_json(Path(earlier[-1]["report"]["path"])):
            problems.append(f"the loop accepted a report in callback {callback - 1} that is not the last report "
                            "record wrote in it; each callback submits the report record wrote, so this run cannot "
                            "converge: finish it, or start a new run")
    problems += review_problems(review, reviewed_identity(run, meta, cycles))
    data, plan = read_plan(run.plan)
    receipt = check_receipt(data, plan, str(run.plan))
    if not receipt["ok"]:
        problems += [f"the candidate fails invariant {f['invariant']}: {f['message']}" for f in receipt["failures"]]
    obligations = compare_obligations(run, meta, plan)
    problems += obligations["errors"]
    previous = cycles[-1]["plan"]["packaged_sha256"] if cycles else meta["frozen"]["packaged_sha256"]
    current = packaged_digest(plan)
    classification = classify(review.get("change_class", "unknown") if isinstance(review, dict) else "unknown",
                              current != previous)
    if classification == "unresolved" and args.exit == "satisfied":
        problems.append("an unresolved cycle cannot report the exit satisfied")
    if problems:
        print(json_text({"recorded": False, "problems": problems}), end="")
        print(f"backchain record: {len(problems)} problem(s); fix them and run record again", file=sys.stderr)
        return EXIT_FAILS
    number = len(cycles) + 1
    directory = run.cycles / f"{number:02d}"
    directory.mkdir()
    write_atomically(run.plan, json_text(graph.package(plan)))
    files = {"review": json_text(review), "plan": run.plan.read_text(encoding="utf-8"),
             "check": json_text(check_receipt(run.plan.read_bytes(), plan, str(run.plan))),
             "comparison": json_text(obligations)}
    for name, text in files.items():
        write_once(directory / f"{name}.json", text)
    gaps, blockers = review["planning_gaps"], review["execution_blockers"]
    entry = {
        "cycle": number, "callback": callback, "classification": classification, "changed": current != previous,
        "change_class": review["change_class"], "findings": len(review["findings"]),
        "review": locator(directory / "review.json"),
        "plan": dict(locator(directory / "plan.json"), packaged_sha256=current),
        "check": dict(locator(directory / "check.json"), ok=receipt["ok"], completion=receipt["completion"]),
        "comparison": dict(locator(directory / "comparison.json"), differences=len(obligations["differences"])),
    }
    evidence_text = (f"Cycle {number} of {meta['binding_id']}: assessment {entry['review']['path']} (sha256 "
                     f"{entry['review']['sha256']}, change_class {review['change_class']}, {len(review['findings'])} "
                     f"finding(s)); candidate {run.plan} packaged sha256 {current}, "
                     f"{'changed' if entry['changed'] else 'unchanged'} this cycle; structure "
                     f"{'ok' if receipt['ok'] else 'invalid'}, completion {receipt['completion']}; obligations kept "
                     f"({len(obligations['differences'])} difference(s) for the review); planning gaps "
                     f"{len(gaps)}, execution blockers {len(blockers)}.")
    handoff = (f"Backchain run {run.dir}, binding {meta['binding_id']}. Candidate {run.plan}, sha256 "
               f"{entry['plan']['sha256']} (the next cycle's candidate_identity); cycles 1-{number} recorded in "
               f"{run.evidence}, each with its assessment, plan, check and comparison under {run.cycles}. Planning "
               f"gaps: {gaps or 'none'}. Execution blockers: {blockers or 'none'}."
               + (f" Next: {review['next_action']}" if review.get("next_action") else ""))
    report = {"classification": classification, "exit_assessment": args.exit,
              "continuation_assessment": args.continuation, "evidence": evidence_text, "handoff": handoff}
    write_once(directory / "report.json", json_text(report))
    entry["report"] = locator(directory / "report.json")
    evidence = {"schema": EVIDENCE_SCHEMA, "binding_id": meta["binding_id"],
                "candidate": {"input_sha256": meta["frozen"]["baseline"]["sha256"],
                              "output_sha256": file_sha256(run.plan)},
                "cycles": cycles + [entry], "planning_gaps": gaps, "execution_blockers": blockers,
                "next_action": review.get("next_action", "")}
    write_atomically(run.evidence, json_text(evidence))
    note = ""
    if entry["changed"] and review["change_class"] in ("trivial", "none"):
        note = " (the plan changed this cycle, so it is non-trivial whatever the assessment says)"
    print(f"Report: {directory / 'report.json'}")
    print(f"cycle {number} recorded: {classification}{note}; next run the packet's verify_script, then submit the "
          "report through done_argv on stdin")
    print(f"Next cycle's candidate_identity: {entry['plan']['sha256']}")
    return EXIT_OK


def binding_problems(run: Run, meta: Dict[str, Any]) -> List[str]:
    """What changed under the run's binding: its frozen inputs, baseline and contract, and every resource prepare
    resolved (Backchain's card, prompts and command line, the Until Loop card and runtime). Adversarial review F2,
    2026-11-01: these digests were recorded but never checked again."""
    frozen = meta.get("frozen", {})
    records = [(f"input {name}", entry) for name, entry in meta["inputs"].items()]
    records += [(f"frozen {name}", frozen[name]) for name in ("baseline", "contract") if name in frozen]
    records += [(f"resource {entry['purpose']}", entry) for entry in meta["resources"]]
    problems = []
    for label, entry in records:
        path = Path(entry.get("path") or entry["locator"])
        if not path.is_file() or file_sha256(path) != entry["sha256"]:
            problems.append(f"the {label} {path} is missing or changed; a changed binding needs a new run")
    return problems


def verification(run: Run) -> List[str]:
    """Why the run's evidence does not hold for the current candidate; empty when it does."""
    meta = run.frozen()
    problems = binding_problems(run, meta)
    cycles = run.recorded()
    if not cycles:
        return problems + ["no cycle is recorded; run record after the cycle's last edit"]
    for entry in cycles:
        for name in ("review", "plan", "check", "comparison", "report"):
            path = Path(entry[name]["path"])
            if not path.is_file() or file_sha256(path) != entry[name]["sha256"]:
                problems.append(f"cycle {entry['cycle']} {name} record {path} is missing or changed")
    _, plan = read_plan(run.plan)
    if file_sha256(run.plan) != cycles[-1]["plan"]["sha256"]:
        problems.append(f"{run.plan} changed after cycle {cycles[-1]['cycle']} was recorded; run record again")
    problems += compare_obligations(run, meta, plan)["errors"]
    return problems


def command_verify(args: argparse.Namespace) -> int:
    problems = verification(Run(args.run))
    print(json_text({"verified": not problems, "problems": problems}), end="")
    return EXIT_OK if not problems else EXIT_FAILS


def packet_problems(run: Run, packet: Any) -> List[str]:
    """Why a packet at the run's receipt is not this run's loop: it repeats the frozen contract's workspace, work,
    conditions, context, exit checks and gate, and names this receipt."""
    if not isinstance(packet, dict):
        return [f"the receipt {run.receipt} is not an Until Loop packet"]
    contract = read_json(run.contract)
    expected = {"workspace": contract["workspace"], "receipt": str(run.receipt), "work": contract["work"],
                "conditions": {"exit": contract["exit_condition"], "repeat": contract["repeat_condition"]},
                "context": contract["context"], "exit_checks": contract["exit_checks"]}
    problems = [f"the receipt's {key} is not this run's" for key, value in expected.items() if packet.get(key) != value]
    progress = packet.get("progress") if isinstance(packet.get("progress"), dict) else {}
    if progress.get("required_trivial_reviews") != contract["required_trivial_reviews"]:
        problems.append("the receipt's review gate is not this run's")
    return problems


def callback_of(packet: Any) -> Optional[int]:
    """The packet's callback number (Until Loop's progress.action_number, from 1), or None."""
    progress = packet.get("progress") if isinstance(packet, dict) and isinstance(packet.get("progress"), dict) else {}
    number = progress.get("action_number")
    return number if isinstance(number, int) and not isinstance(number, bool) and number >= 1 else None


def receipt_problems(run: Run, packet: Any, cycles: List[Dict[str, Any]]) -> List[str]:
    """Why the terminal packet at the run's receipt is not this run's own. Adversarial reviews of 2026-11-01: in
    round 1 (F1) any file saying complete made a run converge; in round 2 (F2) a count of actions against records let
    a hand-written callback hide behind an extra record. So: packet_problems, then every callback has a recorded
    cycle (record stamps each with its callback and, when a callback begins, checks that the one before submitted
    the last report record wrote then), the last callback submitted the last recorded report, and a complete packet
    shows every frozen exit check passing."""
    problems = packet_problems(run, packet)
    if not isinstance(packet, dict):
        return problems
    callbacks = callback_of(packet)
    stamped = {entry.get("callback") for entry in cycles}
    if callbacks is None:
        problems.append("the receipt names no callback number")
    else:
        unrecorded = [str(number) for number in range(1, callbacks + 1) if number not in stamped]
        if unrecorded:
            problems.append(f"the receipt's callback(s) {', '.join(unrecorded)} have no recorded cycle; each callback "
                            "submits the report record wrote")
    if cycles and packet.get("last_report") != read_json(Path(cycles[-1]["report"]["path"])):
        problems.append("the receipt's last_report is not the last recorded cycle's report")
    contract = read_json(run.contract)
    status = packet.get("status")
    if status == "complete":
        results = packet.get("last_check_results")
        passed = {result.get("id") for result in results if isinstance(result, dict) and result.get("passed") is True
                  } if isinstance(results, list) else set()
        failing = [check["id"] for check in contract["exit_checks"] if check["id"] not in passed]
        if failing:
            problems.append(f"the complete receipt does not show these exit checks passing: {', '.join(failing)}")
    elif status != "stopped":
        problems.append(f"the receipt's status {status!r} is not a terminal Until Loop status")
    return problems


def caller_review(review: Dict[str, Any], caller: Dict[str, Any], run: Run, meta: Dict[str, Any],
                  convergence: Dict[str, Any], receipt: Dict[str, Any]) -> Dict[str, Any]:
    """The review of a source-aware run's final {plan, review} (references/caller-contract.md): the final source
    assessment with the caller's action identity and original input identity restored, the observed output digest,
    the structural status of the check receipt, and the opaque convergence record."""
    out = dict(review)
    for key in ("interface", "action", "stage", "action_id", "owner", "workflow_stage"):
        if key in caller:
            out[key] = caller[key]
    supplied = caller.get("candidate") if isinstance(caller.get("candidate"), dict) else {}
    candidate = dict(review["candidate"]) if isinstance(review.get("candidate"), dict) else {}
    candidate.update({key: value for key, value in supplied.items() if key != "output_sha256"})
    candidate["input_sha256"] = supplied.get(
        "input_sha256", meta["inputs"]["draft"]["sha256"] if "draft" in meta["inputs"] else "unavailable")
    candidate["output_sha256"] = file_sha256(run.plan)
    coverage = dict(review["coverage"]) if isinstance(review.get("coverage"), dict) else {}
    coverage["structural_plan_status"] = "valid" if receipt["ok"] else "invalid"
    out.update(candidate=candidate, coverage=coverage, convergence=convergence)
    return out


def command_finish(args: argparse.Namespace) -> int:
    run = Run(args.run)
    meta = run.frozen()
    if not run.receipt.is_file():
        raise Unavailable(f"no receipt at {run.receipt}; start the loop with the command freeze printed")
    packet = read_json(run.receipt)
    status = packet.get("status") if isinstance(packet, dict) else None
    if status == "active":
        raise Unavailable(f"the loop is still active; continue it with the receipt's next_argv ({run.receipt})")
    # A run with a caller packet returns {plan, review} (adversarial review F5, 2026-11-01): the final review object
    # is the model's, written after the loop as references/caller-contract.md shapes it.
    caller = read_json(run.caller) if run.caller.is_file() else None
    review = None
    if caller is not None:
        if args.review is None:
            raise Unavailable("this run has a caller packet, so it returns {plan, review}: write the final review "
                              "object (references/caller-contract.md) and pass it with --review FILE")
        review = read_json(args.review)
        if not isinstance(review, dict):
            raise Unavailable(f"--review {args.review} is not a JSON object")
        mismatched = [f"{key} {review.get(key)!r} (the caller packet's is {caller.get(key)!r})"
                      for key in ("interface", "action", "stage", "action_id") if review.get(key) != caller.get(key)]
        if mismatched:
            raise Unavailable("--review is not this caller action's review: " + "; ".join(mismatched))
        if not all(isinstance(gap, str) for gap in review.get("planning_gaps") or []):
            raise Unavailable("--review planning_gaps is a list of strings")
        # Round 2 (F1): the review must be of the final candidate, not an earlier one or an empty shell.
        final = file_sha256(run.plan)
        assessed = review.get("candidate") if isinstance(review.get("candidate"), dict) else {}
        coverage = review.get("coverage") if isinstance(review.get("coverage"), dict) else {}
        unbound = [problem for problem, holds in (
            (f"candidate.output_sha256 is the final candidate's sha256, {final} (the last record printed it)",
             assessed.get("output_sha256") == final),
            ("findings is a list", isinstance(review.get("findings"), list)),
            ("coverage.source_review_status is complete or incomplete",
             coverage.get("source_review_status") in ("complete", "incomplete"))) if not holds]
        if unbound:
            raise Unavailable("--review does not assess the final candidate: " + "; ".join(unbound))
    cycles = run.recorded()
    problems = verification(run) + receipt_problems(run, packet, cycles)
    data, plan = read_plan(run.plan)
    receipt = check_receipt(data, plan, str(run.plan))
    evidence = read_json(run.evidence) if run.evidence.is_file() else {}
    gaps = unique(evidence.get("planning_gaps", []) + (review.get("planning_gaps") or [] if review else []))
    converged = status == "complete" and not problems and not gaps and receipt["ok"]
    # The run's own records come first: a model's next action never hides a receipt or binding that does not hold.
    next_action = "" if converged else ("; ".join(problems) or evidence.get("next_action") or (
        f"the loop ended {status}" + (f" with planning gaps: {gaps}" if gaps else "")))
    convergence = {
        "binding_id": meta["binding_id"],
        "owner": "selected Until Loop binding",
        "candidate": {"input_sha256": meta["frozen"]["baseline"]["sha256"], "output_sha256": file_sha256(run.plan)},
        "resources": [{"purpose": e["purpose"], "resolved_locator": e["locator"]} for e in meta["resources"]],
        "terminal_receipt": {"resolved_locator": str(run.receipt), "status": status, "opaque": True},
        "domain_evidence": [str(run.evidence)] + [str(Path(c["review"]["path"]).parent) for c in cycles],
        "planning_gaps": gaps,
        "execution_blockers": evidence.get("execution_blockers", []),
        "next_action": next_action,
    }
    result = {"plan": graph.package(plan)}
    if review is None:
        result["convergence"] = convergence
    else:
        result["review"] = caller_review(review, caller, run, meta, convergence, receipt)
    result["structure"] = {"ok": receipt["ok"], "completion": receipt["completion"],
                           "parallel_groups": receipt["parallel_groups"]}
    result["status"] = "converged" if converged else "incomplete"
    write_atomically(run.result, json_text(result))
    print(f"Result: {run.result}")
    if converged:
        hint = (f"; hand it to Plan Dispatcher with: {shlex.join([sys.executable, '-I', '-B', str(Path(__file__).resolve()), 'export', str(run.plan)])}"
                if receipt["completion"] == "complete" else "")
        print(f"backchain finish: converged ({len(evidence.get('cycles', []))} cycle(s)){hint}")
        return EXIT_OK
    print(f"backchain finish: incomplete; next: {next_action}")
    return EXIT_FAILS


# ---------------------------------------------------------------- lenses

_LENS_CARD = re.compile(r"^## (T\d{2}) — ", re.M)


def lens_cards() -> Dict[str, str]:
    """Each card of references/technical-lens-cards.md by its ID, heading included."""
    text = resolve("references/technical-lens-cards.md").read_text(encoding="utf-8")
    starts = [(match.group(1), match.start()) for match in _LENS_CARD.finditer(text)]
    return {identifier: text[start:(starts[index + 1][1] if index + 1 < len(starts) else len(text))].rstrip() + "\n"
            for index, (identifier, start) in enumerate(starts)}


def lens_id(text: str) -> str:
    """T07, t07, T7 and 7 all name card T07."""
    digits = text.upper().removeprefix("T")
    return f"T{int(digits):02d}" if digits.isdigit() else text


def command_lenses(args: argparse.Namespace) -> int:
    cards = lens_cards()
    wanted = unique([lens_id(text) for text in args.ids])
    unknown = [identifier for identifier in wanted if identifier not in cards]
    if unknown:
        raise Unavailable(f"no lens card {', '.join(unknown)}; the cards are {min(cards)} to {max(cards)}")
    sys.stdout.write("\n".join(cards[identifier] for identifier in wanted))
    return EXIT_OK


# ---------------------------------------------------------------- plan commands

def command_check(args: argparse.Namespace) -> int:
    data, plan = read_plan(args.plan)
    receipt = check_receipt(data, plan, str(Path(args.plan).absolute()))
    sys.stdout.write(json_text(receipt))
    print(summary(receipt), file=sys.stderr)
    return EXIT_OK if receipt["ok"] else EXIT_FAILS


def command_package(args: argparse.Namespace) -> int:
    data, plan = read_plan(args.plan)
    out = Path(args.out).absolute()
    write_atomically(out, json_text(graph.package(plan)))
    receipt = check_receipt(data, plan, str(Path(args.plan).absolute()))
    receipt["output"] = str(out)
    receipt["output_sha256"] = file_sha256(out)
    sys.stdout.write(json_text(receipt))
    print(summary(receipt) + f"; packaged to {out}", file=sys.stderr)
    return EXIT_OK if receipt["ok"] else EXIT_FAILS


def command_export(args: argparse.Namespace) -> int:
    data, plan = read_plan(args.plan)
    try:
        exported = export_graph(plan, sha256(data))
    except Fails as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return EXIT_FAILS
    text = json_text(exported)
    if args.out:
        out = Path(args.out).absolute()
        write_atomically(out, text)
        print(f"backchain export: {len(exported['steps'])} step(s) to {out}; check it with Plan Dispatcher's "
              f"`validate-graph` before binding a run", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return EXIT_OK


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="backchain.py", description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = top.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="structural check and completion of a plan")
    check.add_argument("plan", type=Path)
    check.set_defaults(run_command=command_check)
    package = commands.add_parser("package", help="write the plan with recomputed parallel_groups")
    package.add_argument("plan", type=Path)
    package.add_argument("--out", type=Path, required=True)
    package.set_defaults(run_command=command_package)
    export = commands.add_parser("export", help="Plan Dispatcher execution graph of a complete plan")
    export.add_argument("plan", type=Path)
    export.add_argument("--out", type=Path)
    export.set_defaults(run_command=command_export)
    prepare = commands.add_parser("prepare", help="start a planning run")
    prepare.add_argument("--run", type=Path, required=True)
    prepare.add_argument("--request", type=Path, required=True)
    prepare.add_argument("--draft", type=Path, help="an inherited plan to elaborate or revise")
    prepare.add_argument("--caller", type=Path, help="a backchain-caller/v1 packet")
    prepare.add_argument("--passes", choices=tuple(GATES), default="default")
    prepare.add_argument("--until-loop", type=Path, help="the selected Until Loop card (default: the bundled one)")
    prepare.add_argument("--binding", help="the binding id (default: generated)")
    prepare.set_defaults(run_command=command_prepare)
    freeze = commands.add_parser("freeze", help="check the candidate and write the Until Loop contract")
    freeze.add_argument("--run", type=Path, required=True)
    freeze.add_argument("--exit-check", type=Path, action="append",
                        help="a caller's extra exit check: a JSON file with one {id, clause, command}")
    freeze.set_defaults(run_command=command_freeze)
    record = commands.add_parser("record", help="record a cycle and write its Until Loop report")
    record.add_argument("--run", type=Path, required=True)
    record.add_argument("--review", type=Path, required=True)
    record.add_argument("--exit", choices=EXIT_ASSESSMENTS, required=True)
    record.add_argument("--continuation", choices=CONTINUATIONS, required=True)
    record.set_defaults(run_command=command_record)
    verify = commands.add_parser("verify", help="the contract's evidence check")
    verify.add_argument("--run", type=Path, required=True)
    verify.set_defaults(run_command=command_verify)
    finish = commands.add_parser("finish", help="write the run's result after the loop ends")
    finish.add_argument("--run", type=Path, required=True)
    finish.add_argument("--review", type=Path,
                        help="a run with a caller packet: the final review object (references/caller-contract.md)")
    finish.set_defaults(run_command=command_finish)
    lenses = commands.add_parser("lenses", help="print the named technical lens cards (T01 to T42)")
    lenses.add_argument("ids", nargs="+")
    lenses.set_defaults(run_command=command_lenses)
    return top


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_UNAVAILABLE
    try:
        return args.run_command(args)
    except Unavailable as exc:
        print(f"backchain {args.command} could not run: {exc}; this is not a finding about the plan", file=sys.stderr)
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
