import unittest

from pkg.m1 import rle


class RleTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_single(self):
        self.assertEqual(rle("a"), "a1")

    def test_mixed_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_unique(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_long_run(self):
        self.assertEqual(rle("z" * 12), "z12")

    def test_separated_runs(self):
        self.assertEqual(rle("aabaa"), "a2b1a2")

    def test_case_sensitive(self):
        self.assertEqual(rle("aAAa"), "a1A2a1")
