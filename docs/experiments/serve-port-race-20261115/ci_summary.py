#!/usr/bin/env python3
"""The tables of the CI history: what ci_history.py collected, by suite, tier and Node version.

    python3 ci_summary.py ci-history.json[.gz]
"""

import collections
import gzip
import json
import sys

SUITES = ("shiploop-e2e-ticket-comments", "shiploop-e2e-ticket-sla", "shiploop-e2e-user-chain", "shiploop-e2e-user-directory",
          "shiploop-e2e-brownfield", "shiploop-e2e-brownfield-tickets", "shiploop-e2e-resources", "shiploop-e2e-quality")

path = sys.argv[1]
rows = json.load(gzip.open(path, "rt") if path.endswith(".gz") else open(path))
read = [r for r in rows if "unread" not in r]
print(f"{len(rows)} jobs ({len(rows) - len(read)} whose log could not be read), created {min(r['created'] for r in read)[:10]} to "
      f"{max(r['created'] for r in read)[:10]}, {len({r['run'] for r in read})} runs")
print("jobs:", dict(collections.Counter(r["job"] for r in read)))
print("node:", dict(collections.Counter(r["node"] for r in read)), " image:", dict(collections.Counter(r["image"] for r in read)))
first = {}
for r in read:
    first[r["node"]] = min(first.get(r["node"], "9"), r["created"])
print("first job on each node:", {node: when[:16] for node, when in sorted(first.items(), key=lambda kv: kv[1])})
print()
print(f"{'suite':34} {'executions':>10} {'OK':>4} {'FAIL':>4}   quick/full   by node")
for suite in SUITES:
    seen = [(r, r["suites"][suite]) for r in read if suite in r["suites"]]
    tiers = collections.Counter("quick" if r["job"].startswith("quick") else "full" for r, _ in seen)
    nodes = collections.defaultdict(collections.Counter)
    for r, result in seen:
        nodes[r["node"]][result] += 1
    count = collections.Counter(result for _, result in seen)
    print(f"{suite:34} {len(seen):10} {count['OK']:4} {count['FAIL']:4}   {tiers['quick']:3}/{tiers['full']:<3}      "
          + "; ".join(f"{node}: {dict(c)}" for node, c in sorted(nodes.items(), key=lambda kv: str(kv[0]))))
print()
hits = [r for r in read if r.get("collision_lines")]
print(f"jobs whose log names a port collision (before it listened on PORT / did not listen on PORT / answered by pid / EADDRINUSE / "
      f"address already in use): {len(hits)}")
for r in hits:
    print(f"  run {r['run']} attempt {r['attempt']} commit {r['commit']} {r['created'][:16]}Z {r['job']} {r['conclusion']} node {r['node']}")
    for line in r["collision_lines"][:2]:
        print("     ", line[:200])
