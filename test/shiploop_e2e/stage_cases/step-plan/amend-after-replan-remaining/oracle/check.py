#!/usr/bin/env python3
"""Verify step-plan amendment output after document emits replan_remaining."""
import json
import os
import re
import sys
from pathlib import Path

SCENARIO_S1 = {
    "id": "S1",
    "task": "Fix paginate() with Math.ceil (C1).",
    "deps": [],
    "criteria": ["C1"],
    "paths": ["src/paginate.js"],
    "proof": 'node -e \'const {paginate}=require("./src/paginate");if(paginate([1,2,3,4,5],3,2).pages!==3)process.exit(1)\'',
    "skills": [],
}
QUERY_RE = re.compile(r"\b(query|params?|searchparams)\b", re.I)
PARSE_GUARD_RE = re.compile(r"\b(parse|validat\w*|integer|int|rangeerror|400|nan|positive)\b", re.I)


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def load_result() -> dict:
    raw = json.loads(Path(os.environ["STAGE_RESULT"]).read_text(encoding="utf-8"))
    return raw.get("result", raw) if isinstance(raw, dict) else raw


def check_fidelity() -> None:
    res = load_result()
    if res.get("outcome") != "done":
        fail(f"outcome must be done, got {res.get('outcome')!r}")
    steps = res.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        fail("steps must preserve committed S1 plus remaining pending step(s)")
    orig_s1 = SCENARIO_S1
    first = steps[0]
    if not isinstance(first, dict) or first.get("done") is not True:
        fail("steps[0] must be S1 marked done: true")
    for key in ("id", "task", "deps", "criteria", "paths", "proof", "skills"):
        if first.get(key) != orig_s1.get(key):
            fail(f"steps[0].{key} changed on committed step S1: {first.get(key)!r} != {orig_s1.get(key)!r}")
    extra_done = [s.get("id") for s in steps[1:] if isinstance(s, dict) and s.get("done") is True]
    if extra_done:
        fail(f"remaining steps must stay pending (done omitted/false), got done on {extra_done!r}")


def check_amendment() -> None:
    res = load_result()
    if res.get("outcome") != "done":
        fail(f"outcome must be done, got {res.get('outcome')!r}")
    steps = res.get("steps") or []
    pending = [s for s in steps if isinstance(s, dict) and s.get("done") is not True]
    if not pending:
        fail("amended plan must retain at least one pending step for S2 /items")
    parts: list[str] = []
    for step in pending:
        parts.append(str(step.get("task") or ""))
        parts.append(str(step.get("proof") or ""))
    for crit in res.get("criteria") or ():
        if isinstance(crit, dict) and crit.get("id") != "C1":
            parts.append(str(crit.get("text") or ""))
    blob = "\n".join(parts)
    if not (QUERY_RE.search(blob) and PARSE_GUARD_RE.search(blob)):
        fail("amended pending steps/criteria must incorporate TF1 string query-parameter parsing and positive integer validation")


mode = sys.argv[1] if len(sys.argv) == 2 else ""
if mode not in {"fidelity", "amendment"}:
    fail("usage: check.py fidelity|amendment")
{"fidelity": check_fidelity, "amendment": check_amendment}[mode]()
