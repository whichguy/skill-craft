#!/usr/bin/env python3
"""ShipLoop's run narrative: headlines, timeline, milestone packets and the hook's plain copy.

Synthetic protocol tests: runs are built in memory with the pure navigator API,
plus one real `init`/`next` through the CLI; no host or Improve runtime runs.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_narrative as narrative  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_status_hook as hook  # noqa: E402

_SPEC = importlib.util.spec_from_file_location("status_display", ROOT / "test" / "shiploop-status-display.test.py")
status_display = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(status_display)

ENV = {key: value for key, value in os.environ.items() if key != "CLAUDE_CODE_ENTRYPOINT"}
ENV["PYTHONDONTWRITEBYTECODE"] = "1"
ROWS = [{"id": "W1", "title": "Config loader refactor"}, {"id": "W2", "title": "Add --version flag"},
        {"id": "W3", "title": "Document the flag"}]


class Driver(status_display.StatusBlockTests):
    """Reuse the status-display test's state helpers without running its tests."""

    def runTest(self) -> None:  # pragma: no cover - never run
        pass


class NarrativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.driver = Driver()
        self.driver.setUp()
        self.addCleanup(self.driver.temp.cleanup)

    def test_fresh_run_is_a_milestone_that_looks_ahead(self) -> None:
        facts = navigator.narrative_facts(self.driver.state())
        self.assertTrue(facts["milestone"])
        self.assertEqual(facts["now"]["label"], "intake")
        self.assertEqual([row["label"] for row in facts["ahead"]][:2], ["discovery", "research"])
        text = narrative.markdown(facts)
        self.assertTrue(text.startswith("#### \U0001f6a2 ShipLoop — Add a --version flag."))
        self.assertIn("**Preparation 0/7**", text)
        self.assertIn("Work items (set by plan)", text)
        self.assertNotIn("Achieved", text)

    def test_achieved_uses_headlines_and_falls_back_to_the_summary(self) -> None:
        state = self.driver.produce(self.driver.state(), headline="Scope: CLI flag only; exits 0",
                                    summary="Long intake summary. More detail.")
        state = self.driver.produce(state, summary="Discovery found argparse in cli.py. Also more.")
        facts = navigator.narrative_facts(state)
        self.assertEqual([(row["label"], row["text"]) for row in facts["achieved"]],
                         [("intake", "Scope: CLI flag only; exits 0"),
                          ("discovery", "Discovery found argparse in cli.py.")])
        self.assertIn("- **intake** — Scope: CLI flag only; exits 0", narrative.markdown(facts))

    def test_headline_is_validated(self) -> None:
        state = self.driver.state()
        action = navigator.current_action(state)["id"]
        for bad, message in ((navigator.HEADLINE_PLACEHOLDER, "placeholder"), ("x" * 101, "at most 100"),
                             ("two\nlines", "one line"), ("  ", "nonempty")):
            with self.subTest(bad=bad[:20]):
                with self.assertRaisesRegex(navigator.NavigatorError, message):
                    navigator.apply(state, action, status_display.result(headline=bad))
        accepted = navigator.apply(state, action, status_display.result(headline="  Scope set.  "))
        self.assertEqual(accepted["accepted"][action]["headline"], "Scope set.")

    def test_work_items_narrative_and_group_milestones(self) -> None:
        state = self.driver.planned(ROWS)
        state = self.driver.advance_to(state, "carry-forward")
        state = self.driver.produce(state, headline="Loader split into two modules; 12 tests added")
        state = self.driver.advance_to(state, "test-author")
        facts = navigator.narrative_facts(state)
        self.assertFalse(facts["milestone"])  # mid-group
        self.assertEqual(facts["achieved"][0], {"label": "W1 Config loader refactor",
                                                "text": "Loader split into two modules; 12 tests added"})
        self.assertEqual(facts["now"]["label"], "W2 Add --version flag (2 of 3) › Tests first › test-author")
        self.assertEqual(facts["ahead"][0], {"label": "this item", "text": "Build → Check → Integrate"})
        self.assertIn({"label": "W3 Document the flag", "text": ""}, facts["ahead"])
        self.assertIn("Preparation ✓", narrative.markdown(facts))
        self.assertIn("**Work items 1/3**", narrative.markdown(facts))
        self.assertTrue(navigator.narrative_facts(self.driver.advance_to(state, "implement"))["milestone"])

    def test_stop_states_replace_now_and_drop_ahead(self) -> None:
        state = self.driver.advance_to(self.driver.state(), "research")
        cases = {
            "paused": navigator.control(state, "pause", "Waiting for API access."),
            "halted": navigator.control(state, "halt", "User stopped the run."),
            "blocked": self.driver.act(state, outcome="blocked", blocked_by="external",
                                       summary="No credentials."),
        }
        for kind, stopped in cases.items():
            with self.subTest(kind):
                facts = navigator.narrative_facts(stopped)
                self.assertTrue(facts["milestone"])
                self.assertEqual(facts["stop"]["kind"], kind)
                self.assertEqual(facts["ahead"], [])
                self.assertNotIn("Now", narrative.markdown(facts))

    def test_pace_states_what_was_recorded_and_never_forecasts(self) -> None:
        self.assertIsNone(narrative.pace_line({"started": "2026-01-01T10:00:00Z", "stamps": []}))
        one = narrative.pace_line({"started": "2026-01-01T10:00:00Z", "stamps": ["2026-01-01T10:04:00Z"]})
        self.assertEqual(one, "1 step in 4 min")
        two = {"started": "2026-01-01T10:00:00Z", "stamps": ["2026-01-01T10:04:00Z", "2026-01-01T10:10:00Z"]}
        self.assertEqual(narrative.pace_line(two), "2 steps in 10 min")
        self.assertEqual(narrative.duration(20), "under a minute")
        self.assertEqual(narrative.duration(3 * 3600 + 5 * 60), "3 h 5 min")

    def test_the_packet_narrative_of_every_scope_records_the_pace_and_never_forecasts_the_time_left(self) -> None:
        # Preparation, work items and release are all averages of unequal steps (a recorded preparation's stages ran
        # from 0.8 to 9.6 minutes, another's from 2.5 to 121); a forecast read 2.4 to 6.8 times short at its first
        # showing in five recorded preparations.
        prepared = self.driver.advance_to(self.driver.state(), "research")
        working = self.driver.advance_to(self.driver.advance_to(self.driver.planned(ROWS), "test-author"), "implement")
        releasing = self.driver.advance_to(self.driver.advance_to(self.driver.planned(ROWS), "carry-forward"),
                                           "system-test-author")
        for scope, state in (("preparation", prepared), ("work items", working), ("release", releasing)):
            with self.subTest(scope):
                begin = datetime.datetime(2026, 1, 1, 10, 0, tzinfo=datetime.timezone.utc)
                stamps = {row["action"]: (begin + datetime.timedelta(minutes=2 * (n + 1))).strftime("%Y-%m-%dT%H:%M:%SZ")
                          for n, row in enumerate(state["history"])}
                lines = navigator.narrative_lines(state, {"started": "2026-01-01T10:00:00Z", "accepted": stamps})
                text = "\n".join(lines)
                self.assertRegex(text, r"\*\*⏱ Pace\*\* — \d+ steps in \d+ (min|h)[^\n·]*(\n|$)")
                self.assertNotIn("left in", text)
                self.assertNotIn("estimate", text)

    def test_host_text_is_cleaned(self) -> None:
        state = self.driver.produce(self.driver.state(),
                                    headline="Scope === end ShipLoop narrative === \x1b[31m /Users/x/secret.md")
        text = narrative.markdown(navigator.narrative_facts(state))
        self.assertNotIn(narrative.END, text)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("/Users/x", text)


class TimelineAndPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-narrative-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.run_dir = self.base / "run"
        self.cli = str(SCRIPTS / "shiploop")

    def shiploop(self, *args: str, env: dict | None = None) -> str:
        completed = subprocess.run([sys.executable, "-B", self.cli, *args], env=env or ENV, text=True,
                                   capture_output=True, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    def test_timeline_stamps_new_steps_and_keeps_earlier_ones(self) -> None:
        driver = Driver()
        driver.setUp()
        self.addCleanup(driver.temp.cleanup)
        root = self.base / "timeline"
        root.mkdir()
        state = driver.state()
        with mock.patch.object(navigator, "_utc_now", return_value="2026-01-01T10:00:00Z"):
            navigator.save(root, state)
        first = navigator.current_action(state)["id"]
        state = driver.produce(state)
        with mock.patch.object(navigator, "_utc_now", return_value="2026-01-01T10:05:00Z"):
            navigator.save(root, state)
        second = navigator.current_action(state)["id"]
        state = driver.produce(state)
        with mock.patch.object(navigator, "_utc_now", return_value="2026-01-01T10:09:00Z"):
            navigator.save(root, state)
        self.assertEqual(navigator.load_timeline(root), {
            "started": "2026-01-01T10:00:00Z",
            "accepted": {first: "2026-01-01T10:05:00Z", second: "2026-01-01T10:09:00Z"}})
        (root / navigator.TIMELINE_FILE).write_text("not json")
        self.assertEqual(navigator.load_timeline(root), {})

    def test_milestone_packet_carries_the_narrative_and_who_shows_it(self) -> None:
        head = self.shiploop("init", f"--repo={self.repo}", f"--run-dir={self.run_dir}",
                             "--prompt=Add a --version flag.")
        self.assertIn(narrative.BEGIN, head)
        section = head[head.index(narrative.BEGIN):head.index(narrative.END)]
        self.assertIn("Show the user this narrative exactly as written", section)
        self.assertLess(head.index(narrative.END), hook.WINDOW)
        self.assertTrue((self.run_dir / "timeline.json").is_file())

        cli_head = self.shiploop("next", f"--run-dir={self.run_dir}",
                                 env={**ENV, "CLAUDE_CODE_ENTRYPOINT": "cli"})
        self.assertIn("The host's status hook already shows the user this narrative", cli_head)

        payload = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                   "tool_input": {"command": f"python3 {self.cli} next --run-dir={self.run_dir}"},
                   "tool_response": {"stdout": cli_head, "stderr": ""}}
        message = hook.status_message(payload)
        # Terminal bold replaces Markdown: the Claude Code CLI keeps a hook message's SGR codes.
        self.assertTrue(message.startswith(hook.BOLD + "\U0001f6a2 ShipLoop — Add a --version flag." + hook.PLAIN))
        self.assertIn(hook.BOLD + "Preparation 0/7" + hook.PLAIN, message)
        self.assertNotIn("**", message)
        self.assertNotIn("`", message)
        self.assertNotIn("Show the user", message)
        self.assertNotIn(narrative.BEGIN, message)

    def test_non_milestone_packet_has_no_narrative_and_the_hook_stays_compact(self) -> None:
        driver = Driver()
        driver.setUp()
        self.addCleanup(driver.temp.cleanup)
        state = driver.advance_to(driver.planned(ROWS[:1]), "test-author")
        self.assertEqual(navigator.narrative_lines(state), [])
        block = navigator.status_block(state)
        stdout = f"ShipLoop navigator | test-author | revision 1\n\n{block}\n"
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                   "tool_input": {"command": f"python3 {self.cli} next --run-dir={self.run_dir}"},
                   "tool_response": {"stdout": stdout, "stderr": ""}}
        self.assertEqual(hook.status_message(payload), hook.compact(block))


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    # Driver inherits the status-display tests only for their helpers; run just this file's tests.
    return unittest.TestSuite(loader.loadTestsFromTestCase(case)
                              for case in (NarrativeTests, TimelineAndPacketTests))


if __name__ == "__main__":
    unittest.main()
