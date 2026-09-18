from contextlib import ExitStack
import sqlite3
import unittest
from unittest.mock import patch

from catalog import Catalog
from test_support import (
    catalog_path, isolated_catalog, partial_setup, suite, tracked_connections,
)


@suite("focused")
class CatalogContract(unittest.TestCase):
    def test_file_is_created_and_reopens(self):
        """TC-01: a file-backed catalog retains seeds and added rows."""
        with catalog_path() as path, tracked_connections():
            self.assertFalse(path.exists())
            catalog = Catalog.open(path)
            try:
                self.assertTrue(path.is_file())
                catalog.add("pencil", 1)
            finally:
                catalog.close()
            reopened = Catalog.open(path)
            try:
                self.assertEqual(reopened.list_items(), [
                    ("bookmark", 125), ("notebook", 450), ("pencil", 1),
                ])
            finally:
                reopened.close()

    def test_startup_delay_precedes_connection(self):
        """TC-02: test the simulated cost without scheduler-dependent bounds."""
        events = []
        real_connect = sqlite3.connect

        def connect(*args, **kwargs):
            events.append("connect")
            connection = real_connect(*args, **kwargs)
            cleanup.callback(connection.close)
            return connection

        with catalog_path() as path, ExitStack() as cleanup, patch(
            "catalog.time.sleep", side_effect=lambda seconds: events.append(("sleep", seconds))
        ) as sleep, patch("catalog.sqlite3.connect", side_effect=connect):
            catalog = Catalog.open(path)
            try:
                sleep.assert_called_once_with(0.15)
                self.assertEqual(events, [("sleep", 0.15), "connect"])
            finally:
                catalog.close()

    @suite("focused", "smoke")
    def test_add_and_list_sorted(self):
        """TC-03: unsorted insertions must not leak insertion order."""
        with isolated_catalog() as catalog:
            for name, cents in [("zebra", 999), ("mug", 250), ("apple", 1)]:
                catalog.add(name, cents)
            self.assertEqual(catalog.list_items(), [
                ("apple", 1), ("bookmark", 125), ("mug", 250),
                ("notebook", 450), ("zebra", 999),
            ])

    def test_valid_names_and_prices(self):
        """TC-04: nonblank names are data, including quotes and Unicode."""
        rows = [("x", 1), (" padded ", 2), ("café", 100_000), ("reader's guide", 50)]
        with isolated_catalog() as catalog:
            for name, cents in rows:
                with self.subTest(name=name, cents=cents):
                    catalog.add(name, cents)
            self.assertEqual(catalog.list_items(), [
                (" padded ", 2), ("bookmark", 125), ("café", 100_000),
                ("notebook", 450), ("reader's guide", 50), ("x", 1),
            ])

    def test_invalid_names_preserve_state(self):
        """TC-05: rejection must be ValueError and have no row side effects."""
        with isolated_catalog() as catalog:
            catalog.add("existing", 7)
            for index, name in enumerate(["", " ", "\t\n", None, 42, True, b"name", [], {}]):
                with self.subTest(name=name):
                    before = catalog.list_items()
                    with self.assertRaises(ValueError):
                        catalog.add(name, 1)
                    self.assertEqual(catalog.list_items(), before)
                    recovery = (f"recovery-{index}", 3)
                    catalog.add(*recovery)
                    self.assertEqual(catalog.list_items(), sorted(before + [recovery]))

    def test_invalid_prices_preserve_state(self):
        """TC-05: bool is excluded even though Python treats it as an int."""
        with isolated_catalog() as catalog:
            catalog.add("existing", 7)
            invalid = [0, -1, -100, True, False, 1.0, 1.5, "5", None, b"5", [], {}]
            for index, cents in enumerate(invalid):
                with self.subTest(cents=cents):
                    before = catalog.list_items()
                    name = f"candidate-{index}"
                    with self.assertRaises(ValueError):
                        catalog.add(name, cents)
                    self.assertEqual(catalog.list_items(), before)
                    catalog.add(name, 3)
                    self.assertEqual(catalog.list_items(), sorted(before + [(name, 3)]))

    @suite("focused", "smoke")
    def test_duplicates_preserve_state_and_allow_recovery(self):
        """TC-06: a duplicate must neither overwrite nor poison later adds."""
        for name, old_cents in [("bookmark", 125), ("custom", 23)]:
            with self.subTest(name=name), isolated_catalog() as catalog:
                if name == "custom":
                    catalog.add(name, old_cents)
                before = catalog.list_items()
                with self.assertRaises(ValueError):
                    catalog.add(name, 999)
                self.assertEqual(catalog.list_items(), before)
                catalog.add("recovery", 2)
                self.assertEqual(catalog.list_items(), sorted(before + [("recovery", 2)]))

    @suite("focused", "smoke")
    def test_close_is_idempotent_and_releases_connection(self):
        """TC-07: observe release before the fixture's fallback cleanup."""
        with catalog_path() as path, tracked_connections() as connections:
            catalog = Catalog.open(path)
            self.assertEqual(len(connections), 1)
            catalog.close()
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")
            catalog.close()

    def test_catalogs_are_isolated(self):
        """TC-07: adding/closing one catalog must not affect another."""
        with isolated_catalog() as first, isolated_catalog() as second:
            first.add("only-first", 8)
            self.assertEqual(second.list_items(), [("bookmark", 125), ("notebook", 450)])
            first.close()
            second.add("only-second", 9)
            self.assertEqual(second.list_items(), [
                ("bookmark", 125), ("notebook", 450), ("only-second", 9),
            ])

    @suite("focused", "smoke")
    def test_partial_setup_closes_connection_and_allows_recovery(self):
        """TC-08: inspect the acquired handle while helper cleanup is pending."""
        with partial_setup() as connections:
            self.assertEqual(len(connections), 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")
        with isolated_catalog() as catalog:
            catalog.add("recovered", 1)
            self.assertEqual(catalog.list_items(), [
                ("bookmark", 125), ("notebook", 450), ("recovered", 1),
            ])


if __name__ == "__main__":
    unittest.main()
