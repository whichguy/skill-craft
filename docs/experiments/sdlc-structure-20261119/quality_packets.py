#!/usr/bin/env python3
"""Build blind packets for a code reading of paired deliveries (round 13).

For each pair (two run folders of one case) and each of two judges, writes a
folder holding: request.txt, base/ (the product before the change, when there
was one), X/ and Y/ (the two delivered products), X.diff and Y.diff (each
against the base). Which run is X is drawn from a seeded generator for judge A
and reversed for judge B. ShipLoop's own knowledge files (docs/shiploop) and
git data are left out, and any path naming a run folder is replaced.
Writes key.json beside the packets; a judge is never shown it.
Usage: python3 -I quality_packets.py <out root> <seed> <name>=<run folder>,<run folder> ...
"""
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

LEFT_OUT = [":(exclude)docs/shiploop"]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def export(repo, rev, dest):
    dest.mkdir(parents=True)
    tar = subprocess.run(["git", "-C", str(repo), "archive", rev], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)
    shutil.rmtree(dest / "docs" / "shiploop", ignore_errors=True)


def scrub(tree, run):
    hits = 0
    for path in tree.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        new = re.sub(r"/[^\s\"'`)]*e2e-runs-[^\s\"'`)]*", "/RUN", text)
        if new != text:
            path.write_text(new); hits += 1
    return hits


def main(argv):
    out, seed = Path(argv[0]), int(argv[1])
    rng = random.Random(seed)
    key = {"seed": seed, "pairs": {}}
    for spec in argv[2:]:
        name, folders = spec.split("=")
        runs = [Path(f) for f in folders.split(",")]
        flip = rng.random() < 0.5
        key["pairs"][name] = {}
        clones = []
        for i, run in enumerate(runs):
            clone = out / "clones" / f"{name}-{i}"
            subprocess.run(["git", "clone", "-q", str(run / "delivery" / "work.bundle"), str(clone)], check=True)
            result = json.load(open(run / "result.json"))
            clones.append((clone, result, run))
        for judge, swapped in (("A", flip), ("B", not flip)):
            order = clones[::-1] if swapped else clones
            packet = out / f"{name}-{judge}"
            packet.mkdir(parents=True)
            prompt = (order[0][2] / "prompt.txt").read_text()
            (packet / "request.txt").write_text(re.sub(r"^/\S+\s+", "", prompt))
            base_head = (order[0][1].get("committed") or {}).get("start_head")
            has_base = bool((order[0][1].get("base") or {}).get("fixture"))
            if has_base:
                export(order[0][0], base_head, packet / "base")
            sides = {}
            for label, (clone, result, run) in zip("XY", order):
                head = result["committed"]["head"]
                # A product built from nothing has no start commit: diff against the empty tree.
                start = result["committed"].get("start_head") or git(clone, "hash-object", "-t", "tree", "/dev/null").strip()
                export(clone, head, packet / label)
                hits = scrub(packet / label, run)
                (packet / f"{label}.diff").write_text(
                    re.sub(r"/[^\s\"'`)]*e2e-runs-[^\s\"'`)]*", "/RUN", git(clone, "diff", start, head, "--", ".", *LEFT_OUT)))
                sides[label] = {"run": str(run), "effort": result.get("effort"), "model": result.get("model"),
                                "head": head, "files_scrubbed": hits}
            key["pairs"][name][judge] = sides
    (out / "key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(key['pairs'])} pairs, {2 * len(key['pairs'])} packets under {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
