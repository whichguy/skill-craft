"""Exp 2: does the integrate auto-commit take a user's edits?  Uses the snapshot's own test fixture."""
import importlib.util, sys, unittest
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src"
spec = importlib.util.spec_from_file_location("tl", SRC / "test/shiploop-test-loop.test.py")
tl = importlib.util.module_from_spec(spec); sys.modules["tl"] = tl; spec.loader.exec_module(tl)
git = tl.git
PLAN = {"test_commands": tl.COMMANDS, "paths": ["a.py", "b.py"]}

class Exp(tl.TestLoopTests):
    def show(self, label, out):
        files = git(self.repo, "show", "--name-only", "--format=", "HEAD").split()
        print(f"\n## {label}\n  committed files: {files}")
        for f in ("a.py", "b.py"):
            if f in files:
                print(f"  {f} in commit:", git(self.repo, "show", f"HEAD:{f}").strip().replace("\n", " | "))
        print("  status after:", git(self.repo, "status", "--short").strip().replace("\n", " ; ") or "(clean)")
        for line in out.splitlines():
            if line.startswith(("ShipLoop committed", "Not committed")): print("  " + line)

    def test_a_user_dirty_edit_in_file_agent_also_changes(self):
        (self.repo / "a.py").write_text("x = 1\nUSER_WIP = True\n")   # uncommitted before the run
        self.start(); self.drive_to("integrate", step_plan=PLAN)
        (self.repo / "a.py").write_text((self.repo / "a.py").read_text() + "AGENT = 2\n")
        self.show("A user WIP in a.py before run; agent edits a.py", self.complete(tl.DONE))

    def test_b_user_dirty_edit_in_declared_file_agent_does_not_touch(self):
        (self.repo / "b.py").write_text("USER_WIP = True\n")           # untracked, declared, pre-run
        self.start(); self.drive_to("integrate", step_plan=PLAN)
        (self.repo / "a.py").write_text("x = 2\n")
        self.show("B user WIP in declared b.py before run; agent edits a.py only", self.complete(tl.DONE))

    def test_c_user_edits_declared_file_during_run(self):
        self.start(); self.drive_to("integrate", step_plan=PLAN)
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "b.py").write_text("USER_DURING_RUN = True\n")   # user, mid-run, declared path
        self.show("C user creates declared b.py during run", self.complete(tl.DONE))

    def test_d_user_edits_undeclared_file_during_run(self):
        self.start(); self.drive_to("integrate", step_plan=PLAN)
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "notes.txt").write_text("user notes\n")
        self.show("D user creates undeclared notes.txt during run", self.complete(tl.DONE))

if __name__ == "__main__":
    unittest.main(argv=["x", "Exp.test_a_user_dirty_edit_in_file_agent_also_changes", "Exp.test_b_user_dirty_edit_in_declared_file_agent_does_not_touch",
                        "Exp.test_c_user_edits_declared_file_during_run", "Exp.test_d_user_edits_undeclared_file_during_run"], verbosity=1)
