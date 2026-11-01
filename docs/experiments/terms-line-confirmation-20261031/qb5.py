#!/usr/bin/env python3
"""The terms-line confirmation (README.md): does intake item 9 plus a terms-and-references line resolve more of a long, loosely worded
request, on requests QB2 was not designed on?

    python3 qb5.py build   write prompts/<case>-<arm>.md for arms B, Bk, Bk12 and Bsen
    python3 qb5.py jobs    write jobs.tsv (and copy each fixture to the workspace the model reads)
    python3 qb5.py judge   write judge/*.md, judge/mapping.json and jobs-judge.tsv
    python3 qb5.py score   read the judge answers; print the tables and the registered rules; write scores.json

Arms (X1's exercise frame with the tools on and the host's skill list in the packet, as in QB2):
  B     intake item 9 as shipped (the K1-K11 catalog and the model-written ledger)
  Bk    B plus the catalog line K12 (terms and references) and the look-it-up-first sentence
  Bk12  B plus the K12 line only
  Bsen  B plus the sentence only
"""
import importlib.util
import json
import os
import random
import re
import shutil
import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

from cases import CASES, GROUPS
from stats import mean, permutation_p

HERE = Path(__file__).resolve().parent
X1 = HERE.parent / "key-questions-intake-20261030"
FIXTURES = HERE.parents[2] / "test" / "shiploop_e2e" / "fixtures"
WORK = Path(os.environ.get("QB_WORK") or tempfile.gettempdir()) / "terms-line-confirmation-20261031"
SUBJECT = "codex:gpt-6.1-terra:xhigh"
ARMS = ("B", "Bk", "Bk12", "Bsen")
SAMPLES = (1, 2, 3, 4, 5)

_spec = importlib.util.spec_from_file_location("qb2_case", HERE.parent / "question-bank-20261031" / "qb2_case.py")
qb2_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qb2_case)
_spec = importlib.util.spec_from_file_location("x1_score", X1 / "score.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)

K12 = ("K12", "Terms and references",
       ("the names, skills, commands, products and community phrases in the request, and the phrases that point at something it "
        "does not state (\"the usual\", \"as before\"); what each means here and where that was settled (the installed skills, the "
        "repository, or a search), else the best reading and how sure it is."))
SENTENCE = ("Terms and references: settle each by looking, in this order: the installed skills listed above, the repository and "
            "its documents, then a search (`research`). When nothing settles it, record the best reading and how sure you are as "
            "the `default`; use `person` only when two readings remain that lead to different work.")
TOOLS_OLD = "In this exercise you have no tools and no files: answer from the request alone. The repository is empty."
ITEM9_RE = re.compile(r"9\. Key questions\..*?what would show it early\.(?=\n\nRULES:)", re.DOTALL)
REQUEST_RE = re.compile(r"----- BEGIN ORIGINAL REQUEST -----.*\Z", re.DOTALL)

JUDGE = """\
You are grading the first planning stage of a software-delivery harness. A model received only the REQUEST below (a long,
loosely worded message from a person). It could read the files of an existing repository and saw a list of the installed
skills; it had to map the request to outcomes, boundaries and open questions, recording a default for anything no
evidence could settle (the run is unattended). You also see the REPOSITORY FACTS, which are true, and a list of ITEMS
the request raises, each with what a good intake does about it. Grade each OUTPUT on what its text says; its format,
length and field names are irrelevant, and you do not know how any output was produced.

For each output and each item:
- covered: true when the output, anywhere, addresses the item so that a later stage would act on it deliberately; a
  passing mention that settles nothing is not covered.
- quote: when covered, the shortest verbatim excerpt (at most 40 words) copied character for character from that output
  that shows it; otherwise null. A script checks every quote against the output; one not found counts as not covered.
- correct: "yes" when what the output says agrees with what a good intake does for that item; "partial" when it is
  partly right or vague; "no" when it contradicts the repository facts, invents facts, or misreads the term; "na" when
  the item is not covered.
- route: how the output settles it: "environment" (it states what the repository, its documents or the skills list
  show), "knowledge" (it explains the term from general knowledge), "default" (it records an assumption or default),
  "person" (it leaves the item to a person to decide), "silent" (it asserts something without evidence or a flag), or
  "none" (not covered).
For each output also give items_total (how many distinct questions, open items or recorded assumptions it raises) and
noise (how many of those would not change what is built, how it is checked or how it is delivered for this request).

Answer with JSON only, no prose, in this shape:
{{"outputs": {{"O1": {{"items": {{"<item id>": {{"covered": true, "quote": "...", "correct": "yes", "route": "environment"}}}},
"items_total": 0, "noise": 0}}}}}}

REQUEST:
{request}

REPOSITORY FACTS:
{facts}

ITEMS:
{items}

{outputs}
"""


def wrap(text: str, indent: str = "   ") -> str:
    return textwrap.fill(text, width=118, initial_indent=indent, subsequent_indent=indent, break_long_words=False,
                         break_on_hyphens=False)


def request_text(case: dict) -> str:
    paragraphs, current = [], []
    for number, sentence in enumerate(case["sentences"], 1):
        current.append(sentence)
        if number in case["breaks"]:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def build_prompt(case: dict, arm: str) -> str:
    text = (X1 / "prompts" / "battleship-B.md").read_text()
    assert text.count(TOOLS_OLD) == 1 and len(ITEM9_RE.findall(text)) == 1
    skills = "\n".join(f"- {name}: {desc}" for name, desc in qb2_case.SKILLS)
    frame = (wrap("In this exercise you may read files in the working directory, " + case["context"] + ", with read-only shell "
                  "commands; change nothing and start no server. The host lists the installed skills it offers:", "").rstrip()
             + "\n" + skills)
    text = text.replace(TOOLS_OLD, frame, 1)
    item9 = ITEM9_RE.search(text).group(0)
    line = textwrap.fill(f"{K12[0]} {K12[1]}: {K12[2]}", width=118, initial_indent="   - ", subsequent_indent="     ",
                         break_long_words=False, break_on_hyphens=False)
    addition = {"B": "", "Bk": "\n" + line + "\n" + wrap(SENTENCE), "Bk12": "\n" + line, "Bsen": "\n" + wrap(SENTENCE)}[arm]
    text = text.replace(item9, item9 + addition, 1)
    index = " ".join(f"S{number}: {sentence}" for number, sentence in enumerate(case["sentences"], 1))
    block = ("----- BEGIN ORIGINAL REQUEST -----\n" + request_text(case) + "\n----- END ORIGINAL REQUEST -----\n"
             "Sentence index of this request (cite S<n>): " + index + "\n")
    return REQUEST_RE.sub(lambda _m: block, text, count=1)


def cmd_build() -> None:
    (HERE / "prompts").mkdir(exist_ok=True)
    for case_id, case in CASES.items():
        for arm in ARMS:
            text = build_prompt(case, arm)
            (HERE / "prompts" / f"{case_id}-{arm}.md").write_text(text)
            print(f"  {case_id:8} {arm:5} {len(text):6d} characters")


def workspace(case: dict) -> Path:
    target = WORK / "workspace" / case["fixture"]
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FIXTURES / case["fixture"], target, ignore=shutil.ignore_patterns("node_modules", ".git"))
    return target


def cmd_jobs() -> None:
    rows = []
    for case_id, case in CASES.items():
        space = workspace(case)
        for arm in ARMS:
            for sample in SAMPLES:
                rows.append(f"{SUBJECT}\tprompts/{case_id}-{arm}.md\tintake/{case_id}-{arm}-s{sample}.json\t{space}")
    (HERE / "jobs.tsv").write_text("\n".join(rows) + "\n")
    print(f"wrote {len(rows)} subject jobs")


def envelope(path: Path) -> dict:
    return json.loads(path.read_text())


def cmd_judge() -> None:
    out_dir = HERE / "judge"
    out_dir.mkdir(exist_ok=True)
    mapping, jobs = {}, []
    for case_id, case in CASES.items():
        items = "\n".join(f"- {i[0]} ({i[3]}): {i[4]}" for i in case["items"])
        for sample in SAMPLES:
            runs = [(arm, sample) for arm in ARMS]
            random.Random(f"qb5-{case_id}-{sample}").shuffle(runs)
            labels, blocks = {}, []
            for number, (arm, s) in enumerate(runs, 1):
                path = HERE / "intake" / f"{case_id}-{arm}-s{s}.json"
                label = f"O{number}"
                labels[label] = {"arm": arm, "sample": s, "case": case_id, "file": path.relative_to(HERE).as_posix()}
                text = (envelope(path).get("text") or "").strip()
                blocks.append(f"===== OUTPUT {label} =====\n{text}\n===== END OUTPUT {label} =====")
            prompt = JUDGE.format(request=request_text(case), facts=case["facts"], items=items, outputs="\n\n".join(blocks))
            name = f"qb5-{case_id}-s{sample}"
            (out_dir / f"{name}.md").write_text(prompt)
            mapping[name] = labels
            jobs.append(f"opus\tjudge/{name}.md\tjudge/{name}.out.json")
    (out_dir / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / "jobs-judge.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} judge prompts")


def judge_json(path: Path) -> dict:
    text = json.loads(path.read_text()).get("text") or ""
    return json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))


def collect() -> tuple:
    mapping = json.loads((HERE / "judge" / "mapping.json").read_text())
    outputs, unverified = [], []
    for name, labels in mapping.items():
        verdict = judge_json(HERE / "judge" / f"{name}.out.json")["outputs"]
        for label, info in labels.items():
            case = CASES[info["case"]]
            data = envelope(HERE / info["file"])
            text = data.get("text") or ""
            usage = data.get("usage") or {}
            grade = verdict.get(label, {})
            rows = []
            for ident, group, kind, _span, _expected in case["items"]:
                row = (grade.get("items") or {}).get(ident) or {}
                ok = bool(row.get("covered")) and bool(row.get("quote")) and x1.norm(row["quote"]) in x1.norm(text)
                if row.get("covered") and not ok:
                    unverified.append({"name": name, "label": label, "item": ident})
                rows.append({"item": ident, "group": group, "kind": kind, "covered": ok,
                             "correct": row.get("correct") if ok else "na", "route": row.get("route") if ok else "none"})
            n = len(rows)
            outputs.append({
                "arm": info["arm"], "case": info["case"], "sample": info["sample"], "rows": rows,
                "right": sum(r["correct"] == "yes" for r in rows) / n, "covered": sum(r["covered"] for r in rows) / n,
                "partial": sum(r["correct"] == "partial" for r in rows) / n, "wrong": sum(r["correct"] == "no" for r in rows) / n,
                "silent": sum(r["route"] == "silent" for r in rows), "person": sum(r["route"] == "person" for r in rows),
                "items_total": grade.get("items_total") or 0, "noise": grade.get("noise") or 0,
                "out_tokens": usage.get("output_tokens", 0), "uncached": usage.get("input_tokens", 0) - usage.get("cached_input_tokens", 0),
                "commands": len(data.get("commands") or [])})
    return outputs, unverified


def vals(outputs, arm, key, case=None, coarse=None):
    chosen = [o[key] for o in outputs if o["arm"] == arm and (case is None or o["case"] == case)]
    return [coarse(v) for v in chosen] if coarse else chosen


def p_higher(outputs, low, high, key):
    two = lambda v: round(v, 2)
    return permutation_p(vals(outputs, low, key, coarse=two), vals(outputs, high, key, coarse=two))


def p_lower(outputs, high, low, key):
    return permutation_p([-v for v in vals(outputs, high, key)], [-v for v in vals(outputs, low, key)])


def cmd_score() -> None:
    outputs, unverified = collect()
    case_ids = list(CASES)
    report = {"unverified_quotes": unverified, "arms": {}, "cases": {}, "groups": {}, "tests": {}, "rules": {}}
    print(f"graded {len(outputs)} outputs, unverified judge quotes {len(unverified)}")
    print(f"{'arm':5} {'n':>3} {'cover':>6} {'right':>6} {'part':>5} {'wrong':>5} {'silent':>6} {'person':>6} {'out_tok':>8} {'in_unc':>7} "
          f"{'cmds':>5} {'items':>5} {'noise':>5}")
    for arm in ARMS:
        o = [x for x in outputs if x["arm"] == arm]
        s = {k: mean(x[k] for x in o) for k in ("covered", "right", "partial", "wrong", "silent", "person", "out_tokens",
                                                "uncached", "commands", "items_total", "noise")}
        s["n"] = len(o)
        report["arms"][arm] = s
        print(f"{arm:5} {s['n']:3d} {s['covered']:6.2f} {s['right']:6.2f} {s['partial']:5.2f} {s['wrong']:5.2f} {s['silent']:6.2f} "
              f"{s['person']:6.2f} {s['out_tokens']:8.0f} {s['uncached']:7.0f} {s['commands']:5.1f} {s['items_total']:5.1f} {s['noise']:5.1f}")
    print("\nshare of items right, per request and arm:")
    for case_id in case_ids:
        cells = {arm: mean(vals(outputs, arm, "right", case_id)) for arm in ARMS}
        report["cases"][case_id] = cells
        print(f"  {case_id:8} " + "  ".join(f"{arm} {cells[arm]:.2f}" for arm in ARMS))
    print("\nshare of items right, per group and arm (pooled over requests):")
    for group in GROUPS:
        cells = {}
        for arm in ARMS:
            rows = [r for o in outputs if o["arm"] == arm for r in o["rows"] if r["group"] == group]
            cells[arm] = sum(r["correct"] == "yes" for r in rows) / len(rows)
        report["groups"][group] = cells
        print(f"  {group:10} " + "  ".join(f"{arm} {cells[arm]:.2f}" for arm in ARMS))
    print("\nroute mix over all item grades (environment, knowledge, default, person, silent):")
    for arm in ARMS:
        c = Counter(r["route"] for o in outputs if o["arm"] == arm for r in o["rows"])
        print(f"  {arm:5} " + ", ".join(f"{c[k]}" for k in ("environment", "knowledge", "default", "person", "silent")))
    for low, high in (("B", "Bk"), ("B", "Bk12"), ("B", "Bsen"), ("Bk12", "Bk"), ("Bsen", "Bk")):
        report["tests"][f"{high} over {low}"] = {
            "right_diff": mean(vals(outputs, high, "right")) - mean(vals(outputs, low, "right")),
            "p_right_higher": p_higher(outputs, low, high, "right")}
    p_silent = p_lower(outputs, "B", "Bk", "silent")
    ratio = mean(vals(outputs, "Bk", "out_tokens")) / mean(vals(outputs, "B", "out_tokens"))
    gaps = {c: mean(vals(outputs, "Bk", "right", c)) - mean(vals(outputs, "B", "right", c)) for c in case_ids}
    c1 = report["tests"]["Bk over B"]
    report["rules"] = {
        "C1 Bk raises items right by 0.10 or more (p < 0.05)": c1["right_diff"] >= 0.10 and c1["p_right_higher"] < 0.05,
        "C2 Bk is ahead of B in every request": all(g > 0 for g in gaps.values()),
        "C3 Bk has fewer silent assertions per output (p < 0.05)": mean(vals(outputs, "Bk", "silent")) < mean(vals(outputs, "B", "silent")) and p_silent < 0.05,
        "C4 Bk writes at most 1.25 times B's output tokens": ratio <= 1.25}
    report["detail"] = {"p_silent_lower": p_silent, "token_ratio_bk_over_b": ratio, "per_request_gap": gaps}
    (HERE / "scores.json").write_text(json.dumps(report, indent=2) + "\n")
    print("\ntests (exact one-sided permutation on each output's share right, 15 against 15):")
    for key, value in report["tests"].items():
        print(f"  {key:16} diff {value['right_diff']:+.3f}  p {value['p_right_higher']:.4f}")
    print(f"silent assertions, Bk fewer than B: p {p_silent:.4f}; token ratio Bk/B {ratio:.3f}; per-request gap Bk - B: "
          + ", ".join(f"{c} {g:+.3f}" for c, g in gaps.items()))
    print("rules:")
    for key, value in report["rules"].items():
        print(f"  {'HOLDS' if value else 'FAILS':5} {key}")


if __name__ == "__main__":
    {"build": cmd_build, "jobs": cmd_jobs, "judge": cmd_judge, "score": cmd_score}[sys.argv[1]]()
