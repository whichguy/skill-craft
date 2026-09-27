"""E7: per-step implement under a revised plan, repeat, blocked and revise."""
import re, unittest
from fixture import *
OUT = {}
STEPS3 = [{"id": f"S{i}", "task": f"Do part {i}."} for i in (1, 2, 3)]
def plan(steps):
    return {"steps": steps, "test_commands": [dict(tl.COMMANDS[0], criteria=["C1"]), *tl.COMMANDS[1:]],
            "paths": ["a.py"], "criteria": [{"id": "C1", "text": "Check passes."}]}

class E7(tl.TestLoopTests):
    def step_line(self):
        m = re.search(r"Step (S\d+) \((\d+) of (\d+)\)", self.packet())
        return m.group(0) if m else "(no step line)"
    def to_step_plan(self): self.start(); self.drive_to("step-plan")
    def improve_with(self, final):
        st = self.state(); action = st["active_improve"]["action_id"]
        updated = nav.finish_improve(st, action, {"summary": "Improve.", "review_refs": ["r"], "check_refs": ["c"]}, final)
        nav.save(self.run_dir, updated)
    def walk_implement(self, label, limit=8):
        seq = []
        for _ in range(60):
            st = self.state()
            if st.get("active_improve"): self.finish_improve(); continue
            if nav.current_stage(st) == "implement": break
            self.complete(dict(tl.DONE))
        while nav.current_stage(self.state()) == "implement" and len(seq) < limit:
            seq.append(self.step_line()); self.complete(dict(tl.DONE))
        seq.append("-> " + nav.current_stage(self.state()))
        OUT[label] = seq

    def test_a_three_steps(self):
        self.to_step_plan(); self.complete(dict(tl.DONE, **plan(STEPS3))); self.walk_implement("A plan 3 steps")
    def test_b_improve_shrinks_to_one(self):
        self.to_step_plan(); self.complete(dict(tl.DONE, **plan(STEPS3)))
        self.improve_with(dict(tl.DONE, **plan(STEPS3[:1]))); self.walk_implement("B Improve shrinks 3 -> 1")
    def test_c_improve_grows_to_three(self):
        self.to_step_plan(); self.complete(dict(tl.DONE, **plan(STEPS3[:1])))
        self.improve_with(dict(tl.DONE, **plan(STEPS3))); self.walk_implement("C Improve grows 1 -> 3")
    def outcome_mid(self, label, result):
        self.to_step_plan(); self.complete(dict(tl.DONE, **plan(STEPS3)))
        for _ in range(60):
            st = self.state()
            if st.get("active_improve"): self.finish_improve(); continue
            if nav.current_stage(st) == "implement": break
            self.complete(dict(tl.DONE))
        seq = [self.step_line()]; self.complete(dict(tl.DONE)); seq.append(self.step_line())
        try:
            self.complete(result); seq.append(f"after {result['outcome']}: stage={nav.current_stage(self.state())} {self.step_line() if nav.current_stage(self.state())=='implement' else ''}")
        except nav.NavigatorError as e:
            seq.append("REFUSED " + " ".join(str(e).split())[:150])
        st = self.state()
        if nav.current_stage(st) == "step-plan" or st.get("active_improve"):
            # replan with two new steps, then walk implement again
            for _ in range(20):
                st = self.state()
                if st.get("active_improve"): self.finish_improve(); continue
                if nav.current_stage(st) == "step-plan": self.complete(dict(tl.DONE, **plan([{"id": "N1", "task": "New 1."}, {"id": "N2", "task": "New 2."}]))); break
                if nav.current_stage(st) == "implement": break
                self.complete(dict(tl.DONE))
            self.walk_implement("_tmp"); seq += ["replanned:"] + OUT.pop("_tmp")
        OUT[label] = seq
    def test_d_repeat(self): self.outcome_mid("D repeat at S2", dict(tl.DONE, outcome="repeat", summary="Again."))
    def test_e_blocked(self): self.outcome_mid("E blocked at S2", dict(tl.DONE, outcome="blocked", blocked_by="plan", summary="Step impossible."))
    def test_f_revise(self): self.outcome_mid("F revise at S2", dict(tl.DONE, outcome="revise", summary="Plan wrong."))

if __name__ == "__main__":
    unittest.main(argv=["x"], exit=False, verbosity=1)
    for k in sorted(OUT): print(f"{k}:\n   " + "\n   ".join(OUT[k]))
