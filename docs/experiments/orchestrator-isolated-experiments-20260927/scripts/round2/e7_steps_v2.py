"""E7: per-step implement under a revised plan, repeat, blocked and revise."""
import re, unittest
from fixture import *
OUT = {}
STEPS3 = [{"id": f"S{i}", "task": f"Do part {i}."} for i in (1, 2, 3)]
def plan(steps):
    # adapted 2026-10-25: _check_step_sizing now needs criteria + proof per step (paths must be the item's)
    steps = [dict(st, criteria=["C1"], proof="true", paths=["a.py"]) for st in steps]
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
            if self.state().get("active_improve"): self.finish_improve(); seq.append("(Improve)"); continue
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
        seq = [self.step_line()]; self.complete(dict(tl.DONE))
        while self.state().get("active_improve"): self.finish_improve(); seq.append("(Improve)")
        seq.append(self.step_line())
        try:
            self.complete(result); seq.append(f"after {result['outcome']}: status={self.state()['status']} stage={nav.current_stage(self.state())} improve={bool(self.state().get('active_improve'))} {self.step_line() if nav.current_stage(self.state())=='implement' else ''}")
        except nav.NavigatorError as e:
            seq.append("REFUSED " + " ".join(str(e).split())[:150])
        st = self.state()
        if st["status"] == "blocked":
            # adapted: resume a service wait with the check's output, then walk the rest of the plan
            nav.save(self.run_dir, nav.control(st, "resume", observed="true exited 0"))
            seq.append(f"resumed: stage={nav.current_stage(self.state())} {self.step_line()}")
            self.walk_implement("_tmp"); seq += OUT.pop("_tmp"); OUT[label] = seq; return
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
    # adapted 2026-10-25: implement accepts only done, blocked, send-back; blocked says what it awaits
    def test_g_blocked_service_then_resume(self): self.outcome_mid("G blocked (awaiting service) at S2, resume", dict(tl.DONE, outcome="blocked", awaiting=tl.SERVICE_WAIT, summary="Service down."))
    def test_h_send_back(self): self.outcome_mid("H send-back at S2", dict(tl.DONE, outcome="send-back", summary="Plan wrong."))
    def test_f_revise(self): self.outcome_mid("F revise at S2", dict(tl.DONE, outcome="revise", summary="Plan wrong."))

if __name__ == "__main__":
    unittest.main(argv=["x"] + ["E7." + n for n in sorted(vars(E7)) if n.startswith("test_")], exit=False, verbosity=1)
    for k in sorted(OUT): print(f"{k}:\n   " + "\n   ".join(OUT[k]))
