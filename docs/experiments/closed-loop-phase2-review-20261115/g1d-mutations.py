"""Break each fix of replan B (journal R10, R12) on purpose and run the test that guards it; every mutant must be caught.

Round 5 found that round 4's driver (g1b-mutations.py) counted any non-zero exit as caught, a setup error included, and exited 0 even when
mutants survived. This one counts a mutant as caught only when its named test FAILS on an assertion (a FAIL line, no ERROR line), and exits
1 when any mutant is missed, not applied, or ended by an error.

    python3 -B g1d-mutations.py --root <a copy of the tree>    # never the checkout others are using: facade.py is edited in place

The tests run with a `codex` stub first on PATH that exits 1, so a mutant that lets a probe reach its model session cannot start a real one.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

STEPS = "test/shiploop-e2e-adapter-steps.test.py"

# (label, the facade text, its broken form, the test that must fail); a list of (text, broken form) pairs in place of the text when one
# mutant needs several edits
MUTANTS = [
    ("no identity check before a step",
     "problem = identity_problem(layout, probe_env())  # the engine's own environment (run_invocation): refuse now, not after a run",
     "problem = None",
     "ReplanTests.test_a_step_without_a_configured_engine_identity_is_refused_before_anything_starts"),
    ("a guessed identity accepted",
     '"-c", "user.useConfigOnly=true", ',
     "",
     "ReplanTests.test_a_step_without_a_configured_engine_identity_is_refused_before_anything_starts"),
    ("the improver's own view not checked",
     "if gitconfig.is_file():  # otherwise the harness writes",
     "if False:  # otherwise the harness writes",
     "ReplanTests.test_the_improvers_identity_is_the_one_in_the_home_gitconfig"),
    ("the runs probe checks the identity only after its run",
     "problem = identity_problem(layout, probe_env())  # before the run",
     "problem = None  # before the run",
     "ReplanTests.test_the_runs_probe_refuses_before_its_model_session"),
    ("a cancel publishes a finished step",
     '''        if rec["state"] in (*LIVE, "prepared"):
            # One publisher:''',
     '''        if rec["state"] == "prepared":
            finish_publication(layout, rec)
        elif rec["state"] in LIVE:
            # One publisher:''',
     "SecondReviewTests.test_a_cancel_of_a_finished_step_answers_cancelled_as_the_orchestrator_requires"),
    ("a cleanup publishes a finished step",
     '''            if rec["state"] in (*LIVE, "prepared"):
                settle(layout, rec, "cancelled", "ended by cleanup"''',
     '''            if rec["state"] == "prepared":
                finish_publication(layout, rec)
            elif rec["state"] in LIVE:
                settle(layout, rec, "cancelled", "ended by cleanup"''',
     "SecondReviewTests.test_cleanup_ends_a_finished_step_whose_worker_is_gone_and_publishes_nothing"),
    ("a stored kill problem never checked again",
     'if killed is None and rec.get("worker") and kill_problems(rec.get("kill")):',
     "if False:",
     "ReplanTests.test_a_repeated_cleanup_answers_from_the_stored_evidence_until_a_check_resolves_it"),
    ("a cleanup answers from its own call only (round 4's code)",
     [('if killed is None and rec.get("worker") and kill_problems(rec.get("kill")):', "if False:"),
      ('stuck = kill_problems(rec.get("kill"))  # the stored evidence', "stuck = kill_problems(killed)  # the stored evidence")],
     None,
     "ReplanTests.test_a_repeated_cleanup_answers_from_the_stored_evidence_until_a_check_resolves_it"),
    ("escalation without checking ownership again",
     "if number == signal.SIGKILL:  # ownership is decided again",
     "if False:  # ownership is decided again",
     "ReplanTests.test_a_group_recycled_during_the_grace_is_not_sent_sigkill"),
    ("a failure after preparing settled failed",
     'if rec.get("prepared") is not None:',
     "if False:",
     "ReplanTests.test_a_write_that_fails_after_the_tip_moved_leaves_the_step_for_a_poll_to_finish"),
    ("an unreadable epoch read as empty",
     '"unreadable": facts.get("why") or "unreadable",',
     '"unreadable": None,',
     "SecondReviewTests.test_an_epoch_ledger_the_harness_cannot_read_makes_the_cycle_invalid"),
    ("changed sealed evidence not reported",
     'if epoch is not None and epoch["invalid_evidence"]:',
     "if False:",
     "SecondReviewTests.test_sealed_run_evidence_changed_after_recording_makes_the_cycle_invalid"),
    ("the first decision read",
     '"decision": (state.get("decision") or {}).get("result"), "receipts": receipts,',
     '"decision": next((row["result"] for row in rows if row["kind"] == "decision"), None), "receipts": receipts,',
     "SecondReviewTests.test_the_last_decision_of_an_epoch_is_the_one_that_counts"),
    ("any reviewed row counted, seal or not",
     'if attempt["status"] == "reviewed":  # epoch.state\'s own reading',
     'if any(row["kind"] == "reviewed" and row.get("attempt_id") == attempt["id"] for row in rows):  # epoch.state\'s own reading',
     "SecondReviewTests.test_an_epoch_receipt_changed_after_its_review_is_not_a_review"),
    ("calibration not bound to its scoring",
     'if scored != checked["cases"]:',
     "if False:",
     "ProbeTests.test_the_calibrated_claim_needs_a_report_for_this_profile_whose_digest_still_holds"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    root = args.root.resolve()
    facade = root / "test" / "shiploop_e2e" / "adapter" / "facade.py"
    original = facade.read_text()
    digest = hashlib.sha256(original.encode()).hexdigest()
    stubs = Path(tempfile.mkdtemp(prefix="mutant-stubs-"))
    (stubs / "codex").write_text("#!/bin/sh\nexit 1\n")
    (stubs / "codex").chmod(0o755)
    env = {**os.environ, "PATH": f"{stubs}:{os.environ['PATH']}"}
    results = []
    try:
        for label, old, new, test in MUTANTS:
            edits = old if isinstance(old, list) else [(old, new)]  # a mutant may need several edits (round 4's code, say)
            mutated = original
            if any(mutated.count(before) != 1 for before, _after in edits):
                results.append((label, "NOT APPLIED", test))
                continue
            for before, after in edits:
                mutated = mutated.replace(before, after, 1)
            facade.write_text(mutated)
            done = subprocess.run([sys.executable, "-B", STEPS, test], cwd=root, capture_output=True, text=True, timeout=900, check=False, env=env)
            failed = any(line.startswith("FAIL:") for line in done.stderr.splitlines())
            errored = any(line.startswith("ERROR:") for line in done.stderr.splitlines())
            verdict = "caught" if done.returncode != 0 and failed and not errored else "ERRORED" if errored else "MISSED"
            results.append((label, verdict, test))
    finally:
        facade.write_text(original)
    assert hashlib.sha256(facade.read_text().encode()).hexdigest() == digest, "facade.py was not restored"
    for label, verdict, test in results:
        print(f"{verdict:12} {label}  [{test}]")
    caught = sum(verdict == "caught" for _label, verdict, _test in results)
    print(f"{caught} of {len(results)} caught")
    return 0 if caught == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
