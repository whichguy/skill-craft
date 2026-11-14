#!/usr/bin/env python3
"""init-run.py — write manifest.json for a test-harness run (required before suite).

Usage:
  python3 init-run.py --repo <path> --run-dir <path> --cmd <str> \\
    --profile fast|full|unknown --source <src> --mode once|fix-loop \\
    [--rounds-max N] [--assume-fast] [--flag name]...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED = ("repo", "run_dir", "cmd", "profile", "source", "mode")


def main() -> int:
    ap = argparse.ArgumentParser(description="Initialize test-harness run manifest")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--profile", required=True, choices=["fast", "full", "unknown"])
    ap.add_argument(
        "--source",
        required=True,
        choices=["explicit", "doc", "makefile", "package", "path", "agent", "config"],
    )
    ap.add_argument("--mode", required=True, choices=["once", "fix-loop"])
    ap.add_argument("--rounds-max", type=int, default=None)
    ap.add_argument("--assume-fast", action="store_true")
    ap.add_argument("--flag", action="append", default=[], dest="flags")
    ap.add_argument(
        "--suite-scope",
        default="full",
        choices=["full", "subset"],
        help="full release gate vs intentional subset (never confuse with PASS_CLEAN_SCOPED)",
    )
    ap.add_argument(
        "--habitat",
        default="host",
        choices=["host", "container"],
        help="host = porcelain/TMPDIR audit valid; container = FS audit may be unaudited",
    )
    ap.add_argument(
        "--work-root",
        default=None,
        help="suite cwd (defaults to --repo); package identity for nested monorepo runs",
    )
    ap.add_argument(
        "--git-root",
        default=None,
        help="git toplevel (defaults to --repo); used for porcelain Path joins",
    )
    ap.add_argument(
        "--audit-prefix",
        default="",
        help="posix relpath from git_root → work_root when nested; empty when equal",
    )
    args = ap.parse_args()

    repo = str(Path(args.repo).resolve())
    if not Path(repo).is_dir():
        print(json.dumps({"ok": False, "error": "repo_not_dir", "repo": repo}), file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.rounds_max is not None:
        rounds_max = max(1, args.rounds_max)
    else:
        env = os.environ.get("TEST_HARNESS_MAX_ROUNDS", "").strip()
        if env.isdigit() and int(env) > 0:
            rounds_max = int(env)
        else:
            rounds_max = 1 if args.mode == "once" else 5

    flags = list(args.flags or [])
    if args.mode == "once" and "once" not in flags:
        flags.append("once")
    if args.assume_fast and "assume_fast" not in flags:
        flags.append("assume_fast")

    work_root = str(Path(args.work_root).resolve()) if args.work_root else repo
    git_root = str(Path(args.git_root).resolve()) if args.git_root else repo
    audit_prefix = (args.audit_prefix or "").strip().replace("\\", "/").lstrip("/")
    while audit_prefix.endswith("/"):
        audit_prefix = audit_prefix[:-1]
    if audit_prefix == ".":
        audit_prefix = ""

    manifest = {
        "schema_version": 1,
        "repo": work_root,  # suite identity = WORK_ROOT
        "repo_slug": Path(work_root).name,
        "work_root": work_root,
        "git_root": git_root,
        "audit_prefix": audit_prefix,
        "cmd": args.cmd,
        "profile": args.profile,
        "source": args.source,
        "mode": args.mode,
        "rounds_max": rounds_max,
        "assume_fast": bool(args.assume_fast),
        "suite_scope": args.suite_scope,
        "habitat": args.habitat,
        "flags": flags,
        "run_dir": str(run_dir),
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    path = run_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"ok": True, "manifest": str(path), **{k: manifest[k] for k in (
        "repo_slug", "cmd", "profile", "mode", "rounds_max"
    )}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(2)
