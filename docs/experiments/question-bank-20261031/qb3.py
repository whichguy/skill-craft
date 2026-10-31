#!/usr/bin/env python3
"""QB3 (README.md): does a 12-word cap on the answers cut the cost, and is the saving the bank's or the cap's?

    python3 qb3.py build   write prompts/<case>-Qt.md and <case>-Bt.md
    python3 qb3.py jobs    write jobs-qb3.tsv (arms Qt and Bt, samples 1-4)
    python3 qb3.py judge   write judge3/*.md, judge3/mapping.json and jobs-judge-qb3.tsv
    python3 qb3.py score   print the tables and rules R6-R8; writes scores-qb3.json

Arms: Qt is the question bank of arm Qb with one added sentence (every answer at most 12 words); Bt is the shipped ledger
of arm B with one added sentence (every field of a row at most 12 words).  B and Qb samples 1-4 are QB1's own outputs and sit
in the same judge calls as anchors, so each comparison is graded in one call.
"""
import importlib.util
import json
import random
import sys

from common import CASES, HERE, SUBJECT, envelope_text, out_path, prompt_path
from score import collect, lower_p, summarize

JUDGE_DIR = HERE / "judge3"
ARMS = ("B", "Qb", "Qt", "Bt")
SAMPLES = (1, 2, 3, 4)
PAIRS = {"p12": (1, 2), "p34": (3, 4)}
CAP_Q = " Keep each `answer` to 12 words or fewer."
CAP_B = " Keep every field of a row to 12 words or fewer."
ANCHOR_Q = "   assumes and records.\n"
ANCHOR_B = '   settled, or "nothing: the default proceeds").\n'

_spec = importlib.util.spec_from_file_location("qb1_judge", HERE / "judge.py")
qb1_judge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qb1_judge)


def cmd_build() -> None:
    for case in CASES:
        base_q = prompt_path(case["id"], "Qb").read_text()
        base_b = prompt_path(case["id"], "B").read_text()
        assert base_q.count(ANCHOR_Q) == 1 and base_b.count(ANCHOR_B) == 1, case["id"]
        text_q = base_q.replace(ANCHOR_Q, ANCHOR_Q.rstrip("\n") + CAP_Q + "\n", 1)
        text_b = base_b.replace(ANCHOR_B, ANCHOR_B.rstrip("\n") + CAP_B + "\n", 1)
        assert text_q.replace(CAP_Q, "", 1) == base_q and text_b.replace(CAP_B, "", 1) == base_b
        (HERE / "prompts" / f"{case['id']}-Qt.md").write_text(text_q)
        (HERE / "prompts" / f"{case['id']}-Bt.md").write_text(text_b)
    print(f"wrote {2 * len(CASES)} prompts")


def cmd_jobs() -> None:
    rows = []
    for case in CASES:
        for arm in ("Qt", "Bt"):
            for sample in SAMPLES:
                prompt = prompt_path(case["id"], arm).relative_to(HERE.parent).as_posix()
                out = out_path(case["id"], arm, sample).relative_to(HERE).as_posix()
                rows.append(f"{SUBJECT}\t../{prompt}\t{out}")
    (HERE / "jobs-qb3.tsv").write_text("\n".join(rows) + "\n")
    print(f"wrote {len(rows)} QB3 subject jobs")


def cmd_judge() -> None:
    full = qb1_judge.full_prompts()
    JUDGE_DIR.mkdir(exist_ok=True)
    mapping, jobs = {}, []
    for case in CASES:
        for pair, samples in PAIRS.items():
            runs = [(arm, s) for arm in ARMS for s in samples]
            random.Random(f"qb3-{case['id']}-{pair}").shuffle(runs)
            labels, blocks = {}, []
            for index, (arm, s) in enumerate(runs, 1):
                path = out_path(case["id"], arm, s)
                label = f"O{index}"
                labels[label] = {"arm": arm, "sample": s, "file": str(path.relative_to(HERE.parent))}
                blocks.append(f"===== OUTPUT {label} =====\n{envelope_text(path).strip()}\n===== END OUTPUT {label} =====")
            decisions = "\n".join(f"- {g['id']}: {g['decision']} (full request: {g['reference']})"
                                  for g in case["ground_truth"])
            prompt = qb1_judge.x1.JUDGE.format(full=full[case["id"]], vague=" ".join(case["vague"]),
                                               decisions=decisions, outputs="\n\n".join(blocks))
            name = f"qb3-{case['id']}-{pair}"
            (JUDGE_DIR / f"{name}.md").write_text(prompt)
            mapping[name] = labels
            jobs.append(f"opus\tjudge3/{name}.md\tjudge3/{name}.out.json")
    (JUDGE_DIR / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / "jobs-judge-qb3.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} QB3 judge prompts")


def holds(x, ref, token_ceiling):
    """The four clauses R3 and R8 share: recall, output tokens, agreement and noise of ``x`` against ``ref``."""
    clauses = {"recall within 3 points": x["recall"] >= ref["recall"] - 0.03,
               f"output tokens at most {token_ceiling:.0%}": x["out_tokens"] <= token_ceiling * ref["out_tokens"],
               "default agreement within 2 points": (x["agreement"] or 0) >= (ref["agreement"] or 0) - 0.02,
               "noise share at most 5 points above": (x["noise_share"] or 0) <= (ref["noise_share"] or 0) + 0.05}
    return clauses, all(clauses.values())


def cmd_score() -> None:
    runs, unverified = collect(JUDGE_DIR, "qb3-")
    arms = {arm: summarize(runs, arm) for arm in ARMS}
    report = {"unverified_quotes": unverified, "arms": arms, "rules": {}}
    r6_clauses, r6 = holds(arms["Qt"], arms["Qb"], 0.80)
    report["rules"]["R6 the cap cuts the bank's cost (Qt against Qb)"] = {
        "clauses": r6_clauses, "holds": r6 and lower_p(runs, "Qb", "Qt", "out_tokens") < 0.05,
        "p_tokens_lower": lower_p(runs, "Qb", "Qt", "out_tokens")}
    ratio = arms["Qt"]["out_tokens"] / arms["Bt"]["out_tokens"]
    p7 = lower_p(runs, "Bt", "Qt", "out_tokens")
    report["rules"]["R7 the bank is cheaper than the ledger at equal terseness (Qt against Bt)"] = {
        "token_ratio_qt_over_bt": ratio, "p_tokens_lower": p7, "recall_gap_qt_minus_bt": arms["Qt"]["recall"] - arms["Bt"]["recall"],
        "holds": ratio <= 0.85 and p7 < 0.05 and arms["Qt"]["recall"] >= arms["Bt"]["recall"] - 0.03}
    for arm in ("Qt", "Bt"):
        clauses, ok = holds(arms[arm], arms["B"], 0.75)
        report["rules"][f"R8 {arm} replaces B in intake item 9"] = {"clauses": clauses, "holds": ok}
    (HERE / "scores-qb3.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"runs {len(runs)}, unverified judge quotes {len(unverified)}, unparsed {sum(a['unparsed'] for a in arms.values())}")
    print(f"{'arm':3} {'n':>3} {'recall':>7} {'agree':>6} {'noise':>6} {'rows':>5} {'person':>6} {'out_tok':>8} {'reason':>7} "
          f"{'in_unc':>7} {'secs':>5} {'cov/1k':>7}")
    for arm in ARMS:
        a = arms[arm]
        print(f"{arm:3} {a['n']:3d} {a['recall']:7.3f} {a['agreement'] or 0:6.2f} {a['noise_share'] or 0:6.2f} {a['rows']:5.1f} "
              f"{a['person']:6.2f} {a['out_tokens']:8.0f} {a['reasoning']:7.0f} {a['uncached_in']:7.0f} {a['seconds']:5.1f} "
              f"{a['covered_per_1k_out'] or 0:7.2f}")
    print(json.dumps(report["rules"], indent=2))


if __name__ == "__main__":
    {"build": cmd_build, "jobs": cmd_jobs, "judge": cmd_judge, "score": cmd_score}[sys.argv[1]]()
