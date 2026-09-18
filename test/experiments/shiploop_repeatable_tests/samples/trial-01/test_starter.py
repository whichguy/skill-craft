import unittest
from pricing import format_price, price_cents
from test_support import suite

@suite("focused", "smoke")
class PriceFormatStarter(unittest.TestCase):
    def test_common_price_and_format(self):
        self.assertEqual(price_cents(3, 125), 375)
        self.assertEqual(format_price(375), "$3.75")
