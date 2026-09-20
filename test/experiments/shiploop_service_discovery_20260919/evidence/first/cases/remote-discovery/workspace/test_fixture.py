import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from contact_panel import display_contact


class FixtureSmokeTest(unittest.TestCase):
    def test_panel_keeps_existing_display_fields(self):
        self.assertEqual(
            display_contact({"Name": "Example", "ComputedScore__c": 87}),
            {"name": "Example", "score": 87},
        )
