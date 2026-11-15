import unittest

from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_typical_examples(self):
        self.assertEqual(roman_to_int("III"), 3)
        self.assertEqual(roman_to_int("LVIII"), 58)
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_minimum_boundary(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_maximum_boundary(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_subtractive_pairs(self):
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("IX"), 9)
        self.assertEqual(roman_to_int("XL"), 40)
        self.assertEqual(roman_to_int("XC"), 90)
        self.assertEqual(roman_to_int("CD"), 400)
        self.assertEqual(roman_to_int("CM"), 900)

    def test_additive_repeats_and_mixed(self):
        self.assertEqual(roman_to_int("XXVII"), 27)
        self.assertEqual(roman_to_int("XLII"), 42)
        self.assertEqual(roman_to_int("CDXLIV"), 444)
        self.assertEqual(roman_to_int("MM"), 2000)
        self.assertEqual(roman_to_int("MCMLXXXIV"), 1984)


if __name__ == "__main__":
    unittest.main()
