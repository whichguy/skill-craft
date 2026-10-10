#!/usr/bin/env python3
"""For every Skill-Craft-Release commit, did the commits since the previous release touch the E2E journal?

Read-only. Usage: history_evidence.py [repo]   (default: the current directory)
The range for a release R is the one scripts/release.py would see with HEAD at R's first parent:
the newest earlier release commit .. R (all of history, when R is the first release).
"""
import collections
import subprocess
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else "."
JOURNAL = "test/shiploop_e2e/LEARNINGS.md"
CUTOFF = "2026-10-03"


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], check=True, capture_output=True, text=True).stdout


def releases(rev):
    rows = []
    for record in git("log", "--format=%H%x1f%(trailers:key=Skill-Craft-Release,valueonly)%x1e", rev).split("\x1e"):
        sha, _, value = record.strip().partition("\x1f")
        if value.strip():
            rows.append((sha, " ".join(value.split())))
    return rows


rows = []
for sha, trailer in releases("HEAD"):
    parents = git("log", "-1", "--format=%P", sha).split()
    earlier = releases(parents[0]) if parents else []
    span = f"{earlier[0][0]}..{sha}" if earlier else sha
    rows.append({"sha": sha[:8], "date": git("log", "-1", "--format=%as", sha).strip(),
                 "shiploop": any(t.startswith("shiploop@") for t in trailer.replace(",", " ").split()),
                 "commits": len(git("log", "--format=%h", span).split()),
                 "journal": len(git("log", "--format=%h", span, "--", JOURNAL).split()), "trailer": trailer})

count = collections.Counter((r["shiploop"], r["journal"] > 0) for r in rows)
print(f"releases: {len(rows)}")
print(f"ship shiploop, journal commit in range: {count[(True, True)]}; none: {count[(True, False)]}")
print(f"do not ship shiploop, journal commit in range: {count[(False, True)]}; none: {count[(False, False)]}")
for label, chosen in (("since " + CUTOFF, [r for r in rows if r["shiploop"] and r["date"] >= CUTOFF]),
                      ("before " + CUTOFF, [r for r in rows if r["shiploop"] and r["date"] < CUTOFF])):
    print(f"shiploop releases {label}: {len(chosen)}; without a journal commit: {sum(1 for r in chosen if not r['journal'])}")
    for r in chosen:
        if label.startswith("since") and not r["journal"]:
            print(f"  {r['sha']} {r['date']} {r['commits']} commits in range: {r['trailer'][:70]}")
added = git("log", "--diff-filter=A", "--format=%h %as", "--", JOURNAL).split()
print("journal first added:", " ".join(added))
since_journal = [r for r in rows if r["shiploop"] and r["date"] >= added[1]]
print(f"shiploop releases since the journal existed ({added[1]}): {len(since_journal)}; "
      f"without a journal commit: {sum(1 for r in since_journal if not r['journal'])}")
print("releases that do not ship shiploop:")
for r in rows:
    if not r["shiploop"]:
        print(f"  {r['sha']} {r['date']} journal commits in range: {r['journal']}: {r['trailer'][:90]}")
