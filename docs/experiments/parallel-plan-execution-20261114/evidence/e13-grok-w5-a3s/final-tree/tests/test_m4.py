import unittest

from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty_string(self):
        self.assertTrue(balanced(""))

    def test_nested_mixed_with_noise(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatched_pair(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed_open(self):
        self.assertFalse(balanced("(()"))

    def test_close_then_open_wrong_order(self):
        self.assertFalse(balanced("())("))

    def test_no_brackets_is_balanced(self):
        self.assertTrue(balanced("hello world"))

    def test_interleaved_wrong_nesting(self):
        self.assertFalse(balanced("([)]"))

    def test_only_closing(self):
        self.assertFalse(balanced(")))]}"))

    def test_deep_nesting(self):
        self.assertTrue(balanced("{[({[]})]}"))

    def test_adjacent_pairs(self):
        self.assertTrue(balanced("()[]{}"))


if __name__ == "__main__":
    unittest.main()
