"""A recorded assertion plus a skip must remain an invalid suite."""
import unittest


class SkippedAfterAssertion(unittest.TestCase):
    def test_not_accepted_as_mutant_kill(self):
        with self.subTest(case="assertion"):
            self.assertEqual(1, 2)
        self.skipTest("synthetic skip after assertion")
