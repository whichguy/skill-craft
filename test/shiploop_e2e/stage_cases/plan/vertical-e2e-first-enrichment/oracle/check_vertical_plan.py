"""Deterministic oracle for plan/vertical-e2e-first-enrichment."""
import json
import os
import re
import sys
from pathlib import Path

STORE_RE = re.compile(r"\b(store|storage|json file|persist|file[- ]backed|notes-store)\b", re.I)
API_RE = re.compile(r"\b(http|api|endpoint|server|POST /notes|GET /notes|/notes)\b", re.I)
CLI_RE = re.compile(r"\b(cli|bin/notes|command[- ]line)\b", re.I)
SMOKE_RE = re.compile(r"\b(e2e|end[- ]to[- ]end|smoke)\b", re.I)
HORIZONTAL_TITLE_RE = re.compile(r"^\s*(?:build|implement|add|create)?\s*(?:the\s+)?(?:storage|data|persistence|database)\s+layer(?:\s+only)?\s*$", re.I)


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
    if not isinstance(items, list) or len(items) < 2:
        fail("multi-surface feature-rich request should produce at least 2 vertical items (W1 spine + W2+ enrich)")
    first = items[0]
    if not isinstance(first, dict):
        fail("first work item must be an object")
    if first.get("slice") != "spine":
        fail(f"W1 must carry slice='spine', found {first.get('slice')!r}")
    later_slices = [item.get("slice") for item in items[1:] if isinstance(item, dict)]
    if "enrich" not in later_slices:
        fail(f"later work items must include at least one slice='enrich' item, found {later_slices!r}")
    title = str(first.get("title") or "")
    if HORIZONTAL_TITLE_RE.match(title):
        fail(f"W1 title looks like a horizontal layer cut, not a vertical spine: {title!r}")
    w1_text = title + "\n" + str(first.get("context") or "")
    surfaces = sum(bool(pat.search(w1_text)) for pat in (STORE_RE, API_RE, CLI_RE))
    if surfaces < 2:
        fail("W1 spine must cut vertically across at least 2 product surfaces (storage, HTTP API, CLI)")
    if not SMOKE_RE.search(w1_text):
        fail("W1 spine must explicitly include an executable end-to-end smoke check inside W1")


def check_c1(result: dict) -> None:
    items = result.get("work_items")
    if not isinstance(items, list) or not items:
        fail("work_items must be non-empty")
    followed = {ident for item in items if isinstance(item, dict) for ident in (item.get("follows") or ())}
    for req in ("R-1", "R-2", "R-3", "R-4"):
        if req not in followed:
            fail(f"primary requirement {req} must be covered across work_items[*].follows")
    concerns = result.get("concerns")
    if not isinstance(concerns, dict) or not concerns:
        fail("concerns map is required")
    ids = [str(item.get("id")) for item in items if isinstance(item, dict)]
    if set(concerns) != set(ids):
        fail(f"concerns keys {sorted(concerns)} must match work_items IDs {sorted(ids)}")
    if not isinstance(concerns.get(ids[0]), list) or len(concerns[ids[0]]) != 15:
        fail(f"first work item {ids[0]} must map all 15 concerns (cannot defer W1)")
    for item_id in ids[1:]:
        entry = concerns.get(item_id)
        if entry != "deferred" and not (isinstance(entry, list) and len(entry) == 15):
            fail(f"later item {item_id} concerns must be 'deferred' or all 15 rows")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("P1", "C1"):
        fail("usage: check_vertical_plan.py <P1|C1>")
    result = load_result()
    if sys.argv[1] == "P1":
        check_p1(result)
    else:
        check_c1(result)


if __name__ == "__main__":
    main()
