#!/usr/bin/env python3
"""Per-stage health of ShipLoop's stage prompts, read from archived runs' ``RUN/trace.jsonl``.

For each stage: the runs whose trace reaches it, the packets sent for it, the refused callbacks (a script refusal
the model must repair) split into real ``complete`` ones and dry checks (``complete`` with ``check_only``, or the
``check`` verb that replaced it in 8bf10c64), the accepted outcomes other than
``done`` (send-backs and the like), the wall minutes attributed to it (packet to next packet), and the commonest
refusal messages with their numbers and paths stripped. Offline; reads only. Usage:
``python3 stage_health.py [--json OUT]``.
"""
from __future__ import annotations

import argparse
import collections
import glob
import itertools
import json
import os
import re
import statistics
import sys
from pathlib import Path

ROOTS = ("~/e2e-runs", "~/e2e-runs-brownfield", "~/e2e-runs-qr", "~/e2e-runs-x4", "~/e2e-runs-owner-note")
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_stage_spec as stage_spec

ORDER = list(stage_spec.STAGE_SPEC)


def traces() -> list[Path]:
    found = []
    for base in ROOTS:
        for path in glob.glob(os.path.expanduser(base) + "/**/.shiploop-runs/*/run/trace.jsonl", recursive=True):
            if "/test/fixtures/" not in path and "/slice/" not in path:
                found.append(Path(path))
    return sorted(found)


def normalise(message: str) -> str:
    text = re.sub(r"\b(R|C|TC|S|Q|AD|A|E)[-_]?\d+\b", r"\1-n", message)
    text = re.sub(r"[\w./-]*/[\w./-]+", "<path>", text)
    text = re.sub(r"\b\d+(\.\d+)?\b", "n", text)
    return text[:160]


def read(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json")
    args = parser.parse_args()
    reach = collections.Counter()
    packets = collections.Counter()
    refused = collections.Counter()
    checked = collections.Counter()
    outcomes = collections.defaultdict(collections.Counter)
    minutes = collections.defaultdict(list)
    messages = collections.defaultdict(collections.Counter)
    runs_refused = collections.defaultdict(set)
    paths = traces()
    for path in paths:
        rows = read(path)
        seen = set()
        spent = collections.Counter()
        sent = [row for row in rows if row.get("kind") == "packet"]
        for here, after in itertools.pairwise(sent):
            spent[here.get("stage")] += max(0.0, float(after["ts"]) - float(here["ts"])) / 60
        for row in sent:
            packets[row.get("stage")] += 1
            seen.add(row.get("stage"))
        for row in rows:
            if row.get("kind") != "command" or row.get("verb") not in ("complete", "check"):
                continue
            stage = (row.get("stage") or [None])[0]
            if row.get("exit"):
                dry = row.get("check_only") or row.get("verb") == "check"
                (checked if dry else refused)[stage] += 1
                messages[stage][normalise(str(row.get("error") or ""))] += 1
                runs_refused[stage].add(str(path))
            for accepted in row.get("accepted") or ():
                if accepted.get("outcome") and accepted.get("outcome") != "done":
                    outcomes[accepted.get("stage")][accepted["outcome"]] += 1
        for stage in seen:
            reach[stage] += 1
        for stage, value in spent.items():
            minutes[stage].append(value)
    table = []
    for stage in ORDER:
        if not reach[stage]:
            continue
        values = minutes.get(stage) or [0.0]
        table.append({
            "stage": stage, "runs": reach[stage], "packets": packets[stage],
            "refused": refused[stage], "refused_check_only": checked[stage],
            "runs_with_refusal": len(runs_refused[stage]),
            "other_outcomes": dict(outcomes[stage]),
            "median_minutes": round(statistics.median(values), 1), "total_minutes": round(sum(values)),
            "top_refusals": messages[stage].most_common(6),
        })
    print(f"{len(paths)} traced runs")
    print(f"{'stage':20} {'runs':>4} {'pkts':>5} {'ref':>4} {'chk':>4} {'runs_ref':>8} {'med_min':>7} {'tot_min':>7}  other")
    for row in table:
        print(f"{row['stage']:20} {row['runs']:4} {row['packets']:5} {row['refused']:4} {row['refused_check_only']:4} "
              f"{row['runs_with_refusal']:8} {row['median_minutes']:7} {row['total_minutes']:7}  {row['other_outcomes']}")
    for row in table:
        if row["top_refusals"]:
            print("\n" + row["stage"])
            for message, count in row["top_refusals"]:
                print(f"  {count:3}  {message}")
    if args.json:
        Path(args.json).write_text(json.dumps({"runs": len(paths), "stages": table}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
