import unittest

from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_three(self):
        self.assertEqual(roman_to_int("III"), 3)

    def test_fifty_eight(self):
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_mcmxciv(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_min_one(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_max_3999(self):
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

    def test_forty_nine(self):
        self.assertEqual(roman_to_int("XLIX"), 49)

    def test_four_hundred_forty_four(self):
        self.assertEqual(roman_to_int("CDXLIV"), 444)

    def test_two_thousand_twenty_four(self):
        self.assertEqual(roman_to_int("MMXXIV"), 2024)
