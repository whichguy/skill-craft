"""usage: measure_heads.py <worktree> [run_dir_length ...] -> JSON {run_dir_length: {route: {stage: {head, whole, mode}}}}
For each run-dir length the offline walk runs inside shiploop_head_budget.reference_tmpdir(length); lengths are normalised to the
reference install (root 63, CLI 96).  head = navigator.packet_head of the stage's state (built for every stage, also those that
print whole), whole = navigator.render, mode = what the walk printed (whole fits PRINT_LIMIT).  Scratch only."""
import json, sys
from pathlib import Path
wt = Path(sys.argv[1]).resolve()
lengths = [int(a) for a in sys.argv[2:]] or [83]
sys.dont_write_bytecode = True
sys.path.insert(0, str(wt / "skills/shiploop/scripts")); sys.path.insert(0, str(wt / "test/shiploop_e2e")); sys.path.insert(0, str(wt / "test"))
import packets
import shiploop_navigator as navigator
import shiploop_head_budget as hb
cases = json.loads((wt / "test/shiploop_e2e/step_cases.json").read_text())
pairs = {}
original = navigator.render
def render(core, run_dir, state):
    text = original(core, run_dir, state)
    if state["status"] == "active":
        pairs[id(text)] = navigator.packet_head(core, run_dir, state, Path(run_dir) / "packets" / "packet.md")
    return text
navigator.render = render
out = {}
for length in lengths:
    out[length] = {}
    with hb.reference_tmpdir(length):
        for route in ("inline", "ask-agent"):
            pairs.clear()
            wholes = packets.offline_packets(cases["node-fix-bug"], delegation=route, printed=False)
            out[length][route] = {key.split("-", 1)[1]: {
                "head": hb.at_reference_install(pairs[id(whole)], wt, length), "whole": hb.at_reference_install(whole, wt, length),
                "mode": hb.mode_of(whole, navigator.PRINT_LIMIT), "raw_head": len(pairs[id(whole)]), "raw_whole": len(whole)}
                for key, whole in wholes.items() if not key.endswith("-improve")}
print(json.dumps(out, indent=1))
