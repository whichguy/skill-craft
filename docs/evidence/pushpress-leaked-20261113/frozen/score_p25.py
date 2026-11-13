#!/usr/bin/env python3
"""Score the P25 confirmation runs against the gates in design.md (journal Round 13).

usage: score_p25.py --leak-prompts <leak-prompts.json> --leak-pos-c5 <runs.json> [--leak-pos-c4 <runs.json>]
                    [--leak-neg-c5 <runs.json>] [--leak-neg-c4 <runs.json>]
                    [--regression-prompts <round9-prompts.json> --regression-c5 <runs.json>]
                    [--announce-prompts <announce-prompts.json> --announce-c5 <runs.json>] --out <summary.json>

One run per prompt in this design. A run is valid when it has no error and its init skill list holds the pushpress skill. A gate whose file was not given is
"not run"; the decision needs every gate run and passed and every file complete. Stage 1 (the benefit gates L1, L1a, L3) is decided from the leak-positive files
alone; the C4 arm on the leak prompts is only run when C5 passes L1 and L1a, so L3 reads "not run" until then.
"""
import argparse
import json

p = argparse.ArgumentParser()
for k in ("leak-prompts", "leak-pos-c5", "leak-pos-c4", "leak-neg-c5", "leak-neg-c4", "regression-prompts", "regression-c5", "announce-prompts", "announce-c5"):
    p.add_argument("--" + k)
p.add_argument("--out", required=True)
a = p.parse_args()


def load(path):
    return json.load(open(path))


def prompts_of(path):
    return {x["id"]: x for x in load(path)["prompts"]}


def runs(path, prompts):
    d = load(path)
    out = []
    for r in d["records"]:
        pr = prompts[r["id"]]
        out.append(dict(id=r["id"], category=pr["category"], expect_fire=pr["expect_fire"], fired=bool(r.get("pushpress_fired")),
                        valid=("error" not in r and "skipped" not in r and bool(r.get("init_has_pushpress_skill"))),
                        others=r.get("called", []), cost=r.get("cost_usd", 0)))
    return d, out


def count(rs, pred):
    sel = [r for r in rs if pred(r)]
    return sum(1 for r in sel if r["fired"]), len(sel)


leak_prompts = prompts_of(a.leak_prompts) if a.leak_prompts else {}
files, data, costs, claude = {}, {}, {}, set()
spec = [("leak_pos_c5", a.leak_pos_c5, leak_prompts, 12), ("leak_pos_c4", a.leak_pos_c4, leak_prompts, 12),
        ("leak_neg_c5", a.leak_neg_c5, leak_prompts, 12), ("leak_neg_c4", a.leak_neg_c4, leak_prompts, 12)]
if a.regression_c5:
    spec.append(("regression_c5", a.regression_c5, prompts_of(a.regression_prompts), 24))
if a.announce_c5:
    spec.append(("announce_c5", a.announce_c5, prompts_of(a.announce_prompts), 11))
completeness = {}
for name, path, pr, expected in spec:
    if not path:
        continue
    d, rs = runs(path, pr)
    data[name] = rs
    files[name] = path
    costs[name] = d["total_cost_usd"]
    claude.add(d["claude"])
    completeness[name] = dict(runs=len(rs), expected=expected, invalid=sum(1 for r in rs if not r["valid"]))
complete = all(v["runs"] == v["expected"] and v["invalid"] == 0 for v in completeness.values())


def have(*names):
    return all(n in data for n in names)


gates = {}
pos5 = data.get("leak_pos_c5", [])
pos4 = data.get("leak_pos_c4", [])
gates["L1_leak_recall"] = (dict(fired=count(pos5, lambda r: True)[0], runs=len(pos5), line=">= 10 of 12", passed=count(pos5, lambda r: True)[0] >= 10 and len(pos5) == 12)
                           if have("leak_pos_c5") else dict(line=">= 10 of 12", passed=None))
c_code = count(pos5, lambda r: r["category"] == "leak-code")
gates["L1a_code_class_recall"] = (dict(fired=c_code[0], runs=c_code[1], line=">= 4 of 6", passed=c_code[0] >= 4 and c_code[1] == 6)
                                  if have("leak_pos_c5") else dict(line=">= 4 of 6", passed=None))
if have("leak_pos_c5", "leak_pos_c4"):
    f5, f4 = count(pos5, lambda r: True)[0], count(pos4, lambda r: True)[0]
    gates["L3_gain_over_c4"] = dict(c5=f5, c4=f4, gain=f5 - f4, line=">= 4 more", passed=(f5 - f4) >= 4 and len(pos4) == 12 and len(pos5) == 12)
else:
    gates["L3_gain_over_c4"] = dict(line=">= 4 more", passed=None)
if have("leak_neg_c5"):
    n = count(data["leak_neg_c5"], lambda r: True)
    gates["L2_leak_false_fires"] = dict(fired=n[0], runs=n[1], line="<= 1 of 12", passed=n[0] <= 1 and n[1] == 12)
else:
    gates["L2_leak_false_fires"] = dict(line="<= 1 of 12", passed=None)
if have("regression_c5"):
    reg = data["regression_c5"]
    r1 = count(reg, lambda r: r["category"] == "explicit")
    r3 = count(reg, lambda r: not r["expect_fire"])
    r4 = count(reg, lambda r: r["category"] == "neg-sport80")
    gates["R1_explicit_recall"] = dict(fired=r1[0], runs=r1[1], line=">= 5 of 6", passed=r1[0] >= 5 and r1[1] == 6)
    gates["R3_quiet_false_fires"] = dict(fired=r3[0], runs=r3[1], line="<= 1 of 12", passed=r3[0] <= 1 and r3[1] == 12)
    gates["R4_sport80"] = dict(fired=r4[0], runs=r4[1], line="0 of 3", passed=r4[0] == 0 and r4[1] == 3)
else:
    for k, line in (("R1_explicit_recall", ">= 5 of 6"), ("R3_quiet_false_fires", "<= 1 of 12"), ("R4_sport80", "0 of 3")):
        gates[k] = dict(line=line, passed=None)
if have("announce_c5"):
    h = count(data["announce_c5"], lambda r: True)
    gates["A1_announcements_kept"] = dict(fired=h[0], runs=h[1], line=">= 9 of 11", passed=h[0] >= 9 and h[1] == 11)
else:
    gates["A1_announcements_kept"] = dict(line=">= 9 of 11", passed=None)

meas = {}
if have("leak_pos_c5"):
    meas["leak_by_class_c5"] = {c: dict(zip(("fired", "runs"), count(pos5, lambda r, c=c: r["category"] == c))) for c in ("leak-code", "leak-people")}
    meas["leak_prompts_missed_c5"] = sorted(r["id"] for r in pos5 if not r["fired"])
if have("leak_pos_c4"):
    meas["leak_by_class_c4"] = {c: dict(zip(("fired", "runs"), count(pos4, lambda r, c=c: r["category"] == c))) for c in ("leak-code", "leak-people")}
    meas["leak_prompts_missed_c4"] = sorted(r["id"] for r in pos4 if not r["fired"])
if have("leak_neg_c5"):
    meas["leak_false_fires_c5"] = [dict(id=r["id"], category=r["category"], called=r["others"]) for r in data["leak_neg_c5"] if r["fired"]]
    meas["leak_neg_other_skills_called_c5"] = sorted({c for r in data["leak_neg_c5"] for c in r["others"] if c.split(":")[-1] != "pushpress"})
if have("leak_neg_c4"):
    meas["leak_false_fires_c4"] = [dict(id=r["id"], category=r["category"], called=r["others"]) for r in data["leak_neg_c4"] if r["fired"]]
if have("regression_c5"):
    reg = data["regression_c5"]
    r2 = count(reg, lambda r: r["category"] == "implicit")
    meas["R2_implicit_recall_c5"] = dict(fired=r2[0], runs=r2[1], misses=sorted(r["id"] for r in reg if r["category"] == "implicit" and not r["fired"]),
                                         c4_in_round_12="I4 4 of 6 and I6 3 of 6 runs, the other four 12 of 12 (10 of 12 in the confirmation, two runs each)")
    meas["regression_false_fires_c5"] = [r["id"] for r in reg if (not r["expect_fire"]) and r["fired"]]
if have("announce_c5"):
    meas["announce_missed_c5"] = sorted(r["id"] for r in data["announce_c5"] if not r["fired"])

stage1_names = ("L1_leak_recall", "L1a_code_class_recall", "L3_gain_over_c4")
stage1_decided = all(gates[k]["passed"] is not None for k in stage1_names)
stage1_pass = stage1_decided and all(gates[k]["passed"] for k in stage1_names)
all_run = all(g["passed"] is not None for g in gates.values())
all_pass = all_run and all(g["passed"] for g in gates.values())
out = dict(files=files, completeness=completeness, gates=gates, measurements=meas, cost_usd=costs, claude=sorted(claude),
           decision=dict(complete=complete, stage1_decided=stage1_decided, stage1_pass=stage1_pass, all_gates_run=all_run, all_gates_passed=all_pass,
                         description_change_allowed=complete and all_pass))
json.dump(out, open(a.out, "w"), indent=1)

for name, g in gates.items():
    if g["passed"] is None:
        print(f"{name:24s} not run  (line {g['line']})")
        continue
    detail = ", ".join(f"{k}={v}" for k, v in g.items() if k not in ("passed", "line"))
    print(f"{name:24s} {'PASS' if g['passed'] else 'FAIL'}  (line {g['line']}; {detail})")
for k, v in meas.items():
    print(f"  measure {k}: {v}")
print("completeness:", completeness)
print("cost:", costs, "| claude:", sorted(claude))
print("DECISION:", out["decision"])
