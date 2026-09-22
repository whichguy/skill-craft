#!/usr/bin/env python3
"""Qualify ShipLoop's offline native-pilot composition against a chosen Dispatcher.

This is an opt-in local integration check.  It never resolves a branch, fetches
an upstream, or launches a model or native agent.  The caller supplies the
already-checked-out Dispatcher ``SKILL.md`` and receives a durable receipt in a
new directory outside both source checkouts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NATIVE_PILOT_TEST = ROOT / "test" / "experiments" / "shiploop_chain" / "test_native_pilot.py"
SCHEMA = "shiploop-current-dispatcher-qualification/v1"
RUN_TIMEOUT_SECONDS = 900
GIT_HEAD_RE = re.compile(r"^[0-9a-f]{40,64}$")


class QualificationError(ValueError):
    """An explicit integration boundary failed before it could be qualified."""


def fail(message: str) -> None:
    raise QualificationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def is_within(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def absolute_file(value: str, label: str) -> Path:
    requested = Path(value)
    if not requested.is_absolute():
        fail(f"{label} must be an absolute path")
    if requested.name != "SKILL.md":
        fail(f"{label} must name SKILL.md")
    if requested.is_symlink() or not requested.is_file():
        fail(f"{label} must be an existing regular file")
    try:
        return requested.resolve(strict=True)
    except OSError as exc:
        fail(f"cannot resolve {label}: {exc}")


def git_output(checkout: Path, *args: str, label: str) -> str:
    environment = os.environ.copy()
    # Snapshotting must not take an optional Git index lock in either selected
    # checkout.  This command never fetches, switches, restores, or commits.
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout), *args], text=True, capture_output=True,
            timeout=30, check=False, env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"cannot inspect {label} Git checkout: {exc}")
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        suffix = "" if not detail else f": {detail[:400]}"
        fail(f"cannot inspect {label} Git checkout" + suffix)
    return result.stdout


def repository_snapshot(location: Path, label: str, *, require_clean: bool) -> dict[str, Any]:
    checkout_text = git_output(location, "rev-parse", "--show-toplevel", label=label).strip()
    if not checkout_text:
        fail(f"{label} must be inside a Git checkout")
    checkout = Path(checkout_text).resolve()
    head = git_output(checkout, "rev-parse", "HEAD", label=label).strip()
    if GIT_HEAD_RE.fullmatch(head) is None:
        fail(f"{label} Git checkout has no immutable HEAD")
    repo_url = git_output(checkout, "remote", "get-url", "origin", label=label).strip()
    if not repo_url:
        fail(f"{label} Git checkout must define an origin URL")
    status = git_output(
        checkout, "status", "--porcelain=v1", "--untracked-files=all", "--no-renames", label=label,
    )
    if require_clean and status:
        fail(f"{label} Git checkout must be clean before qualification")
    working = git_output(checkout, "diff", "--binary", "--no-ext-diff", label=label)
    staged = git_output(checkout, "diff", "--cached", "--binary", "--no-ext-diff", label=label)
    return {
        "checkout": str(checkout),
        "repo_url": repo_url,
        "exact_head": head,
        "clean": not bool(status),
        "status_sha256": sha256_bytes(status.encode("utf-8")),
        "working_diff_sha256": sha256_bytes(working.encode("utf-8")),
        "staged_diff_sha256": sha256_bytes(staged.encode("utf-8")),
    }


def package_hashes(card: Path) -> dict[str, Any]:
    """Hash every selected-package file and reject links that escape the snapshot."""
    package = card.parent
    files: dict[str, str] = {}
    for item in sorted(package.rglob("*"), key=lambda path: path.as_posix()):
        relative = item.relative_to(package).as_posix()
        if relative.split("/", 1)[0] == ".git":
            continue
        if item.is_symlink():
            fail(f"selected dispatcher package contains a symlink: {relative}")
        if item.is_dir():
            continue
        if not item.is_file():
            fail(f"selected dispatcher package contains a non-regular path: {relative}")
        files[relative] = sha256_file(item)
    if files.get("SKILL.md") != sha256_file(card):
        fail("selected dispatcher package hash does not include SKILL.md")
    return {
        "package_root": str(package),
        "files": files,
        "aggregate_sha256": sha256_bytes(json_bytes(files)),
    }


def assert_unchanged(label: str, before: dict[str, Any], after: dict[str, Any]) -> None:
    if before != after:
        fail(f"{label} changed during qualification; preserve the receipt and inspect the selected checkout")


def capture_after_snapshot(callback: Any) -> dict[str, Any]:
    """Keep an output receipt even when a post-run mutation breaks inspection."""
    try:
        return callback()
    except QualificationError as exc:
        return {"inspection_error": str(exc)}


def new_output_path(value: str) -> Path:
    requested = Path(value)
    if not requested.is_absolute():
        fail("--output must be an absolute path")
    if os.path.lexists(requested):
        fail(f"--output must name a new directory; preserve the existing path: {requested}")
    try:
        return requested.resolve(strict=False)
    except OSError as exc:
        fail(f"cannot resolve --output: {exc}")


def require_output_outside(output: Path, checkout: Path, label: str) -> None:
    if is_within(checkout, output):
        fail(f"--output must be outside the {label} checkout")


def log_value(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def write_text(path: Path, value: str) -> dict[str, str]:
    path.write_text(value, encoding="utf-8")
    return {"path": str(path), "sha256": sha256_file(path)}


def qualification_command(card: Path) -> list[str]:
    return [sys.executable, "-B", str(NATIVE_PILOT_TEST), "--dispatcher-skill", str(card)]


def run_with_process_group(
    command: list[str], environment: dict[str, str], *, timeout_seconds: float = RUN_TIMEOUT_SECONDS,
) -> tuple[int, bool, str, str]:
    """Capture the test run and terminate its process group if its deadline expires."""
    try:
        process = subprocess.Popen(
            command, cwd=ROOT, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        fail(f"cannot start current Dispatcher qualification: {exc}")
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return process.returncode, False, stdout, stderr
    except subprocess.TimeoutExpired:
        group_id = process.pid
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        # The unittest parent can exit after TERM while one of its descendants
        # ignores TERM.  The group remains addressable even after its leader
        # exits, so force that survivor down before returning a timeout result.
        try:
            os.killpg(group_id, 0)
        except ProcessLookupError:
            pass
        else:
            try:
                os.killpg(group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return 124, True, log_value(stdout), log_value(stderr)


def run_qualification(dispatcher_card: Path, output: Path) -> tuple[dict[str, Any], int]:
    source_before = repository_snapshot(ROOT, "skill-craft source", require_clean=True)
    source_checkout = Path(source_before["checkout"])
    dispatcher_before = repository_snapshot(
        dispatcher_card.parent, "selected dispatcher", require_clean=True,
    )
    dispatcher_checkout = Path(dispatcher_before["checkout"])
    if is_within(source_checkout, dispatcher_card) or source_checkout == dispatcher_checkout:
        fail("selected dispatcher must come from a Git checkout distinct from skill-craft")
    package_before = package_hashes(dispatcher_card)

    output.mkdir(mode=0o700, parents=True)
    command = qualification_command(dispatcher_card)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    exit_code, timed_out, stdout, stderr = run_with_process_group(command, environment)
    duration_seconds = round(time.monotonic() - started, 3)
    stdout_log = write_text(output / "native-pilot.stdout.log", stdout)
    stderr_log = write_text(output / "native-pilot.stderr.log", stderr)

    drift: list[str] = []
    source_after = capture_after_snapshot(
        lambda: repository_snapshot(ROOT, "skill-craft source after run", require_clean=True),
    )
    dispatcher_after = capture_after_snapshot(
        lambda: repository_snapshot(dispatcher_card.parent, "selected dispatcher after run", require_clean=False),
    )
    package_after = capture_after_snapshot(
        lambda: package_hashes(dispatcher_card),
    )
    for label, before, after in (
        ("skill-craft source identity", source_before, source_after),
        ("selected dispatcher checkout identity", dispatcher_before, dispatcher_after),
        ("selected dispatcher package", package_before, package_after),
    ):
        try:
            assert_unchanged(label, before, after)
        except QualificationError as exc:
            drift.append(str(exc))

    passed = exit_code == 0 and not timed_out and not drift
    receipt = {
        "schema": SCHEMA,
        "passed": passed,
        "selected_dispatcher": {
            "skill_card": str(dispatcher_card),
            "repository": dispatcher_before,
            "package_hashes": {"before": package_before, "after": package_after},
        },
        "skill_craft_source_identity": {"before": source_before, "after": source_after},
        "actual_run": {
            "argv": command,
            "cwd": str(ROOT),
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_seconds": duration_seconds,
            "stdout": stdout_log,
            "stderr": stderr_log,
        },
        "execution": {
            "model_calls": 0,
            "native_agent_launches": 0,
            "contract": "The qualified native-pilot unittest uses deterministic fixture handles only.",
        },
        "drift": drift,
    }
    receipt_path = output / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt, 0 if passed else 2


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--dispatcher-skill", required=True, help="absolute selected external SKILL.md")
    value.add_argument("--output", required=True, help="new absolute receipt directory outside both checkouts")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        dispatcher_card = absolute_file(args.dispatcher_skill, "--dispatcher-skill")
        output = new_output_path(args.output)
        external = repository_snapshot(dispatcher_card.parent, "selected dispatcher", require_clean=True)
        require_output_outside(output, Path(external["checkout"]), "selected dispatcher")
        source = repository_snapshot(ROOT, "skill-craft source", require_clean=True)
        require_output_outside(output, Path(source["checkout"]), "skill-craft source")
        receipt, exit_code = run_qualification(dispatcher_card, output)
    except QualificationError as exc:
        print(f"current-dispatcher: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"passed": receipt["passed"], "receipt": str(output / "receipt.json")}, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
