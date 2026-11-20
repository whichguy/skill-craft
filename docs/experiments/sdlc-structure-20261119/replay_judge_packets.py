#!/usr/bin/env python3
"""Build the blind packets the judges read for the reader replay.

For each case the packet holds the end-of-work review's fix (its commit message, its code and test patch, its own
review notes) and the six reviewers' reports under letters A to F in a seeded random order, so a judge cannot tell a
plain reviewer from a lens reviewer by position. The letter-to-slot key is written beside the packets and is not
shown to the judges. The reports carry no arm label, though a lens report can give its lens away by what it covers.

It also writes reviewers.json: per reviewer its seconds, turns, dollars, tokens, the number of findings in its
report, and what the path audit and the folder manifest showed. OUT is the folder the scorer reads (the
repository's judge-replay folder), so the result can be rescored without the run folders.

Usage: python3 -I replay_judge_packets.py WORK OUT [PACKETS]     (PACKETS: how many files to split into, default 2)
"""
import json
import pathlib
import random
import re
import sys

SEED = 20261120
SLOTS = ("p1", "p2", "p3", "lb", "lt", "ld")


def main(argv):
    work = pathlib.Path(argv[0])
    out = pathlib.Path(argv[1])
    parts = int(argv[2]) if len(argv) > 2 else 2
    out.mkdir(parents=True, exist_ok=True)
    cases = sorted(p.name for p in (work / "replay" / "out").iterdir() if p.is_dir() and p.name[0] in "cm")
    rng = random.Random(SEED)
    key, blocks, reviewers = {}, [], []
    for case in cases:
        drift = json.loads((work / "replay" / "out" / case / "drift.json").read_text())
        for slot in SLOTS:
            record = json.loads((work / "replay" / "out" / case / f"{slot}.json").read_text())
            numbered = sum(1 for line in record["report"].splitlines() if re.match(r"\d+\.\s+file:", line.strip()))
            reviewers.append({
                "case": case, "slot": slot, "seconds": record["seconds"], "turns": record["turns"],
                "cost_usd": record["cost_usd"], "output_tokens": record["output_tokens"],
                "cache_read_tokens": record["cache_read_tokens"], "cache_write_tokens": record["cache_write_tokens"],
                "input_tokens": record["input_tokens"], "served_models": record["served_models"],
                "tool_calls": record["tool_calls"], "findings": numbered, "has_report": bool(record["report"]),
                "timed_out": record["timed_out"], "forbidden_reads": record["forbidden_reads"],
                "paths_elsewhere": record["paths_elsewhere"], "folder_unchanged": drift["unchanged"],
            })
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
    (out / "reviewers.json").write_text(json.dumps(reviewers, indent=1))
    print(f"reviewers.json: {len(reviewers)} reviewers")


if __name__ == "__main__":
    main(sys.argv[1:])
