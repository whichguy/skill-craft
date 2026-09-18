import unittest

from imports import ConflictError, append_summary_edit, transition
from projection import for_reader


def accepted_record():
    return {
        "id": "sample-import-01",
        "state": "accepted",
        "revision": 3,
        "rows": 2,
        "summary": ["header normalized"],
    }


class ImportStateTest(unittest.TestCase):
    def test_edit_increments_the_revision(self):
        updated = append_summary_edit(accepted_record(), 3, "date normalized")
        self.assertEqual(updated["revision"], 4)
        self.assertEqual(updated["summary"][-1], "date normalized")

    def test_stale_edit_is_rejected(self):
        with self.assertRaises(ConflictError):
            append_summary_edit(accepted_record(), 2, "stale edit")

    def test_projection_has_versioned_shapes(self):
        projecting = transition(accepted_record(), "projecting")
        self.assertNotIn("summary", for_reader(projecting, 1))
        self.assertIn("summary", for_reader(projecting, 2))


if __name__ == "__main__":
    unittest.main()
