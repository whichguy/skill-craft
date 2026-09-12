#!/usr/bin/env python3
"""Focused pure-model tests for ShipLoop early observation checkpoints."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_knowledge as knowledge  # noqa: E402
import shiploop_observations as observations  # noqa: E402


FINGERPRINT = "a" * 64


def ticket(*, stage: str = "verify", step: str | None = "S1", revision: int = 0) -> dict:
    return observations.issue("RUN-PRIMARY-001", stage, step, revision)


def result(
    *,
    revision: int = 0,
    domain: str = "test-strategy",
    disposition: str = "informational",
    scope: list[str] | None = None,
    identifier: str = "OBS-FACT-001",
) -> dict:
    return {
        "summary": "A bounded early observation records a current fact without claiming verification.",
        "knowledge_revision": revision,
        "learnings": "The next action must read current knowledge instead of relying on a stale prompt.",
        "discoveries": [
            {
                "id": identifier,
                "domain": domain,
                "observation": "The isolated fixture exposes a current fact that affects its named scope.",
                "evidence": "The local fixture output records the observed condition.",
                "scope": ["S1"] if scope is None else scope,
                "disposition": disposition,
                "rationale": "The script must retain the fact before the parent action is resolved.",
                "revalidate": "Repeat the relevant check or review after the selected repair route completes.",
            }
        ],
    }


class ShipLoopObservationTests(unittest.TestCase):
    def prepared(self, raw: dict | None = None, *, issued: dict | None = None) -> dict:
        issued = ticket() if issued is None else issued
        raw = result(revision=issued["expected_knowledge_revision"]) if raw is None else raw
        ledger = knowledge.empty_ledger()
        return observations.build_checkpoint(
            ledger=ledger,
            previous_sha256=knowledge.sha256_text(knowledge.render(ledger)),
            ticket=issued,
            raw_result=raw,
            step_ids={"S1", "S2"},
            context_fingerprint=FINGERPRINT,
            recorded_at="2026-09-12T00:00:00Z",
        )

    def test_ticket_is_deterministic_and_binds_only_parent_action_and_revision(self) -> None:
        first = ticket(stage="review", step="S1", revision=3)
        same_identity_other_stage = ticket(stage="verify", step=None, revision=3)
        next_revision = ticket(stage="review", step="S1", revision=4)

        self.assertEqual(first["action"], same_identity_other_stage["action"])
        self.assertNotEqual(first["action"], next_revision["action"])
        self.assertEqual(observations.validate_ticket(first), first)
        forged = dict(first, action="OBS-" + "0" * 32)
        with self.assertRaisesRegex(observations.ObservationError, "script-issued"):
            observations.validate_ticket(forged)
        malformed_version = dict(first, version=True)
        with self.assertRaisesRegex(observations.ObservationError, "unsupported version"):
            observations.validate_ticket(malformed_version)

    def test_timestamp_prefixed_protocol_parent_action_is_valid(self) -> None:
        issued = observations.issue("20260912-000000-abc123", "verify", "S1", 0)
        source = observations.provenance(
            issued,
            context_fingerprint=FINGERPRINT,
            recorded_at="2026-09-12T00:00:00Z",
        )

        self.assertEqual(issued["parent_action"], "20260912-000000-abc123")
        self.assertEqual(knowledge._source(source), source)

    def test_checkpoint_uses_explicit_unverified_provenance_and_preserves_history(self) -> None:
        prepared = self.prepared()

        self.assertEqual(prepared["ledger"]["revision"], 1)
        self.assertEqual(prepared["source"]["kind"], "unverified-observation")
        self.assertEqual(prepared["source"]["verification"], "not-run")
        self.assertNotIn("check_action", prepared["source"])
        self.assertEqual(prepared["checkpoint"]["kind"], "unverified-observation")
        self.assertEqual(prepared["checkpoint"]["previous_knowledge_revision"], 0)
        self.assertEqual(prepared["checkpoint"]["knowledge_revision"], 1)
        self.assertEqual(
            prepared["ledger"]["entries"][0]["source"], prepared["source"]
        )
        self.assertEqual(knowledge._source(prepared["source"]), prepared["source"])

    def test_legacy_verified_provenance_remains_accepted_and_fake_early_check_is_rejected(self) -> None:
        legacy = {
            "action": "RUN-CARRY-001",
            "iteration": "ITER-001",
            "check_action": "CHECK-001",
            "worktree_fingerprint": FINGERPRINT,
            "step": "S1",
            "reported_by": "host",
            "recorded_at": "2026-09-12T00:00:00Z",
        }
        self.assertEqual(knowledge._source(legacy), legacy)

        early = observations.provenance(
            ticket(), context_fingerprint=FINGERPRINT, recorded_at="2026-09-12T00:00:00Z"
        )
        forged = dict(early, verification="passed")
        with self.assertRaisesRegex(knowledge.KnowledgeError, "must not claim"):
            knowledge._source(forged)
        forged = dict(early, check_action="CHECK-001")
        with self.assertRaisesRegex(knowledge.KnowledgeError, "provenance"):
            knowledge._source(forged)

    def test_exact_replay_is_accepted_and_changed_payload_is_rejected(self) -> None:
        issued = ticket()
        raw = result()
        prepared = self.prepared(raw, issued=issued)
        receipt = observations.receipt(issued, prepared)

        self.assertEqual(
            observations.assert_replay(receipt, issued, deepcopy(raw), route_value=prepared["route"]),
            receipt,
        )
        changed = deepcopy(raw)
        changed["learnings"] = "A changed replay must never rewrite the accepted observation."
        with self.assertRaisesRegex(observations.ObservationError, "conflicting replay"):
            observations.assert_replay(receipt, issued, changed, route_value=prepared["route"])

    def test_stale_revision_and_resolution_side_channel_are_rejected(self) -> None:
        stale = result(revision=1)
        with self.assertRaisesRegex(observations.ObservationError, "stale knowledge revision"):
            observations.validate_submission(stale, ticket(), step_ids={"S1"})

        resolution = result()
        resolution["resolutions"] = []
        with self.assertRaisesRegex(observations.ObservationError, "unknown or missing"):
            observations.validate_submission(resolution, ticket(), step_ids={"S1"})

    def test_current_repair_and_credential_routes_are_conservative(self) -> None:
        current = result(disposition="current-step-repair")
        normalized = observations.validate_submission(current, ticket(), step_ids={"S1"})
        self.assertEqual(observations.route(normalized, ticket())["kind"], "current-step-repair")

        wrong_scope = result(disposition="current-step-repair", scope=["S2"])
        normalized_wrong = observations.validate_submission(wrong_scope, ticket(), step_ids={"S1", "S2"})
        with self.assertRaisesRegex(observations.ObservationError, "active parent step"):
            observations.route(normalized_wrong, ticket())

        credential = result(domain="credential-availability", disposition="informational")
        with self.assertRaisesRegex(observations.ObservationError, "must pause"):
            observations.validate_submission(credential, ticket(), step_ids={"S1"})
        credential["discoveries"][0]["disposition"] = "pause"
        normalized_credential = observations.validate_submission(credential, ticket(), step_ids={"S1"})
        self.assertEqual(observations.route(normalized_credential, ticket())["kind"], "pause")

    def test_late_informational_observation_can_not_preserve_bound_proof(self) -> None:
        issued = ticket(stage="verify")
        normalized = observations.validate_submission(result(), issued, step_ids={"S1"})
        initial = observations.route(normalized, issued)
        protected = observations.protect_route(initial, issued, proof_bound=True)
        self.assertEqual(protected["kind"], "proof-repair")
        self.assertEqual(
            observations.protect_route(initial, issued, proof_bound=False),
            initial,
        )

    def test_previous_ledger_hash_and_receipt_route_are_bound(self) -> None:
        issued = ticket()
        with self.assertRaisesRegex(observations.ObservationError, "previous knowledge hash"):
            observations.build_checkpoint(
                ledger=knowledge.empty_ledger(),
                previous_sha256="0" * 64,
                ticket=issued,
                raw_result=result(),
                step_ids={"S1"},
                context_fingerprint=FINGERPRINT,
            )

        prepared = self.prepared(issued=issued)
        accepted = observations.receipt(issued, prepared)
        forged = deepcopy(accepted)
        forged["route"] = {"kind": "pause", "discovery_ids": ["OBS-FACT-001"]}
        with self.assertRaisesRegex(observations.ObservationError, "route"):
            observations.assert_replay(forged, issued, result(), route_value=prepared["route"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
