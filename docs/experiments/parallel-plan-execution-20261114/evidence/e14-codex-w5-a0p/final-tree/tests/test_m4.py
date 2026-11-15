import unittest

from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertIs(balanced(""), True)

    def test_ignored_characters(self):
        self.assertIs(balanced("hello 123!\n"), True)

    def test_nested_with_text(self):
        self.assertIs(balanced("a(b[c]{d})"), True)

    def test_sequential_pairs(self):
        self.assertIs(balanced("()[]{}"), True)

    def test_wrong_type(self):
        self.assertIs(balanced("(]"), False)

    def test_unclosed(self):
        self.assertIs(balanced("(()"), False)

    def test_extra_closer(self):
        self.assertIs(balanced("())("), False)

    def test_crossed_nesting(self):
        self.assertIs(balanced("([)]"), False)

    def test_lone_closer(self):
        self.assertIs(balanced("}"), False)
