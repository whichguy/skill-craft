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
  2. bumps the skill-craft plugin's version in catalog/skill-craft-plugin.json;
  3. prepends a CHANGELOG.md section, led by the plugin version, with the
     notes, and deletes them;
  4. regenerates plugins/skill-craft, the host catalogs and the README inventory;
  5. commits everything with a `Skill-Craft-Release:` trailer.

Every skill ships in the one skill-craft plugin, so every release changes its
version: by the largest bump among the notes (a `version:` note counts as the
bump its old -> new version implies), or by a patch for an output-only release.
The first release of plugins/skill-craft ships the authored version as is.

With no notes, a release is cut only when release output no longer matches
source (a deleted skill, LICENSE or catalog/ change); its trailer names only
the plugin.

A new version must be above the current one and never already released. A
skill never shipped in plugins/skill-craft may ship at its authored version
with a `version:` note. When the release fails before committing, the checkout
is restored to HEAD and the notes are kept.

It never pushes. Publish the commit with scripts/release-push.py.

Usage:
  release.py [--dry-run] [--date YYYY-MM-DD]
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "changes"
PLUGIN = "skill-craft"
BUNDLE = ROOT / "catalog" / "skill-craft-plugin.json"
TRAILER = "Skill-Craft-Release"
# Strict semver, as scripts/skill-frontmatter-to-plugin-json.js checks it.
_NUM = r"0|[1-9]\d*"
_PRE = r"0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*"
SEMVER = re.compile(
    rf"({_NUM})\.({_NUM})\.({_NUM})(?:-((?:{_PRE})(?:\.(?:{_PRE}))*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
    re.ASCII)
FRONT = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)
# The top-level `version:` of the front matter only; never a line past its closing ---.
CARD_VERSION = re.compile(r"\A(---\n(?:(?!---\n).*\n)*?version:[ \t]*)(\S+)([ \t]*\n)")
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
    if "version" in fields and "bump" in fields:
        raise ReleaseError(f"{path.relative_to(ROOT)}: set bump: or version:, not both")
    if "version" in fields:
        if not SEMVER.fullmatch(fields["version"]):
            raise ReleaseError(f"{path.relative_to(ROOT)}: version must be semantic, got {fields['version']!r}")
    elif fields.get("bump") not in BUMPS:
        raise ReleaseError(f"{path.relative_to(ROOT)}: bump must be one of {', '.join(BUMPS)}")
    return fields, body


def semver(version):
    match = SEMVER.fullmatch(version)
    if not match:
        raise ReleaseError(f"current version {version!r} is not semantic")
    return int(match[1]), int(match[2]), int(match[3]), match[4]


def precedence(version):
    """Semver precedence: a release sorts above its prereleases, and
    prerelease identifiers compare numerically or lexically, field by field."""
    major, minor, patch, pre = semver(version)
    ids = tuple((0, int(part), "") if part.isdigit() else (1, 0, part) for part in pre.split(".")) if pre else ()
    return major, minor, patch, pre is None, ids


def bumped(version, bump):
    major, minor, patch, pre = semver(version)
    if pre:
        # A prerelease already stands for its release line: a bump that would
        # land on that line finalizes it (0.3.0-rc.1 minor -> 0.3.0).
        if bump == "major" and minor == patch == 0 or bump == "minor" and patch == 0:
            return f"{major}.{minor}.{patch}"
        if bump == "patch":
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
    return f"{major}.{minor}.{patch + 1}"


def in_head(path):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"HEAD:{path}"],
                          capture_output=True).returncode == 0


def never_released(leaf):
    """True when HEAD's plugin does not bundle the skill: it was never released."""
    return not in_head(f"plugins/{PLUGIN}/skills/{leaf}")


def implied_bump(old, new):
    """The bump class an explicit old -> new skill version stands for."""
    (a, b, _, _), (c, d, _, _) = semver(old), semver(new)
    return "major" if c != a else "minor" if d != b else "patch"


def plan_bundle(releases, released):
    """{old, new} for the skill-craft plugin version this release ships."""
    try:
        old = json.loads(BUNDLE.read_text())["version"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ReleaseError(f"catalog/skill-craft-plugin.json has no version: {exc}")
    if not in_head(f"plugins/{PLUGIN}"):
        new = old
    else:
        bumps = [bump for entry in releases.values() for bump in entry["bumps"]]
        bumps += [implied_bump(entry["old"], entry["new"]) for entry in releases.values() if entry["set"]]
        new = bumped(old, max(bumps, key=BUMPS.index) if bumps else "patch")
        if precedence(new) <= precedence(old):
            raise ReleaseError(f"{PLUGIN}: new version {new} is not above current {old}")
    if f"{PLUGIN}@{new}" in released:
        raise ReleaseError(f"{PLUGIN}: {new} was already released")
    return {"old": old, "new": new}


def released_versions():
    """Every `leaf@version` any Skill-Craft-Release trailer in history has named."""
    values = git("log", f"--format=%(trailers:key={TRAILER},valueonly)")
    return {token for token in re.split(r"[,\s]+", values) if "@" in token}


def plan():
    """Validate the pending notes and return {leaf: entry}. Reads only; changes nothing."""
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
    released = released_versions() if releases else set()
    for leaf, entry in releases.items():
        if entry["set"] and entry["bumps"]:
            raise ReleaseError(f"changes/{leaf}: notes mix bump: and version:; use one or the other")
        match = CARD_VERSION.match(entry["card"].read_text())
        if not match:
            raise ReleaseError(f"skills/{leaf}/SKILL.md has no front matter version")
        entry["old"] = match.group(2)
        bump = max(entry["bumps"], key=BUMPS.index) if entry["bumps"] else None
        entry["new"] = entry["set"] or bumped(entry["old"], bump)
        first_release = entry["new"] == entry["old"] and entry["set"] and never_released(leaf)
        if not first_release and precedence(entry["new"]) <= precedence(entry["old"]):
            raise ReleaseError(f"skills/{leaf}: new version {entry['new']} is not above current {entry['old']}")
        if f"{leaf}@{entry['new']}" in released:
            raise ReleaseError(f"skills/{leaf}: {entry['new']} was already released; "
                               f"add a changes/{leaf} note with version: above it")
    return releases


def plan_all():
    """(skill releases, plugin version change). Reads only; changes nothing."""
    releases = plan()
    return releases, plan_bundle(releases, released_versions())


def apply(releases, bundle, date):
    data = json.loads(BUNDLE.read_text())
    data["version"] = bundle["new"]
    BUNDLE.write_text(json.dumps(data, indent=2) + "\n")
    for leaf, entry in releases.items():
        card = entry["card"]
        card.write_text(CARD_VERSION.sub(lambda m: m.group(1) + entry["new"] + m.group(3), card.read_text(), count=1))
        guide = card.parent / "README.md"
        if guide.is_file():
            lines = guide.read_text().split("\n")
            if lines and lines[0].endswith(" " + entry["old"]):
                lines[0] = lines[0][: -len(entry["old"])] + entry["new"]
                guide.write_text("\n".join(lines))
    items = [(leaf, entry["new"], [body for _, body in entry["notes"]]) for leaf, entry in releases.items()]
    # The plugin version users see on update leads the section and names what it ships.
    shipped = ", ".join(f"{name} {version}" for name, version, _ in sorted(items))
    section = [f"## {date}", "", f"### {PLUGIN} {bundle['new']}", "",
               f"- Skills: {shipped}" if shipped else "- Release output regenerated; no skill changed.", ""]
    for name, version, bodies in sorted(items):
        section.append(f"### {name} {version}")
        section.append("")
        for body in bodies:
            section.extend(("- " if i == 0 else "  ") + line.rstrip() if line.strip() else ""
                           for i, line in enumerate(body.splitlines()))
        section.append("")
    log = ROOT / "CHANGELOG.md"
    previous = log.read_text() if log.is_file() else "# Changelog\n\nWritten by scripts/release.py.\n"
    head, sep, rest = previous.partition("\n## ")
    if sep and rest.startswith(f"{date}\n"):
        # One heading per date: the new blocks go under the existing one.
        tail = "\n" + rest[len(date) + 1:].lstrip("\n")
    else:
        tail = "\n## " + rest if sep else ""
    log.write_text(head.rstrip("\n") + "\n\n" + "\n".join(section) + tail)
    for entry in releases.values():
        for path, _ in entry["notes"]:
            path.unlink()
        folder = entry["notes"][0][0].parent
        if not any(folder.iterdir()):
            folder.rmdir()


def cut(releases, bundle, date):
    """Apply the plan, regenerate release output and commit it."""
    apply(releases, bundle, date)
    subprocess.run(["bash", str(ROOT / "scripts/sync-plugin-views.sh")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["bash", str(ROOT / "scripts/sync-plugin-views.sh"), "--check"], cwd=ROOT, check=True)
    shipped = [(PLUGIN, bundle["new"])] + sorted((leaf, entry["new"]) for leaf, entry in releases.items())
    summary = ", ".join(f"{name} {version}" for name, version in shipped)
    paths = ("skills", "changes", "catalog/skill-craft-plugin.json", "CHANGELOG.md", "README.md", "plugins",
             ".grok-plugin", ".cursor-plugin", ".claude-plugin", ".agents")
    git("add", "-A", "--", *[p for p in paths if (ROOT / p).exists() or git("ls-files", "--", p)])
    git("commit", "-q", "-m", f"release: {summary}", "-m",
        f"{TRAILER}: " + ", ".join(f"{name}@{version}" for name, version in shipped))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args()
    try:
        releases, bundle = plan_all()
        for leaf, entry in sorted(releases.items()):
            print(f"release: {leaf} {entry['old']} -> {entry['new']} ({len(entry['notes'])} note(s))")
        if not releases:
            check = subprocess.run(["bash", str(ROOT / "scripts/sync-plugin-views.sh"), "--check"],
                                   cwd=ROOT, capture_output=True)
            if check.returncode == 0:
                print("release: no pending notes under changes/; nothing to release")
                return 0
            if args.dry_run:
                print(f"release: output drift; would cut an output-only release ({PLUGIN} {bundle['old']} -> {bundle['new']})")
                return 0
            print("release: no pending notes, but release output differs from source; cutting an output-only release")
        print(f"release: {PLUGIN} {bundle['old']} -> {bundle['new']}")
        if args.dry_run:
            return 0
        if git("status", "--porcelain=v1", "--untracked-files=all"):
            raise ReleaseError("checkout must be clean; commit or set aside other work first")
        head = git("rev-parse", "HEAD").strip()
        try:
            cut(releases, bundle, args.date)
        except BaseException:
            # The checkout was clean, so everything outside HEAD is ours to undo.
            if git("rev-parse", "HEAD").strip() == head:
                git("reset", "-q", "--hard", "HEAD")
                git("clean", "-fdq")
                print("release: failed; checkout restored to HEAD (notes kept)", file=sys.stderr)
            raise
        print(f"release: committed {git('rev-parse', '--short', 'HEAD').strip()}; publish with scripts/release-push.py")
        return 0
    except (ReleaseError, subprocess.CalledProcessError) as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
