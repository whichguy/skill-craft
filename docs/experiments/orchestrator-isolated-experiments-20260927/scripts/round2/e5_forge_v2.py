"""X1 (adapted e5_forge.py): can a hand-written terminal packet (no runtime run) pass the verify and test stages?
Changes vs original: _PACKET_KEYS/_PROGRESS_KEYS/contract_path/terminal_path now live in shiploop_loops; static-checks'
quality loop became verify's loop and test-green became the test stage (8 inner stages, 2026-10-10); the forged packet
fills the Until Loop 0.8.0+ keys (exit_checks, last_check_results, check_repairs, verify_script)."""
import json, re, unittest
from fixture import *
import shiploop_loops as loops
OUT = {}
def forge(contract, receipt):
    prog = sorted(loops._PROGRESS_KEYS, key=len)[-1]
    progress = {k: (1 if k in ("action_number", "trivial_streak") else True if k == "unchanged_first_pass" else contract["required_trivial_reviews"]) for k in prog}
    progress["required_trivial_reviews"] = contract["required_trivial_reviews"]
    packet = {k: None for k in loops._PACKET_KEYS}
    packet.update(status="complete", state_file="/nonexistent/innerloop-forged.json", workspace=contract["workspace"],
                  work=contract["work"], conditions={"exit": contract["exit_condition"], "repeat": contract["repeat_condition"]},
                  progress=progress, context=contract["context"], receipt=str(receipt),
                  last_report=dict(tl.TRIVIAL), status_semantics={}, instruction="done",
                  exit_checks=[], check_repairs=[])
    return packet

class E5(tl.TestLoopTests):
    def attempt(self, label, stage):
        a = self.action()
        contract = json.loads((self.run_dir / loops.contract_path(a)).read_text())
        terminal = self.run_dir / loops.terminal_path(a)
        terminal.parent.mkdir(parents=True, exist_ok=True)
        terminal.write_text(json.dumps(forge(contract, terminal)))
        try:
            self.complete(dict(tl.DONE, evidence_refs=[str(terminal)]), loop=False)
            st = self.settle()
            OUT[label] = "ACCEPTED (forgery passed); now at " + str(nav.current_stage(st))
        except nav.NavigatorError as e:
            OUT[label] = "refused: " + re.sub(r"/\S+", "<p>", " ".join(str(e).split()))[:300]

    def test_verify(self):
        self.start(); self.drive_to("verify")
        self.attempt("verify (quality review loop; ex static-checks)", "verify")

    def test_test(self):
        self.start(); self.drive_to("test")
        (self.repo / "fixed.txt").write_text("fixed\n"); (self.repo / "retained.txt").write_text("retained\n")
        self.attempt("test (test loop, commands pass; ex test-green)", "test")

    def test_test_commands_fail(self):
        self.start(); self.drive_to("test")
        self.attempt("test control: forged, commands fail", "test")

if __name__ == "__main__":
    print("PACKET_KEYS", sorted(loops._PACKET_KEYS))
    unittest.main(argv=["x"], exit=False, verbosity=0)
    for k, v in OUT.items(): print(k, "->", v)
