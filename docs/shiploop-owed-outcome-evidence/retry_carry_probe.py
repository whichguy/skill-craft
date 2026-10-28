"""Does an unmet iteration's gap and plan reach the next iteration's prompt?

The owner's "criteria not met" edge: report the gap and a plan, then loop back and execute it. Starts a real Until
Loop, reports one iteration as not done (gap in `evidence`, plan in `handoff`), then reads the next packet.

    python3 -I docs/shiploop-owed-outcome-evidence/retry_carry_probe.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
GAP = "GAP-MARKER: hello.txt is missing"
PLAN = "PLAN-MARKER: next iteration writes hello.txt with the word hello"

tmp = Path(tempfile.mkdtemp(prefix="retry-probe-"))
workspace, receipt = tmp / "ws", tmp / "receipt.json"
workspace.mkdir()
contract = {
    "workspace": str(workspace),
    "work": "Write hello.txt containing the word hello.",
    "exit_condition": "hello.txt exists and contains hello.",
    "repeat_condition": "Repeat while hello.txt is missing or wrong.",
    "required_trivial_reviews": 0,
    "context": {"request": "Probe: does the gap and plan carry forward?", "scope": "only ws/hello.txt",
                "authority": "write inside ws only", "environment": "plain shell", "resources": []},
}
start = subprocess.run([sys.executable, str(RUNTIME), "start", "--receipt", str(receipt)],
                       input=json.dumps(contract), capture_output=True, text=True, check=False)
assert start.returncode == 0, start.stderr
first = json.loads(receipt.read_text())
report = {"classification": "unresolved", "exit_assessment": "unsatisfied", "continuation_assessment": "allowed",
          "evidence": GAP, "handoff": PLAN}
done = subprocess.run(first["done_argv"], input=json.dumps(report), capture_output=True, text=True, check=False)
print("done exit:", done.returncode, "| stderr:", done.stderr.strip()[:200] or "none")
second = json.loads(receipt.read_text())
packet = json.dumps(second)
print("after the report: status", second["status"], "| progress", second["progress"])
print("gap carried into the next packet :", GAP in packet, "| in its instruction text:", GAP in second["instruction"])
print("plan carried into the next packet:", PLAN in packet, "| in its instruction text:", PLAN in second["instruction"])
print("last_report kept:", sorted((second.get("last_report") or {}).keys()))
print("next instruction opens:", second["instruction"][:160])
