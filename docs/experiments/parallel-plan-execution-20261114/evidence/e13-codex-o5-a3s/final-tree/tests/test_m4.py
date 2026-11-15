import unittest
from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_ignored_characters(self):
        self.assertTrue(balanced("hello world 123!"))

    def test_nested(self):
        self.assertTrue(balanced("a(b[c]{d})"))

    def test_sequential_pairs(self):
        self.assertTrue(balanced("()[]{}"))

    def test_mismatched(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_early_closing(self):
        self.assertFalse(balanced("())("))

    def test_crossed_pairs(self):
        self.assertFalse(balanced("([)]"))

    def test_lone_closing(self):
        self.assertFalse(balanced("}"))
