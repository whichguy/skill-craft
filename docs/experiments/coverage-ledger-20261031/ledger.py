#!/usr/bin/env python3
"""Offline coverage ledger over archived ShipLoop runs: does every requirement a run's spec added or changed end with a
test ShipLoop saw pass?

Question (owner, 2026-10-31): do the step tests, taken together at the end of a run, cover what the spec defined, or
does ShipLoop need an end-of-run re-anchoring of the tests on the spec?  Before building anything, measure the gap on
runs that already exist.  Nothing here runs a model or changes a run; it reads each run's state with ShipLoop's own
readers (``shiploop_store``, ``shiploop_planning_revision.current_actions``, ``shiploop_knowledge_home._entries``) and
ShipLoop's own test records (``tests/<action>-verify<N>.md``), the same sources the primary-requirement gate
(``shiploop_primary.passed_cases``) reads.

Per run:

- changed requirements: the R-<n> entries of ``docs/shiploop/spec.md`` added, or changed in text, between the run's
  baseline commit (``RUN/run-baseline.txt``) and the run's final checkout; retired entries are counted apart.
- per changed requirement, its end state, the first that applies:
  - ``inner``: a current test-spec case whose ``requirement`` field names it, and whose ID an accepted inner action's
    passed test record lists;
  - ``inner-criterion``: the same, but only the case's step-plan criterion names it (ranges such as "R-1 through R-4"
    expanded); the case's own ``requirement`` field names another ID.  ShipLoop's ``passed_cases`` reads only the field;
  - ``case-unseen``: a current test-spec case for it exists, but no passed inner record lists its ID;
  - ``system``: no inner case, but system-test-author's catalog (its summary) ties a system command ID to it and the
    system-test stage was accepted (ShipLoop refuses system-test done unless every recorded command passes);
  - ``unverified``: product-acceptance lists it in ``unverified``;
  - ``none``: nothing above: a requirement the run changed that ends with no test and no recorded reason.
- implement's ``not_covered`` rows (behaviour the code added that no case covers) and whether a sub-case ID
  (``<ID> (<letter>)``) for them shows in a passed record.

Usage: ``python3 ledger.py [--json OUT] [RUN_DIR ...]``; without run dirs it finds every archived run under the
E2E output roots that reached product-acceptance, skipping test-fixture copies and seeded slices.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_knowledge_home as knowledge
import shiploop_planning_revision as planning_revision
import shiploop_store as store
import shiploop_test_loop as test_loop

ROOTS = ("~/e2e-runs", "~/e2e-runs-brownfield", "~/e2e-runs-qr", "~/e2e-runs-x4", "~/e2e-runs-owner-note")
SPEC = knowledge.HOME + "/spec.md"
_SUBCASE = re.compile(r"\(\s*[a-z]\s*\)")
# "R-1 through R-4", "R-1 to R-3", "R-1..R-5", "R-1–R-3": knowledge.requirement_ids reads only the two ends.
_RANGE = re.compile(r"\bR-(\d+)\s*(?:through|thru|to|\.\.|–|—)\s*R-(\d+)\b")


def named(text: str) -> list[str]:
    """The requirement IDs a text names, ranges expanded, each once, in numeric order."""
    found = set(knowledge.requirement_ids(text))
    for low, high in _RANGE.findall(text):
        if int(low) < int(high) <= int(low) + 50:
            found |= {"R-" + str(number) for number in range(int(low), int(high) + 1)}
    return sorted(found, key=lambda value: int(value.split("-")[1]))


def find_runs() -> list[Path]:
    """Every archived run directory (the one holding state.md) that reached product-acceptance."""
    found = []
    for base in ROOTS:
        for path in glob.glob(os.path.expanduser(base) + "/**/.shiploop-runs/*/run/state.md", recursive=True):
            if "/test/fixtures/" in path or "/slice/" in path:
                continue
            try:
                state = store.read_record(Path(path))
            except (OSError, store.StorageError):
                continue
            if any(row.get("stage") == "product-acceptance" and row.get("outcome") == "done"
                   for row in state.get("history") or () if isinstance(row, Mapping)):
                found.append(Path(path).parent)
    return sorted(found)


def _git_show(repo: Path, rev: str, name: str) -> str | None:
    done = subprocess.run(["git", "-C", str(repo), "show", rev + ":" + name], check=False, capture_output=True,
                          text=True)
    return done.stdout if done.returncode == 0 else None


def changed_requirements(root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    """The R-<n> entries the run added or changed, from the baseline commit to the final checkout."""
    repo = Path(str(state.get("repo") or ""))
    baseline_file = root / knowledge.RUN_BASELINE
    if not baseline_file.is_file():
        return {"error": "no run baseline"}
    baseline = baseline_file.read_text().strip()
    before_text = _git_show(repo, baseline, SPEC)
    after_path = repo / SPEC
    after_text = after_path.read_text(encoding="utf-8", errors="replace") if after_path.is_file() else None
    if after_text is None:
        after_text = _git_show(repo, "HEAD", SPEC)
    if after_text is None:
        return {"error": "no final spec"}
    before = knowledge._entries(before_text, "R") if before_text and before_text.strip() else {}
    after = knowledge._entries(after_text, "R")
    added = [ident for ident in after if ident not in before and not after[ident].retired]
    changed = [ident for ident in after if ident in before and before[ident].text != after[ident].text
               and not after[ident].retired]
    retired = [ident for ident in after if after[ident].retired and (ident not in before or not before[ident].retired)]
    return {"added": added, "changed": changed, "retired": retired, "total": len(after),
            "text": {ident: after[ident].text for ident in added + changed}}


def _passed_ids(root: Path, state: Mapping[str, Any], inner: bool) -> set:
    """Test IDs a passed run in ShipLoop's records lists: of accepted inner actions (``inner``), else of outer ones."""
    found: set = set()
    actions = dict.fromkeys(str(row.get("action")) for row in state.get("history") or ()
                            if isinstance(row, Mapping) and row.get("outcome") == "done"
                            and bool(row.get("workitem")) == inner)
    for action in actions:
        number = 1
        while (root / test_loop.verify_path(action, number)).is_file():
            try:
                record = store.read_record(root / test_loop.verify_path(action, number))
            except (OSError, store.StorageError):
                record = None
            number += 1
            if not isinstance(record, Mapping) or not record.get("passed"):
                continue
            for run in record.get("runs") or ():
                if isinstance(run, Mapping) and run.get("status") == "passed":
                    missing = {str(ident) for ident in run.get("ids_missing") or ()}
                    found |= {str(ident) for ident in run.get("ids") or () if str(ident) not in missing}
    return found


def _items(state: Mapping[str, Any]) -> list[str]:
    """Every work item ID, current queue and completed, in order, once."""
    names: list[str] = []
    for key in ("completed_work_items", "work_items"):
        for row in state.get(key) or ():
            ident = str(row.get("id")) if isinstance(row, Mapping) else str(row)
            if ident and ident not in names:
                names.append(ident)
    return names


def ledger(root: Path) -> dict[str, Any]:
    state = store.read_record(root / "state.md")
    current = planning_revision.current_actions(state)
    accepted = state.get("accepted") or {}

    def result(item: str | None, stage: str) -> Mapping[str, Any]:
        action = current.get((item, stage))
        value = accepted.get(action) if action else None
        return value if isinstance(value, Mapping) else {}

    spec = changed_requirements(root, state)
    primary = [str(ident) for ident in result(None, "spec").get("primary") or ()]
    inner_passed = _passed_ids(root, state, inner=True)
    outer_passed = _passed_ids(root, state, inner=False)

    items = _items(state)
    queue_items = [str(row.get("id")) for row in state.get("work_items") or () if isinstance(row, Mapping)]
    cases: dict[str, list[dict[str, Any]]] = {}
    case_count = 0
    multi_field = 0   # cases whose own requirement field names two or more IDs
    for item in items:
        criteria = {str(row.get("id")): str(row.get("text") or "")
                    for row in result(item, "step-plan").get("criteria") or () if isinstance(row, Mapping)}
        for case in result(item, "test-spec").get("test_cases") or ():
            if not isinstance(case, Mapping):
                continue
            case_count += 1
            ident = str(case.get("id"))
            by_field = knowledge.requirement_ids(str(case.get("requirement") or ""))
            multi_field += len(by_field) >= 2
            by_criterion = [requirement for name in re.findall(r"[\w-]+", str(case.get("criterion") or ""))
                            for requirement in named(criteria.get(name, "")) if requirement not in by_field]
            for requirement in by_field + by_criterion:
                rows = cases.setdefault(requirement, [])
                if any(row["id"] == ident for row in rows):
                    continue
                rows.append({"id": ident, "item": item, "passed": ident in inner_passed,
                             "in_queue": item in queue_items, "route": "field" if requirement in by_field else
                             "criterion"})

    author = result(None, "system-test-author")
    system_ids = sorted({str(ident) for row in author.get("system_commands") or () if isinstance(row, Mapping)
                         for ident in row.get("ids") or ()})
    inner_ids = {case["id"] for rows in cases.values() for case in rows}
    system_only = [ident for ident in system_ids if ident not in inner_ids]
    catalog = str(author.get("summary") or "")
    system_req: dict[str, list[str]] = {}
    for line in catalog.splitlines():
        hits = [ident for ident in system_only if re.search(r"(?<![\w-])" + re.escape(ident) + r"(?![\w-])", line)]
        for requirement in knowledge.requirement_ids(line) if hits else ():
            system_req.setdefault(requirement, []).extend(hit for hit in hits if hit not in system_req.get(requirement, []))
    system_accepted = bool(result(None, "system-test"))

    unverified = {}
    for row in result(None, "product-acceptance").get("unverified") or ():
        if isinstance(row, Mapping):
            for requirement in knowledge.requirement_ids(str(row.get("requirement") or "")):
                unverified[requirement] = str(row.get("reason") or "")[:200]

    rows = []
    for requirement in spec.get("added", []) + spec.get("changed", []):
        mine = cases.get(requirement, [])
        if any(case["passed"] and case["route"] == "field" for case in mine):
            end = "inner"
        elif any(case["passed"] for case in mine):
            end = "inner-criterion"
        elif mine:
            end = "case-unseen"
        elif system_req.get(requirement) and system_accepted:
            end = "system"
        elif requirement in unverified:
            end = "unverified"
        else:
            end = "none"
        text = spec.get("text", {}).get(requirement, "")
        rows.append({"requirement": requirement, "kind": "added" if requirement in spec.get("added", []) else "changed",
                     "primary": requirement in primary, "end": end,
                     "cases": [case["id"] for case in mine], "passed": [case["id"] for case in mine if case["passed"]],
                     "gate_sees": [case["id"] for case in mine if case["passed"] and case["in_queue"]],
                     "system": system_req.get(requirement, []), "unverified": unverified.get(requirement),
                     # the text only where a reader must judge the row (keeps the export compact)
                     "text": " ".join(text.split())[:240] if end in ("none", "case-unseen") else ""})

    not_covered = []
    for item in items:
        for row in state.get("history") or ():
            if not isinstance(row, Mapping) or row.get("workitem") != item or row.get("stage") != "implement" \
                    or row.get("outcome") != "done":
                continue
            for gap in (accepted.get(row.get("action")) or {}).get("not_covered") or ():
                if isinstance(gap, Mapping):
                    not_covered.append({"item": item, "behaviour": " ".join(str(gap.get("behaviour", "")).split())[:200],
                                        "reason": " ".join(str(gap.get("reason", "")).split())[:160]})
    subcases = sorted(ident for ident in inner_passed if _SUBCASE.search(ident))

    return {"run": str(root), "version": state.get("version"), "status": state.get("status"),
            "items": items, "queue_items": queue_items, "spec": {key: spec.get(key) for key in
                                                                  ("added", "changed", "retired", "total", "error")},
            "primary": primary, "test_cases": case_count, "multi_field_cases": multi_field, "inner_passed": len(inner_passed),
            "outer_passed": len(outer_passed), "system_ids": system_ids, "system_accepted": system_accepted,
            "rows": rows, "not_covered": not_covered, "subcases_passed": subcases,
            "unverified_rows": len(result(None, "product-acceptance").get("unverified") or ())}


def label(run: str) -> str:
    text = run.replace(os.path.expanduser("~"), "~")
    return re.sub(r"/\.shiploop-runs/[^/]+/run$", "", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="*")
    parser.add_argument("--json")
    args = parser.parse_args()
    runs = [Path(run) for run in args.runs] or find_runs()
    out = []
    for root in runs:
        try:
            out.append(ledger(root))
        except Exception as error:  # noqa: BLE001 - a run shape this reader does not know: report it, never skip it
            out.append({"run": str(root), "error": type(error).__name__ + ": " + str(error)[:200]})
    for entry in out:
        print("==", label(entry["run"]), entry.get("version"), entry.get("status"), "items", entry.get("items"))
        if "error" in entry:
            print("   ERROR", entry["error"])
            continue
        spec = entry["spec"]
        print("   spec: added", spec.get("added"), "changed", spec.get("changed"), "retired", spec.get("retired"),
              spec.get("error") or "", "| primary", entry["primary"], "| cases", entry["test_cases"],
              "| inner passed IDs", entry["inner_passed"], "| system IDs", entry["system_ids"],
              "| unverified rows", entry["unverified_rows"])
        for row in entry["rows"]:
            print("   ", row["requirement"], row["kind"], "P" if row["primary"] else "-", row["end"].upper(),
                  "cases", row["cases"], "passed", row["passed"], "system", row["system"],
                  ("unverified: " + row["unverified"]) if row["unverified"] else "",
                  ("| gate sees " + str(row["gate_sees"])) if row["gate_sees"] != row["passed"] else "")
            if row["end"] in ("none", "case-unseen"):
                print("       text:", row["text"])
        for gap in entry["not_covered"]:
            print("    not_covered", gap["item"] + ":", gap["behaviour"], "|", gap["reason"])
        if entry["subcases_passed"]:
            print("    sub-cases passed:", entry["subcases_passed"])
    if args.json:
        Path(args.json).write_text(json.dumps([{**entry, "run": label(entry["run"])} for entry in out], indent=1,
                                              ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
