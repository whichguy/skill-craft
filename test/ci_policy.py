#!/usr/bin/env python3
"""Full-inventory CI planning and exact-checkout qualification guards."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

# Every CI event runs these groups; together they are the complete catalog.
FULL_GROUPS = ["core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus", "experiments"]


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root).decode("utf-8", "surrogateescape").strip()


def select(event_name):
    """Qualify the complete hermetic inventory; no event or path set is exempt."""
    return "full", f"{event_name or 'unknown'} event; CI always runs every hermetic group"


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
        tier, reason = select(os.environ["GITHUB_EVENT_NAME"])
        groups = FULL_GROUPS
        result = {"tier": tier, "groups": groups, "source_sha": source, "reason": reason}
        print(json.dumps(result, indent=2))
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            for key in ("tier", "source_sha"):
                output.write(f"{key}={result[key]}\n")
            output.write("groups=" + json.dumps(groups) + "\n")
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write(f"### CI {tier}\n\n{reason}.\n\nCandidate: `{source}`\n\nGroups: {', '.join(groups)}\n")
        return 0
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ci-policy: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
