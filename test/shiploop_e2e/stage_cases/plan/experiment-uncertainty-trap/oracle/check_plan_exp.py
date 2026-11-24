"""Deterministic oracle for plan/experiment-uncertainty-trap."""
import json
import os
import re
import sys
from pathlib import Path

BATCH_RE = re.compile(r"\b25\b|chunk|batch(?:es|ing)?", re.I)
ESCAPE_RE = re.compile(r"--escape-newlines|escape[- ]?newlines|raw newline|unescap", re.I)


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
    if not q1_rows:
        fail('assumptions must account for intake experiment question Q1 with "question": "Q1"')
    probed = [row for row in q1_rows if row.get("disposition") == "probed"]
    if not probed:
        fail("Q1 must be resolved via an isolated probe (disposition: probed), not left open or unprobed")
    row = probed[0]
    if not isinstance(row.get("check"), str) or not row["check"].strip():
        fail("probed Q1 row must record the probe command in check")
    evidence = row.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        fail("probed Q1 row must list saved probe output in evidence")
    effect = row.get("effect")
    if not isinstance(effect, str) or not effect.strip():
        fail("probed Q1 row must record how the observation changed or confirmed the plan in effect")

    arch_path = Path("docs/shiploop/architecture.md")
    arch_text = arch_path.read_text(encoding="utf-8") if arch_path.is_file() else ""
    combined = json.dumps(result) + "\n" + arch_text
    if not re.search(r"\b25\b", combined):
        fail("plan must capture the observed 25-record batch limit from tools/export-engine.js")
    if not BATCH_RE.search(combined):
        fail("plan must design chunking/batching around the 25-record limit")
    if not ESCAPE_RE.search(combined):
        fail("plan must account for --escape-newlines / raw newline framing behaviour")


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
        fail("usage: check_plan_exp.py <P1|C1>")
    result = load_result()
    if sys.argv[1] == "P1":
        check_p1(result)
    else:
        check_c1(result)


if __name__ == "__main__":
    main()
