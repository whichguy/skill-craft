#!/usr/bin/env python3
"""Large-context recovery checks; synthetic results, no Improve execution."""

from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
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
        while navigator.current_stage(state) != "step-plan":
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
        # Packet re-cut (2026-10-11): the Improve packet is two instructions; the seed result and its exact locator
        # are in the handoff file ShipLoop writes (navigator.improve_handoff_text).
        handoff = navigator.improve_handoff_text(None, self.run, waiting)
        self.assertIn("active_improve.seed_result", handoff)
        self.assertIn("Outcome: done", handoff)
        self.assertIn(action["id"], handoff)
        self.assertNotIn(summary, handoff)
        self.assertNotIn(summary, packet)
        # The Improve stage has its own action id (2026-10-11): the packet's callback names it, not the producer's.
        self.assertIn(navigator.improve_id(waiting), packet)
        self.assertNotIn(action["id"], packet)
        self.assertNotIn("active_improve.seed_result", packet)
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

    def test_a_long_paused_packet_prints_within_the_host_output_limit(self):
        """X11 (e12_head_size.py): paused, halted and blocked packets printed whole past ~20 KB."""
        import contextlib, io
        from unittest import mock
        state = navigator.control(self.state(), "pause", reason="user asked")
        store.write_record(self.run / "state.md", state)
        for text, whole in (("short packet\n", True), (("x" * 60 + "\n") * 1000 + "TAIL\n", False)):
            with self.subTest(whole=whole), mock.patch.object(navigator, "render", return_value=text):
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    navigator.emit(None, self.run, state)
                if whole:
                    self.assertEqual(printed.getvalue(), text)
                else:
                    self.assertLessEqual(len(printed.getvalue()), navigator.PRINT_LIMIT)
                    self.assertIn("Full packet: " + str(navigator.packet_path(self.run, state)), printed.getvalue())
                self.assertEqual(navigator.packet_path(self.run, state).read_text(), text)

    def test_an_improve_printing_does_not_overwrite_the_producer_packet_that_was_sent(self):
        """A reviewed stage printed its producer packet and then the Improve child's at the same path, so after a run the
        producer packet of spec, test-strategy, plan, step-plan and test-spec could not be audited (10 of 46 visits)."""
        import contextlib, io
        state = self.state()
        while navigator.current_stage(state) != "spec":
            state = self.complete(state)
        action = navigator.current_action(state)["id"]
        store.write_record(self.run / "state.md", state)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, state)
        producer = navigator.packet_path(self.run, state)
        sent = producer.read_text()
        waiting = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic packet fixture"})
        self.assertIsNotNone(waiting.get("active_improve"))
        store.write_record(self.run / "state.md", waiting)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, waiting)
        improve = navigator.packet_path(self.run, waiting)
        self.assertNotEqual(improve, producer)
        self.assertEqual(producer.name, action + ".md")
        self.assertEqual(improve.name, navigator.improve_id(waiting) + "-bind.md")  # no card is bound yet: the bind packet
        self.assertEqual(producer.read_text(), sent)
        self.assertIn("Current action: Improve the completed spec result.",
                      navigator.improve_handoff_text(None, self.run, waiting))  # the handoff holds the detail (re-cut)

    def test_the_improve_bind_packet_keeps_its_own_file_when_improve_start_prints(self):
        """An Improve child prints two packets before the runtime starts: improve-bind (no card bound yet) and, once bound,
        the improve packet. Both went to <action>-improve.md, so the bind packet was lost on disk and could not be reviewed
        (packet compaction plan 2026-10-10, Phase 0; the producer-packet fix before it is 897733cb)."""
        import contextlib, io
        state = self.state()
        while navigator.current_stage(state) != "spec":
            state = self.complete(state)
        action = navigator.current_action(state)["id"]
        waiting = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic packet fixture"})
        child = waiting["active_improve"]
        self.assertIsNone(child["skill"])
        store.write_record(self.run / "state.md", waiting)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, waiting)
        bind = navigator.packet_path(self.run, waiting)
        sent = bind.read_text()
        self.assertIn("improve-bind", sent)
        bound = dict(waiting)
        bound["active_improve"] = bridge.binding(waiting, action, navigator.current_stage(waiting),
                                                 child["seed_result"],
                                                 bridge.resolve_skill(str(ROOT / "skills/improve/SKILL.md")),
                                                 improve_action=child["improve_action"])
        navigator.validate(bound)
        store.write_record(self.run / "state.md", bound)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, bound)
        start = navigator.packet_path(self.run, bound)
        self.assertNotEqual(start, bind)
        self.assertEqual(start.name, navigator.improve_id(bound) + ".md")
        self.assertEqual(bind.name, navigator.improve_id(waiting) + "-bind.md")
        self.assertEqual(bind.read_text(), sent)
        # Bound at the transition or by hand, the first packet is the two instructions: run the improve skill, then
        # improve-complete; there is no improve-bind step left in it (packet re-cut, 2026-10-11).
        started = start.read_text()
        self.assertIn("/improve ShipLoop Improve: " + str(navigator.improve_handoff_path(bound["active_improve"])), started)
        self.assertIn(" complete --run-dir=", started)
        self.assertIn("--action=" + navigator.improve_id(bound), started)
        self.assertNotIn("improve-complete", started)
        self.assertNotIn("improve-bind", started)
        # This state was bound by hand with no start behind it, so the packet may name the one route that works,
        # improve-start --restart-stopped; no other improve-start form (such as --opening) exists any more.
        self.assertTrue(all("--restart-stopped" in line for line in re.findall(r"improve-start[^\n]*", started)))

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
        self.assertEqual(store.loads(result_text), {"outcome": "done", "headline": navigator.HEADLINE_PLACEHOLDER,
                                                    "summary": "...",
                                                    "evidence_refs": [navigator.EVIDENCE_PLACEHOLDER]})
        self.assertIn(navigator.current_action(state)["id"], packet)


if __name__ == "__main__":
    unittest.main()
