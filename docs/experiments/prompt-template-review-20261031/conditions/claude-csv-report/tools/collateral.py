import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner
from concurrent.futures import ThreadPoolExecutor
raw = json.load(open(runner.S + "/raw_all.json"))
cond = json.load(open(runner.CD + "/conditions.json"))
ids = [c["id"] for c in cond if c["candidate"]]
surv = [k for k in raw if not k.startswith("_")]
out = {}
for cid in surv:
    runner.clean()
    runner.apply(cid)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda i: (i, runner.witness(i)[0]), [i for i in ids if i != cid]))
    out[cid] = [i for i, rc in res if rc != 0]
    print(cid, "also violates:", out[cid], flush=True)
runner.clean()
json.dump(out, open(runner.S + "/collateral_all.json", "w"), indent=1)
