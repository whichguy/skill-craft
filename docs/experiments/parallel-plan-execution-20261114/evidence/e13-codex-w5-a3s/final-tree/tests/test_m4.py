import unittest

from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(''))

    def test_text_only(self):
        self.assertTrue(balanced('hello, world! 123'))

    def test_nested_with_text(self):
        self.assertTrue(balanced('a(b[c]{d})'))

    def test_adjacent_pairs(self):
        self.assertTrue(balanced('()[]{}'))

    def test_wrong_closing_type(self):
        self.assertFalse(balanced('(]'))

    def test_unclosed_opening(self):
        self.assertFalse(balanced('(()'))

    def test_unexpected_closing(self):
        self.assertFalse(balanced('())('))

    def test_crossing_pairs(self):
        self.assertFalse(balanced('([)]'))

    def test_initial_closing(self):
        self.assertFalse(balanced(']'))


if __name__ == '__main__':
    unittest.main()
