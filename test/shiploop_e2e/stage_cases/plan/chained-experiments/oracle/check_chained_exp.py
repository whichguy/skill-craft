"""Deterministic oracle for plan/chained-experiments."""
import json
import os
import re
import sys
from pathlib import Path

V2_OR_CHUNK_RE = re.compile(r"export-v2-stream|20\b|chunk|4096", re.I)
MODE_JSONL_RE = re.compile(r"--mode\s+jsonl|mode\s*=\s*jsonl|jsonl", re.I)
BUFFER_RE = re.compile(r"4096|byte", re.I)


def fail(msg: str) -> None:
    raise SystemExit(msg)


def load_result() -> dict:
    path = os.environ.get("STAGE_RESULT")
    if not path:
        fail("STAGE_RESULT is not set")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("result must be a JSON object")
    return data


def check_p1(result: dict) -> None:
    assumptions = result.get("assumptions")
    if not isinstance(assumptions, list) or not assumptions:
        fail("assumptions must be a non-empty list")
    q1_rows = [row for row in assumptions if isinstance(row, dict) and row.get("question") == "Q1"]
    if not q1_rows or not any(row.get("disposition") == "probed" for row in q1_rows):
        fail("Q1 must be resolved via at least one probed assumption")
    probed = [row for row in assumptions if isinstance(row, dict) and row.get("disposition") == "probed"]
    for row in probed:
        if not isinstance(row.get("effect"), str) or not row["effect"].strip():
            fail(f"probed row {row.get('id')} must record effect")

    arch_path = Path("docs/shiploop/architecture.md")
    arch_text = arch_path.read_text(encoding="utf-8") if arch_path.is_file() else ""
    combined = json.dumps(result) + "\n" + arch_text
    if not V2_OR_CHUNK_RE.search(combined):
        fail("plan must account for export-v1 limit and fallback/chunking strategy")
    if not MODE_JSONL_RE.search(combined):
        fail("plan must capture export-v2-stream --mode jsonl finding from secondary probe")
    if not BUFFER_RE.search(combined):
        fail("plan must capture the 4096-byte stdin buffer cap from probing export-v2-stream")


def check_c1(result: dict) -> None:
    items = result.get("work_items")
    if not isinstance(items, list) or not items:
        fail("work_items must be non-empty")
    followed = {ident for item in items if isinstance(item, dict) for ident in (item.get("follows") or ())}
    for req in ("R-1", "R-2"):
        if req not in followed:
            fail(f"primary requirement {req} must be covered in work_items[*].follows")
    concerns = result.get("concerns")
    if not isinstance(concerns, dict) or not concerns:
        fail("concerns map is required")
    first_id = items[0].get("id")
    if not isinstance(concerns.get(first_id), list) or len(concerns[first_id]) != 15:
        fail(f"first work item {first_id} must map all 15 concerns")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("P1", "C1"):
        fail("usage: check_chained_exp.py <P1|C1>")
    result = load_result()
    check_p1(result) if sys.argv[1] == "P1" else check_c1(result)


if __name__ == "__main__":
    main()
