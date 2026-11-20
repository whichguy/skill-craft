#!/usr/bin/env python3
"""Score two judges' labels of the sampled `learned` lines (judge-learned/lines.jsonl, out-A.jsonl, out-B.jsonl).

Prints the judges' agreement and Cohen's kappa, the share of lines each label gets from both judges and from either,
the same by step position, and three lines of each label that both judges agree on.

Usage: python3 -I learned_score.py judge-learned
"""
import collections
import json
import pathlib
import sys

LABELS = ("forward", "restates", "process", "unclear")


def read(path):
    return {row["id"]: row for row in (json.loads(line) for line in path.read_text().splitlines() if line.strip())}


def main(folder):
    lines = read(folder / "lines.jsonl")
    first, second = read(folder / "out-A.jsonl"), read(folder / "out-B.jsonl")
    ids = sorted(set(lines) & set(first) & set(second))
    pairs = [(first[i]["label"], second[i]["label"]) for i in ids]
    total = len(pairs)
    observed = sum(a == b for a, b in pairs) / total
    expected = sum((sum(a == label for a, _ in pairs) / total) * (sum(b == label for _, b in pairs) / total) for label in LABELS)
    print(f"lines labelled by both judges: {total} of {len(lines)}; same label {observed:.0%}; kappa {(observed - expected) / (1 - expected):.2f}")
    for label in LABELS:
        both = sum(a == label and b == label for a, b in pairs)
        either = sum(label in (a, b) for a, b in pairs)
        print(f"  {label:<9} both judges {both:>3} ({both / total:.0%}); either {either:>3} ({either / total:.0%}); "
              f"judge A {sum(a == label for a, _ in pairs)}, judge B {sum(b == label for _, b in pairs)}")
    by_step = collections.defaultdict(lambda: [0, 0])
    for i, (a, b) in zip(ids, pairs):
        cell = by_step["first step" if lines[i]["step"] == 1 else "later step"]
        cell[0] += a == b == "forward"
        cell[1] += 1
    print("forward by both judges: " + "; ".join(f"{name} {hit} of {count} ({hit / count:.0%})" for name, (hit, count) in sorted(by_step.items())))
    for label in ("forward", "restates", "process"):
        print(f"\nexamples both judges call {label}:")
        shown = 0
        for i, (a, b) in zip(ids, pairs):
            if a == b == label and shown < 3:
                shown += 1
                print(f"  [{lines[i]['case']}] {lines[i]['learned'][:230]}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
