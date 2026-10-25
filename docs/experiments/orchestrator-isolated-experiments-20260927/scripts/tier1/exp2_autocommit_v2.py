"""Exp 2 (adapted to e707b794): does the in-place auto-commit take a user's edits?

The integrate stage is gone; ShipLoop now commits at each accepted inline implement step (_step_commit) and the rest at
verify (_item_commit), both through item_scope.commit_item.  Same four cases; the commits are read at both points.
"""
import importlib.util, subprocess, sys, unittest
from unittest import mock
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src"
spec = importlib.util.spec_from_file_location("tl", SRC / "test/shiploop-test-loop.test.py")
tl = importlib.util.module_from_spec(spec); sys.modules["tl"] = tl; spec.loader.exec_module(tl)
git, nav = tl.git, tl.nav
PLAN = {"test_commands": tl.COMMANDS, "paths": ["a.py", "b.py"]}
OUT = []

class Exp(tl.TestLoopTests):
    def commits_since(self, base):
        rows = []
        for sha in git(self.repo, "rev-list", "--reverse", base + "..HEAD").split():
            subj = git(self.repo, "log", "-1", "--format=%s", sha).strip()
            files = git(self.repo, "show", "--name-only", "--format=", sha).split()
            body = {f: git(self.repo, "show", f"{sha}:{f}").strip().replace("\n", " | ") for f in files if f in ("a.py", "b.py")}
            rows.append(f"{subj[:40]!r} files={files} {body}")
        return rows

    def implement_done(self):
        return self.complete(tl.DONE)

    def to_verify(self, out_lines):
        for _ in range(60):
            st = self.state()
            if st.get("active_improve"): self.finish_improve(); continue
            if nav.current_stage(st) == "verify":
                self.verify_lines = [l[:200] for l in self.packet().splitlines() if l.startswith(("Changed", "Step plan paths"))]
                return
            if nav.current_stage(st) in tl.test_loop.STAGES: self.pass_loop()
            else: out_lines.append(self.complete(tl.DONE))
        raise AssertionError("no verify")

    def run_case(self, label, pre=None, agent=None, during=None, after_step=None):
        base = git(self.repo, "rev-parse", "HEAD").strip()
        if pre: pre()
        self.start(); self.drive_to("implement", step_plan=PLAN)
        info = {"mode": self.state().get("execution_mode")}
        if agent: agent()
        if during: during()
        out = [self.implement_done()]
        info["after implement step"] = self.commits_since(base)
        if after_step: after_step()
        self.to_verify(out); out.append(self.complete(tl.DONE, loop=None))
        info["after verify"] = self.commits_since(base)
        info["status"] = git(self.repo, "status", "--short").strip().replace("\n", " ; ") or "(clean)"
        info["notices"] = [l for o in out for l in o.splitlines() if l.startswith(("ShipLoop committed", "Not committed"))]
        info["verify packet scope lines"] = self.verify_lines
        # X13: does recovery `next` (public CLI) repeat the not-committed notice after verify's commit?
        cli = SRC / "skills/shiploop/scripts/shiploop"
        p = subprocess.run([sys.executable, str(cli), "next", "--run-dir", str(self.run_dir)], capture_output=True, text=True)
        info["next after verify: stage"] = tl.nav.current_stage(self.state())
        info["next after verify mentions not-committed"] = [l[:160] for l in p.stdout.splitlines()
                                                           if "Not committed" in l or "will not commit" in l or "notes.txt" in l]
        OUT.append((label, info))

    def test_a(self):
        self.run_case("A user WIP in a.py before run; agent edits a.py",
                      pre=lambda: (self.repo / "a.py").write_text("x = 1\nUSER_WIP = True\n"),
                      agent=lambda: (self.repo / "a.py").write_text((self.repo / "a.py").read_text() + "AGENT = 2\n"))
    def test_b(self):
        self.run_case("B user WIP in declared b.py before run; agent edits a.py only",
                      pre=lambda: (self.repo / "b.py").write_text("USER_WIP = True\n"),
                      agent=lambda: (self.repo / "a.py").write_text("x = 2\n"))
    def test_c1(self):
        self.run_case("C1 user creates declared b.py during implement",
                      agent=lambda: (self.repo / "a.py").write_text("x = 2\n"),
                      during=lambda: (self.repo / "b.py").write_text("USER_DURING_RUN = True\n"))
    def test_c2(self):
        self.run_case("C2 user creates declared b.py after the step commit, before verify",
                      agent=lambda: (self.repo / "a.py").write_text("x = 2\n"),
                      after_step=lambda: (self.repo / "b.py").write_text("USER_DURING_RUN = True\n"))
    def test_d(self):
        self.run_case("D user creates undeclared notes.txt during run",
                      agent=lambda: (self.repo / "a.py").write_text("x = 2\n"),
                      during=lambda: (self.repo / "notes.txt").write_text("user notes\n"))

if __name__ == "__main__":
    # The test stage's mutation check is orthogonal to this claim (the fixture's check.sh cannot kill a mutant of a.py).
    with mock.patch.object(tl.test_loop, "mutation_check", return_value=["mutation: skipped (patched by exp2)"]):
        unittest.main(argv=["x"] + ["Exp." + n for n in sorted(vars(Exp)) if n.startswith("test_")], exit=False, verbosity=1)
    for label, info in OUT:
        print("\n## " + label)
        for k, v in info.items(): print("  ", k, ":", v)
