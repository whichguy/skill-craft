"""Probe for docs/local-validation-journal.md, Round 5 (F22): what the runner-environment route would do to the suites.

Round 5's F22 proposed `GIT_CONFIG_COUNT=1, GIT_CONFIG_KEY_0=maintenance.auto, GIT_CONFIG_VALUE_0=false` for every suite at
`run_suites.run_process`. That runner strips exactly those variables on purpose (`_GIT_CONTEXT_OVERRIDES`, commit 78594ebb), because
ask-agent's workspace guard refuses them. This runs the three suites that commit protected through `run_process` in two arms:
  stripped: the runner as it is (the baseline);
  env:      the proposed route, made by emptying the runner's Git-context strip list for the run and putting the three variables
            in the parent environment, so they reach the suite the way the proposal would have sent them.
Usage: python3 -I envroute_probe.py <checkout> <output dir>. It prints one JSON line per suite and arm, and keeps each log.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "test"))
import run_suites  # noqa: E402

SUITES = {
    "ask-agent-parallel": ["python3", "-B", "test/ask-agent-parallel.test.py"],
    "agent-harness-audit": ["python3", "-B", "test/experiments/agent_harness/test_audit.py"],
    "install-arbitrary-skill": ["bash", "test/install-arbitrary-skill.test.sh"],
}
PROPOSED = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "maintenance.auto", "GIT_CONFIG_VALUE_0": "false"}
SIGNS = re.compile(r"^(FAIL|ERROR)\b.*|.*refuses Git context environment overrides.*|^FAILED.*", re.M)


def arm(name: str) -> None:
    for key in PROPOSED:
        os.environ.pop(key, None)
    run_suites._INHERITED_OVERRIDES = run_suites._STATE_OVERRIDES + run_suites._GIT_CONTEXT_OVERRIDES
    if name == "env":
        run_suites._INHERITED_OVERRIDES = run_suites._STATE_OVERRIDES
        os.environ.update(PROPOSED)


for arm_name in ("stripped", "env"):
    arm(arm_name)
    for suite, argv in SUITES.items():
        done = run_suites.run_process(argv, cwd=ROOT, timeout_seconds=900)
        text = done.stdout + "\n" + done.stderr
        (OUT / f"{arm_name}-{suite}.log").write_text(text)
        signs = [m.group(0).strip()[:200] for m in SIGNS.finditer(text)]
        print(json.dumps({"arm": arm_name, "suite": suite, "status": done.status, "returncode": done.returncode,
                          "seconds": round(done.duration_seconds, 1), "error": done.error,
                          "first_signs": signs[:4]}), flush=True)
