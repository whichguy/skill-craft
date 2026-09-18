#!/usr/bin/env python3
"""Read-only structural evidence summary for a ShipLoop planning case.

This reader deliberately reports callback packets as reported evidence.  A
complete terminal packet and its import prove neither review semantics nor the
product plan's correctness.  It executes the selected local ShipLoop package's
store and navigator validator as trusted package code; it is not a sandbox for
an untrusted package.  The reader itself does not mutate run state.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping


def _load_store(package: Path) -> Any:
    source = package / "scripts" / "shiploop_store.py"
    if not source.is_file():
        raise ValueError(f"selected package has no shiploop_store.py: {source}")
    spec = importlib.util.spec_from_file_location("ui_allocation_shiploop_store", source)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load selected shiploop_store.py: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_navigator(package: Path) -> Any:
    """Load navigator and its sibling modules from exactly the selected package."""
    scripts = package / "scripts"
    source = scripts / "shiploop_navigator.py"
    if not source.is_file():
        raise ValueError(f"selected package has no shiploop_navigator.py: {source}")
    names = ("shiploop_navigator", "shiploop_navigator_prompts", "shiploop_navigator_v3_prompts", "shiploop_consumer_delivery", "shiploop_store")
    prior = {name: sys.modules.pop(name, None) for name in names}
    sys.path.insert(0, str(scripts))
    try:
        module = importlib.import_module("shiploop_navigator")
        if Path(module.__file__).resolve() != source.resolve():
            raise ValueError("selected navigator resolved outside the selected package")
        return module
    finally:
        sys.path.pop(0)
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update({name: module for name, module in prior.items() if module is not None})


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _run_file(run: Path, relative: Path, label: str) -> Path:
    """Reject archive paths that traverse or follow links outside this run."""
    if run.is_symlink() or not run.is_dir() or relative.is_absolute():
        raise ValueError(f"unsafe {label} root or path")
    current = run
    for part in relative.parts:
        if part in ("", ".", ".."):
            raise ValueError(f"unsafe {label} path")
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} path contains a symlink")
    resolved_run = run.resolve(strict=True)
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(resolved_run)
    except ValueError as exc:
        raise ValueError(f"{label} path escapes run directory") from exc
    return current


def _archived_evidence(run: Path, value: Any, result: dict[str, Any]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        result["errors"].append("imported evidence is not a list")
        return
    sources = []
    for entry in value:
        if not isinstance(entry, Mapping):
            result["errors"].append("imported evidence has an invalid entry")
            continue
        source, archive, digest = entry.get("source"), entry.get("archive"), entry.get("sha256")
        sources.append({key: entry.get(key) for key in ("source", "archive", "sha256") if key in entry})
        source_path = Path(source) if isinstance(source, str) else None
        path = Path(archive) if isinstance(archive, str) else None
        if (not isinstance(source, str) or not source or not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
                or source_path is None or source_path.is_absolute()
                or any(part in ("", ".", "..") for part in source_path.parts)
                or path is None or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts)):
            result["errors"].append("imported evidence has unsafe or incomplete source identity")
            continue
        try:
            candidate = _run_file(run, path, "imported evidence archive")
        except ValueError as exc:
            result["errors"].append(str(exc))
            continue
        if not candidate.is_file():
            result["errors"].append("imported evidence archive is missing")
        elif _digest(candidate) != digest:
            result["errors"].append("imported evidence archive digest disagrees with identity")
    result["evidence_sources"] = sources


def _terminal_summary(run: Path, action: str, record: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"action_id": action, "structurally_valid": False, "errors": []}
    binding_id = record.get("binding_id")
    if not isinstance(binding_id, str) or not binding_id:
        result["errors"].append("import record has no binding_id")
        return result
    result["binding_id"] = binding_id
    result["binding_marker"] = f"ShipLoop standalone Improve binding: {binding_id}"
    try:
        terminal = _run_file(run, Path("improve") / action / "terminal.json", "terminal archive")
    except ValueError as exc:
        result["errors"].append(str(exc))
        return result
    result["terminal_path"] = str(terminal)
    if not terminal.is_file():
        result["errors"].append("real Improve import has no terminal.json archive")
        return result
    try:
        packet = json.loads(terminal.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result["errors"].append(f"terminal.json is unreadable: {exc}")
        return result
    if not isinstance(packet, Mapping):
        result["errors"].append("terminal.json is not an object")
        return result
    progress = _mapping(packet.get("progress"))
    context = _mapping(packet.get("context"))
    request = context.get("request") if context else None
    required = progress.get("required_trivial_reviews") if progress else None
    streak = progress.get("trivial_streak") if progress else None
    action_number = progress.get("action_number") if progress else None
    if packet.get("status") != "complete":
        result["errors"].append("terminal packet status is not complete")
    if not all(type(value) is int for value in (required, streak, action_number)):
        result["errors"].append("terminal packet has invalid review progress")
    elif required < 2 or streak < required or streak > action_number:
        result["errors"].append("terminal packet does not establish two consecutive trivial reviews")
    if not isinstance(request, str) or result["binding_marker"] not in request.splitlines():
        result["errors"].append("terminal packet lacks the bound Improve marker")
    result["terminal_sha256"] = _digest(terminal)
    result["progress"] = progress
    identities = _mapping(record.get("identities"))
    if not identities:
        result["errors"].append("real Improve import has no identities")
    else:
        result["identities"] = dict(identities)
    receipt = _mapping(record.get("receipt"))
    if receipt:
        result["receipt_refs"] = {
            key: receipt.get(key) for key in ("review_refs", "check_refs") if key in receipt
        }
    expected = identities.get("terminal_packet_sha256") if identities else None
    if not isinstance(expected, str) or len(expected) != 64:
        result["errors"].append("real Improve import has no terminal packet digest identity")
    elif expected != result["terminal_sha256"]:
        result["errors"].append("terminal packet digest disagrees with imported identity")
    _archived_evidence(run, record.get("evidence"), result)
    result["structurally_valid"] = not result["errors"]
    return result


def inspect_case(case_root: str | Path, package_path: str | Path) -> dict[str, Any]:
    """Summarize persisted navigator and imported-Improve structural evidence."""
    root = Path(case_root).resolve()
    run = root / "run"
    state_path = run / "state.md"
    report: dict[str, Any] = {
        "case_root": str(root),
        "callback_content": "reported evidence only; it does not prove semantics",
        "structurally_valid": True,
        "semantic_verification": False,
        "errors": [],
    }
    if not state_path.is_file():
        report["structurally_valid"] = False
        report["errors"].append("case has no persisted run/state.md")
        report.update(kind="missing-state", imports=[])
        return report
    try:
        package = Path(package_path).resolve()
        state = _load_store(package).read_record(state_path)
        navigator = _load_navigator(package)
        navigator.validate(state)
    except Exception as exc:  # StoreError type is package-owned.
        report["structurally_valid"] = False
        report["errors"].append(f"cannot read and validate persisted state.md: {exc}")
        report.update(kind="corrupt-unreadable-or-invalid", imports=[])
        return report
    if not isinstance(state, Mapping):
        report["structurally_valid"] = False
        report["errors"].append("persisted state.md is not an object")
        report.update(kind="corrupt-unreadable-or-invalid", imports=[])
        return report
    action = navigator.current_action(state)
    reported_stage = navigator.current_stage(state)
    report.update(
        kind="persisted-run",
        stage=reported_stage,
        parent_stage=state.get("stage"),
        status=state.get("status"),
        action_identity={key: action.get(key) for key in ("id", "stage")} if action else None,
        accepted_stage_record_count=len(state.get("accepted", {})) if isinstance(state.get("accepted"), Mapping) else None,
    )
    imports = state.get("improve_results")
    if imports is None:
        report["imports"] = []
        report["import_status"] = "no-imports-for-this-protocol"
        return report
    if not isinstance(imports, Mapping):
        report["structurally_valid"] = False
        report["errors"].append("improve_results is not an object")
        report["imports"] = []
        return report
    if not imports:
        report["imports"] = []
        report["import_status"] = "no-import-yet"
        return report
    summaries, predecessors = [], []
    for action_id, record in imports.items():
        if not isinstance(action_id, str) or not isinstance(record, Mapping):
            report["structurally_valid"] = False
            report["errors"].append("improve_results contains an invalid imported record")
            continue
        if record.get("kind") == "synthetic-fixture-predecessor":
            predecessors.append({
                "action_id": action_id, "kind": record["kind"], "claim": record.get("claim"),
                "stage": record.get("stage"), "seed_result": record.get("seed_result"),
            })
            continue
        if record.get("runtime_phase") != "complete":
            report["structurally_valid"] = False
            report["errors"].append(f"Improve import {action_id} is not complete")
        summary = _terminal_summary(run, action_id, record)
        summaries.append(summary)
        if not summary["structurally_valid"]:
            report["structurally_valid"] = False
            report["errors"].extend(f"{action_id}: {error}" for error in summary["errors"])
    report["imports"] = summaries
    report["synthetic_predecessors"] = predecessors
    report["import_status"] = "real-imports-observed" if summaries else "synthetic-predecessors-only"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_root")
    parser.add_argument("--package", required=True, help="selected ShipLoop package directory")
    args = parser.parse_args()
    report = inspect_case(args.case_root, args.package)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["structurally_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
