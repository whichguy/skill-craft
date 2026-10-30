"""Run the stale-mention rule over each of a repository's last N non-merge commits (diff c^..c, grep at c)."""
import re, subprocess, sys
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from stale_mentions import TOKEN, DOC, HISTORY

def git(tree, *a):
    return subprocess.run(["git", *a], cwd=tree, capture_output=True, text=True).stdout

tree, n = sys.argv[1], int(sys.argv[2])
commits = git(tree, "log", "--no-merges", "--format=%h", f"-{n}").split()
total = 0
for c in commits:
    diff = git(tree, "diff", "--no-color", "-U0", f"{c}^", c)
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
    cands = sorted(removed - added)
    hits = {}
    for name in cands[:400]:
        files = git(tree, "grep", "-l", "-w", name, c).splitlines()
        files = [f.split(":", 1)[1] for f in files]
        if any(not DOC.search(f) for f in files):
            continue
        docs = [f for f in files if DOC.search(f) and not HISTORY.search(f)]
        if docs:
            hits[name] = docs[:3]
    total += len(hits)
    subj = git(tree, "log", "-1", "--format=%s", c)[:70].strip()
    print(f"{c} cands={len(cands)} hits={len(hits)} {list(hits.items())[:4]} | {subj}")
print("total hits", total)
