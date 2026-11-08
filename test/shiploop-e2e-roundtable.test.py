#!/usr/bin/env python3
"""Roundtable wiring and observation boundaries; opt-in real-browser calibration.

Set ROUNDTABLE_BROWSER_CALIBRATE=1 with the existing Playwright/Chrome environment
to run the authored browser controls. No model or external service is called.
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test/shiploop_e2e"
sys.path.insert(0, str(HARNESS))
import boundary
import chains

spec = importlib.util.spec_from_file_location("roundtable_accept", HARNESS / "checks/roundtable_accept.py")
accept = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accept)
CASES = json.loads((HARNESS / "cases.json").read_text())
NAMES = ("roundtable", "roundtable-rooms", "roundtable-agent-work")
FIXTURE = HARNESS / "fixtures/roundtable"


class CatalogTests(unittest.TestCase):
    def test_cases_extend_behavior_without_repeating_the_direction_or_adding_caps(self):
        for index, name in enumerate(NAMES):
            case = CASES[name]
            self.assertEqual(case.get("follows"), NAMES[index - 1] if index else None)
            self.assertIn("app", case["prompt"])
            self.assertEqual("Gemini" in case["prompt"], index == 0)
            self.assertNotIn("Buzz", case["prompt"])
            for limit in ("timeout", "check_timeout", "max_turns", "budget"):
                self.assertNotIn(limit, case)
            expected = ["conversation", "rooms", "agent-work"][:index + 1]
            block = case["quality"]["acceptance"]
            self.assertEqual([row["id"] for row in block["checks"]], expected)
            self.assertTrue(all(ident in accept.CHECKS for ident in expected))
            self.assertTrue(all(row.get("source") for row in block["checks"]))

    def test_browser_and_fixture_bytes_are_in_digest_and_withholding_boundaries(self):
        files = set(boundary.oracle_files(HARNESS))
        withheld = set(boundary.held_out_files({name: CASES[name] for name in NAMES}))
        for relative in ("checks/roundtable_accept.py", "checks/roundtable_accept.cjs",
                         "fixtures/roundtable/server.cjs", "fixtures/roundtable/reference.html"):
            self.assertIn(HARNESS / relative, files)
            self.assertIn("test/shiploop_e2e/" + relative, withheld)

    def test_existing_chain_keeps_public_checks_and_final_acceptance(self):
        # Same lookup used by the runner; no new chain or acceptance-merging rule.
        chain = chains.of(CASES, "roundtable-agent-work")
        self.assertEqual(chain, list(NAMES))
        checks = chains.regression(CASES, "roundtable-agent-work")
        self.assertTrue(any("roundtable_contract.py" in command for command in checks))
        block = chains.quality(CASES, "roundtable-agent-work")["acceptance"]
        self.assertEqual([row["id"] for row in block["checks"]], ["conversation", "rooms", "agent-work"])


class ObservationBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "product"
        self.folder.mkdir()
        (self.folder / "app.js").write_text("original\n")

    def result(self, report, *, code=0, mutate=False):
        folder, output = self.folder, self.root / "observation"
        class Product:
            def scratch(self):
                output.mkdir(exist_ok=True)
                return output
            def run(self, argv, *, ceiling):
                assert math.isinf(ceiling), "the observer introduces no new timer"
                if report is not None:
                    (output / "observation.json").write_text(json.dumps(report))
                if mutate:
                    (folder / "app.js").write_text("changed\n")
                return {"returncode": code, "timeout": False}
        product = Product()
        product.folder = folder
        return accept.observe("http://127.0.0.1:1234", product, "conversation")

    def good(self):
        return {"base":"http://127.0.0.1:1234", "mode":"conversation", "observed":True,
                "complete":True, "checks":[{"id":"actual-action", "pass":True}]}

    def test_complete_observation_is_bound_to_unchanged_product(self):
        self.assertIs(self.result(self.good())[0], True)
        report = json.loads((self.root / "observation/observation.json").read_text())
        self.assertEqual(report["source_before"], report["source_after"])

    def test_missing_unavailable_mismatched_or_malformed_evidence_stays_unknown(self):
        for change in (None, {"observed":False}, {"mode":"rooms"}, {"base":"http://other/"}, {"checks":[]},
                       {"checks":[{"pass":True}]}, {"checks":[{"id":"x", "pass":"true"}]}, {"checks":[7]}):
            with self.subTest(change=change):
                report = None if change is None else {**self.good(), **change}
                self.assertIsNone(self.result(report)[0])
                (self.root / "observation/observation.json").unlink(missing_ok=True)

    def test_failed_action_or_incomplete_run_is_not_a_pass(self):
        for change, code in (({"checks":[{"id":"send", "pass":False}]}, 1), ({"complete":False}, 0), ({}, 1)):
            with self.subTest(change=change, code=code):
                self.assertIs(self.result({**self.good(), **change}, code=code)[0], False)

    def test_changed_delivery_is_unqualified_even_with_green_assertions(self):
        self.assertIsNone(self.result(self.good(), mutate=True)[0])

    def test_non_object_report_is_unknown(self):
        for report in ([], 7, "invalid"):
            with self.subTest(report=report):
                self.assertIsNone(self.result(report)[0])


@unittest.skipUnless(os.environ.get("ROUNDTABLE_BROWSER_CALIBRATE") == "1", "opt-in real-browser calibration")
class BrowserCalibrationTests(unittest.TestCase):
    @contextlib.contextmanager
    def server(self, fault="", alternate=False, variant=""):
        env = {**os.environ, "PORT":"0", "ROUNDTABLE_FAULT":fault,
               "ROUNDTABLE_VARIANT":variant or ("alternate" if alternate else "standard")}
        process = subprocess.Popen(["node", str(FIXTURE / "server.cjs")], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = process.stdout.readline()
            self.assertTrue(line.startswith("ready "), line)
            yield "http://127.0.0.1:" + line.split()[1]
        finally:
            process.terminate()
            process.communicate()

    def observe(self, mode, *, fault="", alternate=False, variant=""):
        retained = os.environ.get("ROUNDTABLE_CALIBRATION_OUTPUT")
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as transient:
            output = Path(tempfile.mkdtemp(prefix=mode + "-" + (fault or variant or ("alternate" if alternate else "good")) + "-",
                                           dir=retained or transient))
            with self.server(fault, alternate, variant) as base:
                process = subprocess.run(["node", str(accept.DRIVER), base, mode, str(output)],
                                         capture_output=True, text=True)
            (output / "process.json").write_text(json.dumps({"returncode":process.returncode,
                                                            "stdout":process.stdout, "stderr":process.stderr}, indent=2))
            report = json.loads((output / "observation.json").read_text())
            self.assertTrue(report["observed"], report.get("error"))
            return process.returncode, report

    def test_correct_and_equivalent_interfaces_pass_each_rung(self):
        for alternate in (False, True):
            for mode in ("conversation", "rooms", "agent-work"):
                with self.subTest(alternate=alternate, mode=mode):
                    code, report = self.observe(mode, alternate=alternate)
                    self.assertEqual(code, 0, report.get("error"))
                    self.assertTrue(report["complete"])
                    self.assertTrue(report["captures"])
                    self.assertTrue(all(row["pass"] for row in report["checks"]))
                    self.assertTrue(all(row["conversation"] is not None for row in report["measurements"]))

    def test_equivalent_async_layout_and_message_presentations_pass(self):
        for mode, variant in (("conversation","delayed-processing"), ("rooms","delayed-processing"),
                              ("agent-work","delayed-processing"), ("conversation","responsive-colors"),
                              ("rooms","all-collapsed"), ("agent-work","all-collapsed"),
                              ("conversation","inline-body"), ("conversation","thinking-status"),
                              ("agent-work","task-panel"), ("agent-work","task-panel-reversed"),
                              ("conversation","theme-transition"),
                              ("rooms","modal-drawer"), ("agent-work","modal-drawer"),
                              ("conversation","context-title"), ("conversation","paragraph-lines")):
            with self.subTest(mode=mode, variant=variant):
                code, report = self.observe(mode, variant=variant)
                self.assertEqual(code, 0, report.get("error"))
                self.assertTrue(report["complete"])

    def test_each_defect_fails_its_designated_observation(self):
        defects = (
            ("conversation", "multiline-loss", "multiline-sent-line-breaks"),
            ("conversation", "retry-duplicate", "retry-no-duplicate-person"),
            ("conversation", "dark-control-noop", "appearance-values-changed"),
            ("conversation", "horizontal-overflow", "light-390-composer-reachable"),
            ("rooms", "room-draft-leak", "design-own-draft"),
            ("rooms", "room-reply-leak", "reply-not-in-wrong-room"),
            ("rooms", "unread-stuck", "unread-cleared"),
            ("agent-work", "late-complete", "late-response-stays-cancelled"),
            ("agent-work", "retry-overwrite", "retry-new-attempt"),
            ("agent-work", "result-draft-loss", "result-draft-retained"),
            ("agent-work", "delayed-late-complete", "late-response-stays-cancelled"),
            ("agent-work", "incomplete-plan", "cancel-plan-contract"),
        )
        for mode, fault, intended in defects:
            with self.subTest(fault=fault):
                code, report = self.observe(mode, fault=fault)
                self.assertNotEqual(code, 0)
                self.assertEqual([row["id"] for row in report["checks"] if not row["pass"]], [intended], report.get("error"))


if __name__ == "__main__":
    unittest.main()
