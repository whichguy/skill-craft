"""E2: can an Improve child revise its stage result yet close on one unchanged trivial pass?"""
import importlib.util, json, sys, unittest
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src"
spec = importlib.util.spec_from_file_location("aic", SRC / "test/shiploop-actual-improve-cli.test.py")
aic = importlib.util.module_from_spec(spec); sys.modules["aic"] = aic; spec.loader.exec_module(aic)
store, navigator = aic.store, aic.navigator
OUT = {}

class E2(aic.ImproveCliFixture):
    def run_case(self, label, revise, edit_repo=False):
        state = store.read_record(self.run / "state.md")
        stage = navigator.current_stage(state); self.action = navigator.current_action(state)["id"]
        g = lambda *a: aic.subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, env=self.environment)
        g("init", "-q"); g("-c", "user.email=e@x.invalid", "-c", "user.name=E", "add", "-A")
        g("-c", "user.email=e@x.invalid", "-c", "user.name=E", "commit", "-qm", "base")
        # setUp already completed spec with self.producer and bound its Improve child.
        _raw, first = self.start_ephemeral_child()
        if edit_repo:
            (self.repo / "product/contracts/cold-recovery.md").write_text("# Product contract\n\nEDITED BY REVIEW\n")
        _raw, term = self.done_ephemeral(first, self.child_report("trivial", "satisfied", "allowed", "one pass"))
        row = {"stage": stage, "runtime_status": term["status"], "unchanged_first_pass": term["progress"].get("unchanged_first_pass")}
        if term["status"] != "complete":
            OUT[label] = row; return
        evidence = aic.bridge.receipt_path(self.bound).parent / "reviews"; evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "r1.md").write_text("one review\n"); (evidence / "c.md").write_text("checks\n")
        receipt = {"summary": "One pass.", "review_refs": [str(evidence / "r1.md")], "check_refs": [str(evidence / "c.md")], "lessons": "x"}
        if revise:
            receipt["final_result"] = dict(self.producer, summary="REVISED by the review: the requirement set was rewritten.")
        store.write_record(self.completion_path, receipt)
        r = aic.subprocess.run([sys.executable, "-B", str(aic.CLI), "improve-complete", "--run-dir", str(self.run),
                                "--action", self.action, "--result", str(self.completion_path)], capture_output=True, text=True, env=self.environment, cwd=self.base)
        after = store.read_record(self.run / "state.md")
        row["improve_complete_rc"] = r.returncode
        row["msg"] = (" ".join((r.stderr or r.stdout).split()))[:200] if r.returncode else ""
        row["accepted_summary"] = after["accepted"].get(self.action, {}).get("summary")
        row["advanced_to"] = navigator.current_stage(after) if after["status"] == "active" else after["status"]
        OUT[label] = row

    def test_a_revised_result_one_pass(self): self.run_case("A revised result, no repo edit", revise=True)
    def test_b_unrevised_one_pass(self): self.run_case("B unrevised, no repo edit (control)", revise=False)
    def test_c_repo_edit_one_pass(self): self.run_case("C repo edit during pass (control)", revise=False, edit_repo=True)

if __name__ == "__main__":
    unittest.main(argv=["x"], exit=False, verbosity=1)
    for k, v in OUT.items(): print(k, "->", json.dumps(v))
