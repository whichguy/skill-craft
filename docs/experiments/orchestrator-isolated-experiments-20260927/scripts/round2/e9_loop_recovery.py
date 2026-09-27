"""E9: context lost inside a test loop.  Can a fresh session, given only `shiploop next`, continue?"""
import json, re, shlex, subprocess, sys, unittest
from pathlib import Path
from fixture import *
CLI = SRC / "skills/shiploop/scripts/shiploop"
OUT = {}
def cli_next(run):
    return subprocess.run([sys.executable, str(CLI), "next", "--run-dir", str(run)], capture_output=True, text=True).stdout

class E9(tl.TestLoopTests):
    def full_packet(self):
        head = cli_next(self.run_dir)
        m = re.search(r"Full packet: (\S+)", head)
        return head, (Path(m.group(1)).read_text() if m else "")

    def test_a_mid_loop(self):
        self.start(); self.drive_to("test-green")
        start = next(l for l in self.packet().splitlines() if l.startswith("Start: "))
        words = shlex.split(start[len("Start: "):])
        first = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True, capture_output=True, check=True).stdout)
        state_file, receipt = first["state_file"], first["receipt"]
        # --- context lost here: the session knows nothing but the recovery command ---
        head, full = self.full_packet()
        row = {"state_file_named_in_packet": state_file in head + full,
               "receipt_named_in_packet": receipt in head + full,
               "receipt_holds_active_packet_with_done_argv": bool(json.loads(Path(receipt).read_text()).get("done_argv"))}
        lines = [l for l in (head + full).splitlines() if receipt in l or "in progress" in l.lower() or "already started" in l.lower()]
        row["packet_lines_about_running_loop"] = [re.sub(r"/\S+", "<p>", l)[:160] for l in lines[:4]]
        # Does re-running the printed Start create a second, parallel loop?
        again = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True, capture_output=True).stdout or "{}")
        row["restart_creates_new_state_file"] = again.get("state_file") not in (None, state_file)
        row["first_state_file_still_exists"] = Path(state_file).exists()
        OUT["A context lost mid test-green loop"] = row

    def test_b_after_loop_before_complete(self):
        self.start(); self.drive_to("test-green")
        (self.repo / "fixed.txt").write_text("fixed\n"); (self.repo / "retained.txt").write_text("r\n")
        self.run_loop([tl.TRIVIAL])     # terminal written to the receipt by the runtime
        # --- context lost here ---
        head, full = self.full_packet()
        term = str(self.terminal())
        row = {"terminal_path_named": term in head + full}
        try:
            self.complete(dict(tl.DONE, evidence_refs=[term])); row["complete_from_recovered_packet"] = "accepted"
        except nav.NavigatorError as e:
            row["complete_from_recovered_packet"] = "REFUSED " + " ".join(str(e).split())[:150]
        OUT["B context lost after loop done, before complete"] = row

if __name__ == "__main__":
    unittest.main(argv=["x", "E9"], exit=False, verbosity=0)
    for k, v in OUT.items(): print(f"\n## {k}"); [print(f"   {a}: {b}") for a, b in v.items()]
