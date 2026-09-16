#!/usr/bin/env python3
"""Execution-free checks for the consumer-delivery local fake boundary."""

from __future__ import annotations

import unittest

from fake_deployment import FakeDeployment


class FakeDeploymentTests(unittest.TestCase):
    def test_stale_served_artifact_is_not_current_consumer_behavior(self) -> None:
        target = FakeDeployment("candidate-2", "candidate-1")

        self.assertEqual(target.artifact_identity()["status"], "stale")
        self.assertEqual(target.consumer_behavior(), {
            "kind": "consumer_behavior",
            "status": "blocked",
            "reason": "served artifact is stale",
        })
        self.assertEqual(target.operations, [])

    def test_successful_update_with_login_preserves_effect_without_retry(self) -> None:
        target = FakeDeployment("candidate-2", "candidate-1", ui_mode="login")

        self.assertEqual(
            target.update("private-source-sync"),
            {"kind": "operation_effect", "status": "succeeded"},
        )
        self.assertEqual(target.artifact_identity()["status"], "current")
        self.assertEqual(target.consumer_behavior()["status"], "blocked")
        self.assertEqual(len(target.operations), 1)
        self.assertEqual(target.forbidden_operations, 0)

    def test_current_artifact_does_not_replace_failed_visual_interaction(self) -> None:
        target = FakeDeployment("candidate-2", "candidate-2", ui_mode="broken")

        self.assertEqual(target.artifact_identity()["status"], "current")
        self.assertEqual(target.consumer_behavior(), {
            "kind": "consumer_behavior",
            "status": "failed",
            "reason": "visual interaction failed",
        })

    def test_unknown_operation_outcome_is_not_retried_by_the_fixture(self) -> None:
        target = FakeDeployment("candidate-2", "candidate-1")

        self.assertEqual(
            target.update("private-source-sync", outcome="unknown"),
            {"kind": "operation_effect", "status": "unknown"},
        )
        self.assertEqual(len(target.operations), 1)
        self.assertEqual(target.artifact_identity()["status"], "stale")
        self.assertEqual(target.consumer_behavior()["status"], "blocked")

    def test_forbidden_operation_is_visible_and_does_not_change_target(self) -> None:
        target = FakeDeployment("candidate-2", "candidate-1")

        self.assertEqual(
            target.update("versioned-promotion"),
            {"kind": "operation_effect", "status": "forbidden"},
        )
        self.assertEqual(target.forbidden_operations, 1)
        self.assertEqual(target.served_candidate, "candidate-1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
