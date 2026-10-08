#!/usr/bin/env python3
"""A refusal names the exact way out, and the way out it names is accepted by the same gate.

Every test drives the real ShipLoop CLI.  A run is started with ``init`` and, where a test needs a later stage,
positioned there with the pure navigator and saved, so the CLI under test reads an ordinary run directory.
Nothing here asserts that a sentence exists on its own: each test submits what the packet or the refusal
printed, follows the correction the refusal names (derived from the refusal's own text, not from the test's
knowledge of it), submits the same command again and requires the gate to accept it.
"""

from __future__ import annotations

import concurrent.futures
import itertools
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
CARD = ROOT / "skills" / "improve" / "SKILL.md"
sys.path.insert(0, str(SCRIPTS))

import shiploop_loop_contract as loop_contract  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Nothing to change.", "handoff": "Nothing is open."}
BLOCKED_REPORT = {"classification": "unresolved", "exit_assessment": "unknown", "continuation_assessment": "blocked",
                  "evidence": "The item's goal cannot be reached as planned.", "handoff": "See the evidence."}
# The public graph, declared here and not read from the navigator, so a changed graph updates this test deliberately.
EXPECTED_STAGES = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
    "get-next-work-item", "step-plan", "test-spec", "baseline", "test-author", "test-red", "implement", "test-green",
    "test-refine", "regression", "document", "skill-assess", "skill-validate", "static-checks", "verify", "integrate",
    "integration-verify", "carry-forward",
    "system-test-author", "system-test", "product-acceptance", "release-plan", "release-check", "release",
    "release-verify", "operations", "handoff",
)
# What the accepted plans record, so the stages after them have real commands to run.  The focused command fails
# until implement has created built.txt, which is the red-then-green the test stages expect.
FOCUSED = "test -f built.txt && echo TC-1 || { echo TC-1; exit 1; }"
RESULTS = {
    "step-plan": {"paths": ["built.txt"], "steps": [{"id": "S1", "task": "Create built.txt", "deps": []}],
                  "criteria": [{"id": "C1", "text": "built.txt exists"}],
                  "test_commands": [{"command": FOCUSED, "suite": "focused", "ids": ["TC-1"], "criteria": ["C1"]},
                                    {"command": "test -f built.txt", "suite": "regression"}]},
    "system-test-author": {"system_commands": [{"command": "true", "suite": "check"}]},
    "release-plan": {"consumer_checks": [{"command": "true", "suite": "check"}],
                     "consumer_entry": {"how": "open built.txt", "sources": ["built.txt"]}},
}


def write_block(path: Path, value: object) -> None:
    """Write a result file: Markdown whose one shiploop-state fence holds the JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# ShipLoop navigator result\n\n```shiploop-state\n" + json.dumps(value, indent=2) + "\n```\n",
                    encoding="utf-8")


def read_block(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    return json.loads(text.split("```shiploop-state\n", 1)[1].split("\n```", 1)[0])


def printed_callback(head: str) -> tuple[str, Path, str]:
    """The first callback line of a producer head, the result path it names, and the action id."""
    line = next(row for row in head.splitlines() if row.startswith("Callback for this stage"))
    command = line.split("): ", 1)[1]
    argv = shlex.split(command)
    path = Path(next(a for a in argv if a.startswith("--result=")).split("=", 1)[1])
    action = next(a for a in argv if a.startswith("--action=")).split("=", 1)[1]
    return command, path, action


class RealCliCase(unittest.TestCase):
    """A temporary repository, run directories and the real CLI."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="shiploop-callback-contract-")).resolve()
        self.addCleanup(self.remove_tree, self.base)
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1")
        self.evidence = self.base / "evidence.txt"
        self.evidence.write_text("a note this stage wrote\n")
        self.counter = itertools.count(1)
        self.repo = self.make_repo()

    @staticmethod
    def remove_tree(path: Path) -> None:
        """Remove a run tree that ShipLoop's background progress observer may still be writing into.

        A command returns before that observer finishes (it writes progress.html and progress-observer.json into the
        run directory), so a plain removal can meet "Directory not empty"; retry until the tree is gone.
        """
        for _ in range(25):
            shutil.rmtree(path, ignore_errors=True)
            if not path.exists():
                return
            time.sleep(0.2)

    def make_repo(self) -> Path:
        """A one-commit repository of its own; every run gets one, so a stage's files never leak into another."""
        repo = self.base / f"repo{next(self.counter)}"
        repo.mkdir()
        for argv in (["init", "-q"], ["add", "."]):
            if argv[0] == "add":
                (repo / "a.txt").write_text("x\n")
            subprocess.run(["git", *argv], cwd=repo, env=self.env, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "init"],
                       cwd=repo, env=self.env, check=True, capture_output=True)
        return repo

    def run_argv(self, argv: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(argv, cwd=self.base, env=self.env, capture_output=True, text=True)

    def cli(self, *argv: str) -> subprocess.CompletedProcess:
        return self.run_argv([sys.executable, "-B", str(CLI), *argv])

    def run_printed(self, command: str) -> subprocess.CompletedProcess:
        """Run a command line exactly as a packet printed it."""
        return self.run_argv(shlex.split(command))

    def new_run(self, stage: str = "intake", *, entered: bool = False, **init: str) -> tuple[Path, str]:
        """A run positioned at ``stage``; returns its directory and the head the CLI prints there.

        ``entered`` positions the run one stage earlier and completes that stage through the CLI, so the files a
        transition writes (a loop's contract) exist, as they do in a real run.
        """
        if entered:
            earlier = EXPECTED_STAGES[EXPECTED_STAGES.index(stage) - 1]
            run, head = self.new_run(earlier, **init)
            command, path, _ = printed_callback(head)
            if earlier == "implement":
                (self.repo_of(run) / "built.txt").write_text("hello\n")  # the work implement's step did
            write_block(path, self.fill_done(head))
            return run, self.accepted(command)
        repo = self.repo = self.make_repo()
        run = self.base / ("run" + repo.name.removeprefix("repo"))
        started = self.cli("init", "--repo", str(repo), "--run-dir", str(run), "--prompt=add hello",
                           "--improve-skill", str(CARD), *(f"--{k}={v}" for k, v in init.items()))
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        if stage == "intake":
            return run, started.stdout
        state = store.read_record(run / "state.md")
        while nav.current_stage(state) != stage:
            action, here = nav.current_action(state)["id"], nav.current_stage(state)
            if here == "implement":
                (repo / "built.txt").write_text("hello\n")  # the work the stage's step did
            if here == "release-verify":
                # The gate's own test record, which a real run has by handoff and the handoff packet reads.
                writes, _refusal = test_loop.verify(run, state, "", action, "release-verify")
                for relative, text in writes.items():
                    (run / relative).parent.mkdir(parents=True, exist_ok=True)
                    (run / relative).write_text(text, encoding="utf-8")
            state = nav.apply(state, action, {**DONE, **RESULTS.get(here, {})})
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        nav.save(run, state)
        head = self.cli("next", "--run-dir", str(run))
        self.assertEqual(head.returncode, 0, head.stdout + head.stderr)
        return run, head.stdout

    def repo_of(self, run: Path) -> Path:
        """The repository a run from ``new_run`` works on (each run has its own)."""
        return self.base / ("repo" + run.name.removeprefix("run"))

    def field_values(self) -> dict:
        """The minimum real value of every stage-specific field a done template can print."""
        return {
            "work_items": [{"id": "W1", "title": "Build it", "context": "All of it."}],
            "assumptions": [{"id": "A1", "assumption": "x holds", "disposition": "evidenced",
                             "evidence": [str(self.evidence)]}],
            **{key: value for result in RESULTS.values() for key, value in result.items()
               if key not in ("outcome", "summary")},
        }

    def fill_done(self, head: str) -> dict:
        """The printed done template with each placeholder replaced by real content, field by field."""
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
        values, block = self.field_values(), {}
        for key in template:
            if key == "outcome":
                block[key] = "done"
            elif key == "headline":
                block[key] = "A step finished."
            elif key == "summary":
                block[key] = "What this stage established."
            elif key == "evidence_refs":
                block[key] = [str(self.evidence)]
            else:
                self.assertIn(key, values, f"the template prints {key}: add its minimum real value to this test")
                block[key] = values[key]
        return block

    def state(self, run: Path) -> dict:
        return store.read_record(run / "state.md")

    def recorded(self, run: Path, action: str) -> dict:
        """The result the run holds for an action: accepted, or the seed of the Improve child it started."""
        state = self.state(run)
        return state["accepted"].get(action) or state["active_improve"]["seed_result"]

    def refused(self, command: str, run: Path) -> str:
        """Run a command that must be refused; the run's state file must not change."""
        before = (run / "state.md").read_bytes()
        result = self.run_printed(command)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual((run / "state.md").read_bytes(), before)
        return result.stdout + result.stderr

    def accepted(self, command: str) -> str:
        result = self.run_printed(command)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def done_fields(self) -> dict:
        return {"outcome": "done", "summary": "What this step established.", "headline": "A step was established.",
                "evidence_refs": [str(self.evidence)]}


class RefusalRouteTests(RealCliCase):
    """Each refusal names a correction; submitting it through the same command is accepted."""

    def test_a_wrapped_result_is_refused_with_the_unwrap_and_the_unwrapped_result_is_accepted(self) -> None:
        run, head = self.new_run()
        command, path, action = printed_callback(head)
        wrapped = {"action": action, "navigator_protocol_version": 4, "result": self.done_fields()}
        write_block(path, wrapped)
        reply = self.refused(command, run)
        self.assertIn("stored-record wrapper", reply)
        self.assertIn("run the same complete command again", reply)
        # The correction is read from the reply: the keys it says to delete, and that "result" moves up.
        named = re.search(r"delete the keys ([^;]+);", reply).group(1).split(", ")
        self.assertEqual(sorted(named), sorted(wrapped))
        block = read_block(path)
        write_block(path, {**{k: v for k, v in block.items() if k not in named}, **block["result"]})
        self.assertIn("| discovery |", self.accepted(command))
        self.assertIn(action, self.state(run)["accepted"])

    def test_a_result_missing_summary_or_outcome_is_told_which_and_what_to_add(self) -> None:
        for missing, add in (("summary", '"summary": "<what this step established>"'),
                             ("outcome", '"outcome": "done"')):
            with self.subTest(missing=missing):
                run, head = self.new_run()
                command, path, _ = printed_callback(head)
                block = self.done_fields()
                del block[missing]
                write_block(path, block)
                reply = self.refused(command, run)
                self.assertIn(f'the result is missing "{missing}"', reply)
                self.assertNotIn(f'"{"outcome" if missing == "summary" else "summary"}" and', reply)
                self.assertIn("add " + add, reply)
                self.assertIn("run the same complete command again", reply)
                block[missing] = "done" if missing == "outcome" else "What this step established."
                write_block(path, block)
                self.accepted(command)

    def test_a_result_file_that_does_not_parse_is_a_rejected_request_and_the_fixed_file_is_accepted(self) -> None:
        # A model-written file that is not a result block is a fault in the file, not lost state: the reply names
        # the file, the parser's reason and the same command to run again, and never the lost-state recovery text.
        bad = {
            "no fence": ('{"outcome": "done", "summary": "x"}\n', "found 0"),
            "trailing comma": ('```shiploop-state\n{"outcome": "done", "summary": "x",}\n```\n',
                               "Illegal trailing comma"),
            "unterminated fence": ('```shiploop-state\n{"outcome": "done", "summary": "x"}\n',
                                   "unterminated shiploop-state fence"),
            "duplicate key": ('```shiploop-state\n{"outcome": "done", "summary": "x", "summary": "y"}\n```\n',
                              "duplicate JSON key"),
        }
        for label, (text, reason) in bad.items():
            with self.subTest(label):
                run, head = self.new_run()
                command, path, action = printed_callback(head)
                path.write_text(text, encoding="utf-8")
                reply = self.refused(command, run)
                self.assertIn(str(path), reply)
                self.assertIn(reason, reply)
                self.assertIn("fix the result file and run the same command again", reply)
                self.assertIn("the rejected request did not advance the graph", reply)
                self.assertNotIn("Request failure: no in-memory result", reply)
                self.assertNotIn("Durable cursor recovery", reply)
                write_block(path, self.done_fields())
                self.accepted(command)
                self.assertIn(action, self.state(run)["accepted"])

    def test_each_result_fault_the_checked_line_names_is_refused_and_the_corrected_result_is_accepted(self) -> None:
        # Guard, green before and after the Checked-by wording: every fault the line of a stage without a script-run
        # check names is a real refusal at that stage, and the corrected result is accepted by the same command. If a
        # gate is removed or renamed, the line would over-promise and this fails.
        token = "ghp_" + "Ab1" * 8  # not a credential: a made-up string of the shape the screen refuses
        cases = [
            ("an absolute evidence_refs path that does not exist", "intake",
             lambda block: {**block, "evidence_refs": [str(self.base / "no-such-note.md")]},
             "evidence_refs cite files that do not exist"),
            ("an explicit credential pattern", "intake",
             lambda block: {**block, "summary": "The key is " + token},
             "appears to contain a credential secret"),
            ("an open assumption whose consumer is not in the plan", "plan",
             lambda block: {**block, "assumptions": [{"id": "A2", "assumption": "y holds", "disposition": "open",
                                                      "check": "run y", "reason": "later", "consumer": "W9"}]},
             "is not a work item in this plan"),
            ("a criterion no test command names", "step-plan",
             lambda block: {**block, "criteria": [*block["criteria"], {"id": "C2", "text": "an unnamed criterion"}]},
             "every criterion needs a test command that confirms it"),
            ("a step whose dependency is a later step", "step-plan",
             lambda block: {**block, "steps": [{"id": "S1", "task": "first", "deps": ["S2"]},
                                               {"id": "S2", "task": "second", "deps": []}]},
             "step deps must name earlier steps"),
            ("no system_commands list", "system-test-author",
             lambda block: {k: v for k, v in block.items() if k != "system_commands"},
             "a done system-test-author result must list system_commands"),
            ("no consumer_checks list", "release-plan",
             lambda block: {k: v for k, v in block.items() if k != "consumer_checks"},
             "a done release-plan result must list consumer_checks"),
            ("a consumer_entry source that is not in the repository", "release-plan",
             lambda block: {**block, "consumer_entry": {"how": "open it", "sources": ["nowhere/missing.py"]}},
             "consumer_entry sources do not exist in the repository"),
        ]
        for label, stage, break_it, fragment in cases:
            with self.subTest(label):
                run, head = self.new_run(stage)
                command, path, action = printed_callback(head)
                good = self.fill_done(head)
                write_block(path, break_it(good))
                self.assertIn(fragment, self.refused(command, run))
                write_block(path, good)
                self.accept_after_the_knowledge_files(command, run)
                self.assertEqual(self.recorded(run, action)["outcome"], "done")
        with self.subTest("a skill file in paths beside skill_na"):
            # The exit the refusal names is the same plan without skill_na, the skill file still in paths.  The document
            # stage's half of this fault (a skill file changed after skill_na) needs a real item diff and is paired in
            # test/shiploop-test-loop.test.py.
            run, head = self.new_run("step-plan")
            command, path, action = printed_callback(head)
            good = self.fill_done(head)
            listed = {**good, "paths": [*good["paths"], ".claude/skills/review/SKILL.md"]}
            write_block(path, {**listed, "skill_na": "No repo-local skill applies: README.md is the index and names none."})
            reply = self.refused(command, run)
            self.assertIn("skill_na says no repo-local skill is selected", reply)
            self.assertIn("resubmit the step plan without skill_na", reply)
            write_block(path, listed)
            self.accepted(command)
            self.assertEqual(self.recorded(run, action)["outcome"], "done")
        with self.subTest("the docs/shiploop files a close requires"):
            run, head = self.new_run("test-spec")
            command, path, action = printed_callback(head)
            write_block(path, self.fill_done(head))
            reply = self.refused(command, run)
            self.assertIn("keeps this run's planning knowledge in the repository", reply)
            self.accept_after_the_knowledge_files(command, run)
            self.assertEqual(self.recorded(run, action)["outcome"], "done")

    def accept_after_the_knowledge_files(self, command: str, run: Path) -> None:
        """Run ``command``; at a stage that closes the knowledge home, first write the files its refusal names."""
        result = self.run_printed(command)
        if result.returncode != 0:
            reply = result.stdout + result.stderr
            self.assertIn("keeps this run's planning knowledge in the repository", reply)
            for named in re.findall(r"^- (/\S+)$", reply, re.M):  # the files the refusal names, and nothing else
                Path(named).parent.mkdir(parents=True, exist_ok=True)
                Path(named).write_text("What this file records.\n", encoding="utf-8")
            self.accepted(command)

    def test_a_blocked_result_with_done_fields_is_refused_once_with_every_field_named(self) -> None:
        run, head = self.new_run("plan")
        command, path, _ = printed_callback(head)
        blocked = {"outcome": "blocked", "blocked_by": "external", "summary": "A service this run needs is down.",
                   "headline": "Waiting on a service.", "evidence_refs": [str(self.evidence)],
                   "work_items": [{"id": "W1", "title": "Build it", "context": "Everything."}],
                   "assumptions": [{"id": "A1", "assumption": "The service returns.", "disposition": "evidenced",
                                    "evidence": [str(self.evidence)]}]}
        write_block(path, blocked)
        reply = self.refused(command, run)
        self.assertIn("a blocked result does not carry work_items, assumptions", reply)
        self.assertIn("run the same complete command again", reply)
        # Follow it: delete exactly the fields it names, then submit the same command.
        named = re.search(r"does not carry ([^:]+):", reply).group(1).split(", ")
        write_block(path, {k: v for k, v in blocked.items() if k not in named})
        self.accepted(command)
        seed = self.state(run)["active_improve"]["seed_result"]
        self.assertEqual((seed["outcome"], seed["blocked_by"]), ("blocked", "external"))

    def test_a_wait_without_no_default_is_told_where_it_goes(self) -> None:
        wait = {"kind": "present", "steps": ["Open the app and play one game."], "report": "Whether it played."}
        base = {"outcome": "blocked", "blocked_by": "user", "summary": "A person must try the app."}
        for label, block, expected in (
                ("beside", {**base, "awaiting": wait, "no_default": "Only a person can play it."},
                 "The result has no_default beside awaiting: move it inside awaiting."),
                ("absent", {**base, "awaiting": wait}, "add no_default inside awaiting")):
            with self.subTest(case=label):
                run, head = self.new_run()
                command, path, _ = printed_callback(head)
                write_block(path, block)
                reply = self.refused(command, run)
                self.assertIn("ShipLoop runs unattended: take a stated default", reply)
                self.assertIn(expected, reply)
                self.assertIn(nav.AWAITING_SHAPE, reply)
                fixed = {k: v for k, v in block.items() if k != "no_default"}
                fixed["awaiting"] = {**wait, "no_default": block.get("no_default", "Only a person can play it.")}
                write_block(path, fixed)
                self.accepted(command)
                self.assertEqual(self.state(run)["status"], "blocked")

    def test_unsupported_fields_are_named_and_deleting_them_is_accepted(self) -> None:
        run, head = self.new_run()
        command, path, _ = printed_callback(head)
        block = {**self.done_fields(), "next": "release", "run_id": "nav-x"}
        write_block(path, block)
        reply = self.refused(command, run)
        self.assertIn("result has unsupported fields: next, run_id", reply)
        named = re.search(r"unsupported fields: ([^.]+)\.", reply).group(1).split(", ")
        write_block(path, {k: v for k, v in block.items() if k not in named})
        self.accepted(command)

    def test_an_opening_with_a_renamed_heading_is_told_the_exact_heading_to_use(self) -> None:
        run, head = self.new_run("spec")
        command, path, action = printed_callback(head)
        write_block(path, self.done_fields())
        bind = next(row for row in self.accepted(command).splitlines() if row.startswith("Next command (bind"))
        started = self.accepted(bind.split("details below): ", 1)[1])
        start_line = next(row for row in started.splitlines() if row.startswith("Next command (start"))
        opening = Path(re.search(r"opening file (\S+);", start_line).group(1))
        start = start_line.split("details below): ", 1)[1]
        sections = {"Current context and desired improvements": "The user asked for hello.",
                    "Scope": "a.txt", "Authority": "Local edits only.", "Environment": "Python 3."}

        def text(renamed: str | None) -> str:
            return "\n\n".join(f"## {renamed if renamed and name == 'Environment' else name}\n{body}"
                               for name, body in sections.items()) + "\n"

        opening.parent.mkdir(parents=True, exist_ok=True)
        opening.write_text(text("Environment and validation"), encoding="utf-8")
        reply = self.refused(start, run)
        self.assertIn('no line reading exactly "## Environment"', reply)
        self.assertIn("## Environment and validation", reply)  # the heading it found, to rename
        self.assertIn("run the same improve-start command again", reply)
        opening.write_text(text(None), encoding="utf-8")
        self.assertEqual(json.loads(self.accepted(start))["status"], "active")

    def test_an_empty_section_is_refused_naming_it_and_the_filled_opening_is_accepted(self) -> None:
        run, head = self.new_run("spec")
        command, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        bind = next(row for row in self.accepted(command).splitlines() if row.startswith("Next command (bind"))
        started = self.accepted(bind.split("details below): ", 1)[1])
        start_line = next(row for row in started.splitlines() if row.startswith("Next command (start"))
        opening = Path(re.search(r"opening file (\S+);", start_line).group(1))
        start = start_line.split("details below): ", 1)[1]
        opening.parent.mkdir(parents=True, exist_ok=True)
        opening.write_text("## Current context and desired improvements\nHello.\n\n## Scope\na.txt\n\n"
                           "## Authority\nLocal edits only.\n\n## Environment\n...\n", encoding="utf-8")
        reply = self.refused(start, run)
        self.assertIn("opening needs non-empty sections: ## Environment", reply)
        self.assertIn("run the same improve-start command again", reply)
        opening.write_text(opening.read_text(encoding="utf-8").replace("...", "Python 3."), encoding="utf-8")
        self.assertEqual(json.loads(self.accepted(start))["status"], "active")

    def test_a_condition_no_command_can_confirm_leaves_criteria_by_the_exit_the_refusal_names(self) -> None:
        """Batch 1009 S1: the step plan used to tell the model to mark such a criterion `Confirm by: unconfirmable here`
        in `criteria`, which the gate refuses (a passing command ShipLoop runs is the only confirmation).  The packet
        and the refusal now name the same exit: the condition is not a criterion, it is an open item in the summary."""
        run, head = self.new_run("step-plan")
        command, path, action = printed_callback(head)
        packet = " ".join(full_packet_text(head).split())
        exit_sentence = re.search(r"[^.]*no command can confirm[^.]*\.", packet)
        self.assertIsNotNone(exit_sentence, "the step plan packet says what to do with a condition no command can confirm")
        self.assertIn("open item", exit_sentence.group(0))
        good = self.fill_done(head)
        person_only = {"id": "C2", "text": "A person signs off the layout. Confirm by: unconfirmable here - needs a person."}
        write_block(path, {**good, "criteria": [*good["criteria"], person_only]})
        reply = self.refused(command, run)
        self.assertIn("uncovered: C2", reply)
        self.assertIn("open item", reply)
        # The correction is read from the reply: the ids it lists as uncovered leave `criteria`, and the condition
        # is recorded as an open item in the summary instead.
        uncovered = re.search(r"uncovered: ([^\n;]+?)(?:[.;]|$)", reply, re.MULTILINE).group(1).split(", ")
        kept = [row for row in good["criteria"] + [person_only] if row["id"] not in uncovered]
        write_block(path, {**good, "criteria": kept,
                           "summary": good["summary"] + " Open item: a person signs off the layout and reports back."})
        self.accepted(command)
        self.assertEqual([row["id"] for row in self.recorded(run, action)["criteria"]], ["C1"])

    def test_the_implement_packet_does_not_ask_for_a_field_the_accepted_plan_does_not_hold(self) -> None:
        """Batch 1009 S1: an item that records no test command has no `criteria` and no `Confirm by` text, yet the
        implement Done-when told the model to confirm each criterion by its `Confirm by`.  The row names no field
        and no route (a recorded command exists only for an item that has tests); the accepted plan decides how."""
        run, head = self.new_run("step-plan", **{"planning-review": "none"})
        command, path, _ = printed_callback(head)
        good = self.fill_done(head)
        write_block(path, {**{key: value for key, value in good.items() if key not in ("criteria", "test_commands")},
                           "paths": ["README.md"], "test_commands": [], "test_commands_na": "documentation only"})
        implement = self.accepted(command)
        self.assertIn("| implement |", implement.splitlines()[0])
        done_when = implement.split("Done when", 1)[1].split("Checked by:", 1)[0]
        done_when = " ".join(done_when.split())
        self.assertIn("completion criterion", done_when)
        self.assertNotIn("Confirm by", done_when)
        self.assertNotIn("recorded", done_when)
        self.assertIn("after the last edit", done_when)


def printed_shapes(head: str) -> dict[str, str]:
    """The line the head prints for each outcome other than done: {"repeat": '{"outcome": ...}', ...}."""
    shapes = {}
    for line in head.splitlines():
        found = re.match(r"(repeat|blocked|revise|replan): (\{.*)$", line)
        if found:
            shapes[found.group(1)] = found.group(2)
    return shapes


def first_object(text: str) -> dict:
    """The JSON object a printed shape starts with (anything after it is prose)."""
    value, _ = json.JSONDecoder().raw_decode(text)
    return value


def allowed_outcomes(head: str) -> list[str]:
    line = next(row for row in head.splitlines() if row.startswith("Allowed outcomes: "))
    return [part.strip().split(" ", 1)[0].rstrip(".") for part in line.removeprefix("Allowed outcomes: ").split(" | ")]


class OutcomeShapeTests(RealCliCase):
    """The head prints the exact fields of every outcome the stage allows, and each printed shape is accepted."""

    STAGES = {"intake": ("repeat", "blocked"), "test-red": ("repeat", "blocked", "revise"),
              "system-test-author": ("repeat", "blocked", "replan")}

    def fill(self, outcome: str, shape: dict) -> dict:
        """The minimum real content for a printed shape: its own fields, plus the evidence every result cites."""
        block = {**shape, "summary": "What happened in this stage.", "headline": "A step finished.",
                 "evidence_refs": [str(self.evidence)]}
        if outcome == "blocked":
            block["blocked_by"] = "external"
        if outcome == "replan":
            block["work_items"] = [{"id": "W9", "title": "Corrective item", "context": "What it fixes."}]
        return block

    def test_the_head_prints_a_shape_for_every_allowed_outcome_and_how_to_nest_the_result(self) -> None:
        for stage, others in self.STAGES.items():
            with self.subTest(stage=stage):
                _, head = self.new_run(stage)
                self.assertEqual(allowed_outcomes(head), ["done", *others])
                self.assertEqual(sorted(printed_shapes(head)), sorted(others))
                self.assertIn('"outcome" and "summary" are its top-level fields; do not wrap it in action or result keys',
                              head)
                self.assertIn(nav.AWAITING_SHAPE, head)

    def test_each_printed_outcome_shape_is_accepted_through_the_printed_command(self) -> None:
        for stage, others in self.STAGES.items():
            for outcome in others:
                with self.subTest(stage=stage, outcome=outcome):
                    run, head = self.new_run(stage)
                    command, path, action = printed_callback(head)
                    shape = first_object(printed_shapes(head)[outcome])
                    self.assertEqual(shape["outcome"], outcome)
                    write_block(path, self.fill(outcome, shape))
                    self.accepted(command)
                    self.assertEqual(self.recorded(run, action)["outcome"], outcome)

    def test_the_printed_wait_shape_is_accepted_for_a_blocked_result(self) -> None:
        for kind in ("present", "answer"):
            with self.subTest(kind=kind):
                run, head = self.new_run()
                command, path, _ = printed_callback(head)
                line = printed_shapes(head)["blocked"]
                forms = [first_object(text) for text in re.findall(r'\{"kind": [^}]*\}', line)]
                wait = next(form for form in forms if form["kind"] == kind)
                wait = {key: ("Why nothing else can proceed." if key == "no_default" else
                              ["The person does the step."] if key == "steps" else
                              "What they report." if key == "report" else "Which one?")
                        for key in wait}
                wait["kind"] = kind
                write_block(path, {**self.fill("blocked", {"outcome": "blocked"}), "blocked_by": "user",
                                   "awaiting": wait})
                self.accepted(command)
                self.assertEqual(self.state(run)["status"], "blocked")

    def test_a_blocked_result_built_from_the_done_template_is_still_refused(self) -> None:
        """The failure the shapes prevent: change the outcome of the done template and keep its other fields."""
        run, head = self.new_run("plan")
        command, path, _ = printed_callback(head)
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
        template.update(outcome="blocked", blocked_by="external", summary="Stopped.", headline="Stopped.",
                        evidence_refs=[str(self.evidence)])
        write_block(path, template)
        self.assertIn("a blocked result does not carry work_items, assumptions", self.refused(command, run))

    def test_the_release_plan_template_carries_the_entry_its_gate_requires(self) -> None:
        _, head = self.new_run("release-plan")
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
        self.assertEqual(sorted(template["consumer_entry"]), ["how", "sources"])

    def test_the_improve_start_head_names_the_four_opening_headings(self) -> None:
        run, head = self.new_run("spec")
        command, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        bind = next(row for row in self.accepted(command).splitlines() if row.startswith("Next command (bind"))
        started = self.accepted(bind.split("details below): ", 1)[1]).splitlines()
        start = next(i for i, row in enumerate(started) if row.startswith("Next command (start"))
        for name in nav.OPENING_SECTIONS:
            self.assertIn(f'"## {name}"', started[start + 1])


def full_packet_text(head: str) -> str:
    """The file a head's "Full packet:" line points at."""
    line = next(row for row in head.splitlines() if row.startswith("Full packet: "))
    return Path(line.removeprefix("Full packet: ")).read_text(encoding="utf-8")


class LoopRefusalRouteTests(RealCliCase):
    """A loop stage refused because its loop never ran is told the command that runs it, and that command works."""

    def follow_start(self, reply: str) -> Path:
        """Do what the refusal says: run its start command, follow each packet to complete, return the receipt."""
        start = re.search(r"Start it with: (.*?)  and follow", reply, re.S).group(1)
        words = shlex.split(start)
        self.assertEqual(words[-2], "<")
        packet = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True,
                                           capture_output=True, check=True, timeout=60).stdout)
        while packet["status"] == "active":
            packet = json.loads(subprocess.run(packet["done_argv"], input=json.dumps(TRIVIAL), text=True,
                                               capture_output=True, check=True, timeout=60).stdout)
        self.assertEqual(packet["status"], "complete")
        return Path(re.search(r"Then list (\S+) in evidence_refs", reply).group(1))

    def test_done_before_the_loop_ran_is_told_the_start_command_and_following_it_is_accepted(self) -> None:
        for stage, label in (("test-green", "test loop"), ("static-checks", "quality loop")):
            with self.subTest(stage=stage):
                run, head = self.new_run(stage, entered=True)
                command, path, action = printed_callback(head)
                block = self.done_fields()
                write_block(path, block)
                reply = self.refused(command, run)
                self.assertIn(f"the {label} has not run: no terminal packet exists at", reply)
                # The command in the reply is the one the full packet prints: one definition, not two.
                printed = next(row for row in full_packet_text(head).splitlines() if row.startswith("Start: "))
                self.assertIn("Start it with: " + printed.removeprefix("Start: ") + "  and follow", reply)
                receipt = self.follow_start(reply)
                write_block(path, {**block, "evidence_refs": [*block["evidence_refs"], str(receipt)]})
                self.accepted(command)
                self.assertEqual(nav.current_stage(self.state(run)), "verify" if stage == "static-checks" else "test-refine")

    def test_revise_before_the_loop_stopped_is_told_to_run_it_until_it_stops_blocked(self) -> None:
        run, head = self.new_run("test-green", entered=True)
        command, path, _ = printed_callback(head)
        block = {**self.done_fields(), "outcome": "revise", "summary": "The step plan cannot be met as written."}
        write_block(path, block)
        reply = self.refused(command, run)
        self.assertIn("the test loop has not run", reply)
        self.assertIn("until its status is stopped: report continuation_assessment blocked", reply)
        start = re.search(r"Start it with: (.*?)  and follow", reply, re.S).group(1)
        words = shlex.split(start)
        packet = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True,
                                           capture_output=True, check=True, timeout=60).stdout)
        packet = json.loads(subprocess.run(packet["done_argv"], input=json.dumps(BLOCKED_REPORT), text=True,
                                           capture_output=True, check=True, timeout=60).stdout)
        self.assertEqual(packet["status"], "stopped")
        receipt = re.search(r"Then list (\S+) in evidence_refs and submit revise again", reply).group(1)
        write_block(path, {**block, "evidence_refs": [*block["evidence_refs"], receipt]})
        self.accepted(command)
        self.assertEqual(nav.current_stage(self.state(run)), "step-plan")

    def test_citing_a_receipt_nobody_wrote_is_still_refused(self) -> None:
        for stage, expected in (("test-green", "evidence_refs cite files that do not exist"),
                                ("static-checks", "the quality loop has not run")):
            with self.subTest(stage=stage):
                run, head = self.new_run(stage, entered=True)
                command, path, _ = printed_callback(head)
                write_block(path, self.done_fields())
                named = Path(re.search(r"no terminal packet exists at (\S+)\.", self.refused(command, run)).group(1))
                write_block(path, {**self.done_fields(), "evidence_refs": [str(self.evidence), str(named)]})
                self.assertFalse(named.exists())
                self.assertIn(expected, self.refused(command, run))


# A command that is not a test runner: it exits 0 and prints no test count, so as suite focused it cannot be counted.
PIPELINE = "[ \"$(echo Hello | wc -c | tr -d ' ')\" = 6 ] && echo Hello | grep -qx Hello"
COUNTED = "printf '=== 1 passed in 0.01s ===\\n'"
COUNTED_FAILURE = "printf '=== 1 failed in 0.01s ===\\n'; exit 1"


class UncountedCommandRouteTests(RealCliCase):
    """A recorded command ShipLoop cannot count is refused where it runs, and the refusal names the exit that works.

    system-test runs commands that system-test-author recorded and cannot edit them, so "give the command ids" is
    no way out there: the exit is a replan, and the command is recorded again as suite check.
    """

    def at_system_test(self, command: str, suite: str = "focused") -> tuple[Path, str, str, Path]:
        """A run at system-test whose recorded system command is ``command``; its directory, head, callback, result."""
        recorded = {"system-test-author": {"system_commands": [{"command": command, "suite": suite}]}}
        with mock.patch.dict(RESULTS, recorded):
            run, head = self.new_run("system-test")
        callback, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        return run, head, callback, path

    @staticmethod
    def named_exit(reply: str) -> tuple[str, str]:
        """The outcome the refusal says to report and the result field it says to record the command in."""
        outcome = re.search(r"Report outcome (\w+) now", reply).group(1)
        field = re.search(r"as suite check in (\w+)\.", reply).group(1)
        return outcome, field

    def test_an_uncounted_system_command_is_refused_naming_replan_and_check(self) -> None:
        run, _, callback, _ = self.at_system_test(PIPELINE)
        reply = self.refused(callback, run)
        self.assertIn("could not read how many tests it ran", reply)
        self.assertIn("system-test-author recorded this command and system-test cannot edit it", reply)
        self.assertIn("belongs in suite `check`, judged by its exit code", reply)
        self.assertEqual(self.named_exit(reply), ("replan", "system_commands"))
        # The two lines that sent the model the wrong way: edit the command, or fix the code.
        self.assertNotIn("Give the command ids", reply)
        self.assertNotIn("Fix the code so every command passes", reply)
        self.assertIn("Refused runs for this action: 1 of 7; replan does not wait for them.", reply)

    def test_the_replan_the_refusal_names_is_accepted_with_one_corrective_item(self) -> None:
        run, head, callback, path = self.at_system_test(PIPELINE)
        outcome, field = self.named_exit(self.refused(callback, run))
        # What to submit is read from the reply (outcome, the field to record in) and the packet's printed shape.
        shape = first_object(printed_shapes(head)[outcome])
        item = {"id": "W9", "title": "Record the system check", "context": f"Record `{PIPELINE}` as suite check in {field}."}
        write_block(path, {**shape, "summary": "A recorded command is not a test runner.", "headline": "Replanning.",
                           "evidence_refs": [str(self.evidence)], "work_items": [item]})
        self.accepted(callback)
        state = self.state(run)
        self.assertEqual([row["id"] for row in state["work_items"]][-1], "W9")
        self.assertNotEqual(nav.current_stage(state), "system-test")

    def test_the_same_pipeline_as_done_is_still_refused_and_only_the_replan_re_records_it(self) -> None:
        run, _, callback, path = self.at_system_test(PIPELINE)
        self.named_exit(self.refused(callback, run))  # the refusal names its exit before the gate is tried again
        again = self.refused(callback, run)
        self.assertIn("could not read how many tests it ran", again)
        self.assertIn("Refused runs for this action: 2 of 7", again)
        # Recording it as a check here is not an exit: system-test reruns what was recorded, so the gate holds.
        write_block(path, {**self.done_fields(), "system_commands": [{"command": PIPELINE, "suite": "check"}]})
        self.assertIn("could not read how many tests it ran", self.refused(callback, run))

    def test_a_pipeline_recorded_as_a_check_and_a_counted_focused_command_pass(self) -> None:
        for command, suite in ((PIPELINE, "check"), (COUNTED, "focused")):
            with self.subTest(suite=suite):
                run, _, callback, _ = self.at_system_test(command, suite)
                self.accepted(callback)
                self.assertEqual(nav.current_stage(self.state(run)), "product-acceptance")

    def test_a_counted_failure_keeps_its_own_reply(self) -> None:
        run, _, callback, _ = self.at_system_test(COUNTED_FAILURE)
        reply = self.refused(callback, run)
        self.assertIn("-> exit 1", reply)
        self.assertIn("Fix the code so every command passes", reply)
        self.assertNotIn("Report outcome replan now", reply)

    def test_at_a_stage_whose_commands_the_step_plan_recorded_the_reply_keeps_ids_and_a_flag_and_adds_check(self) -> None:
        recorded = {"step-plan": {**RESULTS["step-plan"], "test_commands": [
            {"command": "echo hi | grep -q nothing", "suite": "focused", "criteria": ["C1"]},
            RESULTS["step-plan"]["test_commands"][1]]}}
        with mock.patch.dict(RESULTS, recorded):
            run, head = self.new_run("test-red")
        callback, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        reply = self.refused(callback, run)
        self.assertIn("Give the command ids and a runner flag that prints test names", reply)
        self.assertIn("for a command that is not a test runner, record it as suite `check`", reply)
        self.assertNotIn("Report outcome replan now", reply)


class OpeningAllowanceTests(RealCliCase):
    """The oversize-opening refusal states the room the sections have, and the room it states is real.

    The Luna 1.16.1 refusal listed whole contract fields (which carry ShipLoop's own text) next to an allowance for
    the model's sections only, so its arithmetic looked 1,165 bytes off (12,478 total, 3,262 over, "about 4,686").
    The allowance was right; the listed sizes were not comparable to it.  Listing each section's own escaped bytes
    (112b239c) made them comparable, and this test keeps them so, through the real gate.
    """

    NAMES = ("Current context and desired improvements", "Scope", "Authority", "Environment")

    def at_improve_start(self) -> tuple[Path, Path, str]:
        """A run with a bound Improve child: its directory, the opening file and the improve-start command."""
        run, head = self.new_run("spec")
        command, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        bind = next(row for row in self.accepted(command).splitlines() if row.startswith("Next command (bind"))
        started = self.accepted(bind.split("details below): ", 1)[1])
        start_line = next(row for row in started.splitlines() if row.startswith("Next command (start"))
        opening = Path(re.search(r"opening file (\S+);", start_line).group(1))
        opening.parent.mkdir(parents=True, exist_ok=True)
        return run, opening, start_line.split("details below): ", 1)[1]

    def write_sections(self, opening: Path, sizes: tuple[int, int, int, int]) -> None:
        """An opening whose four sections hold plain text of exactly these sizes (one byte per character, no escapes)."""
        opening.write_text("".join(f"## {name}\n{'a' * size}\n\n" for name, size in zip(self.NAMES, sizes)),
                           encoding="utf-8")

    def test_the_stated_allowance_is_the_sections_real_room_and_the_refusal_says_how_it_is_counted(self) -> None:
        run, opening, start = self.at_improve_start()
        self.write_sections(opening, (2993, 891, 1057, 4172))  # the sizes of the Luna refusal's four sections
        reply = self.refused(start, run)
        listed = {name: int(size.replace(",", "")) for name, size in re.findall(
            r"(Environment|Scope|Authority|Current context and desired improvements) ([\d,]+)", reply)}
        over = int(re.search(r"([\d,]+) over its", reply).group(1).replace(",", ""))
        allowance = int(re.search(r"may use about ([\d,]+) bytes in all", reply).group(1).replace(",", ""))
        self.assertEqual(sorted(listed), sorted(self.NAMES))
        # The arithmetic the reply invites agrees with its allowance: the sections total less the overage is the
        # room, to within the four placeholder bytes ShipLoop's own measure of its fixed text includes.
        self.assertEqual(sum(listed.values()), 9113)
        self.assertIn(sum(listed.values()) - over - allowance, range(0, 5))
        # What the allowance counts is said once, where the number is.
        self.assertIn("counted as above: escaped like JSON, so a newline or a quote costs 2 bytes and a non-ASCII "
                      "character 6, and a file's byte size undercounts it", reply)
        # ... and the clause is true: the runtime's count of a newline or quote is 2 bytes, of a non-ASCII character 6.
        self.assertEqual((loop_contract.text_bytes("a\n\"b"), loop_contract.text_bytes("\u65e5")), (6, 6))
        # Sections that total the stated allowance are accepted by the same gate; its room ends just above it.
        self.write_sections(opening, (300, 300, 300, allowance + 5 - 900))
        self.assertIn("over its 9,216-byte budget", self.refused(start, run))
        self.write_sections(opening, (300, 300, 300, allowance - 900))
        self.assertEqual(json.loads(self.accepted(start))["status"], "active")


# Stages whose accepted result starts an Improve child (the planning reviews and the last item's carry-forward),
# declared here and not read from the navigator.
CHECKPOINTS = ("spec", "test-strategy", "plan", "step-plan", "test-spec", "carry-forward", "system-test-author",
               "release-plan")
# The stages whose minimal done result is refused for work the model has not done yet, and the exits the
# refusals name: the knowledge files the run keeps in the repository, and the loop that was never started.
EXPECTED_ROUTES = {
    "prepare": ["knowledge files"], "test-spec": ["knowledge files"],
    "test-green": ["start the loop"], "regression": ["start the loop"], "static-checks": ["start the loop"],
    "release-plan": ["knowledge files"], "release-verify": ["knowledge files", "outcome sections"],
}


class EveryStageRouteTests(RealCliCase):
    """Walk the whole graph through the real CLI by following only what each packet and refusal prints."""

    def follow(self, stage: str, reply: str, block: dict) -> str:
        """Do what a refusal names, edit ``block`` if it says to, and name the route taken."""
        if "keeps this run's planning knowledge in the repository" in reply:
            for path in re.findall(r"^- (/\S+)$", reply, re.M):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text("What this file records.\n", encoding="utf-8")
            return "knowledge files"
        if "Write these sections in " in reply:
            path = Path(re.search(r"Write these sections in (\S+), in detail", reply).group(1))
            headings = re.findall(r"'(## [^']+)'", reply)
            path.write_text("".join(f"{heading}\nWhat the run learned.\n\n" for heading in headings), encoding="utf-8")
            return "outcome sections"
        if "has not run: no terminal packet exists at" in reply:
            start = re.search(r"Start it with: (.*?)  and follow", reply, re.S).group(1)
            words = shlex.split(start)
            packet = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True,
                                               capture_output=True, check=True, timeout=60).stdout)
            while packet["status"] == "active":
                packet = json.loads(subprocess.run(packet["done_argv"], input=json.dumps(TRIVIAL), text=True,
                                                   capture_output=True, check=True, timeout=60).stdout)
            block["evidence_refs"].append(re.search(r"Then list (\S+) in evidence_refs", reply).group(1))
            return "start the loop"
        if "give the reason in red_na" in reply:
            block["red_na"] = "The tests already pass: they characterise existing behaviour."
            return "red_na"
        self.fail(f"{stage}: the refusal names no exit this test can follow:\n{reply}")

    def test_every_stage_accepts_its_printed_template_filled_minimally(self) -> None:
        run, head = self.new_run()
        taken: dict[str, list[str]] = {}
        for stage in EXPECTED_STAGES:
            header = next(row for row in head.splitlines() if row.startswith("ShipLoop navigator | "))
            self.assertTrue(header.startswith(f"ShipLoop navigator | {stage} | "), header)
            command, path, action = printed_callback(head)
            self.assertNotIn("<", command, stage)  # a complete command: only the result's content is left to write
            if stage == "implement":
                (self.repo_of(run) / "built.txt").write_text("hello\n")  # the work the step plan's step did
            block = self.fill_done(head)
            write_block(path, block)
            routes, result = [], self.run_printed(command)
            while result.returncode != 0:
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                routes.append(self.follow(stage, result.stdout + result.stderr, block))
                self.assertLess(len(routes), 4, f"{stage}: still refused after {routes}")
                write_block(path, block)
                result = self.run_printed(command)
            if routes:
                taken[stage] = routes
            if stage in CHECKPOINTS:
                # The accepted result starts an Improve child: its first packet leads with the printed bind command.
                self.assertIn("Next command (bind the selected Improve card", result.stdout)
                self.accepted(next(row for row in result.stdout.splitlines()
                                   if row.startswith("Next command (bind")).split("details below): ", 1)[1])
                state = self.state(run)
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
                nav.save(run, state)
                result = self.cli("next", "--run-dir", str(run))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            head = result.stdout
        self.assertEqual(taken, EXPECTED_ROUTES)
        self.assertEqual(self.state(run)["status"], "done")
        self.assertIn("It's all complete.", head)

    def one_outcome(self, stage: str, outcome: str) -> str | None:
        """Submit one stage's printed shape for ``outcome`` through its printed command; the problem, or None."""
        try:
            run, head = self.new_run(stage)
            command, path, action = printed_callback(head)
            shape = first_object(printed_shapes(head)[outcome])
            block = {**shape, "summary": "What happened in this stage.", "headline": "A step finished.",
                     "evidence_refs": [str(self.evidence)]}
            if outcome == "blocked":
                block["blocked_by"] = "external"
            if outcome == "replan":
                block["work_items"] = [{"id": "W9", "title": "Corrective item", "context": "What it fixes."}]
            write_block(path, block)
            result = self.run_printed(command)
            if result.returncode != 0:
                return f"{stage} {outcome}: refused:\n{result.stdout}{result.stderr}"
            if self.recorded(run, action)["outcome"] != outcome:
                return f"{stage} {outcome}: recorded as {self.recorded(run, action)['outcome']}"
        except Exception as error:  # noqa: BLE001 - reported with its stage and outcome below
            return f"{stage} {outcome}: {type(error).__name__}: {error}"
        return None

    def test_every_printed_outcome_shape_is_accepted_at_every_stage(self) -> None:
        loops = ("test-green", "regression", "static-checks")  # revise there needs a loop that stopped blocked
        pairs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            heads = list(pool.map(lambda stage: self.new_run(stage)[1], EXPECTED_STAGES))
        for stage, head in zip(EXPECTED_STAGES, heads):
            # Every allowed outcome other than done has its printed shape (so the pairs cannot be empty), and the
            # callback line is a complete command: no placeholder left for the model to invent.
            self.assertEqual(sorted(printed_shapes(head)), sorted(o for o in allowed_outcomes(head) if o != "done"),
                             stage)
            self.assertNotIn("<", printed_callback(head)[0], stage)
            pairs += [(stage, outcome) for outcome in sorted(printed_shapes(head))
                      if not (outcome == "revise" and stage in loops)]
        self.assertGreaterEqual(len(pairs), 70)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            problems = [p for p in pool.map(lambda pair: self.one_outcome(*pair), pairs) if p]
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
