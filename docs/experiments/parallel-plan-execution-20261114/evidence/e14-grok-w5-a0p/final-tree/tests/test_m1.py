import unittest
from pkg.m1 import rle


class TestRle(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_typical_mixed_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_all_singletons(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_long_single_run(self):
        self.assertEqual(rle("zzzzzzzzzzzz"), "z12")

    def test_single_char(self):
        self.assertEqual(rle("q"), "q1")

    def test_two_runs(self):
        self.assertEqual(rle("aabb"), "a2b2")


if __name__ == "__main__":
    unittest.main()
