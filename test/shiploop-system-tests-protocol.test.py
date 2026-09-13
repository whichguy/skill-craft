#!/usr/bin/env python3
"""Narrow protocol evidence for the DAG-owned system-test catalog."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


def load_module(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


CONTRACT_FIXTURES = load_module(
    "shiploop_system_test_contract_fixtures",
    ROOT / "test" / "shiploop-contracts.test.py",
)
CONTRACT_PROTOCOL_FIXTURES = load_module(
    "shiploop_system_test_contract_protocol_fixtures",
    ROOT / "test" / "shiploop-contract-protocol.test.py",
)


def catalog(*, required_pre: bool = False) -> dict:
    return {
        "version": 1,
        "phases": {
            "pre_deployment": {
                "status": "required" if required_pre else "not-applicable",
                "reason": "The local fixture selects only evidence-backed system test phases.",
            },
            "post_deployment": {
                "status": "not-applicable",
                "reason": "The local fixture has no authorized deployment boundary.",
            },
        },
        "cases": [],
    }


class CatalogCore:
    def __init__(self, dag: dict, receipts: dict[str, dict] | None = None):
        self.dag = dag
        self.receipts = receipts or {}

    def load_dag(self, _root):
        return deepcopy(self.dag)

    def load_receipt(self, _root, step_id):
        return self.receipts.get(step_id)


class SystemTestProtocolTests(unittest.TestCase):
    def _replan_inputs(self, *, owner_activity="system-test-pre", include_owner=True):
        old = {
            "steps": [{"id": "BASE", "activity": "implementation"}],
            "system_tests": {"cases": []},
        }
        owner = {"id": "S3", "activity": owner_activity}
        new = deepcopy(old)
        if include_owner:
            new["steps"].append(owner)
        new["system_tests"]["cases"] = [
            {"id": "SYS-PRE-003", "test_step": "S3"}
        ]
        return old, new

    def _require_replan(self, old, new, *, pending=(), mapping=()):
        root = Path(tempfile.mkdtemp(prefix="shiploop-system-replan-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        state = {"system_test_pending": list(pending)} if pending else {}
        result = {
            "plan_decision": "revise",
            "system_test_review": {
                "decision": "revise",
                "evidence": "A global test requirement changed and needs a mapped correction.",
                "discovery_ids": list(pending),
            },
            "pending_obligation_map": list(mapping),
        }
        writes = {"backchain/plan.md": store.dumps(new, "Revised DAG")}
        protocol.require_system_test_replan(CatalogCore(old), root, state, result, writes)
        return state

    def test_init_marker_and_cold_context_use_authoritative_plan_not_stale_view(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-system-context-") as temp:
            base = Path(temp)
            repo = base / "repo"
            repo.mkdir()
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            for args in (
                ("init", "-q"),
                ("config", "user.email", "fixture@example.invalid"),
                ("config", "user.name", "Fixture"),
                ("commit", "--allow-empty", "-qm", "baseline"),
            ):
                completed = subprocess.run(
                    ["git", "-C", str(repo), *args],
                    capture_output=True,
                    text=True,
                    env=env,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
            run = repo / ".shiploop"
            init = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "init",
                    "--repo",
                    str(repo),
                    "--prompt",
                    "Plan a bounded local fixture.",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            state = store.read_record(run / "state.md")
            self.assertEqual(state["system_test_protocol_version"], 1)
            dag = {"steps": [], "system_tests": catalog()}
            plan = run / "backchain" / "plan.md"
            plan.parent.mkdir()
            store.write_record(plan, dag, title="Fixture authoritative DAG")
            store.write_record(
                run / "lifecycle.md", {"publish": "none"}, title="Fixture lifecycle"
            )
            state["plan_sha256"] = hashlib.sha256(plan.read_bytes()).hexdigest()
            store.write_record(run / "state.md", state, title="ShipLoop state")
            (run / "system-test-requirements.md").write_text(
                "STALE DERIVATIVE", encoding="utf-8"
            )
            output = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "context",
                    "--run-dir",
                    str(run),
                    "--section",
                    "system-test-requirements",
                    "--limit",
                    "8000",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertIn("Authoritative catalog", output.stdout)
            self.assertNotIn("STALE DERIVATIVE", output.stdout)

    def test_required_new_run_rejects_missing_catalog_and_legacy_context_is_honest(
        self,
    ):
        root = Path(tempfile.mkdtemp(prefix="shiploop-system-legacy-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        store.write_record(
            root / "lifecycle.md", {"publish": "none"}, title="Fixture lifecycle"
        )
        core = CatalogCore({"steps": []})
        with self.assertRaisesRegex(protocol.ProtocolError, "catalog is required"):
            protocol.system_test_catalog(
                core, root, {"system_test_protocol_version": 1}
            )
        plan = root / "backchain" / "plan.md"
        plan.parent.mkdir()
        store.write_record(plan, {"steps": []}, title="Legacy DAG")
        with self.assertRaisesRegex(
            protocol.ProtocolError, "legacy run has no system-test catalog"
        ):
            protocol.system_test_context(
                core,
                root,
                {"plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest()},
            )

    def test_system_test_catalog_rejects_malformed_prior_dags(self):
        root = Path(tempfile.mkdtemp(prefix="shiploop-system-prior-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        store.write_record(
            root / "lifecycle.md", {"publish": "none"}, title="Fixture lifecycle"
        )
        core = CatalogCore({"steps": [], "system_tests": catalog()})
        for prior, message in (
            ([], "previous system-test DAG must have a steps list"),
            ({"steps": "not-a-list"}, "previous system-test DAG must have a steps list"),
            ({"steps": [{"id": None}]}, "previous system-test DAG has malformed steps"),
        ):
            with self.subTest(prior=prior), self.assertRaisesRegex(
                protocol.ProtocolError, message
            ):
                protocol.system_test_catalog(core, root, {}, previous=prior)

    def test_checkpoint_review_rejects_missing_and_invalid_values_before_mutation(self):
        root = Path(tempfile.mkdtemp(prefix="shiploop-system-checkpoint-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        state = {
            "stage": "quality",
            "action": {"id": "quality-001"},
            "completed_actions": {},
            "system_test_protocol_version": 1,
        }
        for payload, message in (
            ({"summary": "Quality candidate."}, "system_test_review requires"),
            (
                {
                    "summary": "Quality candidate.",
                    "system_test_review": {
                        "decision": [],
                        "evidence": "The requirements are unchanged.",
                        "discovery_ids": [],
                    },
                },
                "decision must be",
            ),
        ):
            before = deepcopy(state)
            with self.subTest(message=message), self.assertRaisesRegex(
                protocol.ProtocolError, message
            ):
                protocol.complete(None, root, state, "quality-001", payload)
            self.assertEqual(state, before)

    def test_checkpoint_review_enforces_no_change_and_revise_routes(self):
        root = Path(tempfile.mkdtemp(prefix="shiploop-system-review-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root))
        no_change = {
            "system_test_review": {
                "decision": "no-change",
                "evidence": "SYS-PRE-001 remains mapped to its unchanged prerequisite.",
                "discovery_ids": [],
            }
        }
        protocol.validate_system_test_review(root, {}, "quality", no_change)
        changed = deepcopy(no_change)
        changed["system_test_review"].update(decision="revise", discovery_ids=["K-1"])
        with self.assertRaisesRegex(protocol.ProtocolError, "use replan"):
            protocol.validate_system_test_review(root, {}, "quality", changed)
        with self.assertRaisesRegex(protocol.ProtocolError, "revised pending DAG"):
            protocol.validate_system_test_review(root, {}, "post-inner", changed)
        changed["plan_decision"] = "revise"
        protocol.validate_system_test_review(root, {}, "post-inner", changed)

    def test_carry_forward_revise_requires_matching_pending_test_strategy_discovery(self):
        fixture, _core, _dag = self._closure_fixture()
        result = {
            "system_test_review": {
                "decision": "revise",
                "evidence": "SYS-PRE-002 requires a corrective prerequisite mapping.",
                "discovery_ids": ["K-SYSTEM-001"],
            },
            "discoveries": [
                {
                    "id": "K-SYSTEM-001",
                    "domain": "test-strategy",
                    "disposition": "pending-replan",
                }
            ],
        }
        protocol.validate_system_test_review(
            fixture.run_dir, fixture.state, "carry-forward", result
        )
        result["system_test_review"]["discovery_ids"] = []
        with self.assertRaisesRegex(protocol.ProtocolError, "matching pending-replan"):
            protocol.validate_system_test_review(
                fixture.run_dir, fixture.state, "carry-forward", result
            )

    def _closure_fixture(self):
        fixture = CONTRACT_PROTOCOL_FIXTURES.ContractProtocolAdapterTests("runTest")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        step = deepcopy(CONTRACT_FIXTURES.step())
        step["activity"] = "system-test-pre"
        step["inputs"] = [{"need": "repository baseline exists", "from": None}]
        expected = step["contract"]["tests"][0]["expected_outcome"]
        dag = {"steps": [step], "system_tests": catalog(required_pre=True)}
        dag["system_tests"]["cases"] = [
            {
                "id": "SYS-PRE-001",
                "phase": "pre_deployment",
                "requirement": "The integrated local system boundary is checked before publication.",
                "expected_outcome": expected,
                "environment": "isolated local fixture",
                "prerequisites": [],
                "test_step": "S2",
                "test_id": "T-RESULT-001",
                "deployment_step": None,
            }
        ]
        store.write_record(
            fixture.run_dir / "lifecycle.md",
            {"publish": "none"},
            title="Fixture lifecycle",
        )
        fixture.certify_done()
        integrated = fixture.git("rev-parse", "HEAD")
        fixture.rec.update(
            status="complete",
            merged_sha=integrated,
            contract_closure={
                "fully_closed": True,
                "integrated_sha": integrated,
            },
        )
        return fixture, CatalogCore(dag, {"S2": fixture.rec}), dag

    def test_real_contract_done_closure_accepts_then_rejects_tampered_missing_and_unfinished(
        self,
    ):
        fixture, core, _dag = self._closure_fixture()
        protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)
        saved = fixture.rec["contract_done"]
        action = saved["record"]["envelope"]["verify_action"]
        check_path = fixture.run_dir / "checks" / f"{action}.md"
        altered = store.read_record(check_path)
        altered["results"]["checks"][0]["status"] = "failed"
        store.write_record(check_path, altered)
        with self.assertRaisesRegex(
            protocol.ProtocolError, "check evidence changed or is missing"
        ):
            protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)
        fixture, core, _dag = self._closure_fixture()
        action = fixture.rec["contract_done"]["record"]["envelope"]["verify_action"]
        (fixture.run_dir / "checks" / f"{action}.md").unlink()
        with self.assertRaisesRegex(
            protocol.ProtocolError, "check evidence changed or is missing"
        ):
            protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)
        fixture, core, _dag = self._closure_fixture()
        fixture.rec["status"] = "running"
        with self.assertRaisesRegex(protocol.ProtocolError, "is unfinished"):
            protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)

    def test_historic_system_test_certificate_survives_later_knowledge(self):
        fixture, core, _dag = self._closure_fixture()
        later = fixture.add_discovery(
            identifier="later-all-scope-system-test-note",
            observation="A later planning note changes the current knowledge epoch.",
            scope=["S2"],
            disposition="informational",
            action="later-system-test-note",
        )
        fixture.write_ledger(later, action="later-system-test-note")
        protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)

    def test_corrective_system_test_case_blocks_independently_when_unfinished(self):
        fixture, _core, dag = self._closure_fixture()
        corrective = deepcopy(dag["steps"][0])
        corrective["id"] = "S3"
        corrective["inputs"] = [{"need": "repository baseline exists", "from": None}]
        dag["steps"].append(corrective)
        dag["system_tests"]["cases"].append(
            {
                "id": "SYS-PRE-002",
                "phase": "pre_deployment",
                "requirement": "The corrective system boundary is checked before publication.",
                "expected_outcome": corrective["contract"]["tests"][0]["expected_outcome"],
                "environment": "isolated local fixture",
                "prerequisites": [],
                "test_step": "S3",
                "test_id": "T-RESULT-001",
                "deployment_step": None,
            }
        )
        core = CatalogCore(dag, {"S2": fixture.rec})
        with self.assertRaisesRegex(protocol.ProtocolError, "SYS-PRE-002 is unfinished"):
            protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)

    def test_pending_system_test_changes_block_quality_closure(self):
        fixture, core, _dag = self._closure_fixture()
        fixture.state["system_test_pending"] = ["K-SYSTEM-001"]
        with self.assertRaisesRegex(protocol.ProtocolError, "still require a mapped replan"):
            protocol.require_system_test_closure(core, fixture.run_dir, fixture.state)

    def test_system_test_replan_rejects_unrelated_or_case_only_changes(self):
        old, normal = self._replan_inputs(owner_activity="implementation")
        with self.assertRaisesRegex(protocol.ProtocolError, "changed/new pending system-test activity"):
            self._require_replan(old, normal)
        old, unchanged_owner = self._replan_inputs()
        old["steps"].append(deepcopy(unchanged_owner["steps"][-1]))
        with self.assertRaisesRegex(protocol.ProtocolError, "changed/new pending system-test activity"):
            self._require_replan(old, unchanged_owner)

    def test_system_test_replan_maps_pending_discovery_only_to_new_typed_owner(self):
        old, normal = self._replan_inputs(owner_activity="implementation")
        with self.assertRaisesRegex(protocol.ProtocolError, "changed/new pending system-test activity"):
            self._require_replan(
                old,
                normal,
                pending=("K-SYSTEM-001",),
                mapping=({"id": "K-SYSTEM-001", "steps": ["S3"]},),
            )
        old, corrected = self._replan_inputs()
        state = self._require_replan(
            old,
            corrected,
            pending=("K-SYSTEM-001",),
            mapping=({"id": "K-SYSTEM-001", "steps": ["S3"]},),
        )
        self.assertNotIn("system_test_pending", state)


if __name__ == "__main__":
    unittest.main()
