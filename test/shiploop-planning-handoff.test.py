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

import shiploop_context_index as context_index  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_planning_revision as planning_revision  # noqa: E402
import shiploop_store as store  # noqa: E402

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


def full_walk(run: Path, repo: Path, delegation: str):
    """Yield (stage, workitem, packet, state) for every active packet of a two-item run, saving each step."""
    state = nav.new_state(str(repo), "Build a two-player battleship game.", delegation=delegation)
    nav.save(run, state)
    while state["status"] == "active":
        stage = nav.current_stage(state)
        action = nav.current_action(state)["id"]
        yield stage, nav._current_work_item(state), nav.render(None, run, state), state
        result = {"outcome": "done", "summary": f"Synthetic {stage} result.",
                  "evidence_refs": [str(run / "notes" / f"{stage}.md")]}
        if stage == "plan":
            result["work_items"] = [{"id": "W1", "title": "Rules engine"}, {"id": "W2", "title": "Board UI"}]
            result["assumptions"] = []
        state = nav.apply(state, action, result)
        if state.get("active_improve"):
            state = nav.finish_improve(state, action, {"summary": "Synthetic receipt."})
        nav.save(run, state)


class ContextIndexTests(unittest.TestCase):
    def test_every_stage_has_a_read_map_of_earlier_results(self) -> None:
        stages = nav.guidance3.STAGES
        self.assertEqual(set(context_index.STAGE_READS), set(stages))
        inner = nav.guidance3.INNER
        for stage, reads in context_index.STAGE_READS.items():
            for name in reads:
                with self.subTest(stage=stage, read=name):
                    if name.startswith("item:"):
                        self.assertIn(stage, inner, "only work-item stages read item results")
                        self.assertLess(inner.index(name[5:]), inner.index(stage))
                    else:
                        self.assertNotIn(name, inner)
                        self.assertLess(stages.index(name), stages.index(stage))

    def test_every_active_packet_points_at_the_index_and_resolves_its_reads(self) -> None:
        for delegation in ("inline", "ask-agent"):
            with tempfile.TemporaryDirectory(prefix="shiploop-index-") as temp:
                repo, run = Path(temp) / "repo", Path(temp) / "run"
                repo.mkdir()
                run.mkdir()
                visited = set()
                for stage, workitem, packet, state in full_walk(run, repo, delegation):
                    visited.add(stage)
                    with self.subTest(delegation=delegation, stage=stage, workitem=workitem):
                        self.assertIn("Run context index", packet)
                        self.assertIn(str(run / context_index.INDEX_FILE), packet)
                        self.assertNotIn("not accepted yet", packet)
                        for line in context_index.read_first(state, run, stage, workitem):
                            self.assertIn(line, packet)
                        index = (run / context_index.INDEX_FILE).read_text()
                        for action in planning_revision.current_actions(state).values():
                            self.assertIn(str(run / "results" / (action + ".md")), index)
                self.assertEqual(visited, set(nav.guidance3.STAGES))

    def test_the_index_is_derived_and_regenerates_identically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-index-") as temp:
            repo, run = Path(temp) / "repo", Path(temp) / "run"
            repo.mkdir()
            run.mkdir()
            for stage, _, _, state in full_walk(run, repo, "inline"):
                if stage == "implement":
                    break
            saved = (run / context_index.INDEX_FILE).read_text()
            reloaded = store.read_record(run / "state.md")
            self.assertEqual(reloaded["revision"], state["revision"])
            self.assertEqual(context_index.render(reloaded, run, nav.current_stage(reloaded)), saved)
            self.assertIn("do not edit. state.md is the authority", saved)


class PauseGateTests(unittest.TestCase):
    def test_housekeeping_pauses_are_refused_and_user_pauses_kept(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-pause-") as temp:
            state = nav.new_state(str(Path(temp)), "Synthetic request.")
            for reason in ("context-boundary: clear, then run Recovery and Resume",
                           "Need a fresh conversation for the next item", "run /clear first",
                           "context window nearly full; compaction pending"):
                with self.subTest(reason=reason), self.assertRaisesRegex(nav.NavigatorError, "housekeeping"):
                    nav.control(state, "pause", reason)
            for reason in ("user: asked to stop for today", "blocker: org credentials expired",
                           "Synthetic stop", "The requirements are unclear to the user"):
                with self.subTest(reason=reason):
                    self.assertEqual(nav.control(state, "pause", reason)["status"], "paused")


if __name__ == "__main__":
    unittest.main()
