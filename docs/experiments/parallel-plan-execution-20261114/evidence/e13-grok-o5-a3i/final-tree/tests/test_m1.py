import unittest

from pkg.m1 import rle


class TestRle(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_single_character(self):
        self.assertEqual(rle("a"), "a1")

    def test_all_distinct(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_mixed_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_double_digit_run(self):
        self.assertEqual(rle("zzzzzzzzzzzz"), "z12")

    def test_whole_string_one_run(self):
        self.assertEqual(rle("bbbbb"), "b5")

    def test_alternating_pairs(self):
        self.assertEqual(rle("aabbcc"), "a2b2c2")


if __name__ == "__main__":
    unittest.main()
