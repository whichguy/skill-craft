"""E1 on current main: at each stage, a truly bare done via the real dispatch (exact inbox path, check_only), then the fixture's drive_to."""
import contextlib, io, types, unittest
from fixture import *
BARE = {"outcome": "done", "summary": "Bare done: nothing was done."}
ORDER = ("intake discovery research spec test-strategy plan prepare step-plan test-spec implement test document verify "
         "carry-forward system-test-author system-test product-acceptance release-plan release-check release release-verify "
         "operations handoff").split()
ROWS = []
class Matrix(tl.TestLoopTests):
    def bare(self, check_only):
        st = self.state(); act = nav.current_action(st)["id"]
        before = (self.run_dir / "state.md").read_bytes()
        path = self.run_dir / "inbox" / (act + ".md"); path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(BARE, "result"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                nav.dispatch(tl.CORE, self.run_dir, st, types.SimpleNamespace(command="complete", action=act, result=str(path), check_only=check_only))
            changed = (self.run_dir / "state.md").read_bytes() != before
            return "ACCEPTED" + (" (state advanced)" if changed else " (check only)"), ""
        except nav.NavigatorError as e:
            return "refused", " ".join(str(e).split())[:120]
    def test_matrix(self):
        self.start()
        for stage in ORDER:
            try: self.drive_to(stage)
            except AssertionError: ROWS.append((stage, "not reached", "")); continue
            ROWS.append((stage, *self.bare(check_only=True)))
if __name__ == "__main__":
    unittest.main(argv=["x", "Matrix.test_matrix"], exit=False, verbosity=0)
    for s, v, w in ROWS: print(f"{s:20s} {v:26s} {w}")
