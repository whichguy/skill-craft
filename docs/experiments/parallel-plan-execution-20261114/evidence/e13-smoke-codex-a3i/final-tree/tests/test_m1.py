import unittest
from pkg.m1 import rle


class RleTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_single_character(self):
        self.assertEqual(rle("a"), "a1")

    def test_typical_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_all_distinct(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_multidigit_run(self):
        self.assertEqual(rle("z" * 12), "z12")

    def test_separated_repetitions(self):
        self.assertEqual(rle("aabaaa"), "a2b1a3")

    def test_case_sensitive(self):
        self.assertEqual(rle("aaAAAa"), "a2A3a1")
