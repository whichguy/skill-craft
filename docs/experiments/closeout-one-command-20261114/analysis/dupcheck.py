import json, sys, datetime, collections
cut = datetime.datetime(2026,10,29,15,0).timestamp()
INNER = {"step-plan","test-spec","validate-existing","implement","test","document","carry-forward"}
n_pairs = collections.Counter(); ms_wasted = collections.Counter(); n_actions = collections.Counter()
ms_all = collections.Counter(); stage_wall = collections.Counter()
for f in (l.strip() for l in open(sys.argv[1])):
    stage_of = {}; rows = collections.defaultdict(list); first = {}
    for line in open(f, errors="replace"):
        try: r = json.loads(line)
        except Exception: continue
        if r.get("ts", 0) < cut: continue
        a = r.get("action")
        if r.get("kind") == "packet": stage_of.setdefault(a, r.get("stage")); first.setdefault(a, r["ts"])
        if r.get("kind") == "command" and r.get("verb") in ("check", "complete") and stage_of.get(a) in INNER:
            rows[a].append(r)
    for a, rs in rows.items():
        st = stage_of[a]; n_actions[st] += 1
        end = next((r["ts"] for r in rs if r["verb"] == "complete" and r.get("exit") == 0), None)
        if end: stage_wall[st] += end - first[a]
        for r in rs:
            if r["verb"] == "check": ms_all[st] += r.get("ms", 0)
        for prev, cur in zip(rs, rs[1:]):
            if prev["verb"] == "check" and prev.get("exit") == 0 and cur["verb"] == "check":
                n_pairs[st] += 1; ms_wasted[st] += cur.get("ms", 0)
print("stage: actions | yes->check pairs | their script seconds | all check seconds | stage wall seconds")
for st in sorted(n_actions):
    print("%-18s %5d | %4d | %6.0f | %6.0f | %7.0f" % (st, n_actions[st], n_pairs[st], ms_wasted[st]/1000, ms_all[st]/1000, stage_wall[st]))
print("total pairs", sum(n_pairs.values()), "wasted seconds %.0f" % (sum(ms_wasted.values())/1000), "of all wall %.0f" % sum(stage_wall.values()))
