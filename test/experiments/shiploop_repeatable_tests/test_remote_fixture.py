"""Run the retained remote definitions against local service fault fixtures."""
from pathlib import Path
import subprocess
import unittest


class RemoteFixtureTests(unittest.TestCase):
    def test_remote_definitions_and_lifecycle_simulation(self):
        root = Path(__file__).resolve().parent / "remote_fixture"
        result = subprocess.run(
            ["node", "scripts/verify.cjs"], cwd=root, capture_output=True,
            text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
