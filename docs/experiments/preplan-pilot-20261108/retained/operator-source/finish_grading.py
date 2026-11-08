"""Finish the already registered judgments, at most two Astra calls at once."""
from pathlib import Path
import json
import subprocess
import sys
import time

OP = Path(__file__).resolve().parent


def note(event, **fields):
    print(json.dumps({"event": event, "time": time.time(), **fields}), flush=True)


def wait_for(paths):
    while not all(path.exists() for path in paths):
        time.sleep(10)


def verify_judges(paths):
    for path in paths:
        record = json.loads(path.read_text())
        if record.get("exit") != 0 or not record.get("text") or record.get("outside") != [] or record.get("tool_items") != []:
            raise RuntimeError(f"Judge requires parent review; no automatic retry: {path}")


def invoke(script, args, log):
    note("start", script=script, arguments=args)
    with (OP / log).open("w") as output:
        result = subprocess.run([sys.executable, "-B", str(OP / script), *args], stdout=output, stderr=subprocess.STDOUT)
    note("complete", script=script, arguments=args, exit=result.returncode)
    if result.returncode:
        raise RuntimeError(f"Command requires parent review: {script}, {log}")


try:
    # These two already-running paired calls own the two Astra slots.
    prior = [OP / "pairs" / pair / "judge.json" for pair in ("evidence-1", "unavailable-1")]
    wait_for(prior)
    verify_judges(prior)
    for number, indices, pairs in (
        (3, range(9, 13), ["atomic-2", "unicode-1"]),
        (4, range(13, 17), ["unicode-2", "evidence-2"]),
    ):
        names = [f"sample-{i:02}" for i in indices]
        wait_for([OP / (name + "-complete.json") for name in names])
        invoke("grade.py", names, f"grade-cohort-{number}.log")
        verify_judges([OP / "graded" / name / "judge.json" for name in names])
        invoke("pair_judge.py", pairs, f"pair-cohort-{number}.log")
        verify_judges([OP / "pairs" / pair / "judge.json" for pair in pairs])
        invoke("analyze.py", [], "analysis-status.json")
        invoke("scope_audit.py", [], f"scope-cohort-{number}.log")
    invoke("closeout_audit.py", ["--require-complete"], "closeout-status.json")
    note("all_registered_judgments_complete")
except Exception as exc:
    note("needs_parent_review", error=str(exc))
    raise
