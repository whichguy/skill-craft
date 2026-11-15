import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty_string(self):
        self.assertTrue(balanced(""))

    def test_typical_nested_with_other_chars(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatch_types(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed_openers(self):
        self.assertFalse(balanced("(()"))

    def test_closing_then_opening_out_of_order(self):
        self.assertFalse(balanced("())("))

    def test_interleaved_pairs(self):
        self.assertFalse(balanced("([)]"))

    def test_non_bracket_only(self):
        self.assertTrue(balanced("abc 123"))

    def test_deep_proper_nesting(self):
        self.assertTrue(balanced("(((([{}]))))"))

    def test_leading_closer(self):
        self.assertFalse(balanced("]()"))

    def test_sequential_pairs_among_noise(self):
        self.assertTrue(balanced("x()y[]z{}w"))


if __name__ == "__main__":
    unittest.main()
