import sqlite3
import time
from pathlib import Path

STARTUP_DELAY_SECONDS = 0.15
INITIAL_ITEMS = (("bookmark", 125), ("notebook", 450))

class Catalog:
    @classmethod
    def open(cls, path, *, fail_after_open=False):
        self = cls.__new__(cls)
        self._connection = None
        time.sleep(STARTUP_DELAY_SECONDS)
        try:
            self._connection = sqlite3.connect(str(Path(path)))
            self._connection.execute("CREATE TABLE IF NOT EXISTS items (name TEXT PRIMARY KEY, cents INTEGER NOT NULL)")
            self._connection.executemany("INSERT OR IGNORE INTO items VALUES (?, ?)", INITIAL_ITEMS)
            self._connection.commit()
            if fail_after_open:
                raise RuntimeError("simulated partial setup failure")
            return self
        except Exception:
            self.close()
            raise

    def list_items(self):
        return self._connection.execute("SELECT name, cents FROM items ORDER BY name").fetchall()

    def add(self, name, cents):
        if not isinstance(name, str) or not name.strip() or type(cents) is not int or cents <= 0:
            raise ValueError("item")
        try:
            self._connection.execute("INSERT INTO items VALUES (?, ?)", (name, cents))
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise ValueError("duplicate item") from error

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
