"""Where does a verify packet tell the model to run its callback?

Renders the delivery scenario with the real navigator (graph-dry-run; no model, no Git), cuts out the W1 verify
packet and reports each mention of the callback as a percentage of the packet, plus where each block starts.

    python3 -I docs/shiploop-owed-outcome-evidence/packet_position.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "skills/shiploop/scripts/shiploop"

out = subprocess.run([sys.executable, str(CLI), "graph-dry-run", "--scenario", "delivery", "--format", "markdown"],
                     capture_output=True, text=True, check=True).stdout
sections = re.split(r"(?m)^## \d+\. ", out)
packet = next(s for s in sections if s.startswith("W1: verify ->"))
packet = packet.split("\n", 1)[1].strip("\n")
size = len(packet)
print("verify packet characters:", size, "(whole print limit 16,000; head limit 20,000)")
mentions = [round(100 * m.start() / size) for m in re.finditer(r"(?i)\bcallback\b", packet)]
print("callback mentions:", len(mentions), "at % of packet:", mentions)
for name, key in [("callback line", "Callback for this stage"), ("goal", "Goal: "),
                  ("Until Loop block", "Until Loop (no iteration"), ("narrative", "=== ShipLoop narrative"),
                  ("stage guidance", "Current stage guidance"), ("rules", "RULES ("),
                  ("result template", "Result template:"), ("references", "References (symbols"),
                  ("recovery command", "Recovery command ("), ("last accepted", "Last accepted transition")]:
    at = packet.find(key)
    print(f"  {name:18s} starts at {round(100 * at / size):3d}%" if at >= 0 else f"  {name:18s} not found")
print("last line:", packet.rstrip().splitlines()[-1][:100])
