#!/usr/bin/env python3
"""Portable integrity checks for a frozen ShipLoop capability runtime."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any


RUNTIME_VERSION = "shiploop-capability-runtime-v3"
RUNTIME_MANIFEST = "runtime-manifest.json"
RUNTIME_SCHEMA = "shiploop-capability-runtime-freeze-v1"
RUNTIME_FILES = (
    "gateway.py",
    "run_trials.py",
    "collect_blind.py",
    "prepare.py",
    "runtime_validation.py",
)
REQUIRED_TOP_LEVEL_FILES = frozenset((*RUNTIME_FILES, "fixture-app.py"))
REQUIRED_SHIPLOOP_FILES = frozenset(
    {
        "shiploop/README.md",
        "shiploop/SKILL.md",
        "shiploop/commands/shiploop.md",
        "shiploop/references/action-protocol.md",
        "shiploop/references/ledger-contract.md",
        "shiploop/references/navigator.md",
        "shiploop/references/state-files.md",
        "shiploop/scripts/shiploop",
        "shiploop/scripts/shiploop_artifacts.py",
        "shiploop/scripts/shiploop_contract_protocol.py",
        "shiploop/scripts/shiploop_contracts.py",
        "shiploop/scripts/shiploop_navigator.py",
        "shiploop/scripts/shiploop_navigator_dry_run.py",
        "shiploop/scripts/shiploop_objectives.py",
        "shiploop/scripts/shiploop_packets.py",
        "shiploop/scripts/shiploop_protocol.py",
        "shiploop/scripts/shiploop_store.py",
    }
)
MINIMUM_SHIPLOOP_FILE_COUNT = 80
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RuntimeSnapshotError(ValueError):
    """The frozen runtime cannot safely be used."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise RuntimeSnapshotError("runtime manifest contains an unsafe file path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or not path.parts
        or any(part in {"", ".", ".."} or ":" in part for part in path.parts)
    ):
        raise RuntimeSnapshotError("runtime manifest contains an unsafe file path")
    return value


def _expected_files(metadata: dict[str, Any]) -> dict[str, str]:
    if metadata.get("schema") != RUNTIME_SCHEMA:
        raise RuntimeSnapshotError("frozen runtime metadata has an unexpected schema")
    if metadata.get("runtime_version") != RUNTIME_VERSION:
        raise RuntimeSnapshotError("frozen runtime metadata has an unexpected version")
    files = metadata.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeSnapshotError("frozen runtime metadata has no file hashes")
    expected: dict[str, str] = {}
    for raw_relative, expected_digest in files.items():
        relative = _manifest_relative_path(raw_relative)
        if relative == RUNTIME_MANIFEST or "__pycache__" in PurePosixPath(relative).parts or relative.endswith(".pyc"):
            raise RuntimeSnapshotError("runtime manifest lists a cache or manifest file")
        if not isinstance(expected_digest, str) or not SHA256_RE.fullmatch(expected_digest):
            raise RuntimeSnapshotError("runtime manifest contains an invalid file digest")
        expected[relative] = expected_digest
    missing_top_level = REQUIRED_TOP_LEVEL_FILES.difference(expected)
    if missing_top_level:
        raise RuntimeSnapshotError("runtime manifest is missing required top-level files")
    shiploop_files = {relative for relative in expected if relative.startswith("shiploop/")}
    if len(shiploop_files) < MINIMUM_SHIPLOOP_FILE_COUNT or not REQUIRED_SHIPLOOP_FILES.issubset(shiploop_files):
        raise RuntimeSnapshotError("runtime manifest does not contain the complete ShipLoop snapshot shape")
    return expected


def _actual_files(runtime: Path) -> dict[str, str]:
    actual: dict[str, str] = {}
    try:
        for parent, directories, filenames in os.walk(runtime, topdown=True, followlinks=False):
            parent_path = Path(parent)
            for name in sorted(directories):
                candidate = parent_path / name
                if candidate.is_symlink():
                    raise RuntimeSnapshotError("runtime tree contains a symbolic-link component")
                if not candidate.is_dir():
                    raise RuntimeSnapshotError("runtime tree contains an unsafe directory entry")
                if name == "__pycache__":
                    raise RuntimeSnapshotError("runtime tree contains an unexpected bytecode cache")
            for name in sorted(filenames):
                candidate = parent_path / name
                relative = candidate.relative_to(runtime).as_posix()
                if candidate.is_symlink():
                    raise RuntimeSnapshotError("runtime tree contains a symbolic-link component")
                if relative == RUNTIME_MANIFEST:
                    if not candidate.is_file():
                        raise RuntimeSnapshotError("frozen runtime metadata is not a regular file")
                    continue
                if "__pycache__" in PurePosixPath(relative).parts or candidate.suffix == ".pyc":
                    raise RuntimeSnapshotError("runtime tree contains an unexpected bytecode file")
                if not candidate.is_file():
                    raise RuntimeSnapshotError("runtime tree contains a non-regular file")
                actual[relative] = _digest(candidate)
    except OSError as exc:
        raise RuntimeSnapshotError("frozen runtime tree is unreadable") from exc
    return actual


def validate_runtime_snapshot(runtime: Path) -> dict[str, Any]:
    """Validate self-consistency of all manifest digests and the snapshot tree.

    This verifies local frozen inputs against their local manifest. Prepared
    arms separately pin that manifest's digest before a worker can launch.
    """
    runtime = Path(runtime)
    if runtime.is_symlink() or not runtime.is_dir():
        raise RuntimeSnapshotError("frozen runtime directory is unavailable or unsafe")
    manifest_path = runtime / RUNTIME_MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeSnapshotError("frozen runtime metadata is unavailable or unsafe")
    try:
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeSnapshotError("frozen runtime metadata is unreadable") from exc
    if not isinstance(metadata, dict):
        raise RuntimeSnapshotError("frozen runtime metadata must be an object")
    expected = _expected_files(metadata)
    actual = _actual_files(runtime)
    if set(actual) != set(expected):
        raise RuntimeSnapshotError("runtime regular-file tree does not match its manifest")
    for relative, expected_digest in expected.items():
        if actual[relative] != expected_digest:
            raise RuntimeSnapshotError("runtime file digest does not match its manifest")
    return metadata
