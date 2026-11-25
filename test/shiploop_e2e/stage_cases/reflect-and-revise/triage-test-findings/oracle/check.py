#!/usr/bin/env python3
"""Verify reflect-and-revise carries system-test findings and not-exercisable mutants to outer stages."""
import json
import os
import re
import sys
from pathlib import Path

OUTER_TEST_STAGES = {"system-test-author", "system-test"}
SKILL_DECISIONS = {"none", "reuse", "update", "create"}


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def load_result() -> dict:
    raw = json.loads(Path(os.environ["STAGE_RESULT"]).read_text(encoding="utf-8"))
    return raw.get("result", raw) if isinstance(raw, dict) else raw


def check_assumptions() -> None:
    res = load_result()
    if res.get("outcome") != "done":
        fail(f"outcome must be done, got {res.get('outcome')!r}")
    rows = res.get("assumptions")
    if not isinstance(rows, list) or not rows:
        fail("assumptions must carry TF-SYS-1 and src/server.js:18:3 as open outer items")
    open_outer = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if (
            row.get("disposition") == "open"
            and row.get("due_stage") in OUTER_TEST_STAGES
            and str(row.get("settle") or "").strip()
            and str(row.get("reason") or "").strip()
        ):
            open_outer.append(json.dumps(row, sort_keys=True).lower())
    if not open_outer:
        fail("assumptions must include at least one valid open entry due at system-test-author or system-test")
    combined = "\n".join(open_outer)
    has_finding = "tf-sys-1" in combined or ("http" in combined and "paginat" in combined)
    has_mutant = "src/server.js:18:3" in combined or (
        "server.js" in combined and bool(re.search(r"not[- ]exercisable|mutant|listener|port", combined))
    )
    if not has_finding:
        fail("open outer assumptions must carry TF-SYS-1 (HTTP server pagination integration)")
    if not has_mutant:
        fail("open outer assumptions must carry not-exercisable mutant src/server.js:18:3")


def check_skill() -> None:
    res = load_result()
    if res.get("outcome") != "done":
        fail(f"outcome must be done, got {res.get('outcome')!r}")
    skill = res.get("skill")
    if not isinstance(skill, dict) or skill.get("decision") not in SKILL_DECISIONS:
        fail(f"skill must have decision in {sorted(SKILL_DECISIONS)}, got {skill!r}")
    if not str(skill.get("reason") or "").strip():
        fail("skill.reason must be a non-empty string")


mode = sys.argv[1] if len(sys.argv) == 2 else ""
if mode not in {"assumptions", "skill"}:
    fail("usage: check.py assumptions|skill")
{"assumptions": check_assumptions, "skill": check_skill}[mode]()
