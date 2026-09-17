#!/usr/bin/env python3
"""Hermetic contracts for the ShipLoop consumer-delivery prompt pilot.

This validates fixture completeness and durable packet wiring. It does not
score an LLM response or claim a live target was changed.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "test" / "experiments" / "shiploop_delivery"
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(EXPERIMENT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import prepare_packets  # noqa: E402
from shiploop_navigator_prompts import COMMON, IMPROVE, PROMPTS  # noqa: E402


class DeliveryPromptPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = json.loads(
            (EXPERIMENT / "scenarios.json").read_text(encoding="utf-8")
        )
        cls.oracles = json.loads(
            (EXPERIMENT / "oracles.json").read_text(encoding="utf-8")
        )

    def expected_paths(self, variant: str) -> set[Path]:
        return {
            EXPERIMENT / "packets" / variant / f"{scenario['id']}-r{repetition}.md"
            for scenario in self.scenarios
            for repetition in (1, 2)
        }

    def test_fixed_sentinel_scenarios_have_separate_oracles(self) -> None:
        expected_ids = {
            "ambiguous-existing-hosted-ui",
            "approved-private-sync",
            "explicit-source-only",
            "necessary-delivery-missing-authority",
            "identity-without-visual-verification",
            "login-after-upload",
        }
        self.assertEqual({scenario["id"] for scenario in self.scenarios}, expected_ids)
        self.assertEqual(set(self.oracles), expected_ids)
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario["id"]):
                self.assertIn(scenario["stage"], PROMPTS)
                self.assertTrue(scenario["original_request"].strip())
                self.assertTrue(scenario["durable_facts"])
                self.assertTrue(scenario["reference_materials"])
                self.assertTrue(self.oracles[scenario["id"]]["must"])
                self.assertTrue(self.oracles[scenario["id"]]["must_not"])

    def test_frozen_a_and_candidate_b_packets_cover_two_fresh_repetitions(self) -> None:
        for variant in ("A", "B"):
            with self.subTest(variant=variant):
                actual = set((EXPERIMENT / "packets" / variant).glob("*.md"))
                self.assertEqual(actual, self.expected_paths(variant))
                for scenario in self.scenarios:
                    first = (
                        EXPERIMENT / "packets" / variant / f"{scenario['id']}-r1.md"
                    ).read_text(encoding="utf-8")
                    second = (
                        EXPERIMENT / "packets" / variant / f"{scenario['id']}-r2.md"
                    ).read_text(encoding="utf-8")
                    for repetition, packet in ((1, first), (2, second)):
                        self.assertIn("synthetic, read-only interpretation exercise", packet)
                        self.assertIn(f"Variant: {variant}", packet)
                        self.assertIn(f"Independent repetition: {repetition} of 2", packet)
                        self.assertIn(f"Current node: `{scenario['stage']}`", packet)
                        self.assertIn(scenario["original_request"], packet)
                        self.assertIn("## Current stage instructions", packet)
                        self.assertNotIn('"must_not"', packet)
                        self.assertNotRegex(packet, r"https?://")
                    def normalize_repetition(packet: str) -> str:
                        packet = re.sub(
                            r"Independent repetition: [12] of 2",
                            "Independent repetition: X of 2",
                            packet,
                        )
                        return re.sub(
                            r"Action: `synthetic-[ab]-[^`]+-r[12]`",
                            "Action: `synthetic-X`",
                            packet,
                        )

                    normalized_first = normalize_repetition(first)
                    normalized_second = normalize_repetition(second)
                    self.assertEqual(normalized_first, normalized_second)

    def test_a_is_frozen_baseline_and_b_contains_delivery_candidate_wording(self) -> None:
        baseline = (
            EXPERIMENT / "packets" / "A" / "ambiguous-existing-hosted-ui-r1.md"
        ).read_text(encoding="utf-8")
        candidate = (
            EXPERIMENT / "packets" / "B" / "ambiguous-existing-hosted-ui-r1.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("not automatically the consumer boundary", baseline)
        self.assertIn("not automatically the consumer boundary", candidate)
        self.assertNotEqual(baseline, candidate)
        for phrase in (
            "necessary operation or check",
            "applicable user-approved",
            "not silently make work source-only",
            "artifact identity, and consumer behavior",
        ):
            self.assertIn(phrase, COMMON)
        self.assertIn("original request, not only the generated", IMPROVE)
        self.assertIn("required but\nunauthorized or unverified update is blocked", PROMPTS["release-plan"])
        self.assertIn("successful GET cannot replace", PROMPTS["release-verify"])
        self.assertIn("post-update consumer checks", PROMPTS["system-test"])
        self.assertIn("what consumer behavior was verified", PROMPTS["handoff"])

    def test_exploratory_b2_is_separate_and_targets_only_phase_order_cases(self) -> None:
        b2 = EXPERIMENT / "packets" / "B2"
        expected_ids = {
            "approved-private-sync",
            "necessary-delivery-missing-authority",
        }
        expected = {
            b2 / f"{identifier}-r{repetition}.md"
            for identifier in expected_ids
            for repetition in (1, 2)
        }
        self.assertEqual(set(b2.glob("*.md")), expected)
        for path in expected:
            packet = path.read_text(encoding="utf-8")
            self.assertIn("Variant: B2", packet)
            self.assertIn("This current action's deliverable is a non-executing release plan", packet)
            self.assertIn("`release` action owns an authorized synchronization", packet)
        self.assertIn("exploratory_b2_phase_order", self.oracles["approved-private-sync"])
        self.assertIn(
            "exploratory_b2_phase_order",
            self.oracles["necessary-delivery-missing-authority"],
        )

    def test_packet_preparation_is_local_deterministic_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-delivery-packets-") as temp:
            output = Path(temp) / "packets"
            written = prepare_packets.prepare("B", output)
            self.assertEqual(len(written), 12)
            self.assertEqual(set(written), {
                output / f"{scenario['id']}-r{repetition}.md"
                for scenario in self.scenarios
                for repetition in (1, 2)
            })
            with self.assertRaises(FileExistsError):
                prepare_packets.prepare("B", output)

    def test_packet_preparation_can_make_a_declared_narrow_follow_up_set(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-delivery-follow-up-") as temp:
            output = Path(temp) / "packets"
            written = prepare_packets.prepare(
                "B2",
                output,
                ("approved-private-sync", "necessary-delivery-missing-authority"),
            )
            self.assertEqual(len(written), 4)
            self.assertTrue(all("Variant: B2" in path.read_text(encoding="utf-8") for path in written))

    def test_authority_cases_have_private_oracles_and_reproducible_packets(self) -> None:
        cases = json.loads((EXPERIMENT / "authority-cases.json").read_text(encoding="utf-8"))
        oracles = json.loads((EXPERIMENT / "authority-oracles.json").read_text(encoding="utf-8"))
        expected_ids = {
            "standing-current", "one-off-only", "standing-target-drift",
            "unanswered-request", "explicit-source-only", "required-optional-conflict",
            "sync-without-behavior", "same-target-broader-effects",
        }
        self.assertEqual({case["id"] for case in cases}, expected_ids)
        self.assertEqual(set(oracles), expected_ids)
        with tempfile.TemporaryDirectory(prefix="shiploop-authority-packets-") as temp:
            output = Path(temp) / "packets"
            written = prepare_packets.prepare("authority", output)
            self.assertEqual(len(written), len(cases) * 2)
            for case in cases:
                with self.subTest(case=case["id"]):
                    self.assertTrue(oracles[case["id"]]["must"])
                    self.assertTrue(oracles[case["id"]]["must_not"])
                    packet = (output / f"{case['id']}-r1.md").read_text(encoding="utf-8")
                    self.assertIn(case["request"], packet)
                    self.assertIn(PROMPTS[case["stage"]], packet)
                    self.assertIn("delivery-authority.md", packet)
                    self.assertNotIn("authority-oracles.json", packet)
                    for criterion in oracles[case["id"]]["must"]:
                        self.assertNotIn(criterion, packet)
            with self.assertRaises(FileExistsError):
                prepare_packets.prepare("authority", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
