#!/usr/bin/env python3
"""Score the two judges' labels of what one Grok delivery's reviews changed (round 8).

FOLDER holds key.json (which packet is which: a review of the Grok run, or one of six round-7 packets mixed in as
anchors), out-A.jsonl and out-B.jsonl. ROUND7 is round 7's judge folder, whose labels the anchors are checked against.
A review with no change has no packet and counts as not substantive.

Usage: python3 -I grok_review_score.py FOLDER ROUND7 REVIEWS_IN_THE_RUN
"""
import json
import pathlib
import sys

GROUPS = (("the five reviews round 7 removed", ("spec", "test-strategy", "plan", "step-plan", "system-test-author")),
          ("the step reviews", ("document",)), ("the two end reviews", ("carry-forward", "release-plan")))


def labels(path):
    return {row["packet"]: row for row in (json.loads(line) for line in path.read_text().splitlines() if line.strip())}


def main(folder, round7, reviews):
    folder, round7 = pathlib.Path(folder), pathlib.Path(round7)
    key = json.loads((folder / "key.json").read_text())
    a, b = labels(folder / "out-A.jsonl"), labels(folder / "out-B.jsonl")
    old_a, old_b = labels(round7 / "out-A.jsonl"), labels(round7 / "out-B.jsonl")
    same = sum(a[r["packet"]]["label"] == b[r["packet"]]["label"] for r in key)
    print(f"packets: {len(key)}; the two judges give the same label to {same} of {len(key)}")
    for judge, new in (("A", a), ("B", b)):
        anchors = [r for r in key if r["origin"] != "grok"]
        kept = sum(new[r["packet"]]["label"] == old_a[r["source_packet"]]["label"] == old_b[r["source_packet"]]["label"] for r in anchors)
        print(f"anchors, judge {judge}: {kept} of {len(anchors)} labelled as both of round 7's judges labelled them"
              f"{'' if kept >= 5 else ': FEWER THAN FIVE, so the shares below carry no reading'}")
    print("\nthe Grok delivery's reviews (judge A | judge B):")
    grok = {r["stage"]: r for r in key if r["origin"] == "grok"}
    counted = json.loads(reviews)
    both = {}
    for stage, n in counted.items():
        row = grok.get(stage)
        if not row:
            both[stage] = False
            print(f"  {stage:<20} changed nothing ({n} review{'s' if n != 1 else ''})")
            continue
        la, lb = a[row["packet"]], b[row["packet"]]
        both[stage] = la["label"] == lb["label"] == "substantive"
        print(f"  {stage:<20} {la['label']}/{la.get('scope')} | {lb['label']}/{lb.get('scope')} | {la['reason'][:150]}")
    print("\nby group, substantive by both judges:")
    for name, stages in GROUPS:
        members = [s for s in stages if s in counted]
        hits = sum(both[s] for s in members)
        share = hits / len(members) if members else 0
        word = "earns its place" if share >= 0.30 else "does not" if share <= 0.10 else "no reading"
        print(f"  {name:<34} {hits} of {len(members)} ({share:.0%}): {word}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
