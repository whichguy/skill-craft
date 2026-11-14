#!/usr/bin/env python3
"""Where a whole run's time goes, by what the model was doing, and each inner stage's wall time (round 2 evidence).

    python3 time_split.py <run folder root>        # the folder that holds B-csv-report, T-csv-report, B-shared-expenses, ...

Two tables, no model judging anything:

1. Time by call category. Each host tool call is charged the gap since the previous call ended plus its own duration, so a
   call carries the model's thinking before it. Categories, by the command text: close-out (a call that runs ``shiploop
   check``, the loop's ``done`` or ``shiploop complete``), loop start (the first command of a stage, so it carries the
   model's reading and planning from the stage packet; the call itself takes about a tenth of a second), other ShipLoop calls
   (lint, improve-pass, status, ...), re-reads of a packet or receipt, and everything else (work). Report-writing time moves
   between work and close-out when the wording changes, so compare the total and the shares, not one row.
2. Stage wall time of each done inner stage: from its packet first printed to its accepted ``complete`` (trace rows).
"""
from __future__ import annotations

import collections
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closeout_score as cs  # noqa: E402
import whole_score as ws  # noqa: E402

INNER = ws.INNER
ORDER = ["work (edit, run tests, read code, think)", "close-out (check/report/complete)",
         "other shiploop (lint, improve-pass, ...)", "loop start", "re-read packet or receipt", "shiploop next", "loop next"]


def category(cmd: str) -> str:
    if {v for _, v, _ in ws.commands(cmd)} & {"check", "done", "complete"}:
        return ORDER[1]
    if re.search(r"until_loop_ephemeral\.py['\"]?\s+['\"]?start", cmd):
        return "loop start"
    if re.search(r"until_loop_ephemeral\.py['\"]?\s+['\"]?next", cmd):
        return "loop next"
    if re.search(r"/shiploop['\"]?\s+(lint|improve-pass|status|note|workspace|trace|pause|resume)\b", cmd):
        return ORDER[2]
    if re.search(r"/shiploop['\"]?\s+next\b", cmd):
        return "shiploop next"
    if re.search(r"(packets/|loops/)[^ ]*\.(md|json)", cmd) and re.search(r"\b(sed|cat|head|tail|nl|rg|grep)\b", cmd):
        return ORDER[4]
    return ORDER[0]


def split(root: Path):
    out = {}
    for arm in "BT":
        seconds, calls, total = collections.Counter(), collections.Counter(), 0.0
        for case in ("csv-report", "shared-expenses"):
            ordered = cs.tool_calls(root / f"{arm}-{case}")
            previous_end = ordered[0][0]
            for start, end, command in ordered:
                key = category(command)
                cost = max(end - previous_end, 0)
                previous_end = max(previous_end, end)
                seconds[key] += cost
                calls[key] += 1
                total += cost
        out[arm] = (seconds, calls, total)
    return out


def stage_walls(root: Path):
    walls = {"B": collections.defaultdict(list), "T": collections.defaultdict(list)}
    for arm in "BT":
        for case in ("csv-report", "shared-expenses"):
            trace = next(iter((root / f"{arm}-{case}").glob(".shiploop-runs/*/run/trace.jsonl")))
            first, stage_of, done_at, outcome = {}, {}, {}, {}
            for line in open(trace):
                row = json.loads(line)
                if row.get("kind") == "packet":
                    stage_of.setdefault(row["action"], row["stage"])
                    first.setdefault(row["action"], row["ts"])
                if row.get("kind") == "command" and row["verb"] == "complete" and row.get("exit") == 0:
                    done_at.setdefault(row["action"], row["ts"])
                for item in row.get("accepted") or []:
                    outcome[item["action"]] = item.get("outcome")
            for action, ts in done_at.items():
                if stage_of.get(action) in INNER and outcome.get(action, "done") == "done":
                    walls[arm][stage_of[action]].append(ts - first[action])
    return walls


def main(argv):
    root = Path(argv[0]).expanduser()
    out = split(root)
    print(f"{'category':44} {'B seconds':>10} {'B %':>6} {'B calls':>8} | {'T seconds':>10} {'T %':>6} {'T calls':>8}")
    for key in ORDER:
        b, t = out["B"], out["T"]
        print(f"{key:44} {b[0][key]:10.0f} {100 * b[0][key] / b[2]:5.1f}% {b[1][key]:8d} | "
              f"{t[0][key]:10.0f} {100 * t[0][key] / t[2]:5.1f}% {t[1][key]:8d}")
    print(f"{'total (two runs an arm)':44} {out['B'][2]:10.0f} {'':6} {sum(out['B'][1].values()):8d} | "
          f"{out['T'][2]:10.0f} {'':6} {sum(out['T'][1].values()):8d}")
    print()
    walls = stage_walls(root)
    print(f"{'stage wall seconds':18} {'B n':>4} {'B mean':>7} {'B med':>7} | {'T n':>4} {'T mean':>7} {'T med':>7}")
    pooled = {"B": [], "T": []}
    outside = {"B": [], "T": []}
    for stage in INNER:
        rows = {arm: walls[arm][stage] for arm in "BT"}
        if not (rows["B"] or rows["T"]):
            continue
        for arm in "BT":
            pooled[arm] += rows[arm]
            if stage != "test":
                outside[arm] += rows[arm]

        def fmt(values):
            return f"{statistics.mean(values):7.1f} {statistics.median(values):7.1f}" if values else f"{'-':>7} {'-':>7}"
        print(f"{stage:18} {len(rows['B']):4d} {fmt(rows['B'])} | {len(rows['T']):4d} {fmt(rows['T'])}")
    for label, data in (("all done stages", pooled), ("outside the test stage", outside)):
        print(f"{label:22} {len(data['B']):4d} {statistics.mean(data['B']):7.1f} {statistics.median(data['B']):7.1f} | "
              f"{len(data['T']):4d} {statistics.mean(data['T']):7.1f} {statistics.median(data['T']):7.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
