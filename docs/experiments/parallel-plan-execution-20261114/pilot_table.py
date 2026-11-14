#!/usr/bin/env python3
"""pilot_table.py: the pilot's table and its derived overheads, read from the exported score.json files.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A5). Reads evidence/<trial>/score.json and
prints, per host and effort cell, A0 (the parent does every task) against A3 (script-owned ready set, fresh native sub-agents):
the task makespan, the time before the first task, the wait before the dependent task, the whole run, tokens and cost.

  python3 pilot_table.py                 the registered cells and the exploratory default-effort Claude cell
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELLS = [("Claude Sonnet 5.5, high", "r1h-claude-a0", "r1h-claude-a3"), ("Grok 4.6, xhigh", "r1-grok-a0", "r1-grok-a3"),
         ("Codex Sol 6.1, medium", "r1-codex-a0", "r1-codex-a3"),
         ("Claude Sonnet 5.5, default effort (exploratory, not pooled)", "r1-claude-a0", "r1-claude-a3")]


def load(name: str) -> dict:
    return json.loads((HERE / "evidence" / name / "score.json").read_text())


def join_wait(m: dict) -> float | None:
    """Seconds from the last independent task's end to the dependent task's start (the join, from the ledger)."""
    plan = json.loads((HERE / "plans" / "analysis5.json").read_text())
    last = plan["steps"][-1]["id"]
    return None  # filled by ledger below


def ledger(name: str) -> list:
    return [json.loads(line) for line in (HERE / "evidence" / name / "ledger.jsonl").read_text().splitlines()]


def join(name: str) -> float:
    ev = ledger(name)
    ends = [e["ts"] for e in ev if e["kind"] == "end" and e["step"] in ("T1", "T2", "T3", "T4")]
    start5 = next(e["ts"] for e in ev if e["kind"] == "start" and e["step"] == "T5")
    return round(start5 - max(ends), 1)


def fmt(x, nd=1):
    return "n/a" if x is None else (f"{x:,.{nd}f}" if isinstance(x, float) else f"{x:,}")


def main() -> int:
    for label, a0n, a3n in CELLS:
        a0, a3 = load(a0n), load(a3n)
        print(f"\n{label}")
        rows = [("valid, answers correct", f"{a0['valid']}, {a0['answers']['correct']}/5", f"{a3['valid']}, {a3['answers']['correct']}/5"),
                ("agents (native records), peak, ledger peak", "0", f"{a3['native']['agents']}, {a3['native']['peak']}, {a3['peak_concurrency']}"),
                ("independent pairs that overlapped", f"{a0['pairs_overlapped']} of {a0['independent_pairs']}", f"{a3['pairs_overlapped']} of {a3['independent_pairs']}"),
                ("task makespan, first start to last end (s)", fmt(a0["makespan_s"]), fmt(a3["makespan_s"])),
                ("launch to first task start (s)", fmt(a0["timings"]["launch_to_first_start_s"]), fmt(a3["timings"]["launch_to_first_start_s"])),
                ("wait from T1-T4's last end to T5's start (s)", fmt(join(a0n)), fmt(join(a3n))),
                ("whole run, launch to exit (s)", fmt(a0["timings"]["launch_to_exit_s"]), fmt(a3["timings"]["launch_to_exit_s"])),
                ("input tokens, all contexts incl. cache", fmt(a0["tokens"]["input_all"], 0), fmt(a3["tokens"]["input_all"], 0)),
                ("  of which the parent's", fmt(a0["tokens"]["parent_input_all"], 0), fmt(a3["tokens"]["parent_input_all"], 0)),
                ("output tokens", fmt(a0["tokens"]["output_all"], 0), fmt(a3["tokens"]["output_all"], 0)),
                ("cost (USD, where the host reports it)", fmt(a0["tokens"]["cost_usd"], 3), fmt(a3["tokens"]["cost_usd"], 3))]
        w = max(len(r[0]) for r in rows)
        print(f"  {'':<{w}}  {'A0 (parent does all)':>22}  {'A3 (fresh sub-agents)':>22}")
        for r in rows:
            print(f"  {r[0]:<{w}}  {r[1]:>22}  {r[2]:>22}")
        e2e = a3["timings"]["launch_to_exit_s"] / a0["timings"]["launch_to_exit_s"]
        mk = a3["makespan_s"] / a0["makespan_s"]
        tok = a3["tokens"]["input_all"] / a0["tokens"]["input_all"]
        print(f"  A3 against A0: task makespan {mk:.2f}x, whole run {e2e:.2f}x, input tokens {tok:.2f}x"
              + (f", cost {a3['tokens']['cost_usd'] / a0['tokens']['cost_usd']:.2f}x" if a3["tokens"]["cost_usd"] and a0["tokens"]["cost_usd"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
