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
  finish --run DIR            after the loop ends: write DIR/result.json, {plan, convergence}

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
AUTHORITY = ("Plan only: no commit, push, merge, project execution, installation, network access or contact with "
             "people or services, and no broadened scope.")
CHANGE_CLASSES = ("material", "trivial", "none", "unknown")
EXIT_ASSESSMENTS = ("satisfied", "unsatisfied", "unknown")
CONTINUATIONS = ("allowed", "blocked", "cancelled")

# What a run reads, once each, in this order, by route. Paths are relative to the Backchain skill root.
DRAFTING = (("prompts/generator.v1.md", "draft the plan from the request; save the JSON draft as {run}/draft.json"),
            ("prompts/dependency-review.prompt.md", "the dependency context of the draft"),
            ("prompts/elaborator.v1.md", "enrich the draft; save the plan as {run}/plan.json"))
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


def compare_obligations(run: Run, meta: Dict[str, Any], plan: Any) -> Dict[str, Any]:
    """Obligations the candidate must keep. Against the loop baseline: goal_needs exactly, and every confirmation
    difference reported for the review. Against an inherited input: also its step IDs, input edges and (legacy)
    unchanged confirmations. Errors fail; differences need a review finding."""
    baseline = read_json(run.baseline)
    generated = preservation.compare(baseline, plan, "source-aware")
    errors = list(generated["errors"])
    differences = list(generated["confirmation_differences"])
    inherited_result = None
    if run.inherited.is_file():
        inherited = read_json(run.inherited)
        mode = mode_for(meta)
        inherited_result = preservation.compare(inherited, plan, mode)
        errors += [e for e in inherited_result["errors"] if e not in errors]
        differences += inherited_result["confirmation_differences"]
        removed = inherited_edges_removed(inherited, plan)
        missing_ids = inherited_ids_removed(inherited, plan)
        if mode == "legacy":
            errors += [f"inherited input edge removed: {edge}" for edge in removed]
            errors += [f"inherited step removed: {identifier}" for identifier in missing_ids]
        else:
            differences += [{"kind": "inherited_edge_absent", "edge": edge} for edge in removed]
            differences += [{"kind": "inherited_step_absent", "step_id": identifier} for identifier in missing_ids]
    return {"errors": errors, "differences": differences, "goal_needs_preserved": generated["goal_needs_preserved"],
            "inherited_mode": mode_for(meta) if inherited_result is not None else None}


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
    work = (f"One complete Backchain dependency review/fix/check cycle of the candidate {run.plan}. Read "
            f"{resolve('prompts/convergence-review.prompt.md')} and perform its assessment against the frozen request "
            f"{run.request}, its sources and the edit bounds: trace backward from every requested outcome and "
            "verification sink, walk the graph forward, screen every lens category and read the cards it marks "
            "applicable or uncertain, check sources and bounds, and review implementable chunks. Repair every "
            f"finding the edit bounds allow by editing {run.plan}; a review may remove an edge or step this run "
            "generated when it finds it unjustified, never an inherited one. Save the assessment (the review "
            f"prompt's JSON) to a new file, run `{record}`, then the packet's verify_script, then submit the report "
            "file that record prints through done_argv on stdin.")
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
    route = "source-aware" if caller is not None else ("draft" if draft is not None else "fresh")
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
    for baseline, label in ((run.draft, "generated draft"), (run.inherited, "inherited draft")):
        if baseline.is_file():
            before = read_json(baseline)
            mode = "legacy" if label == "generated draft" else mode_for(meta)
            problems += [f"{label}: {error}" for error in preservation.compare(before, plan, mode)["errors"]]
            if label == "inherited draft" and mode == "legacy":
                problems += [f"inherited draft: input edge removed: {e}" for e in inherited_edges_removed(before, plan)]
                problems += [f"inherited draft: step removed: {i}" for i in inherited_ids_removed(before, plan)]
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
          "submit the report record wrote through done_argv on stdin. After the loop ends: " + run.command("finish"))
    return EXIT_OK


def classify(change_class: str, changed: bool) -> str:
    """The loop classification: a measured fact first. A cycle whose plan changed is non-trivial, whatever the
    assessment says; an unknown assessment is unresolved."""
    if change_class == "unknown":
        return "unresolved"
    return "non-trivial" if changed or change_class == "material" else "trivial"


def review_problems(review: Any) -> List[str]:
    if not isinstance(review, dict):
        return ["the assessment is a JSON object"]
    problems = []
    if review.get("change_class") not in CHANGE_CLASSES:
        problems.append("change_class is one of " + ", ".join(CHANGE_CLASSES))
    for key in ("findings", "checks"):
        if not isinstance(review.get(key), list):
            problems.append(f"{key} is a list")
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
    problems = review_problems(review)
    data, plan = read_plan(run.plan)
    receipt = check_receipt(data, plan, str(run.plan))
    if not receipt["ok"]:
        problems += [f"the candidate fails invariant {f['invariant']}: {f['message']}" for f in receipt["failures"]]
    obligations = compare_obligations(run, meta, plan)
    problems += obligations["errors"]
    cycles = run.recorded()
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
        "cycle": number, "classification": classification, "changed": current != previous,
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
    handoff = (f"Backchain run {run.dir}, binding {meta['binding_id']}. Candidate {run.plan} (packaged sha256 "
               f"{current}); cycles 1-{number} recorded in {run.evidence}, each with its assessment, plan, check and "
               f"comparison under {run.cycles}. Planning gaps: {gaps or 'none'}. Execution blockers: "
               f"{blockers or 'none'}." + (f" Next: {review['next_action']}" if review.get("next_action") else ""))
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
    return EXIT_OK


def verification(run: Run) -> List[str]:
    """Why the run's evidence does not hold for the current candidate; empty when it does."""
    meta = run.frozen()
    cycles = run.recorded()
    if not cycles:
        return ["no cycle is recorded; run record after the cycle's last edit"]
    problems = []
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


def command_finish(args: argparse.Namespace) -> int:
    run = Run(args.run)
    meta = run.frozen()
    if not run.receipt.is_file():
        raise Unavailable(f"no receipt at {run.receipt}; start the loop with the command freeze printed")
    packet = read_json(run.receipt)
    status = packet.get("status") if isinstance(packet, dict) else None
    if status == "active":
        raise Unavailable(f"the loop is still active; continue it with the receipt's next_argv ({run.receipt})")
    problems = verification(run)
    data, plan = read_plan(run.plan)
    receipt = check_receipt(data, plan, str(run.plan))
    evidence = read_json(run.evidence) if run.evidence.is_file() else {}
    gaps = evidence.get("planning_gaps", [])
    converged = status == "complete" and not problems and not gaps and receipt["ok"]
    next_action = evidence.get("next_action") or ""
    if not converged and not next_action:
        next_action = ("; ".join(problems) if problems else
                       f"the loop ended {status}" + (f" with planning gaps: {gaps}" if gaps else ""))
    result = {
        "plan": graph.package(plan),
        "convergence": {
            "binding_id": meta["binding_id"],
            "owner": "selected Until Loop binding",
            "candidate": {"input_sha256": meta["frozen"]["baseline"]["sha256"], "output_sha256": file_sha256(run.plan)},
            "resources": [{"purpose": e["purpose"], "resolved_locator": e["locator"]} for e in meta["resources"]],
            "terminal_receipt": {"resolved_locator": str(run.receipt), "status": status, "opaque": True},
            "domain_evidence": [str(run.evidence)] + [str(Path(c["review"]["path"]).parent) for c in evidence.get(
                "cycles", [])],
            "planning_gaps": gaps,
            "execution_blockers": evidence.get("execution_blockers", []),
            "next_action": "" if converged else next_action,
        },
        "structure": {"ok": receipt["ok"], "completion": receipt["completion"],
                      "parallel_groups": receipt["parallel_groups"]},
        "status": "converged" if converged else "incomplete",
    }
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
