#!/usr/bin/env python3
"""decompose.py: how much of a fan-out's saving one context could take by overlapping the waits itself (journal E14).

Arithmetic over exported trials, no model call. For each host's write5 pair (A0 one context, A3 fresh workers at S = 30) it splits the
saving into the part that comes from overlapping the slow verification (the settle, a sleep standing for a test run) and the part that
comes from overlapping the model's own work (reading, writing, running), then predicts what one context would take if it started the
settles together (A0 minus (k - 1) settles). Measured A0p cells, when exported, are printed beside the prediction.

  python3 decompose.py [PLAN_TAG]        PLAN_TAG selects the trial family: w5 (write5, default) or an analysis tag such as s30 (E12).

The split assumes equal tasks, a full wave of k workers (capacity limits counted as rounds) and an unchanged task duration in the
fan-out; it is a reading of the registered cells, not a model fitted to them.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import phases  # noqa: E402

EVIDENCE = Path(os.environ.get("PPE_EVIDENCE", HERE / "evidence"))
HOSTS = ("claude", "grok", "codex")


def trial_names(host: str, tag: str) -> dict:
    if tag == "w5":
        return {"A0": f"e13-{host}-w5-a0s", "A3": f"e13-{host}-w5-a3s", "A0p": f"e14-{host}-w5-a0p"}
    return {"A0": f"e12-{host}-{tag}-a0", "A3": f"e12-{host}-{tag}-a3", "A0p": f"e14-{host}-{tag}-a0p"}


def main(argv=None) -> int:
    tag = (argv or sys.argv[1:] or ["w5"])[0]
    print(f"decomposition of the fan-out saving, trial family {tag!r}")
    print("host    S   k  rounds  task_s  model_s  A0 whole  A3 whole  saving  from waits  from model time  implied overhead  predicted A0p  A3 minus A0p  measured A0p")
    for host in HOSTS:
        names = trial_names(host, tag)
        if not (EVIDENCE / names["A0"]).is_dir() or not (EVIDENCE / names["A3"]).is_dir():
            continue
        a0, a3 = phases.split(names["A0"]), phases.split(names["A3"])
        inv = json.loads((EVIDENCE / names["A0"] / "invocation.json").read_text())
        settle = float(inv.get("settle_s") or 0)
        last = max(a0["task_seconds"], key=lambda s: int("".join(c for c in s if c.isdigit()) or 0))
        independent = [v for s, v in a0["task_seconds"].items() if s != last]
        k = len(independent)
        capacity = int(json.loads((EVIDENCE / names["A3"] / "invocation.json").read_text()).get("capacity") or k)
        score_file = EVIDENCE / names["A3"] / "score.json"
        if score_file.is_file():   # the host's own limit shows as the peak the ledger saw (Codex: three workers whatever the kit allows)
            peak = json.loads(score_file.read_text()).get("peak_concurrency")
            capacity = min(capacity, int(peak)) if peak else capacity
        rounds = math.ceil(k / max(1, min(capacity, k)))
        task = sum(independent) / k
        model = task - settle
        saving = a0["whole"] - a3["whole"]
        from_waits = (k - rounds) * settle
        from_model = (k - rounds) * model
        overhead = from_waits + from_model - saving
        predicted = a0["whole"] - (k - 1) * settle
        measured = ""
        if (EVIDENCE / names["A0p"]).is_dir():
            measured = f"{phases.split(names['A0p'])['whole']:.1f}"
        print(f"{host:<7}{settle:>3.0f}{k:>4}{rounds:>7}{task:>9.1f}{model:>9.1f}{a0['whole']:>10.1f}{a3['whole']:>10.1f}{saving:>8.1f}{from_waits:>12.1f}{from_model:>17.1f}"
              f"{overhead:>18.1f}{predicted:>15.1f}{a3['whole'] - predicted:>14.1f}  {measured}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
