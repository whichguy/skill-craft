#!/usr/bin/env python3
"""Focused pure-model tests for DAG-owned ShipLoop system-test requirements."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_system_tests as system_tests  # noqa: E402


def step(ident, activity=None, parents=(), test_id=None, expected=None):
    value = {
        "id": ident,
        "inputs": [
            {"need": f"output from {parent}", "from": parent} for parent in parents
        ],
    }
    if activity:
        value["activity"] = activity
    if test_id:
        value["contract"] = {"tests": [{"id": test_id, "expected_outcome": expected}]}
    return value


def case(ident, phase, owner, test_id, expected, prerequisites, deployment):
    return {
        "id": ident,
        "phase": phase,
        "requirement": f"{ident} checks the declared system boundary.",
        "expected_outcome": expected,
        "environment": "authorized staging fixture",
        "prerequisites": list(prerequisites),
        "test_step": owner,
        "test_id": test_id,
        "deployment_step": deployment,
    }


def dag(*, publish="dag", pre="required", post="required"):
    expected_pre, expected_post = (
        "Pre deployment system behavior is observable.",
        "Post deployment system behavior is observable.",
    )
    steps = [
        step("BUILD"),
        step("PRE", "system-test-pre", ("BUILD",), "T-PRE-001", expected_pre),
        step("DEPLOY", "publish", ("PRE",)),
        step("POST", "system-test-post", ("DEPLOY",), "T-POST-001", expected_post),
    ]
    cases = []
    if pre == "required":
        cases.append(
            case(
                "SYS-PRE-001",
                "pre_deployment",
                "PRE",
                "T-PRE-001",
                expected_pre,
                ("BUILD",),
                "DEPLOY" if publish == "dag" else None,
            )
        )
    if post == "required":
        cases.append(
            case(
                "SYS-POST-001",
                "post_deployment",
                "POST",
                "T-POST-001",
                expected_post,
                ("DEPLOY",),
                "DEPLOY",
            )
        )
    return {
        "steps": steps,
        "system_tests": {
            "version": 1,
            "phases": {
                "pre_deployment": {
                    "status": pre,
                    "reason": "The pre-release boundary is selected.",
                },
                "post_deployment": {
                    "status": post,
                    "reason": "The deployed boundary is selected.",
                },
            },
            "cases": cases,
        },
    }


class SystemTests(unittest.TestCase):
    def validate(self, value, *, publish="dag", **kwargs):
        return system_tests.validate(value, {"publish": publish}, **kwargs)

    def test_valid_fan_in_pre_deploy_post(self):
        value = dag()
        value["steps"][0]["inputs"] = [
            {"need": "repository baseline exists", "from": None}
        ]
        value["steps"].insert(1, step("CONFIG"))
        value["steps"][2]["inputs"].append({"need": "config", "from": "CONFIG"})
        value["system_tests"]["cases"][0]["prerequisites"].append("CONFIG")
        self.assertEqual(self.validate(value), value["system_tests"])
        rendered = system_tests.render(value)
        self.assertIn("Authoritative catalog", rendered)
        self.assertIn("not test-pass evidence", rendered)

    def test_nondeploy_required_pre_and_all_not_applicable(self):
        value = dag(publish="none", post="not-applicable")
        value["steps"] = [
            row for row in value["steps"] if row["id"] not in ("DEPLOY", "POST")
        ]
        self.assertIsNotNone(self.validate(value, publish="none"))
        empty = dag(pre="not-applicable", post="not-applicable")
        empty["steps"] = [step("BUILD")]
        empty["system_tests"]["cases"] = []
        self.assertEqual(self.validate(empty), empty["system_tests"])

    def test_legacy_absence_and_malformed_fail_closed(self):
        self.assertIsNone(self.validate({"steps": []}))
        self.assertIsNone(self.validate({"steps": []}, previous={"steps": []}))
        with self.assertRaisesRegex(system_tests.SystemTestError, "required"):
            self.validate({"steps": []}, required=True)
        with self.assertRaisesRegex(system_tests.SystemTestError, "cannot be removed"):
            self.validate({"steps": []}, previous=dag())
        broken = dag()
        broken["system_tests"]["version"] = True
        with self.assertRaisesRegex(system_tests.SystemTestError, "version"):
            self.validate(broken)
        broken = dag()
        broken["system_tests"]["cases"][0]["unknown"] = "x"
        with self.assertRaisesRegex(system_tests.SystemTestError, "schema"):
            self.validate(broken)

    def test_missing_prerequisite_order_deployment_and_contract_are_rejected(self):
        for mutate, message in (
            (
                lambda x: x["system_tests"]["cases"][0].update(
                    prerequisites=["MISSING"]
                ),
                "unknown prerequisite",
            ),
            (
                lambda x: x["system_tests"]["cases"][0].update(
                    prerequisites=["DEPLOY"]
                ),
                "transitively precede",
            ),
            (
                lambda x: x["system_tests"]["cases"][1].update(deployment_step=None),
                "deployment_step",
            ),
            (
                lambda x: x["system_tests"]["cases"][0].update(test_id="T-NOPE-001"),
                "contract.tests",
            ),
            (
                lambda x: x["system_tests"]["cases"][0].update(
                    expected_outcome="wrong"
                ),
                "contract.tests",
            ),
        ):
            value = dag()
            mutate(value)
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(system_tests.SystemTestError, message),
            ):
                self.validate(value)

    def test_graph_ordering_cycles_and_owner_negatives_are_rejected(self):
        for mutate, publish, message in (
            (
                lambda x: x["steps"][0].update(
                    inputs=[{"need": "cycle", "from": "POST"}]
                ),
                "dag",
                "cycle",
            ),
            (
                lambda x: x["system_tests"]["cases"][0].update(test_step="MISSING"),
                "dag",
                "unknown test_step",
            ),
            (
                lambda x: x["steps"][1].update(
                    inputs=[{"need": "self", "from": "PRE"}]
                ),
                "dag",
                "depend on itself",
            ),
            (
                lambda x: x["steps"][2].update(inputs=[]),
                "dag",
                "must precede deployment_step",
            ),
            (
                lambda x: (
                    x["steps"][3].update(inputs=[]),
                    x["system_tests"]["cases"][1].update(prerequisites=[]),
                ),
                "dag",
                "must depend on deployment_step",
            ),
            (
                lambda x: x["system_tests"]["cases"][0].update(deployment_step=None),
                "outer-loop",
                "requires lifecycle.publish=dag",
            ),
        ):
            value = dag()
            mutate(value)
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(system_tests.SystemTestError, message),
            ):
                self.validate(value, publish=publish)

    def test_malformed_types_duplicate_ids_and_orphan_case_are_rejected(self):
        for mutate, message in (
            (
                lambda x: x["system_tests"]["phases"]["pre_deployment"].update(
                    status=[]
                ),
                "status",
            ),
            (lambda x: x["system_tests"]["cases"][0].update(phase=[]), "phase"),
            (
                lambda x: x["system_tests"]["cases"].append(
                    deepcopy(x["system_tests"]["cases"][0])
                ),
                "duplicate",
            ),
            (lambda x: x["system_tests"]["cases"].pop(0), "must have cases"),
        ):
            value = dag()
            mutate(value)
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(system_tests.SystemTestError, message),
            ):
                self.validate(value)

    def test_orphan_typed_steps_and_publish_coverage_are_rejected(self):
        value = dag()
        value["steps"].append(
            step("ORPHAN", "system-test-pre", ("BUILD",), "T-ORPHAN-001", "Observed.")
        )
        with self.assertRaisesRegex(
            system_tests.SystemTestError, "typed pre_deployment"
        ):
            self.validate(value)
        value = dag()
        value["steps"].append(step("DEPLOY2", "publish", ("PRE",)))
        with self.assertRaisesRegex(system_tests.SystemTestError, "every publish step"):
            self.validate(value)

    def test_locked_case_cannot_mutate_or_be_removed(self):
        old = dag()
        changed = deepcopy(old)
        changed["system_tests"]["cases"][0]["environment"] = "other"
        with self.assertRaisesRegex(system_tests.SystemTestError, "locked"):
            self.validate(changed, previous=old, locked_steps=("PRE",))
        removed = deepcopy(old)
        removed["system_tests"]["cases"] = removed["system_tests"]["cases"][1:]
        removed["system_tests"]["phases"]["pre_deployment"]["status"] = "not-applicable"
        with self.assertRaisesRegex(system_tests.SystemTestError, "locked"):
            self.validate(removed, previous=old, locked_steps=("DEPLOY",))


if __name__ == "__main__":
    unittest.main()
