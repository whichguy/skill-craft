"""Price/format acceptance cases from SPEC.md; expected values are independent."""

from decimal import Decimal
from fractions import Fraction
import unittest

from pricing import format_price, price_cents
from test_support import suite


def invalid_inputs():
    """Fresh invalid values: no numeric coercion, bool acceptance, or shared state."""
    return (
        -1, -100, -(10**80), True, False, None,
        0.0, 1.0, -1.5, float("nan"), float("inf"), float("-inf"),
        "", "0", "125", b"125", [], {}, (), object(),
        Decimal("1"), Fraction(1, 1), 1 + 0j,
    )


@suite("focused")
class PriceCentsContract(unittest.TestCase):
    @suite("focused", "smoke")
    def test_products(self):
        """PF-01: zeros, identity, ordinary products and exact large integers."""
        cases = (
            (0, 0, 0), (0, 125, 0), (3, 0, 0),
            (1, 125, 125), (125, 1, 125), (7, 19, 133),
            (19, 7, 133), (12, 99, 1188),
            (9007199254740993, 3, 27021597764222979),
            (3, 9007199254740993, 27021597764222979),
            (100000000000000000000, 100000000000000000000,
             10000000000000000000000000000000000000000),
        )
        for quantity, unit_cents, expected in cases:
            with self.subTest(quantity=quantity, unit_cents=unit_cents):
                actual = price_cents(quantity, unit_cents)
                self.assertIs(type(actual), int)
                self.assertEqual(actual, expected)

    def test_invalid_quantity(self):
        """PF-02: validation applies even when a zero price would mask input."""
        for quantity in invalid_inputs():
            for unit_cents in (0, 125):
                with self.subTest(quantity=quantity, unit_cents=unit_cents):
                    with self.assertRaises(ValueError):
                        price_cents(quantity, unit_cents)

    def test_invalid_unit_cents(self):
        """PF-02: independently validate the second argument, also at zero."""
        for unit_cents in invalid_inputs():
            for quantity in (0, 3):
                with self.subTest(quantity=quantity, unit_cents=unit_cents):
                    with self.assertRaises(ValueError):
                        price_cents(quantity, unit_cents)


@suite("focused")
class FormatPriceContract(unittest.TestCase):
    @suite("focused", "smoke")
    def test_decimal_boundaries(self):
        """PF-03: exact strings capture dollars, padding and cent rollover."""
        cases = (
            (0, "$0.00"), (1, "$0.01"), (9, "$0.09"),
            (10, "$0.10"), (11, "$0.11"), (99, "$0.99"),
            (100, "$1.00"), (101, "$1.01"), (109, "$1.09"),
            (110, "$1.10"), (199, "$1.99"), (200, "$2.00"),
            (9999, "$99.99"), (10000, "$100.00"), (10001, "$100.01"),
        )
        for cents, expected in cases:
            with self.subTest(cents=cents):
                self.assertEqual(format_price(cents), expected)

    def test_large_amounts(self):
        """PF-03: no floating point precision loss or scientific notation."""
        cases = (
            (9007199254740993, "$90071992547409.93"),
            (100000000000000000000, "$1000000000000000000.00"),
            (100000000000000000001, "$1000000000000000000.01"),
            (100000000000000000099, "$1000000000000000000.99"),
        )
        for cents, expected in cases:
            with self.subTest(cents=cents):
                self.assertEqual(format_price(cents), expected)

    def test_invalid_cents(self):
        """PF-04: malformed inputs raise the specified exception type."""
        for cents in invalid_inputs():
            with self.subTest(cents=cents):
                with self.assertRaises(ValueError):
                    format_price(cents)


@suite("focused")
class StatelessContract(unittest.TestCase):
    def test_interleaved_calls(self):
        """PF-05: different calls cannot change later results."""
        for _ in range(2):
            self.assertEqual(price_cents(7, 19), 133)
            self.assertEqual(format_price(101), "$1.01")
            self.assertEqual(price_cents(0, 999), 0)
            self.assertEqual(format_price(0), "$0.00")
            self.assertEqual(price_cents(2, 99), 198)
            self.assertEqual(format_price(133), "$1.33")

    @suite("focused", "smoke")
    def test_recovery_after_rejection(self):
        """PF-05: neither validation failures nor successes poison later calls."""
        for bad in (-1, True, "125"):
            with self.subTest(bad=bad):
                self.assertEqual(price_cents(2, 125), 250)
                self.assertEqual(format_price(250), "$2.50")
                with self.assertRaises(ValueError):
                    price_cents(bad, 125)
                self.assertEqual(price_cents(2, 125), 250)
                with self.assertRaises(ValueError):
                    price_cents(2, bad)
                self.assertEqual(price_cents(2, 125), 250)
                with self.assertRaises(ValueError):
                    format_price(bad)
                self.assertEqual(format_price(250), "$2.50")
                self.assertEqual(price_cents(2, 125), 250)


if __name__ == "__main__":
    unittest.main()
