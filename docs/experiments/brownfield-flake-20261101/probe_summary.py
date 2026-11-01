#!/usr/bin/env python3
"""Summarise the flaky-suite probes: python3 probe_summary.py [probe-*.json ...]. Reads only."""
from __future__ import annotations

import collections
import glob
import json
from pathlib import Path
import re
import sys

SCRATCH = Path(__file__).resolve().parent
SIGNATURES = (("socket hang up / ECONNRESET", re.compile(r"socket hang up|ECONNRESET", re.I)),
              ("ECONNREFUSED / EADDRINUSE", re.compile(r"ECONNREFUSED|EADDRINUSE", re.I)),
              ("timeout", re.compile(r"timed out|did not end within|did not listen|timeout|ETIMEDOUT", re.I)),
              ("a held-out check failed", re.compile(r"failed|observed", re.I)))


def signature(text: str) -> str:
    for label, pattern in SIGNATURES:
        if pattern.search(text):
            return label
    return "other"


def main(argv: list[str]) -> int:
    files = argv or sorted(glob.glob(str(SCRATCH / "probe-*.json")))
    print(f"{'probe':8s} {'pool':>4s} {'secs':>6s} {'load':>5s} {'re-graded':>9s}  by kind / by signature")
    for name in files:
        path = Path(name)
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            print(f"{path.stem:8s} (not finished or unreadable)")
            continue
        rows = data["first_pass_disagreements"]
        kinds = collections.Counter(row["kind"] for row in rows)
        sigs = collections.Counter(signature(row["detail"] if isinstance(row["detail"], str) else json.dumps(row["detail"])) for row in rows)
        verdict = "FAILS the cap (4)" if len(data["regraded"]) > 4 else "within the cap"
        print(f"{data['tag'] or path.stem:8s} {data['pool']:4d} {data['seconds']:6.0f} {data['load']:5.1f} {len(data['regraded']):9d}  "
              f"{dict(kinds)} {dict(sigs)} · {verdict}")
        for row in rows:
            detail = row["detail"] if isinstance(row["detail"], str) else json.dumps(row["detail"])
            print(f"   {row['kind']:9s} {row['case']}/{row['variant']}: {re.sub(r'\\s+', ' ', detail)[:230]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
