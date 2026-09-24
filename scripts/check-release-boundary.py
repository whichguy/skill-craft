#!/usr/bin/env python3
"""Keep release output out of ordinary commits.

Only a release commit (made by scripts/release.py, marked with a
`Skill-Craft-Release:` trailer) may change release output:

  - plugins/**, the host catalogs and the README inventory block
  - the `version:` field of any skills/<leaf>/SKILL.md
  - CHANGELOG.md

Ordinary commits change source and add a note under changes/<leaf>/ for every
skill they change. A commit may opt out of the note with a
`No-Change-Note: <reason>` trailer (for example, a typo fix nobody needs to
receive as an update).

Usage:
  check-release-boundary.py --base REV [--head REV]
  check-release-boundary.py --release-sync   # HEAD is a release: output matches source
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_TRAILER = "Skill-Craft-Release"
NO_NOTE_TRAILER = "No-Change-Note"
GENERATED_PREFIXES = ("plugins/", ".grok-plugin/", ".cursor-plugin/", ".claude-plugin/", ".agents/plugins/")
GENERATED_FILES = ("CHANGELOG.md",)
INVENTORY = re.compile(r"<!-- skill-craft:inventory:start -->.*?<!-- skill-craft:inventory:end -->", re.S)
VERSION = re.compile(r"\A---\n(?:.*\n)*?version:[ \t]*(\S.*?)[ \t]*\n(?:.*\n)*?---\n")
SKILL_CARD = re.compile(r"^skills/([^/]+)/SKILL\.md$")
SKILL_FILE = re.compile(r"^skills/([^/]+)/")
NOTE = re.compile(r"^changes/([^/]+)/[^/]+\.md$")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def show(rev, path):
    result = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def trailers(rev):
    found = {}
    for line in git("log", "-1", "--format=%(trailers:only,unfold)", rev).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            found.setdefault(key.strip(), []).append(value.strip())
    return found


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


def check_range(base, head):
    problems = []
    touched_skills = {}
    noted = set()
    opted_out = False
    for rev in git("rev-list", "--no-merges", "--reverse", f"{base}..{head}").split():
        tags = trailers(rev)
        subject = git("log", "-1", "--format=%h %s", rev).strip()
        changed, output = release_output_changes(rev)
        if RELEASE_TRAILER in tags:
            continue
        if output:
            problems.append(f"{subject}: changes release output without a {RELEASE_TRAILER} trailer: "
                            + ", ".join(output[:5]) + (" …" if len(output) > 5 else ""))
        if NO_NOTE_TRAILER in tags:
            opted_out = True
        for path in changed:
            skill = SKILL_FILE.match(path)
            if skill:
                touched_skills.setdefault(skill.group(1), subject)
            note = NOTE.match(path)
            if note and show(rev, path) is not None:
                noted.add(note.group(1))
    if not opted_out:
        for leaf, subject in sorted(touched_skills.items()):
            if leaf not in noted and (ROOT / "skills" / leaf / "SKILL.md").exists():
                problems.append(f"skills/{leaf} changed ({subject}) but no changes/{leaf}/*.md note was added; "
                                f"add one, or a '{NO_NOTE_TRAILER}: <reason>' trailer")
    return problems


def check_release_sync():
    if RELEASE_TRAILER not in trailers("HEAD"):
        print("check-release-boundary: HEAD is not a release commit; release output may lag source")
        return []
    result = subprocess.run(["bash", str(ROOT / "scripts/sync-plugin-views.sh"), "--check"], cwd=ROOT)
    return [] if result.returncode == 0 else ["release commit output does not match its source"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--base")
    group.add_argument("--release-sync", action="store_true")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    problems = check_release_sync() if args.release_sync else check_range(args.base, args.head)
    for problem in problems:
        print(f"check-release-boundary: FAIL {problem}", file=sys.stderr)
    if not problems:
        print("check-release-boundary: OK")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
