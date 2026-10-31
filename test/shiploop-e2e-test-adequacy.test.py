#!/usr/bin/env python3
"""Calibrate the ticket test-writing case; no model calls.

Run: python3 -B test/shiploop-e2e-test-adequacy.test.py
Set SHIPLOOP_ADEQUACY_CALIBRATION_ROOT to retain every report/copy/log externally.
The delivered product is tests, so a correct implementation passing is necessary
but insufficient: useful tests reject binding violations and accept valid edits.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(HARNESS / "checks"))

import boundary  # noqa: E402
import brownfield  # noqa: E402
import quality  # noqa: E402
import ticket_test_adequacy as observer  # noqa: E402
import ticket_test_variants as variants  # noqa: E402

CASE_ID = "ticket-assignment-tests"
CASE = json.loads((HARNESS / "cases.json").read_text())[CASE_ID]
STRONG = ROOT / "test" / "fixtures" / "quality" / "ticket_adequacy_strong.test.js"
ALTERNATIVE = STRONG.with_name("ticket_adequacy_alternative.test.js")
REFERENCE_PATH = ROOT / "test" / "fixtures" / "quality" / "reference_ticket_assignment.py"


def reference_module():
    spec = importlib.util.spec_from_file_location("ticket_assignment_calibration_source", REFERENCE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def files(folder: Path) -> dict[str, str]:
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def normalized_source_guard(delivery: Path) -> str:
    def normal(text):
        text = re.sub(r"/\*[\s\S]*?\*/", "", text)
        return re.sub(r"\s+", "", re.sub(r"//[^\n]*", "", text))
    expected = {name: hashlib.sha256(normal((delivery / name).read_text()).encode()).hexdigest()
                for name in files(delivery) if name.startswith(("src/", "bin/", "scripts/"))
                and name != "src/tickets/query.js"}
    return (
        "const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),"
        "path=require('node:path'),crypto=require('node:crypto');\n"
        "const norm=s=>s.replace(/\\/\\*[\\s\\S]*?\\*\\//g,'').replace(/\\/\\/[^\\n]*/g,'').replace(/\\s+/g,'');\n"
        "test('normalized production snapshot',()=>{for(const [file,want] of Object.entries("
        + json.dumps(expected) + ")){assert.equal(crypto.createHash('sha256').update(norm(fs.readFileSync("
        "path.join(__dirname,'..',file),'utf8'))).digest('hex'),want);}\n"
        "const q=norm(fs.readFileSync(path.join(__dirname,'../src/tickets/query.js'),'utf8'));"
        "assert.ok(!q.includes('given.some('));assert.ok(q.includes('constDEFAULT_LIMIT=20;'));"
        "assert.ok(q.includes(\"params.has('assignee')\"));});\n")


class CaseContract(unittest.TestCase):
    def test_correct_reference_is_pinned_without_reference_added_tests(self):
        reference = reference_module()
        self.assertEqual(brownfield.resolve(CASE), observer.FIXTURE)
        self.assertEqual(CASE["base"]["digest"], "f0e486c77413")
        with tempfile.TemporaryDirectory() as raw:
            built = Path(raw) / "reference"
            reference.build(built, "reference")
            for name in reference.REFERENCE_ADDED:
                (built / name).unlink()
            self.assertEqual(files(built), files(observer.FIXTURE))

    def test_grading_variants_are_the_independently_calibrated_src_only_catalog(self):
        reference = reference_module()
        expected = {name: tuple(tuple(edit) for edit in edits) for name, edits in reference.DEFECTS.items()
                    if name not in {"backoff-linear", "validate-renamed"}}
        self.assertEqual(variants.DEFECTS, expected)
        self.assertEqual(len(expected), 25)
        self.assertTrue(all(edit[0].startswith("src/") for edits in expected.values() for edit in edits))
        self.assertEqual(variants.SOURCE_COMMIT, "c51e218a683a18b01a1b692485cec95512b1d372")
        self.assertEqual(set(observer.CHECKS), {"suite-baseline", "preserve-fixture", "added-tests", "behavior-controls"}
                         | set(expected))
        self.assertEqual(set(observer.CHECKS), {row["id"] for row in CASE["quality"]["acceptance"]["checks"]})

    def test_all_grading_inputs_are_inside_the_qualification_boundary_and_withheld(self):
        cases = json.loads((HARNESS / "cases.json").read_text())
        withheld = boundary.held_out_files(cases)
        for relative in ("test/shiploop_e2e/checks/ticket_test_adequacy.py",
                         "test/shiploop_e2e/checks/ticket_test_variants.py",
                         "test/fixtures/quality/ticket_adequacy_alternative.test.js",
                         "test/fixtures/quality/ticket_adequacy_strong.test.js",
                         "test/shiploop-e2e-test-adequacy.test.py"):
            self.assertIn(relative, withheld)
            self.assertTrue((ROOT / relative).is_file())
        source = (HARNESS / "checks" / "ticket_test_adequacy.py").read_text()
        self.assertNotIn("import reference_ticket_assignment", source)
        self.assertEqual(CASE["quality"]["refuse_ports"], [4180])

    def test_socket_reset_cannot_count_as_a_behavioral_rejection(self):
        # Calibration-02 falsely called a base-suite ECONNRESET a killed contract
        # violation. Feed the observed transport failure through the same path.
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw)
            log = output / "observed-reset.log"
            text = ("ℹ tests 117\nℹ pass 116\nℹ fail 1\n✖ failing tests:\n"
                    "test at test/api.test.js:116:3\n✖ filters by status\n"
                    "  Error: socket hang up\n    code: 'ECONNRESET'\n")
            log.write_text(text)
            record = {"command": ["node", "--test"], "code": 1, "timeout": False, "seconds": 0.3,
                      "counts": {"tests": 117, "pass": 116, "fail": 1}, "port_refusals": 0,
                      "log": str(log), "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                      "output_tail": text}
            with mock.patch.object(observer, "_run_command", return_value=record):
                result = observer._apply_run(observer.FIXTURE, output, "transport-reset", ())
            self.assertEqual(result["status"], "invalid")
            self.assertIn("network", result["reason"])
            self.assertEqual(result["network_reruns"], 2)
            self.assertEqual(len(result["observation_attempts"]), 3)

    def test_passing_test_titles_are_not_infrastructure_errors(self):
        for title in ("oversized body is answered instead of a socket hang up", "could not find invalid input", "SyntaxError: is handled"):
            with self.subTest(title=title):
                record = {"code": 0, "timeout": False, "port_refusals": 0,
                          "counts": {"tests": 118, "pass": 118, "fail": 0},
                          "output_tail": f"✔ {title}\nℹ tests 118\nℹ pass 118\nℹ fail 0\n"}
                self.assertIsNone(observer._invalid_reason(record))

    def test_invalid_assessment_makes_every_case_row_unknown(self):
        report = {"summary": {"invalid_count": 1}, "checks": dict.fromkeys(observer.CHECKS, True),
                  "defects": {name: {"status": "killed"} for name in variants.DEFECTS},
                  "defect_rows_eligible": True, "report_path": "/quality/report.json", "report_sha256": "f" * 64}
        with mock.patch.object(observer, "_assessment_for_product", return_value=report):
            for name, check in observer.CHECKS.items():
                with self.subTest(row=name):
                    passed, note = check("unused", object())
                    self.assertIsNone(passed)
                    self.assertIn(report["report_sha256"], note)

    @unittest.skipUnless(shutil.which("node"), "the observer requires Node.js")
    def test_normalized_source_detector_cannot_earn_behavioral_accuracy(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            delivery = root / "delivery"
            shutil.copytree(observer.FIXTURE, delivery)
            (delivery / "test" / "source-guard.test.js").write_text(normalized_source_guard(delivery))
            report = observer.assess(delivery, root / "assessment")
            self.assertEqual(report["summary"]["invalid_count"], 0)
            self.assertEqual(report["summary"]["killed"], 25)
            self.assertFalse(report["defect_rows_eligible"])

    def test_benign_test_configuration_is_allowed_but_code_and_dependencies_are_not(self):
        with tempfile.TemporaryDirectory() as raw:
            delivery = Path(raw) / "delivery"
            shutil.copytree(observer.FIXTURE, delivery)
            (delivery / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {"": {"name": "helpdesk-tickets", "version": "1.4.0"}}}))
            workflow = delivery / ".github/workflows/test.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: tests\non: push\njobs: {}\n")
            self.assertTrue(observer._protected_integrity(delivery)["pass"])
            (delivery / "new-production.js").write_text("module.exports = {};\n")
            self.assertFalse(observer._protected_integrity(delivery)["pass"])
            (delivery / "new-production.js").unlink()
            (delivery / "package-lock.json").write_text(json.dumps({"packages": {"node_modules/new-dependency": {}}}))
            self.assertFalse(observer._protected_integrity(delivery)["pass"])

    def test_network_recovery_keeps_raw_attempts_and_stops_at_first_valid_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw)
            folders = []
            def command(folder, run_dir, argv, *, product=None):
                folders.append(folder)
                self.assertFalse((folder / "transient.data").exists(), "reruns must start from the original delivery")
                run_dir.mkdir(parents=True)
                if len(folders) == 1:
                    (folder / "transient.data").write_text("only in the first disposable copy")
                    details = "  Error: socket hang up\n    code: 'ECONNRESET'"
                else:
                    details = "  AssertionError: the behavior is wrong\n    code: 'ERR_ASSERTION'"
                log = run_dir / "stdout.log"
                log.write_text(details)
                return {"command": argv, "code": 1, "timeout": False, "seconds": 0.1,
                        "counts": {"tests": 117, "pass": 116, "fail": 1}, "port_refusals": 0,
                        "log": str(log), "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                        "output_tail": details, "failure_details": details}
            with mock.patch.object(observer, "_run_command", side_effect=command) as ran:
                result = observer._apply_run(observer.FIXTURE, output, "network-recovery", ())
            self.assertEqual(ran.call_count, 2)
            self.assertEqual(result["status"], "failed", "a valid failure must stop recovery")
            self.assertEqual(result["network_reruns"], 1)
            self.assertEqual([row["status"] for row in result["observation_attempts"]], ["invalid", "failed"])
            self.assertNotEqual(folders[0], folders[1])
            for row in result["observation_attempts"]:
                self.assertTrue(Path(row["log"]).is_file())

    def test_known_results_and_other_invalids_are_not_retried(self):
        for status, reason in (("passed", "valid pass"), ("failed", "valid failure"),
                               ("invalid", "command timed out after 120 seconds"),
                               ("invalid", "syntax/setup validation failed")):
            with self.subTest(status=status, reason=reason), tempfile.TemporaryDirectory() as raw:
                record = {"status": status, "reason": reason, "seconds": 0.1}
                with mock.patch.object(observer, "_apply_run_once", return_value=record) as ran:
                    result = observer._apply_run(observer.FIXTURE, Path(raw), "observation", ())
                self.assertEqual(ran.call_count, 1)
                self.assertEqual(result["network_reruns"], 0)


@unittest.skipUnless(shutil.which("node"), "the fixture and its test suite require Node.js")
class BehavioralCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        supplied = os.environ.get("SHIPLOOP_ADEQUACY_CALIBRATION_ROOT")
        cls.temporary = None if supplied else tempfile.TemporaryDirectory(prefix="ticket-adequacy-")
        cls.root = Path(supplied or cls.temporary.name).resolve()
        cls.root.mkdir(parents=True, exist_ok=True)
        cls.before = files(observer.FIXTURE)
        cls.reports = {}
        cls.deliveries = {}
        cls.delivery_before = {}
        cls.env = mock.patch.dict(os.environ, {"TMPDIR": str(cls.root / "tmp")})
        (cls.root / "tmp").mkdir(exist_ok=True)
        cls.env.start()
        reference = reference_module()
        for name in ("weak", "reference", "strong", "alternative", "no-assert", "hash-only", "strong-plus-hash", "production-edit"):
            delivery = cls.root / "deliveries" / name
            shutil.copytree(observer.FIXTURE, delivery)
            if name == "reference":
                for relative, text in reference.REFERENCE_ADDED.items():
                    (delivery / relative).write_text(text)
            if name in {"strong", "strong-plus-hash", "production-edit"}:
                shutil.copy2(STRONG, delivery / "test" / "adequacy.test.js")
            if name == "alternative":
                shutil.copy2(ALTERNATIVE, delivery / "test" / "independent-coverage.test.js")
            if name == "no-assert":
                # Ordinary JS under test/ is also discovered by Node, without a .test suffix.
                (delivery / "test" / "added-coverage.js").write_text(
                    "require('node:test').test('an empty added case', () => {});\n")
            if name in {"hash-only", "strong-plus-hash"}:
                protected = {relative: digest for relative, digest in files(delivery).items()
                             if relative.startswith(("src/", "bin/", "scripts/")) or relative == "package.json"}
                (delivery / "test" / "hash-only.test.js").write_text(
                    "const {test}=require('node:test'); const assert=require('node:assert/strict');\n"
                    "const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');\n"
                    "test('source bytes match',()=>{ for(const [file,want] of Object.entries("
                    + json.dumps(protected) + ")) {assert.equal(crypto.createHash('sha256').update("
                    "fs.readFileSync(path.join(__dirname,'..',file))).digest('hex'),want);} });\n")
            if name == "production-edit":
                with (delivery / "src" / "store.js").open("a") as handle:
                    handle.write("\n// The requested task forbids changing this production file.\n")
            cls.deliveries[name] = delivery
            cls.delivery_before[name] = files(delivery)
            cls.reports[name] = observer.assess(delivery, cls.root / "assessments" / name)
        (cls.root / "summary.json").write_text(json.dumps({name: {"guards": report["guards"],
                    "summary": report["summary"], "report": report["report_path"],
                    "report_sha256": report["report_sha256"]} for name, report in cls.reports.items()}, indent=2) + "\n")
        print("calibration evidence:", cls.root)
        print(json.dumps({name: report["summary"] for name, report in cls.reports.items()}, sort_keys=True))

    @classmethod
    def tearDownClass(cls):
        try:
            if files(observer.FIXTURE) != cls.before:
                raise AssertionError("the frozen original fixture changed during calibration")
        finally:
            cls.env.stop()
            if cls.temporary is not None:
                cls.temporary.cleanup()

    def test_baseline_weak_and_no_assert_addition_are_not_fully_adequate(self):
        weak, empty = self.reports["weak"], self.reports["no-assert"]
        self.assertTrue(weak["guards"]["suite-baseline"])
        self.assertFalse(weak["guards"]["added-tests"])
        self.assertTrue(empty["guards"]["added-tests"], "a valid added filename is not itself behavioral adequacy")
        self.assertEqual(weak["summary"]["invalid_count"], 0)
        self.assertEqual(empty["summary"]["invalid_count"], 0)
        self.assertLess(weak["summary"]["killed"], 25)
        self.assertEqual(weak["summary"]["killed"], empty["summary"]["killed"])
        expected = {row["id"] for row in CASE["quality"]["acceptance"]["checks"]
                    if row["grade"] == "pass-to-pass" and row["id"] in variants.DEFECTS}
        for report in (weak, empty):
            self.assertEqual({name for name, row in report["defects"].items() if row["status"] == "killed"}, expected)

    def test_original_reference_suite_has_valid_observations_without_presuming_completeness(self):
        report = self.reports["reference"]
        self.assertTrue(all(report["guards"].values()), report["guards"])
        self.assertEqual(report["summary"]["invalid_count"], 0)
        self.assertGreater(report["summary"]["killed"], self.reports["weak"]["summary"]["killed"])

    def test_independent_strong_suite_catches_all_known_violations_without_false_alarms(self):
        report = self.reports["strong"]
        self.assertEqual(report["baseline"]["pass"], 124)
        self.assertTrue(all(report["guards"].values()), report["guards"])
        self.assertEqual(report["summary"]["invalid_count"], 0)
        self.assertEqual(report["summary"]["killed"], 25)
        self.assertEqual(report["summary"]["survived"], 0)
        self.assertTrue(all(report["checks"].values()))

    def test_hash_only_suite_cannot_earn_behavioral_accuracy_by_detecting_source_edits(self):
        report = self.reports["hash-only"]
        self.assertTrue(report["guards"]["suite-baseline"])
        self.assertEqual(report["summary"]["invalid_count"], 0)
        self.assertEqual(report["summary"]["killed"], 25, "raw observed kills remain visible")
        self.assertFalse(report["guards"]["behavior-controls"])
        self.assertFalse(any(report["checks"][name] for name in variants.DEFECTS))

    def test_independent_alternative_suite_also_passes_without_matching_reference_tests(self):
        report = self.reports["alternative"]
        self.assertTrue(all(report["guards"].values()), report["guards"])
        self.assertEqual(report["summary"]["invalid_count"], 0)
        self.assertEqual(report["summary"]["killed"], 25)
        self.assertTrue(all(report["checks"].values()))

    def test_strong_behavior_tests_plus_source_checksum_are_ineligible_under_the_public_task(self):
        report = self.reports["strong-plus-hash"]
        self.assertTrue(report["guards"]["suite-baseline"])
        self.assertEqual(report["summary"]["killed"], 25)
        self.assertFalse(report["guards"]["behavior-controls"])
        self.assertFalse(report["defect_rows_eligible"])
        self.assertTrue(report["source_read_hints"])

    def test_modifying_production_cannot_earn_behavioral_accuracy(self):
        report = self.reports["production-edit"]
        self.assertTrue(report["guards"]["suite-baseline"])
        self.assertFalse(report["guards"]["preserve-fixture"])
        self.assertFalse(any(report["checks"][name] for name in variants.DEFECTS))

    def test_full_logs_and_hashes_are_retained_for_every_variant(self):
        for name, report in self.reports.items():
            with self.subTest(delivery=name):
                self.assertEqual(files(self.deliveries[name]), self.delivery_before[name],
                                 "assessment must not change the original delivery")
                path = Path(report["report_path"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), report["report_sha256"])
                self.assertEqual(len(report["defects"]), 25)
                for row in [report["baseline"], *report["controls"].values(), *report["defects"].values()]:
                    log = Path(row["log"])
                    self.assertTrue(log.is_file())
                    self.assertEqual(hashlib.sha256(log.read_bytes()).hexdigest(), row["log_sha256"])

    def test_same_observer_runs_through_real_quality_acceptance_once_per_product(self):
        groups = set()
        root = self.root / "quality-integration"
        delivery = self.root / "deliveries" / "strong-with-ci-metadata"
        shutil.copytree(self.deliveries["strong"], delivery)
        (delivery / "package-lock.json").write_text('{"lockfileVersion":3,"packages":{"":{}}}\n')
        workflow = delivery / ".github/workflows/test.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: tests\non: push\njobs: {}\n")
        result = quality.acceptance(delivery, CASE["quality"]["acceptance"], groups=groups,
                                    stop=lambda: None, logs=root / "quality" / "logs", ports=[4180])
        self.assertTrue(result["observed"], result)
        self.assertEqual(len(result["passed"]), 29)
        self.assertEqual(groups, set(), "all owned process groups finished")
        reports = list((root / "quality" / "logs").glob("product-*/scratch-*/report.json"))
        self.assertEqual(len(reports), 1, "29 rows share one assessment of this Product")
        expected = hashlib.sha256(reports[0].read_bytes()).hexdigest()
        for check in result["checks"]:
            self.assertLessEqual(len(check["note"]), 300)
            self.assertIn(expected, check["note"])
            match = re.search(r"report=([^;]+)", check["note"])
            self.assertIsNotNone(match)
            self.assertEqual((root / match.group(1)).resolve(), reports[0].resolve())

    def test_stale_and_unloadable_variants_are_invalid_not_kills(self):
        root = self.root / "invalid-controls"
        stale = observer._apply_run(self.deliveries["strong"], root, "stale", (("src/store.js", "ABSENT PATCH TEXT", "x"),))
        self.assertEqual(stale["status"], "invalid")
        bad_js = observer._apply_run(self.deliveries["strong"], root, "syntax", (("src/store.js", "'use strict';", "const = ;"),))
        self.assertEqual(bad_js["status"], "invalid")
        self.assertIn("syntax", bad_js["reason"])

    def test_real_timeout_is_invalid_and_ends_owned_processes(self):
        delivery = self.root / "deliveries" / "hang"
        shutil.copytree(observer.FIXTURE, delivery)
        (delivery / "test" / "hang.test.js").write_text(
            "const {test}=require('node:test'); test('never ends',()=>new Promise(()=>setInterval(()=>{},100)));\n")
        with mock.patch.object(observer, "RUN_SECONDS", 0.5):
            result = observer._apply_run(delivery, self.root / "invalid-controls", "timeout", ())
        self.assertTrue(result["timeout"])
        self.assertEqual(result["status"], "invalid")

    def test_test_time_source_edits_are_invalid_and_do_not_change_the_original(self):
        delivery = self.root / "deliveries" / "runtime-edit"
        shutil.copytree(observer.FIXTURE, delivery)
        (delivery / "test" / "rewrite.test.js").write_text(
            "require('node:test').test('writes production',()=>{require('node:fs').appendFileSync("
            "require('node:path').join(__dirname,'../src/store.js'),'\\n// changed by test\\n');});\n")
        before = files(delivery)
        result = observer._apply_run(delivery, self.root / "invalid-controls", "runtime-edit", ())
        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["post_run_integrity"]["pass"])
        self.assertIn("src/store.js", result["post_run_integrity"]["changed"])
        self.assertEqual(files(delivery), before)

    def test_a_mutant_only_notification_hang_remains_unknown_never_a_kill(self):
        delivery = self.root / "deliveries" / "unbounded-notification-wait"
        shutil.copytree(observer.FIXTURE, delivery)
        (delivery / "test" / "notification-wait.test.js").write_text(
            "const {test}=require('node:test');const {withService,ticketBody}=require('./helpers');\n"
            "test('waits for the assigned agent',async()=>withService({workerIntervalMs:10},async api=>{"
            "const made=await api.post('/tickets',ticketBody());"
            "await api.put('/tickets/'+made.body.id+'/assignee',{assignee:'agent@example.test'});"
            "while(!(await api.get('/admin/outbox')).body.sent.some(e=>e.to==='agent@example.test'))"
            "await new Promise(resolve=>setTimeout(resolve,5));}));\n")
        baseline = observer._apply_run(delivery, self.root / "invalid-controls", "notification-baseline", ())
        self.assertEqual(baseline["status"], "passed")
        with mock.patch.object(observer, "RUN_SECONDS", 1):
            mutant = observer._apply_run(delivery, self.root / "invalid-controls", "notification-mutant",
                                         variants.DEFECTS["notify-requester"])
        self.assertTrue(mutant["timeout"])
        self.assertEqual(mutant["status"], "invalid")
        self.assertEqual(mutant["network_reruns"], 0)


if __name__ == "__main__":
    unittest.main()
