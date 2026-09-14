#!/usr/bin/env python3
"""Public-CLI coverage for a user-question pause and safe continuation.

The question text is not a state transition by itself.  This fixture proves a
reply is recorded in the current action result, and only its accepted callback
may advance the durable research cursor.
"""

from __future__ import annotations

import copy
import runpy
from pathlib import Path
import shlex
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLANNING_TEST_MODULE = runpy.run_path(str(ROOT / "test" / "shiploop-planning.test.py"))
store = PLANNING_TEST_MODULE["store"]


class QuestionResumeTests(unittest.TestCase):
    """Exercise the public paused-question recovery contract without cursor edits."""

    def setUp(self) -> None:
        fixture_type = PLANNING_TEST_MODULE["PlanningLoopTests"]
        self.fixture = fixture_type()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.bootstrap_to_research()

    def _callback(self, packet: str) -> tuple[list[str], Path]:
        line = next(
            row for row in packet.splitlines()
            if row.startswith("Call this when done: ")
        )
        command = shlex.split(line.removeprefix("Call this when done: "))
        action = self.fixture.state()["action"]["id"]
        self.assertEqual(command[command.index("--action") + 1], action)
        result = Path(command[command.index("--result") + 1])
        self.assertEqual(
            result.resolve(),
            (self.fixture.run_dir / "inbox" / f"{action}.md").resolve(),
        )
        return command, result

    def _answered_research_result(self) -> dict:
        answer = "The owner authorizes the fixture's repository-local deterministic probe only."
        state = copy.deepcopy(
            self.fixture.research_state(
                "user-direction",
                answer=answer,
            )
        )
        state["sources"].append(
            {
                "id": "SRC-OWNER-001",
                "reference": "User direction captured in the current research action",
                "authority": "local",
                "version_or_observed_at": "current ShipLoop action",
                "supports": answer,
                "limitations": "This direction authorizes only the scoped local probe; it proves no remote access.",
            }
        )
        state["questions"][0]["sources"] = ["SRC-OWNER-001"]
        return {
            "summary": "The user direction is recorded as scoped local evidence; remaining research work stays in this action.",
            "body": self.fixture.research_body("user-direction"),
            "research_state": state,
        }

    def test_paused_question_requires_resume_then_a_valid_current_action_callback(self) -> None:
        initial = self.fixture.cli("next").stdout
        self.assertIn("Question handoff:", initial)
        callback, result_path = self._callback(initial)
        action = self.fixture.state()["action"]["id"]

        self.fixture.cli("pause", "--reason", "Need owner direction for the scoped local probe")
        paused = self.fixture.cli("next").stdout
        self.assertIn("Paused, unfinished:", paused)
        self.assertIn("Question handoff:", paused)
        self.assertIn("No completion callback is valid while paused.", paused)
        self.assertNotIn("Call this when done:", paused)
        self.assertEqual(self.fixture.state()["action"]["id"], action)

        candidate = self._answered_research_result()
        store.write_record(result_path, candidate, title="Answered paused research result")
        rejected = self.fixture.cli(
            "done", "--action", action, "--result", str(result_path), code=2
        )
        self.assertIn("run paused; resolve the blocker and resume", rejected.stderr)
        self.fixture.assert_cursor("validate-spec", "research")
        self.assertEqual(self.fixture.state()["action"]["id"], action)

        self.fixture.cli("resume")
        resumed = self.fixture.cli("next").stdout
        self.assertIn("Question handoff:", resumed)
        resumed_callback, resumed_result = self._callback(resumed)
        self.assertEqual(resumed_callback, callback)
        self.assertEqual(resumed_result, result_path)

        malformed = copy.deepcopy(candidate)
        malformed["research_state"]["system_context"]["scope"] = ["local-only"]
        store.write_record(result_path, malformed, title="Malformed answered research result")
        rejected = subprocess.run(
            resumed_callback,
            cwd=self.fixture.repo,
            capture_output=True,
            text=True,
            env=self.fixture.env,
        )
        self.assertEqual(rejected.returncode, 2, rejected.stdout + rejected.stderr)
        self.assertIn("system_context.scope", rejected.stderr)
        self.fixture.assert_cursor("validate-spec", "research")
        self.assertEqual(self.fixture.state()["action"]["id"], action)

        store.write_record(result_path, candidate, title="Accepted answered research result")
        accepted = subprocess.run(
            resumed_callback,
            cwd=self.fixture.repo,
            capture_output=True,
            text=True,
            env=self.fixture.env,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.fixture.assert_cursor("validate-spec", "research-review")
        evidence = (self.fixture.run_dir / "research-evidence.md").read_text()
        self.assertIn(candidate["research_state"]["questions"][0]["answer"], evidence)
        self.assertIn("SRC-OWNER-001", evidence)


if __name__ == "__main__":
    unittest.main()
