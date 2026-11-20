#!/usr/bin/env python3
"""Build the blind packets the judges read for the reader replay.

For each case the packet holds the end-of-work review's fix (its commit message, its code and test patch, its own
review notes) and the six reviewers' reports under letters A to F in a seeded random order, so a judge cannot tell a
plain reviewer from a lens reviewer by position. The letter-to-slot key is written beside the packets and is not
shown to the judges. Lens reviewers' reports do not name their lens.

Usage: python3 -I replay_judge_packets.py WORK [PACKETS]     (PACKETS: how many files to split into, default 2)
"""
import json
import pathlib
import random
import sys

SEED = 20261120
SLOTS = ("p1", "p2", "p3", "lb", "lt", "ld")


def main(argv):
    work = pathlib.Path(argv[0])
    parts = int(argv[1]) if len(argv) > 1 else 2
    out = work / "replay" / "judge"
    out.mkdir(parents=True, exist_ok=True)
    cases = sorted(p.name for p in (work / "replay" / "out").iterdir() if p.is_dir() and p.name[0] in "cm")
    rng = random.Random(SEED)
    key, blocks = {}, []
    for case in cases:
        order = list(SLOTS)
        rng.shuffle(order)
        key[case] = dict(zip("ABCDEF", order, strict=True))
        truth = work / "key" / case
        block = [f"################ CASE {case} ################", "",
                 "---- The end-of-work review's fix: commit message ----", (truth / "fix-message.txt").read_text().strip(),
                 "", "---- The fix: code and test patch ----", (truth / "fix.patch").read_text().rstrip(), "",
                 "---- The end-of-work reviewer's own notes ----", (truth / "end-review.md").read_text().strip()[:6000], ""]
        for letter, slot in key[case].items():
            report = (work / "replay" / "out" / case / f"{slot}.md").read_text().strip()
            block += [f"======== {case} REPORT {letter} ========", report or "(no report was returned)", ""]
        blocks.append("\n".join(block))
    size = -(-len(blocks) // parts)
    for n in range(parts):
        chunk = blocks[n * size:(n + 1) * size]
        (out / f"packet-{n + 1}.txt").write_text("\n\n".join(chunk) + "\n")
        print(f"packet-{n + 1}.txt: {len(chunk)} cases, {sum(len(c) for c in chunk):,} characters")
    (out / "key.json").write_text(json.dumps(key, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
