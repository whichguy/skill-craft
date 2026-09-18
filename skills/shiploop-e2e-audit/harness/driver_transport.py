#!/usr/bin/env python3
"""Bounded, read-only-driver transport for ShipLoop E2E semantic checks.

The transport deliberately knows nothing about a game, DOM, or application
layout.  It sends one canonical JSON request to an explicitly configured argv
adapter and retains only protocol facts and digests.  Raw adapter streams stay
in a private temporary directory because an adapter's stderr is not evidence
and may contain credential-shaped text.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any


REQUEST_SCHEMA = "shiploop-e2e-driver-request/1"
RESPONSE_SCHEMA = "shiploop-e2e-driver-response/1"
TRANSPORT_SCHEMA = "shiploop-e2e-driver-transport/1"
MAX_ARGV_ITEMS = 64
MAX_ARGV_CHARS = 16_384
POLL_SECONDS = 0.02
TERM_GRACE_SECONDS = 0.10
KILL_GRACE_SECONDS = 0.50
CHILD_ENVIRONMENT_KEYS = (
    "PATH",
    "HOME",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SHIPLOOP_E2E_EVIDENCE",
)
FILE_ARGUMENT_SUFFIXES = frozenset((".py", ".js", ".cjs", ".mjs", ".sh"))


class DriverTransportError(RuntimeError):
    """A bounded adapter execution or protocol failure safe to record."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a protocol value deterministically without shell parsing."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def parse_argv(value: Any) -> list[str]:
    """Accept one bounded argv list, never a shell command string."""
    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_ARGV_ITEMS
        or any(not isinstance(item, str) or not item or "\x00" in item for item in value)
        or sum(len(item) for item in value) > MAX_ARGV_CHARS
    ):
        raise ValueError("driver argv must be a bounded non-empty list of strings")
    return list(value)


def _looks_like_file_argument(value: str) -> bool:
    return value.startswith(".") or "/" in value or Path(value).suffix.lower() in FILE_ARGUMENT_SUFFIXES


def _resolve_file_argument(value: str, *, base: Path, executable: bool = False) -> str:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError("driver argv file is unavailable") from exc
    if executable and (not resolved.is_file() or not os.access(resolved, os.X_OK)):
        raise ValueError("driver argv file is not executable")
    if not executable and not (resolved.is_file() or resolved.is_dir()):
        raise ValueError("driver argv path is not a regular file or directory")
    return str(resolved)


def resolve_argv(value: Any, *, base: Path) -> list[str]:
    """Pin executable and file arguments before launch and provenance hashing.

    The registry owns relative file arguments; adapters still execute with the
    product as their working directory. Resolving the two independently keeps
    a candidate's same-named file from changing which adapter runs.
    """
    checked = parse_argv(value)
    try:
        registry_base = Path(base).resolve(strict=True)
    except OSError as exc:
        raise ValueError("driver registry base is unavailable") from exc
    if not registry_base.is_dir():
        raise ValueError("driver registry base is not a directory")

    executable = checked[0]
    if _looks_like_file_argument(executable):
        resolved_executable = _resolve_file_argument(executable, base=registry_base, executable=True)
    else:
        discovered = shutil.which(executable)
        if discovered is None:
            raise ValueError("driver executable is unavailable")
        resolved_executable = _resolve_file_argument(discovered, base=registry_base, executable=True)

    resolved = [resolved_executable]
    for argument in checked[1:]:
        if _looks_like_file_argument(argument):
            resolved.append(_resolve_file_argument(argument, base=registry_base))
        else:
            resolved.append(argument)
    return resolved


def _minimal_child_environment() -> dict[str, str]:
    """Pass only runtime basics and the declared E2E evidence location.

    This bounds incidental host configuration but is not a sandbox. Adapters
    are trusted, externally supplied processes and must use explicit argv for
    their runtime settings instead of inherited interpreter configuration.
    """
    return {key: os.environ[key] for key in CHILD_ENVIRONMENT_KEYS if key in os.environ}


def _stream_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _stop_process_group(process: subprocess.Popen[bytes]) -> dict[str, bool]:
    """End the adapter's private process group, including ordinary children."""
    result = {"term_sent": False, "kill_sent": False}
    if os.name != "posix":
        if process.poll() is None:
            process.kill()
            result["kill_sent"] = True
        try:
            process.wait(timeout=KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        return result
    try:
        os.killpg(process.pid, signal.SIGTERM)
        result["term_sent"] = True
    except (ProcessLookupError, PermissionError, OSError):
        return result
    time.sleep(TERM_GRACE_SECONDS)
    try:
        os.killpg(process.pid, signal.SIGKILL)
        result["kill_sent"] = True
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        process.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    return result


def _wait_for_process(
    process: subprocess.Popen[bytes], stdout_path: Path, stderr_path: Path,
    timeout_seconds: float, max_output_bytes: int,
) -> tuple[int | None, dict[str, bool]]:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if _stream_size(stdout_path) > max_output_bytes or _stream_size(stderr_path) > max_output_bytes:
            termination = _stop_process_group(process)
            raise DriverTransportError("driver-output-exceeded-bound")
        if time.monotonic() >= deadline:
            termination = _stop_process_group(process)
            raise DriverTransportError("driver-timeout")
        time.sleep(POLL_SECONDS)
    # A short-lived wrapper can leave a server/browser child in its private
    # group.  End it before reading the bounded files.
    termination = _stop_process_group(process)
    if _stream_size(stdout_path) > max_output_bytes or _stream_size(stderr_path) > max_output_bytes:
        raise DriverTransportError("driver-output-exceeded-bound")
    return process.returncode, termination


def invoke(
    argv: list[str],
    request: dict[str, Any],
    *,
    cwd: Path,
    timeout_seconds: float,
    max_output_bytes: int,
    configuration: Any = None,
) -> dict[str, Any]:
    """Invoke one adapter and return structured observations plus pinned facts.

    The caller supplies an already-selected argv.  This function neither
    starts a shell nor persists adapter stdout/stderr.  It raises
    :class:`DriverTransportError` for outcomes that cannot support a complete
    semantic trace; callers should turn those into ``unverified`` evidence.
    """
    checked_argv = parse_argv(argv)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("driver timeout must be positive")
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes <= 0:
        raise ValueError("driver max_output_bytes must be a positive integer")
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("driver request must be a shiploop-e2e-driver-request/1 object")
    working_directory = Path(cwd).resolve()
    if not working_directory.is_dir():
        raise ValueError("driver cwd must be an existing directory")
    if request.get("repo") != str(working_directory):
        raise ValueError("driver request repo must equal the resolved driver cwd")
    try:
        request_bytes = canonical_json_bytes(request)
        configuration_digest = digest_json(configuration if configuration is not None else {"argv": checked_argv})
    except (TypeError, ValueError) as exc:
        raise ValueError("driver request/configuration must be JSON serializable") from exc

    try:
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-driver-") as raw_directory:
            raw_root = Path(raw_directory)
            stdin_path = raw_root / "stdin.json"
            stdout_path = raw_root / "stdout.json"
            stderr_path = raw_root / "stderr.log"
            stdin_path.write_bytes(request_bytes)
            with (
                stdin_path.open("rb") as stdin_handle,
                stdout_path.open("wb") as stdout_handle,
                stderr_path.open("wb") as stderr_handle,
            ):
                process = subprocess.Popen(
                    checked_argv,
                    cwd=working_directory,
                    env=_minimal_child_environment(),
                    stdin=stdin_handle,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    start_new_session=os.name == "posix",
                )
                exit_code, termination = _wait_for_process(
                    process, stdout_path, stderr_path, float(timeout_seconds), max_output_bytes
                )
            stdout = stdout_path.read_bytes()
            stderr = stderr_path.read_bytes()
    except DriverTransportError:
        raise
    except OSError as exc:
        raise DriverTransportError("driver-execution-error") from exc

    if exit_code != 0:
        raise DriverTransportError("driver-nonzero-exit")
    try:
        response = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverTransportError("driver-invalid-json") from exc
    if not isinstance(response, dict):
        raise DriverTransportError("driver-response-not-object")
    if response.get("schema") != RESPONSE_SCHEMA:
        raise DriverTransportError("driver-response-schema-mismatch")
    request_sha256 = sha256_bytes(request_bytes)
    if response.get("request_sha256") != request_sha256:
        raise DriverTransportError("driver-request-binding-mismatch")
    if response.get("repo") != str(working_directory):
        raise DriverTransportError("driver-repo-binding-mismatch")
    observations = response.get("observations")
    if not isinstance(observations, list):
        raise DriverTransportError("driver-observations-not-list")

    return {
        "schema": TRANSPORT_SCHEMA,
        "request_sha256": request_sha256,
        "response_sha256": sha256_bytes(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
        "adapter_argv_sha256": digest_json(checked_argv),
        "adapter_configuration_sha256": configuration_digest,
        "adapter_argv_items": len(checked_argv),
        "child_environment_keys": sorted(_minimal_child_environment()),
        "exit_code": exit_code,
        "group_termination": termination,
        "observations": observations,
    }


__all__ = [
    "DriverTransportError",
    "CHILD_ENVIRONMENT_KEYS",
    "MAX_ARGV_CHARS",
    "MAX_ARGV_ITEMS",
    "REQUEST_SCHEMA",
    "RESPONSE_SCHEMA",
    "TRANSPORT_SCHEMA",
    "canonical_json_bytes",
    "digest_json",
    "invoke",
    "parse_argv",
    "resolve_argv",
    "sha256_bytes",
]
