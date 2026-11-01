#!/usr/bin/env python3
"""Probe, read-only: run the brownfield-tickets suite's own graded() once, with every first-pass disagreement logged.

    python3 flake_probe.py WORKTREE_ROOT [TAG]

Prints one JSON line: seconds, the regraded list (what the suite itself counts, at most 4 allowed) and, for each first-pass
disagreement, its kind (accepted, pristine or suite), case, variant and what the failing run printed. The suite's temporary
folders are removed at the end, because graded() leaves that to unittest's module cleanup, which a probe does not run.
"""

import importlib.util
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]).resolve()
tag = sys.argv[2] if len(sys.argv) > 2 else ""
sys.path.insert(0, str(root / "test"))  # the suite is run as a script from test/, so its own directory leads sys.path
spec = importlib.util.spec_from_file_location("bt_probe", root / "test" / "shiploop-e2e-brownfield-tickets.test.py")
module = importlib.util.module_from_spec(spec)
sys.modules["bt_probe"] = module
spec.loader.exec_module(module)

if os.environ.get("PROBE_POOL"):
    module.POOL = int(os.environ["PROBE_POOL"])  # graded() reads the module global when it runs
original = module.agrees
seen = []


def spy(case, variant, kind, result):
    ok = original(case, variant, kind, result)
    if not ok:
        if kind == "accepted":
            rows = result.get("checks", [])
            detail = {"observed": result.get("observed"), "failed": sorted(r["id"] for r in rows if not r["pass"]),
                      "notes": {r["id"]: (r.get("note") or "")[:260] for r in rows if not r["pass"]}}
        else:
            text = (result.stdout or "") + "\n" + (result.stderr or "")
            keep = [ln.strip() for ln in text.splitlines()
                    if re.search(r"✖|not ok|Error|code:|ECONN|hang up|timed out|failureType|expected|actual|duration_ms: ?\d{4,}", ln)]
            detail = {"summary": module.failing(result)[:200], "excerpt": " | ".join(keep[:16])[:2000]}
        seen.append({"kind": kind, "case": case.name, "variant": variant, "detail": detail})
    return ok


module.agrees = spy
started = time.time()
done = module.graded()
elapsed = round(time.time() - started, 1)
tmp = next(iter(done["deliveries"].values())).parents[1]
print(json.dumps({"tag": tag, "load": os.getloadavg()[0], "pool": module.POOL, "seconds": elapsed, "regraded": done["regraded"],
                  "first_pass_disagreements": seen, "servers_left": sorted(done["groups"], key=str)}, default=str))
shutil.rmtree(tmp, ignore_errors=True)
