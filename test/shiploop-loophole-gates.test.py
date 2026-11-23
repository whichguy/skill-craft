#!/usr/bin/env python3
"""Known dodges of ShipLoop's result gates, each sent through the real CLI (owner, 2026-10-24).

``DODGES`` is one table. Each row is a way a model has met a gate's letter but not its purpose, in a live run or in the
template experiments. Each row:
1. builds the dodge from the stage's own done template;
2. submits it with the printed callback, and asserts the refusal;
3. submits the refusal's named next step with the same callback, and asserts it is accepted ("test the route, not the
   wording").

Rule (the run-5 batch, 2026-10-24): a new structured result field or gate adds its known-dodge row here, in the same
commit.

Not a dodge, so not here:
- A search of a code file for its contract docstring, confirmed `searched`. Step-plan duty 3 asks for that criterion
  (Code craft 2-3), and the template experiments' E2 samples did exactly that.
- A test of new code that fails to load on the item's base (``require`` of the module the item adds). That is a real
  failure, and ShipLoop reads it as RED.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("shiploop_callback_contract",
                                               ROOT / "test" / "shiploop-callback-contract.test.py")
contract = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = contract
_SPEC.loader.exec_module(contract)
_IMPROVE = importlib.util.spec_from_file_location("shiploop_actual_improve_cli",
                                                  ROOT / "test" / "shiploop-actual-improve-cli.test.py")
improve_cli = importlib.util.module_from_spec(_IMPROVE)
sys.modules[_IMPROVE.name] = improve_cli
_IMPROVE.loader.exec_module(improve_cli)

_NOTES = importlib.util.spec_from_file_location("shiploop_owner_notes_suite", ROOT / "test" / "shiploop-owner-notes.test.py")
notes_suite = importlib.util.module_from_spec(_NOTES)
sys.modules[_NOTES.name] = notes_suite
_NOTES.loader.exec_module(notes_suite)

FOCUSED = contract.FOCUSED
# A test-strategy target that keeps state between runs (F3), named by the rows that need one.
STATEFUL = {"target": "the shared service", "keeps_state": "yes", "base_state_route": "a clean namespace per run"}
# An unverified outcome of the spec's primary requirement R-1 (F6), and the add-work its refusal names.
PRIMARY_RUN = {"spec": {"primary": ["R-1"]}}
PRIMARY_ROW = dict(contract.UNVERIFIED_ENTRY, requirement="R-1", outcome="a person sees the built file's text",
                   lower_layer_check="the reviewer read the page")
# A test-strategy row whose harness prepare sets up (F1), so prepare's done result owes its harness_runs entry.
PREREQUISITE_RUN = {"test-strategy": {"test_layers": [
    dict(contract.RESULTS["test-strategy"]["test_layers"][0], status="prerequisite",
         reason="prepare sets up the shell harness")]}}
# A follow-on entry the handoff cites to the release-verify lessons, which every positioned run holds.
FOLLOW_ON_ENTRY = {"class": "gap", "statement": "The export exits 0 on an unreadable file.",
                   "source": "lessons.open_next", "request_sentence": "", "needs": "a work item that fixes the exit code"}
DEFAULT_ENTRY = contract.DEFAULT_ENTRY   # a choice the spec made (shiploop_defaults), stated by the fixture's R-1
ADD_TEST = {"outcome": "add-work", "summary": "Add the unit test that shows R-1's logic works.",
            "headline": "R-1 needs a lower-layer test.",
            "work_items": [{"id": "W2", "title": "Add a unit test of R-1's logic",
                            "context": "R-1 is primary and no unit or component test of it passed."}]}


def probe_evidence(block: dict) -> dict:
    """``block`` whose harness_runs evidence is a page beside the real output that shows no test (run 5a's probe)."""
    return {**block, "harness_runs": [dict(row, evidence=str(Path(row["evidence"]).with_name("probe.html")))
                                      for row in block["harness_runs"]]}


def commands(block: dict, change) -> dict:
    """``block`` with ``change`` applied to each of its test_commands rows (a copy)."""
    return {**block, "test_commands": [change(dict(row)) for row in block["test_commands"]]}


def focused(change):
    """A test_commands change that applies ``change`` to the focused rows only."""
    return lambda row: change(row) if row.get("suite") == "focused" else row


def guarded(prefix: str):
    """A dodge that puts ``prefix`` ahead of the focused command's tests."""
    return lambda block: commands(block, focused(lambda row: dict(row, command=prefix + row["command"])))


def targets(rows: list):
    """A test-strategy block whose targets are ``rows``."""
    return lambda block: {**block, "targets": rows}


# (label, where it was seen, stage, positioning results, dodge, refusal fragment, named exit). Each callable takes the
# stage's filled done template and returns a result block.
DODGES = [
    ("an executed criterion confirmed only by a search of the code",
     "run 4's source-grep confirmations (F1)", "step-plan", None,
     lambda block: commands(block, lambda row: dict(row, command="grep -q 'def build' src/build.py")
                            if row.get("criteria") else row),
     "every command naming them only searches text",
     lambda block: block),            # the named exit: a command that runs the code names the criterion
    ("a focused command behind a test -f guard", "run 4's W3 (F2)", "step-plan", None,
     guarded("test -f built.txt && "), "checks for a file or prints a path before its tests run", lambda block: block),
    ("a focused command behind an if-[ ! -e ] guard that prints a fake load error",
     "E3's smoke sample (F2)", "step-plan", None,
     guarded("if [ ! -e built.txt ]; then echo 'Error: Cannot find module built.txt'; exit 1; fi; "),
     "checks for a file or prints a path before its tests run", lambda block: block),
    ("a focused command that prints a path before its tests", "run 4's W3 printf guard (F2)", "step-plan", None,
     guarded("printf '%s\\n' built.txt && "),
     "checks for a file or prints a path before its tests run", lambda block: block),
    ("a target that keeps state with no base-state route", "run 4's W2 remote base run (F1, F3)", "test-strategy", None,
     targets([dict(STATEFUL, base_state_route="n/a")]),
     "keeps state between runs, so base_state_route says how a test still fails",
     targets([STATEFUL])),
    ("a test command naming a target that is no targets row", "F3", "step-plan", None,
     lambda block: commands(block, focused(lambda row: dict(row, target="the shared service"))),
     "which is no test-strategy targets row",
     lambda block: block),            # the named exit: leave target out for a command that runs on the checkout
    ("harness evidence that shows no test running", "run 5a's prepare browser probe (F1)", "prepare", PREREQUISITE_RUN,
     probe_evidence, "shows no test run ShipLoop can read",
     lambda block: block),            # the named exit: the runner's own output of one test it ran
    ("an unverified primary outcome whose lower-layer check is a person's reading", "run 4's product-acceptance (F6)",
     "product-acceptance", PRIMARY_RUN, lambda block: {**block, "unverified": [PRIMARY_ROW]},
     "a primary requirement (spec primary), and its lower_layer_check names no test",
     lambda block: dict(ADD_TEST, evidence_refs=block["evidence_refs"])),   # the named exit: add the missing test
    ("an unverified outcome settled in prose with the list left out", "hello's release-verify on 2.13.2 (E2E trio)",
     "release-verify", {"product-acceptance": {"unverified": [dict(contract.UNVERIFIED_ENTRY, due_stage="release-verify")]}},
     lambda block: {key: value for key, value in block.items() if key != "unverified"},
     "a done release-verify result restates unverified",
     lambda block: {**block, "unverified": [dict(row, due_stage="handoff") for row in block["unverified"]]}),
     # The named exit: restate and defer the still-unobserved reader outcome; no settlement is claimed.
    # The follow-on list (design 4.4): not seen in a live run yet, so the rows name the design's mechanical checks.
    ("a follow-on gap that maps to no sentence of the request", "the follow-on design, 4.4 (no live run yet)",
     "handoff", None, lambda block: {**block, "follow_on": [FOLLOW_ON_ENTRY]},
     "a gap maps to a sentence of the request",
     lambda block: {**block, "follow_on": [dict(FOLLOW_ON_ENTRY, **{"class": "decision"})]}),   # a leftover that maps to none is a decision
    ("a follow-on entry whose source is a commit typed from memory", "the follow-on design, 4.4 (no live run yet)",
     "handoff", None, lambda block: {**block, "follow_on": [dict(FOLLOW_ON_ENTRY, **{"class": "note"},
                                                                 source="commit:0123abc")]},
     "names no commit in this repository",
     lambda block: {**block, "follow_on": [dict(FOLLOW_ON_ENTRY, **{"class": "note"})]}),       # cite a record the run holds
    # The defaults list (its design, 2.3): not seen in a live run yet, so the rows name the design's mechanical checks.
    ("a default left as the template's row with one text filled in", "the defaults design, 2.3 (no live run yet)",
     "spec", None, lambda block: {**block, "defaults": [dict(contract.nav.defaults.TEMPLATE_ROW, requirement="R-1")]},
     "still holds the template placeholder",
     lambda block: {**block, "defaults": []}),              # the named exit: delete the row when nothing was chosen
    ("a default that names a requirement the spec does not hold", "the defaults design, 2.3 (no live run yet)",
     "spec", None, lambda block: {**block, "defaults": [dict(DEFAULT_ENTRY, requirement="R-7")]},
     "has no current entry in",
     lambda block: {**block, "defaults": [DEFAULT_ENTRY]}),   # the named exit: name the R-<n> that carries the answer
]

# improve-commit dodges (F5): (label, where it was seen, the files the fix touches, the message, refusal fragment, the
# message of the named exit).  Each runs at the end-of-work review, whose commit owes the Regression test line.
REGRESSION_TEST = "from src.calc import calc\n\ndef test_calc_rejects_zero():\n    assert calc(0) == 0\n"
COMMIT_DODGES = [
    ("an end-of-work code fix committed with no regression test", "run 4's Improve fixes (F5)", None,
     "fix: guard zero\n\nKey learnings: zero needs a guard.\n", "this commit has no test file",
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: none: the guard only logs\n"),
    ("a regression line naming a test the commit does not hold", "F5", REGRESSION_TEST,
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: test_somewhere_else\n",
     "no test file in this commit holds test_somewhere_else",
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: test_calc_rejects_zero\n"),
    ("a regression line of none with no reason", "F5", None,
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: none:\n",
     "Regression test: none: <why no test can show this fix>",
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: none: the guard only logs\n"),
]


class LoopholeGateTests(contract.RealCliCase):
    def test_each_known_dodge_is_refused_and_its_named_exit_is_accepted(self) -> None:
        for label, seen, stage, positioning, dodge, fragment, exit_route in DODGES:
            with self.subTest(label, seen=seen):
                run, head = self.new_run(stage, results=positioning)
                command, path, action = contract.printed_callback(head)
                good = self.fill_done(head)
                if stage == "release-verify":
                    template = contract.store.loads(head.split("Result template:\n", 1)[1]
                                                    .split("\nAllowed outcomes:", 1)[0])
                    good["unverified"] = template["unverified"]
                    self.assertEqual(good["unverified"],
                                     contract.nav.unverified.current_list(self.state(run))[2])
                contract.write_block(path, dodge(good))
                self.assertIn(fragment, self.refused(command, run))
                route = exit_route(good)
                contract.write_block(path, route)
                # A stage that closes the knowledge home names its files first (the contract suite's own helper).
                contract.RefusalRouteTests.accept_after_the_knowledge_files(self, command, run)
                self.assertEqual(self.recorded(run, action)["outcome"], route["outcome"])
                if stage == "release-verify":
                    recorded = self.recorded(run, action)
                    self.assertEqual(recorded["unverified"],
                                     [dict(row, due_stage="handoff")
                                      for row in positioning["product-acceptance"]["unverified"]])
                    self.assertEqual(recorded["settled"], [])

    def test_every_row_names_where_it_was_seen_and_a_refusal_it_expects(self) -> None:
        labels = [row[0] for row in DODGES]
        self.assertEqual(len(labels), len(set(labels)))
        for label, seen, stage, _positioning, _dodge, fragment, _exit in DODGES:
            with self.subTest(label):
                self.assertIn(stage, contract.EXPECTED_STAGES)
                self.assertTrue(seen.strip() and fragment.strip())


class CommitDodgeTests(improve_cli.ImproveCliFixture):
    """The improve-commit dodges, with the actual-improve-cli suite's commit fixture (its helpers, not its tests)."""

    for _name in ("_write_producer", "_start_parent", "git", "begin", "write", "refused", "line_one", "named_exit",
                  "run_named", "head_message", "code_change"):
        locals()[_name] = getattr(improve_cli.ImproveCommitContractTests, _name)
    del _name

    def setUp(self):
        improve_cli.ImproveCliFixture.setUp(self)
        self.environment["HOME"] = str(self.base / "home")

    def check_commit_dodge(self, label, seen, test_text, message, fragment, exit_message) -> None:
        self.begin("reflect-and-revise", producer_extra=improve_cli.END_OF_WORK)
        self.code_change(test_text)
        self.write(message)
        refusal = self.refused()
        self.assertIn(fragment, self.line_one(refusal), label + " (" + seen + ")")
        before = self.git("rev-parse", "HEAD").strip()
        self.write(exit_message)
        self.run_named(refusal)
        self.assertNotEqual(before, self.git("rev-parse", "HEAD").strip())
        self.assertIn(exit_message.rsplit("\n", 2)[-2], self.head_message())


# The known ways round the owner-notes gate (its design, section 3): each passes, and the fixture shows what passes and
# where the requester can still see it.  (label, the design's row, the fixture's method.)
NOTE_WAYS_ROUND = [
    ("a row says applied or already and the work does not do it",
     "Passes. The stage's review, where it has one, and the report, which shows the words beside the row, are the checks",
     "row_the_work_does_not_bear_out"),
    ("a row says declined for a poor reason", "Passes. The requester reads the reason", "declined_for_a_poor_reason"),
    ("reflect-and-revise names an item that does something else, or a later reflect-and-revise drops or rewrites the item",
     "Passes. The report says whether the item was completed, queued or dropped", "item_dropped_later"),
    ("a rewind reruns the stage that applied a note and the rerun undoes it", "Passes. The row stands",
     "rewind_after_applied"),
    ("the host never records what the user said as a note", "Nothing happens", "never_recorded"),
    ("a note is written in the instant between the last read at handoff and the save",
     "The note command has already said \"written\"; the report does not hold it", "note_after_the_last_read"),
]
SAID = "Name the output file out.txt, not built.txt."


class NoteWaysRoundTests(notes_suite.NoteRun):
    """Each known way round the owner-notes gate passes; the fixture pins what passes and what the requester is shown."""

    def test_the_table_has_one_row_for_each_way_round_the_design_names(self) -> None:
        design = (ROOT / "docs/experiments/ratchet-pilot-20261120/shiploop-notes/DESIGN.md").read_text(encoding="utf-8")
        section = design.split("## 3. Known ways round", 1)[1].split("\n## 4.", 1)[0]
        named = [line.split("|")[2].strip() for line in section.splitlines()
                 if line.startswith("| ") and not line.startswith("| Way round") and not line.startswith("| ---")]
        self.assertEqual([row[1] for row in NOTE_WAYS_ROUND], named)

    def report(self, run) -> str:
        done = self.cli("report", "--run-dir", str(run))
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def row_the_work_does_not_bear_out(self) -> None:
        run, _head = self.new_run("research")
        self.note(run, SAID)
        head = self.next(run)
        untrue = notes_suite.row(did="already", detail="The research already names the output file.")
        self.accept(head, self.result(head, untrue))   # the run still builds built.txt: nothing checks the product
        report = self.report(run)
        self.assertIn("<pre>" + SAID + "</pre>", report)
        self.assertIn("The research already names the output file.", report)

    def declined_for_a_poor_reason(self) -> None:
        run, _head = self.new_run("discovery")
        self.note(run, SAID)
        head = self.next(run)
        self.accept(head, self.result(head, notes_suite.row(did="declined", detail="Not now.")))
        self.assertIn("<td>declined</td><td>Not now.</td>", self.report(run))

    def item_dropped_later(self) -> None:
        run, _head = self.new_run("prepare", results=notes_suite.THREE_ITEMS)
        self.walk(run, self.at("reflect-and-revise", "W1"), results=notes_suite.THREE_ITEMS)
        self.note(run, SAID)
        head = self.next(run)
        # W3 is an item that does something else entirely: the row passes, as the design says.
        self.accept(head, self.result(head, notes_suite.row(did="applied", detail="W3 renames the file", item="W3")))
        self.walk(run, self.at("reflect-and-revise", "W2"), results=notes_suite.THREE_ITEMS)
        state = self.state(run)
        action = contract.nav.current_action(state)["id"]
        state = contract.nav.apply(state, action, {**contract.DONE, **contract.RESULTS["reflect-and-revise"],
                                                   "work_items": []})   # the later reflect-and-revise drops W3
        if state.get("active_improve") is not None:     # W2 is now the last item: its review, synthetic here
            state = contract.nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        contract.nav.save(run, state)
        self.assertIn("<td>W3 (no longer in the queue)</td>", self.report(run))

    def rewind_after_applied(self) -> None:
        run, _head = self.new_run("step-plan")
        self.note(run, SAID)
        head = self.next(run)
        self.walk(run, self.at("test"), rows={"step-plan": [notes_suite.row(did="applied", detail="S1 writes out.txt")]})
        state = self.state(run)
        contract.nav.save(run, contract.nav.apply(state, contract.nav.current_action(state)["id"], {
            "outcome": "send-back", "summary": "The step plan's command is wrong."}))
        head = self.next(run)
        self.assertEqual(self.owes(head), [])          # the rerun owes no row: the applied row stands
        rerun = self.result(head)                      # built.txt exists now: the rerun's plan says it works
        rerun["expectations"] = [dict(contract.STEP_PLAN["expectations"][0], state="works", statement="built.txt exists.",
                                      check="test -f built.txt")]
        self.accept(head, rerun)
        ledger = contract.nav.owner_notes.ledger(self.state(run))
        self.assertEqual([entry["did"] for entry in ledger["N1"]], ["applied"])

    def never_recorded(self) -> None:
        run, head = self.new_run("spec")
        self.assertNotIn("Owner notes", head)
        self.accept(head, self.result(head))
        self.assertFalse((run / contract.nav.owner_notes.DIR).exists())

    def note_after_the_last_read(self) -> None:
        run, head = self.new_run("handoff")
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.result(head))
        real = contract.nav.accept_effects

        def the_owner_writes_before_the_save(*args, **kwargs):
            contract.nav.owner_notes.write(run, SAID)    # after the second read, before the final save
            return real(*args, **kwargs)
        with notes_suite.mock.patch.object(contract.nav, "accept_effects", the_owner_writes_before_the_save):
            code, out, err = notes_suite.run_main(notes_suite.shlex_split(command)[2:])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.state(run)["status"], "done")
        # The run ended without a stage reading N1; what the requester sees of it depends on whether its file was
        # there when the done packet and the report were written (here it was).
        self.assertIn("- N1: not accounted for: no stage's result has a row for it", out)
        self.assertIn("<p>Not accounted for: no stage's result has a row for it.</p>", self.report(run))


for _index, (_label, _said, _method) in enumerate(NOTE_WAYS_ROUND, 1):
    setattr(NoteWaysRoundTests, f"test_way_round_{_index}_passes_as_the_design_says",
            lambda self, method=_method: getattr(self, method)())
del _index, _label, _said, _method


# One test per commit dodge: each needs a fresh repository and run, which the fixture gives per test.
for _index, _row in enumerate(COMMIT_DODGES, 1):
    setattr(CommitDodgeTests, "test_commit_dodge_" + str(_index) + "_is_refused_and_its_named_exit_commits",
            lambda self, row=_row: self.check_commit_dodge(*row))
del _index, _row


if __name__ == "__main__":
    unittest.main()
