#!/usr/bin/env python3
"""Describe the second-reader test's judged items by their place in a list (journal section 63). No model is called.

Reads the evidence folder of the test (key.json, judge-key.json, the two judged files) and prints, for each place
among the five items shown: how many items both judges class `new`, how many one judge does, how many neither; the
pairs of classes the two judges gave; and the class each judge gave to the items they placed as the two described
decisions. This is a description made after the registered score, not one of its readings.

Usage: second_reader_places.py [EVIDENCE_FOLDER] > evidence/second-reader/places.txt
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL = ("final", "latest")


def main() -> int:
    """Print the three descriptions."""
    folder = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "evidence" / "second-reader"
    )
    key = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    lists = json.loads((folder / "judge-key.json").read_text(encoding="utf-8"))["lists"]
    judged = {
        name: json.loads((folder / f"judged-{name}.json").read_text(encoding="utf-8"))[
            "verdicts"
        ]
        for name in ("opus", "astra")
    }
    info = {code: key[name.rsplit("-r", 1)[0]] for code, name in lists.items()}
    sets = (
        (
            "due times, the set the rule reads",
            lambda i: i["case"] == "due" and i["wording"] in FINAL,
        ),
        ("due times, every list", lambda i: i["case"] == "due"),
        ("hello, every list", lambda i: i["case"] == "hello"),
    )
    for label, pick in sets:
        rows: dict[int, list[int]] = collections.defaultdict(lambda: [0, 0, 0, 0])
        for code, one in info.items():
            if not pick(one):
                continue
            pairs = zip(
                judged["opus"][code]["classes"],
                judged["astra"][code]["classes"],
                strict=True,
            )
            for place, (first, second) in enumerate(pairs, 1):
                rows[place][0] += 1
                rows[place][
                    1
                    if first == second == "new"
                    else 2
                    if "new" in (first, second)
                    else 3
                ] += 1
        print(f"{label}: place, items, `new` by both judges, by one, by neither")
        for place in sorted(rows):
            items, both, one_judge, neither = rows[place]
            print(f"   {place}  {items:3d}  {both:3d}  {one_judge:3d}  {neither:3d}")
        print()
    pairs_seen: collections.Counter = collections.Counter()
    for code in info:
        pairs_seen.update(
            zip(
                judged["opus"][code]["classes"],
                judged["astra"][code]["classes"],
                strict=True,
            )
        )
    print("pairs of classes over all shown items (opus, astra): count")
    for (first, second), count in sorted(
        pairs_seen.items(), key=lambda pair: (-pair[1], pair[0])
    ):
        print(f"   {first:9s} {second:9s} {count:3d}")
    print()
    for field in ("way_back", "refusal"):
        seen: collections.Counter = collections.Counter()
        for code in info:
            place = judged["opus"][code][field]
            if place and place == judged["astra"][code][field]:
                seen[
                    (
                        judged["opus"][code]["classes"][place - 1],
                        judged["astra"][code]["classes"][place - 1],
                    )
                ] += 1
        print(
            f"class of the item both judges place as `{field}` (opus, astra): {dict(seen)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
