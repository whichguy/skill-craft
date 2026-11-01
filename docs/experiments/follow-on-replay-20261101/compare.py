"""Compare the readers of the M1 replay and apply the reading fixed before the replay (journal, Round 4).

Readers: ``first`` (Claude Sonnet 5.5: the frozen classification.json for F01..F25 and first-reader-new-rows.json for N1..N7),
``sol-a`` (the second reader, the main comparison), ``sol-b`` (Sol again, reversed class order and another shuffle: its own
noise) and ``grok`` (the third reader, blind to everything else).  Usage: ``python3 -B compare.py [--selftest]``.

Measures (fixed before any reader was called): fine agreement over the seven classes and coarse agreement over the five
groups of classification.json (person+capability, extension+debt, note, decision, gap), for every pair, over all 32 rows and
over the 25 frozen and the 7 new rows; Cohen's kappa on the coarse groups; the gap and decision analyses; a 2-of-3 majority of
first, sol-a and grok.  Nothing here decides a label: the reading rules are printed with the numbers they use.
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
PEEK = HERE.parent / "follow-on-peek-20261031"
FINISHED_RUNS_NOW = 166  # 122 that reached handoff in the 2026-10-31 snapshot + 44 finished since (build_set.py's scan)
FINISHED_RUNS_SNAPSHOT = 122
READERS = ("first", "sol-a", "sol-b", "grok")


def load_first() -> tuple[dict, dict, dict, dict]:
    classification = json.loads((PEEK / "classification.json").read_text(encoding="utf-8"))
    labels, arguable = {}, {}
    for number, entry in enumerate(classification["entries"], 1):
        labels[f"F{number:02d}"] = entry["class"]
        arguable[f"F{number:02d}"] = bool(entry["arguable"])
    for entry in json.loads((HERE / "first-reader-new-rows.json").read_text(encoding="utf-8"))["entries"]:
        labels[entry["id"]] = entry["class"]
        arguable[entry["id"]] = bool(entry["arguable"])
    return labels, arguable, classification["coarse"], classification["classes"]


def load_all() -> tuple[dict, dict, dict, dict, dict]:
    first, arguable, coarse, classes = load_first()
    labels = {"first": first}
    notes = {}
    for name in READERS[1:]:
        path = HERE / "readers" / f"{name}.parsed.json"
        if path.is_file():
            parsed = json.loads(path.read_text(encoding="utf-8"))
            labels[name] = {row: item["class"] for row, item in parsed.items()}
            notes[name] = parsed
    return labels, arguable, coarse, classes, notes


def kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    kinds = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    observed = sum(1 for a, b in pairs if a == b) / n
    expected = sum((sum(1 for a, _ in pairs if a == k) / n) * (sum(1 for _, b in pairs if b == k) / n) for k in kinds)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def agreement(one: dict, two: dict, rows: list[str], coarse: dict | None = None) -> tuple[int, int]:
    pick = (lambda label: coarse[label]) if coarse else (lambda label: label)
    return sum(1 for row in rows if pick(one[row]) == pick(two[row])), len(rows)


def jaccard(one: set, two: set) -> float:
    return 1.0 if not (one | two) else len(one & two) / len(one | two)


def report(labels: dict, arguable: dict, coarse: dict, classes: dict, notes: dict) -> list[str]:
    out = []
    rows = sorted(labels["first"])
    frozen = [row for row in rows if row.startswith("F")]
    new = [row for row in rows if row.startswith("N")]
    present = [name for name in READERS if name in labels]
    out.append(f"rows {len(rows)} ({len(frozen)} frozen, {len(new)} new); readers present: {', '.join(present)}")
    out.append("")
    out.append("== agreement (fine = seven classes; coarse = five groups) ==")
    out.append(f"{'pair':<16}{'fine all':>10}{'fine F':>9}{'fine N':>8}{'coarse all':>12}{'coarse F':>10}{'coarse N':>10}{'kappa(coarse)':>15}")
    for one, two in combinations(present, 2):
        cells = []
        for subset in (rows, frozen, new):
            a, n = agreement(labels[one], labels[two], subset)
            cells.append(f"{a}/{n}")
        for subset in (rows, frozen, new):
            a, n = agreement(labels[one], labels[two], subset, coarse)
            cells.append(f"{a}/{n}")
        k = kappa([(coarse[labels[one][row]], coarse[labels[two][row]]) for row in rows])
        main = "  <- main" if (one, two) == ("first", "sol-a") else ""
        out.append(f"{one + ' vs ' + two:<16}{cells[0]:>10}{cells[1]:>9}{cells[2]:>8}{cells[3]:>12}{cells[4]:>10}{cells[5]:>10}{k:>15.2f}{main}")
    if "sol-a" in labels:
        out.append("")
        out.append("== confusion: first (rows) vs sol-a (columns), seven classes ==")
        order = list(classes)
        out.append(f"{'':<12}" + "".join(f"{name[:5]:>7}" for name in order))
        for left in order:
            out.append(f"{left:<12}" + "".join(f"{sum(1 for row in rows if labels['first'][row] == left and labels['sol-a'][row] == right):>7}" for right in order))
        out.append("")
        out.append("== rows where first and sol-a differ (fine) ==")
        hits = [row for row in rows if labels["first"][row] != labels["sol-a"][row]]
        for row in hits:
            others = "; ".join(f"{name} {labels[name][row]}" for name in present if name not in ("first", "sol-a"))
            alt = notes["sol-a"][row]["alt"]
            out.append(f"{row}: first {labels['first'][row]}{' (arguable)' if arguable[row] else ''} | sol-a {labels['sol-a'][row]}"
                       f"{' (alt ' + alt + ')' if alt else ''} | {others}")
        on_arguable = sum(1 for row in hits if arguable[row])
        out.append(f"{len(hits)} differ; {on_arguable} of them on rows the first reader marked arguable "
                   f"({sum(arguable.values())} of {len(rows)} rows are marked)")
    out.append("")
    out.append("== gap ==")
    gaps = {name: sorted(row for row in rows if labels[name][row] == "gap") for name in present}
    for name in present:
        out.append(f"{name}: {len(gaps[name])} row(s) labelled gap {gaps[name]}")
    second = set(gaps.get("sol-a", [])) | set(gaps.get("sol-b", []))
    confirmed = sorted(row for row in second if "grok" in labels and labels["grok"][row] == "gap")
    out.append(f"labelled gap by a second reader (sol-a or sol-b): {sorted(second)}; also by the third reader (grok): {confirmed}")
    out.append("")
    out.append("== decision ==")
    sets = {name: {row for row in rows if labels[name][row] == "decision"} for name in present}
    for name in present:
        out.append(f"{name}: {len(sets[name])} {sorted(sets[name])}")
    for row in ("F22", "F11"):
        out.append(f"design test row {row}: " + ", ".join(f"{name} {labels[name][row]}" for name in present))
    if "sol-a" in labels:
        out.append(f"jaccard(first, sol-a) = {jaccard(sets['first'], sets['sol-a']):.2f}  (threshold 0.67)")
    for name in ("sol-b", "grok"):
        if name in labels:
            out.append(f"jaccard(first, {name}) = {jaccard(sets['first'], sets[name]):.2f}   (context)")
    if all(name in labels for name in ("sol-a", "grok")):
        out.append("")
        out.append("== 2-of-3 majority (first, sol-a, grok) ==")
        final, unresolved = {}, []
        for row in rows:
            votes = [labels[name][row] for name in ("first", "sol-a", "grok")]
            best = max(set(votes), key=votes.count)
            if votes.count(best) >= 2:
                final[row] = best
            else:
                unresolved.append((row, votes))
        counts = {key: sum(1 for value in final.values() if value == key) for key in classes}
        out.append("final classes: " + ", ".join(f"{key} {counts[key]}" for key in classes) + f"; unresolved {len(unresolved)}")
        for row, votes in unresolved:
            out.append(f"  unresolved {row}: {votes}")
        out.append(f"decision rows after majority: {sorted(row for row, value in final.items() if value == 'decision')}")
        out.append(f"gap rows after majority: {sorted(row for row, value in final.items() if value == 'gap')}")
        n_decision = counts["decision"]
        out.append(f"decision rate over finished runs: first reader {len(sets['first'])} of {FINISHED_RUNS_NOW} "
                   f"({100 * len(sets['first']) / FINISHED_RUNS_NOW:.1f}%); after majority {n_decision} of {FINISHED_RUNS_NOW} "
                   f"({100 * n_decision / FINISHED_RUNS_NOW:.1f}%); the 2026-10-31 snapshot was 3 of {FINISHED_RUNS_SNAPSHOT}")
    out.append("")
    out.append("== predictions written before the run (journal, Round 4) ==")
    if "sol-a" in labels:
        p1 = not gaps["sol-a"]
        a, n = agreement(labels["first"], labels["sol-a"], rows, coarse)
        p2 = a >= 26
        p3 = jaccard(sets["first"], sets["sol-a"]) >= 2 / 3
        hits = [row for row in rows if labels["first"][row] != labels["sol-a"][row]]
        p4 = bool(hits) and 2 * sum(1 for row in hits if arguable[row]) >= len(hits)
        out.append(f"P1 sol-a labels no row gap: {'held' if p1 else 'missed'} ({len(gaps['sol-a'])})")
        out.append(f"P2 coarse agreement first vs sol-a at least 26 of 32: {'held' if p2 else 'missed'} ({a}/{n})")
        out.append(f"P3 jaccard(first, sol-a) on decision at least 0.67: {'held' if p3 else 'missed'} ({jaccard(sets['first'], sets['sol-a']):.2f})")
        out.append(f"P4 at least half of the fine disagreements fall on arguable rows: {'held' if p4 else 'missed'}")
        if "sol-b" in labels:
            a2, n2 = agreement(labels["sol-a"], labels["sol-b"], rows)
            out.append(f"P5 sol-a vs sol-b fine agreement at least 85% (28 of 32): {'held' if a2 >= 28 else 'missed'} ({a2}/{n2})")
    return out


def selftest() -> int:
    first, arguable, coarse, classes = load_first()
    rows = sorted(first)
    assert len(rows) == 32 and sum(1 for r in rows if r.startswith("F")) == 25
    same = {name: dict(first) for name in ("sol-a", "sol-b", "grok")}
    labels = {"first": first, **same}
    notes = {name: {row: {"class": first[row], "alt": None, "reason": ""} for row in rows} for name in same}
    lines = report(labels, arguable, coarse, classes, notes)
    assert any("first vs sol-a" in line and "32/32" in line for line in lines), "identical readers must agree on every row"
    perturbed = dict(first)
    perturbed["F22"] = "extension"
    perturbed["F08"] = "gap"
    labels["sol-a"] = perturbed
    notes["sol-a"] = {row: {"class": perturbed[row], "alt": None, "reason": ""} for row in rows}
    text = "\n".join(report(labels, arguable, coarse, classes, notes))
    assert "sol-a: 1 row(s) labelled gap ['F08']" in text and "jaccard(first, sol-a) = 0.33" in text, text
    assert "30/32" in text
    print("selftest ok: identical readers agree 32/32; two perturbed rows read back as 30/32, one gap, jaccard 0.33")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    print("\n".join(report(*load_all())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
