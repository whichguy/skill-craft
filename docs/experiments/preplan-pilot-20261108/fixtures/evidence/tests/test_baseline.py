import unittest, tempfile, sqlite3
from pathlib import Path
from src import adapter

class Baseline(unittest.TestCase):
    def test_single_row_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = str(Path(tmp) / "db.sqlite")
            self.assertEqual(adapter.apply(p, [{"sku":"old","quantity":2}]), {"accepted":1})
            with sqlite3.connect(p) as db:
                self.assertEqual(db.execute("SELECT * FROM inventory").fetchall(), [("old",2)])

if __name__ == "__main__": unittest.main()
