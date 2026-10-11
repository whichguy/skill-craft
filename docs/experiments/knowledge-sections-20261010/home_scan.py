#!/usr/bin/env python3
"""Read-only scan of the saved E2E knowledge homes for the section notice (batch 1012 task A2).

Repeat with:  python3 docs/experiments/knowledge-sections-20261010/home_scan.py [OUT.json]
(from the repository root; needs the saved runs under /Users/dadleet/e2e-runs, which are only read: no git, no write.)

For every saved home with a docs/shiploop directory it runs ``knowledge_home.section_notices`` at the prepare close (the notice is
the same at every close for the same files) and counts, per file and per heading, how many homes
  - have the file with text,
  - have the heading with a body (present), with nothing under it (empty), or no such heading (missing),
and how many notice lines each home would have printed.  ``either_way_prefix`` counts the homes whose file has a heading that is a
prefix of the table's heading as well (for example "Non-functional" for "Non-functional requirements"), the heading words only,
the body not checked: the delta a looser matching rule would make, for the later decision.  It also lists the headings the saved files really use (levels one to
four, outside code fences), most common first, so a later decision about turning the notice into a refusal can see which words the
models chose instead of the proposed ones.  This is the baseline for the counted-notice measure: nothing here is a threshold.
"""
import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_knowledge_home as k  # noqa: E402

RUNS = "/Users/dadleet/e2e-runs"
MISSING = re.compile(r"^" + re.escape(k.NOTICE_PREFIX) + r"(\S+) has no '([^']+)' section")
EMPTY = re.compile(r"^" + re.escape(k.NOTICE_PREFIX) + r"(\S+) has an empty '([^']+)' section")


def main(out: str) -> None:
    homes, per_home = [], {}
    cell = {name: {heading: collections.Counter() for heading in headings} for name, headings in k.SECTIONS.items()}
    has_file = collections.Counter()
    either_way = {name: collections.Counter() for name in k.SECTIONS}
    used = {name: collections.Counter() for name in k.SECTIONS}
    for work in sorted(glob.glob(RUNS + "/2026*/*/work")):
        if not os.path.isdir(work + "/docs/shiploop"):
            continue
        name = work[len(RUNS) + 1:-len("/work")]
        homes.append(name)
        state = {"repo": work, "prompt": "x", "run_id": "nav-000000"}
        lines = k.section_notices(state, "prepare")
        per_home[name] = len(lines)
        found = {}
        for line in lines:
            hit = MISSING.match(line)
            kind = "missing"
            if not hit:
                hit, kind = EMPTY.match(line), "empty"
            path, heading = hit.group(1), hit.group(2)
            found[(os.path.basename(path), heading)] = kind
        for file, headings in k.SECTIONS.items():
            path = Path(work, k.HOME, file)
            if not k._filled(path):
                continue
            has_file[file] += 1
            text = path.read_text(encoding="utf-8", errors="replace").splitlines()
            titles = [title for _, _, title in k._outline(text)]
            for title in titles:
                used[file][title] += 1
            for heading in headings:
                if any(t.lower().startswith(heading.lower()) or (len(t) >= 4 and heading.lower().startswith(t.lower()))
                       for t in titles):
                    either_way[file][heading] += 1
            for heading in headings:
                cell[file][heading][found.get((file, heading), "present")] += 1
    table = {file: {"homes_with_the_file": has_file[file],
                    "headings": {heading: {**{state: cell[file][heading][state] for state in ("present", "empty", "missing")},
                                           "either_way_prefix": either_way[file][heading]}
                                 for heading in headings},
                    "headings_the_files_use_most": used[file].most_common(25)}
             for file, headings in k.SECTIONS.items()}
    lines_per_home = sorted(per_home.values())
    result = {"homes": len(homes), "table": table, "notice_lines_per_home": per_home,
              "notice_lines_total": sum(lines_per_home),
              "homes_with_no_notice": sum(1 for count in lines_per_home if count == 0),
              "notice_lines_min_median_max": [lines_per_home[0], lines_per_home[len(lines_per_home) // 2], lines_per_home[-1]]}
    Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("homes", len(homes), "| notice lines", result["notice_lines_total"], "| homes with none", result["homes_with_no_notice"])
    for file, row in table.items():
        print(file, "in", row["homes_with_the_file"], "homes")
        for heading, counts in row["headings"].items():
            print("   %-28s present %2d  empty %2d  missing %2d   (either-way prefix: %2d)"
                  % (heading, counts["present"], counts["empty"], counts["missing"], counts["either_way_prefix"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).with_name("home_scan.json")))
