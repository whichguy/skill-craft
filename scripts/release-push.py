#!/usr/bin/env python3
"""Check a frozen, clean release candidate and push it without force.

Qualification commands are operator-selected argv arrays, not shell programs.
This is a publication guard, not a replacement for reviews or server-side rules.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


class ReleaseError(Exception):
    pass


def run(argv, *, cwd, timeout=120):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ReleaseError(f"command failed ({result.returncode}): {argv[0]}\n{result.stderr.strip()}")
    return result.stdout.strip()


def git(repo, *args):
    return run(["git", *args], cwd=repo)


def local_identity(repo, head, tree):
    if git(repo, "rev-parse", "HEAD") != head:
        raise ReleaseError("candidate HEAD does not match --expected-head")
    if git(repo, "rev-parse", "HEAD^{tree}") != tree:
        raise ReleaseError("candidate tree does not match --expected-tree")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseError("candidate checkout must be clean, including untracked files")


def remote_identity(repo, remote, branch, expected_base):
    urls = git(repo, "remote", "get-url", "--push", "--all", remote).splitlines()
    if len(urls) != 1:
        raise ReleaseError("release remote must have exactly one push URL")
    url = urls[0]
    refs = git(repo, "ls-remote", "--exit-code", url, f"refs/heads/{branch}").splitlines()
    if refs != [f"{expected_base}\trefs/heads/{branch}"]:
        raise ReleaseError("remote branch moved or differs from --expected-base")
    return url


def publish(args):
    # Git context overrides could make the explicit repository identity misleading.
    forbidden = {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_NAMESPACE", "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE"}
    overrides = sorted(key for key in os.environ if key in forbidden or key.startswith("GIT_CONFIG"))
    if overrides:
        raise ReleaseError("remove Git context overrides: " + ", ".join(overrides))
    repo = Path(args.repo).resolve(strict=True)
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ReleaseError("--repo must name the repository worktree root")
    for name in ("expected_head", "expected_tree", "expected_base"):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", getattr(args, name)):
            raise ReleaseError(f"--{name.replace('_', '-')} must be a full object ID")
    git(repo, "check-ref-format", f"refs/heads/{args.branch}")
    checks = []
    for raw in args.check:
        check = json.loads(raw)
        if not isinstance(check, list) or not check or any(not isinstance(v, str) or not v for v in check):
            raise ReleaseError("each --check must be a nonempty JSON argv array of nonempty strings")
        checks.append(check)
    local_identity(repo, args.expected_head, args.expected_tree)
    url = remote_identity(repo, args.remote, args.branch, args.expected_base)
    git(repo, "merge-base", "--is-ancestor", args.expected_base, args.expected_head)
    for number, check in enumerate(checks, 1):
        print(f"release check {number}/{len(checks)}: {json.dumps(check)}", file=sys.stderr, flush=True)
        result = subprocess.run(check, cwd=repo, timeout=args.check_timeout, stdout=sys.stderr)
        if result.returncode:
            raise ReleaseError(f"release check {number} failed ({result.returncode}); no push attempted")
        local_identity(repo, args.expected_head, args.expected_tree)
    if remote_identity(repo, args.remote, args.branch, args.expected_base) != url:
        raise ReleaseError("release push URL changed during checks")
    local_identity(repo, args.expected_head, args.expected_tree)
    # Push the frozen object, not a movable branch/HEAD; never use '+' or --force.
    # Server rules still apply. A racing divergent update is rejected by Git.
    receipt = git(repo, "-c", "push.followTags=false", "push", "--porcelain",
                  url, f"{args.expected_head}:refs/heads/{args.branch}")
    return {"status": "pushed", "head": args.expected_head, "tree": args.expected_tree,
            "previous_remote_head": args.expected_base, "branch": args.branch,
            "checks_passed": len(checks), "push_receipt": receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-base", required=True)
    parser.add_argument("--check", action="append", required=True, help="JSON argv array; repeat for multiple checks")
    parser.add_argument("--check-timeout", type=float, default=1800)
    args = parser.parse_args()
    try:
        if args.check_timeout <= 0:
            raise ReleaseError("--check-timeout must be positive")
        print(json.dumps(publish(args), sort_keys=True))
        return 0
    except (ReleaseError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
