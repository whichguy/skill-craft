#!/usr/bin/env python3
"""Turn pending change notes into one release commit.

Ordinary commits never edit versions or release output. They add a note:

  changes/<leaf>/<slug>.md
  ---
  bump: patch            # patch | minor | major, or `version: 1.2.3` to set it
  ---
  One or more lines describing the change for people who install the skill.

This command, run on a clean checkout:

  1. bumps each noted skill's `version:` in skills/<leaf>/SKILL.md (and the
     first line of skills/<leaf>/README.md when it ends with the old version);
  2. prepends the notes to CHANGELOG.md and deletes them;
  3. regenerates plugins/, the host catalogs and the README inventory;
  4. commits everything with a `Skill-Craft-Release:` trailer.

It never pushes. Publish the commit with scripts/release-push.py.

Usage:
  release.py [--dry-run] [--date YYYY-MM-DD]
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "changes"
TRAILER = "Skill-Craft-Release"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")
FRONT = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)
CARD_VERSION = re.compile(r"\A(---\n(?:.*\n)*?version:[ \t]*)(\S+)([ \t]*\n)", re.M)
BUMPS = ("patch", "minor", "major")


class ReleaseError(Exception):
    pass


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def read_note(path):
    match = FRONT.match(path.read_text())
    if not match:
        raise ReleaseError(f"{path.relative_to(ROOT)}: needs a --- front matter block with bump: or version:")
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.split("#", 1)[0].strip()
    body = match.group(2).strip()
    if not body:
        raise ReleaseError(f"{path.relative_to(ROOT)}: describe the change below the front matter")
    if "version" in fields:
        if not SEMVER.match(fields["version"]):
            raise ReleaseError(f"{path.relative_to(ROOT)}: version must be semantic, got {fields['version']!r}")
    elif fields.get("bump") not in BUMPS:
        raise ReleaseError(f"{path.relative_to(ROOT)}: bump must be one of {', '.join(BUMPS)}")
    return fields, body


def bumped(version, bump):
    match = SEMVER.match(version)
    if not match:
        raise ReleaseError(f"current version {version!r} is not semantic")
    major, minor, patch, pre = int(match[1]), int(match[2]), int(match[3]), match[4]
    if pre and bump == "patch":
        # 0.3.0-rc.1 -> 0.3.0-rc.2: stay on the prerelease line.
        parts = pre.split(".")
        if parts[-1].isdigit():
            parts[-1] = str(int(parts[-1]) + 1)
            return f"{major}.{minor}.{patch}-{'.'.join(parts)}"
        return f"{major}.{minor}.{patch}"
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}" if not pre else f"{major}.{minor}.{patch}"


def plan():
    releases = {}
    for path in sorted(CHANGES.glob("*/*.md")) if CHANGES.is_dir() else []:
        leaf = path.parent.name
        card = ROOT / "skills" / leaf / "SKILL.md"
        if not card.is_file():
            raise ReleaseError(f"{path.relative_to(ROOT)}: no skills/{leaf}/SKILL.md")
        fields, body = read_note(path)
        entry = releases.setdefault(leaf, {"card": card, "notes": [], "bumps": [], "set": None})
        entry["notes"].append((path, body))
        if "version" in fields:
            if entry["set"] and entry["set"] != fields["version"]:
                raise ReleaseError(f"changes/{leaf}: notes set different versions")
            entry["set"] = fields["version"]
        else:
            entry["bumps"].append(fields["bump"])
    for leaf, entry in releases.items():
        match = CARD_VERSION.match(entry["card"].read_text())
        if not match:
            raise ReleaseError(f"skills/{leaf}/SKILL.md has no front matter version")
        entry["old"] = match.group(2)
        bump = max(entry["bumps"], key=BUMPS.index) if entry["bumps"] else None
        entry["new"] = entry["set"] or bumped(entry["old"], bump)
        if entry["new"] == entry["old"]:
            raise ReleaseError(f"skills/{leaf}: new version equals current {entry['old']}")
    return releases


def apply(releases, date):
    for leaf, entry in releases.items():
        card = entry["card"]
        card.write_text(CARD_VERSION.sub(lambda m: m.group(1) + entry["new"] + m.group(3), card.read_text(), count=1))
        guide = card.parent / "README.md"
        if guide.is_file():
            lines = guide.read_text().split("\n")
            if lines and lines[0].endswith(" " + entry["old"]):
                lines[0] = lines[0][: -len(entry["old"])] + entry["new"]
                guide.write_text("\n".join(lines))
    section = [f"## {date}", ""]
    for leaf, entry in sorted(releases.items()):
        section.append(f"### {leaf} {entry['new']}")
        section.append("")
        for _, body in entry["notes"]:
            section.extend(f"- {line}" if i == 0 else f"  {line}" for i, line in enumerate(body.splitlines()))
        section.append("")
    log = ROOT / "CHANGELOG.md"
    previous = log.read_text() if log.is_file() else "# Changelog\n\nWritten by scripts/release.py.\n"
    head, sep, rest = previous.partition("\n## ")
    log.write_text(head.rstrip("\n") + "\n\n" + "\n".join(section) + ("\n## " + rest if sep else ""))
    for entry in releases.values():
        for path, _ in entry["notes"]:
            path.unlink()
        folder = entry["notes"][0][0].parent
        if not any(folder.iterdir()):
            folder.rmdir()
    subprocess.run(["bash", str(ROOT / "scripts/sync-plugin-views.sh")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["bash", str(ROOT / "scripts/sync-plugin-views.sh"), "--check"], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    try:
        releases = plan()
        if not releases:
            print("release: no pending notes under changes/")
            return 0
        for leaf, entry in sorted(releases.items()):
            print(f"release: {leaf} {entry['old']} -> {entry['new']} ({len(entry['notes'])} note(s))")
        if args.dry_run:
            return 0
        if git("status", "--porcelain=v1", "--untracked-files=all"):
            raise ReleaseError("checkout must be clean; commit or set aside other work first")
        apply(releases, args.date)
        summary = ", ".join(f"{leaf} {entry['new']}" for leaf, entry in sorted(releases.items()))
        git("add", "-A", "--", "skills", "changes", "CHANGELOG.md", "README.md", "plugins",
            ".grok-plugin", ".cursor-plugin", *[p for p in (".claude-plugin", ".agents") if (ROOT / p).exists()])
        git("commit", "-q", "-m", f"release: {summary}", "-m",
            f"{TRAILER}: " + ", ".join(f"{leaf}@{entry['new']}" for leaf, entry in sorted(releases.items())))
        print(f"release: committed {git('rev-parse', '--short', 'HEAD').strip()}; publish with scripts/release-push.py")
        return 0
    except (ReleaseError, subprocess.CalledProcessError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
