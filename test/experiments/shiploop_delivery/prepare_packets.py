#!/usr/bin/env python3
"""Freeze synthetic fresh-context packets for the consumer-delivery pilot.

Run variant A before changing the catalog and variant B after candidate wording
is in place. This writes only the explicitly selected fixture directory; it
does not execute ShipLoop, inspect a repository, or contact a target.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shiploop_navigator_prompts import PROMPTS  # noqa: E402


def load_json(name: str):
    return json.loads((EXPERIMENT / name).read_text(encoding="utf-8"))


def packet(scenario: dict, variant: str, repetition: int) -> str:
    """Render an execution-free packet without leaking its grading oracle."""
    facts = "\n".join(f"- {fact}" for fact in scenario["durable_facts"])
    references = "\n".join(
        f"- {reference}" for reference in scenario["reference_materials"]
    )
    return f"""# ShipLoop fresh-context interpretation packet

Variant: {variant}
Scenario: {scenario["id"]}
Independent repetition: {repetition} of 2

This is a synthetic, read-only interpretation exercise. Do not execute commands,
inspect an ambient repository, contact a target, create a ShipLoop run, or submit
a completion callback. The facts below are the entire durable context.

## Current ShipLoop assignment

Current node: `{scenario["stage"]}`
Action: `synthetic-{variant.lower()}-{scenario["id"]}-r{repetition}`

## Original request

{scenario["original_request"]}

## Durable facts

{facts}

## Available reference material

{references}

## Response requested

Describe the next appropriate action, which facts require a user decision or
current evidence, which evidence is still needed, and whether this assignment
would end in `done`, `blocked`, or `repeat`. Do not claim an external effect.

## Current stage instructions

{PROMPTS[scenario["stage"]]}
"""


def prepare(
    variant: str, output: Path, scenario_ids: tuple[str, ...] = ()
) -> list[Path]:
    if variant == "authority":
        # Keep grading criteria private; interpreters receive facts, current
        # stage instructions and the policy locator, never the oracle file.
        policy = ROOT / "skills" / "shiploop" / "references" / "delivery-authority.md"
        scenarios = [
            {
                "id": case["id"],
                "stage": case["stage"],
                "original_request": case["request"],
                "durable_facts": case["facts"],
                "reference_materials": [f"Read the packaged delivery-authority policy: {policy}"],
            }
            for case in load_json("authority-cases.json")
        ]
    else:
        scenarios = load_json("scenarios.json")
    by_id = {scenario["id"]: scenario for scenario in scenarios}
    if scenario_ids:
        unknown = set(scenario_ids) - set(by_id)
        if unknown:
            raise ValueError(f"unknown scenario identifiers: {', '.join(sorted(unknown))}")
        scenarios = [by_id[identifier] for identifier in scenario_ids]
    output.mkdir(parents=True, exist_ok=False)
    written = []
    for scenario in scenarios:
        for repetition in (1, 2):
            path = output / f"{scenario['id']}-r{repetition}.md"
            path.write_text(packet(scenario, variant, repetition), encoding="utf-8")
            written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("A", "B", "B2", "authority"), required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help="Defaults to packets/<variant>; refuses to overwrite a frozen packet set.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Optional fixed scenario identifier; repeat only for an explicit follow-up set.",
    )
    args = parser.parse_args()
    output = args.output or EXPERIMENT / "packets" / args.variant
    written = prepare(args.variant, output.resolve(), tuple(args.scenario))
    print(json.dumps({"variant": args.variant, "packets": len(written), "output": str(output.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
