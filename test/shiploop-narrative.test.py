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

import state_home

state_home.isolate()


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
        for bad, message in ((navigator.HEADLINE_PLACEHOLDER, "placeholder"),
                             ("two\nlines", "one line"), ("  ", "nonempty")):
            with self.subTest(bad=bad[:20]):
                with self.assertRaisesRegex(navigator.NavigatorError, message):
                    navigator.apply(state, action, status_display.result(headline=bad))
        accepted = navigator.apply(state, action, status_display.result(headline="  Scope set.  "))
        self.assertEqual(accepted["accepted"][action]["headline"], "Scope set.")

    def test_a_long_headline_is_accepted_whole_and_shown_cut(self) -> None:
        """Plan F2: a headline has no character limit (it was refused past 100); it stays one line, the result keeps it
        whole, and the narrative shows it cut to ``HEADLINE_SHOWN``."""
        long = "Scope set: " + "a very long account of what this step established, " * 4
        self.assertGreater(len(long), navigator.HEADLINE_SHOWN)
        state = self.driver.produce(self.driver.state(), headline=long)
        action = next(iter(state["accepted"]))
        self.assertEqual(state["accepted"][action]["headline"], long.strip())
        shown = navigator.narrative_facts(state)["achieved"][0]["text"]
        self.assertLessEqual(len(shown), navigator.HEADLINE_SHOWN)
        self.assertTrue(shown.startswith("Scope set: a very long account"))

    def test_work_items_narrative_and_group_milestones(self) -> None:
        state = self.driver.planned(ROWS)
        state = self.driver.advance_to(state, "carry-forward")
        state = self.driver.produce(state, headline="Loader split into two modules; 12 tests added")
        # The item boundary is `carry-forward`: this state, before any further advance, is a milestone.
        closed_item = state
        self.assertTrue(navigator.narrative_facts(closed_item)["milestone"], "the carry-forward that closed W1")
        state = self.driver.advance_to(state, "test-spec")
        facts = navigator.narrative_facts(state)
        self.assertFalse(facts["milestone"])  # mid-item
        self.assertEqual(facts["achieved"][0], {"label": "W1 Config loader refactor",
                                                "text": "Loader split into two modules; 12 tests added"})
        self.assertEqual(facts["now"]["label"], "W2 Add --version flag (2 of 3) › Plan › test-spec")
        self.assertEqual(facts["ahead"][0], {"label": "this item", "text": "Validate existing → Build → Carry forward"})
        self.assertIn({"label": "W3 Document the flag", "text": ""}, facts["ahead"])
        self.assertIn("Preparation ✓", narrative.markdown(facts))
        self.assertIn("**Work items 1/3**", narrative.markdown(facts))
        # A mid-item stage carries the status line, like every other non-boundary stage (2026-11-03).
        self.assertFalse(navigator.narrative_facts(self.driver.advance_to(state, "validate-existing"))["milestone"])

    def test_only_the_run_boundaries_are_milestones_so_the_narrative_is_asked_for_few_times(self) -> None:
        """The narrative is a full summary a person reads at a boundary; asked 20 times an item run the model showed it
        at 61% (measured 2026-11-03 over 2,111 emissions in 102 runs). The milestones are the start, `prepare`, each
        item's `carry-forward`, and the outer outcomes; every other stage carries the one-line status instead."""
        # The rule's membership, stated once: a boundary shows the narrative, every other stage does not.
        self.assertEqual(sorted(navigator._MILESTONE_STAGES),
                         ["carry-forward", "handoff", "prepare", "product-acceptance", "release"])
        # A stage that is not a boundary carries no narrative: test-spec follows step-plan inside the item's Plan group.
        mid_item = self.driver.advance_to(self.driver.planned(ROWS), "test-spec")
        self.assertFalse(navigator.narrative_facts(mid_item)["milestone"])
        self.assertEqual(navigator.narrative_lines(mid_item), [])
        # Preparation complete is a boundary, so the run does not fall silent for the prelude's median 26%: the
        # boundary counts once `prepare` is the last accepted stage, which is one produce after advance_to stops.
        at_prepare = self.driver.produce(self.driver.advance_to(self.driver.state(), "prepare"))
        self.assertTrue(navigator.narrative_facts(at_prepare)["milestone"])

    def test_an_improve_stage_is_never_a_milestone_and_its_packet_carries_no_progress(self) -> None:
        """The milestone test reads the last accepted step, which an Improve child does not change: the reviewed result
        is accepted only when the child completes.  So every Improve packet repeated the narrative of the producer
        packet before it (8 of 11 Improve packets of a live run, packet review F6, 2026-10-17)."""
        root = self.driver.repo.parent / "improve-run"
        root.mkdir()
        # The producer whose result is reviewed is `spec`. Before 2026-11-03 a prelude stage such as `research` made
        # the preceding packet a milestone; now the prelude's boundary is `prepare`, which is AFTER `spec`, so the
        # property this test pins is unchanged and simpler to state: an Improve packet is never a milestone and carries
        # no progress block, whatever the producer's own packet showed.
        spec = self.driver.advance_to(self.driver.state(), "spec")
        parked = self.driver.act(spec, summary="Spec drafted.")
        self.assertIsNotNone(parked.get("active_improve"))
        self.assertFalse(navigator.narrative_facts(parked)["milestone"])
        self.assertEqual(navigator.narrative_lines(parked), [])
        navigator.save(root, parked)
        packet = navigator.render(None, root, parked)
        self.assertTrue(packet.startswith(f"ShipLoop navigator | {navigator.IMPROVE_STAGE} |"))
        for absent in (narrative.BEGIN, navigator.STATUS_BEGIN, navigator.status_line(parked), "Host-recorded labels"):
            self.assertNotIn(absent, packet)
        self.assertIsNone(hook.packet_progress(packet))
        self.assertIn("Keepalive marker: SHIPLOOP-RUN run=", packet)  # the keepalive hooks still bind from it
        # A stopped run is a milestone even while a child is parked: its packet tells the user why it stopped.
        self.assertTrue(navigator.narrative_facts(navigator.control(parked, "pause", "Asked to stop."))["milestone"])

    def test_stop_states_replace_now_and_drop_ahead(self) -> None:
        state = self.driver.advance_to(self.driver.state(), "research")
        cases = {
            "paused": navigator.control(state, "pause", "Waiting for API access."),
            "halted": navigator.control(state, "halt", "User stopped the run."),
            # A blocked result always awaits a person or a service, so its stop kind is "awaiting".
            "awaiting": self.driver.act(state, outcome="blocked", summary="No credentials.", awaiting={
                "kind": "present", "steps": ["Provide the API credentials."], "report": "Say when they are set.",
                "no_default": "Only the owner can provide credentials."}),
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
        # Each scope is sampled at a milestone boundary (start, `prepare`, `carry-forward`, `product-acceptance`):
        # since 2026-11-03 only those carry the narrative, so a mid-scope stage has no pace text to check.
        # `advance_to` stops BEFORE the stage runs, so the boundary's own acceptance is one more `produce`:
        # a boundary stage is a milestone once it is the last accepted stage.
        preparing = self.driver.produce(self.driver.advance_to(self.driver.state(), "prepare"))
        closing_item = self.driver.produce(self.driver.advance_to(self.driver.planned(ROWS), "carry-forward"))
        releasing = self.driver.produce(self.driver.advance_to(closing_item, "product-acceptance"))
        for scope, state in (("preparation", preparing), ("work items", closing_item), ("release", releasing)):
            with self.subTest(scope):
                begin = datetime.datetime(2026, 1, 1, 10, 0, tzinfo=datetime.timezone.utc)
                stamps = {row["action"]: (begin + datetime.timedelta(minutes=2 * (n + 1))).strftime("%Y-%m-%dT%H:%M:%SZ")
                          for n, row in enumerate(state["history"])}
                lines = navigator.narrative_lines(state, {"started": "2026-01-01T10:00:00Z", "accepted": stamps})
                self.assertTrue(lines, f"the {scope} boundary must show the narrative")
                text = "\n".join(lines)
                self.assertRegex(text, r"\*\*⏱ Pace\*\* — \d+ steps in \d+ (min|h)[^\n·]*(\n|$)")
                self.assertNotIn("left in", text)
                self.assertNotIn("estimate", text)
        # The run's start is a boundary too, but it has accepted nothing yet: the narrative shows, and the pace line
        # is correctly absent rather than a fabricated "0 steps".
        start = self.driver.state()
        start_lines = navigator.narrative_lines(start, {"started": "2026-01-01T10:00:00Z", "accepted": {}})
        self.assertTrue(start_lines, "the start of a run shows the narrative")
        self.assertNotIn("Pace", "\n".join(start_lines))
        self.assertNotIn("left in", "\n".join(start_lines))

    def test_host_text_is_cleaned(self) -> None:
        state = self.driver.produce(self.driver.state(),
                                    headline="Scope === end ShipLoop narrative === \x1b[31m /Users/x/secret.md")
        text = narrative.markdown(navigator.narrative_facts(state))
        self.assertNotIn(narrative.END, text)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("/Users/x", text)


class NarrativeBoundTests(unittest.TestCase):
    """Run-insights E6: the narrative is capped at NARRATIVE_LIMIT (900) where it is produced; the oldest achieved rows
    fold into one line, and the current stage and what is ahead stay."""

    def test_a_long_run_folds_its_oldest_achieved_rows_within_the_limit(self) -> None:
        facts = navigator.narrative_facts(navigator.new_state("/simulation-only/repo", "Bound fixture.", improve_skill=""))
        facts = dict(facts, achieved=[{"label": f"W{n} implement", "text": "a finished step that " + "x" * 60}
                                      for n in range(1, 41)])
        text = narrative.markdown(facts)
        self.assertLessEqual(len(text), narrative.NARRATIVE_LIMIT)
        self.assertRegex(text, r"- \*\*\d+ earlier steps\*\* — done")
        self.assertIn("W40 implement", text)  # the newest rows stay
        self.assertIn("Now", text)

    def test_a_short_narrative_is_unchanged(self) -> None:
        facts = navigator.narrative_facts(navigator.new_state("/simulation-only/repo", "Short.", improve_skill=""))
        self.assertEqual(narrative.markdown(facts), narrative._markdown(facts))


class TimelineAndPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-narrative-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
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
        # One progress block: the narrative stands in for the status block and the status line.
        self.assertNotIn(navigator.STATUS_BEGIN, head)
        self.assertIsNone(hook.LINE.search(head))
        self.assertTrue(hook.packet_progress(head).startswith(narrative.BEGIN))
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
        state = driver.advance_to(driver.planned(ROWS[:1]), "test-spec")
        self.assertEqual(navigator.narrative_lines(state), [])
        status_line = navigator.status_line(state)
        self.assertEqual(navigator.progress_lines(state), [status_line, ""])
        stdout = f"ShipLoop navigator | test-spec | revision 1\n\n{status_line}\n"
        payload = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                   "tool_input": {"command": f"python3 {self.cli} next --run-dir={self.run_dir}"},
                   "tool_response": {"stdout": stdout, "stderr": ""}}
        message = hook.status_message(payload)
        self.assertEqual(message, hook.compact(status_line))
        self.assertEqual(message.splitlines(), [
            'ShipLoop ▶ Work items > W1 "Config loader refactor" (1 of 1) > Plan > test-spec',
            "Next: test-spec: " + navigator.guidance.STAGE_PURPOSE["test-spec"]])


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    # Driver inherits the status-display tests only for their helpers; run just this file's tests.
    return unittest.TestSuite(loader.loadTestsFromTestCase(case)
                              for case in (NarrativeTests, TimelineAndPacketTests))


if __name__ == "__main__":
    unittest.main()
