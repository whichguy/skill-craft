import unittest

from pkg.m1 import rle


class TestRle(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_typical(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_all_singles(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_single_char(self):
        self.assertEqual(rle("x"), "x1")

    def test_long_run_multi_digit(self):
        self.assertEqual(rle("zzzzzzzzzzzz"), "z12")

    def test_run_of_ten_boundary(self):
        self.assertEqual(rle("a" * 9), "a9")
        self.assertEqual(rle("a" * 10), "a10")

    def test_case_sensitive(self):
        self.assertEqual(rle("aAaA"), "a1A1a1A1")

    def test_non_adjacent_repeats_not_merged(self):
        self.assertEqual(rle("aabaa"), "a2b1a2")


if __name__ == "__main__":
    unittest.main()
