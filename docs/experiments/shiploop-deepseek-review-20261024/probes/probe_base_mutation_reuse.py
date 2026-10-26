"""Probe: with an unchanged tree, does `complete` after a passing `complete --check-only` re-run the base run and
the mutation check?  Counts every command ShipLoop actually runs, by working directory.

Run: python3 probe_base_mutation_reuse.py <repo>/test/shiploop-test-loop.test.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

TEST_FILE = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(TEST_FILE.parent))
spec = importlib.util.spec_from_file_location("shiploop_test_loop_tests", TEST_FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ReuseProbe(mod.TestLoopTests):
    def test_probe(self) -> None:
        self.calc_item(self.REAL_TEST)
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([mod.TRIVIAL])
        done = dict(mod.DONE, evidence_refs=[str(self.terminal())])
        real = mod.test_loop.lint.run_argv
        calls = []

        def counting(argv, cwd, timeout, **kw):
            calls.append((list(argv), str(cwd)))
            return real(argv, cwd, timeout, **kw)

        with mock.patch.object(mod.test_loop.lint, "run_argv", side_effect=counting):
            ok, lines = mod.test_loop.red_check(self.run_dir, self.state(), self.item(), self.action(), None)
            after_red_check = list(calls)
            calls.clear()
            self.complete_output(done, check_only=True)
            after_check_only = list(calls)
            calls.clear()
            self.complete_output(done, check_only=False)
            after_complete = list(calls)

        def show(label, rows):
            inside = [argv for argv, cwd in rows if cwd == str(self.repo)]
            print("\n%s: %d command runs (%d in the checkout, %d elsewhere)"
                  % (label, len(rows), len(inside), len(rows) - len(inside)))
            for argv, cwd in rows:
                print("   ", ("checkout" if cwd == str(self.repo) else "elsewhere"), "|", argv[-1])

        show("red-check (the packet's own command)", after_red_check)
        show("complete --check-only", after_check_only)
        show("complete (the real callback)", after_complete)
        records = sorted(p.name for p in (self.run_dir / "tests").iterdir())
        print("\nrecords:", records)
        import shiploop_store as store
        import shiploop_test_loop as test_loop

    def action_of(self):
        import shiploop_navigator as nav
        import shiploop_store as store
        state = store.read_record(self.run_dir / "state.md")
        return state["cursor"]["action_id"] if "cursor" in state else nav.current_action(state)["id"]


if __name__ == "__main__":
    unittest.main(argv=["probe", "ReuseProbe.test_probe"], exit=False, verbosity=2)
