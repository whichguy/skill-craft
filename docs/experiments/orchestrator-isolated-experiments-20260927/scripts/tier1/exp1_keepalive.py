"""Exp 1: what ends a keepalive continuation chain?  Drives _decide with the real hook-status."""
import json, sys
from common import *
import shiploop_keepalive as ka

def chain(label, host, between, n=20, waiting=False):
    repo, run = fixture("ka-")
    binding = {"run_dir": str(run), "run_id": state(run)["run_id"]}
    rows = []
    for i in range(1, n + 1):
        note = between(run, i)
        d = ka._decide(host, "sess-" + label, binding, waiting=waiting)
        rows.append((i, note, d["decision"], d.get("why", "")[:70]))
        if d["decision"] == "allow":
            break
    print(f"\n## {label} (host={host}, waiting={waiting})")
    for r in rows: print("  ", r)
    return rows

nothing = lambda run, i: "no callback"
def refused(run, i):
    code, out, err = submit(run, {"outcome": "bogus", "summary": "x"})
    return f"refused rc={code}"
def accept_every_3(run, i):
    if i % 3 == 0:
        s = state(run); code, out, err = submit(run, {"outcome": "done", "summary": "Synthetic."})
        return f"done rc={code} rev={state(run)['revision']}"
    code, out, err = submit(run, {"outcome": "bogus", "summary": "x"})
    return "refused"

chain("A no callback between stops", "claude", nothing)
chain("B refused callback between stops", "claude", refused, n=20)
chain("B' refused callbacks, grok", "grok", refused, n=20)
chain("C waiting background task, no progress", "claude", nothing, n=30, waiting=True)
chain("D accepted every third stop", "claude", accept_every_3, n=24)
