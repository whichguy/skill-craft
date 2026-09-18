from __future__ import annotations

def suite(*names):
    """Mark a unittest method or class for focused and/or smoke selection."""
    def apply(target):
        target.__shiploop_suites__ = frozenset(names)
        return target
    return apply

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch
from catalog import Catalog

@contextmanager
def catalog_path():
    with tempfile.TemporaryDirectory(prefix="catalog-test-") as directory:
        yield Path(directory) / "catalog.sqlite"

@contextmanager
def tracked_connections():
    """Observe real acquisitions; close them after assertions even on failure."""
    connections = []
    real_connect = sqlite3.connect

    def connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        connections.append(connection)
        return connection

    with patch("catalog.sqlite3.connect", side_effect=connect):
        try:
            yield connections
        finally:
            for connection in connections:
                connection.close()

@contextmanager
def isolated_catalog():
    with catalog_path() as path, tracked_connections():
        catalog = None
        try:
            catalog = Catalog.open(path)
            yield catalog
        finally:
            if catalog is not None:
                catalog.close()

@contextmanager
def partial_setup():
    """Yield acquired connections after the expected setup error, before cleanup."""
    with catalog_path() as path, tracked_connections() as connections:
        try:
            Catalog.open(path, fail_after_open=True)
        except RuntimeError:
            yield connections
        else:
            raise AssertionError("partial setup did not fail")
