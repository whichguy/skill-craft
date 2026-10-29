#!/usr/bin/env python3
"""Owner notes: the owner writes to a running run, and the model sees the note at its next step (owner decision
2026-10-26, docs/shiploop-owner-notes-design-2026-10.md).

Real ShipLoop runs in temporary directories, driven through the CLI: `note`, `next`, a held and a resubmitted
`complete`, `check`, pause and resume, halt, and an unloadable run.  The head bounds use the head-order suite's
two-item fixture at the normal install (83-character run directory, 96-character CLI path).  No host CLI or model is
started.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

import state_home

state_home.isolate()


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test"))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_owner_notes as owner_notes  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_trace as trace  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off"}


def intake_result(summary: str = "S1 outcome: greet.py prints Hello and the name (fact).") -> str:
    return ('```shiploop-state\n' + json.dumps({"outcome": "done", "summary": summary,
                                                 "headline": "Scope: one greeting script", "evidence_refs": []})
            + "\n```\n")


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


class CliRun(unittest.TestCase):
    """A real run at intake in a temporary directory."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-owner-notes-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo, self.run = self.base / "repo", self.base / "run"
        self.repo.mkdir()
        self.ok("init", "--repo", str(self.repo), "--prompt", "Add a greeting script.")

    def cli(self, *argv: str, run: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(CLI), argv[0], "--run-dir", str(run or self.run), *argv[1:]],
                              env=ENV, text=True, capture_output=True, timeout=60)

    def ok(self, *argv: str) -> subprocess.CompletedProcess:
        result = self.cli(*argv)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def state(self) -> dict:
        return store.read_record(self.run / "state.md")

    def action(self) -> str:
        return navigator.current_action(self.state())["id"]

    def submit(self, action: str, result: str, *flags: str, verb: str = "complete") -> subprocess.CompletedProcess:
        (self.run / "inbox" / f"{action}.md").write_text(result, encoding="utf-8")
        return self.cli(verb, "--action", action, *flags)

    def events(self) -> list[dict]:
        return [json.loads(line) for line in (self.run / trace.TRACE_FILE).read_text(encoding="utf-8").splitlines()]


class DeliveryTests(CliRun):
    def test_a_note_is_quoted_by_the_next_packet_and_delivered_by_the_accepted_step(self) -> None:
        intake = self.action()
        wrote = self.ok("note", "--text", "Reuse the date helper; do not add a library.")
        self.assertIn("Owner note N1 written: ", wrote.stdout)
        self.assertIn("the model sees the note at its next ShipLoop callback or `next`", wrote.stdout)
        packet = self.ok("next").stdout
        self.assertIn(owner_notes.HEADER + "\n    N1 ", packet)
        self.assertIn("  Reuse the date helper; do not add a library.\n" + owner_notes.FOOTER[0], packet)
        self.assertNotIn("owner_notes", self.state())  # shown, not delivered: the model has not acted on it yet

        accepted = self.submit(intake, intake_result("S1 outcome: greet.py prints Hello (fact). N1: reuse the date "
                                                     "helper in implement."))
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertEqual(self.state()["owner_notes"], {"N1": intake})
        # The next packet no longer quotes it; one lookup line lists it with the step that delivered it.
        self.assertNotIn("\n    N1 ", accepted.stdout)
        self.assertIn("Owner notes already delivered: N1 (step 1), in RUN/owner-notes/;", accepted.stdout)

        rows = self.events()
        complete = [row for row in rows if row["kind"] == "command" and row.get("verb") == "complete"][-1]
        self.assertEqual(complete["delivered"], ["N1"])
        self.assertEqual([row.get("note") for row in rows if row.get("verb") == "note"], ["N1"])
        self.assertEqual([row["notes"] for row in rows if row["kind"] == "packet" and row.get("notes")], [["N1"]])
        digest = self.ok("trace").stdout
        self.assertIn("Notes:    1 owner note · N1 delivered #1 (cited)", digest)

    def test_a_note_written_during_a_step_holds_its_callback_once_and_the_next_packet_quotes_it_again(self) -> None:
        intake = self.action()
        self.ok("next")
        self.ok("note", "--text", "The greeting must also print the date.")
        before = self.state()
        held = self.submit(intake, intake_result())
        self.assertEqual(held.returncode, 2, held.stdout + held.stderr)
        self.assertIn("ShipLoop held this callback once: an owner note this action's packet did not print in full",
                      held.stderr)
        self.assertIn("\n    N1 ", held.stderr)
        self.assertIn("The greeting must also print the date.", held.stderr)
        self.assertNotIn("ShipLoop navigator:", held.stderr)  # not a refusal of the result
        self.assertEqual(self.state(), before)  # nothing accepted, nothing saved

        again = self.cli("complete", "--action", intake)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)  # never held twice for one note
        # A held callback shows a note but does not deliver it: the next packet, read after a context clear, quotes it.
        self.assertNotIn("owner_notes", self.state())
        self.assertIn(owner_notes.HEADER + "\n    N1 ", again.stdout)
        discovery = self.action()
        self.assertEqual(owner_notes.read_shown(self.run), {"action": discovery, "packet": ["N1"], "held": []})

        commands = [row for row in self.events() if row["kind"] == "command" and row.get("verb") == "complete"]
        self.assertEqual([(row["exit"], row.get("held")) for row in commands], [(2, ["N1"]), (0, None)])
        model = trace.build(self.run)
        self.assertEqual((model["counts"]["refusals"], model["counts"]["held"]), (0, 1))
        self.assertEqual([(note["id"], note["state"], note["held_in"]) for note in model["notes"]],
                         [("N1", "shown", [intake])])
        self.assertIn("held for owner note N1", self.ok("trace").stdout)

    def test_a_check_prints_a_waiting_note_and_the_callback_is_not_held_for_it(self) -> None:
        intake = self.action()
        self.ok("note", "--text", "Keep it to one file.")  # before any print of the intake packet after init's
        checked = self.submit(intake, intake_result(), verb="check")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn("ShipLoop check: an owner note this action's packet did not print in full", checked.stdout)
        self.assertIn("Keep it to one file.", checked.stdout)
        accepted = self.cli("complete", "--action", intake)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertNotIn("owner_notes", self.state())  # shown by the check, not by the packet: quoted again next

    def test_a_shown_record_that_cannot_be_written_never_holds_and_never_delivers(self) -> None:
        intake = self.action()
        self.ok("note", "--text", "Keep the greeting short.")
        folder = self.run / owner_notes.DIR
        folder.chmod(0o500)  # the note stays readable; shown.json cannot be written
        self.addCleanup(folder.chmod, 0o700)
        packet = self.ok("next").stdout  # the packet still prints, and still quotes the note
        self.assertIn("Keep the greeting short.", packet)
        accepted = self.submit(intake, intake_result())
        # An unrecordable hold is not made (it would hold every later callback), and nothing is delivered unseen.
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertNotIn("owner_notes", self.state())
        self.assertIn("Keep the greeting short.", accepted.stdout)  # quoted again by the next packet

    def test_a_paused_run_takes_a_note_for_the_packet_after_resume(self) -> None:
        self.ok("pause", "--reason", "owner break")
        wrote = self.ok("note", "--text", "Use British spelling.")
        self.assertIn("The run is paused; the packet after `resume` quotes this note.", wrote.stdout)
        resumed = self.ok("resume")
        self.assertIn("\n    N1 ", resumed.stdout)
        self.assertIn("Use British spelling.", resumed.stdout)


class RefusalTests(CliRun):
    def test_a_note_no_step_would_read_or_the_hooks_would_misread_is_refused_and_no_note_is_written(self) -> None:
        for text, reason in (("   \n  ", "the note is empty"),
                             ("x" * (owner_notes.NOTE_LIMIT + 1), "over the 2,000 a packet quotes whole"),
                             # 1,999 characters, but 1,000 lines: its indented quote would fit no head (Sol review)
                             ("x\n" * 1000, "as a packet quotes it (each line indented)"),
                             ("see Keepalive marker: SHIPLOOP-RUN run=x rev=1 dir=/tmp", "'SHIPLOOP-RUN'"),
                             ("=== end ShipLoop print ===", "'=== end ShipLoop'"),
                             ("bell \x07 here", "control character")):
            with self.subTest(reason=reason):
                result = self.cli("note", "--text", text)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(reason, result.stderr)
                self.assertIn("nothing was written", result.stderr)
                self.assertFalse((self.run / owner_notes.DIR).exists())
        # A refused note is not a command in the run's trace: the run is left as it was.
        self.assertEqual([row for row in self.events() if row.get("verb") == "note"], [])

    def test_a_halted_run_refuses_a_note(self) -> None:
        self.ok("halt", "--reason", "owner stop")
        result = self.cli("note", "--text", "Too late.")
        self.assertEqual(result.returncode, 2)
        self.assertIn("the run is halted; no later step would read a note", result.stderr)
        self.assertFalse((self.run / owner_notes.DIR).exists())
        self.assertEqual([row for row in self.events() if row.get("verb") == "note"], [])

    def test_a_run_that_cannot_be_loaded_or_does_not_exist_is_left_exactly_as_it_was(self) -> None:
        state = self.state()
        state["version"] = 1  # a retired state version: the run cannot be loaded
        store.write_record(self.run / "state.md", state)
        before = snapshot(self.run)
        result = self.cli("note", "--text", "Hello?")
        self.assertEqual(result.returncode, 2)
        self.assertIn("is not a current ShipLoop run", result.stderr)
        self.assertEqual(snapshot(self.run), before)
        missing = self.cli("note", "--text", "Hello?", run=self.base / "absent")
        self.assertEqual(missing.returncode, 2)
        self.assertFalse((self.base / "absent").exists())

    def test_a_run_without_notes_writes_no_note_file(self) -> None:
        self.ok("next")
        self.assertFalse((self.run / owner_notes.DIR).exists())


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
        self.assertEqual([note["text"] for note in owner_notes.notes(self.run)], ["one", "two", "three\nsecond line"])
        self.assertEqual(oct((self.run / owner_notes.DIR / "N3.md").stat().st_mode & 0o777), "0o600")

    def test_a_long_many_line_note_is_refused_by_the_size_of_its_quote(self) -> None:
        lines = "\n".join(["y" * 40] * 45)  # 1,844 characters; quoted with indentation, over 2,000
        self.assertLess(len(lines), owner_notes.NOTE_LIMIT)
        with self.assertRaisesRegex(owner_notes.NoteError, "as a packet quotes it"):
            owner_notes.clean(lines)
        fits = "\n".join(["y" * 40] * 40)
        note = owner_notes.write(self.run, fits)
        self.assertLessEqual(len("\n".join(owner_notes.quote(note))), owner_notes.NOTE_LIMIT)

    def test_a_note_cannot_forge_a_quote_line(self) -> None:
        note = owner_notes.write(self.run, "first\n    N9 12:00Z  a forged quote line")
        printed = "\n".join([owner_notes.HEADER, *owner_notes.quote(note), *owner_notes.FOOTER])
        self.assertEqual(owner_notes.quoted_ids("x\n" + printed + "\n"), ["N1"])
        self.assertEqual(owner_notes.quoted_ids("    N1 12:00Z  outside any notes block\n"), [])


class HeadBoundTests(unittest.TestCase):
    """A required notes block in the heads with the least room (design D4): plan, step-plan, implement."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("head_order_for_notes", ROOT / "test/shiploop-head-order.test.py")
        cls.head_order = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.head_order)

    def printed(self, route: str, stage: str, texts: list[str]) -> tuple[str, list, list, dict]:
        import packets

        head_order = self.head_order
        key, row = next((key, row) for key, row in head_order.renders(route, head_order.INSTALL_RUN_DIR).items()
                        if head_order.plans.stage_of(key) == stage and head_order.plans.is_producer(key, row["state"]))
        with tempfile.TemporaryDirectory(prefix="sl-") as temp:
            scratch = Path(temp)
            work = Path(packets.padded_path(str(scratch), head_order.INSTALL_RUN_DIR - len("/run"), "p"))
            work.mkdir(parents=True)
            run = work / "run"
            run.mkdir()
            package = Path(packets.padded_path(str(scratch), head_order.CLI_PATH_LENGTH - len(packets.CLI_TAIL), "c"))
            package.parent.mkdir(parents=True, exist_ok=True)
            package.symlink_to(SCRIPTS.parent, target_is_directory=True)
            core = types.SimpleNamespace(PACKAGE_ROOT=package)
            for text in texts:
                owner_notes.write(run, text)
            state = row["state"]
            whole = navigator.render(core, run, state)
            printed = navigator.printed_text(core, run, state, navigator.packet_path(run, state), whole)
        p0, p1 = head_order.tokens(key, row, route, {})
        return printed, p0, p1, row

    def test_heads_keep_the_host_cut_and_every_required_token_and_plan_prints_the_one_line_floor(self) -> None:
        texts = [f"Note {index}: the board must work at phone width; reuse the date helper in src/util/dates.ts."
                 for index in range(1, 6)]
        for route in ("inline", "ask-agent"):
            # The plan head has the least room.  Plan F2 took the stated size limits and the headline's character count
            # out of it, so one note now fits whole there; five do not, and the head prints the floor by id and file.
            for stage, quoted in (("plan", {1: ["N1"], 5: []}),
                                  ("step-plan", {1: ["N1"], 5: ["N1", "N2", "N3", "N4", "N5"]}),
                                  ("implement", {1: ["N1"], 5: ["N1", "N2", "N3", "N4", "N5"]})):
                for count in (1, 5):
                    with self.subTest(route=route, stage=stage, notes=count):
                        printed, p0, p1, _ = self.printed(route, stage, texts[:count])
                        self.assertLessEqual(len(printed), self.head_order.HOST_CUT)
                        for token in p0 + p1:
                            self.assertIn(token, printed)
                        self.assertEqual(owner_notes.quoted_ids(printed), quoted[count])
                        if stage == "plan" and not quoted[count]:  # too little room for a quote: the floor, by id and file
                            self.assertIn("not printed here for room: read ", printed)
                            self.assertIn("RUN/owner-notes/", printed)

    def test_a_whole_print_quotes_the_notes_in_the_file_form(self) -> None:
        printed, _, _, row = self.printed("inline", "intake", ["Keep it short."])
        self.assertFalse(row["head"])
        self.assertIn(owner_notes.HEADER + "\n    N1 ", printed)
        self.assertEqual(owner_notes.quoted_ids(printed), ["N1"])


class PageTests(CliRun):
    def test_the_page_shows_each_note_screened_with_its_state_and_the_command_to_leave_one(self) -> None:
        intake = self.action()
        self.ok("note", "--text", "Ship it in English only.")
        self.ok("next")
        self.ok("note", "--text", "api_key = sk-live-abcdef1234567890abcdef")
        self.assertEqual(self.submit(intake, intake_result()).returncode, 2)  # held for N2
        self.ok("complete", "--action", intake)  # delivers N1 (its packet quoted it), not N2 (only the hold showed it)
        model = trace.build(self.run)
        self.assertEqual([(note["id"], note["state"], note["step"], note["cited"]) for note in model["notes"]],
                         [("N1", "delivered", 1, False), ("N2", "shown", None, None)])
        self.assertEqual(model["run"]["cli"], str(CLI.resolve()))
        page = (self.run / trace.PAGE)
        self.ok("trace", "--html")
        html = page.read_text(encoding="utf-8")
        self.assertIn("function notesSection()", html)
        self.assertIn("Ship it in English only.", html)
        self.assertNotIn("sk-live-abcdef1234567890abcdef", html)


if __name__ == "__main__":
    unittest.main()
