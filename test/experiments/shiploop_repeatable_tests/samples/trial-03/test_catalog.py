"""Observable SPEC.md contracts; expected values are independent of catalog.py."""

import sqlite3
import unittest
from unittest.mock import patch

import catalog as catalog_module
from catalog import Catalog
from test_support import isolated_catalog, partial_setup, suite, tracked_connections


@suite("focused")
class CatalogWrites(unittest.TestCase):
    @suite("focused", "smoke")
    def test_tc02_add_lists_exact_values_in_name_order(self):
        with isolated_catalog() as catalog:
            catalog.add("zebra", 1)
            catalog.add("apricot", 2_147_483_648)
            catalog.add("middle", 275)
            self.assertEqual(catalog.list_items(), [
                ("apricot", 2_147_483_648),
                ("bookmark", 125),
                ("middle", 275),
                ("notebook", 450),
                ("zebra", 1),
            ])

    def test_tc03_invalid_names_leave_catalog_usable(self):
        for name in ("", " ", "\t\n", None, 0, True, b"item", ["item"]):
            with self.subTest(name=name), isolated_catalog() as catalog:
                with self.assertRaises(ValueError):
                    catalog.add(name, 50)
                self.assertEqual(catalog.list_items(), [
                    ("bookmark", 125), ("notebook", 450),
                ])
                catalog.add("recovery", 1)
                self.assertEqual(catalog.list_items(), [
                    ("bookmark", 125), ("notebook", 450), ("recovery", 1),
                ])

    def test_tc04_invalid_cents_leave_catalog_usable(self):
        for cents in (0, -1, -100, True, False, 1.0, "1", None, [1]):
            with self.subTest(cents=cents), isolated_catalog() as catalog:
                with self.assertRaises(ValueError):
                    catalog.add("new", cents)
                self.assertEqual(catalog.list_items(), [
                    ("bookmark", 125), ("notebook", 450),
                ])
                catalog.add("new", 1)
                self.assertEqual(catalog.list_items(), [
                    ("bookmark", 125), ("new", 1), ("notebook", 450),
                ])

    def test_tc05_duplicates_preserve_values_and_allow_recovery(self):
        for name, original in (("bookmark", 125), ("added", 75)):
            with self.subTest(name=name), isolated_catalog() as catalog:
                expected = [("bookmark", 125), ("notebook", 450)]
                if name == "added":
                    catalog.add(name, original)
                    expected.insert(0, (name, original))
                with self.assertRaises(ValueError):
                    catalog.add(name, 999)
                self.assertEqual(catalog.list_items(), expected)
                catalog.add("recovery", 1)
                self.assertEqual(catalog.list_items(), expected + [("recovery", 1)])

    def test_tc13_positive_integers_at_sqlite_storage_boundary(self):
        # SPEC.md accepts positive int values without stating a storage maximum.
        for cents in (2**63 - 1, 2**63):
            with self.subTest(cents=cents), isolated_catalog() as catalog:
                catalog.add("large", cents)
                self.assertEqual(catalog.list_items(), [
                    ("bookmark", 125), ("large", cents), ("notebook", 450),
                ])


class CatalogResources(unittest.TestCase):
    def test_tc06_startup_delay_precedes_acquisition(self):
        connect = sqlite3.connect

        with patch.object(catalog_module.time, "sleep") as sleep:
            def acquire(*args, **kwargs):
                sleep.assert_called_once_with(0.15)
                return connect(*args, **kwargs)

            with patch.object(catalog_module.sqlite3, "connect", side_effect=acquire) as opened:
                with isolated_catalog() as catalog:
                    self.assertEqual(catalog.list_items(), [
                        ("bookmark", 125), ("notebook", 450),
                    ])
                opened.assert_called_once()
            sleep.assert_called_once_with(0.15)

    def test_tc07_close_releases_connection_and_is_repeatable(self):
        with tracked_connections() as connections, isolated_catalog() as catalog:
            self.assertEqual(len(connections), 1)
            catalog.close()
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")
            catalog.close()
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")

    @suite("smoke")
    def test_tc08_partial_setup_closes_connection_and_recovers(self):
        with partial_setup() as (path, connections):
            self.assertEqual(len(connections), 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")
            recovered = Catalog.open(path)
            try:
                self.assertEqual(recovered.list_items(), [
                    ("bookmark", 125), ("notebook", 450),
                ])
            finally:
                recovered.close()


if __name__ == "__main__":
    unittest.main()
