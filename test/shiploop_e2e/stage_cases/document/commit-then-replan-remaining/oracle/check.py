#!/usr/bin/env python3
"""Verify document stage output for commit-then-amend replan_remaining scenario."""
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


def check_docs():
    readme = (ROOT / "README.md").read_text().lower()
    if "paginate" not in readme or "partial" not in readme:
        fail("README.md must document partial-page pagination behavior")


def check_knowledge():
    k = load_result().get("knowledge")
    if not isinstance(k, dict) or set(k) != {"spec", "architecture", "environment"}:
        fail("knowledge must record spec, architecture, and environment")
    for name in ("spec", "architecture", "environment"):
        if not str(k.get(name) or "").strip():
            fail(f"knowledge.{name} must be nonempty")


def check_replan():
    rp = load_result().get("replan_remaining")
    if not isinstance(rp, dict) or not str(rp.get("reason") or "").strip():
        fail("replan_remaining must specify nonempty reason to re-sequence S2")
    affects = rp.get("affects")
    if not isinstance(affects, list) or "S2" not in affects:
        fail("replan_remaining.affects must name S2")


mode = sys.argv[1] if len(sys.argv) == 2 else ""
if mode not in {"docs", "knowledge", "replan"}:
    fail("usage: check.py docs|knowledge|replan")
{"docs": check_docs, "knowledge": check_knowledge, "replan": check_replan}[mode]()
