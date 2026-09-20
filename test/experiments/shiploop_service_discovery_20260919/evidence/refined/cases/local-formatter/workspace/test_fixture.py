import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from title_formatter import format_title


class ExistingFormatterBehaviorTest(unittest.TestCase):
    def test_whitespace_is_normalized_by_current_formatter(self):
        self.assertEqual(format_title("  client API  "), "Client Api")
