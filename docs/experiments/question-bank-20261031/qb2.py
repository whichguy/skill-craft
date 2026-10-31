#!/usr/bin/env python3
"""QB2 (README.md): one long, loosely worded request over a real workspace, with the tools on.

    python3 qb2.py build   write qb2/prompts/BP1-<arm>.md for arms B, Bp, Qp and Sp
    python3 qb2.py jobs    write jobs-qb2.tsv (and copy the fixture to the workspace the model reads)
    python3 qb2.py judge   write qb2/judge/*.md, qb2/judge/mapping.json and jobs-judge-qb2.tsv
    python3 qb2.py score   read the judge answers and print the tables; writes scores-qb2.json

Arms (all on X1's exercise frame, with the tools on and the host's skill list added):
  B   intake item 9 as shipped (K1-K11 catalog, the model writes the questions)
  Bp  B plus catalog lines K12 (terms and references) and K13 (conflicts and premises) and a look-it-up-first line
  Qp  a fixed bank of the 20 questions plus 7 for K12 and K13, answered by id, with the same line
  Sp  the same bank as imperative statements
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

from bank import bank_item9
from build import ANSWERS
from common import HERE, SUBJECT, X1, envelope, envelope_text, state_block
from qb2_case import BREAKS, CONTEXT, FACTS, GROUPS, ITEMS, SAMPLES_N, SENTENCES, SKILLS
from stats import mean

QB2 = HERE / "qb2"
ARMS = ("B", "Bp", "Qp", "Sp")
CASE_ID = "BP1"
SAMPLES = tuple(range(1, SAMPLES_N + 1))
FIXTURE = HERE.parents[2] / "test" / "shiploop_e2e" / "fixtures" / "node-tickets"
WORK = Path(os.environ.get("QB_WORK") or tempfile.gettempdir()) / "question-bank-20261031"
WORKSPACE = WORK / "workspace" / "node-tickets"

_spec = importlib.util.spec_from_file_location("x1_score", X1 / "score.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)

# catalog lines K12 and K13 in the catalog's own (noun phrase) wording, for arm Bp
EXTRA_LINES = [
    ("K12", "Terms and references",
     ("the names, skills, commands, products and community phrases in the request, and the phrases that point at "
     "something it does not state (\"the usual\", \"as before\"); what each means here and where that was settled (the "
     "installed skills, the repository, or a search), else the best reading and how sure it is.")),
    ("K13", "Conflicts and premises",
     ("any two requirements, numbers or instructions in the request that contradict each other, and any claim about the "
     "existing system that the repository may contradict; the reading the run takes of each and who should confirm it.")),
]
# the same content as bank items, for arms Qp and Sp: (id, question form, statement form)
EXTRA_BANK = [
    ("K12.1", "Which names, skills, commands, products or community phrases in the request need a meaning?",
     "Name the names, skills, commands, products and community phrases in the request that need a meaning."),
    ("K12.2", "Where is each one's meaning settled: the installed skills, the repository, or a search?",
     "State where each one's meaning is settled: the installed skills, the repository, or a search."),
    ("K12.3", ("Which phrases point at something the request does not state (\"the usual\", \"as before\"), and where "
              "can each be found?"),
     ("State the phrases that point at something the request does not state (\"the usual\", \"as before\"), and where "
     "each can be found.")),
    ("K12.4", "For a term nothing settles, what is the best reading, and how sure is it?",
     "State, for a term nothing settles, the best reading and how sure it is."),
    ("K13.1", "Which requirements, numbers or instructions in the request contradict each other?",
     "State which requirements, numbers or instructions in the request contradict each other."),
    ("K13.2", "Which claims about the existing system might the repository contradict, and what does it show?",
     "State which claims about the existing system the repository may contradict, and what it shows."),
    ("K13.3", "Which reading does the run take of each, and who should confirm it?",
     "State the reading the run takes of each, and who should confirm it."),
]
LADDER = ("Terms and references: settle each by looking, in this order: the installed skills listed above, the "
          "repository and its documents, then a search (`research`). When nothing settles it, record the best reading "
          "and how sure you are as the `default`; use `person` only when two readings remain that lead to different work.")

TOOLS_OLD = "In this exercise you have no tools and no files: answer from the request alone. The repository is empty."
ITEM9_RE = re.compile(r"9\. Key questions\..*?what would show it early\.(?=\n\nRULES:)", re.DOTALL)
TEMPLATE_RE = re.compile(r'  "question_categories":.*?  \],\n(?=  "summary")', re.DOTALL)
REQUEST_RE = re.compile(r"----- BEGIN ORIGINAL REQUEST -----.*\Z", re.DOTALL)


def wrap(text: str, indent: str = "   ") -> str:
    return textwrap.fill(text, width=118, initial_indent=indent, subsequent_indent=indent, break_long_words=False,
                         break_on_hyphens=False)


def request_text() -> str:
    paragraphs, current = [], []
    for number, sentence in enumerate(SENTENCES, 1):
        current.append(sentence)
        if number in BREAKS:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def bank9(form: str) -> str:
    """QB1's bank item with the look-it-up-first line before the rows and the K12 and K13 rows after them."""
    head, rows = bank_item9(form).split("   - K1.1 ", 1)
    extra = "".join(f"   - {row[0]} {row[1] if form == 'Q' else row[2]}\n" for row in EXTRA_BANK)
    return head + wrap(LADDER) + "\n   - K1.1 " + rows + extra


def build_prompt(arm: str) -> str:
    text = (X1 / "prompts" / "battleship-B.md").read_text()
    skills = "\n".join(f"- {name}: {desc}" for name, desc in SKILLS)
    tools_new = (wrap("In this exercise you may read files in the working directory, " + CONTEXT + ", with read-only "
                      "shell commands; change nothing and start no server. The host lists the installed skills it "
                      "offers:", "").rstrip() + "\n" + skills)
    assert text.count(TOOLS_OLD) == 1 and len(ITEM9_RE.findall(text)) == 1 and len(TEMPLATE_RE.findall(text)) == 1
    text = text.replace(TOOLS_OLD, tools_new, 1)
    item9 = ITEM9_RE.search(text).group(0)
    if arm == "Bp":
        lines = "\n".join(textwrap.fill(f"{row[0]} {row[1]}: {row[2]}", width=118, initial_indent="   - ",
                                        subsequent_indent="     ", break_long_words=False, break_on_hyphens=False)
                          for row in EXTRA_LINES)
        text = text.replace(item9, item9 + "\n" + lines + "\n" + wrap(LADDER), 1)
    elif arm in ("Qp", "Sp"):
        text = text.replace(item9, bank9("Q" if arm == "Qp" else "S").rstrip("\n"), 1)
        text = TEMPLATE_RE.sub(lambda _m: ANSWERS, text, count=1)
    index = " ".join(f"S{number}: {sentence}" for number, sentence in enumerate(SENTENCES, 1))
    block = ("----- BEGIN ORIGINAL REQUEST -----\n" + request_text() + "\n----- END ORIGINAL REQUEST -----\n"
             "Sentence index of this request (cite S<n>): " + index + "\n")
    return REQUEST_RE.sub(lambda _m: block, text, count=1)


def cmd_build() -> None:
    (QB2 / "prompts").mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        text = build_prompt(arm)
        (QB2 / "prompts" / f"{CASE_ID}-{arm}.md").write_text(text)
        print(f"  {arm:3} {len(text):6d} characters")


def cmd_jobs() -> None:
    if not WORKSPACE.exists():
        WORKSPACE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FIXTURE, WORKSPACE, ignore=shutil.ignore_patterns("node_modules", ".git"))
    rows = []
    for arm in ARMS:
        for sample in SAMPLES:
            prompt = (QB2 / "prompts" / f"{CASE_ID}-{arm}.md").relative_to(HERE).as_posix()
            out = (QB2 / "intake" / f"{CASE_ID}-{arm}-s{sample}.json").relative_to(HERE).as_posix()
            rows.append(f"{SUBJECT}\t{prompt}\t{out}\t{WORKSPACE}")
    (HERE / "jobs-qb2.tsv").write_text("\n".join(rows) + "\n")
    print(f"wrote {len(rows)} QB2 subject jobs; workspace {WORKSPACE}")


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


def cmd_judge() -> None:
    out_dir = QB2 / "judge"
    out_dir.mkdir(parents=True, exist_ok=True)
    items = "\n".join(f"- {i[0]} ({i[3]}): {i[4]}" for i in ITEMS)
    mapping, jobs = {}, []
    for sample in SAMPLES:
        runs = [(arm, sample) for arm in ARMS]
        random.Random(f"qb2-{sample}").shuffle(runs)
        labels, blocks = {}, []
        for number, (arm, s) in enumerate(runs, 1):
            path = QB2 / "intake" / f"{CASE_ID}-{arm}-s{s}.json"
            label = f"O{number}"
            labels[label] = {"arm": arm, "sample": s, "file": path.relative_to(HERE).as_posix()}
            blocks.append(f"===== OUTPUT {label} =====\n{envelope_text(path).strip()}\n===== END OUTPUT {label} =====")
        prompt = JUDGE.format(request=request_text(), facts=FACTS, items=items, outputs="\n\n".join(blocks))
        name = f"qb2-s{sample}"
        (out_dir / f"{name}.md").write_text(prompt)
        mapping[name] = labels
        jobs.append(f"opus\tqb2/judge/{name}.md\tqb2/judge/{name}.out.json")
    (out_dir / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / "jobs-judge-qb2.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} QB2 judge prompts")


def judge_json(path):
    text = json.loads(path.read_text()).get("text") or ""
    return json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))


def cmd_score() -> None:
    mapping = json.loads((QB2 / "judge" / "mapping.json").read_text())
    kind = {i[0]: i[2] for i in ITEMS}
    group = {i[0]: i[1] for i in ITEMS}
    rows, unverified = [], []
    for name, labels in mapping.items():
        verdict = judge_json(QB2 / "judge" / f"{name}.out.json")["outputs"]
        for label, info in labels.items():
            out = HERE / info["file"]
            text = envelope_text(out)
            data = envelope(out)
            usage = data.get("usage") or {}
            grade = verdict.get(label, {})
            for ident, item_kind in kind.items():
                row = (grade.get("items") or {}).get(ident) or {}
                ok = bool(row.get("covered")) and bool(row.get("quote")) and x1.norm(row["quote"]) in x1.norm(text)
                if row.get("covered") and not ok:
                    unverified.append({"arm": info["arm"], "sample": info["sample"], "item": ident})
                rows.append({"arm": info["arm"], "sample": info["sample"], "item": ident, "group": group[ident],
                             "kind": item_kind, "covered": ok, "correct": row.get("correct") if ok else "na",
                             "route": row.get("route") if ok else "none"})
            rows.append({"arm": info["arm"], "sample": info["sample"], "item": "_run",
                         "items_total": grade.get("items_total") or 0, "noise": grade.get("noise") or 0,
                         "out_tokens": usage.get("output_tokens", 0), "reasoning": usage.get("reasoning_output_tokens", 0),
                         "input": usage.get("input_tokens", 0), "cached": usage.get("cached_input_tokens", 0),
                         "commands": len(data.get("commands") or []), "chars": len(text),
                         "parsed": state_block(text) is not None})
    graded = [r for r in rows if r["item"] != "_run"]
    runs = [r for r in rows if r["item"] == "_run"]
    report = {"unverified_quotes": unverified, "arms": {}, "groups": {}, "items": {}}
    print(f"graded {len(runs)} outputs, unverified judge quotes {len(unverified)}")
    print(f"{'arm':3} {'n':>2} {'cover':>6} {'right':>6} {'part':>5} {'wrong':>5} {'person':>6} {'wasted':>6} {'silent':>6} "
          f"{'out_tok':>8} {'in_unc':>7} {'cmds':>5} {'items':>5} {'noise':>5}")
    for arm in ARMS:
        g = [r for r in graded if r["arm"] == arm]
        n = len([r for r in runs if r["arm"] == arm])
        total = len(g)
        mine = [r for r in runs if r["arm"] == arm]
        summary = {
            "n": n, "coverage": sum(r["covered"] for r in g) / total,
            "right": sum(r["correct"] == "yes" for r in g) / total, "partial": sum(r["correct"] == "partial" for r in g) / total,
            "wrong": sum(r["correct"] == "no" for r in g) / total,
            "person_routes": sum(r["route"] == "person" for r in g) / n,
            "wasted_person_routes": sum(r["route"] == "person" and r["kind"] == "env" for r in g) / n,
            "silent": sum(r["route"] == "silent" for r in g) / n,
            "out_tokens": mean(r["out_tokens"] for r in mine), "reasoning": mean(r["reasoning"] for r in mine),
            "uncached_input": mean(r["input"] - r["cached"] for r in mine), "commands": mean(r["commands"] for r in mine),
            "items": mean(r["items_total"] for r in mine), "noise": mean(r["noise"] for r in mine),
            "parsed": sum(r["parsed"] for r in mine)}
        report["arms"][arm] = summary
        print(f"{arm:3} {n:2d} {summary['coverage']:6.2f} {summary['right']:6.2f} {summary['partial']:5.2f} "
              f"{summary['wrong']:5.2f} {summary['person_routes']:6.2f} {summary['wasted_person_routes']:6.2f} "
              f"{summary['silent']:6.2f} {summary['out_tokens']:8.0f} {summary['uncached_input']:7.0f} "
              f"{summary['commands']:5.1f} {summary['items']:5.1f} {summary['noise']:5.1f}")
    print("\ncovered and right (yes) by item group, per output (share of the group's items):")
    print(f"{'group':11} " + " ".join(f"{arm + ' cov/right':>14}" for arm in ARMS))
    for name in GROUPS:
        cells = []
        for arm in ARMS:
            g = [r for r in graded if r["arm"] == arm and r["group"] == name]
            cov, right = sum(r["covered"] for r in g) / len(g), sum(r["correct"] == "yes" for r in g) / len(g)
            report["groups"][f"{name}/{arm}"] = {"coverage": cov, "right": right}
            cells.append(f"{cov:6.2f}/{right:5.2f}  ")
        print(f"{name:11} " + " ".join(f"{c:>14}" for c in cells))
    print("\nper item: runs covered / runs right / routes (of the runs per arm):")
    for ident, _group, _kind, span, _expected in ITEMS:
        cells = []
        for arm in ARMS:
            g = [r for r in graded if r["arm"] == arm and r["item"] == ident]
            routes = Counter(r["route"] for r in g if r["covered"])
            report["items"][f"{ident}/{arm}"] = {"covered": sum(r["covered"] for r in g),
                                                 "right": sum(r["correct"] == "yes" for r in g), "routes": dict(routes)}
            cells.append(f"{sum(r['covered'] for r in g)}/{sum(r['correct'] == 'yes' for r in g)}/{len(g)}")
        print(f"  {ident:3} {span[:46]:46} " + "  ".join(f"{arm} {c}" for arm, c in zip(ARMS, cells)))
    (HERE / "scores-qb2.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    {"build": cmd_build, "jobs": cmd_jobs, "judge": cmd_judge, "score": cmd_score}[sys.argv[1]]()
