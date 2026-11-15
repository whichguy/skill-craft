import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_nested_with_other_chars(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_pair(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_wrong_order(self):
        self.assertFalse(balanced("())("))

    def test_no_brackets(self):
        self.assertTrue(balanced("hello world"))

    def test_only_closing(self):
        self.assertFalse(balanced(")"))


if __name__ == "__main__":
    unittest.main()
