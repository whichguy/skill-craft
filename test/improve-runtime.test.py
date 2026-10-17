#!/usr/bin/env python3
"""Improve's bundled Until Loop runtime: the review gates Improve, ShipLoop and the Backchain packet rely on.

Owner decision 2026-10-16 (Improve-value study, docs/shiploop-improve-stop-rule-journal-2026-10-16.md). Gate 2
(`required_trivial_reviews: 2`, the unchanged-content gate) completes a loop on ONE pass that the report calls trivial and
satisfied, whose checks passed, and after which the runtime measures the content tree equal to the tree after the
previous pass (for the first pass: the tree at start). A pass that changed the tree never completes the loop, however
it is labelled. This generalises the 2026-09-26 unchanged-first-pass rule from the first pass to any pass; it replaces
the two-consecutive-trivial streak at gate 2. There is no count and no timer. Gates 0 and 1 are unchanged, so contracts
written for the published until-loop plugin (ShipLoop's inner-stage loops, Backchain) stay valid.

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
        with self.assertRaisesRegex(runtime.StateError, "must be 0, 1 or 2.*no longer counts that many reviews"):
            runtime.start(dict(contract, required_trivial_reviews=3), self.state_dir)

    def test_the_unchanged_gate_needs_a_tree_it_can_measure(self) -> None:
        plain = self.root / "plain"
        plain.mkdir()
        with self.assertRaisesRegex(runtime.StateError, "needs a content tree the runtime can measure"):
            self.start(workspace=plain)
        self.assertEqual(self.start(gate=1, workspace=plain)["status"], "active")  # the other gates need no Git

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

    def test_the_contract_can_not_carry_a_gate_above_two_or_a_relative_candidate(self) -> None:
        for extra, message in (({"required_trivial_reviews": 4}, "must be 0, 1 or 2"),
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

    def replay(self, outside: bool, passes: list[tuple[str, bool, bool]], stage: str = "stage") -> int:
        """Drive the real runtime with these passes; return the pass number the loop completed on (0 if never)."""
        extra = {"candidate_paths": [str(self.outside)]} if outside else {}
        packet = self.start(**extra)
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

    def test_a_polish_edit_labelled_trivial_is_followed_by_another_pass(self) -> None:
        # The old rule would have counted spec P6 (one word changed) toward two clean passes if it were labelled trivial.
        outside, passes = self.STAGES["spec"]
        relabelled = [(("trivial" if n == 6 else label), changed, material)
                      for n, (label, changed, material) in enumerate(passes, 1)]
        self.assertEqual(self.replay(outside, relabelled), 7)  # not 6, however the pass is labelled


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
