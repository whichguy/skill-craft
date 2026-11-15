import sys, os, glob
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
apex_runs = set(); tap_runs = set(); human_runs = set(); reg_tap = set()
for tf in files:
    rd = os.path.dirname(tf)
    hit = False; tap = False; human = False; regtap = False
    for p in glob.glob(os.path.join(rd, "packets", "sent", "*.md")):
        try: t = open(p, errors="replace").read()
        except Exception: continue
        if "apex run test" not in t: continue
        hit = True
        for line in t.splitlines():
            if "apex run test" in line:
                if "result-format tap" in line:
                    tap = True
                    if "[regression]" in line: regtap = True
                if "result-format human" in line or ("result-format" not in line): human = True
    if hit: apex_runs.add(tf)
    if tap: tap_runs.add(tf)
    if human: human_runs.add(tf)
    if regtap: reg_tap.add(tf)
print("runs whose packets list `sf apex run test`:", len(apex_runs))
print("  ...with --result-format tap on some row:", len(tap_runs))
print("  ...with a [regression] row on tap:", len(reg_tap))
print("  ...with a row that is not tap:", len(human_runs))
for tf in sorted(tap_runs)[:8]: print("   tap run:", tf.replace("/Users/dadleet/", "~/")[:110])
