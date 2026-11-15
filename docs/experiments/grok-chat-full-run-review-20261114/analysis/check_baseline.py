import json, sys, datetime, statistics, collections
cut = datetime.datetime(2026, 10, 29, 15, 0).timestamp()
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
per_run = []; stage_tot = collections.Counter(); stage_n = collections.Counter()
long_calls = 0; n_calls = 0
for f in files:
    stage_of = {}; tot = 0.0; any_cmd = False; longs = 0
    try: lines = open(f, errors="replace").read().splitlines()
    except Exception: continue
    for line in lines:
        try: r = json.loads(line)
        except Exception: continue
        if r.get("ts", 0) < cut: continue
        if r.get("kind") == "packet": stage_of[r.get("action")] = r.get("stage")
        if r.get("kind") != "command" or r.get("verb") != "check": continue
        any_cmd = True
        ms = (r.get("ms") or 0) / 60000
        tot += ms
        st = stage_of.get(r.get("action")) or "?"
        stage_tot[st] += ms; stage_n[st] += 1
        n_calls += 1
        if ms >= 100/60: longs += 1; long_calls += 1
    if any_cmd: per_run.append((tot, longs))
tots = sorted(t for t, _ in per_run)
def pct(p): return tots[min(len(tots)-1, int(len(tots)*p))]
print("runs with >=1 check since 2026-10-29:", len(tots))
print(f"check minutes per run: median {statistics.median(tots):.1f}  p75 {pct(.75):.1f}  p90 {pct(.90):.1f}  p95 {pct(.95):.1f}  max {tots[-1]:.1f}")
print("this trial: 99.6 min ->", f"{sum(1 for t in tots if t < 99.6)} of {len(tots)} earlier runs spent less ({sum(1 for t in tots if t < 99.6)/len(tots)*100:.0f}th percentile)")
print(f"check calls: {n_calls}; calls >= 100 s: {long_calls} ({long_calls/n_calls*100:.1f}%); runs with a >=100 s check: {sum(1 for _, l in per_run if l)}")
print("\nper stage (all runs): calls / minutes / mean seconds")
for st, m in sorted(stage_tot.items(), key=lambda kv: -kv[1])[:8]:
    print(f"   {st:20} {stage_n[st]:>5} calls  {m:8.1f} min  mean {m*60/stage_n[st]:6.1f}s")
