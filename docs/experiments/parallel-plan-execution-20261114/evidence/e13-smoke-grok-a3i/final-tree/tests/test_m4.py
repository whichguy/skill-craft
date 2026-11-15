import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty_string_is_balanced(self):
        self.assertTrue(balanced(""))

    def test_nested_mixed_with_ignored_chars(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed_openers(self):
        self.assertFalse(balanced("(()"))

    def test_wrong_order_extra_close(self):
        self.assertFalse(balanced("())("))

    def test_only_non_brackets_is_balanced(self):
        self.assertTrue(balanced("hello world 123"))

    def test_consecutive_pairs(self):
        self.assertTrue(balanced("()[]{}"))

    def test_interleaved_not_nested(self):
        self.assertFalse(balanced("([)]"))

    def test_deep_nesting(self):
        self.assertTrue(balanced("{[()()][]}"))

    def test_lone_closer(self):
        self.assertFalse(balanced("}"))


if __name__ == "__main__":
    unittest.main()
