#!/usr/bin/env python3
"""Print what changed in a running (or finished) E2E run since the last call.

  python3 test/shiploop_e2e/progress.py <output directory>

Remembers what it already reported in <output>/.progress.json and prints one
block: counters, then only what is new (accepted stages with their turns and
minutes, ShipLoop command failures, truncations, compactions, ended sessions,
the model's latest remark, once which counters the host cannot show, and once the
planning window when it closes). It never
prints packet text or run markers, so a ShipLoop keepalive in the watching session
cannot bind to the run.
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
    peak = m["tokens"]["input_peak"]
    lines = [f"[{int(time.time() - started) // 60} min] turns {metrics.turns_text(m)}, peak context "
             f"{'n/a' if peak is None else str(peak // 1000) + 'K'}, "
             f"cost {('$' + format(m['cost_usd'], '.2f')) if m['cost_usd'] else 'n/a'} | "
             + (f"{state.get('status')}, rev {state.get('revision')}, "
                f"stage {metrics.current_stage(state) or state.get('stage')}, items {items}"
                if state else "no run state yet")]
    # The in-progress stage is on the first line (the item's own stage, not the navigator's
    # `inner-loop` label), and its row moves with every poll, so only accepted stages are listed here.
    # Stage minutes are wall clock: a resume, a sleep or a credit stop inside a stage counts in it.
    stages = [s for s in m["stages"] if not s.get("incomplete")][memo.get("stages", 0):]
    if stages:
        lines.append("  accepted: " + ", ".join(metrics.stage_text(s) for s in stages))
    # The planning window is reported once, when it closes: the live record of the owner's 30-minute planning rule.
    closed = m["planning"]["window"]["closed"]
    if closed and not memo.get("planning"):
        lines.append("  " + metrics.planning_text(m["planning"]))
    # A counter this host's events cannot show prints nothing below, so say so once: silence is not a clean result.
    blind = sorted(set(m["unmeasured"]) - set(memo.get("unmeasured") or []) - {"stage_turns"})
    if blind:
        lines.append("  not measured on this host (nothing printed for these is not a clean result): " + ", ".join(blind))
    for failure in m["shiploop_failures"][memo.get("failures", 0):]:
        lines.append(f"  ShipLoop {failure['verb']} failed (exit {failure['exit']}): {failure['line']}")
    for key, label in (("truncated_outputs", "host truncated outputs"), ("compactions", "compactions"),
                       ("improve_children", "Improve children")):
        if m[key] is not None and m[key] > memo.get(key, 0):  # None: this host cannot show it
            lines.append(f"  {label}: {m[key]} (+{m[key] - memo.get(key, 0)})")
    verified = m["script_verifications"]
    if verified["records"] > memo.get("verified", 0):
        lines.append(f"  ShipLoop-run checks: {verified['passed']}/{verified['records']} passed "
                     f"(+{verified['records'] - memo.get('verified', 0)})"
                     # An attempt that never reached a verdict is an environment problem, not a
                     # product one, so it must be visible while the run is still going.
                     + (f"; {verified['could_not_run']} could not run" if verified.get("could_not_run") else ""))
    for item in m["model_glue"][memo.get("glue", 0):]:
        lines.append("  model glue (" + "; ".join(item["reasons"]) + "): " + item["command"][:120])
    for command in m["cancelled_tool_calls"][memo.get("cancelled", 0):]:
        lines.append("  host cancelled a tool call (permission check): " + " ".join(command.split())[:120])
    for session in m["sessions"][memo.get("sessions", 0):]:
        lines.append(f"  session ended: {session['stop']}"
                     + (f" after {session['turns']} turns" if session["turns"] is not None else ""))
    remark = last_remark(out)
    if remark:
        lines.append("  model: " + remark)
    memo_path.write_text(json.dumps({"stages": len([s for s in m["stages"] if not s.get("incomplete")]),
                                     "failures": len(m["shiploop_failures"]),
                                     "sessions": len(m["sessions"]), "cancelled": len(m["cancelled_tool_calls"]),
                                     **{k: m[k] or 0 for k in ("truncated_outputs", "compactions",
                                                               "improve_children")},
                                     "unmeasured": sorted(m["unmeasured"]), "planning": closed,
                                     "verified": m["script_verifications"]["records"],
                                     "glue": len(m["model_glue"])}))
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(report(Path(sys.argv[1]).expanduser().resolve()), flush=True)
