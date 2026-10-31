#!/usr/bin/env python3
"""Build pilot X1's subject prompts: one per case and arm.

Arm A is ShipLoop's intake duty as shipped (shiploop_prompts.duty("intake")); B adds a key-question item with a fixed
category catalog; C adds the same item without the catalog.  Everything else is byte-identical across arms.
Usage: python3 build.py SHIPLOOP_SCRIPTS_DIR
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[1])
import shiploop_prompts  # noqa: E402

DUTY = shiploop_prompts.duty("intake", delegation="inline").rstrip("\n")

FIELDS = (
    "Per question: `id` (Q1, Q2, ...), `category`, the `question`, `changes` (the requirement, decision, test or\n"
    "   delivery step its answer changes), `route` (inspect: the repository or environment answers it; research:\n"
    "   documentation or other sources answer it; experiment: only running something answers it; default: no evidence\n"
    "   can answer it, so the run assumes `default` and records it; person: only a person can decide it), `default` (the\n"
    "   answer the run assumes and records if nothing settles it) and `blocks` (what cannot proceed until it is\n"
    "   settled, or \"nothing: the default proceeds\")."
)
CATALOG = """\
   - K1 Outcome and consumer: who uses the result, through which entry point, and what observation shows it works?
   - K2 Scope and preserved behaviour: what is in and out, and what existing behaviour must not change?
   - K3 Interfaces and contracts: the exact inputs, outputs, commands, endpoints, files or messages, their names,
     shapes, status codes and errors.
   - K4 Rules and edge cases: the domain rules, limits, invalid inputs, boundaries and end conditions.
   - K5 State and data: what state exists, who owns it, where it lives and for how long, who may see it, and what
     happens on a concurrent change or a restart.
   - K6 Runtime and dependencies: language and runtime versions, allowed or forbidden dependencies, configuration
     (ports, environment variables, files).
   - K7 Structure: the modules or seams the behaviour needs so it can be tested and changed in isolation.
   - K8 Verification: the test framework, its command, and the check that observes each outcome at its real boundary.
   - K9 Delivery: where the result must run or be delivered, and the access that needs.
   - K10 Quality attributes: performance, security, accessibility, interface polish or other bounds.
   - K11 Risks: what would most likely make this work fail or be rejected, and what would show it early."""

ITEM9 = {
    "A": "",
    "B": ("9. Key questions. Ask the key questions about this request before anything is planned. For each category\n"
          "   below decide whether it applies to this request (`question_categories`; one that does not apply gives its\n"
          "   reason in a few words). For each that applies, write in `questions` the questions whose answers would\n"
          "   change a requirement, a design decision, a test or the delivery, and only those.\n   " + FIELDS + "\n"
          + CATALOG),
    "C": ("9. Key questions. Ask the key questions about this request before anything is planned: write in\n"
          "   `questions` the questions whose answers would change a requirement, a design decision, a test or the\n"
          "   delivery, and only those.\n   " + FIELDS),
}

QUESTION_ROW = ('    {"blocks": "...", "category": "...", "changes": "...", "default": "...", "id": "Q1", '
                '"question": "...", "route": "inspect|research|experiment|default|person"}')
TEMPLATE = {
    "A": ['  "evidence_refs": [],',
          '  "headline": "<one line for the user: what this step established>",',
          '  "outcome": "done",',
          '  "summary": "<one clause per request sentence S<n>: the outcome, boundary, default or open question it maps to>"'],
    "B": ['  "evidence_refs": [],',
          '  "headline": "<one line for the user: what this step established>",',
          '  "outcome": "done",',
          '  "question_categories": [{"applies": "yes", "id": "K1"}, {"applies": "no", "id": "K10", "reason": "..."}],',
          '  "questions": [', QUESTION_ROW, '  ],',
          '  "summary": "<one clause per request sentence S<n>: the outcome, boundary, default or open question it maps to>"'],
    "C": ['  "evidence_refs": [],',
          '  "headline": "<one line for the user: what this step established>",',
          '  "outcome": "done",',
          '  "questions": [', QUESTION_ROW, '  ],',
          '  "summary": "<one clause per request sentence S<n>: the outcome, boundary, default or open question it maps to>"'],
}

FRAME = """\
ShipLoop navigator | intake (exercise)
You are the host model of ShipLoop, a script-driven software-delivery harness, doing its first stage, `intake`, for the
request below. The run is unattended: no person will answer questions during it. Do only this stage and implement
nothing. In this exercise you have no tools and no files: answer from the request alone. {context}
Goal: Map the request to outcomes, boundaries and open questions in this result's `summary`.
Done when (confirm each before answering):
- every sentence of the request maps to an outcome, a boundary or an open question
- each open question names who answers it (discovery, or a recorded default) and what it blocks
- the result says where the outcome will be visible, and when

Current stage guidance:
{duty}

RULES:
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.

Result template:
```shiploop-state
{{
{template}
}}
```
Fill the template: each key once, every placeholder (<...> and "...") replaced. Answer with the filled result only, in
one ```shiploop-state fenced block.

Original request (preserve user scope):
----- BEGIN ORIGINAL REQUEST -----
{request}
----- END ORIGINAL REQUEST -----
Sentence index of this request (cite S<n>): {index}
"""


def main() -> None:
    cases = json.loads((HERE / "cases.json").read_text())["cases"]
    out = HERE / "prompts"
    out.mkdir(exist_ok=True)
    for case in cases:
        for arm in ("A", "B", "C"):
            duty = DUTY + ("\n" + ITEM9[arm] if ITEM9[arm] else "")
            text = FRAME.format(context=case["context"], duty=duty, template="\n".join(TEMPLATE[arm]),
                                request=" ".join(case["vague"]),
                                index=" ".join(f"S{i}: {s}" for i, s in enumerate(case["vague"], 1)))
            (out / f"{case['id']}-{arm}.md").write_text(text)
    print(f"wrote {len(cases) * 3} prompts to {out}")


if __name__ == "__main__":
    main()
