"""Prevent process-only or partial campaigns from being called qualified."""
import unittest
import claude_suite


class AcceptanceTests(unittest.TestCase):
    def test_exact_complete_pass(self):
        self.assertTrue(claude_suite.accepted({"commands": [{"exit_code": 0}] * 5},
                                              {"status": "PASS", "passed": True}))

    def test_every_phase_required(self):
        for n in (0, 1, 4, 6):
            self.assertFalse(claude_suite.accepted({"commands": [{"exit_code": 0}] * n},
                                                 {"status": "PASS", "passed": True}))

    def test_noninteger_exit_not_success(self):
        for code in (False, None, "0", 1):
            self.assertFalse(claude_suite.accepted({"commands": [{"exit_code": 0}] * 4 + [{"exit_code": code}]},
                                                 {"status": "PASS", "passed": True}))

    def test_verdict_requires_both_fields(self):
        for verdict in ({"status": "PASS"}, {"passed": True}, {"status": "PASS", "passed": 1},
                        {"status": "INCOMPLETE", "passed": True}, None):
            self.assertFalse(claude_suite.accepted({"commands": [{"exit_code": 0}] * 5}, verdict))


if __name__ == "__main__":
    unittest.main()
