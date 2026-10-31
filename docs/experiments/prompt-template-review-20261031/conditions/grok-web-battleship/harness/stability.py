import json, sys
sys.path.insert(0, ".")
import runall
from runall import *

NOISE = {"R-2 (TC-2) port", "TC-2 (a) empty PORT listens on 3000", "R-1 (TC-1) server listens"}
PORT_IDS = {"R-1.1", "R-2.1", "R-2.2", "R-2.3", "R-2.4", "R-2.5", "R-2.6", "R-2.7"}
PLAN = {"R-4.20": 30, "R-5.9": 30, "R-5.13": 60, "R-5.14": 30, "R-5.25": 30, "R-5.36": 60,
        "R-1.1": 4, "R-2.1": 4, "R-2.2": 4, "R-2.3": 4, "R-2.4": 4, "R-2.5": 4, "R-2.6": 4, "R-2.7": 4,
        "R-4.12": 12, "R-4.27": 6, "R-4.28": 6, "R-5.16": 6}

for i, n in PLAN.items():
    restore(); apply(i)
    genuine = noise = passes = 0
    names = {}
    for _ in range(n):
        r = suite_with_port_guard()[-1]
        if r["exit"] == 0:
            passes += 1
        elif i not in PORT_IDS and set(r["failing"]) <= NOISE:
            noise += 1
        else:
            genuine += 1
            for f in r["failing"]:
                names[f] = names.get(f, 0) + 1
    restore()
    rec = {"id": i, "runs": n, "pass": passes, "noise_only_failures": noise, "genuine_failures": genuine, "failing_tests": names}
    open(SCR + "/stability.jsonl", "a").write(json.dumps(rec) + "\n")
    print(rec, flush=True)
b = run_suite(); print("baseline exit", b["exit"], b["tests"])
