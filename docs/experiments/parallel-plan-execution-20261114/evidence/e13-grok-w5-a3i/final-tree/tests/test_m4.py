import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty_string(self):
        self.assertTrue(balanced(""))

    def test_nested_with_other_chars(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed_openers(self):
        self.assertFalse(balanced("(()"))

    def test_extra_closer_then_opener(self):
        self.assertFalse(balanced("())("))

    def test_non_bracket_chars_only(self):
        self.assertTrue(balanced("hello world"))

    def test_interleaved_wrong_nesting(self):
        self.assertFalse(balanced("([)]"))

    def test_consecutive_pairs(self):
        self.assertTrue(balanced("()[]{}"))

    def test_deeply_nested(self):
        self.assertTrue(balanced("{[()()]}"))

    def test_leading_closer(self):
        self.assertFalse(balanced("]abc["))


if __name__ == "__main__":
    unittest.main()
