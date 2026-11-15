import unittest
from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertIs(balanced(""), True)

    def test_ignored_text(self):
        self.assertIs(balanced("abc 123 !"), True)

    def test_nested_text(self):
        self.assertIs(balanced("a(b[c]{d})"), True)

    def test_sequential_pairs(self):
        self.assertIs(balanced("()[]{}"), True)

    def test_wrong_closer(self):
        self.assertIs(balanced("(]"), False)

    def test_unclosed(self):
        self.assertIs(balanced("(()"), False)

    def test_extra_closer(self):
        self.assertIs(balanced("())("), False)

    def test_crossed(self):
        self.assertIs(balanced("([)]"), False)

    def test_single_brackets(self):
        for char in "()[]{}":
            with self.subTest(char=char):
                self.assertIs(balanced(char), False)
