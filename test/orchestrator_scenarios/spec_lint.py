#!/usr/bin/env python3
"""Gate 2 check for Plan Orchestrator test specs.

Usage: python3 test/orchestrator_scenarios/spec_lint.py SPEC.md [...]

A spec names its suite (a "Suite:" line) and mutants (a "Mutants:" path) and
has the sections Intent under test, Scenarios, Invariants and oracle, Out of
scope, Review (five numbered answers) and Adversarial. Checked mechanically:
every scenario ID has a failure signal and appears as `[ID]` in the suite or as
the `id` of a scenarios/*.json file; every
adversarial row names a class and its coverage; every mutant named in the spec
exists in the mutants file with the scenario the row cites as `killed_by`, and
every mutant in the file is named in the spec. Prints each problem; exits 1 if any.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ("Intent under test", "Scenarios", "Invariants and oracle", "Out of scope", "Review", "Adversarial")
CLASSES = {"contrary", "hostile", "unknown → decided", "unknown → pinned"}


def section(text: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return match.group(1) if match else ""


def table_rows(body: str) -> list[list[str]]:
    rows = []
    for line in body.splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*-", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows[1:]  # drop the header


def lint(spec_path: Path) -> list[str]:
    text = spec_path.read_text(encoding="utf-8")
    problems = [f"missing section: {title}" for title in SECTIONS if not section(text, title).strip()]
    suite_ref = re.search(r"^Suite: `([^`]+)`", text, re.M)
    mutants_ref = re.search(r"Mutants:\s*`([^`]+)`", text)
    if not suite_ref or not mutants_ref:
        return problems + ["spec must name Suite: `...` and Mutants: `...`"]
    suite = (ROOT / suite_ref.group(1)).read_text(encoding="utf-8")
    # Data-driven suites name their scenarios in scenarios/*.json.
    suite += "".join(f"[{json.loads(p.read_text(encoding='utf-8')).get('id')}]"
                     for p in (Path(__file__).parent / "scenarios").glob("*.json"))
    mutants = {m["id"]: m for m in json.loads((ROOT / mutants_ref.group(1)).read_text(encoding="utf-8"))["mutants"]}

    scenarios = {}
    for row in table_rows(section(text, "Scenarios")):
        if len(row) < 3 or not re.fullmatch(r"[A-Z]\d+", row[0]):
            problems.append(f"malformed scenario row: {row}")
            continue
        scenarios[row[0]] = row
        if not row[2]:
            problems.append(f"{row[0]} has no failure signal")
        if f"[{row[0]}]" not in suite:
            problems.append(f"{row[0]} is not tested in {suite_ref.group(1)}")

    answers = re.findall(r"^(\d)\. ", section(text, "Review"), re.M)
    if answers != ["1", "2", "3", "4", "5"]:
        problems.append("Review must answer the five questions, numbered 1-5")

    named = set()
    for row in table_rows(section(text, "Adversarial")):
        if len(row) < 4:
            problems.append(f"malformed adversarial row: {row}")
            continue
        rid, cls, _condition, covered = row[:4]
        if cls not in CLASSES:
            problems.append(f"{rid}: unknown class {cls!r}")
        cited = [token for token in re.findall(r"\b[A-Z]\d+\b", covered) if token in scenarios]
        if not cited:
            problems.append(f"{rid}: coverage cites no scenario")
        for mid in re.findall(r"mutant `([^`]+)`", covered):
            named.add(mid)
            if mid not in mutants:
                problems.append(f"{rid}: mutant {mid} is not in the mutants file")
            elif mutants[mid].get("killed_by") not in cited:
                problems.append(f"{rid}: mutant {mid} killed_by {mutants[mid].get('killed_by')} but row cites {cited}")
    problems += [f"mutant {mid} is not named in the spec" for mid in sorted(set(mutants) - named)]
    return problems


def main() -> int:
    failed = False
    for arg in sys.argv[1:]:
        problems = lint(Path(arg))
        for problem in problems:
            print(f"{arg}: {problem}")
        failed = failed or bool(problems)
    if not failed:
        print("spec lint: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
