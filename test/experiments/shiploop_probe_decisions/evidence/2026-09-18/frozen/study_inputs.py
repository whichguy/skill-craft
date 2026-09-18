#!/usr/bin/env python3
"""Validate the immutable inputs required before a discovery arm can begin."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re


SHA256 = re.compile(r"^[0-9a-f]{64}$")
CALIBRATION = "private/oracle-calibration.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object(path: Path, label: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is unavailable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _relative(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("frozen manifest contains an unsafe path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("frozen manifest contains an unsafe path")
    return path


def _cache(path: PurePosixPath) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc"


def _study_path(study: Path, relative: PurePosixPath) -> Path:
    target = study
    for part in relative.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError("frozen inputs contain a symlink")
    return target


def _supplied_files(study: Path) -> set[str]:
    actual: set[str] = set()
    for name in ("frozen", "guides"):
        root = study / name
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"{name} inputs are unavailable")
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError("frozen inputs contain a symlink")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError("frozen inputs contain a non-regular entry")
            relative = PurePosixPath(path.relative_to(study).as_posix())
            if not _cache(relative):
                actual.add(relative.as_posix())
    return actual


def _manifest(study: Path) -> dict[str, str]:
    path = study / "frozen-inputs.json"
    manifest = _object(path, "frozen-inputs.json")
    if not manifest:
        raise ValueError("frozen-inputs.json must not be empty")
    normalized: dict[str, str] = {}
    for raw_path, digest in manifest.items():
        relative = _relative(raw_path)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError("frozen manifest contains an invalid digest")
        if relative.parts[0] not in {"frozen", "guides"} and relative.as_posix() != CALIBRATION:
            raise ValueError("frozen manifest contains an unsupported path")
        if _cache(relative):
            raise ValueError("frozen manifest must not include generated caches")
        target = _study_path(study, relative)
        if target.is_symlink() or not target.is_file():
            raise ValueError("frozen manifest references an unavailable file")
        try:
            observed = _sha256(target)
        except OSError as exc:
            raise ValueError("frozen manifest references an unreadable file") from exc
        if observed != digest:
            raise ValueError("frozen input hash does not match its manifest")
        normalized[relative.as_posix()] = digest
    expected = {name for name in normalized if name.startswith("frozen/") or name.startswith("guides/")}
    if _supplied_files(study) != expected:
        raise ValueError("frozen inputs do not match the supplied file set")
    if CALIBRATION not in normalized:
        raise ValueError("frozen manifest is missing calibration")
    return normalized


def _state(study: Path, manifest_digest: str) -> None:
    state = _object(_study_path(study, PurePosixPath("study.json")), "study.json")
    status = state.get("status")
    if status != "ready_to_prepare":
        raise ValueError("study status is not ready")
    hashes = state.get("hashes")
    if not isinstance(hashes, dict) or hashes.get("frozen_inputs_manifest") != manifest_digest:
        raise ValueError("study state does not match frozen-inputs.json")
    if state.get("frozen_inputs_manifest") != "frozen-inputs.json":
        raise ValueError("study state does not identify frozen-inputs.json")


def _calibration(study: Path) -> None:
    calibration = _object(_study_path(study, PurePosixPath(CALIBRATION)), "oracle calibration")
    if calibration.get("passed") is not True:
        raise ValueError("oracle calibration did not pass")
    bindings = calibration.get("bindings")
    if not isinstance(bindings, dict):
        raise ValueError("oracle calibration bindings are unavailable")
    try:
        expected = {
            "fixtures.py": _sha256(_study_path(study, PurePosixPath("frozen/fixtures.py"))),
            "PUBLIC_CONTRACTS.md": _sha256(_study_path(study, PurePosixPath("frozen/PUBLIC_CONTRACTS.md"))),
            "oracle.py": _sha256(_study_path(study, PurePosixPath("frozen/oracle.py"))),
        }
    except OSError as exc:
        raise ValueError("oracle calibration inputs are unavailable") from exc
    if any(bindings.get(name) != digest for name, digest in expected.items()):
        raise ValueError("oracle calibration bindings do not match frozen inputs")


def validate_study_inputs(study: Path) -> dict[str, str]:
    """Return the validated frozen manifest or raise ``ValueError`` before work."""
    study = Path(study)
    if study.is_symlink() or not study.is_dir():
        raise ValueError("study directory is unavailable")
    try:
        study = study.resolve(strict=True)
    except OSError as exc:
        raise ValueError("study directory is unavailable") from exc
    manifest_path = _study_path(study, PurePosixPath("frozen-inputs.json"))
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("frozen-inputs.json is unavailable")
    try:
        manifest_digest = _sha256(manifest_path)
    except OSError as exc:
        raise ValueError("frozen-inputs.json is unreadable") from exc
    _state(study, manifest_digest)
    manifest = _manifest(study)
    _calibration(study)
    return manifest
