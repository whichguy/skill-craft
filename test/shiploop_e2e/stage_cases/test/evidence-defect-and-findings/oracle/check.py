#!/usr/bin/env python3
"""Verify evidence-driven test assertions: tests/sub-cases + added_tests and structured test_findings."""
import json
import os
import sys
from pathlib import Path

ROOT = Path.cwd()


def fail(msg):
    raise SystemExit(msg)


def load_result():
    raw = json.loads(Path(os.environ["STAGE_RESULT"]).read_text())
    return raw.get("result", raw) if isinstance(raw, dict) else raw


def check_tests():
    body = (ROOT / "test/paginate.test.js").read_text()
    if "TC-1" not in body or "TC-1 (a)" not in body:
        fail("test/paginate.test.js must contain both TC-1 and sub-case TC-1 (a)")
    res = load_result()
    added = res.get("added_tests") or []
    if not any(isinstance(r, dict) and r.get("id") == "TC-1 (a)" and r.get("command") for r in added):
        fail("result.added_tests must register newly added sub-case TC-1 (a)")


def check_findings():
    res = load_result()
    findings = res.get("test_findings")
    if not isinstance(findings, list) or not findings:
        fail("result.test_findings must record discovered evidence findings")
    for row in findings:
        if not isinstance(row, dict) or row.get("impact") not in {"none", "local", "amend-remaining", "system-test"}:
            fail("each test_findings entry must specify a valid impact tier")
        if not str(row.get("finding") or "").strip() or not str(row.get("next_step") or "").strip():
            fail("each test_findings entry must name finding and next_step")


mode = sys.argv[1] if len(sys.argv) == 2 else ""
if mode not in {"tests", "findings"}:
    fail("usage: check.py tests|findings")
{"tests": check_tests, "findings": check_findings}[mode]()
