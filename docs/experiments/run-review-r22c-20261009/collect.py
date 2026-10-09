#!/usr/bin/env python3
"""Recompute the figures the Run Review findings of 2026-10-09 (increment R22c) cite, from the recorded run folders.

  python3 -B docs/experiments/run-review-r22c-20261009/collect.py [/Users/dadleet/e2e-runs] > figures.json

Reads, never writes, the run folders (outside the repository). Every number a finding or a figure in
test/shiploop_e2e/evidence/general.review.json, r3-battleship-sonnet.review.json or r3-battleship-grok-none.review.json
takes from a run folder is here, so test/shiploop-run-review.test.py checks the bundles against this file and never reads
the run folders. The credential screen is replayed with this checkout's skills/shiploop/scripts/shiploop_privacy.py on
the exact lines the runs submitted (read from events.jsonl), which is how the trigger of each refusal is named.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_privacy  # noqa: E402  (the screen the engine runs at a knowledge close)

FOLDERS = ["20261008/r1-battleship-sonnet", "20261008/r1-checkers-sonnet", "20261008/r1-battleship-grok-none",
           "20261008/r2-battleship-sonnet", "20261008/r2-checkers-sonnet", "20261008/r2-battleship-grok-none",
           "20261008/r3-battleship-sonnet", "20261008/r3-checkers-sonnet", "20261008/r3-battleship-grok-none",
           "20261007/v1230-battleship-sonnet", "20261007/v1230-battleship-grok-none"]
ROUND = [f.split("/")[1] for f in FOLDERS[:9]]
STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
LOG_SECOND = re.compile(r"^\[\s*(\d+)s\]")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stamp(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_dir(folder: Path) -> Path:
    found = sorted(folder.glob(".shiploop-runs/*/run"))
    assert len(found) == 1, folder
    return found[0]


def history(folder: Path) -> list[dict]:
    """state.md history rows, each with its accept stamp from timeline.json."""
    run = run_dir(folder)
    state = json.loads(STATE.search((run / "state.md").read_text(encoding="utf-8")).group(1))
    accepted = load(run / "timeline.json")["accepted"]
    return [{"visit": i, "stage": row["stage"], "outcome": row["outcome"], "accepted": accepted.get(row["action"])}
            for i, row in enumerate(state["history"], 1)]


def strings(value, out: list) -> list:
    if isinstance(value, dict):
        for item in value.values():
            strings(item, out)
    elif isinstance(value, list):
        for item in value:
            strings(item, out)
    elif isinstance(value, str):
        out.append(value)
    return out


def refused_lines(folder: Path, marker: str) -> list[dict]:
    """The spec lines the credential screen flags, from the events before the first refusal naming `marker` that
    write or edit docs/shiploop/spec.md (a guidance file the model read is not what it submitted)."""
    lines = (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(lines, 1) if marker in line and "look like credentials" in line)
    flagged = {}
    for line in lines[:first]:
        if "docs/shiploop/spec.md" not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        for text in strings(event, []):
            for row in text.splitlines():
                if row.strip() and shiploop_privacy.sensitive_text(row):
                    flagged[row.strip()] = True
    result = []
    for row in flagged:
        trips = [part for part in re.split(r"(?<=[.;,])\s", row) if shiploop_privacy.sensitive_text(part)]
        hex_only = re.sub(r"(?i)\b(signature|auth)\b\s*:", "", row)
        result.append({"line": row, "trips_on": trips, "hex_colours": len(re.findall(r"#[0-9a-fA-F]{6}\b", row)),
                       "flagged_without_key_word": shiploop_privacy.sensitive_text(hex_only)})
    return result


def backchain(folder: Path) -> dict:
    root = run_dir(folder) / "backchain"
    return {"check_receipts": len(list(root.glob("**/check-*.json"))) if root.is_dir() else 0,
            "loop_receipts": len(list(root.glob("**/until-loop-receipt.json"))) if root.is_dir() else 0}


def one(folder_name: str) -> dict:
    folder = RUNS / folder_name
    result, metrics = load(folder / "result.json"), load(folder / "metrics.json")
    export = load(folder / "review-export" / "review-export.json")["docs"]["runs"]
    (doc,) = export.values()
    hosts = [load(folder / "invocation.json")["host"]] + [load(p)["host"] for p in sorted(folder.glob("invocation-resume-*.json"))]
    planning = metrics.get("planning") or {}
    window = planning.get("window") or {}
    narrative = metrics.get("narrative") or {}
    failures = metrics.get("shiploop_failures")
    return {
        "key": folder_name.split("/")[1],
        "release": doc.get("release"),
        "invocation_hosts": hosts,
        "status": (result.get("shiploop") or {}).get("status"),
        "stage": (result.get("termination") or {}).get("engine_stage"),
        "checks_passed": sum(bool(c.get("pass")) for c in result.get("checks") or []),
        "checks": len(result.get("checks") or []),
        "visits": len(doc.get("stages") or []),
        "wall_min": doc.get("wallMin"),
        "calls": metrics.get("model_calls"),
        "cost_usd": metrics.get("cost_usd"),
        "planning_window_seconds": window.get("seconds"),
        "planning_window_host_seconds": window.get("host_seconds"),
        "planning_window_min": round(window["seconds"] / 60, 1) if window.get("seconds") is not None else None,
        "planning_improve_children": (planning.get("improve") or {}).get("children"),
        "improve_passes": doc.get("improvePasses"),
        "refusal_lines": [f["line"][:160] for f in failures] if isinstance(failures, list) else None,
        "credential_refusals": sum("look like credentials" in f["line"] for f in failures) if isinstance(failures, list) else None,
        "glue": len(metrics["model_glue"]) if isinstance(metrics.get("model_glue"), list) else metrics.get("model_glue"),
        "narrative_emitted": narrative.get("emitted"),
        "narrative_shown": narrative.get("shown"),
        "skipped_visits": [s["stage"] for s in doc.get("stages") or [] if s.get("skipped")],
        "left_behind_reaped": len(((result.get("left_behind") or {}).get("reaped")) or []),
        **backchain(folder),
    }


def refusal_to_accept(folder: Path, marker: str) -> float:
    """Seconds from the first credential refusal naming `marker` (its events.jsonl line, timed by timeline.jsonl) to
    the spec accept (timeline.json)."""
    lines = (folder / "events.jsonl").read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(lines, 1) if marker in line and "look like credentials" in line)
    marks = [json.loads(line) for line in (folder / "timeline.jsonl").read_text(encoding="utf-8").splitlines()]
    at = [m["t"] for m in marks if m["line"] <= first - 1][-1]
    spec = next(r for r in history(folder) if r["stage"] == "spec")
    return round(stamp(spec["accepted"]) - at, 1)


def luna_recollect(folder: Path) -> dict:
    """The Luna 1.16.1 run's refusals as today's harness records them (metrics.collect is read-only)."""
    sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
    import metrics  # noqa: E402
    failures = metrics.collect(folder, run_dir(folder))["shiploop_failures"]
    return {"failures": len(failures),
            "generic_tails": sum(f["line"].startswith("Read the current packet with next") for f in failures),
            "own_line": sum(bool(re.match(r"(ShipLoop navigator: |shiploop: error: |error: )", f["line"])) for f in failures)}


def log_last_second(path: Path) -> int:
    seconds = [int(m.group(1)) for line in path.read_text(encoding="utf-8").splitlines() if (m := LOG_SECOND.match(line))]
    return seconds[-1]


def main() -> None:
    runs = {r["key"]: r for r in map(one, FOLDERS)}
    out = {"source": str(RUNS), "round_runs": ROUND, "runs": runs}
    # round 1 Grok: the system-test-author visit that ended blocked (accept to accept, timeline.json)
    r1 = history(RUNS / "20261008/r1-battleship-grok-none")
    out["r1_grok_blocked_visit_min"] = round((stamp(r1[-1]["accepted"]) - stamp(r1[-2]["accepted"])) / 60, 1)
    out["r1_grok_blocked_stage"] = r1[-1]["stage"]
    # round 2 Grok: who accepted which visit. The resume that ran Claude is named by its epoch.
    folder = RUNS / "20261008/r2-battleship-grok-none"
    claude = [p for p in folder.glob("invocation-resume-*.json") if load(p)["host"] == "claude"]
    (claude_file,) = claude
    claude_start = int(claude_file.stem.rsplit("-", 1)[1])
    rows = history(folder)
    started = stamp(load(run_dir(folder) / "timeline.json")["started"])
    host_start = started - load(folder / "metrics.json")["planning"]["window"]["before_engine_seconds"]
    harness_end = host_start + log_last_second(RUNS / "20261008/r2-grok.log")
    out["r2_mixed"] = {
        "claude_resume_file": claude_file.name, "claude_start": iso(claude_start),
        "grok_visits": sum(stamp(r["accepted"]) < claude_start for r in rows),
        "claude_visits": sum(stamp(r["accepted"]) >= claude_start for r in rows),
        "first_claude_visit": next(r["visit"] for r in rows if stamp(r["accepted"]) >= claude_start),
        "first_grok_harness_log_last_second": log_last_second(RUNS / "20261008/r2-grok.log"),
        "visits_before_harness_end": sum(stamp(r["accepted"]) < harness_end for r in rows),
        "orphan_gap_min": round((claude_start - harness_end) / 60, 1),
    }
    # round 3 Grok: the open implement visit and where its browser work began
    folder = RUNS / "20261008/r3-battleship-grok-none"
    rows, result = history(folder), load(folder / "result.json")
    pending = [s for s in load(folder / "metrics.json")["stages"] if s.get("outcome") is None]
    log = (RUNS / "20261008/r3-grok-resume.log").read_text(encoding="utf-8").splitlines()
    browser = next(int(m.group(1)) for line in log if (m := LOG_SECOND.match(line)) and re.search(r"(?i)browser|chrome", line))
    resume = [p for p in folder.glob("invocation-resume-*.json")]
    resume_start = int(resume[0].stem.rsplit("-", 1)[1])
    out["r3_grok"] = {
        "last_accept": rows[-1]["accepted"], "last_accepted_stage": rows[-1]["stage"], "accepted_visits": len(rows),
        "resumed_session_seconds": result["process"]["elapsed_seconds"],
        "resumed_session_min": round(result["process"]["elapsed_seconds"] / 60, 1),
        "earlier_stop": [t.get("resume_stop") for t in result.get("earlier_terminations") or []],
        "stop": result["termination"]["resume_stop"].split(" by ")[0],
        "open_implement_seconds": pending[0]["seconds"], "open_implement_min": round(pending[0]["seconds"] / 60, 1),
        "open_implement_turns": pending[0]["turns"],
        "resume_start": iso(resume_start),
        "implement_open_from_session_second": round(stamp(rows[-1]["accepted"]) - resume_start),
        "first_browser_line_second": browser,
        "browser_debug_scripts": len(list(run_dir(folder).glob("scratch/browser-debug*.mjs"))),
    }
    out["credential_replay"] = {
        "r3-battleship-grok-none": refused_lines(RUNS / "20261008/r3-battleship-grok-none", "spec.md:188"),
        "r2-battleship-grok-none": refused_lines(RUNS / "20261008/r2-battleship-grok-none", "spec.md:205"),
    }
    out["credential_refusal_to_spec_accept_seconds"] = {
        key: refusal_to_accept(RUNS / "20261008" / key, marker)
        for key, marker in (("r3-battleship-grok-none", "spec.md:188"), ("r2-battleship-grok-none", "spec.md:205"))}
    out["luna_recollect"] = luna_recollect(RUNS / "20261003/v1161-battleship-luna")
    out["graph_checked_round_runs"] = sorted(k for k in ROUND if runs[k]["check_receipts"])
    out["backchain_loop_round_runs"] = sorted(k for k in ROUND if runs[k]["loop_receipts"])
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
