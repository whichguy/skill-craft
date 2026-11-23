"""Print what one `codex debug prompt-input` rendering shows of skills: the skill roots, every probe-* skill
listed (with its short path), how many other skills are listed, and whether the AGENTS.md text naming the
named folder reached the input."""
import json
import re
import sys

items = json.load(open(sys.argv[1], encoding="utf-8"))
texts = []
for item in items:
    for part in item.get("content") or []:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            texts.append(part["text"])
skills = next((t for t in texts if t.startswith("<skills_instructions>")), "")
roots = re.findall(r"^- `(r\d+)` = `([^`]+)`", skills, re.M)
listed = re.findall(r"^- ([A-Za-z0-9_.:-]+): .*?\(file: ([^)]+)\)$", skills, re.M)
for key, path in roots:
    print(f"   root {key} = {path.split('/skills-discovery/probe/')[-1]}")
probes = [(name, path) for name, path in listed if name.startswith("probe-")]
for name, path in probes:
    print(f"   listed {name}  ({path})")
print(f"   other skills listed: {len(listed) - len(probes)}")
agents = [t for t in texts if t.startswith("# AGENTS.md instructions for")]
print("   AGENTS.md text in input: " + ("yes, names shiploop-skills/" if any("shiploop-skills/" in t for t in agents)
                                       else ("yes" if agents else "no")))
