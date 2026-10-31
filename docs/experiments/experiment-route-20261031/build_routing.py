#!/usr/bin/env python3
"""Build XR's intake prompts (README.md, "XR"): four brownfield requests, arms A and B, samples 1-4, for run.py.

The frame is pilot X1's (../key-questions-intake-20261030/build.py FRAME, unchanged): one intake exercise with no tools. The
duty is ShipLoop's intake duty as shipped (``shiploop_prompts.duty("intake", delegation="inline")``, whose item 9 already
carries the K1-K11 catalog and the question ledger), with the result template of X1's catalog arm, which is the shipped
template. Arm A is that duty; arm B differs in one place, the definition of the `experiment` route (ROUTE_A -> ROUTE_B).
The requests are the live cases' own prompts (test/shiploop_e2e/cases.json), split into sentences by ShipLoop's own
splitter; ticket-import is the new case's prompt (README.md, "XI").  Usage: build_routing.py
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_prompts  # noqa: E402
import shiploop_request  # noqa: E402

_spec = importlib.util.spec_from_file_location("x1_build", HERE.parent / "key-questions-intake-20261030" / "build.py")
x1 = importlib.util.module_from_spec(_spec)
sys.argv = [sys.argv[0], str(SCRIPTS)]
_spec.loader.exec_module(x1)

ROUTE_A = "experiment: only running something answers it;"
ROUTE_B = ("experiment: only running something answers it, as for how fast or how much the existing system handles,\n"
           "   what it keeps across a restart or a concurrent change, and what it really does where its code, documents\n"
           "   and tests disagree;")
SAMPLES = (1, 2, 3, 4)
CASES = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())
CONTEXT = {
    "user-listing": "The repository exists: an existing Node.js project; the next stage (discovery) will inspect it.",
    "ticket-assignment": "The repository exists: an existing Node.js service; the next stage (discovery) will inspect it.",
    "ticket-escalation": ("The repository exists: an existing Node.js service that an earlier run extended with ticket "
                          "assignment; the next stage (discovery) will inspect it."),
    "ticket-import": "The repository exists: an existing Node.js service; the next stage (discovery) will inspect it.",
}
IMPORT_PROMPT = (HERE / "ticket-import-prompt.txt").read_text().strip()


def prompt_of(case: str) -> str:
    return IMPORT_PROMPT if case == "ticket-import" else CASES[case]["prompt"]


def duty(arm: str) -> str:
    text = shiploop_prompts.duty("intake", delegation="inline").rstrip("\n")
    assert text.count(ROUTE_A) == 1, "the shipped route definition moved; rebuild ROUTE_A"
    return text if arm == "A" else text.replace(ROUTE_A, ROUTE_B)


def main() -> None:
    out = HERE / "routing" / "prompts"
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for case in CONTEXT:
        request = prompt_of(case)
        parts = shiploop_request.sentences(request)
        for arm in ("A", "B"):
            text = x1.FRAME.format(context=CONTEXT[case], duty=duty(arm), template="\n".join(x1.TEMPLATE["B"]),
                                   request=request, index=" ".join(f"S{i}: {s}" for i, s in enumerate(parts, 1)))
            path = out / f"{case}-{arm}.md"
            path.write_text(text)
            for sample in SAMPLES:
                jobs.append(f"codex:gpt-6.1-terra:high\trouting/prompts/{case}-{arm}.md\trouting/terra/{case}-{arm}-s{sample}.json")
    (HERE / "jobs-routing.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(CONTEXT) * 2} prompts and {len(jobs)} jobs")


if __name__ == "__main__":
    main()
