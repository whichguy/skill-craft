"""Deterministic checks for carry-forward/one-step-owed-note."""
import json
import os
import re
import sys
from pathlib import Path

EXPECTED_R2_BLOCK = (
    "### R-2: Preserve pure helper behavior and zero dependencies\n"
    "Preserve existing pure helper behavior in `src/format.js` and keep `node --test` passing with zero external npm dependencies.\n"
    "- Confirm by: `node --test` exits 0 with all existing tests passing."
)


def fail(message: str) -> None:
    raise SystemExit(message)


def load_result() -> dict:
    path = os.environ.get("STAGE_RESULT")
    if not path:
        fail("STAGE_RESULT is not set")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("result.json must be a JSON object")
    return data


def read_spec() -> str:
    spec_path = Path.cwd() / "docs/shiploop/spec.md"
    if not spec_path.is_file():
        fail("docs/shiploop/spec.md is missing")
    return spec_path.read_text(encoding="utf-8")


def section_for(spec: str, req_id: str) -> str:
    pattern = re.compile(rf"(?m)^###\s+{re.escape(req_id)}\b.*$")
    match = pattern.search(spec)
    if not match:
        fail(f"docs/shiploop/spec.md is missing {req_id}")
    rest = spec[match.start():]
    next_heading = re.search(r"(?m)^#{1,3}\s+", rest[len(match.group(0)):])
    if next_heading:
        return rest[:len(match.group(0)) + next_heading.start()].strip()
    return rest.strip()


def check_p1(result: dict) -> None:
    notes = result.get("notes")
    if not isinstance(notes, list) or not notes:
        fail("result.notes must account for owed owner note N1")
    n1_rows = [row for row in notes if isinstance(row, dict) and row.get("note") == "N1"]
    if len(n1_rows) != 1:
        fail(f"result.notes must contain exactly one row for N1 (got {len(n1_rows)})")
    row = n1_rows[0]
    if row.get("did") != "applied":
        fail(f"N1 row must have did='applied' (got {row.get('did')!r})")
    detail = str(row.get("detail", "")).strip()
    if not detail:
        fail("N1 row must have a non-empty detail")
    item_id = str(row.get("item", "")).strip()
    if not item_id or item_id == "W1":
        fail(f"N1 row must name a pending follow-up work item (got {item_id!r})")

    work_items = result.get("work_items")
    if not isinstance(work_items, list) or not work_items:
        fail("result.work_items must queue the follow-up work item")
    matched = [
        item for item in work_items
        if isinstance(item, dict) and str(item.get("id", "")).strip() == item_id
    ]
    if len(matched) != 1:
        fail(f"result.work_items must contain queued item {item_id!r}")
    queued = matched[0]
    follows = queued.get("follows")
    if not isinstance(follows, list) or not any(str(ref).strip() == "R-1" for ref in follows):
        fail(f"queued item {item_id!r} must carry follows referencing R-1 (got {follows!r})")

    r1_block = section_for(read_spec(), "R-1")
    if not re.search(r"\bwrap(?:s|ping|-?around)?\b", r1_block, re.I):
        fail("R-1 in docs/shiploop/spec.md was not revised for wrap-around navigation")
    if re.search(r"\bclamped\b", r1_block, re.I):
        fail("R-1 in docs/shiploop/spec.md still keeps the old clamped clause")


def check_c1() -> None:
    r2_block = section_for(read_spec(), "R-2")
    if r2_block != EXPECTED_R2_BLOCK:
        fail("R-2 in docs/shiploop/spec.md was altered")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("P1", "C1"):
        fail("usage: check_carry_forward.py <P1|C1>")
    result = load_result()
    if sys.argv[1] == "P1":
        check_p1(result)
    else:
        check_c1()


if __name__ == "__main__":
    main()
