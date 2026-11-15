import unittest

from pkg.m2 import roman_to_int


class TestRomanToInt(unittest.TestCase):
    def test_simple_additive(self):
        self.assertEqual(roman_to_int("III"), 3)
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_subtractive_pairs(self):
        for s, n in [("IV", 4), ("IX", 9), ("XL", 40), ("XC", 90), ("CD", 400), ("CM", 900)]:
            self.assertEqual(roman_to_int(s), n)

    def test_complex(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)
        self.assertEqual(roman_to_int("MMXXIV"), 2024)

    def test_minimum(self):
        self.assertEqual(roman_to_int("I"), 1)

    def test_maximum(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)

    def test_single_symbols(self):
        for s, n in [("V", 5), ("X", 10), ("L", 50), ("C", 100), ("D", 500), ("M", 1000)]:
            self.assertEqual(roman_to_int(s), n)

    def test_round_trip(self):
        table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                 (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
        for n in range(1, 4000):
            r, m = "", n
            for v, sym in table:
                while m >= v:
                    r += sym
                    m -= v
            self.assertEqual(roman_to_int(r), n)


if __name__ == "__main__":
    unittest.main()
