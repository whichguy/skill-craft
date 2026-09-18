from __future__ import annotations

def suite(*names):
    """Mark a unittest method or class for focused and/or smoke selection."""
    def apply(target):
        target.__shiploop_suites__ = frozenset(names)
        return target
    return apply

from contextlib import contextmanager
from pathlib import Path
import tempfile
from unittest.mock import patch
import catalog as catalog_module
from catalog import Catalog

@contextmanager
def isolated_catalog():
    with tempfile.TemporaryDirectory(prefix="catalog-test-") as directory:
        catalog = None
        try:
            catalog = Catalog.open(Path(directory) / "catalog.sqlite")
            yield catalog
        finally:
            if catalog is not None:
                catalog.close()

@contextmanager
def tracked_connections():
    """Observe real acquisitions; defensively close them after the test oracle."""
    connections = []
    connect = catalog_module.sqlite3.connect

    def acquire(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    try:
        with patch.object(catalog_module.sqlite3, "connect", side_effect=acquire):
            yield connections
    finally:
        for connection in connections:
            connection.close()


@contextmanager
def partial_setup():
    """Yield the failed path and real acquisitions before defensive cleanup."""
    with tempfile.TemporaryDirectory(prefix="catalog-partial-") as directory:
        path = Path(directory) / "catalog.sqlite"
        with tracked_connections() as connections:
            try:
                Catalog.open(path, fail_after_open=True)
            except RuntimeError:
                yield path, connections
            else:
                raise AssertionError("partial setup did not fail")
