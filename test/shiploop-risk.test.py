#!/usr/bin/env python3
"""Focused schema and DAG tests for ShipLoop lifecycle risk decisions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_risk as risk  # noqa: E402


def no_risk_policy() -> dict:
    return {
        "risk_policy_version": 1,
        "security": {
            "decision": "not-applicable",
            "rationale": "The local fixture has no security-sensitive boundary.",
        },
        "fuzz": {
            "decision": "not-applicable",
            "rationale": "The local fixture has no parser or untrusted-input surface.",
        },
        "maintenance": {
            "decision": "not-applicable",
            "rationale": "The local fixture introduces no maintained dependency.",
        },
    }


def maintenance_fields(
    *, step_id: str | None, cadence: str = "Review advisory notices monthly."
) -> dict:
    return {
        "owner": "The product maintainer reviews the selected dependency advisory source.",
        "advisory_source": "The dependency publisher's security advisory feed.",
        "cadence": cadence,
        "mechanism": "Plan a reviewed dependency update in the selected product worktree.",
        "validation": "Run the selected regression and compatibility checks before merge.",
        "rollback": "Revert the bounded update commit if validation or production evidence fails.",
        "step_id": step_id,
    }


def selected_policy(*, maintenance: str = "dag") -> dict:
    policy = no_risk_policy()
    policy["security"] = {
        "decision": "required",
        "rationale": "The service boundary accepts authenticated input.",
        "case_ids": ["T-SEC-001"],
    }
    policy["fuzz"] = {
        "decision": "required",
        "rationale": "The parser must reject malformed untrusted payloads.",
        "case_ids": ["T-FUZZ-001"],
    }
    policy["maintenance"] = {
        "decision": maintenance,
        "rationale": (
            "Perform the dependency maintenance now before the authorized publication."
            if maintenance == "dag"
            else "Record this future maintenance plan without scheduling implementation now."
        ),
        **maintenance_fields(step_id="S2" if maintenance == "dag" else None),
    }
    return policy


def test_case(identifier: str) -> dict:
    return {
        "id": identifier,
        "produces": ["bounded fixture output"],
        "expected_outcome": "The bounded fixture reports the expected outcome.",
        "surface": "integration",
        "evidence_method": "Run the isolated fixture assertion.",
    }


def step(
    identifier: str,
    *,
    tests: list[str] | None = None,
    inputs: list[dict] | None = None,
    activity: str | None = None,
    produces: list[str] | None = None,
) -> dict:
    value = {
        "id": identifier,
        "statement": f"Complete bounded {identifier} work.",
        "produces": produces if produces is not None else [f"{identifier} output"],
        "inputs": inputs if inputs is not None else [],
        "contract": {"tests": [test_case(case) for case in tests or []]},
    }
    if activity is not None:
        value["activity"] = activity
    return value


def dag(*, publication_depends_on_maintenance: bool = True) -> dict:
    publish_inputs = (
        [{"need": "S2 output", "from": "S2"}]
        if publication_depends_on_maintenance
        else []
    )
    return {
        "steps": [
            step("S1", tests=["T-SEC-001"]),
            step("S2", tests=["T-FUZZ-001"]),
            step("S3", activity="publish", inputs=publish_inputs),
        ]
    }


class LifecycleRiskPolicyTests(unittest.TestCase):
    def assertHas(self, errors: list[str], fragment: str) -> None:
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in errors: {errors!r}",
        )

    def test_local_no_risks_policy_is_explicit_and_has_no_dag_requirements(
        self,
    ) -> None:
        policy = no_risk_policy()

        self.assertEqual(risk.validate_policy(policy, required=True), [])
        self.assertEqual(
            risk.validate_dag(policy, {"steps": [step("S1")]}),
            [],
        )

    def test_selected_security_fuzz_and_maintenance_map_to_exact_contracts(
        self,
    ) -> None:
        policy = selected_policy()

        self.assertEqual(risk.validate_policy(policy, required=True), [])
        self.assertEqual(risk.validate_dag(policy, dag()), [])

    def test_absent_policy_is_legacy_only_when_caller_does_not_require_it(self) -> None:
        self.assertEqual(risk.validate_policy(None, required=False), [])
        self.assertHas(
            risk.validate_policy(None, required=True),
            "risk_policy is required",
        )
        self.assertHas(
            risk.validate_dag(None, dag()),
            "risk_policy is required",
        )

    def test_present_missing_or_noncanonical_versions_do_not_downgrade_to_legacy(
        self,
    ) -> None:
        for version in (None, False, 0, 1.0, "1", 2):
            policy = no_risk_policy()
            if version is None:
                policy.pop("risk_policy_version")
            else:
                policy["risk_policy_version"] = version
            errors = risk.validate_policy(policy, required=False)
            self.assertTrue(
                errors, f"version {version!r} silently downgraded: {errors!r}"
            )
            self.assertHas(errors, "risk_policy_version")

    def test_mixed_mapping_keys_return_schema_errors_instead_of_crashing(self) -> None:
        policy = no_risk_policy()
        policy[1] = "not a JSON object key"
        policy["extra"] = "also unsupported"
        errors = risk.validate_policy(policy, required=True)
        self.assertHas(errors, "non-string keys")
        self.assertHas(errors, "unsupported keys")

        policy = no_risk_policy()
        policy["security"][1] = "not a JSON object key"
        policy["security"]["extra"] = "also unsupported"
        errors = risk.validate_policy(policy, required=True)
        self.assertHas(
            errors, "risk_policy.security not-applicable has non-string keys"
        )
        self.assertHas(
            errors, "risk_policy.security not-applicable has unsupported keys"
        )

    def test_required_cases_must_be_nonempty_unique_and_exact_t_ids(self) -> None:
        policy = selected_policy()
        policy["security"]["case_ids"] = []
        self.assertHas(risk.validate_policy(policy, required=True), "case_ids")

        policy = selected_policy()
        policy["security"]["case_ids"] = ["T-SEC-001", "T-SEC-001"]
        self.assertHas(risk.validate_policy(policy, required=True), "must not repeat")

        policy = selected_policy()
        policy["security"]["case_ids"] = ["security-001"]
        self.assertHas(risk.validate_policy(policy, required=True), "exact T-")

    def test_not_applicable_cannot_claim_selected_cases_or_maintenance_fields(
        self,
    ) -> None:
        policy = no_risk_policy()
        policy["security"]["case_ids"] = ["T-SEC-001"]
        self.assertHas(risk.validate_policy(policy, required=True), "not-applicable")

        policy = no_risk_policy()
        policy["maintenance"]["owner"] = "An owner that contradicts not-applicable."
        self.assertHas(risk.validate_policy(policy, required=True), "not-applicable")

    def test_blocked_decisions_are_valid_spec_records_but_cannot_pass_sequence(
        self,
    ) -> None:
        policy = no_risk_policy()
        policy["security"] = {
            "decision": "blocked",
            "rationale": "The required authorized probe is unavailable.",
            "case_ids": ["T-PLANNED-001"],
        }
        policy["fuzz"] = {
            "decision": "blocked",
            "rationale": "The isolated malformed-input fixture is not available yet.",
            "case_ids": ["T-PLANNED-002"],
        }
        policy["maintenance"] = {
            "decision": "blocked",
            "rationale": "The advisory source owner has not authorized the requested review.",
        }

        self.assertEqual(risk.validate_policy(policy, required=True), [])
        errors = risk.validate_dag(policy, dag())
        self.assertHas(errors, "security testing is blocked")
        self.assertHas(errors, "fuzz testing is blocked")
        self.assertHas(errors, "maintenance is blocked")
        self.assertFalse(
            any("T-PLANNED-001 is not present" in error for error in errors)
        )

    def test_required_cases_reject_absent_or_ambiguous_definitions(self) -> None:
        policy = selected_policy()
        policy["security"]["case_ids"] = ["T-MISSING-001"]
        self.assertHas(risk.validate_dag(policy, dag()), "is not present")

        duplicated = dag()
        duplicated["steps"][1]["contract"]["tests"].append(test_case("T-SEC-001"))
        self.assertHas(
            risk.validate_dag(selected_policy(), duplicated), "maps ambiguously"
        )

        policy = selected_policy()
        policy["fuzz"]["case_ids"] = ["T-SEC-001"]
        self.assertEqual(risk.validate_dag(policy, dag()), [])

    def test_maintenance_dag_requires_existing_producer_and_precedes_publish(
        self,
    ) -> None:
        policy = selected_policy()
        policy["maintenance"]["step_id"] = "S9"
        self.assertHas(
            risk.validate_dag(policy, dag()), "does not name an existing DAG step"
        )

        nonproducer = dag()
        nonproducer["steps"][1]["produces"] = []
        self.assertHas(
            risk.validate_dag(selected_policy(), nonproducer), "must be a producer"
        )

        self.assertHas(
            risk.validate_dag(
                selected_policy(), dag(publication_depends_on_maintenance=False)
            ),
            "must precede publication",
        )

    def test_operate_later_is_a_future_plan_not_an_implicit_scheduled_step(
        self,
    ) -> None:
        policy = selected_policy(maintenance="operate-later")
        local_dag = {"steps": [step("S1", tests=["T-SEC-001", "T-FUZZ-001"])]}

        self.assertEqual(risk.validate_policy(policy, required=True), [])
        self.assertEqual(risk.validate_dag(policy, local_dag), [])

        invalid = deepcopy(policy)
        invalid["maintenance"]["step_id"] = "S1"
        self.assertHas(
            risk.validate_policy(invalid, required=True), "step_id must be null"
        )


if __name__ == "__main__":
    unittest.main()
