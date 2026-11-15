import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_typical_nested(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_close_before_open(self):
        self.assertFalse(balanced("())("))

    def test_no_brackets(self):
        self.assertTrue(balanced("hello world 123"))

    def test_lone_closer(self):
        self.assertFalse(balanced("}"))

    def test_lone_opener(self):
        self.assertFalse(balanced("["))

    def test_interleaved(self):
        self.assertFalse(balanced("([)]"))

    def test_sequential_groups(self):
        self.assertTrue(balanced("()[]{}"))

    def test_deep_nesting(self):
        self.assertTrue(balanced("(" * 500 + ")" * 500))


if __name__ == "__main__":
    unittest.main()
