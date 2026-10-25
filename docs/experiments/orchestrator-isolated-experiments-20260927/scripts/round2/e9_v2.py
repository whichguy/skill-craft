"""X10 (adapted e9_loop_recovery.py): context lost inside the test loop; can a fresh session given only `shiploop next`
continue?  Changes: test-green -> test; the start command is loops.start_command (no 'Start: ' line now); own tests only."""
import json, re, shlex, subprocess, sys, unittest
from pathlib import Path
from fixture import *
from own import run_own
import shiploop_loops as loops
CLI = SRC / "skills/shiploop/scripts/shiploop"
OUT = {}
def cli_next(run):
    r = subprocess.run([sys.executable, str(CLI), "next", "--run-dir", str(run)], capture_output=True, text=True)
    return r.stdout + r.stderr
class E9(tl.TestLoopTests):
    def full_packet(self):
        head = cli_next(self.run_dir)
        paths = re.findall(r"(/\S+/packets/\S+\.md)", head)
        full = Path(paths[0].rstrip(".,;:)")).read_text() if paths and Path(paths[0].rstrip(".,;:)")).is_file() else ""
        return head, full
    def test_a_mid_loop(self):
        self.start(); self.drive_to("test")
        cmd = loops.start_command(loops.runtime(self.state()), self.terminal(), self.run_dir / loops.contract_path(self.action()))
        words = shlex.split(cmd)
        first = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True, capture_output=True, check=True).stdout)
        state_file, receipt = first["state_file"], first["receipt"]
        head, full = self.full_packet()
        both = head + full
        row = {"receipt_named": receipt in both,
               "says_already_started": "already started" in both,
               "says_run_receipt_next_argv": "run its next_argv" in both or "receipt's next_argv" in both,
               "start_command_still_printed": cmd in both}
        row["lines"] = [re.sub(r"/\S+", "<p>", l)[:200] for l in both.splitlines() if "already started" in l or "next_argv" in l][:3]
        again = subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True, capture_output=True)
        row["restart_rc"] = again.returncode
        row["restart_msg"] = short = " ".join((again.stderr or again.stdout).split())[:160]
        row["first_state_file_still_exists"] = Path(state_file).exists()
        # continue from the receipt's next_argv
        rec = json.loads(Path(receipt).read_text())
        nxt = json.loads(subprocess.run(rec["next_argv"], text=True, capture_output=True, check=True).stdout)
        (self.repo / "fixed.txt").write_text("fixed\n"); (self.repo / "retained.txt").write_text("r\n")
        fin = json.loads(subprocess.run(nxt["done_argv"], input=json.dumps(tl.TRIVIAL), text=True, capture_output=True, check=True).stdout)
        row["continued_loop_status"] = fin["status"]
        try:
            self.complete(dict(tl.DONE, evidence_refs=[receipt]), loop=False); row["complete_after_continue"] = "accepted"
        except nav.NavigatorError as e:
            row["complete_after_continue"] = "REFUSED " + " ".join(str(e).split())[:150]
        OUT["A context lost mid test loop"] = row
    def test_b_after_loop_before_complete(self):
        self.start(); self.drive_to("test")
        (self.repo / "fixed.txt").write_text("fixed\n"); (self.repo / "retained.txt").write_text("r\n")
        self.run_loop([tl.TRIVIAL])
        head, full = self.full_packet()
        term = str(self.terminal())
        row = {"terminal_path_named": term in head + full}
        try:
            self.complete(dict(tl.DONE, evidence_refs=[term]), loop=False); row["complete_from_recovered_packet"] = "accepted"
        except nav.NavigatorError as e:
            row["complete_from_recovered_packet"] = "REFUSED " + " ".join(str(e).split())[:150]
        OUT["B context lost after loop done, before complete"] = row
if __name__ == "__main__":
    run_own(E9)
    for k, v in OUT.items(): print(f"\n## {k}"); [print(f"   {a}: {b}") for a, b in v.items()]
