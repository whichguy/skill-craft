#!/usr/bin/env python3
"""Focused pure-model tests for ShipLoop outer-work obligations."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_outer_work as outer_work  # noqa: E402
import shiploop_store as store  # noqa: E402


def provenance(*, stage: str = "verify", step: str | None = "S1") -> dict:
    return {
        "parent_action": "A-INNER-001",
        "parent_step": step,
        "parent_stage": stage,
    }


def request(
    *,
    request_id: str = "OWR-001",
    expected_revision: int = 0,
    required_action: str = "Obtain the release owner's explicit approval before publication.",
    target_stage: str = "quality",
    entry_id: str = "OW-RELEASE-001",
    dedupe_key: str = "release-owner-approval",
) -> dict:
    return {
        "request_id": request_id,
        "expected_revision": expected_revision,
        "entry_id": entry_id,
        "dedupe_key": dedupe_key,
        "required_action": required_action,
        "target_stage": target_stage,
        "target_alias": "production-release",
        "prerequisites": [
            "The candidate revision remains the reviewed and verified revision.",
            "The release owner has the current quality evidence.",
        ],
        "expected_outcome": "The release owner records whether publication may proceed.",
        "evidence": "Current quality report and the bound candidate revision are available for review.",
        "authority_limitations": "This journal does not authorize publication or deployment; the release owner must approve it separately.",
        "rationale": "Production publication is outside the inner implementation authority.",
    }


class OuterWorkTests(unittest.TestCase):
    def append(self, ledger: dict, value: dict, *, stage: str = "verify"):
        return outer_work.append(ledger, value, provenance(stage=stage))

    def test_empty_record_renders_as_one_markdown_authoritative_ledger(self) -> None:
        ledger = outer_work.empty()

        self.assertEqual(ledger["revision"], 0)
        self.assertEqual(ledger["events"], [])
        self.assertEqual(ledger["entries"], [])
        self.assertEqual(outer_work.validate(ledger), ledger)
        rendered = outer_work.render(ledger)
        self.assertIn("ShipLoop outer work", rendered)
        self.assertEqual(store.loads(rendered), ledger)

    def test_ledger_version_must_be_the_exact_supported_integer(self) -> None:
        for version in (True, 1.0, "1", 2):
            with self.subTest(version=version):
                ledger = outer_work.empty()
                ledger["version"] = version
                with self.assertRaisesRegex(outer_work.OuterWorkError, "unsupported version"):
                    outer_work.validate(ledger)

    def test_append_creates_a_planned_effective_entry_and_stage_order_is_monotonic(
        self,
    ) -> None:
        ledger, receipt = self.append(outer_work.empty(), request())

        self.assertEqual(receipt["outcome"], "created")
        self.assertTrue(receipt["obligation_created"])
        self.assertEqual(ledger["revision"], 1)
        self.assertEqual(len(ledger["events"]), 1)
        self.assertEqual(ledger["entries"][0]["status"], "planned")
        self.assertEqual(
            [row["id"] for row in outer_work.pending_for_stage(ledger, "quality")],
            ["OW-RELEASE-001"],
        )
        self.assertEqual(
            [row["id"] for row in outer_work.pending_for_stage(ledger, "publish")],
            ["OW-RELEASE-001"],
        )
        self.assertEqual(
            [row["id"] for row in outer_work.pending_for_stage(ledger, "handoff")],
            ["OW-RELEASE-001"],
        )

    def test_publish_work_does_not_block_quality_but_blocks_publish_and_handoff(
        self,
    ) -> None:
        ledger, _ = self.append(
            outer_work.empty(),
            request(target_stage="publish", entry_id="OW-PUBLISH-001", dedupe_key="publish-approval"),
        )

        self.assertEqual(outer_work.pending_for_stage(ledger, "quality"), [])
        self.assertEqual(
            [row["id"] for row in outer_work.pending_for_stage(ledger, "publish")],
            ["OW-PUBLISH-001"],
        )
        self.assertEqual(
            [row["id"] for row in outer_work.pending_for_stage(ledger, "handoff")],
            ["OW-PUBLISH-001"],
        )

    def test_exact_request_replay_is_idempotent_but_changed_replay_is_rejected(self) -> None:
        first_request = request()
        ledger, first_receipt = self.append(outer_work.empty(), first_request)

        replayed, replay_receipt = self.append(ledger, deepcopy(first_request))
        self.assertEqual(replayed, ledger)
        self.assertEqual(replay_receipt, first_receipt)

        changed = deepcopy(first_request)
        changed["rationale"] = "A changed request must not reuse an accepted request receipt."
        with self.assertRaisesRegex(outer_work.OuterWorkError, "request_id"):
            self.append(ledger, changed)

    def test_semantic_duplicate_gets_a_receipt_without_a_second_obligation(self) -> None:
        ledger, _ = self.append(outer_work.empty(), request())
        duplicate = request(request_id="OWR-002", expected_revision=ledger["revision"])

        ledger, receipt = self.append(ledger, duplicate, stage="planning")
        self.assertEqual(receipt["outcome"], "duplicate")
        self.assertFalse(receipt["obligation_created"])
        self.assertEqual(ledger["revision"], 2)
        self.assertEqual(len(ledger["events"]), 2)
        self.assertEqual(len(ledger["entries"]), 1)
        self.assertEqual(ledger["entries"][0]["status"], "planned")

    def test_advertised_event_cap_and_post_twenty_five_resolution_stay_valid(self) -> None:
        capped = outer_work.empty()
        for number in range(1, outer_work.MAX_EVENTS + 1):
            capped, _ = self.append(
                capped,
                request(
                    request_id=f"OWR-CAP-{number:03d}",
                    expected_revision=capped["revision"],
                ),
            )
        self.assertEqual(capped["revision"], outer_work.MAX_EVENTS)
        self.assertEqual(len(capped["events"]), outer_work.MAX_EVENTS)
        self.assertEqual(
            [event["revision"] for event in capped["events"]],
            list(range(1, outer_work.MAX_EVENTS + 1)),
        )
        self.assertEqual(outer_work.validate(capped), capped)
        with self.assertRaisesRegex(outer_work.OuterWorkError, "events exceed"):
            self.append(
                capped,
                request(
                    request_id="OWR-CAP-OVERFLOW",
                    expected_revision=capped["revision"],
                ),
            )

        after_twenty_five = outer_work.empty()
        for number in range(1, 26):
            after_twenty_five, _ = self.append(
                after_twenty_five,
                request(
                    request_id=f"OWR-RESOLVE-{number:03d}",
                    expected_revision=after_twenty_five["revision"],
                ),
            )
        resolved = outer_work.resolve(
            after_twenty_five,
            {
                "entry_id": "OW-RELEASE-001",
                "expected_revision": after_twenty_five["revision"],
                "evidence": "The release owner recorded the quality decision against the candidate revision.",
                "reason": "The required approval was obtained for the reviewed candidate.",
            },
            provenance(stage="quality", step=None),
        )
        self.assertEqual(resolved["revision"], 26)
        self.assertEqual(resolved["entries"][0]["status"], "resolved")
        self.assertEqual(resolved["entries"][0]["resolution"]["resolved_revision"], 26)

    def test_new_details_reopen_a_resolved_entry_under_its_stable_dedupe_key(
        self,
    ) -> None:
        ledger, _ = self.append(outer_work.empty(), request())
        ledger = outer_work.resolve(
            ledger,
            {
                "entry_id": "OW-RELEASE-001",
                "expected_revision": ledger["revision"],
                "evidence": "The release owner recorded the quality decision against the candidate revision.",
                "reason": "The required approval was obtained for the reviewed candidate.",
            },
            provenance(stage="quality", step=None),
        )
        self.assertEqual(ledger["entries"][0]["status"], "resolved")
        self.assertIn("resolution", ledger["entries"][0])

        revised = request(request_id="OWR-002", expected_revision=ledger["revision"])
        revised["expected_outcome"] = "The release owner records a fresh decision for the revised candidate."
        ledger, receipt = self.append(ledger, revised)

        self.assertEqual(receipt["outcome"], "reopened")
        self.assertEqual(ledger["entries"][0]["status"], "planned")
        self.assertNotIn("resolution", ledger["entries"][0])
        self.assertEqual(
            [row["id"] for row in outer_work.pending_for_stage(ledger, "quality")],
            ["OW-RELEASE-001"],
        )

    def test_exact_duplicate_does_not_reopen_a_resolved_entry(self) -> None:
        ledger, _ = self.append(outer_work.empty(), request())
        ledger = outer_work.resolve(
            ledger,
            {
                "entry_id": "OW-RELEASE-001",
                "expected_revision": ledger["revision"],
                "evidence": "The release owner recorded the quality decision against the candidate revision.",
                "reason": "The required approval was obtained for the reviewed candidate.",
            },
            provenance(stage="quality", step=None),
        )

        ledger, receipt = self.append(
            ledger,
            request(request_id="OWR-002", expected_revision=ledger["revision"]),
        )
        self.assertEqual(receipt["outcome"], "duplicate")
        self.assertEqual(ledger["entries"][0]["status"], "resolved")
        self.assertEqual(outer_work.pending_for_stage(ledger, "quality"), [])

    def test_resolution_requires_evidence_reason_and_the_matching_outer_stage(self) -> None:
        ledger, _ = self.append(outer_work.empty(), request())
        incomplete = {
            "entry_id": "OW-RELEASE-001",
            "expected_revision": ledger["revision"],
            "evidence": "A decision exists.",
        }
        with self.assertRaisesRegex(outer_work.OuterWorkError, "unexpected schema"):
            outer_work.resolve(ledger, incomplete, provenance(stage="quality", step=None))

        complete = dict(incomplete, reason="The listed action was completed with the supplied evidence.")
        with self.assertRaisesRegex(outer_work.OuterWorkError, "matching target stage"):
            outer_work.resolve(ledger, complete, provenance(stage="publish", step=None))

    def test_only_event_backed_effective_entries_are_valid_and_waive_is_not_a_resolution(
        self,
    ) -> None:
        ledger, _ = self.append(outer_work.empty(), request())
        forged = deepcopy(ledger)
        forged["entries"][0]["status"] = "resolved"
        with self.assertRaisesRegex(outer_work.OuterWorkError, "effective entry"):
            outer_work.validate(forged)

        waived = {
            "entry_id": "OW-RELEASE-001",
            "expected_revision": ledger["revision"],
            "evidence": "No evidence is needed.",
            "reason": "waived",
            "status": "waived",
        }
        with self.assertRaisesRegex(outer_work.OuterWorkError, "unexpected schema"):
            outer_work.resolve(ledger, waived, provenance(stage="quality", step=None))

    def test_credential_looking_text_and_unstable_ids_are_rejected_before_append(self) -> None:
        secret = request()
        secret["evidence"] = "Authorization: Bearer sk-proj-0123456789abcdef"
        with self.assertRaisesRegex(outer_work.OuterWorkError, "credential"):
            self.append(outer_work.empty(), secret)

        unsafe = request()
        unsafe["entry_id"] = "OW release approval"
        with self.assertRaisesRegex(outer_work.OuterWorkError, "stable safe identifier"):
            self.append(outer_work.empty(), unsafe)

    def test_current_read_receipt_binds_the_full_markdown_record(self) -> None:
        ledger, _ = self.append(outer_work.empty(), request())
        receipt = {
            "revision": ledger["revision"],
            "digest": hashlib.sha256(outer_work.render(ledger).encode("utf-8")).hexdigest(),
            "target_stage": "quality",
        }

        outer_work.check_read(ledger, receipt, target_stage="quality")
        stale = dict(receipt, digest="0" * 64)
        with self.assertRaisesRegex(outer_work.OuterWorkError, "current outer_work_read"):
            outer_work.check_read(ledger, stale, target_stage="quality")
        wrong_stage = dict(receipt, target_stage="publish")
        with self.assertRaisesRegex(outer_work.OuterWorkError, "current outer_work_read"):
            outer_work.check_read(ledger, wrong_stage, target_stage="quality")

    def test_templates_expose_the_expected_revision_and_required_fields(self) -> None:
        request_template = outer_work.request_template("OWR-NEW", 7)
        self.assertEqual(request_template["request_id"], "OWR-NEW")
        self.assertEqual(request_template["expected_revision"], 7)
        self.assertTrue(
            {
                "entry_id",
                "dedupe_key",
                "required_action",
                "target_stage",
                "target_alias",
                "prerequisites",
                "expected_outcome",
                "evidence",
                "authority_limitations",
                "rationale",
            }.issubset(request_template)
        )
        resolution_template = outer_work.resolution_template("OW-RELEASE-001", 8)
        self.assertEqual(resolution_template["entry_id"], "OW-RELEASE-001")
        self.assertEqual(resolution_template["expected_revision"], 8)
        self.assertEqual(set(resolution_template), {"entry_id", "expected_revision", "evidence", "reason"})


if __name__ == "__main__":
    unittest.main()
