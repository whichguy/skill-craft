import json, sys
from pathlib import Path
d = Path(sys.argv[1]); pats = sys.argv[2:]
for line in open(d/"events.jsonl"):
    try: e = json.loads(line)
    except Exception: continue
    it = e.get("item") or {}
    if e.get("type") != "item.completed" or it.get("type") != "command_execution": continue
    cmd = it.get("command", "")
    if any(p in cmd for p in pats):
        out = it.get("aggregated_output") or ""
        print(f"[{it['id']}] len(out)={len(out)} exit={it.get('exit_code')}\n  CMD: {cmd[:600]}")
