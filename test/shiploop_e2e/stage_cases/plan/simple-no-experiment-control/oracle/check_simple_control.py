"""Deterministic oracle for plan/simple-no-experiment-control."""
import json
import os
import sys
from pathlib import Path


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
    items = result.get("work_items")
    if not isinstance(items, list) or len(items) != 1:
        count = len(items) if isinstance(items, list) else type(items).__name__
        fail(f"small cohesive bugfix must remain 1 work item (W1), got {count}")
    assumptions = result.get("assumptions")
    if not isinstance(assumptions, list):
        fail("assumptions must be a list")
    probed = [row for row in assumptions if isinstance(row, dict) and row.get("disposition") == "probed"]
    if probed:
        fail(f"trivial static bugfix needs 0 unnecessary experiments, got {len(probed)} probed row(s)")


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
        fail("usage: check_simple_control.py <P1|C1>")
    result = load_result()
    check_p1(result) if sys.argv[1] == "P1" else check_c1(result)


if __name__ == "__main__":
    main()
