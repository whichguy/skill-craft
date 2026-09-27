#!/usr/bin/env python3
"""Check a distilled spec mechanically: claims, citations that resolve, leaks.

    spec_check.py SPEC REPO --forbid NAME [--forbid NAME ...]

A citation is `path:line` or `path:start-end` inside an `Evidence:` line; it
resolves when the file exists in REPO and the lines are within it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("repo", type=Path)
    ap.add_argument("--forbid", action="append", default=[])
    args = ap.parse_args()
    text = args.spec.read_text()
    claims = re.findall(r"^\s*(?:[-*]\s*)?\**(D-\d+)\b", text, re.M)
    # Split into claim blocks to see which claims carry evidence.
    blocks = re.split(r"(?m)^(?=\s*(?:[-*]\s*)?\**D-\d+\b)", text)
    no_evidence, bad, good = [], [], 0
    for block in blocks:
        m = re.match(r"\s*(?:[-*]\s*)?\**(D-\d+)", block)
        if not m:
            continue
        cites = re.findall(r"([\w./-]+\.[\w]+):(\d+)(?:-(\d+))?", block)
        if "Evidence" not in block or not cites:
            no_evidence.append(m.group(1))
        for path, start, end in cites:
            f = args.repo / path
            if not f.is_file():
                bad.append(f"{m.group(1)} {path}:{start} (no such file)")
                continue
            n = len(f.read_text(errors="replace").splitlines())
            if int(start) > n or (end and int(end) > n):
                bad.append(f"{m.group(1)} {path}:{start}{'-' + end if end else ''} (file has {n} lines)")
            else:
                good += 1
    leaks = [w for w in args.forbid if re.search(re.escape(w), text, re.I)]
    report = {"claims": len(set(claims)), "claims_without_evidence": no_evidence,
              "citations_resolved": good, "citations_bad": bad, "leaks": leaks,
              "unknowns_section": bool(re.search(r"(?im)^#+\s*\d*\.?\s*unknowns", text))}
    print(json.dumps(report, indent=2))
    return 0 if report["claims"] and not no_evidence and not bad and not leaks else 1


if __name__ == "__main__":
    sys.exit(main())
