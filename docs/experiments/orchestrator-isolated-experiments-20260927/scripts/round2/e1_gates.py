"""E1: at every stage, is a bare {outcome: done, summary} accepted?  If not, why, and what did it take?"""
import json, sys, unittest
from fixture import *
BARE = {"outcome": "done", "summary": "Bare done: nothing was done."}
ROWS = []

class Matrix(tl.TestLoopTests):
    def try_bare(self, stage):
        st = self.state(); before = (self.run_dir / "state.md").read_bytes()
        try:
            self.complete(dict(BARE))
        except nav.NavigatorError as exc:
            assert (self.run_dir / "state.md").read_bytes() == before
            return False, str(exc).splitlines()[0][:150]
        return True, ""

    def test_matrix(self):
        self.start()
        recorded = {"steps": [{"id": "S1", "task": "Make the planned change."}],
                    "test_commands": [dict(tl.COMMANDS[0], criteria=["C1"]), *tl.COMMANDS[1:]], "paths": ["a.py"],
                    "criteria": [{"id": "C1", "text": "The item's focused check passes."}]}
        seen = set()
        for _ in range(300):
            st = self.state()
            if st["status"] != "active": break
            if st.get("active_improve") is not None:
                self.finish_improve(); continue
            stage = nav.current_stage(st); act = nav.current_action(st)["id"]
            if act in seen:
                pass
            seen.add(act)
            ok, why = self.try_bare(stage)
            row = {"stage": stage, "bare_done": "ACCEPTED" if ok else "refused", "why": why, "needed": ""}
            ROWS.append(row)
            if ok: continue
            # advance the way the fixture does, recording what it took
            if stage in tl.knowledge_support.knowledge.CLOSES:
                tl.knowledge_support.write(st)
                ok2, why2 = self.try_bare(stage)
                if ok2: row["needed"] = "knowledge-home files present"; continue
            if stage == "step-plan":
                row["needed"] = "steps, test_commands, paths, criteria"; self.complete(dict(tl.DONE, **recorded))
            elif stage == "release-plan":
                row["needed"] = "consumer_entry, consumer_checks"
                self.complete(dict(tl.DONE, consumer_entry={"how": "run python3 a.py", "sources": ["a.py"]}, consumer_checks=[tl.COMMANDS[1]]))
            elif stage == "system-test-author":
                row["needed"] = "system_commands"; self.complete(dict(tl.DONE, system_commands=[tl.COMMANDS[1]]))
            elif stage in test_loop.STAGES:
                row["needed"] = "Until Loop terminal packet + script rerun of recorded commands"; self.pass_loop()
            elif stage == "static-checks":
                row["needed"] = "quality-loop terminal packet"
                self.run_quality_loop()
                self.complete(dict(tl.DONE, evidence_refs=[str(self.run_dir / "quality" / (self.action() + "-terminal.json"))]))
            elif stage == "plan":
                row["needed"] = "assumptions list"; self.complete(dict(BARE, assumptions=[]))
            else:
                row["needed"] = "(fixture DONE)"; self.complete(dict(tl.DONE))
        print("final status:", self.state()["status"], nav.current_stage(self.state()))

if __name__ == "__main__":
    unittest.main(argv=["x", "Matrix.test_matrix"], exit=False, verbosity=0)
    by = {}
    for r in ROWS: by.setdefault(r["stage"], r)
    spec = {s: stage_spec.stage(s) for s in by}
    out = []
    for s, r in by.items():
        dw = list(getattr(spec[s], "done_when", []) or [])
        out.append(dict(r, done_when_count=len(dw), done_when=dw))
        print(f"{s:22s} bare={r['bare_done']:9s} needed={r['needed'] or '-':45s} done_when={len(dw)}  {r['why'][:90]}")
    (Path(__file__).parent / "e1_gates.json").write_text(json.dumps(out, indent=1))
