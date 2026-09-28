"""E5: can a hand-written terminal packet (no runtime run) pass static-checks and test-green?"""
import json, re, unittest
from fixture import *
import shiploop_quality as quality
OUT = {}
def forge(contract, receipt):
    """What a model could write from the contract file ShipLoop printed, without running the loop."""
    prog = sorted(quality._PROGRESS_KEYS, key=len)[-1]
    progress = {k: (1 if k in ("action_number", "trivial_streak") else True if k == "unchanged_first_pass" else contract["required_trivial_reviews"]) for k in prog}
    progress["required_trivial_reviews"] = contract["required_trivial_reviews"]
    packet = {k: None for k in quality._PACKET_KEYS}
    packet.update(status="complete", state_file="/nonexistent/innerloop-forged.json", workspace=contract["workspace"],
                  work=contract["work"], conditions={"exit": contract["exit_condition"], "repeat": contract["repeat_condition"]},
                  progress=progress, context=contract["context"], receipt=str(receipt),
                  last_report=dict(tl.TRIVIAL), status_semantics={}, instruction="done")
    return packet

class E5(tl.TestLoopTests):
    def attempt(self, label, contract_rel, terminal):
        contract = json.loads((self.run_dir / contract_rel).read_text())
        terminal.parent.mkdir(parents=True, exist_ok=True)
        terminal.write_text(json.dumps(forge(contract, terminal)))
        try:
            self.complete(dict(tl.DONE, evidence_refs=[str(terminal)])); OUT[label] = "ACCEPTED (forgery passed)"
        except nav.NavigatorError as e:
            OUT[label] = "refused: " + re.sub(r"/\S+", "<p>", " ".join(str(e).split()))[:220]

    def test_static_checks(self):
        self.start(); self.drive_to("static-checks")
        a = self.action()
        self.attempt("static-checks (quality loop)", quality.contract_path(a), self.run_dir / quality.terminal_path(a))

    def test_test_green(self):
        self.start(); self.drive_to("test-green")
        (self.repo / "fixed.txt").write_text("fixed\n")   # commands really pass; only the loop is skipped
        a = self.action()
        self.attempt("test-green (test loop, commands pass)", test_loop.contract_path(a), self.run_dir / test_loop.terminal_path(a))

if __name__ == "__main__":
    print("PACKET_KEYS", sorted(quality._PACKET_KEYS)); print("PROGRESS_KEYS", [sorted(x) for x in quality._PROGRESS_KEYS])
    unittest.main(argv=["x"], exit=False, verbosity=0)
    for k, v in OUT.items(): print(k, "->", v)
