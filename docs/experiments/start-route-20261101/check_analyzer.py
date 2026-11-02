"""Calibration of analyze.py, run as `python3 -I check_analyzer.py` from this folder (no model, a few seconds).

It feeds the analyzer the counterexamples Astra's review found on 2026-11-01 (a partial design that printed RELEASE, a host whose
sessions never started that printed NO REGRESSION FOUND, a plan slot with no session) and the ones Sol's review of the fixes found
the same day (a partial batch with no plan still printed RELEASE, a treatment that never started still read as no regression, a
reaper that killed a process whose path only contained the trial's), and replays every committed batch with its registered plan:
the verdict a fresh run prints from the compact rows must equal the verdict line of the committed analysis output.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze  # noqa: E402
import start_probe


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


def run_analyzer(rows, *flags, plan=True):
    """The analyzer's printed report for `rows`, as a fresh process reads them from a results file. The batch is complete against
    its plan by construction (the plan lists the rows' own slots) unless `plan` is False, which runs it with no --plan at all."""
    with tempfile.TemporaryDirectory() as folder:
        results, planned = Path(folder, "results.jsonl"), Path(folder, "plan.json")
        results.write_text("".join(json.dumps(r) + "\n" for r in rows))
        planned.write_text(json.dumps([{"slot": r["slot"]} for r in rows]))
        return subprocess.run([sys.executable, "-I", str(HERE / "analyze.py"), str(results), *flags, *(["--plan", str(planned)] if plan else [])],
                              capture_output=True, text=True, check=True).stdout


def verdict_of(text):
    lines = [line for line in text.splitlines() if line.startswith(("DECISION:", "VERDICT:"))]
    return lines[-1] if lines else None


def host_batch(control, treatment):
    """The registered host design (four requests, both arms, twelve sessions a cell) with the start each arm made."""
    rows, slot = [], 0
    for stimulus in ("sf-ui", "repo", "inplace-hello", "nogit-hello"):
        right = "workspace" if stimulus in ("sf-ui", "repo") else "direct"
        for arm, start in (("C", control), ("T2", treatment)):
            for _ in range(12):
                rows.append(host_row(slot, stimulus, arm, right if start == "right" else start))
                slot += 1
    return rows


class NoPlanTests(unittest.TestCase):
    """Sol's review: thirteen rows of a 104-slot batch met every condition and printed RELEASE, because completeness was only
    checked when --plan was given. A verdict needs the registered plan; without it the arithmetic is shown, not decided."""

    def thirteen_of_the_batch(self):
        rows = [guard_row(i, "sf-ui", "GOLD", "direct", True, "workspace") for i in range(8)]
        rows.append(guard_row(100, "sf-ui", "G", "workspace", False, "workspace"))
        rows += [guard_row(200 + i, "inplace-hello", "G", "direct", True, "direct", True) for i in range(2)]
        rows += [guard_row(300 + i, "nogit-hello", "G", "direct", True, "direct", True) for i in range(2)]
        return rows

    def test_a_partial_batch_that_meets_every_condition_is_not_a_release_without_its_plan(self):
        verdict = verdict_of(run_analyzer(self.thirteen_of_the_batch(), "--mode", "guard", "--gate", "e", plan=False))
        self.assertTrue(verdict.startswith("VERDICT: INSUFFICIENT: no --plan"), verdict)
        self.assertIn("RELEASE: H1, H2 and H3 are met", verdict)   # the arithmetic is still shown, beside the refusal to decide

    def test_the_same_partial_batch_with_the_registered_plan_names_its_missing_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            plan = Path(folder, "plan.json")
            plan.write_text(json.dumps([{"slot": r["slot"]} for r in complete_guard_batch()]))
            verdict = verdict_of(run_analyzer(self.thirteen_of_the_batch(), "--mode", "guard", "--gate", "e", "--plan", str(plan), plan=False))
        self.assertTrue(verdict.startswith("VERDICT: INSUFFICIENT: "), verdict)
        self.assertIn("planned slot(s) have no valid session", verdict)

    def test_a_complete_batch_with_its_plan_keeps_its_verdict(self):
        rows = complete_guard_batch()
        verdict = verdict_of(run_analyzer(rows, "--mode", "guard", "--gate", "e"))
        self.assertEqual(verdict, "VERDICT: RELEASE: H1, H2 and H3 are met")

    def test_a_start_set_decision_also_needs_the_plan(self):
        rows, slot = [], 0
        for stimulus in ("sf-ui", "hello", "repo"):
            for arm in analyze.ARMS:
                for i in range(6):
                    wrong = stimulus == "sf-ui" and (arm == "C" and i < 4 or arm == "T2" and i < 1)
                    rows.append(host_row(slot, stimulus, arm, "direct" if wrong else "workspace"))
                    slot += 1
        decision = verdict_of(run_analyzer(rows, "--arms", str(HERE / "arms.json"), plan=False))
        self.assertTrue(decision.startswith("DECISION: INSUFFICIENT: no --plan"), decision)


class UnreadableTests(unittest.TestCase):
    """Sol's review: with every treatment session unable to start, the controls alone kept the aggregate no-start share at half,
    the comparison skipped the zero denominators, and the host read NO REGRESSION FOUND."""

    def hosts(self, control, treatment):
        return verdict_of(run_analyzer(host_batch(control, treatment), "--mode", "hosts"))

    def test_a_treatment_that_never_started_is_unreadable_not_free_of_regression(self):
        self.assertTrue(self.hosts("right", "none").startswith("VERDICT: UNREADABLE"), self.hosts("right", "none"))

    def test_a_control_that_never_started_is_unreadable_too(self):
        self.assertTrue(self.hosts("none", "right").startswith("VERDICT: UNREADABLE"), self.hosts("none", "right"))

    def test_one_request_whose_treatment_never_started_hides_nothing(self):
        rows = host_batch("right", "right")
        for row in rows:
            if row["stimulus"] == "repo" and row["arm"] == "T2":
                row["start"] = "none"
        verdict = verdict_of(run_analyzer(rows, "--mode", "hosts"))
        self.assertTrue(verdict.startswith("VERDICT: UNREADABLE"), verdict)
        self.assertIn("repo/T2", verdict)

    def test_the_same_holds_for_the_explicit_requests_of_the_in_place_set(self):
        rows = [r for r in host_batch("right", "none") if r["stimulus"] in ("inplace-hello", "nogit-hello")]
        verdict = verdict_of(run_analyzer(rows, "--mode", "inplace"))
        self.assertTrue(verdict.startswith("VERDICT: UNREADABLE"), verdict)

    def test_a_host_batch_that_started_everywhere_and_did_nothing_wrong_is_still_fine(self):
        self.assertEqual(self.hosts("right", "right"), "VERDICT: NO REGRESSION FOUND")

    def test_no_sessions_at_all_is_insufficient_in_every_mode(self):
        for flags, label in ((["--mode", "hosts"], "VERDICT"), (["--mode", "inplace"], "VERDICT"), (["--mode", "guard"], "VERDICT"),
                             ([], "DECISION")):
            with self.subTest(flags=flags):
                self.assertTrue(verdict_of(run_analyzer([], *flags)).startswith(f"{label}: INSUFFICIENT"),
                                verdict_of(run_analyzer([], *flags)))


class ReaperTests(unittest.TestCase):
    """start_probe.reap kills what is left of a trial. It must kill processes that use the trial's folder and no others: Astra's
    review made the match component-wise against a longer sibling name, and Sol's showed a trailing-character blacklist still let
    /t/trial-a1+backup and /other/t/trial-a1 through."""
    TRIAL = "/tmp/trial-a1"

    def killed(self, command):
        def listing(argv, **kwargs):
            return SimpleNamespace(stdout=f"987654 {os.getuid()} {command}\n" if argv[0] == "ps" else "")
        with mock.patch.object(start_probe.subprocess, "run", side_effect=listing), \
                mock.patch.object(start_probe.os, "kill") as kill:
            start_probe.reap(Path(self.TRIAL))
        return bool(kill.call_args_list)

    def test_a_process_that_uses_the_trial_folder_is_killed(self):
        for command in ("worker /tmp/trial-a1", "worker /tmp/trial-a1/work", "worker --run-dir=/tmp/trial-a1/run",
                        "SHIPLOOP_RUN=/tmp/trial-a1/run worker", "PATH=/usr/bin:/tmp/trial-a1/bin worker",
                        "python3 -c \"import os; os.chdir('/tmp/trial-a1/work')\"", "worker '/tmp/trial-a1/work'"):
            with self.subTest(command=command):
                self.assertTrue(self.killed(command))

    def test_a_process_whose_path_only_contains_the_trials_is_left_alone(self):
        for command in ("worker /tmp/trial-a10/work", "worker /tmp/trial-a1+backup/work", "worker /other/tmp/trial-a1/work",
                        "worker /tmp/trial-a1.old/work", "worker /tmp/trial-a1-x", "worker /tmp/xtrial-a1/work",
                        "worker /tmp/trial-a1~/work", "worker /tmp/trial-a1@2/work", "worker /mnt/tmp/trial-a1"):
            with self.subTest(command=command):
                self.assertFalse(self.killed(command))


# (compact rows, registered plan, flags, committed output)
BATCHES = [
    ("results-compact.jsonl", "plan.json", ["--arms", "arms.json"], "analysis-output.txt"),
    ("results-r2-compact.jsonl", "plan-r2.json", ["--arms", "arms-r2.json"], "analysis-r2-output.txt"),
    ("results-i1-compact.jsonl", "plan-inplace.json", ["--mode", "inplace"], "analysis-i1-output.txt"),
    ("results-h-claude-compact.jsonl", "plan-hosts.json", ["--mode", "hosts", "--arms", "arms-r2.json"], "analysis-h-claude-output.txt"),
    ("results-h-grok-compact.jsonl", "plan-hosts.json", ["--mode", "hosts", "--arms", "arms-r2.json"], "analysis-h-grok-output.txt"),
    ("results-guard-compact.jsonl", "plan-guard.json", ["--mode", "guard"], "analysis-guard-output.txt"),
    ("results-guard2-compact.jsonl", "plan-guard2.json", ["--mode", "guard", "--gate", "e"], "analysis-guard2-output.txt"),
]


def verdict_line(text):
    lines = [line for line in text.splitlines() if line.startswith(("DECISION:", "VERDICT:"))]
    return lines[-1] if lines else None


class ReplayTests(unittest.TestCase):
    def test_every_committed_batch_keeps_its_conclusion(self):
        for rows, plan, flags, committed in BATCHES:
            with self.subTest(batch=rows):
                fresh = subprocess.run([sys.executable, "-I", str(HERE / "analyze.py"), str(HERE / rows), "--plan", str(HERE / plan), *flags],
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
