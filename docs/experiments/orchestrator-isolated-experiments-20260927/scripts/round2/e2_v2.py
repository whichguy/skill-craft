"""X3 (adapted e2_revised_onepass.py): can an Improve review revise its stage result yet close on one trivial pass?
Changes: the Improve child is started by ShipLoop at the producer's complete (bind_current/start_ephemeral_child);
the import is `shiploop complete --action <improve stage id> --notes ... --final-result ...` (completion_receipt),
not `improve-complete`; own tests only.  Case D: a non-trivial first pass (control: the loop must continue)."""
import importlib.util, json, sys, unittest
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src"; sys.path.insert(0, str(SRC / "test"))  # the driver expects its own dir on sys.path
spec = importlib.util.spec_from_file_location("aic", SRC / "test/shiploop-actual-improve-cli.test.py")
aic = importlib.util.module_from_spec(spec); sys.modules["aic"] = aic; spec.loader.exec_module(aic)
store, navigator = aic.store, aic.navigator
OUT = {}
class E2(aic.ImproveCliFixture):
    def run_case(self, label, revise, edit_repo=False, classification="trivial"):
        state = store.read_record(self.run / "state.md")
        stage = self.bound["stage"]
        g = lambda *a: aic.subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, env=self.environment)
        g("init", "-q"); g("-c", "user.email=e@x.invalid", "-c", "user.name=E", "add", "-A")
        g("-c", "user.email=e@x.invalid", "-c", "user.name=E", "commit", "-qm", "base")
        contract = self.child_contract()
        _raw, first = self.start_ephemeral_child()
        if edit_repo:
            (self.repo / "product/contracts/cold-recovery.md").write_text("# Product contract\n\nEDITED BY REVIEW\n")
        exit_a = "satisfied" if classification == "trivial" else "unsatisfied"
        _raw, term = self.done_ephemeral(first, self.child_report(classification, exit_a, "allowed", "one pass"))
        row = {"stage": stage, "child_required_trivial_reviews": contract["required_trivial_reviews"],
               "runtime_status_after_1_pass": term["status"],
               "unchanged_first_pass": term["progress"].get("unchanged_first_pass")}
        if term["status"] != "complete":
            OUT[label] = row; return
        seed = store.read_record(self.run / "state.md")["active_improve"]["seed_result"]
        final = dict(seed, summary="REVISED by the review: the requirement set was rewritten.") if revise else None
        flags, _ = self.completion_receipt(final_result=final)
        r = aic.subprocess.run([sys.executable, "-B", str(aic.CLI), "complete", "--run-dir", str(self.run),
                                "--action", self.improve, *flags], capture_output=True, text=True, env=self.environment, cwd=self.base)
        after = store.read_record(self.run / "state.md")
        row["import_rc"] = r.returncode
        row["msg"] = (" ".join((r.stderr or r.stdout).split()))[:220] if r.returncode else ""
        row["accepted_summary"] = (after["accepted"].get(self.action) or {}).get("summary")
        row["advanced_to"] = navigator.current_stage(after) if after["status"] == "active" else after["status"]
        OUT[label] = row
    def test_a(self): self.run_case("A revised result, no repo edit", revise=True)
    def test_b(self): self.run_case("B unrevised, no repo edit (control)", revise=False)
    def test_c(self): self.run_case("C repo edit during the one trivial pass", revise=False, edit_repo=True)
    def test_d(self): self.run_case("D non-trivial first pass (control)", revise=False, classification="non-trivial")
if __name__ == "__main__":
    suite = unittest.TestSuite(E2(n) for n in ("test_a", "test_b", "test_c", "test_d"))
    unittest.TextTestRunner(verbosity=1).run(suite)
    for k, v in OUT.items(): print(k, "->", json.dumps(v))
