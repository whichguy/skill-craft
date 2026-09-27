"""E8: does the lint gate on each implement step punish (or undo) work a later step completes?"""
import re, unittest
from fixture import *
import e7_steps as e7
OUT = {}
TWO = [{"id": "S1", "task": "Add the import and the call site."}, {"id": "S2", "task": "Add the helper the call uses."}]

class E8(tl.TestLoopTests):
    def run_mode(self, mode, s1_text, label):
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Lint fixture.", improve_skill=str(tl.IMPROVE_CARD), lint_option=mode))
        self.drive_to("step-plan"); self.complete(dict(tl.DONE, **e7.plan(TWO)))
        for _ in range(60):
            st = self.state()
            if st.get("active_improve"): self.finish_improve(); continue
            if nav.current_stage(st) == "implement": break
            self.complete(dict(tl.DONE))
        (self.repo / "a.py").write_text(s1_text)
        row = []
        try:
            out = self.complete(dict(tl.DONE)); row.append("S1 done accepted")
        except nav.NavigatorError as e:
            row.append("S1 REFUSED: " + re.sub(r"/\S+", "<p>", " ".join(str(e).split()))[:200]); OUT[label] = row; return
        row.append("a.py after S1 accepted: " + (self.repo / "a.py").read_text().replace("\n", " | "))
        row.append("now at: " + nav.current_stage(self.state()) + " " + str(re.findall(r"Step \S+ \(\d of \d\)", self.packet())))
        OUT[label] = row

    def test_report_unused_import(self): self.run_mode("report", "import os\nx = 1\n", "report: S1 adds import S2 will use")
    def test_fix_unused_import(self): self.run_mode("fix", "import os\nx = 1\n", "fix: S1 adds import S2 will use")
    def test_report_undefined(self): self.run_mode("report", "x = helper()\n", "report: S1 calls helper S2 defines")
    def test_fix_undefined(self): self.run_mode("fix", "x = helper()\n", "fix: S1 calls helper S2 defines")

if __name__ == "__main__":
    unittest.main(argv=["x", "E8"], exit=False, verbosity=0)
    for k, v in OUT.items(): print(f"\n## {k}"); [print("   " + x) for x in v]
