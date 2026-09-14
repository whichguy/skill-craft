#!/usr/bin/env python3
"""Protocol-level managed SYS invalidation checks using real check evidence."""

from __future__ import annotations

from copy import deepcopy
import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CONTRACTS = ROOT / "test" / "shiploop-contracts.test.py"
CONTRACT_PROTOCOL = ROOT / "test" / "shiploop-contract-protocol.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load fixture {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


FIXTURES = load_module("shiploop_managed_invalidation_contracts", CONTRACTS)
CONTRACT_FIXTURES = load_module(
    "shiploop_managed_invalidation_contract_protocol", CONTRACT_PROTOCOL
)

import shiploop_contract_protocol as contract_protocol  # noqa: E402
import shiploop_invalidation as invalidation  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


class ManagedCore:
    """Only the protocol surface exercised by SYS closure and invalidation."""

    def __init__(self, fixture, dag, receipts):
        self.fixture = fixture
        self.dag = dag
        self.receipts = receipts

    def load_dag(self, _root):
        return deepcopy(self.dag)

    def load_receipt(self, _root, step_id):
        return self.receipts.get(step_id)

    def steps_by_id(self, _root):
        return {step["id"]: deepcopy(step) for step in self.dag["steps"]}

    def produces_texts(self, value):
        return [value] if isinstance(value, str) else list(value)

    def git_run(self, worktree, *args):
        return subprocess.run(
            ["git", "-C", str(worktree), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


class ManagedSystemInvalidationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = CONTRACT_FIXTURES.ContractProtocolAdapterTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.original_step = deepcopy(FIXTURES.step())
        self.original_step["activity"] = "system-test-pre"
        self.original_step["inputs"] = [
            {"need": "repository baseline exists", "from": None}
        ]
        self.case = {
            "id": "SYS-PRE-001",
            "phase": "pre_deployment",
            "requirement": "The integrated local system boundary is checked before publication.",
            "expected_outcome": self.original_step["contract"]["tests"][0]["expected_outcome"],
            "environment": "isolated local fixture",
            "prerequisites": [],
            "test_step": "S2",
            "test_id": "T-RESULT-001",
            "deployment_step": None,
        }
        self.dag = {
            "steps": [self.original_step],
            "system_tests": {
                "version": 1,
                "phases": {
                    "pre_deployment": {
                        "status": "required",
                        "reason": "The fixture checks the assembled local system boundary.",
                    },
                    "post_deployment": {
                        "status": "not-applicable",
                        "reason": "The fixture has no deployment target.",
                    },
                },
                "cases": [self.case],
            },
        }
        self.fixture.state.update(
            active_step="S2",
            managed_improve_protocol_version=1,
            system_test_protocol_version=1,
            repo_root=str(self.fixture.worktree),
        )
        store.write_record(
            self.fixture.run_dir / "lifecycle.md",
            {"publish": "none"},
            title="Fixture lifecycle",
        )
        self.fixture.certify_done()
        merged = self.fixture.git("rev-parse", "HEAD")
        self.fixture.rec.update(
            id="S2",
            status="complete",
            merged_sha=merged,
            contract_closure={"fully_closed": True, "integrated_sha": merged},
        )
        self.receipts = {"S2": self.fixture.rec}
        self.core = ManagedCore(self.fixture, self.dag, self.receipts)
        self.fixture.rec["system_test_proofs"] = {
            self.case["id"]: invalidation.capture_system_proof(
                self.dag["system_tests"],
                self.dag["steps"],
                self.receipts,
                case_id=self.case["id"],
                product_identity=protocol.managed_product_identity(
                    self.core, self.fixture.run_dir, self.fixture.state
                ),
            )
        }
        self.original_proof = deepcopy(self.fixture.rec["system_test_proofs"])

    def add_corrective_product_merge(self):
        path = self.fixture.worktree / "corrective.txt"
        path.write_text("corrected behavior\n", encoding="utf-8")
        self.fixture.git("add", "corrective.txt")
        self.fixture.git("commit", "-qm", "Correct product behavior")
        merged = self.fixture.git("rev-parse", "HEAD")
        self.dag["steps"].append(
            {
                "id": "FIX",
                "activity": "implementation",
                "produces": ["corrected product behavior"],
                "inputs": [],
            }
        )
        self.receipts["FIX"] = {
            "status": "complete",
            "merged_sha": merged,
            "final_head": merged,
            "contract_done": {"fixture": "corrective product proof"},
            "contract_closure": {"fully_closed": True, "integrated_sha": merged},
        }

    def add_current_sys_owner(
        self,
        *,
        step_id,
        case_id,
        requirement,
        author_path=None,
    ):
        step = deepcopy(self.original_step)
        step["id"] = step_id
        step["inputs"] = [{"need": "repository baseline exists", "from": None}]
        self.dag["steps"].append(step)
        replacement = deepcopy(self.case)
        replacement.update(id=case_id, test_step=step_id, requirement=requirement)
        self.dag["system_tests"]["cases"].append(replacement)

        # A suite may author its bytes before the final SYS pass.  A later
        # revalidation owner deliberately reuses those bytes and records only
        # an audit commit, so it does not invalidate a sibling fresh proof.
        if author_path is not None:
            target = self.fixture.worktree / author_path
            target.write_text("current system test fixture\n", encoding="utf-8")
            self.fixture.git("add", author_path)
            self.fixture.git("commit", "-qm", f"Author {case_id} system test")
        else:
            self.fixture.git(
                "commit", "--allow-empty", "-qm", f"Record {case_id} current system evidence"
            )
        self.fixture.core.selected_step = step
        self.fixture.state["active_step"] = step_id
        rec = {"id": step_id, "worktree": str(self.fixture.worktree)}
        check = deepcopy(FIXTURES.verify_record())
        check["results"]["action"] = f"verify-{step_id}-1"
        check["results"]["action_id"] = f"verify-{step_id}-1"
        check["git_baseline"] = self.fixture.git("rev-parse", "HEAD")
        check["worktree_fingerprint"] = self.fixture.artifact_fingerprint()
        self.fixture.write_check(check)
        rec["contract_done"] = contract_protocol.capture(
            self.fixture.core,
            self.fixture.run_dir,
            self.fixture.state,
            rec,
            FIXTURES.done_evidence(),
            phase="final-verify",
            check=check,
        )
        merged = self.fixture.git("rev-parse", "HEAD")
        rec.update(
            status="complete",
            merged_sha=merged,
            contract_closure={"fully_closed": True, "integrated_sha": merged},
        )
        self.receipts[step_id] = rec
        rec["system_test_proofs"] = {
            replacement["id"]: invalidation.capture_system_proof(
                self.dag["system_tests"],
                self.dag["steps"],
                self.receipts,
                case_id=replacement["id"],
                product_identity=protocol.managed_product_identity(
                    self.core, self.fixture.run_dir, self.fixture.state
                ),
            )
        }
        return replacement, rec

    def add_equivalent_current_sys_case(self):
        return self.add_current_sys_owner(
            step_id="S3",
            case_id="SYS-PRE-002",
            requirement=self.case["requirement"],
        )

    def test_later_product_merge_blocks_quality_until_new_equivalent_sys_proof_maps_old_case(self):
        self.add_corrective_product_merge()
        current = protocol.managed_system_invalidation(
            self.core, self.fixture.run_dir, self.fixture.state
        )
        self.assertIsNotNone(current)
        self.assertEqual(current["decision"]["stale_case_ids"], ["SYS-PRE-001"])
        with self.assertRaisesRegex(protocol.ProtocolError, "stale SYS evidence requires"):
            protocol.require_system_test_closure(
                self.core, self.fixture.run_dir, self.fixture.state
            )
        self.assertEqual(self.fixture.rec["system_test_proofs"], self.original_proof)

        replacement, _rec = self.add_equivalent_current_sys_case()
        current = protocol.managed_system_invalidation(
            self.core, self.fixture.run_dir, self.fixture.state
        )
        self.assertEqual(current["decision"]["stale_case_ids"], ["SYS-PRE-001"])
        result = {
            "system_test_revalidation": {
                "version": 1,
                "product_content_identity_sha256": current["decision"][
                    "current_product_content_identity_sha256"
                ],
                "replacements": [
                    {
                        "stale_case_id": "SYS-PRE-001",
                        "replacement_case_id": replacement["id"],
                    }
                ],
            }
        }
        protocol.require_system_test_closure(
            self.core, self.fixture.run_dir, self.fixture.state, result=result
        )
        self.assertEqual(self.fixture.rec["system_test_proofs"], self.original_proof)

    def test_certified_review_ledger_commit_is_excluded_but_later_product_bytes_still_stale_sys_proof(self):
        ledger = self.fixture.worktree / "REVIEW_CONVERGE.md"
        ledger.write_text("# Certified review coverage\n", encoding="utf-8")
        self.fixture.git("add", "REVIEW_CONVERGE.md")
        self.fixture.git("commit", "-qm", "Record certified review coverage")
        after_ledger = protocol.managed_system_invalidation(
            self.core, self.fixture.run_dir, self.fixture.state
        )
        self.assertIsNotNone(after_ledger)
        self.assertEqual(after_ledger["decision"]["stale_case_ids"], [])
        self.assertTrue(
            after_ledger["decision"]["decisions"]["SYS-PRE-001"]["changes"][
                "revision_changed"
            ]
        )

        self.add_corrective_product_merge()
        after_product = protocol.managed_system_invalidation(
            self.core, self.fixture.run_dir, self.fixture.state
        )
        self.assertEqual(after_product["decision"]["stale_case_ids"], ["SYS-PRE-001"])
        self.assertEqual(
            after_product["decision"]["decisions"]["SYS-PRE-001"]["changes"][
                "receipts"
            ]["added"],
            ["FIX"],
        )

    def test_author_all_sys_suites_then_revalidate_stale_a_without_new_bytes_reaches_a_finite_release_state(self):
        # S2/A already captured a real SYS proof.  Authoring the independent
        # S3/B suite changes product bytes, which correctly makes A stale.
        b_case, _b_receipt = self.add_current_sys_owner(
            step_id="S3",
            case_id="SYS-PRE-002",
            requirement="The additional system journey reports the exact system output.",
            author_path="tests-system-b.txt",
        )
        after_b = protocol.managed_system_invalidation(
            self.core, self.fixture.run_dir, self.fixture.state
        )
        self.assertEqual(after_b["decision"]["stale_case_ids"], ["SYS-PRE-001"])
        self.assertEqual(after_b["decision"]["fresh_case_ids"], [b_case["id"]])

        # S4 is a new equivalent A owner.  It runs against the current product
        # but reuses the suites already authored by S2 and S3; its audit-only
        # merge leaves B's product content identity fresh.
        new_a, _new_a_receipt = self.add_current_sys_owner(
            step_id="S4",
            case_id="SYS-PRE-003",
            requirement=self.case["requirement"],
        )
        current = protocol.managed_system_invalidation(
            self.core, self.fixture.run_dir, self.fixture.state
        )
        self.assertEqual(current["decision"]["stale_case_ids"], ["SYS-PRE-001"])
        self.assertEqual(
            current["decision"]["fresh_case_ids"],
            ["SYS-PRE-002", "SYS-PRE-003"],
        )
        protocol.require_system_test_closure(
            self.core,
            self.fixture.run_dir,
            self.fixture.state,
            result={
                "system_test_revalidation": {
                    "version": 1,
                    "product_content_identity_sha256": current["decision"][
                        "current_product_content_identity_sha256"
                    ],
                    "replacements": [
                        {
                            "stale_case_id": "SYS-PRE-001",
                            "replacement_case_id": new_a["id"],
                        }
                    ],
                }
            },
        )
        self.assertEqual(self.fixture.rec["system_test_proofs"], self.original_proof)

    def test_original_sys_proof_cannot_be_rewritten_to_hide_receipt_tampering(self):
        self.fixture.rec["contract_done"]["check_sha256"] = "0" * 64
        with self.assertRaisesRegex(protocol.ProtocolError, "check evidence changed or is missing"):
            protocol.require_system_test_closure(
                self.core, self.fixture.run_dir, self.fixture.state
            )
        self.assertEqual(self.fixture.rec["system_test_proofs"], self.original_proof)

    def test_duplicate_or_foreign_owner_cannot_replace_original_sys_snapshot(self):
        self.dag["steps"].append(
            {
                "id": "FOREIGN",
                "activity": "implementation",
                "produces": ["foreign fixture output"],
                "inputs": [],
            }
        )
        duplicate = {
            "id": "FOREIGN",
            "status": "complete",
            "system_test_proofs": deepcopy(self.original_proof),
        }
        self.receipts["FOREIGN"] = duplicate
        with self.assertRaisesRegex(protocol.ProtocolError, "one original owner"):
            protocol.managed_system_invalidation(
                self.core, self.fixture.run_dir, self.fixture.state
            )


if __name__ == "__main__":
    unittest.main()
