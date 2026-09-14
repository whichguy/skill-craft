#!/usr/bin/env python3
"""Public-CLI regression coverage for ShipLoop early observations."""

from __future__ import annotations

import copy
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_action_walk_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_observations_action_fixture", str(ACTION_WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {ACTION_WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


ACTION = load_action_walk_fixture()

import shiploop_knowledge as knowledge  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class ObservationProtocolTests(ACTION.ShipLoopActionWalkFixture):
    """Exercise the script-issued observation callback through fresh CLI calls."""

    def init_at_preflight(self) -> dict:
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--bound-plan",
            str(self.bound_plan),
            "--execution-mode",
            "legacy",
            "--prompt",
            "Exercise early current-knowledge observations without relying on host memory.",
        )
        state = self.state()
        self.assertEqual(state["stage"], "preflight")
        self.assertEqual(state.get("observation_protocol_version"), 1)
        self.assertEqual(state["knowledge_revision"], 0)
        return state

    def observation_context(self) -> dict:
        return self.read_context_record("observation")

    def observation_result(
        self,
        ticket: dict,
        *,
        identifier: str = "OBS-EARLY-001",
        domain: str = "documentation",
        disposition: str = "informational",
        scope: list[str] | None = None,
    ) -> dict:
        return {
            "summary": "A current bounded observation is recorded before the parent action completes.",
            "knowledge_revision": ticket["expected_knowledge_revision"],
            "learnings": "The next cold host must read current knowledge instead of treating this result as verification.",
            "discoveries": [
                {
                    "id": identifier,
                    "domain": domain,
                    "observation": "The observed local condition must remain visible to the next applicable action.",
                    "evidence": "A local fixture inspection recorded the condition without an external side effect.",
                    "scope": ["all"] if scope is None else scope,
                    "disposition": disposition,
                    "rationale": "The finding is durable operational context, not proof of a passing check.",
                    "revalidate": "Inspect the current condition again when the selected repair or test action runs.",
                }
            ],
        }

    def submit_observation(self, ticket: dict, payload: dict, *, label: str, code: int = 0):
        return self.cli(
            "done",
            "--action",
            ticket["action"],
            "--result",
            self.record(label, payload),
            code=code,
        )

    def test_preflight_observation_is_durable_replay_safe_and_never_completes_parent(self) -> None:
        before = self.init_at_preflight()
        ticket = self.observation_context()["ticket"]
        self.assertEqual(ticket["parent_action"], before["action"]["id"])
        self.assertEqual(ticket["expected_knowledge_revision"], 0)
        payload = self.observation_result(ticket)

        self.submit_observation(ticket, payload, label="preflight-observation")
        after = self.state()
        self.assertEqual(after["action"], before["action"])
        self.assertEqual(after["stage"], "preflight")
        self.assertEqual(after["completed_actions"], before["completed_actions"])
        self.assertEqual(after.get("last_completion"), before.get("last_completion"))
        self.assertEqual(after["knowledge_revision"], 1)
        self.assertEqual(after["knowledge_action_id"], ticket["action"])
        self.assertNotIn("observation_repair", after)

        ledger = knowledge.read_bound(self.run_dir, after)
        self.assertEqual(ledger["entries"][0]["id"], "OBS-EARLY-001")
        source = ledger["entries"][0]["source"]
        self.assertEqual(source["kind"], "unverified-observation")
        self.assertEqual(source["verification"], "not-run")
        self.assertEqual(source["parent_action"], before["action"]["id"])
        self.assertNotIn("check_action", source)

        checkpoint = store.read_record(self.run_dir / "knowledge-history" / f"{ticket['action']}.md")
        self.assertEqual(checkpoint["kind"], "unverified-observation")
        self.assertEqual(checkpoint["source"], source)
        receipt_path = self.run_dir / "observations" / f"{ticket['action']}.md"
        receipt = store.read_record(receipt_path)
        self.assertEqual(receipt["checkpoint"], f"knowledge-history/{ticket['action']}.md")
        self.assertEqual(receipt["knowledge_revision"], 1)
        self.assertEqual(
            after["observation_receipts"][ticket["action"]],
            hashlib.sha256(
                json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        )

        # A new CLI invocation rehydrates state from Markdown; exact side-action
        # replay is a no-op even though current knowledge has a newer revision.
        self.cli("next")
        state_before_replay = (self.run_dir / "state.md").read_bytes()
        self.submit_observation(ticket, copy.deepcopy(payload), label="preflight-observation-replay")
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)
        self.assertEqual(store.read_record(receipt_path), receipt)

        changed = copy.deepcopy(payload)
        changed["learnings"] = "A changed replay must not rewrite the accepted durable observation."
        rejected = self.submit_observation(
            ticket, changed, label="preflight-observation-conflict", code=2
        )
        self.assertIn("conflicting replay", rejected.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)

        current_ticket = self.observation_context()["ticket"]
        stale = self.observation_result(current_ticket, identifier="OBS-STALE-001")
        stale["knowledge_revision"] -= 1
        rejected = self.submit_observation(
            current_ticket, stale, label="preflight-observation-stale", code=2
        )
        self.assertIn("stale knowledge revision", rejected.stderr)

        secret = self.observation_result(current_ticket, identifier="OBS-SECRET-001")
        secret["discoveries"][0]["observation"] = "api_key=sk-proj-0123456789abcdef"
        rejected = self.submit_observation(
            current_ticket, secret, label="preflight-observation-secret", code=2
        )
        self.assertIn("credential", rejected.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)

    def test_preflight_permission_pause_is_rejected_before_any_durable_mutation(self) -> None:
        before = self.init_at_preflight()
        ticket = self.observation_context()["ticket"]
        payload = self.observation_result(
            ticket,
            identifier="OBS-CREDENTIAL-PAUSE-001",
            domain="credential-availability",
            disposition="pause",
        )
        state_before = (self.run_dir / "state.md").read_bytes()
        knowledge_before = (self.run_dir / "knowledge.md").read_bytes()
        history_before = (self.run_dir / "history.md").read_bytes()

        rejected = self.submit_observation(
            ticket, payload, label="preflight-credential-pause", code=2
        )
        self.assertIn("cannot resolve permission", rejected.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before)
        self.assertEqual((self.run_dir / "knowledge.md").read_bytes(), knowledge_before)
        self.assertEqual((self.run_dir / "history.md").read_bytes(), history_before)
        self.assertFalse(
            (self.run_dir / "knowledge-history" / f"{ticket['action']}.md").exists()
        )
        self.assertFalse((self.run_dir / "observations" / f"{ticket['action']}.md").exists())
        after = self.state()
        self.assertEqual(after["action"], before["action"])
        self.assertEqual(after["stage"], "preflight")
        self.assertNotIn("paused", after)
        self.assertNotIn("observation_repair", after)

        # The rejected side callback cannot strand the parent or require a
        # recovery path that does not exist at preflight.
        self.cli("next")
        self.complete(
            {
                "summary": "The committed baseline remains usable after the rejected side callback.",
                "baseline": "committed-head",
            },
            label="preflight-after-rejected-pause",
        )
        self.assertEqual(self.state()["stage"], "approach")

    def test_repair_availability_rejects_outer_quality_handoff_and_keeps_existing_routes(self) -> None:
        self.assertFalse(
            protocol.observation_repair_available(
                {"stage": "objective-review", "objective": {"kind": "quality"}}
            )
        )
        self.assertFalse(
            protocol.observation_repair_available(
                {"stage": "objective-review", "objective": {"kind": "handoff"}}
            )
        )
        self.assertFalse(protocol.observation_repair_available({"stage": "quality"}))
        self.assertFalse(protocol.observation_repair_available({"stage": "handoff"}))
        self.assertTrue(
            protocol.observation_repair_available(
                {"stage": "implement", "active_step": "S1"}
            )
        )
        self.assertTrue(
            protocol.observation_repair_available(
                {"stage": "objective-review", "objective": {"kind": "approach"}}
            )
        )

    def test_objective_observation_pauses_then_repair_rebinds_the_future_action(self) -> None:
        self.init_at_preflight()
        self.complete(
            {
                "summary": "The repository baseline is committed and available for a bounded approach decision.",
                "baseline": "committed-head",
            },
            label="preflight",
        )
        self.assertEqual(self.state()["stage"], "approach")
        self.complete(
            {
                "summary": "The approach candidate records the intended local delivery boundary.",
                "body": "# Approach\n\nUse scoped local steps with fresh checks and durable handoff records.\n",
            },
            label="approach-objective-start",
        )
        before = self.state()
        self.assertEqual(before["stage"], "objective-review")
        ticket = self.observation_context()["ticket"]
        payload = self.observation_result(ticket, identifier="OBS-OBJECTIVE-001")

        self.submit_observation(ticket, payload, label="objective-observation")
        paused = self.state()
        self.assertEqual(paused["action"], before["action"])
        self.assertEqual(paused["stage"], "objective-review")
        self.assertIn("observation_repair", paused)
        self.assertEqual(paused["observation_repair"]["parent_action"], before["action"]["id"])
        self.assertIn("New unverified knowledge", paused["paused"])

        rejected = self.cli("resume", code=2)
        self.assertIn("require repair", rejected.stderr)
        self.cli(
            "repair",
            "--action",
            before["action"]["id"],
            "--reason",
            "The new current observation requires a fresh approach objective review.",
        )
        rebound = self.state()
        self.assertEqual(rebound["stage"], "objective-review")
        self.assertNotEqual(rebound["action"]["id"], before["action"]["id"])
        self.assertNotIn("paused", rebound)
        self.assertNotIn("observation_repair", rebound)
        self.assertEqual(rebound["knowledge_revision"], paused["knowledge_revision"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
