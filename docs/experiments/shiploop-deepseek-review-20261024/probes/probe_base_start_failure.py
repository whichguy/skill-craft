"""Probe: what does the base run say when the focused command never reaches the tests?

Run: python3 probe_base_start_failure.py <repo>/test/shiploop-test-loop.test.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path

TEST_FILE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(TEST_FILE.parent))
spec = importlib.util.spec_from_file_location("shiploop_test_loop_tests", TEST_FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class StartFailureProbe(mod.TestLoopTests):
    def test_probe(self) -> None:
        self.calc_item(self.REAL_TEST)
        # Rewrite the item's focused command as one that fails before any test can run.
        broken = {"command": "python3 -c \"import sys; sys.exit(3)\"", "suite": "focused",
                  "ids": ["test_tc1"]}
        with self.patched_commands(broken):
            ok, lines = mod.test_loop.red_check(self.run_dir, self.state(), self.item(), self.action(), None)
        print("\nred_check ok =", ok)
        for line in lines:
            print("   |", line)

    def patched_commands(self, row):
        import shiploop_test_loop as test_loop
        real = test_loop.base_commands
        import contextlib

        @contextlib.contextmanager
        def patcher():
            def fake(state, work_item):
                return [row]
            test_loop.base_commands = fake
            try:
                yield
            finally:
                test_loop.base_commands = real
        return patcher()


if __name__ == "__main__":
    unittest.main(argv=["probe", "StartFailureProbe.test_probe"], exit=False, verbosity=2)
