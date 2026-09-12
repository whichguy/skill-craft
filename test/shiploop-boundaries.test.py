#!/usr/bin/env python3
"""Real-Git closure boundaries and lifecycle side-effect consistency."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_protocol as protocol  # noqa: E402


class ClosureBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-boundaries-")
        self.repo = Path(self.tmp.name).resolve()
        self.run = self.repo / ".shiploop"
        self.run.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q")
        self.git("config", "user.name", "Boundary Fixture")
        self.git("config", "user.email", "boundary@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.product = self.repo / "product.txt"
        self.product.write_text("reviewed result\n")
        self.git("add", "product.txt")
        self.git("commit", "-qm", "integrated product")
        self.receipt = {"status": "complete", "merged_sha": self.git("rev-parse", "HEAD")}
        self.ledger_gaps = []
        self.core = SimpleNamespace(
            git_run=self.git_run,
            steps_by_id=lambda _root: {"S1": {}},
            load_receipt=lambda _root, _sid: self.receipt,
            residual_gaps=lambda _state, _dest: self.ledger_gaps,
        )
        self.state = {"repo_root": str(self.repo)}

    def tearDown(self):
        self.tmp.cleanup()

    def git_run(self, repo, *args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=self.env)

    def git(self, *args):
        result = self.git_run(self.repo, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def check(self):
        protocol.require_outer_product_baseline(self.core, self.run, self.state)

    def test_integrated_tree_and_same_tree_audits_pass_with_run_metadata(self):
        (self.run / "result.md").write_text("durable metadata\n")
        self.check()
        self.git("commit", "--allow-empty", "-qm", "outer audit only")
        self.check()

    def test_unreviewed_dirty_or_committed_product_changes_cannot_close(self):
        self.product.write_text("late unreviewed correction\n")
        with self.assertRaisesRegex(protocol.ProtocolError, "unreviewed checkout"):
            self.check()
        self.git("add", "product.txt")
        self.git("commit", "-qm", "unreviewed change")
        with self.assertRaisesRegex(protocol.ProtocolError, "product changed"):
            self.check()

    def test_hidden_index_change_cannot_close(self):
        self.product.write_text("staged change\n")
        self.git("add", "product.txt")
        self.product.write_text("reviewed result\n")
        with self.assertRaisesRegex(protocol.ProtocolError, "unreviewed checkout"):
            self.check()

    def test_only_certified_coverage_ledger_change_is_allowed(self):
        (self.repo / "REVIEW_CONVERGE.md").write_text("fixture certified ledger\n")
        self.git("add", "REVIEW_CONVERGE.md")
        self.git("commit", "-qm", "coverage ledger")
        self.check()
        self.ledger_gaps = ["ledger is not bound to the selected plan"]
        with self.assertRaisesRegex(protocol.ProtocolError, "ledger change is not certified"):
            self.check()

    def test_missing_integration_evidence_cannot_close(self):
        self.receipt.pop("merged_sha")
        with self.assertRaisesRegex(protocol.ProtocolError, "integration anchor"):
            self.check()


class LifecycleConsistencyTests(unittest.TestCase):
    def test_none_and_outer_loop_forbid_dag_side_effects(self):
        for activity in ("preparation", "publish"):
            for disposition in ("none", "outer-before" if activity == "preparation" else "outer-loop"):
                with self.subTest(activity=activity, disposition=disposition):
                    lifecycle = {"preparation": "none", "publish": "none", activity: disposition}
                    with self.assertRaisesRegex(protocol.ProtocolError, "forbids a DAG"):
                        protocol.validate_lifecycle_steps({"steps": [{"activity": activity}]}, lifecycle)

    def test_dag_requires_its_step_and_accepts_consistent_contract(self):
        with self.assertRaisesRegex(protocol.ProtocolError, "requires a DAG"):
            protocol.validate_lifecycle_steps({"steps": [{}]}, {"preparation": "dag", "publish": "none"})
        protocol.validate_lifecycle_steps(
            {"steps": [{"activity": "preparation"}, {"activity": "publish"}]},
            {"preparation": "dag", "publish": "dag"},
        )


class PendingObligationMapBoundaryTests(unittest.TestCase):
    """Keep post-inner map shape errors local to their validator."""

    def setUp(self):
        self.root = Path("/pending-obligation-map-fixture")
        self.core = SimpleNamespace(
            load_receipt=lambda _root, step_id: (
                {"status": "complete"} if step_id == "S1" else None
            )
        )
        self.obligations = [{"id": "K-PENDING-001", "scope": ["S2"]}]

    @staticmethod
    def dag(*, changed_s2=False):
        return {
            "steps": [
                {"id": "S1", "statement": "Already completed work.", "inputs": []},
                {
                    "id": "S2",
                    "statement": (
                        "Changed pending work for the mapped obligation."
                        if changed_s2
                        else "Pending work before the mapped obligation."
                    ),
                    "inputs": [],
                },
            ]
        }

    def validate(self, mapping, *, revised=None):
        return protocol.validate_pending_obligation_map(
            self.core,
            self.root,
            self.dag(),
            revised or self.dag(),
            self.obligations,
            mapping,
        )

    def test_map_cannot_point_to_an_unchanged_pending_step(self):
        with self.assertRaisesRegex(
            protocol.ProtocolError, "not changed or added"
        ):
            self.validate([{"id": "K-PENDING-001", "steps": ["S2"]}])

    def test_map_cannot_point_to_a_completed_step(self):
        with self.assertRaisesRegex(protocol.ProtocolError, "only target pending"):
            self.validate([{"id": "K-PENDING-001", "steps": ["S1"]}])

    def test_map_cannot_replace_an_open_obligation_id(self):
        with self.assertRaisesRegex(
            protocol.ProtocolError, "retain every open obligation ID"
        ):
            self.validate([{"id": "K-UNRELATED-001", "steps": ["S2"]}])


if __name__ == "__main__":
    unittest.main()
