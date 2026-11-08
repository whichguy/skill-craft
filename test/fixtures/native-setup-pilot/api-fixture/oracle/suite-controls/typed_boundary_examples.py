"""Follow-up examples for typed proposal boundaries omitted by a generated suite.

These cases remain outside the subject and the original six-fault comparison.
They check public contract behavior on both correct implementations; they are
not evidence that the original generated suite covered these inputs.
"""
import unittest

import change_app


class TypedProposalBoundaryExamples(unittest.TestCase):
    def setUp(self):
        change_app.fixture_seed()

    def assert_rejected(self, parameter, value):
        arguments = {
            "actor": "alice",
            "record_id": "demo-1",
            "expected_version": 1,
            "changes": {"amount": 25},
            "idempotency_key": "typed-boundary",
        }
        arguments[parameter] = value
        before = change_app.read_record("alice", "demo-1")
        result = change_app.propose_change(**arguments)
        self.assertEqual(set(result), {"ok", "error"})
        self.assertIs(result["ok"], False)
        error = result["error"]
        self.assertIsInstance(error, str)
        self.assertRegex(error, r"^[A-Za-z_]\w*(?:Error|Exception)\b")
        self.assertIn(parameter, error)
        self.assertLessEqual(len(error), 120)
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)

    def test_non_string_record_id_is_rejected_without_mutation(self):
        for value in (42, [], {"id": "demo-1"}):
            with self.subTest(value=value):
                self.assert_rejected("record_id", value)

    def test_non_integer_version_is_rejected_without_mutation(self):
        for value in ("1", 1.0, True):
            with self.subTest(value=value):
                self.assert_rejected("expected_version", value)

    def test_non_string_key_is_rejected_without_mutation(self):
        for value in (7, [], {}):
            with self.subTest(value=value):
                self.assert_rejected("idempotency_key", value)

    def test_non_dict_changes_are_rejected_without_mutation(self):
        for value in ([], [("amount", 25)], "amount=25"):
            with self.subTest(value=value):
                self.assert_rejected("changes", value)


if __name__ == "__main__":
    unittest.main()
