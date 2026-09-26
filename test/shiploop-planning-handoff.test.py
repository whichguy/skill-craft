#!/usr/bin/env python3
"""ShipLoop planning handoff: each planning packet names the accepted results it builds on.

The prelude writes the planning basis (intake through plan).  The stages that
turn it into work -- step-plan, test-spec, system-test-author and release-plan
-- must be handed those accepted results by the script, not left to find them
in state.md.  This walks one synthetic run on both delegation routes and checks
which accepted result files each packet names.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))

import shiploop_navigator as nav  # noqa: E402

# Consumer stage -> the root planning results its packet must name.
REQUIRED_SOURCES = {
    "plan": {"intake", "discovery", "research", "spec", "test-strategy"},
    "step-plan": {"spec", "test-strategy", "plan"},
    "test-spec": {"spec", "test-strategy", "plan", "step-plan"},
    "implement": {"step-plan"},
    "system-test-author": {"spec", "test-strategy", "plan"},
    "release-plan": {"spec", "test-strategy", "plan"},
}


def walk(delegation: str) -> dict[str, set[str]]:
    """Run one work item to done; return, per stage, the accepted stages its packet names."""

    with tempfile.TemporaryDirectory(prefix="shiploop-handoff-") as temp:
        repo = Path(temp) / "repo"
        run = Path(temp) / "run"
        repo.mkdir()
        run.mkdir()
        state = nav.new_state(str(repo), "Build a two-player battleship game.", delegation=delegation)
        accepted: dict[str, str] = {}
        seen: dict[str, set[str]] = {}
        while state["status"] == "active":
            stage = nav.current_stage(state)
            action = nav.current_action(state)["id"]
            packet = nav.render(None, run, state)
            seen[stage] = {name for name, done in accepted.items()
                           if str(run / "results" / (done + ".md")) in packet}
            result = {"outcome": "done", "summary": f"Synthetic {stage} result.",
                      "evidence_refs": [str(run / "notes" / f"{stage}.md")]}
            if stage == "plan":
                result["work_items"] = [{"id": "W1", "title": "Rules engine"}]
                result["assumptions"] = []
            state = nav.apply(state, action, result)
            if state.get("active_improve"):
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt."})
            accepted[stage] = action
        return seen


class PlanningHandoffTests(unittest.TestCase):
    def test_each_planning_consumer_names_the_accepted_results_it_builds_on(self) -> None:
        for delegation in ("inline", "ask-agent"):
            seen = walk(delegation)
            for stage, required in REQUIRED_SOURCES.items():
                with self.subTest(delegation=delegation, stage=stage):
                    self.assertIn(stage, seen, "the walk never reached this stage")
                    self.assertLessEqual(required, seen[stage],
                                         f"missing: {sorted(required - seen[stage])}")

    def test_every_planning_stage_registers_its_files_for_the_next_stage(self) -> None:
        planning = set(nav.guidance3.PRELUDE) | set(nav.guidance3.PLANNING_REVIEW_STAGES)
        for delegation in ("inline", "ask-agent"):
            for stage in sorted(planning):
                with self.subTest(delegation=delegation, stage=stage):
                    self.assertIn("Register every produced planning file",
                                  nav.guidance3.prompt(stage, delegation=delegation))

    def test_the_step_planning_set_is_the_planning_reviews_after_the_prelude(self) -> None:
        self.assertEqual(nav.STEP_PLANNING_STAGES,
                         {"step-plan", "test-spec", "system-test-author", "release-plan"})


if __name__ == "__main__":
    unittest.main()
