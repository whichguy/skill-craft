import unittest

from pkg.m1 import rle


class TestRle(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_typical(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_no_repeats(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_multi_digit_run(self):
        self.assertEqual(rle("z" * 12), "z12")

    def test_single_char(self):
        self.assertEqual(rle("q"), "q1")

    def test_case_sensitive(self):
        self.assertEqual(rle("aAaa"), "a1A1a2")

    def test_non_adjacent_same_char(self):
        self.assertEqual(rle("abab"), "a1b1a1b1")

    def test_long_run(self):
        self.assertEqual(rle("x" * 100), "x100")


if __name__ == "__main__":
    unittest.main()
