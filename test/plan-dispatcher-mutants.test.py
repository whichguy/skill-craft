#!/usr/bin/env python3
"""Gates 2 and 4 of the Plan Orchestrator test method, for every spec.

Each spec under test/orchestrator_scenarios/specs/ must pass spec_lint.py, and
every mutants file under test/orchestrator_scenarios/mutants/ must have each of
its contrary changes killed by the scenario its spec names (mutate.py).
"""

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "test/orchestrator_scenarios"


class OrchestratorGates(unittest.TestCase):
    def run_tool(self, *argv: str) -> None:
        result = subprocess.run([sys.executable, *argv], cwd=ROOT, capture_output=True, text=True,
                                timeout=1500, check=False)
        self.assertEqual(result.returncode, 0, result.stdout[-6000:] + result.stderr[-2000:])

    def test_specs_pass_review_lint(self) -> None:
        specs = sorted(str(path) for path in (SCENARIOS / "specs").glob("*.md"))
        self.assertTrue(specs)
        self.run_tool(str(SCENARIOS / "spec_lint.py"), *specs)

    def test_every_mutant_is_killed_by_its_named_scenario(self) -> None:
        files = sorted((SCENARIOS / "mutants").glob("*.json"))
        self.assertTrue(files)
        for mutants in files:
            with self.subTest(mutants=mutants.name):
                self.run_tool(str(SCENARIOS / "mutate.py"), str(mutants))


if __name__ == "__main__":
    unittest.main()
