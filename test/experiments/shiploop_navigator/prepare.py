#!/usr/bin/env python3
"""Prepare isolated, explicitly synthetic prompt and Improve experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as nav  # noqa: E402

SPEC = """# Range normalization contract

`normalize_ranges(ranges)` takes a list of two-element lists or tuples. Both
endpoints must be integers; booleans are invalid. Start must not exceed end.
Invalid endpoints, pair shape, or reversed ranges raise ValueError.
Return sorted, disjoint two-element lists. Merge overlap AND touching endpoints.
A contained range must never shorten the containing range. Empty input returns
an empty list. Neither the caller's outer list nor its nested pairs may change.

Keep this a small standard-library function. No dependencies, network, installs,
or publication. Improve the implementation, test cases, and PLAN.md together.
"""

BOUNDARY_EXAMPLES = """
These are closed intervals on a continuous number line, with integer endpoints.
Touching means a shared endpoint, not merely consecutive integer values.
For example, [[1, 2], [2, 4]] becomes [[1, 4]], while [[1, 2], [3, 4]] stays
[[1, 2], [3, 4]] because the gap between 2 and 3 must remain.
"""

CODE = """def normalize_ranges(ranges):
    ranges.sort()
    merged = []
    for start, end in ranges:
        if start > end:
            continue
        if merged and start < merged[-1][1]:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
"""

TESTS = """import unittest
from ranges import normalize_ranges

class RangeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(normalize_ranges([]), [])

    def test_overlap(self):
        self.assertEqual(normalize_ranges([[1, 3], [2, 4]]), [[1, 4]])

if __name__ == '__main__':
    unittest.main()
"""

PLAN = """# Current implementation plan

Sort the incoming list in place. Merge only strict overlap; set the current
endpoint to the next endpoint. Silently skip reversed pairs. Check empty input
and ordinary overlap; leave other boundary cases for a later task.
"""


def current_packet(run: Path) -> str:
    """Export the real CLI packet, including its relocated executable path."""
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / "skills/shiploop/scripts/shiploop"),
         "next", "--run-dir", str(run)],
        cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout


def state_at(repo: Path, goal: str, stage: str, *, second_work: bool = False):
    state = nav.new_state(str(repo), goal)
    for _ in range(70):
        if state["stage"] == stage and (not second_work or state["work_index"] == 1):
            return state
        result = {"outcome": "done", "summary": "Synthetic setup transition, not performed project work."}
        if state["stage"] == "plan":
            result["work_items"] = [
                {"id": "W1", "title": "Initial supplier"},
                {"id": "W2", "title": "Current implementation"},
                {"id": "W3", "title": "Downstream consumer"},
            ]
        state = nav.apply(state, state["action"]["id"], result)
    raise AssertionError("setup route did not reach its target")


def write_case(out: Path, identifier: str, goal: str, stage: str, **options):
    base = out / identifier
    repo, run = base / "project", base / "run"
    repo.mkdir(parents=True)
    state = state_at(repo, goal, stage, second_work=options.get("second_work", False))
    if options.get("blocked"):
        state = nav.apply(state, state["action"]["id"], {
            "outcome": "blocked", "summary": "Required staging credentials are unavailable; the condition is unresolved."
        })
    run.mkdir()
    nav.save(run, state)
    packet = base / "packet.md"
    packet.write_text(current_packet(run))
    return {"id": identifier, "packet": str(packet), "stage": state["stage"],
            "action": state["action"]["id"], "characters": len(packet.read_text())}


def create_fixture(fixture: Path, specification: str) -> str:
    fixture.mkdir()
    for name, content in {"SPEC.md": specification, "PLAN.md": PLAN, "ranges.py": CODE, "test_ranges.py": TESTS}.items():
        (fixture / name).write_text(content)
    def git(*args):
        return subprocess.run(["git", *args], cwd=fixture, check=True, text=True, capture_output=True)
    git("init", "-b", "main")
    git("config", "user.name", "Navigator experiment fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("add", ".")
    git("commit", "-m", "Seed isolated range fixture", "-m", "The existing tests exercise empty input and ordinary overlap. Use the specification as the source of expected behavior; green checks alone do not establish complete coverage.")
    return git("rev-parse", "HEAD").stdout.strip()


def prepare(out: Path, *, explicit_boundary: bool = False):
    cases = [
        write_case(out, "plan", "Improve only the implementation plan. Do not edit code or publish. Scenario fact: a material dependency omission was repaired, then exactly one complete trivial-only review passed. Current plan checks pass; a second clean review has not occurred.", "plan-improve"),
        write_case(out, "product", "Improve the code, tests and plan for the scoped feature, with local edits allowed and no publication. Scenario fact: two earlier clean reviews covered the old candidate; a material code change was then made and its tests have not been rerun.", "product-improve"),
        write_case(out, "verify", "Complete local verification for a changed parser. Scenario fact: the previous check report is green but predates the latest parser edit. Running local tests and linters is authorized. Do not publish.", "verify"),
        write_case(out, "release", "Deliver the local fixture only. Do not merge, push, install or deploy anything. Release is not part of this task. All local checks were completed in this scenario; report release as not applicable without requesting permission to publish.", "release"),
        write_case(out, "queue", "Carry forward the local implementation work. Scenario fact: W1 is completed, W2 is current, W3 is pending. We learned W3 needs a new prerequisite W4. Add W4 before W3 in future work; preserve W1 and W2. No publication.", "carry-forward", second_work=True),
        write_case(out, "blocked", "Required staging acceptance tests must run before this task can complete; do not waive them or substitute local checks. Scenario fact: staging credentials remain unavailable. Do not declare completion or resume until that condition changes.", "system-test", blocked=True),
    ]
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    fixture = out / "improve-fixture"
    specification = SPEC + (BOUNDARY_EXAMPLES if explicit_boundary else "")
    baseline = create_fixture(fixture, specification)
    control = out / "control-fixture"
    control_baseline = create_fixture(control, specification)
    control_task = out / "control-task.md"
    control_task.write_text(f"Execute one engineering pass in {control}. Improve ranges.py, test_ranges.py and PLAN.md to satisfy SPEC.md, preserving SPEC.md. Read local history; review and plan once, implement, run meaningful checks and fix/check failures as needed, then stop. No Improve campaign or independent reviewer. Local edits and commits are authorized; no network, dependencies, installation or remote publication. Record actual checks and limitations in EXPERIMENT.md.\n")
    run = out / "improve-run"
    run.mkdir()
    goal = f"Improve only ranges.py, test_ranges.py and PLAN.md in {fixture} to satisfy SPEC.md. Read SPEC.md as the required behavior. Local fixture edits and commits are authorized; no network, dependencies, installation or remote publication. Preserve SPEC.md. Complete only the current Improve action and stop after its one successful callback; do not execute the next stage. Candidate baseline is {baseline}."
    state = state_at(fixture, goal, "product-improve")
    nav.save(run, state)
    packet = out / "improve-packet.md"
    packet.write_text(current_packet(run))
    manifest = {"fixture": str(fixture), "run": str(run), "packet": str(packet),
                "baseline": baseline, "action": state["action"]["id"], "cases": cases,
                "control_fixture": str(control), "control_baseline": control_baseline,
                "control_task": str(control_task), "explicit_boundary": explicit_boundary}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--explicit-boundary", action="store_true")
    args = parser.parse_args()
    if args.output:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
    else:
        output = Path(tempfile.mkdtemp(prefix="shiploop-navigator-experiments-")).resolve()
    print(json.dumps(prepare(output, explicit_boundary=args.explicit_boundary), indent=2))
