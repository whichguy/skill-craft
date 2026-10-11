"""Generate the Run Review hand-off of harness batch 1011 from the merged code (docs/shiploop-batch-1011-run-review-handoff-2026-10-09.md).

Nothing in the hand-off is typed by hand except the "null means" and "group" columns: every key path, type and example value is
produced here by the merged harness code, from three sources:

* saved runs under /Users/dadleet/e2e-runs (read only: metrics.collect, fidelity.safe_build, metrics.blocked_detail,
  run.outcome_class, environment.result_block with a regrade's start and end, run.folder_record and run.baseline_report; none
  of them starts a process or writes a file);
* fake-host runs through run.main at the merged head (the harness's own fake hosts from test/shiploop-e2e.test.py, in a
  temporary folder): the keys only a launch writes (launch records, sessions.jsonl, product_at_stop, a regrade's *_at_regrade);
* the committed evidence of group G5 (docs/experiments/batch-1011p-g5-quality-20261009/evidence.json `example_block`: the
  quality block quality.measure wrote for 20261008/r3-checkers-sonnet), because the quality phase is not re-run here (it runs
  the delivery's own tests).

Run from the repository root: SHIPLOOP_PROGRESS=off python3 docs/experiments/batch-1011-run-review-handoff-20261009/generate.py
It writes shapes.json beside itself and the hand-off markdown.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUNS = Path("/Users/dadleet/e2e-runs")
DOC = ROOT / "docs" / "shiploop-batch-1011-run-review-handoff-2026-10-09.md"
sys.path[:0] = [str(ROOT / "test" / "shiploop_e2e"), str(ROOT / "skills" / "shiploop" / "scripts")]

import environment  # noqa: E402
import fidelity  # noqa: E402
import metrics  # noqa: E402
import run  # noqa: E402

SAVED = ["20261008/r1-battleship-sonnet", "20261008/r2-checkers-sonnet", "20261008/r3-battleship-sonnet",
         "20261008/r1-battleship-grok-none", "20261008/r2-battleship-grok-none", "20261008/r3-battleship-grok-none",
         "20261007/v1230-battleship-grok-none"]


def saved_records() -> dict:
    """What the merged code reads from each saved run, as a regrade at the merged head would record it."""
    cases = json.loads(run.CASES.read_text())
    found = {}
    for name in SAVED:
        out = RUNS / name
        result = json.loads((out / "result.json").read_text())
        ledger = Path(result["shiploop"]["run_dir"]) if (result.get("shiploop") or {}).get("run_dir") else None
        invocation = json.loads((out / "invocation.json").read_text())
        cli = run.run_cli(invocation["host"], out, Path(invocation.get("plugin_dir") or out / "missing-plugin"))
        tools = metrics.ToolLog()
        collected = metrics.collect(out, ledger, tools=tools)
        collected["fidelity"] = fidelity.safe_build(out, ledger, tools, engine_scripts=cli.parent, exporter=run.REVIEW_EXPORTER)
        state = metrics.engine_state(ledger)
        termination = {**(result.get("termination") or {}),
                       **{f"engine_{key}": value for key, value in metrics.blocked_detail(state).items()}}
        klass, basis = run.outcome_class(bool(result.get("pass")), termination)
        env = environment.result_block(out, environment.restated_start(out),
                                       environment.unobserved("regraded: the end of the run was not observed"))
        record = run.folder_record(out, cases)
        row = record["row"]
        identity = {key: row.get(key) for key in run.IDENTITY_FIELDS}
        found[name] = {
            "result": {"outcome_class": klass, "outcome_basis": basis, "termination": termination, "environment": env,
                       "prompt_sha256": row.get("prompt_sha256"), "host_build": row.get("host_build"),
                       "span": {"started": row.get("started"), "ended": row.get("ended")},
                       "identity_unmeasured": {**row.get("identity_unmeasured", {}), **record["why_not"]},
                       "versions": {"plugin_sha256": row.get("plugin_sha256")}},
            "metrics": collected,
            "row": {**identity, "identity_unmeasured": row.get("identity_unmeasured"), "termination": row.get("termination")},
        }
    return found


def fake_records() -> dict:
    """Fake-host runs through run.main at the merged head: what only a launch writes."""
    spec = importlib.util.spec_from_file_location("e2e_main_tests", ROOT / "test" / "shiploop-e2e.test.py")
    e2e = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = e2e
    spec.loader.exec_module(e2e)
    found: dict = {}

    class Runs(e2e.CaseRunCase):
        def test_runs(self):
            e2e.isolate_git(self)
            card = self.plugin / "skills" / "improve" / "SKILL.md"
            card.parent.mkdir(parents=True, exist_ok=True)
            card.write_text("# Improve\n")
            for label, extra, mode, host, env in (
                    ("fake claude hello", ("--case", "hello"), "done", "claude", None),
                    ("fake grok hello", ("--case", "hello"), "done", "grok", None),
                    ("fake claude hello --planning-review none", ("--case", "hello", "--planning-review", "none"), "done",
                     "claude", {"FAKE_PLANNING_REVIEW": "none"}),
                    ("fake grok hello, stopped (engine active)", ("--case", "hello", "--max-resumes", "0"), "stuck", "grok", None)):
                code, result, _printed, out = self.case_main(label.replace(" ", "-").replace(",", "").replace("(", "")
                                                             .replace(")", ""), *extra, mode=mode, host=host, env=env)
                rows = [json.loads(line) for line in self.baselines.read_text().splitlines()] if self.baselines.exists() else []
                found[label] = {"result": result, "metrics": json.loads((out / "metrics.json").read_text()),
                                "invocation": json.loads((out / "invocation.json").read_text()),
                                "sessions": [json.loads(line) for line in (out / "sessions.jsonl").read_text().splitlines()],
                                "row": rows[-1] if rows and rows[-1].get("output") == result.get("output") else None}
            # A regrade of the finished Claude run: the *_at_regrade termination keys and the regrade's own launch record.
            out = self.tmp / "fake-claude-hello"
            with e2e.contextlib.redirect_stdout(e2e.io.StringIO()):
                run.main(["--host", "claude", "--claude-bin", str(self.fakes["claude"]), "--resume-run", str(out), "--grade-only",
                          "--baseline", str(self.baselines)])
            found["fake claude hello, regraded"] = {"result": json.loads((out / "result.json").read_text())}

    result = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(unittest.TestLoader().loadTestsFromTestCase(Runs))
    if not result.wasSuccessful():
        raise SystemExit(f"the fake runs failed: {result.errors or result.failures}")
    return found


def report_records() -> dict:
    """`run.py --baseline-report --json` over the saved runs (read only): records[] and cells[]."""
    report = run.baseline_report(ROOT / "test" / "shiploop_e2e" / "baselines.jsonl", [RUNS / "20261008", RUNS / "20261007"])
    wanted = {str(RUNS / name) for name in SAVED}
    records = [r for r in report["records"] if str(r.get("output")) in wanted]
    cells = sorted((c for c in report["cells"] if c["cell"].get("case") in ("battleship", "checkers")),
                   key=lambda c: (c["cell"].get("host") != "claude", -c["attempts"]["counted"]))
    return {"records": records, "cells": cells, "inputs": report.get("inputs")}


def kind(value) -> str:
    return {bool: "boolean", int: "integer", float: "number", str: "string", list: "array", dict: "object",
            type(None): "null"}[type(value)]


def short(value, width: int = 110) -> str:
    text = json.dumps(value, default=str)
    text = text.replace(str(RUNS), "<e2e-runs>").replace(tempfile.gettempdir(), "<tmp>").replace(str(Path.home()), "~")
    return text if len(text) <= width else text[:width - 1] + "…"


def lookup(data, path: str):
    """The value at a dotted path; `[]` steps into the first element of a list."""
    for part in path.split("."):
        if part.endswith("[]"):
            data = data.get(part[:-2]) if isinstance(data, dict) else None
            data = data[0] if isinstance(data, list) and data else None
        else:
            data = data.get(part) if isinstance(data, dict) else None
    return data


def example(sources: dict, record: str, path: str) -> tuple[str, str, str]:
    """(type, example, run) from the first source that has a non-null value at the path, else its null."""
    seen_null = None
    for name, source in sources.items():
        data = source.get(record) if isinstance(source, dict) else None
        if data is None:
            continue
        value = lookup(data, path)
        present = _present(data, path)
        if value is not None:
            return kind(value), short(value), name
        if present and seen_null is None:
            seen_null = name
    return ("null", "null", seen_null) if seen_null else ("(absent)", "", "")


def _present(data, path: str) -> bool:
    parts = path.split(".")
    for part in parts[:-1]:
        data = data.get(part.rstrip("[]")) if isinstance(data, dict) else None
        if part.endswith("[]"):
            data = data[0] if isinstance(data, list) and data else None
    return isinstance(data, dict) and parts[-1] in data


# (path, null means, group, new in batch 1011). The first three columns of the doc come from the generated data.
RESULT = [
    ("outcome_class", "unknown (outcome_basis says why); never a verdict", "G4", True),
    ("outcome_basis", "never null", "G4", True),
    ("termination.engine_blocked_by", "no accepted blocked result, or the block was answered", "G4", True),
    ("termination.engine_awaiting_kind", "as engine_blocked_by", "G4", True),
    ("termination.engine_awaiting_no_default", "awaits no one (true: the result states why no default would do)", "G4", True),
    ("termination.engine_status_at_regrade", "(only on a regrade that kept the original ending)", "base", False),
    ("termination.engine_stage_at_regrade", "(regrade only)", "G4", True),
    ("termination.engine_blocked_by_at_regrade", "(regrade only) as engine_blocked_by", "G4", True),
    ("product_at_stop", "absent for a run that passed", "G4", True),
    ("product_at_stop.ran", "never null; false with reason when nothing could run", "G4", True),
    ("product_at_stop.checks[]", "(ran: true)", "G4", True),
    ("environment.start", "{observed: false, reason} when not recorded", "G4", True),
    ("environment.start.tools", "(observed start) a tool not found or not read is null, reason in unread", "G4", True),
    ("environment.start.browser", "(observed start) {declared: false, ...} when no need is declared", "G4", True),
    ("environment.end", "{observed: false, reason} for a regrade", "G4", True),
    ("environment.hosts_used", "{observed: false, reason} when a launch record cannot be read", "G4", True),
    ("environment.mixed_host", "as hosts_used", "G4", True),
    ("environment.environments[]", "one entry per readable launch, first first", "G4", True),
    ("environment.environments[].host_build", "null with identity_unmeasured.host_build (runrecord.host_build)", "G4+G3", True),
    ("environment.environments[].identity_unmeasured", "{} when the build is known", "integration", True),
    ("environment.environments[].environment", "null with environment_reason for a launch from before the record", "G4", True),
    ("environment.launches_unreadable", "[] when every launch record reads", "G4", True),
    ("environment.overlap", "{observed: false, reason} when this run's timeline has no span", "G4", True),
    ("environment.overlap.runs[]", "[] means no sibling's host events overlapped (not that nothing else ran)", "G4", True),
    ("environment.overlap.siblings_unreadable", "names, never dropped", "G4", True),
    ("quality", "absent on runs from before this change; {observed: false, reason} when not measured", "G5", True),
    ("quality.mutation.ratio", "(observed) killed / (killed + survived); compare only within one operator_id", "G5", True),
    ("quality.acceptance", "(Checkers) {observed: false, reason} when not run", "G5", True),
    ("quality.memory_writes", "null with unmeasured.memory_writes when no Claude session or no launch record", "G5", True),
    ("prompt_sha256", "the case prompt (before a --planning-review none sentence), output folder masked", "G3", True),
    ("host_build", "null with identity_unmeasured.host_build (the FIRST launch's build)", "G3", True),
    ("span", "{started: null, ended: null} without readable timeline stamps", "G3", True),
    ("identity_unmeasured", "{} when every identity field is known; a reason per null field", "G3", True),
    ("versions.plugin_sha256", "null with versions.plugin_sha256_unmeasured / identity_unmeasured.plugin_sha256", "G3", True),
]
METRICS = [
    ("fidelity", "{schema, error} when the builder raised; parts null with fidelity.unmeasured[part]", "G1", True),
    ("fidelity.evidence", "null with unmeasured.evidence", "G1", True),
    ("fidelity.validation", "null with unmeasured.validation", "G1", True),
    ("fidelity.edits", "heuristic list; null when the stream holds no tool call", "G1", True),
    ("fidelity.refusals", "heuristic list", "G1", True),
    ("fidelity.end_state", "null with unmeasured.end_state (blocked fields read through metrics.blocked_detail)", "G1", True),
    ("fidelity.unmeasured", "{} when every part was measured", "G1", True),
    ("fresh_starts", "[] measured none only when fresh_starts_unmeasured is null", "G2", True),
    ("fresh_starts[].reorientation", "measured: false with reason, and no counts, when the window cannot be placed", "G2", True),
    ("fresh_starts_unmeasured", "null when the list is complete; else notes joined with '; '", "G2", True),
    ("unreported_sessions", "null for a stream with Grok in it (no session start marker), reason in unmeasured", "G3", False),
    ("unreported_sessions_at_least", "null where the count is exact (not Grok)", "G3", True),
    ("span", "{started: null, ended: null} without readable stamps", "G3", True),
]
SESSIONS = [
    ("row", "start | end", "G2", True), ("n", "the launch's number", "G2", True), ("kind", "first | fresh | continued", "G2", True),
    ("reason", "start | resume-run | after-interrupt | resume-loop", "G2", True), ("events_line", "never null", "G2", True),
    ("told", "null for a first launch (no recovery command)", "G2", True),
    ("engine", "null before ShipLoop wrote state", "G2", True), ("status", "(end row) exited | stopped | ... | crashed", "G2", True),
    ("reconstructed", "(only in G2's fixtures of runs from before sessions.jsonl)", "G2", True),
]
INVOCATION = [
    ("host_build", "null with identity_unmeasured.host_build; Claude's is always null (init event)", "G3", True),
    ("identity_unmeasured", "{} when known", "G3", True),
    ("versions.plugin_sha256", "null with versions.plugin_sha256_unmeasured", "G3", True),
    ("needs", "[] when nothing declares a need", "G4", True),
    ("environment", "{observed: false, reason} on a regrade's own record", "G4", True),
    ("planning_review", "null when the option was not given", "G5", True),
    ("improve_skill", "null unless --planning-review none", "G5", True),
]
ROW = [
    ("plugin_sha256", "null with identity_unmeasured.plugin_sha256", "G3", True),
    ("prompt_sha256", "as result.json", "G3", True), ("host_build", "as result.json", "G3", True),
    ("local_head", "null with identity_unmeasured.local_head", "G3", True), ("started", "as span", "G3", True),
    ("ended", "as span", "G3", True), ("planning_seconds", "null while the window is open or unread", "G3", True),
    ("identity_unmeasured", "{} when all known; a row without it predates it", "G3", True),
    ("termination", "the result's termination minus run.ROW_EXCLUDED_TERMINATION (no blocked detail)", "integration", False),
]
REPORT_RECORD = ["output", "record", "case", "source", "host", "model", "effort", "planning_review", "prompt_sha256", "plugin_version",
                 "plugin_sha256", "host_build", "local_head", "started", "ended", "minutes", "planning_seconds", "planning_minutes",
                 "cost_usd", "turns", "lower_bound", "pass", "engine_status", "process_status", "hosts_used", "class", "why",
                 "recomputed", "identity_unmeasured", "overlaps"]
REPORT_CELL = ["cell", "attempts", "builds", "host_builds", "measures.cost_usd", "measures.minutes", "overlap", "outputs"]


GENERATED: dict = {}  # what the tables show, kept as shapes.json (compact: one example per key path)


def table(rows: list, sources: dict, record: str, section: str) -> list[str]:
    lines = ["| Key path | Type | Null means | Example (source) | Group | New |", "|---|---|---|---|---|---|"]
    for path, meaning, group, new in rows:
        typ, value, name = example(sources, record, path)
        GENERATED.setdefault(section, []).append({"path": path, "type": typ, "example": value, "source": name, "group": group,
                                                  "new": new, "null_means": meaning})
        cell = f"`{value}` ({name})" if name else "no generated example"
        lines.append(f"| `{path}` | {typ} | {meaning.replace('|', 'or')} | {cell.replace('|', '/')} | {group} | "
                     f"{'yes' if new else 'no'} |")
    return lines


def main() -> None:
    os.environ.setdefault("SHIPLOOP_PROGRESS", "off")
    saved = saved_records()
    fakes = fake_records()
    report = report_records()
    evidence = json.loads((ROOT / "docs" / "experiments" / "batch-1011p-g5-quality-20261009" / "evidence.json").read_text())
    g5 = {f"G5 evidence: {evidence['example_block']['run']}": {"result": {"quality": evidence["example_block"]["block"]}}}
    sources = {**saved, **g5, **fakes}
    result_keys = {}
    for name, source in {**fakes}.items():
        for key in source["result"]:
            result_keys.setdefault(key, name)
    lines = [
        "# Run Review hand-off: the record shapes after the batch 1011 merge (2026-10-09)",
        "",
        "Generated by `docs/experiments/batch-1011-run-review-handoff-20261009/generate.py` at the integration head (do not edit by",
        "hand; rerun it). Key paths, types and examples are what the merged code produced: saved runs under `<e2e-runs>`",
        "(`/Users/dadleet/e2e-runs`, read only, as a regrade at the merged head reads them), fake-host runs through `run.main`",
        "(`fake ...`: the keys only a launch writes), and G5's committed quality evidence. The full generated data is",
        "`shapes.json` beside the script. \"New\" marks a key that runs from before this batch do not have (absent, not null).",
        "",
        "## Contents",
        "",
        "1. result.json: top-level keys and their groups",
        "2. result.json additions",
        "3. metrics.json additions",
        "4. sessions.jsonl rows",
        "5. Launch records (invocation*.json) additions",
        "6. Baseline row additions",
        "7. `run.py --baseline-report --json`",
        "",
        "## 1. result.json: top-level keys and their groups",
        "",
        "| Key | Group | First seen in |",
        "|---|---|---|",
    ]
    groups = {"prompt_sha256": "G3", "host_build": "G3", "span": "G3", "identity_unmeasured": "G3", "outcome_class": "G4",
              "outcome_basis": "G4", "environment": "G4", "product_at_stop": "G4 (runs that did not pass)", "quality": "G5",
              "quality_regrade_skipped": "G5 (a regrade that could not measure)"}
    for key, name in result_keys.items():
        lines.append(f"| `{key}` | {groups.get(key, 'before batch 1011')} | {name} |")
    lines += ["", "`fidelity` is in metrics.json only (G1), never in result.json; `metrics` copies a fixed subset of metrics.json.", ""]
    lines += ["## 2. result.json additions", ""] + table(RESULT, sources, "result", "result.json")
    lines += ["", "## 3. metrics.json additions", ""] + table(METRICS, sources, "metrics", "metrics.json")
    session_sources = {name: {"row": fakes[name]["sessions"][0]} for name in fakes if "sessions" in fakes[name]}
    session_sources.update({f"{name} (end row)": {"row": fakes[name]["sessions"][-1]} for name in fakes if "sessions" in fakes[name]})
    fixture = ROOT / "test" / "fixtures" / "reorientation" / "r3-battleship-grok-none" / "sessions.jsonl"
    if fixture.is_file():
        session_sources["G2 fixture r3-battleship-grok-none (reconstructed)"] = {
            "row": [json.loads(line) for line in fixture.read_text().splitlines()][-1]}
    lines += ["", "## 4. sessions.jsonl rows", ""] + table(SESSIONS, session_sources, "row", "sessions.jsonl")
    lines += ["", "## 5. Launch records (invocation*.json) additions", ""] + table(
        INVOCATION, {name: {"invocation": source["invocation"]} for name, source in fakes.items() if "invocation" in source},
        "invocation", "invocation*.json")
    row_sources = {**{name: {"row": source["row"]} for name, source in saved.items()},
                   **{name: {"row": source["row"]} for name, source in fakes.items() if source.get("row")}}
    lines += ["", "## 6. Baseline row additions", "", "Not in the row (pinned by tests): `quality`, `outcome_class`, `outcome_basis`,",
              "`environment`, `engine_blocked_by`, `engine_awaiting_*` and the G4 `*_at_regrade` readings.", ""]
    lines += table(ROW, row_sources, "row", "baseline row")
    record_sources = {Path(r["output"]).name: {"record": r} for r in report["records"]}
    cell_sources = {f"cell {c['cell'].get('case')} {c['cell'].get('host')}": {"cell": c} for c in report["cells"]}
    lines += ["", "## 7. `run.py --baseline-report --json`", "",
              "`{inputs, records, cells, notes}` over the saved runs and the committed baselines.jsonl (G3; read only).", "",
              "records[]:", ""]
    lines += table([(key, "null where unknown (see identity_unmeasured / why)", "G3", True) for key in REPORT_RECORD],
                   record_sources, "record", "baseline report records[]")
    lines += ["", "cells[]:", ""]
    lines += table([(key, "never null", "G3", True) for key in REPORT_CELL], cell_sources, "cell", "baseline report cells[]")
    GENERATED["result.json top-level keys"] = {key: groups.get(key, "before batch 1011") for key in result_keys}
    (HERE / "shapes.json").write_text(json.dumps(GENERATED, indent=1) + "\n")
    DOC.write_text("\n".join(lines) + "\n")
    print(f"wrote {DOC.relative_to(ROOT)} and {(HERE / 'shapes.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
