#!/usr/bin/env python3
"""Focused report rendering coverage for the DAG-owned system-test catalog."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
REPORT_TEST = ROOT / "test" / "shiploop-report.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_report_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_system_tests_report_fixture", str(REPORT_TEST)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {REPORT_TEST}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


FIXTURE = load_report_fixture()
from shiploop_report import render_report  # noqa: E402


class SystemTestsReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = FIXTURE.ShipLoopReportTests(methodName="runTest")
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def _catalog_run(self) -> None:
        plan = self.fixture.read("backchain/plan.md")
        step = plan["steps"][0]
        step["activity"] = "system-test-pre"
        step["contract"]["tests"][0].update(
            id="T-SYSTEM-REPORT-ESCAPE",
            expected_outcome="Expected <script>alert(2)</script> outcome.",
        )
        plan["system_tests"] = {
            "version": 1,
            "phases": {
                "pre_deployment": {
                    "status": "required",
                    "reason": "The integrated fixture is the selected boundary.",
                },
                "post_deployment": {
                    "status": "not-applicable",
                    "reason": "No deployment exists for this fixture.",
                },
            },
            "cases": [
                {
                    "id": "SYS-REPORT-ESCAPE",
                    "phase": "pre_deployment",
                    "requirement": "Exercise <script>alert(1)</script> safely.",
                    "expected_outcome": "Expected <script>alert(2)</script> outcome.",
                    "environment": "fixture <b>environment</b>",
                    "prerequisites": [],
                    "test_step": "S1",
                    "test_id": "T-SYSTEM-REPORT-ESCAPE",
                    "deployment_step": None,
                }
            ],
        }
        self.fixture.record("backchain/plan.md", plan, "ShipLoop dependency sequence")
        lifecycle = self.fixture.read("lifecycle.md")
        lifecycle["publish"] = "none"
        self.fixture.record("lifecycle.md", lifecycle, "ShipLoop lifecycle")
        state = self.fixture.read("state.md")
        state["system_test_protocol_version"] = 1
        self.fixture.record("state.md", state, "ShipLoop state")

    def test_valid_catalog_is_escaped_and_labels_receipt_pointers_as_historical(self) -> None:
        self._catalog_run()
        rendered, metadata = render_report(self.fixture.run_dir)

        self.assertEqual(metadata["outcome"], "complete")
        self.assertIn('id="system-tests"', rendered)
        self.assertIn("SYS-REPORT-ESCAPE", rendered)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("steps/S1.md; T-SYSTEM-REPORT-ESCAPE", rendered)
        self.assertIn("historical receipt pointers", rendered)
        self.assertIn("backchain/plan.md", metadata["sources"])

    def test_legacy_absence_is_not_rendered_as_an_uncertified_catalog(self) -> None:
        rendered, metadata = render_report(self.fixture.run_dir)

        self.assertEqual(metadata["outcome"], "complete")
        self.assertNotIn('id="system-tests"', rendered)
        self.assertNotIn("uncertified system-test catalog", rendered.lower())

    def test_terminal_marker_requires_a_catalog(self) -> None:
        state = self.fixture.read("state.md")
        state["system_test_protocol_version"] = 1
        self.fixture.record("state.md", state, "ShipLoop state")

        rendered, metadata = render_report(self.fixture.run_dir)

        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertTrue(
            any("system_tests catalog is required" in error for error in metadata["evidence_errors"])
        )
        self.assertNotIn('id="system-tests"', rendered)

    def test_terminal_malformed_present_catalog_fails_closed_without_marker(self) -> None:
        plan = self.fixture.read("backchain/plan.md")
        plan["system_tests"] = {"version": 99}
        self.fixture.record("backchain/plan.md", plan, "ShipLoop dependency sequence")

        rendered, metadata = render_report(self.fixture.run_dir)

        self.assertEqual(metadata["outcome"], "unfinished")
        self.assertTrue(
            any("system-test requirements are unavailable" in error for error in metadata["evidence_errors"])
        )
        self.assertNotIn('id="system-tests"', rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
