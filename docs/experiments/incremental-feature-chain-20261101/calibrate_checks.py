#!/usr/bin/env python3
"""No-model calibration of the incremental feature-chain behavior oracles.

Run from any directory with:
    python3 docs/experiments/incremental-feature-chain-20261101/calibrate_checks.py

The expected status matrix below is frozen before variants are run. Stdout is
one JSON document with the aggregate result and captured evidence for every
variant/oracle cell. Exit 0 means every cell matched its expected checker exit.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHECKS = HERE / "checks.py"
BASE_CHECKS = ROOT / "test" / "shiploop_e2e" / "checks" / "csv_report.py"
TEST_FIXTURE = HERE / "fixtures" / "test_report.py"
CHECK_ORDER = ("unit", "totals", "invalid", "missing", "empty", "base-scope", "filter", "output")
BASE_ORACLES = {"unit", "totals", "invalid", "missing", "empty"}
FEATURE_ORACLES = {"base-scope", "filter", "output"}

# Each pair uses a different implementation structure: a procedural manual
# parser with direct accumulation, and argparse with dataclass records/totals.
CORRECT_CONTROLS = {
    "procedural-base": ("procedural", "base", "none"),
    "procedural-filter": ("procedural", "filter", "none"),
    "procedural-full": ("procedural", "full", "none"),
    "argparse-base": ("argparse", "base", "none"),
    "argparse-filter": ("argparse", "filter", "none"),
    "argparse-full": ("argparse", "full", "none"),
    "argparse-full-info-stderr": ("argparse", "full", "success-stderr"),
    "argparse-full-buffered-crlf": ("argparse", "full", "buffered-crlf"),
}

SCOPE_CONTROLS = {
    "base-noop-selector": ("procedural", "filter", "noop-selector"),
}

FAULT_CONTROLS = {
    "lost-base-behavior": ("procedural", "full", "lost-base"),
    "case-insensitive-match": ("procedural", "full", "case-insensitive"),
    "substring-match": ("argparse", "full", "substring"),
    "hides-unselected-invalid": ("procedural", "full", "hide-invalid"),
    "hides-unselected-negative": ("procedural", "full", "hide-negative-unselected"),
    "csv-ignores-filter": ("argparse", "full", "csv-ignores-filter"),
    "wrong-default-format": ("procedural", "full", "wrong-default"),
    "malformed-one-column-csv": ("procedural", "full", "one-column-csv"),
}

MAPPED_CONTROLS = {**CORRECT_CONTROLS, **SCOPE_CONTROLS}
VARIANTS = {**MAPPED_CONTROLS, **FAULT_CONTROLS}

# 0 means the oracle must pass; 1 means it must reject the variant. These
# expectations are intentionally literal and are not inferred from behavior.
EXPECTED = {
    "procedural-base": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 0, "filter": 1, "output": 1,
    },
    "procedural-filter": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 1,
    },
    "procedural-full": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 0,
    },
    "argparse-base": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 0, "filter": 1, "output": 1,
    },
    "argparse-filter": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 1,
    },
    "argparse-full": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 0,
    },
    "argparse-full-info-stderr": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 0,
    },
    "argparse-full-buffered-crlf": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 0,
    },
    "base-noop-selector": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 0, "filter": 1, "output": 1,
    },
    "lost-base-behavior": {
        "unit": 1, "totals": 1, "invalid": 1, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 1, "output": 1,
    },
    "case-insensitive-match": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 1, "output": 0,
    },
    "substring-match": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 1, "output": 0,
    },
    "hides-unselected-invalid": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 1, "output": 1,
    },
    "hides-unselected-negative": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 1, "output": 1,
    },
    "csv-ignores-filter": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 1,
    },
    "wrong-default-format": {
        "unit": 1, "totals": 1, "invalid": 1, "missing": 0, "empty": 1,
        "base-scope": 1, "filter": 1, "output": 1,
    },
    "malformed-one-column-csv": {
        "unit": 0, "totals": 0, "invalid": 0, "missing": 0, "empty": 0,
        "base-scope": 1, "filter": 0, "output": 1,
    },
}


def source_for(style: str, stage: str, bug: str) -> str:
    template = (HERE / "fixtures" / style / "report.py.in").read_text(encoding="utf-8")
    rendered = template.replace("@@STAGE@@", stage).replace("@@BUG@@", bug)
    if "@@STAGE@@" in rendered or "@@BUG@@" in rendered:
        raise RuntimeError(f"unexpanded fixture placeholder in {style}")
    return rendered


def clip(value: Any, limit: int = 8000) -> tuple[str, bool]:
    if value is None:
        return "", False
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    value = str(value)
    if len(value) <= limit:
        return value, False
    return value[:limit] + "...[truncated]", True


def input_manifest(base_checks: Path) -> dict[str, dict[str, str]]:
    """Return stable identities for every request, oracle, fixture, and calibrator input."""
    paths = {
        "checks": CHECKS,
        "csv_report": base_checks,
        "checks_source": HERE / "checks-source.json",
        "procedural_fixture": HERE / "fixtures" / "procedural" / "report.py.in",
        "argparse_fixture": HERE / "fixtures" / "argparse" / "report.py.in",
        "test_fixture": TEST_FIXTURE,
        "calibrator": Path(__file__),
        "request_base": HERE / "01-base.txt",
        "request_filter": HERE / "02-region.txt",
        "request_output": HERE / "03-csv-output.txt",
    }
    manifest = {}
    for label, path in paths.items():
        resolved = Path(path).expanduser().resolve(strict=True)
        if not resolved.is_file():
            raise FileNotFoundError(f"calibration input {label} is not a file: {resolved}")
        manifest[label] = {
            "path": str(resolved),
            "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
        }
    return manifest


def source_context() -> dict[str, str]:
    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return done.stdout.rstrip("\n")

    return {
        "head": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "status": git("status", "--short", "--untracked-files=all"),
    }


def run_cell(variant: str, product: Path, oracle: str, base_checks: Path) -> dict[str, Any]:
    if oracle in BASE_ORACLES:
        argv = [sys.executable, str(base_checks), oracle]
        timeout = 360 if oracle == "unit" else 90
    else:
        argv = [sys.executable, "checks.py", oracle]
        timeout = 180
    cell: dict[str, Any] = {
        "id": f"{variant}:{oracle}",
        "variant": variant,
        "oracle": oracle,
        "argv": argv,
        "cwd": str(product),
        "expected_exit": EXPECTED[variant][oracle],
    }
    try:
        done = subprocess.run(
            argv,
            cwd=product,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
        actual = done.returncode
        stdout, stdout_truncated = clip(done.stdout)
        stderr, stderr_truncated = clip(done.stderr)
    except subprocess.TimeoutExpired as exc:
        actual = None
        stdout, stdout_truncated = clip(exc.stdout)
        stderr, stderr_truncated = clip(exc.stderr)
        stderr += f"\nTimed out after {timeout} seconds"
    failure_diagnostic = None
    named_failure = None
    if oracle in FEATURE_ORACLES and EXPECTED[variant][oracle] == 1:
        match = re.match(rf"^FAIL {re.escape(oracle)}: \[([^\]]+)\]", stdout)
        named_failure = bool(match) and "Traceback" not in stdout and "Traceback" not in stderr
        failure_diagnostic = match.group(1) if match else None
    matched = actual == EXPECTED[variant][oracle]
    if oracle in FEATURE_ORACLES and EXPECTED[variant][oracle] == 1:
        matched = matched and named_failure is True
    cell.update(
        {
            "actual_exit": actual,
            "matched": matched,
            "named_failure_diagnostic": failure_diagnostic,
            "failure_is_named_and_traceback_free": named_failure,
            "stdout": stdout,
            "stdout_truncated": stdout_truncated,
            "stderr": stderr,
            "stderr_truncated": stderr_truncated,
        }
    )
    return cell


def source_map_coverage(cells: list[dict[str, Any]]) -> dict[str, Any]:
    mapping = json.loads((HERE / "checks-source.json").read_text(encoding="utf-8"))
    groups = mapping["checks"]["condition_groups"]
    source_ids = set(mapping["sources"])
    mapped: dict[str, list[str]] = {}
    for cell in cells:
        if cell["variant"] not in MAPPED_CONTROLS or cell["oracle"] not in groups:
            continue
        if cell["actual_exit"] != 0 or not cell["stdout"].startswith(f"PASS {cell['oracle']}: "):
            continue
        status_line = cell["stdout"].splitlines()[0]
        identifiers = status_line.split(": ", 1)[1].split(", ")
        for identifier in identifiers:
            citations = []
            for rule in groups[cell["oracle"]]:
                if rule.get("id") == identifier or identifier.startswith(rule.get("id_prefix", "\0")):
                    citations = rule["sources"]
                    break
            mapped[identifier] = citations
    invalid_sources = sorted(
        {source for citations in mapped.values() for source in citations if source not in source_ids}
    )
    unmapped = sorted(identifier for identifier, citations in mapped.items() if not citations)
    return {
        "conditions_observed": len(mapped),
        "unmapped_conditions": unmapped,
        "unknown_source_ids": invalid_sources,
        "all_conditions_mapped": bool(mapped) and not unmapped and not invalid_sources,
        "condition_sources": [
            {"condition_id": identifier, "sources": citations}
            for identifier, citations in sorted(mapped.items())
        ],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Calibrate the incremental CSV checks without model calls.")
    parser.add_argument("--base-checks", type=Path, default=BASE_CHECKS)
    args = parser.parse_args(argv)
    base_checks = args.base_checks.expanduser().resolve(strict=True)

    if set(VARIANTS) != set(EXPECTED):
        raise RuntimeError("variant and frozen expectation inventories differ")
    if any(set(matrix) != set(CHECK_ORDER) for matrix in EXPECTED.values()):
        raise RuntimeError("a frozen expectation row does not cover every oracle")
    expected_matrix_sha256 = hashlib.sha256(
        json.dumps(EXPECTED, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    context = source_context()
    inputs = input_manifest(base_checks)

    cells = []
    for variant, (style, stage, bug) in VARIANTS.items():
        with tempfile.TemporaryDirectory(prefix=f"shiploop-cal-{variant}-") as temporary:
            product = Path(temporary)
            (product / "report.py").write_text(source_for(style, stage, bug), encoding="utf-8")
            (product / "checks.py").write_text(CHECKS.read_text(encoding="utf-8"), encoding="utf-8")
            (product / "test_report.py").write_text(TEST_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            for oracle in CHECK_ORDER:
                cell = run_cell(variant, product, oracle, base_checks)
                cell.update(
                    {
                        "implementation_style": style,
                        "stage": stage,
                        "fault": bug if variant in FAULT_CONTROLS else None,
                        "control_note": {
                            "argparse-full-info-stderr": "informational stderr on successful CSV output",
                            "argparse-full-buffered-crlf": "default CSV dialect CRLF plus print() adds an empty physical record",
                            "base-noop-selector": "accepts --region but returns the unfiltered base result; behavior probe only",
                        }.get(variant),
                    }
                )
                cells.append(cell)

    mismatches = [cell["id"] for cell in cells if not cell["matched"]]
    total = len(cells)
    matched = total - len(mismatches)
    source_map = source_map_coverage(cells)
    stderr_cell = next(
        cell for cell in cells if cell["id"] == "argparse-full-info-stderr:output"
    )
    observed_rows = []
    for line in stderr_cell["stdout"].splitlines()[1:]:
        if line.startswith("OBSERVED successful-stderr: "):
            observed_rows.extend(json.loads(line.split(": ", 1)[1]))
    success_stderr_control = {
        "cell_id": stderr_cell["id"],
        "actual_exit": stderr_cell["actual_exit"],
        "diagnostic_observed": any(
            "report: CSV output generated" in row["stderr"] for row in observed_rows
        ),
        "checker_observed_conditions": [row["condition"] for row in observed_rows],
        "accepted": (
            stderr_cell["matched"]
            and stderr_cell["actual_exit"] == 0
            and any("report: CSV output generated" in row["stderr"] for row in observed_rows)
        ),
    }
    inputs_after = input_manifest(base_checks)
    context_after = source_context()
    inputs_unchanged = inputs == inputs_after
    context_unchanged = context == context_after
    evidence_stable = inputs_unchanged and context_unchanged
    result = {
        "schema_version": 1,
        "calibration": "incremental-feature-chain-20261101",
        "live_model_calls": 0,
        "implementations": {
            "procedural": "manual option parser; direct row validation and aggregation",
            "argparse": "argparse CLI; dataclass entries followed by a separate totals pass",
        },
        "stages": ["base", "filter", "full"],
        "faults": [
            "lost-base-behavior",
            "case-insensitive-match",
            "substring-match",
            "hides-unselected-invalid",
            "hides-unselected-negative",
            "csv-ignores-filter",
            "wrong-default-format",
            "malformed-one-column-csv",
        ],
        "coverage_notes": {
            "early_filter": "The staged procedural-filter and argparse-filter controls each expect base-scope failure; no duplicate early-filter variant is retained.",
            "base_noop_selector": "The separate base-noop-selector control covers accepted --region with exit 0 and unchanged output; semantic assessment of deferred knowledge remains human review.",
        },
        "summary": {
            "variants": len(VARIANTS),
            "oracles_per_variant": len(CHECK_ORDER),
            "cells": total,
            "matched": matched,
            "mismatches": mismatches,
            "all_expectations_matched": (
                not mismatches
                and source_map["all_conditions_mapped"]
                and success_stderr_control["accepted"]
                and evidence_stable
            ),
            "inputs_unchanged": inputs_unchanged,
            "context_unchanged": context_unchanged,
        },
        "context": context,
        "context_after": context_after,
        "inputs": inputs,
        "inputs_after": inputs_after,
        "expected_matrix_sha256": expected_matrix_sha256,
        "harmless_success_stderr_control": success_stderr_control,
        "source_map_coverage": source_map,
        "cells": cells,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (
        0
        if not mismatches
        and source_map["all_conditions_mapped"]
        and success_stderr_control["accepted"]
        and evidence_stable
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
