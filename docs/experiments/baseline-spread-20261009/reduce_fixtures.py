#!/usr/bin/env python3
"""Reduce saved E2E run folders to the compact extracts test/fixtures/baseline-spread/ holds.

A fixture keeps the SHAPE of a run folder (file names, invocation*.json launch records, result.json, metrics.json,
timeline.jsonl, prompt.txt, state.md in the run directory) and only the keys the baseline reader looks at.  The plugin
build is replaced by a three-file stub whose bytes name the real tree's digest, so two folders whose real trees were
byte-identical still hold identical stubs and two that differed hold different ones.  Recorded absolute paths are kept
as they were (they point at the machine the run was made on), which is also the situation of any moved folder.

    python3 reduce_fixtures.py [--from /Users/dadleet/e2e-runs] [--to test/fixtures/baseline-spread]

Provenance: the extracts in the repository were made from the folders listed in RUNS on 2026-10-09.  The saved runs are
the evidence and live outside the repository; no test reads them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

RUNS = (
    "20261006/v1220-battleship-sonnet",
    "20261007/v1230-battleship-sonnet",
    "20261008/r1-battleship-sonnet",
    "20261008/r1-checkers-sonnet",
    "20261008/r2-battleship-sonnet",
    "20261008/r2-checkers-sonnet",
    "20261008/r3-battleship-sonnet",
    "20261008/r3-checkers-sonnet",
    "20261006/v1220-battleship-grok-medium-none",
    "20261007/v1230-battleship-grok-none",
    "20261008/r1-battleship-grok-none",
    "20261008/r2-battleship-grok-none",
    "20261008/r3-battleship-grok-none",
    "20261005/v1210-battleship-grok-medium",
)
# the committed baselines.jsonl rows these runs wrote (the run folder's own `output` names the row)
KEEP_ROW = ("date", "case", "style", "suite", "host", "model", "effort", "termination", "unmeasured", "source",
            "plugin_version", "shiploop_version", "planning_review", "pass", "verdicts", "checks_passed", "checks", "turns",
            "cost_usd", "sessions", "output")


def read(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def tree_digest(root: Path) -> str | None:
    if not root.is_dir():
        return None
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc" or path.is_symlink() or not path.is_file():
            continue
        digest.update(relative.as_posix().encode() + b"\0" + hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return digest.hexdigest()[:12]


def reduce_run(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    result = read(source / "result.json")
    invocations = sorted(source.glob("invocation*.json"))
    first = read(source / "invocation.json")
    output = (result or first or {}).get("output") or str(source)
    # launch records: identity and versions, no argv or checks
    for path in invocations:
        record = read(path) or {}
        reduced = {k: record.get(k) for k in ("case", "host", "model", "effort", "plugin_dir", "versions", "resumed_run", "seeded")}
        (target / path.name).write_text(json.dumps(reduced, indent=1) + "\n")
        plugin_dir = record.get("plugin_dir") or ""
        marker = output + "/"
        if plugin_dir.startswith(marker):
            stub = target / plugin_dir[len(marker):]
            real = Path(plugin_dir.replace(output, str(source)))
            digest = tree_digest(real)
            (stub / ".claude-plugin").mkdir(parents=True, exist_ok=True)
            (stub / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": (record.get("versions") or {}).get("plugin_version")}) + "\n")
            (stub / "skills" / "shiploop" / "scripts").mkdir(parents=True, exist_ok=True)
            (stub / "skills" / "shiploop" / "scripts" / "shiploop").write_text(f"# stub of a tree whose real digest was {digest}\n")
    if (source / "prompt.txt").is_file():
        (target / "prompt.txt").write_text((source / "prompt.txt").read_text())
    stamps = [line for line in (source / "timeline.jsonl").read_text().splitlines() if line.strip()] if (source / "timeline.jsonl").is_file() else []
    if stamps:
        (target / "timeline.jsonl").write_text("\n".join(stamps[:2] + stamps[-2:]) + "\n")
    # the engine's state.md (the planning_review key), at the same place under the run folder
    run_dir = ((result or {}).get("shiploop") or {}).get("run_dir")
    if run_dir and run_dir.startswith(output + "/") and (Path(run_dir.replace(output, str(source))) / "state.md").is_file():
        state = (Path(run_dir.replace(output, str(source))) / "state.md").read_text()
        body = state[state.index("```shiploop-state"):]
        body = body[: body.index("```", 10) + 3]
        keep = json.loads(body.split("\n", 1)[1].rsplit("\n```", 1)[0])
        keep = {k: keep[k] for k in ("status", "stage", "planning_review") if k in keep}
        placed = target / run_dir[len(output) + 1:]
        placed.mkdir(parents=True, exist_ok=True)
        (placed / "state.md").write_text("```shiploop-state\n" + json.dumps(keep, indent=1) + "\n```\n")
    if result is None:
        return
    metrics = result.get("metrics") or {}
    process = result.get("process") or {}
    reduced = {
        "case": result.get("case"), "host": result.get("host"), "model": result.get("model"), "effort": result.get("effort"),
        "pass": result.get("pass"),
        "invoked": {"pass": (result.get("invoked") or {}).get("pass")},
        "plugin": {"pass": (result.get("plugin") or {}).get("pass")},
        "versions": result.get("versions"),
        "process": {k: process.get(k) for k in ("status", "returncode", "elapsed_seconds", "stop", "pass", "regraded")}
                   | {"sessions": [{k: s.get(k) for k in ("status", "stop", "host", "resumed")} for s in process.get("sessions") or []]},
        "termination": result.get("termination"),
        **({"earlier_terminations": result["earlier_terminations"]} if result.get("earlier_terminations") else {}),
        "shiploop": {"pass": (result.get("shiploop") or {}).get("pass"), "run_dir": run_dir},
        "committed": {"pass": (result.get("committed") or {}).get("pass")},
        "checks": [{"pass": c.get("pass")} for c in result.get("checks") or []],
        "resumed_run": result.get("resumed_run"), "seeded": result.get("seeded"),
        "metrics": {k: metrics.get(k) for k in ("claude_code_version", "turns", "model_calls", "cost_usd", "unreported_sessions",
                                                "compactions", "truncated_outputs", "cancelled_tool_calls", "model_glue", "tmp_writes",
                                                "shiploop_failures")}
                   | {"unmeasured": {name: "reduced" for name in metrics.get("unmeasured") or {}}},
        "output": result.get("output"),
    }
    (target / "result.json").write_text(json.dumps(reduced, indent=1) + "\n")
    saved = read(source / "metrics.json") or {}
    (target / "metrics.json").write_text(json.dumps({"claude_code_version": saved.get("claude_code_version"),
                                                     "planning": {"window": (saved.get("planning") or {}).get("window")}}, indent=1) + "\n")
    # Claude's init event names its build even in a run whose metrics did not record it
    if result.get("host") == "claude" and (source / "events.jsonl").is_file():
        for line in (source / "events.jsonl").read_text(errors="replace").splitlines()[:5]:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "system" and event.get("subtype") == "init":
                (target / "events.jsonl").write_text(json.dumps({k: event.get(k) for k in ("type", "subtype", "claude_code_version")}) + "\n")
                break


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", type=Path, default=Path("/Users/dadleet/e2e-runs"))
    parser.add_argument("--to", dest="target", type=Path, default=Path(__file__).resolve().parents[3] / "test/fixtures/baseline-spread")
    parser.add_argument("--baseline", type=Path, default=Path(__file__).resolve().parents[3] / "test/shiploop_e2e/baselines.jsonl")
    args = parser.parse_args()
    outputs = set()
    for name in RUNS:
        folder = args.source / name
        reduce_run(folder, args.target / "runs" / folder.name)
        outputs.add(str(folder))
    rows = [json.loads(line) for line in args.baseline.read_text().splitlines() if line.strip()]
    kept = [{k: row.get(k) for k in KEEP_ROW if k in row} for row in rows if row.get("output") in outputs]
    (args.target / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in kept))
    print(f"{len(RUNS)} run folders, {len(kept)} baseline rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
