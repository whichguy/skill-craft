import json, sys, re
from pathlib import Path
C = Path(sys.argv[1]); arm = sys.argv[2]
files = {"runtime-ephemeral.md": 27913, "technical-interactions.md": 9608, "elaborator.v1.md": None, "technical-lens-cards.md": None}
tot = {f: 0 for f in files}; n = 0; first = {f: [] for f in files}
for d in sorted((C/"runs").iterdir()):
    if f"-{arm}-" not in d.name: continue
    n += 1
    whole = {f: False for f in files}
    idx = 0
    for line in open(d/"events.jsonl"):
        try: e = json.loads(line)
        except Exception: continue
        it = e.get("item") or {}
        if e.get("type") != "item.completed" or it.get("type") != "command_execution": continue
        idx += 1
        cmd = it.get("command", ""); out = it.get("aggregated_output") or ""
        # split shell segments on ; && newline
        for seg in re.split(r";|&&|\n", cmd):
            seg = re.sub(r"^/bin/zsh -lc ", "", seg.strip()).strip("'\" ")
            for f in files:
                if re.match(r"^cat\s", seg) and f in seg and "|" not in seg:
                    if not whole[f]: first[f].append(idx)
                    whole[f] = True
    for f in files: tot[f] += whole[f]
print(arm, "runs", n, {f: tot[f] for f in files})
print("first whole-read command index (1-based)", {f: first[f] for f in ("runtime-ephemeral.md","technical-interactions.md")})
