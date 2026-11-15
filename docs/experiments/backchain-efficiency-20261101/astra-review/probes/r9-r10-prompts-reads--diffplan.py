import json, sys
from pathlib import Path
a = json.loads(Path(sys.argv[1]).read_text()); b = json.loads(Path(sys.argv[2]).read_text())
sa = {s["id"]: s for s in a["steps"]}; sb = {s["id"]: s for s in b["steps"]}
for k in ("goal","initial_state","goal_needs","unresolved"):
    if a.get(k) != b.get(k): print(f"[{k}] A={json.dumps(a.get(k))}\n      B={json.dumps(b.get(k))}")
for i in sorted(set(sa)|set(sb)):
    if i not in sa: print(f"+ step {i}: {sb[i]['statement']}\n   produces={sb[i]['produces']}\n   inputs={[(x['need'][:80],x['from']) for x in sb[i]['inputs']]}"); continue
    if i not in sb: print(f"- step {i}: {sa[i]['statement']}"); continue
    for f in ("statement","produces","inputs","confirm"):
        if sa[i].get(f) != sb[i].get(f):
            if f=="inputs":
                ea={(x['need'],x['from']) for x in sa[i]['inputs']}; eb={(x['need'],x['from']) for x in sb[i]['inputs']}
                for e in eb-ea: print(f"~ {i}.inputs + {e[1]} <- {e[0][:110]}")
                for e in ea-eb: print(f"~ {i}.inputs - {e[1]} <- {e[0][:110]}")
            elif f=="confirm":
                print(f"~ {i}.confirm changed")
            else:
                print(f"~ {i}.{f}: {json.dumps(sa[i].get(f))[:200]}\n      -> {json.dumps(sb[i].get(f))[:200]}")
