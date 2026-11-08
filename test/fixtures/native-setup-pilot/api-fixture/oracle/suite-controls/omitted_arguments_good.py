"""Known-good contract checks: Python binding errors stay outside app envelopes."""
import unittest

import change_app
import setup_app


class OmittedArgumentsContract(unittest.TestCase):
    def setUp(self):
        setup_app.fixture_seed({"display_name": "Original", "mode": "review"})
        change_app.fixture_seed()

    def test_missing_and_extra_arguments_raise_python_type_error(self):
        values = {"display_name": "Launch", "mode": "safe"}
        calls = (
            lambda: setup_app.read_config("extra"),
            lambda: setup_app.save_setup("admin"),
            lambda: setup_app.save_setup("admin", values, "extra"),
            lambda: setup_app.fixture_seed(),
            lambda: setup_app.fixture_seed(values, "extra"),
            lambda: change_app.read_record("alice"),
            lambda: change_app.read_record("alice", "demo-1", "extra"),
            lambda: change_app.propose_change("alice", "demo-1", 1, {"amount": 20}),
            lambda: change_app.propose_change(
                "alice", "demo-1", 1, {"amount": 20}, "key", "extra"
            ),
            lambda: change_app.confirm_change("alice"),
            lambda: change_app.confirm_change("alice", "p1", "extra"),
            lambda: change_app.cancel_change("alice"),
            lambda: change_app.cancel_change("alice", "p1", "extra"),
            lambda: change_app.fixture_seed(None, "extra"),
        )
        for index, call in enumerate(calls):
            with self.subTest(call=index):
                with self.assertRaises(TypeError) as raised:
                    call()
                self.assertIs(type(raised.exception), TypeError)

    def test_read_record_none_is_the_documented_exception(self):
        self.assertIsNone(change_app.read_record("bob", "demo-1"))
