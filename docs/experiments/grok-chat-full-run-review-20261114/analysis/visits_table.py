import json, sys
o = json.load(open(sys.argv[1]))
run = list(o["docs"]["runs"].values())[0]
st = run["stages"]
cum = 0.0
print(f"{'#':>2} {'action':8} {'stage':18} {'min':>6} {'cum':>6} {'outcome':10} {'calls':>5} {'ctx%':>5} {'cmp':>3} {'pktKB':>6} {'impr':>5} evid")
for i, s in enumerate(st, 1):
    c = s.get("context") or {}
    imp = (s.get("improve") or {})
    cum += s["min"]
    print(f"{i:>2} {s['action'][4:12]:8} {s['stage']:18} {s['min']:>6.1f} {cum:>6.1f} {str(s['outcome']):10} {c.get('calls','-'):>5} {c.get('peakPct','-'):>5} {c.get('compactions',0):>3} {(s.get('packetBytes') or 0)/1024:>6.1f} {imp.get('min','-') if imp else '-':>5} {s.get('evidenceClass')}")
print("total min:", round(cum, 1))
from collections import defaultdict
by = defaultdict(lambda: [0, 0.0])
for s in st:
    by[s["stage"]][0] += 1; by[s["stage"]][1] += s["min"]
print()
for k, (n, m) in sorted(by.items(), key=lambda kv: -kv[1][1]):
    print(f"  {k:18} visits {n:>2}  {m:>6.1f} min")
