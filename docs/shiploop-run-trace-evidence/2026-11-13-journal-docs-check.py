"""Structural and citation check of the research journals: fences, one H1, table cell counts, relative links and
anchors, backticked repo paths, `path:line` citations and cited commit hashes (on origin/main, only on another local
ref, or not in the repository). Read-only; resolves everything against HEAD and origin/main.

Usage: python3 -I 2026-11-13-journal-docs-check.py [--json out.json]   (run it anywhere inside the checkout)
A hex token that is not a commit (an action ID, a sha256 prefix) is counted as "not-in-repo"; read the rows, not the sum.
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()
os.chdir(REPO)

def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)

tracked = set(git("ls-files").stdout.split("\n"))
tracked_dirs = set()
for p in tracked:
    parts = p.split("/")
    for i in range(1, len(parts)):
        tracked_dirs.add("/".join(parts[:i]))

files = sorted(p for p in tracked if (re.fullmatch(r"docs/[^/]*(journal|results|register)[^/]*\.md", p)
                                      or p in ("test/shiploop_e2e/LEARNINGS.md", "test/shiploop_e2e/SPEC.md")))

# commits on main
main_commits = set(git("rev-list", "origin/main").stdout.split())
all_commits = set(git("rev-list", "--all").stdout.split())
def resolve(prefix):
    r = git("rev-parse", "--verify", "-q", prefix + "^{commit}")
    return r.stdout.strip() if r.returncode == 0 else ""

HASH = re.compile(r"(?<![0-9A-Za-z_/.\-])([0-9a-f]{7,40})(?![0-9A-Za-z_\-])")
PATHTOK = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"(?<!\!)\[([^\]\n]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
PATHLINE = re.compile(r"\b((?:skills|test|scripts|docs|agents|catalog|changes)/[\w./\-]+\.(?:py|md|sh|json|jsonl|js|yml|yaml|toml|txt)):(\d+)\b")
ROOTS = ("docs/", "skills/", "test/", "scripts/", "agents/", "catalog/", "changes/", "plugins/", ".github/", ".claude-plugin/")

def slug(heading):
    h = re.sub(r"`", "", heading.strip().lower())
    h = re.sub(r"[^\w\- ]", "", h, flags=re.UNICODE)
    return h.replace(" ", "-")

report = collections.OrderedDict()
totals = collections.Counter()
hash_rows = collections.defaultdict(lambda: collections.Counter())
hash_bad = collections.defaultdict(list)

for path in files:
    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    problems = collections.defaultdict(list)
    # --- fences
    open_fence = None
    in_code = [False] * len(lines)
    for i, line in enumerate(lines):
        m = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if m:
            mark = m.group(1)
            if open_fence is None:
                open_fence = (mark[0], len(mark), i + 1)
                in_code[i] = True
            elif mark[0] == open_fence[0] and len(mark) >= open_fence[1] and not m.group(2).strip():
                open_fence = None
                in_code[i] = True
            else:
                in_code[i] = True
        elif open_fence is not None:
            in_code[i] = True
    if open_fence is not None:
        problems["unclosed-fence"].append(f"opened line {open_fence[2]}")
    # --- headings
    heads = [(i + 1, re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", l)) for i, l in enumerate(lines) if not in_code[i] and re.match(r"^#{1,6}\s", l)]
    h1 = [h for h in heads if len(h[1].group(1)) == 1]
    if len(h1) != 1:
        problems["h1-count"].append(f"{len(h1)} H1 headings")
    slugs = collections.Counter(slug(h[1].group(2)) for h in heads)
    prev = 0
    for n, m in heads:
        lvl = len(m.group(1))
        if prev and lvl > prev + 1:
            problems["heading-level-skip"].append(f"line {n}: H{prev} -> H{lvl}")
        prev = lvl
    # --- tables: consistent column counts in a block
    i = 0
    while i < len(lines):
        if not in_code[i] and lines[i].lstrip().startswith("|"):
            j = i
            counts = []
            while j < len(lines) and lines[j].lstrip().startswith("|") and not in_code[j]:
                row = lines[j].strip()
                cells = re.split(r"(?<!\\)\|", row)
                counts.append(len(cells) - 2 if row.endswith("|") else len(cells) - 1)
                j += 1
            if len(set(counts)) > 1:
                problems["table-column-mismatch"].append(f"line {i+1}: columns {sorted(set(counts))}")
            i = j
        else:
            i += 1
    # --- links and anchors
    for i, line in enumerate(lines):
        if in_code[i]:
            continue
        scrub = re.sub(r"`[^`]*`", "", line)
        for m in LINK.finditer(scrub):
            target = m.group(2)
            if re.match(r"^(https?:|mailto:|tel:)", target):
                continue
            ref, _, anchor = target.partition("#")
            if ref == "":
                if anchor and slug(anchor.replace("-", " ")) != anchor and anchor not in slugs:
                    # try raw
                    pass
                if anchor and anchor not in slugs:
                    problems["broken-anchor"].append(f"line {i+1}: #{anchor}")
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), ref))
            if resolved not in tracked and resolved not in tracked_dirs and not os.path.exists(resolved):
                problems["broken-link"].append(f"line {i+1}: {target}")
            elif anchor and resolved.endswith(".md") and resolved in tracked:
                try:
                    other = open(resolved, encoding="utf-8").read().split("\n")
                    oslugs = {slug(re.sub(r"^#+\s+", "", l)) for l in other if re.match(r"^#{1,6}\s", l)}
                    if anchor not in oslugs:
                        problems["broken-anchor"].append(f"line {i+1}: {target}")
                except OSError:
                    pass
    # --- repo path citations in backticks (and bare path:line)
    for i, line in enumerate(lines):
        for m in PATHTOK.finditer(line):
            tok = m.group(1).strip()
            if not tok.startswith(ROOTS) or " " in tok or tok.endswith("/*") or "<" in tok or "{" in tok or "$" in tok:
                continue
            core = re.split(r"[:#]", tok)[0].rstrip(".,;)")
            if "*" in core or "..." in core:
                if not glob.glob(core):
                    problems["missing-glob"].append(f"line {i+1}: {core}")
                continue
            if core in tracked or core.rstrip("/") in tracked_dirs or os.path.exists(core):
                continue
            problems["missing-path"].append(f"line {i+1}: {core}")
        for m in PATHLINE.finditer(line):
            p, n = m.group(1), int(m.group(2))
            if p in tracked:
                size = len(open(p, encoding="utf-8", errors="replace").read().split("\n"))
                totals["pathline-citations"] += 1
                if n > size:
                    problems["pathline-out-of-range"].append(f"line {i+1}: {p}:{n} (file has {size})")
            else:
                if os.path.exists(p):
                    totals["pathline-citations"] += 1
                else:
                    problems["pathline-missing-file"].append(f"line {i+1}: {p}:{n}")
    # --- hashes
    seen = set()
    for i, line in enumerate(lines):
        scrub = re.sub(r"https?://\S+", "", line)
        for m in HASH.finditer(scrub):
            h = m.group(1)
            if not (re.search(r"[a-f]", h) and re.search(r"\d", h)):
                continue
            if h in seen:
                continue
            seen.add(h)
            full = resolve(h)
            if full and full in main_commits:
                hash_rows[path]["on-main"] += 1
            elif full and full in all_commits:
                hash_rows[path]["local-only"] += 1
                hash_bad[path].append((i + 1, h, "local-only"))
            elif full:
                hash_rows[path]["object-not-commit-or-other-ref"] += 1
            else:
                hash_rows[path]["not-in-repo"] += 1
                hash_bad[path].append((i + 1, h, "not-in-repo"))
    report[path] = {k: v for k, v in problems.items()}
    totals["files"] += 1

print("files checked:", totals["files"])
cats = collections.Counter()
for p, probs in report.items():
    for k, v in probs.items():
        cats[k] += len(v)
print("\nproblem categories (count of findings):", dict(cats))
print("path:line citations seen:", totals["pathline-citations"])
print()
for p, probs in report.items():
    if probs:
        print(p)
        for k, v in probs.items():
            print(f"   {k}: {len(v)}")
            for row in v[:3]:
                print(f"       {row}")
print("\n=== hash citations per file (distinct hash tokens) ===")
tot = collections.Counter()
for p in files:
    c = hash_rows.get(p)
    if c:
        tot.update(c)
print("total:", dict(tot))
worst = sorted(((sum(v for k, v in c.items() if k != 'on-main'), p, dict(c)) for p, c in hash_rows.items()), reverse=True)[:12]
for n, p, c in worst:
    print(f"  {n:3d} not-on-main  {p}  {c}")
if "--json" in sys.argv:
    out = sys.argv[sys.argv.index("--json") + 1]
    json.dump({"report": report, "hash_rows": {k: dict(v) for k, v in hash_rows.items()},
               "hash_bad": {k: v for k, v in hash_bad.items()}}, open(out, "w"), indent=1)
