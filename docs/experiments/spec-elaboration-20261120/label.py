#!/usr/bin/env python3
"""Sort the held-out checklist's items by an outside rule, and read saved verdicts by the sorted sets.

The coverage judge counts an item as covered when the specification settles it, whether or not the request called
for it. This file adds the reading the judge cannot give: which items a specification of that request has to settle
(the requested outcome's own behaviour, and engineering rigour) and which are product capability the request did
not ask for. The rule is the owner's, recorded 2026-09-27 in commit e18cbce9ec577a61a8cdea353c6794804b09f1d9 and
in skills/rubric-eval/scripts/rubric_eval.py's value audit. Two models of different families sort the items, blind
to every arm and every verdict; only the items both sort the same way are used. No saved verdict is changed.

    python3 -I label.py label --judge=opus|astra   one sorting session over all the items -> labels/<judge>.json
    python3 -I label.py sets                       agreement and the sets -> labels/sets.json
    python3 -I label.py bands                      how far a repeat of the same arm moves on each set -> labels/bands.json
    python3 -I label.py shortfalls                 what the released stage covers in neither of its two draws
    python3 -I label.py split ROUND[,ROUND...] [--tag=gpt]     covered per set, per arm and driver
    python3 -I label.py gains ROUND --arm=A --control=P [--control-round=R] [--categories=a,b] [--set=X3]   item by item
    python3 -I label.py pair --rounds=R1,R2 --arm=A --control=P     the registered readings R16 to R19
    python3 -I label.py stable --rounds=R1,R2 --arm=A --control=P [--set=X1]   items A settles in every round and P in none

Run from anywhere. Needs grade.py beside it.
"""
import hashlib
import json
import re
import sys
import textwrap
import uuid
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python3 -I leaves the script's own folder off the path
import grade  # the judges, their runner and the verdict reader

LABELS = HERE / "labels"
KINDS = ("set", "limit", "both", "neither")
SCOPES = ("needed", "beyond", "mixed")
JUDGE_TAGS = {"opus": None, "astra": "gpt"}  # where each coverage judge's verdicts are kept
# Sol sessions before round 4c were shown the user's own skills (journal section 7): never a repeat pair.
EXPOSED_SOL = {"round-1", "round-2", "round-3", "round-4"}
BAND_FLOOR = 2
RELEASED = "P-shiploop-spec"

LABEL_PROMPT = """You are sorting the items of a fixed checklist. You judge; you change nothing but the one file named at the end.

`items.json` in your working directory holds four one-sentence requests for software and, under each, a list of
items: things a written specification for that request might settle. Each item has an `id` and a `nuance`. You are
shown no specification and need none: sort each item by what it asks a specification to settle.

Give every item two labels.

`kind`: what a specification has to write down to settle the item.
- "set": the members of a set have to be named: the states, conditions, cases or inputs that behave differently
  (which states count, which conditions stop or refuse something, which cases are treated apart).
- "limit": a limit has to be stated: a numeric bound, cap, size, rate, time or count, and what happens at it or
  beyond it.
- "both": it asks for both of those.
- "neither": it asks for something else (a behaviour, a flow, a decision, a control, a record, a rule to preserve).
Choose by the main thing the item asks for. An item that only mentions a number or a list in passing is "neither".

`scope`: how the item stands to its request, by this rule, which comes from the owner of the delivery tooling these
specifications are written for. Engineering rigour (tests against the real runtime, correct deployment steps,
quotas, failure routing and ownership, data retention, security checks, marked assumptions) is the expected
standard even for a small request. Product capability the request does not need (features, stores, services,
sign-in, channels the user sees or the product runs) is overbuilding.
- "needed": the item is the requested outcome's own behaviour (what it does, its boundaries, its error behaviour,
  how its parts and the existing product meet, what must be preserved), or it is engineering rigour in the rule's
  sense. A specification that left it unsettled would leave the requested thing wrong or unsafe to build.
- "beyond": the item is product capability the request does not ask for and the requested outcome works without: a
  further feature, control, view, store, service or channel. A specification may leave it out and say so.
- "mixed": the item bundles a needed part with a beyond part; say which is which in `why`.

Judge each item against its own request only. Do not ask whether the item would be good to have: ask what the rule
says it is.

Write `verdict.json` in your working directory, and nothing else:
{"labels": [{"case": "<case id>", "id": "<item id>", "kind": "set|limit|both|neither", "scope": "needed|beyond|mixed", "why": "<one line>"}, ...]}
One entry for every item of every case, in the order given.
"""


def items():
    """Every checklist item as ((case, id), item) in file order."""
    return [((c["id"], n["id"]), n) for c in grade.cases().values() for n in c["nuances"]]


def cmd_label(flags):
    name = flags.get("judge", "opus")
    judge = grade.JUDGES[name]
    LABELS.mkdir(exist_ok=True)
    out = LABELS / f"{name}.json"
    if out.is_file():
        print("SKIP", out.name, "exists")
        return
    cwd = grade.WORK / "labels" / f"label-{name}-{uuid.uuid4().hex[:6]}"
    cwd.mkdir(parents=True)
    (cwd / "items.json").write_text(json.dumps(
        [{"case": c["id"], "request": c["request"],
          "items": [{"id": n["id"], "nuance": n["nuance"]} for n in c["nuances"]]}
         for c in grade.cases().values()], indent=1) + "\n")
    rc, cost = grade.run_session(LABEL_PROMPT, cwd, judge, int(flags.get("timeout", 1800)))
    labels, problem = grade.read_verdict(cwd, "labels")
    if rc != 0 or labels is None:
        raise SystemExit(f"FAIL label {name}: rc={rc} {problem or ''}  (session folder {cwd})")
    seen = {}
    for entry in labels:
        if isinstance(entry, dict) and "case" in entry and "id" in entry:
            entry["kind"] = str(entry.get("kind") or "").strip().lower()
            entry["scope"] = str(entry.get("scope") or "").strip().lower()
            seen[(entry["case"], entry["id"])] = entry
    wanted = [key for key, _ in items()]
    missing = [list(k) for k in wanted if k not in seen]
    odd = [list(k) for k in wanted if k in seen and (seen[k]["kind"] not in KINDS or seen[k]["scope"] not in SCOPES)]
    out.write_text(json.dumps({
        "judge": judge["model"], "judge_effort": judge["effort"], "cost_usd": cost,
        "prompt_sha256": hashlib.sha256(LABEL_PROMPT.encode()).hexdigest(),
        "missing": missing, "unknown_labels": odd,
        "labels": [seen[k] for k in wanted if k in seen]}, indent=1) + "\n")
    print(f"DONE label {name}: {len(seen)} of {len(wanted)} items, missing={len(missing)} unknown={len(odd)}",
          "kinds", dict(Counter(seen[k]["kind"] for k in wanted if k in seen)),
          "scopes", dict(Counter(seen[k]["scope"] for k in wanted if k in seen)))
    if missing or odd:
        raise SystemExit("the labels are incomplete: remove the file and sort again")


def load_labels(name):
    data = json.loads((LABELS / f"{name}.json").read_text())
    return {(e["case"], e["id"]): e for e in data["labels"]}


def build_sets():
    """The sets, from the items both sorters label alike. Keys are (case, id) tuples."""
    a, b = load_labels("opus"), load_labels("astra")
    keys = [k for k, _ in items()]
    is_target = lambda e: e["kind"] in ("set", "limit", "both")
    target = [k for k in keys if is_target(a[k]) and is_target(b[k])]
    beyond = [k for k in keys if a[k]["scope"] == b[k]["scope"] == "beyond"]
    needed = [k for k in keys if a[k]["scope"] == b[k]["scope"] == "needed"]
    return {
        "all": keys,
        "target": target,                                          # both: it turns on a set or a limit
        "beyond": beyond,                                          # both: capability the request did not ask for
        "needed": needed,                                          # both: requested behaviour or rigour
        "X1": [k for k in target if k not in beyond],             # R16: set-or-limit items not agreed beyond
        "X2": [k for k in needed if k not in target],             # R17: the other needed items
        "X3": beyond,                                              # R18: agreed beyond
    }, a, b


def cmd_sets(_flags):
    sets, a, b = build_sets()
    keys = sets["all"]
    cat = {k: n["category"] for k, n in items()}
    kind_agree = sum(1 for k in keys if a[k]["kind"] == b[k]["kind"])
    target_agree = sum(1 for k in keys if (a[k]["kind"] != "neither") == (b[k]["kind"] != "neither"))
    scope_agree = sum(1 for k in keys if a[k]["scope"] == b[k]["scope"])
    lines = [f"{len(keys)} items, sorted by claude-opus-5-5 (high) and gpt-6.2-astra (high), blind to arms and verdicts",
             f"same `kind` label: {kind_agree} of {len(keys)}; same on set-or-limit against neither: {target_agree}",
             f"same `scope` label: {scope_agree} of {len(keys)}",
             "scope, opus by astra: " + json.dumps({f"{x}/{y}": n for (x, y), n in sorted(
                 Counter((a[k]["scope"], b[k]["scope"]) for k in keys).items())}),
             "kind, opus by astra: " + json.dumps({f"{x}/{y}": n for (x, y), n in sorted(
                 Counter((a[k]["kind"], b[k]["kind"]) for k in keys).items())}),
             ""]
    for name in ("target", "needed", "beyond", "X1", "X2", "X3"):
        by = Counter(cat[k] for k in sets[name])
        lines.append(f"{name:7} {len(sets[name]):3}  by category: " + ", ".join(f"{c} {n}" for c, n in sorted(by.items())))
    lines.append("")
    lines.append("items both sorters call beyond (capability the request did not ask for):")
    nu = dict(items())
    for k in sets["beyond"]:
        lines.append(f"  {k[0]} {k[1]} [{cat[k]}] {textwrap.shorten(nu[k]['nuance'], 110)}")
    lines.append("items in X1 (set-or-limit, not agreed beyond):")
    for k in sets["X1"]:
        lines.append(f"  {k[0]} {k[1]} [{cat[k]}] ({a[k]['kind']}/{b[k]['kind']}) {textwrap.shorten(nu[k]['nuance'], 100)}")
    print("\n".join(lines))
    (LABELS / "sets.json").write_text(json.dumps(
        {"agreement": {"kind": kind_agree, "set_or_limit": target_agree, "scope": scope_agree, "of": len(keys)},
         **{name: [list(k) for k in sets[name]] for name in sets if name != "all"}}, indent=1) + "\n")
    (LABELS / "sets.txt").write_text("\n".join(lines) + "\n")


def verdict_states(round_name, tag, arm, driver):
    """{(case, id): state} for one arm and driver in one round under one judge, or {} when a case is missing."""
    out = {}
    folder = grade.grades_dir(round_name, tag)
    for case in grade.cases():
        path = folder / f"{case}__{arm}__{driver}.json"
        if not path.is_file():
            return {}
        for v in json.loads(path.read_text())["verdicts"]:
            out[(case, v["id"])] = v
    return out


def cells(round_name, tag=None):
    """The (arm, driver) pairs with all four cases graded in a round."""
    folder = grade.grades_dir(round_name, tag)
    found = defaultdict(set)
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        case, arm, driver = path.stem.split("__")
        found[(arm, driver)].add(case)
    return sorted(k for k, got in found.items() if got == set(grade.cases()))


def covered(states, keys):
    return sum(1 for k in keys if states.get(k, {}).get("state") == "covered")


def repeat_pairs():
    """Every two draws of one arm on one driver, in different rounds, with clean sessions (registered judge)."""
    rounds = sorted(p.name for p in (HERE / "grades").iterdir() if p.is_dir() and p.name.startswith("round-")
                    and "@" not in p.name)
    seen = defaultdict(list)
    for r in rounds:
        for arm, driver in cells(r):
            if driver.startswith("sol") and r in EXPOSED_SOL:
                continue
            seen[(arm, driver)].append(r)
    return [(arm, driver, r1, r2) for (arm, driver), rs in sorted(seen.items())
            for i, r1 in enumerate(rs) for r2 in rs[i + 1:]]


def cmd_bands(flags):
    if (LABELS / "bands.json").is_file() and not flags.get("force"):
        raise SystemExit("labels/bands.json exists: the bands are fixed before the paired rounds and are not recomputed")
    sets, _, _ = build_sets()
    upto = flags.get("upto")  # only pairs from rounds before the paired check: fixed when registered
    pairs = [p for p in repeat_pairs() if not upto or (p[2] <= upto and p[3] <= upto)]
    lines, bands = [f"repeat pairs (same arm, same driver, two rounds, clean sessions, registered judge): {len(pairs)}"], {}
    for name in ("X1", "X2", "X3", "all"):
        moves = []
        for arm, driver, r1, r2 in pairs:
            d = covered(verdict_states(r2, None, arm, driver), sets[name]) - covered(verdict_states(r1, None, arm, driver), sets[name])
            moves.append((abs(d), arm, driver, r1, r2, d))
        worst = max(moves) if moves else (0,)
        bands[name] = max(BAND_FLOOR, worst[0])
        lines.append(f"{name:4} {len(sets[name]):3} items: a repeat moved by " + ", ".join(
            f"{m[5]:+d} ({m[1].split('-')[0]} {m[2].split('-')[0]} {m[3][6:]}>{m[4][6:]})" for m in moves)
            + f"  -> band {bands[name]}")
    print("\n".join(lines))
    (LABELS / "bands.json").write_text(json.dumps({"pairs": [list(p) for p in pairs], "bands": bands}, indent=1) + "\n")
    (LABELS / "bands.txt").write_text("\n".join(lines) + "\n")


def stable_shortfalls():
    """Per driver: the items the released stage covered in neither round 5 nor round 6 (registered judge)."""
    out = {}
    for driver in ("sonnet-high", "sol-medium"):
        a, b = verdict_states("round-5", None, RELEASED, driver), verdict_states("round-6", None, RELEASED, driver)
        out[driver] = [k for k, _ in items() if a[k]["state"] != "covered" and b[k]["state"] != "covered"]
    return out


def cmd_shortfalls(_flags):
    nu, short = dict(items()), stable_shortfalls()
    lines = []
    for driver, keys in short.items():
        a, b = verdict_states("round-5", None, RELEASED, driver), verdict_states("round-6", None, RELEASED, driver)
        both = sum(1 for k in nu if a[k]["state"] == "covered" and b[k]["state"] == "covered")
        lines.append(f"{driver}: the released stage covered {both} items in both draws, {len(nu) - both - len(keys)} in one "
                     f"of the two, {len(keys)} in neither")
        lines.append("  in neither, by category: " + ", ".join(
            f"{c} {n}" for c, n in sorted(Counter(nu[k]["category"] for k in keys).items())))
        for k in keys:
            lines.append(f"  {k[0]} {k[1]} [{nu[k]['category']}] {a[k]['state']}/{b[k]['state']}  "
                         f"{textwrap.shorten(nu[k]['nuance'], 110)}")
    print("\n".join(lines))
    LABELS.mkdir(exist_ok=True)
    (LABELS / "stable-shortfalls.json").write_text(json.dumps({d: [list(k) for k in ks] for d, ks in short.items()}, indent=1) + "\n")
    (LABELS / "stable-shortfalls.txt").write_text("\n".join(lines) + "\n")


def cmd_split(rounds, flags):
    sets, _, _ = build_sets()
    tag = flags.get("tag")
    print(f"covered, by set (judge: {'gpt-6.2-astra' if tag else 'claude-opus-5-5'})")
    print(f"{'round':10} {'arm':24} {'driver':12} " + " ".join(f"{n + ' /' + str(len(sets[n])):>10}" for n in ("X1", "X2", "X3", "all")))
    for r in rounds.split(","):
        for arm, driver in cells(r, tag):
            s = verdict_states(r, tag, arm, driver)
            print(f"{r:10} {arm:24} {driver:12} " + " ".join(f"{covered(s, sets[n]):>10}" for n in ("X1", "X2", "X3", "all")))


def cmd_gains(round_name, flags):
    """Item by item: what `arm` covered that `control` did not, and the reverse, with what each specification said."""
    arm, control = flags["arm"], flags.get("control", RELEASED)
    control_round, other_round = flags.get("control-round", round_name), flags.get("other-control-round")
    only = set(flags["categories"].split(",")) if flags.get("categories") else None
    within = set(build_sets()[0][flags["set"]]) if flags.get("set") else None
    nu = dict(items())
    lines = [f"# {arm} against {control}, {round_name}, item by item" + (f" ({', '.join(sorted(only))} items)" if only else "")
             + (f" (set {flags['set']})" if within is not None else ""), ""]
    for driver in ("sonnet-high", "sol-medium"):
        for tag, judge in ((None, "claude-opus-5-5"), ("gpt", "gpt-6.2-astra")):
            A, C = verdict_states(round_name, tag, arm, driver), verdict_states(control_round, tag, control, driver)
            O = verdict_states(other_round, tag, control, driver) if other_round else {}
            if not A or not C:
                continue
            keys = [k for k in nu if (not only or nu[k]["category"] in only) and (within is None or k in within)]
            up = [k for k in keys if A[k]["state"] == "covered" and C[k]["state"] != "covered"]
            down = [k for k in keys if C[k]["state"] == "covered" and A[k]["state"] != "covered"]
            lines.append(f"## {driver}, judge {judge}: {len(up)} covered by {arm} and not by {control}; {len(down)} the other way")
            if tag:
                lines.append("  " + ", ".join(f"+{k[0]} {k[1]}" for k in up) + " | " + ", ".join(f"-{k[0]} {k[1]}" for k in down))
                lines.append("")
                continue
            for sign, group in (("+", up), ("-", down)):
                for k in group:
                    also = f"; {control} in {other_round}: {O[k]['state']}" if O else ""
                    lines.append(f"{sign} {k[0]} {k[1]} [{nu[k]['category']}] {control}: {C[k]['state']}{also}; {arm}: {A[k]['state']}")
                    lines.append(f"    item: {nu[k]['nuance']}")
                    lines.append(f"    {control} ({C[k].get('where')}): {textwrap.shorten(str(C[k].get('quote')), 420)}")
                    lines.append(f"    {arm} ({A[k].get('where')}): {textwrap.shorten(str(A[k].get('quote')), 420)}")
            lines.append("")
    text = "\n".join(lines)
    print(text)
    if flags.get("out"):
        Path(flags["out"]).write_text(text + "\n")


def cmd_stable(flags):
    """Items `arm` covers in every round and `control` in none (registered judge), with what each specification said,
    and how the second judge scored the same cells. The reverse list too."""
    sets, _, _ = build_sets()
    rounds, arm, control = flags["rounds"].split(","), flags["arm"], flags.get("control", RELEASED)
    name = flags.get("set", "X1")
    nu = dict(items())
    title = (f"# {arm} against {control} over {', '.join(rounds)}, set {name} ({len(sets[name])} items): items settled by one arm"
             " in every round and by the other in none (registered judge), with the second judge's states beside them")
    lines = [title, ""]
    for driver in ("sonnet-high", "sol-medium"):
        A = {(j, r): verdict_states(r, tag, arm, driver) for j, tag in JUDGE_TAGS.items() for r in rounds}
        C = {(j, r): verdict_states(r, tag, control, driver) for j, tag in JUDGE_TAGS.items() for r in rounds}
        if not all(A.values()) or not all(C.values()):
            lines.append(f"## {driver}: not every round is graded by both judges yet")
            continue
        def cov(V, j, k):
            return [V[(j, r)][k]["state"] == "covered" for r in rounds]

        def show(V, j, k):
            return "/".join(V[(j, r)][k]["state"][:3] for r in rounds)

        up = [k for k in sets[name] if all(cov(A, "opus", k)) and not any(cov(C, "opus", k))]
        down = [k for k in sets[name] if all(cov(C, "opus", k)) and not any(cov(A, "opus", k))]
        both = [k for k in up if all(cov(A, "astra", k)) and not any(cov(C, "astra", k))]
        lines.append(f"## {driver}: {len(up)} settled by {arm} in every round and by {control} in none; "
                     f"{len(both)} of them the same under the second judge; {len(down)} the other way")
        for sign, group in (("+", up), ("-", down)):
            for k in group:
                lines.append(f"{sign} {k[0]} {k[1]} [{nu[k]['category']}]  {control}: opus {show(C, 'opus', k)}, astra {show(C, 'astra', k)};"
                             f"  {arm}: opus {show(A, 'opus', k)}, astra {show(A, 'astra', k)}")
                lines.append(f"    item: {nu[k]['nuance']}")
                for r in rounds:
                    lines.append(f"    {control} {r} ({C[('opus', r)][k].get('where')}): {textwrap.shorten(str(C[('opus', r)][k].get('quote')), 300)}")
                for r in rounds:
                    lines.append(f"    {arm} {r} ({A[('opus', r)][k].get('where')}): {textwrap.shorten(str(A[('opus', r)][k].get('quote')), 300)}")
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if flags.get("out"):
        Path(flags["out"]).write_text(text + "\n")


def spec_size(round_name, arm, driver):
    words = tokens = requirements = n = 0
    for case in grade.cases():
        slot = HERE / "results" / round_name / f"{case}__{arm}__{driver}"
        if not (slot / "spec.md").is_file():
            continue
        text = grade.judged_text(slot)
        meta = json.loads((slot / "meta.json").read_text())
        words += len(text.split())
        requirements += len(set(re.findall(r"^#{2,4}\s*R-(\d+)\b", text, re.MULTILINE)))
        tokens += int(((meta.get("usage") or {}).get("output_tokens")) or 0)
        n += 1
    return {"specs": n, "words": words, "requirements": requirements, "output_tokens": tokens}


def status(deltas, band):
    """The registered reading of one driver's same-round differences under both judges ({judge: [d1, d2, ...]})."""
    means = {j: sum(d) / len(d) for j, d in deltas.items()}
    if all(m >= band for m in means.values()) and all(x > 0 for d in deltas.values() for x in d):
        return "shown"
    if all(m <= -band for m in means.values()) and all(x < 0 for d in deltas.values() for x in d):
        return "worse"
    if all(m > 0 for m in means.values()) and means["opus"] >= band / 2:
        return "interim"
    if all(m < 0 for m in means.values()):
        return "below, not shown"
    return "nothing shown"


def cmd_pair(flags):
    sets, _, _ = build_sets()
    bands = json.loads((LABELS / "bands.json").read_text())["bands"]
    rounds, arm, control = flags["rounds"].split(","), flags["arm"], flags.get("control", RELEASED)
    short = stable_shortfalls()
    lines = [f"{arm} against {control}, same-round pairs in {', '.join(rounds)}",
             f"bands (the largest move between two draws of one arm, fixed before these rounds): {bands}", ""]
    verdict = {}
    for driver in ("sonnet-high", "sol-medium"):
        lines.append(f"== {driver}")
        states = {(j, r, a): verdict_states(r, tag, a, driver) for j, tag in JUDGE_TAGS.items() for r in rounds for a in (arm, control)}
        if not all(states.values()):
            lines.append("   not every round is graded by both judges yet")
            continue
        verdict[driver] = {}
        for name, reading in (("X1", "R16 set-or-limit items"), ("X2", "R17 the other needed items"),
                              ("X3", "R18 capability not asked for"), ("all", "the whole checklist")):
            deltas, shown = {}, []
            for j in JUDGE_TAGS:
                per = [(covered(states[(j, r, arm)], sets[name]), covered(states[(j, r, control)], sets[name])) for r in rounds]
                deltas[j] = [m - p for m, p in per]
                shown.append(f"{j}: " + ", ".join(f"{m} vs {p} ({m - p:+d})" for m, p in per)
                             + f", mean {sum(deltas[j]) / len(deltas[j]):+.1f}")
            verdict[driver][name] = status(deltas, bands[name])
            lines.append(f"   {reading} ({len(sets[name])} items, band {bands[name]}): " + "; ".join(shown)
                         + f"  => {verdict[driver][name]}")
        keys = short[driver]
        lines.append(f"   R19 the {len(keys)} items the released stage covered in neither earlier draw: " + "; ".join(
            f"{j}: " + ", ".join(f"{covered(states[(j, r, arm)], keys)} vs {covered(states[(j, r, control)], keys)}" for r in rounds)
            for j in JUDGE_TAGS))
        sizes = [(spec_size(r, arm, driver), spec_size(r, control, driver)) for r in rounds]
        for field in ("words", "requirements", "output_tokens"):
            ratios = [m[field] / p[field] for m, p in sizes if p[field]]
            lines.append(f"   {field}: " + ", ".join(f"{m[field]} vs {p[field]}" for m, p in sizes)
                         + (f"  mean ratio {sum(ratios) / len(ratios):.2f}" if ratios else ""))
        lines.append("")
    if len(verdict) == 2:
        r16 = [verdict[d]["X1"] for d in verdict]
        harm = [d for d in verdict if verdict[d]["X2"] == "worse" or verdict[d]["X3"] == "shown" or verdict[d]["X1"] == "worse"]
        if "shown" in r16 and not harm:
            lines.append("DECISION RULE: R16 is shown on a driver and no harm reading fails -> the cue is put to the owner.")
        elif "interim" in r16 and not harm and len(rounds) < 3:
            lines.append("DECISION RULE: R16 is interim on a driver and no harm reading fails -> one more paired round, then the result stands.")
        else:
            lines.append("DECISION RULE: R16 is not shown" + (f", and a harm reading fails on {', '.join(harm)}" if harm else "")
                         + " -> no change is proposed.")
    text = "\n".join(lines)
    print(text)
    if flags.get("out"):
        Path(flags["out"]).write_text(text + "\n")


def main():
    args, flags = grade.flags_and_args(sys.argv[1:])
    if not args:
        print(__doc__)
        raise SystemExit(2)
    simple = {"label": cmd_label, "sets": cmd_sets, "bands": cmd_bands, "shortfalls": cmd_shortfalls, "pair": cmd_pair,
              "stable": cmd_stable}
    if args[0] in simple:
        simple[args[0]](flags)
    elif args[0] in ("split", "gains") and len(args) > 1:
        {"split": cmd_split, "gains": cmd_gains}[args[0]](args[1], flags)
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
