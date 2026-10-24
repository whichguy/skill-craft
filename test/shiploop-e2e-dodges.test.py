#!/usr/bin/env python3
"""No-model checks for the E2E harness's run-level dodge counters (metrics.dodge_counts).

Each detector ported from the template experiments (E2 source_search and inspected_ui, E3 _GUARD, f14d4ec4) gets a
positive and a negative fixture: grep-only checks on code files split by their criterion's confirm (a ``searched``
docstring grep is context, not a dodge), guarded REDs, criteria confirmed by inspection, and surviving mutants read from
``tests/<action>-mutation<N>.md``. Fixtures are written to a temporary run folder; no host starts.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))

import metrics  # noqa: E402


def write_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# ShipLoop record\n\n```shiploop-state\n" + json.dumps(record, indent=2) + "\n```\n")


def step_plan(criteria: list[dict], commands: list[dict], steps: list[dict] | None = None) -> dict:
    return {"criteria": criteria, "test_commands": commands, "steps": steps or []}


class GrepChecks(unittest.TestCase):
    def test_grep_on_code_serving_an_executed_criterion_is_a_dodge(self) -> None:
        found = metrics.plan_dodges(step_plan([{"id": "C1", "text": "Moves are validated.", "confirm": "executed"}],
                                              [{"command": "grep -q validateMove src/board.js", "criteria": ["C1"],
                                                "suite": "focused"}]))
        self.assertEqual(found["grep"]["executed"], ["grep -q validateMove src/board.js"])

    def test_searched_docstring_grep_is_context_not_a_dodge(self) -> None:
        found = metrics.plan_dodges(step_plan([{"id": "C2", "text": "validateMove documents its contract.",
                                                "confirm": "searched"}],
                                              [{"command": "grep -q '@param move' src/board.js", "criteria": ["C2"],
                                                "suite": "focused"}]))
        self.assertEqual(found["grep"], {"searched": ["grep -q '@param move' src/board.js"], "executed": [], "unmatched": []})

    def test_step_proof_grep_with_no_criterion_is_context(self) -> None:
        found = metrics.plan_dodges(step_plan([], [], [{"id": "S1", "proof": "grep -n render lib/view.ts"}]))
        self.assertEqual(found["grep"]["unmatched"], ["grep -n render lib/view.ts"])
        self.assertEqual(found["grep"]["executed"], [])

    def test_a_grep_beside_a_real_test_of_the_same_criterion_is_no_dodge(self) -> None:
        """Sol pass 2, finding 6: judged per criterion, as the step-plan gate judges it."""
        found = metrics.plan_dodges(step_plan(
            [{"id": "C1", "text": "Moves are validated.", "confirm": "executed"}],
            [{"command": "node --test test/board.test.js", "criteria": ["C1"], "suite": "focused"},
             {"command": "grep -q validateMove src/board.js", "criteria": ["C1"], "suite": "check"}],
            [{"id": "S1", "criteria": ["C1"], "proof": "grep -q validateMove src/board.js"}]))
        self.assertEqual(found["grep"]["executed"], [])
        self.assertEqual(found["grep"]["unmatched"], ["grep -q validateMove src/board.js"])  # the step proof: context

    def test_runner_or_docs_grep_is_not_counted(self) -> None:
        found = metrics.plan_dodges(step_plan([{"id": "C1", "text": "x", "confirm": "executed"}],
                                              [{"command": "node --test test/board.test.js", "criteria": ["C1"]},
                                               {"command": "grep -q Install README.md", "criteria": ["C1"]}]))
        self.assertEqual(found["grep"], {"searched": [], "executed": [], "unmatched": []})


class GuardedRed(unittest.TestCase):
    def test_file_guard_on_a_focused_command_is_counted(self) -> None:
        for command in ("test ! -f src/records.js && node --test",
                        "if [ ! -e src/records.js ]; then exit 1; fi; node --test",
                        "node -e \"require.resolve('./src/records')\" && node --test"):
            found = metrics.plan_dodges(step_plan([], [{"command": command, "suite": "focused"}]))
            self.assertEqual(found["guarded"], [command], command)

    def test_plain_focused_command_and_regression_guard_are_not_counted(self) -> None:
        found = metrics.plan_dodges(step_plan([], [{"command": "node --test --test-name-pattern TC-1", "suite": "focused"},
                                                   {"command": "test -f a.js && node --test", "suite": "regression"}]))
        self.assertEqual(found["guarded"], [])


class Inspected(unittest.TestCase):
    def test_inspected_confirm_and_inspection_text_are_counted(self) -> None:
        found = metrics.plan_dodges(step_plan([{"id": "C1", "text": "The button shows.", "confirm": "inspected"},
                                               {"id": "C2", "text": "The board renders; inspection suffices."}], []))
        self.assertEqual(found["inspected"], ["C1", "C2"])

    def test_executed_criteria_are_not_counted(self) -> None:
        found = metrics.plan_dodges(step_plan([{"id": "C1", "text": "Inspect the board.", "confirm": "executed"},
                                               {"id": "C2", "text": "Inspected and executed in the DOM harness."}], []))
        self.assertEqual(found["inspected"], [])


class RunCounts(unittest.TestCase):
    def test_run_folder_counts_and_report_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            plan = step_plan([{"id": "C1", "text": "Moves are validated.", "confirm": "executed"},
                              {"id": "C2", "text": "Docstring.", "confirm": "searched"},
                              {"id": "C3", "text": "Looks right.", "confirm": "inspected"}],
                             [{"command": "grep -q validateMove src/board.js", "criteria": ["C1"], "suite": "focused"},
                              {"command": "grep -q '@param' src/board.js", "criteria": ["C2"], "suite": "focused"},
                              {"command": "test ! -f src/x.js && node --test", "suite": "focused"}])
            write_record(run / "results" / "nav-a.md", {"action": "nav-a", "stage": "step-plan", "result": plan})
            write_record(run / "results" / "nav-b.md", {"action": "nav-b", "stage": "test-spec", "result": plan})
            write_record(run / "tests" / "nav-a-mutation1.md", {"survived": 5})
            write_record(run / "tests" / "nav-a-mutation2.md", {"survived": 2})
            write_record(run / "tests" / "nav-a-mutation-check-only.md", {"survived": 9})
            counts = metrics.dodge_counts(run)
        self.assertEqual({k: counts[k] for k in ("plans", "grep_searched", "grep_executed", "grep_unmatched", "guarded",
                                                 "inspected", "surviving_mutants", "dodges")},
                         {"plans": 1, "grep_searched": 1, "grep_executed": 1, "grep_unmatched": 0, "guarded": 1,
                          "inspected": 1, "surviving_mutants": 2, "dodges": 4})
        line = metrics.dodge_text(counts)
        self.assertIn("Test-quality dodges: 4", line)
        self.assertIn("surviving mutants 2", line)

    def test_absent_records_are_unmeasured_not_zero_mutants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            counts = metrics.dodge_counts(Path(tmp))
        self.assertEqual((counts["plans"], counts["dodges"], counts["surviving_mutants"]), (0, 0, None))
        self.assertEqual(metrics.dodge_counts(None)["plans"], 0)


if __name__ == "__main__":
    unittest.main()
