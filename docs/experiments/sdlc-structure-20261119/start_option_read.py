#!/usr/bin/env python3
"""Read round 9's card test: what each start-only sample passed in its first start command and what the run recorded.

ROOT holds one folder a sample, made by `run.py --stop-after-start`; the arm is in the folder's name (`-plain-` or
`-card-`), the request too (`-exp-` shared-expenses, `-due-` ticket-due-times).

Usage: python3 -I start_option_read.py ROOT
"""
import json
import pathlib
import re
import sys

OPTION = re.compile(r'"planning_review": "([a-z]+)"')
PASSED = re.compile(r"--planning-review[= ]+([a-z]+)")


def main(root):
    rows = []
    for folder in sorted(p for p in pathlib.Path(root).iterdir() if p.is_dir()):
        arm = "card" if "-card-" in folder.name else "plain"
        case = "shared-expenses" if "-exp-" in folder.name else "ticket-due-times"
        state = next(iter(folder.glob(".shiploop-runs/*/run/state.md")), None)
        recorded = OPTION.search(state.read_text(errors="replace")) if state else None
        first = None
        events = folder / "events.jsonl"
        for line in events.read_text(errors="replace").splitlines() if events.exists() else ():
            if '"rawInput"' in line and "shiploop" in line and ("workspace start" in line or " init " in line):
                passed = PASSED.search(line)
                first = (passed.group(1) if passed else "not passed") + (", with --improve-skill" if "--improve-skill" in line else "")
                break
        result = folder / "result.json"
        route = json.loads(result.read_text()).get("start_route") if result.exists() else None
        rows.append({"name": folder.name, "arm": arm, "case": case, "recorded": recorded.group(1) if recorded else None,
                     "first": first, "route": route})
    print(f"{'sample':<20}{'arm':<7}{'request':<18}{'recorded':<10}{'first start command passed':<34}route")
    for r in rows:
        print(f"{r['name']:<20}{r['arm']:<7}{r['case']:<18}{r['recorded']!s:<10}{r['first']!s:<34}{r['route']}")
    print()
    counts = {}
    for arm in ("plain", "card"):
        group = [r for r in rows if r["arm"] == arm]
        none = [r for r in group if r["recorded"] == "none" or str(r["first"]).startswith("none")]
        counts[arm] = len(none)
        print(f"{arm}: {len(group)} sessions; passed none: {len(none)}; started no run: {sum(r['recorded'] is None for r in group)}; "
              + "; ".join(f"{case} {sum(r['case'] == case for r in none)} of {sum(r['case'] == case for r in group)}"
                          for case in ("shared-expenses", "ticket-due-times")))
    verdict = ("the card stops it" if counts["card"] <= 1 and counts["plain"] >= 4
               else "the test cannot read" if counts["plain"] <= 1 else "no effect shown")
    print(f"\nthe registered reading (the card stops it if at most 1 of its 12 pass none and at least 4 of the 12 plain ones do; "
          f"it cannot read if the plain arm shows 1 or fewer): {verdict}")


if __name__ == "__main__":
    main(sys.argv[1])
