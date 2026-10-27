"""Per work item of each recorded run: its steps' declared paths, and how many path groups they form.

`groups` joins every two steps that share a path (connected components of the overlap graph); `runs` joins only
consecutive steps. A step with no paths of its own works on the item's (shiploop_loops.implement_scope).

Usage: python3 item_width.py ~/e2e-runs/2026102*/*/
"""
import itertools
import json
import re
import sys
from pathlib import Path


def state(path):
    m = re.search(r"```shiploop-state\n(.*?)\n```", path.read_text(errors="replace"), re.DOTALL)
    return json.loads(m.group(1)) if m else None


def groups(steps):
    parent = list(range(len(steps)))

    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i

    for i in range(len(steps)):
        for j in range(i):
            if set(steps[i]) & set(steps[j]):
                parent[find(i)] = find(j)
    return len({find(i) for i in range(len(steps))})


def runs(steps):
    return (1 if steps else 0) + sum(not (set(a) & set(b)) for a, b in itertools.pairwise(steps))


for run in sys.argv[1:]:
    for results in sorted(Path(run).glob(".shiploop-runs/*/run/results")):
        latest = {}  # the last done step-plan result of each item
        for f in sorted(results.glob("*.md"), key=lambda p: p.stat().st_mtime):
            d = state(f)
            if not d or d.get("stage") != "step-plan" or (d.get("result") or {}).get("outcome") != "done":
                continue
            latest[d.get("workitem")] = (d["result"].get("steps") or [], list(d["result"].get("paths") or []))
        for item, (steps, item_paths) in latest.items():
            paths = [list(s.get("paths") or []) or item_paths for s in steps]
            print(f"{Path(run).name:42} {item:4} steps={len(steps)} groups={groups(paths)} runs={runs(paths)} "
                  + " | ".join(f"{s.get('id')}:{','.join(p)}" for s, p in zip(steps, paths)))
