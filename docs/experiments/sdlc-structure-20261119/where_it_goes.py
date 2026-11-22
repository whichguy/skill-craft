#!/usr/bin/env python3
"""Where a whole delivery's time and tokens go (round 12). Reads metrics.json and
result.json of every run folder under the given roots; reads only.
A whole delivery is a run whose ShipLoop status is done. Prints, per driver:
time by phase, model calls, context size, token counts and what fills the context.
Usage: python3 -I where_it_goes.py <runs root> ...
"""
import collections
import json
import statistics
import sys
from pathlib import Path

PLANNING = ["intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare", "step-plan", "test-spec"]
BUILD = ["validate-existing", "implement", "test", "document", "carry-forward"]


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else float("nan")


def main(roots):
    rows = collections.defaultdict(list)
    for root in roots:
        for mpath in sorted(Path(root).glob("*/*/metrics.json")):
            folder = mpath.parent
            try:
                m = json.load(open(mpath)); r = json.load(open(folder / "result.json"))
            except (OSError, ValueError):
                continue
            ship = r.get("shiploop") or {}
            if ship.get("status") != "done":
                continue
            ver = (r.get("versions") or {}).get("shiploop_version")
            drv = f"{(r.get('model') or '?').split('-')[0]}@{r.get('effort')}"
            stages = m.get("stages") or []
            sec = collections.Counter()
            for s in stages:
                name = s.get("stage")
                grp = "planning" if name in PLANNING else "build" if name in BUILD else "after"
                sec[grp] += s.get("seconds") or 0
                sec[name] += s.get("seconds") or 0
            total = sum(s.get("seconds") or 0 for s in stages)
            peaks = [(s.get("context") or {}).get("peak") for s in stages if (s.get("context") or {}).get("peak")]
            calls = sum((s.get("context") or {}).get("calls") or 0 for s in stages)
            use = ((m.get("sessions") or [{}])[0].get("usage")) or {}
            tok = m.get("tokens") or {}
            cs = (m.get("context_summary") or {}).get("share") or {}
            imp = m.get("improve_reviews") or {}
            rev = sum((c.get("review_seconds") or 0) for c in imp.get("per_child") or [])
            rows[drv].append({
                "run": folder.name, "ver": ver, "total": total, "sec": sec, "steps": sum(1 for s in stages if s.get("stage") == "implement"),
                "nstages": len(stages), "calls": calls or m.get("model_calls"), "first": peaks[0] if peaks else None,
                "peak": max(peaks) if peaks else tok.get("input_peak"), "cost": m.get("cost_usd"),
                "read": use.get("cache_read_input_tokens"), "write": use.get("cache_creation_input_tokens"),
                "out": use.get("output_tokens") or tok.get("output"), "processed": tok.get("processed"),
                "share": cs, "review": rev, "edited": imp.get("edited_children"), "children": imp.get("children"),
            })
    for drv, rs in sorted(rows.items()):
        print(f"\n== {drv}: {len(rs)} whole deliveries; ShipLoop {dict(collections.Counter(r['ver'] for r in rs))}")
        print(f"  minutes in stages, median {med(r['total'] for r in rs)/60:.1f}; stage records {med(r['nstages'] for r in rs):.0f}; build steps {med(r['steps'] for r in rs):.0f}; model calls {med(r['calls'] for r in rs):.0f}")
        for grp in ("planning", "build", "after"):
            print(f"  {grp:9s} {100*med(r['sec'][grp]/r['total'] for r in rs if r['total']):4.0f}% of stage time (median)")
        for name in ("implement", "test", "document", "step-plan", "system-test-author", "spec", "test-strategy", "plan"):
            print(f"    {name:19s} {100*med(r['sec'][name]/r['total'] for r in rs if r['total']):4.1f}%   median {med(r['sec'][name] for r in rs):5.0f} s")
        print(f"  reviews: median {med(r['review'] for r in rs):.0f} s, {100*med(r['review']/r['total'] for r in rs if r['total']):.0f}% of stage time; edited {sum(r['edited'] or 0 for r in rs)} of {sum(r['children'] or 0 for r in rs)} reviewed results")
        print(f"  context tokens: at the first stage {med(r['first'] for r in rs):,.0f}, at the end {med(r['peak'] for r in rs):,.0f}")
        if any(r["read"] for r in rs):
            print(f"  tokens, medians: re-read from cache {med(r['read'] for r in rs):,.0f}; newly written {med(r['write'] for r in rs):,.0f}; output {med(r['out'] for r in rs):,.0f}; cost ${med(r['cost'] for r in rs):.2f}")
            print(f"  re-read tokens per model call, median {med(r['read']/r['calls'] for r in rs if r['read'] and r['calls']):,.0f}")
        else:
            print(f"  tokens, medians: processed {med(r['processed'] for r in rs):,.0f}; output {med(r['out'] for r in rs):,.0f}; cost {med(r['cost'] for r in rs)}")
        keys = sorted({k for r in rs for k in r["share"]}, key=lambda k: -med(r["share"].get(k, 0) for r in rs))
        print("  what the tool results put in the context (median share of bytes): " + ", ".join(f"{k} {100*med(r['share'].get(k, 0) for r in rs):.0f}%" for k in keys[:5]))


main(sys.argv[1:])
