"""Scratch experiment: how the vendored Until Loop (read only import) decides complete for gate 0, 1 and 2.

Run: python3 docs/experiments/shiploop-fast-planning-20261004/gate_experiment.py
Writes only under a temporary directory it removes at the end; reads the vendored runtime in this repository.
"""
import importlib.util, json, os, subprocess, sys, tempfile, shutil
from pathlib import Path
RUNTIME = str(Path(__file__).resolve().parents[3] / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py")
spec = importlib.util.spec_from_file_location("ul", RUNTIME)
ul = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(ul)

SCRATCH = os.path.dirname(os.path.abspath(__file__))
base = tempfile.mkdtemp(prefix="gate-")

def repo():
    d = tempfile.mkdtemp(prefix="ws-", dir=base)
    subprocess.run(["git", "-C", d, "init", "-q"], check=True)
    subprocess.run(["git", "-C", d, "config", "user.email", "x@example.com"], check=True)
    subprocess.run(["git", "-C", d, "config", "user.name", "x"], check=True)
    open(os.path.join(d, "plan.json"), "w").write("{}\n")
    subprocess.run(["git", "-C", d, "add", "plan.json"], check=True)
    subprocess.run(["git", "-C", d, "commit", "-qm", "init"], check=True)
    return d

def contract(ws, gate, exit_text="exit"):
    return {"workspace": ws, "work": "one review", "exit_condition": exit_text, "repeat_condition": "repeat",
            "required_trivial_reviews": gate,
            "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e", "resources": []}}

def report(cls, exit_a, cont="allowed"):
    return {"classification": cls, "exit_assessment": exit_a, "continuation_assessment": cont,
            "evidence": "observed", "handoff": "h"}

def run(label, gate, steps, exit_text="exit"):
    """steps: list of (classification, exit_assessment, change_tree_before_report)"""
    ws = repo()
    packet = ul.start(contract(ws, gate, exit_text), directory=base)
    path = packet["state_file"]
    trace = []
    for n, (cls, ex, change) in enumerate(steps, 1):
        if change:
            open(os.path.join(ws, f"edit{n}.txt"), "w").write("changed\n")
        action = f"{packet['state_file'] and ''}"
        # the action token is run id + action number; read it from done_argv
        token = [a for a in packet["done_argv"] if a.startswith("--action=")][0].split("=", 1)[1]
        try:
            packet = ul.done(path, token, report(cls, ex))
        except ul.StateError as error:
            trace.append(f"pass {n}: REFUSED {error}")
            break
        trace.append(f"pass {n}: {cls}/{ex}{' +edit' if change else ''} -> {packet['status']} streak={packet['progress']['trivial_streak']}"
                     + (" unchanged_first_pass" if packet['progress'].get('unchanged_first_pass') else ""))
        if packet["status"] != "active":
            break
    print(f"[{label}] gate={gate}")
    for t in trace:
        print("   ", t)
    return packet["status"]

# gate 2: today's Improve
run("improve today, first pass trivial and tree unchanged", 2, [("trivial", "satisfied", False)])
run("improve today, first pass trivial but edited (tree changed)", 2, [("trivial", "satisfied", True), ("trivial", "satisfied", False), ("trivial", "satisfied", False)])
run("improve today, first pass non-trivial (changed), then two trivial", 2, [("non-trivial", "unsatisfied", True), ("trivial", "unsatisfied", False), ("trivial", "satisfied", False)])
run("improve today, test-strategy shape: non-trivial but exit satisfied on pass 1", 2, [("non-trivial", "satisfied", True), ("trivial", "satisfied", False), ("trivial", "satisfied", False)])
# gate 1: test and quality loops
run("gate 1, first pass trivial", 1, [("trivial", "satisfied", False)])
run("gate 1, first pass non-trivial changes candidate", 1, [("non-trivial", "satisfied", True), ("trivial", "satisfied", False)])
# gate 0: generic default of the runtime
run("gate 0, first pass non-trivial changes candidate, exit satisfied", 0, [("non-trivial", "satisfied", True)])
run("gate 0, first pass non-trivial, exit unsatisfied (model reads 'two consecutive' text)", 0, [("non-trivial", "unsatisfied", True), ("trivial", "satisfied", False)])
run("gate 0, first pass unresolved/unsatisfied", 0, [("unresolved", "unsatisfied", False), ("trivial", "satisfied", False)])
# invalid combinations the runtime refuses
run("gate 0, unresolved + satisfied", 0, [("unresolved", "satisfied", False)])
shutil.rmtree(base)
