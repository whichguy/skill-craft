#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's static-checks quality loop on the bound Until Loop.

The run binds the repository's source Improve card, so the loop uses the real
bundled Until Loop runtime; each test drives it only as far as it needs.
"""
from __future__ import annotations

import contextlib
import io
import json
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
IMPROVE_CARD = ROOT / "skills/improve/SKILL.md"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402
import shiploop_store as store  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic iteration; no semantic claim.", "handoff": "Synthetic fixture; nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", exit_assessment="unsatisfied")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class QualityLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-quality-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "repo"
        self.run_dir = self.repo / "runs" / "r1"   # inside the checkout: must stay out of the inventory
        self.run_dir.mkdir(parents=True)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "quality@example.invalid")
        git(self.repo, "config", "user.name", "Quality Test")
        (self.repo / ".gitignore").write_text("ignored.txt\nruns/\n")
        (self.repo / "a.py").write_text("x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    # -- driving -----------------------------------------------------------------

    def start(self, improve_skill: str = str(IMPROVE_CARD)) -> None:
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Quality fixture.", improve_skill=improve_skill,
                                             lint_option="off"))

    def state(self) -> dict:
        return store.read_record(self.run_dir / "state.md")

    def complete(self, result: dict) -> str:
        state = self.state()
        action = nav.current_action(state)["id"]
        if (nav.current_stage(state) == "plan" and result.get("outcome") == "done"
                and "assumptions" not in result):
            result = dict(result, assumptions=[])
        if (nav.current_stage(state) == "step-plan" and result.get("outcome") == "done"
                and "test_commands" not in result):
            result = dict(result, test_commands=[], test_commands_na="Synthetic fixture; no test commands.",
                          paths=["src/**"])
        if nav.current_stage(state) in knowledge_support.knowledge.CLOSES:
            knowledge_support.write(state)
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(result, "result"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            nav.dispatch(CORE, self.run_dir, state,
                         types.SimpleNamespace(command="complete", action=action, result=str(path)))
        return buffer.getvalue()

    def finish_improve(self) -> None:
        state = self.state()
        action = state["active_improve"]["action_id"]
        updated = nav.finish_improve(state, action, {"summary": "Synthetic Improve.",
                                                     "review_refs": ["synthetic://r"],
                                                     "check_refs": ["synthetic://c"]})
        writes, payload = nav._lint_transition(CORE, self.run_dir, state, updated)
        nav.save(self.run_dir, updated, writes)
        nav._lint_finish(self.run_dir, payload)

    def drive_to(self, stage: str, *, improve_stage: str | None = None) -> dict:
        """Advance with synthetic results; an Improve child at ``improve_stage`` is left pending."""
        for _ in range(200):
            state = self.state()
            child = state.get("active_improve")
            if child is not None:
                if child["stage"] == improve_stage:
                    return state
                self.finish_improve()
                continue
            current = nav.current_stage(state)
            if current == stage and improve_stage is None:
                return state
            if current == "implement":
                (self.repo / "a.py").write_text("x = 2\n")
                (self.repo / "new_mod.py").write_text("def entry(value):\n    return value\n")
                (self.repo / "ignored.txt").write_text("not product\n")
            if current == quality.STAGE:
                self.run_loop([TRIVIAL])
                self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
            else:
                self.complete(DONE)
        raise AssertionError("did not reach " + stage)

    # -- the bound Until Loop ------------------------------------------------------

    def action(self) -> str:
        return nav.current_action(self.state())["id"]

    def terminal(self) -> Path:
        return self.run_dir / quality.terminal_path(self.action())

    def packet(self) -> str:
        return nav.render(CORE, self.run_dir, self.state())

    def run_loop(self, reports: list[dict], *, contract_edit=None) -> dict:
        """Start the packet's printed command, submit ``reports`` in order and save the last packet."""
        start = next(line for line in self.packet().splitlines() if line.startswith("Start: "))
        words = shlex.split(start[len("Start: "):])
        self.assertEqual(words[-2], "<")
        contract = json.loads(Path(words[-1]).read_text())
        if contract_edit is not None:
            contract_edit(contract)
        packet = json.loads(subprocess.run(words[:-2], input=json.dumps(contract), text=True,
                                           capture_output=True, check=True, timeout=30).stdout)
        raw = ""
        for report in reports:
            self.assertEqual(packet["status"], "active")
            raw = subprocess.run(packet["done_argv"], input=json.dumps(report), text=True,
                                 capture_output=True, check=True, timeout=30).stdout
            packet = json.loads(raw)
        # The runtime, started with the printed --receipt, already wrote the last packet there.
        self.assertEqual(json.loads(self.terminal().read_text()), packet)
        return packet

    # -- tests ---------------------------------------------------------------------

    def test_packet_carries_script_authored_contract_rubric_and_inventory(self):
        self.start()
        self.drive_to(quality.STAGE)
        packet = self.packet()
        action = self.action()
        self.assertIn("Quality loop (bound Until Loop", packet)
        card = str(ROOT / "skills/improve/runtime/until-loop/ADAPTER.md")
        self.assertIn("Bound Until Loop card (open it if its rules are not already in your context): " + card, packet)
        self.assertIn("Allowed outcomes: done | blocked.", packet)
        contract = json.loads((self.run_dir / quality.contract_path(action)).read_text())
        self.assertEqual(contract["work"], prompts.QUALITY_ITERATION.strip())
        self.assertEqual(contract["exit_condition"], prompts.QUALITY_EXIT_CONDITION)
        self.assertEqual(contract["repeat_condition"], prompts.QUALITY_REPEAT_CONDITION)
        self.assertEqual(contract["required_trivial_reviews"], 1)
        self.assertEqual(contract["workspace"], str(self.repo))
        self.assertIn("Trace.", contract["work"])
        purposes = {row["purpose"]: row["locator"] for row in contract["context"]["resources"]}
        self.assertEqual(Path(purposes["Code craft rubric the review applies"]).read_text(), prompts.CODE_CRAFT)
        self.assertIn("accepted step plan: criteria, focused tests and checks", purposes)
        # Inventory: tracked edit and new untracked file; ignored file and run directory excluded.
        self.assertIn("Change inventory for W1", packet)
        self.assertIn("  M a.py", packet)
        self.assertIn("  A new_mod.py", packet)
        rows = [line for line in packet.split("Change inventory for W1", 1)[1].splitlines()
                if line.startswith("  ")]
        self.assertEqual(rows, ["  M a.py", "  A new_mod.py"])  # ignored file and run directory absent

    def test_render_never_runs_git(self):
        self.start()
        self.drive_to(quality.STAGE)
        with mock.patch.object(lint, "_git", side_effect=AssertionError("render ran Git")):
            self.assertIn("  A new_mod.py", self.packet())

    def test_completed_loop_is_accepted_as_done(self):
        self.start()
        self.drive_to(quality.STAGE)
        terminal = self.run_loop([MATERIAL, TRIVIAL])
        self.assertEqual((terminal["status"], terminal["progress"]["action_number"]), ("complete", 2))
        self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertEqual(nav.current_stage(self.state()), "verify")

    def test_done_without_a_matching_terminal_packet_is_refused(self):
        self.start()
        self.drive_to(quality.STAGE)
        before = (self.run_dir / "state.md").read_bytes()
        cases = [
            (DONE, "list the saved terminal packet in evidence_refs"),
            (dict(DONE, outcome="repeat"), "accepts only done or blocked"),
        ]
        for result, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(nav.NavigatorError, message):
                self.complete(result)
        edits = {
            "work": lambda contract: contract.update(work="Something easier."),
            "authority": lambda contract: contract["context"].update(authority="Anything goes."),
        }
        for name, edit in edits.items():
            with self.subTest(edited=name):
                self.run_loop([TRIVIAL], contract_edit=edit)
                with self.assertRaisesRegex(nav.NavigatorError, "not from a run of this action's contract"):
                    self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        # Editing the contract file itself cannot reshape the loop: ShipLoop rebuilds it from state.
        contract_file = self.run_dir / quality.contract_path(self.action())
        contract_file.write_text(contract_file.read_text().replace("Trace.", "Skim."))
        self.run_loop([TRIVIAL])
        with self.assertRaisesRegex(nav.NavigatorError, "not from a run of this action's contract"):
            self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        # A malformed packet is refused cleanly, not with a crash.
        self.terminal().write_text(json.dumps({"status": "complete", "conditions": [], "progress": 1}))
        with self.assertRaisesRegex(nav.NavigatorError, "not a complete Until Loop packet"):
            self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_a_terminal_packet_the_runtime_did_not_write_is_refused(self):
        """Audit 2026-09-26: a six-key object copied from the contract passed as the terminal packet."""
        self.start()
        self.drive_to(quality.STAGE)
        before = (self.run_dir / "state.md").read_bytes()
        result = dict(DONE, evidence_refs=[str(self.terminal())])
        contract = json.loads((self.run_dir / quality.contract_path(self.action())).read_text())
        forged = {"status": "complete", "workspace": contract["workspace"], "work": contract["work"],
                  "conditions": {"exit": contract["exit_condition"], "repeat": contract["repeat_condition"]},
                  "progress": {"action_number": 1, "trivial_streak": 1,
                               "required_trivial_reviews": contract["required_trivial_reviews"]},
                  "context": contract["context"]}
        self.terminal().write_text(json.dumps(forged))
        with self.assertRaisesRegex(nav.NavigatorError, "not a complete Until Loop packet"):
            self.complete(result)
        # A genuine packet from a run started without the printed --receipt is not this action's receipt.
        start = next(line for line in self.packet().splitlines() if line.startswith("Start: "))
        words = shlex.split(start[len("Start: "):])
        argv = words[:words.index("--receipt")]
        first = json.loads(subprocess.run(argv, input=Path(words[-1]).read_text(), text=True,
                                          capture_output=True, check=True, timeout=30).stdout)
        raw = subprocess.run(first["done_argv"], input=json.dumps(TRIVIAL), text=True,
                             capture_output=True, check=True, timeout=30).stdout
        self.terminal().write_text(raw)
        with self.assertRaisesRegex(nav.NavigatorError, "not written by a run started with --receipt"):
            self.complete(result)
        # A full copy whose run is still live is refused too.
        live = self.run_loop([])
        self.assertEqual(live["status"], "active")
        copy = dict(live, status="complete", next_argv=None, done_argv=None, report_schema=None,
                    last_report=TRIVIAL)
        self.terminal().write_text(json.dumps(copy))
        with self.assertRaisesRegex(nav.NavigatorError, "still live"):
            self.complete(result)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_loop_past_the_iteration_limit_must_report_blocked(self):
        self.start()
        self.drive_to(quality.STAGE)
        terminal = self.run_loop([MATERIAL, MATERIAL, MATERIAL, TRIVIAL])
        self.assertEqual(terminal["progress"]["action_number"], prompts.QUALITY_LOOP_LIMIT + 1)
        refs = [str(self.terminal())]
        with self.assertRaisesRegex(nav.NavigatorError, "more than 3 is outside the contract"):
            self.complete(dict(DONE, evidence_refs=refs))
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", summary="Loop exceeded its limit.", evidence_refs=refs))
        self.assertEqual(self.state()["status"], "blocked")

    def test_stopped_loop_reports_blocked(self):
        self.start()
        self.drive_to(quality.STAGE)
        self.run_loop([dict(MATERIAL, continuation_assessment="cancelled")])
        refs = [str(self.terminal())]
        with self.assertRaisesRegex(nav.NavigatorError, "stopped quality loop reports outcome blocked"):
            self.complete(dict(DONE, evidence_refs=refs))
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", summary="Material finding at iteration 1.",
                           evidence_refs=refs))
        self.assertEqual(self.state()["status"], "blocked")

    def test_blocked_without_a_terminal_packet_is_accepted(self):
        """A loop that never started (for example, no usable runtime) can still report blocked."""
        self.start()
        self.drive_to(quality.STAGE)
        self.assertFalse(self.terminal().exists())
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", summary="Until Loop runtime unavailable."))
        self.assertEqual(self.state()["status"], "blocked")

    def test_run_without_improve_card_says_unavailable(self):
        self.start(improve_skill="")
        self.drive_to(quality.STAGE)
        self.assertIn("Unavailable: no Improve card is bound to this run", self.packet())

    def test_non_git_checkout_records_unavailable_inventory_and_completes(self):
        plain = self.base / "plain"
        plain.mkdir()
        text = lint.inventory_writes(self.run_dir, plain, "W1", "A1")[lint.inventory_path("A1")]
        self.assertIn("unavailable", text)
        self.assertIn("not a Git checkout", text)
        (self.run_dir / "lint").mkdir(exist_ok=True)
        (self.run_dir / lint.inventory_path("A1")).write_text(text)
        self.assertIn("No change inventory recorded for W1 (not a Git checkout)",
                      "\n".join(lint.render_inventory_lines(self.run_dir, "A1", "W1")))

    def test_end_of_work_improve_carries_the_full_rubric(self):
        self.start()
        state = self.drive_to("carry-forward", improve_stage="carry-forward")
        with contextlib.redirect_stdout(io.StringIO()):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="improve-bind", action=state["active_improve"]["action_id"],
                skill_card=str(IMPROVE_CARD)))
        packet = self.packet()
        self.assertIn(prompts.END_REVIEW_FOCUS.strip().splitlines()[0], packet)
        self.assertIn("2. Fail at the door.", packet)
        self.assertIn("4. Spend tokens on information.", packet)

    def test_planning_improve_does_not_carry_the_end_focus(self):
        self.start()
        state = self.drive_to("spec", improve_stage="spec")
        with contextlib.redirect_stdout(io.StringIO()):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="improve-bind", action=state["active_improve"]["action_id"],
                skill_card=str(IMPROVE_CARD)))
        self.assertIn("Planning review focus", self.packet())
        self.assertNotIn("End-of-work code review focus", self.packet())


class PromptTests(unittest.TestCase):
    def test_code_craft_appears_once_in_code_stages_for_both_routes(self):
        for delegation in (prompts.ASK_AGENT, prompts.INLINE):
            for stage in ("implement", "static-checks", "test-author", "verify"):
                text = prompts.prompt(stage, delegation=delegation)
                with self.subTest(delegation=delegation, stage=stage):
                    self.assertEqual(text.count("2. Fail at the door."), 1)
        self.assertNotIn("Fail at the door", prompts.prompt("spec"))

    def test_code_craft_keeps_user_facing_text_translatable(self):
        rubric = " ".join(prompts.CODE_CRAFT.split())
        self.assertIn("7. Write text that can be translated.", rubric)
        self.assertIn("never assembled from fragments", rubric)
        self.assertIn("Keep log text, error codes and machine identifiers stable and untranslated", rubric)
        self.assertIn("bypasses the repository's catalog", " ".join(prompts.QUALITY_ITERATION.split()))

    def test_namespace_placement_is_planned_and_reviewed(self):
        rubric = " ".join(prompts.CODE_CRAFT.split())
        self.assertIn("8. Put it where it belongs.", rubric)
        self.assertIn("narrowest visibility a present consumer needs", rubric)
        self.assertIn("outside the planned namespace", " ".join(prompts.QUALITY_ITERATION.split()))
        plan = " ".join(prompts.prompt("plan").split())
        self.assertIn("When the work adds code or stored data, forecast where it lives.", plan)
        self.assertIn("a remote runtime behind an MCP server", plan)
        self.assertIn("each service of a multi-service system", plan)
        self.assertIn("Record both as a short", plan)
        step = " ".join(prompts.prompt("step-plan").split())
        self.assertIn("reopen the plan's Namespace and data map and the current tree of each environment it touches.", step)
        self.assertIn("Stored data follows the planned schema", rubric)
        self.assertIn("Using Schema and storage guidance, decide how each environment stores the data", plan)
        self.assertIn("Namespace and data map", plan)
        self.assertIn("the owning environment, the schema change mechanism and the round-trip check", step)
        routes = (
            ("Namespace and placement guidance", "coding-practices.md#namespaces-and-placement"),
            ("Schema and storage guidance", "coding-practices.md#schema-and-storage"),
        )
        for stage in ("plan", "step-plan"):
            for route in routes:
                with self.subTest(stage=stage, route=route[0]):
                    self.assertIn(route, prompts.STAGE_REFERENCES[stage])

    def test_ui_work_defaults_to_a_rich_interactive_interface(self):
        self.assertIn("or the rich UI interaction the plan calls for", " ".join(prompts.CODE_CRAFT.split()))
        self.assertIn("a plain or static interaction where the plan called for a rich one",
                      " ".join(prompts.QUALITY_ITERATION.split()))
        for stage in ("plan", "step-plan"):
            with self.subTest(stage=stage):
                self.assertIn("For a human-facing UI, default to an ambitious, highly interactive design",
                              " ".join(prompts.prompt(stage).split()))

    def test_supporting_stages_carry_their_code_quality_duties(self):
        expected = {
            "step-plan": "each such entry point checks its arguments and carries a contract",
            "test-spec": "one rejection case per\nconstraint it checks",
            "test-author": "Author the specified rejection cases",
            "verify": "entry-point inventory against the actual\ndiff",
            "system-test-author": "shared test helpers check their arguments",
            "static-checks": "run this work item's quality loop on the bound Until Loop",
        }
        for stage, phrase in expected.items():
            with self.subTest(stage=stage):
                self.assertIn(" ".join(phrase.split()), " ".join(prompts.prompt(stage).split()))


if __name__ == "__main__":
    unittest.main()
