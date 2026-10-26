#!/usr/bin/env python3
"""E3: after a send-back about RED, is the redone focused command behavioural, or guarded by a file-existence check?

    python3 test/shiploop_e2e/evaluators/e3_red.py score <sample>
    python3 test/shiploop_e2e/evaluators/e3_red.py verify

From the records only:
- ``guarded``: the latest step plan's focused commands hold a file-existence guard or a print-only path
  (test -f/-e, [ -f ], ls, stat, an existsSync call, or a printf/echo of a path) ahead of the tests;
- ``base``: the test gate's first base run of a focused command: did it fail (exit not 0), and does its output name a
  behaviour (a failing test line, an assertion, or an error raised while loading the code the item adds) rather than
  only printing a path? A new module's tests fail to load on the base: that is a real failure, so it counts.
``value`` is 1 when no focused command is guarded and the first base run failed behaviourally; 0 otherwise; None when the
sample reached no step plan. ``verify``: run 4's W3 focused command is ``guarded`` and its base output (a printed path) is
not behavioural; a clean command with a failing-assertion output is ``behavioural``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

_GUARD = re.compile(r"(^|&&|\|\||;|\(|\bif|\bthen)\s*!?\s*(test\s+(!\s+)?-[efsd]\s|\[\[?\s+(!\s+)?-[efsd]\s|ls\s|stat\s|"
                    r"printf\s+'%s\\n'\s|echo\s+\S+\.\w+\s*(&&|;|$))|existsSync\(")
_BEHAVIOUR = re.compile(r"(not ok\b|✖|\bFAIL(ED)?\b|AssertionError|Error \[ERR_ASSERTION\]|expected\b.*\bactual|"
                        r"\b\w*Error\b|cannot find module)", re.I)
_PATH_ONLY = re.compile(r"^\s*\S+\.\w+\s*$")


def guarded(command: str) -> bool:
    return bool(_GUARD.search(command))


def behavioural(run: dict) -> bool:
    """A base run that failed because a behaviour was missing: a non-zero exit with a failing test or assertion line."""
    if run.get("exit") in (0, None):
        return False
    lines = [line for line in f"{run.get('stdout', '')}\n{run.get('stderr', '')}".splitlines() if line.strip()]
    meaningful = [line for line in lines if not _PATH_ONLY.match(line)]
    return any(_BEHAVIOUR.search(line) for line in meaningful)


def judge(step_plan: dict | None, bases: list[dict]) -> dict:
    if step_plan is None:
        return {"value": None, "why": "no step plan"}
    focused = [c.get("command", "") for c in step_plan.get("test_commands") or [] if c.get("suite") == "focused"]
    guards = [c for c in focused if guarded(c)]
    first = next((run for record in bases for run in record.get("runs") or [] if run.get("suite") == "focused"), None)
    base = None if first is None else {"exit": first.get("exit"), "status": first.get("status"),
                                       "behavioural": behavioural(first)}
    return {"value": int(not guards and bool(base and base["behavioural"])), "focused": focused, "guarded": guards,
            "base": base, "verdict": "guarded" if guards else "behavioural" if base and base["behavioural"] else
            "no-behavioural-base-failure"}


def score(sample: Path) -> dict:
    folder = common.run_dir(sample)
    plans = common.results(folder, "step-plan")
    return judge(plans[-1].get("result") if plans else None, common.base_runs(folder))


def verify() -> list[dict]:
    rows = []
    plan = common.read_block(common.RUN4 / "run" / "results" / f"{common.RUN4_STEP_PLAN}.md")
    base = common.read_block(common.RUN4 / "run" / "tests" / "nav-bda6e75df846451ebee2ff56aeaa2333-base1.md")
    if plan is None or base is None:
        rows.append({"record": "run 4", "ok": False, "why": f"run 4's records are not readable under {common.RUN4}"})
    else:
        found = judge(plan["result"], [base])
        rows.append({"record": "run 4 W3 focused command and base run", "expect": "guarded", "got": found,
                     "ok": found["verdict"] == "guarded" and found["value"] == 0 and not found["base"]["behavioural"]})
    # The first live smoke sample (E3 arm A, 2026-10-24): a guard that prints a fake load error when the file is absent.
    faked = {"test_commands": [{"command": "if test ! -f src/records.js; then echo 'Error: Cannot find module "
                                           "src/records.js'; exit 1; fi; node --test --test-name-pattern 'TC-1|TC-2'",
                                "suite": "focused"}]}
    found = judge(faked, [{"runs": [{"suite": "focused", "exit": 1, "stdout": "Error: Cannot find module src/records.js\n"}]}])
    rows.append({"record": "planted if-test guard with a faked load error", "expect": "guarded", "got": found,
                 "ok": found["verdict"] == "guarded" and found["value"] == 0})
    clean = {"test_commands": [{"command": "node --test --test-reporter=spec test/records.test.js", "suite": "focused"}]}
    run = {"suite": "focused", "exit": 1, "stdout": "✖ TC-1 parse reads every field (1.2ms)\n  AssertionError "
                                                    "[ERR_ASSERTION]: Expected values to be strictly deep-equal\n"}
    found = judge(clean, [{"runs": [run]}])
    rows.append({"record": "planted behavioural", "expect": "behavioural", "got": found,
                 "ok": found["verdict"] == "behavioural" and found["value"] == 1})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
