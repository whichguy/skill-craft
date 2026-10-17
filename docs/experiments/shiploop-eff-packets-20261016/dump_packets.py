"""Dump every offline packet of the node-fix-bug step case (inline and ask-agent routes; the whole render and the printed
head) as text files: dump_packets.py <checkout root> <output dir>.  Run it on the base and on the changed checkout, then
compare the two directories with packet_diff.py (lines) and packet_sizes.py (characters)."""
import sys, json
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2])
sys.path.insert(0, str(root / "test/shiploop_e2e")); sys.path.insert(0, str(root / "skills/shiploop/scripts"))
import packets
case = json.loads((root / "test/shiploop_e2e/step_cases.json").read_text())["node-fix-bug"]
for deleg in ("inline", "ask-agent"):
    for kind, printed in (("full", False), ("printed", True)):
        d = out / deleg / kind; d.mkdir(parents=True, exist_ok=True)
        for key, text in packets.offline_packets(case, deleg, printed=printed).items():
            (d / (key + ".txt")).write_text(text)
