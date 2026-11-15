import unittest

from pkg.m2 import roman_to_int


class RomanToIntTests(unittest.TestCase):
    def test_minimum(self):
        self.assertEqual(roman_to_int('I'), 1)

    def test_maximum(self):
        self.assertEqual(roman_to_int('MMMCMXCIX'), 3999)

    def test_repeated_symbols(self):
        self.assertEqual(roman_to_int('III'), 3)

    def test_additive_symbols(self):
        self.assertEqual(roman_to_int('LVIII'), 58)

    def test_mixed_subtractions(self):
        self.assertEqual(roman_to_int('MCMXCIV'), 1994)

    def test_each_subtractive_pair(self):
        for numeral, value in [('IV', 4), ('IX', 9), ('XL', 40),
                               ('XC', 90), ('CD', 400), ('CM', 900)]:
            with self.subTest(numeral=numeral):
                self.assertEqual(roman_to_int(numeral), value)

    def test_thousands(self):
        self.assertEqual(roman_to_int('MMM'), 3000)


if __name__ == '__main__':
    unittest.main()
