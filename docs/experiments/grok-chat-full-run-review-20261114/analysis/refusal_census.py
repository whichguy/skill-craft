import json, sys, re, collections, datetime
cut = datetime.datetime(2026, 10, 29, 15, 0).timestamp()
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
INNER = {"step-plan","test-spec","validate-existing","implement","test","document","carry-forward","system-test-author","system-test"}
runs_with_cmds = set()
timeouts = collections.Counter()           # (verb, tail) -> n
timeout_runs = collections.defaultdict(set)
uncounted = collections.Counter(); uncounted_runs = set(); unc_heads = collections.Counter()
mut = 0; mut_runs = set(); mut_files = 0; mut_testish = 0; mut_testish_runs = set()
fix_after_nov = 0
for f in files:
    try:
        lines = open(f, errors="replace").read().splitlines()
    except Exception:
        continue
    stage_of = {}
    for line in lines:
        try: r = json.loads(line)
        except Exception: continue
        if r.get("ts", 0) < cut: continue
        if r.get("kind") == "packet": stage_of[r.get("action")] = r.get("stage")
        if r.get("kind") != "command": continue
        runs_with_cmds.add(f)
        e = r.get("error")
        if not isinstance(e, str): continue
        verb = r.get("verb")
        if "reached no verdict about the product" in e:
            if "No command reached a verdict about the product" in e: tail = "neutral sentence"
            elif "Fix the code so every command passes" in e: tail = "'Fix the code so every command passes'"
            elif "Fix the code (or a test" in e: tail = "'Fix the code (or a test...)'"
            else: tail = "other"
            timeouts[(verb, tail)] += 1; timeout_runs[(verb, tail)].add(f)
        if "could not read how many tests it ran" in e:
            uncounted[verb] += 1; uncounted_runs.add(f)
            m = re.search(r"\[(?:regression|focused)\] (.{0,60})", e)
            if m: unc_heads[m.group(1)[:40]] += 1
        if "mutants of this item's changed product lines survived" in e:
            mut += 1; mut_runs.add(f)
            for path in re.findall(r"^- (\S+?):\d+:\d+:", e, re.M):
                mut_files += 1
                if re.search(r"(?i)(^|/)(tests?|__tests__|spec)/|test[^/]*\.[a-z]+$|[._-]test\.|[._-]spec\.|Test\.", path):
                    mut_testish += 1; mut_testish_runs.add(f)
print("traces read:", len(files), " runs with ShipLoop commands since 2026-10-29:", len(runs_with_cmds))
print("\nTIMEOUT ('reached no verdict about the product') refusals:")
if not timeouts:
    print("   none in any retained run")
for k, v in sorted(timeouts.items(), key=lambda kv: -kv[1]):
    print(f"   verb={k[0]:9} tail={k[1]:40} n={v:>3} in {len(timeout_runs[k])} runs")
print("\nUNCOUNTED ('could not read how many tests it ran'):", dict(uncounted), "in", len(uncounted_runs), "runs")
print("   most common command heads:", unc_heads.most_common(6))
print("\nMUTATION refusals:", mut, "in", len(mut_runs), "runs; mutants listed:", mut_files, "; in test-looking files:", mut_testish, "(", len(mut_testish_runs), "runs )")
