#!/usr/bin/env python3
"""Atomic report publication and the one-action completion alias."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_delivery as delivery  # noqa: E402
import shiploop_improve_bridge as improve_bridge  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-delivery-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = {"phase": "done", "stage": "done", "revision": 12}
        self.html = "<!doctype html><title>Verified result</title>"
        self.meta = {
            "schema_version": 1,
            "source_digest": "a" * 64,
            "outcome": "complete",
            "evidence_complete": True,
            "evidence_errors": [],
        }

    def test_prepared_report_and_state_share_transaction_inputs(self):
        writes = {"history.md": store.dumps([]), "handoff.md": store.dumps({"summary": "Done"})}
        with patch.object(delivery, "render_report", return_value=(self.html, self.meta)) as render:
            result = delivery.prepare_terminal_report(self.root, self.state, writes)
        overlay = render.call_args.kwargs["overrides"]
        self.assertEqual(store.loads(overlay["state.md"])["stage"], "done")
        self.assertIn("handoff.md", overlay)
        self.assertEqual(result["report.html"], self.html)
        saved = store.loads(result["state.md"])
        self.assertEqual(saved["report"]["sha256"], hashlib.sha256(self.html.encode()).hexdigest())
        self.assertEqual(saved["report"]["source_digest"], "a" * 64)

    def test_terminal_overlay_keeps_only_bound_handoff_objective_certificate(self):
        loop = "delivery-fixture-handoff-objective"
        certificate = f"objectives/{loop}/certificate.md"
        receipt = f"objectives/{loop}.md"
        self.state.update(
            delivery_objective_protocol_version=1,
            objective={
                "loop_id": loop,
                "kind": "handoff",
                "base_stage": "handoff",
                "receipt": receipt,
                "candidate": f"objectives/{loop}/candidate.md",
                "status": "finalized",
                "certificate": certificate,
            },
        )
        writes = {
            receipt: store.dumps({"loop_id": loop}),
            certificate: store.dumps({"loop_id": loop}),
            "results/delivery-fixture-finalize.md": store.dumps({"summary": "Done"}),
            "handoff.md": store.dumps({"summary": "Done"}),
        }
        with patch.object(delivery, "render_report", return_value=(self.html, self.meta)) as render:
            result = delivery.prepare_terminal_report(self.root, self.state, writes)
        overlay = render.call_args.kwargs["overrides"]
        self.assertIn(receipt, overlay)
        self.assertIn(certificate, overlay)
        self.assertEqual(result[certificate], writes[certificate])
        self.assertNotIn("report.html", overlay)

    def test_terminal_overlay_refuses_unknown_or_unsafe_writes(self):
        loop = "delivery-fixture-handoff-objective"
        for relative, message in (
            (f"objectives/{loop}/candidate.md", "accepted report input"),
            (f"objectives/{loop}/certificate.md", "accepted report input"),
            ("../escape.md", "terminal write path is unsafe"),
        ):
            with self.subTest(relative=relative), patch.object(
                delivery, "render_report", return_value=(self.html, self.meta)
            ):
                with self.assertRaisesRegex(delivery.DeliveryError, message):
                    delivery.prepare_terminal_report(
                        self.root, self.state, {relative: "untrusted"}
                    )

    def test_incomplete_evidence_cannot_prepare_success(self):
        meta = dict(self.meta, outcome="unfinished", evidence_complete=False, evidence_errors=["Missing test"])
        with patch.object(delivery, "render_report", return_value=(self.html, meta)):
            with self.assertRaisesRegex(delivery.DeliveryError, "Missing test"):
                delivery.prepare_terminal_report(self.root, self.state, {})
        self.assertNotIn("report", self.state)

    def test_halted_report_remains_unfinished(self):
        state = dict(self.state, phase="halted", stage="halted")
        meta = dict(self.meta, outcome="unfinished", evidence_complete=False)
        with patch.object(delivery, "render_report", return_value=(self.html, meta)):
            writes = delivery.prepare_terminal_report(self.root, state, {})
        self.assertEqual(store.loads(writes["state.md"])["report"]["outcome"], "unfinished")
        self.assertFalse(delivery.valid_complete_report(self.root, state))

    def test_validation_checks_html_and_current_sources(self):
        with patch.object(delivery, "render_report", return_value=(self.html, self.meta)):
            writes = delivery.prepare_terminal_report(self.root, self.state, {})
            store.transaction(self.root, writes)
            self.assertTrue(delivery.valid_complete_report(self.root, self.state))
        changed = dict(self.meta, source_digest="b" * 64)
        with patch.object(delivery, "render_report", return_value=(self.html, changed)):
            self.assertFalse(delivery.valid_complete_report(self.root, self.state))
        (self.root / "report.html").write_text("forged", encoding="utf-8")
        with patch.object(delivery, "render_report", return_value=(self.html, self.meta)):
            self.assertFalse(delivery.valid_complete_report(self.root, self.state))

    def test_report_symlink_refused(self):
        (self.root / "report.html").symlink_to(self.root / "elsewhere")
        with patch.object(delivery, "render_report", return_value=(self.html, self.meta)):
            with self.assertRaises(delivery.DeliveryError):
                delivery.prepare_terminal_report(self.root, self.state, {})

    def test_done_alias_requires_action_and_result(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "shiploop"), "done"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--action", result.stderr)
        self.assertIn("--result", result.stderr)

    def test_managed_terminal_transaction_renders_only_durable_parent_state(self):
        for terminal in ("done", "halted"):
            with self.subTest(terminal=terminal):
                root = self.root / terminal
                root.mkdir()
                durable = {"phase": terminal, "stage": terminal, "revision": 12,
                           "action": {"id": "terminal-action", "stage": terminal}}
                transient = dict(durable, _managed_improve_projection={"private": True})
                child_path = "managed-improve/bound-child.md"
                child_body = store.dumps({"status": "converged" if terminal == "done" else "stopped"})
                pending = {"handoff.md": store.dumps({"summary": "Recorded outcome."})}
                bridged = dict(pending, **{child_path: child_body})
                metadata = dict(self.meta, outcome="complete" if terminal == "done" else "unfinished")
                with patch.object(improve_bridge, "prepare", return_value=(durable, bridged, [])), patch.object(
                    delivery, "render_report", return_value=(self.html, metadata)
                ) as render:
                    protocol.persist(root, transient, "complete:objective-finalize", pending)
                overlay = render.call_args.kwargs["overrides"]
                self.assertNotIn(child_path, overlay)
                self.assertEqual((root / child_path).read_text(), child_body)
                saved = store.read_record(root / "state.md")
                self.assertFalse(any(key.startswith("_") for key in saved))
                self.assertEqual(saved, transient)
                self.assertEqual(store.loads(overlay["state.md"])["action"], durable["action"])
                self.assertEqual(saved["report"]["source_digest"], metadata["source_digest"])
                self.assertEqual((root / "report.html").read_text(), self.html)

    def test_managed_namespace_does_not_hide_caller_supplied_terminal_writes(self):
        pending = {"managed-improve/unbound-child.md": "Unvalidated caller content"}
        with patch.object(improve_bridge, "prepare", return_value=(dict(self.state), dict(pending), [])):
            with self.assertRaisesRegex(protocol.ProtocolError, "accepted report input"):
                protocol.persist(self.root, dict(self.state), "halt", pending)
        self.assertFalse((self.root / "state.md").exists())
        self.assertFalse((self.root / "managed-improve").exists())

    def test_managed_success_gate_requires_its_bound_child_certificate(self):
        self.state["managed_improve_protocol_version"] = 1
        with patch.object(delivery, "render_report", return_value=(self.html, self.meta)):
            store.transaction(self.root, delivery.prepare_terminal_report(self.root, self.state, {}))
            with patch.object(improve_bridge, "validate_imported_certificate", return_value={"validated": True}):
                self.assertTrue(delivery.valid_complete_report(self.root, self.state))
            with patch.object(improve_bridge, "validate_imported_certificate", return_value=None):
                self.assertFalse(delivery.valid_complete_report(self.root, self.state))
            with patch.object(improve_bridge, "validate_imported_certificate", side_effect=ValueError("changed certificate")):
                self.assertFalse(delivery.valid_complete_report(self.root, self.state))


if __name__ == "__main__":
    unittest.main()
