#!/usr/bin/env python3
"""resolve-scope.py — single source of truth for package vs monorepo scope.

Usage:
  python3 resolve-scope.py --repo <WORK_ROOT path>
  python3 resolve-scope.py --repo <path> --pretty

Stdout JSON (no trailing notes):
  work_root, git_root (or null), audit_prefix, porc_repo,
  suite_rel (relpath under git worktree for suite cwd; "" when equal),
  slug, nested (bool)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def resolve(work_root: str) -> dict:
    wr = Path(work_root).resolve()
    if not wr.is_dir():
        raise ValueError("not_a_directory")

    r = subprocess.run(
        ["git", "-C", str(wr), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    git_root: str | None
    if r.returncode == 0 and (r.stdout or "").strip():
        git_root = str(Path(r.stdout.strip()).resolve())
    else:
        git_root = None

    audit_prefix = ""
    nested = False
    if git_root and git_root != str(wr):
        rel = os.path.relpath(str(wr), git_root).replace("\\", "/")
        if not rel.startswith(".."):
            audit_prefix = rel if rel != "." else ""
            nested = bool(audit_prefix)

    porc_repo = git_root or str(wr)
    suite_rel = audit_prefix  # under a full-repo worktree, suite cwd is this subpath
    if nested and git_root:
        slug = f"{Path(git_root).name}--{wr.name}"
    else:
        slug = wr.name

    return {
        "work_root": str(wr),
        "git_root": git_root,
        "audit_prefix": audit_prefix,
        "porc_repo": porc_repo,
        "suite_rel": suite_rel,
        "slug": slug,
        "nested": nested,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve WORK_ROOT / GIT_ROOT / AUDIT_PREFIX")
    ap.add_argument("--repo", required=True, help="WORK_ROOT (suite cwd; package path OK)")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()
    try:
        data = resolve(args.repo)
    except ValueError as e:
        print(json.dumps({"error": str(e), "path": args.repo}), file=sys.stderr)
        return 2
    if args.pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
