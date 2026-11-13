#!/usr/bin/env python3
"""Score the P1(b) confirmation runs against the gates in design.md.

usage: score_trigger.py --regression <regression-C4.json> --regression-prompts <Round 9 prompts.json>
                        --heldout-prompts <heldout-prompts.json> --pub-announce <heldout-published.json>
                        --c4-pos <heldout-C4-pos.json> --c4-neg <heldout-C4-neg.json> [--pub-neg <heldout-published-neg.json>] --out <summary.json>

Counts runs, not prompts. A run is valid when it has no error. The decision line says whether every gate passed and every file is complete.
"""
import argparse
import json

p = argparse.ArgumentParser()
for k in ("regression", "regression-prompts", "heldout-prompts", "pub-announce", "c4-pos", "c4-neg", "out"):
    p.add_argument("--" + k, required=True)
p.add_argument("--pub-neg")
a = p.parse_args()


def load(path):
    return json.load(open(path))


reg_prompts = {x["id"]: x for x in load(a.regression_prompts)["prompts"]}
ho_prompts = {x["id"]: x for x in load(a.heldout_prompts)["prompts"]}


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


reg_d, reg = runs(a.regression, reg_prompts)
pub_d, pub = runs(a.pub_announce, ho_prompts)
pos_d, pos = runs(a.c4_pos, ho_prompts)
neg_d, neg = runs(a.c4_neg, ho_prompts)
pubneg_d, pubneg = runs(a.pub_neg, ho_prompts) if a.pub_neg else (None, [])

out = dict(files=dict(regression=a.regression, c4_pos=a.c4_pos, c4_neg=a.c4_neg, pub_announce=a.pub_announce, pub_neg=a.pub_neg))
out["completeness"] = dict(
    regression=dict(runs=len(reg), expected=48, invalid=sum(1 for r in reg if not r["valid"])),
    c4_positive=dict(runs=len(pos), expected=40, invalid=sum(1 for r in pos if not r["valid"])),
    c4_quiet=dict(runs=len(neg), expected=24, invalid=sum(1 for r in neg if not r["valid"])),
    published_announce=dict(runs=len(pub), expected=22, invalid=sum(1 for r in pub if not r["valid"])))
complete = all(v["runs"] == v["expected"] and v["invalid"] == 0 for v in out["completeness"].values())

r1 = count(reg, lambda r: r["category"] == "explicit")
r2 = count(reg, lambda r: r["category"] == "implicit")
r3 = count(reg, lambda r: not r["expect_fire"])
r4 = count(reg, lambda r: r["category"] == "neg-sport80")
h1 = count(pos, lambda r: r["category"] == "announce")
h3p = count(pub, lambda r: r["category"] == "announce")
h4 = count(neg, lambda r: not r["expect_fire"])
h2 = count(pos, lambda r: True)
by_type = {t: count(pos, lambda r, t=t: r["category"] == t) for t in ("announce", "task", "question", "after")}
gates = dict(
    R1_explicit_recall=dict(fired=r1[0], runs=r1[1], line=">= 11 of 12", passed=r1[0] >= 11 and r1[1] == 12),
    R3_false_fires=dict(fired=r3[0], runs=r3[1], line="<= 1 of 24", passed=r3[0] <= 1 and r3[1] == 24),
    R4_sport80=dict(fired=r4[0], runs=r4[1], line="0 of 6", passed=r4[0] == 0 and r4[1] == 6),
    H1_announce_recall=dict(fired=h1[0], runs=h1[1], line=">= 18 of 22", passed=h1[0] >= 18 and h1[1] == 22),
    H3_gain_over_published=dict(c4=h1[0], published=h3p[0], gain=h1[0] - h3p[0], line=">= 10 more", passed=(h1[0] - h3p[0]) >= 10 and h3p[1] == 22),
    H4_quiet_false_fires=dict(fired=h4[0], runs=h4[1], line="<= 1 of 24", passed=h4[0] <= 1 and h4[1] == 24))
out["gates"] = gates
out["measurements"] = dict(
    R2_implicit_recall=dict(fired=r2[0], runs=r2[1], line_of_round_9=">= 8 of 12", misses=sorted({r["id"] for r in reg if r["category"] == "implicit" and not r["fired"]})),
    H2_all_positive=dict(fired=h2[0], runs=h2[1], good_if=">= 34 of 40"),
    H2_by_type={t: dict(fired=v[0], runs=v[1]) for t, v in by_type.items()},
    positive_prompts_missed_in_any_run=sorted({r["id"] for r in pos if not r["fired"]}),
    positive_prompts_missed_in_both_runs=sorted({i for i in {r["id"] for r in pos} if all(not r["fired"] for r in pos if r["id"] == i)}),
    false_fires_listed=[dict(id=i, called=list(c)) for i, c in sorted({(r["id"], tuple(r["others"])) for r in neg if r["fired"]})],
    regression_false_fires_listed=[dict(id=r["id"]) for r in reg if (not r["expect_fire"]) and r["fired"]],
    published_on_quiet=(dict(fired=count(pubneg, lambda r: True)[0], runs=len(pubneg)) if a.pub_neg else None),
    other_skills_called_in_quiet_runs=sorted({c for r in neg for c in r["others"] if c.split(":")[-1] != "pushpress"}))
out["cost_usd"] = dict(regression=reg_d["total_cost_usd"], c4_positive=pos_d["total_cost_usd"], c4_quiet=neg_d["total_cost_usd"], published_announce=pub_d["total_cost_usd"],
                       published_quiet=(pubneg_d or {}).get("total_cost_usd"))
out["claude"] = sorted({d["claude"] for d in (reg_d, pub_d, pos_d, neg_d)})
out["decision"] = dict(complete=complete, all_gates_passed=all(g["passed"] for g in gates.values()),
                       description_change_allowed=complete and all(g["passed"] for g in gates.values()))
json.dump(out, open(a.out, "w"), indent=1)

for name, g in gates.items():
    detail = ", ".join(f"{k}={v}" for k, v in g.items() if k not in ("passed", "line"))
    print(f"{name:26s} {'PASS' if g['passed'] else 'FAIL'}  (line {g['line']}; {detail})")
m = out["measurements"]
print("R2 implicit recall (measure):", m["R2_implicit_recall"])
print("H2 all positive (measure):", m["H2_all_positive"], "| by type:", m["H2_by_type"])
print("positive prompts missed in any run:", m["positive_prompts_missed_in_any_run"], "| in both runs:", m["positive_prompts_missed_in_both_runs"])
print("false fires on held-out quiet prompts:", m["false_fires_listed"], "| Round 9 quiet prompts:", m["regression_false_fires_listed"])
print("completeness:", out["completeness"])
print("cost:", out["cost_usd"], "| claude:", out["claude"])
print("DECISION:", out["decision"])
