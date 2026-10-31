#!/usr/bin/env python3
"""Build QB1's judge prompts with X1's judge text unchanged (../key-questions-intake-20261030/judge_build.py JUDGE).

One prompt per case and sample pair (p12, p34, p56, p78): the twelve outputs of arms A, B, Qb, Sb, Bq and Bs, shuffled
with the seed ``qb1-<case>-<pair>`` and relabelled O1..O12, so every arm is graded in the same call and none is
identifiable.  The arm map goes to judge/mapping.json, apart from the prompts.  Writes jobs-judge.tsv for run.py (judge:
Opus).  Usage: python3 judge.py
"""
import importlib.util
import json
import random

from common import ARMS, CASES, HERE, PAIRS, X1, envelope_text, out_path

_spec = importlib.util.spec_from_file_location("x1_judge_build", X1 / "judge_build.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)
FULL = HERE.parents[2] / "test" / "shiploop_e2e" / "cases.json"


def full_prompts() -> dict:
    data = json.loads(FULL.read_text())
    rows = data if isinstance(data, list) else data.get("cases", data)
    items = rows.items() if isinstance(rows, dict) else [(row.get("id"), row) for row in rows]
    return {key: row.get("prompt") for key, row in items}


def main() -> None:
    full = full_prompts()
    mapping, jobs = {}, []
    out_dir = HERE / "judge"
    out_dir.mkdir(exist_ok=True)
    for case in CASES:
        for pair, samples in PAIRS.items():
            runs = [(arm, s) for arm in ARMS for s in samples]
            random.Random(f"qb1-{case['id']}-{pair}").shuffle(runs)
            labels, blocks = {}, []
            for index, (arm, s) in enumerate(runs, 1):
                path = out_path(case["id"], arm, s)
                label = f"O{index}"
                labels[label] = {"arm": arm, "sample": s, "file": str(path.relative_to(HERE.parent))}
                blocks.append(f"===== OUTPUT {label} =====\n{envelope_text(path).strip()}\n===== END OUTPUT {label} =====")
            decisions = "\n".join(f"- {g['id']}: {g['decision']} (full request: {g['reference']})"
                                  for g in case["ground_truth"])
            prompt = x1.JUDGE.format(full=full[case["id"]], vague=" ".join(case["vague"]), decisions=decisions,
                                     outputs="\n\n".join(blocks))
            name = f"qb1-{case['id']}-{pair}"
            (out_dir / f"{name}.md").write_text(prompt)
            mapping[name] = labels
            jobs.append(f"opus\tjudge/{name}.md\tjudge/{name}.out.json")
    (out_dir / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / "jobs-judge.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} judge prompts")


if __name__ == "__main__":
    main()
