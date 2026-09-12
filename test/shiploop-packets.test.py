#!/usr/bin/env python3
"""Cold-host acceptance tests for ShipLoop's thin action packet."""

from __future__ import annotations

import os
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-packets-")
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(ROOT / "test/fixtures/shiploop/backchain-leaf"),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Packet Test")
        self.git("config", "user.email", "packet@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")
        self.run_dir = self.repo / ".shiploop"

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def cli(self, *args, code=0):
        result = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            env=self.env,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def state(self):
        import shiploop_store as store

        return store.read_record(self.run_dir / "state.md")

    def result(self, name, value):
        import shiploop_store as store

        path = self.root / name
        store.write_record(path, value)
        return str(path)

    def packet(self, state):
        import shiploop_packets
        import shiploop_protocol

        core = SimpleNamespace(**runpy.run_path(str(CLI)))
        return shiploop_packets.render(core, self.run_dir, state, shiploop_protocol.__dict__)

    def test_initial_packet_has_cold_start_task_environment_schema_and_done_alias(self):
        packet = self.cli(
            "init", "--repo", str(self.repo), "--prompt", "Build a tested browser and API entrypoint"
        ).stdout
        state = self.state()
        action = state["action"]["id"]
        result_path = self.run_dir / "inbox" / f"{action}.md"

        for marker in (
            f"Action: {action}",
            "Stage: preflight",
            f"Worktree: {self.repo}",
            "Incoming prompt (exact):",
            "Environment: not frozen yet",
            "Lint oracle:",
            "Objective:",
            "Until:",
            "Continue while:",
            "Evidence required:",
            "Bounded context:",
            "Result template",
            "\"baseline\": \"committed-head\"",
            "When done:",
            "Call this when done:",
        ):
            self.assertIn(marker, packet)
        self.assertIn(f"--action {action}", packet)
        self.assertIn(f"--result {result_path}", packet)
        self.assertIn(f"done --run-dir {self.run_dir}", packet)
        self.assertNotIn("It's all complete.", packet)

    def test_last_accepted_action_explains_replay_and_current_recovery(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        first = self.state()["action"]["id"]
        payload = self.result(
            "preflight.md",
            {"summary": "Committed baseline inspected.", "baseline": "committed-head"},
        )
        after_first = self.cli("done", "--action", first, "--result", payload).stdout
        state = self.state()
        current = state["action"]["id"]
        self.assertNotEqual(first, current)
        self.assertIn(f"Last accepted: {first}", after_first)
        self.assertIn(f"Action: {current}", after_first)
        self.assertIn(f"done --run-dir {self.run_dir} --action {current}", after_first)

        revision = state["revision"]
        replay = self.cli("done", "--action", first, "--result", payload).stdout
        self.assertEqual(self.state()["revision"], revision)
        self.assertIn(f"Last accepted: {first}", replay)
        self.assertIn(f"Action: {current}", replay)

    def test_rejected_completion_keeps_the_action_and_prints_exact_recovery(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        before = self.state()
        action = before["action"]["id"]

        rejected = self.cli(
            "done",
            "--action",
            action,
            "--result",
            self.result("invalid-preflight.md", {"summary": "Baseline omitted."}),
            code=2,
        )

        after = self.state()
        self.assertEqual(after["action"], before["action"])
        self.assertEqual(after["revision"], before["revision"])
        self.assertIn(
            f"Recover the current durable action: python3 {CLI} next --run-dir {self.run_dir}",
            rejected.stderr,
        )

    def test_paused_legacy_and_missing_state_packets_do_not_offer_completion(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        state = self.state()

        paused = self.cli("pause", "--reason", "Need an authorized environment decision").stdout
        self.assertIn("Paused, unfinished:", paused)
        self.assertIn("Recovery:", paused)
        self.assertNotIn("When done:", paused)
        self.assertNotIn("Call this when done:", paused)
        self.assertNotIn("It's all complete.", paused)

        legacy = dict(state)
        legacy.pop("planning_protocol_version", None)
        legacy_packet = self.packet(legacy)
        self.assertIn("Legacy planning protocol", legacy_packet)
        self.assertIn("planning-upgrade", legacy_packet)
        self.assertNotIn("Call this when done:", legacy_packet)

        missing = dict(state)
        missing["action"] = {}
        missing_packet = self.packet(missing)
        self.assertIn("Blocked: authoritative state has no usable current action ID.", missing_packet)
        self.assertNotIn("When done:", missing_packet)
        self.assertNotIn("Call this when done:", missing_packet)

    def test_objective_packet_is_self_contained_and_uses_ten_body_history_gate(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        preflight = self.state()["action"]["id"]
        self.cli(
            "complete",
            "--action",
            preflight,
            "--result",
            self.result(
                "preflight.md",
                {"summary": "Committed baseline inspected.", "baseline": "committed-head"},
            ),
        )
        approach = self.state()["action"]["id"]
        objective_packet = self.cli(
            "complete",
            "--action",
            approach,
            "--result",
            self.result("approach.md", {"summary": "Approach drafted.", "body": "# Approach\nConcrete scope."}),
        ).stdout
        state = self.state()
        action = state["action"]["id"]
        self.assertEqual(state["stage"], "objective-review")
        for marker in (
            "Stage: objective-review",
            "Objective state (current only):",
            "Objective candidate and current pass only:",
            "--section objective",
            "History index (not review proof; enumerate current rows):",
            "History full-body proof for each index row N:",
            "--limit 10 --skip 0",
            "--limit 1 --skip N --full",
            "Objective-loop guidance: read only",
            "objective-loops.md#loop-contract",
            "objective-loops.md#review-rubric",
            "\"assessment\":",
            "\"history_assessment\":",
            "\"test_review\":",
            f"--action {action}",
            f"--result {self.run_dir / 'inbox' / f'{action}.md'}",
        ):
            self.assertIn(marker, objective_packet)
        self.assertNotIn("--limit 10 --skip 0 --full", objective_packet)
        self.assertIn("Call this when done:", objective_packet)

    def test_objective_packet_guidance_routes_only_to_existing_sections(self):
        import shiploop_packets
        import shiploop_protocol

        core = SimpleNamespace(REF_DIR=SCRIPTS.parent / "references")
        document = (core.REF_DIR / "objective-loops.md").read_text()
        headings = {
            "loop-contract": "Loop contract",
            "review-rubric": "Review rubric",
            "plan-and-apply": "Plan and apply",
            "checks-and-commits": "Checks and commits",
            "finalization-and-recovery": "Finalization and recovery",
        }
        for section, heading in headings.items():
            self.assertIn(f"## {heading}", document)
        for stage, sections in shiploop_protocol.OBJECTIVE_SECTIONS.items():
            guidance = "\n".join(
                shiploop_packets._guidance_lines(
                    core,
                    stage,
                    {"OBJECTIVE_SECTIONS": shiploop_protocol.OBJECTIVE_SECTIONS},
                )
            )
            self.assertIn("Objective-loop guidance: read only", guidance)
            for section in sections:
                self.assertIn(f"objective-loops.md#{section}", guidance)

    def test_coverage_objective_packet_exposes_the_corrective_replan_route(self):
        import shiploop_packets

        action = "coverage-objective"
        result = self.run_dir / "inbox" / f"{action}.md"
        lines = shiploop_packets._outer_objective_replan_lines(
            SimpleNamespace(PACKAGE_ROOT=SCRIPTS.parent),
            self.run_dir,
            action,
            {"objective_binding": {"kind": "coverage"}},
            result,
        )
        packet = "\n".join(lines)

        self.assertIn("do not patch this objective session", packet)
        self.assertIn("plan_decision:'revise'", packet)
        self.assertIn("complete plan, complete dag", packet)
        self.assertIn(
            f"replan --run-dir {self.run_dir} --action {action} --result {result}",
            packet,
        )
        self.assertNotIn("done --", packet)

    def test_contract_evidence_templates_bind_done_rows_to_real_test_ids(self):
        import shiploop_packets

        evidence = shiploop_packets._done_evidence(
            {
                "done_integrated": [
                    {
                        "id": "D-RESULT",
                        "produces": ["result"],
                        "evidence_method": "Run the result test.",
                        "completion": "integrated",
                    },
                    {
                        "id": "D-COMBINED",
                        "produces": ["result", "documentation"],
                        "evidence_method": "Inspect the combined result.",
                        "completion": "integrated",
                    },
                ],
                "done_deployed": [
                    {
                        "id": "D-DEPLOYED",
                        "produces": ["result"],
                        "evidence_method": "Probe the authorized deployment.",
                        "completion": "deployed",
                    }
                ],
                "tests": [
                    {
                        "id": "T-RESULT",
                        "produces": ["result"],
                        "expected_outcome": "The result passes.",
                    }
                ],
                "documentation": [],
            }
        )

        self.assertEqual(evidence["done"][0]["reference"], "check:T-RESULT")
        self.assertEqual(evidence["done"][0]["source"], "verify-record")
        self.assertEqual(evidence["done"][1]["source"], "manual-observation")
        self.assertNotIn("check:D-COMBINED", evidence["done"][1]["reference"])
        self.assertEqual(evidence["done"][2]["source"], "host-reported")

    def test_sequence_template_contains_a_valid_v1_step_contract(self):
        import shiploop_contracts
        import shiploop_packets

        template, notes = shiploop_packets._execution_template("sequence", {}, {})
        self.assertIsInstance(template, dict)
        self.assertTrue(notes)
        dag = template["dag"]

        self.assertEqual(dag["contract_version"], 1)
        self.assertEqual(shiploop_contracts.dag_gaps(dag, require_contract=True), [])
        self.assertEqual(
            shiploop_contracts.contract_for_step(dag["steps"][0])["objective"],
            dag["steps"][0]["statement"],
        )

    def test_knowledge_binding_accepts_the_protocol_scope_list(self):
        import shiploop_packets

        binding, error = shiploop_packets._knowledge_binding(
            self.run_dir,
            {"active_step": "S1", "knowledge_revision": 3},
            {
                "knowledge_context": lambda _root, _state: (
                    {
                        "obligations": [
                            {"status": "open"},
                            {"status": "scheduled"},
                        ]
                    },
                    ["all", "S1"],
                    "bounded current knowledge",
                )
            },
        )

        self.assertIsNone(error)
        self.assertEqual(binding["scope"], ["all", "S1"])
        self.assertEqual(binding["unmapped_obligations"], 1)
        self.assertEqual(binding["scheduled_obligations"], 1)

    def test_review_packets_do_not_offer_an_invalid_planning_check_command(self):
        import shiploop_packets
        import shiploop_planning

        core = SimpleNamespace(PACKAGE_ROOT=SCRIPTS.parent)
        api = {"planning": shiploop_planning}
        review = shiploop_packets._check_commands(
            core,
            self.run_dir,
            {"stage": "research-review"},
            api,
            "research-review-action",
            {},
        )
        verify = shiploop_packets._check_commands(
            core,
            self.run_dir,
            {"stage": "research-verify"},
            api,
            "research-verify-action",
            {},
        )

        self.assertEqual(review, [])
        self.assertTrue(any("planning-verify" in line for line in verify))

    def test_check_manifest_packet_has_a_valid_shape_and_exact_acceptance(self):
        import shiploop_evidence
        import shiploop_packets

        core = SimpleNamespace(REF_DIR=SCRIPTS.parent / "references")
        state = {"stage": "objective-verify"}
        info = {"objective_binding": {"kind": "approach"}}
        acceptance, error = shiploop_packets._check_manifest_acceptance(
            core,
            self.run_dir,
            state,
            {
                "objective_expected_acceptance": lambda _core, _root, _state, kind: [
                    f"objective {kind}"
                ]
            },
            info,
        )
        self.assertIsNone(error)
        self.assertEqual(acceptance, ["objective approach"])

        lines = shiploop_packets._check_manifest_lines(
            core,
            self.run_dir,
            state,
            {
                "objective_expected_acceptance": lambda _core, _root, _state, kind: [
                    f"objective {kind}"
                ]
            },
            info,
        )
        fence = lines.index("```shiploop-state")
        manifest = json.loads(lines[fence + 1])
        self.assertEqual(
            manifest["checks"][1]["acceptance"], ["objective approach"]
        )
        self.assertIn("#check-manifest-and-evidence", "\n".join(lines))
        self.assertIn("Never put a ShipLoop CLI invocation", "\n".join(lines))
        self.assertIn("same --run-dir", "\n".join(lines))
        for row in manifest["checks"]:
            row["argv"] = ["python3", "-c", "pass"]
        validated = shiploop_evidence.validate_manifest(
            manifest, acceptance,
        )
        self.assertEqual(
            validated["checks"][1]["acceptance"], ["objective approach"]
        )

    def test_commit_packets_supply_verifier_body_and_stage_local_learnings(self):
        import shiploop_evidence
        import shiploop_packets

        baseline = self.git("rev-parse", "HEAD")
        core = SimpleNamespace(PACKAGE_ROOT=SCRIPTS.parent)

        objective = {
            "id": "OBJ-P1",
            "git_baseline": baseline,
            "check_action": "objective-check",
            "review": {"learnings": "Objective review learning."},
            "plan": {"learnings": "Objective plan learning."},
            "apply": {"learnings": "Objective apply learning."},
        }
        planning = {
            "id": "PLAN-P1",
            "git_baseline": baseline,
            "check_action": "planning-check",
            "review": {"learnings": "Planning review learning."},
            "applied": {"learnings": "Planning apply learning."},
        }
        step_plan = {
            "id": "STEP-P1",
            "git_baseline": baseline,
            "check_action": "step-plan-check",
            "review": {"learnings": "Step-plan review learning."},
            "revise": {"learnings": "Step-plan revise learning."},
        }
        primary = {
            "id": "INNER-I1",
            "previous_sha": baseline,
            "check_action": "inner-check",
            "review": {"learnings": "Implementation review learning."},
            "plan_learnings": ["Nested plan learning."],
            "applied": {"learnings": "Implementation apply learning."},
            "carry_forward": {"learnings": "Carry-forward learning."},
        }
        cases = (
            (
                {"stage": "objective-commit"},
                {},
                {"objective_receipt": {"current_pass": objective}},
                "OBJ-P1",
                "Objective plan learning.",
                "Audit-commit constraints:",
            ),
            (
                {"stage": "research-commit"},
                {"planning_receipt": lambda _root, _state: ("research", {"current_iteration": planning})},
                {},
                "PLAN-P1",
                "Planning apply learning.",
                "Audit-commit constraints:",
            ),
            (
                {"stage": "step-plan-commit"},
                {},
                {"step_plan_receipt": {"current_pass": step_plan}},
                "STEP-P1",
                "Step-plan revise learning.",
                "Audit-commit constraints:",
            ),
            (
                {"stage": "commit"},
                {},
                {"receipt": {"iteration": primary}},
                "INNER-I1",
                "Nested plan learning.",
                "Primary-commit constraints:",
            ),
        )
        objective_body = None
        for state, api, info, iteration_id, learning, constraint in cases:
            lines, error = shiploop_packets._commit_packet_lines(
                core, self.run_dir, state, api, info
            )
            self.assertIsNone(error)
            packet = "\n".join(lines)
            self.assertIn(f"Authoritative iteration ID: {iteration_id}", packet)
            self.assertIn(f"Authoritative Git baseline: {baseline}", packet)
            self.assertIn(learning, packet)
            self.assertIn(constraint, packet)
            self.assertIn(f"ShipLoop-Iteration: {iteration_id}", packet)
            if iteration_id == "OBJ-P1":
                objective_body = packet.split("```text\n", 1)[1].rsplit("\n```", 1)[0]

        self.assertIsInstance(objective_body, str)
        concrete_body = objective_body.replace(
            "[replace with reviewed finding IDs and durable dispositions]",
            "F-001 was resolved in the objective candidate.",
        )
        self.git("commit", "--allow-empty", "-m", concrete_body)
        sha = self.git("rev-parse", "HEAD")
        validated = shiploop_evidence.validate_commit(
            self.repo, sha, baseline, "OBJ-P1"
        )
        self.assertEqual(validated["sha"], sha)

        oversized = "Long durable learning. " * 100
        long_objective = dict(objective)
        long_objective["review"] = {"learnings": oversized}
        long_lines, error = shiploop_packets._commit_packet_lines(
            core,
            self.run_dir,
            {"stage": "objective-commit"},
            {},
            {"objective_receipt": {"current_pass": long_objective}},
        )
        self.assertIsNone(error)
        long_packet = "\n".join(long_lines)
        self.assertIn("Required learnings are intentionally not truncated.", long_packet)
        self.assertIn("--section iteration", long_packet)
        self.assertNotIn(oversized, long_packet)
        self.assertIn("ShipLoop-Iteration: OBJ-P1", long_packet)

    def test_failed_checks_and_uncertified_terminal_never_claim_completion(self):
        import shiploop_packets
        import shiploop_store as store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        state = self.state()
        failed = dict(state)
        failed.update(phase="residual", stage="quality")
        failed["action"] = {"id": "failed-quality", "stage": "quality"}
        (self.run_dir / "checks").mkdir()
        store.write_record(
            self.run_dir / "checks/failed-quality.md",
            {
                "binding_error": "Bound candidate fingerprint changed after checks.",
                "results": {
                    "all_passed": False,
                    "content_changed": False,
                    "checks": [
                        {
                            "id": "lint-current",
                            "status": "timeout",
                            "exit": None,
                            "log_path": "/safe/logs/lint-current.log",
                        }
                    ],
                },
            },
        )
        failed_packet = self.packet(failed)
        self.assertIn("Checks currently FAIL", failed_packet)
        self.assertIn(
            f"Check diagnostics record: {self.run_dir / 'checks/failed-quality.md'}",
            failed_packet,
        )
        self.assertIn("lint-current: status='timeout'; exit=None; log=/safe/logs/lint-current.log", failed_packet)
        self.assertIn("Bound candidate fingerprint changed after checks.", failed_packet)
        self.assertNotIn("When done:", failed_packet)
        self.assertNotIn("Call this when done:", failed_packet)
        self.assertNotIn("It's all complete.", failed_packet)

        store.write_record(
            self.run_dir / "checks/binding-only.md",
            {
                "objective_passed": False,
                "binding_error": "Candidate identity changed after a passing command.",
                "results": {"all_passed": True, "content_changed": False},
            },
        )
        self.assertTrue(
            shiploop_packets._failed_check(
                self.run_dir, "binding-only", {"store": store}
            )
        )

        terminal = dict(state)
        terminal.update(phase="done", stage="done")
        terminal["action"] = {"id": "uncertified-terminal", "stage": "done"}
        terminal_packet = self.packet(terminal)
        self.assertIn("Terminal cursor is not evidence-complete", terminal_packet)
        self.assertIn("Recovery:", terminal_packet)
        self.assertNotIn("It's all complete.", terminal_packet)
        self.assertNotIn("Call this when done:", terminal_packet)


if __name__ == "__main__":
    unittest.main()
