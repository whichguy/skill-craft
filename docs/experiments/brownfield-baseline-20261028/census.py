#!/usr/bin/env python3
"""Deterministic repository census for a brownfield baseline (experiment X1, 2026-10-28).

    python3 census.py REPO [--json OUT.json] [--md OUT.md]

A map of an existing repository that a script can produce in seconds, before any model reads it: identity, size,
the file classes, the directory map with its code, test and docs weight and recent activity, the root files, the
documentation inventory (READMEs, instruction files, numbered-document sets that look like decision records) and the
hot spots.  The Markdown form is short enough to quote into a packet; the JSON form is for scripts.

Reads only Git and the tracked files of REPO: no model, no network, nothing written in REPO.  Generic by
construction: file classes come from ShipLoop's own catalog (skills/shiploop/references/path-classes.json, through
shiploop_item_scope.classify); no stack, language or tool is named here.  A decision record is found by its content,
not its name: a Markdown-like file with at least three of the four parts decision records share (status, context,
decision, consequences) as headings or as a `Status:` line.  (Round 1 matched digit-prefixed file names instead: it
missed both real ADR sets, `20200924-*.md` and `adr-007-*.md`, and flagged numbered tutorial chapters.)
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_item_scope as item_scope  # noqa: E402

TEXT_LIMIT = 2_000_000          # bytes; a larger file is counted, not read
DOC_SUFFIXES = (".md", ".rst", ".adoc", ".txt")
# The shared parts of a decision record, as a heading or (status) a `Status:` line or list item.
RECORD_PART = re.compile(r"^(?:#{1,4}\s*(status|context|decision|consequences)\b|[-*]?\s*\**(status)\**\s*:)", re.I)


def decision_record(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:250]
    except OSError:
        return False
    return len({match.group(1) or match.group(2) for line in head if (match := RECORD_PART.match(line.strip()))}
               - {None}) >= 3


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def lines_of(path: Path) -> int | None:
    """Text lines of a tracked file, or None for a binary, unreadable or oversized one."""
    try:
        if path.stat().st_size > TEXT_LIMIT:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def size_class(code_lines: int) -> str:
    for bound, name in ((5_000, "small"), (50_000, "medium"), (500_000, "large")):
        if code_lines < bound:
            return name
    return "huge"


def census(repo: Path) -> dict:
    started = time.monotonic()
    head = git(repo, "rev-parse", "HEAD").strip()
    files = [name for name in git(repo, "ls-files", "-z").split("\0") if name]
    first, last = git(repo, "log", "--reverse", "--format=%cs", "--max-parents=0").split()[:1] or ["?"], \
        git(repo, "log", "-1", "--format=%cs").strip()
    commits = int(git(repo, "rev-list", "--count", "HEAD").strip())

    per_class = collections.Counter()
    per_class_lines = collections.Counter()
    per_ext = collections.Counter()
    dirs: dict = collections.defaultdict(lambda: collections.Counter())
    docs, records = [], collections.defaultdict(list)
    for name in files:
        cls = item_scope.classify(name)
        count = lines_of(repo / name)
        per_class[cls] += 1
        per_class_lines[cls] += count or 0
        suffix = Path(name).suffix.lower() or "(none)"
        if cls == "code" and count:
            per_ext[suffix] += count
        parts = name.split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        second = "/".join(parts[:2]) if len(parts) > 2 else top
        for key in {top, second}:
            dirs[key][cls + "_files"] += 1
            dirs[key][cls + "_lines"] += count or 0
        if suffix in DOC_SUFFIXES:
            docs.append((name, count or 0))
            if suffix != ".txt" and decision_record(repo / name):
                records["/".join(parts[:-1]) or "(root)"].append(parts[-1])

    # Activity: commits per path in the last 365 days (names only: no blob is read, so a blobless clone works).
    touched = collections.Counter()
    log = git(repo, "log", "--since=365.days", "--no-renames", "--name-only", "--format=%x00%H")
    recent_commits = 0
    for block in log.split("\0"):
        names = [line for line in block.splitlines()[1:] if line.strip()]
        if block.strip():
            recent_commits += 1
        for path in names:
            touched[path] += 1
    for path, hits in touched.items():
        parts = path.split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        dirs[top]["commits_365d"] += hits
        if len(parts) > 2:
            dirs["/".join(parts[:2])]["commits_365d"] += hits

    code_lines = per_class_lines["code"]
    tops = sorted((key for key in dirs if "/" not in key), key=lambda key: -(dirs[key]["code_lines"] + dirs[key]["test_lines"]))
    # Expand a top-level directory that holds a fifth or more of the code into its second level.
    rows = []
    for key in tops:
        rows.append(key)
        if code_lines and dirs[key]["code_lines"] >= code_lines / 5:
            subs = sorted((sub for sub in dirs if sub.startswith(key + "/")),
                          key=lambda sub: -(dirs[sub]["code_lines"] + dirs[sub]["test_lines"]))
            rows += subs[:8]
    hot = [(path, hits) for path, hits in touched.most_common(60)
           if item_scope.classify(path) in ("code", "test") and path in set(files)][:12]
    root_files = sorted(name for name in files if "/" not in name)
    # Instruction-like files (an upper-case Markdown name) at the root and one level down, where packages keep theirs.
    instructions = sorted(name for name in files if name.count("/") <= 1 and name.endswith(".md")
                          and Path(name).stem.isupper())
    readmes = sorted((name, count) for name, count in docs if Path(name).name.lower().startswith("readme"))
    decision_sets = {folder: sorted(names) for folder, names in records.items()}
    subjects = git(repo, "log", "-8", "--format=%cs %s").splitlines()
    return {
        "repo": str(repo), "head": head, "commits": commits, "first_commit": first[0], "last_commit": last,
        "tracked_files": len(files), "size_class": size_class(code_lines),
        "classes": {cls: {"files": per_class[cls], "lines": per_class_lines[cls]} for cls in sorted(per_class)},
        "code_extensions": per_ext.most_common(12),
        "map": [{"path": key, **dict(dirs[key])} for key in rows[:30]],
        # The whole inventory (every directory to two levels): the map above is the display, never the coverage
        # universe (round 2, after Astra's review: a truncated map cannot vouch for areas it leaves out).
        "inventory": [{"path": key, **dict(dirs[key])} for key in sorted(dirs)],
        "root_files": root_files, "instruction_files": instructions, "readmes": readmes[:15],
        "docs_files": len(docs), "decision_sets": decision_sets, "commits_365d": recent_commits,
        "hot_spots": hot, "recent_subjects": subjects,
        "seconds": round(time.monotonic() - started, 2),
    }


def markdown(data: dict) -> str:
    out = [f"# Census of {Path(data['repo']).name} at {data['head'][:12]}", "",
           f"- {data['tracked_files']} tracked files; {data['commits']} commits from {data['first_commit']} to "
           f"{data['last_commit']} ({data['commits_365d']} in the last 365 days); size class {data['size_class']}; "
           f"census took {data['seconds']} s.",
           "- Classes (files / text lines): " + "; ".join(
               f"{cls} {row['files']} / {row['lines']}" for cls, row in data["classes"].items()),
           "- Code lines by extension: " + ", ".join(f"{ext} {count}" for ext, count in data["code_extensions"]),
           "", "## Map (code, test and docs weight; commits touching it in 365 days)", "",
           "| Path | Code files / lines | Test files / lines | Docs files | Commits 365d |", "|---|---|---|---|---|"]
    for row in data["map"]:
        out.append(f"| {row['path']} | {row.get('code_files', 0)} / {row.get('code_lines', 0)} | "
                   f"{row.get('test_files', 0)} / {row.get('test_lines', 0)} | {row.get('docs_files', 0)} | "
                   f"{row.get('commits_365d', 0)} |")
    out += ["", "## Root files", "", ", ".join(data["root_files"][:60]) + (" …" if len(data["root_files"]) > 60 else ""),
            "", "## Documentation", "",
            "- READMEs: " + (", ".join(f"{name} ({count} lines)" for name, count in data["readmes"]) or "none"),
            "- Instruction files at the root: " + (", ".join(data["instruction_files"]) or "none"),
            f"- Markdown-like files in all: {data['docs_files']}",
            "- Decision records (found by content): " + ("; ".join(
                f"{folder} ({len(names)}: {names[0]} … {names[-1]})" for folder, names in data["decision_sets"].items())
                or "none"),
            "", "## Hot spots (code and test files changed most in 365 days)", ""]
    out += [f"- {path} ({hits})" for path, hits in data["hot_spots"]] or ["- none"]
    out += ["", "## Recent commits", ""] + [f"- {subject}" for subject in data["recent_subjects"]]
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--md", type=Path)
    args = parser.parse_args()
    data = census(args.repo.resolve())
    if args.json:
        args.json.write_text(json.dumps(data, indent=1) + "\n")
    text = markdown(data)
    if args.md:
        args.md.write_text(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
