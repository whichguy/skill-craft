#!/usr/bin/env python3
"""Regression gates for the two packet teach-back follow-up proposals."""

from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))

import shiploop_packets as packets  # noqa: E402
import shiploop_until as until  # noqa: E402


class LoopScopeTests(unittest.TestCase):
    def test_every_converging_family_distinguishes_loop_exit_from_delivery(self):
        cases = [
            ("objective-review", {"objective_binding": {"kind": "approach", "base_stage": "approach"}},
             {"objectives": SimpleNamespace(is_objective_stage=lambda _: True)}),
            ("objective-plan", {"objective_binding": {"kind": "handoff", "base_stage": "handoff"}},
             {"objectives": SimpleNamespace(is_objective_stage=lambda _: True)}),
            ("behavior-review", {}, {"planning": SimpleNamespace(is_planning_stage=lambda _: True)}),
            ("step-plan-review", {}, {"is_step_plan_stage": lambda _: True}),
            ("review", {}, {}),
        ]
        for stage, info, api in cases:
            with self.subTest(stage=stage):
                lines = packets._stage_lifecycle(stage, info, api, history_limit=7)
                text = "\n".join(lines)
                boundary = next(line for line in lines if line.startswith("Delivery completion:"))
                self.assertIn("only", boundary)
                self.assertIn("terminal", boundary)
                self.assertIn("It's all complete.", boundary)
                self.assertIn("report", boundary)
                self.assertIn("next packet", boundary)
                self.assertLess(text.index("Until:"), text.index(boundary))
                self.assertIn("this loop only", text)
                self.assertIn("Continue while: open findings remain or required proof is missing.", text)
                self.assertIn("owning loop", until.review_improve_cycle(7))

    def test_baseline_reader_precedes_quality_summary_and_never_invents_availability(self):
        for status in ("not-yet-assessed", "recorded", "unavailable"):
            with self.subTest(status=status):
                quality = {
                    "initial_candidate": {"path": "results/origin.md"},
                    "assessment": {"status": status},
                }
                lines = packets._quality_orientation_lines({"quality": quality})
                self.assertTrue(lines[0].startswith("Read first: context --section quality-baseline"))
                self.assertIn("not current proof", lines[0])
                self.assertTrue(lines[1].startswith("Quality:"))
        lines = packets._quality_orientation_lines({
            "quality": {"assessment": {"status": "unavailable"}}
        })
        self.assertFalse(any("Read first:" in line for line in lines))
        self.assertIn("unavailable", "\n".join(lines))

    def test_real_reader_and_callback_preserve_action_and_loop_boundaries(self):
        fixture_type = runpy.run_path(str(ROOT / "test/shiploop-orientation-integration.test.py"))[
            "OrientationIntegrationTests"
        ]
        fixture = fixture_type()
        try:
            fixture.setUp()
            for reviewed in (False, True):
                if reviewed:
                    fixture.review()
                before = (fixture.f.run_dir / "state.md").read_bytes()
                packet = fixture.f.cli("next").stdout
                reader = next(line for line in packet.splitlines() if line.startswith("Read first:"))
                self.assertIn("context --section quality-baseline", reader)
                self.assertLess(packet.index(reader), packet.index("Quality:"))
                result = fixture.f.cli("context", "--section", "quality-baseline")
                self.assertIn(fixture.origin_action, result.stdout)
                self.assertEqual((fixture.f.run_dir / "state.md").read_bytes(), before)
                self.assertEqual(fixture.receipt()["completed_passes"], [])
                self.assertIn("Delivery completion:", packet)
                self.assertEqual(packet.count("Call this when done:"), 1)
            fixture.f.cli("pause", "--reason", "Await owner input.")
            paused = fixture.f.cli("next").stdout
            self.assertNotIn("Read first:", paused)
            self.assertNotIn("Call this when done:", paused)
            self.assertNotIn("Delivery completion:", paused)
        finally:
            fixture.doCleanups()


if __name__ == "__main__":
    unittest.main(verbosity=2)
