#!/usr/bin/env python3
"""Build X2's judge prompts (README.md, "X2"): per case and sample pair, the six spec outputs of arms A, D and C,
shuffled with the seed ``x2-<subject>-<case>-<pair>`` and relabelled O1..O6; each output is shown as its SPEC.MD (the
fenced spec.md block) and its RESULT (the shiploop-state block).  The arm map goes to judge/spec-<slug>-mapping.json.
Writes jobs-judge-<tag>-<slug>.tsv (judge: Opus).  Usage: judge_spec.py [SUBJECT_SLUG] [ARMS] [TAG]
(X2: A,D,C spec; X2b: A,B spec-x2b, the same judge text with four outputs a call).
"""
import json
import random
import re
import sys

from common import CASES, HERE, envelope_text, spec_block
from judge_intake import full_prompts

PAIRS = {"p12": (1, 2), "p34": (3, 4)}

JUDGE = """\
You are grading the `spec` stage of a software-delivery harness. A model saw only the VAGUE REQUEST below (and the
earlier stages' results, which also came from the vague request) and had to write the living spec, KNOWLEDGE/spec.md,
and a stage result for an unattended run, recording a default for anything no evidence could settle. You also see the
FULL REQUEST the user really meant, and a list of DECISIONS the full request pins that the vague one leaves open. Grade
each OUTPUT on what its text says; its length and style are irrelevant, and you do not know how any output was produced.

Each OUTPUT has two parts: SPEC.MD (the living spec it wrote) and RESULT (its stage result, with a summary).

For each output and each decision:
- spec_pinned: true when SPEC.MD states one specific choice for this decision (in a requirement, an acceptance line, a
  non-functional requirement, a constraint, or a recorded default or assumption), so an implementer reading only SPEC.MD
  would build that choice. A statement that leaves the choice open ("a configurable port", "a suitable test framework",
  "to be decided", "an appropriate format") is not pinned.
- acceptance: true when spec_pinned and the choice is stated in an acceptance line (or a requirement line) that says
  how it will be confirmed (a command, a request and its expected response, an observation).
- carried: true when spec_pinned, or when SPEC.MD or RESULT records this decision as an open question, a gap, an
  assumption or a default for a later stage to settle, so a later stage would decide it deliberately rather than by
  accident. A passing mention that settles nothing is not carried.
- quote: when carried, the shortest verbatim excerpt (at most 40 words) copied character for character from SPEC.MD
  that shows it, or from RESULT only when SPEC.MD does not carry it; otherwise null. A script checks every quote
  against the output; one not found counts as not carried, and a pinned decision whose quote is not in SPEC.MD counts
  as not pinned.
- matches: "yes" when the output commits to a choice for that decision (SPEC.MD first, else RESULT) that agrees with
  the full request; "no" when it commits to one that conflicts with it; "na" when it commits to none.
- flagged: true when the committed choice is marked as a default, an assumption or an open question that the owner or
  a later stage can confirm or change (for example listed under "Open questions", or labelled default or assumed);
  false otherwise.

For each output also give:
- requirements: how many requirements SPEC.MD numbers (R-<n>);
- scope_additions: how many of those add a feature or obligation that neither the vague request nor the full request
  asks for (generic quality requirements the harness asks every spec to assess, such as a polished interface, are not
  additions), with up to three short examples in scope_examples.

Answer with JSON only, no prose, in this shape:
{{"outputs": {{"O1": {{"decisions": {{"<decision id>": {{"spec_pinned": true, "acceptance": true, "carried": true,
"quote": "...", "matches": "yes", "flagged": false}}}}, "requirements": 0, "scope_additions": 0,
"scope_examples": []}}}}}}

FULL REQUEST (what the user meant):
{full}

VAGUE REQUEST (what the model saw):
{vague}

DECISIONS:
{decisions}

{outputs}
"""


def parts(text: str) -> tuple[str, str]:
    spec = spec_block(text).strip()
    match = re.search(r"```shiploop-state\s*(.*?)```", text, re.S)
    return spec, (match.group(1).strip() if match else "")


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    arms = tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("A", "D", "C")
    tag = sys.argv[3] if len(sys.argv) > 3 else "spec"          # X2b: A,B spec-x2b
    seed = {"spec": "x2", "spec-x2b": "x2b"}[tag]
    full = full_prompts()
    mapping, jobs = {}, []
    for case in CASES:
        for pair, samples in PAIRS.items():
            runs = [(arm, s) for arm in arms for s in samples
                    if (HERE / "spec" / slug / f"{case['id']}-{arm}-s{s}.json").is_file()]
            if not runs:
                continue
            random.Random(f"{seed}-{slug}-{case['id']}-{pair}").shuffle(runs)
            labels, blocks = {}, []
            for index, (arm, s) in enumerate(runs, 1):
                path = HERE / "spec" / slug / f"{case['id']}-{arm}-s{s}.json"
                spec, result = parts(envelope_text(path))
                label = f"O{index}"
                labels[label] = {"arm": arm, "sample": s, "file": str(path.relative_to(HERE))}
                blocks.append(f"===== OUTPUT {label} =====\n----- SPEC.MD -----\n{spec}\n----- RESULT -----\n{result}\n"
                              f"===== END OUTPUT {label} =====")
            decisions = "\n".join(f"- {g['id']}: {g['decision']} (full request: {g['reference']})"
                                  for g in case["ground_truth"])
            prompt = JUDGE.format(full=full[case["id"]], vague=" ".join(case["vague"]), decisions=decisions,
                                  outputs="\n\n".join(blocks))
            name = f"{tag}-{slug}-{case['id']}-{pair}"
            (HERE / "judge" / f"{name}.md").write_text(prompt)
            mapping[name] = labels
            jobs.append(f"opus\tjudge/{name}.md\tjudge/{name}.out.json")
    (HERE / "judge" / f"{tag}-{slug}-mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / f"jobs-judge-{tag}-{slug}.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} {tag} judge prompts for {slug}")


if __name__ == "__main__":
    main()
