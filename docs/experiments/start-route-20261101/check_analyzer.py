"""Calibration of analyze.py, run as `python3 -I check_analyzer.py` from this folder (no model, a few seconds).

It feeds the analyzer the counterexamples Astra's review found on 2026-11-01 (a partial design that printed RELEASE, a host whose
sessions never started that printed NO REGRESSION FOUND, a plan slot with no session) and replays every committed batch: the
verdict a fresh run prints from the compact rows must equal the verdict line of the committed analysis output.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402


def guard_row(slot, stimulus, arm, start, refused, final, in_place=False):
    return {"slot": slot, "attempt": 1, "stimulus": stimulus, "arm": arm, "i": slot, "start": start, "valid": True,
            "refused": refused, "final_route": final, "starts": [{"route": start, "in_place": in_place}],
            "self_bootstrap": False, "read_run_start": False, "seconds_to_start": 1.0}


def host_row(slot, stimulus, arm, start):
    return {"slot": slot, "attempt": 1, "stimulus": stimulus, "arm": arm, "i": slot, "start": start, "valid": True,
            "self_bootstrap": False, "read_run_start": False, "seconds_to_start": None}


def complete_guard_batch():
    rows = [guard_row(i, "sf-ui", "GOLD", "direct", True, "workspace") for i in range(10)]
    rows += [guard_row(100 + i, "sf-ui", "G", "workspace", False, "workspace") for i in range(5)]
    rows += [guard_row(200 + i, "inplace-hello", "G", "direct", True, "direct", True) for i in range(4)]
    rows += [guard_row(300 + i, "nogit-hello", "G", "direct", True, "direct", True) for i in range(4)]
    return rows


class CounterexampleTests(unittest.TestCase):
    def test_a_partial_design_is_insufficient_not_release(self):
        rows = [guard_row(i, "sf-ui", "GOLD", "direct", True, "workspace") for i in range(8)]
        rows += [guard_row(100 + i, "inplace-hello", "G", "direct", True, "direct", True) for i in range(4)]
        _, verdict = analyze.evaluate_guard(rows, "h1")
        self.assertTrue(verdict.startswith("INSUFFICIENT"), verdict)

    def test_a_complete_design_that_meets_every_condition_is_release(self):
        _, verdict = analyze.evaluate_guard(complete_guard_batch(), "e")
        self.assertTrue(verdict.startswith("RELEASE"), verdict)

    def test_h3_cannot_pass_on_no_observations(self):
        rows = [r for r in complete_guard_batch() if not (r["stimulus"] == "sf-ui" and r["arm"] == "G")]
        _, verdict = analyze.evaluate_guard(rows, "e")
        self.assertTrue(verdict.startswith("INSUFFICIENT"), verdict)

    def test_a_host_whose_sessions_never_started_is_unreadable_not_fine(self):
        rows = [host_row(i, s, a, "none") for i, (s, a) in enumerate(
            [(s, a) for s in ("sf-ui", "repo", "inplace-hello", "nogit-hello") for a in ("C", "T2") for _ in range(4)])]
        _, verdict = analyze.evaluate_hosts(analyze.tally(rows))
        self.assertTrue(verdict.startswith("UNREADABLE"), verdict)

    def test_a_planned_slot_with_no_session_makes_the_verdict_insufficient(self):
        with tempfile.TemporaryDirectory() as folder:
            results, plan = Path(folder, "results.jsonl"), Path(folder, "plan.json")
            rows = complete_guard_batch()
            results.write_text("".join(json.dumps(r) + "\n" for r in rows))
            plan.write_text(json.dumps([{"slot": r["slot"]} for r in rows] + [{"slot": 999}]))
            out = subprocess.run([sys.executable, "-I", str(HERE / "analyze.py"), str(results), "--mode", "guard", "--gate", "e",
                                  "--plan", str(plan)], capture_output=True, text=True, check=True).stdout
            self.assertIn("VERDICT: INSUFFICIENT: 1 planned slot(s) have no valid session (999)", out)

    def test_the_card_sizes_of_a_historical_batch_are_the_recorded_ones(self):
        self.assertEqual(analyze.card_sizes(HERE / "arms.json"), {"C": 30011, "T1": 30033, "T2": 30115})


# (compact rows, flags, committed output)
BATCHES = [
    ("results-compact.jsonl", ["--arms", "arms.json"], "analysis-output.txt"),
    ("results-r2-compact.jsonl", ["--arms", "arms-r2.json"], "analysis-r2-output.txt"),
    ("results-i1-compact.jsonl", ["--mode", "inplace"], "analysis-i1-output.txt"),
    ("results-h-claude-compact.jsonl", ["--mode", "hosts", "--arms", "arms-r2.json"], "analysis-h-claude-output.txt"),
    ("results-h-grok-compact.jsonl", ["--mode", "hosts", "--arms", "arms-r2.json"], "analysis-h-grok-output.txt"),
    ("results-guard-compact.jsonl", ["--mode", "guard"], "analysis-guard-output.txt"),
    ("results-guard2-compact.jsonl", ["--mode", "guard", "--gate", "e"], "analysis-guard2-output.txt"),
]


def verdict_line(text):
    lines = [line for line in text.splitlines() if line.startswith(("DECISION:", "VERDICT:"))]
    return lines[-1] if lines else None


class ReplayTests(unittest.TestCase):
    def test_every_committed_batch_keeps_its_conclusion(self):
        for rows, flags, committed in BATCHES:
            with self.subTest(batch=rows):
                fresh = subprocess.run([sys.executable, "-I", str(HERE / "analyze.py"), str(HERE / rows), *flags],
                                       capture_output=True, text=True, check=True, cwd=HERE).stdout
                self.assertEqual(verdict_line(fresh), verdict_line((HERE / committed).read_text()))


class DetectorTests(unittest.TestCase):
    """start_probe.detect_start reads the first ShipLoop start from a command. The known gaps below are Astra's (2026-11-01); they are
    marked as expected failures so that fixing one turns the test red until the marker is removed. In the effect-stop probes the route
    that decides is read from the disk, not from this detector."""

    CLI = "python3 /x/skills/shiploop/scripts/shiploop"

    def setUp(self):
        import start_probe
        self.detect = start_probe.detect_start

    def test_the_two_starts_and_a_read_of_the_verb(self):
        self.assertEqual(self.detect(f"{self.CLI} init --repo /tmp/w --prompt=x"), "direct")
        self.assertEqual(self.detect(f"{self.CLI} workspace start --repo /tmp/w --prompt=x"), "workspace")
        self.assertIsNone(self.detect(f"{self.CLI} init --help"))
        self.assertIsNone(self.detect(f"{self.CLI} workspace start --help"))

    def test_a_help_request_that_names_the_repository_is_not_a_start(self):
        self.assertIsNone(self.detect(f"{self.CLI} init --repo /tmp/w --help"))

    @unittest.expectedFailure
    def test_known_gap_a_command_that_only_prints_a_start_is_not_a_start(self):
        self.assertIsNone(self.detect("printf '%s' '" + self.CLI + " init --repo /tmp/w --prompt=x'"))

    @unittest.expectedFailure
    def test_known_gap_a_variable_start_without_the_word_shiploop_in_the_command_is_a_start(self):
        self.assertEqual(self.detect("$CLI init --repo /tmp/w --prompt=x"), "direct")

    @unittest.expectedFailure
    def test_known_gap_an_unrelated_init_list_before_a_workspace_start_does_not_decide(self):
        cmd = ("python3 -c \"a=['init']; import subprocess; "
               "subprocess.run(['python3','/x/scripts/shiploop','workspace','start','--repo','r','--prompt','p'])\"")
        self.assertEqual(self.detect(cmd), "workspace")


if __name__ == "__main__":
    unittest.main(verbosity=2)
