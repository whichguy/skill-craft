#!/usr/bin/env python3
"""Build XR's judge prompts (README.md, "XR"): one per case and sample pair (samples 1-2, then 3-4), holding the four
outputs of arms A and B shuffled with the seed ``xr-<case>-<pair>`` and relabelled O1..O4.  The judge sees each question's
id, category, text and `changes`, never its route, and classes it RUNTIME or NOT_RUNTIME by the pre-registered rule.  The
arm map goes to routing/judge/mapping.json.  Writes jobs-judge-routing.tsv for run.py (judge: Opus).
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "question-record-20261031"))
from common import envelope_text, state_block  # noqa: E402
import build_routing  # noqa: E402

PAIRS = {"p12": (1, 2), "p34": (3, 4)}
JUDGE = """\
You classify the questions that the first planning stage of a software-delivery run asked about a request to change an
existing system. For each question decide one class, by this rule only:

RUNTIME: settling it reliably needs the existing system observed while it runs: how fast or how much it handles, what it
keeps across a restart, a crash or a concurrent change, the exact output, order or shape it produces, or which of
conflicting sources (its code, its documents, its tests) holds.
NOT_RUNTIME: anything else: intent or policy the request leaves open, structure or conventions read from the code, the
delivery, or a decision only a person can make.

Judge each question on its own text. You are not told how anyone proposed to answer it, and the outputs are unlabeled.

Context: {context}

The request:
----- BEGIN REQUEST -----
{request}
----- END REQUEST -----

{outputs}

Answer with one JSON object only, no prose: {{"O1": {{"Q1": "RUNTIME", "Q2": "NOT_RUNTIME", ...}}, "O2": {{...}}, ...}},
with every output and every question id listed above."""


def rows(path: Path) -> list[dict]:
    result = state_block(envelope_text(path)) or {}
    return [q for q in result.get("questions") or [] if isinstance(q, dict)]


def main() -> None:
    out = HERE / "routing" / "judge"
    out.mkdir(parents=True, exist_ok=True)
    mapping, jobs = {}, []
    for case in build_routing.CONTEXT:
        for pair, samples in PAIRS.items():
            runs = [(arm, s) for arm in ("A", "B") for s in samples]
            random.Random(f"xr-{case}-{pair}").shuffle(runs)
            labels, blocks = {}, []
            for index, (arm, s) in enumerate(runs, 1):
                path = HERE / "routing" / "terra" / f"{case}-{arm}-s{s}.json"
                label = f"O{index}"
                labels[label] = {"arm": arm, "sample": s, "file": path.relative_to(HERE).as_posix()}
                lines = [f"- {q.get('id')} [{q.get('category')}] {q.get('question')} (changes: {q.get('changes')})"
                         for q in rows(path)]
                blocks.append(f"===== OUTPUT {label} =====\n" + ("\n".join(lines) or "(no questions)")
                              + f"\n===== END OUTPUT {label} =====")
            name = f"routing-{case}-{pair}"
            (out / f"{name}.md").write_text(JUDGE.format(context=build_routing.CONTEXT[case],
                                                         request=build_routing.prompt_of(case),
                                                         outputs="\n\n".join(blocks)))
            mapping[name] = labels
            jobs.append(f"opus\trouting/judge/{name}.md\trouting/judge/{name}.out.json")
    (out / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (HERE / "jobs-judge-routing.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} judge prompts")


if __name__ == "__main__":
    main()
