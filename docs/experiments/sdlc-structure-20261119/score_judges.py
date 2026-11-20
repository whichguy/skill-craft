#!/usr/bin/env python3
"""Score the two judges' verdicts on what planning reviews changed (judge/out-{A,B}-{1,2}.jsonl against
judge/diff-key.json): verdict shares by reviewed stage, agreement (Cohen's kappa), and the share of ALL reviews
of a stage that made a substantive edit (edit rate from the pass logs x judged substance share)."""
import collections
import json
import pathlib
import sys

J = pathlib.Path(sys.argv[1])
key = {k["item"]: k for k in json.loads((J / "diff-key.json").read_text())}
def load(judge):
    out = {}
    for batch in (1, 2):
        for line in (J / f"out-{judge}-{batch}.jsonl").read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["item"]] = row
    return out
A, B = load("A"), load("B")
items = sorted(set(key) & set(A) & set(B))
print(f"items in key {len(key)}; judged by A {len(A)}; by B {len(B)}; by both {len(items)}")
labels = ["substance", "sharpening", "record", "unclear"]
agree = sum(A[i]["verdict"] == B[i]["verdict"] for i in items) / len(items)
pa = collections.Counter(A[i]["verdict"] for i in items); pb = collections.Counter(B[i]["verdict"] for i in items)
expected = sum(pa[l] * pb[l] for l in labels) / len(items) ** 2
print(f"exact agreement {agree:.0%}; Cohen's kappa {(agree - expected) / (1 - expected):.2f} (four labels)")
bin_a = {i: A[i]["verdict"] == "substance" for i in items}; bin_b = {i: B[i]["verdict"] == "substance" for i in items}
agree2 = sum(bin_a[i] == bin_b[i] for i in items) / len(items)
ya, yb = sum(bin_a.values()) / len(items), sum(bin_b.values()) / len(items)
exp2 = ya * yb + (1 - ya) * (1 - yb)
print(f"substance vs not: agreement {agree2:.0%}; kappa {(agree2 - exp2) / (1 - exp2):.2f}")
print("confusion (rows judge A, columns judge B):")
print(f"{'':<12}" + "".join(f"{l:>12}" for l in labels))
for la in labels:
    print(f"{la:<12}" + "".join(f"{sum(1 for i in items if A[i]['verdict'] == la and B[i]['verdict'] == lb):>12}" for lb in labels))
# edit rates from the pass logs (evidence/review-yield.txt): share of all reviews of the stage that edited anything
EDIT_RATE = {"step-plan": 0.37, "spec": 0.28, "test-strategy": 0.24, "plan": 0.06}
print(f"\n{'reviewed stage':<16}{'judged':>7}{'substance A':>13}{'substance B':>13}{'both':>7}{'either':>8}{'gate (A/B)':>12}"
      f"{'reviews that edit':>19}{'substantive edit per review (both..either)':>44}")
for stage in ("step-plan", "spec", "test-strategy", "plan"):
    group = [i for i in items if key[i]["stage"] == stage]
    n = len(group)
    sa = sum(bin_a[i] for i in group); sb = sum(bin_b[i] for i in group)
    both = sum(bin_a[i] and bin_b[i] for i in group); either = sum(bin_a[i] or bin_b[i] for i in group)
    ga = sum(bool(A[i].get("gate")) for i in group); gb = sum(bool(B[i].get("gate")) for i in group)
    rate = EDIT_RATE[stage]
    print(f"{stage:<16}{n:>7}{sa / n:>13.0%}{sb / n:>13.0%}{both / n:>7.0%}{either / n:>8.0%}{f'{ga}/{gb}':>12}"
          f"{rate:>19.0%}{f'{rate * both / n:.0%} .. {rate * either / n:.0%}':>44}")
print("\nexamples both judges called substance (judge A's reason):")
for stage in ("step-plan", "spec", "test-strategy", "plan"):
    picks = [i for i in items if key[i]["stage"] == stage and bin_a[i] and bin_b[i]][:3]
    for i in picks:
        print(f"  [{stage}] {i}: {A[i]['why']}")
print("\nexamples both judges called sharpening or record:")
for stage in ("step-plan", "spec", "test-strategy", "plan"):
    picks = [i for i in items if key[i]["stage"] == stage and not bin_a[i] and not bin_b[i]][:2]
    for i in picks:
        print(f"  [{stage}] {i}: {A[i]['why']}")
