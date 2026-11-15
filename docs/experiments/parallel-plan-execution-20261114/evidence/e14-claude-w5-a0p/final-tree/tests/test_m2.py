import unittest
from pkg.m2 import roman_to_int


class TestRoman(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(roman_to_int("III"), 3)

    def test_mixed(self):
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_subtractive(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_min(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_max(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_four_nine(self):
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("IX"), 9)

    def test_forty_ninety_cd_cm(self):
        self.assertEqual(roman_to_int("XL"), 40)
        self.assertEqual(roman_to_int("XC"), 90)
        self.assertEqual(roman_to_int("CD"), 400)
        self.assertEqual(roman_to_int("CM"), 900)


if __name__ == "__main__":
    unittest.main()
