"""Offline adversarial checks for the Salesforce Lightning proof contract."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import salesforce_proof as proof  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SalesforceProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.candidate = self.root / "candidate"
        component = self.candidate / "force-app" / "main" / "default" / "lwc" / "checkers" / "checkers.js"
        component.parent.mkdir(parents=True)
        component.write_text("export default class Checkers {}\n", encoding="utf-8")
        self.component = component
        self.expected = {"trial_id": "salesforce-trial", "candidate_digest": "c" * 64}
        self.target = {
            "schema": proof.TARGET_PREFLIGHT_SCHEMA,
            "status": "connected",
            "org_type": "developer",
            "expected_org_id": "00D000000000001AAA",
            "observed_org_id": "00D000000000001AAA",
            "expected_instance_url": "https://fixture-dev.my.salesforce.com",
            "observed_instance_url": "https://fixture-dev.my.salesforce.com",
            "expected_lightning_host": "fixture-dev.lightning.force.com",
            "observed_lightning_host": "fixture-dev.lightning.force.com",
            "my_domain": "fixture-dev",
            # A Developer Edition is intentionally allowed to be non-sandbox.
            "is_sandbox": False,
        }
        self.deployment_id = "0Af000000000001AAA"
        self.mapping = {
            "schema": proof.SOURCE_MAPPING_SCHEMA,
            **self.expected,
            "org_id": self.target["expected_org_id"],
            "instance_url": self.target["expected_instance_url"],
            "deployment_id": self.deployment_id,
            "rationale": "The retained component map identifies the deployed Lightning source.",
            "components": [{
                "path": self.component.relative_to(self.candidate).as_posix(),
                "sha256": _sha256(self.component),
                "kind": "lightning-web-component",
                "component_type": "LightningComponentBundle",
                "full_name": "checkers",
            }],
        }
        self.mapping_sha256 = "a" * 64
        self.raw_result = {
            "status": 0,
            "result": {
                "id": self.deployment_id,
                "status": "Succeeded",
                "checkOnly": False,
                "details": {"componentFailures": [], "componentSuccesses": [{
                    "componentType": "LightningComponentBundle", "fullName": "checkers", "success": True,
                }]},
            },
        }
        self.raw_result_sha256 = "b" * 64
        self.receipt = {
            "schema": proof.DEPLOYMENT_RECEIPT_SCHEMA,
            "provider": "salesforce-dx",
            "status": "succeeded",
            "job_id": self.deployment_id,
            "candidate_digest": self.expected["candidate_digest"],
            "org_id": self.target["expected_org_id"],
            "instance_url": self.target["expected_instance_url"],
            "raw_deployment_result_sha256": self.raw_result_sha256,
            "component_mapping_sha256": self.mapping_sha256,
        }
        self.deployment = {
            "schema": proof.DEPLOYMENT_OBSERVATION_SCHEMA,
            **self.expected,
            "provider": "salesforce-dx",
            "status": "succeeded",
            "org_id": self.target["expected_org_id"],
            "instance_url": self.target["expected_instance_url"],
            "lightning_host": self.target["expected_lightning_host"],
            "deployment_id": self.deployment_id,
        }
        self.hosted = {
            "schema": proof.HOSTED_OBSERVATION_SCHEMA,
            **self.expected,
            "org_id": self.target["expected_org_id"],
            "instance_url": self.target["expected_instance_url"],
            "deployment_id": self.deployment_id,
            "lightning_host": self.target["expected_lightning_host"],
            "lightning_route": "https://fixture-dev.lightning.force.com/lightning/n/Checkers",
            "authenticated": True,
        }
        self.trace = {
            **self.hosted,
            "schema": proof.LIGHTNING_BROWSER_TRACE_SCHEMA,
        }

    def deployment_errors(self, deployment: dict | None = None, *, raw_result: dict | None = None) -> list[str]:
        return proof.deployment_errors(
            deployment or self.deployment, expected=self.expected, preflight=self.target,
            receipt=self.receipt, raw_result=raw_result or self.raw_result,
            raw_result_sha256=self.raw_result_sha256, mapping=self.mapping,
            mapping_sha256=self.mapping_sha256, candidate_root=self.candidate,
        )

    def test_complete_developer_org_proof_is_accepted_without_a_sandbox_requirement(self) -> None:
        self.assertEqual([], proof.target_preflight_errors(self.target))
        self.assertEqual([], proof.source_mapping_errors(
            self.mapping, expected=self.expected, candidate_root=self.candidate,
        ))
        self.assertEqual([], self.deployment_errors())
        self.assertEqual([], proof.hosted_errors(
            self.hosted, expected=self.expected, deployment=self.deployment, trace=self.trace,
        ))
        self.assertEqual([], proof.cross_binding_errors(self.deployment, self.hosted, self.mapping))

    def test_deployment_rejects_a_different_org_and_wrong_raw_job(self) -> None:
        wrong_org = deepcopy(self.deployment)
        wrong_org["org_id"] = "00D000000000002AAA"
        self.assertIn("salesforce-deployment-target-preflight-org_id-mismatch", self.deployment_errors(wrong_org))

        wrong_job = deepcopy(self.raw_result)
        wrong_job["result"]["id"] = "0Af000000000002AAA"
        self.assertIn("salesforce-raw-deployment-result-job-id-mismatch", self.deployment_errors(raw_result=wrong_job))

    def test_target_preflight_binds_expected_and_observed_target_values(self) -> None:
        wrong_org = deepcopy(self.target)
        wrong_org["observed_org_id"] = "00D000000000002AAA"
        self.assertIn("salesforce-target-preflight-org-id-mismatch", proof.target_preflight_errors(wrong_org))

        wrong_instance = deepcopy(self.target)
        wrong_instance["observed_instance_url"] = "https://other-dev.my.salesforce.com"
        self.assertIn("salesforce-target-preflight-instance-url-mismatch", proof.target_preflight_errors(wrong_instance))

        wrong_host = deepcopy(self.target)
        wrong_host["expected_lightning_host"] = "other-dev.lightning.force.com"
        self.assertIn("salesforce-target-preflight-my-domain-lightning-host-mismatch", proof.target_preflight_errors(wrong_host))

        enhanced = deepcopy(self.target)
        enhanced.update(
            expected_instance_url="https://fixture-dev.develop.my.salesforce.com",
            observed_instance_url="https://fixture-dev.develop.my.salesforce.com",
            expected_lightning_host="fixture-dev.develop.lightning.force.com",
            observed_lightning_host="fixture-dev.develop.lightning.force.com",
            my_domain="fixture-dev",
        )
        self.assertEqual([], proof.target_preflight_errors(enhanced))
        enhanced["expected_lightning_host"] = "unrelated.lightning.force.com"
        self.assertIn(
            "salesforce-target-preflight-instance-lightning-host-mismatch",
            proof.target_preflight_errors(enhanced),
        )

    def test_raw_deployment_requires_non_check_only_matching_component_successes(self) -> None:
        check_only = deepcopy(self.raw_result)
        check_only["result"]["checkOnly"] = True
        self.assertIn("salesforce-raw-deployment-result-check-only", self.deployment_errors(raw_result=check_only))

        missing_component = deepcopy(self.raw_result)
        missing_component["result"]["details"]["componentSuccesses"] = []
        self.assertIn(
            "salesforce-raw-deployment-result-component-successes-invalid",
            self.deployment_errors(raw_result=missing_component),
        )

        failed_component = deepcopy(self.raw_result)
        failed_component["result"]["details"]["componentSuccesses"][0]["success"] = False
        self.assertIn(
            "salesforce-raw-deployment-result-component-failed",
            self.deployment_errors(raw_result=failed_component),
        )

        for value in (None, "true", 1):
            with self.subTest(success=value):
                malformed = deepcopy(self.raw_result)
                component = malformed["result"]["details"]["componentSuccesses"][0]
                if value is None:
                    del component["success"]
                else:
                    component["success"] = value
                self.assertIn(
                    "salesforce-raw-deployment-result-component-success-invalid",
                    self.deployment_errors(raw_result=malformed),
                )

        undeployed_mapping = deepcopy(self.mapping)
        undeployed_mapping["components"][0]["full_name"] = "unrelatedComponent"
        errors = proof.deployment_errors(
            self.deployment, expected=self.expected, preflight=self.target, receipt=self.receipt,
            raw_result=self.raw_result, raw_result_sha256=self.raw_result_sha256,
            mapping=undeployed_mapping, mapping_sha256=self.mapping_sha256, candidate_root=self.candidate,
        )
        self.assertIn("salesforce-raw-deployment-result-component-missing", errors)

    def test_lightning_route_is_bound_to_the_preflight_host_and_supports_app_or_tab_routes(self) -> None:
        wrong_hosted = deepcopy(self.hosted)
        wrong_hosted["lightning_route"] = "https://other.lightning.force.com/lightning/n/Checkers"
        wrong_trace = deepcopy(self.trace)
        wrong_trace["lightning_route"] = wrong_hosted["lightning_route"]
        errors = proof.hosted_errors(
            wrong_hosted, expected=self.expected, deployment=self.deployment, trace=wrong_trace,
        )
        self.assertIn("salesforce-hosted-observation-lightning-route-host-mismatch", errors)

        app_hosted = deepcopy(self.hosted)
        app_hosted["lightning_route"] = "https://fixture-dev.lightning.force.com/lightning/app/Checkers?view=game"
        app_trace = deepcopy(self.trace)
        app_trace["lightning_route"] = app_hosted["lightning_route"]
        self.assertEqual([], proof.hosted_errors(
            app_hosted, expected=self.expected, deployment=self.deployment, trace=app_trace,
        ))
        self.assertTrue(proof.lightning_route_errors("https://user@fixture-dev.lightning.force.com/lightning/n/Checkers"))
        self.assertTrue(proof.lightning_route_errors("https://fixture-dev.lightning.force.com:443/lightning/n/Checkers"))
        self.assertTrue(proof.lightning_route_errors("https://fixture-dev.lightning.force.com:not-a-port/lightning/n/Checkers"))

    def test_source_mapping_rejects_changed_or_non_lightning_candidate_source(self) -> None:
        self.component.write_text("export default class ChangedCheckers {}\n", encoding="utf-8")
        errors = proof.source_mapping_errors(
            self.mapping, expected=self.expected, candidate_root=self.candidate,
        )
        self.assertIn("salesforce-source-mapping-component-digest-mismatch", errors)

        self.mapping["components"][0]["kind"] = "metadata"
        errors = proof.source_mapping_errors(
            self.mapping, expected=self.expected, candidate_root=self.candidate,
        )
        self.assertIn("salesforce-source-mapping-lightning-component-missing", errors)

    def test_generic_gas_shape_cannot_qualify_as_salesforce_deployment(self) -> None:
        generic = {
            "schema": "shiploop-e2e-authorized-deployment-observation/1",
            **self.expected,
            "provider": "mcp-gas-deploy",
            "script_id": "script-test",
            "version_number": 1,
            "deployment_id": self.deployment_id,
            "web_app_url": "https://script.google.com/macros/s/example/exec",
        }
        errors = self.deployment_errors(generic)
        self.assertIn("salesforce-deployment-schema-invalid", errors)
        self.assertIn("salesforce-deployment-provider-invalid", errors)

    def test_cross_binding_rejects_a_hosted_record_for_another_deployment_target(self) -> None:
        wrong_hosted = deepcopy(self.hosted)
        wrong_hosted["org_id"] = "00D000000000002AAA"
        errors = proof.cross_binding_errors(self.deployment, wrong_hosted, self.mapping)
        self.assertIn("salesforce-deployment-hosted-org_id-mismatch", errors)



if __name__ == "__main__":
    unittest.main()
