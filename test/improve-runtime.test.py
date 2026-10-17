#!/usr/bin/env python3
"""Improve's bundled Until Loop runtime: the review gates Improve, ShipLoop and the Backchain packet rely on.

Owner decision 2026-10-16 (Improve-value study, docs/shiploop-improve-stop-rule-journal-2026-10-16.md). Gate 2
(`required_trivial_reviews: 2`, the unchanged-content gate) completes a loop on ONE pass that the report calls trivial and
satisfied, whose checks passed, and after which the runtime measures the content tree equal to the tree after the
previous pass (for the first pass: the tree at start). A pass that changed the tree never completes the loop, however
it is labelled. This generalises the 2026-09-26 unchanged-first-pass rule from the first pass to any pass; it replaces
the two-consecutive-trivial streak at gate 2. There is no count and no timer. Gates 0 and 1 are unchanged, so contracts
written for the published until-loop plugin (ShipLoop's inner-stage loops, Backchain) stay valid.

Gate 3 (D-6 / R1 of the efficiency plan, a PROPOSAL awaiting the owner's S-10 text) is the same measurement with the
rule main had before the stop rule, for ShipLoop's implement and carry-forward reviews, which are code reviews: a first
pass that is trivial, satisfied and leaves the content as it started completes; once any pass has changed the content,
it takes TWO consecutive trivial, satisfied passes that each leave it unchanged. A trivial pass that changed the
content never completes at either gate. Gate 2 is unchanged.

A directory that is not a Git worktree is measured too (through a throwaway bare repository), so an in-place run
outside Git starts its Improve review the same way (F3 of the efficiency plan).

Owner decision 2026-10-04 (fast planning, increment I2). The ShipLoop plan packet's one-pass text tells the host
to write `required_trivial_reviews: 0` for the Backchain planning child. OnePassGateTests reads the gate from the
printed text and drives this runtime with it, so the one-pass exit is proved through the real gate.
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
sys.dont_write_bytecode = True  # never leave __pycache__ inside the shipped runtime
spec = importlib.util.spec_from_file_location("until_loop_ephemeral", SCRIPT)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_prompts as prompts  # noqa: E402

TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Full review; nothing worth changing; checks pass.", "handoff": "Nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", evidence="Found and fixed a material gap.")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def token(packet: dict) -> str:
    return next(arg.split("=", 1)[1] for arg in packet["done_argv"] if arg.startswith("--action="))


class LoopCase(unittest.TestCase):
    """A Git repo with one committed file, an uncommitted file, an ignored directory, and a state directory."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="improve-runtime-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.repo = self.root / "repo"
        self.state_dir = self.root / "state"
        self.outside = self.root / "outside" / "result.md"  # a stage result that lives outside the worktree
        self.repo.mkdir()
        self.state_dir.mkdir()
        self.outside.parent.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "r@example.invalid")
        git(self.repo, "config", "user.name", "R")
        (self.repo / "app.py").write_text("x = 1\n")
        (self.repo / ".gitignore").write_text("build/\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        (self.repo / "wip.py").write_text("# uncommitted work that was already there\n")

    def start(self, gate: int = 2, workspace: Path | None = None, **extra) -> dict:
        contract = {"workspace": str(workspace or self.repo), "work": "Review the candidate.",
                    "exit_condition": "A review finds nothing worth changing.", "repeat_condition": "Repeat.",
                    "required_trivial_reviews": gate,
                    "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e",
                                "resources": []}, **extra}
        return runtime.start(contract, self.state_dir)

    @staticmethod
    def done(packet: dict, report: dict = TRIVIAL) -> dict:
        return runtime.done(packet["state_file"], token(packet), report)

    def edit(self, text: str = "x = 2\n") -> None:
        (self.repo / "app.py").write_text(text)


class UnchangedGateTests(LoopCase):
    """The cases the owner named: (a) to (g) of the stop-rule brief, plus the A-B-A case from the study."""

    def test_a_trivial_pass_that_changed_nothing_completes_at_pass_one(self) -> None:  # (a)
        packet = self.start()
        self.assertEqual(packet["progress"], {"action_number": 1, "required_trivial_reviews": 2,
                                              "last_pass_changed_tree": None})
        (self.repo / "build").mkdir()
        (self.repo / "build" / "out.txt").write_text("ignored output\n")  # ignored files do not count
        (self.repo / ".shiploop-improve").mkdir()
        (self.repo / ".shiploop-improve" / "review-1.md").write_text("review\n")  # nor review notes
        terminal = self.done(packet)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"], {"action_number": 1, "required_trivial_reviews": 2,
                                                "last_pass_changed_tree": False})
        self.assertIn("unchanged from the previous pass", terminal["instruction"])

    def test_a_pass_that_edits_then_a_trivial_unchanged_pass_completes_at_pass_two_not_three(self) -> None:  # (b)
        packet = self.start()
        self.edit()
        active = self.done(packet, MATERIAL)
        self.assertEqual(active["status"], "active")
        self.assertIs(active["progress"]["last_pass_changed_tree"], True)
        terminal = self.done(active)  # no edit between the passes
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"]["action_number"], 2)

    def test_a_pass_labelled_trivial_that_changed_the_tree_does_not_complete(self) -> None:  # (c)
        for change in (lambda: self.edit(), lambda: (self.repo / "new_test.py").write_text("def test(): pass\n"),
                       lambda: (self.repo / "wip.py").write_text("# edited during the review\n")):
            with self.subTest(change=change):
                packet = self.start()
                change()
                active = self.done(packet, TRIVIAL)  # labelled trivial, satisfied, checks fine, yet it changed content
                self.assertEqual(active["status"], "active")
                self.assertIs(active["progress"]["last_pass_changed_tree"], True)
                self.assertIn("cannot end the loop however it was labelled", active["instruction"])
                self.assertEqual(active["last_report"]["classification"], "trivial")  # nothing else is reset or rewritten
                self.assertEqual(self.done(active)["status"], "complete")  # the next unchanged trivial pass ends it

    def test_a_committed_change_is_still_a_change(self) -> None:
        packet = self.start()
        self.edit("x = 3\n")
        git(self.repo, "commit", "-qam", "review fix")
        self.assertEqual(self.done(packet)["status"], "active")

    def test_a_material_pass_then_a_trivial_pass_that_changes_again_keeps_going(self) -> None:  # (d)
        packet = self.start()
        self.edit("x = 2\n")
        active = self.done(packet, MATERIAL)
        self.edit("x = 3\n")
        active = self.done(active, TRIVIAL)  # trivial label, but it edited again
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["progress"]["action_number"], 3)
        terminal = self.done(active)
        self.assertEqual((terminal["status"], terminal["progress"]["action_number"]), ("complete", 3))

    def test_a_then_b_then_a_trees_is_not_a_clean_pass(self) -> None:
        packet = self.start()
        self.edit("x = 2\n")                      # tree B
        active = self.done(packet, MATERIAL)
        self.edit("x = 1\n")                      # back to the start tree A: a change against B, not against A
        active = self.done(active, TRIVIAL)
        self.assertEqual(active["status"], "active")
        self.assertIs(active["progress"]["last_pass_changed_tree"], True)
        self.assertEqual(self.done(active)["status"], "complete")

    def test_a_change_to_the_candidate_file_outside_the_worktree_counts(self) -> None:  # (e)
        packet = self.start(candidate_paths=[str(self.outside)])
        self.outside.write_text("plan v1\n")      # creating the file is a change: absent -> present
        active = self.done(packet, TRIVIAL)
        self.assertEqual(active["status"], "active")
        self.assertIs(active["progress"]["last_pass_changed_tree"], True)
        self.outside.write_text("plan v2\n")      # only the outside file changed; the worktree did not
        active = self.done(active, TRIVIAL)
        self.assertEqual(active["status"], "active")
        self.assertIs(active["progress"]["last_pass_changed_tree"], True)
        self.assertEqual(self.done(active)["status"], "complete")

    def test_without_candidate_paths_an_outside_file_is_not_seen(self) -> None:
        packet = self.start()
        self.outside.write_text("plan v1\n")
        self.assertEqual(self.done(packet)["status"], "complete")  # why ShipLoop lists the stage result as a candidate

    def test_an_unsatisfied_or_incomplete_report_does_not_complete_even_with_an_unchanged_tree(self) -> None:  # (f)
        for fields in ({"exit_assessment": "unsatisfied"}, {"exit_assessment": "unknown"},
                       {"classification": "non-trivial"}, {"classification": "unresolved", "exit_assessment": "unsatisfied"}):
            with self.subTest(fields=fields):
                active = self.done(self.start(), dict(TRIVIAL, **fields))
                self.assertEqual(active["status"], "active")
                self.assertIs(active["progress"]["last_pass_changed_tree"], False)

    def test_failed_checks_with_an_unchanged_tree_do_not_complete(self) -> None:  # (f)
        checks = [{"id": "C1", "clause": "the suite passes", "command": "false"}]
        packet = self.start(exit_checks=checks)
        runtime.record(packet["state_file"], token(packet),
                       io.BytesIO(b"=== until-loop check C1\nboom\n\nUNTIL-LOOP-CHECK C1 exit=1\n"), io.StringIO())
        active = self.done(packet, TRIVIAL)
        self.assertEqual(active["status"], "active")
        self.assertIs(active["progress"]["last_pass_changed_tree"], False)  # unchanged, trivial, satisfied: the checks decide
        self.assertIn("C1", active["instruction"])
        runtime.record(active["state_file"], token(active),
                       io.BytesIO(b"=== until-loop check C1\n\nUNTIL-LOOP-CHECK C1 exit=0\n"), io.StringIO())
        self.assertEqual(self.done(active, TRIVIAL)["status"], "complete")

    def test_a_recorded_candidate_file_edit_after_the_verify_run_is_a_changed_workspace(self) -> None:
        checks = [{"id": "C1", "clause": "the suite passes", "command": "true"}]
        packet = self.start(exit_checks=checks, candidate_paths=[str(self.outside)])
        runtime.record(packet["state_file"], token(packet),
                       io.BytesIO(b"=== until-loop check C1\n\nUNTIL-LOOP-CHECK C1 exit=0\n"), io.StringIO())
        self.outside.write_text("edited after the checks ran\n")
        with self.assertRaisesRegex(runtime.StateError, "workspace changed after the recorded verify run"):
            self.done(packet, TRIVIAL)

    def test_a_cancelled_or_blocked_report_still_stops_the_loop(self) -> None:
        for fields, reason in (({"continuation_assessment": "cancelled"}, "cancelled"),
                               ({"continuation_assessment": "blocked", "exit_assessment": "unsatisfied"}, "blocked")):
            with self.subTest(reason=reason):
                stopped = self.done(self.start(), dict(MATERIAL, **fields))
                self.assertEqual(stopped["status"], "stopped")

    def test_gates_zero_and_one_keep_their_meaning_and_their_packet_shape(self) -> None:
        # (gate, label, status): the contracts ShipLoop's inner-stage loops and Backchain write for the published plugin.
        for gate, label, status in ((0, "non-trivial", "complete"), (1, "non-trivial", "active"),
                                    (1, "trivial", "complete")):
            with self.subTest(gate=gate, label=label):
                packet = self.start(gate=gate)
                self.assertEqual(packet["progress"], {"action_number": 1, "trivial_streak": 0,
                                                      "required_trivial_reviews": gate})
                self.edit(f"x = {gate}{label}\n")  # an edit never matters to these gates
                result = self.done(packet, dict(TRIVIAL, classification=label))
                self.assertEqual(result["status"], status)
                self.assertEqual(result["progress"], {"action_number": 1 if status == "complete" else 2,
                                                      "trivial_streak": 1 if label == "trivial" else 0,
                                                      "required_trivial_reviews": gate})

    def test_the_default_gate_is_zero_and_a_larger_one_is_refused(self) -> None:
        contract = {"workspace": str(self.repo), "work": "w", "exit_condition": "e", "repeat_condition": "r",
                    "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e", "resources": []}}
        self.assertEqual(runtime.start(contract, self.state_dir)["progress"]["required_trivial_reviews"], 0)
        with self.assertRaisesRegex(runtime.StateError, "must be 0, 1, 2 or 3.*no longer count that many reviews"):
            runtime.start(dict(contract, required_trivial_reviews=4), self.state_dir)
        self.assertEqual(runtime.start(dict(contract, required_trivial_reviews=3),
                                       self.state_dir)["progress"]["required_trivial_reviews"], 3)

    def test_the_unchanged_gates_need_a_tree_the_runtime_can_measure(self) -> None:
        # A tree that cannot be measured (Git fails on the workspace, or a candidate file cannot be read) can never show a
        # pass unchanged, so the loop would never end: the start is refused, at both unchanged gates.
        for gate in (2, 3):
            with self.subTest(gate=gate), mock.patch.object(runtime, "_workspace_tree", return_value=None):
                with self.assertRaisesRegex(runtime.StateError, "needs a content tree the runtime can measure"):
                    self.start(gate=gate)
        self.assertNotIn("must be a Git worktree", SCRIPT.read_text())  # a directory outside Git is measured (F3)

    def test_candidate_paths_must_be_absolute_unique_paths(self) -> None:
        for bad, message in (("a.md", "must be a list"), (["a.md"], "absolute file path"),
                             ([str(self.outside), str(self.outside)], "must be unique"), ([""], "nonblank")):
            with self.subTest(bad=bad), self.assertRaisesRegex(runtime.StateError, message):
                self.start(candidate_paths=bad)


class StatCacheTests(LoopCase):
    """A change must never read as "unchanged" (nor the reverse): Git's stat cache is not trusted for the measurement.

    Git trusts a cached entry whose stat data (here: mtime seconds and size, `core.checkStat minimal`) matches and whose
    mtime is older than the index file's.  The runtime measures through a COPY of the index, whose fresh mtime defeats
    Git's racy check, so a same-size edit made within the cached mtime's second went unseen until the runtime marked the
    copy racy.  Seen live in this suite as a pass that "changed" nothing, then "changed" it back, across a second boundary.
    """

    def test_a_same_size_edit_with_the_cached_stat_data_is_still_a_change(self) -> None:
        git(self.repo, "config", "core.checkStat", "minimal")
        old = time.time() - 30
        os.utime(self.repo / "app.py", (old, old))
        git(self.repo, "update-index", "--refresh")  # the index entry now carries that old mtime
        packet = self.start()
        (self.repo / "app.py").write_text("x = 7\n")  # the same six bytes as "x = 1\n"
        os.utime(self.repo / "app.py", (old, old))    # and the same mtime, so the stat data still matches the cache
        active = self.done(packet, TRIVIAL)
        self.assertEqual(active["status"], "active")
        self.assertIs(active["progress"]["last_pass_changed_tree"], True)
        # the same edit, measured again with nothing in between, is unchanged: the measurement is repeatable
        self.assertEqual(self.done(active)["status"], "complete")


class OldShapeIsRefusedTests(LoopCase):
    """(g) One supported version: the retired unchanged-first-pass state and packet key are refused, not read."""

    def test_a_saved_state_from_the_older_runtime_is_refused_with_the_way_forward(self) -> None:
        packet = self.start()
        state = Path(packet["state_file"])
        old = runtime.json.loads(state.read_text())
        old["start_tree"] = old.pop("last_tree")  # the older runtime's field for the tree at start
        del old["last_pass_changed_tree"]
        state.write_text(runtime.json.dumps(old))
        for call in (lambda: runtime.next_packet(state), lambda: runtime.read_state(state),
                     lambda: runtime.done(state, token(packet), TRIVIAL)):
            with self.assertRaisesRegex(runtime.StateError,
                                        r"written by an older Until Loop.*records start_tree.*start a new run"):
                call()

    def test_a_saved_state_without_the_new_fields_is_an_invalid_schema(self) -> None:
        packet = self.start()
        state = Path(packet["state_file"])
        old = runtime.json.loads(state.read_text())
        del old["last_tree"]
        state.write_text(runtime.json.dumps(old))
        with self.assertRaisesRegex(runtime.StateError, "invalid schema"):
            runtime.read_state(state)

    def test_the_old_progress_key_and_the_gate_two_streak_are_gone(self) -> None:
        packet = self.start()
        self.assertEqual(set(packet["progress"]), {"action_number", "required_trivial_reviews", "last_pass_changed_tree"})
        terminal = self.done(packet)
        self.assertEqual(set(terminal["progress"]), {"action_number", "required_trivial_reviews", "last_pass_changed_tree"})
        source = SCRIPT.read_text()
        for retired in ('"unchanged_first_pass"', '"start_tree"'):
            self.assertEqual(source.count(retired), 1 if retired == '"start_tree"' else 0,
                             retired + ": only the refusal of an old state may name start_tree")

    def test_the_contract_can_not_carry_a_gate_above_three_or_a_relative_candidate(self) -> None:
        for extra, message in (({"required_trivial_reviews": 4}, "must be 0, 1, 2 or 3"),
                               ({"candidate_paths": ["rel.md"]}, "absolute file path")):
            with self.subTest(extra=extra), self.assertRaisesRegex(runtime.StateError, message):
                runtime.start(dict(self.contract(), **extra), self.state_dir)

    def contract(self) -> dict:
        return {"workspace": str(self.repo), "work": "w", "exit_condition": "e", "repeat_condition": "r",
                "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e", "resources": []}}


class StopRuleReplayTests(LoopCase):
    """The live Salesforce-chess Improve run (2026-10-16, docs/shiploop-improve-stop-rule-journal-2026-10-16.md).

    Each stage's per-pass facts come from the Improve-value study (21 passes over five stages): the label the model gave
    the pass, and whether it changed the stage's candidate. The stages whose candidate lives outside the worktree
    (plan, step-plan, test-spec results in run/inbox) are replayed by editing a file outside the repo, listed as a
    candidate path, exactly as ShipLoop's contract lists it. Material passes (the study's eight) carry a "material" flag.
    """

    # (label, changed, material) per pass. A "polish" edit (spec P6, test-strategy P3, plan P2) was labelled non-trivial.
    STAGES = {
        "spec": (False, [("non-trivial", True, True)] * 5 + [("non-trivial", True, False)]
                 + [("trivial", False, False)] * 2),
        "test-strategy": (False, [("non-trivial", True, True), ("trivial", False, False), ("non-trivial", True, False),
                                  ("trivial", False, False), ("trivial", False, False)]),
        "plan": (True, [("non-trivial", True, True), ("non-trivial", True, False), ("trivial", False, False),
                        ("trivial", False, False)]),
        "step-plan": (True, [("trivial", False, False)]),
        "test-spec": (True, [("non-trivial", True, True), ("trivial", False, False), ("trivial", False, False)]),
    }
    OBSERVED_PASSES = {"spec": 8, "test-strategy": 5, "plan": 4, "step-plan": 1, "test-spec": 3}
    EXPECTED_STOP = {"spec": 7, "test-strategy": 2, "plan": 3, "step-plan": 1, "test-spec": 2}

    # Where gate 3 (the two-pass rule of ShipLoop's code reviews) would have stopped the same passes: 21 of 21, the count the
    # run actually took, so the two-pass rule gives back none of the saving that gate 2 measured on planning stages.
    EXPECTED_STOP_GATE_3 = {"spec": 8, "test-strategy": 5, "plan": 4, "step-plan": 1, "test-spec": 3}

    def replay(self, outside: bool, passes: list[tuple[str, bool, bool]], stage: str = "stage", gate: int = 2) -> int:
        """Drive the real runtime with these passes; return the pass number the loop completed on (0 if never)."""
        extra = {"candidate_paths": [str(self.outside)]} if outside else {}
        packet = self.start(gate=gate, **extra)
        for number, (label, changed, _material) in enumerate(passes, 1):
            if changed:
                target = self.outside if outside else self.repo / "app.py"
                target.write_text(f"{stage} pass {number} edit\n")  # unique, so no edit repeats earlier content
            packet = self.done(packet, dict(TRIVIAL, classification=label))
            if packet["status"] == "complete":
                return number
        return 0

    def test_each_stage_stops_where_the_study_replayed_it_and_never_before_a_material_pass(self) -> None:
        total_observed = total_replayed = 0
        for stage, (outside, passes) in self.STAGES.items():
            with self.subTest(stage=stage):
                self.assertEqual(len(passes), self.OBSERVED_PASSES[stage])
                stop = self.replay(outside, passes, stage)
                self.assertEqual(stop, self.EXPECTED_STOP[stage])
                changed_before_stop = [n for n, (_l, changed, _m) in enumerate(passes[:stop], 1) if changed]
                self.assertGreaterEqual(stop, (max(changed_before_stop) if changed_before_stop else 0) + 1)
                self.assertFalse(passes[stop - 1][1], "the pass the loop ends on changed nothing")
                material = [n for n, (_l, _c, is_material) in enumerate(passes, 1) if is_material]
                self.assertTrue(all(n < stop for n in material), "every material pass comes before the stop")
                total_observed += self.OBSERVED_PASSES[stage]
                total_replayed += stop
        self.assertEqual((total_observed, total_replayed), (21, 15))

    def test_the_same_passes_under_the_two_pass_gate_stop_where_the_run_actually_stopped(self) -> None:
        for stage, (outside, passes) in self.STAGES.items():
            with self.subTest(stage=stage):
                stop = self.replay(outside, passes, stage, gate=3)
                self.assertEqual(stop, self.EXPECTED_STOP_GATE_3[stage])
                self.assertEqual(stop, self.OBSERVED_PASSES[stage])
                self.assertGreaterEqual(stop, self.EXPECTED_STOP[stage])  # never earlier than gate 2
                self.assertTrue(all(n < stop for n, (_l, _c, material) in enumerate(passes, 1) if material))

    def test_a_polish_edit_labelled_trivial_is_followed_by_another_pass(self) -> None:
        # The old rule would have counted spec P6 (one word changed) toward two clean passes if it were labelled trivial.
        outside, passes = self.STAGES["spec"]
        relabelled = [(("trivial" if n == 6 else label), changed, material)
                      for n, (label, changed, material) in enumerate(passes, 1)]
        self.assertEqual(self.replay(outside, relabelled), 7)  # not 6, however the pass is labelled


class TwoPassGateTests(LoopCase):
    """Gate 3: ShipLoop's implement and carry-forward reviews (efficiency plan D-6 / R1).

    A first pass that is trivial, satisfied and leaves the content as it started completes (the 2026-09-26 rule, 2be7906b).
    Once any pass has changed the content, two consecutive trivial, satisfied passes that each leave it unchanged complete.
    A trivial pass that changed the content never completes, and a pass that is unchanged but unsatisfied (or not trivial)
    breaks the pair.  Gate 2 stops on the first of them.

    The unsatisfied case is stricter than the streak of 2be7906b, which counted a trivial pass whatever its exit (an
    unsatisfied pass then a satisfied one ended at pass 2): an unsatisfied exit says something still remains, so that pass
    is not one of the two.  That is safe only because the frozen exit names no pass count (U2-R1): a contract that said
    "two such passes in a row are needed" made a literal reader report the first clean pass after an edit unsatisfied,
    which delayed the end by a pass (ENN ends at 3, EUNN at 4).  test/shiploop-quality.test.py pins the contract.
    """

    # Each letter is one pass: E = edits the file, reported non-trivial; T = edits the file, reported trivial (the label is
    # not trusted); N = changes nothing, reported trivial and satisfied; U = changes nothing, reported trivial but with the
    # exit unsatisfied.  (passes, the pass gate 2 completes on, the pass gate 3 completes on); 0 = still open afterwards.
    SEQUENCES = (
        ("N", 1, 1),
        ("EN", 2, 0),
        ("ENN", 2, 3),
        ("ENENN", 2, 5),
        ("EEN", 3, 0),
        ("EENN", 3, 4),
        ("TN", 2, 0),
        ("TNN", 2, 3),
        ("TTTT", 0, 0),
        ("UN", 2, 0),
        ("UNN", 2, 3),
        ("ENUNN", 2, 5),
        ("EUN", 3, 0),      # the literal reader's report of the first clean pass after an edit: not a pair at gate 3
        ("EUNN", 3, 4),
    )

    def drive(self, gate: int, passes: str, **extra) -> tuple[int, dict]:
        self.edit("x = 1\n")  # every sequence starts from the committed content
        packet = self.start(gate=gate, **extra)
        for number, mark in enumerate(passes, 1):
            if mark in "ET":
                self.edit(f"x = {number + 1}\n")  # a new content every time, and never the committed "x = 1"
            report = dict(TRIVIAL)
            if mark == "E":
                report["classification"] = "non-trivial"
            if mark == "U":
                report["exit_assessment"] = "unsatisfied"
            packet = self.done(packet, report)
            if packet["status"] == "complete":
                return number, packet
        return 0, packet

    def test_each_sequence_completes_on_the_pass_its_gate_names(self) -> None:
        for passes, at_gate_2, at_gate_3 in self.SEQUENCES:
            for gate, expected in ((2, at_gate_2), (3, at_gate_3)):
                with self.subTest(passes=passes, gate=gate):
                    self.assertEqual(self.drive(gate, passes)[0], expected)

    def test_the_first_pass_rule_is_the_one_main_had_and_gate_two_ends_there_too(self) -> None:
        for gate in (2, 3):
            with self.subTest(gate=gate):
                number, terminal = self.drive(gate, "N")
                self.assertEqual((number, terminal["progress"]), (1, {
                    "action_number": 1, "required_trivial_reviews": gate, "last_pass_changed_tree": False}))

    def test_a_trivial_label_on_a_pass_that_changed_the_content_never_completes(self) -> None:
        for gate in (2, 3):
            with self.subTest(gate=gate):
                number, packet = self.drive(gate, "TTTT")
                self.assertEqual((number, packet["status"]), (0, "active"))
                self.assertIs(packet["progress"]["last_pass_changed_tree"], True)

    def test_a_candidate_file_edit_alone_counts_as_a_change_at_gate_three(self) -> None:
        packet = self.start(gate=3, candidate_paths=[str(self.outside)])
        self.outside.write_text("result v1\n")                  # absent -> present, the worktree untouched
        packet = self.done(packet, MATERIAL)
        packet = self.done(packet)                              # one unchanged pass after a change is not enough at gate 3
        self.assertEqual(packet["status"], "active")
        self.assertEqual(self.done(packet)["status"], "complete")
        # the same run without the edit completes on its first pass
        self.assertEqual(self.done(self.start(gate=3, candidate_paths=[str(self.outside)]))["status"], "complete")

    def test_a_then_b_then_a_trees_is_not_clean_at_gate_three(self) -> None:
        packet = self.start(gate=3)
        self.edit("x = 2\n")                                    # tree B
        packet = self.done(packet, MATERIAL)
        self.edit("x = 1\n")                                    # back to the start tree A: a change against B
        packet = self.done(packet, TRIVIAL)
        self.assertEqual((packet["status"], packet["progress"]["last_pass_changed_tree"]), ("active", True))
        packet = self.done(packet)                              # the first unchanged pass since
        self.assertEqual(packet["status"], "active")
        self.assertEqual(self.done(packet)["status"], "complete")

    def test_failed_checks_on_an_unchanged_pass_break_the_pair(self) -> None:
        checks = [{"id": "C1", "clause": "the suite passes", "command": "false"}]
        passed = io.BytesIO  # one recorded run per pass, the way the packet's verify_script reports it
        ok = b"=== until-loop check C1\n\nUNTIL-LOOP-CHECK C1 exit=0\n"
        packet = self.start(gate=3, exit_checks=checks)
        self.edit()
        runtime.record(packet["state_file"], token(packet), passed(ok), io.StringIO())
        packet = self.done(packet, MATERIAL)                    # pass 1 changed the content
        runtime.record(packet["state_file"], token(packet), passed(ok), io.StringIO())
        packet = self.done(packet, TRIVIAL)                     # pass 2: unchanged, checks pass: the first of the pair
        self.assertEqual(packet["status"], "active")
        runtime.record(packet["state_file"], token(packet),
                       io.BytesIO(b"=== until-loop check C1\nboom\n\nUNTIL-LOOP-CHECK C1 exit=1\n"), io.StringIO())
        packet = self.done(packet, TRIVIAL)                     # pass 3: unchanged but a check failed: not a pair
        self.assertEqual(packet["status"], "active")
        runtime.record(packet["state_file"], token(packet),
                       io.BytesIO(b"=== until-loop check C1\n\nUNTIL-LOOP-CHECK C1 exit=0\n"), io.StringIO())
        packet = self.done(packet, TRIVIAL)                     # pass 4: the first clean pass since the failure
        self.assertEqual(packet["status"], "active")
        runtime.record(packet["state_file"], token(packet),
                       io.BytesIO(b"=== until-loop check C1\n\nUNTIL-LOOP-CHECK C1 exit=0\n"), io.StringIO())
        self.assertEqual(self.done(packet, TRIVIAL)["status"], "complete")  # pass 5: the second

    def test_cancelled_and_blocked_still_stop_a_gate_three_loop(self) -> None:
        for fields in ({"continuation_assessment": "cancelled"},
                       {"continuation_assessment": "blocked", "exit_assessment": "unsatisfied"}):
            with self.subTest(fields=fields):
                self.assertEqual(self.done(self.start(gate=3), dict(MATERIAL, **fields))["status"], "stopped")

    def test_the_packets_say_which_pass_ends_the_loop(self) -> None:
        packet = self.start(gate=3)
        self.assertEqual(packet["progress"], {"action_number": 1, "required_trivial_reviews": 3,
                                              "last_pass_changed_tree": None})
        self.assertIn("After a pass has changed the content it takes two such passes in a row", packet["instruction"])
        self.assertNotIn("two such passes in a row", self.start(gate=2)["instruction"])
        self.edit()
        changed = self.done(packet, TRIVIAL)                    # labelled trivial, but it edited: the runtime says why not
        self.assertIn("ends on two consecutive passes you report trivial and satisfied", changed["instruction"])
        one_clean = self.done(changed)
        self.assertEqual(one_clean["status"], "active")
        self.assertIn("one more distinct full review", one_clean["instruction"])
        terminal = self.done(one_clean)
        self.assertEqual(terminal["status"], "complete")
        self.assertIn("also trivial and satisfied with the content unchanged", terminal["instruction"])
        self.assertEqual(set(terminal["progress"]), {"action_number", "required_trivial_reviews", "last_pass_changed_tree"})
        self.assertIs(terminal["progress"]["last_pass_changed_tree"], False)
        # the first-pass completion keeps the gate-2 wording: nothing before it changed the content
        first = self.done(self.start(gate=3))
        self.assertIn("unchanged from the previous pass", first["instruction"])
        self.assertNotIn("also trivial and satisfied", first["instruction"])

    def test_no_new_state_field_keeps_the_two_pass_gate_inside_the_gate_two_state_shape(self) -> None:
        # The pair is read from the latest report, trivial_streak and last_pass_changed_tree, so a gate-3 run adds no field.
        two, three = Path(self.start(gate=2)["state_file"]), Path(self.start(gate=3)["state_file"])
        self.assertEqual(set(runtime.json.loads(two.read_text())), set(runtime.json.loads(three.read_text())))


class PlainDirectoryTests(LoopCase):
    """F3: a workspace that is not a Git worktree (an explicit in-place ShipLoop run) is measured like one.

    The unchanged-content gates measure the workspace through a throwaway bare repository, so the same rule applies and
    nothing is written into the workspace.  The measurement honours .gitignore files in the directory, like the Git case.
    """

    def plain(self) -> Path:
        directory = self.root / "plain"
        directory.mkdir()
        (directory / "doc.md").write_text("# Notes\n")
        return directory

    @staticmethod
    def listing(directory: Path) -> list[str]:
        return sorted(str(path.relative_to(directory)) for path in directory.rglob("*"))

    def test_a_start_outside_git_is_accepted_and_an_unchanged_trivial_pass_completes(self) -> None:
        for gate in (2, 3):
            with self.subTest(gate=gate):
                plain = self.plain() if gate == 2 else self.root / "plain"
                packet = self.start(gate=gate, workspace=plain)
                self.assertEqual(packet["status"], "active")
                self.assertEqual(self.done(packet)["status"], "complete")

    def test_a_change_outside_git_is_a_change_and_the_next_unchanged_pass_ends_the_loop(self) -> None:
        plain = self.plain()
        packet = self.start(workspace=plain)
        (plain / "doc.md").write_text("# Notes\nA new line.\n")
        packet = self.done(packet, TRIVIAL)
        self.assertEqual((packet["status"], packet["progress"]["last_pass_changed_tree"]), ("active", True))
        (plain / "added.md").write_text("new file\n")
        packet = self.done(packet, TRIVIAL)
        self.assertEqual((packet["status"], packet["progress"]["last_pass_changed_tree"]), ("active", True))
        self.assertEqual(self.done(packet)["status"], "complete")

    def test_ignored_and_runtime_files_outside_git_do_not_count_and_nothing_is_written_into_the_directory(self) -> None:
        plain = self.plain()
        (plain / ".gitignore").write_text("build/\n")
        before = self.listing(plain)
        packet = self.start(workspace=plain)
        (plain / "build").mkdir()
        (plain / "build" / "out.txt").write_text("ignored output\n")
        (plain / ".shiploop-improve").mkdir()
        (plain / ".shiploop-improve" / "review-1.md").write_text("review\n")
        terminal = self.done(packet)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(sorted(set(self.listing(plain)) - set(before)),
                         [".shiploop-improve", ".shiploop-improve/review-1.md", "build", "build/out.txt"])
        self.assertFalse((plain / ".git").exists(), "the throwaway repository lives elsewhere")

    def test_a_candidate_file_outside_a_plain_directory_counts_too(self) -> None:
        plain = self.plain()
        packet = self.start(workspace=plain, candidate_paths=[str(self.outside)])
        self.outside.write_text("result v1\n")
        packet = self.done(packet, TRIVIAL)
        self.assertEqual((packet["status"], packet["progress"]["last_pass_changed_tree"]), ("active", True))
        self.assertEqual(self.done(packet)["status"], "complete")

    def test_the_measurement_is_repeatable_and_leaves_no_temporary_repository_behind(self) -> None:
        plain = self.plain()
        scratch = Path(tempfile.gettempdir())
        before = {path.name for path in scratch.glob("until-loop-tree-*")}
        first, second = runtime._workspace_tree(str(plain)), runtime._workspace_tree(str(plain))
        self.assertRegex(first, r"^[0-9a-f]{40}$")
        self.assertEqual(first, second)
        (plain / "doc.md").write_text("# Notes\nchanged\n")
        self.assertNotEqual(runtime._workspace_tree(str(plain)), first)
        self.assertEqual({path.name for path in scratch.glob("until-loop-tree-*")}, before)

    def test_a_temporary_directory_inside_the_workspace_is_not_part_of_the_tree(self) -> None:
        # Review finding (P2): with TMPDIR inside the measured workspace the throwaway repository, or in a worktree the
        # temporary index file, was part of the tree it measured, so no pass could ever read as unchanged.
        for kind in ("plain", "worktree"):
            with self.subTest(kind=kind):
                workspace = self.plain() if kind == "plain" else self.repo
                scratch = workspace / "tmp"
                scratch.mkdir(exist_ok=True)
                with mock.patch.object(tempfile, "tempdir", str(scratch)):
                    first, second = runtime._workspace_tree(str(workspace)), runtime._workspace_tree(str(workspace))
                    self.assertIsNotNone(first)
                    self.assertEqual(first, second)
                    packet = self.start(workspace=workspace)
                    self.assertEqual(self.done(packet)["status"], "complete")
                self.assertEqual(list(scratch.iterdir()), [], "the measurement removes its own scratch")

    def test_a_directory_git_cannot_snapshot_is_still_refused_at_start(self) -> None:
        if os.geteuid() == 0:
            self.skipTest("root reads an unreadable file")
        plain = self.plain()
        locked = plain / "locked.md"
        locked.write_text("secret\n")
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o600)
        with self.assertRaisesRegex(runtime.StateError, "needs a content tree the runtime can measure"):
            self.start(workspace=plain)


# --------------------------------------------------------------------------------------------------------------------
class OnePassGateTests(unittest.TestCase):
    """The gate the plan packet prints for the Backchain child, started on the real runtime.

    The packet text, not a constant in this test, supplies the gate: a host copies the printed
    `required_trivial_reviews` into the child's start contract, so that is the value driven here.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="one-pass-gate-")
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name).resolve() / "plan"
        self.state_dir = Path(temp.name).resolve() / "state"
        self.workspace.mkdir()
        self.state_dir.mkdir()
        git(self.workspace, "init", "-q")
        git(self.workspace, "config", "user.email", "r@example.invalid")
        git(self.workspace, "config", "user.name", "R")
        (self.workspace / "candidate.json").write_text("{}\n")
        git(self.workspace, "add", "-A")
        git(self.workspace, "commit", "-qm", "base")

    @staticmethod
    def printed(mode: str) -> tuple[int, str]:
        """The gate, and the verbatim exit condition when the packet prints one, from the plan packet of `mode`."""
        text = " ".join(prompts._backchain_guidance("plan", backchain_passes=mode).split())
        gates = re.findall(r"`required_trivial_reviews: (\d+)`", text)
        assert len(gates) == 1, (mode, gates)
        exit_text = re.search(r"verbatim, appending only case-specific clauses: (.+?)\. A pass that completes", text)
        return int(gates[0]), (exit_text.group(1) if exit_text else "Two consecutive reviews find nothing to change.")

    def start(self, mode: str) -> dict:
        gate, exit_condition = self.printed(mode)
        contract = {"workspace": str(self.workspace), "work": "One dependency review/fix/check cycle.",
                    "exit_condition": exit_condition, "repeat_condition": "Repeat for a named open gap.",
                    "required_trivial_reviews": gate,
                    "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e",
                                "resources": []}}
        return runtime.start(contract, self.state_dir)

    @staticmethod
    def report(packet: dict, **fields: str) -> dict:
        report = dict(TRIVIAL, **fields)
        return runtime.done(packet["state_file"], token(packet), report)

    def test_the_one_pass_text_prints_gate_zero_and_the_converge_text_prints_two(self) -> None:
        self.assertEqual(self.printed("one")[0], 0)
        self.assertEqual(self.printed("converge")[0], 2)

    def test_a_repairing_first_pass_that_assesses_the_exit_satisfied_completes_after_one_action(self) -> None:
        packet = self.start("one")
        self.assertEqual(packet["progress"]["required_trivial_reviews"], 0)
        terminal = self.report(packet, classification="non-trivial", exit_assessment="satisfied")
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"]["action_number"], 1)
        self.assertEqual(terminal["progress"]["trivial_streak"], 0)

    def test_an_unsatisfied_report_continues_and_the_next_satisfied_report_completes(self) -> None:
        packet = self.start("one")
        active = self.report(packet, classification="non-trivial", exit_assessment="unsatisfied")
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["progress"]["action_number"], 2)  # no ceiling: the open gap keeps the loop going
        terminal = self.report(active, classification="trivial", exit_assessment="satisfied")
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"]["action_number"], 2)

    def test_an_unresolved_report_cannot_claim_a_satisfied_exit(self) -> None:
        packet = self.start("one")
        with self.assertRaisesRegex(runtime.StateError, "unresolved report cannot claim a satisfied exit"):
            self.report(packet, classification="unresolved", exit_assessment="satisfied")
        # the refusal changed nothing: the same action still takes a valid report
        self.assertEqual(self.report(packet, classification="trivial", exit_assessment="satisfied")["status"],
                         "complete")

    def test_a_blocked_report_stops_the_loop(self) -> None:
        # A runtime pin (the SPEC's "a blocker ends the loop as before"): it holds at any printed gate, so it
        # shows the stop route stays open under gate 0, not that the packet text changed.
        packet = self.start("one")
        stopped = self.report(packet, classification="unresolved", exit_assessment="unsatisfied",
                              continuation_assessment="blocked")
        self.assertEqual(stopped["status"], "stopped")

    def test_the_converge_gate_printed_in_the_packet_is_the_unchanged_content_gate(self) -> None:
        packet = self.start("converge")
        (self.workspace / "candidate.json").write_text('{"repaired": true}\n')
        active = self.report(packet, classification="non-trivial", exit_assessment="satisfied")
        self.assertEqual(active["status"], "active")
        (self.workspace / "candidate.json").write_text('{"repaired": "again"}\n')
        active = self.report(active, classification="trivial", exit_assessment="satisfied")
        self.assertEqual(active["status"], "active")  # a trivial label on a pass that edited the plan does not end it
        self.assertEqual(self.report(active, classification="trivial", exit_assessment="satisfied")["status"],
                         "complete")


if __name__ == "__main__":
    unittest.main()
