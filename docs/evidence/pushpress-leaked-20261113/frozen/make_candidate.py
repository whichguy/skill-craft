#!/usr/bin/env python3
"""Make a plugin payload that differs from the published one only in the description block of skills/pushpress/SKILL.md.
usage: make_candidate.py <published payload dir> <out payload dir> <description text file> [<source SKILL.md for the body; default: the published one>]"""
import importlib.util
import os
import pathlib
import re
import shutil
import sys
import textwrap

src, out, textfile = map(pathlib.Path, sys.argv[1:4])
body_src = pathlib.Path(sys.argv[4]) if len(sys.argv) > 4 else src / "skills" / "pushpress" / "SKILL.md"
if out.exists():
    sys.exit(f"{out} exists: choose a new name")
shutil.copytree(src, out)
desc = " ".join(textfile.read_text(encoding="utf-8").split())
block = "description: >-\n" + "\n".join("  " + ln for ln in textwrap.wrap(desc, width=118)) + "\n"
card = body_src.read_text(encoding="utf-8")
new, n = re.subn(r"^description:\s*>-?\s*\n(?:[ \t]+.*\n?)*", block, card, count=1, flags=re.M)
assert n == 1
(out / "skills" / "pushpress" / "SKILL.md").write_text(new, encoding="utf-8")
spec = importlib.util.spec_from_file_location("ppt", os.environ.get("PUSHPRESS_TEST_PY", "test/pushpress.test.py"))  # run from the repository root, or set the variable
ppt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppt)
raw = ppt.description(new)
print(f"description: folded {len(desc)} chars; raw block as the repo test measures it: {len(raw)} (cap 1024); contains PushPress: {'PushPress' in raw}")
# only the description block may differ from the card used as the body source
a = card.splitlines(); b = new.splitlines()
import difflib
changed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
print("changed lines (all inside the description block):", len(changed), "| first changed:", changed[0][:60] if changed else None)
