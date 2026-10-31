#!/usr/bin/env python3
"""Stage 3's registration (docs/shiploop-e2e-closed-loop-plan-2026-10-30.md): one ShipLoop build against itself,
a promotion/5 `calibration` epoch on Codex gpt-6.1-terra at xhigh, the subject every Terra round since 2026-10-29 used.

    python3 docs/experiments/e2e-calibration-20261031/registration.py --plugin PLUGIN_DIR > registration-template.json

Both arms bind the same plugin build, so every sealed attempt of a case is a sample of that build. Battleship's attempts
come first in the list because launch_all dispatches in this order and battleship has never run on Terra: its time is
unknown and likely the longest, so starting it first keeps the parallel slots busy. Reviews are not part of a calibration.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS))
import run as runner  # noqa: E402

# Attempts per arm. Eight samples of each brownfield case give 560 three-against-three splits for spread.py; battleship's
# four samples measure its time on Terra and give a first, coarse spread.
CASES = {"battleship": 2, "user-listing": 4, "ticket-assignment": 4}
DRIVER = {"host": "codex", "model": "gpt-6.1-terra", "effort": "xhigh"}
ARMS = ("control", "candidate")


def template(build: str) -> dict:
    attempts = [{"id": f"{arm}-{case}-{n}", "arm": arm, "case": case}
                for case, per_arm in CASES.items() for n in range(1, per_arm + 1) for arm in ARMS]
    return {"contract": "promotion/5", "purpose": "calibration",
            "cases": {case: {"role": "regression", "attempts": per_arm} for case, per_arm in CASES.items()},
            "arms": {arm: {"shiploop_build": build, "driver": dict(DRIVER)} for arm in ARMS},
            "attempts": attempts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plugin", type=Path, required=True, help="the built plugins/skill-craft folder both arms run")
    args = parser.parse_args(argv)
    if not (args.plugin / "skills" / "shiploop" / "SKILL.md").is_file():
        parser.error(f"{args.plugin} is not a skill-craft plugin build with the ShipLoop skill")
    build = runner.tree_digest(args.plugin)
    if not build:
        parser.error(f"{args.plugin}: the plugin tree cannot be digested")
    print(json.dumps(template(build), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
