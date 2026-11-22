#!/usr/bin/env python3
"""Count refused ShipLoop commands across run folders (round 11). Reads only.

A refusal is a `command` record in a run's trace.jsonl with a non-zero exit and
an `error` text. Each is put in a named class. For each class: how many, in how
many runs, of how many runs that ran a command at that stage, and the time from
the refusal to the next accepted check, complete or review command (an upper
bound on its cost: any real work done in between is counted too). Then the rate
of five classes per ShipLoop version and driver, and the cost per whole
delivery (a run that reached the operations stage).
Usage: python3 -I refusal_census.py <runs root> ...
"""
import collections, json, re, statistics, sys
from pathlib import Path

GROUPS = [
    ("mutation check: a changed line's mutant survived", r"mutation check"),
    ("step proof names a file the base lacks and no earlier step declares", r"Proof runs .* which the item base does not have"),
    ("requirements file edited beyond this step's lines (restore to HEAD)", r"^Restore .* to what HEAD holds"),
    ("test strategy: no unit or component row", r"no unit or component row"),
    ("step paths with no expectation listing them", r"step paths have no expectation"),
    ("implement result: not_covered shape", r"^not_covered is"),
    ("implement result: learned shape", r"^learned is a list"),
    ("implement result: unsupported fields", r"unsupported fields"),
    ("review pass: record how the changed result was checked", r"record how you checked the changed result"),
    ("review pass: add a 'Regression test' line", r"Regression test"),
    ("plan: concern owner_stage not an allowed stage", r"owner_stage must be one of"),
    ("plan: concern rows missing or misshaped", r"every concern needs a row|a concern that does not apply is|maps the concerns of every"),
    ("test run or base run failed (tests red)", r"ShipLoop (test|base) run"),
    ("step plan: focused command only searches text", r"only searches text"),
    ("step plan: criterion without its own test command or ID", r"needs a test command that confirms|no focused test ID|criteria must be a nonempty"),
    ("evidence_refs cite files that do not exist", r"evidence_refs cite files"),
    ("add assumptions/decisions/cases to a file", r"^Add (assumptions|decisions|the missing cases)"),
    ("review: no bound stage / run the review first / loop ended", r"no bound current Improve|Run the improve skill|loop has already ended|receipt is not complete|loop is still active"),
    ("review pass left files uncommitted", r"left files uncommitted"),
    ("step plan: proof must be one command line", r"proof must be one nonblank command line"),
    ("step plan: open plan assumptions due here", r"open plan assumptions"),
]

def group(err):
    for name, rx in GROUPS:
        if re.search(rx, err):
            return name
    return "other"

def main(roots):
    reached = collections.Counter()
    g = collections.defaultdict(lambda: {"n": 0, "runs": set(), "wait": [], "ver": collections.Counter(), "drv": collections.Counter(), "stage": collections.Counter()})
    nruns = 0; total_wait = 0.0; span = 0.0
    for root in roots:
        for trace in sorted(Path(root).glob("*/*/.shiploop-runs/*/run/trace.jsonl")):
            folder = trace.parents[3]
            try: inv = json.load(open(folder / "invocation.json"))
            except Exception: inv = {}
            recs = []
            for line in open(trace, errors="replace"):
                try: r = json.loads(line)
                except ValueError: continue
                if r.get("kind") == "command": recs.append(r)
            if not recs: continue
            nruns += 1
            span += recs[-1]["ts"] - recs[0]["ts"]
            ver = (inv.get("versions") or {}).get("shiploop_version")
            drv = f"{inv.get('model')}@{inv.get('effort')}"
            for st in {(r.get("stage") or [None])[0] for r in recs}: reached[st] += 1
            for i, r in enumerate(recs):
                if r.get("exit") in (0, None) or not r.get("error"): continue
                st = (r.get("stage") or [None])[0]
                name = group(r["error"])
                wait = None
                for n in recs[i + 1:]:
                    if n.get("exit") == 0 and n.get("verb") in ("check", "complete", "improve-pass", "improve-commit"):
                        wait = n["ts"] - r["ts"]; break
                e = g[name]; e["n"] += 1; e["runs"].add(str(folder)); e["ver"][ver] += 1; e["drv"][drv.split("-")[0] + "@" + drv.split("@")[1]] += 1; e["stage"][st] += 1
                if wait is not None: e["wait"].append(wait); total_wait += wait
    print(f"runs with commands: {nruns}; traced span {span/3600:.1f} h; time from a refusal to the next accepted command, summed: {total_wait/3600:.1f} h ({100*total_wait/span:.0f}%)")
    print("runs reaching stage:", dict(sorted(reached.items(), key=lambda kv: (-kv[1], str(kv[0])))))
    print(f"\n{'n':>4} {'runs':>4} {'of':>4} {'med s':>6} {'sum min':>7}  class | stage | versions | drivers")
    for name, e in sorted(g.items(), key=lambda kv: (-sum(kv[1]["wait"]), kv[0])):
        st = e["stage"].most_common(1)[0][0]
        med = statistics.median(e["wait"]) if e["wait"] else 0
        print(f"{e['n']:4d} {len(e['runs']):4d} {reached[st]:4d} {med:6.0f} {sum(e['wait'])/60:7.0f}  {name} | {st} | {dict(e['ver'])} | {dict(e['drv'])}")



RATES = {"proof": ("step-plan", r"Proof runs .* which the item base does not have"),
         "restore": ("document", r"^Restore .* to what HEAD holds"),
         "mutation": ("test", r"mutation check"),
         "layers": ("test-strategy", r"no unit or component row"),
         "owner_stage": ("plan", r"owner_stage must be one of")}
OWN_WORK = r"mutation check|ShipLoop (test|base) run|step proof"
ACCEPTS = ("check", "complete", "improve-pass", "improve-commit")


def rates(roots):
    den = collections.Counter(); hit = collections.Counter(); whole = []
    for root in roots:
        for trace in sorted(Path(root).glob("*/*/.shiploop-runs/*/run/trace.jsonl")):
            folder = trace.parents[3]
            try: inv = json.load(open(folder / "invocation.json"))
            except Exception: inv = {}
            ver = (inv.get("versions") or {}).get("shiploop_version")
            drv = (inv.get("model") or "?").split("-")[0] + "@" + str(inv.get("effort"))
            recs = []
            for line in open(trace, errors="replace"):
                try: r = json.loads(line)
                except ValueError: continue
                if r.get("kind") == "command": recs.append(r)
            if not recs: continue
            stages = {(r.get("stage") or [None])[0] for r in recs}
            for key, (stage, rx) in RATES.items():
                if stage in stages:
                    den[(key, ver)] += 1; den[(key, drv)] += 1
                    if any(r.get("exit") and r.get("error") and re.search(rx, r["error"]) for r in recs):
                        hit[(key, ver)] += 1; hit[(key, drv)] += 1
            if "operations" in stages:
                wait = own = 0.0
                for i, r in enumerate(recs):
                    if r.get("exit") and r.get("error"):
                        for n in recs[i + 1:]:
                            if n.get("exit") == 0 and n.get("verb") in ACCEPTS:
                                wait += n["ts"] - r["ts"]
                                if re.search(OWN_WORK, r["error"]): own += n["ts"] - r["ts"]
                                break
                whole.append((drv, (recs[-1]["ts"] - recs[0]["ts"]) / 60, wait / 60, (wait - own) / 60))
    print("\nruns with the refusal / runs that reached its stage, by ShipLoop version and by driver")
    for key in RATES:
        print(f"  {key:12s}", {k[1]: f"{hit[k]}/{den[k]}" for k in sorted(den, key=str) if k[0] == key})
    print(f"\nwhole deliveries (reached operations): {len(whole)}; minutes, medians")
    print("  driver          n   span   after any refusal   after a refusal that is not a failed test, mutant or proof (max)")
    for drv in sorted({w[0] for w in whole}):
        ws = [w for w in whole if w[0] == drv]
        print(f"  {drv:14s} {len(ws):2d} {statistics.median(w[1] for w in ws):6.1f} {statistics.median(w[2] for w in ws):8.1f} "
              f"{statistics.median(w[3] for w in ws):22.1f} ({max(w[3] for w in ws):.1f})")


main(sys.argv[1:])
rates(sys.argv[1:])
