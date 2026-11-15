import unittest

from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_simple_additive(self):
        self.assertEqual(roman_to_int("III"), 3)
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_mixed_subtractive_example(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_min_and_max_bounds(self):
        self.assertEqual(roman_to_int("I"), 1)
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_subtractive_pairs(self):
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("IX"), 9)
        self.assertEqual(roman_to_int("XL"), 40)
        self.assertEqual(roman_to_int("XC"), 90)
        self.assertEqual(roman_to_int("CD"), 400)
        self.assertEqual(roman_to_int("CM"), 900)

    def test_thousands_and_typical_years(self):
        self.assertEqual(roman_to_int("MMXXIV"), 2024)
        self.assertEqual(roman_to_int("MCMLXXXIV"), 1984)
        self.assertEqual(roman_to_int("MM"), 2000)

    def test_all_symbols_once(self):
        self.assertEqual(roman_to_int("MDCLXVI"), 1666)

    def test_repeated_same_symbol(self):
        self.assertEqual(roman_to_int("XXX"), 30)
        self.assertEqual(roman_to_int("CCC"), 300)
        self.assertEqual(roman_to_int("MMM"), 3000)


if __name__ == "__main__":
    unittest.main()
