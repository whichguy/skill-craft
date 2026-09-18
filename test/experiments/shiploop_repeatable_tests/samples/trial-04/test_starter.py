import unittest
from test_support import isolated_catalog, suite

@suite("focused", "smoke")
class CatalogStarter(unittest.TestCase):
    def test_seeded_items_are_sorted(self):
        with isolated_catalog() as catalog:
            self.assertEqual(catalog.list_items(), [("bookmark", 125), ("notebook", 450)])
