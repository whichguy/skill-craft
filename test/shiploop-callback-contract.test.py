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

import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_reference as reference  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

sys.path.insert(0, str(ROOT / "test"))
from shiploop_loop_support import finish_loop, with_receipt  # noqa: E402
import shiploop_knowledge_support as knowledge_support  # noqa: E402

DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Nothing to change.", "handoff": "Nothing is open."}
BLOCKED_REPORT = {"classification": "unresolved", "exit_assessment": "unknown", "continuation_assessment": "blocked",
                  "evidence": "The item's goal cannot be reached as planned.", "handoff": "See the evidence."}
# The public graph, declared here and not read from the navigator, so a changed graph updates this test deliberately.
EXPECTED_STAGES = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
    "step-plan", "test-spec", "validate-existing", "implement", "test", "document", "verify", "carry-forward",
    "system-test-author", "system-test", "product-acceptance", "release-plan", "release-check", "release",
    "release-verify", "operations", "handoff",
)
# What the accepted plans record, so the stages after them have real commands to run.  The focused command fails
# until implement has created built.txt, which is the red-then-green the test stage expects (ShipLoop's base run sees
# TC-1 fail, the candidate run sees it pass).  It prints a verbose-unittest listing so ShipLoop reads TC-1's outcome.
FOCUSED = ("if test -f built.txt; then printf 'test_built (TC-1) ... ok\\n\\nRan 1 test in 0.001s\\n\\nOK\\n'; "
           "else printf 'test_built (TC-1) ... FAIL\\n\\nRan 1 test in 0.001s\\n\\nFAILED (failures=1)\\n'; "
           "exit 1; fi")
STEP_PLAN = {"paths": ["built.txt"], "steps": [{"id": "S1", "task": "Create built.txt", "deps": [],
                                               "criteria": ["C1"], "paths": ["built.txt"], "skills": [],
                                               "check": "test -f built.txt",
                                               "cards": ["coding-practices.md#existing-behavior"]}],
             "match": [{"what": "a plain text file, like the repository's other text files", "like": None}],
             "criteria": [{"id": "C1", "text": "built.txt exists"}],
             "test_commands": [{"command": FOCUSED, "suite": "focused", "ids": ["TC-1"], "criteria": ["C1"]},
                               {"command": "test -f built.txt", "suite": "regression"},
                               {"command": "true", "suite": "check"}],
             "expectations": [{"id": "E1", "state": "absent", "statement": "built.txt does not exist yet.",
                               "steps": ["S1"], "paths": ["built.txt"], "check": "test ! -e built.txt"}]}
SKILL_NONE = {"decision": "none", "reason": "Synthetic fixture: no procedure repeated."}
# The consumer contract's hand-off fields (2026-10-11): TC-1's case (its requirement R-1 has an entry in the living spec
# the fixture writes, LIVING_SPEC), the open-item lists, and release-verify's lessons.
TEST_CASES = [{"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "the focused command lists TC-1 ok",
               "red": "built.txt is missing on the base", "green": "built.txt exists after the change"}]
LESSONS = {"learned": "Synthetic fixture: nothing learned.", "considerations": "none", "open_next": "none"}
# implement's record (owner, 2026-10-17): the eight considerations and one observation for S1's criterion C1.
CONSIDERATIONS = {key: "Synthetic fixture: built.txt is one plain file; " + key.replace("_", " ") + " follows the step "
                  "plan (anchor: STEP_PLAN)." for key in nav.CONSIDERATIONS}
EVIDENCE = [{"criterion": "C1", "ran_or_inspected": "test -f built.txt", "observed": "exit 0",
             "output": "the step-proof record", "establishes": "built.txt exists", "limits": "none"}]
LIVING_SPEC = "# Spec\n\n## Requirements\n\n- R-1: built.txt exists.\n"
RESULTS = {
    "step-plan": dict(STEP_PLAN, follows=[]),
    "test-spec": {"test_cases": TEST_CASES, "assumptions": []},
    "implement": {"considerations": CONSIDERATIONS, "evidence": EVIDENCE},
    "verify": {"assumptions": []},
    "carry-forward": {"skill": SKILL_NONE, "assumptions": []},
    "system-test-author": {"system_commands": [{"command": "true", "suite": "check"}], "assumptions": []},
    "system-test": {"assumptions": []},
    "release-plan": {"consumer_checks": [{"command": "true", "suite": "check"}],
                     "consumer_entry": {"how": "open built.txt", "sources": ["built.txt"]}, "assumptions": []},
    "release-verify": {"assumptions": [], "lessons": LESSONS},
}
# The hand-off fields an inner loop stage's template leaves to its result-shape block (navigator.HANDOFF_SHAPES).
HANDOFF_KEYS = ("follows", "test_cases", "not_covered", "assumptions", "lessons")

# Request outcomes no executed check observed, as product-acceptance lists them: one reported at the handoff, one at the
# stage whose external effect it gates.
UNVERIFIED_ENTRY = {"outcome": "the exported file opens in the customer's reader",
                    "reason": "this host has no copy of that reader",
                    "check": "open the exported file in the reader and report what shows",
                    "owner": "the user", "due_stage": "handoff"}
UNVERIFIED_EARLY = dict(UNVERIFIED_ENTRY, outcome="the deployed page loads for a signed-in user",
                        reason="no sign-in is available to this run", due_stage="release-check")
OPEN_ASSUMPTION = {"id": "A1", "assumption": "the export is checked by file tests only", "disposition": "open",
                   "check": "open the export in the reader", "reason": "no reader here", "consumer": "W1"}


def write_block(path: Path, value: object, *, loop: bool = True) -> None:
    """Write a result file: Markdown whose one shiploop-state fence holds the JSON.

    At an INNER stage a done or revise result first runs the stage's Until Loop through the real runtime (done ends it
    satisfied, revise stops it blocked) and cites the receipt, as the printed template does; ``loop=False`` writes the
    value as given, for the tests of the loop refusal itself.
    """
    if loop and isinstance(value, dict) and value.get("outcome") in ("done", "revise") and path.parent.name == "inbox":
        run = path.parent.parent
        if (run / "state.md").is_file() and loops.cursor(store.read_record(run / "state.md")) is not None:
            receipt = finish_loop(run, outcome="done" if value["outcome"] == "done" else "blocked")
            value = with_receipt(value, receipt)
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
            head = self.accepted(command)
            state = self.state(run)
            if state.get("active_improve") is not None:
                # implement's per-step Improve child (2026-10-10): its review is not under test here, so finish it with
                # the pure API and write the next action's loop contract with the function the CLI's transition uses.
                action = state["active_improve"]["action_id"]
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
                nav.save(run, state)
                for relative, text in loops.contract_writes(run, state).items():
                    (run / relative).parent.mkdir(parents=True, exist_ok=True)
                    (run / relative).write_text(text, encoding="utf-8")
                head = self.cli("next", "--run-dir", str(run)).stdout
            return run, head
        repo = self.repo = self.make_repo()
        run = self.base / ("run" + repo.name.removeprefix("repo"))
        started = self.cli("init", "--repo", str(repo), "--run-dir", str(run), "--prompt=add hello",
                           "--improve-skill", str(CARD), *(f"--{k}={v}" for k, v in init.items()))
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        state = store.read_record(run / "state.md")
        if stage == "intake":
            return run, started.stdout
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
            "unverified": [],
            **{key: value for result in RESULTS.values() for key, value in result.items()
               if key not in ("outcome", "summary", "assumptions")},
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
        # Two templates omit a field their gate requires (reported; pinned by
        # test_each_inner_template_prints_every_field_its_gate_requires), so add the fixture's own value.
        if "steps" in block and "expectations" not in block:
            block["expectations"] = STEP_PLAN["expectations"]
        if "ShipLoop navigator | carry-forward | " in head and "skill" not in block:
            block["skill"] = SKILL_NONE
        found = re.search(r"ShipLoop navigator \| ([a-z-]+) \| ", head)
        stage = found.group(1) if found else ""
        for key, value in RESULTS.get(stage, {}).items():
            if key in HANDOFF_KEYS and key not in block:
                block[key] = value
        if stage == "test-spec":
            # One case per focused ID of this run's step plan, naming R-1, which the living spec gets as an entry.
            path = printed_callback(head)[1]
            state = store.read_record(path.parent.parent / "state.md")
            _action, plan = test_loop._step_plan(state, state["work_items"][state["work_index"]]["id"])
            focused = [ident for row in plan.get("test_commands") or () if row.get("suite") == "focused"
                       for ident in row.get("ids") or ()]
            block["test_cases"] = [dict(TEST_CASES[0], id=ident) for ident in focused]
            living = Path(state["repo"]) / knowledge.HOME / "spec.md"
            if focused and knowledge.entry_text(Path(state["repo"]), "R-1") is None:
                living.parent.mkdir(parents=True, exist_ok=True)
                living.write_text((living.read_text(encoding="utf-8") if living.is_file() else "") + LIVING_SPEC,
                                  encoding="utf-8")
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

    @staticmethod
    def handoff_of(out: str) -> str:
        """The handoff file an Improve packet's first instruction names (the improve skill reads it)."""
        named = re.search(r"/improve " + re.escape(nav.IMPROVE_ARGUMENT_PREFIX) + r"(\S+)", out)
        assert named is not None, out
        return Path(named.group(1)).read_text(encoding="utf-8")

    def started_child(self, run: Path) -> tuple[Path, Path]:
        """The opening ShipLoop wrote and the receipt of the Improve child it started at the transition.

        Since 2026-10-11 the Improve stage is set up by the script: the producer's complete leaves a bound child with its
        opening, frozen contract and an active receipt, and the model neither writes the opening nor starts the child.
        """
        child = self.state(run)["active_improve"]
        return nav.improve_opening_path(child), standalone.receipt_path(child)

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
        cases = [
            ("an absolute evidence_refs path that does not exist", "intake",
             lambda block: {**block, "evidence_refs": [str(self.base / "no-such-note.md")]},
             "evidence_refs cite files that do not exist"),
            ("an open assumption whose consumer is not in the plan", "plan",
             lambda block: {**block, "assumptions": [{"id": "A2", "assumption": "y holds", "disposition": "open",
                                                      "check": "run y", "reason": "later", "consumer": "W9"}]},
             "is not a work item in this plan"),
            ("a criterion no test command names", "step-plan",
             lambda block: {**block, "criteria": [*block["criteria"], {"id": "C2", "text": "an unnamed criterion"}],
                            "steps": [dict(block["steps"][0], criteria=["C1", "C2"])]},
             "every criterion needs a test command that confirms it"),
            ("a step whose dependency is a later step", "step-plan",
             lambda block: {**block, "steps": [dict(block["steps"][0], id="S1", deps=["S2"]),
                                               dict(block["steps"][0], id="S2", deps=[])]},
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
            ("no unverified list", "product-acceptance",
             lambda block: {k: v for k, v in block.items() if k != "unverified"},
             "a done product-acceptance result must list unverified"),
            ("an unverified entry without an owner", "product-acceptance",
             lambda block: {**block, "unverified": [{key: value for key, value in UNVERIFIED_ENTRY.items()
                                                      if key != "owner"}]},
             "unverified[0] needs exactly outcome, reason, check, owner, due_stage"),
            ("an unverified entry that keeps one template placeholder", "product-acceptance",
             lambda block: {**block, "unverified": [dict(UNVERIFIED_ENTRY, check="<what the owner does and reports>")]},
             "unverified[0].check is still a template placeholder"),
            ("an unverified entry whose field holds two placeholders", "product-acceptance",
             lambda block: {**block, "unverified": [dict(UNVERIFIED_ENTRY, owner="<who> or <who else>")]},
             "unverified[0].owner is still a template placeholder"),
            ("an unverified due stage that is not a later stage", "product-acceptance",
             lambda block: {**block, "unverified": [dict(UNVERIFIED_ENTRY, due_stage="system-test")]},
             "is not a later stage"),
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
        with self.subTest("the unverified template row copied unchanged"):
            run, head = self.new_run("product-acceptance")
            command, path, action = printed_callback(head)
            template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
            self.assertEqual(len(template["unverified"]), 1)  # the head prints one example row to replace or delete
            write_block(path, dict(self.fill_done(head), unverified=template["unverified"]))
            self.assertIn("still a template placeholder", self.refused(command, run))
            write_block(path, dict(self.fill_done(head), unverified=[UNVERIFIED_ENTRY]))
            self.accepted(command)
            self.assertEqual(self.recorded(run, action)["unverified"], [UNVERIFIED_ENTRY])
        with self.subTest("the docs/shiploop files a close requires"):
            run, head = self.new_run("prepare")   # test-spec is no close since consumer contract 4b
            command, path, action = printed_callback(head)
            write_block(path, self.fill_done(head))
            reply = self.refused(command, run)
            self.assertIn("keeps this run's planning knowledge in the repository", reply)
            self.accept_after_the_knowledge_files(command, run)
            self.assertEqual(self.recorded(run, action)["outcome"], "done")

    @staticmethod
    def full_packet(head: str) -> str:
        """The whole packet, whitespace-flattened.  ``emit`` prints it whole up to PRINT_LIMIT (re-cut round 2); only an
        over-limit packet prints a head with a "Full packet:" pointer."""
        return " ".join(full_packet_text(head).split())

    def test_a_check_row_with_ids_is_refused_with_the_rule_the_packet_prints_and_the_row_without_them_is_accepted(self) -> None:
        # Packet review 2026-10-10, row 2: the refusal came 4+ times because only the template's focused row showed ids.
        rows = {"system-test-author": "system_commands", "release-plan": "consumer_checks"}
        for stage, field in rows.items():
            with self.subTest(stage):
                run, head = self.new_run(stage)
                command, path, action = printed_callback(head)
                self.assertIn("no ids or min_tests", self.full_packet(head))  # both duties say a check row has none
                good = self.fill_done(head)
                write_block(path, {**good, field: [{"command": "true", "suite": "check", "ids": ["TC-1"]}]})
                first = self.run_printed(command)  # a close asks for its knowledge files before it reads the result
                for named in re.findall(r"^- (/\S+)$", first.stdout + first.stderr, re.M):
                    Path(named).parent.mkdir(parents=True, exist_ok=True)
                    Path(named).write_text("What this file records.\n", encoding="utf-8")
                self.assertIn("a check command is judged by its exit code and takes no ids or min_tests",
                              self.refused(command, run))
                write_block(path, {**good, field: [{"command": "true", "suite": "check"}]})
                self.accept_after_the_knowledge_files(command, run)
                self.assertEqual(self.recorded(run, action)["outcome"], "done")

    def test_an_assumption_with_an_extra_key_is_refused_as_the_plan_packet_says_and_the_exact_fields_are_accepted(self) -> None:
        # Packet review 2026-10-10, row 11a: r2-checkers-sonnet was refused twice for a key the template does not print.
        run, head = self.new_run("plan")
        command, path, action = printed_callback(head)
        self.assertIn("with exactly the template's fields per disposition", self.full_packet(head))
        good = self.fill_done(head)
        row = good["assumptions"][0]
        self.assertEqual(row["disposition"], "evidenced")
        write_block(path, {**good, "assumptions": [{**row, "consumer": "W1"}]})
        self.assertIn("needs exactly evidence", self.refused(command, run))
        write_block(path, good)
        self.accepted(command)
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

    def test_release_verify_names_its_knowledge_files_before_the_refusal_and_the_named_files_are_accepted(self) -> None:
        # release-verify runs the consumer checks and closes the knowledge home.  Its Checked-by line named only the
        # run, so its files were met first as a refusal in 4 runs (packet review 2026-10-10, P-rv-1).  The packet now says
        # it first; writing what it says is accepted in one go.  Since consumer contract 4c the close needs environment.md
        # alone: the lessons are a result field.
        run, head = self.new_run("release-verify")
        command, path, action = printed_callback(head)
        full = full_packet_text(head)
        checked = next(row for row in full.splitlines() if row.startswith("Checked by: "))
        self.assertIn("a HOME file this stage must have written, missing or empty", checked)
        self.assertIn("reruns every recorded test command", checked)  # the run the line used to name alone
        done = full[full.index("Done when"):full.index("Checked by: ")]
        for word in ("environment.md", "lessons"):
            self.assertIn(word, done)
        self.assertNotIn("outcome.md", full)
        write_block(path, self.fill_done(head))
        reply = self.refused(command, run)
        named = re.findall(r"^- (/\S+)$", reply, re.M)
        self.assertEqual(sorted(Path(file).name for file in named), ["environment.md"])
        for file in named:
            self.assertIn(Path(file).name, done)  # every file the refusal names was named before it
            Path(file).parent.mkdir(parents=True, exist_ok=True)
            Path(file).write_text("What this file records.\n", encoding="utf-8")
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["outcome"], "done")

    def git(self, repo: Path, *argv: str) -> str:
        return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@example.invalid", "-c", "user.name=t", *argv],
                              env=self.env, check=True, capture_output=True, text=True).stdout

    def test_a_repository_whose_home_has_no_architecture_is_refused_at_prepare_and_the_file_it_names_is_accepted(self) -> None:
        # A home an earlier version committed has every file but architecture.md.  The next run meets one refusal, at
        # prepare, that names that file alone and says what it holds; writing exactly it is accepted by the same command.
        run, head = self.new_run("prepare")
        command, path, action = printed_callback(head)
        repo = self.repo_of(run)
        write_block(path, self.fill_done(head))
        listed = re.findall(r"^- (/\S+)$", self.refused(command, run), re.M)
        architecture = [named for named in listed if named.endswith("/docs/shiploop/architecture.md")]
        self.assertEqual(len(architecture), 1, listed)  # a first prepare asks for it with the rest
        for named in listed:
            if named not in architecture:
                Path(named).parent.mkdir(parents=True, exist_ok=True)
                Path(named).write_text("What this file records.\n", encoding="utf-8")
        self.git(repo, "add", "docs/shiploop")
        self.git(repo, "commit", "-qm", "an earlier run's home")
        reply = self.refused(command, run)
        self.assertEqual(reply.splitlines()[0], "ShipLoop navigator: Before prepare is done, write: " + architecture[0])
        self.assertEqual(re.findall(r"^- (/\S+)$", reply, re.M), architecture)
        self.assertIn("\narchitecture.md holds the stack (language, frameworks, dependencies and why)", reply)
        Path(architecture[0]).write_text("What this file records.\n", encoding="utf-8")  # exactly the file the refusal names
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["outcome"], "done")
        self.assertTrue(self.git(repo, "log", "-1", "--format=%s").strip().endswith("knowledge at prepare"))
        # The file the refusal named: nothing else rides in the commit (no feature list since consumer contract 4c).
        self.assertEqual(sorted(self.git(repo, "show", "--name-only", "--format=", "HEAD").split()),
                         ["docs/shiploop/architecture.md"])

    def accept_a_prepare_with_files(self, sectioned: bool) -> tuple:
        """A run at prepare whose refusal's files are written (with every named section, or as prose), then accepted.

        Returns the run, the accepted command's CLI result, and the action id.
        """
        run, head = self.new_run("prepare")
        command, path, action = printed_callback(head)
        repo = self.repo_of(run)
        write_block(path, self.fill_done(head))
        for named in re.findall(r"^- (/\S+)$", self.refused(command, run), re.M):
            file = Path(named)
            file.parent.mkdir(parents=True, exist_ok=True)
            living = file.parent == repo / knowledge.HOME and file.name in knowledge.SECTIONS
            file.write_text(knowledge_support.sections(file.name) if sectioned and living else "What this file records.\n",
                            encoding="utf-8")
        result = self.run_printed(command)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return run, result, action

    @staticmethod
    def named_in(line: str) -> list:
        """The headings a printed notice line names: the quoted words between the prefix and the first semicolon."""
        return re.findall(r"'([^']+)'", line[len(knowledge.NOTICE_PREFIX):].split(";", 1)[0])

    def test_a_close_whose_files_have_no_named_sections_is_accepted_and_prints_one_counted_line_per_file(self) -> None:
        # The notice is not a refusal: prose files that the refusal asked for are accepted by the same command, and the
        # lines are on stdout, each starting with the fixed prefix, the file's absolute path first.
        run, result, action = self.accept_a_prepare_with_files(sectioned=False)
        self.assertEqual(self.recorded(run, action)["outcome"], "done")
        found = [row for row in result.stdout.splitlines() if row.startswith(knowledge.NOTICE_PREFIX)]
        self.assertEqual(len(found), len(knowledge.SECTIONS))
        self.assertEqual(found, knowledge.section_notices(self.state(run), "prepare"))
        self.assertEqual([row.split(" ")[3] for row in found],
                         [str(self.repo_of(run) / knowledge.HOME / name) for name in knowledge.SECTIONS])
        self.assertEqual([heading for row in found for heading in self.named_in(row)],
                         [heading for headings in knowledge.SECTIONS.values() for heading in headings])
        self.assertEqual("".join(row for row in result.stdout.splitlines(True) if row.startswith(knowledge.NOTICE_PREFIX)),
                         "".join(row + "\n" for row in found))
        self.assertEqual(result.stdout.count(knowledge.ARCHITECTURE_HOLDS), 1)
        self.assertNotIn(knowledge.NOTICE_PREFIX, result.stderr)
        self.assertTrue(self.git(self.repo_of(run), "log", "-1", "--format=%s").strip().endswith("knowledge at prepare"))

    def test_the_fix_a_notice_names_applied_to_its_file_silences_that_heading_and_only_that_heading(self) -> None:
        # The notice is no gate, so the way out is read from the printed line itself: the headings it names, the '## ' it says.
        run, result, action = self.accept_a_prepare_with_files(sectioned=False)
        printed = [row for row in result.stdout.splitlines() if row.startswith(knowledge.NOTICE_PREFIX)]
        line = next(row for row in printed if " " + str(self.repo_of(run) / knowledge.HOME / "environment.md") + " has " in row)
        self.assertIn("'Commands'", line.split(";", 1)[0])
        self.assertIn("add the heading if missing", line)
        file = Path(line.split(" ")[3])
        file.write_text(file.read_text(encoding="utf-8") + "\n## Commands\n\nnpm test\n", encoding="utf-8")
        again = knowledge.section_notices(self.state(run), "prepare")
        self.assertEqual(len(again), len(printed))
        self.assertEqual([row for row in again if row != again[printed.index(line)]], [row for row in printed if row != line])
        expected = [heading for heading in self.named_in(line) if heading != "Commands"]
        self.assertEqual(self.named_in(again[printed.index(line)]), expected)
        self.assertNotIn("'Commands'", again[printed.index(line)].split(";", 1)[0])

    def test_a_close_whose_files_have_every_named_section_is_accepted_and_prints_no_notice(self) -> None:
        run, result, action = self.accept_a_prepare_with_files(sectioned=True)
        self.assertEqual(self.recorded(run, action)["outcome"], "done")
        self.assertNotIn(knowledge.NOTICE_PREFIX, result.stdout + result.stderr)

    def test_test_spec_with_validate_existing_recorded_after_it_is_no_close_and_prints_no_notice(self) -> None:
        # The common route: test-spec is accepted and, in the same call, the script records validate-existing (every
        # expectation matches).  test-spec is no close since consumer contract 4b (its cases are in state): it requires no
        # feature file, and a home of prose files prints no section notice.
        run, head = self.new_run("test-spec", **{"planning-review": "none"})
        command, path, action = printed_callback(head)
        repo, state = self.repo_of(run), self.state(run)
        home = repo / knowledge.HOME
        for name in knowledge.SECTIONS:
            (home / name).parent.mkdir(parents=True, exist_ok=True)
            (home / name).write_text("What this file records.\n", encoding="utf-8")
        write_block(path, self.fill_done(head))
        before = len(state["history"])
        result = self.run_printed(command)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = [(row["stage"], row["outcome"]) for row in self.state(run)["history"][before:]]
        self.assertEqual(rows, [("test-spec", "done"), ("validate-existing", "done")], "the route under test")
        self.assertNotIn(knowledge.NOTICE_PREFIX, result.stdout + result.stderr)

    def test_a_stage_that_is_no_close_prints_no_notice_although_a_file_lacks_its_sections(self) -> None:
        run, head = self.new_run("intake")
        command, path, action = printed_callback(head)
        home = self.repo_of(run) / knowledge.HOME
        home.mkdir(parents=True, exist_ok=True)
        (home / "environment.md").write_text("# Environment\n\nNode 22.\n", encoding="utf-8")
        write_block(path, self.fill_done(head))
        result = self.run_printed(command)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn(knowledge.NOTICE_PREFIX, result.stdout + result.stderr)
        self.assertEqual(self.recorded(run, action)["outcome"], "done")

    def test_a_dropped_decision_id_is_refused_with_its_exit_on_line_1_and_the_exit_is_accepted(self) -> None:
        # A later run's prepare, on a repository whose home an earlier run committed with two decisions.  Line 1 is the
        # fix, the file and the command, with no ID list; the IDs follow on line 2.  The heading to use is read from the
        # refusal, not known by the test.
        run, head = self.new_run("prepare")
        command, path, action = printed_callback(head)
        repo = self.repo_of(run)
        write_block(path, self.fill_done(head))
        for named in re.findall(r"^- (/\S+)$", self.refused(command, run), re.M):
            Path(named).parent.mkdir(parents=True, exist_ok=True)
            Path(named).write_text("What this file records.\n", encoding="utf-8")
        architecture = repo / "docs/shiploop/architecture.md"
        architecture.write_text("# Architecture\n\nAD-1 In-memory board.\nAD-2 One module per concern.\n", encoding="utf-8")
        self.git(repo, "add", "docs/shiploop")
        self.git(repo, "commit", "-qm", "an earlier run's home")
        architecture.write_text("# Architecture\n\nAD-1 In-memory board.\n", encoding="utf-8")  # this run's version loses AD-2
        reply = self.refused(command, run)
        first = reply.splitlines()[0]
        # The template, not a column: where `cut -c1-250` falls depends on how long this machine's temporary directory is
        # (the knowledge suite tests the cut at the lengths of the real checkouts).
        self.assertEqual(first.replace(str(architecture), "<file>"),
                         "ShipLoop navigator: Restore the lost AD-<n> in <file> or move it under 'Superseded', "
                         "then run the same complete command again.")
        self.assertNotIn("AD-2", first)
        self.assertIn("The architecture no longer mentions AD-2.", reply.splitlines()[1])
        heading = re.search(r"move it under '([^']+)'", first).group(1)
        architecture.write_text(architecture.read_text(encoding="utf-8") + "\n## " + heading + "\n\nAD-2: split by layer instead.\n",
                                encoding="utf-8")
        self.accepted(command)  # the same printed command
        self.assertEqual(self.recorded(run, action)["outcome"], "done")
        self.assertIn("## " + heading, self.git(repo, "show", "HEAD:docs/shiploop/architecture.md"))

    def test_an_architecture_line_that_looks_like_a_credential_is_accepted_and_committed(self) -> None:
        # Owner decision 2026-10-16: no credential-pattern refusal. architecture.md records auth shapes
        # ("Password: bcrypt, cost 12", "SECRET_KEY = os.environ[...]"); the close takes them as written and commits them.
        run, head = self.new_run("prepare")
        command, path, action = printed_callback(head)
        repo = self.repo_of(run)
        write_block(path, self.fill_done(head))
        for named in re.findall(r"^- (/\S+)$", self.refused(command, run), re.M):
            Path(named).parent.mkdir(parents=True, exist_ok=True)
            Path(named).write_text("What this file records.\n", encoding="utf-8")
        architecture = repo / "docs/shiploop/architecture.md"
        written = "# Architecture\n\nPassword: bcrypt, cost 12\nSECRET_KEY = os.environ['SECRET_KEY']\nAuth: sf login (alias de)\n"
        architecture.write_text(written, encoding="utf-8")
        reply = self.accepted(command)  # the same printed command, no rewording asked for
        self.assertNotIn("Reword", reply)
        self.assertNotIn("look like credentials", reply)
        self.assertEqual(self.recorded(run, action)["outcome"], "done")
        self.assertEqual(self.git(repo, "show", "HEAD:docs/shiploop/architecture.md"), written)

    def test_a_result_with_credential_looking_text_is_accepted_by_the_same_command(self) -> None:
        # Owner decision 2026-10-16: documentation lines such as these were refused by the retired screen (`auth`,
        # `token` and `signature` followed by `:` and a word); the result is accepted as written.
        token = "ghp_" + "Ab1" * 8  # a made-up string of the shape the retired screen refused
        run, head = self.new_run("intake")
        command, path, action = printed_callback(head)
        summary = ("Auth: sf login (alias de); access token: not printed; signature: static; Bearer " + token
                   + "; password=hunter2")
        write_block(path, {**self.fill_done(head), "summary": summary})
        reply = self.accepted(command)
        self.assertNotIn("appears to contain a credential", reply)
        self.assertEqual(self.recorded(run, action)["summary"], summary)
        packet = self.full_packet(head)
        self.assertNotIn("credential pattern", packet)
        self.assertNotIn("looks like a credential", packet)

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

    def test_shiploop_writes_the_opening_with_the_four_exact_headings_and_a_renamed_one_is_told_the_heading(self) -> None:
        run, head = self.new_run("spec")
        command, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        out = self.accepted(command)
        opening, _receipt = self.started_child(run)
        text = opening.read_text(encoding="utf-8")
        found = nav._opening_sections(text)  # the gate ShipLoop's own opening passes at the transition
        self.assertEqual(tuple(found), nav.OPENING_SECTIONS)
        self.assertTrue(all(body and body != "..." for body in found.values()))
        self.assertNotIn("write the opening file", out + self.handoff_of(out))
        # The section gate still names the heading it expected and the one it found.
        with self.assertRaises(nav.NavigatorError) as caught:
            nav._opening_sections(text.replace("## Environment", "## Environment and validation"))
        self.assertIn('no line reading exactly "## Environment"', str(caught.exception))
        self.assertIn("## Environment and validation", str(caught.exception))  # the heading it found, to rename

    def test_shiploop_writes_the_opening_and_starts_the_child_at_the_transition(self) -> None:
        """The printed packet asks the model to do neither: ShipLoop wrote the opening, froze the contract and started the child.

        Batch 1010 A3 (the missing opening directory) is subsumed: ShipLoop makes the directory and the file itself.
        """
        for stage in ("spec", "test-strategy"):
            with self.subTest(stage=stage):
                run, head = self.new_run(stage)
                command, path, _ = printed_callback(head)
                write_block(path, self.fill_done(head))
                out = self.accepted(command)
                opening, receipt = self.started_child(run)
                self.assertTrue(opening.is_file())
                self.assertTrue(opening.with_name("start.json").is_file())
                self.assertTrue(opening.with_name("parent-return.md").is_file())
                self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "active")
                handoff = self.handoff_of(out)
                for text in (out, handoff):
                    self.assertNotIn("write the opening file", text)
                    self.assertNotIn("--opening", text)
                self.assertNotIn("improve-start", out)
                self.assertTrue(out.splitlines()[0].startswith("ShipLoop navigator | improve | revision "))

    def test_a_directory_that_cannot_be_made_does_not_stop_the_transition_or_its_packet(self) -> None:
        """Batch 1010 A3 review: the Improve directory is a courtesy, so its failure must not take the transition down.

        REPORTED SOURCE DEFECT (2026-10-11, improve-stage port): a regular file where ``.shiploop-improve`` belongs
        makes ``_start_improve``'s ``opening.parent.mkdir`` raise NotADirectoryError, and ``_improve_stage_start``
        catches only NavigatorError, so the producer's complete exits 2 ("ShipLoop blocked") instead of leaving the
        Improve stage pending with the packet naming ``improve-start --restart-stopped``.  Remove this decorator when
        the source catches OSError there.
        """
        run, head = self.new_run("spec")
        command, path, _ = printed_callback(head)
        write_block(path, self.fill_done(head))
        (self.repo_of(run) / ".shiploop-improve").write_text("a file, not a directory\n", encoding="utf-8")
        out = self.accepted(command)
        self.assertTrue(out.splitlines()[0].startswith("ShipLoop navigator | improve | revision "))
        self.assertIn("--restart-stopped", out)

    def test_an_empty_opening_section_is_refused_naming_it(self) -> None:
        """The section gate ShipLoop's own opening passes still names an empty section (the model no longer writes one)."""
        text = ("## Current context and desired improvements\nHello.\n\n## Scope\na.txt\n\n"
                "## Authority\nLocal edits only.\n\n## Environment\n...\n")
        with self.assertRaises(nav.NavigatorError) as caught:
            nav._opening_sections(text)
        self.assertIn("opening needs non-empty sections: ## Environment", str(caught.exception))
        self.assertEqual(tuple(nav._opening_sections(text.replace("...", "Python 3."))), nav.OPENING_SECTIONS)

    def test_a_condition_no_command_can_confirm_leaves_criteria_by_the_exit_the_refusal_names(self) -> None:
        """Batch 1009 S1: the step plan used to tell the model to mark such a criterion `Confirm by: unconfirmable here`
        in `criteria`, which the gate refuses (a passing command ShipLoop runs is the only confirmation).  The packet
        and the refusal now name the same exit: the condition is not a criterion, it is an open item in the summary."""
        run, head = self.new_run("step-plan")
        command, path, action = printed_callback(head)
        packet = " ".join(full_packet_text(head).split())
        # the duty says it in two sentences (re-cut 2026-10-11): the condition is not a criterion; list it as an open item
        exit_sentence = re.search(r"[^.]*no command can confirm[^.]*\.[^.]*\.", packet)
        self.assertIsNotNone(exit_sentence, "the step plan packet says what to do with a condition no command can confirm")
        self.assertIn("open item", exit_sentence.group(0))
        good = self.fill_done(head)
        person_only = {"id": "C2", "text": "A person signs off the layout. Confirm by: unconfirmable here - needs a person."}
        # The step names C2 too, so the plan is sized and the refusal is the one for a criterion no command confirms.
        write_block(path, {**good, "criteria": [*good["criteria"], person_only],
                           "steps": [dict(good["steps"][0], criteria=["C1", "C2"])]})
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

    def test_test_strategy_done_when_asks_a_probe_of_each_host_tool(self) -> None:
        """Batch 1010 A4: the text every run displays carries the probe obligation, and the entry is not a free exit.

        The probe paragraph of the test-strategy duty sits deep in a long packet; neither round-2 Sonnet run read it
        (no tool result holds "probed now by doing" or "stand-in"), both read only the head, Checkers first ran Chrome
        about 470 events after that head and Battleship never ran a command naming it.  Done-when is the text every run
        displays, so the obligation goes there and the how stays in the duty.  Two defects the audit found are held
        here.  A condition that let "record the access gap" stand in for the probe passed both runs unchanged, so the
        gap must be the result of a failed probe.  And "do the case's first step" with no stand-in repeats the wording
        that sent a run to the product's own address before the product existed (482fff76).  A third, found on review:
        an Improve contract joins the entries with "; ", so an entry holds no ";" of its own (the stage-spec test pins
        that for every stage).  The one automatic check stays the form check: a cited path must exist.
        """
        run, head = self.new_run("test-strategy")
        command, path, _ = printed_callback(head)
        done_when = " ".join(head.split("Done when", 1)[1].split("Checked by:", 1)[0].split())
        for part in ("each case that needs a host tool (a browser, a device, an account, a service)",
                     "cites the output of probing it now by doing the case's first step",
                     "against a stand-in while the product does not exist, and only a failed probe is recorded as the "
                     "access gap",
                     "the requirement it leaves unobserved"):
            self.assertIn(part, done_when)
        self.assertEqual(done_when.count("probing"), 1)  # one entry, stated once
        # The Checked-by line claims no script check of the probe: the model confirms it, and a cited path must exist.
        checked = head.split("Checked by:", 1)[1].split("\n", 1)[0]
        self.assertIn("you confirm each condition", checked)
        self.assertNotIn("probe", checked)
        output = self.base / "probe-output.txt"
        write_block(path, {**self.fill_done(head), "evidence_refs": [str(output)]})
        self.assertIn("evidence_refs cite files that do not exist", self.refused(command, run))
        output.write_text("page title read back by the tool: stand-in\n")
        self.accepted(command)

    def test_the_implement_packet_does_not_ask_for_a_field_the_accepted_plan_does_not_hold(self) -> None:
        """Batch 1009 S1: an item that records no test command has no `criteria` and no `Confirm by` text, yet the
        implement Done-when told the model to confirm each criterion by its `Confirm by`.  The row names no field
        and no route (a recorded command exists only for an item that has tests); the accepted plan decides how."""
        run, head = self.new_run("step-plan", **{"planning-review": "none"})
        command, path, _ = printed_callback(head)
        good = self.fill_done(head)
        write_block(path, {**{key: value for key, value in good.items() if key not in ("criteria", "test_commands")},
                           "paths": ["README.md"], "test_commands": [], "test_commands_na": "documentation only",
                           "steps": [{"id": "S1", "task": "Document the change.", "paths": ["README.md"], "skills": [],
                                      "check": "test -f README.md", "cards": ["coding-practices.md#documentation"]}],
                           "expectations": [{"id": "E1", "state": "absent", "statement": "README.md does not exist yet.",
                                             "steps": ["S1"], "paths": ["README.md"],
                                             "check": "test ! -e README.md"}]})
        spec_head = self.accepted(command)
        # test-spec is issued for every item now; a documentation-only item's spec lists no cases.
        self.assertIn("ShipLoop navigator | test-spec | ", spec_head)
        spec_command, spec_path, _ = printed_callback(spec_head)
        write_block(spec_path, self.fill_done(spec_head))
        refused = self.run_printed(spec_command)
        if refused.returncode != 0:  # the knowledge files test-spec closes: write the ones the refusal names
            for named in re.findall(r"(/\S+\.md)", refused.stdout + refused.stderr):
                if not Path(named).exists():
                    Path(named).parent.mkdir(parents=True, exist_ok=True)
                    Path(named).write_text("What this file records.\n", encoding="utf-8")
        implement = self.accepted(spec_command)
        # Every expectation matches, so ShipLoop records validate-existing and issues implement.
        self.assertIn("ShipLoop navigator | implement | ", implement)
        # An inner stage's head points at the /until-loop argument, whose exit conditions are its one Done-when list.
        self.assertIn("Done when: every exit condition in the /until-loop argument below holds", implement)
        done_when = implement.split("Exit when ALL of these hold:", 1)[1].split("Repeat while", 1)[0]
        done_when = " ".join(done_when.split())
        # Owner 2026-10-17: the row names the criteria assigned to this step, which holds vacuously when the plan records
        # none, and never a `Confirm by` field; the step block prints no Serves line, so no criterion is asked for.
        self.assertIn("each criterion assigned to this step has evidence", done_when)
        self.assertNotIn("Confirm by", done_when)
        self.assertIn("after the last edit", done_when)
        self.assertNotIn("  Serves:", implement)


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


class StepSizingRouteTests(RealCliCase):
    """The step-sizing gate (owner, 2026-10-10): each refusal names its fault, and the sized plan is accepted.

    Every step lists the paths it changes (from the item's paths) and, when the result lists criteria, the criteria it
    satisfies; every criterion is satisfied by some step; and a step that only changes test files is refused unless
    the whole item is tests.
    """

    def test_each_unsized_step_plan_is_refused_by_name_and_the_sized_plan_is_accepted(self) -> None:
        run, head = self.new_run("step-plan")
        command, path, action = printed_callback(head)
        good = self.fill_done(head)
        step = good["steps"][0]
        self.assertEqual((step["paths"], step["criteria"]), (["built.txt"], ["C1"]))
        bare = {key: value for key, value in step.items() if key not in ("paths", "criteria")}
        test_file = "tests/test_built.py"
        cases = [
            # Owner D3 (2026-10-17): a step names its Proof and cards; its paths are optional.
            ("a step without its check", {**good, "steps": [{k: v for k, v in step.items() if k != "check"}]},
             "step S1 must name its check"),
            ("a step without cards", {**good, "steps": [{k: v for k, v in step.items() if k != "cards"}]},
             "step S1 must list cards"),
            ("a card that does not resolve", {**good, "steps": [dict(step, cards=["coding-practices.md#nope"])]},
             "step S1 names cards that do not resolve to a reference file and heading: coding-practices.md#nope"),
            ("a step without criteria while the result lists criteria", {**good, "steps": [dict(bare, paths=["built.txt"])]},
             "step S1 must list criteria: the IDs of the criteria it satisfies (C1)"),
            ("a step naming a criterion the result does not list", {**good, "steps": [dict(step, criteria=["C1", "C9"])]},
             "step S1 names criteria the result does not list: C9"),
            ("a step path the item does not declare", {**good, "steps": [dict(step, paths=["built.txt", "other.txt"])]},
             "step S1 changes paths the item does not declare: other.txt"),
            ("a criterion no step satisfies",
             {**good, "criteria": [*good["criteria"], {"id": "C2", "text": "built.txt is committed"}],
              "test_commands": [*good["test_commands"], {"command": "true", "suite": "check", "criteria": ["C2"]}]},
             "no step satisfies C2"),
            ("a step that only changes test files",
             {**good, "paths": ["built.txt", test_file],
              "steps": [dict(step, id="S1", paths=[test_file]), dict(step, id="S2", deps=["S1"])]},
             "step S1 only changes test files. Tests are not a step"),
        ]
        for label, block, fragment in cases:
            with self.subTest(label):
                write_block(path, block)
                self.assertIn(fragment, self.refused(command, run))
        write_block(path, dict(good, steps=[{k: v for k, v in step.items() if k != "paths"}]))
        self.accepted(command)
        self.assertNotIn("paths", self.recorded(run, action)["steps"][0])

    def test_an_item_that_is_only_tests_may_have_a_test_only_step(self) -> None:
        run, head = self.new_run("step-plan")
        command, path, action = printed_callback(head)
        good = self.fill_done(head)
        tests = ["tests/test_built.py"]
        expectation = {"id": "E1", "state": "absent", "statement": "The test file does not exist yet.", "steps": ["S1"],
                       "paths": tests, "check": "test ! -e " + tests[0]}
        write_block(path, {**good, "paths": tests, "steps": [dict(good["steps"][0], paths=tests)],
                           "expectations": [expectation]})
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["steps"][0]["paths"], tests)

    def test_the_printed_template_steps_are_accepted_as_written_once_placeholders_are_filled(self) -> None:
        run, head = self.new_run("step-plan")
        command, path, action = printed_callback(head)
        template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])

        def fill(value, key=""):
            """Replace each placeholder; every structural field (ids, deps, criteria, suites) stays as printed."""
            if isinstance(value, dict):
                return {k: fill(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [fill(v, key) for v in value]
            if not isinstance(value, str) or not (value == "..." or value.startswith("<")):
                return value
            return {"paths": "built.txt", "command": "true", "evidence_refs": str(self.evidence),
                    "check": "test -f built.txt", "cards": "coding-practices.md#existing-behavior", "like": None}.get(
                key, "What this field records.")

        block = fill(template)
        block["follows"] = []   # the follows placeholder names IDs; this repository's living spec has none to follow
        # An expectation's placeholders name a real fact: the works one the repository's existing file, the absent
        # one the file the steps add, each with a read-only check of it (ids, states and steps stay as printed).
        for row in block["expectations"]:
            target = "a.txt" if row["state"] == "works" else "built.txt"
            row["paths"] = [target]
            row["check"] = ("test -f " if row["state"] == "works" else "test ! -e ") + target
        self.assertEqual([(row["id"], row["deps"], row["criteria"]) for row in block["steps"]],
                         [("S1", [], ["C1"]), ("S2", ["S1"], ["C2"])])
        write_block(path, block)
        self.accepted(command)
        self.assertEqual([(row["check"], row["cards"]) for row in self.recorded(run, action)["steps"]],
                         [("test -f built.txt", ["coding-practices.md#existing-behavior"]), ("test -f built.txt", [])])


class UnverifiedRouteTests(RealCliCase):
    """What the run leaves unverified is listed once, at product-acceptance, and reaches the stage that reports it."""

    FIELDS = ("outcome", "reason", "check", "owner", "due_stage")

    def full_packet(self, head: str) -> str:
        return full_packet_text(head)

    def at(self, stage: str, **accepted: dict) -> tuple[Path, str]:
        """A run positioned at ``stage`` whose earlier stages were accepted with these extra result fields."""
        with mock.patch.dict(RESULTS, accepted):
            return self.new_run(stage)

    def test_product_acceptance_prints_the_assumptions_recorded_open_and_records_the_list_it_accepts(self) -> None:
        run, head = self.at("product-acceptance", plan={"assumptions": [OPEN_ASSUMPTION]})
        packet = self.full_packet(head)
        self.assertIn("Plan assumptions recorded open at planning", packet)
        self.assertIn("A1 (consumer W1): the export is checked by file tests only", packet)
        self.assertIn("check that would settle it: open the export in the reader", packet)
        # The ledger never updates a disposition, so the line states what was recorded, not that it is still true.
        self.assertIn("the ledger does not update dispositions", packet)
        command, path, action = printed_callback(head)
        write_block(path, dict(self.fill_done(head), unverified=[UNVERIFIED_ENTRY, UNVERIFIED_EARLY]))
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["unverified"], [UNVERIFIED_ENTRY, UNVERIFIED_EARLY])

    def test_the_stage_an_entry_is_due_at_prints_it_and_the_handoff_prints_every_entry(self) -> None:
        listed = {"product-acceptance": {"unverified": [UNVERIFIED_ENTRY, UNVERIFIED_EARLY]}}
        _, head = self.at("release-plan", **listed)
        self.assertNotIn(UNVERIFIED_EARLY["outcome"], self.full_packet(head))  # not due yet
        _, head = self.at("release-check", **listed)
        due = self.full_packet(head)
        for field in self.FIELDS:
            self.assertIn(UNVERIFIED_EARLY[field], due)
        self.assertNotIn(UNVERIFIED_ENTRY["outcome"], due)  # that one is due at the handoff, not here
        _, head = self.at("handoff", **listed)
        handoff = self.full_packet(head)
        for entry in (UNVERIFIED_ENTRY, UNVERIFIED_EARLY):
            for field in self.FIELDS:
                self.assertIn(entry[field], handoff)
        # The check is what the owner does and reports to settle the outcome; it is not a person who reports.
        self.assertIn(" | owner: the user | to settle: open the exported file in the reader and report what shows"
                      " | due: handoff", handoff)
        # The handoff duty (list each open item as unverified, with who reports what) is stated once in the packet,
        # by the stage's duties; the lines that print the list state facts, not a second instruction.
        self.assertEqual(" ".join(handoff.split()).count("each with who does what and what they report back"), 1)

    def test_the_handoff_tells_none_listed_from_no_list_recorded_and_scopes_both_to_product_acceptance(self) -> None:
        _, head = self.at("handoff", **{"product-acceptance": {"unverified": []}})
        none_listed = self.full_packet(head)
        self.assertIn("Product-acceptance listed no unverified request outcome", none_listed)
        _, head = self.at("handoff")  # product-acceptance accepted without the field, as a run saved before it was
        not_recorded = self.full_packet(head)
        self.assertIn("No unverified list is recorded for product-acceptance (unmeasured, not zero)", not_recorded)
        self.assertNotIn("listed no unverified", not_recorded)
        for packet in (none_listed, not_recorded):
            # An empty or absent list says nothing about the open items another stage recorded in its own result.
            self.assertIn("another stage recorded", packet)

    def test_the_report_lists_the_outcomes_and_tells_none_listed_from_not_recorded(self) -> None:
        import html
        marked = dict(UNVERIFIED_ENTRY, outcome="the <b>export</b> opens")
        for label, accepted, expected in (
                ("entries", {"unverified": [marked]}, [html.escape(marked[field]) for field in self.FIELDS]),
                ("none listed", {"unverified": []}, ["none listed"]),
                ("not recorded", {}, ["not recorded"])):
            with self.subTest(label):
                run, _ = self.at("handoff", **{"product-acceptance": accepted})
                report = self.cli("report", "--run-dir", str(run)).stdout
                self.assertIn("<h2>Unverified request outcomes</h2>", report)
                for text in expected:
                    self.assertIn(text, report)
                self.assertNotIn("<b>export</b>", report)  # model-written text is escaped

    def test_a_saved_result_whose_entries_are_any_text_loads_while_the_gate_refuses_it(self) -> None:
        # validate() re-canonicalises every accepted result on load, so the stored shape must be loose enough that
        # a later edit of the field set never refuses a saved run; the CLI gate holds the exact shape.
        run, head = self.new_run("product-acceptance")
        state = self.state(run)
        earlier_shape = [{"outcome": "o", "reason": "r"}]
        accepted = nav.apply(state, nav.current_action(state)["id"], {**DONE, "unverified": earlier_shape})
        nav.validate(accepted)
        command, path, _ = printed_callback(head)
        write_block(path, dict(self.fill_done(head), unverified=earlier_shape))
        self.assertIn("needs exactly outcome, reason, check, owner, due_stage", self.refused(command, run))
        # And a packet that prints a loaded entry of an earlier shape must not depend on fields it lacks.
        _, handoff = self.at("handoff", **{"product-acceptance": {"unverified": earlier_shape}})
        self.assertIn("- o | reason: r | owner: ", self.full_packet(handoff))

    def test_text_that_only_contains_angle_brackets_is_not_a_placeholder(self) -> None:
        run, head = self.new_run("product-acceptance")
        command, path, action = printed_callback(head)
        entry = dict(UNVERIFIED_ENTRY, outcome="the <canvas> element draws the board", reason="the <canvas> is not "
                     "reachable from this host")
        write_block(path, dict(self.fill_done(head), unverified=[entry]))
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["unverified"], [entry])

    def test_unverified_is_refused_off_its_stage_and_on_a_result_that_is_not_done(self) -> None:
        state = nav.new_state(str(self.repo), "Off-stage fixture.")
        with self.assertRaisesRegex(nav.NavigatorError, "allowed only on a done product-acceptance result"):
            nav.apply(state, nav.current_action(state)["id"], {**DONE, "unverified": []})
        run, _ = self.new_run("product-acceptance")
        state = self.state(run)
        blocked = {"outcome": "blocked", "blocked_by": "external", "summary": "A service is down.", "unverified": []}
        with self.assertRaisesRegex(nav.NavigatorError, "a blocked result does not carry unverified"):
            nav.apply(state, nav.current_action(state)["id"], blocked)


class OutcomeShapeTests(RealCliCase):
    """The head prints the exact fields of every outcome the stage allows, and each printed shape is accepted."""

    @staticmethod
    def reference_text() -> str:
        return reference.render(nav.new_state("/simulation-only/repo", "Synthetic."), Path("/simulation-only/run"))

    # test-red is folded into test, which has no repeat outcome (its Until Loop repeats the work).
    STAGES = {"intake": ("repeat", "blocked"), "test": ("blocked", "revise"),
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
                # The packet says "outcome" and "summary" are top-level; the no-wrap rule and the awaiting shapes are
                # reference.md's (re-cut round 2), which the packet points at as reference#blocked.
                self.assertIn('"outcome" and "summary" top-level', " ".join(head.split()))
                self.assertIn("reference#blocked", head)
                self.assertIn("not wrap it in action or result keys", " ".join(self.reference_text().split()))
                self.assertIn('"kind": "present"', self.reference_text())

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
                # The awaiting shapes are no longer printed in the packet (reference#blocked): take them from the source.
                self.assertIn("reference#blocked", line)
                forms = [first_object(text) for text in re.findall(r'\{"kind": [^}]*\}', nav.AWAITING_SHAPE)]
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

    def test_the_opening_shiploop_writes_names_the_four_opening_headings(self) -> None:
        run, head = self.new_run("spec")
        command, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        handoff = self.handoff_of(self.accepted(command))
        opening, _receipt = self.started_child(run)
        for name in nav.OPENING_SECTIONS:
            self.assertIn(f"## {name}\n", opening.read_text(encoding="utf-8"))  # the opening ShipLoop froze into start.json
            self.assertNotIn(f"## {name}\n", handoff)  # the handoff no longer prints an opening template to fill


def full_packet_text(head: str) -> str:
    """The whole packet: what ``emit`` printed, or the file a head's "Full packet:" line points at (over PRINT_LIMIT)."""
    line = next((row for row in head.splitlines() if row.startswith("Full packet: ")), None)
    if line is None:
        return head
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
        # test-green and static-checks are folded into test and verify (8-stage loop, 2026-10-10).
        for stage, following in (("test", ("document", "verify")), ("verify", ("carry-forward",))):
            with self.subTest(stage=stage):
                run, head = self.new_run(stage, entered=True)
                command, path, action = printed_callback(head)
                block = {**self.done_fields(), **({"assumptions": []} if stage == "verify" else {})}
                write_block(path, block, loop=False)
                reply = self.refused(command, run)
                self.assertIn(f"the {stage} loop has not run: no terminal packet exists at", reply)
                # The packet no longer prints a start command (re-cut round 2): it names the card section that holds it,
                # and the refusal reply carries the one command.
                self.assertIn('section "Start from a parent-written contract"', full_packet_text(head))
                self.assertIn("Start it with: ", reply)
                receipt = self.follow_start(reply)
                write_block(path, {**block, "evidence_refs": [*block["evidence_refs"], str(receipt)]}, loop=False)
                self.accepted(command)
                self.assertIn(nav.current_stage(self.state(run)), following)

    def test_revise_before_the_loop_stopped_is_told_to_run_it_until_it_stops_blocked(self) -> None:
        run, head = self.new_run("test", entered=True)
        command, path, _ = printed_callback(head)
        block = {**self.done_fields(), "outcome": "revise", "summary": "The step plan cannot be met as written."}
        write_block(path, block, loop=False)
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
        write_block(path, {**block, "evidence_refs": [*block["evidence_refs"], receipt]}, loop=False)
        self.accepted(command)
        self.assertEqual(nav.current_stage(self.state(run)), "step-plan")

    def test_citing_a_receipt_nobody_wrote_is_still_refused(self) -> None:
        for stage in ("test", "verify"):
            with self.subTest(stage=stage):
                run, head = self.new_run(stage, entered=True)
                command, path, _ = printed_callback(head)
                write_block(path, self.done_fields(), loop=False)
                named = Path(re.search(r"no terminal packet exists at (\S+)\.", self.refused(command, run)).group(1))
                write_block(path, {**self.done_fields(), "evidence_refs": [str(self.evidence), str(named)]},
                            loop=False)
                self.assertFalse(named.exists())
                reply = self.refused(command, run)
                self.assertTrue("evidence_refs cite files that do not exist" in reply
                                or f"the {stage} loop has not run" in reply, reply)


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
        write_block(path, {**self.done_fields(), "assumptions": []})
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
        self.assertIn(f"Refused runs for this action: 1 of {test_loop.MAX_REFUSED_RUNS}; replan does not wait for them.", reply)

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
        self.assertIn(f"Refused runs for this action: 2 of {test_loop.MAX_REFUSED_RUNS}", again)
        # Recording it as a check here is not an exit: system-test reruns what was recorded, so the gate holds.
        write_block(path, {**self.done_fields(), "assumptions": [],
                           "system_commands": [{"command": PIPELINE, "suite": "check"}]})
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
            {"command": "echo hi | grep -q hi", "suite": "focused", "criteria": ["C1"]},  # passes, prints no count
            RESULTS["step-plan"]["test_commands"][1]]}}
        with mock.patch.dict(RESULTS, recorded):
            run, head = self.new_run("test")  # test-red is folded into test
        callback, path, _ = printed_callback(head)
        write_block(path, self.done_fields())
        reply = self.refused(callback, run)
        self.assertIn("Give the command ids and a runner flag that prints test names", reply)
        self.assertIn("for a command that is not a test runner, record it as suite `check`", reply)
        self.assertNotIn("Report outcome replan now", reply)


class InnerGateRouteTests(RealCliCase):
    """The 8-stage inner gates (2026-10-10): each refusal names its fault, and the exit it names is accepted.

    Every case submits through the real CLI with the stage's Until Loop run first (write_block), so the refusal is the
    gate's own, not the loop check's.
    """

    def submit_until_gate(self, command: str, run: Path) -> str:
        """The refusal for ``command``, after writing any knowledge files a close names first (another gate)."""
        reply = self.refused(command, run)
        if "keeps this run's planning knowledge in the repository" in reply:
            for named in re.findall(r"^- (/\S+)$", reply, re.M):
                Path(named).parent.mkdir(parents=True, exist_ok=True)
                Path(named).write_text("What this file records.\n", encoding="utf-8")
            reply = self.refused(command, run)
        return reply

    def step_plan(self) -> tuple[Path, str, Path, str, dict]:
        run, head = self.new_run("step-plan")
        command, path, action = printed_callback(head)
        return run, command, path, action, self.fill_done(head)

    def test_a_step_plan_with_test_commands_and_no_check_row_takes_check_na(self) -> None:
        run, command, path, action, good = self.step_plan()
        no_check = {**good, "test_commands": [row for row in good["test_commands"] if row["suite"] != "check"]}
        write_block(path, no_check)
        reply = self.refused(command, run)
        self.assertIn("test_commands has no check row", reply)
        self.assertIn("give check_na with the reason there is none", reply)
        write_block(path, {**no_check, "check_na": ""})
        self.assertIn("check_na must be nonblank text", self.refused(command, run))
        write_block(path, {**good, "check_na": "No lint for a text file."})
        self.assertIn("test_commands has a check row, so drop check_na", self.refused(command, run))
        write_block(path, {**no_check, "check_na": "No lint, type or build command applies to a text file."})
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["check_na"],
                         "No lint, type or build command applies to a text file.")

    def test_an_expectation_without_a_check_is_refused_and_the_one_with_its_check_is_accepted(self) -> None:
        run, command, path, action, good = self.step_plan()
        unchecked = [{key: value for key, value in good["expectations"][0].items() if key != "check"}]
        write_block(path, {**good, "expectations": unchecked})
        self.assertIn("expectations[0] has id, state, statement, steps and check", self.refused(command, run))
        write_block(path, {**good, "expectations": [{**unchecked[0], "check": "test ! -e built.txt"}]})
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["expectations"][0]["check"], "test ! -e built.txt")

    def test_an_existing_step_path_without_a_works_expectation_is_refused_until_one_lists_it(self) -> None:
        run, command, path, action, good = self.step_plan()
        existing = "a.txt"  # every fixture repository commits it
        self.assertTrue((self.repo_of(run) / existing).is_file())
        touching = {**good, "paths": ["built.txt", existing],
                    "steps": [dict(good["steps"][0], paths=["built.txt", existing])]}
        write_block(path, touching)
        reply = self.refused(command, run)
        self.assertIn("these step paths have no expectation listing them in paths: a.txt (step S1, needs works or "
                      "broken)", reply)
        works = {"id": "E2", "state": "works", "statement": "a.txt holds its line.", "steps": ["S1"],
                 "paths": [existing], "check": "grep -q x a.txt"}
        write_block(path, {**touching, "expectations": [*good["expectations"], works]})
        self.accepted(command)
        self.assertEqual([row["id"] for row in self.recorded(run, action)["expectations"]], ["E1", "E2"])

    def test_a_new_step_path_without_an_absent_expectation_is_refused_until_one_lists_it(self) -> None:
        run, command, path, action, good = self.step_plan()
        write_block(path, {**good, "expectations": []})
        reply = self.refused(command, run)
        self.assertIn("built.txt (step S1, needs absent)", reply)
        # A works expectation does not cover a path that is not there: the gate names the state a new path needs.
        wrong = dict(good["expectations"][0], state="works", check="test -f built.txt")
        write_block(path, {**good, "expectations": [wrong]})
        self.assertIn("A new path needs an absent expectation", self.refused(command, run))
        write_block(path, good)
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["expectations"][0]["state"], "absent")

    def test_a_skill_locator_that_does_not_exist_is_refused_and_dropping_the_locator_is_accepted(self) -> None:
        run, command, path, action, good = self.step_plan()
        missing = str(self.base / "no-such-skill" / "SKILL.md")
        skill = {"name": "review", "why": "Review the new file's wording.", "locator": missing}
        write_block(path, {**good, "steps": [dict(good["steps"][0], skills=[skill])]})
        reply = self.refused(command, run)
        self.assertIn("step S1 skill review: locator " + missing + " does not exist", reply)
        self.assertIn("drop the locator", reply)
        kept = {key: value for key, value in skill.items() if key != "locator"}
        write_block(path, {**good, "steps": [dict(good["steps"][0], skills=[kept])]})
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["steps"][0]["skills"], [kept])

    def test_test_spec_cases_and_focused_ids_must_match_both_ways(self) -> None:
        """The consumer contract's test_cases gate (3.3; it replaced the feature test-spec.md check): each fault's line 1
        names the fix, the result file and the same command, and the corrected result is accepted through it."""
        run, head = self.new_run("test-spec")
        command, path, action = printed_callback(head)
        good = self.fill_done(head)
        case = TEST_CASES[0]
        faults = [({**good, "test_cases": TEST_CASES + [dict(case, id="TC-2")]}, "Fix the case IDs in ",
                   "Not listed by a focused command of W1: TC-2."),
                  ({key: value for key, value in good.items() if key != "test_cases"}, "Add test_cases to ",
                   "Focused IDs: TC-1."),
                  ({**good, "test_cases": [dict(case, criterion="C9")]}, "Fix the case criteria in ",
                   "TC-1 names C9; the criteria are C1."),
                  ({**good, "test_cases": [dict(case, requirement="R-12")]}, "Fix case requirements in ",
                   "TC-1 names R-12.")]
        for block, fix, detail in faults:
            with self.subTest(fix):
                write_block(path, block)
                reply = self.submit_until_gate(command, run)
                self.assertIn("ShipLoop navigator: " + fix + str(path) + ", then run the same complete command again.\n",
                              reply)
                self.assertIn(detail, reply)
        write_block(path, good)
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["test_cases"], TEST_CASES)

    def test_carry_forward_needs_a_skill_decision_and_an_update_names_an_existing_skill(self) -> None:
        run, head = self.new_run("carry-forward")
        command, path, action = printed_callback(head)
        good = self.fill_done(head)
        write_block(path, {key: value for key, value in good.items() if key != "skill"})
        reply = self.submit_until_gate(command, run)
        self.assertIn('carry-forward needs skill: {"decision": "none" | "reuse" | "update" | "create"', reply)
        missing = str(self.repo_of(run) / ".claude" / "skills" / "hello" / "SKILL.md")
        write_block(path, {**good, "skill": {"decision": "update", "reason": "The step repeated.", "path": missing,
                                             "evidence": ["W1 S1"]}})
        self.assertIn("the skill decision names a SKILL.md that does not exist: " + missing,
                      self.submit_until_gate(command, run))
        write_block(path, {**good, "skill": SKILL_NONE})
        self.accepted(command)
        self.assertEqual(self.recorded(run, action)["skill"], SKILL_NONE)


# Stages whose accepted result starts an Improve child (the planning reviews and the last item's carry-forward),
# declared here and not read from the navigator.
CHECKPOINTS = ("spec", "test-strategy", "plan", "step-plan", "test-spec", "implement", "carry-forward",
               "system-test-author", "release-plan")
# Stages ShipLoop records by script when its own checks leave nothing to do (every expectation matches; the item's diff
# touches no code or test path); a walk sees their history row, not a packet.
SCRIPT_RECORDED = ("validate-existing", "document")
# The stages whose minimal done result is refused for work the model has not done yet, and the exits the
# refusals name: the knowledge files the run keeps in the repository, and the loop that was never started.
EXPECTED_ROUTES = {
    # Only prepare asks for files: since consumer contract 4c the later closes need environment.md alone, which the walk's
    # earlier stages already wrote (no feature file, no outcome sections).
    "prepare": ["knowledge files"],
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
            if stage in SCRIPT_RECORDED and not header.startswith(f"ShipLoop navigator | {stage} | "):
                self.assertIn(stage, [row["stage"] for row in self.state(run)["history"]])
                continue
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
                # The accepted result starts an Improve child: ShipLoop binds its recorded card at the transition, so
                # the first packet is the two instructions with no bind command (re-cut 2026-10-11).
                self.assertIn("/improve " + nav.IMPROVE_ARGUMENT_PREFIX, result.stdout)
                self.assertNotIn("improve-bind", result.stdout)
                state = self.state(run)
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
                nav.save(run, state)
                result = self.cli("next", "--run-dir", str(run))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            head = result.stdout
        self.assertEqual(taken, EXPECTED_ROUTES)
        self.assertEqual(self.state(run)["status"], "done")
        self.assertIn("It's all complete.", head)

    def test_each_inner_template_prints_every_field_its_gate_requires(self) -> None:
        """A model fills the printed template; a field the gate refuses without must be in it (S-3).

        Fails on the 2026-10-10 engine: the step-plan template prints no expectations and no step skills, and the
        carry-forward template prints no skill decision, while each gate refuses a done result without them.
        """
        required = {"step-plan": ("expectations",), "carry-forward": ("skill",)}
        for stage, fields in required.items():
            with self.subTest(stage=stage):
                _run, head = self.new_run(stage)
                template = store.loads(head.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])
                for field in fields:
                    self.assertIn(field, template)
                if stage == "step-plan":
                    for step in template["steps"]:
                        self.assertIn("skills", step)

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
        loops = ()  # write_block stops an INNER stage's loop blocked before a revise, so every revise is submitted
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
        self.assertGreaterEqual(len(pairs), 55)  # 24 stages since the 8-stage inner loop (was 70 over 34)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            problems = [p for p in pool.map(lambda pair: self.one_outcome(*pair), pairs) if p]
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
