#!/usr/bin/env python3
"""Hermetic tests for ``shiploop_loops``: the Until Loop every inner stage runs (owner decision 2026-10-10).

ShipLoop writes each inner action's loop contract on entry, prints the loop block in the packet (RUN the Until Loop
with the literal start command first, then the argument between two marker lines, then the result) and, before it
accepts the result, checks the runtime's receipt against the contract rebuilt from state.
The contract tests feed the contract to the real bundled runtime (its own schema validator and its ``start``); the
terminal tests run the real runtime to the state they need; the navigator tests submit through the real gate.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_inner_fixture as fx  # noqa: E402
import shiploop_loop_support as support  # noqa: E402
from shiploop_packet_view import callback_argv, callback_result_path  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic iteration; no semantic claim.", "handoff": "Synthetic fixture; nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", exit_assessment="unsatisfied")
BLOCKED = dict(MATERIAL, continuation_assessment="blocked")
CANCELLED = dict(MATERIAL, continuation_assessment="cancelled")
# What a blocked result waits on (run-insights plan N5): the Until Loop runtime is an outside service, so these tests
# block on a service wait, whose read-only check says when it is back.
SERVICE_WAIT = {"kind": "service", "service": "the Until Loop runtime", "check": "true",
                "no_default": "The loop cannot run without its runtime, and nothing else in this stage can proceed."}


# The slash command for the loop, as a regular expression: "/until-loop" that is not the start of a path segment
# (the runtime the start command runs lives in `.../runtime/until-loop/scripts/`).
SLASH_FORM = r"/until-loop(?![\w/.-])"


def _runtime_module():
    """The bundled runtime script itself, for its own contract validator."""
    cli = Path(loops.runtime({})["runtime_cli"])
    spec = importlib.util.spec_from_file_location("until_loop_runtime_under_test", cli)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Synthetic(unittest.TestCase):
    """A run directory and a state built by hand: one item W1 whose accepted step plan has two steps."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-loops-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.repo, self.root = base / "repo", base / "run"
        self.repo.mkdir()
        (self.root / "loops").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.cli = loops.runtime(self.state_for("verify"))["runtime_cli"]

    def state_for(self, stage: str, title: str = "Add parser") -> dict:
        return {
            "repo": str(self.repo), "prompt": "Build a parser for the thing", "run_id": "run-abc123",
            "stage": "inner-loop", "work_index": 0, "improve_skill": "", "delegation": "inline",
            "work_items": [{"id": "W1", "title": title}],
            "inner_loops": {"W1": {"stage": stage, "action": {"id": "A-" + stage}}},
            "history": [{"stage": "step-plan", "workitem": "W1", "action": "A-sp", "outcome": "done"}],
            "accepted": {"A-sp": {"outcome": "done", "steps": [
                {"id": "S1", "task": "t", "paths": ["src/a.py", "src/b.py"], "criteria": ["C1"]},
                {"id": "S2", "task": "t2", "paths": ["src/c.py"], "criteria": ["C1"]}]}},
        }

    def write(self, state: dict) -> dict:
        writes = loops.contract_writes(self.root, state)
        for relative, text in writes.items():
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.root / relative).write_text(text)
        return writes

    def runtime(self, args: list, stdin: str) -> dict:
        done = subprocess.run([sys.executable, self.cli, *args], input=stdin, text=True, capture_output=True,
                              timeout=60)
        return json.loads(done.stdout)

    def start(self, stage: str) -> tuple[dict, Path]:
        """Write the stage's contract and start it under the real runtime; returns (state, receipt)."""
        state = self.state_for(stage)
        writes = self.write(state)
        receipt = loops.receipt_path(self.root, "A-" + stage)
        packet = self.runtime(["start", "--receipt", str(receipt)], writes[loops.contract_path("A-" + stage)])
        self.assertEqual(packet["status"], "active", packet)
        return state, receipt

    def report(self, receipt: Path, *reports: dict) -> dict:
        packet = json.loads(receipt.read_text())
        for report in reports:
            packet = self.runtime(packet["done_argv"][2:], json.dumps(report))
        return packet

    def refused(self, state: dict, result: dict, message: str) -> None:
        with self.assertRaisesRegex(loops.LoopError, message):
            loops.check_terminal(self.root, state, result)


class ContractTests(Synthetic):
    def test_growing_contracts_and_reports_round_trip_without_truncation(self):
        """Exercise content growth, not a byte budget that changes with checkout and temporary paths."""
        for case_count in (1, 1000):
            with self.subTest(case_count=case_count):
                state = self.state_for("test")
                command = "python3 -m unittest " + " ".join(f"tests.test_case_{n}" for n in range(case_count))
                state["accepted"]["A-sp"]["test_commands"] = [{"command": command, "suite": "focused"}]
                text = self.write(state)[loops.contract_path("A-test")]
                contract = json.loads(text)
                self.assertIn(command, contract["work"])
                # Separate receipts keep each sample a fresh runtime invocation. Commands are instructions only.
                receipt = self.root / "loops" / f"content-{case_count}.json"
                packet = self.runtime(["start", "--receipt", str(receipt)], text)
                self.assertEqual(packet["status"], "active", packet)
                self.assertEqual(packet["work"], contract["work"])
                self.assertEqual(packet["context"], contract["context"])
                report = dict(TRIVIAL,
                              evidence="\n".join(f"Case {n}: synthetic evidence — café." for n in range(case_count)),
                              handoff="\n".join(f"Case {n}: retain this finding — 日本語." for n in range(case_count)))
                terminal = self.report(receipt, report)
                self.assertEqual(terminal["status"], "complete", terminal)
                self.assertEqual(terminal["last_report"], report)
                self.assertEqual(json.loads(receipt.read_text()), terminal)

    def test_every_inner_stage_contract_is_in_the_runtime_schema_and_the_runtime_starts_from_it(self):
        validate = _runtime_module()._validate_contract
        self.assertEqual(set(loops.STAGES), set(stage_spec.INNER))
        for stage in stage_spec.INNER:
            with self.subTest(stage=stage):
                state, action = self.state_for(stage), "A-" + stage
                writes = self.write(state)
                value = loops.contract(self.root, state, action)
                # The runtime's own validator returns the contract unchanged: no field added, dropped or normalised.
                # The 0.8.0 runtime normalizes a contract without exit checks to an empty list; nothing else changes.
                self.assertEqual(validate(json.loads(json.dumps(value)), input_contract=True), {**value, "exit_checks": []})
                self.assertEqual(json.loads(writes[loops.contract_path(action)]), value)
                self.assertEqual(loops.contract(self.root, state, action), value, "not deterministic")
                self.assertEqual(value["required_trivial_reviews"], 1 if stage == "verify" else 0)
                # an inline implement step's first condition ends with the criteria assigned to it (fix plan T11)
                scope = loops.implement_scope(state, "W1", action) if stage == "implement" else None
                self.assertEqual(value["exit_condition"], loops.exit_condition(stage, scope))
                self.assertEqual(value["exit_condition"].splitlines(),
                                 [f"{n}. {c}" for n, c in enumerate(loops.worded_stage(stage, scope).done_when, 1)])
                self.assertTrue(value["repeat_condition"].startswith("Repeat while "))
                self.assertIn("there is no iteration limit", value["repeat_condition"])
                self.assertNotIn("Build a parser", json.dumps(value), "the request text leaked into the contract")
                self.assertIn(str(self.root / "state.md"), value["context"]["request"])
                self.assertEqual(stage == "verify", quality.RUBRIC_PATH in writes)
                receipt = loops.receipt_path(self.root, action)
                packet = self.runtime(["start", "--receipt", str(receipt)], writes[loops.contract_path(action)])
                self.assertEqual(packet["status"], "active", packet)
                self.assertEqual((packet["work"], packet["conditions"]["exit"], packet["conditions"]["repeat"],
                                  packet["context"]),
                                 (value["work"], value["exit_condition"], value["repeat_condition"],
                                  value["context"]))
                self.assertEqual(json.loads(receipt.read_text())["status"], "active")

    def test_the_ask_agent_implement_contract_names_every_step_and_the_runtime_starts_from_it(self):
        """One implement action builds both steps of the plan on the ask-agent route: the exit conditions, the work and the
        scope all say so, in the runtime's own schema (U11); a one-step plan and the inline route keep the per-step words."""
        validate = _runtime_module()._validate_contract
        state = dict(self.state_for("implement"), delegation="ask-agent")
        writes = self.write(state)
        value = loops.contract(self.root, state, "A-implement")
        # The runtime normalises the optional list a stage loop does not write (exit_checks): it comes back empty.
        self.assertEqual(validate(json.loads(json.dumps(value)), input_contract=True), {**value, "exit_checks": []})
        lines = value["exit_condition"].splitlines()
        self.assertEqual(len(lines), len(stage_spec.stage("implement").done_when))
        self.assertEqual(lines[0], "1. only the paths of steps S1 to S2 (src/a.py, src/b.py, src/c.py) changed since the "
                                   "first of them began, and no work outside those steps is in them")
        self.assertIn("for the change of every step, S1 to S2, in order. Write no tests", value["work"])
        self.assertIn("src/a.py, src/b.py, src/c.py", value["context"]["scope"])
        receipt = loops.receipt_path(self.root, "A-implement")
        packet = self.runtime(["start", "--receipt", str(receipt)], writes[loops.contract_path("A-implement")])
        self.assertEqual((packet["status"], packet["conditions"]["exit"]), ("active", value["exit_condition"]))
        one = dict(state)
        one["accepted"] = {"A-sp": dict(state["accepted"]["A-sp"], steps=state["accepted"]["A-sp"]["steps"][:1])}
        self.assertEqual(loops.contract(self.root, one, "A-implement")["exit_condition"].splitlines()[0],
                         "1. " + stage_spec.stage("implement").done_when[0])

    def test_the_step_contract_binds_its_anchors_and_rebuilds_the_same_after_the_living_files_change(self):
        """T12: the inline step's Work names its criteria, the R-<n> they name and the item's AD-<n>; the contract rebuilt
        at complete equals the one written at entry, though the step edited HOME/spec.md in between (the anchors are
        read from state, never from the living files)."""
        state = self.state_for("implement")
        state["accepted"]["A-sp"].update(criteria=[{"id": "C1", "text": "The header is read as R-2 states."}],
                                         follows=["R-1", "AD-3"])
        written = json.loads(self.write(state)[loops.contract_path("A-implement")])
        home = self.repo / "docs" / "shiploop"
        home.mkdir(parents=True)
        (home / "spec.md").write_text("# Spec\n\n- R-2: the header, edited by the step.\n- R-9: new.\n")
        self.assertEqual(loops.contract(self.root, state, "A-implement"), written)
        for token in ("step S1", "C1", "R-2", "AD-3",
                      "until each requirement assigned to this step is satisfied and none of the others is broken"):
            self.assertIn(token, written["work"])
        self.assertNotRegex(written["work"], r"\bR-1\b")   # a criterion names R-2, so the item's R-1 is not this step's

    def test_the_ask_agent_work_sentence_is_unchanged_and_names_no_step_proof(self):
        """T31: the whole-plan action keeps today's Work word for word (the chain runs the steps; no single-step gate)."""
        state = dict(self.state_for("implement"), delegation="ask-agent")
        value = loops.contract(self.root, state, "A-implement")
        self.assertEqual(value["work"], "Do duty items 1-7 of " + str(self.root) + "/packets/A-implement.md for the change "
                                        "of every step, S1 to S2, in order. Write no tests and start no later step.")
        # its exits keep the steps' wording, and no step-proof gate applies to it (shiploop-test-loop, T31's gate test)
        self.assertTrue(value["exit_condition"].startswith("1. only the paths of steps S1 to S2"))
        self.assertEqual(value["repeat_condition"], loops.REPEAT["implement"])

    def test_the_repeat_texts_route_a_person_or_a_service_to_blocked_and_an_unachievable_plan_to_send_back(self):
        """Run-insights plan N5 (E3): when no further iteration helps, blocked is only for a person's or a service's action
        (access, authority, a decision) and send-back is for a plan proven unachievable as planned; the retired outcome
        names appear in no repeat text."""
        for name, text in (("REPEAT_STEP", loops.REPEAT_STEP), ("REPEAT[implement]", loops.REPEAT["implement"])):
            with self.subTest(text=name):
                flat = " ".join(text.split())
                self.assertIn("blocked when a person or an outside service must act (access, authority, a decision)", flat)
                self.assertIn("send-back", flat)
                self.assertIn("unachievable as planned", flat)
        for name, text in {**loops.REPEAT, "REPEAT_STEP": loops.REPEAT_STEP}.items():
            with self.subTest(retired_in=name):
                for retired in ("revise", "replan"):
                    self.assertNotIn(retired, text)

    def test_verify_writes_the_code_craft_rubric_its_contract_names(self):
        writes = self.write(self.state_for("verify"))
        self.assertEqual(writes[quality.RUBRIC_PATH], prompts.CODE_CRAFT)
        value = loops.contract(self.root, self.state_for("verify"), "A-verify")
        purposes = {row["purpose"]: row["locator"] for row in value["context"]["resources"]}
        self.assertEqual(purposes["Code craft rubric the review applies"], str(self.root / quality.RUBRIC_PATH))

    def test_implement_contract_names_the_current_step_and_the_items_paths_with_no_step_fence(self):
        """The inline step's scope is its assigned criteria within the item's declared paths (implement-step fix plan
        D3: no step path fence), and its Work names the step."""
        state = self.state_for("implement")
        state["accepted"]["A-sp"]["paths"] = ["src/a.py", "src/b.py", "src/c.py"]
        value = loops.contract(self.root, state, "A-implement")
        self.assertIn("step S1", value["work"])
        self.assertIn("Step S1 of work item W1: its assigned criteria, within the item's declared paths (src/a.py, "
                      "src/b.py, src/c.py)", value["context"]["scope"])
        self.assertNotIn("only its paths", value["context"]["scope"])
        state = self.state_for("implement")
        state["history"].append({"stage": "implement", "workitem": "W1", "action": "A-i1", "outcome": "done"})
        self.assertIn("step S2", loops.contract(self.root, state, "A-implement")["work"])
        state["history"].append({"stage": "implement", "workitem": "W1", "action": "A-i2", "outcome": "done"})
        with self.assertRaisesRegex(loops.LoopError, "no implement step left"):
            loops.contract(self.root, state, "A-implement")

    def test_no_contract_resource_or_scope_names_a_feature_folder_test_strategy_or_test_spec(self):
        """Consumer contract 4b: the engine's part of every inner contract (scope and resources) names only the living files.

        The work texts are the inner-loop session's packet text (``WORK``); they move with its renderer swap."""
        for stage in stage_spec.INNER:
            with self.subTest(stage=stage):
                value = loops.contract(self.root, self.state_for(stage), "A-" + stage)
                engine = json.dumps({"scope": value["context"]["scope"], "resources": value["context"]["resources"]})
                for removed in ("/features/", "test-strategy", "/test-spec.md", "test spec", "feature plan"):
                    self.assertNotIn(removed, engine)

    def test_resources_are_packet_pass_log_three_living_files_and_step_plan(self):
        home = self.repo / "docs" / "shiploop"
        for stage in stage_spec.INNER:
            with self.subTest(stage=stage):
                resources = loops.contract(self.root, self.state_for(stage), "A-" + stage)["context"]["resources"]
                self.assertEqual([row["locator"] for row in resources[:6]], [
                    str(self.root / "packets" / ("A-" + stage + ".md")), str(self.root / "notes" / ("A-" + stage + ".md")),
                    str(home / "spec.md"), str(home / "architecture.md"), str(home / "environment.md"),
                    str(self.root / "results" / "A-sp.md")])
                self.assertEqual(len(resources), 9 if stage == "verify" else 6)

    def test_a_contract_is_only_for_the_current_inner_action(self):
        with self.assertRaisesRegex(loops.LoopError, "not the current inner action"):
            loops.contract(self.root, self.state_for("test"), "A-other")
        self.assertEqual(loops.contract_writes(self.root, {"stage": "spec"}), {})


class InvokeLinesTests(Synthetic):
    """The block says what to run, with what argument, and what the result is (owner, 2026-10-16; one start route on
    every host, plan 6.3): a cleared model acts on it without opening any card or naming any tool."""

    def block(self, state: dict, stage: str | None = None) -> support.LoopBlock:
        return support.LoopBlock("\n".join(loops.invoke_lines(self.root, state)))

    def test_the_block_runs_the_loop_first_and_shows_the_argument_between_two_markers(self):
        for stage in stage_spec.INNER:
            state = self.state_for(stage)
            if stage == "implement":
                state["inner_loops"]["W1"]["action"]["id"] = "A-implement"
            with self.subTest(stage=stage):
                self.write(state)
                lines = loops.invoke_lines(self.root, state)
                value = loops.contract(self.root, state, "A-" + stage)
                contract_file = self.root / loops.contract_path("A-" + stage)
                receipt = loops.receipt_path(self.root, "A-" + stage)
                command = loops.start_command(loops.runtime(state), receipt, contract_file)
                # (a) The RUN line, the literal start command and the follow line come first, in that order.
                self.assertEqual(lines[:5], ["", loops.BLOCK_HEADING, loops.INVOKE_LINE, command, loops.FOLLOW_LINE])
                self.assertTrue(loops.INVOKE_LINE.startswith("RUN the Until Loop now, once, before any work"))
                # (b) Both marker lines, once, after the command, and between them exactly the five fields.
                self.assertEqual((lines.count(loops.ARGUMENT_BEGIN), lines.count(loops.ARGUMENT_END)), (1, 1))
                begin, end = lines.index(loops.ARGUMENT_BEGIN), lines.index(loops.ARGUMENT_END)
                self.assertEqual(begin, 5, "the argument follows the follow line directly")
                self.assertLess(begin, end)
                self.assertEqual(lines[begin + 1:end], [
                    *("Work: " + value["work"]).splitlines(), "Exit when ALL of these hold:",
                    *value["exit_condition"].splitlines(), value["repeat_condition"],
                    "Contract: " + str(contract_file), "Receipt: " + str(receipt)])
                labelled = [line for line in lines[begin + 1:end] if line.startswith(support.ARGUMENT_FIELDS)]
                self.assertEqual([next(label for label in support.ARGUMENT_FIELDS if line.startswith(label))
                                  for line in labelled], list(support.ARGUMENT_FIELDS))
                # (c) The result and the exit-evidence rule close the block, each once.
                self.assertEqual(lines[end + 1:], [loops.RESULT_LINE, " ".join(loops.LOOP_RULE.split())])
                self.assertNotIn("Argument:", lines)
                self.assertFalse([line for line in lines if line.startswith("    ")], "an indented argument line")
                self.assertFalse([line for line in lines if "ADAPTER.md" in line or line.startswith("How to invoke")])

    def test_the_block_names_one_start_route_and_no_tool(self):
        """The command is the only route: no line names the Skill tool, a skill of that name or the slash form, and
        the active-receipt clause and the exit-evidence sentence each appear once."""
        self.assertFalse(hasattr(loops, "HOST_LINE"), "the per-host line was removed")
        for stage in stage_spec.INNER:
            with self.subTest(stage=stage):
                state = self.state_for(stage)
                self.write(state)
                text = "\n".join(loops.invoke_lines(self.root, state))
                for forbidden in ("Skill tool", "skill until-loop", "Claude Code", "Any other host"):
                    self.assertNotIn(forbidden, text)
                # The slash form, not the runtime directory the start command runs (`.../until-loop/scripts/...`).
                self.assertIsNone(re.search(SLASH_FORM, text))
                self.assertEqual(text.count("a second start resets the loop"), 1)
                self.assertEqual(text.count("Call an exit condition satisfied only when a command or file shows it "
                                            "after your last edit."), 1)
                self.assertEqual(text.count(" start --receipt "), 1, "one start command")
        for needed in ("Receipt below already exists and is active", "run its next_argv instead"):
            self.assertIn(needed, loops.INVOKE_LINE)

    def test_the_packet_prints_the_literal_start_command_and_it_starts_the_loop(self):
        """The printed command is the one that starts the loop, on this action's own contract and receipt."""
        for stage in ("step-plan", "test", "document", "verify"):
            with self.subTest(stage=stage):
                state = self.state_for(stage)
                self.write(state)
                block = self.block(state)
                action = "A-" + stage
                contract_file, receipt = self.root / loops.contract_path(action), loops.receipt_path(self.root, action)
                expected = loops.start_command(loops.runtime(state), receipt, contract_file)
                self.assertEqual(block.command, expected)
                self.assertEqual(block.lines[1:3], [loops.INVOKE_LINE, expected], "the command is the RUN line's next line")
                words = shlex.split(block.command)
                self.assertEqual(words[:2][0], "python3")
                self.assertTrue(words[1].endswith("until-loop/scripts/until_loop_ephemeral.py"))
                self.assertEqual(words[2:], ["start", "--receipt", str(receipt), "<", str(contract_file)])
                # The command and the argument name the same two files.
                self.assertEqual(block.field("Contract: "), str(contract_file))
                self.assertEqual(block.field("Receipt: "), str(receipt))
                self.assertFalse(receipt.exists())
                with tempfile.TemporaryDirectory(prefix="shiploop-cwd-") as elsewhere:
                    started = block.run(Path(elsewhere))
                self.assertEqual(started["status"], "active", started)
                self.assertEqual(started["receipt"], str(receipt))
                self.assertEqual(json.loads(receipt.read_text()), started)
                self.assertEqual(started["work"], json.loads(contract_file.read_text())["work"])
                self.assertEqual([started["done_argv"][2], started["next_argv"][2]], ["done", "next"])

    def test_the_result_line_names_the_receipt_the_next_command_and_the_runtimes_five_report_fields(self):
        """What the finished loop leaves, what to do with it, and the report the runtime requires (SP-4)."""
        state = self.state_for("document")
        self.write(state)
        block = self.block(state)
        self.assertEqual(block.result, loops.RESULT_LINE)
        for needed in ("the Receipt says status complete", "stopped: report it", "evidence_refs",
                       "the Callback command above", "run the start command above again",
                       "an active receipt: its next_argv instead", "then run the Callback again"):
            self.assertIn(needed, block.result)
        # The Receipt it points at is the argument's, with the path the command writes.
        self.assertEqual(block.field("Receipt: "), str(loops.receipt_path(self.root, "A-document")))
        # The closing rule is the exit-evidence sentence and nothing else; the receipt and contract rule is said once,
        # where the argument is introduced.
        self.assertEqual(block.lines[-1], " ".join(loops.LOOP_RULE.split()))
        self.assertEqual(block.lines[-1], "Call an exit condition satisfied only when a command or file shows it after "
                                          "your last edit.")
        self.assertIn("do not edit that file or the receipt", loops.FOLLOW_LINE)
        self.assertIn("Never write or edit the receipt", loops.RECEIPT_RULE)

    def test_the_printed_report_fields_are_the_runtimes_required_fields_and_enums(self):
        """The text names the fields and values of the schema the real runtime hands out, not a copy that can drift."""
        state, receipt = self.start("document")
        schema = json.loads(receipt.read_text())["report_schema"]
        self.assertEqual(len(schema["required"]), 5)
        text = loops.REPORT_FIELDS
        for field in schema["required"]:
            self.assertIn(field, text)
        for field, spec in schema["properties"].items():
            if "enum" in spec:
                self.assertIn(field + " " + "|".join(spec["enum"]), text)
        self.assertEqual(text.count("nonblank text"), 1)
        for line in (loops.RESULT_LINE, loops.RESUME_RESULT_LINE):
            self.assertTrue(line.endswith(text))

    def test_a_started_loop_leads_with_resume_not_run_and_prints_no_start_command(self):
        """The runtime does not refuse a second start for one receipt, so a packet read after the start prints no
        start command (plan 6.3, LP-3): the resume line takes the RUN line's place and the result line names next_argv."""
        state = self.state_for("test")
        self.write(state)
        fresh = loops.invoke_lines(self.root, state)
        command = self.block(state).command
        self.assertEqual(fresh[:4], ["", loops.BLOCK_HEADING, loops.INVOKE_LINE, command])
        self.assertEqual(self.block(state).run(self.root)["status"], "active")
        started = loops.invoke_lines(self.root, state)
        self.assertEqual(started[:4], ["", loops.BLOCK_HEADING, loops.RESUME_LINE, loops.ARGUMENT_LEAD])
        self.assertNotIn(loops.INVOKE_LINE, started)
        self.assertNotIn(loops.FOLLOW_LINE, started)
        self.assertFalse([line for line in started if " start --receipt " in line], "no start command to run twice")
        self.assertIsNone(self.block(state).command)
        self.assertIn("do not start it again", loops.RESUME_LINE)
        self.assertIn("a second start resets it", loops.RESUME_LINE)
        # The argument and the closing rule stay for a reader who lost context; the result line has no start command.
        self.assertEqual(started[4:-2], fresh[5:-2])
        self.assertEqual(started[-2:], [loops.RESUME_RESULT_LINE, fresh[-1]])
        self.assertNotIn("start command", loops.RESUME_RESULT_LINE)
        self.assertIn("next_argv", loops.RESUME_RESULT_LINE)

    def test_the_ask_agent_implement_block_has_the_same_shape_and_one_command(self):
        """The whole-plan implement action of the ask-agent route prints the same block: command first, argument after."""
        state = dict(self.state_for("implement"), delegation="ask-agent")
        state["inner_loops"]["W1"]["action"]["id"] = "A-implement"
        self.write(state)
        lines = loops.invoke_lines(self.root, state)
        receipt, contract_file = loops.receipt_path(self.root, "A-implement"), self.root / loops.contract_path("A-implement")
        self.assertEqual(lines[:5], ["", loops.BLOCK_HEADING, loops.INVOKE_LINE,
                                     loops.start_command(loops.runtime(state), receipt, contract_file), loops.FOLLOW_LINE])
        self.assertIn("for the change of every step, S1 to S2, in order. Write no tests", "\n".join(lines))
        self.assertEqual(lines.count(loops.ARGUMENT_BEGIN), 1)

    def test_a_missing_contract_says_blocked(self):
        state, _receipt = self.start("test")
        (self.root / loops.contract_path("A-test")).unlink()
        self.assertEqual(loops.invoke_lines(self.root, state)[-1],
                         "The loop contract is missing; report outcome blocked naming this path.")

    def test_no_runtime_prints_unavailable_with_the_blocked_route(self):
        state = dict(self.state_for("document"), improve_skill=str(self.repo / "missing" / "SKILL.md"))
        lines = loops.invoke_lines(self.root, state)
        self.assertNotIn(loops.INVOKE_LINE, lines)
        self.assertTrue(lines[-1].startswith("Unavailable: the Until Loop runtime cannot be resolved"))
        self.assertTrue(lines[-1].endswith("Report outcome blocked with this reason."))

    def test_outside_an_inner_stage_nothing_is_printed(self):
        self.assertEqual(loops.invoke_lines(self.root, {"stage": "spec"}), [])


class RenderedPacketsTests(unittest.TestCase):
    """One start route in every looped stage's printed text (plan U9): the packet file's text and the head a long packet
    prints, inline and ask-agent, name the literal command and no tool.  The offline step slice drives the navigator
    through a neutral case with synthetic results, so every inner stage's packet is the one a run prints.  (Its
    implement packet, on either route, says the loop is unavailable: the synthetic step plan has no steps; the Synthetic
    tests above cover both routes' implement block.)"""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
        import packets as offline
        case = json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text())["node-fix-bug"]
        cls.renders = {(route, printed): offline.offline_packets(case, route, printed)
                       for route in ("inline", "ask-agent") for printed in (False, True)}

    def looped(self):
        """(label, stage, text) of every looped stage's packet; an Improve stage's packet has its own Skill-tool line."""
        for (route, printed), packets in self.renders.items():
            for key, text in packets.items():
                if not key.endswith("-improve"):
                    yield f"{route} {'head' if printed else 'file'} {key}", key.split("-", 1)[1], text

    def test_every_looped_stage_prints_the_run_line_then_the_command_and_names_no_tool(self):
        seen, unavailable = set(), []
        for label, stage, text in self.looped():
            with self.subTest(packet=label):
                for forbidden in ("Skill tool", "skill until-loop"):
                    self.assertNotIn(forbidden, text)
                self.assertIsNone(re.search(SLASH_FORM, text), "the slash form of the loop")
                block = support.LoopBlock(text)
                if block.lines[1].startswith("Unavailable: "):
                    unavailable.append(stage)
                    continue
                seen.add(stage)
                self.assertEqual(block.lines[1], loops.INVOKE_LINE)
                self.assertTrue(block.command and block.command == block.lines[2], "the command follows the RUN line")
                self.assertEqual(block.lines[3], loops.FOLLOW_LINE)
                self.assertEqual(block.begins, [4], "the argument follows the command")
                self.assertEqual(len([line for line in block.lines if " start --receipt " in line]), 1)
        self.assertEqual(seen, set(stage_spec.INNER) - {"implement"}, "every other inner stage was rendered with its block")
        self.assertEqual(set(unavailable), {"implement"})

    def test_the_head_and_the_test_stage_name_the_argument_by_its_name_not_the_slash_form(self):
        texts = [text for _label, _stage, text in self.looped()]
        self.assertTrue(any(nav.DONE_WHEN_LOOP in text for text in texts))
        self.assertIn("the Until Loop argument below", nav.DONE_WHEN_LOOP)
        floors = [text for _label, stage, text in self.looped() if stage == "test"]
        self.assertTrue(floors and all("recorded command in the Until Loop argument above from " in text for text in floors))


class CheckTerminalTests(Synthetic):
    def test_a_complete_satisfied_receipt_supports_done_only(self):
        for stage, classification in (("implement", "non-trivial"), ("verify", "trivial")):
            with self.subTest(stage=stage):
                state, receipt = self.start(stage)
                refs = {"evidence_refs": [str(receipt)]}
                self.refused(state, {"outcome": "done", **refs}, f"the {stage} loop is still active")
                final = self.report(receipt, dict(TRIVIAL, classification=classification))
                self.assertEqual(final["status"], "complete", final)
                loops.check_terminal(self.root, state, {"outcome": "done", **refs})
                # repeat is retired: the bound Until Loop repeats the work, so no outcome repeats the graph.
                self.refused(state, {"outcome": "repeat", **refs},
                             f"{stage} accepts only done, blocked, send-back; the bound Until Loop repeats the work")
                self.refused(state, {"outcome": "send-back", **refs}, f"a complete {stage} loop reports outcome done")
                # ShipLoop lists the receipt itself (U10, X-15): the check needs only the file, and returns it.
                self.assertEqual(loops.check_terminal(self.root, state, {"outcome": "done", "evidence_refs": []}), receipt)
                self.assertEqual(loops.cite_receipt({"outcome": "done", "evidence_refs": []}, receipt)["evidence_refs"],
                                 [str(receipt)])
                self.refused(self.state_for(stage, title="Other title"), {"outcome": "done", **refs},
                             "not from a run of this action's contract")

    def test_an_active_receipt_is_reported_before_the_contract_is_compared(self):
        """E4 (run-insights plan 8.5): a live run from another contract must end first, because the runtime refuses a new
        start over an active receipt, so a contract mismatch named first would send the model to a start command that is
        refused.  Once the run ends, the same result is refused for its contract."""
        state, receipt = self.start("verify")
        other = self.state_for("verify", title="Other title")
        refs = {"evidence_refs": [str(receipt)]}
        self.refused(other, {"outcome": "done", **refs}, "the verify loop is still active")
        self.refused(other, {"outcome": "send-back", **refs}, "the verify loop is still active")
        self.report(receipt, TRIVIAL)
        self.refused(other, {"outcome": "done", **refs}, "not from a run of this action's contract")
        loops.check_terminal(self.root, state, {"outcome": "done", **refs})

    def test_cite_receipt_lists_the_checked_receipt_once_and_changes_nothing_else(self):
        receipt = Path("/run/loops/A-terminal.json")
        base = {"outcome": "done", "summary": "s", "evidence_refs": ["/run/notes/a.md"]}
        cited = loops.cite_receipt(base, receipt)
        self.assertEqual(cited, {**base, "evidence_refs": ["/run/notes/a.md", str(receipt)]})
        self.assertEqual(base["evidence_refs"], ["/run/notes/a.md"])             # the submitted mapping is not changed
        self.assertIs(loops.cite_receipt(cited, receipt), cited)                  # already listed: as it is
        self.assertEqual(loops.cite_receipt({"outcome": "done"}, receipt)["evidence_refs"], [str(receipt)])
        self.assertIs(loops.cite_receipt(base, None), base)                       # no receipt was checked
        text = {"outcome": "done", "evidence_refs": "not a list"}
        self.assertIs(loops.cite_receipt(text, receipt), text)                    # a malformed field is left to its gate

    def test_a_blocked_result_before_the_loop_started_checks_no_receipt_and_cites_none(self):
        state = self.state_for("carry-forward")
        self.write(state)
        result = {"outcome": "blocked", "evidence_refs": []}
        self.assertIsNone(loops.check_terminal(self.root, state, result))
        self.assertIs(loops.cite_receipt(result, None), result)

    def test_verify_needs_a_final_trivial_satisfied_report(self):
        state, receipt = self.start("verify")
        self.report(receipt, MATERIAL, TRIVIAL)
        refs = {"outcome": "done", "evidence_refs": [str(receipt)]}
        packet = json.loads(receipt.read_text())
        packet["last_report"]["classification"] = "non-trivial"
        receipt.write_text(json.dumps(packet))
        self.refused(state, refs, "this loop's review gate needs a final trivial report")
        packet["last_report"].update(classification="trivial", exit_assessment="unsatisfied")
        receipt.write_text(json.dumps(packet))
        self.refused(state, refs, "a complete terminal packet needs a final report whose exit is satisfied")

    def test_a_missing_receipt_refuses_done_with_the_start_command_and_accepts_blocked(self):
        state = self.state_for("carry-forward")
        self.write(state)
        receipt = loops.receipt_path(self.root, "A-carry-forward")
        start = loops.start_command(loops.runtime(state), receipt, self.root / loops.contract_path("A-carry-forward"))
        with self.assertRaises(loops.LoopError) as caught:
            loops.check_terminal(self.root, state, {"outcome": "done", "evidence_refs": [str(receipt)]})
        self.assertIn("the carry-forward loop has not run: no terminal packet exists at " + str(receipt),
                      str(caught.exception))
        self.assertIn("Start it with: " + start, str(caught.exception))
        loops.check_terminal(self.root, state, {"outcome": "blocked", "evidence_refs": []})
        self.refused(state, {"outcome": "send-back", "evidence_refs": []}, "carry-forward accepts only done, blocked;")

    def test_a_blocked_stop_supports_blocked_or_send_back_and_a_cancelled_one_nothing(self):
        state, receipt = self.start("test-spec")
        self.assertEqual(self.report(receipt, BLOCKED)["status"], "stopped")
        for outcome in ("blocked", "send-back"):
            loops.check_terminal(self.root, state, {"outcome": outcome, "evidence_refs": [str(receipt)]})
        self.refused(state, {"outcome": "done", "evidence_refs": [str(receipt)]},
                     "a test-spec loop stopped as blocked reports outcome blocked, with awaiting, or send-back")
        state, receipt = self.start("step-plan")
        self.report(receipt, CANCELLED)
        for outcome in ("done", "blocked"):
            self.refused(state, {"outcome": outcome, "evidence_refs": [str(receipt)]},
                         "the step-plan loop was cancelled after 1 iterations; it has no iteration limit")
        # A packet read after the start prints no start command (a second start resets the loop), so the refusal that
        # tells the model to start again carries it.
        command = loops.start_command(loops.runtime(state), receipt, self.root / loops.contract_path("A-step-plan"))
        with self.assertRaises(loops.LoopError) as caught:
            loops.check_terminal(self.root, state, {"outcome": "done", "evidence_refs": [str(receipt)]})
        self.assertIn("start the loop again with " + command + " and run it", str(caught.exception))

    def test_a_receipt_the_runtime_did_not_write_is_refused(self):
        state, receipt = self.start("document")
        self.report(receipt, TRIVIAL)
        result = {"outcome": "done", "evidence_refs": [str(receipt)]}
        genuine = json.loads(receipt.read_text())
        receipt.write_text(json.dumps({k: v for k, v in genuine.items() if k != "status_semantics"}))
        self.refused(state, result, "not a complete Until Loop packet")
        receipt.write_text(json.dumps(dict(genuine, receipt=str(receipt) + ".other")))
        self.refused(state, result, "not written by a run started with --receipt")
        receipt.write_text(json.dumps(dict(genuine, done_argv=["x"])))
        self.refused(state, result, "still offers a callback")
        receipt.write_text("not json")
        self.refused(state, result, "is not valid JSON")

    def test_outside_an_inner_stage_there_is_no_loop_to_check(self):
        self.refused({"stage": "spec"}, {"outcome": "done"}, "not in an inner stage")


class NavigatorLoopTests(fx.RunDriver):
    """The navigator's ``complete`` checks the receipt first, at every inner stage (here verify, the review loop)."""

    def receipt(self) -> Path:
        return loops.receipt_path(self.run_dir, self.action())

    def run_loop(self, reports: list, *, contract_edit=None) -> dict:
        """Start the packet's printed command, submit ``reports`` in order; the runtime writes the receipt."""
        # The command is the one the packet prints (owner, 2026-10-16), split into words so a test can edit the contract.
        # A packet read after the start prints none (a second start resets the loop): a test that starts again on
        # purpose builds the same command the gate names.
        block = support.LoopBlock(self.packet())
        command = loops.start_command(loops.runtime(self.state()), self.receipt(), Path(block.field("Contract: ")))
        self.assertIn(block.command, (command, None))
        words = shlex.split(command)
        self.assertEqual(words[-2], "<")
        contract = json.loads(Path(words[-1]).read_text())
        if contract_edit is not None:
            contract_edit(contract)
        packet = json.loads(subprocess.run(words[:-2], input=json.dumps(contract), text=True,
                                           capture_output=True, check=True, timeout=30).stdout)
        for report in reports:
            self.assertEqual(packet["status"], "active")
            packet = json.loads(subprocess.run(packet["done_argv"], input=json.dumps(report), text=True,
                                               capture_output=True, check=True, timeout=30).stdout)
        self.assertEqual(json.loads(self.receipt().read_text()), packet)
        return packet

    def submit(self, result: dict) -> str:
        return self.complete(result, prepare_inner=False)

    def test_the_packet_carries_the_invoke_block_and_the_entry_wrote_the_contract(self):
        self.start()
        self.drive_to("verify")
        packet = self.packet()
        self.assertIn(loops.INVOKE_LINE, packet)
        contract = json.loads((self.run_dir / loops.contract_path(self.action())).read_text())
        self.assertEqual(contract, loops.contract(self.run_dir, self.state(), self.action()))
        self.assertEqual(contract["workspace"], str(self.repo))
        self.assertIn("\nWork: " + contract["work"] + "\n", packet)
        block = support.LoopBlock(packet)
        self.assertEqual((len(block.begins), len(block.ends)), (1, 1))
        self.assertEqual(block.field("Contract: "), str(self.run_dir / loops.contract_path(self.action())))
        self.assertEqual(block.field("Receipt: "), str(self.receipt()))

    def test_a_run_without_an_improve_card_uses_the_bundled_runtime(self):
        """Since 2026-10-10 every inner stage runs a loop, so a run that selected no Improve card binds the improve
        skill bundled beside ShipLoop instead of printing the loop as unavailable."""
        self.start(improve_skill="")
        self.drive_to("verify")
        packet = self.packet()
        self.assertIn(loops.INVOKE_LINE, packet)
        # The packet names the bundled runtime's script in the command it prints, not a card to read.
        self.assertIn(" " + str(fx.ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py") + " start ",
                      packet)
        self.assertNotIn("ADAPTER.md", packet.split("Until Loop (no iteration limit")[1])
        self.assertNotIn("Unavailable:", packet)

    def test_a_completed_loop_is_accepted_as_done(self):
        self.start()
        self.drive_to("verify")
        terminal = self.run_loop([MATERIAL, TRIVIAL])
        self.assertEqual((terminal["status"], terminal["progress"]["action_number"]), ("complete", 2))
        self.submit(dict(fx.DONE, evidence_refs=[str(self.receipt())]))
        self.assertEqual(nav.current_stage(self.state()), "carry-forward")

    def test_done_without_a_matching_receipt_is_refused_and_nothing_is_saved(self):
        self.start()
        self.drive_to("verify")
        before = (self.run_dir / "state.md").read_bytes()
        for result, message in ((fx.DONE, "the verify loop has not run: no terminal packet exists at"),
                                (dict(fx.DONE, outcome="repeat"), "verify accepts only done, blocked, send-back")):
            with self.subTest(message=message), self.assertRaisesRegex(nav.NavigatorError, message):
                self.submit(result)
        edits = {"work": lambda contract: contract.update(work="Something easier."),
                 "authority": lambda contract: contract["context"].update(authority="Anything goes.")}
        for name, edit in edits.items():
            with self.subTest(edited=name):
                self.run_loop([TRIVIAL], contract_edit=edit)
                with self.assertRaisesRegex(nav.NavigatorError, "not from a run of this action's contract"):
                    self.submit(dict(fx.DONE, evidence_refs=[str(self.receipt())]))
        # Editing the contract file itself cannot reshape the loop: ShipLoop rebuilds it from state.
        contract_file = self.run_dir / loops.contract_path(self.action())
        self.assertIn("Do duty items", contract_file.read_text())  # the edit below must change the file (re-cut wording)
        contract_file.write_text(contract_file.read_text().replace("Do duty items", "Skim duty items"))
        self.run_loop([TRIVIAL])
        with self.assertRaisesRegex(nav.NavigatorError, "not from a run of this action's contract"):
            self.submit(dict(fx.DONE, evidence_refs=[str(self.receipt())]))
        self.receipt().write_text(json.dumps({"status": "complete", "conditions": [], "progress": 1}))
        with self.assertRaisesRegex(nav.NavigatorError, "not a complete Until Loop packet"):
            self.submit(dict(fx.DONE, evidence_refs=[str(self.receipt())]))
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_a_copied_or_live_receipt_is_refused(self):
        """Audit 2026-09-26: a six-key object copied from the contract passed as the terminal packet."""
        self.start()
        self.drive_to("verify")
        before = (self.run_dir / "state.md").read_bytes()
        result = dict(fx.DONE, evidence_refs=[str(self.receipt())])
        contract = json.loads((self.run_dir / loops.contract_path(self.action())).read_text())
        self.receipt().parent.mkdir(exist_ok=True)
        self.receipt().write_text(json.dumps({
            "status": "complete", "workspace": contract["workspace"], "work": contract["work"],
            "conditions": {"exit": contract["exit_condition"], "repeat": contract["repeat_condition"]},
            "progress": {"action_number": 1, "trivial_streak": 1,
                         "required_trivial_reviews": contract["required_trivial_reviews"]},
            "context": contract["context"]}))
        with self.assertRaisesRegex(nav.NavigatorError, "not a complete Until Loop packet"):
            self.submit(result)
        self.receipt().unlink()
        live = self.run_loop([])
        self.assertEqual(live["status"], "active")
        self.receipt().write_text(json.dumps(dict(live, status="complete", next_argv=None, done_argv=None,
                                                  report_schema=None, last_report=TRIVIAL)))
        with self.assertRaisesRegex(nav.NavigatorError, "still live"):
            self.submit(result)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_the_loop_has_no_iteration_limit(self):
        """Owner decision 2026-09-26: ShipLoop loops run until their exit condition holds."""
        self.start()
        self.drive_to("verify")
        self.assertIn("there is no iteration limit", self.packet())
        terminal = self.run_loop([MATERIAL] * 6 + [TRIVIAL])
        self.assertEqual(terminal["progress"]["action_number"], 7)
        refs = [str(self.receipt())]
        for outcome in ("send-back", "blocked"):
            with self.assertRaisesRegex(nav.NavigatorError, "a complete verify loop reports outcome done"):
                self.submit(dict(fx.DONE, outcome=outcome, awaiting=SERVICE_WAIT, evidence_refs=refs))
        self.submit(dict(fx.DONE, evidence_refs=refs))
        self.assertEqual(nav.current_stage(self.state()), "carry-forward")

    def test_a_cancelled_loop_is_refused_and_a_blocked_stop_reports_blocked(self):
        self.start()
        self.drive_to("verify")
        self.run_loop([MATERIAL] * 4 + [CANCELLED])
        refs = [str(self.receipt())]
        for outcome in ("done", "send-back", "blocked"):
            with self.assertRaisesRegex(nav.NavigatorError, "cancelled after 5 iterations; it has no iteration "
                                                             "limit.*pause command"):
                self.submit(dict(fx.DONE, outcome=outcome, awaiting=SERVICE_WAIT, evidence_refs=refs))
        self.receipt().unlink()
        self.run_loop([BLOCKED])
        with self.assertRaisesRegex(nav.NavigatorError, "stopped as blocked reports outcome blocked"):
            self.submit(dict(fx.DONE, evidence_refs=refs))
        self.submit(dict(fx.DONE, outcome="blocked", awaiting=SERVICE_WAIT,
                         summary="Material finding at iteration 1.", evidence_refs=refs))
        self.assertEqual(self.state()["status"], "blocked")

    def test_blocked_without_a_receipt_is_accepted(self):
        """A loop that never started (for example, no usable runtime) can still report blocked."""
        self.start()
        self.drive_to("verify")
        self.assertFalse(self.receipt().exists())
        self.submit(dict(fx.DONE, outcome="blocked", awaiting=SERVICE_WAIT, summary="Until Loop runtime unavailable."))
        self.assertEqual(self.state()["status"], "blocked")

    def test_an_earlier_inner_stage_is_gated_the_same_way(self):
        """implement (no trivial review asked): done needs the receipt, and a complete non-trivial run is enough."""
        self.start()
        self.drive_to("implement")
        (self.repo / "a.py").write_text("x = 2\n")
        with self.assertRaisesRegex(nav.NavigatorError, "the implement loop has not run"):
            self.submit(fx.DONE)
        self.run_loop([MATERIAL, dict(MATERIAL, exit_assessment="satisfied", continuation_assessment="allowed")])
        self.submit(dict(fx.DONE, evidence_refs=[str(self.receipt())]))
        # Accepted: the step's Improve child (owner decision 6) now reviews it.
        self.assertEqual(self.state()["active_improve"]["stage"], "implement")


class DutyTests(unittest.TestCase):
    def test_no_inner_duty_tells_the_model_to_write_the_receipt_the_packet_says_not_to_touch(self):
        """The duty once said to save every packet to a "printed latest-packet path" and the terminal one byte for
        byte; the packet prints a receipt the runtime writes and tells the model not to write or edit it."""
        for stage in loops.STAGES:
            duty = prompts.DUTIES[stage]
            with self.subTest(stage):
                self.assertNotIn("latest-packet", duty)
                self.assertNotIn("byte for byte", duty)
        self.assertIn("do not write or edit it", loops.RECEIPT_LINE)



class MissingContractTests(unittest.TestCase):
    """A run that reached an inner stage without a transition (a seeded run; a recovery after the file was lost) gets the
    stage's contract when ShipLoop prints its packet. The first live step slices on the 8 stages (2026-10-10) stopped at
    step-plan with "The loop contract is missing; report outcome blocked": the seed records the earlier stages in state,
    so no complete wrote the contract."""

    def test_next_writes_the_contract_of_a_run_seeded_at_step_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-missing-contract-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            run = Path(temp).resolve() / "run"
            run.mkdir()
            state = nav.new_state(str(repo), "Build a thing.", delegation="inline")
            while nav.current_stage(state) != "step-plan":
                here, action = nav.current_stage(state), nav.current_action(state)["id"]
                extra = {"work_items": [{"id": "W1", "title": "one", "context": "c"}]} if here == "plan" else {}
                state = nav.apply(state, action, {"outcome": "done", "summary": "Synthetic", **extra})
                if state.get("active_improve") is not None:
                    state = nav.finish_improve(state, action, {"summary": "Synthetic review"})
            nav.save(run, state)
            action = nav.current_action(state)["id"]
            contract = run / loops.contract_path(action)
            self.assertFalse(contract.exists())
            printed = subprocess.run([sys.executable, "-B", str(ROOT / "skills/shiploop/scripts/shiploop"), "next",
                                      "--run-dir", str(run)], capture_output=True, text=True,
                                     env={**__import__("os").environ, "SHIPLOOP_PROGRESS": "off"})
            self.assertEqual(printed.returncode, 0, printed.stderr)
            self.assertTrue(contract.is_file())
            self.assertEqual(json.loads(contract.read_text()), loops.contract(run, state, action))
            self.assertNotIn("The loop contract is missing", (run / "packets" / (action + ".md")).read_text())


    def test_check_only_inside_the_loop_accepts_the_prefilled_receipt_before_it_exists(self) -> None:
        """The live hello run on 13d278dd (2026-10-11) was refused "evidence_refs cite files that do not exist: ...
        loops/<action>-terminal.json. Write the file" for a --check-only run inside the loop: the receipt is the
        runtime's, so a check from inside the loop must not ask the model to write it."""
        with tempfile.TemporaryDirectory(prefix="shiploop-check-only-receipt-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            run = Path(temp).resolve() / "run"
            run.mkdir()
            state = nav.new_state(str(repo), "Build a thing.", delegation="inline")
            while nav.current_stage(state) != "document":
                here, action = nav.current_stage(state), nav.current_action(state)["id"]
                extra = ({"work_items": [{"id": "W1", "title": "one", "context": "c"}]} if here == "plan" else
                         {"steps": [{"id": "S1", "task": "Make it."}]} if here == "step-plan" else {})
                state = nav.apply(state, action, {"outcome": "done", "summary": "Synthetic", **extra})
                if state.get("active_improve") is not None:
                    state = nav.finish_improve(state, action, {"summary": "Synthetic review"})
            nav.save(run, state)
            action = nav.current_action(state)["id"]
            receipt = loops.receipt_path(run, action)
            self.assertFalse(receipt.exists())
            result = run / "inbox" / (action + ".md")
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_text("```shiploop-state\n" + json.dumps({"outcome": "done", "summary": "Docs updated.",
                              "headline": "Docs updated.", "evidence_refs": [str(receipt)]}) + "\n```\n")
            cli = [sys.executable, "-B", str(ROOT / "skills/shiploop/scripts/shiploop"), "complete", "--run-dir", str(run),
                   "--action", action, "--result", str(result)]
            env = {**__import__("os").environ, "SHIPLOOP_PROGRESS": "off"}
            checked = subprocess.run(cli + ["--check-only"], capture_output=True, text=True, env=env)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertNotIn("Write the file", checked.stdout + checked.stderr)
            # The real complete still needs the receipt: the loop's own check refuses, naming the start command.
            real = subprocess.run(cli, capture_output=True, text=True, env=env)
            self.assertEqual(real.returncode, 2, real.stdout + real.stderr)
            self.assertIn("has not run", real.stdout + real.stderr)


class WorkTextTests(Synthetic):
    """The Work and Repeat text of each contract cites the packet's duty items and the one command that tests a draft
    result; both were false in the artifact run (U11, SP-5, TD-6, SPEC-7, VR-6)."""

    # The pin: how many numbered duty items each inner stage's duty prints (the highest number; verify's item 8, the
    # assembly check, prints on the ask-agent route only).  A duty edit that adds, drops or renumbers an item fails here,
    # and the range its Work cites (counted from the same text) moves with it.
    DUTY_ITEMS = {"step-plan": 12, "test-spec": 8, "validate-existing": 4, "implement": 7, "test": 8, "document": 7,
                  "verify": 12, "carry-forward": 4}
    # The items each Work cites.  A stage's loop does its whole duty but verify's: items 10 to 12 (commit nothing, the
    # summary, the send-back route) follow the review loop, and its duty says items 1-7 repeat and 8-9 are done once.
    LOOP_LAST = {"verify": 9}

    def numbers(self, stage: str, route: str) -> list:
        return [int(n) for n in re.findall(r"(?m)^(\d+)\. ", prompts.duty(stage, delegation=route))]

    def work(self, stage: str, route: str = "inline") -> str:
        state = dict(self.state_for(stage), delegation=route)
        return loops.contract(self.root, state, "A-" + stage)["work"]

    def cited(self, work: str) -> list:
        """The duty items a Work line cites, from "duty items 1-7 and 9 of ..." """
        found = re.search(r"duty items ([\d, and-]+) of ", work)
        self.assertTrue(found, work)
        items = []
        for part in re.split(r", | and ", found.group(1).strip()):
            first, _, last = part.partition("-")
            items += list(range(int(first), int(last or first) + 1))
        return items

    def test_the_pinned_duty_counts_are_the_counts_the_packet_prints(self):
        for stage in stage_spec.INNER:
            for route in prompts.DELEGATIONS:
                with self.subTest(stage=stage, route=route):
                    found = self.numbers(stage, route)
                    self.assertEqual(max(found), self.DUTY_ITEMS[stage])
                    self.assertEqual(found, sorted(found))

    def test_each_work_cites_the_duty_items_the_packet_prints_and_the_loop_does_and_no_other(self):
        for stage in stage_spec.INNER:
            for route in prompts.DELEGATIONS:
                with self.subTest(stage=stage, route=route):
                    printed = [n for n in self.numbers(stage, route) if n <= self.LOOP_LAST.get(stage, 99)]
                    self.assertEqual(self.cited(self.work(stage, route)), printed)

    def test_the_ranges_read_as_ranges_and_verify_skips_the_assembly_item_inline(self):
        self.assertIn("duty items 1-12 of ", self.work("step-plan"))
        self.assertIn("duty items 1-4 of ", self.work("carry-forward", "ask-agent"))
        self.assertIn("duty items 1-9 of ", self.work("verify", "ask-agent"))
        self.assertIn("duty items 1-7 and 9 of ", self.work("verify", "inline"))

    def test_the_cited_range_follows_the_duty_text_it_is_generated_from(self):
        """A renumbering cannot leave a stale range: add an item to a duty and the Work moves with it."""
        original = prompts.DUTIES["document"]
        try:
            prompts.DUTIES["document"] = original + "8. **Extra.** An eighth item.\n"
            self.assertIn("duty items 1-8 of ", self.work("document"))
        finally:
            prompts.DUTIES["document"] = original
        self.assertIn("duty items 1-7 of ", self.work("document"))

    def test_verify_says_which_items_repeat_and_which_are_done_once(self):
        text = {route: " ".join(prompts.duty("verify", delegation=route).split()) for route in prompts.DELEGATIONS}
        self.assertIn("Each review iteration does items 1-7 in order; items 8-9 once, before you report the exit "
                      "satisfied.", text["ask-agent"])
        self.assertIn("Each review iteration does items 1-7 in order; item 9 once, before you report the exit "
                      "satisfied.", text["inline"])
        # the exit condition that item 9 serves
        self.assertIn("later-phase checks are marked pending with their owner", stage_spec.stage("verify").done_when[3])
        for route in prompts.DELEGATIONS:
            self.assertIn("9. **Later checks.**", prompts.duty("verify", delegation=route))

    def test_the_assembly_item_prints_on_the_ask_agent_route_only(self):
        self.assertIn("8. **Assembly.**", prompts.duty("verify", delegation="ask-agent"))
        self.assertNotIn("Assembly", prompts.duty("verify", delegation="inline"))

    def test_the_check_only_command_is_the_callback_with_the_flag_added_not_a_printed_command(self):
        for stage in ("step-plan", "test-spec", "test"):
            with self.subTest(stage=stage):
                work = " ".join(self.work(stage).split())
                self.assertIn("then run the Callback command with `--check-only` added and fix each refusal", work)
                self.assertNotIn("printed there", work)
        self.assertIn("(it runs the base run, the candidate run and the mutation check without counting)",
                      " ".join(self.work("test").split()))
        self.assertIn("a lint finding or a check-only refusal", loops.REPEAT["test"])
        for stage in ("document", "implement", "verify", "carry-forward", "validate-existing"):
            self.assertNotIn("check-only", self.work(stage), stage)

    def test_the_printed_callback_with_the_flag_added_is_a_check_only_run(self):
        """Paired with the behaviour the sentence describes: the packet prints the Callback, and the same command plus
        --check-only runs the stage's gates without completing the action."""
        with tempfile.TemporaryDirectory(prefix="shiploop-check-only-callback-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            run = Path(temp).resolve() / "run"
            run.mkdir()
            state = nav.new_state(str(repo), "Build a thing.", delegation="inline")
            while nav.current_stage(state) != "document":
                here, action = nav.current_stage(state), nav.current_action(state)["id"]
                extra = ({"work_items": [{"id": "W1", "title": "one", "context": "c"}]} if here == "plan" else
                         {"steps": [{"id": "S1", "task": "Make it."}]} if here == "step-plan" else {})
                state = nav.apply(state, action, {"outcome": "done", "summary": "Synthetic", **extra})
                if state.get("active_improve") is not None:
                    state = nav.finish_improve(state, action, {"summary": "Synthetic review"})
            nav.save(run, state)
            action = nav.current_action(state)["id"]
            printed = subprocess.run([sys.executable, "-B", str(ROOT / "skills/shiploop/scripts/shiploop"), "next",
                                      "--run-dir", str(run)], capture_output=True, text=True,
                                     env={**__import__("os").environ, "SHIPLOOP_PROGRESS": "off"})
            command = callback_argv(printed.stdout)
            result = callback_result_path(printed.stdout)  # the label names it; the command has no --result flag
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_text("```shiploop-state\n" + json.dumps({"outcome": "done", "summary": "Docs updated.",
                              "headline": "Docs updated.", "evidence_refs": [str(loops.receipt_path(run, action))]})
                              + "\n```\n")
            checked = subprocess.run([*command, "--check-only"], capture_output=True, text=True,
                                     env={**__import__("os").environ, "SHIPLOOP_PROGRESS": "off"})
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("ShipLoop check-only: every script gate for document accepts this result", checked.stdout)
            self.assertEqual(nav.current_action(store.read_record(run / "state.md"))["id"], action)  # not completed


class OneStepRunTests(unittest.TestCase):
    """loops.one_step_run (efficiency plan U16, row VR-2): the one-step one-item fact carry-forward's short duties rest on,
    proved from state alone."""

    @staticmethod
    def state(items: int, steps, implements: int = 1, plan_done: bool = True) -> dict:
        history = [{"action": "sp", "stage": "step-plan", "workitem": "W1", "outcome": "done"}]
        history += [{"action": "i" + str(n), "stage": "implement", "workitem": "W1", "outcome": "done"}
                    for n in range(implements)]
        plan = {"outcome": "done" if plan_done else "send-back"}
        if steps is not None:
            plan["steps"] = [{"id": "S" + str(n + 1)} for n in range(steps)]
        return {"work_items": [{"id": "W" + str(n + 1)} for n in range(items)], "history": history,
                "accepted": {"sp": plan}}

    def test_one_item_with_one_step_is_the_fact(self) -> None:
        self.assertEqual(loops.one_step_run(self.state(1, 1)), "W1")

    def test_several_items_several_steps_or_no_accepted_plan_are_not(self) -> None:
        self.assertIsNone(loops.one_step_run(self.state(2, 1)))   # a pending or completed second item
        self.assertIsNone(loops.one_step_run(self.state(1, 2)))
        self.assertIsNone(loops.one_step_run(self.state(1, 2, implements=1)))  # ask-agent builds both steps in one action
        self.assertIsNone(loops.one_step_run(self.state(1, 1, plan_done=False)))
        self.assertIsNone(loops.one_step_run({"work_items": [], "history": [], "accepted": {}}))

    def test_a_plan_without_steps_counts_its_implement_actions(self) -> None:
        self.assertEqual(loops.one_step_run(self.state(1, None, implements=1)), "W1")
        self.assertIsNone(loops.one_step_run(self.state(1, None, implements=2)))


if __name__ == "__main__":
    unittest.main()
