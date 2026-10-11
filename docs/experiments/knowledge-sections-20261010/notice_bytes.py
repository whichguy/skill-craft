#!/usr/bin/env python3
"""Bytes of the section notice block a close prints (batch 1012 task A2, the one-line-per-file round).

Repeat with:  python3 docs/experiments/knowledge-sections-20261010/notice_bytes.py [--scripts DIR] [OUT.json]
(from the repository root; the saved runs under /Users/dadleet/e2e-runs are only read.)  ``--scripts`` names the directory that
holds ``shiploop_knowledge_home.py`` (default: this tree); ``git archive <commit> skills/shiploop/scripts`` into a scratch directory
measures an earlier commit with the same script.

The block is what ``section_notices`` returns at a close, printed one line each: the sum of ``len(line.encode()) + 1`` (the newline).
Two figures:
  - ``saved_homes``: the block for every saved home with a docs/shiploop directory, at the home's real path (they are the
    homes ``home_scan.py`` reads), with lines, bytes, and the longest line;
  - ``prose_home``: one synthetic home whose four fact files are prose with no section, at the temporary directory the machine
    gives, and at roots that put the longest file path (``environment.md``) at 137 characters (the longest saved E2E checkout,
    LEARNINGS.md 2026-10-09) and at 212 (the length at which the block of the commit before this round is the "about 8.9 KB at
    a real checkout path" its journal quoted).
"""
import glob
import json
import os
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = "/Users/dadleet/e2e-runs"


def main(argv: list) -> None:
    scripts = ROOT / "skills/shiploop/scripts"
    if "--scripts" in argv:
        at = argv.index("--scripts")
        scripts = Path(argv[at + 1]).resolve()
        del argv[at:at + 2]
    out = argv[0] if argv else str(Path(__file__).with_name("notice_bytes.json"))
    sys.path.insert(0, str(scripts))
    import shiploop_knowledge_home as k

    def block(root: str) -> list:
        return k.section_notices({"repo": root, "prompt": "x", "run_id": "nav-000000"}, "prepare")

    def size(lines: list) -> int:
        return sum(len(line.encode("utf-8")) + 1 for line in lines)

    homes = {}
    for work in sorted(glob.glob(RUNS + "/2026*/*/work")):
        if os.path.isdir(work + "/docs/shiploop"):
            lines = block(work)
            homes[work[len(RUNS) + 1:-len("/work")]] = {"lines": len(lines), "bytes": size(lines),
                                                         "longest_line": max((len(line) for line in lines), default=0)}
    sizes = sorted(row["bytes"] for row in homes.values())
    prose = {}
    base = tempfile.mkdtemp(prefix="notice-bytes-")
    for label, file_path in (("temporary_directory", None), ("environment_md_path_137", 137), ("environment_md_path_212", 212)):
        root = base if file_path is None else base + "/" + "r" * (file_path - len("/docs/shiploop/environment.md") - len(base) - 1)
        for name in k.SECTIONS:
            (Path(root) / k.HOME / name).parent.mkdir(parents=True, exist_ok=True)
            (Path(root) / k.HOME / name).write_text("# " + name + "\n\nProse with no sections.\n", encoding="utf-8")
        lines = block(root)
        prose[label] = {"environment_md_path_chars": len(root + "/docs/shiploop/environment.md"), "lines": len(lines),
                        "bytes": size(lines), "longest_line": max(len(line) for line in lines)}
    result = {"scripts": str(scripts), "saved_homes": {"homes": len(homes), "bytes_min_median_mean_max_total": [
                  sizes[0], sizes[len(sizes) // 2], round(statistics.mean(sizes)), sizes[-1], sum(sizes)],
                  "lines_min_max": [min(r["lines"] for r in homes.values()), max(r["lines"] for r in homes.values())],
                  "per_home": homes},
              "prose_home": prose}
    Path(out).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print("saved homes", len(homes), "bytes min/median/mean/max/total", result["saved_homes"]["bytes_min_median_mean_max_total"])
    for label, row in prose.items():
        print("prose home,", label, row)


if __name__ == "__main__":
    main(sys.argv[1:])
