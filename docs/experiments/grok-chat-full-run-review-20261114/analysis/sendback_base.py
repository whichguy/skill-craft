import json, sys, datetime, collections
cut = datetime.datetime(2026, 10, 29, 15, 0).timestamp()
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
EXIT = collections.Counter(); runs_with = collections.defaultdict(set); runs_seen = set()
for f in files:
    try: lines = open(f, errors="replace").read().splitlines()
    except Exception: continue
    for line in lines:
        try: r = json.loads(line)
        except Exception: continue
        if r.get("ts", 0) < cut: continue
        if r.get("kind") != "command" or r.get("verb") != "complete" or r.get("exit") != 0: continue
        st = r.get("stage")
        if not (isinstance(st, list) and len(st) == 2): continue
        a, b = st
        if a not in ("implement", "test"): continue
        runs_seen.add(f)
        kind = "send-back/replan" if b in ("step-plan", "test-spec", "plan") or (a == "test" and b == "implement") else "advance"
        EXIT[(a, kind)] += 1
        if kind != "advance": runs_with[a].add(f)
for a in ("implement", "test"):
    adv = EXIT[(a, "advance")]; sb = EXIT[(a, "send-back/replan")]
    print(f"{a:10} accepted exits: {adv+sb:>5}  send-back/replan: {sb:>4} ({sb/max(adv+sb,1)*100:4.1f}%)  runs with >=1: {len(runs_with[a])} of {len(runs_seen)}")
