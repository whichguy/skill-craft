"""X7 (adapted e6_trivial_cmds.py): which trivial or printed test commands get through step-plan, the test stage
(base run = red, candidate run = green, mutation check) and verify's rerun (regression)?
Changes vs original: test-red/test-green are gone; the test stage runs base_check, loop_run and mutation_check at done;
the walk uses drive_to (which completes step-plan with the plan) and pass-through stages; own tests only."""
import json, re, unittest
from fixture import *
from own import run_own
FOCUSED_REAL = {"command": "sh check.sh fixed.txt", "suite": "focused"}
CASES = {
    "0 control: real one-test runner":       [FOCUSED_REAL, {"command": "test -f retained.txt", "suite": "regression"}],
    "1 true (focused)":                      [{"command": "true", "suite": "focused"}],
    "2 bare fake summary (focused)":         [{"command": "printf 'Ran 5 tests in 0.1s\\n\\nOK\\n'", "suite": "focused"}],
    "3 unittest zero tests (focused)":       [{"command": "python3 -m unittest discover -s emptydir", "suite": "focused"}],
    "A fake summary + red_na (focused)":     [{"command": "printf 'Ran 5 tests in 0.1s\\n\\nOK\\n'", "suite": "focused", "ids": ["T1"]}],
    "B summary around real condition":       [{"command": "echo 'Ran 5 tests in 0.1s'; echo OK; test -f fixed.txt", "suite": "focused"}],
    "C regression `true`":                   [FOCUSED_REAL, {"command": "true", "suite": "regression"}],
    "D regression bare fake summary":        [FOCUSED_REAL, {"command": "printf 'Ran 9 tests in 0.1s\\n\\nOK\\n'", "suite": "regression"}],
}
RED_NA = {"A fake summary + red_na (focused)": [{"id": "T1", "reason": "characterisation"}]}
RES = {}
def short(e): return re.sub(r"/\S+", "<p>", " ".join(str(e).split()))[:230]
def make(name, cmds):
    def t(self):
        (self.repo / "emptydir").mkdir(exist_ok=True)
        self.start()
        plan = {"paths": ["a.py"], "test_commands": [dict(cmds[0], criteria=["C1"]), *cmds[1:]],
                "criteria": [{"id": "C1", "text": "It works."}]}
        out = {}
        try:
            self.drive_to("test", step_plan=plan); out["step-plan"] = "accepted"
        except (nav.NavigatorError, AssertionError) as e:
            out["step-plan/walk"] = "REFUSED: " + short(e); RES[name] = out; return
        (self.repo / "fixed.txt").write_text("fixed\n"); (self.repo / "retained.txt").write_text("retained\n")
        try:
            self.run_loop([tl.TRIVIAL])
            extra = {"red_na": RED_NA[name]} if name in RED_NA else {}
            self.complete(dict(tl.DONE, evidence_refs=[str(self.terminal())], **extra), loop=False)
            out["test stage (base/red + candidate/green + mutation)"] = "accepted"
        except (nav.NavigatorError, AssertionError) as e:
            out["test stage"] = "REFUSED: " + short(e); RES[name] = out; return
        try:
            self.drive_to("carry-forward"); out["verify rerun (regression)"] = "accepted"
        except (nav.NavigatorError, AssertionError) as e:
            out["verify rerun"] = "REFUSED: " + short(e)
        RES[name] = out
    return t
class E6(tl.TestLoopTests): pass
for i, (n, c) in enumerate(CASES.items()): setattr(E6, f"test_{i}", make(n, c))
if __name__ == "__main__":
    run_own(E6)
    for n, o in RES.items(): print(f"\n## {n}"); [print(f"   {k}: {v}") for k, v in o.items()]
