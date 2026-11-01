#!/usr/bin/env python3
"""The follow-on list: what a delivered run leaves for a later run, classified once, cited, and routed by the script.

Design: docs/shiploop-follow-on-run-design-2026-10-31.md (sections 4 and 8).  The handoff's done result carries
``follow_on``, a list of entries {class, statement, source, request_sentence, needs}.  ShipLoop refuses only mechanical
faults (a missing list, an entry without its five texts, a class outside the vocabulary, a template placeholder left in,
a source no record of the run holds, a gap without a request sentence) and records and prints the rest.  A ``gap`` or a
``decision`` makes the script write ``RUN/follow-on-request.md`` and print the command that starts a follow-on run; it
starts nothing and never blocks ``done``.

Every route test drives the real CLI through the helpers of the callback-contract suite: it submits what the packet or
the refusal printed, follows the exit the refusal names, and requires the same gate to accept it.
"""
from __future__ import annotations

import html
import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("shiploop_callback_contract",
                                               ROOT / "test" / "shiploop-callback-contract.test.py")
contract = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = contract
_SPEC.loader.exec_module(contract)
nav, store = contract.nav, contract.store

CLASSES = ("gap", "decision", "person", "capability", "extension", "debt", "note")
FIELDS = ("class", "statement", "source", "request_sentence", "needs")
GAP = {"class": "gap", "statement": "The export exits 0 on an unreadable file although the request asks for exit 1.",
       "source": "unverified:R-1", "request_sentence": "S1",
       "needs": "a work item that makes the exit code match the request"}
DECISION = {"class": "decision", "statement": "Whether exponent notation counts as a number in the export.",
            "source": "lessons.open_next", "request_sentence": "",
            "needs": "the requester's answer"}
NOTE = {"class": "note", "statement": "The reader opens a large export slowly.", "source": "result:operations",
        "request_sentence": "", "needs": "nothing: knowledge for a later change"}
PERSON = {"class": "person", "statement": "Someone confirms the export in the customer's reader.",
          "source": "unverified:R-1", "request_sentence": "", "needs": "the user opens the file and reports"}


def follow_on_module():
    """The module under test, imported on use so a missing module fails the test that needs it and not the file."""
    return importlib.import_module("shiploop_follow_on")


# What the sources of an entry can name: product-acceptance's unverified row and the plan's open assumption.
PRIOR = {"product-acceptance": {"unverified": [contract.UNVERIFIED_ENTRY]},
         "plan": {"assumptions": [contract.OPEN_ASSUMPTION]}}


class FollowOnCase(contract.RealCliCase):
    """A run positioned at the handoff, with what the sources of an entry can name."""

    def at_handoff(self, **accepted: dict) -> tuple[Path, str]:
        with mock.patch.dict(contract.RESULTS, {**PRIOR, **accepted}):
            return self.new_run("handoff")

    def block(self, head: str, follow_on: object) -> dict:
        """The printed done template filled minimally, with this ``follow_on`` in place of the fixture's."""
        filled = self.fill_done(head)
        filled["follow_on"] = follow_on
        return filled

    def finish(self, run: Path, head: str, follow_on: object) -> str:
        """Submit a done handoff carrying ``follow_on`` through the printed callback; the output is the done packet."""
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.block(head, follow_on))
        return self.accepted(command)


class ShapeTests(unittest.TestCase):
    def test_the_vocabulary_and_the_recommendation_rule(self) -> None:
        module = follow_on_module()
        self.assertEqual(tuple(module.CLASSES), CLASSES)
        self.assertEqual(tuple(module.FIELDS), FIELDS)
        entries = [GAP, DECISION, NOTE, PERSON]
        self.assertEqual([row["class"] for row in module.recommended(entries)], ["gap", "decision"])
        self.assertEqual(module.recommended([NOTE, PERSON]), [])
        self.assertEqual(module.recommended([]), [])

    def test_the_stored_shape_is_loose_and_a_non_list_is_refused(self) -> None:
        module = follow_on_module()
        self.assertEqual(module.canonical([{"class": " gap ", "anything": "x"}]), [{"class": "gap", "anything": "x"}])
        for bad in ("gap", {"class": "gap"}, [["gap"]], [{"class": 3}]):
            with self.subTest(bad=bad), self.assertRaisesRegex(module.FollowOnError, r"follow_on(\[0\])? must be"):
                module.canonical(bad)


    def test_an_isolated_run_starts_from_the_original_checkout_and_a_direct_run_from_its_own(self) -> None:
        module = follow_on_module()
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            store.write_record(workspace / "workspace.md", {"source_repo": "/the/original/checkout"}, "ShipLoop workspace")
            isolated = {"execution_mode": "navigator-worktree", "repo": "/the/isolated/worktree"}
            self.assertEqual(module.source_repo(isolated, workspace / "run"), "/the/original/checkout")
            self.assertEqual(module.source_repo(dict(isolated, execution_mode="navigator"), workspace / "run"),
                             "/the/isolated/worktree")
            # An isolated run whose workspace record is gone falls back to its own checkout rather than failing.
            self.assertEqual(module.source_repo(isolated, workspace / "missing" / "run"), "/the/isolated/worktree")

    def test_a_request_with_shell_syntax_reaches_the_start_command_as_plain_text(self) -> None:
        # The design's safety claim: nothing the model wrote is parsed by the shell, whatever the request file holds
        # and whatever the paths are called.  The stand-in for the CLI records the argv it receives.
        module = follow_on_module()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "a dir with spaces"
            base.mkdir()
            request = base / module.FILE
            text = "Fix `touch pwned` and $(touch pwned2) and \"double\" and 'single' and $HOME and ; touch pwned3.\nNext line.\n"
            request.write_text(text, encoding="utf-8")
            echo = Path(temp) / "echo_argv.py"
            echo.write_text("import json, os, sys\nopen(os.environ['FO_OUT'], 'w').write(json.dumps(sys.argv[1:]))\n",
                            encoding="utf-8")
            out = Path(temp) / "argv.json"
            repo = str(Path(temp) / "it's a repo")
            command = module.start_command('"$CLI"', repo, request)
            done = subprocess.run(command, shell=True, cwd=temp, env={**os.environ, "CLI": str(echo), "FO_OUT": str(out)},
                                  capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")),
                             ["workspace", "start", "--repo", repo, "--prompt=" + text.rstrip("\n")])
            self.assertEqual([path.name for path in Path(temp).iterdir() if path.name.startswith("pwned")], [])


class RouteTests(FollowOnCase):
    def test_the_handoff_template_prints_the_row_and_the_duty_names_each_class_once(self) -> None:
        _run, head = self.at_handoff()
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
        self.assertEqual(template["follow_on"], [dict(follow_on_module().TEMPLATE_ROW)])
        packet = " ".join(contract.full_packet_text(head).split())
        for name in CLASSES:
            self.assertIn("`" + name + "`", packet)
        # The duty is stated once in the packet; the lines around it state facts.
        self.assertEqual(packet.count("A `gap` or a `decision` makes ShipLoop write a request"), 1)

    def test_each_fault_is_refused_naming_its_exit_and_the_corrected_list_is_accepted(self) -> None:
        run, head = self.at_handoff()
        command, path, action = contract.printed_callback(head)
        good = self.block(head, [])
        without = {key: value for key, value in good.items() if key != "follow_on"}
        template_row = dict(follow_on_module().TEMPLATE_ROW)
        faults = (
            ("left out", without, "a done handoff result lists follow_on"),
            ("not a list", dict(good, follow_on=DECISION), "follow_on must be a list"),
            ("the template row copied", dict(good, follow_on=[template_row]), "is still a template placeholder"),
            ("a class outside the vocabulary", dict(good, follow_on=[dict(NOTE, **{"class": "idea"})]),
             "is not one of gap, decision, person, capability, extension, debt, note"),
            ("an extra key", dict(good, follow_on=[dict(NOTE, owner="the user")]),
             "needs exactly class, statement, source, request_sentence, needs"),
            ("an empty statement", dict(good, follow_on=[dict(NOTE, statement=" ")]), "must be nonempty text"),
            ("a source the run does not hold", dict(good, follow_on=[dict(NOTE, source="result:release-plan-x")]),
             "resolves to no record of this run"),
            ("a source with no kind", dict(good, follow_on=[dict(NOTE, source="somewhere")]),
             "resolves to no record of this run"),
            ("an unverified row the run does not list", dict(good, follow_on=[dict(PERSON, source="unverified:R-9")]),
             "resolves to no record of this run"),
            ("a commit the repository does not hold", dict(good, follow_on=[dict(NOTE, source="commit:0123abc")]),
             "names no commit in this repository"),
            ("a gap with no request sentence", dict(good, follow_on=[dict(GAP, request_sentence="")]),
             "a gap maps to a sentence of the request"),
            ("a request sentence the request lacks", dict(good, follow_on=[dict(GAP, request_sentence="S9")]),
             "is not a sentence of the request"),
        )
        for label, block, fragment in faults:
            with self.subTest(label):
                contract.write_block(path, block)
                self.assertIn(fragment, self.refused(command, run))
        # Each refusal names an exit: the list with nothing left, which the template's rule says is allowed.
        contract.write_block(path, good)
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["follow_on"], [])

    def test_every_source_form_resolves_against_the_run(self) -> None:
        run, head = self.at_handoff()
        head_commit = contract.subprocess.run(["git", "-C", str(self.repo_of(run)), "rev-parse", "HEAD"],
                                              capture_output=True, text=True, check=True).stdout.strip()
        sources = ("unverified:R-1", "assumption:A1", "lessons.learned", "lessons.considerations",
                   "lessons.open_next", "result:operations", "result:product-acceptance", "commit:" + head_commit[:10])
        entries = [dict(NOTE, source=source, statement="From " + source + ".") for source in sources]
        self.finish(run, head, entries)
        self.assertEqual([row["source"] for row in self.recorded(run, contract.printed_callback(head)[2])["follow_on"]],
                         list(sources))
        self.assertEqual(self.state(run)["status"], "done")

    def test_a_gap_and_a_decision_recommend_a_run_the_script_writes_its_request_and_done_is_not_blocked(self) -> None:
        run, head = self.at_handoff()
        out = self.finish(run, head, [GAP, DECISION, NOTE, PERSON])
        self.assertEqual(self.state(run)["status"], "done")
        self.assertIn("It's all complete.", out)
        request = (run / "follow-on-request.md").read_text(encoding="utf-8")
        for entry in (GAP, DECISION):
            self.assertIn(entry["statement"], request)
        for entry in (NOTE, PERSON):
            self.assertNotIn(entry["statement"], request)
        self.assertIn("Everything the project already does must keep working.", request)
        self.assertIn("run the existing tests first", request)
        flat = " ".join(out.split())
        self.assertIn("Follow-on: a follow-on run is recommended by 1 gap and 1 decision (2 more entries are recorded).", flat)
        self.assertIn("ShipLoop starts nothing", flat)
        start = next(line for line in out.splitlines() if " workspace start " in line)
        self.assertTrue(start.startswith("python3 "), start)
        self.assertIn("--repo " + str(self.repo_of(run)), start)
        self.assertTrue(start.endswith('--prompt="$(cat ' + str(run / "follow-on-request.md") + ')"'), start)

    def test_the_printed_start_command_starts_a_run_whose_request_is_the_file(self) -> None:
        run, head = self.at_handoff()
        out = self.finish(run, head, [GAP])
        start = next(line for line in out.splitlines() if " workspace start " in line)
        started = subprocess.run(start, shell=True, cwd=self.base, env=self.env, capture_output=True, text=True,
                                 timeout=120, check=False)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertIn("ShipLoop navigator | intake |", started.stdout)
        new_run = Path(re.search(r"--run-dir=(\S+)", started.stdout).group(1))
        # The new run's request is the file's text, verbatim: the shell never re-read what the model wrote.
        self.assertEqual(self.state(new_run)["prompt"].strip(), (run / "follow-on-request.md").read_text().strip())
        self.assertIn(GAP["statement"], (new_run / "request.md").read_text(encoding="utf-8"))

    def test_entries_that_recommend_nothing_write_no_request_and_print_no_start_command(self) -> None:
        run, head = self.at_handoff()
        out = self.finish(run, head, [NOTE, PERSON])
        self.assertFalse((run / "follow-on-request.md").exists())
        self.assertNotIn(" workspace start ", out)
        self.assertIn("Follow-on: 2 entries are recorded and none recommends a follow-on run (see the report).",
                      " ".join(out.split()))

    def test_the_request_file_goes_when_the_accepted_list_no_longer_recommends(self) -> None:
        # A later handoff (after add-work reopens the outer stages) can accept a list that recommends nothing; the
        # request the earlier list wrote must not outlive it.
        run, head = self.at_handoff()
        self.finish(run, head, [GAP])
        self.assertTrue((run / "follow-on-request.md").is_file())
        state = self.state(run)
        action = [row["action"] for row in state["history"] if row["stage"] == "handoff"][-1]
        state["accepted"][action]["follow_on"] = [NOTE]
        nav.save(run, state)
        self.assertFalse((run / "follow-on-request.md").exists())
        state["accepted"][action]["follow_on"] = [DECISION]
        nav.save(run, state)
        self.assertIn(DECISION["statement"], (run / "follow-on-request.md").read_text(encoding="utf-8"))

    def test_an_empty_list_prints_no_follow_on_line_and_writes_no_request(self) -> None:
        run, head = self.at_handoff()
        out = self.finish(run, head, [])
        self.assertFalse((run / "follow-on-request.md").exists())
        self.assertNotIn("Follow-on:", out)

    def test_the_report_lists_entries_escaped_and_tells_none_listed_from_not_recorded(self) -> None:
        marked = dict(DECISION, statement="Whether the <b>export</b> may truncate.")
        for label, extra, expected in (
                ("entries", {"follow_on": [GAP, marked]},
                 [html.escape(GAP[name]) for name in FIELDS if GAP[name]] + [html.escape(marked["statement"])]),
                ("none listed", {"follow_on": []}, ["none listed"]),
                ("not recorded", {}, ["not recorded"])):
            with self.subTest(label):
                run, _head = self.new_run("handoff")
                state = self.state(run)
                nav.save(run, nav.apply(state, nav.current_action(state)["id"], {**contract.DONE, **extra}))
                report = self.cli("report", "--run-dir", str(run)).stdout
                self.assertIn("<h2>Follow-on</h2>", report)
                for text in expected:
                    self.assertIn(text, report)
                self.assertNotIn("<b>export</b>", report)   # model-written text is escaped
                if label == "entries":
                    self.assertIn("follow-on-request.md", report)
                    self.assertIn(' workspace start ', report)

    def test_a_saved_result_whose_entries_are_any_text_loads_while_the_gate_refuses_it(self) -> None:
        # validate() re-canonicalises every accepted result on load, so a later edit of the field set must never
        # refuse a saved run; the CLI gate holds the exact shape.
        run, head = self.at_handoff()
        state = self.state(run)
        earlier_shape = [{"class": "note", "statement": "s"}]
        accepted = nav.apply(state, nav.current_action(state)["id"], {**contract.DONE, "follow_on": earlier_shape})
        nav.validate(accepted)
        command, path, _action = contract.printed_callback(head)
        contract.write_block(path, self.block(head, earlier_shape))
        self.assertIn("needs exactly class, statement, source, request_sentence, needs", self.refused(command, run))

    def test_follow_on_is_refused_off_its_stage_and_on_a_result_that_is_not_done(self) -> None:
        state = nav.new_state(str(self.repo), "Off-stage fixture.")
        with self.assertRaisesRegex(nav.NavigatorError, "follow_on is allowed only on a done handoff result"):
            nav.apply(state, nav.current_action(state)["id"], {**contract.DONE, "follow_on": []})
        run, _head = self.at_handoff()
        state = self.state(run)
        blocked = {"outcome": "blocked",
                   "awaiting": {"kind": "service", "service": "The export service.",
                                "check": "curl -fsS https://export.example.test/health",
                                "no_default": "Only the service coming back can unblock this."},
                   "summary": "A service is down.", "follow_on": []}
        with self.assertRaisesRegex(nav.NavigatorError, "a blocked result does not carry follow_on"):
            nav.apply(state, nav.current_action(state)["id"], blocked)

    def test_a_run_saved_without_the_list_still_loads_and_reports_nothing_was_recorded(self) -> None:
        run, _head = self.new_run("handoff")
        state = self.state(run)
        done = nav.apply(state, nav.current_action(state)["id"], dict(contract.DONE))
        nav.validate(done)
        self.assertIsNone(follow_on_module().recorded(done))


class RequestFileTests(unittest.TestCase):
    """The request the script builds from the list: pure text, so a model-written statement never reaches a shell."""

    def test_the_request_names_each_gap_and_decision_with_its_source_and_keeps_the_earlier_decisions(self) -> None:
        module = follow_on_module()
        text = module.request_text([GAP, DECISION, NOTE], run_dir="/runs/one", lessons_subject="docs(shiploop): x")
        self.assertIn(GAP["statement"], text)
        self.assertIn("S1 of the earlier request", text)
        self.assertIn(DECISION["statement"], text)
        self.assertIn("lessons.open_next", text)
        self.assertNotIn(NOTE["statement"], text)
        self.assertIn("Keep the decisions in the living spec and architecture unless a finding above says otherwise",
                      text)
        self.assertIn("/runs/one/request.md", text)
        self.assertEqual(module.request_text([NOTE], run_dir="/runs/one", lessons_subject=""), "")

    def test_a_statement_or_needs_text_that_ends_with_a_period_does_not_double_it_and_one_without_gets_it(self) -> None:
        """Round 6 saw "...implement and test it.. Recorded in lessons.open_next." twice: the model's needs text ended with a period
        and the template added another."""
        module = follow_on_module()
        ended = dict(DECISION, statement="Whether exponent notation counts as a number.", needs="the requester's answer.")
        bare = dict(DECISION, statement="Whether exponent notation counts as a number", needs="the requester's answer")
        for row in (ended, bare):
            text = module.request_text([row], run_dir="/runs/one", lessons_subject="")
            self.assertIn("Whether exponent notation counts as a number. Needs: the requester's answer. Recorded in lessons.open_next.",
                          text)
            self.assertNotIn("..", text)


if __name__ == "__main__":
    unittest.main()
