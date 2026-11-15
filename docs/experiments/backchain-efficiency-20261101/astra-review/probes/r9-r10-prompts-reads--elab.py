import json, sys, re
from pathlib import Path
C = Path(sys.argv[1])
for d in sorted((C/"runs").iterdir()):
    if "-candidate-" not in d.name: continue
    a = d/"artifacts"; rd = next(a.rglob("run.json")).parent
    run = json.loads((rd/"run.json").read_text())
    has_draft = (rd/"input/draft.json").is_file(); has_caller = (rd/"input/caller.json").is_file()
    routeset = "REVISING" if (has_caller and has_draft) else ("ELABORATING" if has_draft else "DRAFTING")
    idx = 0; elab_idx = []; direct_idx = []; dr_write = None; prepare_out = None
    for line in open(d/"events.jsonl"):
        try: e = json.loads(line)
        except Exception: continue
        it = e.get("item") or {}
        if e.get("type") != "item.completed" or it.get("type") != "command_execution": continue
        idx += 1; cmd = it.get("command", "")
        for seg in re.split(r";|&&|\n", cmd):
            seg = re.sub(r"^/bin/zsh -lc ", "", seg.strip()).strip("'\" ")
            if re.match(r"^cat\s", seg) and "|" not in seg:
                if "elaborator.v1.md" in seg: elab_idx.append(idx)
                if "direct.v1.md" in seg: direct_idx.append(idx)
        if "dependency-review" in cmd and ("write" in cmd or ">" in cmd or "dump" in cmd) and dr_write is None and "cat resources" not in cmd[:60]:
            dr_write = idx
    drs = list(a.rglob("dependency-review*.json"))
    kept = len(json.loads(drs[0].read_text()).get("questions", [])) if drs else None
    print(f"{d.name:48s} {run['route']:12s} {routeset:11s} kept={kept} direct@{direct_idx} elaborator@{elab_idx} dr_written@{dr_write}")
