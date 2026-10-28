"""D8 evidence: which line stands for an R-<n> or AD-<n> entry, in real knowledge homes, before and after the fix.

    python3 entry_starts.py OLD_REV ROOT [ROOT ...]

Finds every ``docs/shiploop/spec.md`` and ``architecture.md`` under the roots, counts the forms each ID starts in (first
start -> later starts), and compares ``shiploop_knowledge_home._entries`` and ``outline`` at OLD_REV with this checkout's.
Reads files only; imports the old module from ``git show`` into a temporary folder.
"""

from __future__ import annotations

import collections
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "shiploop" / "scripts"
MODULE = "skills/shiploop/scripts/shiploop_knowledge_home.py"
sys.path.insert(0, str(SCRIPTS))
import shiploop_knowledge_home as new  # noqa: E402


def old_module(rev: str):
    source = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{MODULE}"], check=True, capture_output=True,
                            text=True).stdout
    path = Path(tempfile.mkdtemp()) / "old_knowledge_home.py"
    path.write_text(source)
    spec = importlib.util.spec_from_file_location("old_knowledge_home", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def form(line: str) -> str:
    text = line.lstrip()
    for name, pattern in (("heading", r"#{1,4}\s"), ("list", r"[-*+]\s"), ("list", r"\d+[.)]\s")):
        if re.match(pattern, text):
            return name
    return "table" if text.startswith("|") else "plain line"


def main(rev: str, roots: list[str]) -> None:
    old = old_module(rev)
    paths = sorted(path for root in roots for path in Path(root).expanduser().rglob("docs/shiploop/*.md")
                   if path.name in ("spec.md", "architecture.md") and "node_modules" not in path.parts)
    patterns, moved, outlines, total, repeated = collections.Counter(), collections.Counter(), 0, 0, 0
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        prefix = "R" if path.name == "spec.md" else "AD"
        lines, fenced = text.splitlines(), new._fenced(text.splitlines())
        starts = collections.defaultdict(list)
        for index, line in enumerate(lines):
            match = new._ENTRY_START.match(line)
            if match and not fenced[index] and match.group(1).startswith(prefix + "-"):
                starts[match.group(1)].append(form(line))
        repeated += any(len(found) > 1 for found in starts.values())
        for found in starts.values():
            if len(found) > 1:
                patterns[found[0] + " -> " + ", ".join(sorted(set(found[1:])))] += 1
        before, after = old._entries(text, prefix), new._entries(text, prefix)
        assert before.keys() == after.keys(), path
        total += len(before)
        for ident in before:
            if before[ident] != after[ident]:
                assert before[ident].retired == after[ident].retired, (path, ident)
                moved[form(before[ident].text.splitlines()[0]) + " -> " + form(after[ident].text.splitlines()[0])] += 1
        outlines += old.outline(text, path.name) != new.outline(text, path.name)
    print(f"files {len(paths)}; entries {total}; files with an ID that starts more than once {repeated}")
    print("first start -> later starts:")
    for pattern, count in patterns.most_common():
        print(f"  {count:4d}  {pattern}")
    print(f"entries whose start moved: {sum(moved.values())} {dict(moved)}; retired flags changed: 0 (asserted); "
          f"outlines changed: {outlines}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
