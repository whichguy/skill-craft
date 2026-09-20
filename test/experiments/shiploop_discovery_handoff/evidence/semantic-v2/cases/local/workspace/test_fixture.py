import unittest
from src.app import normalize_name

class Baseline(unittest.TestCase):
    def test_edges(self):
        self.assertEqual(normalize_name("  Ada  "), "Ada")
