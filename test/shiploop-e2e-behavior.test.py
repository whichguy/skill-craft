import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
CASE_DIR = TEST_DIR / "shiploop_e2e"
FIXTURES = CASE_DIR / "fixtures" / "battleship"
CHECKER = CASE_DIR / "checks" / "battleship.py"


class BattleshipBehaviorChecksTest(unittest.TestCase):
    def run_check(self, fixture: Path, action: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-behavior-") as scratch:
            env = dict(os.environ, SHIPLOOP_BATTLESHIP_DIAGNOSTICS=scratch)
            return subprocess.run(
                [sys.executable, str(CHECKER), action],
                cwd=fixture,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=60,
            )

    def assert_check_passes(self, fixture: Path, action: str) -> None:
        result = self.run_check(fixture, action)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_case_metadata_accounts_for_both_delivery_prompts(self) -> None:
        cases = json.loads((CASE_DIR / "cases.json").read_text())
        expected_ids = {
            "battleship": {"BS-1", "BS-2", "BS-3", "BS-4", "BS-5", "BS-6"},
            "battleship-scoring": {"BSS-1", "BSS-2", "BSS-3", "BSS-4"},
        }
        for name in ("battleship", "battleship-scoring"):
            with self.subTest(case=name):
                case = cases[name]
                self.assertEqual(case["kind"], "delivery")
                self.assertEqual(case["expected_terminal"], "done")
                requirements = case["requirements"]
                self.assertTrue(requirements)
                ids = [item["id"] for item in requirements]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(set(ids), expected_ids[name])
                self.assertTrue(all(item["description"].strip() for item in requirements))

    def test_reference_and_alternative_pass_behavior_and_transfer_controls(self) -> None:
        for variant in ("reference", "alternative"):
            fixture = FIXTURES / variant
            with self.subTest(variant=variant, action="tests"):
                self.assert_check_passes(fixture, "tests")
            with self.subTest(variant=variant, action="delivery"):
                self.assert_check_passes(fixture, "delivery")
            with self.subTest(variant=variant, action="transfer"):
                self.assert_check_passes(fixture, "transfer")

    def test_zero_tests_and_nonfunctional_stub_are_rejected(self) -> None:
        fixture = FIXTURES / "broken"
        no_tests = self.run_check(fixture, "tests")
        self.assertNotEqual(no_tests.returncode, 0, no_tests.stdout + no_tests.stderr)
        self.assertIn("without evidence of a passing test", no_tests.stderr)

        broken_game = self.run_check(fixture, "delivery")
        self.assertNotEqual(broken_game.returncode, 0, broken_game.stdout + broken_game.stderr)
        self.assertIn("no shot returned hit or sunk", broken_game.stderr)
        self.assertIn("Diagnostics retained at:", broken_game.stderr)

    def test_scoring_checks_accept_two_implementations_and_reject_stub(self) -> None:
        for variant in ("reference", "alternative"):
            with self.subTest(variant=variant):
                self.assert_check_passes(FIXTURES / variant, "scoring")

        broken_game = self.run_check(FIXTURES / "broken", "scoring")
        self.assertNotEqual(broken_game.returncode, 0, broken_game.stdout + broken_game.stderr)
        self.assertIn("no shot returned hit or sunk", broken_game.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
