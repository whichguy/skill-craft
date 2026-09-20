import unittest
from src.app import normalize_case_id

class Baseline(unittest.TestCase):
    def test_case_id_edges(self):
        self.assertEqual(normalize_case_id("  CASE-17  "), "CASE-17")

if __name__ == "__main__":
    unittest.main(verbosity=2)
