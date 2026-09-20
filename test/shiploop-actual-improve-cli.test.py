#!/usr/bin/env python3
"""Real ShipLoop/Improve CLI composition; fixture judgments are synthetic."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


CLI = ROOT / "skills/shiploop/scripts/shiploop"
CARD = ROOT / "skills/improve/SKILL.md"
EPHEMERAL = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
LEGACY_UNTIL = ROOT / "skills/improve/runtime/until-loop/scripts/until-loop"


class ImproveCliFixture(unittest.TestCase):
    """Hermetic parent fixture shared by ephemeral and explicit legacy routes."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-child-cli-")
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo"
        self.run = self.base / "run"
        self.environment = {
            **os.environ,
            "PATH": "/Library/Developer/CommandLineTools/usr/bin:" + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.repo.mkdir()
        self.product_contract = self.repo / "product/contracts/cold-recovery.md"
        self.product_contract.parent.mkdir(parents=True)
        self.product_contract.write_text("# Product contract\n\n## child-contract-transfer\n", encoding="utf-8")
        self.product_test = self.repo / "test/product_contract_test.py"
        self.product_test.parent.mkdir()
        self.product_test.write_text("class ProductContractTests:\n    def test_child_contract_transfer(self):\n        pass\n", encoding="utf-8")
        self._start_parent(CARD)

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, executable, *args, status=0):
        result = subprocess.run(
            [sys.executable, "-B", str(executable), *map(str, args)], text=True,
            capture_output=True, cwd=self.base, timeout=30, env=self.environment,
        )
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def invoke_argv(self, argv, payload=None, status=0):
        input_bytes = None if payload is None else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        result = subprocess.run(
            [str(item) for item in argv], input=input_bytes, text=False,
            capture_output=True, cwd=self.base, timeout=30, env=self.environment,
        )
        detail = (result.stdout + result.stderr).decode("utf-8", "replace")
        self.assertEqual(result.returncode, status, detail)
        try:
            packet = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.fail(f"runtime did not return JSON: {detail}\n{exc}")
        self.assertIsInstance(packet, dict)
        return result, packet

    def _prepare_parent_evidence(self):
        self.run_note = self.run / "notes/parent-evidence.md"
        self.run_note.parent.mkdir(parents=True, exist_ok=True)
        self.run_note.write_text("# parent-evidence-transfer\n", encoding="utf-8")
        self.parent_evidence_refs = [
            str(self.product_contract) + "#child-contract-transfer",
            str(self.product_test) + "::ProductContractTests::test_child_contract_transfer",
            str(self.run_note) + "#parent-evidence-transfer",
        ]

    def _start_parent(self, card):
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", self.run,
                    "--prompt", "Protocol composition fixture", "--improve-skill", card)
        self._prepare_parent_evidence()
        self.state = store.read_record(self.run / "state.md")
        self.action = self.state["action"]["id"]
        self.producer = {"outcome": "done", "summary": "Fixture intake evidence.",
                         "evidence_refs": self.parent_evidence_refs}
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "done", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(card)

    def _start_parent_at_stage(self, stage, evidence_refs, card=CARD):
        """Create a real CLI parent at a target stage after synthetic setup only.

        The pure navigator transitions below deliberately do not claim preceding
        Improve execution.  The test's target-stage bind, child runtime and
        parent import still use the actual command-line interfaces.
        """
        run = self.base / ("parent-" + stage)
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", run,
                    "--prompt", "Synthetic predecessor navigation for CLI composition.",
                    "--improve-skill", card)
        state = store.read_record(run / "state.md")
        while navigator.current_stage(state) != stage:
            predecessor = navigator.current_stage(state)
            action = navigator.current_action(state)["id"]
            setup = {
                "outcome": "done",
                "summary": (
                    "Synthetic predecessor navigation only for " + predecessor
                    + "; no child Improve runtime executed."
                ),
            }
            if predecessor == "plan":
                setup["work_items"] = [{"id": "W1", "title": "Synthetic local-skill item"}]
            state = navigator.apply(state, action, setup)
            state = navigator.finish_improve(state, action, {
                "summary": "Synthetic predecessor receipt only; no semantic review claim.",
            })
        navigator.save(run, state)
        self.run = run
        self.state = state
        self.action = navigator.current_action(state)["id"]
        self.parent_evidence_refs = list(evidence_refs)
        self.producer = {
            "outcome": "done",
            "summary": "Fixture local-skill assessment; synthetic prior navigation is setup only.",
            "evidence_refs": self.parent_evidence_refs,
        }
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "done", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(card)

    def bind_current(self, card=CARD):
        self.invoke(CLI, "improve-bind", "--run-dir", self.run, "--action", self.action,
                    "--skill-card", card)
        self.bound = store.read_record(self.run / "state.md")["active_improve"]
        self.completion_path = self.run / "inbox" / (self.action + "-improve.md")
        self.parent_route_path = self.run / "parent-recovery.json"
        self._write_parent_route()

    def _parent_import_argv(self):
        return [sys.executable, "-B", str(CLI), "improve-complete", "--run-dir", str(self.run),
                "--action", self.action, "--result", str(self.completion_path)]

    def _workspace_return_argv(self):
        return [sys.executable, "-B", str(CLI), "workspace", "return", "--workspace-root", str(self.run.parent)]

    def _write_parent_route(self):
        store.write_record(self.parent_route_path, {
            "state": str(self.run / "state.md"),
            "completion_input": str(self.completion_path),
            "improve_complete_argv": self._parent_import_argv(),
            "workspace_return_argv": self._workspace_return_argv(),
        })

    def child_context(self):
        receipt = bridge.receipt_path(self.bound)
        resources = [
            {"purpose": "selected Improve skill", "locator": self.bound["skill"]["skill_card"]},
            {"purpose": "bound Until Loop runtime", "locator": self.bound["skill"]["runtime_cli"]},
            {"purpose": "ShipLoop parent state", "locator": str(self.run / "state.md")},
            {"purpose": "ShipLoop completion input", "locator": str(self.completion_path)},
            {"purpose": "ShipLoop exact return commands", "locator": str(self.parent_route_path)},
            {"purpose": "latest child packet receipt", "locator": str(receipt)},
        ]
        resources.extend({"purpose": "opaque parent evidence locator", "locator": value}
                         for value in self.parent_evidence_refs)
        return {
            "request": "Synthetic ShipLoop v3 Improve composition fixture.\n" + self.bound["contract_marker"]
                       + "\nDo exactly one review cycle per returned callback.",
            "scope": "Review only this frozen ShipLoop action and its producer evidence.",
            "authority": "ShipLoop v3 no-commit authority: do not commit, merge, push, or broaden scope.",
            "environment": "Use the current fixture workspace and declared Python/Git commands only.",
            "resources": resources,
        }

    def child_contract(self):
        return {
            "workspace": str(self.repo.resolve()),
            "work": "Review the frozen ShipLoop candidate, make only authorized fixes, and run current checks.",
            "exit_condition": "Current evidence establishes the requested result after two qualifying trivial reviews.",
            "repeat_condition": "Continue while useful authorized review work remains; otherwise stop incomplete.",
            "required_trivial_reviews": 2,
            "context": self.child_context(),
        }

    def save_packet(self, result):
        path = bridge.receipt_path(self.bound)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.stdout)
        self.assertEqual(path.read_bytes(), result.stdout)
        self.packet_path = path
        return path

    def start_ephemeral_child(self):
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        result, packet = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)],
            self.child_contract(),
        )
        self.assertEqual(packet["status"], "active")
        self.save_packet(result)
        return result, packet

    def child_report(self, classification, exit_assessment, continuation_assessment, label):
        return {
            "classification": classification,
            "exit_assessment": exit_assessment,
            "continuation_assessment": continuation_assessment,
            "evidence": "Synthetic runtime composition observation: " + label,
            "handoff": (
                "Synthetic only; this is not semantic review proof. Current packet receipt: "
                + str(bridge.receipt_path(self.bound)) + ". Parent state: " + str(self.run / "state.md")
                + ". Completion input: " + str(self.completion_path)
                + ". Parent route file: " + str(self.parent_route_path)
                + ". Exact parent import argv: " + json.dumps(self._parent_import_argv())
                + ". Exact workspace return argv: " + json.dumps(self._workspace_return_argv())
                + ". Preserve the binding marker and opaque parent evidence locators."
            ),
        }

    def done_ephemeral(self, packet, report):
        result, successor = self.invoke_argv(packet["done_argv"], report)
        self.save_packet(result)
        return result, successor

    def finish_ephemeral(self, first=None):
        if first is None:
            _raw, first = self.start_ephemeral_child()
        _raw, second = self.done_ephemeral(
            first, self.child_report("non-trivial", "unsatisfied", "allowed", "material finding"))
        _raw, third = self.done_ephemeral(
            second, self.child_report("trivial", "unsatisfied", "allowed", "first qualifying review"))
        terminal_raw, terminal = self.done_ephemeral(
            third, self.child_report("trivial", "satisfied", "allowed", "second qualifying review"))
        self.assertEqual(terminal["status"], "complete")
        self.assertFalse(Path(terminal["state_file"]).exists())
        return terminal_raw, terminal

    def completion_receipt(self, *, final_result=None):
        evidence = bridge.receipt_path(self.bound).parent / "reviews"
        evidence.mkdir(parents=True, exist_ok=True)
        review_one, review_two, checks = (evidence / "review-one.md", evidence / "review-two.md", evidence / "checks.md")
        for path in (review_one, review_two, checks):
            path.write_text("Synthetic protocol evidence: " + path.name + "\n", encoding="utf-8")
        receipt = {
            "summary": "Runtime mechanics completed; no actual review claim.",
            "review_refs": [str(review_one), str(review_two)],
            "check_refs": [str(checks)],
            "lessons": "A terminal callback receipt is structural evidence, not semantic proof.",
        }
        if final_result is not None:
            receipt["final_result"] = final_result
        store.write_record(self.completion_path, receipt)
        return self.completion_path, receipt

    def complete_current_stage_through_actual_improve(self, evidence_refs, summary):
        """Advance one current stage through its existing Improve callbacks."""
        state = store.read_record(self.run / "state.md")
        stage = navigator.current_stage(state)
        self.action = navigator.current_action(state)["id"]
        self.parent_evidence_refs = list(evidence_refs)
        self.producer = {
            "outcome": "done",
            "summary": summary,
            "evidence_refs": self.parent_evidence_refs,
        }
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "done", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current()
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                    "--action", self.action, "--result", completion)
        return stage, self.action, store.read_record(self.run / "state.md")

    def legacy_card(self):
        root = self.base / "legacy-improve"
        runtime = root / "runtime/until-loop"
        scripts = runtime / "scripts"
        scripts.mkdir(parents=True)
        card = root / "SKILL.md"
        card.write_text("---\nname: improve\nversion: legacy-fixture\n---\nExplicit legacy until-loop v2 fixture.\n", encoding="utf-8")
        (runtime / "ADAPTER.md").write_text("---\nname: until-loop\nversion: legacy-fixture\n---\nLegacy v2 runtime.\n", encoding="utf-8")
        (runtime / "references").mkdir()
        shutil.copyfile(LEGACY_UNTIL.parent.parent / "references/decision-rubric.md",
                        runtime / "references/decision-rubric.md")
        for name in ("until-loop", "until_loop_v2.py", "until_loop_packet.py"):
            shutil.copyfile(LEGACY_UNTIL.parent / name, scripts / name)
        return card

    def legacy_parent(self, card):
        run = self.base / "legacy-run"
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", run,
                    "--prompt", "Legacy composition fixture", "--improve-skill", card)
        state = store.read_record(run / "state.md")
        action = state["action"]["id"]
        input_path = run / "inbox" / (action + ".md")
        store.write_record(input_path, {"outcome": "done", "summary": "Legacy fixture"})
        self.invoke(CLI, "done", "--run-dir", run, "--action", action, "--result", input_path)
        self.invoke(CLI, "improve-bind", "--run-dir", run, "--action", action, "--skill-card", card)
        return run, action, store.read_record(run / "state.md")["active_improve"]

    def initialize_legacy_child(self, runtime, binding):
        contract = {
            "version": 1, "policy": "decision-rubric/2",
            "original_request": "Legacy protocol-only fixture.\n" + binding["contract_marker"],
            "interpretation": "Test durable v2 compatibility without ambient selection.",
            "criteria": [{"id": "C1", "text": "Fixture evidence exists", "basis": {"kind": "request", "reference": "fixture"}}],
        }
        contract_path = self.base / "legacy-contract.json"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        self.invoke(runtime, "v2", "init", "--repo", self.repo, "--contract-file", contract_path)
        child = json.loads((self.repo / ".until-loop/state.json").read_text(encoding="utf-8"))
        Path(child["action"]["result_path"]).write_text(json.dumps({
            "action_id": child["action"]["id"], "contract_revision": 1, "decision": "complete",
            "criteria": [{"id": "C1", "status": "satisfied", "evidence": "Synthetic legacy fixture"}],
            "next_action": None, "blocker": None,
        }), encoding="utf-8")
        return child


class EphemeralImproveCliTests(ImproveCliFixture):
    def test_planning_improve_packet_carries_graph_identity_through_real_child_callbacks(self):
        """Synthetic predecessors reach both planning stages; child callbacks are real."""
        for stage, expected_stage in (("plan", "prepare"), ("step-plan", "test-spec")):
            with self.subTest(stage=stage):
                graph = self.repo / "plans" / (stage + "-execution-graph.json")
                graph.parent.mkdir(parents=True, exist_ok=True)
                graph_bytes = (json.dumps({
                    "version": 1,
                    "steps": [
                        {"id": "A", "deps": [], "contract": {
                            "task": "Prepare " + stage,
                            "ready": ["Planning inputs are available"],
                            "done": ["Preparation evidence is recorded"],
                        }},
                        {"id": "B", "deps": ["A"], "contract": {
                            "task": "Verify " + stage,
                            "ready": ["Preparation evidence is recorded"],
                            "done": ["Verification evidence is recorded"],
                        }},
                    ],
                }, sort_keys=True) + "\n").encode("utf-8")
                graph.write_bytes(graph_bytes)
                graph_identity = str(graph) + "#sha256=" + hashlib.sha256(graph_bytes).hexdigest()

                self._start_parent_at_stage(stage, [graph_identity])
                parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
                self.assertIn(graph_identity, parent_packet)
                # Check guidance routing, not paragraph wrapping or the model's judgment.
                guidance = " ".join(parent_packet.split())
                for clause in (
                    "Review the actual steps after their creation", "any linked execution graph",
                    "ready/done criteria", "independent paths", "resource exclusions",
                    "integration/verification ownership",
                ):
                    self.assertIn(clause, guidance)

                start_raw, first = self.start_ephemeral_child()
                cold_raw, cold = self.invoke_argv(first["next_argv"])
                self.assertEqual(start_raw.stdout, cold_raw.stdout)
                self.assertEqual(cold["context"], self.child_context())
                self.assertIn(
                    {"purpose": "opaque parent evidence locator", "locator": graph_identity},
                    cold["context"]["resources"],
                )
                self.save_packet(cold_raw)
                terminal_raw, terminal = self.finish_ephemeral(cold)
                self.assertEqual(terminal["context"], cold["context"])

                completion, _receipt = self.completion_receipt()
                self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                            "--action", self.action, "--result", completion)
                resumed = store.read_record(self.run / "state.md")
                self.assertEqual(navigator.current_stage(resumed), expected_stage)
                self.assertEqual(
                    resumed["improve_results"][self.action]["seed_result"]["evidence_refs"],
                    [graph_identity],
                )
                self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

                if stage != "step-plan":
                    continue

                step_plan_action = self.action
                for next_stage in ("test-spec", "baseline", "test-author", "test-red"):
                    self.assertEqual(navigator.current_stage(resumed), next_stage)
                    evidence = self.repo / "evidence" / (next_stage + ".md")
                    evidence.parent.mkdir(parents=True, exist_ok=True)
                    evidence.write_text("# " + next_stage + "\n", encoding="utf-8")
                    observed_stage, _action, resumed = self.complete_current_stage_through_actual_improve(
                        [str(evidence) + "#fixture"],
                        "Fixture advance through actual Improve for " + next_stage + ".",
                    )
                    self.assertEqual(observed_stage, next_stage)

                self.assertEqual(navigator.current_stage(resumed), "implement")
                self.assertNotEqual(resumed["history"][-1]["action"], step_plan_action)
                self.assertEqual(resumed["accepted"][step_plan_action]["evidence_refs"], [graph_identity])
                self.assertEqual(
                    resumed["improve_results"][step_plan_action]["seed_result"]["evidence_refs"],
                    [graph_identity],
                )

                cold = self.invoke(CLI, "next", "--run-dir", self.run).stdout
                self.assertIn("ShipLoop navigator | implement |", cold)
                self.assertIn("State: " + str(self.run / "state.md"), cold)
                self.assertIn(
                    "If this action depends on earlier accepted context, read the durable state and the relevant result record",
                    cold,
                )
                self.assertIn(
                    "Parallel-chain guide: "
                    + str(ROOT / "skills/shiploop/references/parallel-chain.md")
                    + "#parallel-implementation-chains",
                    cold,
                )
                self.assertIn("bind this action to the default parallel", cold)
                self.assertIn("mode when the selected Plan Dispatcher and Ask-Agent contracts are compatible", cold)

    def test_default_ephemeral_callbacks_preserve_context_then_import_once(self):
        self.assertEqual(self.state["navigator_protocol_version"], 3)
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        self.assertEqual(self.bound["skill"]["runtime_version"], "0.4.0-rc.2")
        self.assertEqual(self.bound["skill"]["skill_version"], "0.2.0-rc.4")
        parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        for text in (self.bound["contract_marker"], "Bound Until Loop CLI locator: " + str(EPHEMERAL.resolve()),
                     "Child latest packet receipt: " + str(bridge.receipt_path(self.bound)), "no-commit",
                     "Save exact, complete raw JSON stdout", "Completion deletes the child's temporary state"):
            self.assertIn(text, parent_packet)

        start_raw, first = self.start_ephemeral_child()
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], self.child_context())
        self.assertEqual(cold["context"]["resources"][-len(self.parent_evidence_refs):], [
            {"purpose": "opaque parent evidence locator", "locator": value}
            for value in self.parent_evidence_refs])
        self.save_packet(cold_raw)

        _raw, second = self.done_ephemeral(cold, self.child_report("non-trivial", "unsatisfied", "allowed", "material finding"))
        self.assertEqual(second["progress"]["trivial_streak"], 0)
        _raw, third = self.done_ephemeral(second, self.child_report("trivial", "unsatisfied", "allowed", "first qualifying review"))
        self.assertEqual(third["progress"]["trivial_streak"], 1)
        self.assertIn(json.dumps(self._parent_import_argv()), third["last_report"]["handoff"])
        terminal_raw, terminal = self.done_ephemeral(third, self.child_report("trivial", "satisfied", "allowed", "second qualifying review"))
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"], {"action_number": 3, "trivial_streak": 2, "required_trivial_reviews": 2})
        self.assertFalse(state_file.exists())
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        self.assertEqual(terminal["context"], self.child_context())
        self.assertIn(str(self.parent_route_path), terminal["last_report"]["handoff"])
        self.assertIn(json.dumps(self._workspace_return_argv()), terminal["last_report"]["handoff"])
        self.assertFalse((self.repo / ".until-loop").exists())

        completion, receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        after = (self.run / "state.md").read_bytes()
        state = store.read_record(self.run / "state.md")
        record = state["improve_results"][self.action]
        self.assertEqual(state["stage"], "discovery")
        self.assertIsNone(state["active_improve"])
        self.assertEqual(record["runtime_phase"], "complete")
        self.assertEqual(record["seed_result"]["evidence_refs"], self.parent_evidence_refs)
        archive = self.run / "improve" / self.action / "terminal.json"
        self.assertEqual(archive.read_bytes(), terminal_raw.stdout)
        self.assertEqual(record["identities"]["terminal_packet_sha256"], hashlib.sha256(terminal_raw.stdout).hexdigest())
        self.assertNotEqual(before, after)
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        self.assertEqual(after, (self.run / "state.md").read_bytes())
        store.write_record(completion, dict(receipt, summary="Conflicting callback"))
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        self.assertEqual(after, (self.run / "state.md").read_bytes())

    def test_empty_initial_commit_retains_selected_untracked_scope_through_child_recovery(self):
        """Exercise immutable transport; synthetic reports do not prove review conduct."""
        def git(*args):
            result = subprocess.run(
                ["git", "-C", str(self.repo), *args], text=True, capture_output=True,
                timeout=30, env=self.environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout.strip()

        git("init", "-q")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "user.name", "Fixture")
        git("config", "commit.gpgsign", "false")
        git("config", "core.hooksPath", "/dev/null")
        git("commit", "--allow-empty", "-qm", "empty initial scope baseline")
        initial_head = git("rev-parse", "HEAD")
        self.assertEqual(git("show", "--format=", "--name-only", "HEAD"), "")

        product = self.repo / "product/checkers.py"
        requirements = self.repo / "docs/requirements.md"
        scratch = self.repo / "scratch/notes.md"
        for path, body in (
            (product, "def move_piece():\n    return 'ok'\n"),
            (requirements, "# Requirements\n\n- A player can move a piece.\n"),
            (scratch, "Unrelated working note.\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        status_before_child = git("status", "--porcelain=v1", "--untracked-files=all")
        for path in (product, requirements, scratch):
            self.assertIn("?? " + str(path.relative_to(self.repo)), status_before_child)
        index_before = (self.repo / ".git/index").read_bytes()

        base_context = self.child_context()
        selected_resources = [
            {"purpose": "selected untracked product candidate", "locator": str(product)},
            {"purpose": "selected untracked requirements", "locator": str(requirements)},
        ]
        manual_context = {
            "request": (
                "Synthetic empty-history candidate-scope fixture.\n"
                + self.bound["contract_marker"]
                + "\nDo exactly one review cycle per returned callback."
            ),
            "scope": (
                "Frozen candidate inventory at " + initial_head + ": include "
                + str(product) + " and " + str(requirements) + "; exclude "
                + str(scratch) + ". The empty initial commit and unchanged HEAD "
                + "do not replace this candidate."
            ),
            "authority": "ShipLoop v3 no-commit authority: do not commit, merge, push, or broaden scope.",
            "environment": "Use the current fixture workspace and declared Python/Git commands only.",
            "resources": base_context["resources"] + selected_resources,
        }
        self.assertNotIn(str(scratch), [resource["locator"] for resource in manual_context["resources"]])
        self.assertIn(str(scratch), manual_context["scope"])
        contract = self.child_contract()
        contract["context"] = manual_context

        start_raw, first = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)], contract
        )
        self.assertEqual(first["status"], "active")
        self.save_packet(start_raw)
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], manual_context)
        self.assertEqual(cold["context"]["resources"][-2:], selected_resources)
        self.save_packet(cold_raw)

        _raw, second = self.done_ephemeral(
            cold, self.child_report("non-trivial", "unsatisfied", "allowed", "synthetic fixture finding")
        )
        _raw, third = self.done_ephemeral(
            second, self.child_report("trivial", "unsatisfied", "allowed", "synthetic first review")
        )
        terminal_raw, terminal = self.done_ephemeral(
            third, self.child_report("trivial", "satisfied", "allowed", "synthetic second review")
        )
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], manual_context)

        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        archive = self.run / "improve" / self.action / "terminal.json"
        archived = json.loads(archive.read_text(encoding="utf-8"))
        self.assertEqual(archive.read_bytes(), terminal_raw.stdout)
        self.assertEqual(archived["context"], manual_context)
        self.assertEqual(store.read_record(self.run / "state.md")["improve_results"][self.action]["runtime_phase"], "complete")

        self.assertEqual(git("rev-parse", "HEAD"), initial_head)
        self.assertEqual((self.repo / ".git/index").read_bytes(), index_before)
        status_after_child = git("status", "--porcelain=v1", "--untracked-files=all")
        for path in (product, requirements, scratch):
            self.assertIn("?? " + str(path.relative_to(self.repo)), status_after_child)
        self.assertEqual(product.read_text(encoding="utf-8"), "def move_piece():\n    return 'ok'\n")
        self.assertEqual(requirements.read_text(encoding="utf-8"), "# Requirements\n\n- A player can move a piece.\n")
        self.assertEqual(scratch.read_text(encoding="utf-8"), "Unrelated working note.\n")

    def test_current_system_baseline_and_delta_survive_bound_child_recovery(self):
        """Host-authored references survive real child CLI recovery and import.

        Predecessor navigation and judgments are synthetic. This does not prove
        the child interpreted the spec; it verifies the explicit handoff duty
        and transport of two distinct product artifacts through the bound runtime.
        """
        baseline = self.repo / "docs/current-system.md"
        delta = self.base / "incoming-spec.md"
        baseline.parent.mkdir(parents=True)
        baseline.write_text(
            "# Current system\n\n## as-of-v1\nObserved: polling runs missed jobs once.\n",
            encoding="utf-8",
        )
        delta.write_text(
            "# Incoming request\n\n## tag-filter\nAdd selection; preserve missed-run behavior.\n",
            encoding="utf-8",
        )
        refs = [str(baseline) + "#as-of-v1", str(delta) + "#tag-filter"]
        self._start_parent_at_stage("spec", refs)
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        for locator in refs:
            self.assertIn(locator, packet)
        handoff = " ".join(packet.split())
        self.assertIn("carry selected prior-baseline and incoming-spec sections", handoff)
        self.assertIn("into this child's existing contract before review", handoff)

        # The host must author this context; ShipLoop does not read the artifacts
        # or populate the semantic child contract automatically.
        contract = self.child_contract()
        context = self.child_context()
        context["resources"][-2:] = [
            {"purpose": "prior as-of baseline", "locator": refs[0]},
            {"purpose": "incoming change specification", "locator": refs[1]},
        ]
        contract["context"] = context
        raw, first = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)],
            contract,
        )
        self.save_packet(raw)
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(cold["context"], context)
        self.save_packet(cold_raw)
        _raw, second = self.done_ephemeral(
            cold, self.child_report("trivial", "unsatisfied", "allowed", "synthetic first review")
        )
        terminal_raw, terminal = self.done_ephemeral(
            second, self.child_report("trivial", "satisfied", "allowed", "synthetic second review")
        )
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], context)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                    "--action", self.action, "--result", completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "test-strategy")
        self.assertEqual(resumed["improve_results"][self.action]["seed_result"]["evidence_refs"], refs)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

    def test_skill_assess_local_skill_bundle_survives_actual_child_cold_recovery(self):
        """A host-authored child contract retains concrete local-skill locators.

        Earlier navigation and the review judgments are synthetic fixtures.  The
        selected skill-assess parent, ephemeral callbacks, terminal receipt, and
        parent resume use the real ShipLoop/Improve CLIs.
        """
        index = self.repo / "SHIPLOOP.md"
        local_card = self.repo / "skills/release-evidence-triage/SKILL.md"
        input_contract = self.repo / "docs/release-contract.md"
        validation = self.repo / "test/test_release_evidence.py"
        index.write_text(
            "# Fixture repository index\n\n## Local skills\n\n"
            "- [Release evidence](skills/release-evidence-triage/SKILL.md)\n",
            encoding="utf-8",
        )
        local_card.parent.mkdir(parents=True)
        local_card.write_text("# Release evidence triage\n", encoding="utf-8")
        input_contract.parent.mkdir(parents=True)
        input_contract.write_text("# Release contract\n\n## current-input\n", encoding="utf-8")
        validation.parent.mkdir(exist_ok=True)
        validation.write_text("def test_current_contract():\n    pass\n", encoding="utf-8")
        local_skill_refs = [
            str(index) + "#local-skills",
            str(local_card) + "#release-evidence-triage",
            str(input_contract) + "#current-input",
            str(validation) + "::test_current_contract",
        ]
        self._start_parent_at_stage("skill-assess", local_skill_refs)
        self.assertEqual(navigator.current_stage(self.state), "skill-assess")
        parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("Current action: Improve the completed skill-assess result.", parent_packet)
        for locator in local_skill_refs:
            self.assertIn(locator, parent_packet)

        # This separate-process cold packet must tell the host to author the
        # transfer below. Resource transport alone would pass without that duty.
        handoff = " ".join(parent_packet.split())
        for clause in (
            "When this candidate selects, uses or changes a repository-local skill",
            "effective input/default sources",
            "into this child's existing contract/review notes before the first review",
            "current defaults and preserved older uses",
            "A no-fit decision needs its inspected sources and rationale",
            "a successful runtime receipt alone cannot prove skill use",
        ):
            self.assertIn(clause, handoff)

        base_context = self.child_context()
        manual_context = {
            "request": (
                "Host-authored fixture child contract for the selected local skill; "
                "the parent packet cannot create this semantic handoff.\n"
                + self.bound["contract_marker"]
            ),
            "scope": "Review only the frozen skill-assess evidence bundle and its retained locators.",
            "authority": "ShipLoop v3 no-commit authority: do not commit, merge, push, or broaden scope.",
            "environment": "Use the current fixture workspace and declared Python/Git commands only.",
            "resources": base_context["resources"][:6] + [
                {"purpose": "repository local skill index", "locator": local_skill_refs[0]},
                {"purpose": "selected repository local skill card", "locator": local_skill_refs[1]},
                {"purpose": "selected skill input contract", "locator": local_skill_refs[2]},
                {"purpose": "selected skill validation", "locator": local_skill_refs[3]},
            ],
        }
        contract = self.child_contract()
        contract["work"] = "Host-authored fixture review of a frozen local-skill selection."
        contract["context"] = manual_context
        start_raw, first = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)], contract
        )
        self.assertEqual(first["status"], "active")
        self.save_packet(start_raw)
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], manual_context)
        self.assertEqual(cold["context"]["resources"][-4:], manual_context["resources"][-4:])
        self.save_packet(cold_raw)

        _raw, second = self.done_ephemeral(
            cold, self.child_report("non-trivial", "unsatisfied", "allowed", "synthetic fixture finding")
        )
        _raw, third = self.done_ephemeral(
            second, self.child_report("trivial", "unsatisfied", "allowed", "synthetic first review")
        )
        terminal_raw, terminal = self.done_ephemeral(
            third, self.child_report("trivial", "satisfied", "allowed", "synthetic second review")
        )
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], manual_context)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "skill-validate")
        self.assertEqual(resumed["improve_results"][self.action]["seed_result"]["evidence_refs"], local_skill_refs)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        resumed_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("ShipLoop navigator | skill-validate |", resumed_packet)

    def test_active_stopped_and_missing_ephemeral_receipts_do_not_release_parent(self):
        completion, _receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        _raw, active = self.start_ephemeral_child()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        _raw, stopped = self.done_ephemeral(active, self.child_report("unresolved", "unknown", "blocked", "fixture blocker"))
        self.assertEqual(stopped["status"], "stopped")
        self.assertFalse(Path(stopped["state_file"]).exists())
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        self.packet_path.unlink()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_linked_completion_inbox_cannot_be_read_or_advance(self):
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        original = completion.with_name("elsewhere.md")
        completion.replace(original)
        completion.symlink_to(original)
        before = (self.run / "state.md").read_bytes()
        result = self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                             "--result", completion, status=2)
        self.assertIn("non-symlink", result.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_relative_skill_selection_remains_bound_for_cold_recovery(self):
        selected = self.base / "selected-improve.md"
        selected.symlink_to(CARD)
        run = self.base / "relative-selection-run"
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", run,
                    "--prompt", "Relative selection recovery fixture", "--improve-skill", selected.name)
        state = store.read_record(run / "state.md")
        action = state["action"]["id"]
        result_path = run / "inbox" / (action + ".md")
        store.write_record(result_path, {"outcome": "done", "summary": "Fixture producer"})
        self.invoke(CLI, "done", "--run-dir", run, "--action", action, "--result", result_path)
        before = (run / "state.md").read_bytes()
        cold = subprocess.run([sys.executable, "-B", str(CLI), "next", "--run-dir", str(run)], cwd="/",
                              text=True, capture_output=True, timeout=30, env=self.environment)
        self.assertEqual(cold.returncode, 0, cold.stderr)
        self.assertIn("--skill-card=" + str(selected), cold.stdout)
        bound = subprocess.run([sys.executable, "-B", str(CLI), "improve-bind", "--run-dir", str(run),
                                "--action", action, "--skill-card", state["improve_skill"]], cwd="/",
                               text=True, capture_output=True, timeout=30, env=self.environment)
        self.assertEqual(bound.returncode, 0, bound.stderr)
        self.assertNotEqual(before, (run / "state.md").read_bytes())
        skill = store.read_record(run / "state.md")["active_improve"]["skill"]
        self.assertEqual(skill["skill_card"], str(CARD.resolve()))
        self.assertEqual(skill["runtime_cli"], str(EPHEMERAL.resolve()))

    def test_workspace_return_waits_for_terminal_receipt_and_excludes_ephemeral_artifacts(self):
        source = self.base / "source"
        source.mkdir()
        for args in (("init", "-q"), ("config", "user.email", "fixture@example.invalid"),
                     ("config", "user.name", "Fixture"), ("config", "commit.gpgsign", "false"),
                     ("config", "core.hooksPath", "/dev/null")):
            subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True, env=self.environment)
        (source / "product.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "product.txt"], check=True, capture_output=True, env=self.environment)
        subprocess.run(["git", "-C", str(source), "commit", "-qm", "baseline"], check=True, capture_output=True, env=self.environment)
        workspace = self.base / "isolated"
        self.invoke(CLI, "workspace", "start", "--repo", source, "--workspace-root", workspace,
                    "--prompt", "Synthetic final return boundary fixture", "--improve-skill", CARD)
        self.repo, self.run = workspace / "worktree", workspace / "run"
        self.product_contract = self.product_test = self.repo / "product.txt"
        self._prepare_parent_evidence()
        state = store.read_record(self.run / "state.md")
        while navigator.current_stage(state) != "handoff":
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic setup"})
            state = navigator.finish_improve(state, action, {"summary": "Synthetic predecessor child"})
        navigator.save(self.run, state)
        self.action = navigator.current_action(state)["id"]
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, {"outcome": "done", "summary": "Final fixture handoff",
                                        "evidence_refs": self.parent_evidence_refs})
        self.invoke(CLI, "done", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(CARD)
        completion, receipt = self.completion_receipt()
        _raw, active = self.start_ephemeral_child()
        self.invoke(CLI, "workspace", "return", "--workspace-root", workspace, status=2)
        self.assertEqual((source / "product.txt").read_text(encoding="utf-8"), "baseline\n")
        (self.repo / "product.txt").write_text("final child reviewed candidate\n", encoding="utf-8")
        terminal_raw, terminal = self.finish_ephemeral(active)
        self.assertEqual(terminal["status"], "complete")
        before_import = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                    "--result", completion, status=2)
        self.assertEqual(before_import, (self.run / "state.md").read_bytes())
        self.invoke(CLI, "workspace", "plan-return", "--workspace-root", workspace)
        plan_path = workspace / "return-plan.md"
        plan = store.read_record(plan_path)
        self.assertTrue(any(".shiploop-improve" in Path(row["path"]).parts for row in plan["paths"]))
        for row in plan["paths"]:
            if ".shiploop-improve" in Path(row["path"]).parts:
                self.assertEqual(row["disposition"], "exclude")
            else:
                row["disposition"] = "keep"
        store.write_record(plan_path, plan)
        store.write_record(completion, dict(receipt, final_result={
            "outcome": "blocked", "summary": "Review finished but the delivery prerequisite is unresolved.",
        }))
        self.invoke(CLI, "workspace", "return", "--workspace-root", workspace, status=2)
        self.assertEqual((source / "product.txt").read_text(encoding="utf-8"), "baseline\n")
        store.write_record(completion, receipt)
        self.invoke(CLI, "workspace", "return", "--workspace-root", workspace)
        self.assertEqual((source / "product.txt").read_text(encoding="utf-8"), "final child reviewed candidate\n")
        self.assertFalse((source / ".shiploop-improve").exists())
        self.assertEqual(before_import, (self.run / "state.md").read_bytes())
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        self.assertEqual(store.read_record(self.run / "state.md")["status"], "done")
        self.assertEqual(receipt["summary"], "Runtime mechanics completed; no actual review claim.")


class LegacyImproveCliCompatibilityTests(ImproveCliFixture):
    def test_explicit_legacy_card_still_composes_durable_v2(self):
        card = self.legacy_card()
        run, action, binding = self.legacy_parent(card)
        runtime = card.parent / "runtime/until-loop/scripts/until-loop"
        self.assertEqual(binding["skill"]["runtime_cli"], str(runtime.resolve()))
        child = self.initialize_legacy_child(runtime, binding)
        state_path = self.repo / ".until-loop/state.json"
        before_cold_next = state_path.read_bytes()
        cold = self.invoke(runtime, "v2", "next", "--repo", self.repo)
        self.assertIn(binding["contract_marker"], cold.stdout)
        self.assertEqual(before_cold_next, state_path.read_bytes())
        root = self.repo / ".until-loop"
        for name in ("working.md", "review-a.md", "review-b.md", "checks.md"):
            (root / name).write_text("Synthetic legacy evidence: " + name + "\n", encoding="utf-8")
        completion = run / "inbox" / (action + "-improve.md")
        store.write_record(completion, {"summary": "Legacy runtime mechanics complete.",
                                        "review_refs": [str(root / "review-a.md"), str(root / "review-b.md")],
                                        "check_refs": [str(root / "checks.md")]})
        self.invoke(CLI, "improve-complete", "--run-dir", run, "--action", action, "--result", completion, status=2)
        self.invoke(runtime, "v2", "submit", "--repo", self.repo, "--action-id", child["action"]["id"])
        self.invoke(CLI, "improve-complete", "--run-dir", run, "--action", action, "--result", completion)
        record = store.read_record(run / "state.md")["improve_results"][action]
        self.assertEqual(record["runtime_phase"], "done")
        self.assertTrue((run / "improve" / action / "state.json").is_file())


if __name__ == "__main__":
    unittest.main()
