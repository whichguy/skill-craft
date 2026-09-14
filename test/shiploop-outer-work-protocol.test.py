#!/usr/bin/env python3
"""Real-CLI and helper-level regression coverage for ShipLoop outer work."""

from __future__ import annotations

import copy
import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_action_walk_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_outer_work_action_fixture", str(ACTION_WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {ACTION_WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


ACTION = load_action_walk_fixture()

import shiploop_outer_work as outer_work  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class OuterWorkProtocolTests(ACTION.ShipLoopActionWalkFixture):
    """Exercise the public callback once and hard-to-reach gates directly."""

    def init_at_preflight(self) -> dict:
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--bound-plan",
            str(self.bound_plan),
            "--execution-mode",
            self.execution_mode,
            "--prompt",
            "Exercise the bounded outer-work journal through a real ShipLoop CLI run.",
        )
        state = self.state()
        self.assertEqual(state["stage"], "preflight")
        self.assertTrue(state.get("outer_work_protocol_version") == 1)
        return state

    def outer_context(self) -> dict:
        """Read every real CLI page without exceeding the 8000-character limit."""
        offset = 0
        digest = None
        chunks: list[str] = []
        while True:
            args = [
                "context",
                "--section",
                "outer-work",
                "--offset",
                str(offset),
                "--limit",
                "8000",
            ]
            if digest is not None:
                args.extend(("--digest", digest))
            result = self.cli(*args)
            header, body = result.stdout.split("\n", 1)
            match = re.fullmatch(
                r"Context outer-work; digest ([0-9a-f]{64}); characters (\d+):(\d+)/(\d+)",
                header,
            )
            self.assertIsNotNone(match, result.stdout)
            assert match is not None
            page_digest, start, end, total = match.groups()
            self.assertEqual(int(start), offset)
            self.assertEqual(page_digest, digest or page_digest)
            chunks.append(body[: int(end) - offset])
            offset = int(end)
            digest = page_digest
            if offset == int(total):
                return store.loads("".join(chunks))

    def outer_request(
        self,
        context: dict,
        *,
        entry_id: str = "OW-RELEASE-001",
        dedupe_key: str = "release-owner-approval",
        target_stage: str = "quality",
        expected_outcome: str = "The release owner records whether publication may proceed.",
    ) -> dict:
        request = copy.deepcopy(context["append_template"])
        request.update(
            entry_id=entry_id,
            dedupe_key=dedupe_key,
            required_action="Obtain the release owner's explicit approval before publication.",
            target_stage=target_stage,
            target_alias="production-release",
            prerequisites=[
                "The candidate revision remains the reviewed and verified revision.",
                "The release owner has the current quality evidence.",
            ],
            expected_outcome=expected_outcome,
            evidence="Current quality report and bound candidate revision are available for review.",
            authority_limitations="This journal does not authorize publication or deployment; the release owner must approve it separately.",
            rationale="Production publication is outside the inner implementation authority.",
        )
        return request

    def journal(self, payload: dict, *, operation: str = "append", code: int = 0):
        return self.cli(
            "journal",
            "--target",
            "outer",
            "--operation",
            operation,
            "--action",
            self.action_id(),
            "--result",
            self.record(f"outer-{operation}", payload),
            code=code,
        )

    def ledger(self) -> dict:
        return outer_work.validate(store.read_record(self.run_dir / "outer-work.md"))

    def test_real_cli_preflight_is_lazy_replay_safe_and_tamper_safe(self) -> None:
        before = self.init_at_preflight()
        self.assertFalse((self.run_dir / "outer-work.md").exists())

        empty_context = self.outer_context()
        self.assertEqual(empty_context["entries"], [])
        self.assertIn(f"--action {before['action']['id']}", empty_context["append_callback"])
        self.assertIn("--target outer", empty_context["append_callback"])
        self.assertIn("--operation append", empty_context["append_callback"])
        self.assertFalse((self.run_dir / "outer-work.md").exists())

        payload = self.outer_request(empty_context)
        action = before["action"]
        stage = before["stage"]
        self.journal(payload)
        after_append = self.state()
        self.assertEqual(after_append["action"], action)
        self.assertEqual(after_append["stage"], stage)
        self.assertGreater(after_append["revision"], before["revision"])
        self.assertTrue((self.run_dir / "outer-work.md").is_file())
        ledger = self.ledger()
        self.assertEqual(ledger["revision"], 1)
        self.assertEqual(ledger["events"][0]["provenance"]["parent_stage"], "preflight")
        self.assertEqual(ledger["entries"][0]["status"], "planned")

        # A fresh CLI process can cold-read the record and its existing IDs.
        cold_context = self.outer_context()
        self.assertEqual(cold_context["entries"][0]["id"], "OW-RELEASE-001")
        self.assertEqual(cold_context["append_template"]["expected_revision"], 1)

        state_before_replay = (self.run_dir / "state.md").read_bytes()
        self.journal(payload)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)
        self.assertEqual(len(self.ledger()["events"]), 1)

        conflicting = dict(payload)
        conflicting["rationale"] = "A changed body cannot reuse an accepted journal request ID."
        rejected = self.journal(conflicting, code=2)
        self.assertIn("conflicting replay", rejected.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)

        # A new request ID for the same dependency becomes an audited duplicate,
        # not another planned obligation.
        duplicate = self.outer_request(cold_context)
        self.journal(duplicate)
        duplicate_ledger = self.ledger()
        self.assertEqual(duplicate_ledger["revision"], 2)
        self.assertEqual(len(duplicate_ledger["events"]), 2)
        self.assertEqual(len(duplicate_ledger["entries"]), 1)
        self.assertEqual(duplicate_ledger["events"][-1]["receipt"]["outcome"], "duplicate")

        current_context = self.outer_context()
        stale = self.outer_request(current_context)
        stale["expected_revision"] = 1
        rejected = self.journal(stale, code=2)
        self.assertIn("stale outer-work revision", rejected.stderr)

        secret = self.outer_request(current_context)
        secret["evidence"] = "Authorization: Bearer sk-proj-0123456789abcdef"
        rejected = self.journal(secret, code=2)
        self.assertIn("credential", rejected.stderr)
        self.assertEqual(self.ledger()["revision"], 2)

        outer_path = self.run_dir / "outer-work.md"
        original = outer_path.read_bytes()
        outer_path.write_text("tampered outer work\n", encoding="utf-8")
        rejected = self.cli(
            "context", "--section", "outer-work", "--offset", "0", "--limit", "8000", code=2
        )
        self.assertIn("changed outside", rejected.stderr)
        outer_path.write_bytes(original)
        outer_path.unlink()
        rejected = self.cli(
            "context", "--section", "outer-work", "--offset", "0", "--limit", "8000", code=2
        )
        self.assertIn("missing", rejected.stderr)
        outer_path.write_bytes(original)

    def test_real_cli_rejects_publish_target_when_lifecycle_has_no_outer_publish(self) -> None:
        before = self.init_at_preflight()
        store.write_record(
            self.run_dir / "lifecycle.md",
            {
                "acceptance": ["The local fixture remains checked before handoff."],
                "preparation": "none",
                "publish": "none",
                "quality": True,
                "reason": "This fixture has no authorized external publication route.",
            },
            title="Fixture lifecycle",
        )
        payload = self.outer_request(
            self.outer_context(),
            entry_id="OW-PUBLISH-REJECTED-001",
            dedupe_key="publish-not-enabled",
            target_stage="publish",
        )

        rejected = self.journal(payload, code=2)
        self.assertIn("publish is not an enabled outer stage", rejected.stderr)
        self.assertFalse((self.run_dir / "outer-work.md").exists())
        after = self.state()
        self.assertEqual(after["action"], before["action"])
        self.assertEqual(after["stage"], before["stage"])

    def test_real_cli_rejects_tampered_or_forged_journal_receipts(self) -> None:
        before = self.init_at_preflight()
        payload = self.outer_request(self.outer_context())
        self.journal(payload)
        after_append = self.state()
        self.assertEqual(after_append["action"], before["action"])
        self.assertEqual(after_append["stage"], before["stage"])
        self.assertIn(payload["request_id"], after_append["outer_work_receipts"])

        receipt_path = self.run_dir / "journal-requests" / f"{payload['request_id']}.md"
        original_receipt = receipt_path.read_bytes()
        tampered = store.read_record(receipt_path)
        tampered["input_digest"] = "0" * 64
        store.write_record(receipt_path, tampered, title="Tampered outer-work receipt")
        state_before_replay = (self.run_dir / "state.md").read_bytes()
        rejected = self.journal(payload, code=2)
        self.assertIn("receipt binding mismatch", rejected.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_replay)
        self.assertEqual(self.ledger()["revision"], 1)
        receipt_path.write_bytes(original_receipt)

        # The current callback ID has not been issued before. A forged file at
        # that exact path must fail its absent state binding, not suppress the
        # otherwise valid append.
        current_context = self.outer_context()
        forged_payload = self.outer_request(
            current_context,
            entry_id="OW-FORGED-RECEIPT-001",
            dedupe_key="forged-receipt-rejection",
        )
        forged_path = self.run_dir / "journal-requests" / f"{forged_payload['request_id']}.md"
        self.assertFalse(forged_path.exists())
        store.write_record(
            forged_path,
            {
                "input_digest": "0" * 64,
                "parent_action": before["action"]["id"],
                "request": forged_payload,
                "operation": "append",
                "receipt": {"outcome": "created"},
            },
            title="Forged outer-work request receipt",
        )
        state_before_forgery = (self.run_dir / "state.md").read_bytes()
        rejected = self.journal(forged_payload, code=2)
        self.assertIn("receipt binding mismatch", rejected.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_forgery)
        self.assertNotIn(forged_payload["request_id"], self.state()["outer_work_receipts"])
        ledger = self.ledger()
        self.assertEqual(ledger["revision"], 1)
        self.assertEqual([entry["id"] for entry in ledger["entries"]], ["OW-RELEASE-001"])

    def test_real_cli_inner_append_does_not_advance_the_step_plan_action(self) -> None:
        before = self.bootstrap_to_first_step_plan()
        context = self.outer_context()
        payload = self.outer_request(
            context,
            entry_id="OW-INNER-001",
            dedupe_key="inner-discovered-quality-check",
            target_stage="quality",
        )
        action = before["action"]
        self.journal(payload)

        after = self.state()
        self.assertEqual(after["action"], action)
        self.assertEqual(after["stage"], "step-plan")
        self.assertEqual(after["active_step"], "S1")
        ledger = self.ledger()
        self.assertEqual(ledger["events"][0]["provenance"]["parent_stage"], "step-plan")
        self.assertEqual(ledger["entries"][0]["target_stage"], "quality")

    def direct_request(
        self,
        *,
        request_id: str,
        expected_revision: int,
        target_stage: str = "publish",
        entry_id: str = "OW-PUBLISH-001",
        dedupe_key: str = "publish-approval",
        expected_outcome: str = "The authorized publisher records the publication decision.",
    ) -> dict:
        return {
            "request_id": request_id,
            "expected_revision": expected_revision,
            "entry_id": entry_id,
            "dedupe_key": dedupe_key,
            "required_action": "Obtain the authorized publication decision for the reviewed candidate.",
            "target_stage": target_stage,
            "target_alias": "production-release",
            "prerequisites": ["The candidate has the current whole-product quality evidence."],
            "expected_outcome": expected_outcome,
            "evidence": "The quality report identifies the bound candidate revision.",
            "authority_limitations": "The journal does not grant publication authority or perform a publication.",
            "rationale": "Publication needs a distinct authorized outer-stage decision.",
        }

    def install_direct_ledger(self, state: dict, ledger: dict) -> dict:
        body = outer_work.render(ledger)
        (self.run_dir / "outer-work.md").write_text(body, encoding="utf-8")
        installed = copy.deepcopy(state)
        installed.update(
            outer_work_protocol_version=1,
            outer_work_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            outer_work_revision=ledger["revision"],
        )
        return installed

    def record_full_outer_read(self, state: dict, *, end: int | None = None) -> None:
        body = protocol.outer_work_context(self.run_dir, state)
        protocol.record_outer_work_page(
            self.run_dir,
            state,
            checksum=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            offset=0,
            end=len(body) if end is None else end,
            total=len(body),
        )

    def test_outer_gate_read_receipts_stage_order_and_exact_resolution(self) -> None:
        state = self.init_at_preflight()
        ledger, _ = outer_work.append(
            outer_work.empty(),
            self.direct_request(request_id="OWR-DIRECT-001", expected_revision=0),
            {"parent_action": state["action"]["id"], "parent_step": None, "parent_stage": "planning"},
        )
        state = self.install_direct_ledger(state, ledger)
        state["stage"] = "quality"

        # A partial page cannot certify the full current context.
        self.record_full_outer_read(state, end=1)
        with self.assertRaisesRegex(protocol.ProtocolError, "every page"):
            protocol.require_outer_work_read(
                self.run_dir, state, stage="quality", require_resolved=True
            )
        self.record_full_outer_read(state)
        protocol.require_outer_work_read(
            self.run_dir, state, stage="quality", require_resolved=True
        )

        # The same target is due at publish and handoff but not prematurely at
        # quality; every newly selected stage must have its own full read.
        for stage in ("publish", "handoff"):
            state["stage"] = stage
            self.record_full_outer_read(state)
            with self.assertRaisesRegex(protocol.ProtocolError, f"blocks {stage}"):
                protocol.require_outer_work_read(
                    self.run_dir, state, stage=stage, require_resolved=True
                )

        # A changed journal revision invalidates a formerly complete receipt.
        state["stage"] = "quality"
        self.record_full_outer_read(state)
        ledger, _ = outer_work.append(
            ledger,
            self.direct_request(
                request_id="OWR-DIRECT-002", expected_revision=ledger["revision"]
            ),
            {"parent_action": state["action"]["id"], "parent_step": None, "parent_stage": "verify"},
        )
        state = self.install_direct_ledger(state, ledger)
        with self.assertRaisesRegex(protocol.ProtocolError, "every page"):
            protocol.require_outer_work_read(
                self.run_dir, state, stage="quality", require_resolved=True
            )
        self.record_full_outer_read(state)
        protocol.require_outer_work_read(
            self.run_dir, state, stage="quality", require_resolved=True
        )

        # An action-bound page receipt cannot be borrowed by another action.
        read_path = self.run_dir / "outer-work-reads" / f"{state['action']['id']}.md"
        bad_action = store.read_record(read_path)
        bad_action["action"] = "A-OTHER-001"
        store.write_record(read_path, bad_action, title="Bad outer-work read receipt")
        with self.assertRaisesRegex(protocol.ProtocolError, "every page"):
            protocol.require_outer_work_read(
                self.run_dir, state, stage="quality", require_resolved=True
            )
        self.record_full_outer_read(state)

        # A quality action cannot resolve publication work, even after reading
        # the current context. The matching publish action can, and a changed
        # later request reopens the stable effective entry.
        resolution = dict(
            outer_work.resolution_template("OW-PUBLISH-001", ledger["revision"]),
            request_id=protocol.outer_work_request_id(state, ledger),
        )
        with self.assertRaisesRegex(outer_work.OuterWorkError, "matching target stage"):
            protocol.journal_outer_work(
                self.run_dir, state, state["action"]["id"], resolution, "resolve"
            )

        state["stage"] = "publish"
        self.record_full_outer_read(state)
        protocol.journal_outer_work(
            self.run_dir, state, state["action"]["id"], resolution, "resolve"
        )
        resolved = self.ledger()
        self.assertEqual(resolved["entries"][0]["status"], "resolved")

        reopened = self.direct_request(
            request_id=protocol.outer_work_request_id(state, resolved),
            expected_revision=resolved["revision"],
            expected_outcome="The authorized publisher records a fresh decision for the revised candidate.",
        )
        protocol.journal_outer_work(
            self.run_dir, state, state["action"]["id"], reopened, "append"
        )
        reopened_ledger = self.ledger()
        self.assertEqual(reopened_ledger["entries"][0]["status"], "planned")
        self.assertEqual(reopened_ledger["events"][-1]["receipt"]["outcome"], "reopened")


if __name__ == "__main__":
    unittest.main()
