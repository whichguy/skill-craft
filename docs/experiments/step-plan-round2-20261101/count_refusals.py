#!/usr/bin/env python3
"""Exit-2 step-plan `check` rows per sample, split into refusals (an error field) and crashes (none), plus refused `complete`
rows (round 2's review, findings #5 to #7: `samples.refusals` reads shiploop_trace.refused, which leaves `check` out).

    python3 count_refusals.py ROOT [ROOT ...] > refusal_counts.txt

A crash row is the A1 AttributeError of the pre-b6b8f52a builds: the CLI died before writing an error, so the row has exit 2 and
no error field. The session logs name the AttributeError for each of them.
"""
import glob, json, sys
def rows(trace):
    for l in open(trace):
        try: yield json.loads(l)
        except ValueError: pass
def stage_of(e):
    s = e.get("stage"); return s[-1] if isinstance(s, list) else s
for root in sys.argv[1:]:
    print("==", root.split("20261101/")[-1])
    tot = {"ref": 0, "ref_samples": 0, "crash": 0, "crash_samples": 0}
    for trace in sorted(glob.glob(root + "/**/.shiploop-runs/*/run/trace.jsonl", recursive=True)):
        name = trace.split(root)[-1].split("/.shiploop-runs")[0].strip("/")
        checks = [e for e in rows(trace) if e.get("verb") == "check" and stage_of(e) == "step-plan" and str(e.get("exit")) == "2"]
        ref = [e.get("error", "")[:90] for e in checks if e.get("error")]
        crash = [i for i, e in enumerate([e for e in rows(trace) if e.get("verb") == "check" and stage_of(e) == "step-plan"])
                 if str(e.get("exit")) == "2" and not e.get("error")]
        comp = [(stage_of(e), str(e.get("error", ""))[:80]) for e in rows(trace) if e.get("verb") == "complete" and str(e.get("exit")) not in ("0", "None")]
        tot["ref"] += len(ref); tot["ref_samples"] += bool(ref); tot["crash"] += len(crash); tot["crash_samples"] += bool(crash)
        print(f"  {name}: refused checks {len(ref)} {ref} | crash rows {len(crash)} at step-plan check #{[c+1 for c in crash]} | refused completes {comp}")
    print("  TOTAL", tot)
