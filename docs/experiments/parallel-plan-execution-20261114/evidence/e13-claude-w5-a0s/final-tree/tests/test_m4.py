import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_nested_mixed(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatch(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_close_before_open(self):
        self.assertFalse(balanced("())("))

    def test_only_other_chars(self):
        self.assertTrue(balanced("hello world 123"))

    def test_single_closer(self):
        self.assertFalse(balanced("}"))

    def test_single_opener(self):
        self.assertFalse(balanced("["))

    def test_interleaved(self):
        self.assertFalse(balanced("([)]"))

    def test_sequence(self):
        self.assertTrue(balanced("()[]{}"))


if __name__ == "__main__":
    unittest.main()
