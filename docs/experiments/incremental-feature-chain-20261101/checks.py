#!/usr/bin/env python3
"""Experiment-local behavioral checks for the three incremental requests.

Run from a product work directory with ``python3 checks.py base-scope|filter|output``.
Inputs are created in temporary directories outside that work directory. The
base-scope check establishes behavior only; a human must review source and
living knowledge to judge whether the deferred requirement was recorded well.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


HEADER = ("date", "region", "product", "units", "unit_price")
INVALID_UNSELECTED_LINES = (
    ("wrong-column-count", 3),
    ("negative-units", 4),
    ("fractional-units", 5),
    ("nonnumeric-price", 6),
    ("negative-price", 7),
)
PASSED: list[str] = []
OBSERVED_SUCCESS_STDERR: list[dict[str, str]] = []


class CheckFailure(Exception):
    pass


def require(condition_id: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise CheckFailure(f"[{condition_id}] expected {expected!r}; got {actual!r}")
    PASSED.append(condition_id)


def run_report(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "report.py", *(str(arg) for arg in args)],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=45,
    )


def write_csv(folder: Path, name: str, rows: list[tuple[str, ...]]) -> Path:
    path = folder / name
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
    return path


def summary(done: subprocess.CompletedProcess[str], condition: str, exit_code: int) -> dict[str, Any]:
    require(f"{condition}.exit", done.returncode, exit_code)
    try:
        value = json.loads(done.stdout, parse_float=Decimal, parse_int=Decimal)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CheckFailure(
            f"[{condition}.json] expected one JSON object; got stdout={done.stdout!r}, "
            f"stderr={done.stderr!r} ({exc})"
        ) from exc
    if not isinstance(value, dict):
        raise CheckFailure(f"[{condition}.json] expected an object; got {value!r}")
    return value


def decimal_value(value: Any, condition: str) -> Decimal:
    if isinstance(value, bool):
        raise CheckFailure(f"[{condition}] expected a JSON number; got {value!r}")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CheckFailure(f"[{condition}] expected a JSON number; got {value!r}") from exc
    if not result.is_finite():
        raise CheckFailure(f"[{condition}] expected a finite JSON number; got {value!r}")
    return result


def check_summary(
    done: subprocess.CompletedProcess[str],
    condition: str,
    *,
    exit_code: int,
    rows: int,
    revenue: str,
    by_region: dict[str, str],
    by_product: dict[str, int],
) -> dict[str, Any]:
    data = summary(done, condition, exit_code)
    require(f"{condition}.rows", data.get("rows"), Decimal(rows))
    require(
        f"{condition}.revenue",
        decimal_value(data.get("revenue"), f"{condition}.revenue"),
        Decimal(revenue),
    )
    regions = data.get("by_region")
    if not isinstance(regions, dict):
        raise CheckFailure(f"[{condition}.by_region] expected an object; got {regions!r}")
    normalized_regions = {
        str(name): decimal_value(amount, f"{condition}.by_region.{name}")
        for name, amount in regions.items()
    }
    require(
        f"{condition}.by_region",
        normalized_regions,
        {name: Decimal(amount) for name, amount in by_region.items()},
    )
    products = data.get("by_product")
    if not isinstance(products, dict):
        raise CheckFailure(f"[{condition}.by_product] expected an object; got {products!r}")
    require(
        f"{condition}.by_product",
        products,
        by_product,
    )
    return data


def usage_error(done: subprocess.CompletedProcess[str], condition: str) -> None:
    require(f"{condition}.exit", done.returncode, 2)
    require(f"{condition}.stdout-empty", done.stdout, "")
    if not done.stderr.strip():
        raise CheckFailure(f"[{condition}.stderr] expected a usage diagnostic; stderr was empty")
    if "Traceback" in done.stderr:
        raise CheckFailure(f"[{condition}.no-traceback] got a traceback: {done.stderr!r}")
    PASSED.extend((f"{condition}.stderr-present", f"{condition}.no-traceback"))


def filter_inputs(folder: Path) -> tuple[Path, Path]:
    first = write_csv(
        folder,
        "regions-a.csv",
        [
            ("2026-01-01", "North", "widget", "2", "1.25"),
            ("2026-01-02", "north", "gadget", "3", "1.00"),
            ("2026-01-03", "Northern", "widget", "7", "0.50"),
            ("2026-01-04", "", "blank", "4", "0.25"),
            (),
        ],
    )
    second = write_csv(
        folder,
        "regions-b.csv",
        [
            ("2026-01-05", "North", "gadget", "1", "10.00"),
            ("2026-01-06", "South", "widget", "8", "0.25"),
            (),
        ],
    )
    return first, second


def base_scope() -> None:
    with tempfile.TemporaryDirectory(prefix="shiploop-base-scope-") as temporary:
        folder = Path(temporary)
        path = write_csv(
            folder,
            "scope.csv",
            [
                ("2026-01-01", "North", "widget", "2", "1.25"),
                ("2026-01-02", "South", "gadget", "1", "10.00"),
            ],
        )
        baseline = run_report(path)
        check_summary(
            baseline,
            "base-scope.base-contract",
            exit_code=0,
            rows=2,
            revenue="12.50",
            by_region={"North": "2.50", "South": "10.00"},
            by_product={"widget": 2, "gadget": 1},
        )

        probe = run_report("--region", "North", path)
        if probe.returncode == 0:
            observed = summary(probe, "base-scope.selector-probe", 0)
            if observed == baseline_result(baseline):
                PASSED.append("base-scope.filter-not-implemented")
            else:
                raise CheckFailure(
                    "[base-scope.filter-not-implemented] --region produced a result "
                    f"different from the unfiltered base result: {observed!r}"
                )
        elif probe.returncode != 0 and probe.stdout == "" and "Traceback" not in probe.stderr:
            PASSED.append("base-scope.filter-not-implemented")
        else:
            raise CheckFailure(
                "[base-scope.filter-not-implemented] selector probe did not establish "
                f"absence of filtering: exit={probe.returncode}, stdout={probe.stdout!r}, "
                f"stderr={probe.stderr!r}"
            )


def baseline_result(done: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(done.stdout, parse_float=Decimal, parse_int=Decimal)


def filter_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="shiploop-filter-") as temporary:
        folder = Path(temporary)
        first, second = filter_inputs(folder)

        check_summary(
            run_report("--region", "North", first, second),
            "filter.exact-multiple-files-all-aggregations",
            exit_code=0,
            rows=2,
            revenue="12.50",
            by_region={"North": "12.50"},
            by_product={"widget": 2, "gadget": 1},
        )
        check_summary(
            run_report("--region", "north", first, second),
            "filter.case-sensitive",
            exit_code=0,
            rows=1,
            revenue="3.00",
            by_region={"north": "3.00"},
            by_product={"gadget": 3},
        )
        check_summary(
            run_report("--region", "Nor", first, second),
            "filter.substring-near-match",
            exit_code=0,
            rows=0,
            revenue="0.00",
            by_region={},
            by_product={},
        )
        check_summary(
            run_report("--region", "", first, second),
            "filter.empty-region",
            exit_code=0,
            rows=1,
            revenue="1.00",
            by_region={"": "1.00"},
            by_product={"blank": 4},
        )
        check_summary(
            run_report("--region", "NoSuchRegion", first, second),
            "filter.no-match-empty-aggregations",
            exit_code=0,
            rows=0,
            revenue="0.00",
            by_region={},
            by_product={},
        )
        check_summary(
            run_report(first, second),
            "filter.omitted-selector-base-behavior",
            exit_code=0,
            rows=6,
            revenue="22.00",
            by_region={
                "North": "12.50",
                "north": "3.00",
                "Northern": "3.50",
                "": "1.00",
                "South": "2.00",
            },
            by_product={"widget": 17, "gadget": 4, "blank": 4},
        )

        invalid = write_csv(
            folder,
            "invalid-unselected.csv",
            [
                ("2026-02-01", "North", "widget", "2", "1.25"),
                ("2026-02-02", "South", "wrong-column-count"),
                ("2026-02-03", "South", "negative-units", "-2", "1.00"),
                ("2026-02-04", "South", "fractional-units", "1.5", "1.00"),
                ("2026-02-05", "South", "nonnumeric-price", "1", "free"),
                ("2026-02-06", "South", "negative-price", "1", "-0.25"),
                ("2026-02-07", "North", "gadget", "1", "1.00"),
            ],
        )
        done = run_report("--region", "North", invalid)
        check_summary(
            done,
            "filter.unselected-invalid-still-reported",
            exit_code=2,
            rows=2,
            revenue="3.50",
            by_region={"North": "3.50"},
            by_product={"widget": 2, "gadget": 1},
        )
        for label, line in INVALID_UNSELECTED_LINES:
            require(
                f"filter.unselected-{label}-diagnostic",
                f"{invalid}:{line}" in done.stderr,
                True,
            )
        require(
            "filter.unselected-invalid-all-diagnostics",
            all(f"{invalid}:{line}" in done.stderr for _, line in INVALID_UNSELECTED_LINES),
            True,
        )

        missing = folder / "unreadable.csv"
        done = run_report("--region", "North", invalid, missing)
        require("filter.unreadable-precedes-invalid.exit", done.returncode, 1)
        require("filter.unreadable-precedes-invalid.stdout-empty", done.stdout, "")
        if not done.stderr.strip() or "Traceback" in done.stderr:
            raise CheckFailure(
                "[filter.unreadable-precedes-invalid.stderr] expected an unreadable-file "
                f"diagnostic without a traceback; got {done.stderr!r}"
            )
        PASSED.extend(
            (
                "filter.unreadable-precedes-invalid.stderr-present",
                "filter.unreadable-precedes-invalid.no-traceback",
            )
        )

        usage_error(run_report("--region"), "filter.missing-region-value")


def csv_rows(stdout: str, condition: str) -> list[list[str]]:
    try:
        return [row for row in csv.reader(io.StringIO(stdout, newline="")) if row != []]
    except csv.Error as exc:
        raise CheckFailure(f"[{condition}] stdout is not parseable CSV: {exc}; {stdout!r}") from exc


def csv_result(
    done: subprocess.CompletedProcess[str], condition: str, exit_code: int = 0
) -> list[list[str]]:
    require(f"{condition}.exit", done.returncode, exit_code)
    if exit_code == 0 and done.stderr:
        OBSERVED_SUCCESS_STDERR.append({"condition": condition, "stderr": done.stderr})
    return csv_rows(done.stdout, condition)


def output_checks() -> None:
    with tempfile.TemporaryDirectory(prefix="shiploop-output-") as temporary:
        folder = Path(temporary)
        special = write_csv(
            folder,
            "special-regions.csv",
            [
                ("2026-03-01", "zeta", "widget", "1", "1.20"),
                ("2026-03-02", "Zebra", "gadget", "2", "0.25"),
                ("2026-03-03", "Älpha", "widget", "3", "0.40"),
                ("2026-03-04", "Ångström", "gadget", "1", "2.25"),
                ("2026-03-05", "comma,region", "item", "2", "0.25"),
                ("2026-03-06", 'quote "region"', "item", "3", "0.40"),
                ("2026-03-07", "multi\nline", "item", "4", "0.25"),
                ("2026-03-08", "", "item", "2", "0.25"),
            ],
        )
        default_json = run_report(special)
        explicit_json = run_report("--format", "json", special)
        default_data = check_summary(
            default_json,
            "output.default-json",
            exit_code=0,
            rows=8,
            revenue="8.35",
            by_region={
                "zeta": "1.20",
                "Zebra": "0.50",
                "Älpha": "1.20",
                "Ångström": "2.25",
                "comma,region": "0.50",
                'quote "region"': "1.20",
                "multi\nline": "1.00",
                "": "0.50",
            },
            by_product={"widget": 4, "gadget": 3, "item": 11},
        )
        explicit_data = check_summary(
            explicit_json,
            "output.explicit-json",
            exit_code=0,
            rows=8,
            revenue="8.35",
            by_region={
                "zeta": "1.20",
                "Zebra": "0.50",
                "Älpha": "1.20",
                "Ångström": "2.25",
                "comma,region": "0.50",
                'quote "region"': "1.20",
                "multi\nline": "1.00",
                "": "0.50",
            },
            by_product={"widget": 4, "gadget": 3, "item": 11},
        )
        require("output.explicit-json-equals-default", explicit_data, default_data)

        done = run_report("--format", "csv", special)
        rows = csv_result(done, "output.csv-table")
        expected_regions = sorted(
            (
                "zeta",
                "Zebra",
                "Älpha",
                "Ångström",
                "comma,region",
                'quote "region"',
                "multi\nline",
                "",
            )
        )
        revenues = {
            "zeta": "1.20",
            "Zebra": "0.50",
            "Älpha": "1.20",
            "Ångström": "2.25",
            "comma,region": "0.50",
            'quote "region"': "1.20",
            "multi\nline": "1.00",
            "": "0.50",
        }
        require("output.csv-header-columns", rows[0] if rows else [], ["region", "revenue"])
        require(
            "output.csv-data-row-arity",
            all(len(row) == 2 for row in rows[1:]),
            True,
        )
        require(
            "output.csv-codepoint-region-order",
            [row[0] for row in rows[1:]],
            expected_regions,
        )
        require(
            "output.csv-two-decimal-revenue",
            rows[1:],
            [[region, revenues[region]] for region in expected_regions],
        )
        require(
            "output.csv-quoted-values-round-trip",
            {row[0] for row in rows[1:] if row},
            set(expected_regions),
        )

        first_order = csv_result(
            run_report("--region", "comma,region", "--format", "csv", special),
            "output.filter-region-before-format",
        )
        second_order = csv_result(
            run_report("--format", "csv", "--region", "comma,region", special),
            "output.filter-format-before-region",
        )
        expected_one = [["region", "revenue"], ["comma,region", "0.50"]]
        require("output.filter-region-before-format-fields", first_order, expected_one)
        require("output.filter-format-before-region-fields", second_order, expected_one)
        require("output.filter-option-orders-equivalent", first_order, second_order)

        invalid = write_csv(
            folder,
            "invalid-csv-selection.csv",
            [
                ("2026-04-01", "comma,region", "item", "2", "0.25"),
                ("2026-04-02", "other", "wrong-column-count"),
                ("2026-04-03", "other", "negative-units", "-2", "1.00"),
                ("2026-04-04", "other", "fractional-units", "1.5", "1.00"),
                ("2026-04-05", "other", "nonnumeric-price", "1", "free"),
                ("2026-04-06", "other", "negative-price", "1", "-0.25"),
                ("2026-04-07", "comma,region", "item", "1", "1.00"),
            ],
        )
        done = run_report("--region", "comma,region", "--format", "csv", invalid)
        rows = csv_result(done, "output.csv-filtered-validation", exit_code=2)
        require(
            "output.csv-unselected-invalid-still-diagnosed-and-selected-output",
            rows,
            [["region", "revenue"], ["comma,region", "1.50"]],
        )
        for label, line in INVALID_UNSELECTED_LINES:
            require(
                f"output.csv-unselected-{label}-diagnostic",
                f"{invalid}:{line}" in done.stderr,
                True,
            )
        require(
            "output.csv-unselected-invalid-all-diagnostics",
            all(f"{invalid}:{line}" in done.stderr for _, line in INVALID_UNSELECTED_LINES),
            True,
        )

        missing_file = folder / "not-readable.csv"
        done = run_report("--format", "csv", "--region", "comma,region", invalid, missing_file)
        require("output.csv-unreadable-precedence.exit", done.returncode, 1)
        require("output.csv-unreadable-precedence.stdout-empty", done.stdout, "")
        if not done.stderr.strip() or "Traceback" in done.stderr:
            raise CheckFailure(
                "[output.csv-unreadable-precedence.stderr] expected an unreadable-file "
                f"diagnostic without a traceback; got {done.stderr!r}"
            )
        PASSED.extend(
            (
                "output.csv-unreadable-precedence.stderr-present",
                "output.csv-unreadable-precedence.no-traceback",
            )
        )

        empty_selection = csv_result(
            run_report("--region", "absent", "--format", "csv", special),
            "output.csv-empty-selection",
        )
        require("output.csv-empty-selection-header-only", empty_selection, [["region", "revenue"]])
        header_only = write_csv(folder, "header-only.csv", [])
        header_result = csv_result(
            run_report("--format", "csv", header_only), "output.csv-header-only-input"
        )
        require("output.csv-header-only-input-header-only", header_result, [["region", "revenue"]])

        usage_error(run_report("--format"), "output.missing-format-value")
        usage_error(
            run_report("--format", "xml", special), "output.unsupported-format-value"
        )


CHECKS = {
    "base-scope": base_scope,
    "filter": filter_checks,
    "output": output_checks,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in CHECKS:
        print("usage: checks.py " + "|".join(CHECKS), file=sys.stderr)
        return 2
    name = argv[0]
    try:
        CHECKS[name]()
    except (CheckFailure, InvalidOperation, OSError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL {name}: {exc}")
        return 1
    print(f"PASS {name}: " + ", ".join(PASSED))
    if OBSERVED_SUCCESS_STDERR:
        print(
            "OBSERVED successful-stderr: "
            + json.dumps(OBSERVED_SUCCESS_STDERR, ensure_ascii=False)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
