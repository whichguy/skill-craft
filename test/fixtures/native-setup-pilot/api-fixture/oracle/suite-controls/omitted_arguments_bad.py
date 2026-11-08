"""Known-bad contract control: missing arguments are wrongly expected as envelopes."""
import unittest

import setup_app


class WrongArityEnvelopeExpectation(unittest.TestCase):
    def test_missing_required_argument_is_not_a_python_binding_error(self):
        try:
            result = setup_app.save_setup("admin")
        except TypeError:
            result = None
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), {"ok", "error"})
