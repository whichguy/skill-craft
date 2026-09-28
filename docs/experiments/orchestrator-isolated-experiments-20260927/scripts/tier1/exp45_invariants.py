"""Exp 4+5: refusals change nothing; next is idempotent; recovery `next` equals the packet complete printed.

Walks a whole one-item delivery with the snapshot's own fixture driver (real test loops, real
Until Loop), and at every new action probes the public CLI.
"""
import difflib, importlib.util, json, re, subprocess, sys, unittest
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "src"
spec = importlib.util.spec_from_file_location("tl", SRC / "test/shiploop-test-loop.test.py")
tl = importlib.util.module_from_spec(spec); sys.modules["tl"] = tl; spec.loader.exec_module(tl)
nav, store = tl.nav, tl.store
CLI = SRC / "skills/shiploop/scripts/shiploop"
LOG = []

def cli(*a):
    p = subprocess.run([sys.executable, str(CLI), *a], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

class Walk(tl.TestLoopTests):
    prev_action = None
    def complete(self, result):
        out = super().complete(result)
        self.probe(out)
        return out

    def finish_improve(self):
        super().finish_improve()
        self.probe(None)

    def probe(self, printed):
        st = self.state(); run = str(self.run_dir)
        if st["status"] != "active": return
        cur = nav.current_action(st)["id"]; stage = nav.current_stage(st)
        pfile = nav.packet_path(self.run_dir, st)
        before_state = (self.run_dir / "state.md").read_bytes()
        p_after_complete = pfile.read_text() if pfile.exists() else None
        row = {"stage": stage, "action": cur[-10:], "rev": st["revision"], "improve": bool(st.get("active_improve"))}
        # 5: recovery equals what complete printed / wrote
        rc1, h1, e1 = cli("next", "--run-dir", run)
        p1 = pfile.read_text() if pfile.exists() else None
        rc2, h2, e2 = cli("next", "--run-dir", run)
        p2 = pfile.read_text() if pfile.exists() else None
        row["next_rc"] = rc1
        row["next_idempotent"] = (h1 == h2 and p1 == p2 and (self.run_dir / "state.md").read_bytes() == before_state)
        row["file_same_as_complete"] = (p_after_complete == p1) if p_after_complete is not None else "no-file"
        if printed is not None and printed.strip():
            row["head_same_as_complete"] = printed.strip() == h1.strip()
            if not row["head_same_as_complete"]:
                row["head_diff"] = [l for l in difflib.unified_diff(printed.splitlines(), h1.splitlines(), lineterm="", n=0)
                                    if l[:1] in "+-" and not l.startswith(("+++", "---"))][:6]
        else:
            row["head_same_as_complete"] = "n/a (no complete output)"
        if p_after_complete is not None and p1 is not None and p_after_complete != p1:
            row["file_diff"] = [l for l in difflib.unified_diff(p_after_complete.splitlines(), p1.splitlines(), lineterm="", n=0)
                                if l[:1] in "+-" and not l.startswith(("+++", "---"))][:6]
        # 4: refusals leave state unchanged
        refusals = {}
        inbox = self.run_dir / "inbox"; inbox.mkdir(exist_ok=True)
        bad = inbox / "exp-bad.md"; bad.write_text(store.dumps({"outcome": "bogus", "summary": "x"}, "result"))
        good = inbox / "exp-good.md"; good.write_text(store.dumps({"outcome": "done", "summary": "x"}, "result"))
        probes = {"bogus_outcome": ("complete", "--action", cur, "--result", str(bad)),
                  "missing_file": ("complete", "--action", cur, "--result", str(inbox / "nope.md")),
                  "stale_action": ("complete", "--action", self.prev_action or "nav-000-stale", "--result", str(good)),
                  "wrong_verb": ("improve-complete", "--action", cur, "--result", str(good))}
        if st.get("active_improve"):
            probes.pop("wrong_verb")
        for name, argv in probes.items():
            s0 = (self.run_dir / "state.md").read_bytes()
            rc, o, e = cli(argv[0], "--run-dir", run, *argv[1:])
            changed = (self.run_dir / "state.md").read_bytes() != s0
            refusals[name] = ("rc=%d" % rc) + (" STATE-CHANGED" if changed else "")
            if changed:
                self.fail(f"{name} changed state at {stage}: rc={rc} {o[-200:]} {e[-200:]}")
        row["refusals"] = refusals
        LOG.append(row); self.prev_action = cur

    def test_walk(self):
        self.start(); self.drive_to("handoff")

if __name__ == "__main__":
    r = unittest.main(argv=["x", "Walk.test_walk"], exit=False, verbosity=1)
    out = Path(__file__).with_suffix(".jsonl"); out.write_text("\n".join(json.dumps(x) for x in LOG) + "\n")
    print(len(LOG), "actions probed ->", out)
