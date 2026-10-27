"""Scratch: the acceptance-set selection rule, fixed before any grading (seed 20261024).

Per kind (system-test, product-acceptance, release-verify, operations, improve-review), 6 artifacts:
  1. the shortest and the longest by word count (the thin and the full end of the range);
  2. seeded draws from Grok/Codex runs until 3 of the 6 come from those hosts (where enough exist);
  3. seeded draws from any host for the rest;
  at most 2 artifacts per source run within a kind and at most 4 per source run overall.
Eligible: outer kinds need a ShipLoop rerun record in the facts block; reviews always carry pass records.
"""
import json, random, sys
from collections import Counter
from pathlib import Path

pool = [json.loads(l) for l in open(sys.argv[1])]
host = {}
for a in pool:
    r = a["source"]["run"]
    if r not in host:
        host[r] = json.loads((Path(r) / "invocation.json").read_text()).get("host")
    a["host"] = host[r]
rnd = random.Random(20261024)
per_run = Counter()
chosen = []
for kind in ("system-test", "product-acceptance", "release-verify", "operations", "improve-review"):
    c = [a for a in pool if a["kind"] == kind and (kind == "improve-review" or "ShipLoop record" in a["facts"])]
    c.sort(key=lambda a: (a["words"], a["id"]))
    mine, kind_run = [], Counter()

    def ok(a):
        r = a["source"]["run"]
        return a not in mine and kind_run[r] < 2 and per_run[r] < 4

    def take(a):
        mine.append(a); kind_run[a["source"]["run"]] += 1; per_run[a["source"]["run"]] += 1

    for a in (c[0], c[-1]):
        if ok(a):
            take(a)
    rest = c[1:-1]; rnd.shuffle(rest)
    for a in rest:
        if len(mine) >= 6 or sum(x["host"] != "claude" for x in mine) >= 3:
            break
        if a["host"] != "claude" and ok(a):
            take(a)
    for a in rest:
        if len(mine) >= 6:
            break
        if ok(a):
            take(a)
    chosen += mine
    print(kind, "eligible", len(c), "hosts", dict(Counter(a["host"] for a in c)))
for a in chosen:
    print(f"{a['kind']:20} {a['host']:7} {a['words']:4}w facts {a['facts_words']:4}w {a['id']}")
Path(sys.argv[2]).write_text("\n".join(a["id"] for a in chosen) + "\n")
json.dump([{k: a[k] for k in ("id", "kind", "slot", "case", "host", "words", "facts_words", "sha")} | {"run": a["source"]["run"]}
           for a in chosen], open(sys.argv[3], "w"), indent=1)
