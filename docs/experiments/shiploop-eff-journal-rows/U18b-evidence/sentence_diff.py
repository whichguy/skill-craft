#!/usr/bin/env python3
"""U18b check: every sentence of the old Improve ShipLoop route card stands word for word in the new route files.

Reads the old card from Git (6ed81762, the base of the split), drops its headings, splits it into sentences and prints
those that no new route file (the core and its five case files) holds whitespace-normalized. At the split seven did not,
all rewritten on purpose: the old card's opening paragraph (four sentences, now the core's opening), the review inputs'
intro sentence (which said every input applies to every review; the file now opens each section on its condition), and two
sentences the one-pass stop rule (5e377ff7, owner 2026-10-20) had left stale in the card: the Exit rule's "one-pass exit"
Git check (the runtime applies it only to a gate of two or more) and the Assess step's "two distinct, consecutive" cycles
(review-policy.md says one).

Usage, from the repository root: python3 docs/experiments/shiploop-eff-journal-rows/U18b-evidence/sentence_diff.py
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REF = ROOT / "skills" / "improve" / "references"
NAMES = ("shiploop-route.md", "shiploop-route-rules.md", "shiploop-route-cases.md", "shiploop-route-recovery.md",
         "shiploop-route-ask-agent.md", "shiploop-review-inputs.md")
OLD = subprocess.check_output(["git", "-C", str(ROOT), "show", "6ed81762:skills/improve/references/shiploop-route.md"],
                              text=True)

old = "\n".join(line for line in OLD.split("\n") if not line.startswith("#"))
new = " ".join(" ".join((REF / name).read_text(encoding="utf-8").split()) for name in NAMES)
sentences = re.split(r"(?<=[.;:])\s+(?=[A-Z`*(\-\[])", " ".join(old.split()))
missing = [sentence for sentence in sentences if sentence.strip() and sentence not in new]
print(len(sentences), "sentences;", len(missing), "not word for word:")
for sentence in missing:
    print("-", sentence[:200])
