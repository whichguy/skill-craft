"""Create anonymized pairwise inputs without calling models or grading them."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output
    manifest = json.loads((root / "manifest.json").read_text())
    kinds = {
        "synthetic-planning-only": ({"drag", "retry", "refresh"}, {"A", "B"}),
        "equal-information-planning-only": ({"equal-retry", "recovery"}, {"A", "C"}),
    }
    cases, variants = kinds[manifest["kind"]]
    if set(manifest["judge_order"]) != cases or any(
        len(order) != 2 or set(order) != variants for order in manifest["judge_order"].values()
    ):
        raise ValueError("unexpected judge matrix")
    guidance = Path(__file__).with_name("judge-instructions.md").read_text()
    preregistration = Path(__file__).with_name("README.md").read_text()
    oracle = preregistration.split("## Mandatory criteria\n", 1)[1].split("## Replanning rule", 1)[0]
    oracle = oracle.replace("A may", "An answer without the contract may")
    oracle = oracle.replace("B must", "An answer with the contract must")
    for case, order in manifest["judge_order"].items():
        packet = guidance + "\n## Frozen preregistration\n" + oracle
        if manifest["kind"] == "equal-information-planning-only":
            followup = Path(__file__).with_name("round2-plan.md").read_text()
            followup = followup.split("1. `equal-retry`", 1)[1].split("Each case gets", 1)[0]
            packet += "\n## Equal-information follow-up requirements\n1. `equal-retry`" + followup
        packet += f"\n## Current case\n{case}\n"
        for anonymous, actual in zip(("A", "B"), order):
            packet += f"\n## CONTEXT {anonymous}\n" + (root / f"{case}-{actual}.md").read_text()
            packet += f"\n## ANSWER {anonymous}\n" + (root / f"{case}-{actual}.json").read_text()
        with (root / f"judge-{case}.md").open("x") as stream:
            stream.write(packet)
        print(f"judge-{case}.md")


if __name__ == "__main__":
    main()
