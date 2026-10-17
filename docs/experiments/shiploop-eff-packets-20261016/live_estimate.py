"""Estimate PK3 on real packet files from a live run made before it (the Salesforce chess run, full packet files of 11 stages):
apply prose_symbols to each (old heading swapped for the new, the GUIDES definition added) and compare sizes.
    live_estimate.py <checkout> <directory of the live packet files>"""
import sys, re, types
from pathlib import Path
root = Path(sys.argv[1]); sys.path.insert(0, str(root / "skills/shiploop/scripts"))
import shiploop_navigator as nav
live = Path(sys.argv[2])
OLD = "References (defined once; the packet names files by these symbols):"
tb = ta = 0
for f in sorted(live.glob("*.md")):
    t = f.read_text(errors="replace")
    if OLD not in t:
        continue
    run = re.search(r"dir=(\S+)$", t, re.M).group(1); wt = re.search(r"WORKTREE = (\S+)", t).group(1)
    g = re.search(r"^Coding decision guide: (\S+)/coding-guidance", t, re.M)
    guides = g.group(1) if g else None
    if not guides:
        m = re.search(r"^[A-Za-z -]+: (\S+)/[\w-]+\.md(?:#[\w-]+)?$", t, re.M)
        guides = m.group(1) if m else None
    new = t.replace(OLD, nav.REFERENCES_HEAD)
    if guides:
        new = new.replace(" (run records)\n", " (run records) · GUIDES = " + guides + " (the skill's guides)\n", 1)
    core = types.SimpleNamespace(PACKAGE_ROOT=Path(guides).parent) if guides else None
    out = nav.prose_symbols(new, core, Path(run), {"repo": wt})
    tb += len(t); ta += len(out)
    print(f"{f.name:20s} {len(t):7d} -> {len(out):7d} ({len(out)-len(t):+6d}, {100*(len(out)-len(t))/len(t):+.1f}%)")
print(f"TOTAL {tb} -> {ta} ({ta-tb:+d}, {100*(ta-tb)/tb:+.1f}%)")
