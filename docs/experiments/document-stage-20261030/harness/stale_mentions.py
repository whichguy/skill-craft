"""Prototype of a script-derived document-packet hint: names the item's code no longer has that docs still mention.

    python3 -I stale_mentions.py <worktree> [<base ref>]

A name is an identifier-like token (4+ characters) on a removed line of a non-doc file in the item's diff, absent from
every added line, and absent from every tracked non-doc file now.  Each such name is searched (whole word) in the doc
path class.  Generic: no language rules; a hint for the document stage, never a gate.
"""

import re
import subprocess
import sys

TOKEN = re.compile(r"\b(?=[A-Za-z0-9_]*(?:_|[a-z][A-Z]))[A-Za-z_][A-Za-z0-9_]{3,}\b")  # identifier-shaped: an underscore or a camel hump
DOC = re.compile(r"(\.md|\.rst|\.adoc|\.txt)$|^docs/|(^|/)CHANGELOG")
HISTORY = re.compile(r"(^|/)CHANGELOG|\d{4}-?\d{2}-?\d{2}|(^|/)(experiments|archive|history)/|journal|LEARNINGS", re.I)


def git(tree, *args):
    return subprocess.run(["git", *args], cwd=tree, capture_output=True, text=True).stdout


def stale_mentions(tree, base="HEAD"):
    diff = git(tree, "diff", "--no-color", "-U0", base, "--", ".")
    removed, added, path = set(), set(), None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif path and DOC.search(path):
            continue
        elif line.startswith("-") and not line.startswith("---"):
            removed |= set(TOKEN.findall(line))
        elif line.startswith("+"):
            added |= set(TOKEN.findall(line))
    hits = {}
    for name in sorted(removed - added):
        code = [p for p in git(tree, "grep", "-l", "-w", name).splitlines() if not DOC.search(p)]
        if code:
            continue  # the code still has the name
        docs = [h for h in git(tree, "grep", "-n", "-w", name).splitlines() if DOC.search(h.split(":", 1)[0]) and not HISTORY.search(h.split(":", 1)[0])
                and not h.startswith("docs/shiploop/")]
        if docs:
            hits[name] = [":".join(h.split(":", 2)[:2]) for h in docs]
    return hits


if __name__ == "__main__":
    found = stale_mentions(sys.argv[1], *(sys.argv[2:3]))
    print("Names the item's code no longer has that its docs still mention (script-derived): "
          + ("; ".join(f"`{n}`: " + ", ".join(locs) for n, locs in found.items()) if found else "none") + ".")
