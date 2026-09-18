"""Contract examples derived from SPEC.md; case IDs are stable selectors."""
from decimal import Decimal
from fractions import Fraction
import unittest

from pricing import format_price, price_cents
from test_support import suite


def invalid_numbers():
    """Fresh representatives of negative integers and non-integer types."""
    return (
        -1, -10**30, 0.0, 1.5, float("nan"), float("inf"),
        "", "125", b"125", None, [], {}, (), complex(1, 0),
        Decimal("125"), Fraction(125, 1), object(),
    )


class PriceCentsContract(unittest.TestCase):
    @suite("focused", "smoke")
    def test_tc01_nonnegative_products(self):
        for quantity, unit_cents, expected in (
            (0, 0, 0), (0, 125, 0), (3, 0, 0), (1, 1, 1),
            (1, 125, 125), (3, 125, 375), (125, 3, 375), (12, 99, 1188),
        ):
            with self.subTest(quantity=quantity, unit_cents=unit_cents):
                actual = price_cents(quantity, unit_cents)
                self.assertIs(type(actual), int)
                self.assertEqual(actual, expected)

    def test_tc02_large_products_are_exact(self):
        for quantity, unit_cents, expected in (
            (9007199254740993, 3, 27021597764222979),
            (3, 9007199254740993, 27021597764222979),
            (10**40, 10**40, 10**80),
        ):
            with self.subTest(quantity=quantity, unit_cents=unit_cents):
                actual = price_cents(quantity, unit_cents)
                self.assertIs(type(actual), int)
                self.assertEqual(actual, expected)

    @suite("focused")
    def test_tc03_invalid_quantity_raises_value_error(self):
        for quantity in invalid_numbers():
            for unit_cents in (0, 125):
                with self.subTest(quantity=quantity, unit_cents=unit_cents):
                    with self.assertRaises(ValueError):
                        price_cents(quantity, unit_cents)

    @suite("focused")
    def test_tc04_invalid_unit_raises_value_error(self):
        for unit_cents in invalid_numbers():
            for quantity in (0, 3):
                with self.subTest(quantity=quantity, unit_cents=unit_cents):
                    with self.assertRaises(ValueError):
                        price_cents(quantity, unit_cents)

    @suite("focused", "smoke")
    def test_tc05_boolean_operands_raise_value_error(self):
        for value in (False, True):
            for other in (0, 3):
                for quantity, unit_cents in ((value, other), (other, value)):
                    with self.subTest(quantity=quantity, unit_cents=unit_cents):
                        with self.assertRaises(ValueError):
                            price_cents(quantity, unit_cents)

    def test_tc06_price_calls_are_stateless_after_errors(self):
        self.assertEqual(price_cents(3, 125), 375)
        with self.assertRaises(ValueError):
            price_cents(-1, 125)
        self.assertEqual(price_cents(2, 99), 198)
        with self.assertRaises(ValueError):
            price_cents(3, True)
        self.assertEqual(format_price(1), "$0.01")
        self.assertEqual(price_cents(0, 125), 0)
        self.assertEqual(price_cents(3, 125), 375)


class FormatPriceContract(unittest.TestCase):
    @suite("focused", "smoke")
    def test_tc07_dollars_have_exactly_two_decimal_digits(self):
        for cents, expected in (
            (0, "$0.00"), (1, "$0.01"), (9, "$0.09"), (10, "$0.10"),
            (99, "$0.99"), (100, "$1.00"), (101, "$1.01"),
            (109, "$1.09"), (110, "$1.10"), (199, "$1.99"),
            (200, "$2.00"), (999, "$9.99"), (1000, "$10.00"),
            (1001, "$10.01"), (123456, "$1234.56"),
        ):
            with self.subTest(cents=cents):
                actual = format_price(cents)
                self.assertIsInstance(actual, str)
                self.assertEqual(actual, expected)

    def test_tc08_large_cents_are_formatted_exactly(self):
        for cents, expected in (
            (9007199254740993, "$90071992547409.93"),
            (12345678901234567890123456789012345,
             "$123456789012345678901234567890123.45"),
        ):
            with self.subTest(cents=cents):
                self.assertEqual(format_price(cents), expected)

    @suite("focused")
    def test_tc09_invalid_cents_raise_value_error(self):
        for cents in invalid_numbers():
            with self.subTest(cents=cents):
                with self.assertRaises(ValueError):
                    format_price(cents)

    @suite("focused", "smoke")
    def test_tc10_boolean_cents_raise_value_error(self):
        for cents in (False, True):
            with self.subTest(cents=cents):
                with self.assertRaises(ValueError):
                    format_price(cents)

    def test_tc11_format_calls_are_stateless_after_errors(self):
        self.assertEqual(format_price(375), "$3.75")
        with self.assertRaises(ValueError):
            format_price(-1)
        self.assertEqual(format_price(1), "$0.01")
        with self.assertRaises(ValueError):
            format_price(False)
        self.assertEqual(price_cents(2, 99), 198)
        self.assertEqual(format_price(0), "$0.00")
        self.assertEqual(format_price(375), "$3.75")
