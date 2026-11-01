"""Small product-side test used by the inherited `unit` checker during calibration."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class BaseReportTest(unittest.TestCase):
    def test_basic_json_totals(self):
        with tempfile.TemporaryDirectory(prefix="report-unit-") as temporary:
            path = Path(temporary) / "records.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(("date", "region", "product", "units", "unit_price"))
                writer.writerow(("2026-01-01", "North", "widget", "2", "1.25"))
            done = subprocess.run(
                [sys.executable, "report.py", str(path)],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=30,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            data = json.loads(done.stdout)
            self.assertEqual(data["rows"], 1)
            self.assertEqual(data["by_product"], {"widget": 2})


if __name__ == "__main__":
    unittest.main()
