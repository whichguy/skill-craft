#!/usr/bin/env python3
"""Build pilot X1's judge prompts: one per case, its outputs shuffled and relabelled O1..On (mapping kept apart).

The judge sees the full case prompt (the reference), the vague request the subjects saw, the ground-truth decisions
and each output's text.  It never sees an arm label.  Usage: python3 judge_build.py SAMPLES (e.g. 1,2)
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FULL = Path("/Users/dadleet/src/skill-craft/test/shiploop_e2e/cases.json")

JUDGE = """\
You are grading the first planning stage of a software-delivery harness. A model received only the VAGUE REQUEST
below and had to map it to outcomes, boundaries and open questions, recording a default for anything no evidence
could settle (the run is unattended). You also see the FULL REQUEST the user really meant, and a list of DECISIONS the
full request pins that the vague one leaves open. Grade each OUTPUT on what its text says; its format, length and
field names are irrelevant, and you do not know how any output was produced.

For each output and each decision:
- covered: true when the output, anywhere (summary, questions, assumptions, defaults, boundaries, risks), raises that
  decision as a question, records a default or assumption for it, or states it as a boundary, so that a later stage
  would decide it deliberately rather than by accident. A passing mention that settles nothing is not covered.
- quote: when covered, the shortest verbatim excerpt (at most 40 words) copied character for character from that
  output that shows it; otherwise null. A script checks every quote against the output; one not found counts as not
  covered.
- default_matches: "yes" when the output commits to an answer or default for that decision that agrees with the full
  request; "no" when it commits to one that conflicts with it; "na" when it commits to none or does not cover it.

For each output also give:
- items_total: how many distinct questions, open items or recorded assumptions/defaults the output raises;
- noise: how many of those would not change what is built, how it is checked or how it is delivered for this
  request (generic or ceremonial items), with up to three short examples in noise_examples.

Answer with JSON only, no prose, in this shape:
{{"outputs": {{"O1": {{"decisions": {{"<decision id>": {{"covered": true, "quote": "...", "default_matches": "yes"}}}},
"items_total": 0, "noise": 0, "noise_examples": []}}}}}}

FULL REQUEST (what the user meant):
{full}

VAGUE REQUEST (what the model saw):
{vague}

DECISIONS:
{decisions}

{outputs}
"""


def output_text(path: Path) -> str:
    envelope = json.loads(path.read_text())
    return envelope.get("text") or ""


def main() -> None:
    samples = [int(s) for s in sys.argv[1].split(",")]
    cases = json.loads((HERE / "cases.json").read_text())["cases"]
    full = {}
    data = json.loads(FULL.read_text())
    rows = data if isinstance(data, list) else data.get("cases", data)
    for key, row in (rows.items() if isinstance(rows, dict) else [(r.get("id"), r) for r in rows]):
        full[key] = row.get("prompt")
    mapping = {}
    for case in cases:
        runs = [(arm, s) for arm in ("A", "B", "C") for s in samples]
        random.Random(f"x1-{case['id']}").shuffle(runs)
        labels = {}
        blocks = []
        for index, (arm, s) in enumerate(runs, 1):
            path = HERE / "outputs" / f"{case['id']}-{arm}-s{s}.json"
            label = f"O{index}"
            labels[label] = {"arm": arm, "sample": s, "file": path.name}
            blocks.append(f"===== OUTPUT {label} =====\n{output_text(path).strip()}\n===== END OUTPUT {label} =====")
        decisions = "\n".join(f"- {g['id']}: {g['decision']} (full request: {g['reference']})"
                              for g in case["ground_truth"])
        prompt = JUDGE.format(full=full[case["id"]], vague=" ".join(case["vague"]), decisions=decisions,
                              outputs="\n\n".join(blocks))
        (HERE / "judge" / f"{case['id']}.md").write_text(prompt)
        mapping[case["id"]] = labels
    (HERE / "judge" / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    print("wrote", len(cases), "judge prompts")


if __name__ == "__main__":
    main()
