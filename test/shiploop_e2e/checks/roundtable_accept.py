"""Independent browser acceptance for the opt-in Roundtable delivery ladder.

The visible case requests define accessible names and the deterministic endpoint,
not DOM IDs, CSS structure or token values. Each check starts a fresh browser
context; later case declarations explicitly include the earlier checks. These
observations establish behavior and collect rendering evidence, not a taste score
or proof that an architecture file caused the implementation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


DRIVER = Path(__file__).with_suffix(".cjs")


def source_digest(folder: Path) -> str:
    """Bind observations to the delivered copy without retaining its file contents."""
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or any(p in {".git", "node_modules", "__pycache__"} for p in path.relative_to(folder).parts):
            continue
        digest.update(path.relative_to(folder).as_posix().encode() + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def observe(base, product, mode):
    output = product.scratch()
    before = source_digest(product.folder)
    result = product.run(["node", str(DRIVER), base, mode, str(output)], ceiling=float("inf"))
    report_path = output / "observation.json"
    if result.get("timeout"):
        return None, f"observer interrupted; evidence: {output}"
    if not report_path.is_file():
        return None, f"observer did not produce a report (exit {result.get('returncode')}); evidence: {output}"
    try:
        report = json.loads(report_path.read_text())
    except (OSError, ValueError) as error:
        return None, f"unreadable observer report: {error}; evidence: {output}"
    if not isinstance(report, dict):
        return None, f"observer report is not an object; evidence: {output}"
    after = source_digest(product.folder)
    report["source_before"] = before
    report["source_after"] = after
    report["source_unchanged"] = before == after
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if before != after:
        return None, f"delivered copy changed during observation; evidence: {output}"
    if report.get("mode") != mode or report.get("base") != base or report.get("observed") is not True:
        return None, f"observation unavailable or identity mismatch: {report.get('error')}; evidence: {output}"
    rows = report.get("checks")
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) or not row.get("id") or
                                                   type(row.get("pass")) is not bool for row in rows):
        return None, f"incomplete observation rows; evidence: {output}"
    failed = [row["id"] for row in rows if not row["pass"]]
    passed = not failed and report.get("complete") is True and result.get("returncode") == 0
    return passed, f"{len(rows)} assertions; failures: {', '.join(failed) or 'none'}; complete={report.get('complete')}; evidence: {output}"


def conversation(base, product):
    return observe(base, product, "conversation")


def rooms(base, product):
    return observe(base, product, "rooms")


def agent_work(base, product):
    return observe(base, product, "agent-work")


CHECKS = {
    "conversation": conversation,
    "rooms": rooms,
    "agent-work": agent_work,
}
