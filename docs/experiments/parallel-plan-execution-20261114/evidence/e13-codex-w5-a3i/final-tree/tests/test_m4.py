import unittest

from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(''))

    def test_ordinary_text(self):
        self.assertTrue(balanced('hello 123!'))

    def test_nested_with_text(self):
        self.assertTrue(balanced('a(b[c]{d})'))

    def test_adjacent_pairs(self):
        self.assertTrue(balanced('()[]{}'))

    def test_mismatched_pair(self):
        self.assertFalse(balanced('(]'))

    def test_unclosed(self):
        self.assertFalse(balanced('(()'))

    def test_extra_closer(self):
        self.assertFalse(balanced('())('))

    def test_crossed_nesting(self):
        self.assertFalse(balanced('([)]'))

    def test_single_closer(self):
        self.assertFalse(balanced('}'))


if __name__ == '__main__':
    unittest.main()
