"""E6: which trivial test commands get through step-plan, test-red and test-green?"""
import json, unittest
from fixture import *
CASES = {
    "true (focused)":            [{"command": "true", "suite": "focused"}],
    "echo fake summary":         [{"command": "printf 'Ran 5 tests in 0.1s\\n\\nOK\\n'", "suite": "focused"}],
    "echo fake then fail-less":  [{"command": "echo 'Ran 5 tests in 0.1s'; echo OK; test -f fixed.txt", "suite": "focused"}],
    "unittest zero tests":       [{"command": "python3 -m unittest discover -s emptydir", "suite": "focused"}],
    "real one-test runner":      [{"command": "sh check.sh fixed.txt", "suite": "focused"}],
}
RES = {}
def make(name, cmds):
    def t(self):
        (self.repo / "emptydir").mkdir(exist_ok=True)
        self.start()
        plan = {"steps": [{"id": "S1", "task": "Change."}], "paths": ["a.py"],
                "test_commands": [dict(cmds[0], criteria=["C1"]), *cmds[1:]],
                "criteria": [{"id": "C1", "text": "It works."}]}
        out = {}
        try:
            self.drive_to("step-plan")
            self.complete(dict(tl.DONE, **plan)); out["step-plan"] = "accepted"
        except nav.NavigatorError as e:
            out["step-plan"] = "REFUSED: " + str(e).splitlines()[0][:120]; RES[name] = out; return
        # walk to test-red with bare results
        for _ in range(40):
            st = self.state()
            if st.get("active_improve"): self.finish_improve(); continue
            if nav.current_stage(st) == "test-red": break
            self.complete(dict(tl.DONE))
        try:
            self.complete(dict(tl.DONE)); out["test-red"] = "accepted"
        except nav.NavigatorError as e:
            out["test-red"] = "REFUSED: " + " ".join(str(e).split())[:160]
            RES[name] = out; return
        self.complete(dict(tl.DONE))  # implement
        try:
            self.run_loop([tl.TRIVIAL]); self.complete(dict(tl.DONE, evidence_refs=[str(self.terminal())]))
            out["test-green"] = "accepted"
        except (nav.NavigatorError, AssertionError) as e:
            out["test-green"] = "REFUSED: " + " ".join(str(e).split())[:160]
        RES[name] = out
    return t
class E6(tl.TestLoopTests): pass
for i, (n, c) in enumerate(CASES.items()): setattr(E6, f"test_{i}", make(n, c))
if __name__ == "__main__":
    unittest.main(argv=["x"], exit=False, verbosity=0)
    for n, o in RES.items(): print(f"\n## {n}"); [print(f"   {k}: {v}") for k, v in o.items()]
