"""Bind Improve's declarative policy without importing its standalone runtime.

The package copy is content-pinned; new runs snapshot it in the existing
Markdown transaction. Resume reads that snapshot, never an ambient host skill.
This module neither advances a stage nor counts a review.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping


POLICY_ID = "improve/review-policy/v1"
RUN_FILE = "improve-policy.md"
SOURCE_FILE = "improve-review-policy.md"
PIN_FILE = "improve-policy-pin.json"
MAX_BYTES = 32768
PRODUCT_STAGES = frozenset((
    "review", "improve-plan", "improve-apply", "iteration-document", "verify",
    "carry-forward", "commit", "final-verify", "post-inner", "merge",
))


class ImprovePolicyError(ValueError):
    """The selected policy cannot safely support an action packet."""


def _read(path: Path) -> bytes:
    """Refuse aliases, special files and oversized input before reading."""
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ImprovePolicyError(f"Improve policy must be a regular single-link file: {path}")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                raise ImprovePolicyError(f"Improve policy changed during read: {path}")
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ImprovePolicyError(f"Improve policy exceeds {MAX_BYTES} bytes: {path}")
        return data
    except OSError as exc:
        raise ImprovePolicyError(f"Improve policy unavailable at {path}: {exc}") from exc


def _body(data: bytes, expected_hash: str) -> str:
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ImprovePolicyError("Improve policy digest mismatch; restore the bound bytes, do not rebind an active run")
    try:
        body = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ImprovePolicyError("Improve policy must be UTF-8") from exc
    if not body.startswith("# Improve review policy\n") or f"\nPolicy ID: {POLICY_ID}\n" not in body:
        raise ImprovePolicyError("unsupported Improve policy identity")
    return body


def validate_binding(state: Mapping[str, Any]) -> dict[str, Any] | None:
    if "improve_policy" not in state:
        return None  # Existing runs keep their established policy, without a lazy upgrade.
    binding = state["improve_policy"]
    if (not isinstance(binding, dict)
            or set(binding) != {"version", "policy_id", "sha256"}
            or type(binding["version"]) is not int or binding["version"] != 1
            or binding["policy_id"] != POLICY_ID
            or not isinstance(binding["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", binding["sha256"])):
        raise ImprovePolicyError("unsupported Improve policy binding")
    return binding


def load_package(ref_dir: Path) -> tuple[dict[str, Any], str]:
    pin = json.loads(_read(Path(ref_dir) / PIN_FILE))
    binding = validate_binding({"improve_policy": pin})
    assert binding is not None
    return binding, _body(_read(Path(ref_dir) / SOURCE_FILE), binding["sha256"])


def initialize(ref_dir: Path, state: dict[str, Any], writes: dict[str, str]) -> None:
    binding, body = load_package(ref_dir)
    state["improve_policy"] = binding
    writes[RUN_FILE] = body


def bound_path(root: Path, state: Mapping[str, Any]) -> Path | None:
    binding = validate_binding(state)
    if binding is None:
        return None
    path = Path(root) / RUN_FILE
    _body(_read(path), binding["sha256"])
    return path


def cycle(path: Path, binding: Mapping[str, Any], history_limit: int) -> str:
    """Project only the owner binding; qualitative review policy lives in Markdown."""
    if type(history_limit) is not int or history_limit < 1:
        raise ImprovePolicyError("Improve policy requires a positive history window")
    return (
        "Review-and-improve cycle (owning loop): read the full frozen Improve policy at "
        f"{path} (policy {binding['policy_id']}; SHA-256 {binding['sha256']}).\n"
        "Execution mode: ShipLoop-managed. Perform ONLY the current named stage, then use "
        "this packet's exact Call this when done command. Do not execute the whole cycle "
        "in this action or invoke Improve's standalone card/Until runtime.\n"
        f"Owner history window: last {history_limit} full Git commit bodies (all if fewer); "
        "use the printed history reader. The window supplies context, not edit scope.\n"
        "Owner evidence: current state.md, selected step/iteration receipts, result paths and "
        "checks. Markdown is authoritative; only scripts count two distinct verified, "
        "audit-committed trivial passes. A host completion claim is not proof.\n"
        "Owner overrides: a distinct verbose learning commit is required EVERY iteration, "
        "including no-change audit iterations; never include unrelated staged work. "
        "Keep ShipLoop's stricter materiality decisions, required lint/tests, nested "
        "plan gates, documentation and carry-forward checkpoints. Readiness still requires "
        "fresh final verification and the remaining ShipLoop stages; no sidecar state."
    )
