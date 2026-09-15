#!/usr/bin/env python3
"""Prepare a fresh opt-in recovery fixture using real CLI navigation only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

from oracle import grade

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "skills/shiploop/scripts/shiploop"
PREFIX = ("intake", "discovery", "research", "research-improve", "spec",
          "spec-improve", "test-strategy", "plan", "plan-improve", "step-plan",
          "step-plan-improve")
SPEC = """# Required behavior

Implement clean_lines(text) in lines.py. Accept str only; otherwise raise
TypeError. Split using Python splitlines(), strip each resulting line, discard
empty strings, and preserve order and duplicates. Empty or whitespace-only text
returns []. For example ' a \\n \\n b\\n a ' returns ['a', 'b', 'a'].
Keep the function small and stdlib-only. This specification is immutable.
"""
SEED = "def clean_lines(text):\n    return text.splitlines()\n"
REFERENCE = """def clean_lines(text):
    if not isinstance(text, str):
        raise TypeError('text must be str')
    return [line for raw in text.splitlines() if (line := raw.strip())]
"""


def command(argv: list[str], cwd: Path) -> str:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                          check=True, timeout=30).stdout


def prepare(out: Path) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = out / "fixture"
    fixture.mkdir()
    (fixture / "SPEC.md").write_text(SPEC)
    (fixture / "lines.py").write_text(SEED)
    (fixture / "PLAN.md").write_text("# Plan\nImplement SPEC.md. Refine and author tests from its behavior.\n")
    command(["git", "init", "-b", "main"], fixture)
    command(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "add", "SPEC.md", "lines.py", "PLAN.md"], fixture)
    command(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "-m", "Seed isolated clean_lines recovery fixture"], fixture)
    calibration = out / "calibration"
    calibration.mkdir()
    reference = calibration / "reference.py"
    reference.write_text(REFERENCE)
    scores = {"seed": grade(fixture / "lines.py"), "reference": grade(reference)}
    assert scores["seed"]["passed"] < scores["seed"]["total"]
    assert scores["reference"]["passed"] == scores["reference"]["total"]
    (calibration / "scores.json").write_text(json.dumps(scores, indent=2) + "\n")
    run = out / "run"
    goal = (f"Deliver clean_lines per immutable SPEC.md in {fixture}. Execute only the "
            "current action and stop after its one successful callback; do not perform "
            "the returned next action. Read actual code and relevant durable notes, "
            "reconcile prior effects, and preserve evidence in the run notes. Local "
            "fixture source, tests and PLAN.md edits are authorized. No source-checkout "
            "edits, network, dependencies, installation, commits, push or deployment. "
            "Earlier prelude transitions are explicitly synthetic test setup.")
    packet = command([sys.executable, "-B", str(CLI), "init", f"--repo={fixture}",
                      f"--run-dir={run}", f"--prompt={goal}"], out)
    for stage in PREFIX:
        assert packet.startswith(f"ShipLoop navigator | {stage} |")
        result_path = Path(packet.split("Write the structured result to: ", 1)[1].splitlines()[0])
        result_path.write_text('```shiploop-state\n' + json.dumps({
            "outcome": "done", "summary": "Synthetic setup only; no project work claimed."}) + '\n```\n')
        argv = shlex.split(packet.split("Call this when done:\n", 1)[1].splitlines()[0])
        packet = command([sys.executable, "-B", *argv[1:]], out)
    assert packet.startswith("ShipLoop navigator | implement |")
    (out / "initial-packet.md").write_text(packet)
    (out / "initial-state.md").write_text((run / "state.md").read_text())
    recovery = packet.split("Recovery command:\n", 1)[1].splitlines()[0]
    handoff = out / "handoff.md"
    handoff.write_text(f"# Durable ShipLoop locator\n\nRepository: {fixture}\nCLI: {CLI}\n"
                       f"Run directory: {run}\nAuthoritative state: {run / 'state.md'}\n\n"
                       f"Recover the current task from the saved run:\n\n```sh\n{recovery}\n```\n\n"
                       "This locator records no graph position. Execute only the recovered current "
                       "action, reconcile actual effects, submit its current callback, then stop.\n")
    manifest = {"fixture": str(fixture), "run": str(run), "handoff": str(handoff),
                "source_base": command(["git", "rev-parse", "HEAD"], ROOT).strip(),
                "source_has_uncommitted_candidate": bool(command(["git", "status", "--porcelain"], ROOT).strip())}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))
