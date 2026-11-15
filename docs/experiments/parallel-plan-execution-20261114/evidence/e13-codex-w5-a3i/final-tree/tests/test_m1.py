import unittest

from pkg.m1 import rle


class RleTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_single_character(self):
        self.assertEqual(rle("q"), "q1")

    def test_mixed_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_distinct_characters(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_multidigit_run(self):
        self.assertEqual(rle("z" * 12), "z12")

    def test_separated_repeated_character(self):
        self.assertEqual(rle("aabaa"), "a2b1a2")

    def test_case_sensitive(self):
        self.assertEqual(rle("aaAAa"), "a2A2a1")


if __name__ == "__main__":
    unittest.main()
