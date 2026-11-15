import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty_string(self):
        self.assertTrue(balanced(""))

    def test_nested_with_other_characters(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed_openers(self):
        self.assertFalse(balanced("(()"))

    def test_wrong_order_and_extra_close(self):
        self.assertFalse(balanced("())("))

    def test_only_non_brackets(self):
        self.assertTrue(balanced("hello world 123"))

    def test_interleaved_wrong_nesting(self):
        self.assertFalse(balanced("([)]"))

    def test_single_closer(self):
        self.assertFalse(balanced("}"))

    def test_deep_same_type_nesting(self):
        self.assertTrue(balanced("(((([]))))"))

    def test_all_three_pairs_adjacent(self):
        self.assertTrue(balanced("()[]{}"))


if __name__ == "__main__":
    unittest.main()
