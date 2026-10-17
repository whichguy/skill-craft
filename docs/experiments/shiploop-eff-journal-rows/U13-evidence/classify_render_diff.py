"""Classify every added and removed line of render_diff.py's output for unit U13 (efficiency plan G-RENDER).

    python3 classify_render_diff.py <diff.md> <old render dir> <new render dir>

A line is one of the classes below, or it sits in a stage whose print form changed between the two renders (a head before, the
whole text now, because the whole text fell under PRINT_LIMIT), where the head's chrome lines and the quoted blocks are moved
into or out of the print and are not changes of text.  Anything else is UNCLASSIFIED and the exit code is 1.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

CLASSES = (
    ("planning-sources", r"^(Current planning sources:|Current accepted root actions below|- (intake|discovery|research|spec|test-strategy|plan): (no current accepted result|RUN/results/))"),
    ("last-accepted summary line", r"^Summary: as the status block's Done line shows\."),
    ("delivery block to anchor lines", r"^(Delivery (consumer|candidate|behavior|necessity|authority|obligations)|For an observation, copy|- [\w-]+ \[(required|optional);)"),
    ("followed entries to IDs (diff below)", r"^(follows \(|- R-\d+|- AD-\d+|  \| |- R-)"),
    ("later steps: id and paths", r"^Later steps \("),
    ("test rules: shapes once", r"^(Base run: before the candidate run|Each focused and regression command must also run|Optional at test:)"),
    ("not_covered label shared", r"^(not_covered \(|- An uncovered behaviour|- not recorded by implement)"),
)


def stage_names(render: Path) -> list[str]:
    """The stage headings render_diff prints for a render, in order: ``stage``, ``stage#2``, ..."""
    seen: Counter = Counter()
    names = []
    for packet in json.loads((render / "manifest.json").read_text())["packets"]:
        seen[packet["stage"]] += 1
        names.append(packet["stage"] + ("#%d" % seen[packet["stage"]] if seen[packet["stage"]] > 1 else ""))
    return names


def flipped(old: Path, new: Path) -> set[str]:
    """The stages whose printed form (head or whole) differs between the two renders."""
    before = {name: packet["head"] for name, packet in zip(stage_names(old), json.loads((old / "manifest.json").read_text())["packets"])}
    after = {name: packet["head"] for name, packet in zip(stage_names(new), json.loads((new / "manifest.json").read_text())["packets"])}
    return {name for name in before if name in after and before[name] != after[name]}


def main(argv: list[str]) -> int:
    diff, old, new = Path(argv[1]), Path(argv[2]), Path(argv[3])
    moved = flipped(old, new)
    totals: Counter = Counter()
    sizes: Counter = Counter()
    unclassified = []
    stage = None
    for line in diff.read_text().splitlines():
        heading = re.match(r"^## (.*)", line)
        if heading:
            stage = heading.group(1)
            continue
        match = re.match(r"^  ([+-])\s+(\d+)\s+\[(\w+)\]\s(.*?)(\s+<- NOT ALLOWLISTED.*)?$", line)
        if not match:
            continue
        sign, size, _where, text = match.group(1), int(match.group(2)), match.group(3), match.group(4)
        label = next((name for name, pattern in CLASSES if re.match(pattern, text)), None)
        if label is None and stage in moved:
            label = "print form changed (head <-> whole): chrome moved in or out of the print"
        if label is None:
            unclassified.append((stage, sign, size, text[:100]))
            continue
        totals[(label, sign)] += 1
        sizes[(label, sign)] += size
    print(f"# {diff.name}: {sum(totals.values())} changed lines classified, {len(unclassified)} unclassified")
    print(f"stages whose print form changed: {', '.join(sorted(moved)) or 'none'}\n")
    print("| class | added lines | added chars | removed lines | removed chars |\n|---|--:|--:|--:|--:|")
    for label in sorted({key[0] for key in totals}):
        print(f"| {label} | {totals[(label, '+')]} | {sizes[(label, '+')]} | {totals[(label, '-')]} | {sizes[(label, '-')]} |")
    for item in unclassified:
        print("UNCLASSIFIED", item)
    return 1 if unclassified else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
