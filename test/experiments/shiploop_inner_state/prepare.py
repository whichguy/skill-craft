#!/usr/bin/env python3
"""Opt-in two-item fixture; setup declarations are explicitly synthetic."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "skills/shiploop/scripts/shiploop"
FIXTURE = ROOT / "test/experiments/shiploop_entry_recovery/evidence/fixture"
PRELUDE = "intake discovery research research-improve spec spec-improve test-strategy plan plan-improve".split()
INNER = "step-plan step-plan-improve implement test-refine test-author document verify product-improve integrate carry-forward".split()


def command(argv: list[str], cwd: Path) -> str:
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                          check=True, timeout=30).stdout


def prepare(out: Path) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = out / "fixture"
    fixture.mkdir()
    for name in ("SPEC.md", "lines.py", "test_lines.py"):
        shutil.copyfile(FIXTURE / name, fixture / name)
    (fixture / "PLAN.md").write_text(
        "# Fixture scope\nReview the existing implementation against immutable SPEC.md.\n"
        "Retain adequate tests and avoid artificial edits. Earlier graph transitions are synthetic.\n")
    command(["git", "init", "-b", "main"], fixture)
    command(["git", "add", "SPEC.md", "PLAN.md", "lines.py", "test_lines.py"], fixture)
    command(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "-m", "Reuse correct clean_lines candidate for isolated ownership trial"], fixture)
    run = out / "run"
    goal = (
        f"Review clean_lines against immutable SPEC.md in {fixture}. Work only on the "
        "current action, reconcile durable evidence and use its printed callback once "
        "complete, then stop before the returned action. Local fixture source/tests/PLAN "
        "and run notes may be edited if evidence warrants. Do not manufacture edits. "
        "No commits, push, source-checkout edits, new dependencies, installation, network "
        "or deployment. Earlier transitions are synthetic setup, not delivered work. "
        "An independent reviewer is available through the trial owner; request a review "
        "when needed and retain its actual scope/findings."
    )
    packet = command([sys.executable, "-B", str(CLI), "init", f"--repo={fixture}",
                      f"--run-dir={run}", f"--prompt={goal}"], out)
    state = json.loads((run / "state.md").read_text().split("```shiploop-state\n", 1)[1].split("```", 1)[0])
    assert state["navigator_protocol_version"] == 2, "trial requires Navigator protocol2"
    setup = PRELUDE + INNER + INNER[:INNER.index("product-improve")]
    for stage in setup:
        assert packet.startswith(f"ShipLoop navigator | {stage} |"), packet[:100]
        result = {"outcome": "done", "summary": "Synthetic fixture setup; no stage work claimed."}
        if stage == "plan":
            result["work_items"] = [
                {"id": "W1", "title": "Synthetic preceding work item"},
                {"id": "W2", "title": "Review existing clean_lines candidate", "context": "Read SPEC.md and PLAN.md."},
            ]
        path = Path(packet.split("Write the structured result to: ", 1)[1].splitlines()[0])
        path.write_text("```shiploop-state\n" + json.dumps(result) + "\n```\n")
        argv = shlex.split(packet.split("Call this when done:\n", 1)[1].splitlines()[0])
        packet = command([sys.executable, "-B", *argv[1:]], out)
    assert packet.startswith("ShipLoop navigator | product-improve |")
    state = json.loads((run / "state.md").read_text().split("```shiploop-state\n", 1)[1].split("```", 1)[0])
    assert state["stage"] == "inner-loop" and state["action"] is None
    assert state["inner_loops"]["W1"] == {"stage": "done", "action": None}
    assert state["inner_loops"]["W2"]["stage"] == "product-improve"
    (out / "initial-packet.md").write_text(packet)
    (out / "initial-state.md").write_text((run / "state.md").read_text())
    recovery = packet.split("Recovery command:\n", 1)[1].splitlines()[0]
    handoff = out / "handoff.md"
    handoff.write_text(
        f"# Durable locator\n\nRepository: {fixture}\nCLI: {CLI}\nRun directory: {run}\n"
        f"Authoritative state: {run / 'state.md'}\n\n```sh\n{recovery}\n```\n\n"
        "Recover the current action from this existing run. Perform only that action, "
        "then submit its callback and stop. Do not initialize another run.\n")
    manifest = {"fixture": str(fixture), "run": str(run), "handoff": str(handoff),
                "synthetic_setup_transitions": len(setup),
                "source_base": command(["git", "rev-parse", "HEAD"], ROOT).strip(),
                "source_has_uncommitted_candidate": bool(command(["git", "status", "--porcelain"], ROOT).strip())}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))
