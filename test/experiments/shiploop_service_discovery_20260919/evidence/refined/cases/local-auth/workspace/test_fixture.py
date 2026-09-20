import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))
from auth_service import PasswordAuth


class Logger:
    def __init__(self):
        self.events = []

    def info(self, event, **details):
        self.events.append((event, details))


class Sessions:
    def __init__(self):
        self.issued = []

    def issue(self, subject):
        self.issued.append(subject)
        return "synthetic-session"


class ExistingAuthBehaviorTest(unittest.TestCase):
    def test_failed_password_attempt_is_logged_without_session(self):
        logger, sessions = Logger(), Sessions()
        with self.assertRaises(PermissionError):
            PasswordAuth(logger, sessions).authenticate("sam", "wrong", False)
        self.assertEqual(logger.events[0][0], "login_failed")
        self.assertEqual(sessions.issued, [])
