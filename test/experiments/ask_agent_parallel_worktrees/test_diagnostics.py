"""Focused contract tests for diagnostics.py; uses only the Python standard library."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import diagnostics


class DiagnosticTests(unittest.TestCase):
    def test_fixture_failure_has_expected_observed_and_exact_report_pointer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "verification.json"
            report = {"checks": {"combined_pipeline_oracle_passes": False}}
            report_path.write_text(json.dumps(report), encoding="utf-8")

            records = diagnostics.report_check_diagnostics(
                report, report_path, phase="verify"
            )

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["schema"], diagnostics.SCHEMA)
        self.assertEqual(record["code"], "PIPELINE_ORACLE_FAILED")
        self.assertEqual(record["severity"], "error")
        self.assertEqual(record["phase"], "verify")
        self.assertIn("ascending-task pipeline", record["expected"])
        self.assertIs(record["observed"], False)
        self.assertEqual(record["rationale_ref"], "CONTRACT.md#pass-gates")
        self.assertEqual(record["evidence"][0]["json_pointer"], "/checks/combined_pipeline_oracle_passes")
        self.assertEqual(record["evidence"][0]["hash_status"], "hashed")
        self.assertEqual(len(record["evidence"][0]["sha256"]), 64)

    def test_native_unknown_is_warning_with_report_and_event_citations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "native-verification.json"
            event_path = root / "root-updates.jsonl"
            event_bytes=b'{"type":"example"}\n'
            event_path.write_bytes(event_bytes)
            report = {
                "checks": {
                    "parent_collected_all_children": {
                        "status": "UNKNOWN",
                        "detail": "one terminal collection event is not available",
                        "evidence": [{"path": str(event_path), "line": 8}],
                    }
                }
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")

            records = diagnostics.report_check_diagnostics(
                report, report_path, phase="native-audit"
            )

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["severity"], "warning")
        self.assertIn("terminal typed result", record["expected"])
        self.assertEqual(record["observed"]["status"], "UNKNOWN")
        self.assertEqual(record["evidence"][0]["json_pointer"], "/checks/parent_collected_all_children")
        event_ref = record["evidence"][1]
        self.assertEqual(event_ref["path"], str(event_path))
        self.assertEqual(event_ref["line"], 8)
        self.assertEqual(
            event_ref["report_pointer"],
            "/checks/parent_collected_all_children/evidence/0",
        )
        self.assertEqual(event_ref["sha256"], hashlib.sha256(event_bytes).hexdigest())

    def test_missing_nested_evidence_is_cited_without_a_hash_or_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "native-verification.json"
            missing_path = root / "not-retained.jsonl"
            report = {
                "checks": {
                    "parent_terminal": {
                        "status": "INCOMPLETE",
                        "detail": "parent has not exited",
                        "evidence": [{"path": str(missing_path), "line": 4}],
                    }
                }
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")

            record = diagnostics.report_check_diagnostics(
                report, report_path, phase="native-audit"
            )[0]

        missing_ref = record["evidence"][1]
        self.assertEqual(missing_ref["path"], str(missing_path))
        self.assertEqual(missing_ref["hash_status"], "missing")
        self.assertNotIn("sha256", missing_ref)
        self.assertEqual(record["severity"], "warning")
        self.assertEqual(record["observed"]["status"], "INCOMPLETE")

    def test_json_pointer_escapes_report_check_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"
            report_path.write_text("{}", encoding="utf-8")
            custom_rule = diagnostics.CheckRule(
                code="CUSTOM_CHECK_FAILED",
                expected="The named check passes.",
                rationale="This custom check is explicitly mapped by its caller.",
                recovery="Inspect the mapped check.",
            )
            record = diagnostics.report_check_diagnostics(
                {"checks": {"odd/~name": False}},
                report_path,
                phase="verify",
                rules={"odd/~name": custom_rule},
            )[0]

        self.assertEqual(record["evidence"][0]["json_pointer"], "/checks/odd~1~0name")

    def test_unmapped_false_check_is_not_recast_as_a_generic_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"
            report_path.write_text("{}", encoding="utf-8")
            records = diagnostics.report_check_diagnostics(
                {"checks": {"future_check": False}}, report_path, phase="verify"
            )

        self.assertEqual(records, [])

    def test_integration_check_uses_integrity_pointer_and_matching_action_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "integration-result.json"
            action_path = root / "patch-check.json"
            action_path.write_text('{"exit_code":1}\n', encoding="utf-8")
            report = {
                "integrity_checks": {
                    "worker_2_patch_paths_exact": {
                        "passed": False,
                        "details": {"paths": ["src/step_2.py", "notes.txt"]},
                    }
                },
                "failure": {
                    "code": "PATCH_PATHS_INVALID",
                    "phase": "worker_2_patch_paths_exact",
                    "expected": ["src/step_2.py"],
                    "observed": {"paths": ["src/step_2.py", "notes.txt"]},
                    "evidence_path": str(action_path),
                },
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")

            records = diagnostics.report_check_diagnostics(
                report, report_path, phase="integrate"
            )

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["code"], "PATCH_PATHS_INVALID")
        self.assertEqual(record["severity"], "error")
        self.assertIn("Worker 2", record["expected"])
        self.assertEqual(record["evidence"][0]["json_pointer"], "/integrity_checks/worker_2_patch_paths_exact")
        self.assertEqual(record["evidence"][1]["path"], str(action_path))
        self.assertEqual(
            record["evidence"][1]["report_pointer"],
            "/failure/evidence_path",
        )

    def test_operation_failure_maps_only_a_known_structured_category(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / "integration-result.json"
            action_path = root / "patch-apply.json"
            action_path.write_text('{"exit_code":1}\n', encoding="utf-8")
            report = {
                "failure": {
                    "code": "PATCH_APPLY_FAILED",
                    "phase": "patch-apply-2",
                    "expected": "exit_code == 0",
                    "observed": {"exit_code": 1, "stderr": "conflict"},
                    "evidence_path": str(action_path),
                    "retry_semantics": "Retain prior applied modules; do not rerun.",
                }
            }
            report_path.write_text(json.dumps(report), encoding="utf-8")

            record = diagnostics.operation_failure_diagnostic(report, report_path)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["code"], "PATCH_APPLY_FAILED")
        self.assertEqual(record["phase"], "patch-apply-2")
        self.assertEqual(record["expected"], "exit_code == 0")
        self.assertEqual(record["observed"]["stderr"], "conflict")
        self.assertEqual(record["evidence"][1]["path"], str(action_path))
        self.assertEqual(record["retry_safety"], "Retain prior applied modules; do not rerun.")

    def test_unknown_operation_failure_is_left_uninterpreted(self):
        self.assertIsNone(
            diagnostics.operation_failure_diagnostic(
                {"failure": {"code": "SOME_FUTURE_FAILURE", "phase": "later"}},
                "/tmp/result.json",
            )
        )

    def test_emission_writes_the_same_json_line_to_stderr_and_append_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            log_path = Path(temporary) / "diagnostics.jsonl"
            stderr = io.StringIO()
            record = diagnostics.make_diagnostic(
                code="FIXTURE_SCOPE_INVALID",
                severity="error",
                phase="prepare",
                expected="worker IDs are 1..N",
                observed={"worker_ids": ["1", "3"]},
                rationale="The manifest does not match the fixture assignment contract.",
                rationale_ref="CONTRACT.md#pass-gates",
                evidence=[],
                recovery="Preserve the run and inspect the manifest.",
                retry_safety="Use a fresh run after reconciling the manifest.",
            )

            diagnostics.emit_diagnostics([record], jsonl_path=log_path, stream=stderr)

            stderr_row = json.loads(stderr.getvalue())
            log_row = json.loads(log_path.read_text(encoding="utf-8"))

        self.assertEqual(stderr_row, record)
        self.assertEqual(log_row, record)

    def test_exit_helper_uses_cli_error_status(self):
        diagnostic = diagnostics.make_diagnostic(
            code="FIXTURE_SCOPE_INVALID",
            severity="error",
            phase="prepare",
            expected="the manifest is valid",
            observed="invalid",
            rationale="The operational prerequisite was not satisfied.",
            rationale_ref="CONTRACT.md#pass-gates",
            evidence=[],
            recovery="Inspect the retained manifest.",
            retry_safety="Do not reuse a partially prepared run.",
        )
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            diagnostics.exit_with_diagnostic(diagnostic)

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(json.loads(stderr.getvalue())["code"], "FIXTURE_SCOPE_INVALID")


if __name__ == "__main__":
    unittest.main()
