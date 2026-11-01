#!/usr/bin/env python3
"""Break down start_routes.py's JSON: which start command did the model choose first, by request and host?

    python3 -I start_routes.py --since 2026-10-24 --json routes.json && python3 -I recount.py routes.json

The 51 `init` rows of the case hello-startup-contract are another session's evaluator fixtures (a scripted start, not a
model's choice) and are left out of the model-chosen counts; they are listed so the exclusion can be checked.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

rows = json.loads(Path(sys.argv[1]).read_text())
fixture = [r for r in rows if r["case"] == "hello-startup-contract" and r["start"] == "direct"]
model = [r for r in rows if r["start"] and r not in fixture]
print(f"runs with an event stream since 2026-10-24: {len(rows)}; with a ShipLoop start found: {sum(bool(r['start']) for r in rows)}")
print(f"left out as scripted fixtures (hello-startup-contract, init): {len(fixture)}")
where = Counter(r["run"].split("/")[1] + "/" + "/".join(r["run"].split("/")[2:4]) for r in fixture)
for place, n in where.most_common(4):
    print(f"   {n:3d}  {place}")
print()
print("model-chosen first start by host:")
for host in sorted({r["host"] for r in model}):
    c = Counter(r["start"] for r in model if r["host"] == host)
    print(f"   {host:6s} workspace {c['workspace']:3d}  direct {c['direct']:3d}")
print()
print("Codex, by request kind (Salesforce prompts name the org and say the project root is the current directory):")
for label, pick in (("Salesforce cases", lambda r: "salesforce" in (r["case"] or "")),
                    ("all other cases", lambda r: "salesforce" not in (r["case"] or ""))):
    c = Counter(r["start"] for r in model if r["host"] == "codex" and pick(r))
    n = c["workspace"] + c["direct"]
    print(f"   {label:17s} workspace {c['workspace']:3d}  direct {c['direct']:3d}  ({c['direct']}/{n})")
print()
print("every model-chosen direct start:")
for r in model:
    if r["start"] == "direct":
        print(f"   {r['case']:26s} {r['host']} {r['model']} {r['effort']:6s} folder check: {r['folder_check'] or '-':7s} {r['run'][-60:]}")
