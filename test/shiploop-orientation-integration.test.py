#!/usr/bin/env python3
"""Public-CLI checks for reset-safe packet provenance and purpose navigation."""

from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_objectives as objectives  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class OrientationIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Composition avoids rediscovering all tests on an imported TestCase.
        fixture_class = runpy.run_path(str(ROOT / "test/shiploop-packets.test.py"))["PacketTests"]
        self.f = fixture_class()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.f.cli(
            "init", "--repo", str(self.f.repo), "--run-dir", str(self.f.run_dir),
            "--execution-mode", "legacy",
            "--prompt=Build a local CSV summary CLI; do not fabricate missing input.",
        )
        self.complete({"summary": "Baseline inspected; owner input is absent.", "baseline": "committed-head"})
        self.origin_action = self.f.state()["action"]["id"]
        self.candidate = {
            "summary": "Approach candidate; input-dependent quality is unassessed.",
            "body": "# Approach\n\nInspect owner CSV, plan expected outputs, then implement scoped CLI tests.\n",
        }
        self.initial_result = self.f.result("approach-source.md", self.candidate)
        self.f.cli("done", "--action", self.origin_action, "--result", self.initial_result)

    def complete(self, value):
        aid = self.f.state()["action"]["id"]
        return self.f.cli("done", "--action", aid, "--result", self.f.result(aid + ".md", value))

    def receipt(self):
        return store.read_record(self.f.run_dir / self.f.state()["objective"]["receipt"])

    def review(self):
        aid = self.f.state()["action"]["id"]
        self.f.cli("history", "--run-dir", str(self.f.run_dir), "--action", aid,
                   "--limit", "7", "--skip", "0", "--full")
        self.complete({
            "summary": "The initial review found missing input behavior to clarify.",
            "findings": [{"id": "F-INPUT", "severity": "material", "category": "edge-condition",
                          "summary": "Specify absent-input behavior."}],
            "assessment": {key: "Inspected the current approach and recorded the input gap."
                           for key in objectives.ASSESSMENT_KEYS},
            "history_assessment": "Read the full baseline commit; no earlier implementation exists.",
            "test_review": "Expected absent-input behavior must be specified before product tests.",
            "learnings": "An absent owner fixture cannot establish observed CSV behavior.",
        })
        return aid

    def test_real_callbacks_bind_origin_and_first_review_without_counting_a_cycle(self):
        rec = self.receipt()
        self.assertEqual(rec["origin"]["action_id"], self.origin_action)
        self.assertEqual(rec["origin"]["result_sha256"], protocol.digest(self.candidate))
        before = (self.f.run_dir / "state.md").read_bytes()
        packet = self.f.cli("next", "--run-dir", str(self.f.run_dir)).stdout
        self.assertIn(str(self.f.run_dir / "prompt.md"), packet)
        self.assertIn("--section prompt", packet)
        self.assertRegex(packet, r"not yet assessed|unassessed")
        self.assertIn("not approved", packet)
        self.assertEqual((self.f.run_dir / "state.md").read_bytes(), before)

        review_action = self.review()
        rec = self.receipt()
        self.assertEqual(rec["first_assessment"]["action_id"], review_action)
        self.assertEqual(rec["completed_passes"], [])
        self.assertEqual(self.f.state()["stage"], "objective-plan")

        before = (self.f.run_dir / "state.md").read_bytes()
        replay = self.f.cli("done", "--action", self.origin_action,
                            "--result", self.initial_result).stdout
        self.assertIn("Stage: objective-plan", replay)
        self.assertEqual((self.f.run_dir / "state.md").read_bytes(), before)

    def test_changed_candidate_retains_original_assessment_as_history(self):
        review_action = self.review()
        self.complete({"summary": "Plan the absent-input clarification.", "addresses": ["F-INPUT"],
                       "body": "# Plan\n\nReject absent input rather than fabricate data.\n",
                       "learnings": "The fix is an explicit expected outcome, not fabricated evidence."})
        changed = dict(self.candidate, body=self.candidate["body"] + "Reject absent input with a clear diagnostic.\n")
        self.complete({"summary": "Clarified the candidate.", "candidate": changed, "material": True,
                       "addresses": ["F-INPUT"], "resolutions": [{"id": "F-INPUT", "evidence": "Candidate now specifies rejection."}],
                       "test_changes": "Later product tests must assert the documented rejection.",
                       "learnings": "Changed meaning requires fresh assessment and checks."})
        quality = protocol.packet_orientation(self.f.run_dir, self.f.state())["quality"]
        self.assertEqual(quality["assessment"]["action_id"], review_action)
        self.assertFalse(quality["assessment"]["current_candidate_matches"])
        self.assertEqual(quality["initial_candidate"]["action_id"], self.origin_action)
        self.assertEqual(self.receipt()["completed_passes"], [])

    def test_corrupt_accepted_origin_blocks_orientation_without_mutating_cursor(self):
        self.review()
        before = (self.f.run_dir / "state.md").read_bytes()
        path = self.f.run_dir / "results" / f"{self.origin_action}.md"
        store.write_record(path, dict(self.candidate, summary="Altered after acceptance."))
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "shiploop"), "next", "--run-dir", str(self.f.run_dir)],
            cwd=self.f.repo, env=self.f.env, capture_output=True, text=True,
        )
        output = result.stdout + result.stderr
        self.assertRegex(output, r"(?:Blocked|ShipLoop blocked):")
        self.assertNotIn("Call this when done:", output)
        self.assertEqual((self.f.run_dir / "state.md").read_bytes(), before)

    def test_supporting_context_safe_return_executes_the_actual_cli(self):
        before = (self.f.run_dir / "state.md").read_bytes()
        output = self.f.cli("context", "--section", "prompt").stdout
        command = next(line.removeprefix("Safe return: ") for line in output.splitlines()
                       if line.startswith("Safe return: "))
        result = subprocess.run(shlex.split(command), cwd=self.f.repo, env=self.f.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: objective-review", result.stdout)
        self.assertIn(self.f.state()["action"]["id"], result.stdout)
        self.assertEqual((self.f.run_dir / "state.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
