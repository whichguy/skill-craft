import unittest
from pkg.m2 import roman_to_int


class RomanTests(unittest.TestCase):
    def test_minimum(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_maximum(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_repeated(self):
        self.assertEqual(roman_to_int("III"), 3)

    def test_additive(self):
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_mixed(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_subtractive_pairs(self):
        for numeral, value in [("IV", 4), ("IX", 9), ("XL", 40), ("XC", 90), ("CD", 400), ("CM", 900)]:
            with self.subTest(numeral=numeral):
                self.assertEqual(roman_to_int(numeral), value)

    def test_all_additive_symbols(self):
        self.assertEqual(roman_to_int("MDCLXVI"), 1666)
