#!/usr/bin/env python3
"""Hermetic fixtures for the product and coverage evaluation boundary."""
import base64
import copy
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

HARNESS = Path(__file__).resolve().parent / "shiploop_e2e"
sys.path.insert(0, str(HARNESS))
from hosted_outcome import evaluation as e  # noqa: E402

EXAMPLE = HARNESS / "scenarios/grok-chat-outcome/evaluation.example.json"
EVENT = {"kind": "json_pointer", "pointer": "/events/0"}
ASSERTION = {"kind": "json_pointer", "pointer": "/events/0/assertion"}
LINE = {"kind": "lines", "start": 1, "end": 1}
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7XcAAAAASUVORK5CYII=")


class Content(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.links = []
        self.tags = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs["href"])


class OutcomeEvaluation(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.builder_output = self.root / "builder"
        self.builder_output.mkdir()
        self.review_path = self.root / "result.md"
        self.anchor_path = self.root / "sealed-discovery.json"
        self.generation = {
            "generation_id": "first-attempt",
            "build_sha256": "a" * 64,
            "source_sha256": "b" * 64,
            "deployment_ids": ["0Af000000000001"],
            "org_id": "00D000000000001",
            "user_id": "005000000000001",
            "prefix": "E2EOne",
            "app_url": "https://fixture.example/lightning/app/E2EOne",
            "retained_state": "RETAINED_QUIESCENT",
        }
        self.routes = {}
        self.test_artifacts = []
        self.references = []
        self.review = json.loads(EXAMPLE.read_text())

    def artifact(self, name, content):
        path = self.root / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(json.dumps(content) + "\n", encoding="utf-8")
        return {"path": str(path), "sha256": e.sha256(path.read_bytes())}

    def seal(self):
        anchor = self.artifact(self.anchor_path.name, {
            "evaluation_generation": self.generation,
            "evaluation_routes": self.routes,
            "evaluation_test_artifacts": self.test_artifacts,
            "evaluation_reference_artifacts": self.references,
        })
        self.review["anchor"] = anchor
        self.artifact(self.review_path.name, self.review)
        return anchor

    def assess(self, anchor=None, **overrides):
        anchor = self.seal() if anchor is None else anchor
        inputs = {"anchor": anchor, "routes": self.routes, "builder_output": self.builder_output}
        return e.assess(self.review_path, **(inputs | overrides))

    def route(self, name, assertion, *, locator=EVENT, content=None):
        ref = self.artifact(name + ".trace", content if content is not None else {
            "events": [{"assertion": assertion, "unrelated": "MUST_NOT_EMBED_RAW_TRACE"}],
        })
        self.routes[name] = ref
        return {"route": name, "artifact": ref, "locator": copy.deepcopy(locator), "proves": assertion}

    def product(self, verdict, reason, *observations, journey="approved_writes"):
        self.review["journeys"][journey]["product"] = {
            "verdict": verdict, "reason": reason, "observations": list(observations),
        }

    def add_test(self, *, journey="approved_writes", layer="app_unit", environment="local",
                 status="PASS", generated=True):
        test_id = f"{layer}-{len(self.test_artifacts)}"
        definition = self.artifact(f"builder/{test_id}.txt", b"assert proposal.confirmed is False\n")
        row = {
            "test_id": test_id,
            "behavior": "A rejected proposal has no approved write.",
            "layer": layer,
            "environment": environment,
            "generated": generated,
            "status": status,
            "tested_generation": None,
            "test_definition": {"artifact": definition, "locator": dict(LINE), "proves": "Exact review assertion"},
            "execution": None,
            "assertion": None,
            "limitations": [],
        }
        if environment == "mock":
            row["limitations"].append("Canned provider response only.")
        if layer == "harness_self_test":
            row["limitations"].append("Exercises evaluator fixtures and receipts.")
        tested = {key: copy.deepcopy(self.generation[key]) for key in e.TEST_IDENTITY}
        if environment != "hosted":
            tested["deployment_ids"] = []
        if generated:
            self.test_artifacts.append({"artifact": definition, "tested_generation": copy.deepcopy(tested),
                                        "layer": layer, "environment": environment})
        if status in ("PASS", "FAIL"):
            ref = self.artifact(f"builder/{test_id}.json", {
                "events": [{"test_id": test_id, "assertion": "reject writes", "status": status}],
            })
            row.update(tested_generation=tested,
                       execution={"artifact": ref, "locator": dict(EVENT), "proves": "This test completed"},
                       assertion={"artifact": ref, "locator": dict(ASSERTION), "proves": "This behavior was asserted"})
            self.test_artifacts.append({"artifact": ref, "tested_generation": copy.deepcopy(tested),
                                        "layer": layer, "environment": environment})
        self.review["journeys"][journey]["coverage"]["tests"].append(row)
        return row

    def test_supplied_example_accepts_seven_unknown_findings_with_incomplete_generation(self):
        self.generation.update(build_sha256=None, source_sha256=None, deployment_ids=[], app_url=None)
        summary = self.assess()
        self.assertEqual(summary["measures"], {"observed": 0, "passed": 0, "failed": 0, "unknown": 7})
        self.assertEqual(set(summary["floors"].values()), {False})
        self.assertEqual(summary["evaluator_qualification"], "UNQUALIFIED")
        self.assertEqual(summary["generic_improvement"], "NOT_MEASURED")
        self.assertEqual(summary["coverage_summary"]["executions_by_layer"], [])
        self.assertEqual(summary["review_result"]["sha256"], e.sha256(self.review_path.read_bytes()))
        self.assertIn("<title>Grok Bot E2E effectiveness unmeasured</title>", e.render_html(summary))

    def test_per_journey_product_and_coverage_are_required(self):
        del self.review["journeys"]["responsive_keyboard"]["coverage"]
        with self.assertRaisesRegex(ValueError, "journey fields"):
            self.assess()
        del self.review["journeys"]["responsive_keyboard"]
        with self.assertRaisesRegex(ValueError, "reviewed journeys"):
            self.assess()

    def test_generated_source_and_executed_result_are_distinct(self):
        pending = self.add_test(journey="setup", status="NOT_RUN")
        executed = self.add_test(layer="salesforce_native", environment="hosted")
        summary = self.assess()
        self.assertEqual(summary["coverage_summary"]["app_not_run_findings"], 1)
        self.assertEqual(summary["coverage_summary"]["executions_by_layer"], [
            {"layer": "salesforce_native", "environment": "hosted", "status": "PASS", "findings": 1},
        ])
        self.assertIsNone(pending["tested_generation"])
        pending["execution"] = executed["execution"]
        with self.assertRaisesRegex(ValueError, "unproven execution"):
            self.assess()

    def test_missing_definition_cannot_claim_generated_test(self):
        pending = self.add_test(status="NOT_RUN")
        pending["test_definition"] = None
        with self.assertRaisesRegex(ValueError, "generated test needs source"):
            self.assess()

    def test_foreign_definition_cannot_claim_generated_not_run(self):
        anchor = self.seal()
        row = self.add_test(status="NOT_RUN")
        row["test_definition"]["artifact"] = self.artifact(
            "generation-B-only.py", b"def test_b_only():\n    assert proposal.cancelled\n",
        )
        row["test_definition"]["locator"] = {"kind": "lines", "start": 2, "end": 2}
        self.artifact(self.review_path.name, self.review)
        with self.assertRaisesRegex(ValueError, "definition is not sealed"):
            self.assess(anchor)

    def test_unsealed_builder_path_cannot_claim_generated_source(self):
        anchor = self.seal()
        row = self.add_test(status="NOT_RUN")
        self.artifact(self.review_path.name, self.review)
        with self.assertRaisesRegex(ValueError, "definition is not sealed"):
            self.assess(anchor)
        row["generated"] = False
        self.artifact(self.review_path.name, self.review)
        with self.assertRaisesRegex(ValueError, "app NOT_RUN"):
            self.assess(anchor)
        row.update(status="UNKNOWN", test_definition=None)
        self.artifact(self.review_path.name, self.review)
        summary = self.assess(anchor)
        self.assertEqual(summary["coverage_summary"]["app_unknown_findings"], 1)
        self.assertEqual(summary["coverage_summary"]["app_not_run_findings"], 0)
        self.assertEqual(summary["coverage_summary"]["executions_by_layer"], [])

    def test_generated_definition_must_match_registered_artifact_layer_and_environment(self):
        row = self.add_test(status="NOT_RUN", layer="integration")
        definition = row["test_definition"]["artifact"]
        tested = {key: copy.deepcopy(self.generation[key]) for key in e.TEST_IDENTITY}
        tested["deployment_ids"] = []
        registration = {"artifact": definition, "tested_generation": tested,
                        "layer": "integration", "environment": "local"}
        for wrong_registration in (
            registration | {"layer": "harness_self_test"},
            registration | {"environment": "mock"},
            registration | {"artifact": self.artifact("copy.txt", Path(definition["path"]).read_bytes())},
        ):
            with self.subTest(wrong_registration=wrong_registration):
                self.test_artifacts[:] = [wrong_registration]
                with self.assertRaisesRegex(ValueError, "definition is not sealed"):
                    self.assess()

    def test_generated_definition_rejects_wrong_build_source_or_deployment_registration(self):
        row = self.add_test(status="NOT_RUN", layer="salesforce_native", environment="hosted")
        tested = {key: copy.deepcopy(self.generation[key]) for key in e.TEST_IDENTITY}
        for field, value in (
            ("build_sha256", "e" * 64),
            ("source_sha256", "f" * 64),
            ("deployment_ids", ["0Af000000000002"]),
            ("generation_id", "generation-B"),
        ):
            with self.subTest(field=field):
                self.test_artifacts[:] = [{
                    "artifact": row["test_definition"]["artifact"],
                    "tested_generation": tested | {field: value},
                    "layer": "salesforce_native", "environment": "hosted",
                }]
                with self.assertRaisesRegex(ValueError, "different or unidentified"):
                    self.assess()

    def test_registered_execution_does_not_seal_a_different_definition(self):
        row = self.add_test()
        row["test_definition"]["artifact"] = self.artifact("other-source.txt", b"assert unrelated\n")
        with self.assertRaisesRegex(ValueError, "definition is not sealed"):
            self.assess()

    def test_sealed_definition_without_execution_renders_generated_not_run(self):
        row = self.add_test(status="NOT_RUN", layer="salesforce_native", environment="hosted")
        anchor = self.seal()
        result = self.assess(anchor)
        self.assertEqual(result["coverage_summary"]["executions_by_layer"], [])
        self.assertEqual(result["coverage_summary"]["app_not_run_findings"], 1)
        self.assertEqual(result["measures"]["unknown"], 7)
        html = e.render_html(result)
        self.assertIn("Salesforce native · hosted · NOT_RUN · Generated", html)
        self.assertIn(Path(row["test_definition"]["artifact"]["path"]).as_uri(), Content(html).links)
        self.assertNotIn("Execution result", html)

        original_ref = row["test_definition"]["artifact"]
        updated_ref = self.artifact(original_ref["path"], b"assert different\n")
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            self.assess(anchor)
        row["test_definition"]["artifact"] = updated_ref
        self.artifact(self.review_path.name, self.review)
        with self.assertRaisesRegex(ValueError, "definition is not sealed"):
            self.assess(anchor)

    def test_wrong_build_source_deployment_or_generation_refuses_execution(self):
        row = self.add_test(layer="salesforce_native", environment="hosted")
        tested = copy.deepcopy(row["tested_generation"])
        for field, value in (
            ("build_sha256", "e" * 64),
            ("source_sha256", "f" * 64),
            ("deployment_ids", ["0Af000000000002"]),
            ("generation_id", "another-generation"),
        ):
            with self.subTest(field=field):
                row["tested_generation"] = tested | {field: value}
                with self.assertRaisesRegex(ValueError, "different or unidentified"):
                    self.assess()

    def test_claimed_execution_and_assertion_each_require_sealed_provenance(self):
        row = self.add_test()
        valid_assertion = row["assertion"]
        unsealed = self.artifact("different-build.log", b"PASS from some build\n")
        row["assertion"] = {"artifact": unsealed, "locator": LINE, "proves": "A supposed assertion"}
        with self.assertRaisesRegex(ValueError, "assertion is not sealed"):
            self.assess()
        row["assertion"] = valid_assertion
        self.test_artifacts.clear()
        with self.assertRaisesRegex(ValueError, "execution is not sealed"):
            self.assess()

    def test_primary_evidence_and_assertion_hashes_and_bounds_are_checked(self):
        row = self.add_test()
        locator = row["assertion"]["locator"]
        row["assertion"]["locator"] = {"kind": "json_pointer", "pointer": "/events/9"}
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            self.assess()
        row["assertion"]["locator"] = locator
        row["test_definition"]["locator"] = {"kind": "lines", "start": 1, "end": 2}
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            self.assess()
        row["test_definition"]["locator"] = LINE
        Path(row["execution"]["artifact"]["path"]).write_text("tampered execution", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            self.assess()

    def test_bare_route_and_unsealed_screenshot_cannot_support_product_pass(self):
        browser = self.route("browser", "The proposal presents the exact intended changes.")
        records = self.route("records", "Independent readback shows only the confirmed change.")
        self.product("PASS", "The proposed write is exact.", "browser", "records")
        with self.assertRaisesRegex(ValueError, "evidence link"):
            self.assess()
        screenshot = self.artifact("unrelated.png", PNG)
        fake = browser | {"artifact": screenshot,
                          "locator": {"kind": "png_region", "x": 0, "y": 0, "width": 1, "height": 1}}
        self.product("PASS", "Both product surfaces observed.", fake, records)
        with self.assertRaisesRegex(ValueError, "sealed route artifact"):
            self.assess()

    def test_valid_specific_observations_prove_one_outcome_only(self):
        browser = self.route("browser", "The proposal presents the exact intended changes.")
        records = self.route("records", "Readback shows only the confirmed change.")
        self.product("PASS", "Expected write behavior independently observed.", browser, records)
        self.assertEqual(self.assess()["measures"], {"observed": 1, "passed": 1, "failed": 0, "unknown": 6})
        self.product("PASS", "Approval looks correct.", browser)
        with self.assertRaisesRegex(ValueError, "missing required route"):
            self.assess()

    def test_sealed_png_region_and_exact_artifact_bytes(self):
        locator = {"kind": "png_region", "x": 0, "y": 0, "width": 1, "height": 1}
        browser = self.route("browser", "The reference interaction is visible.", locator=locator, content=PNG)
        self.product("PASS", "Rendered behavior checked.", browser, journey="grok_bot_experience")
        self.assertEqual(self.assess()["measures"]["passed"], 1)
        browser["locator"]["width"] = 2
        with self.assertRaisesRegex(ValueError, "PNG region is out of bounds"):
            self.assess()
        browser["locator"]["width"] = 1
        Path(browser["artifact"]["path"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.assess()

    def test_copied_routes_and_mismatched_anchor_are_rejected(self):
        self.route("browser", "The browser reaches the intended generation.")
        anchor = self.seal()
        alternate = self.artifact("copy.trace", Path(self.routes["browser"]["path"]).read_bytes())
        with self.assertRaisesRegex(ValueError, "routes must match"):
            self.assess(anchor, routes={"browser": alternate})
        anchor_copy = self.artifact("copy.json", self.anchor_path.read_bytes())
        with self.assertRaisesRegex(ValueError, "different discovery anchor"):
            self.assess(anchor_copy)
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            self.assess(anchor | {"sha256": "0" * 64})

    def test_symlink_or_builder_owned_review_is_rejected(self):
        anchor = self.seal()
        alias = self.root / "alias.md"
        alias.symlink_to(self.review_path)
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            e.assess(alias, anchor=anchor, routes=self.routes, builder_output=self.builder_output)
        builder_copy = self.builder_output / "forged.md"
        builder_copy.write_bytes(self.review_path.read_bytes())
        with self.assertRaisesRegex(ValueError, "outside builder output"):
            e.assess(builder_copy, anchor=anchor, routes=self.routes, builder_output=self.builder_output)

    def test_harness_counts_cannot_create_any_app_coverage(self):
        row = self.add_test(layer="harness_self_test", generated=False)
        row["behavior"] = "85 harness suites and 32 adapter checks passed."
        summary = self.assess()
        self.assertEqual(summary["coverage_summary"]["harness_findings"], 1)
        self.assertEqual(summary["coverage_summary"]["app_pass_findings"], 0)
        self.assertEqual(summary["coverage_summary"]["executions_by_layer"], [])
        self.assertEqual(summary["measures"]["unknown"], 7)

    def test_mocked_provider_stays_mock_coverage(self):
        row = self.add_test(journey="setup", layer="integration", environment="mock")
        summary = self.assess()
        self.assertEqual(summary["coverage_summary"]["executions_by_layer"], [
            {"layer": "integration", "environment": "mock", "status": "PASS", "findings": 1},
        ])
        self.assertEqual(summary["journeys"]["setup"]["product"]["verdict"], "UNKNOWN")
        row["layer"] = "live_provider"
        with self.assertRaisesRegex(ValueError, "invalid test layer or execution environment"):
            self.assess()
        row["layer"], row["environment"] = "live_provider", "hosted"
        row["tested_generation"]["deployment_ids"] = list(self.generation["deployment_ids"])
        with self.assertRaisesRegex(ValueError, "execution is not sealed"):
            self.assess()

    def test_green_app_unit_does_not_hide_demonstrated_product_defect(self):
        records = self.route("records", "A declined proposal created the synthetic row.")
        self.product("FAIL", "Readback shows a business write after rejection.", records)
        self.add_test()
        result = self.assess()
        self.assertEqual(result["measures"], {"observed": 1, "passed": 0, "failed": 1, "unknown": 6})
        self.assertEqual(result["coverage_summary"]["app_pass_findings"], 1)
        self.assertFalse(result["floors"]["qualified_acceptance"])

    def test_immutable_replay_survives_retirement_and_preserves_source_bytes(self):
        self.product("PASS", "The keyboard can complete the workflow.",
                     self.route("browser", "Keyboard focus and recovery observed."), journey="responsive_keyboard")
        anchor = self.seal()
        before = self.assess(anchor)
        html = e.render_html(before)
        self.artifact("latest-settlement.json", {"state": "SETTLED", "retired": True})
        after = self.assess(anchor)
        self.assertEqual(before, after)
        self.assertEqual(e.render_html(after), html)
        self.assertEqual(e.sha256(self.anchor_path.read_bytes()), anchor["sha256"])
        self.assertEqual(after["generation"]["retained_state"], "RETAINED_QUIESCENT")

    def test_html_links_real_generation_and_evidence_and_escapes_review_text(self):
        records = self.route("records", "A declined proposal created the synthetic row.")
        self.product("FAIL", "<script>alert('verdict')</script>", records)
        row = self.add_test()
        row["behavior"] = "Content <b> reviewed & assessed"
        reference = self.artifact("public doc.txt", b"Locally archived official reference\n")
        self.references.append({"label": "Grok Bot reference", "artifact": reference})
        html = e.render_html(self.assess())
        content = Content(html)
        self.assertEqual(set(e.JOURNEY_ROUTES) - set(content.ids), set())
        self.assertEqual(len(content.ids), len(set(content.ids)))
        self.assertEqual(content.links[0], self.generation["app_url"])
        self.assertIn(Path(reference["path"]).as_uri(), content.links)
        self.assertNotIn("script", content.tags)
        self.assertIn("&lt;script&gt;alert", html)
        self.assertIn("Content &lt;b&gt; reviewed &amp; assessed", html)
        self.assertIn("0 PASS · 1 FAIL · 6 UNKNOWN", html)
        self.assertIn("App unit · local · PASS", html)
        self.assertIn("Gaps and limits", html)
        self.assertIn("Retained state at sealing: RETAINED_QUIESCENT", html)
        self.assertIn(self.generation["source_sha256"], html)
        self.assertIn("JSON pointer /events/0", html)
        self.assertNotIn("MUST_NOT_EMBED_RAW_TRACE", html)

    def test_token_bearing_url_is_refused(self):
        self.generation["app_url"] += "?access_token=fixture"
        with self.assertRaisesRegex(ValueError, "invalid generation app URL"):
            self.assess()

    def test_prelaunch_artifact_has_no_fake_generation_review_or_test_results(self):
        result = e.unmeasured_summary("Fresh live run is NOT_STARTED.")
        html = e.render_html(result)
        self.assertIsNone(result["review_result"])
        self.assertEqual(result["measures"]["unknown"], 7)
        self.assertIn("Grok Bot E2E effectiveness unmeasured", html)
        self.assertIn("NOT_STARTED", html)
        self.assertIn("Coverage remains unknown", html)
        self.assertEqual(Content(html).links, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
