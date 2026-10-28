#!/usr/bin/env python3
"""Measure a baseline knowledge home (experiment X2): sizes, entry counts, source classes, links, and check C1.

    python3 summarize.py NAME=REPO [NAME=REPO ...] [--json OUT]

REPO is a checkout whose docs/shiploop/ holds a baseline.  Prints one row per baseline.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baseline_check as check  # noqa: E402

CLASSES = ("documented", "tested", "observed", "inferred", "conflict")


def measure(name: str, repo: Path) -> dict:
    home = repo / check.HOME
    spec = (home / "spec.md").read_text(errors="replace") if (home / "spec.md").is_file() else ""
    arch = (home / "architecture.md").read_text(errors="replace") if (home / "architecture.md").is_file() else ""
    reqs = check.knowledge._entries(spec, "R")
    decisions = check.knowledge._entries(arch, "AD")
    classes = collections.Counter()
    for entry in reqs.values():
        source = re.search(r"Source:(.*?)(?:·|$)", entry.text, re.M)
        for cls in CLASSES:
            if source and re.search(r"\b" + cls + r"\b", source.group(1)):
                classes[cls] += 1
    linked = sum(1 for entry in decisions.values() if re.search(r"stated:\s*`?[^`]*(adr|decision)", entry.text, re.I))
    bullets = sum(len(re.findall(r"^\s*- ", entry.text, re.M)) for entry in reqs.values())
    coverage = re.search(r"^Baseline coverage:.*$", spec, re.M)
    sources = check.sources(repo)
    return {
        "name": name, "spec_bytes": len(spec.encode()), "architecture_bytes": len(arch.encode()),
        "requirements": len(reqs), "bullets": bullets, "decisions": len(decisions),
        "inherited": sum("(inherited" in e.text.splitlines()[0] for e in decisions.values()),
        "superseded": sum(e.retired for e in decisions.values()), "linked_records": linked,
        "source_classes": dict(classes), "coverage_line": coverage.group(0) if coverage else None,
        "c1": sources["stats"], "c1_findings": len(sources["findings"]),
        "c1_examples": sources["findings"][:8],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pairs", nargs="+")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    rows = [measure(*pair.split("=", 1)[0:1], Path(pair.split("=", 1)[1])) for pair in args.pairs]
    for row in rows:
        stats = row["c1"]
        print(f"{row['name']}: spec {row['spec_bytes']} B, architecture {row['architecture_bytes']} B; "
              f"R {row['requirements']} ({row['bullets']} bullets), AD {row['decisions']} "
              f"({row['inherited']} inherited, {row['superseded']} superseded, {row['linked_records']} linking records); "
              f"classes {row['source_classes']}; C1 locators {stats['resolved']}/{stats['locators']} resolve, "
              f"{stats['with_locator']}/{stats['entries']} entries anchored, {row['c1_findings']} findings")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
