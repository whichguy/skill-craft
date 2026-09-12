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


if __name__ == "__main__":
    unittest.main()
