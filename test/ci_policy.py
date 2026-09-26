#!/usr/bin/env python3
"""CI tier selection (quick for ordinary changes, full for releases) and exact-checkout guards."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

FULL_GROUPS = ["core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus"]


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root).decode("utf-8", "surrogateescape").strip()


RELEASE_TRAILER = "Skill-Craft-Release:"
ZERO_SHA = "0" * 40


def commit_exists(root, rev):
    if not rev or rev == ZERO_SHA:
        return False
    return subprocess.run(["git", "cat-file", "-e", f"{rev}^{{commit}}"], cwd=root,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def is_release(root, rev="HEAD"):
    """A release commit (scripts/release.py) carries the Skill-Craft-Release trailer."""
    body = git(root, "log", "-1", "--format=%B", rev)
    return any(line.startswith(RELEASE_TRAILER) for line in body.splitlines())


def parent(root):
    return git(root, "rev-parse", "HEAD^1") if commit_exists(root, "HEAD^1") else ""


def select(root, event_name, event, requested):
    """Return (tier, reason, base).  Quick runs the suites matching base..HEAD; full ignores base.

    Ordinary pushes and pull requests run quick.  Only release commits and an
    explicit manual full run the complete inventory.
    """
    if event_name == "workflow_dispatch":
        if requested not in {"quick", "full"}:
            raise ValueError("manual CI requires an explicit quick or full tier")
        return requested, "explicit manual selection", parent(root) if requested == "quick" else ""
    if event_name == "push" and is_release(root):
        return "full", "release commit", ""
    if event_name == "pull_request":
        try:
            pr = event["pull_request"]
            base = git(root, "merge-base", pr["base"]["sha"], pr["head"]["sha"])
        except (KeyError, TypeError, subprocess.CalledProcessError):
            return "quick", "pull request base unknown; quick baseline only", ""
        return "quick", "pull request changes", base
    if event_name == "push":
        before = event.get("before", "") if isinstance(event, dict) else ""
        if commit_exists(root, before):
            return "quick", "pushed changes", before
        return "quick", "push without a known previous commit; last commit only", parent(root)
    return "quick", "unclassified event; last commit only", parent(root)


def guard(root, expected):
    actual = git(root, "rev-parse", "HEAD")
    if actual != expected:
        raise ValueError(f"checkout identity changed: expected {expected}, got {actual}")
    subprocess.run(["git", "diff", "--exit-code"], cwd=root, check=True)
    subprocess.run(["git", "diff", "--cached", "--exit-code"], cwd=root, check=True)
    paths = []
    for flags in (("--exclude-standard",), ("--ignored", "--exclude-standard")):
        raw = subprocess.check_output(["git", "ls-files", "--others", "-z", *flags], cwd=root)
        paths.extend(p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p)
    unexpected = [p for p in paths if not (
        "__pycache__" in PurePosixPath(p).parts and p.endswith(".pyc")
        and not (Path(root) / p).is_symlink()
    )]
    if unexpected:
        raise ValueError("unexpected checkout outputs: " + repr(unexpected))
    print(f"Checkout unchanged: {actual}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "guard"))
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    root = Path.cwd()
    try:
        if args.command == "guard":
            guard(root, args.expected_sha)
            return 0
        source = git(root, "rev-parse", "HEAD")
        if source != args.expected_sha:
            raise ValueError("planner checkout does not match the event's candidate SHA")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        tier, reason, base = select(root, os.environ["GITHUB_EVENT_NAME"], event, os.environ.get("REQUESTED_TIER", ""))
        groups = FULL_GROUPS if tier == "full" else ["quick"]
        result = {"tier": tier, "groups": groups, "source_sha": source, "base": base, "reason": reason}
        print(json.dumps(result, indent=2))
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            for key in ("tier", "source_sha", "base"):
                output.write(f"{key}={result[key]}\n")
            output.write("groups=" + json.dumps(groups) + "\n")
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write(f"### CI {tier}\n\n{reason}.\n\nCandidate: `{source}`\n\n"
                          f"Groups: {', '.join(groups)}\n" + (f"\nChanges since: `{base}`\n" if base else ""))
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ci-policy: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
