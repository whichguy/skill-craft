#!/usr/bin/env python3
"""Focused contract checks for ShipLoop's versioned DAG step contracts."""

from __future__ import annotations

from copy import deepcopy
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_contracts as contracts  # noqa: E402


_CORE_LOADER = SourceFileLoader("shiploop_contract_core", str(SCRIPTS / "shiploop"))
_CORE_SPEC = spec_from_loader(_CORE_LOADER.name, _CORE_LOADER)
assert _CORE_SPEC is not None
CORE = module_from_spec(_CORE_SPEC)
sys.modules[_CORE_LOADER.name] = CORE
_CORE_LOADER.exec_module(CORE)


HEAD = "a" * 40
ENVIRONMENT = "b" * 64
ARTIFACT = "c" * 64


def contract(*, deployment: bool = False) -> dict:
    return {
        "objective": "Create the exact result artifact without changing the input fixture.",
        "ready": [
            {
                "id": "R-INPUT-001",
                "condition": "The checked input fixture exists at the selected worktree.",
                "evidence_method": "Inspect the selected worktree fixture path before editing.",
            }
        ],
        "done": [
            {
                "id": "D-RESULT-001",
                "condition": "The result artifact has the exact expected contents.",
                "produces": ["result artifact exists"],
                "evidence_method": "Run the exact-output check from the verification manifest.",
                "completion": "integrated",
            },
            *(
                [
                    {
                        "id": "D-DEPLOY-001",
                        "condition": "The deployed entrypoint serves the exact result artifact.",
                        "produces": ["result artifact exists"],
                        "evidence_method": "Use the authorized delivery smoke probe against the named entrypoint.",
                        "completion": "deployed",
                    }
                ]
                if deployment
                else []
            ),
        ],
        "tests": [
            {
                "id": "T-RESULT-001",
                "produces": ["result artifact exists"],
                "expected_outcome": "The result artifact contains exactly the expected line.",
                "surface": "integration",
                "evidence_method": "Run the exact-output check from the verification manifest.",
            }
        ],
        "documentation": [
            {
                "id": "DOC-RESULT-001",
                "condition": "The README records how to run the exact-output check.",
                "evidence_method": "Review the README command and exercise it during verification.",
            }
        ],
    }


def step(*, inputs: list[dict] | None = None, deployment: bool = False) -> dict:
    return {
        "id": "S2",
        "statement": "Create the exact result artifact without changing the input fixture.",
        "produces": ["result artifact exists"],
        "inputs": inputs if inputs is not None else [{"need": "input artifact exists", "from": "S1"}],
        "contract": contract(deployment=deployment),
    }


def dag(*, version: int | None = 1, deployment: bool = False) -> dict:
    value = {
        "goal": "The result artifact exists.",
        "initial_state": ["repository exists"],
        "unresolved": [],
        "steps": [step(deployment=deployment)],
    }
    if version is not None:
        value["contract_version"] = version
    return value


def verify_record() -> dict:
    return {
        "manifest": {
            "checks": [
                {
                    "id": "T-RESULT-001",
                    "kind": "test",
                    "acceptance": ["result artifact exists"],
                }
            ]
        },
        "results": {
            "action": "verify-S2-1",
            "action_id": "verify-S2-1",
            "all_passed": True,
            "content_changed": False,
            "checks": [
                {"id": "T-RESULT-001", "kind": "test", "status": "passed", "exit": 0}
            ],
        },
    }


def planning_verify_record() -> dict:
    return {
        "planning_passed": True,
        "manifest": {
            "checks": [
                {
                    "id": "R-INPUT-001",
                    "kind": "test",
                    "acceptance": ["step plan"],
                }
            ]
        },
        "results": {
            "action": "step-plan-verify-S2-1",
            "action_id": "step-plan-verify-S2-1",
            "all_passed": True,
            "content_changed": False,
            "checks": [
                {"id": "R-INPUT-001", "kind": "test", "status": "passed", "exit": 0}
            ],
        },
    }


def ready_evidence() -> dict:
    return {
        "ready": [
            {
                "id": "R-INPUT-001",
                "condition": "The checked input fixture exists at the selected worktree.",
                "method": "Inspect the selected worktree fixture path before editing.",
                "source": "manual-observation",
                "reference": "fixture/input.txt",
                "observed": "The fixture exists at the selected worktree and has the expected baseline bytes.",
            }
        ]
    }


def done_evidence(*, deployed: bool = False) -> dict:
    value = {
        "done": [
            {
                "id": "D-RESULT-001",
                "method": "Run the exact-output check from the verification manifest.",
                "source": "verify-record",
                "reference": "check:T-RESULT-001",
                "observed": "The exact-output check passed against the result artifact.",
            }
        ],
        "tests": [
            {
                "id": "T-RESULT-001",
                "check_id": "T-RESULT-001",
                "expected_outcome": "The result artifact contains exactly the expected line.",
                "observed_outcome": "The result artifact contained exactly the expected line.",
                "source": "verify-record",
            }
        ],
        "documentation": [
            {
                "id": "DOC-RESULT-001",
                "method": "Review the README command and exercise it during verification.",
                "source": "manual-observation",
                "reference": "README.md#verification",
                "observed": "The documented verification command matched the executed exact-output check.",
            }
        ],
    }
    if deployed:
        value["done"].append(
            {
                "id": "D-DEPLOY-001",
                "method": "Use the authorized delivery smoke probe against the named entrypoint.",
                "source": "host-reported",
                "reference": "delivery.md#smoke",
                "observed": "The authorized smoke probe observed the deployed entrypoint serving the expected artifact.",
            }
        )
    return value


def certified_rebind() -> dict:
    return {
        "certified_head": HEAD,
        "certified_artifact_identity": ARTIFACT,
        "certified_verify_action": "verify-S2-1",
        "certified_contract_sha256": contracts.contract_identity(
            contracts.contract_for_step(step())
        ),
        "ancestry": [HEAD],
    }


class StepContractSchemaTests(unittest.TestCase):
    def test_versionless_dag_is_compatible_until_an_explicit_upgrade_gate(self) -> None:
        legacy = dag(version=None)
        self.assertEqual(contracts.dag_gaps(legacy), [])
        self.assertTrue(contracts.migration_required(legacy))
        self.assertIn(
            "missing contract_version",
            "\n".join(contracts.dag_gaps(legacy, require_contract=True)),
        )

    def test_versioned_dag_requires_complete_normalized_contracts(self) -> None:
        value = dag()
        self.assertEqual(contracts.dag_gaps(value), [])
        normalized = contracts.contract_for_step(value["steps"][0])
        self.assertEqual(normalized["objective"], value["steps"][0]["statement"])
        self.assertEqual(normalized["done"][0]["produces"], ["result artifact exists"])

        incomplete = deepcopy(value)
        incomplete["steps"][0]["contract"]["tests"][0]["produces"] = []
        gaps = contracts.dag_gaps(incomplete)
        self.assertIn("tests T-RESULT-001 must link one or more produces", "\n".join(gaps))

    def test_criterion_ids_and_evidence_methods_are_not_optional_labels(self) -> None:
        invalid_id = dag()
        invalid_id["steps"][0]["contract"]["ready"][0]["id"] = "ready"
        self.assertIn("ready criterion ID", "\n".join(contracts.dag_gaps(invalid_id)))

        invalid_method = dag()
        invalid_method["steps"][0]["contract"]["done"][0]["evidence_method"] = "TBD"
        self.assertIn(
            "evidence_method must be concrete",
            "\n".join(contracts.dag_gaps(invalid_method)),
        )

    def test_dependency_ready_to_plan_is_not_certified_ready_to_code(self) -> None:
        value = step()
        blocked = contracts.dependency_readiness(value, completed_suppliers=set())
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["missing_dependencies"], ["S1"])

        ready = contracts.dependency_readiness(value, completed_suppliers={"S1"})
        self.assertEqual(ready["status"], "ready-to-plan")
        self.assertFalse(ready["certified_ready_to_code"])
        self.assertEqual(
            contracts.packet_view(value)["readiness_evaluated_at"],
            "selected-step/cold-resume",
        )


class StepContractEvidenceTests(unittest.TestCase):
    def test_ready_requires_bound_pre_edit_evidence_not_a_boolean(self) -> None:
        value = step()
        result = contracts.validate_discharge(
            value,
            ready_evidence(),
            phase="ready",
            verify_record=planning_verify_record(),
            head=HEAD,
            environment_identity=ENVIRONMENT,
            artifact_identity=ARTIFACT,
        )
        self.assertEqual(result["ready_evidence"], ready_evidence())
        self.assertIsNone(result["done_evidence"])
        self.assertEqual(
            result["record"]["validated_receipt"]["discharged"]["ready"],
            ["R-INPUT-001"],
        )

        boolean_claim = ready_evidence()
        boolean_claim["ready"] = [{"id": "R-INPUT-001", "ready": True}]
        with self.assertRaisesRegex(contracts.ContractError, "evidence row"):
            contracts.validate_discharge(
                value,
                boolean_claim,
                phase="ready",
                verify_record=planning_verify_record(),
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

    def test_ready_and_test_evidence_require_real_test_checks_with_zero_exit(self) -> None:
        value = step()
        wrong_kind = planning_verify_record()
        wrong_kind["manifest"]["checks"][0]["kind"] = "lint"
        with self.assertRaisesRegex(contracts.ContractError, "bound to a test check"):
            contracts.validate_discharge(
                value,
                ready_evidence(),
                phase="ready",
                verify_record=wrong_kind,
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

        missing_exit = planning_verify_record()
        del missing_exit["results"]["checks"][0]["exit"]
        with self.assertRaisesRegex(contracts.ContractError, "did not pass"):
            contracts.validate_discharge(
                value,
                ready_evidence(),
                phase="ready",
                verify_record=missing_exit,
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

        product_wrong_kind = verify_record()
        product_wrong_kind["manifest"]["checks"][0]["kind"] = "lint"
        with self.assertRaisesRegex(contracts.ContractError, "must be a test check"):
            contracts.validate_discharge(
                value,
                done_evidence(),
                phase="final-verify",
                verify_record=product_wrong_kind,
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

    def test_final_and_merge_bind_test_doc_done_evidence_to_real_verify_record(self) -> None:
        value = step()
        result = contracts.validate_discharge(
            value,
            done_evidence(),
            phase="final-verify",
            verify_record=verify_record(),
            head=HEAD,
            environment_identity=ENVIRONMENT,
            artifact_identity=ARTIFACT,
        )
        self.assertEqual(result["done_evidence"], done_evidence())
        self.assertEqual(
            result["record"]["validated_receipt"]["discharged"]["tests"],
            ["T-RESULT-001"],
        )

        bad_record = verify_record()
        bad_record["results"]["checks"][0]["status"] = "failed"
        with self.assertRaisesRegex(contracts.ContractError, "did not pass"):
            contracts.validate_discharge(
                value,
                done_evidence(),
                phase="merge",
                verify_record=bad_record,
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
                certified_rebind=certified_rebind(),
            )

    def test_merge_requires_all_deployed_evidence_before_closure(self) -> None:
        value = step(deployment=True)
        with self.assertRaisesRegex(contracts.ContractError, "missing required criterion evidence"):
            contracts.validate_discharge(
                value,
                done_evidence(),
                phase="final-verify",
                verify_record=verify_record(),
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

        merged = contracts.validate_discharge(
            value,
            done_evidence(deployed=True),
            phase="merge",
            verify_record=verify_record(),
            head=HEAD,
            environment_identity=ENVIRONMENT,
            artifact_identity=ARTIFACT,
            certified_rebind={
                **certified_rebind(),
                "certified_contract_sha256": contracts.contract_identity(
                    contracts.contract_for_step(value)
                ),
            },
        )
        receipt = merged["record"]["validated_receipt"]
        self.assertEqual(receipt["deployed_done"], ["D-DEPLOY-001"])
        self.assertTrue(receipt["fully_closed_after_integration_assertion"])
        self.assertFalse(receipt["fully_closed"])

    def test_deployed_done_must_be_host_reported_and_audit_rebind_is_not_boolean(self) -> None:
        value = step(deployment=True)
        wrong_source = done_evidence(deployed=True)
        wrong_source["done"][1]["source"] = "verify-record"
        with self.assertRaisesRegex(contracts.ContractError, "requires host-reported"):
            contracts.validate_discharge(
                value,
                wrong_source,
                phase="final-verify",
                verify_record=verify_record(),
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

        fake_script_reference = done_evidence()
        fake_script_reference["done"][0]["reference"] = "check:invented"
        with self.assertRaisesRegex(contracts.ContractError, "not bound to a real verify-record check"):
            contracts.validate_discharge(
                step(),
                fake_script_reference,
                phase="final-verify",
                verify_record=verify_record(),
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )

        with self.assertRaisesRegex(contracts.ContractError, "requires a certified same-tree rebind"):
            contracts.validate_discharge(
                step(),
                done_evidence(),
                phase="post-inner",
                verify_record=verify_record(),
                head=HEAD,
                environment_identity=ENVIRONMENT,
                artifact_identity=ARTIFACT,
            )


def primary_cycle(number: int, *, outcome: str = "trivial") -> dict:
    iteration_id = f"run-S2-I{number}"
    sha = f"{number:040x}"
    return {
        "id": iteration_id,
        "outcome": outcome,
        "primary_commit": sha,
        "commit": {"sha": sha, "action": iteration_id},
        "check_action": f"verify-S2-{number}",
        "review": {"findings": []},
        "applied": {"material": outcome == "material"},
        "carry_forward": {"action": f"carry-S2-{number}"},
    }


class ImproveUntilIntegrationTests(unittest.TestCase):
    def test_only_verified_primary_cycles_can_satisfy_two_clean(self) -> None:
        self.assertTrue(
            CORE.improve_two_clean(
                {"improve_cycles": [primary_cycle(1), primary_cycle(2)]}
            )
        )

        unverified = [
            {"id": "run-S2-I1", "outcome": "trivial", "primary_commit": "a" * 40},
            {"id": "run-S2-I2", "outcome": "trivial", "primary_commit": "b" * 40},
        ]
        self.assertFalse(CORE.improve_two_clean({"improve_cycles": unverified}))

        self.assertFalse(
            CORE.improve_two_clean(
                {"improve_cycles": [primary_cycle(1), "untrusted row", primary_cycle(2)]}
            )
        )

        reset_by_repair = [
            primary_cycle(1),
            primary_cycle(2),
            {"outcome": "material", "kind": "repair-checkpoint"},
            primary_cycle(3),
        ]
        self.assertFalse(CORE.improve_two_clean({"improve_cycles": reset_by_repair}))


if __name__ == "__main__":
    unittest.main()
