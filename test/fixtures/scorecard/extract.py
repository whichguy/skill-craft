#!/usr/bin/env python3
"""Rebuild the compact extracts in runs/ from the saved runs under /Users/dadleet/e2e-runs (2026-10-10 to 2026-10-25).

The scorecard tests read the extracts, never the saved runs. This script is provenance, not a test: run it by hand on the
machine that holds the runs, then commit the result. Each extract keeps the run's path under the runs root and only the keys
test/shiploop_e2e/scorecard.py reads: result.json and metrics.json reduced, the first two and last two timeline stamps, and
a suite's suite-result.json (the scorecard finds a suite case's runs root by it).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

RUNS = Path("/Users/dadleet/e2e-runs")
HERE = Path(__file__).resolve().parent
PICK = ["20261024/gate-290-b60ed7-claude-batch/hello", "20261024/gate-290-b60ed7-claude-batch/seat-reservations",
        "20261024/gate-290-b60ed7-claude-batch/battleship", "20261024/gate-290-b60ed7-claude-csv-report",
        "20261024/gate-290-b60ed7-codex-hello", "20261020/chess-sf-full-9e52e8", "20261010/checkers-1"]
SUITES = ["20261024/gate-290-b60ed7-claude-batch"]


def reduced_result(r: dict) -> dict:
    quality = r.get("quality") or {}
    keep_quality = {}
    for name in ("mutation", "acceptance"):
        part = quality.get(name)
        if isinstance(part, dict):
            keep_quality[name] = {k: part.get(k) for k in ("observed", "reason", "ratio", "operator_id") if k in part}
            if isinstance(part.get("checks"), list):
                keep_quality[name]["checks"] = [{"id": c.get("id"), "pass": c.get("pass")} for c in part["checks"]]
        elif name in quality:
            keep_quality[name] = part
    left = r.get("left_behind") or {}
    return {"case": r.get("case"), "host": r.get("host"), "model": r.get("model"), "effort": r.get("effort"),
            "versions": {k: (r.get("versions") or {}).get(k) for k in ("source", "plugin_version", "shiploop_version")},
            "outcome_class": r.get("outcome_class"), "pass": r.get("pass"),
            **{name: {"pass": (r.get(name) or {}).get("pass")} for name in ("invoked", "plugin", "process", "shiploop", "committed")},
            "checks": [{"pass": c.get("pass")} for c in r.get("checks") or []], "quality": keep_quality,
            "resumed_run": {"from_host": (r.get("resumed_run") or {}).get("from_host")} if r.get("resumed_run") else None,
            "environment": {"mixed_host": (r.get("environment") or {}).get("mixed_host"),
                            "environments": [{"host": e.get("host"), "host_build": e.get("host_build")}
                                             for e in (r.get("environment") or {}).get("environments") or [] if isinstance(e, dict)]},
            "left_behind": {k: left.get(k) for k in ("observed", "reason", "survived") if k in left}}


def reduced_metrics(m: dict) -> dict:
    fidelity = m.get("fidelity") or {}
    end = fidelity.get("end_state") or {}
    starts = m.get("fresh_starts")
    return {"span": m.get("span"), "cost_usd": m.get("cost_usd"), "unreported_sessions": m.get("unreported_sessions"),
            "claude_code_version": m.get("claude_code_version"),
            "nomenclature": ({"retired": {term: {"texts": (hit or {}).get("texts")} for term, hit in (m["nomenclature"].get("retired") or {}).items()}}
                             if isinstance(m.get("nomenclature"), dict) else m.get("nomenclature")),
            "unmeasured": {k: "kept" for k in (m.get("unmeasured") or {})}, "turns": m.get("turns"),
            "shiploop_failures": [{} for _ in m.get("shiploop_failures") or []], "improve_children": m.get("improve_children"),
            "planning": {"window": (m.get("planning") or {}).get("window")},
            "fresh_starts": ([{"reorientation": {k: (s.get("reorientation") or {}).get(k) for k in ("measured", "seconds")}}
                              for s in starts] if isinstance(starts, list) else starts),
            "fresh_starts_unmeasured": m.get("fresh_starts_unmeasured"),
            "fidelity": ({"end_state": {"status": end.get("status"), "unverified": {"entries": (end.get("unverified") or {}).get("entries")}},
                          "evidence": {"counts": {"skipped": ((fidelity.get("evidence") or {}).get("counts") or {}).get("skipped")}},
                          "edits": {"script_owned": [{} for _ in ((fidelity.get("edits") or {}).get("script_owned") or [])]},
                          "refusals": {k: (fidelity.get("refusals") or {}).get(k) for k in ("count", "repeated")}}
                         if fidelity else {})}


def main() -> None:
    out = HERE / "runs"
    shutil.rmtree(out, ignore_errors=True)
    for run in PICK:
        src, dst = RUNS / run, out / run
        dst.mkdir(parents=True)
        (dst / "result.json").write_text(json.dumps(reduced_result(json.loads((src / "result.json").read_text())), indent=1) + "\n")
        (dst / "metrics.json").write_text(json.dumps(reduced_metrics(json.loads((src / "metrics.json").read_text())), indent=1) + "\n")
        lines = [line for line in (src / "timeline.jsonl").read_text().splitlines() if line.strip()]
        (dst / "timeline.jsonl").write_text("\n".join(lines[:2] + lines[-2:]) + "\n")
    for suite in SUITES:  # the case names and verdicts only: the scorecard reads whether the file is there, and paths name a machine
        record = json.loads((RUNS / suite / "suite-result.json").read_text())
        cases = [{k: row.get(k) for k in ("case", "pass", "skipped", "gate") if k in row} for row in record.get("cases") or []]
        (out / suite / "suite-result.json").write_text(json.dumps({"suite": record.get("suite"), "cases": cases}, indent=1) + "\n")


if __name__ == "__main__":
    if not RUNS.is_dir():
        sys.exit(f"the saved runs are not here: {RUNS}")
    main()
