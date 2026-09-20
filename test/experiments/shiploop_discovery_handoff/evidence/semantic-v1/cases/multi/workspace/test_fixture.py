import unittest
from src.app import CRM_RUNTIME_ALIAS

class Baseline(unittest.TestCase):
    def test_binding_name(self):
        self.assertEqual(CRM_RUNTIME_ALIAS, "crm-review-service")
