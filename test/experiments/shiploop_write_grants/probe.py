#!/usr/bin/env python3
"""Probe which ShipLoop workspace writes a host's sandbox allows.

Run from inside a host's shell tool with the toy repository as the working
directory. Each probe creates and removes its own artifact and prints one
JSON line, so a transcript is enough evidence.

    python3 probe.py --repo TOY --runs-parent RUNS
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path

HOST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED",
            "CODEX_THREAD_ID", "CODEX_CI", "GROK_AGENT", "GROK_SANDBOX", "GROK_SESSION_ID")


def _file(path: Path) -> str:
    try:
        path.write_text("probe\n")
        path.unlink()
        return "ok"
    except OSError as exc:
        return f"{type(exc).__name__}: {exc.strerror}"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return "ok" if result.returncode == 0 else ("fail: " + (result.stderr.strip().splitlines() or ["?"])[-1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--runs-parent", required=True)
    args = parser.parse_args()
    repo, runs = Path(args.repo).resolve(), Path(args.runs_parent).resolve()
    tag = secrets.token_hex(3)
    common = Path(subprocess.run(["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                 capture_output=True, text=True).stdout.strip())
    rows = {
        "cwd": os.getcwd(),
        "env": {k: os.environ[k] for k in HOST_ENV if k in os.environ},
        "write_repo_worktree_file": _file(repo / f".probe-{tag}"),
        "write_runs_parent_file": _file(runs / f".probe-{tag}"),
        "write_git_common_file": _file(common / f"probe-{tag}"),
    }
    worktree = runs / f"wt-{tag}"
    rows["git_worktree_add"] = _git(repo, "worktree", "add", "-q", "-b", f"probe/{tag}", str(worktree), "HEAD")
    if rows["git_worktree_add"] == "ok":
        rows["write_in_worktree"] = _file(worktree / "f.txt")
        (worktree / "f.txt").write_text("x\n") if rows["write_in_worktree"] == "ok" else None
        rows["git_commit_in_worktree"] = (_git(worktree, "add", "f.txt") == "ok"
                                          and _git(worktree, "-c", "user.name=p", "-c", "user.email=p@p",
                                                   "commit", "-qm", "probe")) or "fail: add"
        _git(repo, "worktree", "remove", "--force", str(worktree))
        _git(repo, "branch", "-D", f"probe/{tag}")
    print("PROBE " + json.dumps(rows, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
