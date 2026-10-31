#!/usr/bin/env python3
"""Build X1-T's judge prompts with X1's judge text unchanged (../key-questions-intake-20261030/judge_build.py JUDGE).

One prompt per case and sample pair (samples 1-2, then 3-4): the six outputs of arms A, B and C, shuffled with the seed
``x1t-<subject>-<case>-<pair>`` and relabelled O1..O6.  The arm map goes to judge/intake-<subject>-mapping.json, apart
from the prompts.  Writes jobs-judge-intake.tsv for run.py (judge: Opus).  Usage: judge_intake.py [SUBJECT_SLUG]
"""
import importlib.util
import json
import random
import sys

from common import CASES, HERE, X1, envelope_text, intake_out

_spec = importlib.util.spec_from_file_location("x1_judge_build", X1 / "judge_build.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)
PAIRS = {"p12": (1, 2), "p34": (3, 4)}


def full_prompts() -> dict:
    data = json.loads(x1.FULL.read_text())
    rows = data if isinstance(data, list) else data.get("cases", data)
    items = rows.items() if isinstance(rows, dict) else [(row.get("id"), row) for row in rows]
    return {key: row.get("prompt") for key, row in items}


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    full = full_prompts()
    mapping, jobs = {}, []
    out_dir = HERE / "judge"
    out_dir.mkdir(exist_ok=True)
    for case in CASES:
        for pair, samples in PAIRS.items():
            runs = [(arm, s) for arm in ("A", "B", "C") for s in samples]
            random.Random(f"x1t-{slug}-{case['id']}-{pair}").shuffle(runs)
            labels, blocks = {}, []
            for index, (arm, s) in enumerate(runs, 1):
                path = intake_out(slug, case["id"], arm, s)
                label = f"O{index}"
                labels[label] = {"arm": arm, "sample": s, "file": str(path.relative_to(HERE.parent))}
                blocks.append(f"===== OUTPUT {label} =====\n{envelope_text(path).strip()}\n===== END OUTPUT {label} =====")
            decisions = "\n".join(f"- {g['id']}: {g['decision']} (full request: {g['reference']})"
                                  for g in case["ground_truth"])
            prompt = x1.JUDGE.format(full=full[case["id"]], vague=" ".join(case["vague"]), decisions=decisions,
                                     outputs="\n\n".join(blocks))
            name = f"intake-{slug}-{case['id']}-{pair}"
            (out_dir / f"{name}.md").write_text(prompt)
            mapping[name] = labels
            jobs.append(f"opus\tjudge/{name}.md\tjudge/{name}.out.json")
    (out_dir / f"intake-{slug}-mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / f"jobs-judge-intake-{slug}.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} intake judge prompts for {slug}")


if __name__ == "__main__":
    main()
