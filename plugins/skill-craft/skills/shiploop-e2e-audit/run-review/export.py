#!/usr/bin/env python3
"""Export one ShipLoop E2E run as Run Review documents (see SCHEMA.md).

  export.py RUN_DIR [--key KEY] [--name NAME] [--order N] [--out DIR]
  export.py --defaults [--out DIR]

RUN_DIR is an output directory of test/shiploop_e2e/run.py. The export reads only
the run's own records (metrics.json, result.json, invocation.json and the ShipLoop
run directory) and writes only under --out (default RUN_DIR/review-export):

  docs/<collection>/<id>.json  one file per document
  writes.json                  the documents as ArtifactData `set` operations
  facts.md                     plain numbers for the reviewer
  review-export.json           every document in one compact file, to commit

A missing metrics.json, timeline.json or results/ is an error naming the file
(exit 2), never an empty export. The same input gives byte-identical output.
Stdlib only; no network and no model calls.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
DEFAULTS = HERE / "defaults"
SCHEMA_ID = "run-review-export/v1"
MAX_COMPACT_BYTES = 200_000
MAX_KNOWLEDGE = 40
MAX_FAILURE_LINE = 240

# Stage -> phase. The phase orders match defaults/expectations.json (phase-<order>); the stage names
# are shiploop_stage_spec.STAGES, and a test checks that every stage there is listed here once.
# carry-forward ("record lessons and revise the remaining queue") runs once per work item before
# the next select-work, so it belongs to Integrate, not System test.
PHASES = (
    ("Understand", ("intake", "discovery", "research")),
    ("Specify", ("spec", "test-strategy")),
    ("Plan", ("plan", "prepare", "select-work", "step-plan")),
    ("Build", ("test-spec", "baseline", "test-author", "test-red", "implement", "test-green", "test-refine")),
    ("Prove", ("regression", "document", "skill-assess", "skill-validate", "static-checks", "verify")),
    ("Integrate", ("integrate", "integration-verify", "carry-forward")),
    ("System test", ("system-test-author", "system-test", "product-acceptance")),
    ("Release", ("release-plan", "release-check", "release", "release-verify", "operations", "handoff")),
)
STAGE_PHASE = {stage: order for order, (_, stages) in enumerate(PHASES) for stage in stages}
# ShipLoop run status -> the page's run status.
RUN_STATUS = {"active": "active", "paused": "active", "blocked": "blocked", "halted": "failed", "done": "done"}
COLLECTION_ORDER = ("runs", "backchain", "expectations", "config", "observations", "actions", "iterations")

# ---------------------------------------------------------------- the contract, as data (SCHEMA.md)
# A field spec is (type, required). Types: "string", "number", "boolean", "iso", "any-scalar",
# ("enum", values), ("list", item), ("items", {field: spec}) for a list of objects,
# ("map", value type) for an object of values. A `?` field of an item is not required.
S, N, B, ISO = "string", "number", "boolean", "iso"
PHASE_STATES = ("done", "running", "blocked", "none")
SCHEMA = {
    "expectations": {
        "kind": (("enum", ("phase", "group", "criterion", "iter")), True),
        "order": (N, False), "title": (S, False), "short": (S, False), "text": (S, False),
        "group": (S, False), "status": (("enum", ("holds", "bent", "broken", "unjudged")), False),
        "revs": (("items", {"at": (ISO, True), "from": (S, True), "to": (S, True), "reason": (S, True),
                            "obs": (S, False), "iter": (S, False)}), False),
        "updatedAt": (ISO, False),
    },
    "runs": {
        "key": (S, True), "name": (S, True), "order": (N, True), "release": (S, True),
        "phases": (("list", ("enum", PHASE_STATES)), True),
        "time": (S, True), "imp": (S, True), "refusals": (N, True), "glue": (N, True),
        "wallMin": (N, False), "host": (S, False), "model": (S, False), "effort": (S, False), "case": (S, False),
        "status": (("enum", ("done", "active", "blocked", "failed")), False),
        "startedAt": (ISO, False), "endedAt": (ISO, False),
        "verdicts": (("map", B), False),
        "stages": (("items", {"stage": (S, True), "outcome": (S, True), "min": (N, True), "turns": (N, False),
                              "packetBytes": (N, False), "resultBytes": (N, False)}), False),
        "knowledge": (("map", N), False),
        "improve": (("items", {"stage": (S, True), "passes": (N, True), "seconds": (N, True), "bytes": (N, True)}),
                    False),
        "failures": (("items", {"verb": (S, True), "line": (S, True)}), False),
        "evidence": (S, False),
    },
    "backchain": {
        "run": (S, False), "loop": (S, False), "phase": (N, False), "order": (N, False), "title": (S, False),
        "stageMin": (N, False),
        "segments": (("items", {"label": (S, True), "min": (N, True),
                                "kind": (("enum", ("added", "wasted", "insurance", "unclear", "neutral")), True),
                                "note": (S, True), "pass": (N, False), "change": (S, False),
                                "streak": (N, False)}), False),
        "facts": (("items", {"k": (S, True), "v": (S, True)}), False),
    },
    "observations": {
        "phase": (N, False), "criterion": (S, False),
        "kind": (("enum", ("defect", "recovered", "decision", "noise", "added", "wasted")), False),
        "run": (S, False), "status": (("enum", ("open", "fixed", "accepted", "reexpected")), False),
        "title": (S, False), "expected": (S, False), "observed": (S, False), "evidence": (S, False),
        "createdAt": (ISO, False),
    },
    "actions": {"title": (S, False), "why": (S, False), "goal": (S, False), "criterion": (S, False),
                "base": (N, False), "status": (S, False)},
    "iterations": {
        "n": (N, False), "title": (S, False),
        "kind": (("enum", ("retrospective", "build", "pilot", "screen", "e2e", "decision")), False),
        "status": (("enum", ("planned", "running", "done")), False), "run": (S, False),
        "cost": ("any-scalar", False), "setBeforeData": (B, False), "expect": (S, False), "observed": (S, False),
        "verdict": (("enum", ("pending", "confirmed", "partly", "refuted")), False),
        "touches": (("list", S), False), "ifConfirmed": (S, False), "ifRefuted": (S, False), "next": (S, False),
        "engineChange": (S, False), "observedAt": (ISO, False),
    },
    # config/page and config/prompt share the collection; every field is a string.
    "config": {"title": (S, False), "artifactUrl": (S, False), "synthPreamble": (S, False),
               "concatPreamble": (S, False), "constraints": (S, False), "closing": (S, False)},
}


class ExportError(Exception):
    """A run directory the exporter cannot read faithfully; the message names what is missing."""


def _type_problem(spec, value, where: str) -> list[str]:
    if spec == S:
        return [] if isinstance(value, str) else [f"{where}: expected a string"]
    if spec == N:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return [] if ok else [f"{where}: expected a number"]
    if spec == B:
        return [] if isinstance(value, bool) else [f"{where}: expected a boolean"]
    if spec == ISO:
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return []
            except ValueError:
                pass
        return [f"{where}: expected an ISO date-time string"]
    if spec == "any-scalar":
        return [] if isinstance(value, (str, int, float)) and not isinstance(value, bool) else [
            f"{where}: expected a string or number"]
    kind, arg = spec
    if kind == "enum":
        return [] if value in arg else [f"{where}: {value!r} is not one of {', '.join(arg)}"]
    if kind == "list":
        if not isinstance(value, list):
            return [f"{where}: expected an array"]
        return [p for i, item in enumerate(value) for p in _type_problem(arg, item, f"{where}[{i}]")]
    if kind == "map":
        if not isinstance(value, dict):
            return [f"{where}: expected an object"]
        return [p for k, v in value.items() for p in _type_problem(arg, v, f"{where}.{k}")]
    if kind == "items":
        if not isinstance(value, list):
            return [f"{where}: expected an array"]
        problems = []
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                problems.append(f"{where}[{i}]: expected an object")
                continue
            problems += _fields_problems(arg, item, f"{where}[{i}]")
        return problems
    raise ValueError(f"unknown field spec {spec!r}")


def _fields_problems(fields: dict, doc: dict, where: str) -> list[str]:
    problems = []
    for name, (spec, required) in fields.items():
        if name not in doc:
            if required:
                problems.append(f"{where}: missing required field {name!r}")
            continue
        if doc[name] is None and not required:
            continue  # null is the same as absent for an optional field
        problems += _type_problem(spec, doc[name], f"{where}.{name}")
    return problems


def validate_doc(collection: str, doc) -> list[str]:
    """SCHEMA.md's required fields and types for one document ([] when it conforms)."""
    if collection not in SCHEMA:
        return [f"unknown collection {collection!r}"]
    if not isinstance(doc, dict):
        return [f"{collection}: a document must be an object"]
    return _fields_problems(SCHEMA[collection], doc, collection)


def extra_fields(collection: str, doc: dict) -> list[str]:
    """Top-level fields the contract does not name (allowed; the page ignores them)."""
    return sorted(set(doc) - set(SCHEMA.get(collection, {})))


# ---------------------------------------------------------------- reading the run

STATE_FENCE = re.compile(r"```shiploop-state\n(?P<json>.*?)\n```", re.S)
NAV_ID = re.compile(r"nav-[0-9a-f]{8,32}")


def _read_json(path: Path):
    if not path.is_file():
        raise ExportError(f"missing {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ExportError(f"cannot read {path}: {exc}") from exc


def _optional_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, UnicodeError, ValueError):
        return None


def _record(path: Path) -> dict | None:
    """The JSON in a ShipLoop Markdown record's ```shiploop-state fence (None when absent or unreadable)."""
    try:
        match = STATE_FENCE.search(path.read_text(encoding="utf-8"))
        value = json.loads(match.group("json")) if match else None
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _when(text) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def _minutes(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60


def find_run_dir(out: Path, named: str | None = None) -> Path:
    """The ShipLoop run directory (state.md beside timeline.json) inside a run output directory.

    Re-implements the harness's discovery (test/shiploop_e2e/run.py grade_shiploop; this module
    may not import from test/): an external workspace root `<out>/.shiploop-runs/*/run`, or a run
    kept inside the repository under `<out>/work/.shiploop*`. The run result.json names is chosen
    when it is among them, so the export describes the run the harness graded; otherwise the
    newest state.md.
    """
    patterns = (".shiploop-runs/*/run", "work/.shiploop*", "work/.shiploop*/run", "work/.shiploop*/*/run",
                "work/.shiploop*/*/*/run")
    candidates: list[Path] = []
    for pattern in patterns:
        for path in sorted(out.glob(pattern)):
            if path.is_dir() and (path / "state.md").is_file() and path not in candidates:
                candidates.append(path)
    if not candidates:
        raise ExportError(f"no ShipLoop run directory (a state.md) under {out}/.shiploop-runs/*/run "
                          f"or {out}/work/.shiploop*")
    if named:
        for path in candidates:
            if path.resolve() == Path(named).resolve():
                return path
    return max(candidates, key=lambda p: ((p / "state.md").stat().st_mtime, str(p)))


def current_stage(state: dict) -> str | None:
    """The run's effective stage, including a work item's inner-loop stage (None when done)."""
    stage = state.get("stage")
    if stage == "inner-loop":
        try:
            item = state["work_items"][state["work_index"]]["id"]
            return state["inner_loops"][item]["stage"]
        except (KeyError, IndexError, TypeError):
            return None
    return None if stage == "done" else stage


def derive_phases(stage_phases: list[int], current: int | None, status: str | None) -> list[str]:
    """One state per phase: running/blocked for the current phase, done for any other phase the run
    reached (its reached stages are all accepted once the run has moved on), none otherwise."""
    reached = set(stage_phases)
    states = []
    for order in range(len(PHASES)):
        if status == "done":
            states.append("done" if order in reached else "none")
        elif order == current:
            states.append("blocked" if status in ("blocked", "halted") else "running")
        else:
            states.append("done" if order in reached else "none")
    return states


def _fmt_minutes(minutes: float | None) -> str:
    if minutes is None:
        return "unknown time"
    return f"{round(minutes)} min" if minutes < 120 else f"{minutes / 60:.1f} h"


def _time_text(status: str | None, wall: float | None, accepted: int) -> str:
    if not accepted:
        return "no stage accepted yet"
    spent = _fmt_minutes(wall)
    return {"done": f"done in {spent}", "active": f"running, {spent} at snapshot",
            "blocked": f"blocked after {spent}", "failed": f"halted after {spent}"}.get(status, spent)


def _knowledge(checkouts: list[Path]) -> tuple[dict, Path | None]:
    """Byte sizes of docs/shiploop/** in the first checkout that has it (largest first, at most 40)."""
    for root in checkouts:
        home = root / "docs" / "shiploop"
        if home.is_dir():
            sizes = {path.relative_to(root).as_posix(): path.stat().st_size
                     for path in sorted(home.rglob("*")) if path.is_file() and not path.is_symlink()}
            top = sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_KNOWLEDGE]
            return dict(top), root
    return {}, None


# ---------------------------------------------------------------- Backchain loop ledger

# Digest keys a review record may carry for the candidate before and after its pass, by layout.
INPUT_KEYS = ("candidate_input_sha256", "candidate_from_sha256", "candidate_sha256_before")
OUTPUT_KEYS = ("candidate_output_sha256", "candidate_to_sha256", "candidate_sha256_after")


def _find_key(value, keys: tuple[str, ...], depth: int = 0):
    """The first string value under any of `keys` (breadth-first by key priority, three levels deep)."""
    if not isinstance(value, dict) or depth > 3:
        return None
    for key in keys:
        if isinstance(value.get(key), str):
            return value[key]
    for child in value.values():
        found = _find_key(child, keys, depth + 1)
        if found:
            return found
    return None


def _digests(record: dict) -> tuple[str | None, str | None]:
    before, after = _find_key(record, INPUT_KEYS), _find_key(record, OUTPUT_KEYS)
    identity = record.get("candidate_identity")
    if after is None and isinstance(identity, dict) and isinstance(identity.get("sha256"), str):
        after = identity["sha256"]  # a first pass may record only the candidate it left
    return before, after


def _snapshots(loop: Path) -> dict[str, Path]:
    found = {}
    for path in sorted([*loop.glob("*candidate*.json"), *loop.glob("*/*candidate*.json")]):
        if path.is_file():
            found.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), path)
    return found


def _step_diff(old: Path, new: Path) -> str | None:
    def steps(path):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise ValueError("no steps")
        return {str(row.get("id")): json.dumps(row, sort_keys=True) for row in rows if isinstance(row, dict)}
    try:
        before, after = steps(old), steps(new)
    except (OSError, UnicodeError, ValueError):
        return None
    changed = sum(1 for k in before.keys() & after.keys() if before[k] != after[k])
    parts = [f"{changed} step{'s' if changed != 1 else ''} changed"] if changed else []
    for label, ids in (("added", sorted(after.keys() - before.keys())), ("removed", sorted(before.keys() - after.keys()))):
        if ids:
            parts.append(f"{label} {', '.join(ids)}" if len(ids) <= 3 else f"{len(ids)} {label}")
    return ", ".join(parts) or "other fields changed"


def _reply(path: Path | None) -> tuple[int | None, str | None]:
    """(progress.trivial_streak, last_report.classification) from the Until Loop's reply to a pass's done
    callback (JSON, possibly inside captured stdout)."""
    try:
        text = path.read_text(encoding="utf-8") if path and path.is_file() else ""
        start, end = text.find("{"), text.rfind("}")
        reply = json.loads(text[start:end + 1]) if start >= 0 else {}
    except (OSError, UnicodeError, ValueError):
        return None, None
    reply = reply if isinstance(reply, dict) else {}
    progress = reply.get("progress") if isinstance(reply.get("progress"), dict) else {}
    report = reply.get("last_report") if isinstance(reply.get("last_report"), dict) else {}
    streak = progress.get("trivial_streak")
    return (streak if isinstance(streak, int) and not isinstance(streak, bool) else None,
            report.get("classification") if isinstance(report.get("classification"), str) else None)


def _passes(loop: Path) -> tuple[str | None, list[tuple[str, Path, Path | None]]]:
    """(layout, [(number, review record, done reply)]) for the two layouts the runs keep."""
    records = loop / "review-records"
    plan = sorted(((m.group(1), p) for p in records.glob("action-*-review.json")
                   if (m := re.fullmatch(r"action-(\d+)-review\.json", p.name))), key=lambda t: int(t[0]))
    if plan:
        return "action-N-review", [(n, p, loop / "pass-reports" / f"action{int(n)}-done-packet.json") for n, p in plan]
    step = sorted(((m.group(1), p) for p in records.glob("review-*.json")
                   if (m := re.fullmatch(r"review-(\d+)\.json", p.name))), key=lambda t: int(t[0]))
    if step:
        rows = []
        for n, p in step:
            corrected = records / f"review-{n}-callback-result-corrected.stdout"
            rows.append((n, p, corrected if corrected.is_file() else records / f"review-{n}-callback-result.stdout"))
        return "review-NN", rows
    return None, []


def _loop_name(directory: str) -> str:
    if "step-plan" in directory:
        return "step-plan"
    if "plan" in directory:
        return "plan"
    return directory.removeprefix("backchain-")


def _owner(loop: str, start: datetime | None, text: str, actions: list[dict]) -> dict | None:
    """The accepted action whose stage ran the loop: named in the receipt or start input, else by time."""
    def inside(action):
        return start is not None and action["from"] is not None and action["from"] <= start <= action["at"]
    tokens = list(dict.fromkeys(NAV_ID.findall(text)))
    named = [a for a in actions if any(a["id"].startswith(t) for t in tokens)]
    for pool in ([a for a in named if a["stage"] == loop and inside(a)], [a for a in named if a["stage"] == loop],
                 [a for a in named if inside(a)], named if len(named) == 1 else [],
                 [a for a in actions if a["stage"] == loop and inside(a)],
                 [a for a in actions if inside(a)]):
        if pool:
            return pool[0]
    return None


def _integer_split(raw: list[float], total: int | None) -> list[int]:
    """Round each part; when a total is given, the last part absorbs the rounding so the sum is exact
    (cumulative rounding instead if that would make it negative)."""
    parts = [round(x) for x in raw]
    if total is None:
        return parts
    parts[-1] = total - sum(parts[:-1])
    if parts[-1] < 0:
        edges, running = [0], 0.0
        for x in raw:
            running += x
            edges.append(round(running))
        edges[-1] = total
        parts = [b - a for a, b in zip(edges, edges[1:])]
    return parts


def loop_doc(run_key: str, run_dir: Path, loop: Path, actions: list[dict], order: int) -> dict:
    """One backchain/<runKey>-<loop> document. Best effort: an unreadable layout gives segments []."""
    name = _loop_name(loop.name)
    receipt = _optional_json(loop / "until-loop-receipt.json") or {}
    start_input = loop / "until-loop-start-input.json"
    layout, passes = _passes(loop)
    loop_start = _mtime(start_input) if start_input.is_file() else (_mtime(passes[0][1]) if passes else None)
    text = json.dumps(receipt) + (start_input.read_text(encoding="utf-8", errors="replace")
                                  if start_input.is_file() else "")
    owner = _owner(name, loop_start, text, actions)
    progress = receipt.get("progress") if isinstance(receipt.get("progress"), dict) else {}
    facts = [{"k": "Passes", "v": str(len(passes))},
             {"k": "Final status", "v": str(receipt.get("status") or "unknown")}]
    if "trivial_streak" in progress:
        facts.append({"k": "Trivial streak", "v": f"{progress.get('trivial_streak')} of "
                                                  f"{progress.get('required_trivial_reviews', '?')} required"})
    facts.append({"k": "Receipt", "v": (loop / "until-loop-receipt.json").relative_to(run_dir).as_posix()})
    stage = owner["stage"] if owner else None
    doc = {"run": run_key, "loop": name, "phase": STAGE_PHASE.get(stage or name, 2), "order": order,
           "title": f"{name[:1].upper()}{name[1:]} loop", "stageMin": None, "segments": [], "facts": facts}
    if layout is None:
        facts.append({"k": "Layout", "v": "not recognized: no review-records/action-N-review.json "
                                          "or review-records/review-NN.json"})
        return doc
    snapshots: dict[str, Path] | None = None
    rows, previous_end, previous_after = [], loop_start, None
    for index, (number, path, reply) in enumerate(passes, 1):
        record = _optional_json(path) or {}
        end = _mtime(path)
        before, after = _digests(record)
        before = before or previous_after
        if before and after and before == after:
            change = "none"
        elif before and after:
            snapshots = _snapshots(loop) if snapshots is None else snapshots
            diff = (_step_diff(snapshots[before], snapshots[after])
                    if before in snapshots and after in snapshots else None)
            change = diff or "changed"
        else:
            change = "unknown"
        streak, classification = _reply(reply)
        row = {"label": f"Pass {index}", "kind": "unclear", "pass": index, "change": change,
               "note": f"The loop recorded it as {classification}." if classification else "",
               "raw": _minutes(previous_end, end) if previous_end else 0.0}
        if streak is not None:
            row["streak"] = streak
        rows.append(row)
        previous_end, previous_after = end, after or previous_after
    stage_min = None
    if owner and owner["from"] is not None and loop_start is not None and owner["from"] <= loop_start \
            and previous_end <= owner["at"]:
        stage_min = round(owner["min"])
        raw = [_minutes(owner["from"], loop_start), *(r["raw"] for r in rows), _minutes(previous_end, owner["at"])]
        split = _integer_split(raw, stage_min)
        segments = [{"label": "Before the loop", "min": split[0], "kind": "neutral",
                     "note": f"From the previous accept to the loop start ({stage} stage)."}]
        segments += [dict({k: v for k, v in r.items() if k != "raw"}, min=m) for r, m in zip(rows, split[1:-1])]
        segments.append({"label": "After the loop", "min": split[-1], "kind": "neutral",
                         "note": f"From the last pass to the {stage} stage's accept."})
        facts.append({"k": "Stage", "v": f"{stage}, {stage_min} min accept to accept"})
    else:
        split = _integer_split([r["raw"] for r in rows], None)
        segments = [dict({k: v for k, v in r.items() if k != "raw"}, min=m) for r, m in zip(rows, split)]
        facts.append({"k": "Stage", "v": f"{stage}: the loop lies outside its accept window" if owner
                      else "not matched to an accepted action"})
    doc["stageMin"], doc["segments"] = stage_min, segments
    return doc


def find_loops(scratch: Path) -> list[Path]:
    """Directories under scratch/ (up to three levels) that hold an until-loop-receipt.json."""
    found = []
    for pattern in ("*/until-loop-receipt.json", "*/*/until-loop-receipt.json", "*/*/*/until-loop-receipt.json"):
        found += [p.parent for p in sorted(scratch.glob(pattern)) if p.is_file()]
    return found


# ---------------------------------------------------------------- the run document

def _clean_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "run"


def _text(value) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def build_run(out: Path, key: str | None = None, name: str | None = None,
              order: int | None = None) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """({collection: {id: document}}, facts.md lines) for one run output directory."""
    out = out.expanduser().resolve()
    if not out.is_dir():
        raise ExportError(f"not a directory: {out}")
    metrics = _read_json(out / "metrics.json")
    result = _optional_json(out / "result.json") or {}
    invocation = _optional_json(out / "invocation.json") or {}
    run_dir = find_run_dir(out, (result.get("shiploop") or {}).get("run_dir"))
    timeline = _read_json(run_dir / "timeline.json")
    if not isinstance(timeline, dict) or not isinstance(timeline.get("accepted"), dict):
        raise ExportError(f"{run_dir / 'timeline.json'} has no accepted map")
    results = run_dir / "results"
    if not results.is_dir():
        raise ExportError(f"missing {results}")
    state = _record(run_dir / "state.md")
    if state is None:
        raise ExportError(f"cannot read the shiploop-state record in {run_dir / 'state.md'}")

    history = [h for h in state.get("history") or [] if isinstance(h, dict)]
    position = {}
    for index, entry in enumerate(history):
        position.setdefault(entry.get("action"), index)
    started = _when(timeline.get("started"))
    accepted = []
    for action, stamp in timeline["accepted"].items():
        moment = _when(stamp)
        if moment is None:
            raise ExportError(f"{run_dir / 'timeline.json'}: accept time {stamp!r} of {action} is not ISO")
        accepted.append((moment, position.get(action, len(history)), action, stamp))
    accepted.sort()

    actions, stages, phases_seen = [], [], []
    from_state, unknown = [], []
    previous, last_phase = started, 0
    for moment, _, action, stamp in accepted:
        record = _record(results / f"{action}.md")
        if record is not None:
            body = record.get("result") if isinstance(record.get("result"), dict) else {}
            stage, outcome = record.get("stage"), record.get("outcome") or body.get("outcome")
        else:
            entry = next((h for h in history if h.get("action") == action), None)
            if entry is None:
                raise ExportError(f"missing {results / (action + '.md')} for an accepted action")
            stage, outcome = entry.get("stage"), entry.get("outcome")
            from_state.append(action)
        stage, outcome = str(stage or "unknown"), str(outcome or "unknown")
        if stage in STAGE_PHASE:
            last_phase = STAGE_PHASE[stage]
        else:
            unknown.append(stage)
        minutes = _minutes(previous, moment) if previous else 0.0
        row = {"stage": stage, "outcome": outcome, "min": round(minutes, 1)}
        for field, path in (("packetBytes", run_dir / "packets" / f"{action}.md"), ("resultBytes", results / f"{action}.md")):
            if path.is_file():
                row[field] = path.stat().st_size
        stages.append(row)
        phases_seen.append(last_phase)
        actions.append({"id": action, "stage": stage, "from": previous, "at": moment, "min": minutes})
        previous = moment

    raw_status = state.get("status")
    status = RUN_STATUS.get(raw_status)
    now = current_stage(state)
    current = None if raw_status == "done" else STAGE_PHASE.get(now, phases_seen[-1] if phases_seen else 0)
    if now and now not in STAGE_PHASE and raw_status != "done":
        unknown.append(now)
    wall = _minutes(started, accepted[-1][0]) if started and accepted else None

    versions = invocation.get("versions") or result.get("versions") or {}
    host = _text(invocation.get("host")) or _text(result.get("host"))
    model = _text(invocation.get("model")) or _text(result.get("model"))
    effort = _text(invocation.get("effort")) or _text(result.get("effort"))
    case = _text(invocation.get("case")) or _text(result.get("case"))
    plugin, shiploop = _text(versions.get("plugin_version")), _text(versions.get("shiploop_version"))
    release = (f"skill-craft {plugin}, ShipLoop {shiploop}" if plugin and shiploop
               else f"skill-craft {plugin}" if plugin else f"ShipLoop {shiploop}" if shiploop else "unknown")
    first = started or (accepted[0][0] if accepted else None)
    key = _clean_key(key or "-".join([host or "unknown", model or "unknown", plugin or "unknown", case or "unknown",
                                      first.strftime("%Y%m%d") if first else "undated"]))
    name = name or (" ".join(part for part in (host, model, effort) if part) or "unknown host") + \
        (f", release {plugin}" if plugin else "")
    order = order if order is not None else (int(first.timestamp()) if first else 0)

    improve_root = run_dir / "improve"
    children = sum(1 for p in improve_root.iterdir() if p.is_dir()) if improve_root.is_dir() else 0
    reviews = metrics.get("improve_reviews") if isinstance(metrics.get("improve_reviews"), dict) else {}
    failures = [f for f in metrics.get("shiploop_failures") or [] if isinstance(f, dict)]
    glue = metrics.get("model_glue") or []
    # An Improve child is named by the action whose stage started it; list them in accept order.
    rank = {a["id"]: (i, a["stage"]) for i, a in enumerate(actions)}
    children_rows = []
    for child in reviews.get("per_child") or []:
        if isinstance(child, dict):
            place, stage = rank.get(child.get("child"), (len(actions), str(child.get("child"))))
            children_rows.append((place, stage, {"stage": stage, "passes": child.get("passes", 0),
                                                 "seconds": child.get("seconds", 0), "bytes": child.get("bytes", 0)}))
    improve = [row for _, _, row in sorted(children_rows, key=lambda t: (t[0], t[1]))]
    checkouts = [out / "work", run_dir.parent / "worktree"]
    knowledge, knowledge_root = _knowledge(checkouts if raw_status == "done" else checkouts[::-1])

    run = {"key": key, "name": name, "order": order, "release": release,
           "phases": derive_phases(phases_seen, current, raw_status),
           "time": _time_text(status, wall, len(accepted)),
           "imp": f"{children} children" + (f", {reviews['passes']} review passes" if reviews.get("passes") else ""),
           "refusals": len(failures), "glue": len(glue), "stages": stages,
           "failures": [{"verb": str(f.get("verb")), "line": str(f.get("line") or "")[:MAX_FAILURE_LINE]}
                        for f in failures],
           "improve": improve, "knowledge": knowledge, "evidence": str(out)}
    for field, value in (("host", host), ("model", model), ("effort", effort), ("case", case), ("status", status),
                         ("startedAt", timeline.get("started") if started else None)):
        if value:
            run[field] = value
    if wall is not None:
        run["wallMin"] = round(wall, 1)
    if raw_status == "done" and accepted:
        run["endedAt"] = accepted[-1][3]
    verdicts = {}
    for verdict in ("invoked", "plugin", "process", "shiploop", "committed"):
        if isinstance(result.get(verdict), dict) and isinstance(result[verdict].get("pass"), bool):
            verdicts[verdict] = result[verdict]["pass"]
    if isinstance(result.get("checks"), list) and result["checks"]:
        verdicts["checks"] = all(bool(c.get("pass")) for c in result["checks"] if isinstance(c, dict))
    if verdicts:
        run["verdicts"] = verdicts

    docs: dict[str, dict[str, dict]] = {"runs": {key: run}, "backchain": {}}
    loops = []
    scratch = run_dir / "scratch"
    for loop in find_loops(scratch) if scratch.is_dir() else []:
        try:
            doc = loop_doc(key, run_dir, loop, actions, 0)
        except Exception as exc:  # noqa: BLE001 - the ledger is best effort and never fails the export
            doc = {"run": key, "loop": _loop_name(loop.name), "phase": 2, "order": 0,
                   "title": f"{_loop_name(loop.name)} loop", "stageMin": None, "segments": [],
                   "facts": [{"k": "Ledger", "v": f"not built: {type(exc).__name__}: {exc}"}]}
        start = loop / "until-loop-start-input.json"
        loops.append(((start.stat().st_mtime if start.is_file() else 0.0), loop.name, doc))
    loops.sort(key=lambda t: (t[0], t[1]))
    for index, (_, _, doc) in enumerate(loops, 1):
        doc["order"] = index
        doc_id, suffix = f"{key}-{doc['loop']}", 2
        while doc_id in docs["backchain"]:
            doc_id, suffix = f"{key}-{doc['loop']}-{suffix}", suffix + 1
        docs["backchain"][doc_id] = doc

    facts = _facts(run, run_dir, out, raw_status, reviews, failures, knowledge_root, docs["backchain"],
                   unknown, from_state)
    return docs, facts


def _facts(run, run_dir, out, raw_status, reviews, failures, knowledge_root, loops, unknown, from_state) -> list[str]:
    stages = run["stages"]
    totals: dict[str, list] = {}
    for row in stages:
        totals.setdefault(row["stage"], []).append(row["min"])
    slowest = sorted(totals.items(), key=lambda kv: (-sum(kv[1]), kv[0]))[:5]
    verbs: dict[str, int] = {}
    for failure in failures:
        verbs[str(failure.get("verb"))] = verbs.get(str(failure.get("verb")), 0) + 1
    knowledge = run["knowledge"]
    largest = next(iter(knowledge.items()), None)
    lines = [f"# Run Review facts: {run['key']}", "",
             f"- Run: ShipLoop status {raw_status or 'unknown'}; {len(stages)} accepted actions; "
             f"{run.get('wallMin', 'unknown')} min from start to the last accept",
             f"- Driver: {' '.join(run[k] for k in ('host', 'model', 'effort') if k in run) or 'unknown'}; "
             f"case {run.get('case', 'unknown')}; {run['release']}",
             "- Verdicts: " + (", ".join(f"{k} {'pass' if v else 'fail'}" for k, v in run["verdicts"].items())
                               if run.get("verdicts") else "no result.json"),
             "- Slowest stages (min, accept to accept): " + (", ".join(
                 f"{stage} {sum(m):.1f}" + (f" ({len(m)}x)" if len(m) > 1 else "") for stage, m in slowest) or "none"),
             f"- Phases: {', '.join(f'{title} {state}' for (title, _), state in zip(PHASES, run['phases']))}",
             f"- Improve: {run['imp']}" + (f"; most passes in one child: {reviews.get('max_passes')}"
                                           if reviews.get("max_passes") else ""),
             f"- ShipLoop command failures: {len(failures)}" + (
                 f" ({', '.join(f'{v} {n}' for v, n in sorted(verbs.items()))})" if verbs else ""),
             f"- Model glue: {run['glue']} commands",
             f"- Planning documents: {len(knowledge)} files, {sum(knowledge.values()) / 1024:.1f} KB"
             + (f" in {knowledge_root.relative_to(out).as_posix() if knowledge_root.is_relative_to(out) else knowledge_root}"
                f"; largest {largest[0]} {largest[1] / 1024:.1f} KB" if largest else ""),
             f"- Packets {sum(r.get('packetBytes', 0) for r in stages) / 1024:.1f} KB, results "
             f"{sum(r.get('resultBytes', 0) for r in stages) / 1024:.1f} KB over {len(stages)} accepted actions",
             "- Backchain loops: " + ("; ".join(
                 f"{d['loop']} {next((f['v'] for f in d['facts'] if f['k'] == 'Passes'), '?')} passes, "
                 f"{next((f['v'] for f in d['facts'] if f['k'] == 'Final status'), '?')}"
                 + (f", stage {d['stageMin']} min" if d.get("stageMin") is not None else "")
                 for d in loops.values()) or "none found under scratch/"),
             f"- Run directory: {run_dir.relative_to(out).as_posix()}"]
    if unknown:
        lines.append(f"- Stages not in the phase table (shown with the previous phase): {', '.join(sorted(set(unknown)))}")
    if from_state:
        lines.append(f"- Accepted actions without a result file (stage from state.md): {len(from_state)}")
    return lines


# ---------------------------------------------------------------- writing

def _validate_all(docs: dict[str, dict[str, dict]]) -> list[str]:
    return [f"{collection}/{doc_id}: {problem}" for collection, items in sorted(docs.items())
            for doc_id, doc in sorted(items.items()) for problem in validate_doc(collection, doc)]


def write_export(out: Path, docs: dict[str, dict[str, dict]], facts: list[str] | None = None,
                 compact: bool = True, prune_prefix: str | None = None) -> Path:
    """Validate every document, then write docs/, writes.json and (for a run) facts.md and review-export.json."""
    problems = _validate_all(docs)
    if problems:
        raise ExportError("documents violate SCHEMA.md:\n  " + "\n  ".join(problems))
    extras = [f"{c}/{i}: {', '.join(extra_fields(c, d))}" for c, items in sorted(docs.items())
              for i, d in sorted(items.items()) if extra_fields(c, d)]
    if facts is not None and extras:
        facts = [*facts, f"- Fields the contract does not name: {'; '.join(extras)}"]
    bundle = json.dumps({"schema": SCHEMA_ID, "docs": docs}, sort_keys=True, separators=(",", ":")) + "\n"
    if compact and len(bundle.encode("utf-8")) > MAX_COMPACT_BYTES:
        raise ExportError(f"review-export.json would be {len(bundle.encode('utf-8'))} bytes, over {MAX_COMPACT_BYTES}")
    out = out.expanduser().resolve()
    writes = []
    for collection in sorted(docs, key=lambda c: (COLLECTION_ORDER.index(c) if c in COLLECTION_ORDER else 99, c)):
        folder = out / "docs" / collection
        if docs[collection]:
            folder.mkdir(parents=True, exist_ok=True)
        if prune_prefix:  # an earlier export of this run may have written documents this one no longer has
            for stale in sorted(folder.glob("*.json")) if folder.is_dir() else []:
                if (stale.stem == prune_prefix or stale.stem.startswith(prune_prefix + "-")) \
                        and stale.stem not in docs[collection]:
                    stale.unlink()
        for doc_id in sorted(docs[collection]):
            path = folder / f"{doc_id}.json"
            path.write_text(json.dumps(docs[collection][doc_id], sort_keys=True, indent=1) + "\n", encoding="utf-8")
            writes.append({"op": "set", "collection": collection, "doc_id": doc_id, "file_path": str(path)})
    (out / "writes.json").write_text(json.dumps(writes, indent=1) + "\n", encoding="utf-8")
    if facts is not None:
        (out / "facts.md").write_text("\n".join(facts) + "\n", encoding="utf-8")
    if compact:
        (out / "review-export.json").write_text(bundle, encoding="utf-8")
    return out


def export_run(run_out: Path, key: str | None = None, name: str | None = None, order: int | None = None,
               out: Path | None = None) -> Path:
    """Export one run output directory; returns the export directory."""
    run_out = Path(run_out).expanduser().resolve()
    docs, facts = build_run(run_out, key, name, order)
    run_key = next(iter(docs["runs"]))
    return write_export(out or run_out / "review-export", docs, facts, compact=True, prune_prefix=run_key)


def defaults_docs() -> dict[str, dict[str, dict]]:
    expectations = _read_json(DEFAULTS / "expectations.json")
    config = _read_json(DEFAULTS / "config.json")
    docs: dict[str, dict[str, dict]] = {"expectations": {}, "config": {}}
    for entry in expectations:
        docs["expectations"][entry["key"]] = {k: v for k, v in entry.items() if k != "key"}
    for doc_id, doc in config.items():
        docs["config"][doc_id] = doc
    return docs


def export_defaults(out: Path | None = None) -> Path:
    """The starting expectations and page settings, for a create-only seed of a new page."""
    return write_export(out or Path(tempfile.gettempdir()) / "run-review-defaults", defaults_docs(), compact=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", nargs="?", type=Path, help="a run output directory of test/shiploop_e2e/run.py")
    parser.add_argument("--defaults", action="store_true", help="export the starting expectations and settings")
    parser.add_argument("--key", help="the runs document id (default <host>-<model>-<release>-<case>-<yyyymmdd>)")
    parser.add_argument("--name", help="the run's display name")
    parser.add_argument("--order", type=int, help="sort key (default the run's start, epoch seconds)")
    parser.add_argument("--out", type=Path, help="export directory (default RUN_DIR/review-export)")
    args = parser.parse_args(argv)
    if args.defaults == (args.run_dir is not None):
        parser.error("give a RUN_DIR or --defaults")
    try:
        path = export_defaults(args.out) if args.defaults else export_run(
            args.run_dir, args.key, args.name, args.order, args.out)
    except ExportError as exc:
        print(f"export: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
