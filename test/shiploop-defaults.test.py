#!/usr/bin/env python3
"""The defaults list: the answers a specification chose where the request does not say, recorded once and shown.

Design: docs/experiments/ratchet-pilot-20261120/shiploop-defaults/DESIGN.md.  The spec's done result carries
``defaults``, a list of entries {requirement, question, default, alternative, why}.  ShipLoop refuses only mechanical
faults (a missing list, an entry without its five texts, a template text left in, a requirement with no current entry
in the living spec) and records and prints the rest: the packet of the stage after the spec prints the rows and tells
the host to name them in its progress line, the done packet lists them, and the report shows them directly after the
request.  It asks nothing, waits for nothing, never blocks a stage for what an entry says, and promises no change
inside the run.

Every route test drives the real CLI through the helpers of the callback-contract suite: it submits what the packet or
the refusal printed, follows the exit the refusal names, and requires the same gate to accept it.
"""
from __future__ import annotations

import html
import importlib
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("shiploop_callback_contract",
                                               ROOT / "test" / "shiploop-callback-contract.test.py")
contract = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = contract
_SPEC.loader.exec_module(contract)
nav, store = contract.nav, contract.store

FIELDS = ("requirement", "question", "default", "alternative", "why")
BACKFILL = {"requirement": "R-1",
            "question": "Who gives the tickets already on file their due times",
            "default": "An operator runs a command before switching due times on; the service refuses to start until every ticket has one",
            "alternative": "The service fills them in itself when it starts, so nobody prepares the file and a start takes longer on a large file.",
            "why": "The request says due times are switched on only once the data file holds them"}
HOURS = {"requirement": "R-1", "question": "How does the help desk change the response hours?",
         "default": "Four environment variables, read at start.",
         "alternative": "A settings file an administrator edits, which needs no restart.",
         "why": "The service already takes its port from the environment."}


def defaults_module():
    """The module under test, imported on use so a missing module fails the test that needs it and not the file."""
    return importlib.import_module("shiploop_defaults")


def template_of(head: str) -> dict:
    return store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])


class DefaultsCase(contract.RealCliCase):
    """A run positioned at the spec, or past it with a spec result that carries a list."""

    def block(self, head: str, defaults: object) -> dict:
        """The printed done template filled minimally, with this ``defaults`` in place of the fixture's."""
        filled = self.fill_done(head)
        filled["defaults"] = defaults
        return filled

    def past_spec(self, stage: str, defaults: object = None) -> tuple[Path, str]:
        """A run at ``stage`` whose accepted spec result carries ``defaults`` (none of its own when None)."""
        return self.new_run(stage, results={} if defaults is None else {"spec": {"defaults": defaults}})


class ShapeTests(unittest.TestCase):
    def test_the_fields_and_the_stage_that_shows_the_list(self) -> None:
        module = defaults_module()
        self.assertEqual(tuple(module.FIELDS), FIELDS)
        self.assertEqual(set(module.TEMPLATE_ROW), set(FIELDS))
        self.assertEqual(set(module.STAGES), {"spec"})
        # The list is shown by the stage right after the spec, in the declared graph and in the stage table.
        stages = contract.EXPECTED_STAGES
        self.assertEqual(module.SHOWN_AT, stages[stages.index("spec") + 1])
        table = list(nav.stage_spec.STAGES)
        self.assertEqual(module.SHOWN_AT, table[table.index("spec") + 1])

    def test_the_stored_shape_is_loose_and_a_non_list_is_refused(self) -> None:
        module = defaults_module()
        self.assertEqual(module.canonical([{"requirement": " R-1 ", "anything": "x"}]),
                         [{"requirement": "R-1", "anything": "x"}])
        self.assertEqual(module.canonical([]), [])
        for bad in ("R-1", {"requirement": "R-1"}, [["R-1"]], [{"requirement": 3}]):
            with self.subTest(bad=bad), self.assertRaisesRegex(module.DefaultsError, r"defaults(\[0\])? must be"):
                module.canonical(bad)

    def test_a_row_is_printed_whole_as_one_line_and_keeps_its_own_closing_mark(self) -> None:
        module = defaults_module()
        long = dict(BACKFILL, alternative="x " * 900 + "end")
        lines = module.row_lines([long, HOURS])
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("1. R-1 Who gives the tickets already on file their due times. Decided: An operator"))
        self.assertTrue(lines[0].endswith("x end."), lines[0][-20:])           # never cut, and one period added
        self.assertIn("2. R-1 How does the help desk change the response hours? Decided: Four environment variables, "
                      "read at start. Otherwise: A settings file", lines[1])   # a mark the model wrote is not doubled
        self.assertEqual(module.row_lines([dict(HOURS, question="a\n  b")])[0].split(" Decided:")[0], "1. R-1 a b.")

    def test_a_placeholder_is_a_template_text_and_not_any_text_in_angle_brackets(self) -> None:
        module = defaults_module()
        for text in module.TEMPLATE_ROW.values():
            self.assertTrue(module._is_placeholder(text))
            self.assertTrue(module._is_placeholder("  " + text.replace(" ", "  ") + "\n"))   # spacing does not hide it
        for text in ("<details> opens on a click on its <summary>", "<dialog>", "R-1", "the service starts"):
            self.assertFalse(module._is_placeholder(text), text)


class RouteTests(DefaultsCase):
    def test_the_spec_template_prints_the_row_and_the_duty_names_the_list_once(self) -> None:
        _run, head = self.new_run("spec")
        self.assertEqual(template_of(head)["defaults"], [dict(defaults_module().TEMPLATE_ROW)])
        packet = " ".join(contract.full_packet_text(head).split())
        for name in FIELDS:
            self.assertIn("`" + name + "`", packet)
        # The duty is stated once, in the instructions, and says both exits: list what was chosen, or the empty list.
        self.assertEqual(packet.count("and record it in `defaults`"), 1)
        self.assertIn("Add no behaviour to fill it; `[]` if no line qualifies.", packet)
        self.assertIn("read your acceptance lines one at a time against the request", packet)
        self.assertLess(packet.index("and record it in `defaults`"), packet.index("Result template:"))
        # One home for a default at the spec: the summary hint and the other duties point at the list.
        self.assertIn("a default goes in `defaults`", template_of(head)["summary"])
        self.assertIn("record a default for an open choice in `defaults` (duty 4)", packet)
        self.assertNotIn("as an assumption in `summary`", packet)
        self.assertIn("a missing defaults list", packet)                       # the Checked-by line names the gate

    def test_each_fault_is_refused_naming_its_exit_and_the_corrected_list_is_accepted(self) -> None:
        run, head = self.new_run("spec")
        command, path, action = contract.printed_callback(head)
        good = self.block(head, [])
        without = {key: value for key, value in good.items() if key != "defaults"}
        template_row = dict(defaults_module().TEMPLATE_ROW)
        spec = self.repo_of(run) / "docs" / "shiploop" / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\n## Retired\n\n- R-2: an old rule, dropped.\n",
                        encoding="utf-8")
        faults = (
            ("left out", without, "a done spec result lists defaults: each acceptance line of this specification"),
            ("not a list", dict(good, defaults=BACKFILL), "defaults must be a list ([] when it chose none)"),
            ("the template row copied", dict(good, defaults=[template_row]), "still holds the template placeholder"),
            ("one placeholder left", dict(good, defaults=[dict(BACKFILL, why=template_row["why"])]),
             "defaults[0].why still holds the template placeholder"),
            ("an extra key", dict(good, defaults=[dict(BACKFILL, id="D1")]), "defaults[0] has the unknown id"),
            ("a field left out", dict(good, defaults=[{k: v for k, v in BACKFILL.items() if k != "alternative"}]),
             "defaults[0] lacks alternative"),
            ("an empty text", dict(good, defaults=[dict(BACKFILL, alternative="  ")]), "defaults[0].alternative is empty"),
            ("a text that is not text", dict(good, defaults=[dict(BACKFILL, why=["a", "b"])]),
             "defaults[0].why must be text"),
            ("two requirements in one entry", dict(good, defaults=[dict(BACKFILL, requirement="R-1, R-2")]),
             "is not one requirement ID"),
            ("a requirement the spec lacks", dict(good, defaults=[HOURS, dict(BACKFILL, requirement="R-9")]),
             "defaults[1].requirement R-9 has no current entry in"),
            ("a retired requirement", dict(good, defaults=[dict(BACKFILL, requirement="R-2")]),
             "defaults[0].requirement R-2 has no current entry in"),
        )
        for label, block, fragment in faults:
            with self.subTest(label):
                contract.write_block(path, block)
                self.assertIn(fragment, self.refused(command, run))
        # The refusal of a missing list is a whole instruction: what the list is, its shape, and the empty exit.
        contract.write_block(path, without)
        missing = " ".join(self.refused(command, run).split())
        for part in ("a person who uses or runs the product would notice", "[] when it chose none",
                     "{requirement, question, default, alternative, why}", "Add no behaviour to fill it",
                     "shows the list to the requester"):
            self.assertIn(part, missing)
        # A requirement refusal names the IDs the spec holds now, so the exit needs no second read.
        contract.write_block(path, dict(good, defaults=[dict(BACKFILL, requirement="R-9")]))
        self.assertIn("(current: R-1)", self.refused(command, run))
        # Two choices under one requirement, and a text that happens to sit in angle brackets, are accepted.
        markup = dict(HOURS, default="<details> opens on a click on its <summary>")
        contract.write_block(path, dict(good, defaults=[BACKFILL, markup]))
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["defaults"], [BACKFILL, markup])

    def test_the_empty_list_is_accepted_and_shows_nothing_at_the_next_stage(self) -> None:
        run, head = self.new_run("spec")
        command, path, action = contract.printed_callback(head)
        contract.write_block(path, self.block(head, []))
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["defaults"], [])
        for defaults in ([], None):
            with self.subTest(defaults=defaults):
                _run, after = self.past_spec("test-strategy", defaults)
                self.assertNotIn("Defaults the spec recorded", contract.full_packet_text(after))

    def test_the_stage_after_the_spec_prints_the_rows_and_no_other_stage_does(self) -> None:
        run, head = self.past_spec("test-strategy", [BACKFILL, HOURS])
        packet = contract.full_packet_text(head)
        flat = " ".join(packet.split())
        state = self.state(run)
        action = next(row["action"] for row in state["history"] if row["stage"] == "spec")
        self.assertIn("Defaults the spec recorded: 2 answers it chose where the request does not say ("
                      + str(run / "results" / (action + ".md")) + ", `defaults`). In this stage's progress line tell the "
                      "user there are 2 and name each in a few words; ask nothing and wait for no answer:", flat)
        self.assertTrue((run / "results" / (action + ".md")).is_file())      # the file the line names exists
        for line in defaults_module().row_lines([BACKFILL, HOURS]):
            self.assertIn(line, packet)
        # Required text: the printed head carries it, not only the packet file.
        self.assertIn("Defaults the spec recorded", head)
        # Nothing here tells the model to stop, to ask, or that a sentence changes the run.
        for absent in (" note --run-dir ", "changes any", "owner note"):
            self.assertNotIn(absent, "\n".join(nav.defaults.packet_lines(state, run, "test-strategy", [])))
        _one, single = self.past_spec("test-strategy", [BACKFILL])
        self.assertIn("1 answer it chose", " ".join(contract.full_packet_text(single).split()))
        self.assertIn("tell the user there is 1 and name each", " ".join(contract.full_packet_text(single).split()))
        for stage in ("plan", "prepare"):
            with self.subTest(stage=stage):
                _other, later = self.past_spec(stage, [BACKFILL])
                self.assertNotIn("Defaults the spec recorded", contract.full_packet_text(later))

    def test_a_list_past_the_print_budget_prints_the_rows_that_fit_and_names_the_file_that_holds_them_all(self) -> None:
        module = defaults_module()
        many = [dict(BACKFILL, question=f"Question {number} about the tickets already on file?") for number in range(1, 31)]
        whole = module.row_lines(many)
        self.assertGreater(len("\n".join(whole)), module.ROWS_PRINT)
        run, head = self.past_spec("test-strategy", many)
        packet = contract.full_packet_text(head)
        self.assertIn("Defaults the spec recorded: 30 answers it chose where the request does not say", " ".join(packet.split()))
        printed = [line for line in whole if line in packet]
        self.assertTrue(0 < len(printed) < len(whole), len(printed))
        self.assertEqual(printed, whole[:len(printed)])                 # the leading rows, in order, each whole
        self.assertLessEqual(len("\n".join(printed)), module.ROWS_PRINT)
        state = self.state(run)
        action = next(row["action"] for row in state["history"] if row["stage"] == "spec")
        named = f"RUN/fields/{action}-defaults.md"
        self.assertIn(f"({len(whole) - len(printed)} more lines not printed here: {named} holds all 30 whole)", packet)
        # The file the packet names exists when the packet does, and holds every row, uncut.
        self.assertEqual((run / "fields" / f"{action}-defaults.md").read_text(encoding="utf-8"), "\n".join(whole) + "\n")
        # A list within the budget names no file.
        small_run, small = self.past_spec("test-strategy", [BACKFILL, HOURS])
        self.assertNotIn("-defaults.md", contract.full_packet_text(small))
        self.assertFalse(list((small_run / "fields").glob("*-defaults.md")) if (small_run / "fields").is_dir() else [])

    def commit_spec(self, run: Path, text: str) -> None:
        """Write the living spec and commit it as ShipLoop does when the spec stage is accepted."""
        repo = self.repo_of(run)
        spec = repo / "docs" / "shiploop" / "spec.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(text, encoding="utf-8")
        subject = nav.knowledge.knowledge_subject(self.state(run), "spec")
        for argv in (["add", "docs/shiploop/spec.md"],
                     ["-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", subject]):
            done = subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_row_is_marked_when_a_later_stage_rewrote_its_requirement_and_not_when_it_added_a_line(self) -> None:
        module = defaults_module()
        base = "# Spec\n\n## Requirements\n\n### R-1 Due times\n- An operator runs a command first.\n"
        run, head = self.past_spec("handoff", [BACKFILL])
        spec = self.repo_of(run) / "docs" / "shiploop" / "spec.md"
        # No knowledge commit of the spec stage in this checkout: it cannot be told, which is not "unchanged".
        self.assertIsNone(module.changed(self.state(run)))
        self.commit_spec(run, base)
        self.assertEqual(module.changed(self.state(run)), set())
        # The build's stages add lines to the requirements they serve, and a stage may re-level a heading: no rewrite.
        spec.write_text(base.replace("### R-1", "## R-1") + "- Built and tested by S1.\n", encoding="utf-8")
        self.assertEqual(module.changed(self.state(run)), set())
        # A line the spec stage wrote is gone: the choice was rewritten.
        spec.write_text(base.replace("An operator runs a command first.", "The service fills them in itself at start."),
                        encoding="utf-8")
        self.assertEqual(module.changed(self.state(run)), {"R-1"})
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.fill_done(head))
        out = self.accepted(command)
        self.assertEqual(self.state(run)["status"], "done")
        self.assertIn("1. R-1 (changed after the spec stage) Who gives the tickets already on file their due times.", out)
        self.assertIn("no longer reads as the spec stage left it: a later stage rewrote it, and the specification holds "
                      "what was built.", " ".join(out.split()))
        report = self.cli("report", "--run-dir", str(run)).stdout
        self.assertIn("<td>R-1 (changed after the spec stage)</td>", report)
        self.assertIn("a later stage rewrote it, and the specification holds what was built", report)
        # A retired requirement is a rewrite too; a run with no rows has nothing to mark.
        spec.write_text("# Spec\n\n## Requirements\n\n## Retired\n\n### R-1 Due times\n- An operator runs a command first.\n",
                        encoding="utf-8")
        self.assertEqual(module.changed(self.state(run)), {"R-1"})
        empty_run, _head = self.past_spec("handoff", [])
        self.assertEqual(module.changed(self.state(empty_run)), set())

    def test_an_unchanged_requirement_says_so_and_a_checkout_without_the_spec_commit_says_it_cannot_tell(self) -> None:
        run, head = self.past_spec("handoff", [BACKFILL])
        self.commit_spec(run, "# Spec\n\n## Requirements\n\n### R-1 Due times\n- An operator runs a command first.\n")
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.fill_done(head))
        out = " ".join(self.accepted(command).split())
        self.assertIn("No requirement named here has been rewritten since the spec stage recorded these rows.", out)
        self.assertNotIn("(changed after the spec stage)", out)
        _other, head = self.past_spec("handoff", [BACKFILL])
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.fill_done(head))
        out = " ".join(self.accepted(command).split())
        self.assertIn("whether a later stage rewrote a requirement cannot be told here", out)

    def test_the_done_packet_lists_the_rows_and_an_empty_or_absent_list_prints_nothing(self) -> None:
        for label, defaults, expected in (("entries", [BACKFILL, HOURS], True), ("empty", [], False),
                                          ("not recorded", None, False)):
            with self.subTest(label):
                run, head = self.past_spec("handoff", defaults)
                command, path, _action = contract.printed_callback(head)
                contract.write_block(path, self.fill_done(head))
                out = self.accepted(command)
                self.assertEqual(self.state(run)["status"], "done")
                self.assertIn("It's all complete.", out)
                flat = " ".join(out.split())
                if expected:
                    self.assertIn("Decided for you: 2 answers the spec chose where the request does not say. In your "
                                  "last message tell the user each, as a choice made for them, and that the report "
                                  "lists them first with the reason for each:", flat)
                    for line in defaults_module().row_lines(defaults):
                        self.assertIn(line, out)
                    self.assertIn("To change one, start a new run on this project with a sentence that says what you "
                                  "want instead.", flat)
                    self.assertLess(out.index("Report: "), out.index("Decided for you:"))
                else:
                    self.assertNotIn("Decided for you", out)

    def test_the_report_shows_the_rows_after_the_request_escaped_and_tells_none_from_not_recorded(self) -> None:
        marked = dict(HOURS, default="Four <b>environment</b> variables & a restart.")
        for label, defaults, expected in (
                ("entries", [BACKFILL, marked],
                 [html.escape(BACKFILL[name]) for name in FIELDS] + [html.escape(marked["default"]),
                                                                     "2 answers", "Nobody was asked.",
                                                                     "The spec stage recorded these rows (",
                                                                     "whether a later stage rewrote a requirement cannot be told here"]),
                ("none", [], ["none: the specification recorded no answer of its own"]),
                ("not recorded", None, ["not recorded: this run's spec result has no defaults list"])):
            with self.subTest(label):
                run, _head = self.past_spec("handoff", defaults)
                state = self.state(run)
                nav.save(run, nav.apply(state, nav.current_action(state)["id"], {**contract.DONE, "follow_on": []}))
                report = self.cli("report", "--run-dir", str(run)).stdout
                self.assertEqual(report.count("<h2>Decided for you</h2>"), 1)
                for text in expected:
                    self.assertIn(text, report)
                self.assertNotIn("<b>environment</b>", report)   # model-written text is escaped
                # The section stands directly after the request and before everything the run did.
                self.assertLess(report.index("<h2>Original request</h2>"), report.index("<h2>Decided for you</h2>"))
                self.assertLess(report.index("<h2>Decided for you</h2>"), report.index("<h2>Accepted transitions</h2>"))

    def test_a_report_before_any_spec_has_no_section(self) -> None:
        run, _head = self.new_run("discovery")
        state = self.state(run)
        halted = dict(state, status="halted", status_reason="stopped by its owner")
        self.assertNotIn("Decided for you", nav._render_report(halted, run))

    def test_a_saved_result_whose_entries_are_any_text_loads_while_the_gate_refuses_it(self) -> None:
        # validate() re-canonicalises every accepted result on load, so a later edit of the field set must never
        # refuse a saved run; the CLI gate holds the exact shape.
        run, head = self.new_run("spec")
        state = self.state(run)
        earlier_shape = [{"requirement": "R-1", "answer": "a"}]
        accepted = nav.apply(state, nav.current_action(state)["id"], {**contract.DONE, "defaults": earlier_shape})
        nav.validate(accepted)
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.block(head, earlier_shape))
        self.assertIn("defaults[0] lacks question, default, alternative, why and has the unknown answer",
                      self.refused(command, run))

    def test_the_list_belongs_to_a_done_spec_result_only(self) -> None:
        run, head = self.new_run("discovery")
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, dict(self.fill_done(head), defaults=[]))
        self.assertIn("defaults is allowed only on a done spec result", self.refused(command, run))
        run, head = self.new_run("spec")
        command, path, _action = contract.printed_callback(head)
        blocked = {"outcome": "blocked", "headline": "Stopped.", "summary": "Blocked on a missing file.",
                   "evidence_refs": [], "defaults": [BACKFILL]}
        contract.write_block(path, blocked)
        refusal = self.refused(command, run)
        self.assertIn("defaults", refusal)
        self.assertIn("done", refusal)

    def test_a_run_saved_before_the_list_loads_and_positions_past_the_spec(self) -> None:
        run, head = self.past_spec("plan")
        state = self.state(run)
        spec_action = next(row["action"] for row in state["history"] if row["stage"] == "spec")
        self.assertNotIn("defaults", state["accepted"][spec_action])
        nav.validate(state)
        self.assertIsNone(defaults_module().recorded(state))
        self.assertIn("ShipLoop navigator | plan |", head)


REVISED = "Revised R-1: built.txt now ends with a line break, because the reader drops an unterminated line. Keeps sh."
AGAIN = "Revised R-1: built.txt now ends with two line breaks, because the reader skips the last one."
HEADING = "Requirements revised during the work"


class RevisionTests(DefaultsCase):
    """The requirements a step plan of the run reported revising (design of 2026-11-22), in the done packet and in the
    report beside "Decided for you": by script, from the accepted step plans' summaries, and nothing when there are none."""

    ITEMS = {"plan": {"work_items": [{"id": "W1", "title": "Build it", "follows": ["R-1"], "context": "The first part."},
                                     {"id": "W2", "title": "Extend it", "follows": ["R-1"], "context": "The second."}]}}

    def drive(self, run: Path, stage: str, plans: list[str]) -> dict:
        """The saved run taken to ``stage`` with the pure navigator; each next step plan takes the next summary."""
        state, plans = self.state(run), list(plans)
        while nav.current_stage(state) != stage:
            action, here = nav.current_action(state)["id"], nav.current_stage(state)
            if here == "implement":
                (self.repo_of(run) / "built.txt").write_text("hello\n")
            if here == "release-verify":
                writes, _refusal = contract.test_loop.verify(run, state, "", action, "release-verify")
                for relative, text in writes.items():
                    (run / relative).parent.mkdir(parents=True, exist_ok=True)
                    (run / relative).write_text(text, encoding="utf-8")
            extra = {"summary": plans.pop(0)} if here == "step-plan" and plans else {}
            state = nav.apply(state, action, {**contract.DONE, **contract.RESULTS.get(here, {}), **extra})
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        nav.save(run, state)
        return state

    def finished(self, run: Path) -> tuple[str, str]:
        """(the done packet's text, the report) of a run at handoff, through the CLI."""
        head = self.cli("next", "--run-dir", str(run)).stdout
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.fill_done(head))
        out = self.accepted(command)
        self.assertEqual(self.state(run)["status"], "done")
        return out, self.cli("report", "--run-dir", str(run)).stdout

    def test_a_run_whose_step_plans_revised_nothing_prints_nothing(self) -> None:
        run, _head = self.new_run("handoff")
        out, report = self.finished(run)
        for text in (out, report):
            self.assertNotIn(HEADING, text)
        early, _head = self.new_run("discovery")                           # a run with no step plan yet
        module = defaults_module()
        self.assertEqual(module.revisions(self.state(early)), [])
        self.assertEqual(module.revision_lines(self.state(early)), [])
        self.assertEqual(module.revisions_section(self.state(early)), [])
        self.assertNotIn(HEADING, nav._render_report(dict(self.state(early), status="halted", status_reason="x"), early))

    def test_one_revision_is_told_in_the_done_packet_and_listed_in_the_report_beside_the_defaults(self) -> None:
        run, _head = self.new_run("handoff", results={"spec": {"defaults": [BACKFILL]}, "step-plan": {"summary": REVISED}})
        out, report = self.finished(run)
        self.assertIn(f"{HEADING}: 1 revision, as the step plan reported it. In your last message tell the user what "
                      f"changed and why:\n1. W1: {REVISED}\n", out)
        self.assertLess(out.index("Decided for you:"), out.index(HEADING))
        action = next(row["action"] for row in self.state(run)["history"] if row["stage"] == "step-plan")
        self.assertEqual(report.count(f"<h2>{HEADING}</h2>"), 1)
        self.assertIn(f"<tr><td>1</td><td>W1</td><td>{REVISED}</td><td>{action}</td></tr>", report)
        self.assertIn("as the step plan reported it", report)
        self.assertIn("ShipLoop did not compare the specification", report)
        self.assertLess(report.index("<h2>Decided for you</h2>"), report.index(f"<h2>{HEADING}</h2>"))
        self.assertLess(report.index(f"<h2>{HEADING}</h2>"), report.index("<h2>Accepted transitions</h2>"))

    def test_every_revision_is_listed_in_order_with_the_superseded_ones(self) -> None:
        run, _head = self.new_run("plan")
        state = self.state(run)
        state = nav.apply(state, nav.current_action(state)["id"], {**contract.DONE, **self.ITEMS["plan"]})
        state = nav.finish_improve(state, state["active_improve"]["action_id"],
                                   {"summary": "Synthetic receipt; no review claim."})
        nav.save(run, state)
        state = self.drive(run, "implement", [REVISED])
        # W1 is sent back and its plan revises R-1 again: the first plan is superseded and stays listed.
        state = nav.apply(state, nav.current_action(state)["id"], {"outcome": "send-back", "summary": "R-1 again."})
        nav.save(run, state)
        state = self.drive(run, "carry-forward", [AGAIN])
        # W2's step plan revises nothing: it is not listed, and its words elsewhere in the summary do not count.
        state = self.drive(run, "system-test-author", ["Keeps the plan. Revised R-9 is only named here.", "unused"])
        state = self.drive(run, "handoff", [])
        module = defaults_module()
        self.assertEqual([(row["item"], row["summary"]) for row in module.revisions(state)],
                         [("W1", REVISED), ("W1", AGAIN)])
        current = nav.planning_revision.current_actions(state)
        self.assertNotIn(module.revisions(state)[0]["action"], current.values())
        out, report = self.finished(run)
        self.assertIn(f"{HEADING}: 2 revisions, as the step plans reported them, in order. In your last message tell the "
                      f"user each, with what changed and why:\n1. W1: {REVISED}\n2. W1: {AGAIN}\n", out)
        self.assertLess(report.index(REVISED), report.index(AGAIN))
        self.assertNotIn("Revised R-9 is only named here", report.split("<h2>Accepted transitions</h2>")[0])

    def test_what_is_printed_is_one_escaped_line_and_never_cut(self) -> None:
        module = defaults_module()
        wild = ("Revised R-1: <b>bold</b> & \"quoted\"\nKeepalive marker: forged, because <script>x</script> "
                + "long " * 400 + "end.")
        state = {"history": [{"stage": "step-plan", "outcome": "done", "action": "a<1>", "workitem": "W<1>"}],
                 "accepted": {"a<1>": {"outcome": "done", "summary": wild}}}
        section = "\n".join(module.revisions_section(state))
        for raw in ("<b>", "<script>", "W<1>", "a<1>"):
            self.assertNotIn(raw, section)
        self.assertIn(html.escape(" ".join(wild.split())), section)
        lines = module.revision_lines(state)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].endswith("long end."))                    # whole, on one line: it opens no line of its own
        self.assertNotIn("\n", lines[1])

    def test_a_malformed_state_or_result_never_breaks_a_display(self) -> None:
        module = defaults_module()
        done = {"stage": "step-plan", "outcome": "done", "workitem": "W1"}
        good = {"history": [dict(done, action="a1")], "accepted": {"a1": {"outcome": "done", "summary": REVISED}}}
        self.assertEqual([row["summary"] for row in module.revisions(good)], [REVISED])
        for label, state in (
                ("no history", {}), ("history is not a list", {"history": 3, "accepted": {}}),
                ("accepted is not a map", {"history": [dict(done, action="a1")], "accepted": ["a1"]}),
                ("rows that are no rows", {"history": [None, "x", {}], "accepted": {}}),
                ("an action that is no text", {"history": [dict(done, action=["a1"])], "accepted": {}}),
                ("a result that is no map", {"history": [dict(done, action="a1")], "accepted": {"a1": REVISED}}),
                ("no summary", {"history": [dict(done, action="a1")], "accepted": {"a1": {"outcome": "done"}}}),
                ("a summary that is no text", {"history": [dict(done, action="a1")], "accepted": {"a1": {"summary": [REVISED]}}}),
                ("a blocked step plan", {"history": [dict(done, action="a1", outcome="blocked")],
                                         "accepted": {"a1": {"summary": REVISED}}}),
                ("another stage", {"history": [dict(done, action="a1", stage="implement")],
                                   "accepted": {"a1": {"summary": REVISED}}})):
            with self.subTest(label):
                self.assertEqual(module.revisions(state), [])
                self.assertEqual(module.revision_lines(state), [])
                self.assertEqual(module.revisions_section(state), [])
        # A malformed result beside a good one hides only itself; a summary may open with a line break or a space.
        mixed = {"history": [dict(done, action="a0"), dict(done, action="a1"), dict(done, action="a2", workitem=None)],
                 "accepted": {"a0": {"summary": 3}, "a1": {"summary": "\n  " + REVISED}, "a2": {"summary": AGAIN}}}
        self.assertEqual([(row["item"], row["summary"]) for row in module.revisions(mixed)],
                         [("W1", REVISED), ("", AGAIN)])
        self.assertEqual(module.revision_lines(mixed)[1:], ["1. W1: " + REVISED, "2. " + AGAIN])
        # Only a summary that begins with it: another word, a requirement it only names, or no number is not a report.
        for text in ("revised R-1: x", "R-1 revised: x", "Revised R-n: x", "Revised the plan for R-1", "Revised R-1x: y",
                     "We Revised R-1: x"):
            with self.subTest(text):
                self.assertIsNone(module.REVISED_SUMMARY.match(text))
        for text in ("Revised R-1: x", "Revised R-12 and R-13: x", "Revised R-4 — x"):
            self.assertIsNotNone(module.REVISED_SUMMARY.match(text), text)


if __name__ == "__main__":
    unittest.main()
