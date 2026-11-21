#!/usr/bin/env python3
"""Score the two judges' labels of what the removed reviews changed (round 7).

FOLDER holds key.json (removed_review_diffs.py), out-A.jsonl and out-B.jsonl: one line per packet with `label`
(substantive, wording, records) and, for substantive, `scope` (within, beyond, unclear). A review with no change
has no packet and counts as not substantive.

Usage: python3 -I removed_review_score.py FOLDER
"""
import collections
import json
import pathlib
import sys


def labels(path):
    return {row["packet"]: row for row in (json.loads(line) for line in path.read_text().splitlines() if line.strip())}


def main(folder):
    folder = pathlib.Path(folder)
    key = json.loads((folder / "key.json").read_text())
    a, b = labels(folder / "out-A.jsonl"), labels(folder / "out-B.jsonl")
    packets = [row["packet"] for row in key if row["packet"]]
    same = sum(a[n]["label"] == b[n]["label"] for n in packets)
    counts_a, counts_b = collections.Counter(a[n]["label"] for n in packets), collections.Counter(b[n]["label"] for n in packets)
    expected = sum(counts_a[label] * counts_b[label] for label in set(counts_a) | set(counts_b)) / (len(packets) ** 2) if packets else 0
    kappa = (same / len(packets) - expected) / (1 - expected) if packets and expected < 1 else float("nan")
    print(f"reviews of the removed stages: {len(key)}; with a change (a packet): {len(packets)}; the judges give the same label to "
          f"{same} of {len(packets)}; kappa {kappa:.2f}")
    print(f"labels, judge A: {dict(counts_a)}; judge B: {dict(counts_b)}")
    cells = collections.defaultdict(list)
    for row in key:
        cells[(row["driver"], row["stage"])].append(row)
        cells[(row["driver"], "all removed stages")].append(row)

    def both(row):
        n = row["packet"]
        return bool(n) and a[n]["label"] == "substantive" and b[n]["label"] == "substantive"

    def either(row):
        n = row["packet"]
        return bool(n) and "substantive" in (a[n]["label"], b[n]["label"])

    def scope(row, wanted):
        n = row["packet"]
        return both(row) and a[n].get("scope") == wanted and b[n].get("scope") == wanted

    print(f"\n{'driver':<26}{'reviewed stage':<22}{'reviews':>8}{'changed':>9}{'substantive, both':>19}{'either':>8}{'within, both':>14}{'beyond, both':>14}")
    order = ("spec", "test-strategy", "plan", "step-plan", "system-test-author", "all removed stages")
    for driver in sorted({d for d, _ in cells}):
        for stage in order:
            group = cells.get((driver, stage))
            if not group:
                continue
            n_both = sum(both(r) for r in group)
            print(f"{driver:<26}{stage:<22}{len(group):>8}{sum(bool(r['packet']) for r in group):>9}"
                  f"{f'{n_both} ({n_both / len(group):.0%})':>19}{sum(either(r) for r in group):>8}"
                  f"{sum(scope(r, 'within') for r in group):>14}{sum(scope(r, 'beyond') for r in group):>14}")
    print("\nper packet (judge A | judge B):")
    for row in key:
        n = row["packet"]
        if n:
            print(f"  {n:>3} {row['driver']:<24}{row['stage']:<20}{row['folder']:<30} {a[n]['label']}/{a[n].get('scope')} | "
                  f"{b[n]['label']}/{b[n].get('scope')} | {a[n].get('reason', '')[:110]}")


if __name__ == "__main__":
    main(sys.argv[1])
