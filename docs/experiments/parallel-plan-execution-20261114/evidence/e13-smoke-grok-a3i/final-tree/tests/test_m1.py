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
        self.assertEqual(rle("x"), "x1")

    def test_two_runs(self):
        self.assertEqual(rle("aabb"), "a2b2")

    def test_alternating(self):
        self.assertEqual(rle("abab"), "a1b1a1b1")


if __name__ == "__main__":
    unittest.main()
