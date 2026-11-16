#!/usr/bin/env python3
"""CI tier selection (quick for ordinary changes, full for releases) and exact-checkout guards."""
import argparse
import json
import os
import re
from pathlib import Path, PurePosixPath
import subprocess

# Five disjoint groups cover the full catalog once on CI's latest stable Python.
FULL_GROUPS = ["core", "shiploop-1", "shiploop-2", "shiploop-3", "e2e-apparatus"]


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root).decode("utf-8", "surrogateescape").strip()


RELEASE_TRAILER = "Skill-Craft-Release:"
ZERO_SHA = "0" * 40


def commit_exists(root, rev):
    if not isinstance(rev, str) or not rev or rev == ZERO_SHA or rev.startswith("-"):
        return False
    return subprocess.run(["git", "cat-file", "-e", f"{rev}^{{commit}}"], cwd=root,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def is_release(root, rev="HEAD"):
    """A release commit (scripts/release.py) carries the Skill-Craft-Release trailer."""
    body = git(root, "log", "-1", "--format=%B", rev)
    return any(line.startswith(RELEASE_TRAILER) for line in body.splitlines())


def pushes_release(root, before):
    """Whether any commit in a verified before..HEAD range is a release commit.

    scripts/release.py never pushes, so a release commit can reach main under
    a later ordinary commit; it still needs the full tier.
    """
    if not ancestor(root, before):
        raise ValueError("release detection requires a verified ancestor base")
    revs = git(root, "rev-list", f"{before}..HEAD").split()
    return any(is_release(root, rev) for rev in revs)


def parent(root):
    return git(root, "rev-parse", "HEAD^1") if commit_exists(root, "HEAD^1") else ""


# Exact infrastructure paths only: ordinary runtime/protocol/state edits remain targeted.
INFRASTRUCTURE_PATHS = frozenset({
    ".github/workflows/ci.yml", "test/ci_policy.py", "test/ci-policy.test.py",
    "test/suite_catalog.py", "test/test-groups.test.py", "test/run_suites.py",
    "test/run-all.sh", "test/suite_durations.json", "test/ci_summary.py",
    "test/ci-summary.test.py", "test/ci_node_stable.cjs",
})


def ancestor(root, base, head="HEAD"):
    return commit_exists(root, base) and subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, head], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def known_changes(root, base, reason):
    if not base or not ancestor(root, base):
        return "full", "change base unknown or not an ancestor; safe full run", ""
    try:
        changed = git(root, "diff", "--no-renames", "--name-only", base, "HEAD").splitlines()
    except subprocess.CalledProcessError:
        return "full", "change range unavailable; safe full run", ""
    if INFRASTRUCTURE_PATHS.intersection(changed):
        return "full", "CI selection/runner/catalog infrastructure changes", ""
    return "quick", reason, base


def select(root, event_name, event, requested):
    """Select full whenever the complete change range cannot be established."""
    if event_name == "workflow_dispatch":
        if requested not in {"quick", "full"}:
            raise ValueError("manual CI requires an explicit quick or full tier")
        if requested == "full":
            return "full", "explicit manual selection", ""
        return known_changes(root, parent(root), "explicit manual selection")
    if event_name == "schedule":
        return "full", "scheduled weekly full run", ""
    if event_name == "pull_request":
        try:
            pr = event["pull_request"]
            refs = [pr["base"]["sha"], pr["head"]["sha"]]
            if not all(isinstance(ref, str) and re.fullmatch(r"[0-9a-fA-F]{40}", ref)
                       and commit_exists(root, ref) for ref in refs):
                return "full", "pull request base unknown; safe full run", ""
            base = git(root, "merge-base", *refs)
        except (KeyError, TypeError, subprocess.CalledProcessError):
            return "full", "pull request base unknown; safe full run", ""
        return known_changes(root, base, "pull request changes")
    if event_name == "push":
        before = event.get("before", "") if isinstance(event, dict) else ""
        if (not isinstance(before, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", before)
                or not ancestor(root, before)):
            return "full", "push base unknown or not an ancestor; safe full run", ""
        if pushes_release(root, before):
            return "full", "release commit", ""
        return known_changes(root, before, "pushed changes")
    return "full", "unclassified event; safe full run", ""


def boundary_base(root, event_name, event, expected):
    """Validate history independently of the planner; never narrow a push range."""
    if git(root, "rev-parse", "HEAD") != expected:
        raise ValueError("release boundary checkout does not match candidate SHA")
    if event_name in {"workflow_dispatch", "schedule"}:
        return None
    if event_name == "pull_request":
        pr = event["pull_request"]
        parents = git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
        if len(parents) != 2 or parents != [pr["base"]["sha"], pr["head"]["sha"]]:
            raise ValueError("release boundary requires the PR merge candidate and validated first parent")
        return parents[0]
    if event_name != "push":
        raise ValueError("release boundary: unsupported event " + event_name)
    if not isinstance(event, dict):
        raise ValueError("release boundary: invalid push event; full history required")
    base = event.get("before", "")
    if (not isinstance(base, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", base)
            or base == ZERO_SHA or not ancestor(root, base)):
        raise ValueError("release boundary: push base absent, invalid, missing or not an ancestor; full history required")
    return base


def boundary(root, event_name, event, expected):
    base = boundary_base(root, event_name, event, expected)
    if base is None:
        print("release boundary: not applicable for " + event_name)
        return
    subprocess.run(["python3", "-B", "scripts/check-release-boundary.py", "--base", base],
                   cwd=root, check=True)


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
    parser.add_argument("command", choices=("plan", "guard", "boundary"))
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    root = Path.cwd()
    try:
        if args.command == "guard":
            guard(root, args.expected_sha)
            return 0
        source = git(root, "rev-parse", "HEAD")
        if source != args.expected_sha:
            raise ValueError("checkout does not match the event's candidate SHA")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        if args.command == "boundary":
            boundary(root, os.environ["GITHUB_EVENT_NAME"], event, args.expected_sha)
            return 0
        tier, reason, base = select(root, os.environ["GITHUB_EVENT_NAME"], event, os.environ.get("REQUESTED_TIER", ""))
        from run_suites import changed_paths
        from suite_catalog import planned_quick_groups
        changed = changed_paths(root, base) if base else ()
        groups = FULL_GROUPS if tier == "full" else list(planned_quick_groups(changed))
        result = {"tier": tier, "groups": groups, "source_sha": source, "base": base, "reason": reason}
        print(json.dumps(result, indent=2))
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            for key in ("tier", "source_sha", "base"):
                output.write(f"{key}={result[key]}\n")
            output.write("groups=" + json.dumps(groups) + "\n")
        from ci_summary import selection_counts
        counts = selection_counts(groups, changed, change_scope_available=bool(base))
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write(f"### CI {tier}\n\n{reason}.\n\nCandidate: `{source}`\n\n"
                          f"Groups: {', '.join(groups)}\n\nSelection scopes: {json.dumps(counts, sort_keys=True)}\n" + (f"\nChanges since: `{base}`\n" if base else ""))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ci-policy: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
