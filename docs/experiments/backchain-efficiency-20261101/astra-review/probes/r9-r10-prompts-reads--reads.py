import json, sys, re
from pathlib import Path
C = Path(sys.argv[1])
targets = ["runtime-ephemeral.md", "technical-interactions.md", "technical-lenses.md", "technical-lens-cards.md", "convergence.md", "caller-contract.md", "elaborator.v1.md", "dependency-review.prompt.md", "convergence-review.prompt.md", "ADAPTER.md", "SKILL.md", "direct.v1.md"]
for d in sorted((C/"runs").iterdir()):
    if f"-{sys.argv[2]}-" not in d.name: continue
    hits = {t: [] for t in targets}
    for line in open(d/"events.jsonl"):
        try: e = json.loads(line)
        except Exception: continue
        it = e.get("item") or {}
        if e.get("type") != "item.completed" or it.get("type") != "command_execution": continue
        cmd = it.get("command", "")
        for t in targets:
            if t in cmd:
                # classify read mode for this file
                seg = cmd
                mode = "cat" if re.search(r"cat\s+[^;|&]*"+re.escape(t), cmd) else ("sed" if re.search(r"sed\s+-n\s+'[^']*'\s+[^;|&]*"+re.escape(t), cmd) else ("rg/grep" if re.search(r"(rg|grep)[^;|&]*"+re.escape(t), cmd) else "other"))
                if mode == "sed":
                    m = re.search(r"sed\s+-n\s+'([^']*)'\s+[^;|&]*"+re.escape(t), cmd); mode = "sed " + m.group(1)
                hits[t].append(mode)
    print(d.name, {k.replace(".md",""): v for k, v in hits.items() if v and k in ("runtime-ephemeral.md","technical-interactions.md","elaborator.v1.md","convergence.md","technical-lens-cards.md")})
