#!/usr/bin/env python3
"""Keep release output out of ordinary commits.

Only a release commit (made by scripts/release.py, marked with a
`Skill-Craft-Release:` trailer) may change release output:

  - plugins/**, the host catalogs and the README inventory block
  - the `version:` field of any skills/<leaf>/SKILL.md
  - CHANGELOG.md

A release commit is checked out in a temporary worktree and its output must
match its own source (`sync-plugin-views.sh --check`).

Ordinary commits change source and add a note under changes/<leaf>/ for every
skill whose skills/<leaf>/ tree or agents/<leaf>.md card they change. A commit
may opt itself out with a `No-Change-Note: <reason>` trailer (for example, a
typo fix nobody needs to receive as an update). Only scripts/release.py may
delete a note that was pending before the range. Trailers count only in the
message's final paragraph (keys in any case). When --head is HEAD, the pending
notes must also pass the release command's own validation.

Commits whose parents predate this guard are skipped.

Usage:
  check-release-boundary.py --base REV [--head REV]
"""

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = "scripts/check-release-boundary.py"
RELEASE_TRAILER = "Skill-Craft-Release"
NO_NOTE_TRAILER = "No-Change-Note"
GENERATED_PREFIXES = ("plugins/", ".grok-plugin/", ".cursor-plugin/", ".claude-plugin/", ".agents/plugins/")
GENERATED_FILES = ("CHANGELOG.md",)
INVENTORY = re.compile(r"<!-- skill-craft:inventory:start -->.*?<!-- skill-craft:inventory:end -->", re.S)
# The top-level `version:` of the front matter only; never a line past its closing ---.
VERSION = re.compile(r"\A---\n(?:(?!---\n).*\n)*?version:[ \t]*(\S.*?)[ \t]*\n(?:.*\n)*?---\n")
SKILL_CARD = re.compile(r"^skills/([^/]+)/SKILL\.md$")
LEAF_SOURCE = re.compile(r"^(?:skills/([^/]+)/|agents/([^/]+)\.md$)")
NOTE = re.compile(r"^changes/([^/]+)/[^/]+\.md$")
TRAILER_LINE = re.compile(rf"^({RELEASE_TRAILER}|{NO_NOTE_TRAILER})\s*:", re.I | re.M)


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def show(rev, path):
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def exists(rev, path):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{rev}:{path}"],
                          capture_output=True).returncode == 0


def trailers(rev):
    found = {}
    for line in git("log", "-1", "--format=%(trailers:only,unfold)", rev).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            found.setdefault(key.strip().lower(), []).append(value.strip())
    return found


def misplaced(rev, tags):
    """A hint for guard trailers written in the message but not read by git as trailers."""
    keys = sorted({m.group(1) for m in TRAILER_LINE.finditer(git("log", "-1", "--format=%B", rev))
                   if m.group(1).lower() not in tags})
    if not keys:
        return ""
    return (f" ({', '.join(keys)} is in the message but git does not read it as a trailer. Put it in the "
            "final paragraph with Co-Authored-By and no blank line between them.)")


def card_version(text):
    if text is None:
        return None
    match = VERSION.match(text)
    return match.group(1) if match else None


def inventory(text):
    if text is None:
        return None
    match = INVENTORY.search(text)
    return match.group(0) if match else None


def release_output_changes(rev):
    """Release-output paths a single commit changes, compared with its first parent."""
    parent = f"{rev}^"
    changed = git("diff", "--name-only", "--no-renames", parent, rev).split()
    found = []
    for path in changed:
        if path.startswith(GENERATED_PREFIXES) or path in GENERATED_FILES:
            found.append(path)
        elif path == "README.md" and inventory(show(parent, path)) != inventory(show(rev, path)):
            found.append("README.md (inventory block)")
        elif SKILL_CARD.match(path) and card_version(show(parent, path)) != card_version(show(rev, path)):
            if show(parent, path) is not None and show(rev, path) is not None:
                found.append(f"{path} (version)")
    return changed, found


def predates_guard(rev):
    # Transition rule: commits written before this guard existed follow the old
    # workflow. Delete this once the pre-guard branches have landed.
    return not any(exists(parent, GUARD) for parent in git("log", "-1", "--format=%P", rev).split())


def output_matches_source(rev):
    """Check a release commit out on its own and run its sync check there."""
    temp = Path(tempfile.mkdtemp(prefix="release-boundary-"))
    tree = temp / "tree"
    try:
        git("worktree", "add", "-q", "--detach", str(tree), rev)
        result = subprocess.run(["bash", "scripts/sync-plugin-views.sh", "--check"], cwd=tree,
                                capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout + result.stderr)
        return result.returncode == 0
    finally:
        subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(tree)], capture_output=True)
        shutil.rmtree(temp, ignore_errors=True)


def note_changes(rev):
    """(status, path) for every changes/ file a commit adds, modifies or deletes."""
    rows = git("diff", "--name-status", "--no-renames", f"{rev}^", rev, "--", "changes").splitlines()
    return [tuple(row.split("\t", 1)) for row in rows if row]


def pending_notes_problem():
    """Run scripts/release.py's own validation over the pending notes."""
    spec = importlib.util.spec_from_file_location("skill_craft_release", ROOT / "scripts/release.py")
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    try:
        release.plan()
    except release.ReleaseError as exc:
        return f"pending change notes would break the next release: {exc}"
    return None


def check_range(base, head):
    if subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{base}^{{commit}}"],
                      capture_output=True).returncode != 0:
        raise SystemExit(f"release boundary: base {base} is not a commit in this clone "
                         "(force push or shallow fetch?); pass a reachable --base")
    problems = []
    touched = {}
    noted_paths = set()
    for rev in git("rev-list", "--no-merges", "--reverse", f"{base}..{head}").split():
        subject = git("log", "-1", "--format=%h %s", rev).strip()
        if predates_guard(rev):
            print(f"check-release-boundary: skip {subject.split()[0]} (predates the release guard)")
            continue
        tags = trailers(rev)
        if RELEASE_TRAILER.lower() in tags:
            if not output_matches_source(rev):
                problems.append(f"{subject}: release commit output does not match its source")
            continue
        hint = misplaced(rev, tags)
        changed, output = release_output_changes(rev)
        if output:
            problems.append(f"{subject}: changes release output without a {RELEASE_TRAILER} trailer: "
                            + ", ".join(output[:5]) + (" …" if len(output) > 5 else "") + hint)
        for status, path in note_changes(rev):
            if not NOTE.match(path):
                continue
            if status in ("A", "M"):
                noted_paths.add(path)
            elif status == "D" and path in noted_paths:
                noted_paths.discard(path)
            elif status == "D" and exists(base, path):
                problems.append(f"{subject}: deletes pending change note {path}; "
                                "only scripts/release.py consumes notes")
        if NO_NOTE_TRAILER.lower() in tags:
            continue
        for path in changed:
            source = LEAF_SOURCE.match(path)
            if source:
                touched.setdefault(source.group(1) or source.group(2), []).append((subject, path, hint))
    noted = {NOTE.match(path).group(1) for path in noted_paths}
    for leaf, sightings in sorted(touched.items()):
        if leaf not in noted and exists(head, f"skills/{leaf}/SKILL.md"):
            subject, path, _ = sightings[0]
            hint = next((h for _, _, h in sightings if h), "")
            problems.append(f"{path} changed ({subject}) but no changes/{leaf}/*.md note was added; "
                            f"add one, or a '{NO_NOTE_TRAILER}: <reason>' trailer{hint}")
    if git("rev-parse", head) == git("rev-parse", "HEAD"):
        problem = pending_notes_problem()
        if problem:
            problems.append(problem)
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    problems = check_range(args.base, args.head)
    for problem in problems:
        print(f"check-release-boundary: FAIL {problem}", file=sys.stderr)
    if not problems:
        print("check-release-boundary: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
