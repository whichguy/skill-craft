import unittest

from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_typical_nested(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_closer_before_opener(self):
        self.assertFalse(balanced("())("))

    def test_no_brackets(self):
        self.assertTrue(balanced("hello, world <>"))

    def test_lone_closer(self):
        self.assertFalse(balanced("}"))

    def test_improper_interleave(self):
        self.assertFalse(balanced("([)]"))

    def test_sequential_groups(self):
        self.assertTrue(balanced("()[]{}"))


if __name__ == "__main__":
    unittest.main()
