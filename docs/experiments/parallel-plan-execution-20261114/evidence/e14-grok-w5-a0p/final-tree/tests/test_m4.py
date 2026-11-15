import unittest
from pkg.m4 import balanced


class TestBalanced(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_nested_with_other_chars(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_mismatch(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_wrong_order(self):
        self.assertFalse(balanced("())("))

    def test_only_letters(self):
        self.assertTrue(balanced("hello"))


if __name__ == "__main__":
    unittest.main()
