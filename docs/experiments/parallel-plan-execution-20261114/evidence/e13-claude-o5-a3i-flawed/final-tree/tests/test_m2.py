import unittest

from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_simple_additive(self):
        self.assertEqual(roman_to_int("III"), 3)

    def test_mixed(self):
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_complex_subtractive(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_minimum(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_maximum(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_each_subtractive_pair(self):
        cases = {"IV": 4, "IX": 9, "XL": 40, "XC": 90, "CD": 400, "CM": 900}
        for s, n in cases.items():
            with self.subTest(s=s):
                self.assertEqual(roman_to_int(s), n)

    def test_single_symbols(self):
        cases = {"V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        for s, n in cases.items():
            with self.subTest(s=s):
                self.assertEqual(roman_to_int(s), n)


if __name__ == "__main__":
    unittest.main()
