#!/usr/bin/env python3
"""Large-context recovery checks; synthetic results, no Improve execution."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


class PacketBoundsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-packet-bounds-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.run = self.repo / "run"
        self.run.mkdir()

    def state(self, prompt="Implement the requested behavior."):
        # Bounds were measured on the delegated route's longer packets.
        return navigator.new_state(str(self.repo), prompt,
                                   delegation="ask-agent")

    def complete(self, state, **extra):
        action = navigator.current_action(state)
        waiting = navigator.apply(state, action["id"], {
            "outcome": "done", "summary": "Synthetic packet fixture", **extra,
        })
        if waiting.get("active_improve") is None:
            return waiting
        return navigator.finish_improve(waiting, action["id"], {
            "summary": "Synthetic review; no semantic claim", "lessons": "Read relevant references.",
        })

    def cold_packet(self, state):
        path = self.run / "state.md"
        store.write_record(path, state)
        before = path.read_bytes()
        cold = store.read_record(path)
        packet = navigator.render(None, self.run, cold)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(cold, state)
        return packet

    def test_large_work_context_is_recoverable_without_copying_it_into_packet(self):
        state = self.state()
        long_context = "c" * 2_000_000 + "REQUIRED_CONTEXT_TAIL"
        long_title = "t" * 100_000 + "TITLE_TAIL"
        while navigator.current_stage(state) != "select-work":
            extra = {}
            if navigator.current_stage(state) == "plan":
                extra["work_items"] = [{"id": "W1", "title": long_title, "context": long_context}]
            state = self.complete(state, **extra)
        packet = self.cold_packet(state)
        self.assertNotIn(long_context, packet)
        self.assertIn(str(self.run / "state.md"), packet)
        self.assertIn("work_items[0].context", packet)
        self.assertIn("work_items[0].title", packet)
        self.assertIn("Read the complete required context before acting", packet)
        self.assertEqual(state["work_items"][0]["context"], long_context)
        self.assertIn(navigator.current_action(state)["id"], packet)

    def test_large_original_request_retains_full_scope_in_durable_field(self):
        request = "r" * 2_000_000 + "KEEP_THIS_USER_CONSTRAINT"
        state = self.state(request)
        packet = self.cold_packet(state)
        self.assertNotIn(request, packet)
        self.assertIn("field prompt", packet)
        self.assertEqual(state["prompt"], request)

    def test_large_pending_result_uses_exact_seed_locator_and_same_callback(self):
        state = self.state()
        while navigator.current_stage(state) != "spec":
            state = self.complete(state)
        action = navigator.current_action(state)
        summary = "s" * 2_000_000 + "SEED_CONSTRAINT_TAIL"
        waiting = navigator.apply(state, action["id"], {"outcome": "done", "summary": summary})
        self.assertIsNotNone(waiting.get("active_improve"))
        packet = self.cold_packet(waiting)
        self.assertIn("active_improve.seed_result", packet)
        self.assertIn("Outcome: done", packet)
        self.assertIn(action["id"], packet)
        self.assertNotIn(summary, packet)
        self.assertEqual(waiting["active_improve"]["seed_result"]["summary"], summary)

    def test_many_long_evidence_references_keep_full_record_and_bound_packet(self):
        refs = [f"evidence/{index}/" + "x" * 1000 for index in range(1000)]
        state = self.complete(self.state(), evidence_refs=refs)
        action = state["history"][-1]["action"]
        packet = self.cold_packet(state)
        self.assertIn(f"accepted.{action}.evidence_refs", packet)
        self.assertEqual(state["accepted"][action]["evidence_refs"], refs)

    def test_short_context_and_request_still_render_in_full(self):
        state = self.state("Keep the exact short user request.")
        packet = self.cold_packet(state)
        self.assertIn(state["prompt"], packet)
        self.assertNotIn("Read the complete required context before acting", packet)

    def test_large_block_reason_keeps_resume_route(self):
        state = navigator.control(self.state(), "pause", reason="b" * 2_000_000 + "REASON_TAIL")
        packet = self.cold_packet(state)
        self.assertIn("status_reason", packet)
        self.assertIn("Resume:", packet)

    def test_oversized_delivery_template_is_not_truncated_into_invalid_json(self):
        state = navigator.new_state(str(self.repo), "Observe local behavior.", delivery_contract=True)
        while navigator.current_stage(state) != "plan":
            state = self.complete(state)
        contract = {
            "consumer": "local CLI", "target": "local target", "behavior": "expected output",
            "candidate": "c" * 100_000, "operation": "local checks", "necessity": "not-required",
            "basis": "Explicit local-only request", "exclusions": [],
            "authority": {"status": "not-required", "kind": "request", "reference": "Local-only",
                          "target": "local target", "operation": "local checks"},
            "obligations": [{"id": "pre", "consumer": "local CLI", "target": "local target",
                             "kind": "pre-update", "phase": "system-test",
                             "expected": "Current local checks pass", "required": True},
                            {"id": "behavior", "consumer": "local CLI", "target": "local target",
                             "kind": "behavior", "phase": "release-verify",
                             "expected": "Observed output matches request", "required": True}],
        }
        state = self.complete(state, delivery_assessment={"kind": "contract", "contract": contract})
        while navigator.current_stage(state) != "system-test":
            state = self.complete(state)
        packet = self.cold_packet(state)
        self.assertIn("accepted (delivery_assessment records in history order)", packet)
        self.assertIn("does not waive any required observation", packet)
        result_text = packet.split("Result template:\n", 1)[1].split("\nCall this when done:", 1)[0]
        # The minimal fallback keeps the placeholder the script refuses, never
        # an empty list a worker could copy verbatim.
        self.assertEqual(store.loads(result_text), {"outcome": "done", "summary": "...",
                                                    "evidence_refs": [navigator.EVIDENCE_PLACEHOLDER]})
        self.assertIn(navigator.current_action(state)["id"], packet)


if __name__ == "__main__":
    unittest.main()
