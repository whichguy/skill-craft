import unittest

from pkg.m1 import rle


class TestRle(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_typical_mixed_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_all_singletons(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_double_digit_run(self):
        self.assertEqual(rle("zzzzzzzzzzzz"), "z12")

    def test_single_character(self):
        self.assertEqual(rle("q"), "q1")

    def test_two_same_characters(self):
        self.assertEqual(rle("aa"), "a2")

    def test_alternating_pairs(self):
        self.assertEqual(rle("aabbcc"), "a2b2c2")

    def test_run_then_singleton_then_run(self):
        self.assertEqual(rle("xxxyzz"), "x3y1z2")
