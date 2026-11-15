import unittest

from pkg.m1 import rle


class RleTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_one_character(self):
        self.assertEqual(rle("x"), "x1")

    def test_typical_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_distinct_characters(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_multidigit_count(self):
        self.assertEqual(rle("z" * 12), "z12")

    def test_separated_equal_characters(self):
        self.assertEqual(rle("aabaa"), "a2b1a2")

    def test_case_sensitive(self):
        self.assertEqual(rle("aaAAa"), "a2A2a1")
