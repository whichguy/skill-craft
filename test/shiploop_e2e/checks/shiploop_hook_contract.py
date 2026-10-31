#!/usr/bin/env python3
"""Check the selected ShipLoop package's incomplete-loop keepalive contract.

The E2E runner calls this from ``work/`` with ``E2E_CHECKS`` set. It uses the
fixture's synthetic declarations to reach one document action, then tests the
selected package's real Until Loop runtime, hook decision, and callback gates.
This is a capability check, not evidence that a model naturally stopped early
or that the hello application itself improved.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any


class ContractFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ContractFailure(message)


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_signature(root: Path) -> tuple[dict[str, tuple[str, int]], str]:
    """Map regular package files to (content hash, executable mode), excluding interpreter caches."""
    if root.is_symlink() or not root.is_dir():
        fail(f"package directory is missing or a symlink: {root}")
    entries: dict[str, tuple[str, int]] = {}
    for here, folders, names in os.walk(root, followlinks=False):
        base = Path(here)
        for folder in list(folders):
            child = base / folder
            if child.is_symlink():
                fail(f"package contains a symlink directory: {child.relative_to(root)}")
            if folder == "__pycache__":
                folders.remove(folder)
        for name in names:
            path = base / name
            if path.suffix == ".pyc":
                continue
            if path.is_symlink() or not path.is_file():
                fail(f"package contains a non-regular entry: {path.relative_to(root)}")
            mode = stat.S_IMODE(path.stat().st_mode)
            entries[path.relative_to(root).as_posix()] = (digest_file(path), mode)
    signature_bytes = "".join(f"{name}\0{entries[name][0]}\0{entries[name][1]:04o}\n"
                               for name in sorted(entries)).encode()
    return entries, hashlib.sha256(signature_bytes).hexdigest()


def runner_tree_digest(root: Path) -> str:
    """Match run.py's 12-hex package digest over file paths and bytes."""
    entries, _ = tree_signature(root)
    value = "".join(f"{name}\0{entries[name][0]}\n" for name in sorted(entries, key=Path)).encode()
    return hashlib.sha256(value).hexdigest()[:12]


def same_tree(wanted: Path, actual: Path) -> tuple[str, str]:
    wanted_entries, wanted_sig = tree_signature(wanted)
    actual_entries, actual_sig = tree_signature(actual)
    if wanted_entries != actual_entries:
        names = sorted(set(wanted_entries) | set(actual_entries))
        changed = next((name for name in names if wanted_entries.get(name) != actual_entries.get(name)), "unknown")
        fail(f"installed package differs from wanted package at {changed}")
    return wanted_sig, actual_sig


def resolve_work(raw: str) -> Path:
    try:
        return Path(raw).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        fail(f"invocation cwd cannot be resolved: {exc}")


def locate_invocation(work: Path, override: str | None) -> tuple[Path, dict[str, Any]]:
    if override:
        candidates = [Path(override).expanduser().resolve()]
    else:
        candidates = [parent / "invocation.json" for parent in (work, *work.parents)]
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fail(f"invocation identity is unreadable at {path}: {exc}")
        if not isinstance(record, dict):
            fail(f"invocation identity is not an object at {path}")
        recorded = record.get("cwd")
        if isinstance(recorded, str) and resolve_work(recorded) == work:
            matches.append((path.resolve(), record))
        elif override:
            fail("test-only invocation override does not identify this checked delivery's cwd")
    if len(matches) != 1:
        fail("matching invocation identity is unknown or ambiguous; expected one ancestor invocation.json whose cwd "
             "is the checked delivery")
    path, record = matches[0]
    if not override and path.parent not in work.parents:
        fail("matching invocation.json is not an ancestor of the checked delivery")
    return path, record


def package_identity(invocation: dict[str, Any]) -> tuple[Path, Path, dict[str, Any]]:
    wanted_raw = invocation.get("plugin_dir")
    versions = invocation.get("versions")
    recorded_digest = versions.get("plugin_sha256") if isinstance(versions, dict) else None
    if not isinstance(wanted_raw, str) or not wanted_raw or not isinstance(recorded_digest, str):
        fail("selected package identity is unknown: invocation lacks plugin_dir or versions.plugin_sha256")
    wanted = Path(wanted_raw).expanduser().resolve()
    actual_record = invocation.get("plugin")
    host = invocation.get("host")
    if host in ("codex", "grok"):
        if not isinstance(actual_record, dict) or actual_record.get("pass") is not True:
            fail(f"selected {host} installation identity is unknown: plugin.pass is not true")
        actual_raw = actual_record.get("path")
        if not isinstance(actual_raw, str) or not actual_raw:
            fail(f"selected {host} installation identity is unknown: plugin.path is absent")
        actual = Path(actual_raw).expanduser().resolve()
    elif host == "claude":
        # Claude loads the exact package named on its recorded --plugin-dir argv.
        argv = invocation.get("argv")
        names_wanted = any(str(part) == str(wanted) for part in (argv or [])) if isinstance(argv, list) else False
        flags_wanted = any(str(part) == "--plugin-dir=" + str(wanted) for part in (argv or [])) \
            if isinstance(argv, list) else False
        pair_wanted = isinstance(argv, list) and any(
            str(argv[index]) == "--plugin-dir" and index + 1 < len(argv)
            and Path(str(argv[index + 1])).expanduser().resolve() == wanted
            for index in range(len(argv)))
        if not (names_wanted or flags_wanted or pair_wanted):
            fail("selected Claude package identity is unknown: recorded argv does not name plugin_dir")
        actual = wanted
    else:
        fail(f"selected package identity is unknown for host {host!r}")
    if runner_tree_digest(wanted) != recorded_digest:
        fail("wanted frozen package no longer matches invocation versions.plugin_sha256")
    wanted_sig, actual_sig = same_tree(wanted, actual)
    if wanted_sig != actual_sig:
        fail("installed package signature differs from the wanted frozen package")
    return wanted, actual, {"host": host, "plugin_dir": str(wanted), "installed_path": str(actual),
                            "plugin_sha256": recorded_digest, "signature_sha256": actual_sig}


def load_selected_modules(actual_plugin: Path) -> tuple[Path, dict[str, Any]]:
    skill = actual_plugin / "skills" / "shiploop"
    scripts = skill / "scripts"
    if not scripts.is_dir():
        fail(f"selected package has no ShipLoop scripts directory: {scripts}")
    sys.path.insert(0, str(scripts))
    modules: dict[str, Any] = {}
    for name in ("shiploop_navigator", "shiploop_store", "shiploop_loops", "shiploop_keepalive",
                 "shiploop_protocol"):
        module = importlib.import_module(name)
        origin = Path(str(module.__file__)).resolve()
        try:
            origin.relative_to(scripts.resolve())
        except ValueError:
            fail(f"{name} was imported outside the selected package: {origin}")
        modules[name] = module
    return skill, modules


def snapshot(driver: Any, receipt: Path, state_file: str | None) -> dict[str, Any]:
    files = {"state.md": driver.run_dir / "state.md", "receipt": receipt}
    for relative in driver.PATHS:
        files["product/" + relative] = driver.repo / relative
    if state_file:
        files["loop_state"] = Path(state_file)
    result: dict[str, Any] = {}
    for label, path in files.items():
        result[label] = {"exists": path.is_file(), "sha256": digest_file(path) if path.is_file() else None}
    return result


def run_argv(argv: Any, input_text: str, *, label: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
        fail(f"runtime receipt has no valid {label}")
    try:
        return subprocess.run(argv, input=input_text, text=True, capture_output=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        fail(f"Until Loop {label} did not finish within {timeout} seconds")


def callback_observations(keepalive: Any, host: str, binding: dict[str, Any], *, action_id: str,
                          callback: str | None, done_argv: list[str] | None,
                          driver: Any, receipt: Path, state_file: str | None,
                          before: dict[str, Any]) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    errors: list[str] = []
    progress_before = keepalive.run_status(binding["run_dir"]).get("progress")
    for index in range(3):
        decision = keepalive._decide(host, "hook-contract-probe", binding)
        reason = str(decision.get("reason") or "")
        record = {"attempt": index + 1, "decision": decision.get("decision"),
                  "why": decision.get("why"), "reason": reason}
        decisions.append(record)
        if decision.get("decision") != "continue":
            errors.append(f"decision {index + 1} was {decision.get('decision')!r}: {decision.get('why', 'no reason')}")
        if action_id not in reason:
            errors.append(f"reason {index + 1} omits current action {action_id}")
        if done_argv is not None and shlex.join(done_argv) not in reason:
            errors.append(f"reason {index + 1} omits the active loop's current done argv")
        if callback is not None and callback not in reason:
            errors.append(f"reason {index + 1} omits the pending stage callback")
    after = snapshot(driver, receipt, state_file)
    if before != after:
        errors.append("keepalive decisions changed product, state, receipt, or loop-state bytes")
    progress_after = keepalive.run_status(binding["run_dir"]).get("progress")
    if progress_before != progress_after:
        errors.append("run progress changed during unchanged-progress hook decisions")
    return {"decisions": decisions, "errors": errors, "snapshot_after": after,
            "progress_before": progress_before, "progress_after": progress_after}


def write_receipt(path: Path | None, receipt: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_probe(invocation: dict[str, Any], selected: Path, modules: dict[str, Any],
              record_phase: Any) -> dict[str, Any]:
    check_dir = Path(os.environ.get("E2E_CHECKS", "")).resolve()
    test_dir = check_dir.parent.parent
    fixture_path = test_dir / "shiploop_inner_fixture.py"
    loop_support_path = test_dir / "shiploop_loop_support.py"
    if not fixture_path.is_file() or not loop_support_path.is_file():
        fail("frozen operator inner fixture/runtime scaffolding is unavailable")
    sys.path.insert(0, str(test_dir))
    import shiploop_inner_fixture as fx  # noqa: E402
    import shiploop_loop_support as loop_support  # noqa: E402

    # The fixture supplies synthetic prior-stage declarations; its gates and loop calls use these selected modules.
    skill = selected / "skills" / "shiploop"
    improve_skill = selected / "skills" / "improve" / "SKILL.md"
    if not improve_skill.is_file():
        fail("selected package's Improve SKILL.md is unavailable")
    fx.CORE = types.SimpleNamespace(PACKAGE_ROOT=skill, REF_DIR=skill / "references")

    scratch = tempfile.TemporaryDirectory(prefix="shiploop-hook-contract-")
    driver = fx.RunDriver()
    original_home = modules["shiploop_keepalive"].home
    try:
        driver.setUp()
        private_home = Path(scratch.name) / "keepalive"
        modules["shiploop_keepalive"].home = lambda: private_home
        driver.start(str(improve_skill.resolve()))
        state = driver.drive_to("document")
        current = modules["shiploop_loops"].cursor(state)
        if current is None or current[0] != "document":
            fail("synthetic fixture did not reach one document inner action after its implement work")
        action_id = current[1]
        if driver.action() != action_id:
            fail("current action token differs from the selected inner implement action")
        receipt_path = modules["shiploop_loops"].receipt_path(driver.run_dir, action_id)
        contract_path = driver.run_dir / modules["shiploop_loops"].contract_path(action_id)
        if not contract_path.is_file():
            fail("the selected implement action has no saved Until Loop contract")
        block = loop_support.LoopBlock.find(driver.packet())
        if block is None or not block.command:
            fail("the selected implement packet has no Until Loop start command")
        bound = modules["shiploop_loops"].runtime(state)
        expected_start = modules["shiploop_loops"].start_command(bound, receipt_path, contract_path)
        if block.command != expected_start:
            fail("packet Until Loop start command does not match selected runtime and saved contract")
        start_packet = block.run(driver.repo)
        if not isinstance(start_packet, dict) or start_packet.get("status") != "active":
            fail("selected Until Loop runtime did not start an active loop")
        active = json.loads(receipt_path.read_text(encoding="utf-8"))
        if active.get("status") != "active" or not isinstance(active.get("done_argv"), list):
            fail("selected Until Loop runtime did not record an active done argv")
        active_snapshot = snapshot(driver, receipt_path, active.get("state_file"))
        if not active_snapshot["loop_state"]["exists"]:
            fail("active Until Loop state file is absent")

        invalid_before = active_snapshot
        invalid = run_argv(active["done_argv"], "{}\n", label="invalid done report")
        invalid_after = snapshot(driver, receipt_path, active.get("state_file"))
        invalid_errors = []
        if invalid.returncode == 0:
            invalid_errors.append("Until Loop runtime accepted an invalid done report")
        if invalid_before != invalid_after:
            invalid_errors.append("refused invalid done report changed product, state, receipt, or loop-state bytes")
        record_phase({"phase": "invalid_done_report", "action_id": action_id,
                      "returncode": invalid.returncode, "before": invalid_before,
                      "after": invalid_after, "errors": invalid_errors, "status": "fail" if invalid_errors else "pass"})
        if invalid_errors:
            fail(invalid_errors[0])

        keepalive = modules["shiploop_keepalive"]
        host = str(invocation.get("host"))
        if host not in keepalive.HOSTS:
            fail(f"selected hook host is unknown: {host}")
        status = keepalive.run_status(str(driver.run_dir))
        if status.get("error") or status.get("status") != "active":
            fail("selected keepalive cannot read the fixture run while its Until Loop is active")
        binding: dict[str, Any] = {"run_dir": str(driver.run_dir), "run_id": status.get("run_id"),
                                   "last_block_progress": status.get("progress"), "turn_blocks": 0}
        active_probe = callback_observations(keepalive, host, binding, action_id=action_id, callback=None,
                                             done_argv=active["done_argv"], driver=driver, receipt=receipt_path,
                                             state_file=active.get("state_file"), before=active_snapshot)
        record_phase({"phase": "active_loop_missing_done", "action_id": action_id,
                      "binding": {"run_id_sha256": hashlib.sha256(str(status.get("run_id", "")).encode()).hexdigest(),
                                  "progress": status.get("progress")},
                      "snapshot_before": active_snapshot,
                      **active_probe, "status": "fail" if active_probe["errors"] else "pass"})
        if active_probe["errors"]:
            fail(active_probe["errors"][0])

        report = loop_support._report("done", "truthful fixture: prior synthetic implement work satisfies its saved conditions")
        terminal_result = run_argv(active["done_argv"], report, label="truthful fixture done report")
        if terminal_result.returncode != 0:
            fail("selected Until Loop runtime refused the truthful fixture terminal report")
        terminal = json.loads(receipt_path.read_text(encoding="utf-8"))
        if terminal.get("status") != "complete" or terminal.get("done_argv") is not None:
            fail("selected Until Loop runtime did not write a terminal receipt")
        pending_state = driver.state()
        if driver.action() != action_id or modules["shiploop_loops"].cursor(pending_state) is None:
            fail("terminal Until Loop advanced or changed the pending stage action before its callback")
        terminal_snapshot = snapshot(driver, receipt_path, terminal.get("state_file"))
        if terminal_snapshot["loop_state"]["exists"]:
            fail("terminal Until Loop retained its runtime state file")
        terminal_status = keepalive.run_status(str(driver.run_dir))
        if terminal_status.get("error") or terminal_status.get("status") != "active":
            fail("selected keepalive cannot read the fixture run while its stage callback is pending")
        binding["last_block_progress"] = terminal_status.get("progress")
        binding["turn_blocks"] = 0
        callback = modules["shiploop_navigator"]._callback(
            fx.CORE, driver.run_dir, "complete", action=action_id)
        terminal_probe = callback_observations(keepalive, host, binding, action_id=action_id,
                                               callback=callback, done_argv=None, driver=driver,
                                               receipt=receipt_path, state_file=terminal.get("state_file"),
                                               before=terminal_snapshot)
        record_phase({"phase": "terminal_loop_missing_stage_callback", "action_id": action_id,
                      "binding": {"run_id_sha256": hashlib.sha256(
                          str(terminal_status.get("run_id", "")).encode()).hexdigest(),
                                  "progress": terminal_status.get("progress")},
                      "snapshot_before": terminal_snapshot,
                      "pending_callback": callback, **terminal_probe,
                      "status": "fail" if terminal_probe["errors"] else "pass"})
        if terminal_probe["errors"]:
            fail(terminal_probe["errors"][0])

        history_before = list(pending_state.get("history") or [])
        accepted = driver.complete({"outcome": "done", "summary": "Synthetic fixture document result.",
                                    "knowledge": dict(fx.KNOWLEDGE_NONE)},
                                   prepare_inner=False)
        after_callback = driver.state()
        history_after = list(after_callback.get("history") or [])
        old_count_before = sum(row.get("action") == action_id for row in history_before if isinstance(row, dict))
        old_count_after = sum(row.get("action") == action_id for row in history_after if isinstance(row, dict))
        if old_count_after != old_count_before:
            fail("stage callback created an accepted history entry before its separate Improve review completed")
        child = after_callback.get("active_improve")
        if (not isinstance(child, dict) or child.get("stage") != "document"
                or child.get("action_id") != action_id or child.get("seed_result", {}).get("outcome") != "done"):
            fail("accepted stage callback did not leave its result pending in the separate Improve review")
        product_after_callback = {name: row for name, row in snapshot(driver, receipt_path, None).items()
                                  if name.startswith("product/")}
        product_expected = {name: row for name, row in terminal_snapshot.items() if name.startswith("product/")}
        if product_after_callback != product_expected:
            fail("accepted stage callback changed the partial product")
        child_action = child.get("improve_action")
        if not child_action or child_action == action_id:
            fail("the Improve review does not have a distinct pending child action")
        record_phase({"phase": "accepted_stage_callback", "action_id": action_id,
                      "callback_output_sha256": hashlib.sha256(accepted.encode()).hexdigest(),
                      "history_entries_for_action": old_count_after,
                      "improve_review_action": child_action,
                      "review_pending": True, "partial_product_preserved": True, "status": "pass"})

        # Finish the fixture's separate review through its existing synthetic fixture helper.
        driver.finish_improve()
        final_state = driver.state()
        final_count = sum(row.get("action") == action_id for row in final_state.get("history", [])
                          if isinstance(row, dict))
        if final_count != old_count_before + 1 or final_state.get("active_improve") is not None \
                or driver.action() == action_id:
            fail("finishing the separate Improve review did not advance the action exactly once")
        final_product = {name: row for name, row in snapshot(driver, receipt_path, None).items()
                         if name.startswith("product/")}
        if final_product != product_expected:
            fail("finishing the separate Improve review changed the partial product")
        record_phase({"phase": "fixture_improve_review_finished", "action_id": action_id,
                      "review_action": child_action, "history_entries_for_action": final_count,
                      "partial_product_preserved": final_product == product_expected, "status": "pass"})
        return {"fixture_run_id_sha256": hashlib.sha256(
                    str(state.get("run_id", "")).encode()).hexdigest(),
                "action_id": action_id,
                "scope": "synthetic prior-stage declarations, implement work, and fixture knowledge/proof defaults; "
                         "selected package modules, Until Loop runtime, keepalive decisions, and real callback gates"}
    finally:
        modules["shiploop_keepalive"].home = original_home
        try:
            driver.doCleanups()
        finally:
            scratch.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocation-file", help="test-only offline calibration input; final E2E case uses ancestor lookup")
    args = parser.parse_args()
    work = Path.cwd().resolve()
    report: dict[str, Any] = {"schema": "shiploop-hook-contract/v1", "verdict": "unknown",
                              "work_cwd": str(work),
                              "scope": "Capability probe with synthetic fixture stages and fixture knowledge/proof defaults; "
                                       "not a live model-behavior or hello-app claim.",
                              "phases": [], "failure_or_unknown": None}
    receipt_path: Path | None = None
    try:
        invocation_path, invocation = locate_invocation(work, args.invocation_file)
        receipt_path = invocation_path.parent / "shiploop-hook-contract-receipt.json"
        report["invocation"] = {"path": str(invocation_path), "case": invocation.get("case"),
                                "host": invocation.get("host"), "cwd": invocation.get("cwd")}
        wanted, actual, identity = package_identity(invocation)
        report["package"] = identity
        before_entries, before_signature = tree_signature(actual)
        _skill, modules = load_selected_modules(actual)
        report["selected_modules"] = {name: str(Path(module.__file__).resolve()) for name, module in modules.items()}
        check_dir = Path(os.environ.get("E2E_CHECKS", "")).resolve()
        test_dir = check_dir.parent.parent
        sys.path.insert(0, str(test_dir))
        def record_phase(phase: dict[str, Any]) -> None:
            report["phases"].append(phase)
            write_receipt(receipt_path, report)

        result = run_probe(invocation, actual, modules, record_phase)
        after_entries, after_signature = tree_signature(actual)
        if before_entries != after_entries or before_signature != after_signature:
            fail("selected installed package changed during the conformance probe")
        if runner_tree_digest(wanted) != identity["plugin_sha256"]:
            fail("wanted package digest changed during the conformance probe")
        report["fixture_run_id_sha256"] = result["fixture_run_id_sha256"]
        report["action_id"] = result["action_id"]
        report["fixture_scope"] = result["scope"]
        report["package_signature_before_sha256"] = before_signature
        report["package_signature_after_sha256"] = after_signature
        report["verdict"] = "pass"
        print("PASS: selected ShipLoop package continued the pending action through active and terminal loop states")
        return 0
    except ContractFailure as exc:
        report["failure_or_unknown"] = str(exc)
        report["verdict"] = "fail"
        print("FAIL: " + str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 - unknown identity or harness mismatch must never pass
        report["failure_or_unknown"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        report["verdict"] = "fail"
        print("FAIL: conformance probe could not establish a passing result: " + report["failure_or_unknown"])
        return 1
    finally:
        write_receipt(receipt_path, report)


if __name__ == "__main__":
    raise SystemExit(main())
