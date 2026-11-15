import unittest
from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_three(self):
        self.assertEqual(roman_to_int("III"), 3)

    def test_fifty_eight(self):
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_mcmxciv(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_one(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_max(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_four(self):
        self.assertEqual(roman_to_int("IV"), 4)


if __name__ == "__main__":
    unittest.main()
