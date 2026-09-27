#!/usr/bin/env python3
"""Print what changed in a running (or finished) E2E run since the last call.

  python3 test/shiploop_e2e/progress.py <output directory>

Remembers what it already reported in <output>/.progress.json and prints one
block: counters, then only what is new (accepted stages with their turns and
minutes, ShipLoop command failures, truncations, compactions, ended sessions,
the model's latest remark). It never prints packet text or run markers, so a
ShipLoop keepalive in the watching session cannot bind to the run.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills/shiploop/scripts"))
import shiploop_store as store  # noqa: E402


def run_state(out: Path) -> tuple[Path | None, dict]:
    for path in sorted(out.rglob("state.md")):
        if path.relative_to(out).parts[0] in ("home", "build"):
            continue
        try:
            state = store.read_record(path)
        except Exception:
            continue
        if isinstance(state, dict) and "status" in state:
            return path.parent, state
    return None, {}


def last_remark(out: Path) -> str:
    text, said = "", ""
    for _, event in metrics.events(out / "events.jsonl"):
        if event.get("type") == "text" and isinstance(event.get("data"), str):
            text += event["data"]
        elif event.get("type") == "tool_call":
            said, text = (" ".join(text.split()) or said), ""
    remark = " ".join(text.split()) or said
    return "" if metrics.MARKER.search(remark) else remark[:200]


def report(out: Path) -> str:
    memo_path = out / ".progress.json"
    try:
        memo = json.loads(memo_path.read_text())
    except (OSError, ValueError):
        memo = {}
    run_dir, state = run_state(out)
    m = metrics.collect(out, run_dir)
    started = (out / "invocation.json").stat().st_mtime if (out / "invocation.json").is_file() else time.time()
    items = f"{len(state.get('completed_work_items') or [])}/{len(state.get('work_items') or [])}"
    lines = [f"[{int(time.time() - started) // 60} min] turns {m['turns']}, peak context "
             f"{m['tokens']['input_peak'] // 1000}K, cost {('$' + format(m['cost_usd'], '.2f')) if m['cost_usd'] else 'n/a'} | "
             + (f"{state.get('status')}, rev {state.get('revision')}, stage {state.get('stage')}, items {items}"
                if state else "no run state yet")]
    stages = m["stages"][memo.get("stages", 0):]
    if stages:
        lines.append("  accepted: " + ", ".join(
            f"{s['stage']} {s['turns']}t/{s['seconds'] / 60:.1f}m" if "turns" in s else s["stage"] for s in stages))
    for failure in m["shiploop_failures"][memo.get("failures", 0):]:
        lines.append(f"  ShipLoop {failure['verb']} failed (exit {failure['exit']}): {failure['line']}")
    for key, label in (("truncated_outputs", "host truncated outputs"), ("compactions", "compactions"),
                       ("improve_children", "Improve children"), ("test_runs", "test runs")):
        if m[key] > memo.get(key, 0):
            lines.append(f"  {label}: {m[key]} (+{m[key] - memo.get(key, 0)})")
    for session in m["sessions"][memo.get("sessions", 0):]:
        lines.append(f"  session ended: {session['stop']} after {session['turns']} turns")
    remark = last_remark(out)
    if remark:
        lines.append("  model: " + remark)
    memo_path.write_text(json.dumps({"stages": len(m["stages"]), "failures": len(m["shiploop_failures"]),
                                     "sessions": len(m["sessions"]),
                                     **{k: m[k] for k in ("truncated_outputs", "compactions",
                                                          "improve_children", "test_runs")}}))
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(report(Path(sys.argv[1]).expanduser().resolve()), flush=True)
