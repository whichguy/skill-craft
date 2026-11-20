#!/usr/bin/env python3
"""Score the reader replay from the judges' verdicts.

Reads, in the folder given: key.json (which letter was which reviewer), out-A-*.jsonl and out-B-*.jsonl (one judge
verdict per report: caught, near or missed), reviewers.json (seconds, dollars, findings, audit) and cases.json.
A report counts as caught only when both judges say caught; the either-judge count is printed beside it.

Usage: python3 -I replay_score.py JUDGE_FOLDER
"""
import collections
import json
import math
import pathlib
import re
import statistics
import sys

PLAIN = ("p1", "p2", "p3")
LENS = ("lb", "lt", "ld")
NAMES = {"lb": "behaviour", "lt": "tests", "ld": "documents and craft"}
OTHER_OUTCOME = re.compile(r"reject|opposite|bound(ing)? |rather than (lift|accept|preserv)|instead of accept", re.IGNORECASE)


def wilson(k, n):
    if not n:
        return 0.0, 0.0
    z = 1.96
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def kappa(pairs):
    labels = sorted({x for pair in pairs for x in pair})
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    expected = sum((sum(a == label for a, _ in pairs) / n) * (sum(b == label for _, b in pairs) / n) for label in labels)
    return observed, (observed - expected) / (1 - expected) if expected < 1 else 1.0


def sign_test(wins, losses):
    """Two-sided exact binomial p for wins against losses at one half."""
    n = wins + losses
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main(folder):
    key = json.loads((folder / "key.json").read_text())
    cases = {c["id"]: c for c in json.loads((folder / "cases.json").read_text())}
    reviewers = {(r["case"], r["slot"]): r for r in json.loads((folder / "reviewers.json").read_text())}
    verdict = {"A": {}, "B": {}}
    why = {"A": {}, "B": {}}
    for judge, seen in verdict.items():
        for path in sorted(folder.glob(f"out-{judge}-*.jsonl")):
            for line in path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    seen[(row["case"], key[row["case"]][row["report"]])] = row["verdict"]
                    why[judge][(row["case"], key[row["case"]][row["report"]])] = row.get("why") or ""
    ids = sorted(key)
    slots = PLAIN + LENS
    missing = [(c, s, j) for c in ids for s in slots for j in verdict if (c, s) not in verdict[j]]
    print(f"cases {len(ids)}; reports {len(ids) * len(slots)}; verdicts missing {len(missing)}")
    pairs = [(verdict["A"][(c, s)], verdict["B"][(c, s)]) for c in ids for s in slots]
    agree, k3 = kappa(pairs)
    agree2, k2 = kappa([(a == "caught", b == "caught") for a, b in pairs])
    print(f"judges agree on {agree:.0%} of reports (kappa {k3:.2f}); on caught against not caught {agree2:.0%} (kappa {k2:.2f})")
    print("verdicts, judge A / judge B:", dict(collections.Counter(a for a, _ in pairs)), "/",
          dict(collections.Counter(b for _, b in pairs)))

    def both(c, s):
        return verdict["A"][(c, s)] == "caught" and verdict["B"][(c, s)] == "caught"

    def either(c, s):
        return "caught" in (verdict["A"][(c, s)], verdict["B"][(c, s)])

    for label, hit in (("both judges (registered)", both), ("either judge", either)):
        plain_reports = sum(hit(c, s) for c in ids for s in PLAIN)
        lens_reports = sum(hit(c, s) for c in ids for s in LENS)
        m2 = [c for c in ids if any(hit(c, s) for s in PLAIN)]
        m3 = [c for c in ids if any(hit(c, s) for s in LENS)]
        all_six = [c for c in ids if any(hit(c, s) for s in slots)]
        low, high = wilson(plain_reports, len(ids) * 3)
        print(f"\n== caught, counted when {label} say caught ==")
        print(f"M1 one plain reader: {plain_reports} of {len(ids) * 3} reports ({plain_reports / (len(ids) * 3):.0%}, "
              f"95% interval {low:.0%} to {high:.0%})")
        print(f"M2 three plain readers: {len(m2)} of {len(ids)} cases ({len(m2) / len(ids):.0%})")
        print(f"M3 three lens readers:  {len(m3)} of {len(ids)} cases ({len(m3) / len(ids):.0%})")
        only_lens = sorted(set(m3) - set(m2))
        only_plain = sorted(set(m2) - set(m3))
        print(f"   M3 minus M2: {len(m3) - len(m2):+d} cases; lens only {only_lens}; plain only {only_plain}; "
              f"sign test p {sign_test(len(only_lens), len(only_plain)):.2f}")
        print(f"   M2 minus M1: {len(m2) / len(ids) - plain_reports / (len(ids) * 3):+.0%} points")
        print(f"   lens reports that caught: {lens_reports} of {len(ids) * 3}; any of the six readers: {len(all_six)} of {len(ids)}")
        for slot in LENS:
            got = [c for c in ids if hit(c, slot)]
            print(f"   lens {NAMES[slot]:<20} {len(got):>2} of {len(ids)}  {got}")
        for draw in PLAIN:
            print(f"   plain draw {draw:<15} {sum(hit(c, draw) for c in ids):>2} of {len(ids)}")
        for group, name in (("c", "items of one step"), ("m", "longer items")):
            sub = [c for c in ids if c.startswith(group)]
            print(f"   {name}: plain reports {sum(hit(c, s) for c in sub for s in PLAIN)} of {len(sub) * 3}; three plain "
                  f"{sum(any(hit(c, s) for s in PLAIN) for c in sub)} of {len(sub)}; three lens "
                  f"{sum(any(hit(c, s) for s in LENS) for c in sub)} of {len(sub)}")
    near = [(c, s) for c in ids for s in slots
            if "near" in (verdict["A"][(c, s)], verdict["B"][(c, s)]) and not either(c, s)]
    print(f"\nreports a judge called near and neither called caught: {len(near)}")

    def noticed(c, s):
        return verdict["A"][(c, s)] != "missed" and verdict["B"][(c, s)] != "missed"

    print("\n== exploratory, not registered: the reader had the same behaviour in hand (both judges say caught or near) ==")
    print(f"plain reports {sum(noticed(c, s) for c in ids for s in PLAIN)} of {len(ids) * 3}; lens reports "
          f"{sum(noticed(c, s) for c in ids for s in LENS)} of {len(ids) * 3}")
    print(f"cases: any of three plain {sum(any(noticed(c, s) for s in PLAIN) for c in ids)} of {len(ids)}; any of three lens "
          f"{sum(any(noticed(c, s) for s in LENS) for c in ids)} of {len(ids)}; any of the six "
          f"{sum(any(noticed(c, s) for s in slots) for c in ids)} of {len(ids)}; the behaviour lens alone "
          f"{sum(noticed(c, 'lb') for c in ids)} of {len(ids)}")
    other = [(c, s) for c, s in near if OTHER_OUTCOME.search(why["A"][(c, s)]) and OTHER_OUTCOME.search(why["B"][(c, s)])]
    print(f"near reports where both judges' sentences say the reader argued for another outcome (reject or bound the "
          f"input, or call the rejection correct): {len(other)} of {len(near)}, in cases {sorted({c for c, _ in other})}")
    print(f"\n{'case':<5}{'example':<19}{'fix':<50}" + "".join(f"{s:>5}" for s in slots))
    for c in ids:
        marks = "".join(f"{('yes' if both(c, s) else 'one' if either(c, s) else '.'):>5}" for s in slots)
        print(f"{c:<5}{cases[c]['case']:<19}{cases[c]['fix_subject'][:48]:<50}{marks}")
    print("(yes: both judges say caught; one: one judge; .: neither)")
    print("\n== cost and conduct ==")
    for name, group in (("plain", PLAIN), ("lens", LENS)):
        rows = [reviewers[(c, s)] for c in ids for s in group]
        print(f"{name:<6} per reader: median {statistics.median(r['seconds'] for r in rows):.0f} s, "
              f"${statistics.median(r['cost_usd'] or 0 for r in rows):.2f}, {statistics.median(r['turns'] or 0 for r in rows):.0f} turns, "
              f"{statistics.median(r['findings'] for r in rows):.0f} findings; total ${sum(r['cost_usd'] or 0 for r in rows):.2f}, "
              f"{sum(r['findings'] for r in rows)} findings in {len(rows)} reports")
    everyone = list(reviewers.values())
    per_case = collections.defaultdict(list)
    for (c, _), r in reviewers.items():
        per_case[c].append(r["seconds"])
    print(f"all {len(everyone)} readers: ${sum(r['cost_usd'] or 0 for r in everyone):.2f}; no report {sum(not r['has_report'] for r in everyone)}; "
          f"timed out {sum(r['timed_out'] for r in everyone)}; served models "
          f"{sorted({m for r in everyone for m in r['served_models']})}")
    print(f"one case's six readers, slowest reader: median {statistics.median(max(v) for v in per_case.values()):.0f} s; "
          f"sum of the six: median {statistics.median(sum(v) for v in per_case.values()):.0f} s")
    print(f"shared case folder unchanged after its six readers: {sum(r['folder_unchanged'] for r in everyone) // 6} of {len(ids)} cases")
    flagged = sorted((r["case"], r["slot"]) for r in everyone if r["forbidden_reads"])
    print(f"readers the path audit flagged for a path under another reader's or case's folder: {flagged}; "
          f"readers that named another path outside their two folders: {sum(bool(r['paths_elsewhere']) for r in everyone)}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
