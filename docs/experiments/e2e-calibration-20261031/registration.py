#!/usr/bin/env python3
"""Stage 3's registration (docs/shiploop-e2e-closed-loop-plan-2026-10-30.md): one ShipLoop build against itself,
a promotion/5 `calibration` epoch on Codex gpt-6.1-terra at high, the subject of the stage 5 cycle, on that cycle's two
cases (csv-report and seat-reservations), so its figure measures the noise of the comparison it would replace.

    python3 docs/experiments/e2e-calibration-20261031/registration.py --plugin PLUGIN_DIR > registration-template.json

Both arms bind the same plugin build, so every sealed attempt of a case is a sample of that build. The first design ran
battleship, user-listing and ticket-assignment at xhigh; each declares a fixed port, which run.py leases machine-wide and
launch_all does not serialise, so its own parallel attempts would have refused each other. Reviews are not part of a
calibration.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS))
import run as runner  # noqa: E402

# Attempts per arm. Eight samples of a case (four in each arm) give 560 three-against-three splits for spread.py.
CASES = {"csv-report": 4, "seat-reservations": 4}
DRIVER = {"host": "codex", "model": "gpt-6.1-terra", "effort": "high"}
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
