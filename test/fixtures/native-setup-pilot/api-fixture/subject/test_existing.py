"""Basic regression checks for setup and record operations."""
import unittest

import change_app
import setup_app


class ExistingTests(unittest.TestCase):
    def setUp(self):
        setup_app.fixture_seed({"display_name": "Demo", "mode": "safe"})
        change_app.fixture_seed()

    def test_config_can_be_read(self):
        self.assertEqual(setup_app.read_config(), {"display_name": "Demo", "mode": "safe"})

    def test_invalid_setup_preserves_configuration(self):
        before = setup_app.read_config()
        self.assertFalse(setup_app.save_setup("admin", {"display_name": "", "mode": "safe"})["ok"])
        self.assertEqual(setup_app.read_config(), before)

    def test_owner_can_confirm_change(self):
        proposal = change_app.propose_change("alice", "demo-1", 1, {"amount": 25}, "existing-1")
        self.assertTrue(proposal["ok"])
        self.assertTrue(change_app.confirm_change("alice", proposal["proposal_id"])["ok"])
        self.assertEqual(change_app.read_record("alice", "demo-1")["amount"], 25)

    def test_non_owner_cannot_read_record(self):
        self.assertIsNone(change_app.read_record("bob", "demo-1"))


if __name__ == "__main__":
    unittest.main()
