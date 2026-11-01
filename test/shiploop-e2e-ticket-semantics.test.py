#!/usr/bin/env python3
"""No-model checks for the offline ticket semantic probe."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "test" / "shiploop_e2e" / "probes" / "ticket_semantics.py"
SPEC = importlib.util.spec_from_file_location("ticket_semantics_probe", PROBE_PATH)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class TapClassification(unittest.TestCase):
    def test_exact_pass_is_valid(self):
        report = """TAP version 13
1..1
# tests 1
# pass 1
# fail 0
# cancelled 0
# skipped 0
# todo 0
"""
        result = probe.classify(report, 0, 1)
        self.assertEqual((result["outcome"], result["validity"]), ("PASS", "valid"))

    def test_named_behavior_failure_is_valid_failure(self):
        report = """TAP version 13
not ok 1 - SEM_CLOCK_1 same-agent no-op preserves updated after deterministic clock advance
1..1
# tests 1
# pass 0
# fail 1
# cancelled 0
# skipped 0
# todo 0
"""
        result = probe.classify(report, 1, 1)
        self.assertEqual((result["outcome"], result["validity"]), ("FAIL", "valid"))
        self.assertEqual(len(result["failed_names"]), 1)

    def test_expected_count_mismatch_is_unknown_even_when_node_exits_zero(self):
        report = """TAP version 13
1..1
# tests 1
# pass 1
# fail 0
# cancelled 0
# skipped 0
# todo 0
"""
        result = probe.classify(report, 0, 2)
        self.assertEqual((result["outcome"], result["validity"]), ("UNKNOWN", "count_mismatch"))

    def test_zero_tests_is_unknown_not_a_pass(self):
        report = """TAP version 13
1..0
# tests 0
# pass 0
# fail 0
# cancelled 0
# skipped 0
# todo 0
"""
        result = probe.classify(report, 0, 1)
        self.assertEqual((result["outcome"], result["validity"]), ("UNKNOWN", "count_mismatch"))

    def test_timeout_and_setup_failure_remain_distinct_unknowns(self):
        timeout = probe.classify("", -1, 1, validity="timeout")
        setup = probe.classify("", -1, 1, validity="setup_failure")
        self.assertEqual((timeout["outcome"], timeout["validity"]), ("UNKNOWN", "timeout"))
        self.assertEqual((setup["outcome"], setup["validity"]), ("UNKNOWN", "setup_failure"))


class ExplicitTestFiles(unittest.TestCase):
    def test_only_explicit_root_relative_files_are_accepted(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "test").mkdir()
            (root / "test" / "one.test.js").write_text("// fixture\n")
            self.assertEqual(probe.explicit_files(root, ["test/one.test.js"], "suite"), ["test/one.test.js"])
            for invalid in (["test/*.test.js"], ["../one.test.js"], ["/tmp/one.test.js"]):
                with self.subTest(invalid=invalid), self.assertRaises(probe.SetupError):
                    probe.explicit_files(root, invalid, "suite")
            with self.assertRaises(probe.SetupError):
                probe.explicit_files(root, ["test/one.test.js", "test/one.test.js"], "suite")


class RepetitionAggregation(unittest.TestCase):
    def test_three_declared_clock_repetitions_aggregate_as_four_attempts(self):
        plans = [
            ("clock", "clock_probe", ["test/clock.js"], 1, "PASS", 3),
            ("control", "original", ["test/original.js"], 1, "PASS", 1),
        ]
        results = [{"prediction_matched": True} for _ in range(4)]
        self.assertEqual(probe.expected_attempt_count(plans), 4)
        self.assertTrue(probe.predictions_match(results, plans, source_unchanged=True, runtime_unchanged=True))
        self.assertFalse(probe.predictions_match(results[:3], plans, source_unchanged=True, runtime_unchanged=True))

    def test_zero_expected_count_or_repetition_is_rejected(self):
        with self.assertRaises(probe.SetupError):
            probe.validate_positive_counts(116, 6, 6, 0)
        with self.assertRaises(probe.SetupError):
            probe.validate_positive_counts(116, 0, 6, 3)


if __name__ == "__main__":
    unittest.main()
