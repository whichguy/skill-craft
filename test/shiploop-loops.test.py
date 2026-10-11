#!/usr/bin/env python3
"""Hermetic tests for ``shiploop_loops``: the Until Loop every inner stage runs (owner decision 2026-10-10).

ShipLoop writes each inner action's loop contract on entry, prints the strong ``INVOKE /until-loop`` block in the
packet and, before it accepts the result, checks the runtime's receipt against the contract rebuilt from state.
The contract tests feed the contract to the real bundled runtime (its own schema validator and its ``start``); the
terminal tests run the real runtime to the state they need; the navigator tests submit through the real gate.
"""
from __future__ import annotations

import importlib.util
import json
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
import shiploop_loop_contract as loop_contract  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic iteration; no semantic claim.", "handoff": "Synthetic fixture; nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", exit_assessment="unsatisfied")
BLOCKED = dict(MATERIAL, continuation_assessment="blocked")
CANCELLED = dict(MATERIAL, continuation_assessment="cancelled")


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
            "stage": "inner-loop", "work_index": 0, "improve_skill": "",
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
                self.assertIsNone(loop_contract.size_problem(value))
                self.assertEqual(value["required_trivial_reviews"], 1 if stage == "verify" else 0)
                self.assertEqual(value["exit_condition"], loops.exit_condition(stage))
                self.assertEqual(value["exit_condition"].splitlines(),
                                 [f"{n}. {c}" for n, c in enumerate(stage_spec.stage(stage).done_when, 1)])
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

    def test_verify_writes_the_code_craft_rubric_its_contract_names(self):
        writes = self.write(self.state_for("verify"))
        self.assertEqual(writes[quality.RUBRIC_PATH], prompts.CODE_CRAFT)
        value = loops.contract(self.root, self.state_for("verify"), "A-verify")
        purposes = {row["purpose"]: row["locator"] for row in value["context"]["resources"]}
        self.assertEqual(purposes["Code craft rubric the review applies"], str(self.root / quality.RUBRIC_PATH))

    def test_implement_contract_names_the_current_step_and_only_its_paths(self):
        value = loops.contract(self.root, self.state_for("implement"), "A-implement")
        self.assertIn("step S1", value["work"])
        self.assertIn("src/a.py, src/b.py", value["context"]["scope"])
        self.assertNotIn("src/c.py", value["context"]["scope"])
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
    def test_the_invoke_block_prints_the_argument_the_start_command_and_the_receipt_rules(self):
        state = self.state_for("implement")
        self.write(state)
        lines = loops.invoke_lines(self.root, state)
        value = loops.contract(self.root, state, "A-implement")
        contract_file = self.root / loops.contract_path("A-implement")
        receipt = loops.receipt_path(self.root, "A-implement")
        start = loops.start_command(loops.runtime(state), receipt, contract_file)
        exits = ["    " + line for line in value["exit_condition"].splitlines()]
        head = lines.index(loops.INVOKE_LINE)
        self.assertEqual(lines[head:head + 7 + len(exits)], [
            loops.INVOKE_LINE, "Argument:", "    Work: " + value["work"], "    Exit when ALL of these hold:",
            *exits, "    " + value["repeat_condition"], "    Contract: " + str(contract_file),
            "    Receipt: " + str(receipt)])
        self.assertTrue(lines[0] == "" and "there is no iteration limit" in lines[1])
        how = next(line for line in lines if line.startswith("How to invoke:"))
        self.assertIn("Skill tool with skill until-loop", how)
        self.assertIn(loops.runtime(state)["runtime_card"], how)
        self.assertIn("Start (the card runs exactly this; the contract file wins over the argument text): " + start,
                      lines)
        self.assertEqual(lines[-2:], [loops.RECEIPT_RULE, loops.RECEIPT_REF_LINE])
        self.assertIn("Never write or edit the receipt", loops.RECEIPT_RULE)
        self.assertNotIn(loops.RESUME_LINE, lines)

    def test_a_started_loop_says_resume_and_a_missing_contract_says_blocked(self):
        state, _receipt = self.start("test")
        self.assertEqual(loops.invoke_lines(self.root, state)[-1], loops.RESUME_LINE)
        (self.root / loops.contract_path("A-test")).unlink()
        self.assertIn("The loop contract is missing; report outcome blocked naming this path.",
                      loops.invoke_lines(self.root, state))

    def test_no_runtime_prints_unavailable_with_the_blocked_route(self):
        state = dict(self.state_for("document"), improve_skill=str(self.repo / "missing" / "SKILL.md"))
        lines = loops.invoke_lines(self.root, state)
        self.assertNotIn(loops.INVOKE_LINE, lines)
        self.assertTrue(lines[-1].startswith("Unavailable: the Until Loop runtime cannot be resolved"))
        self.assertTrue(lines[-1].endswith("Report outcome blocked with this reason."))

    def test_outside_an_inner_stage_nothing_is_printed(self):
        self.assertEqual(loops.invoke_lines(self.root, {"stage": "spec"}), [])


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
                self.refused(state, {"outcome": "repeat", **refs},
                             f"{stage} accepts only done, blocked, revise; the bound Until Loop repeats the work")
                self.refused(state, {"outcome": "revise", **refs}, f"a complete {stage} loop reports outcome done")
                self.refused(state, {"outcome": "done", "evidence_refs": []},
                             "list the saved terminal packet in evidence_refs")
                self.refused(self.state_for(stage, title="Other title"), {"outcome": "done", **refs},
                             "not from a run of this action's contract")

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
        self.refused(state, {"outcome": "revise", "evidence_refs": []}, "carry-forward accepts only done, blocked;")

    def test_a_blocked_stop_supports_blocked_or_revise_and_a_cancelled_one_nothing(self):
        state, receipt = self.start("test-spec")
        self.assertEqual(self.report(receipt, BLOCKED)["status"], "stopped")
        for outcome in ("blocked", "revise"):
            loops.check_terminal(self.root, state, {"outcome": outcome, "evidence_refs": [str(receipt)]})
        self.refused(state, {"outcome": "done", "evidence_refs": [str(receipt)]},
                     "a test-spec loop stopped as blocked reports outcome blocked")
        state, receipt = self.start("step-plan")
        self.report(receipt, CANCELLED)
        for outcome in ("done", "blocked"):
            self.refused(state, {"outcome": outcome, "evidence_refs": [str(receipt)]},
                         "the step-plan loop was cancelled after 1 iterations; it has no iteration limit")

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
        prefix = "Start (the card runs exactly this; the contract file wins over the argument text): "
        start = next(line for line in self.packet().splitlines() if line.startswith(prefix))
        words = shlex.split(start[len(prefix):])
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
        self.assertIn("    Work: " + contract["work"], packet)

    def test_a_run_without_an_improve_card_uses_the_bundled_runtime(self):
        """Since 2026-10-10 every inner stage runs a loop, so a run that selected no Improve card binds the improve
        skill bundled beside ShipLoop instead of printing the loop as unavailable."""
        self.start(improve_skill="")
        self.drive_to("verify")
        packet = self.packet()
        self.assertIn(loops.INVOKE_LINE, packet)
        self.assertIn(str(fx.ROOT / "skills/improve/runtime/until-loop/ADAPTER.md"), packet)
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
                                (dict(fx.DONE, outcome="repeat"), "verify accepts only done, blocked, revise")):
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
        contract_file.write_text(contract_file.read_text().replace("Run every recorded command", "Skim"))
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
        for outcome in ("revise", "blocked"):
            with self.assertRaisesRegex(nav.NavigatorError, "a complete verify loop reports outcome done"):
                self.submit(dict(fx.DONE, outcome=outcome, blocked_by="external", evidence_refs=refs))
        self.submit(dict(fx.DONE, evidence_refs=refs))
        self.assertEqual(nav.current_stage(self.state()), "carry-forward")

    def test_a_cancelled_loop_is_refused_and_a_blocked_stop_reports_blocked(self):
        self.start()
        self.drive_to("verify")
        self.run_loop([MATERIAL] * 4 + [CANCELLED])
        refs = [str(self.receipt())]
        for outcome in ("done", "revise", "blocked"):
            with self.assertRaisesRegex(nav.NavigatorError, "cancelled after 5 iterations; it has no iteration "
                                                             "limit.*pause command"):
                self.submit(dict(fx.DONE, outcome=outcome, blocked_by="external", evidence_refs=refs))
        self.receipt().unlink()
        self.run_loop([BLOCKED])
        with self.assertRaisesRegex(nav.NavigatorError, "stopped as blocked reports outcome blocked"):
            self.submit(dict(fx.DONE, evidence_refs=refs))
        self.submit(dict(fx.DONE, outcome="blocked", blocked_by="external",
                         summary="Material finding at iteration 1.", evidence_refs=refs))
        self.assertEqual(self.state()["status"], "blocked")

    def test_blocked_without_a_receipt_is_accepted(self):
        """A loop that never started (for example, no usable runtime) can still report blocked."""
        self.start()
        self.drive_to("verify")
        self.assertFalse(self.receipt().exists())
        self.submit(dict(fx.DONE, outcome="blocked", blocked_by="external", summary="Until Loop runtime unavailable."))
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


if __name__ == "__main__":
    unittest.main()
