#!/usr/bin/env python3
"""Owner notes are accounted for by a row in a stage's result, never by a print (design:
docs/experiments/ratchet-pilot-20261120/shiploop-notes/DESIGN.md, section 2; the tests of section 5).

A done result of any producer stage carries ``notes``: one {"note", "did", "detail"} per note it owes (``item`` too on an
applied row at plan and carry-forward).  ShipLoop refuses ``done`` while a row is missing, extra or malformed, before
every other gate, and the refusal's first line names the notes, their folder and the result file.  Where a note stands
(open, carried, settled) is read from the rows of every accepted done result in order.

Every admission under test runs through the real CLI (``check``, ``complete``, an Improve stage's ``complete``), with
both output streams read.  A run is positioned with the pure navigator and saved, as the callback-contract suite does
(its helpers, not its tests), and the review tests use the actual Improve CLI suite's fixture.  Two races that a
subprocess cannot time (a note between the two reads at the end of a run, a run that ends while a note is written) run
the CLI's own entry point in this process with one function wrapped.  No model or host CLI is started.

The groups below follow the bullets of the design's section 5, "Tests with no model", in order.
"""
from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import typing
import unittest
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, file: str):
    """A sibling suite as a module, once: a suite that loads this one may have loaded it already."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


contract = _load("shiploop_callback_contract", "shiploop-callback-contract.test.py")
improve_cli = _load("shiploop_actual_improve_cli", "shiploop-actual-improve-cli.test.py")
v4 = _load("shiploop_navigator_v4", "shiploop-navigator-v4.test.py")
nav, store = contract.nav, contract.store
owner_notes = nav.owner_notes
CLI = contract.CLI
SCRIPTS = contract.SCRIPTS
sys.path.insert(0, str(SCRIPTS))
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402
import shiploop_trace as trace  # noqa: E402

WORDS = "Reuse the date helper in src/dates.py; do not add a library."
SECOND = "The greeting must also print the date."
THIRD = "Keep the output to one line."
ITEMS = [{"id": "W1", "title": "Build it", "follows": ["R-1"], "context": "The first part."},
         {"id": "W2", "title": "Extend it", "follows": ["R-1"], "context": "The second part."},
         {"id": "W3", "title": "Finish it", "follows": ["R-1"], "context": "The third part."}]
THREE_ITEMS = {"plan": {"work_items": ITEMS}}
# The duty an ordinary stage's block ends with, as the design (2.6) words it.
DUTY = ("Each is the run owner's instruction for this run. Account for each in this stage's result, \"notes\": one "
        "{\"note\", \"did\", \"detail\"} per note. did: \"applied\" (this stage did what it asks, within what this stage may "
        "change; say what changed), \"already\" (the run already does it; say where), \"carried\" (it needs something "
        "this stage may not change; say what; the next stage must then account for it), \"declined\" (it cannot be done "
        "in this run; say why). ShipLoop refuses done without them.")


def row(note: str = "N1", did: str = "already", detail: str = "src/dates.py is already the only date code.",
        **extra: str) -> dict:
    return {"note": note, "did": did, "detail": detail, **extra}


def lines(text: str) -> list[str]:
    return text.splitlines()


class NoteRun(contract.RealCliCase):
    """A real run positioned at a stage, with the notes and the rows a test gives it."""

    def setUp(self) -> None:
        super().setUp()
        self.env["SHIPLOOP_PROGRESS"] = "off"

    def field_values(self) -> dict:
        return {**super().field_values(), "notes": [], "work_items": [dict(ITEMS[0])]}

    def note(self, run: Path, text: str = WORDS, *, status: int = 0) -> subprocess.CompletedProcess:
        done = self.cli("note", "--run-dir", str(run), "--text", text)
        self.assertEqual(done.returncode, status, done.stdout + done.stderr)
        return done

    def next(self, run: Path) -> str:
        printed = self.cli("next", "--run-dir", str(run))
        self.assertEqual(printed.returncode, 0, printed.stdout + printed.stderr)
        return printed.stdout

    def result(self, head: str, *rows: dict, **fields) -> dict:
        """The printed template filled in, with ``rows`` as its ``notes`` (none: the key left out)."""
        block = self.fill_done(head)
        block.pop("notes", None)
        if rows:
            block["notes"] = list(rows)
        block.update(fields)
        return block

    def send(self, head: str, block: dict, *, verb: str = "complete", loop: bool = True) -> subprocess.CompletedProcess:
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, block, loop=loop)
        return self.run_printed(contract.check_command(command) if verb == "check" else command)

    def refuse(self, run: Path, head: str, block: dict, *, verb: str = "complete", loop: bool = True) -> str:
        """Submit ``block``; it must be refused on standard error with exit 2, print nothing else and save nothing."""
        before = (run / "state.md").read_bytes()
        done = self.send(head, block, verb=verb, loop=loop)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertEqual(done.stdout, "")
        self.assertEqual((run / "state.md").read_bytes(), before)
        return done.stderr

    def accept(self, head: str, block: dict, *, loop: bool = True) -> str:
        done = self.send(head, block, loop=loop)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout

    def owes(self, packet: str) -> list[str]:
        """The note ids a packet's block says this stage owes (empty: no block)."""
        if "Owner notes this stage must account for (" not in packet:
            return []
        block = packet.split("Owner notes this stage must account for (", 1)[1].split(DUTY[:40], 1)[0]
        return re.findall(r"^ {4}(N\d+) \d\d:\d\dZ  ", block, re.MULTILINE)

    def walk(self, run: Path, until, results: dict | None = None, rows: dict | None = None) -> dict:
        """Advance the saved run with the pure navigator until ``until(state)``, as ``new_run`` positions one; ``rows``
        gives a stage's result its ``notes`` ({stage: [rows]}, each stage's next result only)."""
        state, repo, rows = self.state(run), self.repo_of(run), dict(rows or {})
        while not until(state):
            action, here = nav.current_action(state)["id"], nav.current_stage(state)
            if here == "implement":
                (repo / "built.txt").write_text("hello\n")
            if here == "release-verify":
                writes, _refusal = test_loop.verify(run, state, "", action, "release-verify")
                for relative, text in writes.items():
                    (run / relative).parent.mkdir(parents=True, exist_ok=True)
                    (run / relative).write_text(text, encoding="utf-8")
            extra = {"notes": rows.pop(here)} if here in rows else {}
            state = nav.apply(state, action, {**contract.DONE, **contract.RESULTS.get(here, {}),
                                              **(results or {}).get(here, {}), **extra})
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        nav.save(run, state)
        return state

    @staticmethod
    def at(stage: str, item: str | None = None):
        return lambda state: (nav.current_stage(state) == stage
                              and (item is None or nav._current_work_item(state) == item))

    def first_line(self, text: str) -> str:
        return lines(text)[0]


# ---------------------------------------------------------------------------- 1. a note written after the packet printed


class AfterThePacketTests(NoteRun):
    """Section 5, bullet 1."""

    def test_check_and_complete_refuse_with_a_first_line_that_names_the_note_and_the_row_is_accepted(self) -> None:
        run, head = self.new_run("spec")
        _command, path, action = contract.printed_callback(head)
        self.note(run)
        block = self.result(head)
        checked = self.refuse(run, head, block, verb="check")
        self.assertEqual(self.first_line(checked),
                         f"ShipLoop check: owner note N1 is not accounted for: read {run}/owner-notes/N1.md, add its "
                         f"row to \"notes\" in {path}, then run this again.")
        # The check's answer is a no, with the reason.
        answer = store.read_record(run / "checks" / f"{action}.md")
        self.assertEqual(answer["answer"], "no")
        self.assertIn("owner note N1 is not accounted for", answer["reason"])
        # Then the row's shape and the four meanings of did, the fault, the note's words and what to do.
        self.assertEqual(lines(checked)[1:6], [
            ('A row: {"note": "N<k>", "did": "applied" | "already" | "carried" | "declined", "detail": "<text>"}, one per '
             "owed note and no other row:"),
            "  applied: this stage did what the note asks, within what this stage may change; detail says what changed",
            "  already: the run already does what it asks; detail says where",
            ("  carried: it needs something this stage may not change; detail says what; the next stage must then "
             "account for it"),
            "  declined: it cannot be done in this run; detail says why"])
        self.assertIn("\n- N1 has no row\n", checked)
        self.assertIn(f"\n    N1 {owner_notes.read(run)[0]['written_at'][11:16]}Z  {WORDS}\n", checked)
        self.assertIn("If a note changes this stage's work, do that work first and run this stage's checks again",
                      checked)
        completed = self.refuse(run, head, block)
        self.assertEqual(self.first_line(completed),
                         f"ShipLoop navigator: owner note N1 is not accounted for: read {run}/owner-notes/N1.md, add "
                         f"its row to \"notes\" in {path}, then run this again.")
        # Refused each time, never held "once": the same result is refused again, and again.
        for _ in range(2):
            self.assertEqual(self.first_line(self.refuse(run, head, block)), self.first_line(completed))
        accepted = self.accept(head, self.result(head, row()))
        self.assertNotIn("Owner notes this stage must account for", accepted)
        state = self.state(run)
        parked = state["active_improve"]["seed_result"]   # spec starts an Improve stage: the result waits for it
        self.assertEqual(parked["notes"], [row()])
        # Both streams of the trace: the refusals are refusals, with the first line as the error.
        commands = [event for event in store.read_jsonl(run / trace.TRACE_FILE) if event.get("kind") == "command"]
        self.assertEqual([(event["verb"], event["exit"]) for event in commands if event["verb"] in ("check", "complete")],
                         [("check", 2), ("complete", 2), ("complete", 2), ("complete", 2), ("complete", 0)])
        self.assertEqual(trace.build(run)["counts"]["refusals"], 3)
        self.assertTrue(all("held" not in event and "shown" not in event and "delivered" not in event
                            for event in commands))

    def test_three_notes_are_named_by_id_with_their_folder(self) -> None:
        run, head = self.new_run("discovery")
        _command, path, _action = contract.printed_callback(head)
        for text in (WORDS, SECOND, THIRD):
            self.note(run, text)
        block = self.result(head)
        expected = (f"owner notes N1, N2 and N3 are not accounted for: read each in {run}/owner-notes/, add their rows "
                    f"to \"notes\" in {path}, then run this again.")
        self.assertEqual(self.first_line(self.refuse(run, head, block, verb="check")), "ShipLoop check: " + expected)
        self.assertEqual(self.first_line(self.refuse(run, head, block)), "ShipLoop navigator: " + expected)
        # One row present and two missing: the first line names the two, and the row that is there stands.
        refused = self.refuse(run, head, self.result(head, row("N2")))
        self.assertTrue(self.first_line(refused).startswith("ShipLoop navigator: owner notes N1 and N3 are not "
                                                            "accounted for: read each in "), refused)
        self.accept(head, self.result(head, row("N1"), row("N2"), row("N3", "declined", "No date is shown here.")))


# ---------------------------------------------------------------------------- 2. a note written before the packet prints


class BeforeThePacketTests(NoteRun):
    """Section 5, bullet 2."""

    def test_the_packet_quotes_the_note_with_the_duty_and_the_row_is_accepted_at_the_first_try(self) -> None:
        run, _head = self.new_run("research")
        self.note(run)
        head = self.next(run)
        written = owner_notes.read(run)[0]["written_at"][11:16]
        self.assertIn("Owner notes this stage must account for (the run owner wrote these during the run; verbatim, "
                      "oldest first; each is a file in RUN/owner-notes/):\n"
                      f"    N1 {written}Z  {WORDS}\n" + DUTY + "\nGoal: ", head)
        # The template has one row for it, and the checked line names the gate first.
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
        self.assertEqual(template["notes"], [{"note": "N1", "did": owner_notes.DID_PLACEHOLDER,
                                              "detail": owner_notes.DETAIL_PLACEHOLDER}])
        checked = next(line for line in lines(head) if line.startswith("Checked by: "))
        self.assertIn('refuses a missing or extra "notes" row for an owner note this stage owes, a did outside applied, '
                      "already, carried or declined, or an empty detail; ", checked)
        self.accept(head, self.result(head, row(did="applied", detail="research names src/dates.py as the one "
                                                                       "helper to reuse")))
        self.assertEqual(self.state(run)["accepted"][contract.printed_callback(head)[2]]["notes"],
                         [row(did="applied", detail="research names src/dates.py as the one helper to reuse")])

    def test_a_reprint_settles_nothing(self) -> None:
        run, _head = self.new_run("intake")
        self.note(run)
        for _ in range(3):
            head = self.next(run)
            self.assertEqual(self.owes(head), ["N1"])
        self.assertEqual(owner_notes.ledger(self.state(run)), {})
        self.assertEqual(sorted(path.name for path in (run / owner_notes.DIR).iterdir()), ["N1.md"])
        self.refuse(run, head, self.result(head))


# ---------------------------------------------------------------------------- 3. each refusal


class RefusalTests(NoteRun):
    """Section 5, bullet 3: each fault is refused with the fault named, and the fixed row is accepted."""

    def test_rows_that_do_not_account_for_the_owed_notes_are_refused(self) -> None:
        run, _head = self.new_run("intake")
        self.note(run)
        self.note(run, SECOND)
        head = self.next(run)
        for label, rows, first, fault in (
                ("a missing row", [row()], "owner note N2 is not accounted for: read ", "- N2 has no row"),
                ("an extra row", [row(), row("N2"), row("N9")], '"notes" in ',
                 "- this stage owes no row for N9: no owner note N9 is on file in"),
                ("two rows for one note", [row(), row("N2"), row("N2")], '"notes" has two rows for N2: keep exactly one',
                 "- N2 has two rows; keep exactly one"),
                ("an unknown did", [row(), row("N2", "noted")], "owner note N2 is not accounted for: read ",
                 "- N2's row \"did\" is 'noted', not one of applied, already, carried or declined"),
                ("an empty detail", [row(), row("N2", detail=" ")], "owner note N2 is not accounted for: read ",
                 '- N2\'s row "detail" is empty'),
                ("the template's detail", [row(), row("N2", detail=owner_notes.DETAIL_PLACEHOLDER)],
                 "owner note N2 is not accounted for: read ",
                 ('- N2\'s row "detail" still holds a placeholder ("...", a text in angle brackets or the template\'s '
                  "own): write what this stage did with the note")),
                ("an item outside plan and carry-forward", [row(), row("N2", "applied", item="W1")],
                 "owner note N2 is not accounted for: read ",
                 '- N2\'s row "item" goes only on an applied row at plan or carry-forward: remove it'),
                ("an unknown key", [row(), row("N2", why="x")], "owner note N2 is not accounted for: read ",
                 "- N2's row has the unknown 'why'"),
                ("a list that is not one", "N1", '"notes" is not a list: give it in ',
                 '- "notes" is not a list of rows')):
            with self.subTest(label):
                block = self.result(head)
                block["notes"] = rows
                refused = self.refuse(run, head, block)
                self.assertTrue(self.first_line(refused).startswith("ShipLoop navigator: " + first), refused)
                if fault:
                    self.assertIn("\n" + fault, refused)
        self.accept(head, self.result(head, row(), row("N2", "carried", "the date is the build's to print")))

    def test_plan_names_the_work_item_of_the_queue_its_result_leaves(self) -> None:
        run, _head = self.new_run("plan")
        self.note(run)
        head = self.next(run)
        self.assertIn(', and name in "item" the work item of this result\'s queue that does it), ', head)
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
        self.assertEqual(template["notes"][0]["item"], owner_notes.ITEM_PLACEHOLDER)
        good = self.result(head, row(did="applied", detail="W1 reuses src/dates.py", item="W1"))
        for label, bad, fault in (
                ("no item", row(did="applied", detail="W1 reuses src/dates.py"), ('"item" is missing: an applied row '
                 "at plan names the work item of the queue this result leaves that does it (W1)")),
                ("an item of no queue", row(did="applied", detail="W9 reuses it", item="W9"),
                 "\"item\" 'W9' is not in the queue this result leaves (W1)"),
                ("an item on an already row", row(item="W1"), ('"item" goes only on an applied row; this one is '
                 "already: remove it"))):
            with self.subTest(label):
                refused = self.refuse(run, head, dict(good, notes=[bad]))
                self.assertIn(fault, refused)
        # The queue the result leaves, not the one it replaces: an item the result adds is one it may name.
        self.accept(head, dict(good, work_items=[*good["work_items"], dict(ITEMS[1])],
                               concerns=contract.inner_fixture.no_concerns_map(["W1", "W2"]),
                               notes=[row(did="applied", detail="W2 reuses src/dates.py", item="W2")]))

    def test_carry_forward_settles_with_a_pending_item_and_may_not_carry(self) -> None:
        run, _head = self.new_run("prepare", results=THREE_ITEMS)
        self.walk(run, self.at("carry-forward", "W2"), results=THREE_ITEMS)
        self.note(run)
        head = self.next(run)
        self.assertNotIn('"carried"', head.split("Owner notes this stage must account for", 1)[1].split("Goal:", 1)[0])
        self.assertIn("A note that needs no work is \"already\". An owner note is the direction the rule on a changed "
                      "requirement waits for: when one changes a requirement, revise that requirement's entry in "
                      "KNOWLEDGE/spec.md in place (the ID stays; say the owner note revised it; keep no copy of the old "
                      "clause), queue the item that follows it, and report done, not blocked.", head)
        good = self.result(head)
        for label, bad, fault in (
                ("carried", row(did="carried", detail="needs W3"),
                 ('"did" is "carried", which carry-forward may not give: it settles every note it owes (applied, '
                  'already or declined); a note that needs a later work item is "applied" with that item')),
                ("no item", row(did="applied", detail="W3 reuses it"), ('"item" is missing: an applied row at '
                 "carry-forward names the work item of the future queue this result leaves that does it (W3)")),
                ("the current item", row(did="applied", detail="done here", item="W2"),
                 '"item" is W2, the item this carry-forward closes'),
                ("a finished item", row(did="applied", detail="done there", item="W1"), '"item" is W1, a finished item'),
                ("an item of no queue", row(did="applied", detail="W9 does it", item="W9"),
                 "\"item\" 'W9' is not in the future queue this result leaves (W3)")):
            with self.subTest(label):
                block = dict(good, notes=[bad])
                self.assertIn(fault, self.refuse(run, head, block))
        self.accept(head, dict(good, notes=[row(did="applied", detail="W3 reuses src/dates.py", item="W3")]))
        self.assertEqual(owner_notes.ledger(self.state(run))["N1"][-1]["item"], "W3")

    def test_handoff_settles_every_note_and_may_not_carry(self) -> None:
        run, _head = self.new_run("handoff")
        self.note(run)
        head = self.next(run)
        refused = self.refuse(run, head, self.result(head, row(did="carried", detail="a later run")))
        self.assertIn('"did" is "carried", which handoff may not give: it settles every note it owes (applied, already '
                      "or declined)", refused)
        self.assertIn("  carried: not at handoff, which settles every note it owes", refused)
        done = self.accept(head, self.result(head, row(did="declined", detail="The run is at its handoff.")))
        self.assertIn("It's all complete.", done)


# ---------------------------------------------------------------------------- 4. the ledger


class LedgerTests(NoteRun):
    """Section 5, bullet 4: where a note stands, read from every accepted result in order."""

    def test_a_row_at_one_steps_implement_stays_settled_through_the_next_steps_result(self) -> None:
        two_steps = {"step-plan": dict(
            contract.STEP_PLAN, follows=[], paths=["built.txt", "more.txt"],
            steps=[dict(contract.STEP_PLAN["steps"][0]),
                   {"id": "S2", "task": "Create more.txt", "deps": ["S1"], "criteria": ["C1"],
                    "proof": "test -f built.txt", "skills": []}])}
        run, _head = self.new_run("implement", results=two_steps)
        self.note(run)
        state = self.walk(run, lambda state: nav.current_stage(state) == "implement"
                          and (nav.loops.current_step(state, "W1") or {}).get("id") == "S2",
                          results=two_steps, rows={"implement": [row()]})
        self.assertEqual(owner_notes.standing(owner_notes.ledger(state)["N1"]), "settled")
        packet = self.next(run)
        self.assertEqual(self.owes(packet), [])
        self.assertIn("Owner notes accounted for: N1 already at implement of W1 (step ", packet)

    def test_a_note_carried_at_implement_is_owed_by_the_items_carry_forward_and_by_no_step_before_it(self) -> None:
        run, head = self.new_run("implement")
        (self.repo_of(run) / "built.txt").write_text("hello\n")
        self.note(run)
        self.accept(head, self.result(head, row(did="carried", detail="the requirement must say which helper")))
        for stage in ("test", "document"):
            with self.subTest(stage):
                self.walk(run, self.at(stage))
                packet = self.next(run)
                self.assertEqual(self.owes(packet), [])
                self.assertIn("N1 carried by implement of W1 (step ", packet)
                self.assertIn(", for W1 carry-forward;", packet)
        self.walk(run, self.at("carry-forward"))
        head = self.next(run)
        self.assertEqual(self.owes(head), ["N1"])
        self.assertIn("      Carried here by implement of W1 (step ", head)
        self.refuse(run, head, self.result(head))
        self.accept(head, self.result(head, row(detail="R-1 already names src/dates.py")))

    def test_a_note_carried_at_discovery_is_owed_at_research(self) -> None:
        run, head = self.new_run("discovery")
        self.note(run)
        self.accept(head, self.result(head, row(did="carried", detail="research picks the helper")))
        head = self.next(run)
        self.assertEqual(self.owes(head), ["N1"])
        self.assertIn("      Carried here by discovery (step 2): research picks the helper", head)

    def test_settled_notes_stay_settled_through_a_reconcile_and_both_send_backs(self) -> None:
        with self.subTest("a reconcile"):
            # The reconcile itself through the pure navigator (its CLI route needs a stopped child runtime, which the
            # navigator-v4 suite drives): the state it leaves is read here as every packet reads it.
            run, _head = self.new_run("intake")
            self.note(run)
            state = self.walk(run, self.at("plan"), rows={"intake": [row()]})
            action = nav.current_action(state)["id"]
            waiting = nav.apply(state, action, {**contract.DONE, "work_items": [dict(ITEMS[0])]})
            child = waiting["active_improve"]
            child = bridge.binding(waiting, action, "plan", child["seed_result"],
                                   bridge.resolve_skill(str(contract.CARD)), improve_action=child["improve_action"])
            waiting = dict(waiting, active_improve=child)
            receipt = {"summary": "The research premise is unresolved.", "target": "research",
                       "evidence_refs": [str(self.evidence)]}
            record = v4.NavigatorV4Tests.synthetic_stopped_record(None, child, action, receipt)
            reconciled = nav.reconcile(waiting, action, record, receipt)
            self.assertEqual(nav.current_stage(reconciled), "research")
            found = owner_notes.read(run)
            self.assertEqual(owner_notes.owed(reconciled, found, "research", None), [])
            self.assertEqual(owner_notes.standing(owner_notes.ledger(reconciled)["N1"]), "settled")
            self.assertTrue(owner_notes.accounted_lines(run, reconciled, [])[0].startswith(
                "Owner notes accounted for: N1 already at intake (step 1)"))
        with self.subTest("an inner send-back"):
            run, _head = self.new_run("step-plan")
            self.note(run)
            state = self.walk(run, self.at("test"), rows={"step-plan": [row()]})
            nav.save(run, nav.apply(state, nav.current_action(state)["id"],
                                    {"outcome": "send-back", "summary": "The step plan's command is wrong."}))
            packet = self.next(run)
            self.assertIn("ShipLoop navigator | step-plan |", packet)
            self.assertEqual(self.owes(packet), [])
        with self.subTest("an outer send-back"):
            run, _head = self.new_run("system-test-author")
            self.note(run)
            state = self.walk(run, self.at("system-test"), rows={"system-test-author": [row()]})
            nav.save(run, nav.apply(state, nav.current_action(state)["id"],
                                    {"outcome": "send-back", "summary": "The system commands are wrong."}))
            packet = self.next(run)
            self.assertIn("ShipLoop navigator | system-test-author |", packet)
            self.assertEqual(self.owes(packet), [])

    def test_after_add_work_the_corrective_items_first_stage_owes_the_note_and_the_revisited_stage_does_not(self) -> None:
        run, head = self.new_run("product-acceptance")
        self.note(run)
        add = {"outcome": "add-work", "summary": "R-1 needs a corrective item.", "headline": "One more item.",
               "evidence_refs": [str(self.evidence)],
               "work_items": [{"id": "W2", "title": "Correct it", "context": "The fix product-acceptance found."}]}
        self.accept(head, add)   # no rows: notes is a done-only field
        head = self.next(run)
        self.assertIn("ShipLoop navigator | step-plan |", head)
        self.assertEqual(self.owes(head), ["N1"])
        self.walk(run, self.at("product-acceptance"), rows={"step-plan": [row(detail="W2's plan reuses it")]})
        packet = self.next(run)
        self.assertEqual(self.owes(packet), [])
        self.assertIn("N1 already at step-plan of W2 (step ", packet)

    def test_handoff_owes_every_note_not_settled(self) -> None:
        run, _head = self.new_run("release-verify")
        self.note(run)
        self.walk(run, self.at("handoff"), rows={"release-verify": [row(did="carried", detail="handoff decides")]})
        self.note(run, SECOND)
        head = self.next(run)
        self.assertEqual(self.owes(head), ["N1", "N2"])


# ---------------------------------------------------------------------------- 5. a check's yes, and a closed loop


class CheckAndLoopTests(NoteRun):
    """Section 5, bullet 5."""

    def test_a_yes_from_check_then_a_note_then_complete_is_refused_and_recorded_as_a_no(self) -> None:
        run, head = self.new_run("discovery")
        command, path, action = contract.printed_callback(head)
        block = self.fill_done(head)
        contract.write_block(path, block)
        checked = self.run_printed(contract.check_command(command))
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn("The callback takes this answer", checked.stdout)   # a yes complete would reuse
        self.assertEqual(store.read_record(run / "checks" / f"{action}.md")["answer"], "yes")
        self.note(run)
        refused = self.refused(command, run)
        self.assertTrue(refused.startswith("ShipLoop navigator: owner note N1 is not accounted for: "), refused)
        answer = store.read_record(run / "checks" / f"{action}.md")
        self.assertEqual(answer["answer"], "no")
        self.assertIn("owner note N1 is not accounted for", answer["reason"])

    def test_a_note_after_an_inner_loop_closed_is_accepted_with_its_row_and_the_loop_not_run_again(self) -> None:
        run, head = self.new_run("test-spec")
        command, path, _action = contract.printed_callback(head)
        block = self.fill_done(head)
        contract.write_block(path, block)                        # the stage's loop runs and closes here
        closed = contract.read_block(path)
        receipt = nav.loops.receipt_path(run, _action)
        before = receipt.read_bytes()
        self.note(run)
        self.refused(command, run)
        contract.write_block(path, dict(closed, notes=[row()]), loop=False)    # the same receipt, cited again
        self.accepted(command)
        self.assertEqual(receipt.read_bytes(), before)


# ---------------------------------------------------------------------------- 6. a review


class ReviewTests(improve_cli.ImproveCliFixture):
    """Section 5, bullet 6, through the actual Improve CLI (the actual-improve-cli suite's fixture: a real bound child and
    runtime).  The producer at spec writes its result with a row for N1; the review imports it."""

    writing = True

    def _write_producer(self, stage):
        if stage == "spec" and self.writing:
            self.invoke(improve_cli.CLI, "note", "--run-dir", self.run, "--text", WORDS)
            self.producer["notes"] = [row()]
        super()._write_producer(stage)

    def parked(self) -> dict:
        self._start_parent_at_stage("spec", [str(self.product_contract)])
        seed = store.read_record(self.run / "state.md")["active_improve"]["seed_result"]
        self.assertEqual(seed["notes"], [row()])
        return seed

    def import_review(self, final_result=None, status=0):
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt(final_result=final_result)
        return self.invoke(improve_cli.CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion,
                           status=status)

    def accepted_rows(self) -> list:
        return store.read_record(self.run / "state.md")["accepted"][self.action].get("notes")

    def test_the_handoff_names_each_note_and_the_unchanged_result_imports(self) -> None:
        self.parked()
        handoff = nav.improve_handoff_path(self.bound).read_text(encoding="utf-8")
        self.assertIn("## Owner notes this result accounts for", handoff)
        self.assertIn("Read each note and check that the work does what its row says", handoff)
        self.assertIn(f"- N1 ({self.run}/owner-notes/N1.md): already: src/dates.py is already the only date code.",
                      handoff)
        self.import_review()
        self.assertEqual(self.accepted_rows(), [row()])

    def test_a_replacement_that_drops_a_row_is_refused_and_one_that_changes_it_imports(self) -> None:
        seed = self.parked()
        dropped = {key: value for key, value in seed.items() if key != "notes"}
        refused = self.import_review(dropped, status=2).stderr
        self.assertEqual(lines(refused)[0], "ShipLoop navigator: the review's result does not keep the owner notes rows "
                         f"of the reviewed result (N1): read {self.run}/owner-notes/N1.md, fix \"notes\" in "
                         f"{self.final_path}, then run the same callback again with --final-result set to that file.")
        self.assertIn("- N1 has no row, though the reviewed result had one: keep a row for it", refused)
        changed = dict(seed, notes=[row(did="applied", detail="The spec now names src/dates.py.")])
        completion, _receipt = self.completion_receipt(final_result=changed)
        self.invoke(improve_cli.CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        self.assertEqual(self.accepted_rows(), [row(did="applied", detail="The spec now names src/dates.py.")])

    def test_a_review_that_changes_the_outcome_leaves_the_note_owed(self) -> None:
        seed = self.parked()
        blocked = {"outcome": "blocked", "summary": "The spec needs the owner's choice of helper.",
                   "evidence_refs": seed["evidence_refs"],
                   "awaiting": {"kind": "answer", "question": "Which helper?", "no_default": "Two would do."}}
        self.import_review(blocked)
        state = store.read_record(self.run / "state.md")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(owner_notes.ledger(state), {})
        self.invoke(improve_cli.CLI, "resume", "--run-dir", self.run, "--answer", "Use src/dates.py.")
        packet = self.invoke(improve_cli.CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("ShipLoop navigator | spec |", packet)
        self.assertIn(f"  {WORDS}\n", packet.split("Owner notes this stage must account for (", 1)[1])

    def test_a_note_that_arrives_during_the_review_is_owed_by_the_next_stage_and_a_replay_passes(self) -> None:
        self.parked()
        self.invoke(improve_cli.CLI, "note", "--run-dir", self.run, "--text", SECOND)
        # The producer's exact replay of its parked result passes as before: not an admission.
        self.invoke(improve_cli.CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        # A replacement that takes N2 in is refused: the review keeps the parked rows.
        seed = store.read_record(self.run / "state.md")["active_improve"]["seed_result"]
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt(final_result=dict(seed, notes=[row(), row("N2")]))
        refused = self.invoke(improve_cli.CLI, "complete", "--run-dir", self.run, "--action", self.improve,
                              *completion, status=2).stderr
        self.assertIn("- N2 has a row the reviewed result did not have: a note that arrived during the review is the "
                      "next stage's; remove the row", refused)
        completion, _receipt = self.completion_receipt()
        out = self.invoke(improve_cli.CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        self.assertIn("ShipLoop navigator | test-strategy |", out.stdout)
        block = out.stdout.split("Owner notes this stage must account for (", 1)[1].split("Goal:", 1)[0]
        self.assertIn(f"  {SECOND}\n", block)
        self.assertNotIn(WORDS, block)
        self.assertIn("Owner notes accounted for: N1 already at spec (step ", out.stdout)

    def test_a_stage_the_script_records_owes_nothing_and_the_note_waits_for_the_next_producer(self) -> None:
        # The review stage itself is recorded by the script: with no row in the parked result, its import takes no note
        # in, whatever arrived, and the next producer owes them.
        self.writing = False
        self._start_parent_at_stage("spec", [str(self.product_contract)])
        self.invoke(improve_cli.CLI, "note", "--run-dir", self.run, "--text", WORDS)
        out = self.import_review().stdout
        self.assertIsNone(self.accepted_rows())
        self.assertIn("ShipLoop navigator | test-strategy |", out)
        self.assertIn(f"  {WORDS}\n", out.split("Owner notes this stage must account for (", 1)[1])


class ScriptRecordedTests(NoteRun):
    """Section 5, bullet 6, a stage the script records without a review: validate-existing, recorded in the transition
    that accepts test-spec when every expectation check matches.  A note written after test-spec's admission read the
    notes is not taken in by it nor by the stage the script records, and implement owes it (one read per admission)."""

    def test_a_note_written_after_the_admissions_read_waits_for_the_next_producer(self) -> None:
        run, head = self.new_run("test-spec")
        self.note(run)
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.result(head, row(detail="The cases test src/dates.py as it is.")))
        real_read = owner_notes.read

        def read_then_the_owner_writes(root):
            found = real_read(root)
            if not (Path(root) / owner_notes.DIR / "N2.md").exists():
                owner_notes.write(root, SECOND)
            return found
        with mock.patch.object(owner_notes, "read", read_then_the_owner_writes):
            code, out, err = run_main(shlex_split(command)[2:])
        self.assertEqual(code, 0, err)
        state = self.state(run)
        self.assertEqual([entry["stage"] for entry in state["history"][-2:]], ["test-spec", "validate-existing"])
        self.assertNotIn("notes", state["accepted"][state["history"][-1]["action"]])
        self.assertEqual(list(owner_notes.ledger(state)), ["N1"])
        self.assertIn("ShipLoop navigator | implement |", out)
        self.assertEqual(self.owes(out), ["N2"])
        self.assertEqual(self.owes(self.next(run)), ["N2"])


# ---------------------------------------------------------------------------- 7. outcomes that hold no rows


class OutcomeTests(NoteRun):
    """Section 5, bullet 7: blocked, paused, send-back and add-work hold no rows and leave the notes owed."""

    def test_a_blocked_result_holds_no_row_and_its_resumed_stage_owes_the_note(self) -> None:
        run, head = self.new_run("release-check")
        self.note(run)
        blocked = {"outcome": "blocked", "summary": "The release needs a sign-in.", "evidence_refs": [],
                   "awaiting": {"kind": "present", "steps": ["Sign in"], "report": "Signed in", "no_default": "None."}}
        refused = self.refuse(run, head, dict(blocked, notes=[row()]))
        self.assertIn("a blocked result does not carry notes", refused)
        self.accept(head, blocked)
        resumed = self.cli("resume", "--run-dir", str(run), "--observed", "Signed in.")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(self.owes(resumed.stdout), ["N1"])

    def test_a_paused_producer_owes_the_note_after_resume(self) -> None:
        run, _head = self.new_run("spec")
        self.assertEqual(self.cli("pause", "--run-dir", str(run), "--reason", "owner break").returncode, 0)
        wrote = self.note(run)
        self.assertIn("The run is paused at spec; N1 is accounted for by its done result after `resume`.", wrote.stdout)
        resumed = self.cli("resume", "--run-dir", str(run))
        self.assertEqual(self.owes(resumed.stdout), ["N1"])

    def test_a_send_back_holds_no_row_and_the_stage_it_reruns_owes_the_note(self) -> None:
        run, head = self.new_run("test", entered=True)
        self.note(run)
        sent = {"outcome": "send-back", "summary": "The step plan's focused command names the wrong file.",
                "headline": "Back to the step plan.", "evidence_refs": [str(self.evidence)]}
        self.accept(head, sent)
        packet = self.next(run)
        self.assertIn("ShipLoop navigator | step-plan |", packet)
        self.assertEqual(self.owes(packet), ["N1"])


# ---------------------------------------------------------------------------- 8. the end of the run


def shlex_split(command: str) -> list[str]:
    import shlex
    return shlex.split(command)


def run_main(argv: list[str]) -> tuple[int, str, str]:
    """The CLI's own entry point, run in this process so that a test can wrap one function; both streams captured."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
            mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "off"}):
        try:
            code = _CLI_MODULE.main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
    return code, out.getvalue(), err.getvalue()


def _load_cli():
    """The extensionless ``shiploop`` script as a module (its ``main`` passes itself to the protocol as the core)."""
    loader = importlib.machinery.SourceFileLoader("shiploop_cli_entry", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


_CLI_MODULE = _load_cli()


class EndTests(NoteRun):
    """Section 5, bullet 8."""

    def test_a_note_written_between_the_two_reads_at_handoff_refuses_the_completion(self) -> None:
        run, head = self.new_run("handoff")
        self.note(run)
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.result(head, row(did="declined", detail="Nothing is left to change.")))
        real_read, calls = owner_notes.read, []

        def second_read_finds_a_new_note(root):
            calls.append(1)
            if len(calls) == 2:
                owner_notes.write(root, SECOND)
            return real_read(root)
        with mock.patch.object(owner_notes, "read", second_read_finds_a_new_note):
            code, out, err = run_main(shlex_split(command)[2:])
        self.assertEqual((code, out), (2, ""), err)
        self.assertEqual(lines(err)[0],
                         f"ShipLoop navigator: owner note N2 arrived while this handoff was being completed and is not "
                         f"accounted for: read {run}/owner-notes/N2.md, add its row to \"notes\" in {path}, then run "
                         "this again.")
        self.assertEqual(self.state(run)["status"], "active")
        contract.write_block(path, self.result(head, row(did="declined", detail="Nothing is left to change."),
                                               row("N2", "declined", "The run is at its handoff.")))
        self.assertIn("It's all complete.", self.accepted(command))

    def test_a_note_written_after_the_run_ended_is_refused(self) -> None:
        run, head = self.new_run("handoff")
        self.accept(head, self.result(head))
        refused = self.note(run, status=2)
        self.assertIn("ShipLoop note: the run is done; no later step would read a note, so nothing was written.",
                      refused.stderr)
        self.assertFalse((run / owner_notes.DIR).exists())

    def test_the_note_command_says_so_when_the_run_ends_as_it_writes(self) -> None:
        run, head = self.new_run("handoff")
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.result(head))
        real_write = owner_notes.write

        def write_then_the_run_ends(root, text, **kwargs):
            note = real_write(root, text, **kwargs)
            # The model's completion read the notes before this note was written; its save lands now.
            with mock.patch.object(owner_notes, "read", lambda _root: []):
                code, _out, err = run_main(shlex_split(command)[2:])
            self.assertEqual(code, 0, err)
            return note
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(owner_notes, "write", write_then_the_run_ends), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = owner_notes.main(["--run-dir", str(run), "--text", WORDS])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), f"Owner note N1 written: {run}/owner-notes/N1.md.\n")
        self.assertEqual(err.getvalue(), "ShipLoop note: the run ended (done) while N1 was being written, so no stage "
                                         "read it and none will. Start a new run on this project with its words.\n")


# ---------------------------------------------------------------------------- 9. a run with no note; a stored row


class NoNoteTests(NoteRun):
    """Section 5, bullet 9."""

    def test_a_run_with_no_note_and_closed_standard_input_prints_and_stores_nothing_of_notes(self) -> None:
        run, head = self.new_run("intake")
        stages = []
        for _ in range(6):   # intake to plan: three of them start an Improve stage, whose import is synthetic here
            command, path, _action = contract.printed_callback(head)
            stages.append(re.search(r"ShipLoop navigator \| ([a-z-]+) \|", head).group(1))
            contract.write_block(path, self.result(head))
            done = subprocess.run(shlex_split(command), cwd=self.base, env=self.env, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            if self.state(run).get("active_improve") is not None:
                state = self.state(run)
                nav.save(run, nav.finish_improve(state, state["active_improve"]["action_id"],
                                                 {"summary": "Synthetic receipt; no review claim."}))
            head = self.next(run)
            for text in (done.stdout, head):
                self.assertNotIn("Owner note", text)
                self.assertNotIn('"notes"', text)
        state = self.state(run)
        self.assertTrue(all("notes" not in result for result in state["accepted"].values()), stages)
        self.assertNotIn("owner_notes", state)
        self.assertFalse((run / owner_notes.DIR).exists())
        self.assertNotIn("Your notes", self.cli("report", "--run-dir", str(run)).stdout)
        for event in store.read_jsonl(run / trace.TRACE_FILE):
            for key in ("held", "shown", "delivered", "notes", "note"):
                self.assertNotIn(key, event)

    def test_a_stored_result_with_notes_reloads_when_the_note_files_are_gone(self) -> None:
        run, head = self.new_run("discovery")
        self.note(run)
        self.accept(head, self.result(head, row()))
        for path in (run / owner_notes.DIR).iterdir():
            path.unlink()
        (run / owner_notes.DIR).rmdir()
        nav.validate(self.state(run))
        packet = self.next(run)
        self.assertIn("Owner notes accounted for: N1 already at discovery (step 2)", packet)
        report = self.cli("report", "--run-dir", str(run))
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn("<h3>N1: settled</h3>", report.stdout)
        self.assertIn("Its file (owner-notes/N1.md) is no longer in the run folder.", report.stdout)

    def test_a_run_saved_with_a_delivery_record_is_not_resumed(self) -> None:
        run, _head = self.new_run("intake")
        state = self.state(run)
        state["owner_notes"] = {"N1": nav.current_action(state)["id"]}
        store.write_record(run / "state.md", state)
        refused = self.cli("next", "--run-dir", str(run))
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("unexpected: owner_notes", refused.stderr)


# ---------------------------------------------------------------------------- 10. what the requester sees; sizes


class DisplayTests(NoteRun):
    """Section 5, bullet 10: the done packet, the report and trace; packet sizes."""

    def test_the_done_packet_the_report_and_the_trace_say_what_became_of_each_note(self) -> None:
        run, _head = self.new_run("prepare", results=THREE_ITEMS)
        self.note(run, WORDS)
        self.note(run, SECOND)
        self.walk(run, self.at("carry-forward", "W2"), results=THREE_ITEMS,
                  rows={"prepare": [row(), row("N2", "carried", "the date is the items' work")]})
        head = self.next(run)
        self.accept(head, self.result(head, row("N2", "applied", "W3 prints the date", item="W3")))
        self.note(run, "Name it <b>out.txt</b> & keep it.")
        self.walk(run, self.at("handoff"), results=THREE_ITEMS)
        head = self.next(run)
        self.assertEqual(self.owes(head), ["N3"])
        done = self.accept(head, self.result(head, row("N3", "declined", "The build already named its file.")))
        self.assertIn(f"Report: {run}/report.html\n"
                      "Your notes: 3 owner notes. In your last message tell the user what happened to each; the "
                      "report's section \"Your notes\" has each note's words and every row:\n"
                      "- N1: already at prepare: src/dates.py is already the only date code.\n"
                      "- N2: applied at carry-forward of W2 (item W3, completed): W3 prints the date\n"
                      "- N3: declined at handoff: The build already named its file.\n", done)
        report = (run / "report.html").read_text(encoding="utf-8")
        section = report[report.index("<h2>Your notes</h2>"):report.index("<h2>Accepted transitions</h2>")]
        self.assertLess(report.index("<h2>Original request</h2>"), report.index("<h2>Your notes</h2>"))
        self.assertIn("<pre>Name it &lt;b&gt;out.txt&lt;/b&gt; &amp; keep it.</pre>", section)
        self.assertNotIn("<b>out.txt</b>", section)
        self.assertIn("<td>carry-forward</td><td>W2</td><td>applied</td><td>W3 prints the date</td>"
                      "<td>W3 (completed)</td>", section)
        self.assertIn("<td>prepare</td><td>\u2014</td><td>carried</td><td>the date is the items&#x27; work</td>", section)
        model = trace.build(run)
        self.assertEqual([(note["id"], note["state"], [r["did"] for r in note["rows"]]) for note in model["notes"]],
                         [("N1", "settled", ["already"]), ("N2", "settled", ["carried", "applied"]),
                          ("N3", "settled", ["declined"])])
        digest = self.cli("trace", "--run-dir", str(run)).stdout
        self.assertIn("Notes:    3 owner notes · N1 settled (already at prepare #", digest)
        self.assertEqual(self.cli("trace", "--run-dir", str(run), "--html").returncode, 0)
        page = (run / trace.PAGE).read_text(encoding="utf-8")
        self.assertIn("function notesSection()", page)
        self.assertIn('open: ["amber", "open: no row yet"], carried: ["violet", "carried"], settled: ["green", '
                      '"settled"]', page)

    def test_a_halted_run_shows_its_open_notes_as_not_accounted_for(self) -> None:
        run, _head = self.new_run("spec")
        self.note(run)
        halted = self.cli("halt", "--run-dir", str(run), "--reason", "owner stop")
        self.assertEqual(halted.returncode, 0, halted.stderr)
        self.assertIn(f"Owner note N1 is not accounted for: the run stopped before a stage settled it ({run}/owner-notes/;"
                      " the report lists it).", halted.stdout)
        report = (run / "report.html").read_text(encoding="utf-8")
        self.assertIn("<h3>N1, written ", report)
        self.assertIn(": open</h3>", report)
        self.assertIn("<p>Not accounted for: no stage's result has a row for it.</p>", report)

    def test_the_block_keeps_its_bounds_with_a_long_note_several_notes_and_a_long_run_path(self) -> None:
        for label, texts, deep in (("one long note", ["x" * 1980], False),
                                   ("several notes", [f"Note {n}: " + "y" * 1800 for n in range(1, 6)], False),
                                   ("a long run path", [f"Note {n}: " + "z" * 1800 for n in range(1, 6)], True)):
            with self.subTest(label), tempfile.TemporaryDirectory(prefix="sl-notes-") as temp:
                run = Path(temp) / ("d" * 120 if deep else "r") / "run"
                run.mkdir(parents=True)
                state = nav.new_state(str(self.repo), "Add hello.", lint_option="off")
                nav.save(run, state)
                for text in texts:
                    owner_notes.write(run, text)
                waiting = owner_notes.owed(state, owner_notes.read(run), "intake", None)
                block, forms = owner_notes.packet_forms(run, state, "intake", waiting)
                named = re.compile(r"^ {4}N\d+(?:, N\d+)*(?: and N\d+)? (?:is|are) not printed here")
                self.assertLessEqual(sum(len(line) + 1 for line in block[1:-1] if not named.match(line)),
                                     owner_notes.BLOCK_LIMIT)
                self.assertEqual(block[-1], owner_notes.duty("intake"))
                self.assertTrue(all(form[-1] == owner_notes.duty("intake") for form in forms))
                if len(texts) > 3:
                    self.assertRegex(block[-2], r"^ {4}N4 and N5 are not printed here for room: read .*N4\.md and "
                                                r".*N5\.md before acting\.$")
                self.assertIn(str(run / owner_notes.DIR), block[0])


# ---------------------------------------------------------------------------- kept from the earlier suite


class NoteCommandTests(NoteRun):
    """What still holds of the note command: refused notes write nothing, an unloadable run is left as it was, a run
    with no note has no folder, and the reply says who accounts for the note."""

    def test_a_note_no_step_would_read_or_the_hooks_would_misread_is_refused_and_no_note_is_written(self) -> None:
        run, _head = self.new_run("intake")
        for text, reason in (("   \n  ", "the note is empty"),
                             ("x" * (owner_notes.NOTE_LIMIT + 1), "over the 2,000 a packet quotes whole"),
                             ("x\n" * 1000, "as a packet quotes it (each line indented)"),
                             ("see Keepalive marker: SHIPLOOP-RUN run=x rev=1 dir=/tmp", "'SHIPLOOP-RUN'"),
                             ("=== end ShipLoop print ===", "'=== end ShipLoop'"),
                             ("bell \x07 here", "control character")):
            with self.subTest(reason=reason):
                result = self.note(run, text, status=2)
                self.assertIn(reason, result.stderr)
                self.assertIn("nothing was written", result.stderr)
                self.assertFalse((run / owner_notes.DIR).exists())
        self.assertEqual([row for row in store.read_jsonl(run / trace.TRACE_FILE) if row.get("verb") == "note"], [])

    def test_a_halted_run_refuses_a_note(self) -> None:
        run, _head = self.new_run("intake")
        self.assertEqual(self.cli("halt", "--run-dir", str(run), "--reason", "owner stop").returncode, 0)
        result = self.note(run, "Too late.", status=2)
        self.assertIn("the run is halted; no later step would read a note", result.stderr)
        self.assertFalse((run / owner_notes.DIR).exists())

    def test_a_run_that_cannot_be_loaded_or_does_not_exist_is_left_exactly_as_it_was(self) -> None:
        run, _head = self.new_run("intake")
        state = self.state(run)
        state["version"] = 1
        store.write_record(run / "state.md", state)
        before = {str(path): path.read_bytes() for path in run.rglob("*") if path.is_file()}
        result = self.note(run, "Hello?", status=2)
        self.assertIn("is not a current ShipLoop run", result.stderr)
        self.assertEqual({str(path): path.read_bytes() for path in run.rglob("*") if path.is_file()}, before)
        missing = self.cli("note", "--run-dir", str(self.base / "absent"), "--text", "Hello?")
        self.assertEqual(missing.returncode, 2)
        self.assertFalse((self.base / "absent").exists())

    def test_text_with_a_byte_that_is_not_utf8_is_refused_and_writes_nothing(self) -> None:
        run, _head = self.new_run("intake")
        refused = self.cli("note", "--run-dir", str(run), "--text", os.fsdecode(b"caf\xe9 is one byte"))
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("ShipLoop note: the note holds a byte that is not UTF-8 text", refused.stderr)
        self.assertNotIn("Traceback", refused.stderr)
        bad_file = self.base / "note.txt"
        bad_file.write_bytes(b"caf\xe9 is one byte")
        from_file = self.cli("note", "--run-dir", str(run), "--file", str(bad_file))
        self.assertEqual(from_file.returncode, 2, from_file.stdout + from_file.stderr)
        self.assertIn("the file is not UTF-8 text", from_file.stderr)
        self.assertFalse((run / owner_notes.DIR).exists())

    def test_a_run_without_notes_writes_no_note_file(self) -> None:
        run, _head = self.new_run("intake")
        self.next(run)
        self.assertFalse((run / owner_notes.DIR).exists())

    def test_the_reply_says_who_accounts_for_the_note(self) -> None:
        run, _head = self.new_run("implement")
        action = nav.current_action(self.state(run))["id"]
        self.assertEqual(self.note(run).stdout,
                         f"Owner note N1 written: {run}/owner-notes/N1.md.\n"
                         f"The run is at W1 implement (action {action}); N1 is accounted for by its done result, which "
                         "ShipLoop checks for a row when it is next checked or completed (a result already being read "
                         "leaves it to the next stage's).\n")

    def test_a_notes_folder_that_cannot_be_read_refuses_the_result(self) -> None:
        run, head = self.new_run("intake")
        self.note(run)
        folder = run / owner_notes.DIR
        folder.chmod(0o000)
        self.addCleanup(folder.chmod, 0o700)
        refused = self.refuse(run, head, self.result(head, row()))
        self.assertTrue(self.first_line(refused).startswith("ShipLoop navigator: the owner notes folder cannot be read ("),
                        refused)
        self.assertIn(f"): {folder}, so ShipLoop cannot tell", self.first_line(refused))
        self.assertIn("so ShipLoop cannot tell which owner notes this result must account for", refused)


class NoteFileTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-owner-notes-")
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name)

    def test_notes_take_the_next_free_number_and_leave_no_temporary_file(self) -> None:
        first = owner_notes.write(self.run, "one")
        (self.run / owner_notes.DIR / "N2.md").write_text(store.dumps(
            {"id": "N2", "written_at": "2026-10-26T10:00:00Z", "text": "two"}, owner_notes.TITLE), encoding="utf-8")
        third = owner_notes.write(self.run, "three\r\nsecond line   \n\n")
        self.assertEqual((first["id"], third["id"]), ("N1", "N3"))
        self.assertEqual(sorted(path.name for path in (self.run / owner_notes.DIR).iterdir()),
                         ["N1.md", "N2.md", "N3.md"])
        self.assertEqual([note["text"] for note in owner_notes.read(self.run)], ["one", "two", "three\nsecond line"])
        self.assertEqual(oct((self.run / owner_notes.DIR / "N3.md").stat().st_mode & 0o777), "0o600")

    def test_a_long_many_line_note_is_refused_by_the_size_of_its_quote(self) -> None:
        many = "\n".join(["y" * 40] * 45)   # 1,844 characters; quoted with indentation, over 2,000
        self.assertLess(len(many), owner_notes.NOTE_LIMIT)
        with self.assertRaisesRegex(owner_notes.NoteError, "as a packet quotes it"):
            owner_notes.clean(many)
        fits = "\n".join(["y" * 40] * 40)
        note = owner_notes.write(self.run, fits)
        self.assertLessEqual(len("\n".join(owner_notes.quote(note))), owner_notes.NOTE_LIMIT)

    def test_a_stored_row_keeps_its_shape_only_and_reproduces_itself(self) -> None:
        rows = [{"note": " N1 ", "did": "maybe", "anything": "x\n"}]
        canonical = owner_notes.canonical(rows)
        self.assertEqual(canonical, [{"note": "N1", "did": "maybe", "anything": "x"}])
        self.assertEqual(owner_notes.canonical(canonical), canonical)
        for bad in ("N1", [["N1"]], [{"note": 3}]):
            with self.subTest(bad=bad), self.assertRaises(owner_notes.NoteError):
                owner_notes.canonical(bad)


class PageTests(NoteRun):
    def test_the_page_screens_each_note_and_builds_the_command_to_leave_one(self) -> None:
        run, head = self.new_run("intake")
        self.note(run, "Ship it in English only.")
        self.note(run, "api_key = sk-live-abcdef1234567890abcdef")
        self.accept(head, self.result(head, row(), row("N2", "declined", "a key is not an instruction")))
        model = trace.build(run)
        self.assertEqual([(note["id"], note["state"]) for note in model["notes"]], [("N1", "settled"), ("N2", "settled")])
        self.assertEqual(model["run"]["cli"], str(CLI.resolve()))
        self.assertEqual(self.cli("trace", "--run-dir", str(run), "--html").returncode, 0)
        html = (run / trace.PAGE).read_text(encoding="utf-8")
        self.assertIn("Ship it in English only.", html)
        self.assertNotIn("sk-live-abcdef1234567890abcdef", html)
        self.assertIn("account for the note with a row, and ShipLoop refuses it until it does.", html)



# ---------------------------------------------------------------------------- the code review's fixes (fix brief)
#
# The outside review of the first build ("Fix first") and the fix brief's decisions; the owner's word of 17:00 kept
# the first pass to items 3, 7 (a) to (c) and 13, and the accepted candidate's brief (A to J) adds the rest that main
# needs.  Each class names its item.

EXCEPTION = ("unless an owner note this stage owes asks for the requirement change: then rewrite the requirement in "
             "place, queue the work and report done")
# carry-forward's duty 1 keeps spec.md as the steps wrote it (2026-11-22); its one exception is the rewrite EXCEPTION allows.
SPEC_EXCEPTION = ("except a requirement that an owner note this stage owes asks to change (rewrite that entry in place, as "
                  "the owner notes block says)")
# document's duty: six real deliveries of six that got a note during the build sent the step back to step-plan; none
# finished the step as planned (accept brief, item H).  Since 2026-11-22 it asks for what the requirement must say too.
DOCUMENT_SENTENCE = ("Add lines only; a requirement whose intent moved is no edit: report send-back naming the R-<n> and what "
                     "it must say.")
# step-plan's knowledge duty with the clause every delivery's route needs (coordinator's item K): the four sessions that
# got a note during the build sent the step back and rewrote the requirement at step-plan, against the released "write
# nothing else in KNOWLEDGE/".
STEP_PLAN_EXCEPTION = ("Keep every R-<n> and AD-<n>; write nothing else in KNOWLEDGE/, unless an owner note this stage "
                       "owes asks for a requirement change: then rewrite that requirement in place in KNOWLEDGE/spec.md "
                       "(the ID stays; its entry keeps no copy of the old clause) and plan the step for the rewritten "
                       "text.")


def flat(text: str) -> str:
    return " ".join(text.split())


class StandingTextTests(unittest.TestCase):
    """Fix brief item 3, accept brief item H and item K: the carry-forward duty and the carry-forward loop's rule carry
    the owner-note exception in their standing text, whatever notes are on file (that stage cannot send back); document's
    duty says no word of a note, so a stage of a work item whose step a note changes may send it back; and step-plan's
    knowledge duty lets it rewrite the requirement such a note changes, which is where every such delivery did it."""

    def test_carry_forward_carries_the_exception_and_document_its_own_sentence(self) -> None:
        import shiploop_loops as loops
        import shiploop_prompts as prompts
        for route in (prompts.INLINE, prompts.ASK_AGENT):
            with self.subTest(route=route):
                document = flat(prompts.duty("document", delegation=route))
                self.assertIn(DOCUMENT_SENTENCE + " ", document)
                self.assertNotIn("owner note", document.lower())
                self.assertIn("stop the loop and report blocked; it is no queue edit, " + EXCEPTION,
                              flat(prompts.duty("carry-forward", delegation=route)))
                self.assertIn(STEP_PLAN_EXCEPTION, flat(prompts.duty("step-plan", delegation=route)))
        self.assertIn("that is not a queue edit, " + EXCEPTION + ".", loops.REPEAT["carry-forward"])
        for stage in ("step-plan", "test-spec", "validate-existing", "implement", "test", "document"):
            with self.subTest(stage=stage):
                self.assertNotIn("finished as planned", flat(owner_notes.duty(stage)))
                self.assertNotIn("not a send-back", flat(owner_notes.duty(stage)))


class StandingTextPacketTests(NoteRun):
    """Fix brief item 3 and accept brief item H, as a run with no note prints it (the parity claim narrowed to these
    clauses): the document packet names no owner note, the carry-forward packet names one only in its two standing
    clauses (duty 1's spec line and duty 2), and the carry-forward loop's contract carries the rule.  The carry-forward of
    a run with one step in one item prints its queue duty in a short form with no rule to block on a changed requirement,
    so no exception there either; a run with items still to come prints the whole duty."""

    def test_a_run_with_no_note_names_an_owner_note_only_in_the_standing_clauses(self) -> None:
        run, _head = self.new_run("prepare", results=THREE_ITEMS)
        self.walk(run, self.at("step-plan", "W1"), results=THREE_ITEMS)
        packet = flat(self.next(run))
        self.assertIn(STEP_PLAN_EXCEPTION, packet)
        self.assertEqual(packet.lower().count("owner note"), 1)
        self.walk(run, self.at("document", "W1"), results=THREE_ITEMS)
        packet = flat(self.next(run))
        self.assertIn(DOCUMENT_SENTENCE, packet)
        self.assertNotIn("owner note", packet.lower())
        self.walk(run, self.at("carry-forward", "W1"), results=THREE_ITEMS)
        packet = flat(self.next(run))
        action = nav.current_action(self.state(run))["id"]
        rule = json.loads((run / nav.loops.contract_path(action)).read_text(encoding="utf-8"))["repeat_condition"]
        self.assertIn(EXCEPTION, rule)
        self.assertIn("it is no queue edit, " + EXCEPTION, packet)
        self.assertEqual(packet.count(SPEC_EXCEPTION), 1)
        self.assertEqual(packet.lower().count("owner note"), packet.count(EXCEPTION) + SPEC_EXCEPTION.count("owner note"))
        self.assertNotIn("Owner notes", packet)
        self.assertFalse((run / owner_notes.DIR).exists())


class FirstLineTests(NoteRun):
    """Fix brief item 7 (a) to (c): the first line for a row whose "note" is no id (no crash), for notes given as a
    scalar and for two rows for one note says what to do, on both commands, and the check records its no."""

    def test_a_non_id_row_a_scalar_and_a_duplicate_each_get_their_own_first_line(self) -> None:
        run, _head = self.new_run("intake")
        self.note(run)
        head = self.next(run)
        _command, path, action = contract.printed_callback(head)
        for label, rows, first in (
                ("a row that names no note id", [row(), row("typo")],
                 (f'"notes" has a row whose "note" is "typo", which is not an owner note id (N<k>): fix or remove it '
                  f"in {path}, then run this again.")),
                ("a scalar", "N1", (f'"notes" is not a list: give it in {path} as a list with one row per owed note '
                                    "(N1), then run this again.")),
                ("two rows for one note", [row(), row()],
                 f'"notes" has two rows for N1: keep exactly one in {path}, then run this again.')):
            with self.subTest(label):
                block = self.result(head)
                block["notes"] = rows
                for verb, prefix in (("check", "ShipLoop check: "), ("complete", "ShipLoop navigator: ")):
                    self.assertEqual(self.first_line(self.refuse(run, head, block, verb=verb)), prefix + first)
                self.assertEqual(store.read_record(run / "checks" / f"{action}.md")["answer"], "no")


class CurrentItemMessageTests(NoteRun):
    """Fix brief item 13: the refusal of an item that is the one this carry-forward closes lists the pending items."""

    def test_the_current_item_refusal_lists_the_queue(self) -> None:
        run, _head = self.new_run("prepare", results=THREE_ITEMS)
        self.walk(run, self.at("carry-forward", "W2"), results=THREE_ITEMS)
        self.note(run)
        head = self.next(run)
        refused = self.refuse(run, head, self.result(head, row(did="applied", detail="done here", item="W2")))
        self.assertIn('"item" is W2, the item this carry-forward closes: name a pending item of the future queue this '
                      'result leaves that does the work (W3), or say "already" when the run already does it', refused)
        self.assertNotIn("{listed}", refused)


# ---------------------------------------------------------------------------- the accepted candidate (accept brief)


class UnreadableNoteTests(NoteRun):
    """Accept brief item A: a note file that cannot be read, or whose record cannot be parsed, refuses the admission
    with a first line that names the file and says what to do; only names that are not N<k>.md are left out."""

    def test_an_unreadable_or_broken_note_file_refuses_check_and_complete_and_names_the_file(self) -> None:
        run, _head = self.new_run("discovery")
        self.note(run)
        self.note(run, SECOND)
        head = self.next(run)
        _command, path, _action = contract.printed_callback(head)
        block = self.result(head, row(), row("N2"))
        first = run / owner_notes.DIR / "N1.md"
        first.chmod(0o000)
        self.addCleanup(first.chmod, 0o600)
        for verb, prefix in (("check", "ShipLoop check: "), ("complete", "ShipLoop navigator: ")):
            refused = self.refuse(run, head, block, verb=verb)
            self.assertEqual(self.first_line(refused),
                             f"{prefix}an owner note cannot be read (Permission denied): {first}, so ShipLoop cannot tell "
                             "which owner notes this result must account for: make it readable as the note command "
                             f"wrote it, then run this again (the result file {path} needs no change for this).")
        first.chmod(0o600)
        second = run / owner_notes.DIR / "N2.md"
        second.write_text("not a note record\n", encoding="utf-8")
        refused = self.refuse(run, head, block)
        self.assertTrue(self.first_line(refused).startswith("ShipLoop navigator: an owner note is not a note record ("),
                        refused)
        self.assertIn(f"): {second}, so ShipLoop cannot tell", self.first_line(refused))
        # The packet still shows the notes that read as notes.
        self.assertEqual(self.owes(self.next(run)), ["N1"])
        # A file whose name is not N<k>.md is no note: it is left out.
        second.unlink()
        (run / owner_notes.DIR / "N2.md.bak").write_text("anything\n", encoding="utf-8")
        self.accept(head, self.result(head, row()))


class NoteIdTests(NoteRun):
    """Accept brief item B: a new note's id is above every id on file and in the ledger, and the done packet, the
    report and the trace list the ids on file with the ids in the ledger."""

    def test_a_new_note_never_takes_the_id_of_a_settled_note_whose_file_is_gone(self) -> None:
        run, head = self.new_run("discovery")
        self.note(run)
        self.accept(head, self.result(head, row()))
        (run / owner_notes.DIR / "N1.md").unlink()
        wrote = self.note(run, SECOND)
        self.assertTrue(wrote.stdout.startswith(f"Owner note N2 written: {run}/owner-notes/N2.md."), wrote.stdout)
        head = self.next(run)
        self.assertEqual(self.owes(head), ["N2"])
        self.accept(head, self.result(head, row("N2", detail="research already prints the date")))
        report = self.cli("report", "--run-dir", str(run)).stdout
        self.assertIn("<h3>N1: settled</h3>", report)
        self.assertIn("<p>Its file (owner-notes/N1.md) is no longer in the run folder.</p>", report)
        notes = trace.build(run)["notes"]
        self.assertEqual([(note["id"], note["state"], note.get("file_gone")) for note in notes],
                         [("N1", "settled", True), ("N2", "settled", False)])
        self.walk(run, self.at("handoff"))
        head = self.next(run)
        done = self.accept(head, self.result(head))
        self.assertIn("- N1: already at discovery: src/dates.py is already the only date code. (its file is no longer "
                      "in the run folder)\n- N2: already at research: research already prints the date\n", done)

    def test_a_new_note_never_takes_the_id_of_a_parked_rows_note(self) -> None:
        run, head = self.new_run("spec")
        self.note(run)
        self.accept(head, self.result(head, row()))            # spec parks its result for the review
        self.assertEqual(self.state(run)["active_improve"]["seed_result"]["notes"], [row()])
        (run / owner_notes.DIR / "N1.md").unlink()
        self.assertTrue(self.note(run, SECOND).stdout.startswith(f"Owner note N2 written: {run}/owner-notes/N2.md."))


class RowTextTests(NoteRun):
    """Accept brief item C: detail and item refuse the placeholder forms the packet names and a lone surrogate."""

    def test_placeholder_forms_and_a_lone_surrogate_are_refused(self) -> None:
        run, _head = self.new_run("intake")
        self.note(run)
        head = self.next(run)
        for label, detail in (("an ellipsis", "..."), ("an ellipsis character", "…"), ("a text in angle brackets",
                                                                                            "<text>"),
                              ("the template's detail", owner_notes.DETAIL_PLACEHOLDER)):
            with self.subTest(label):
                refused = self.refuse(run, head, self.result(head, row(detail=detail)))
                self.assertIn('- N1\'s row "detail" still holds a placeholder ("...", a text in angle brackets or the '
                              "template's own): write what this stage did with the note", refused)
        _command, path, _action = contract.printed_callback(head)
        block = self.result(head, row(detail="SURROGATE"))
        before = (run / "state.md").read_bytes()
        path.write_text("```shiploop-state\n" + json.dumps(block).replace("SURROGATE", "\\ud800") + "\n```\n",
                        encoding="utf-8")
        done = self.run_printed(contract.printed_callback(head)[0])
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn('- N1\'s row "detail" holds a character that is not UTF-8 text: write plain text', done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertEqual((run / "state.md").read_bytes(), before)
        # A text that only starts and ends with angle brackets is no placeholder.
        self.accept(head, self.result(head, row(detail="<details> already opens on a click on its <summary>")))

    def test_an_item_in_angle_brackets_is_refused_at_plan(self) -> None:
        run, _head = self.new_run("plan")
        self.note(run)
        head = self.next(run)
        refused = self.refuse(run, head, self.result(head, row(did="applied", detail="W1 does it", item="<W1>")))
        self.assertIn('- N1\'s row "item" still holds a placeholder ("...", a text in angle brackets or the template\'s '
                      "own): write the work item that does it", refused)


class ImportRefusalTests(improve_cli.ImproveCliFixture):
    """Accept brief items D and E: the import's refusal names the notes and their folder in its first line and keeps its
    own repair route, and a malformed notes field is refused there when the parked result had no row."""

    writing = True

    def _write_producer(self, stage):
        if stage == "spec" and self.writing:
            self.invoke(improve_cli.CLI, "note", "--run-dir", self.run, "--text", WORDS)
            self.producer["notes"] = [row()]
        super()._write_producer(stage)

    def import_with(self, final: dict, status: int) -> str:
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt(final_result=final)
        done = self.invoke(improve_cli.CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion,
                           status=status)
        self.assertEqual(done.stdout, "")
        return done.stderr

    def test_a_dropped_row_is_refused_with_the_note_and_its_folder_in_the_first_line(self) -> None:
        self._start_parent_at_stage("spec", [str(self.product_contract)])
        seed = store.read_record(self.run / "state.md")["active_improve"]["seed_result"]
        refused = self.import_with({key: value for key, value in seed.items() if key != "notes"}, 2)
        self.assertEqual(lines(refused)[0],
                         "ShipLoop navigator: the review's result does not keep the owner notes rows of the reviewed "
                         f"result (N1): read {self.run}/owner-notes/N1.md, fix \"notes\" in {self.final_path}, then run "
                         "the same callback again with --final-result set to that file.")
        self.assertIn('\nA row: {"note": "N<k>", "did": ', refused)
        self.assertIn("\n- N1 has no row, though the reviewed result had one: keep a row for it\n", refused)
        self.assertIn(f"Z  {WORDS}\n", refused)

    def test_a_malformed_notes_field_is_refused_at_import_when_the_parked_result_had_no_row(self) -> None:
        self.writing = False
        self._start_parent_at_stage("spec", [str(self.product_contract)])
        seed = store.read_record(self.run / "state.md")["active_improve"]["seed_result"]
        self.assertNotIn("notes", seed)
        refused = self.import_with(dict(seed, notes=None), 2)
        self.assertEqual(lines(refused)[0],
                         "ShipLoop navigator: the review's result gives \"notes\" that is not a list: give it in "
                         f"{self.final_path} as [] or leave it out (the reviewed result accounted for no note), then run "
                         "the same callback again with --final-result set to that file.")


class HelpTextTests(NoteRun):
    """Accept brief item G: the CLI's help and the README's steering section say the row rule."""

    def test_the_help_and_the_readme_say_the_note_is_accounted_for_by_a_row(self) -> None:
        shown = self.cli("--help").stdout
        self.assertIn("the run's owner: leave a note the next done result must account for with a row (applied, "
                      "already, carried or declined; --text or --file)", flat(shown))
        readme = (ROOT / "skills/shiploop/README.md").read_text(encoding="utf-8")
        section = readme.split("### 5. Steer a run in flight", 1)[1].split("### 6.", 1)[0]
        self.assertIn("The next done result must account for the note with a row in its `notes` (applied, already, "
                      "carried or declined), and ShipLoop refuses that result until it does.", flat(section))
        self.assertNotIn("until a step that showed it is accepted", section)


class SecondStepTests(NoteRun):
    """A guard of the ledger itself (the review: a ledger that kept only the latest implement result would pass a
    fixture that stops at S2's packet): S2's result with no row for a note S1 settled is accepted, through the CLI."""

    TWO_STEPS: typing.ClassVar[dict] = {"step-plan": dict(
        contract.STEP_PLAN, follows=[], paths=["built.txt", "more.txt"],
        steps=[dict(contract.STEP_PLAN["steps"][0]),
               {"id": "S2", "task": "Create more.txt", "deps": ["S1"], "criteria": ["C1"],
                "proof": "test -f more.txt", "skills": []}],
        expectations=[*contract.STEP_PLAN["expectations"],
                      {"id": "E2", "state": "absent", "statement": "more.txt does not exist yet.", "steps": ["S2"],
                       "paths": ["more.txt"], "check": "test ! -e more.txt"}])}

    def test_the_second_steps_result_owes_no_row_for_a_note_the_first_step_settled(self) -> None:
        run, _head = self.new_run("implement", results=self.TWO_STEPS)
        self.note(run)
        self.walk(run, lambda state: nav.current_stage(state) == "implement"
                  and (nav.loops.current_step(state, "W1") or {}).get("id") == "S2",
                  results=self.TWO_STEPS, rows={"implement": [row()]})
        head = self.next(run)
        self.assertEqual(self.owes(head), [])
        (self.repo_of(run) / "more.txt").write_text("more\n")
        self.accept(head, self.result(head))
        state = self.state(run)
        self.assertEqual([entry["did"] for entry in owner_notes.ledger(state)["N1"]], ["already"])
        self.assertEqual(sum(1 for entry in state["history"] if entry["stage"] == "implement"), 2)


class ReconcileTakesOutTheSettlingResultTests(NoteRun):
    """A guard of the ledger itself (the review: a ledger of the current view would pass a reconcile that keeps the
    settling result): the note is settled at research, the real improve-reconcile route (the navigator-v4 suite's
    helpers) rewinds to discovery, before it, and the fresh results after the rewind owe no row."""

    for _name in ("stopped_packet", "reconciliation_input", "cli_reconcile"):
        locals()[_name] = v4.NavigatorV4Tests.__dict__[_name]
    del _name

    def test_the_fresh_results_after_the_rewind_owe_no_row(self) -> None:
        run, head = self.new_run("research")
        self.note(run)
        self.accept(head, self.result(head, row(detail="research picks src/dates.py")))
        state = self.walk(run, self.at("plan"))
        action = nav.current_action(state)["id"]
        waiting = nav.apply(state, action, {**contract.DONE, "work_items": [dict(ITEMS[0])]})
        self.skill = bridge.resolve_skill(str(contract.CARD))
        child = bridge.binding(waiting, action, "plan", waiting["active_improve"]["seed_result"], self.skill,
                               improve_action=waiting["active_improve"]["improve_action"])
        nav.save(run, dict(waiting, active_improve=child))
        self.run = run
        self.stopped_packet(child)
        _receipt, path, _evidence = self.reconciliation_input(action, target="discovery")
        reconciled = self.cli_reconcile(child["improve_action"], path)   # the command names the Improve stage
        self.assertEqual(reconciled.returncode, 0, reconciled.stdout + reconciled.stderr)
        for stage in ("discovery", "research"):
            with self.subTest(stage):
                head = self.next(run)
                self.assertIn(f"ShipLoop navigator | {stage} |", head)
                self.assertEqual(self.owes(head), [])
                self.accept(head, self.result(head))
        self.assertEqual([entry["stage"] for entry in owner_notes.ledger(self.state(run))["N1"]], ["research"])


class RouteRun(NoteRun):
    """A run whose item goes back to step-plan, with the planning review on: the review's import, the living spec and
    R-1's rewrite."""

    OLD_R1 = "- R-1: built.txt exists."
    NEW_R1 = "- R-1: built.txt exists and holds the greeting the owner's note N1 asks for."

    def commit_spec(self, run: Path) -> Path:
        """R-1's entry as the spec stage's knowledge commit leaves it (the positioning records results without commits)."""
        living = self.repo_of(run) / nav.knowledge.HOME / "spec.md"
        living.parent.mkdir(parents=True, exist_ok=True)
        living.write_text(contract.LIVING_SPEC, encoding="utf-8")
        self.assertTrue(nav.knowledge.commit(self.state(run), "spec").commit)
        return living

    def finish_review(self, run: Path) -> str:
        """Finish a parked review with the pure API and run what its import runs after the gates (the save, the
        transition, the knowledge commit: ``accept_effects``), so a home the reviewed stage changed is committed."""
        state = self.state(run)
        if state.get("active_improve") is not None:
            action = state["active_improve"]["action_id"]
            finished = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
            nav.accept_effects(types.SimpleNamespace(PACKAGE_ROOT=SCRIPTS.parent), run, state, finished,
                               action_id=action)
        return self.next(run)

    def spec_of(self, run: Path, ref: str | None = None) -> str:
        """The living spec in the working tree, or as commit ``ref`` holds it."""
        repo = self.repo_of(run)
        if ref is None:
            return (repo / nav.knowledge.HOME / "spec.md").read_text(encoding="utf-8")
        return subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{nav.knowledge.HOME}/spec.md"],
                              capture_output=True, text=True, check=True).stdout

    def rewrite_r1(self, run: Path) -> None:
        path = self.repo_of(run) / nav.knowledge.HOME / "spec.md"
        path.write_text(self.spec_of(run).replace(self.OLD_R1, self.NEW_R1), encoding="utf-8")


class RouteTests(RouteRun):
    """The route every real delivery took (accept brief, "Tests"), pinned through the CLI: a note written while
    implement is open is refused there; the step goes back to step-plan with a send-back that holds no row; step-plan
    owes the row and is accepted with applied; the item's later stages and its carry-forward owe nothing.  And the
    other shape seen: carried at step-plan, then already at that item's carry-forward."""

    def test_a_note_during_implement_goes_back_to_step_plan_and_is_settled_there(self) -> None:
        run, head = self.new_run("implement")
        living = self.commit_spec(run)
        self.note(run)
        refused = self.refuse(run, head, self.result(head), verb="check", loop=False)   # a check runs inside the loop
        self.assertTrue(self.first_line(refused).startswith("ShipLoop check: owner note N1 is not accounted for: read "),
                        refused)
        # The rewrite the note asks for is refused here, at implement (step_spec_refusal names the send-back).
        self.rewrite_r1(run)
        (self.repo_of(run) / "built.txt").write_text("hello\n")
        refused = self.refuse(run, head, self.result(head, row(did="applied", detail="R-1 now says what N1 asks")))
        self.assertIn("; to change a requirement, report send-back naming it and what it must say.", refused)
        self.assertIn("Found: changed or removed: " + self.OLD_R1, refused)
        living.write_text(contract.LIVING_SPEC, encoding="utf-8")       # the tree as the step began, for the send-back
        (self.repo_of(run) / "built.txt").unlink()
        sent = {"outcome": "send-back", "summary": "The owner's note changes R-1; the step plan must follow it.",
                "headline": "Back to the step plan for N1.", "evidence_refs": [str(self.evidence)]}
        # The step's loop stops blocked for the send-back; the result is then sent again without the row.
        self.assertIn("a send-back result does not carry notes", self.refuse(run, head, dict(sent, notes=[row()])))
        head = self.accept(head, sent, loop=False)
        self.assertIn("ShipLoop navigator | step-plan |", head)
        self.assertEqual(self.owes(head), ["N1"])
        self.refuse(run, head, self.result(head))
        # step-plan rewrites the requirement in place (the ID stays, no copy of the old clause) and is accepted; the
        # import of its review commits the home, so the steps after it start from the rewritten spec.
        self.rewrite_r1(run)
        head = self.accept(head, self.result(head, row(did="applied", detail="R-1 and the step plan now say what N1 "
                                                                              "asks")))
        head = self.finish_review(run)
        self.assertIn(self.NEW_R1, self.spec_of(run, "HEAD"))
        self.assertNotIn(self.OLD_R1, self.spec_of(run, "HEAD"))
        for stage in ("test-spec", "implement", "test", "document", "carry-forward"):
            with self.subTest(stage):
                if "ShipLoop navigator | improve |" in head:
                    head = self.finish_review(run)
                self.assertIn(f"ShipLoop navigator | {stage} |", head)
                self.assertEqual(self.owes(head), [])
                if stage == "implement":
                    (self.repo_of(run) / "built.txt").write_text("hello\n")
                done = self.accept(head, self.result(head))
                head = done if "ShipLoop navigator |" in done else self.next(run)
        self.finish_review(run)                   # the last item's carry-forward waits for its review
        ledger = owner_notes.ledger(self.state(run))
        self.assertEqual([(entry["stage"], entry["did"]) for entry in ledger["N1"]], [("step-plan", "applied")])

    def test_a_note_carried_at_step_plan_is_settled_at_that_items_carry_forward(self) -> None:
        run, _head = self.new_run("step-plan")
        self.note(run)
        head = self.next(run)
        self.accept(head, self.result(head, row(did="carried", detail="the requirement is the item's to change")))
        self.finish_review(run)
        self.walk(run, self.at("carry-forward"))
        head = self.next(run)
        self.assertEqual(self.owes(head), ["N1"])
        self.assertIn("      Carried here by step-plan of W1 (step ", head)
        self.accept(head, self.result(head, row(detail="the item already does what N1 asks")))
        self.finish_review(run)                   # the last item's carry-forward waits for its review
        ledger = owner_notes.ledger(self.state(run))
        self.assertEqual([(entry["stage"], entry["did"]) for entry in ledger["N1"]],
                         [("step-plan", "carried"), ("carry-forward", "already")])


class RequirementRouteTests(RouteRun):
    """The same route with no note (owner, 2026-11-22: "Let step-plan rewrite"; design of 2026-11-22): a step finds that a
    requirement must change and sends back naming it; the redone step plan rewrites the entry in place, says so in its
    summary and is accepted through its review; the rewrite is in HEAD, test-spec quotes it through ``follows``, the next
    implement's step gate takes it as its baseline, and the done packet and the report tell the requester."""

    NEW_R1 = ("- R-1: built.txt exists and ends with a line break (revised at step-plan: the reader drops an unterminated "
              "line, evidence.txt).")
    SUMMARY = ("Revised R-1: built.txt now ends with a line break, because the reader drops an unterminated line. Retains "
               "the sh harness.")

    def sent(self) -> dict:
        return {"outcome": "send-back", "headline": "R-1 must change.", "evidence_refs": [str(self.evidence)],
                "summary": "R-1 must say that built.txt ends with a line break, because the reader drops an unterminated "
                           "line (evidence.txt)."}

    def test_a_requirement_a_step_finds_must_change_is_rewritten_at_the_redone_step_plan(self) -> None:
        run, head = self.new_run("implement")
        living = self.commit_spec(run)
        # The step may not write it: the gate's refusal names the send-back, whose result may then go.
        self.rewrite_r1(run)
        (self.repo_of(run) / "built.txt").write_text("hello\n")
        refused = self.refuse(run, head, self.result(head))
        self.assertIn("; to change a requirement, report send-back naming it and what it must say.", refused)
        living.write_text(contract.LIVING_SPEC, encoding="utf-8")
        (self.repo_of(run) / "built.txt").unlink()
        head = self.accept(head, self.sent(), loop=False)
        self.assertIn("ShipLoop navigator | step-plan |", head)
        sender = self.state(run)["history"][-1]["action"]
        packet = flat(contract.full_packet_text(head))
        self.assertIn("\"" + self.sent()["summary"] + "\" Evidence: RUN/results/" + sender + ".md.", packet)
        self.assertIn("rewrite the clause in place the same way", packet)
        self.assertEqual(self.owes(head), [])                             # no note: the send-back is the direction
        # The rewrite, in place: the ID stays and no copy of the old clause; the mandated summary; follows names it.
        self.rewrite_r1(run)
        head = self.accept(head, self.result(head, summary=self.SUMMARY, follows=["R-1"]))
        self.assertIn("ShipLoop navigator | improve |", head)             # the redone plan is reviewed
        head = self.finish_review(run)
        self.assertIn(self.NEW_R1, self.spec_of(run, "HEAD"))
        self.assertNotIn(self.OLD_R1, self.spec_of(run, "HEAD").splitlines())
        # test-spec is handed the rewritten entry by value, through follows.
        self.assertIn("ShipLoop navigator | test-spec |", head)
        packet = contract.full_packet_text(head)
        self.assertIn(self.NEW_R1, packet)
        self.assertNotIn(self.OLD_R1, packet.splitlines())
        head = self.accept(head, self.result(head))
        if "ShipLoop navigator | improve |" in head:
            head = self.finish_review(run)
        # The next implement's step gate compares with the rewritten text: going back to the old clause is refused, the
        # rewritten spec with this step's own line in the entry is accepted.
        self.assertIn("ShipLoop navigator | implement |", head)
        (self.repo_of(run) / "built.txt").write_text("hello\n")
        rewritten = self.spec_of(run)
        living.write_text(contract.LIVING_SPEC, encoding="utf-8")
        self.assertIn("Found: changed or removed: " + self.NEW_R1, self.refuse(run, head, self.result(head)))
        living.write_text(rewritten.replace(self.NEW_R1, self.NEW_R1 + "\n  Met by built.txt. (W1/S1)"), encoding="utf-8")
        head = self.accept(head, self.result(head))
        self.assertIn("ShipLoop navigator | test |", head)
        # The requester is told, in the done packet and in the report beside "Decided for you".
        self.walk(run, self.at("handoff"))
        head = self.next(run)
        out = flat(self.accept(head, self.result(head)))
        self.assertIn("Requirements revised during the work: 1 revision, as the step plan reported it. In your last message "
                      "tell the user what changed and why: 1. W1: " + self.SUMMARY, out)
        report = self.cli("report", "--run-dir", str(run)).stdout
        self.assertIn("<h2>Requirements revised during the work</h2>", report)
        self.assertIn(self.SUMMARY, report)

    def test_a_requirement_the_document_stage_finds_must_change_takes_the_same_route(self) -> None:
        run, head = self.new_run("document", entered=True)
        living = self.commit_spec(run)
        self.rewrite_r1(run)
        refused = self.refuse(run, head, self.result(head))
        self.assertIn("Found: changed or removed: " + self.OLD_R1, refused)
        living.write_text(contract.LIVING_SPEC, encoding="utf-8")
        head = self.accept(head, self.sent(), loop=False)                 # the exit the refusal names, accepted
        self.assertIn("ShipLoop navigator | step-plan |", head)
        self.assertIn("document sent W1 back to step-plan (send-back 1)", flat(contract.full_packet_text(head)))

    def test_a_revision_reaches_a_later_item_through_its_context_and_unrelated_work_stays(self) -> None:
        run, _head = self.new_run("prepare", results=THREE_ITEMS)
        self.commit_spec(run)
        self.rewrite_r1(run)                                              # as W1's step plan left R-1
        self.walk(run, self.at("carry-forward", "W1"), results={**THREE_ITEMS, "step-plan": {"summary": self.SUMMARY}})
        head = self.next(run)
        packet = flat(contract.full_packet_text(head))
        self.assertIn("one that follows a requirement this item's step plan revised included", packet)
        self.assertIn("is not the incompatible finding below", packet)
        carried = ("The second part. W1's step plan revised R-1: built.txt ends with a line break (KNOWLEDGE/spec.md R-1); "
                   "recheck when the reader changes.")
        head = self.accept(head, self.result(head, work_items=[dict(ITEMS[1], context=carried), dict(ITEMS[2])]))
        self.assertIn("ShipLoop navigator | step-plan |", head)
        self.assertIn("Work item context: " + carried, flat(contract.full_packet_text(head)))
        self.assertEqual(self.state(run)["work_items"][2], ITEMS[2])      # W3 is as the plan left it


if __name__ == "__main__":
    unittest.main()
