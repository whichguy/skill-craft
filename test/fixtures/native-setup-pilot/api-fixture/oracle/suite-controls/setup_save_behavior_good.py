"""Known-good Save controls: execute Save and observe persistence and denial."""
import unittest

import setup_app


class SetupSaveBehavior(unittest.TestCase):
    def setUp(self):
        setup_app.fixture_seed({"display_name": "Original", "mode": "review"})

    def test_admin_save_persists_exact_configuration(self):
        result = setup_app.save_setup(
            "admin", {"display_name": "Launch", "mode": "safe"}
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(
            setup_app.read_config(),
            {"display_name": "Launch", "mode": "safe"},
        )

    def test_denied_save_leaves_configuration_unchanged(self):
        before = setup_app.read_config()
        result = setup_app.save_setup(
            "guest", {"display_name": "Unauthorized", "mode": "safe"}
        )
        self.assertEqual(set(result), {"ok", "error"})
        self.assertFalse(result["ok"])
        self.assertIn("PermissionError:", result["error"])
        self.assertIn("actor", result["error"])
        self.assertEqual(setup_app.read_config(), before)
