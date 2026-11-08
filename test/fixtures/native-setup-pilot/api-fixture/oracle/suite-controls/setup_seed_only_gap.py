"""Deliberately weak but valid: seeded state passes without executing Save."""
import unittest

import setup_app


class SeedOnlyGap(unittest.TestCase):
    def setUp(self):
        setup_app.fixture_seed({"display_name": "Launch", "mode": "review"})

    def test_desired_state_is_already_present(self):
        self.assertEqual(
            setup_app.read_config(),
            {"display_name": "Launch", "mode": "review"},
        )
