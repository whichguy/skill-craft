"""Can the Until Loop runtime tell an iteration whose work is done from one not started?

Starts a real loop with --receipt in a temporary workspace, records the instruction, does the iteration's work
(writes the file) without calling done, then runs the receipt's read-only next_argv and compares.

    python3 -I docs/shiploop-owed-outcome-evidence/loop_next_probe.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"

tmp = Path(tempfile.mkdtemp(prefix="loop-probe-"))
workspace, receipt = tmp / "ws", tmp / "receipt.json"
workspace.mkdir()
contract = {
    "workspace": str(workspace),
    "work": "Write hello.txt containing the word hello.",
    "exit_condition": "hello.txt exists and contains hello.",
    "repeat_condition": "Repeat while hello.txt is missing or wrong; stop blocked only if the workspace is unwritable.",
    "required_trivial_reviews": 0,
    "context": {"request": "Probe: what does the runtime say on next?", "scope": "only ws/hello.txt",
                "authority": "write inside ws only", "environment": "plain shell", "resources": []},
}
start = subprocess.run([sys.executable, str(RUNTIME), "start", "--receipt", str(receipt)],
                       input=json.dumps(contract), capture_output=True, text=True, check=False)
assert start.returncode == 0, start.stderr
before = json.loads(receipt.read_text())
print("after start   : status", before["status"], "| progress", before["progress"],
      "| receipt keys", sorted(before))

(workspace / "hello.txt").write_text("hello\n")  # the iteration's work, with no done call
again = subprocess.run(before["next_argv"], capture_output=True, text=True, check=False)
after = json.loads(again.stdout)
print("after the work: status", after["status"], "| progress", after["progress"])
print("instruction identical before and after the work:", after["instruction"] == before["instruction"])
print("instruction opens:", before["instruction"][:120])
print("status_semantics.active:", before["status_semantics"]["active"])
