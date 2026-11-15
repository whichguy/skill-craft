import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_nested_with_other_chars(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_wrong_order(self):
        self.assertFalse(balanced("())("))

    def test_only_closer(self):
        self.assertFalse(balanced(")"))

    def test_no_brackets(self):
        self.assertTrue(balanced("hello world 123"))

    def test_sequential_groups(self):
        self.assertTrue(balanced("()[]{}"))

    def test_interleaved(self):
        self.assertFalse(balanced("([)]"))


if __name__ == "__main__":
    unittest.main()
