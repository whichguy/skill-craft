"""Independent public-behavior oracle used only inside the fixture harness."""
import unittest

import change_app
import setup_app


class ErrorAssertions:
    def assert_error(self, result, error_type, parameter):
        self.assertEqual(set(result), {"ok", "error"})
        self.assertFalse(result["ok"])
        error = result["error"]
        self.assertIsInstance(error, str)
        self.assertTrue(error)
        self.assertLessEqual(len(error), 120)
        self.assertTrue(error.startswith(error_type + ":"))
        self.assertIn(parameter, error)


class SetupOracle(ErrorAssertions, unittest.TestCase):
    def setUp(self):
        setup_app.fixture_seed({"display_name": "Original", "mode": "review"})

    def test_admin_save_persists_exact_nonsecret_configuration(self):
        result = setup_app.save_setup(
            "admin", {"display_name": "Launch", "mode": "safe"}
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(
            setup_app.read_config(), {"display_name": "Launch", "mode": "safe"}
        )
        long_name = "x" * 121
        self.assertEqual(
            setup_app.save_setup("admin", {"display_name": long_name, "mode": "review"}),
            {"ok": True},
        )
        self.assertEqual(setup_app.read_config(),
                         {"display_name": long_name, "mode": "review"})

    def test_read_returns_a_copy(self):
        value = setup_app.read_config()
        value["display_name"] = "tampered"
        self.assertEqual(
            setup_app.read_config(), {"display_name": "Original", "mode": "review"}
        )

    def test_denied_save_does_not_mutate(self):
        before = setup_app.read_config()
        result = setup_app.save_setup(
            "bob", {"display_name": "Unauthorized", "mode": "safe"}
        )
        self.assert_error(result, "PermissionError", "actor")
        self.assertEqual(setup_app.read_config(), before)

    def test_invalid_saves_do_not_mutate(self):
        before = setup_app.read_config()
        cases = (
            ("admin", [], "TypeError", "values"),
            ("admin", {"display_name": 7, "mode": "safe"}, "TypeError", "display_name"),
            ("admin", {"display_name": "   ", "mode": "safe"}, "ValueError", "display_name"),
            ("admin", {"display_name": "Valid", "mode": []}, "TypeError", "mode"),
            ("admin", {"display_name": "Valid", "mode": "secret"}, "ValueError", "mode"),
            ("admin", {"display_name": "Valid", "mode": "safe", "extra": 1},
             "ValueError", "values"),
            ("admin", {"display_name": "Valid"}, "ValueError", "values"),
            (42, {"display_name": "Valid", "mode": "safe"}, "TypeError", "actor"),
        )
        for actor, values, error_type, parameter in cases:
            with self.subTest(actor=actor, values=values):
                self.assert_error(
                    setup_app.save_setup(actor, values), error_type, parameter
                )
                self.assertEqual(setup_app.read_config(), before)


class ChangeOracle(ErrorAssertions, unittest.TestCase):
    def setUp(self):
        change_app.fixture_seed()

    def propose(self, amount, key, version=1):
        return change_app.propose_change(
            "alice", "demo-1", version, {"amount": amount}, key
        )

    def test_propose_is_preconfirmation_only_and_key_replay_is_idempotent(self):
        before = change_app.read_record("alice", "demo-1")
        long_key = self.propose(24, "k" * 121)
        self.assertTrue(long_key["ok"])
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)
        first = self.propose(25, "same")
        replay = self.propose(25, "same")
        conflict = self.propose(26, "same")
        self.assertTrue(first["ok"])
        self.assertEqual(replay, first)
        self.assert_error(conflict, "ValueError", "idempotency_key")
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)

    def test_confirm_writes_exact_value_once_on_replay(self):
        proposal = self.propose(37, "confirm")
        self.assertTrue(proposal["ok"])
        pid = proposal["proposal_id"]
        self.assertEqual(change_app.confirm_change("alice", pid),
                         {"ok": True, "replayed": False})
        applied = change_app.read_record("alice", "demo-1")
        self.assertEqual(applied["amount"], 37)
        self.assertEqual(applied["version"], 2)
        self.assertEqual(change_app.confirm_change("alice", pid),
                         {"ok": True, "replayed": True})
        self.assertEqual(change_app.read_record("alice", "demo-1"), applied)

    def test_stale_snapshot_fails_without_overwriting_winner(self):
        older = self.propose(20, "older")
        newer = self.propose(30, "newer")
        self.assertTrue(older["ok"])
        self.assertTrue(newer["ok"])
        self.assertTrue(change_app.confirm_change("alice", newer["proposal_id"])["ok"])
        winner = change_app.read_record("alice", "demo-1")
        stale = change_app.confirm_change("alice", older["proposal_id"])
        self.assert_error(stale, "ValueError", "proposal_id")
        self.assertIn("expected_version", stale["error"])
        self.assertEqual(change_app.read_record("alice", "demo-1"), winner)
        self.assertEqual(winner["amount"], 30)

    def test_owner_checks_cover_propose_confirm_cancel(self):
        before = change_app.read_record("alice", "demo-1")
        denied = change_app.propose_change(
            "bob", "demo-1", 1, {"amount": 50}, "bob-key"
        )
        self.assert_error(denied, "PermissionError", "actor")
        own = self.propose(50, "alice-key")
        self.assert_error(
            change_app.confirm_change("bob", own["proposal_id"]),
            "PermissionError", "actor",
        )
        self.assert_error(
            change_app.cancel_change("bob", own["proposal_id"]),
            "PermissionError", "actor",
        )
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)
        self.assertTrue(change_app.confirm_change("alice", own["proposal_id"])["ok"])

    def test_cancel_and_cancel_replay_never_change_record(self):
        proposal = self.propose(88, "cancel")
        before = change_app.read_record("alice", "demo-1")
        pid = proposal["proposal_id"]
        self.assertEqual(change_app.cancel_change("alice", pid),
                         {"ok": True, "replayed": False})
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)
        self.assertEqual(change_app.cancel_change("alice", pid),
                         {"ok": True, "replayed": True})
        self.assert_error(
            change_app.confirm_change("alice", pid), "ValueError", "proposal_id"
        )
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)

    def test_invalid_or_stale_proposals_fail_without_mutation(self):
        before = change_app.read_record("alice", "demo-1")
        cases = (
            (3, "demo-1", 1, {"amount": 10}, "bad-actor", "TypeError", "actor"),
            ("alice", 3, 1, {"amount": 10}, "bad-record", "TypeError", "record_id"),
            ("alice", "demo-1", False, {"amount": 10}, "bad-version",
             "TypeError", "expected_version"),
            ("alice", "demo-1", 0, {"amount": 10}, "stale",
             "ValueError", "expected_version"),
            ("alice", "demo-1", 1, [], "bad-changes", "TypeError", "changes"),
            ("alice", "demo-1", 1, {"amount": 10, "owner": "bob"}, "bad-fields",
             "ValueError", "changes"),
            ("alice", "demo-1", 1, {"amount": True}, "bad-bool", "TypeError", "amount"),
            ("alice", "demo-1", 1, {"amount": 0}, "bad-low", "ValueError", "amount"),
            ("alice", "demo-1", 1, {"amount": 101}, "bad-high", "ValueError", "amount"),
            ("alice", "demo-1", 1, {"amount": 10}, 9, "TypeError", "idempotency_key"),
            ("alice", "demo-1", 1, {"amount": 10}, "", "ValueError", "idempotency_key"),
            ("alice", "missing", 1, {"amount": 10}, "missing",
             "KeyError", "record_id"),
            ("bob", "demo-1", 1, {"amount": 10}, "unauthorized",
             "PermissionError", "actor"),
        )
        for actor, record_id, version, changes, key, error_type, parameter in cases:
            with self.subTest(actor=actor, record_id=record_id, version=version, key=key):
                self.assert_error(
                    change_app.propose_change(
                        actor, record_id, version, changes, key
                    ),
                    error_type,
                    parameter,
                )
                self.assertEqual(change_app.read_record("alice", "demo-1"), before)

    def test_invalid_or_unknown_proposal_arguments_are_typed_and_nonmutating(self):
        before = change_app.read_record("alice", "demo-1")
        self.assert_error(
            change_app.confirm_change(7, "missing"), "TypeError", "actor"
        )
        self.assert_error(
            change_app.confirm_change("alice", None), "TypeError", "proposal_id"
        )
        self.assert_error(
            change_app.confirm_change("alice", "missing"), "KeyError", "proposal_id"
        )
        self.assert_error(
            change_app.cancel_change(7, "missing"), "TypeError", "actor"
        )
        self.assert_error(
            change_app.cancel_change("alice", None), "TypeError", "proposal_id"
        )
        self.assert_error(
            change_app.cancel_change("alice", "missing"), "KeyError", "proposal_id"
        )
        self.assertEqual(change_app.read_record("alice", "demo-1"), before)


if __name__ == "__main__":
    unittest.main()
