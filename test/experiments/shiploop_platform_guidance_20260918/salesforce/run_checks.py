#!/usr/bin/env python3
"""Run deliberately narrow local checks for the Salesforce guidance experiment.

This is a fixture scanner, not an Apex parser, compiler, security analyzer, or
Salesforce runtime. It proves only that the seed/reference/mutant corpus is
discriminating under the stated text rules. The separate Node test executes a
small JavaScript state/cache model; it is not LWC Jest.
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APEX = ROOT / "fixtures" / "apex"
LWC_TEST = ROOT / "fixtures" / "lwc" / "contract.test.mjs"

SOQL = re.compile(r"\[\s*SELECT\b", re.IGNORECASE)
DML = re.compile(
    r"\b(?:insert|update|delete|upsert|undelete|merge)\b|"
    r"\bDatabase\.(?:insert|update|delete|upsert|undelete|merge)\b",
    re.IGNORECASE,
)


def strip_comments(source: str) -> str:
    """Remove fixture comments so the intentionally simple scanner is stable."""

    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", source)


def loop_bodies(source: str) -> list[str]:
    """Return braced bodies following `for (...)` in this constrained corpus."""

    bodies: list[str] = []
    cursor = 0
    while True:
        found = re.search(r"\bfor\s*\(", source[cursor:], re.IGNORECASE)
        if not found:
            return bodies
        start = cursor + found.start()
        brace = source.find("{", start)
        if brace < 0:
            return bodies
        depth = 0
        for index in range(brace, len(source)):
            char = source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    bodies.append(source[brace + 1 : index])
                    cursor = index + 1
                    break
        else:
            return bodies


def security_assessment(path: Path) -> dict[str, bool]:
    source = strip_comments(path.read_text())
    has_explicit_sharing = bool(
        re.search(r"\b(?:public|global)\s+(?:with|inherited)\s+sharing\s+class\b", source)
    )
    has_user_query = "WITH USER_MODE" in source
    has_user_dml = bool(
        re.search(r"\b(?:insert|update|delete|upsert|undelete)\s+as\s+user\b", source)
        or re.search(r"\bAccessLevel\.USER_MODE\b", source)
    )
    has_system_mode = bool(
        re.search(r"\bwithout\s+sharing\s+class\b", source)
        or "WITH SYSTEM_MODE" in source
        or "AccessLevel.SYSTEM_MODE" in source
        or re.search(r"\b(?:insert|update|delete|upsert|undelete)\s+as\s+system\b", source)
    )
    return {
        "explicit_sharing": has_explicit_sharing,
        "explicit_user_query": has_user_query,
        "explicit_user_dml": has_user_dml,
        "no_unexplained_system_mode": not has_system_mode,
        "accepted_by_explicit_intent_rule": (
            has_explicit_sharing
            and has_user_query
            and has_user_dml
            and not has_system_mode
        ),
    }


def bulk_assessment(path: Path) -> dict[str, bool | int]:
    source = strip_comments(path.read_text())
    bodies = loop_bodies(source)
    has_loop_work = bool(bodies)
    has_query_in_loop = any(SOQL.search(body) for body in bodies)
    has_dml_in_loop = any(DML.search(body) for body in bodies)
    outside_loops = source
    for body in bodies:
        outside_loops = outside_loops.replace(body, "")
    has_collection_query = bool(SOQL.search(outside_loops))
    has_collection_dml = bool(DML.search(outside_loops))
    return {
        "loop_count": len(bodies),
        "has_loop_work": has_loop_work,
        "query_in_loop": has_query_in_loop,
        "dml_in_loop": has_dml_in_loop,
        "query_outside_loop": has_collection_query,
        "dml_outside_loop": has_collection_dml,
        "accepted_by_bulk_shape_rule": (
            has_loop_work
            and not has_query_in_loop
            and not has_dml_in_loop
            and has_collection_query
            and has_collection_dml
        ),
    }


def require(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def main() -> int:
    security = {
        name: security_assessment(APEX / filename)
        for name, filename in {
            "seed": "seed_sharing_only.cls",
            "reference": "reference_explicit_user_mode.cls",
            "mutant": "mutant_explicit_system_mode.cls",
        }.items()
    }
    bulk = {
        name: bulk_assessment(APEX / filename)
        for name, filename in {
            "seed": "seed_query_and_dml_in_loop.trigger",
            "reference": "reference_bulkified.trigger",
            "mutant": "mutant_dml_in_loop.trigger",
        }.items()
    }
    failures: list[str] = []
    require(
        security["reference"]["accepted_by_explicit_intent_rule"],
        "security reference should satisfy the explicit-intent fixture rule",
        failures,
    )
    require(
        not security["seed"]["accepted_by_explicit_intent_rule"],
        "security seed should be rejected for missing explicit intent",
        failures,
    )
    require(
        not security["mutant"]["accepted_by_explicit_intent_rule"],
        "security mutant should be rejected for explicit system mode",
        failures,
    )
    require(
        bulk["reference"]["accepted_by_bulk_shape_rule"],
        "bulk reference should satisfy the collection/query/update shape rule",
        failures,
    )
    require(
        not bulk["seed"]["accepted_by_bulk_shape_rule"],
        "bulk seed should be rejected for query and DML in its loop",
        failures,
    )
    require(
        not bulk["mutant"]["accepted_by_bulk_shape_rule"],
        "bulk mutant should be rejected for DML in its loop",
        failures,
    )

    node = shutil.which("node")
    node_result: dict[str, object]
    if node is None:
        failures.append("node is required for the LWC state/cache model")
        node_result = {"available": False, "command": None, "exit_code": None}
    else:
        completed = subprocess.run(
            [node, "--test", str(LWC_TEST)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        node_result = {
            "available": True,
            "command": f"{node} --test {LWC_TEST}",
            "exit_code": completed.returncode,
            "tap_tail": "\n".join(completed.stdout.splitlines()[-8:]),
        }
        require(
            completed.returncode == 0,
            "Node LWC state/cache model should pass",
            failures,
        )

    report = {
        "command": "python3 run_checks.py",
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "node_available": node is not None,
        },
        "fixture_assertions": {
            "apex_security": security,
            "apex_bulk": bulk,
            "lwc_state_and_async_model": node_result,
        },
        "passed": not failures,
        "failures": failures,
        "evidence_boundary": (
            "Apex checks are source-text fixture checks only; Node executes a "
            "JavaScript model only. Neither is Apex runtime, org security, "
            "governor-limit, LDS, wire-service, or browser evidence."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
