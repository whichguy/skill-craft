#!/usr/bin/env python3
"""Protocol-v4 planning-reconciliation tests.

The stopped-child cases use the bundled ephemeral Until Loop runtime.  The
ordinary producer/Improve predecessors are synthetic so this stays focused on
the navigator's v4 boundary rather than testing the Improve algorithm again.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_planning_revision as revision  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


class InterruptedTransaction(RuntimeError):
    """Test-only fault used to leave one recoverable store transaction."""


class NavigatorV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-navigator-v4-")
        self.addCleanup(self.temp.cleanup)
        self.temp_root = Path(self.temp.name).resolve()
        self.repo = self.temp_root / "project"
        self.run = self.temp_root / "run"
        self.repo.mkdir()
        self.run.mkdir()
        self.skill = bridge.resolve_skill(str(ROOT / "skills" / "improve" / "SKILL.md"))

    def state(self, protocol_version: int = 4) -> dict:
        return navigator.new_state(
            str(self.repo.resolve()),
            "Reconcile a planning premise in a small isolated project.",
            protocol_version=protocol_version,
        )

    @staticmethod
    def result(stage: str, **extra: object) -> dict:
        return {
            "outcome": "done",
            "summary": f"Synthetic {stage} producer result.",
            "evidence_refs": [],
            **extra,
        }

    @staticmethod
    def synthetic_improve(stage: str) -> dict:
        return {
            "summary": f"Synthetic Improve result for {stage}.",
            "review_refs": [f"synthetic://review/{stage}/one", f"synthetic://review/{stage}/two"],
            "check_refs": [f"synthetic://check/{stage}"],
            "lessons": f"Keep the current conclusion from {stage}.",
        }

    def complete_synthetic(self, state: dict, *, extra: dict | None = None) -> dict:
        stage = navigator.current_stage(state)
        action = navigator.current_action(state)["id"]
        waiting = navigator.apply(state, action, self.result(stage, **(extra or {})))
        return navigator.finish_improve(waiting, action, self.synthetic_improve(stage))

    def at_plan(self, protocol_version: int = 4) -> dict:
        state = self.state(protocol_version)
        while navigator.current_stage(state) != "plan":
            state = self.complete_synthetic(state)
        return state

    def bound_plan_child(self, state: dict) -> tuple[dict, str, dict]:
        self.assertEqual(navigator.current_stage(state), "plan")
        return self.bound_current_child(state)

    def bound_current_child(self, state: dict) -> tuple[dict, str, dict]:
        stage = navigator.current_stage(state)
        action = navigator.current_action(state)["id"]
        waiting = navigator.apply(state, action, self.result(stage))
        binding = bridge.binding(
            waiting, action, stage, waiting["active_improve"]["seed_result"], self.skill,
        )
        waiting = copy.deepcopy(waiting)
        waiting["active_improve"] = binding
        navigator.validate(waiting)
        return waiting, action, binding

    def cold_bound_packet(self, state: dict, root: Path) -> tuple[dict, str, dict, str]:
        """Persist a bound child before reading its recovery packet."""
        waiting, action, binding = self.bound_current_child(state)
        navigator.save(root, waiting)
        cold = store.read_record(root / "state.md")
        return cold, action, binding, navigator.render(None, root, cold)

    def stopped_packet(self, binding: dict) -> str:
        contract = {
            "workspace": binding["workspace"],
            "work": "Review the provisional planning premise and preserve reconciliation evidence.",
            "exit_condition": "The planning premise and its evidence are coherent.",
            "repeat_condition": "Continue while an authorized planning issue remains.",
            "required_trivial_reviews": 2,
            "context": {
                "request": "Review this ShipLoop plan.\n" + binding["contract_marker"],
                "scope": "Only the provisional planning evidence and review notes.",
                "authority": "Do not commit, merge, push, or start a replacement child.",
                "environment": "Local isolated protocol test.",
                "resources": [],
            },
        }
        started = subprocess.run(
            [sys.executable, "-B", self.skill["runtime_cli"], "start"],
            input=json.dumps(contract), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=30,
        )
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        packet = json.loads(started.stdout)
        terminal = subprocess.run(
            packet["done_argv"],
            input=json.dumps({
                "classification": "unresolved",
                "exit_assessment": "unsatisfied",
                "continuation_assessment": "cancelled",
                "evidence": "An upstream planning premise remains unresolved.",
                "handoff": "Preserve the stopped packet and let the parent reconcile the premise.",
            }),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
        )
        self.assertEqual(terminal.returncode, 0, terminal.stdout + terminal.stderr)
        stopped = json.loads(terminal.stdout)
        self.assertEqual(stopped["status"], "stopped")
        self.assertFalse(Path(stopped["state_file"]).exists())
        packet_path = bridge.receipt_path(binding)
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(terminal.stdout, encoding="utf-8")
        return terminal.stdout

    def reconciliation_input(self, action: str, *, target: str = "research") -> tuple[dict, Path, Path]:
        evidence = self.repo / f"reconciliation-{action}.md"
        evidence.write_text("Observed a contradictory planning premise.\n", encoding="utf-8")
        receipt = {
            "summary": f"The {target} premise requires reconciliation.",
            "target": target,
            "evidence_refs": [str(evidence.resolve())],
        }
        path = self.run / "inbox" / f"{action}-reconcile.md"
        path.write_text(store.dumps(receipt, "Stopped Improve reconciliation receipt"), encoding="utf-8")
        return receipt, path, evidence

    def cli_reconcile(self, action: str, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable, "-B", str(SCRIPTS / "shiploop"), "improve-reconcile",
                "--run-dir", str(self.run), "--action", action, "--result", str(path),
            ],
            cwd=self.repo,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
        )

    def real_stopped_plan(self) -> tuple[dict, str, dict, Path, Path, dict]:
        waiting, action, binding = self.bound_plan_child(self.at_plan())
        navigator.save(self.run, waiting)
        self.stopped_packet(binding)
        receipt, path, evidence = self.reconciliation_input(action)
        return waiting, action, receipt, path, evidence, binding

    def synthetic_stopped_record(self, child: dict, action: str, receipt: dict) -> dict:
        source = "reconciliation-evidence.md"
        return {
            "version": 1,
            "binding_id": child["binding_id"],
            "workspace": child["workspace"],
            "action_id": action,
            "stage": "plan",
            "seed_result": copy.deepcopy(child["seed_result"]),
            "skill": copy.deepcopy(child["skill"]),
            "runtime_phase": "stopped",
            "identities": {
                "terminal_packet_sha256": "a" * 64,
                "context_sha256": "b" * 64,
                "last_report_sha256": "c" * 64,
                "evidence_sha256": {source: "d" * 64},
            },
            "evidence": [{
                "source": source,
                "archive": f"improve/{action}/evidence/01-{source}",
                "sha256": "d" * 64,
            }],
            "submission": copy.deepcopy(receipt),
            "receipt": {
                "summary": receipt["summary"],
                "target": receipt["target"],
                "evidence_refs": [source],
            },
            "stale_check_note": "Synthetic stopped receipt for navigator-only projection testing.",
        }

    def test_actual_stopped_cli_settlement_archives_and_replays_without_live_child_reads(self) -> None:
        _waiting, action, receipt, path, evidence, binding = self.real_stopped_plan()

        settled = self.cli_reconcile(action, path)
        self.assertEqual(settled.returncode, 0, settled.stdout + settled.stderr)
        state_path = self.run / "state.md"
        first_state = state_path.read_bytes()
        state = store.read_record(state_path)
        navigator.validate(state)
        self.assertEqual(navigator.current_stage(state), "research")
        self.assertIsNone(state["active_improve"])
        self.assertEqual(len(state["planning_reconciliations"]), 1)
        event = state["planning_reconciliations"][0]
        self.assertEqual(set(event), {
            "action", "target", "binding_id", "recorded_at", "clock_source", "receipt_sha256",
        })
        self.assertEqual(event["action"], action)
        self.assertEqual(event["target"], receipt["target"])
        record = state["improve_results"][action]
        receipt_archive = self.run / "improve" / action / "receipt.md"
        self.assertEqual(receipt_archive.read_text(encoding="utf-8"),
                         store.dumps(record, "ShipLoop standalone Improve receipt"))
        self.assertEqual(event["receipt_sha256"],
                         hashlib.sha256(receipt_archive.read_bytes()).hexdigest())
        revision.validate_archives(state, self.run)

        # Reconciliation replay consumes the identical parent submission, but
        # must never read the mutable child packet or evidence again.
        bridge.receipt_path(binding).write_text("not a runtime packet", encoding="utf-8")
        evidence.write_text("Changed after archival.\n", encoding="utf-8")
        replay = self.cli_reconcile(action, path)
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        self.assertEqual(state_path.read_bytes(), first_state)

        changed = dict(receipt, summary="A different reconciliation request.")
        path.write_text(store.dumps(changed, "Stopped Improve reconciliation receipt"), encoding="utf-8")
        rejected = self.cli_reconcile(action, path)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(state_path.read_bytes(), first_state)

    def test_stopped_settlement_transaction_rolls_forward_as_one_batch(self) -> None:
        waiting, action, _receipt, path, _evidence, _binding = self.real_stopped_plan()
        args = SimpleNamespace(command="improve-reconcile", action=action, result=str(path))
        actual_transaction = store.transaction

        def interrupt_after_first_target(root, writes, deletes=None, **_kwargs):
            def crash(_phase, _index):
                raise InterruptedTransaction("leave reconciliation transaction for recovery")

            return actual_transaction(root, writes, deletes, fault=crash)

        with mock.patch.object(navigator.store, "transaction", side_effect=interrupt_after_first_target):
            with self.assertRaisesRegex(InterruptedTransaction, "reconciliation transaction"):
                navigator.dispatch(None, self.run, waiting, args)
        self.assertTrue((self.run / "transaction.md").is_file())
        self.assertTrue(store.recover(self.run))
        self.assertFalse((self.run / "transaction.md").exists())
        recovered = store.read_record(self.run / "state.md")
        navigator.validate(recovered)
        revision.validate_archives(recovered, self.run)
        self.assertIn(action, recovered["improve_results"])
        self.assertTrue((self.run / "results" / f"{action}.md").is_file())

    def test_two_reconciliations_follow_history_order_even_when_clocks_reverse(self) -> None:
        first_waiting, first_action, first_child = self.bound_plan_child(self.at_plan())
        first_receipt = {
            "summary": "Research premise is unresolved.",
            "target": "research",
            "evidence_refs": [str(self.repo / "first-evidence.md")],
        }
        state = navigator.reconcile(
            first_waiting, first_action,
            self.synthetic_stopped_record(first_child, first_action, first_receipt), first_receipt,
        )
        for expected in ("research", "spec", "test-strategy"):
            self.assertEqual(navigator.current_stage(state), expected)
            state = self.complete_synthetic(state)
        second_waiting, second_action, second_child = self.bound_plan_child(state)
        second_receipt = {
            "summary": "Discovery premise is unresolved.",
            "target": "discovery",
            "evidence_refs": [str(self.repo / "second-evidence.md")],
        }
        state = navigator.reconcile(
            second_waiting, second_action,
            self.synthetic_stopped_record(second_child, second_action, second_receipt), second_receipt,
        )
        state["planning_reconciliations"][1]["recorded_at"] = "2000-01-01T00:00:00.000000Z"
        navigator.validate(state)
        self.assertEqual(
            [event["action"] for event in state["planning_reconciliations"]],
            [first_action, second_action],
        )
        self.assertEqual(navigator.current_stage(state), "discovery")
        current = revision.current_actions(state)
        self.assertNotIn((None, "discovery"), current)
        self.assertNotIn((None, "research"), current)
        self.assertNotIn((None, "plan"), current)
        self.assertIn((None, "intake"), current)

    def test_reconcile_matches_the_bound_workspace_by_canonical_identity(self) -> None:
        alias = self.temp_root / "project-alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        state = navigator.new_state(
            str(alias), "Reconcile a plan through a workspace alias.", protocol_version=4,
        )
        while navigator.current_stage(state) != "plan":
            state = self.complete_synthetic(state)
        waiting, action, child = self.bound_plan_child(state)
        receipt = {
            "summary": "The aliased planning premise requires reconciliation.",
            "target": "research",
            "evidence_refs": [str(self.repo / "alias-evidence.md")],
        }
        record = self.synthetic_stopped_record(child, action, receipt)
        record["workspace"] = str(self.repo.resolve())

        other = self.temp_root / "other-workspace"
        other.mkdir()
        mismatched = copy.deepcopy(record)
        mismatched["workspace"] = str(other)
        with self.assertRaisesRegex(navigator.NavigatorError, "does not match"):
            navigator.reconcile(waiting, action, mismatched, receipt)

        updated = navigator.reconcile(waiting, action, record, receipt)
        self.assertEqual(updated["improve_results"][action]["workspace"], str(self.repo.resolve()))
        self.assertEqual(navigator.current_stage(updated), "research")

    def test_reconcile_is_rejected_by_normal_success_paths_and_after_prepare(self) -> None:
        state = self.at_plan()
        action = navigator.current_action(state)["id"]
        reconcile_result = {
            "outcome": "reconcile",
            "summary": "A premise needs revision.",
            "evidence_refs": [str(self.repo / "evidence.md")],
            "reconciliation_target": "research",
        }
        with self.assertRaisesRegex(navigator.NavigatorError, "improve-reconcile"):
            navigator.apply(state, action, reconcile_result)
        with self.assertRaisesRegex(navigator.NavigatorError, "reconciliation_target"):
            navigator.apply(state, action, {
                "outcome": "done",
                "summary": "A normal result cannot carry a reconciliation target.",
                "evidence_refs": [],
                "reconciliation_target": "research",
            })
        waiting = navigator.apply(state, action, self.result("plan"))
        with self.assertRaisesRegex(navigator.NavigatorError, "improve-reconcile"):
            navigator.finish_improve(waiting, action, {"summary": "synthetic"}, reconcile_result)

        prepared = navigator.finish_improve(waiting, action, self.synthetic_improve("plan"))
        self.assertEqual(navigator.current_stage(prepared), "prepare")
        with self.assertRaisesRegex(navigator.NavigatorError, "before prepare"):
            navigator.reconcile(prepared, navigator.current_action(prepared)["id"], {}, {
                "summary": "Too late.",
                "target": "research",
                "evidence_refs": [str(self.repo / "evidence.md")],
            })

    def test_v4_packet_uses_stable_planning_locators_and_v3_shape_stays_exact(self) -> None:
        state = self.at_plan()
        root = self.run
        producer = navigator.render(None, root, state)
        notebook = self.repo / ".shiploop-improve" / state["run_id"] / "planning-investigation.md"
        self.assertIn(str(ROOT / "skills" / "shiploop" / "references" / "planning-experiments.md"), producer)
        self.assertIn(str(notebook), producer)

        waiting, action, _child = self.bound_plan_child(state)
        improve = navigator.render(None, root, waiting)
        self.assertIn(f"{action}-reconcile.md", improve)
        self.assertIn("collect or confirm the recorded native worker owner", improve)
        self.assertIn("do not duplicate the full parent packet", improve)
        self.assertIn("use the context-first opening as the compact planning summary", improve)
        self.assertIn("'Current context and desired improvements' first", improve)
        self.assertIn("improve-reconcile", improve)

        legacy = navigator.new_state(str(self.repo), "Keep v3 stable.", protocol_version=3)
        self.assertEqual(legacy["version"], navigator.STATE_VERSION)
        self.assertEqual(legacy["navigator_protocol_version"], 3)
        self.assertNotIn("planning_reconciliations", legacy)
        legacy = self.complete_synthetic(legacy)
        self.assertEqual(set(legacy["history"][0]), {
            "stage", "outcome", "summary", "workitem", "action",
        })

    def test_cold_v4_initial_plan_packet_declares_bounded_experiment_contract(self) -> None:
        state = self.at_plan()
        cold, action, binding, packet = self.cold_bound_packet(state, self.run)
        scratch = (
            Path(binding["workspace"]) / ".shiploop-improve" / ".experiments"
            / cold["run_id"] / action
        )
        packet_lower = packet.lower()

        self.assertEqual(navigator.current_stage(cold), "plan")
        self.assertIn("Planning experiment objective:", packet)
        self.assertIn("Planning experiment exit:", packet)
        self.assertIn("zero experiments", packet_lower)
        self.assertIn("sufficient evidence", packet_lower)
        self.assertIn("inconclusive", packet_lower)
        self.assertIn("remains unresolved", packet_lower)
        self.assertIn("existing qualifying reviews", packet_lower)
        self.assertIn("nested loop", packet_lower)
        self.assertIn("Planning scratch directory: " + str(scratch), packet)
        self.assertIn("frozen scope", packet_lower)
        self.assertIn("product integration", packet_lower)
        self.assertIn("decisions or decision-relevant evidence", packet_lower)
        self.assertIn("final_result", packet)
        self.assertIn("complete ordered work_items", packet)
        self.assertEqual(packet.count("Planning experiments guide:"), 1)
        self.assertEqual(packet.count("Planning investigation notebook:"), 1)
        self.assertIn("only this v4 initial plan child may use the printed parent-only improve-reconcile route after worker collection", packet)

    def test_planning_scratch_cannot_alias_runtime_action_directory(self) -> None:
        state = self.at_plan()
        state["action"]["id"] = "experiments"
        cold, action, binding, packet = self.cold_bound_packet(state, self.run)
        scratch_line = next(line for line in packet.splitlines()
                            if line.startswith("Planning scratch directory: "))
        scratch = Path(scratch_line.split(": ", 1)[1])
        runtime_root = bridge.receipt_path(binding).parent
        self.assertEqual(action, "experiments")
        self.assertEqual(scratch, self.repo / ".shiploop-improve" / ".experiments"
                         / cold["run_id"] / action)
        self.assertNotIn(runtime_root, scratch.parents)
        self.assertNotIn(scratch, runtime_root.parents)
        self.assertNotEqual(scratch, runtime_root)

    def test_v4_experiment_contract_is_limited_to_the_initial_plan_child(self) -> None:
        legacy_root = self.temp_root / "v3-plan"
        legacy_root.mkdir()
        _legacy, _action, _binding, legacy_packet = self.cold_bound_packet(
            self.at_plan(protocol_version=3), legacy_root,
        )

        other_v4 = self.state()
        while navigator.current_stage(other_v4) != "research":
            other_v4 = self.complete_synthetic(other_v4)
        other_root = self.temp_root / "v4-research"
        other_root.mkdir()
        _other, _action, _binding, other_packet = self.cold_bound_packet(other_v4, other_root)

        for packet in (legacy_packet, other_packet):
            self.assertNotIn("Planning experiment objective:", packet)
            self.assertNotIn("Planning experiment exit:", packet)
            self.assertNotIn("Planning scratch directory:", packet)
            self.assertNotIn("improve-reconcile", packet)

    def test_cold_reconciled_v4_plan_packet_lists_current_sources_and_revalidates_queue(self) -> None:
        waiting, action, _receipt, path, _evidence, _binding = self.real_stopped_plan()
        old_sources = revision.current_actions(waiting)
        settled = self.cli_reconcile(action, path)
        self.assertEqual(settled.returncode, 0, settled.stdout + settled.stderr)
        state = store.read_record(self.run / "state.md")
        while navigator.current_stage(state) != "plan":
            state = self.complete_synthetic(state)
        navigator.save(self.run, state)
        cold = store.read_record(self.run / "state.md")
        current = revision.current_actions(cold)
        packet = navigator.render(None, self.run, cold)

        self.assertEqual(navigator.current_stage(cold), "plan")
        for stage in ("intake", "discovery", "research", "spec", "test-strategy"):
            self.assertIn(current[(None, stage)], packet)
        self.assertIn("Current planning sources:", packet)
        self.assertIn("revalidate the current work-item queue", packet.lower())
        sources = packet.split("Current planning sources:", 1)[1].split(
            "Planning experiments guide:", 1,
        )[0]
        for stage in ("research", "spec", "test-strategy"):
            self.assertNotIn(old_sources[(None, stage)], sources)
            self.assertIn(str(self.run / "results" / (current[(None, stage)] + ".md")), sources)
        self.assertIn(str(self.run / "improve" / action / "receipt.md"), sources)

    def test_v3_active_plan_rejects_reconcile_and_keeps_persisted_packet_readable(self) -> None:
        state = self.at_plan(protocol_version=3)
        action = navigator.current_action(state)["id"]
        waiting = navigator.apply(state, action, self.result("plan"))
        receipt = {
            "summary": "This v3 child cannot request a reconciliation route.",
            "target": "research",
            "evidence_refs": [str(self.repo / "v3-evidence.md")],
        }
        with self.assertRaisesRegex(navigator.NavigatorError, "protocol 4"):
            navigator.reconcile(waiting, action, {}, receipt)

        navigator.save(self.run, waiting)
        before = (self.run / "state.md").read_bytes()
        packet = navigator.render(None, self.run, store.read_record(self.run / "state.md"))
        self.assertIn("Current action: Improve the completed plan result.", packet)
        input_path = self.run / "inbox" / f"{action}-reconcile.md"
        input_path.write_text(store.dumps(receipt, "Stopped Improve reconciliation receipt"), encoding="utf-8")
        rejected = self.cli_reconcile(action, input_path)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("improve-reconcile requires navigator protocol 4", rejected.stderr)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        navigator.render(None, self.run, store.read_record(self.run / "state.md"))

    def test_archive_reader_rejects_post_open_substitution(self) -> None:
        archive = self.run / "improve" / "action" / "receipt.md"
        archive.parent.mkdir(parents=True)
        archive.write_text("original archive bytes", encoding="utf-8")
        replacement = self.run / "replacement.md"
        replacement.write_text("substituted archive bytes", encoding="utf-8")
        original_open = revision.os.open

        def open_then_substitute(path, flags, *args, **kwargs):
            descriptor = original_open(path, flags, *args, **kwargs)
            if path == "receipt.md" and kwargs.get("dir_fd") is not None:
                archive.unlink()
                replacement.replace(archive)
            return descriptor

        with mock.patch.object(revision.os, "open", side_effect=open_then_substitute):
            with self.assertRaisesRegex(
                revision.PlanningRevisionError,
                "changed while it was read|must be a regular single-link file",
            ):
                revision._regular_file(self.run, "improve/action/receipt.md", "test archive")

    def test_cli_defaults_to_v3_and_accepts_explicit_v4(self) -> None:
        self.assertEqual(navigator.LATEST_PROTOCOL_VERSION, 3)
        self.assertEqual(navigator.MAX_SUPPORTED_PROTOCOL_VERSION, 4)

        def initialize(name: str, version: int | None) -> dict:
            run = self.temp_root / name
            argv = [
                sys.executable, "-B", str(SCRIPTS / "shiploop"), "init",
                "--repo", str(self.repo), "--run-dir", str(run),
                "--prompt", "Initialize a protocol selection fixture.",
            ]
            if version is not None:
                argv.extend(["--navigator-version", str(version)])
            completed = subprocess.run(
                argv, cwd=self.repo, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            return store.read_record(run / "state.md")

        default = initialize("default-v3", None)
        explicit = initialize("explicit-v4", 4)
        self.assertEqual(default["navigator_protocol_version"], 3)
        self.assertNotIn("planning_reconciliations", default)
        self.assertEqual(explicit["navigator_protocol_version"], 4)
        self.assertEqual(explicit["planning_reconciliations"], [])

    def test_projection_keeps_v3_latest_done_and_accepts_missing_synthetic_workitem(self) -> None:
        old_history = {
            "navigator_protocol_version": 3,
            "history": [
                {"action": "old", "stage": "research", "outcome": "done", "workitem": None},
                {"action": "new", "stage": "research", "outcome": "done"},
            ],
            "accepted": {"old": {}, "new": {}},
        }
        self.assertEqual(revision.current_actions(old_history)[(None, "research")], "new")


if __name__ == "__main__":
    unittest.main(verbosity=2)
