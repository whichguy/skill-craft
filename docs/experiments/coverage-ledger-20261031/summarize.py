#!/usr/bin/env python3
"""Join ledger.json with classification.json and print the tallies the README reports.

Refuses (exit 1) when a `none` row has no classification or a classification names a row the ledger does not hold, so
a rerun of ledger.py that changes the gap set cannot pass with a stale hand classification.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ledger = json.loads((HERE / "ledger.json").read_text())
    classified = {(row["run"], row["requirement"]): row for row in json.loads(
        (HERE / "classification.json").read_text())["rows"]}
    runs = [entry for entry in ledger if "error" not in entry and not entry["spec"].get("error")]
    errors = [entry for entry in ledger if "error" in entry]
    unbaselined = [entry for entry in ledger if "error" not in entry and entry["spec"].get("error")]
    ends = collections.Counter(row["end"] for entry in runs for row in entry["rows"])
    primary = collections.Counter(row["end"] for entry in runs for row in entry["rows"] if row["primary"])
    none = [(entry["run"], row["requirement"]) for entry in runs for row in entry["rows"] if row["end"] == "none"]
    missing = [key for key in none if key not in classified]
    stale = [key for key in classified if key not in set(none)]
    categories = collections.Counter(classified[key]["category"] for key in none if key in classified)
    not_covered = sum(len(entry["not_covered"]) for entry in runs)
    nc_runs = sum(1 for entry in runs if entry["not_covered"])
    print(f"archived runs that reached product-acceptance: {len(ledger)}; with a run baseline: {len(runs)}; "
          f"without (before the knowledge-home baseline): {len(unbaselined)}; unreadable: {len(errors)}")
    print(f"requirements added or changed: {sum(ends.values())} (primary {sum(primary.values())})")
    for end in ("inner", "inner-criterion", "system", "unverified", "case-unseen", "none"):
        print(f"  {end:16} {ends.get(end, 0):4}   primary {primary.get(end, 0):4}")
    print("none, by hand category:")
    for category, count in categories.most_common():
        print(f"  {category:22} {count:3}")
    cases = sum(entry["test_cases"] for entry in runs)
    multi = sum(entry["multi_field_cases"] for entry in runs)
    print(f"test-spec cases: {cases}; whose requirement field names two or more IDs: {multi}")
    print(f"not_covered rows: {not_covered} in {nc_runs} runs")
    if missing or stale:
        print("classification out of date: unclassified", missing, "stale", stale)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
