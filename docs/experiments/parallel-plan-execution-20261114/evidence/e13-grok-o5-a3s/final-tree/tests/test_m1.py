import unittest

from pkg.m1 import rle


class TestRle(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_single_char(self):
        self.assertEqual(rle("a"), "a1")

    def test_all_unique(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_typical_mixed_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_long_run_two_digit_count(self):
        self.assertEqual(rle("zzzzzzzzzzzz"), "z12")

    def test_all_same(self):
        self.assertEqual(rle("bbbbb"), "b5")

    def test_alternating(self):
        self.assertEqual(rle("ababab"), "a1b1a1b1a1b1")

    def test_run_then_singleton(self):
        self.assertEqual(rle("xxxy"), "x3y1")


if __name__ == "__main__":
    unittest.main()
