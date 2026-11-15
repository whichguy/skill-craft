"""One trial's own ShipLoop trace: CLI time by verb and stage, every command of 100 s or more, every refusal with
its message, and how many packet prints were reprints.

    python3 -I trial_trace.py RUN_DIR/.shiploop-runs/<id>/run/trace.jsonl

Reads only ``trace.jsonl`` (ShipLoop's own record: kind packet / command, with ``ms``, ``exit``, ``error``).
"""
import collections
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1])]
cmds = [r for r in rows if r.get("kind") == "command"]


def stage_of(r):
    st = r.get("stage")
    return st[0] if isinstance(st, list) else st


print("ShipLoop commands recorded in the trace:", len(cmds))
by_verb = collections.defaultdict(lambda: [0, 0.0])
by_stage = collections.defaultdict(lambda: [0, 0.0, 0])
for r in cmds:
    ms = r.get("ms") or 0
    by_verb[r["verb"]][0] += 1
    by_verb[r["verb"]][1] += ms / 60000
    s = stage_of(r)
    by_stage[s][0] += 1
    by_stage[s][1] += ms / 60000
    if r.get("exit") not in (0, None):
        by_stage[s][2] += 1
print("total ShipLoop CLI time: %.1f min" % sum(v[1] for v in by_verb.values()))
for k, (n, m) in sorted(by_verb.items(), key=lambda kv: -kv[1][1]):
    print("  verb %-12s n=%3d %7.1f min" % (k, n, m))
print()
for k, (n, m, bad) in sorted(by_stage.items(), key=lambda kv: -kv[1][1]):
    if m > 0.2:
        print("  stage %-20s n=%3d %7.1f min   refused/nonzero %d" % (k, n, m, bad))
print("\ncommands >= 100 s:")
for r in cmds:
    if (r.get("ms") or 0) >= 100000:
        print("  %sZ %-9s %-18s %6.0fs exit=%s action=%s" % (
            r["at"][11:19], r["verb"], stage_of(r), r["ms"] / 1000, r.get("exit"), r["action"][4:12]))

errs = [(i + 1, r) for i, r in enumerate(rows) if "error" in r]
print("\nrefusals: %d (trace line, time, verb, stage, first 300 characters of the message)" % len(errs))
for ln, r in errs:
    print("  [%3d] %sZ %-8s %-18s %s" % (ln, r["at"][11:19], r.get("verb"), stage_of(r),
                                        r["error"].replace("\n", " ")[:300].rstrip()))

pk = [(i, r) for i, r in enumerate(rows) if r.get("kind") == "packet"]
seen, first, again, fchars, rchars = {}, 0, 0, 0, 0
for i, r in pk:
    if r["action"] in seen:
        again += 1
        rchars += r.get("printed", 0)
    else:
        first += 1
        fchars += r.get("printed", 0)
    seen[r["action"]] = i
print("\npacket prints: %d first prints (%.0f KB), %d reprints (%.0f KB, %.0f%% of printed text)" % (
    first, fchars / 1024, again, rchars / 1024, rchars / max(fchars + rchars, 1) * 100))
