import unittest
from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(''))

    def test_ignores_text(self):
        self.assertTrue(balanced('plain text 123!'))

    def test_nested(self):
        self.assertTrue(balanced('a(b[c]{d})'))

    def test_adjacent_pairs(self):
        self.assertTrue(balanced('()[]{}'))

    def test_mismatch(self):
        self.assertFalse(balanced('(]'))

    def test_unclosed(self):
        self.assertFalse(balanced('(()'))

    def test_extra_close(self):
        self.assertFalse(balanced('())('))

    def test_crossed(self):
        self.assertFalse(balanced('([)]'))

    def test_leading_close(self):
        self.assertFalse(balanced('}abc'))
