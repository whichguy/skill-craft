#!/usr/bin/env python3
"""Does a candidate repository carry material logic of its own?

    repo_value.py REPO [--spec SPEC]

A rebuild of a thin layer over other packages mostly re-composes those
packages, so it says little about the builder. This measures, from files:

- own_code_lines: non-blank, non-comment lines of tracked source, excluding
  tests, fixtures, type declarations, configs, docs and build scripts;
- runtime_deps: packages the program needs at run time;
- workspaces: a monorepo or aggregation of packages (disqualifying);
- dependency_evidence_share (with --spec): the share of the spec's citations
  that point into dependency code rather than the repository's own files.

Selection gate (PLAN.md): own_code_lines >= 1000, no workspaces, and, once a
spec exists, dependency_evidence_share <= 0.25.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SOURCE = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|rb|java|kt|swift|vue|svelte)$")
EXCLUDE = re.compile(r"(^|/)(test|tests|__tests__|spec|fixtures?|examples?|docs?|scripts|bench\w*)/"
                     r"|\.(test|spec)\.|\.d\.ts$|(^|/)[^/]*config[^/]*$")
COMMENT = re.compile(r"^\s*(//|#|\*|/\*|\*/)")


def own_code_lines(repo: Path) -> int:
    files = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True,
                           check=True).stdout.splitlines()
    total = 0
    for name in files:
        if SOURCE.search(name) and not EXCLUDE.search(name):
            text = (repo / name).read_text(errors="replace")
            total += sum(1 for line in text.splitlines() if line.strip() and not COMMENT.match(line))
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--spec", type=Path)
    args = ap.parse_args()
    pkg_path = args.repo / "package.json"
    pkg = json.loads(pkg_path.read_text()) if pkg_path.is_file() else {}
    report = {"own_code_lines": own_code_lines(args.repo),
              "runtime_deps": len(pkg.get("dependencies", {})),
              "workspaces": bool(pkg.get("workspaces")) or bool(re.search(
                  r"^packages:\s*\n\s+-", (args.repo / "pnpm-workspace.yaml").read_text(), re.M)
                  if (args.repo / "pnpm-workspace.yaml").is_file() else False)}
    if args.spec:
        cites = re.findall(r"([\w./@-]+\.\w+):\d+", args.spec.read_text())
        dep = [c for c in cites if c.startswith("node_modules/") or (
               not (args.repo / c).is_file()
               and ((args.repo / "node_modules" / c).is_file() or (args.repo / "node_modules" / ("@" + c)).is_file()))]
        report["dependency_evidence_share"] = round(len(dep) / len(cites), 2) if cites else None
    share = report.get("dependency_evidence_share")
    report["material"] = (report["own_code_lines"] >= 1000 and not report["workspaces"]
                          and (share is None or share <= 0.25))
    print(json.dumps(report, indent=2))
    return 0 if report["material"] else 1


if __name__ == "__main__":
    sys.exit(main())
