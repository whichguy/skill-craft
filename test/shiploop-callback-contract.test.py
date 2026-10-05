#!/usr/bin/env python3
"""A refusal names the exact way out, and the way out it names is accepted by the same gate.

Every test drives the real ShipLoop CLI.  A run is started with ``init`` and, where a test needs a later stage,
positioned there with the pure navigator and saved, so the CLI under test reads an ordinary run directory.
Nothing here asserts that a sentence exists on its own: each test submits what the packet or the refusal
printed, follows the correction the refusal names (derived from the refusal's own text, not from the test's
knowledge of it), submits the same command again and requires the gate to accept it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
CARD = ROOT / "skills" / "improve" / "SKILL.md"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402

DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Nothing to change.", "handoff": "Nothing is open."}
BLOCKED_REPORT = {"classification": "unresolved", "exit_assessment": "unknown", "continuation_assessment": "blocked",
                  "evidence": "The item's goal cannot be reached as planned.", "handoff": "See the evidence."}
# The public graph, declared here and not read from the navigator, so a changed graph updates this test deliberately.
EXPECTED_STAGES = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
    "select-work", "step-plan", "test-spec", "baseline", "test-author", "test-red", "implement", "test-green",
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
        self._temporary = tempfile.TemporaryDirectory(prefix="shiploop-callback-contract-")
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name).resolve()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1")
        self.evidence = self.base / "evidence.txt"
        self.evidence.write_text("a note this stage wrote\n")
        self.counter = 0
        self.repo = self.make_repo()

    def make_repo(self) -> Path:
        """A one-commit repository of its own; every run gets one, so a stage's files never leak into another."""
        repo = self.base / f"repo{self.counter}"
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
                (self.repo / "built.txt").write_text("hello\n")  # the work implement's step did
            write_block(path, self.fill_done(head))
            return run, self.accepted(command)
        self.counter += 1
        self.repo = self.make_repo()
        run = self.base / f"run{self.counter}"
        started = self.cli("init", "--repo", str(self.repo), "--run-dir", str(run), "--prompt=add hello",
                           "--improve-skill", str(CARD), *(f"--{k}={v}" for k, v in init.items()))
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        if stage == "intake":
            return run, started.stdout
        state = store.read_record(run / "state.md")
        while nav.current_stage(state) != stage:
            action, here = nav.current_action(state)["id"], nav.current_stage(state)
            if here == "implement":
                (self.repo / "built.txt").write_text("hello\n")  # the work the stage's step did
            state = nav.apply(state, action, {**DONE, **RESULTS.get(here, {})})
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        nav.save(run, state)
        head = self.cli("next", "--run-dir", str(run))
        self.assertEqual(head.returncode, 0, head.stdout + head.stderr)
        return run, head.stdout

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


if __name__ == "__main__":
    unittest.main()
