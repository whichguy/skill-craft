#!/usr/bin/env python3
"""Focused durable-state tests for ShipLoop's managed Improve bridge."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_improve_bridge as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402
from shiploop_report import render_report  # noqa: E402


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


FIRST_PHASE = {
    "research": "research-review",
    "behavior": "behavior-review",
    "spec": "spec-review",
    "objective": "objective-review",
    "step-plan": "step-plan-review",
    "product": "review",
}


class ShipLoopImproveBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.count = 0

    def tearDown(self):
        self.temp.cleanup()

    def make_root(self, name="run"):
        root = self.root / name
        root.mkdir()
        (root / "prompt.md").write_text("Deliver the bounded candidate.\n", encoding="utf-8")
        policy = "# Improve policy\n\nBounded local review policy.\n"
        (root / "improve-policy.md").write_text(policy, encoding="utf-8")
        contract = (ROOT / "skills" / "shiploop" / "references" / "improve-managed-consumer.md").read_bytes()
        (root / bridge.CONTRACT_PATH).write_bytes(contract)
        return root, sha256(policy.encode("utf-8")), sha256(contract)

    def initial_state(self, root, policy_digest, contract_digest, profile):
        phase = FIRST_PHASE[profile]
        state = {
            "run_id": "run01",
            "phase": "validate-spec",
            "stage": phase,
            "action": {"id": "base01", "stage": phase},
            "completed_actions": {},
            "revision": 0,
            "repo_root": str(root),
            "improve_policy": {"sha256": policy_digest},
            "managed_improve_contract_sha256": contract_digest,
        }
        bridge.initialize(state)
        return state

    def transaction(self, root, state, event, writes=None, *, fault=None):
        durable, staged, deletes = bridge.prepare(root, state, event, writes or {}, [])
        staged["state.md"] = store.dumps(durable, "ShipLoop state")
        store.transaction(root, staged, deletes, fault=fault)
        return durable

    def start(self, profile="research", *, root=None, policy_digest=None, contract_digest=None):
        if root is None:
            root, policy_digest, contract_digest = self.make_root(profile)
        state = self.initial_state(root, policy_digest, contract_digest, profile)
        durable = self.transaction(root, state, "complete:base01")
        self.assertEqual(durable["stage"], bridge.STAGE)
        self.assertEqual(durable["action"]["id"], durable[bridge.STATE_KEY]["parent_action"])
        projected = bridge.project(root, store.read_record(root / "state.md"))
        self.assertEqual(projected["stage"], FIRST_PHASE[profile])
        self.assertEqual(projected["action"]["id"], "base01")
        return root, projected

    def start_product_with_active_step(self):
        root, policy, contract = self.make_root("product-scope")
        (root / "steps").mkdir()
        step = {
            "id": "S1",
            "worktree": "/worktrees/S1",
            "base_sha": "a" * 40,
            "mutable_iteration_note": "initial",
        }
        (root / "steps" / "S1.md").write_text(
            store.dumps(step, "active step receipt"), encoding="utf-8"
        )
        state = self.initial_state(root, policy, contract, "product")
        state["active_step"] = "S1"
        self.transaction(root, state, "complete:base01")
        return root, bridge.project(root, store.read_record(root / "state.md"))

    def flags_for(self, profile, phase, *, pause=False):
        if profile == "step-plan" and phase == "step-plan-review":
            return {"disposition": "not-required"}
        if profile == "product" and phase == "iteration-document":
            return {
                "documentation_disposition": "not-needed",
                "skill_disposition": "not-needed",
            }
        if profile == "product" and phase == "carry-forward":
            return {"disposition": "pause" if pause else "continue"}
        return {}

    def advance(self, root, state, *, kind="complete", pause=False, fault=None, evidence_files=None):
        """Simulate already-validated typed handler facts before persistence."""
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        profile = state[bridge.STATE_KEY]["profile"]
        phase = child["current_phase"]
        old_action = state["action"]["id"]
        self.count += 1
        proof = f"proofs/{old_action}.md"
        body = f"proof {self.count} for {phase}\n"
        result = {"summary": f"Completed managed {phase} action {old_action}."}
        result_digest = bridge._digest(result)
        writes = {
            proof: body,
            f"results/{old_action}.md": store.dumps(result, "ShipLoop result"),
        }
        evidence_refs = [proof]
        if evidence_files is not None:
            for relative, text in evidence_files.items():
                writes[relative] = text
                evidence_refs.append(relative)
        event = {
            "kind": kind,
            "phase": phase,
            "evidence_refs": evidence_refs,
            "flags": self.flags_for(profile, phase, pause=pause) if kind == "complete" else {},
        }
        if kind in bridge._INCOMPLETE:  # Checked by the controller; bridge only carries it.
            event["reason"] = "recorded prerequisite is unavailable"
        elif kind == "repair":
            event["reason"] = "recorded repair reopens the current review"
        elif phase.endswith("-commit") or phase == "commit":
            commit = f"{self.count:040x}"
            event.update(
                audit_commit=commit,
                completed_pass={
                    "id": f"pass{self.count}",
                    "outcome": "trivial",
                    "verified": True,
                    "commit": commit,
                    "evidence_ref": proof,
                },
                open_findings=[],
            )
        elif phase.endswith("-finalize") or phase == "final-verify":
            identity = sha256(f"identity-{self.count}".encode("utf-8"))
            event.update(
                output_identity={
                    "identity_digest": identity,
                    "artifact_digests": {proof: sha256(body.encode("utf-8"))},
                },
                fresh_evidence={
                    "binding_sha256": state[bridge.STATE_KEY]["binding_sha256"],
                    "action": old_action,
                    "identity_digest": identity,
                    "checks": [{"id": "check01", "result": "passed", "evidence_ref": proof}],
                    "evidence_ref": proof,
                    "result": "passed",
                },
            )

        controller = bridge._controller()
        _updated, route = controller.apply(child, event)
        state["completed_actions"][old_action] = result_digest
        state["last_completion"] = {
            "action": old_action,
            "stage": phase,
            "result_digest": result_digest,
        }
        state["revision"] += 1
        if route["status"] == "active":
            next_phase = route["current_phase"]
            state["stage"] = next_phase
            state["action"] = {"id": f"next{self.count:03d}", "stage": next_phase}
        else:
            state["stage"] = "after-managed"
            state["action"] = {"id": f"after{self.count:03d}", "stage": "after-managed"}
        bridge.set_evidence(state, event)
        self.transaction(root, state, f"complete:{phase}", writes, fault=fault)
        return bridge.project(root, store.read_record(root / "state.md")), event, proof

    def complete_final(self, root, state, *, check_ref, output_artifacts, before_prepare=None):
        """Submit one already-validated final callback with explicit live output bytes."""
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        phase = child["current_phase"]
        self.assertTrue(phase.endswith("-finalize") or phase == "final-verify")
        old_action = state["action"]["id"]
        self.count += 1
        proof = f"proofs/{old_action}.md"
        body = f"final proof {self.count} for {phase}\n"
        identity = sha256(f"final-identity-{self.count}".encode("utf-8"))
        result = {"summary": f"Completed managed {phase} action {old_action}."}
        result_digest = bridge._digest(result)
        event = {
            "kind": "complete",
            "phase": phase,
            "evidence_refs": [proof, check_ref],
            "flags": {},
            "output_identity": {
                "identity_digest": identity,
                "artifact_digests": dict(output_artifacts),
            },
            "fresh_evidence": {
                "binding_sha256": state[bridge.STATE_KEY]["binding_sha256"],
                "action": old_action,
                "identity_digest": identity,
                "checks": [{"id": "check01", "result": "passed", "evidence_ref": check_ref}],
                "evidence_ref": check_ref,
                "result": "passed",
            },
        }
        controller = bridge._controller()
        _updated, route = controller.apply(child, event)
        self.assertEqual(route["status"], "converged")
        state["completed_actions"][old_action] = result_digest
        state["last_completion"] = {
            "action": old_action,
            "stage": phase,
            "result_digest": result_digest,
        }
        state["revision"] += 1
        state["stage"] = "after-managed"
        state["action"] = {"id": f"after{self.count:03d}", "stage": "after-managed"}
        bridge.set_evidence(state, event)
        if before_prepare is not None:
            before_prepare()
        self.transaction(
            root,
            state,
            f"complete:{phase}",
            {proof: body, f"results/{old_action}.md": store.dumps(result, "ShipLoop result")},
        )
        return bridge.project(root, store.read_record(root / "state.md"))

    def converge_research(self, root, state, *, terminal_fault=None):
        while state.get(bridge.STATE_KEY):
            phase = state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"]
            state, _event, _proof = self.advance(
                root, state, fault=terminal_fault if phase == "research-finalize" else None
            )
        return state

    def test_legacy_is_inert_and_every_profile_starts_with_a_fixed_parent(self):
        legacy = {"run_id": "old", "stage": "review", "action": {"id": "old01", "stage": "review"}}
        self.assertFalse(bridge.enabled(legacy))
        self.assertEqual(bridge.prepare(self.root, legacy, "status"), (legacy, {}, []))

        for profile in FIRST_PHASE:
            root, policy, contract = self.make_root(profile)
            _root, state = self.start(profile, root=root, policy_digest=policy, contract_digest=contract)
            parent = store.read_record(root / "state.md")
            self.assertEqual(parent["stage"], bridge.STAGE)
            self.assertEqual(parent[bridge.STATE_KEY]["profile"], profile)
            state, _event, _proof = self.advance(root, state)
            self.assertEqual(store.read_record(root / "state.md")["stage"], bridge.STAGE)
            self.assertEqual(state[bridge.PRIVATE_KEY]["record"]["child"]["status"], "active")

    def test_start_fault_recovers_parent_and_child_together(self):
        root, policy, contract = self.make_root("fault-start")
        state = self.initial_state(root, policy, contract, "research")

        def fault(_where, _index):
            raise RuntimeError("simulated interruption")

        with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
            self.transaction(root, state, "complete:base01", fault=fault)
        self.assertTrue((root / "transaction.md").is_file())
        self.assertTrue(store.recover(root))
        durable = store.read_record(root / "state.md")
        self.assertEqual(durable["stage"], bridge.STAGE)
        receipt = root / durable[bridge.STATE_KEY]["receipt"]
        self.assertTrue(receipt.is_file())
        cold = bridge.project(root, durable)
        self.assertEqual(cold["stage"], "research-review")

    def test_repair_pause_and_same_child_resume_are_controller_owned(self):
        root, state = self.start("research")
        child_id = state[bridge.STATE_KEY]["id"]
        state, _event, _proof = self.advance(root, state, kind="repair")
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        self.assertEqual(child["current_phase"], "research-review")
        self.assertEqual(child["phase_records"][-1]["kind"], "repair")

        state, _event, proof = self.advance(root, state, kind="blocked")
        durable = store.read_record(root / "state.md")
        self.assertEqual(durable[bridge.STATE_KEY]["status"], "blocked")
        self.assertEqual(durable["stage"], bridge.STAGE)
        resumed = bridge.resume(
            root, state, reason="the recorded prerequisite is now available", evidence_refs=[proof]
        )
        self.assertTrue(resumed["resumed"])
        self.transaction(root, state, "resume")
        state = bridge.project(root, store.read_record(root / "state.md"))
        self.assertEqual(state[bridge.STATE_KEY]["id"], child_id)
        self.assertEqual(state[bridge.STATE_KEY]["status"], "active")
        self.assertEqual(state[bridge.PRIVATE_KEY]["record"]["child"]["phase_records"][-1]["kind"], "resume")

        # The ordinary CLI resume path has no separate child command.  When it
        # sees a durable incomplete child, ``prepare(..., "resume")`` records
        # the same controller-owned recovery from the interruption evidence.
        state, _event, _proof = self.advance(root, state, kind="blocked")
        self.transaction(root, state, "resume")
        state = bridge.project(root, store.read_record(root / "state.md"))
        self.assertEqual(state[bridge.STATE_KEY]["id"], child_id)
        self.assertEqual(state[bridge.PRIVATE_KEY]["record"]["child"]["phase_records"][-1]["kind"], "resume")

    def test_product_pause_is_preserved_in_the_child_packet(self):
        root, policy, contract = self.make_root("pause")
        _root, state = self.start("product", root=root, policy_digest=policy, contract_digest=contract)
        while state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"] != "carry-forward":
            state, _event, _proof = self.advance(root, state)
        state["paused"] = "carry-forward blocker requires a recorded resolution"
        state, _event, _proof = self.advance(root, state, pause=True)
        metadata = bridge.packet_metadata(state)
        self.assertTrue(metadata["paused"])
        self.assertEqual(state["stage"], "carry-forward")
        durable = store.read_record(root / "state.md")
        self.assertEqual(durable["stage"], bridge.STAGE)
        self.assertTrue(durable["paused"])

        # A normal CLI resume supplies no child event.  The controller clears
        # its own pause while preserving carry-forward as the required action.
        state.pop("paused")
        self.transaction(root, state, "resume")
        state = bridge.project(root, store.read_record(root / "state.md"))
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        self.assertEqual(child["current_phase"], "carry-forward")
        self.assertFalse(child["paused"])
        self.assertEqual(child["phase_records"][-1]["kind"], "resume")
        self.assertNotIn("paused", store.read_record(root / "state.md"))

    def test_required_step_plan_repair_resumes_at_disposition_only(self):
        root, state = self.start("step-plan")
        state["phase"] = "implement"
        state["stage"] = "step-plan-disposition"
        state["action"] = {"id": "stepdisposition01", "stage": "step-plan-disposition"}
        state["paused"] = "scope finding requires an explicit disposition"
        state["revision"] += 1
        self.transaction(
            root,
            state,
            "step-plan-repair",
            {"step-planning/loop/abandoned/disposition.md": store.dumps({"status": "abandoned"}, "step disposition repair")},
        )
        durable = store.read_record(root / "state.md")
        self.assertEqual(durable[bridge.STATE_KEY]["status"], "active")
        self.assertEqual(durable["paused"], "scope finding requires an explicit disposition")

        state = bridge.project(root, durable)
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        self.assertEqual(child["current_phase"], "step-plan-disposition")
        self.assertTrue(child["paused"])
        self.assertEqual(child["phase_records"][-1]["kind"], "repair")
        self.assertEqual(child["phase_records"][-1]["flags"], {"disposition": "required"})
        stale = copy.deepcopy(state)

        # Resume only clears the controller pause.  It cannot return to review
        # or revise until the required disposition produces a typed result.
        state.pop("paused")
        self.transaction(root, state, "resume")
        state = bridge.project(root, store.read_record(root / "state.md"))
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        self.assertEqual(child["current_phase"], "step-plan-disposition")
        self.assertFalse(child["paused"])
        self.assertEqual(child["phase_records"][-1]["kind"], "resume")
        with self.assertRaisesRegex(bridge.BridgeError, "changed since projection|projection is stale"):
            bridge.prepare(root, stale, "status")

        state, _event, _proof = self.advance(root, state)
        self.assertEqual(
            state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"],
            "step-plan-review",
        )

    def test_cli_shaped_repair_pause_resume_and_halt_need_no_completion_event(self):
        """The ordinary protocol commands do not call ``set_evidence``."""
        root, state = self.start("research")
        child_id = state[bridge.STATE_KEY]["id"]
        parent_action = state[bridge.STATE_KEY]["parent_action"]
        stale_callback = copy.deepcopy(state)

        # This matches the protocol repair shape: it replaces the typed
        # cursor and stages an abandoned receipt, but records no successful
        # completed action and supplies no bridge event.
        state["phase"] = "validate-spec"
        state["stage"] = "research-review"
        state["action"] = {"id": "repair01", "stage": "research-review"}
        state["revision"] += 1
        archive = "planning/research-iterations/repair01.md"
        self.transaction(
            root, state, "planning-repair",
            {archive: store.dumps({"status": "abandoned", "reason": "new evidence"}, "planning repair")},
        )
        state = bridge.project(root, store.read_record(root / "state.md"))
        child = state[bridge.PRIVATE_KEY]["record"]["child"]
        self.assertEqual(child["status"], "active")
        self.assertEqual(child["current_phase"], "research-review")
        self.assertEqual(child["phase_records"][-1]["kind"], "repair")
        self.assertTrue(all(ref.startswith("managed-improve/") for ref in child["phase_records"][-1]["evidence_refs"]))
        self.assertNotIn(parent_action, store.read_record(root / "state.md")["completed_actions"])
        with self.assertRaisesRegex(bridge.BridgeError, "status differs|changed since projection|projection is stale"):
            bridge.prepare(root, stale_callback, "status")

        # Generic pause only writes a reason in state.  It must become a
        # resumable controller interruption, leaving the top-level reason so
        # the existing CLI can authorize `resume` on a cold state.
        state["paused"] = "waiting for the bounded prerequisite"
        self.transaction(root, state, "pause")
        paused = store.read_record(root / "state.md")
        self.assertEqual(paused["paused"], "waiting for the bounded prerequisite")
        self.assertEqual(paused[bridge.STATE_KEY]["status"], "blocked")
        self.assertEqual(store.read_record(root / paused[bridge.STATE_KEY]["receipt"])["child"]["phase_records"][-1]["kind"], "blocked")

        state = bridge.project(root, paused)
        state.pop("paused")  # exactly what the CLI does before persist("resume")
        self.transaction(root, state, "resume")
        state = bridge.project(root, store.read_record(root / "state.md"))
        self.assertEqual(state[bridge.STATE_KEY]["id"], child_id)
        self.assertEqual(state[bridge.STATE_KEY]["status"], "active")
        self.assertNotIn("paused", store.read_record(root / "state.md"))
        self.assertEqual(state[bridge.PRIVATE_KEY]["record"]["child"]["phase_records"][-1]["kind"], "resume")

        # Halt must also be an explicit controller terminal, not a fabricated
        # parent completion or convergence certificate.
        state["phase"] = "halted"
        state["stage"] = "halted"
        state["action"] = {"id": "halt01", "stage": "halted"}
        state["halt_reason"] = "operator stopped the run"
        self.transaction(
            root, state, "halt",
            {"handoff.md": store.dumps({"status": "unfinished"}, "handoff")},
        )
        halted = store.read_record(root / "state.md")
        self.assertEqual(halted[bridge.STATE_KEY]["status"], "stopped")
        self.assertNotIn(parent_action, halted["completed_actions"])
        self.assertFalse((root / "managed-improve" / f"{child_id}-certificate.md").exists())

    def test_cli_shaped_step_plan_repair_and_cross_profile_replan_preserve_old_child(self):
        root, state = self.start("step-plan")
        old_child = state[bridge.STATE_KEY]["id"]
        old_parent_action = state[bridge.STATE_KEY]["parent_action"]
        state["phase"] = "implement"
        state["stage"] = "step-plan-review"
        state["action"] = {"id": "steprepair01", "stage": "step-plan-review"}
        state["revision"] += 1
        self.transaction(
            root, state, "step-plan-repair",
            {"step-planning/loop/abandoned/pass.md": store.dumps({"status": "abandoned"}, "step repair")},
        )
        state = bridge.project(root, store.read_record(root / "state.md"))
        self.assertEqual(state[bridge.PRIVATE_KEY]["record"]["child"]["phase_records"][-1]["kind"], "repair")
        self.assertNotIn(old_parent_action, store.read_record(root / "state.md")["completed_actions"])

        # A post-inner objective repair changes owner from objective to product.
        # The old child is left needs-replan and its recovery proof is linked
        # from the new product parent; it is never imported as a success.
        root, state = self.start("objective")
        stale_objective = copy.deepcopy(state)
        objective_binding = copy.deepcopy(state[bridge.STATE_KEY])
        state.pop("objective", None)
        state["phase"] = "implement"
        state["stage"] = "review"
        state["action"] = {"id": "productrepair01", "stage": "review"}
        state["revision"] += 1
        archive = "objectives/obj01/abandoned/pass01.md"
        durable = self.transaction(
            root, state, "post-inner-objective-repair",
            {archive: store.dumps({"status": "abandoned", "reason": "replan"}, "objective repair")},
        )
        recovery = durable[bridge.RECOVERY_KEY]
        self.assertEqual(recovery["from_child"], objective_binding["id"])
        self.assertEqual(recovery["from_parent_action"], objective_binding["parent_action"])
        self.assertEqual(recovery["status"], "needs-replan")
        self.assertEqual(recovery["reason"], "replan")
        self.assertTrue(recovery["to_child"])
        self.assertEqual(durable[bridge.STATE_KEY]["profile"], "product")
        old_record = store.read_record(root / objective_binding["receipt"])
        self.assertEqual(old_record["child"]["status"], "needs-replan")
        self.assertTrue((root / archive).is_file())
        self.assertNotIn(objective_binding["parent_action"], durable["completed_actions"])

        # The successor gets the immutable abandonment receipt and snapshots
        # in its bound input.  Packet metadata exposes that exact handoff only
        # to this destination child, including its non-circular source hash.
        successor = bridge.project(root, copy.deepcopy(durable))
        metadata = bridge.packet_metadata(successor)
        handoff = metadata["recovery_handoff"]
        self.assertEqual(handoff["from_child"], objective_binding["id"])
        self.assertEqual(handoff["to_child"], durable[bridge.STATE_KEY]["id"])
        self.assertEqual(handoff["source_receipt_sha256"], sha256((root / objective_binding["receipt"]).read_bytes()))
        successor_record = store.read_record(root / durable[bridge.STATE_KEY]["receipt"])
        self.assertIsNotNone(successor_record["input_identity"]["recovery"])
        self.assertEqual(successor_record["input_identity"]["recovery"]["recovery_sha256"], handoff["sha256"])

        evidence_path = root / handoff["evidence_refs"][0]
        evidence = evidence_path.read_bytes()
        evidence_path.write_bytes(b"tampered recovery evidence\n")
        with self.assertRaisesRegex(bridge.BridgeError, "recovery evidence changed|phase evidence changed"):
            bridge.project(root, copy.deepcopy(durable))
        evidence_path.write_bytes(evidence)

        source_path = root / objective_binding["receipt"]
        source = source_path.read_bytes()
        source_path.write_bytes(source + b"\n")
        with self.assertRaisesRegex(bridge.BridgeError, "recovery source receipt changed"):
            bridge.project(root, copy.deepcopy(durable))
        source_path.write_bytes(source)
        with self.assertRaisesRegex(bridge.BridgeError, "status differs|changed since projection|projection is stale"):
            bridge.prepare(root, stale_objective, "status")

        # A blocked recovery successor keeps the active handoff.  It may only
        # be discharged after this exact bound child converges and imports.
        successor, _event, _proof = self.advance(root, successor, kind="blocked")
        blocked = store.read_record(root / "state.md")
        self.assertEqual(blocked[bridge.RECOVERY_KEY]["to_child"], durable[bridge.STATE_KEY]["id"])
        self.transaction(root, successor, "resume")
        successor = bridge.project(root, store.read_record(root / "state.md"))
        successor_binding = copy.deepcopy(successor[bridge.STATE_KEY])
        while successor.get(bridge.STATE_KEY):
            successor, _event, _proof = self.advance(root, successor)
        imported = store.read_record(root / "state.md")
        self.assertNotIn(bridge.RECOVERY_KEY, imported)
        self.assertEqual(imported[bridge.IMPORT_KEY]["child_receipt"], successor_binding["receipt"])
        self.assertEqual(
            bridge.validate_imported_certificate(root, imported)["profile"], "product"
        )
        imported_successor = store.read_record(root / successor_binding["receipt"])
        self.assertEqual(
            imported_successor["input_identity"]["recovery"]["from_child"],
            objective_binding["id"],
        )

        # The consumed handoff cannot block a later, unrelated objective.
        ordinary = copy.deepcopy(imported)
        ordinary["stage"] = "objective-review"
        ordinary["action"] = {"id": "ordinaryobjective01", "stage": "objective-review"}
        ordinary["revision"] += 1
        next_parent = self.transaction(root, ordinary, "complete:ordinaryobjective01")
        self.assertNotIn(bridge.RECOVERY_KEY, next_parent)
        next_record = store.read_record(root / next_parent[bridge.STATE_KEY]["receipt"])
        self.assertIsNone(next_record["input_identity"]["recovery"])

    def test_planning_revisit_abandons_without_starting_or_certifying_a_child(self):
        root, state = self.start("research")
        previous = copy.deepcopy(state[bridge.STATE_KEY])
        state["phase"] = "validate-spec"
        state["stage"] = "survey"
        state["action"] = {"id": "revisit01", "stage": "survey"}
        state["revision"] += 1
        archive = "planning-history/revisit01/reason.md"
        durable = self.transaction(
            root, state, "planning-revisit:survey",
            {archive: store.dumps({"reason": "new research boundary", "to": "survey"}, "planning revisit")},
        )
        self.assertNotIn(bridge.STATE_KEY, durable)
        self.assertEqual(durable["stage"], "survey")
        recovery = durable[bridge.RECOVERY_KEY]
        self.assertEqual(recovery["from_child"], previous["id"])
        self.assertIsNone(recovery["to_child"])
        old_record = store.read_record(root / previous["receipt"])
        self.assertEqual(old_record["child"]["status"], "needs-replan")
        self.assertFalse((root / "managed-improve" / f"{previous['id']}-certificate.md").exists())

    def test_terminal_import_is_atomic_and_binds_bytes_and_evidence(self):
        root, state = self.start("research")
        while state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"] != "research-finalize":
            state, _event, _proof = self.advance(root, state)
        stale_terminal_callback = copy.deepcopy(state)

        def fault(_where, _index):
            raise RuntimeError("interrupt terminal import")

        with self.assertRaisesRegex(RuntimeError, "interrupt terminal import"):
            self.advance(root, state, fault=fault)
        self.assertTrue(store.recover(root))
        durable = store.read_record(root / "state.md")
        self.assertNotIn(bridge.STATE_KEY, durable)
        imported = durable[bridge.IMPORT_KEY]
        self.assertEqual(imported["certificate_sha256"], bridge.validate_imported_certificate(root, durable)["certificate_sha256"])
        changed_scope = copy.deepcopy(durable)
        changed_scope["run_id"] = "another-run"
        with self.assertRaisesRegex(bridge.BridgeError, "run scope changed"):
            bridge.validate_imported_certificate(root, changed_scope)
        self.assertEqual(
            sha256((root / imported["certificate"]).read_bytes()), imported["certificate_bytes_sha256"]
        )
        self.assertEqual(
            sha256((root / imported["child_receipt"]).read_bytes()), imported["child_receipt_sha256"]
        )
        parent_action = imported["parent_action"]
        parent_result = store.read_record(root / "results" / f"{parent_action}.md")
        parent_digest = bridge._digest(parent_result)
        self.assertEqual(durable["completed_actions"][parent_action], parent_digest)
        self.assertEqual(durable["last_completion"]["result_digest"], parent_digest)
        self.assertEqual(parent_result["status"], "converged")
        self.assertEqual(parent_result["managed_improve"]["certificate"], imported["certificate"])
        self.assertEqual(parent_result["managed_improve"]["certificate_sha256"], imported["certificate_sha256"])
        child_record = store.read_record(root / imported["child_receipt"])
        child_actions = bridge._action_rows_to_map(
            child_record["child"]["execution"]["completed_actions"],
            label="test child completion rows",
        )
        self.assertTrue(child_actions)
        for action_id, digest in child_actions.items():
            self.assertEqual(durable["completed_actions"][action_id], digest)
            self.assertEqual(
                bridge._digest(store.read_record(root / "results" / f"{action_id}.md")),
                digest,
            )
        with self.assertRaisesRegex(bridge.BridgeError, "changed since projection|projection is stale|status differs"):
            bridge.prepare(root, stale_terminal_callback, "status")

        evidence_path = next(iter(imported["evidence_manifest"]))
        original = (root / evidence_path).read_bytes()
        (root / evidence_path).write_bytes(b"changed after import\n")
        with self.assertRaisesRegex(bridge.BridgeError, "phase evidence changed|evidence or output identity changed"):
            bridge.validate_imported_certificate(root, durable)
        (root / evidence_path).write_bytes(original)

        certificate_path = root / imported["certificate"]
        certificate = certificate_path.read_bytes()
        certificate_path.write_text(store.dumps({"corrupt": True}, "corrupt certificate"), encoding="utf-8")
        with self.assertRaisesRegex(bridge.BridgeError, "certificate bytes changed"):
            bridge.validate_imported_certificate(root, durable)
        certificate_path.write_bytes(certificate)

        # Exercise the real renderer's ordinary completion bindings.  Other
        # terminal evidence is intentionally absent from this focused fixture.
        report_state = copy.deepcopy(durable)
        report_state.update(phase="done", stage="done", outer_check_action=parent_action)
        store.write_record(root / "state.md", report_state, title="ShipLoop state")
        _html, metadata = render_report(root)
        self.assertIn(f"results/{parent_action}.md", metadata["sources"])
        self.assertFalse(
            any(
                "does not match last completion" in error
                or "does not match its completed-action fingerprint" in error
                for error in metadata["evidence_errors"]
            )
        )

    def test_terminal_import_rejects_conflicting_child_or_parent_result_bindings(self):
        root, state = self.start("research")
        state, _event, _proof = self.advance(root, state)
        child_action = "base01"
        durable = store.read_record(root / "state.md")
        forged_parent = copy.deepcopy(durable)
        forged_parent["completed_actions"][child_action] = "0" * 64
        store.write_record(root / "state.md", forged_parent, title="ShipLoop state")
        with self.assertRaisesRegex(bridge.BridgeError, "child replay conflicts"):
            bridge.project(root, forged_parent)
        store.write_record(root / "state.md", durable, title="ShipLoop state")

        while state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"] != "research-finalize":
            state, _event, _proof = self.advance(root, state)
        parent_action = state[bridge.STATE_KEY]["parent_action"]
        parent_result_path = root / "results" / f"{parent_action}.md"
        parent_result_path.write_text(
            store.dumps({"summary": "Conflicting parent result."}, "ShipLoop result"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(bridge.BridgeError, "parent result path already contains different proof"):
            self.advance(root, state)

        ledger_root, policy, contract = self.make_root("research-ledger")
        _root, ledger_state = self.start(
            "research", root=ledger_root, policy_digest=policy, contract_digest=contract
        )
        while ledger_state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"] != "research-finalize":
            ledger_state, _event, _proof = self.advance(ledger_root, ledger_state)
        ledger_parent_action = ledger_state[bridge.STATE_KEY]["parent_action"]
        ledger_state[bridge.PRIVATE_KEY]["parent"]["completed_actions"][ledger_parent_action] = "0" * 64
        ledger_state["completed_actions"][ledger_parent_action] = "0" * 64
        with self.assertRaisesRegex(bridge.BridgeError, "parent action has a conflicting terminal import"):
            self.advance(ledger_root, ledger_state)

    def test_imported_objective_allows_a_successor_step_allocation(self):
        root, state = self.start("objective")
        while state.get(bridge.STATE_KEY):
            state, _event, _proof = self.advance(root, state)
        durable = store.read_record(root / "state.md")
        self.assertIsNone(durable.get("active_step"))

        # The completed objective's frozen input had no active step.  The
        # parent may now schedule S1; this is a successor allocation, not a
        # mutation of a still-active managed child.
        (root / "steps").mkdir()
        (root / "steps" / "S1.md").write_text(
            store.dumps(
                {
                    "id": "S1",
                    "run_id": durable["run_id"],
                    "status": "running",
                    "worktree": "/worktrees/S1",
                    "base_sha": "a" * 40,
                },
                "successor step receipt",
            ),
            encoding="utf-8",
        )
        allocated = copy.deepcopy(durable)
        allocated["active_step"] = "S1"
        allocated["stage"] = "step-plan"
        allocated["action"] = {"id": "allocate01", "stage": "step-plan"}
        certificate = bridge.validate_imported_certificate(root, allocated)
        self.assertEqual(certificate["profile"], "objective")

    def test_stale_receipts_policy_input_and_parent_overlay_fail_closed(self):
        root, state = self.start("research")
        stale = copy.deepcopy(state)
        state, _event, _proof = self.advance(root, state)
        with self.assertRaisesRegex(bridge.BridgeError, "changed since projection|projection is stale"):
            bridge.prepare(root, stale, "status")

        current = bridge.project(root, store.read_record(root / "state.md"))
        current["repo_root"] = "/tmp/foreign-repository"
        with self.assertRaisesRegex(bridge.BridgeError, "cannot change parent field repo_root"):
            bridge.prepare(root, current, "status")

        durable = store.read_record(root / "state.md")
        policy_path = root / "improve-policy.md"
        policy = policy_path.read_bytes()
        policy_path.write_bytes(b"different policy\n")
        with self.assertRaisesRegex(bridge.BridgeError, "policy digest changed"):
            bridge.project(root, durable)
        policy_path.write_bytes(policy)

        prompt_path = root / "prompt.md"
        prompt = prompt_path.read_bytes()
        prompt_path.write_bytes(b"different prompt\n")
        with self.assertRaisesRegex(bridge.BridgeError, "frozen requirement prompt.md digest changed"):
            bridge.project(root, durable)
        prompt_path.write_bytes(prompt)

        contract_path = root / bridge.CONTRACT_PATH
        contract = contract_path.read_bytes()
        contract_path.write_bytes(b"changed run contract\n")
        with self.assertRaisesRegex(bridge.BridgeError, "frozen requirement improve-managed-contract.md digest changed"):
            bridge.project(root, durable)
        contract_path.write_bytes(contract)

        bundled_read = bridge._bundled_read

        def stale_contract(relative, *, label):
            if relative == "references/improve-managed-consumer.md":
                return b"stale bundled contract\n"
            return bundled_read(relative, label=label)

        with mock.patch.object(bridge, "_bundled_read", side_effect=stale_contract):
            with self.assertRaisesRegex(bridge.BridgeError, "consumer contract differs from its pin"):
                bridge._controller()

    def test_product_active_step_scope_and_candidate_definition_are_bound(self):
        root, state = self.start_product_with_active_step()
        durable = store.read_record(root / "state.md")
        binding = durable[bridge.STATE_KEY]
        receipt_path = root / binding["receipt"]
        record = store.read_record(receipt_path)
        self.assertEqual(record["input_identity"]["scope"]["active_step"], "S1")
        self.assertEqual(record["input_identity"]["candidate"]["step_id"], "S1")

        # The parked state cannot be redirected to another step, whether an
        # adversary changes the cold parent or a projected callback does so.
        cold = copy.deepcopy(durable)
        cold["active_step"] = "S2"
        with self.assertRaisesRegex(bridge.BridgeError, "active step scope changed"):
            bridge.project(root, cold)
        projected = copy.deepcopy(state)
        projected["active_step"] = "S2"
        with self.assertRaisesRegex(bridge.BridgeError, "cannot change parent field active_step"):
            bridge.prepare(root, projected, "status")

        # Both the wrapper scope digest and the immutable candidate identity
        # are bound to this child receipt.
        original = receipt_path.read_bytes()
        corrupt = store.read_record(receipt_path)
        corrupt["scope_inventory_sha256"] = "0" * 64
        receipt_path.write_text(store.dumps(corrupt, bridge.CHILD_TITLE), encoding="utf-8")
        with self.assertRaisesRegex(bridge.BridgeError, "scope inventory differs"):
            bridge.project(root, copy.deepcopy(durable))
        receipt_path.write_bytes(original)

        corrupt = store.read_record(receipt_path)
        corrupt["input_identity"]["candidate"]["base_sha"] = "b" * 40
        receipt_path.write_text(store.dumps(corrupt, bridge.CHILD_TITLE), encoding="utf-8")
        with self.assertRaisesRegex(bridge.BridgeError, "input identity differs"):
            bridge.project(root, copy.deepcopy(durable))
        receipt_path.write_bytes(original)

        # Iteration content is intentionally mutable: only the stable running
        # definition (step ID, worktree, base SHA) is live-bound.
        step_path = root / "steps" / "S1.md"
        step = store.read_record(step_path)
        step["mutable_iteration_note"] = "changed during Improve"
        step_path.write_text(store.dumps(step, "active step receipt"), encoding="utf-8")
        bridge.project(root, copy.deepcopy(durable))
        step["base_sha"] = "b" * 40
        step_path.write_text(store.dumps(step, "active step receipt"), encoding="utf-8")
        with self.assertRaisesRegex(bridge.BridgeError, "live candidate base_sha changed"):
            bridge.project(root, copy.deepcopy(durable))

    def test_terminal_output_identity_rejects_candidate_drift_before_import(self):
        root, state = self.start("research")
        while state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"] != "research-finalize":
            state, _event, _proof = self.advance(root, state)
        final_action = state["action"]["id"]
        check_ref = f"checks/{final_action}.md"
        check_path = root / check_ref
        check_path.parent.mkdir()
        check_body = "fresh final check passed\n"
        check_path.write_text(check_body, encoding="utf-8")
        candidate_path = root / "candidate-output.md"
        candidate_path.write_text("checked candidate\n", encoding="utf-8")
        expected = sha256(candidate_path.read_bytes())

        with self.assertRaisesRegex(bridge.BridgeError, "output artifact candidate-output.md digest changed"):
            self.complete_final(
                root,
                state,
                check_ref=check_ref,
                output_artifacts={
                    "candidate-output.md": expected,
                    check_ref: sha256(check_body.encode("utf-8")),
                },
                before_prepare=lambda: candidate_path.write_text("changed after validation\n", encoding="utf-8"),
            )
        durable = store.read_record(root / "state.md")
        self.assertIn(bridge.STATE_KEY, durable)
        self.assertFalse((root / "managed-improve" / f"{durable[bridge.STATE_KEY]['id']}-certificate.md").exists())

    def test_evidence_snapshot_allows_historical_alias_reuse_but_final_check_stays_live(self):
        root, state = self.start("research")
        historical_action = state["action"]["id"]
        historical_check = f"checks/{historical_action}.md"
        state, _event, _proof = self.advance(
            root,
            state,
            evidence_files={historical_check: "accepted historical check\n"},
        )
        durable = store.read_record(root / "state.md")
        record = store.read_record(root / durable[bridge.STATE_KEY]["receipt"])
        accepted_refs = record["child"]["phase_records"][0]["evidence_refs"]
        self.assertNotIn(historical_check, accepted_refs)
        self.assertTrue(all(ref.startswith("managed-improve/") for ref in accepted_refs))

        # Historical source aliases can be reused because the bridge copied
        # their accepted bytes into namespaced evidence snapshots.
        (root / historical_check).write_text("reused alias with later bytes\n", encoding="utf-8")
        state = bridge.project(root, durable)
        while state[bridge.PRIVATE_KEY]["record"]["child"]["current_phase"] != "research-finalize":
            state, _event, _proof = self.advance(root, state)

        final_action = state["action"]["id"]
        final_check = f"checks/{final_action}.md"
        final_check_path = root / final_check
        final_check_body = "current final check passed\n"
        final_check_path.write_text(final_check_body, encoding="utf-8")
        self.complete_final(
            root,
            state,
            check_ref=final_check,
            output_artifacts={final_check: sha256(final_check_body.encode("utf-8"))},
        )
        imported = store.read_record(root / "state.md")
        self.assertIn(final_check, imported[bridge.IMPORT_KEY]["evidence_manifest"])
        final_check_path.write_text("tampered current check\n", encoding="utf-8")
        with self.assertRaisesRegex(bridge.BridgeError, "output artifact checks/.+ digest changed"):
            bridge.validate_imported_certificate(root, imported)

    def test_product_commit_accepts_only_the_staged_typed_cycle_receipt(self):
        root, state = self.start("product")
        state["active_step"] = "S1"
        commit = "a" * 40
        event = {
            "completed_pass": {
                "id": "pass1", "outcome": "trivial", "verified": True,
                "commit": commit, "evidence_ref": "steps/S1.md",
            }
        }
        staged = {
            "steps/S1.md": store.dumps(
                {
                    "improve_cycles": [
                        {
                            "id": "pass1", "outcome": "trivial", "primary_commit": commit,
                            "check_action": "check01",
                        }
                    ]
                },
                "staged product cycle",
            )
        }
        # The path intentionally does not exist on disk: this proves the
        # bridge validates the typed receipt destined for the same transaction.
        self.assertFalse((root / "steps" / "S1.md").exists())
        bridge._typed_pass_matches(root, state, event, staged)


if __name__ == "__main__":
    unittest.main(verbosity=2)
