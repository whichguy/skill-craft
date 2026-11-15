import unittest

from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_simple_additions(self):
        self.assertEqual(roman_to_int("III"), 3)
        self.assertEqual(roman_to_int("XII"), 12)
        self.assertEqual(roman_to_int("XXVII"), 27)

    def test_typical_examples(self):
        self.assertEqual(roman_to_int("LVIII"), 58)
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_minimum_and_maximum(self):
        self.assertEqual(roman_to_int("I"), 1)
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_subtractive_pairs(self):
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("IX"), 9)
        self.assertEqual(roman_to_int("XL"), 40)
        self.assertEqual(roman_to_int("XC"), 90)
        self.assertEqual(roman_to_int("CD"), 400)
        self.assertEqual(roman_to_int("CM"), 900)

    def test_single_symbols(self):
        self.assertEqual(roman_to_int("V"), 5)
        self.assertEqual(roman_to_int("X"), 10)
        self.assertEqual(roman_to_int("L"), 50)
        self.assertEqual(roman_to_int("C"), 100)
        self.assertEqual(roman_to_int("D"), 500)
        self.assertEqual(roman_to_int("M"), 1000)

    def test_compound_subtractive(self):
        self.assertEqual(roman_to_int("XLIX"), 49)
        self.assertEqual(roman_to_int("XCIX"), 99)
        self.assertEqual(roman_to_int("CDXLIV"), 444)
        self.assertEqual(roman_to_int("CMXCIX"), 999)

    def test_thousands(self):
        self.assertEqual(roman_to_int("MMXXIV"), 2024)
        self.assertEqual(roman_to_int("MMM"), 3000)
        self.assertEqual(roman_to_int("MCMLXXXIV"), 1984)


if __name__ == "__main__":
    unittest.main()
