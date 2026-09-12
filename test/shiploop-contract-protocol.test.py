#!/usr/bin/env python3
"""Focused real-Git checks for ShipLoop Ready/Done protocol adapters.

The adapter owns the runtime binding that the pure contract validator cannot
observe: persisted check records, Git ancestry, working-tree bytes, and the
current-step slice of Markdown-authoritative knowledge.  These tests use a
small real Git repository so an audit-only commit is distinguishable from a
product change that happens to be reverted later.
"""

from __future__ import annotations

from copy import deepcopy
import importlib.machinery
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CONTRACT_FIXTURES = ROOT / "test" / "shiploop-contracts.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_contract_fixtures():
    """Reuse the public step/evidence fixture rather than retyping a contract."""
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_contract_fixtures", str(CONTRACT_FIXTURES)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {CONTRACT_FIXTURES}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


FIXTURES = load_contract_fixtures()

import shiploop_contract_protocol as protocol  # noqa: E402
import shiploop_evidence as evidence  # noqa: E402
import shiploop_knowledge as knowledge  # noqa: E402
import shiploop_store as store  # noqa: E402


class RealGitCore:
    """The narrow core surface consumed by the adapter under test."""

    def __init__(self, selected_step: dict):
        self.selected_step = deepcopy(selected_step)

    def steps_by_id(self, _root: Path) -> dict[str, dict]:
        return {self.selected_step["id"]: deepcopy(self.selected_step)}

    def git_run(self, worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(worktree), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


class ContractProtocolAdapterTests(unittest.TestCase):
    """Use durable Markdown and Git instead of mocked identities."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.run_dir = base / "run"
        self.run_dir.mkdir()
        self.worktree = base / "product"
        self.worktree.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "shiploop-test@example.invalid")
        self.git("config", "user.name", "ShipLoop Contract Test")
        (self.worktree / "input.txt").write_text("baseline input\n", encoding="utf-8")
        self.git("add", "input.txt")
        self.git("commit", "-qm", "Initial fixture")

        self.core = RealGitCore(FIXTURES.step())
        self.state = {
            "active_step": "S2",
            "step_contract_protocol_version": 1,
            "environment_sha256": "e" * 64,
        }
        self.rec: dict = {"worktree": str(self.worktree)}
        self.ledger = knowledge.empty_ledger()
        self.write_ledger(self.ledger, action="")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.worktree), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            self.fail("Git command failed: " + completed.stderr.strip())
        return completed.stdout.strip()

    def source(self, action: str) -> dict:
        return {
            "action": action,
            "iteration": "I1",
            "check_action": "check-I1",
            "worktree_fingerprint": "fixture-fingerprint",
            "step": "S2",
            "reported_by": "host",
            "recorded_at": "2026-09-11T00:00:00Z",
        }

    def write_ledger(self, ledger: dict, *, action: str) -> None:
        """Write the real Markdown ledger and its matching state binding."""
        body = knowledge.render(ledger)
        (self.run_dir / "knowledge.md").write_text(body, encoding="utf-8")
        self.ledger = ledger
        self.state.update(
            knowledge_revision=ledger["revision"],
            knowledge_sha256=knowledge.sha256_bytes(body.encode("utf-8")),
            knowledge_action_id=action if ledger["revision"] else "",
        )

    def add_discovery(
        self,
        *,
        identifier: str,
        observation: str,
        scope: list[str],
        disposition: str,
        action: str,
    ) -> dict:
        result = knowledge.validate_result(
            {
                "summary": f"Record {identifier} for the durable fixture.",
                "knowledge_revision": self.ledger["revision"],
                "learnings": "Preserve scoped environmental facts in Markdown.",
                "discoveries": [
                    {
                        "id": identifier,
                        "domain": "environment",
                        "observation": observation,
                        "evidence": "fixture environment observation",
                        "scope": scope,
                        "disposition": disposition,
                        "rationale": "The fixture must exercise current and future step scopes.",
                        "revalidate": "Inspect the selected scope on the next cold resume.",
                    }
                ],
            },
            expected_revision=self.ledger["revision"],
            step_ids={"S2", "S3"},
        )
        return knowledge.apply_result(self.ledger, result, self.source(action))

    def write_check(self, value: dict) -> dict:
        action = value["results"]["action_id"]
        store.write_record(self.run_dir / "checks" / f"{action}.md", value)
        return value

    def artifact_fingerprint(self) -> str:
        try:
            excluded = [str(self.run_dir.relative_to(self.worktree))]
        except ValueError:
            excluded = []
        return evidence.fingerprint(self.worktree, excluded=excluded)

    def planning_check(self) -> dict:
        value = deepcopy(FIXTURES.planning_verify_record())
        value.update(
            git_baseline=self.git("rev-parse", "HEAD"),
            worktree_fingerprint=self.artifact_fingerprint(),
        )
        return self.write_check(value)

    def product_check(self) -> dict:
        value = deepcopy(FIXTURES.verify_record())
        value.update(
            git_baseline=self.git("rev-parse", "HEAD"),
            worktree_fingerprint=self.artifact_fingerprint(),
        )
        return self.write_check(value)

    def certify_ready(self) -> dict:
        saved = protocol.capture(
            self.core,
            self.run_dir,
            self.state,
            self.rec,
            FIXTURES.ready_evidence(),
            phase="ready",
            check=self.planning_check(),
        )
        self.rec["contract_ready"] = saved
        return saved

    def certify_done(self) -> dict:
        (self.worktree / "result.txt").write_text("expected result\n", encoding="utf-8")
        self.git("add", "result.txt")
        self.git("commit", "-qm", "Create expected result")
        saved = protocol.capture(
            self.core,
            self.run_dir,
            self.state,
            self.rec,
            FIXTURES.done_evidence(),
            phase="final-verify",
            check=self.product_check(),
        )
        self.rec["contract_done"] = saved
        return saved

    def test_capture_ready_and_require_ready_bind_real_persisted_check(self) -> None:
        saved = self.certify_ready()

        self.assertEqual(saved["step"], "S2")
        self.assertEqual(saved["evidence"], FIXTURES.ready_evidence())
        self.assertEqual(
            saved["record"]["validated_receipt"]["discharged"]["ready"],
            ["R-INPUT-001"],
        )
        protocol.require_ready(self.core, self.run_dir, self.state, self.rec)

    def test_ready_binding_excludes_a_custom_run_directory_inside_the_worktree(self) -> None:
        inside_worktree = self.worktree / ".shiploop-custom-run"
        shutil.move(str(self.run_dir), inside_worktree)
        self.run_dir = inside_worktree

        self.certify_ready()

        protocol.require_ready(self.core, self.run_dir, self.state, self.rec)

    def test_require_ready_rejects_tampered_and_missing_check_evidence(self) -> None:
        self.certify_ready()
        action = "step-plan-verify-S2-1"
        check_path = self.run_dir / "checks" / f"{action}.md"
        altered = store.read_record(check_path)
        altered["results"]["checks"][0]["status"] = "failed"
        store.write_record(check_path, altered)
        with self.assertRaisesRegex(protocol.ContractGateError, "check evidence changed"):
            protocol.require_ready(self.core, self.run_dir, self.state, self.rec)

        self.certify_ready()
        check_path.unlink()
        with self.assertRaisesRegex(protocol.ContractGateError, "check evidence"):
            protocol.require_ready(self.core, self.run_dir, self.state, self.rec)

    def test_done_revalidation_allows_audit_only_unchanged_tree_commit(self) -> None:
        saved = self.certify_done()
        certified_head = saved["record"]["envelope"]["head"]
        self.git("commit", "--allow-empty", "-qm", "Audit: record unchanged validation")
        current_head = self.git("rev-parse", "HEAD")

        rebound = protocol.revalidate_done(
            self.core, self.run_dir, self.state, self.rec, phase="post-inner"
        )

        self.assertEqual(rebound["record"]["envelope"]["head"], current_head)
        self.assertEqual(
            rebound["record"]["validated_receipt"]["status"],
            "done-evidence-certified",
        )
        self.assertNotEqual(certified_head, current_head)

    def test_done_revalidation_rejects_product_change_even_if_reverted(self) -> None:
        self.certify_done()
        result = self.worktree / "result.txt"
        result.write_text("accidental product change\n", encoding="utf-8")
        self.git("add", "result.txt")
        self.git("commit", "-qm", "Accidental result change")
        result.write_text("expected result\n", encoding="utf-8")
        self.git("add", "result.txt")
        self.git("commit", "-qm", "Restore expected result")

        with self.assertRaisesRegex(protocol.ContractGateError, "changed the product tree"):
            protocol.revalidate_done(
                self.core, self.run_dir, self.state, self.rec, phase="post-inner"
            )

    def test_done_revalidation_rejects_staged_index_change_hidden_by_worktree_bytes(self) -> None:
        self.certify_done()
        result = self.worktree / "result.txt"
        baseline_fingerprint = evidence.fingerprint(self.worktree)
        # Stage a different blob, then restore only the worktree file. The
        # source fingerprint intentionally cannot see index blob contents, so
        # the protocol must also reject the non-clean Git state.
        result.write_text("staged-only product change\n", encoding="utf-8")
        self.git("add", "result.txt")
        result.write_text("expected result\n", encoding="utf-8")
        self.assertEqual(baseline_fingerprint, evidence.fingerprint(self.worktree))
        self.assertTrue(self.git("status", "--porcelain"))

        with self.assertRaisesRegex(protocol.ContractGateError, "uncommitted"):
            protocol.revalidate_done(
                self.core, self.run_dir, self.state, self.rec, phase="post-inner"
            )

    def test_done_capture_rejects_staged_index_change_before_certification(self) -> None:
        result = self.worktree / "result.txt"
        result.write_text("expected result\n", encoding="utf-8")
        self.git("add", "result.txt")
        self.git("commit", "-qm", "Create expected result")
        result.write_text("staged-only product change\n", encoding="utf-8")
        self.git("add", "result.txt")
        result.write_text("expected result\n", encoding="utf-8")

        with self.assertRaisesRegex(protocol.ContractGateError, "uncommitted"):
            protocol.capture(
                self.core,
                self.run_dir,
                self.state,
                self.rec,
                FIXTURES.done_evidence(),
                phase="final-verify",
                check=self.product_check(),
            )

    def test_done_revalidation_rejects_missing_persisted_final_check(self) -> None:
        self.certify_done()
        (self.run_dir / "checks" / "verify-S2-1.md").unlink()

        with self.assertRaisesRegex(protocol.ContractGateError, "check evidence"):
            protocol.revalidate_done(
                self.core, self.run_dir, self.state, self.rec, phase="post-inner"
            )

    def test_current_step_environment_observation_invalidates_ready_certificate(self) -> None:
        initial = self.add_discovery(
            identifier="current-environment",
            observation="The selected input fixture is readable.",
            scope=["S2"],
            disposition="informational",
            action="current-environment-1",
        )
        self.write_ledger(initial, action="current-environment-1")
        before = protocol.environment_identity(self.run_dir, self.state)
        self.certify_ready()

        changed = self.add_discovery(
            identifier="current-environment",
            observation="The selected input fixture now requires a different parser.",
            scope=["S2"],
            disposition="informational",
            action="current-environment-2",
        )
        self.write_ledger(changed, action="current-environment-2")

        self.assertNotEqual(before, protocol.environment_identity(self.run_dir, self.state))
        with self.assertRaisesRegex(protocol.ContractGateError, "environment changed"):
            protocol.require_ready(self.core, self.run_dir, self.state, self.rec)

    def test_scheduling_unrelated_future_obligation_keeps_ready_certificate_valid(self) -> None:
        self.certify_ready()
        before = protocol.environment_identity(self.run_dir, self.state)
        future = self.add_discovery(
            identifier="future-contract-check",
            observation="A later S3 check must be scheduled before that step starts.",
            scope=["S3"],
            disposition="pending-replan",
            action="future-observation",
        )
        self.ledger = future
        scheduled = knowledge.map_pending_obligations(
            future,
            {"future-contract-check": ["S3"]},
            self.source("future-map"),
        )
        self.write_ledger(scheduled, action="future-map")

        self.assertEqual(before, protocol.environment_identity(self.run_dir, self.state))
        protocol.require_ready(self.core, self.run_dir, self.state, self.rec)


if __name__ == "__main__":
    unittest.main()
