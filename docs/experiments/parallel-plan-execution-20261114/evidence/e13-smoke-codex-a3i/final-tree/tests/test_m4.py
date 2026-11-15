import unittest
from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(''))

    def test_ignored_characters(self):
        self.assertTrue(balanced('ordinary text 123'))

    def test_nested(self):
        self.assertTrue(balanced('a(b[c]{d})'))

    def test_adjacent(self):
        self.assertTrue(balanced('()[]{}'))

    def test_mismatched(self):
        self.assertFalse(balanced('(]'))

    def test_unclosed(self):
        self.assertFalse(balanced('(()'))

    def test_extra_closing(self):
        self.assertFalse(balanced('())('))

    def test_crossed(self):
        self.assertFalse(balanced('([)]'))

    def test_initial_closing(self):
        self.assertFalse(balanced(']text'))


if __name__ == '__main__':
    unittest.main()
