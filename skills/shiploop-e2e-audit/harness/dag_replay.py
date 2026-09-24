#!/usr/bin/env python3
"""Replay bounded ShipLoop DAG callback fixtures through the real navigator.

The replay is a fast, local apparatus check.  It starts no model and executes
no captured terminal command or project work.  Its only child process is
``mock_grok.py``, a dedicated JSONL callback transport whose output is consumed
by the selected ShipLoop navigator's actual state-transition functions.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import Any

import layout

HERE = layout.HARNESS_ROOT
DEFAULT_SKILL_ROOT = layout.default_skill_root()
MOCK_PATH = HERE / "mock_grok.py"
CASE_SCHEMA = "shiploop-e2e-dag-case/1"
MOCK_REQUEST_SCHEMA = "shiploop-e2e-mock-grok-request/1"
MOCK_RESPONSE_SCHEMA = "shiploop-e2e-mock-grok-response/1"
SIMULATION_SCOPE = (
    "Synthetic apparatus only: real navigator transition functions consume local mock "
    "callbacks. No model, network, repository work, captured shell command, product, "
    "or live E2E verdict is produced."
)
_CASE_FIELDS = frozenset((
    "schema", "id", "kind", "protocol_version", "provenance", "prompt", "steps",
    "expected_final", "expected_failure",
))
_STEP_FIELDS = frozenset((
    "at", "owner", "command", "result", "receipt", "final_result", "expect", "status",
    "expect_owner", "expect_error", "action",
))
_COMMANDS = frozenset((
    "done", "produce", "finish-improve", "pause", "resume", "halt", "cold-load",
    "stale-produce", "duplicate-produce", "conflicting-produce", "malformed-produce",
    "duplicate-finish-improve", "conflicting-finish-improve", "stale-finish-improve",
))
_STATUSES = frozenset(("active", "paused", "blocked", "halted", "done"))
_KIND = "synthetic"
_PROTOCOL_VERSION = 3
_V3_PRELUDE = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
)
_V3_INNER = (
    "select-work", "step-plan", "test-spec", "baseline", "test-author", "test-red",
    "implement", "test-green", "test-refine", "regression", "document", "skill-assess",
    "skill-validate", "static-checks", "verify", "integrate", "integration-verify",
    "carry-forward",
)
_V3_OUTER = (
    "system-test-author", "system-test", "product-acceptance", "release-plan",
    "release-check", "release", "release-verify", "operations", "handoff",
)
# The Improve schedule, stated literally so the replay oracle stays independent
# of the navigator's own constants: every planning/contract producer, plus the
# successful carry-forward that leaves no work item pending, parks for Improve.
# Every other producer result is accepted directly.
_V3_PLANNING_CHECKPOINTS = frozenset((
    "spec", "test-strategy", "plan", "step-plan", "test-spec",
    "system-test-author", "release-plan",
))
_MOCK_RESPONSE_TIMEOUT_SECONDS = 5.0
# The navigator's top-level import closure.
_ENGINE_MODULES = frozenset((
    "shiploop_navigator",
    "shiploop_navigator_v3_prompts",
    "shiploop_consumer_delivery",
    "shiploop_planning_revision",
    "shiploop_privacy",
    "shiploop_store",
))
# A module path alone is not an execution identity: Python can retain bytecode
# for that path after the selected package changes.  Pin the full closure hash
# on first import in this process and fail closed on a later mismatch.
_PROCESS_LOADED_PACKAGE_SHA256: dict[str, str] = {}


class DagReplayError(ValueError):
    """Raised for invalid fixture input, mock binding, or unexpected DAG behavior."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _file_hash(path: Path) -> str:
    return _sha256(path.read_bytes())


def _within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DagReplayError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DagReplayError(f"{label} must be nonempty text")
    return value


def _owner(state: Mapping[str, Any]) -> str:
    if state.get("navigator_protocol_version") in (3, 4) and state.get("stage") == "inner-loop":
        return str(state["work_items"][state["work_index"]]["id"])
    return "root"


def _canonical_fixture_digest(case: Mapping[str, Any]) -> str:
    return _sha256(_json_bytes(case))


def validate_case(raw: Any, *, origin: str = "fixture") -> dict[str, Any]:
    """Validate the small, explicit replay-fixture contract before execution."""
    if not isinstance(raw, dict):
        raise DagReplayError(f"{origin}: case must be an object")
    keys = set(raw)
    required = {"schema", "id", "kind", "protocol_version", "provenance", "steps", "expected_final"}
    if not required <= keys or not keys <= _CASE_FIELDS:
        raise DagReplayError(f"{origin}: case has unsupported or missing fields")
    if raw["schema"] != CASE_SCHEMA:
        raise DagReplayError(f"{origin}: unsupported case schema")
    case_id = _text(raw["id"], f"{origin} id")
    if not all(char.isalnum() or char in "_-" for char in case_id):
        raise DagReplayError(f"{origin}: id has unsafe characters")
    if raw["kind"] != _KIND:
        raise DagReplayError(f"{origin}: kind must be synthetic")
    if type(raw["protocol_version"]) is not int or raw["protocol_version"] != _PROTOCOL_VERSION:
        raise DagReplayError(f"{origin}: protocol_version must be 3")
    if not isinstance(raw["provenance"], dict):
        raise DagReplayError(f"{origin}: provenance must be an object")
    if "prompt" in raw:
        _text(raw["prompt"], f"{origin} prompt")
    steps = raw["steps"]
    if not isinstance(steps, list) or not steps or len(steps) > 500:
        raise DagReplayError(f"{origin}: steps must contain 1..500 entries")
    for number, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            raise DagReplayError(f"{origin}: step {number} must be an object")
        step_keys = set(step)
        if not {"at", "expect"} <= step_keys or not step_keys <= _STEP_FIELDS:
            raise DagReplayError(f"{origin}: step {number} has unsupported or missing fields")
        _text(step["at"], f"{origin} step {number} at")
        _text(step["expect"], f"{origin} step {number} expect")
        command = step.get("command", "done")
        if command not in _COMMANDS:
            raise DagReplayError(f"{origin}: step {number} has unsupported command")
        for key in ("owner", "expect_owner", "expect_error", "action"):
            if key in step:
                _text(step[key], f"{origin} step {number} {key}")
        if "status" in step and step["status"] not in _STATUSES:
            raise DagReplayError(f"{origin}: step {number} status is invalid")
        for key in ("result", "receipt", "final_result"):
            if key in step and not isinstance(step[key], dict):
                raise DagReplayError(f"{origin}: step {number} {key} must be an object")
        if command in {"done", "produce", "stale-produce", "duplicate-produce", "conflicting-produce", "malformed-produce"} and "result" not in step:
            raise DagReplayError(f"{origin}: step {number} producer command needs result")
        if command in {"finish-improve", "duplicate-finish-improve", "conflicting-finish-improve", "stale-finish-improve"} and "receipt" not in step:
            raise DagReplayError(f"{origin}: step {number} Improve completion needs receipt")
    final = raw["expected_final"]
    if not isinstance(final, dict) or set(final) - {"stage", "status", "owner", "completed_work_items"}:
        raise DagReplayError(f"{origin}: expected_final is invalid")
    if not {"stage", "status"} <= set(final):
        raise DagReplayError(f"{origin}: expected_final needs stage and status")
    _text(final["stage"], f"{origin} expected_final stage")
    if final["status"] not in _STATUSES:
        raise DagReplayError(f"{origin}: expected_final status is invalid")
    if "owner" in final:
        _text(final["owner"], f"{origin} expected_final owner")
    if "completed_work_items" in final:
        completed = final["completed_work_items"]
        if not isinstance(completed, list) or any(not isinstance(item, str) or not item for item in completed):
            raise DagReplayError(f"{origin}: expected_final completed_work_items is invalid")
    if "expected_failure" in raw:
        _text(raw["expected_failure"], f"{origin} expected_failure")
    return raw


def load_case(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load one immutable JSON fixture, retaining its exact source hash."""
    try:
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DagReplayError(f"cannot read fixture {path}: {exc}") from exc
    case = validate_case(value, origin=str(path))
    return case, {"kind": "file", "path": str(path.resolve()), "sha256": _sha256(data)}


def _result(stage: str, *, outcome: str = "done", work_items: list[dict[str, str]] | None = None,
            summary: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "outcome": outcome,
        "summary": summary or f"Synthetic {stage} declaration; no project work executed.",
    }
    if work_items is not None:
        value["work_items"] = work_items
    return value


def _receipt(stage: str, *, marker: str = "complete") -> dict[str, Any]:
    return {
        "summary": f"Synthetic Improve {marker} for {stage}; no Improve runtime executed.",
        "review_refs": [f"synthetic://dag/{stage}/review"],
        "check_refs": [f"synthetic://dag/{stage}/check"],
        "lessons": f"Synthetic retained lesson for {stage}.",
    }


def _v3_path_steps(stages: tuple[str, ...], *, work_items: list[dict[str, str]] | None = None,
                   active_owner: str = "W1", terminal_target: str | None = None) -> list[dict[str, Any]]:
    """Build independent expected edges for the v3 producer/Improve schedule.

    A literal checkpoint producer parks its action and a synthetic Improve
    completion advances it. Every other producer advances directly.
    """
    rows: list[dict[str, Any]] = []
    item_ids = [row["id"] for row in work_items] if work_items else [active_owner]
    item_index = 0
    for index, stage in enumerate(stages):
        target = stages[index + 1] if index + 1 < len(stages) else (terminal_target or "done")
        if stage == "carry-forward":
            item_index += 1
        checkpoint = stage in _V3_PLANNING_CHECKPOINTS or (
            stage == "carry-forward" and item_index >= len(item_ids)
        )
        edge: dict[str, Any] = {"expect": target, "status": "done" if target == "done" else "active"}
        if target in _V3_INNER:
            if item_index >= len(item_ids):
                raise DagReplayError("synthetic path expects an unavailable work item")
            edge["expect_owner"] = item_ids[item_index]
        produce: dict[str, Any] = {
            "at": stage, "command": "produce",
            "result": _result(stage, work_items=work_items if stage == "plan" else None),
        }
        # Omit an inner owner rather than placing None in the strict schema.
        if stage not in _V3_INNER:
            produce["owner"] = "root"
        if checkpoint:
            rows.append({**produce, "expect": stage, "status": "active"})
            rows.append({"at": stage, "command": "finish-improve", "receipt": _receipt(stage), **edge})
        else:
            rows.append({**produce, **edge})
    return rows


def _synthetic_case(case_id: str, steps: list[dict[str, Any]], expected_final: dict[str, str], *,
                    expected_failure: str | None = None) -> dict[str, Any]:
    case: dict[str, Any] = {
        "schema": CASE_SCHEMA,
        "id": case_id,
        "kind": "synthetic",
        "protocol_version": 3,
        "provenance": {
            "source": "dag_replay.py synthetic builder",
            "meaning": "Fixture controls only; no retained model or product behavior.",
        },
        "prompt": "Synthetic ShipLoop DAG replay fixture; no project work.",
        "steps": steps,
        "expected_final": expected_final,
    }
    if expected_failure is not None:
        case["expected_failure"] = expected_failure
    return case


def synthetic_cases() -> dict[str, dict[str, Any]]:
    """Return independent v3 calibration cases; expected edges are literal here."""
    full_path = _V3_PRELUDE + _V3_INNER + _V3_OUTER
    cases: dict[str, dict[str, Any]] = {
        "synthetic-v3-full": _synthetic_case(
            "synthetic-v3-full", _v3_path_steps(full_path),
            {"stage": "done", "status": "done", "completed_work_items": ["W1"]}
        ),
        "synthetic-v3-two-work-items": _synthetic_case(
            "synthetic-v3-two-work-items",
            _v3_path_steps(
                _V3_PRELUDE + _V3_INNER + _V3_INNER + _V3_OUTER,
                work_items=[{"id": "W1", "title": "First synthetic item"}, {"id": "W2", "title": "Second synthetic item"}],
            ),
            {"stage": "done", "status": "done", "completed_work_items": ["W1", "W2"]},
        ),
    }

    # Replay guards need a parked child, so they run at the first checkpoint.
    to_spec = _v3_path_steps(("intake", "discovery", "research"), terminal_target="spec")
    wait_steps = to_spec + [
        {"at": "spec", "command": "produce", "result": _result("spec"), "expect": "spec", "status": "active"},
        {"at": "spec", "command": "duplicate-produce", "result": _result("spec"), "expect": "spec", "status": "active"},
        {"at": "spec", "command": "conflicting-produce", "result": _result("spec", summary="Conflicting synthetic declaration."), "expect": "spec", "status": "active", "expect_error": "step awaits actual Improve"},
        {"at": "spec", "command": "finish-improve", "receipt": _receipt("spec"), "expect": "test-strategy", "status": "active"},
        {"at": "test-strategy", "command": "duplicate-finish-improve", "receipt": _receipt("spec"), "expect": "test-strategy", "status": "active"},
        {"at": "test-strategy", "command": "conflicting-finish-improve", "receipt": _receipt("spec", marker="conflict"), "expect": "test-strategy", "status": "active", "expect_error": "conflicting Improve completion replay"},
        {"at": "test-strategy", "command": "stale-finish-improve", "receipt": _receipt("test-strategy"), "expect": "test-strategy", "status": "active", "expect_error": "stale Improve parent action"},
    ]
    cases["synthetic-v3-improve-replay-guards"] = _synthetic_case(
        "synthetic-v3-improve-replay-guards", wait_steps, {"stage": "test-strategy", "status": "active"}
    )

    paused_steps = [
        {"at": "intake", "command": "pause", "expect": "intake", "status": "paused"},
        {"at": "intake", "command": "cold-load", "expect": "intake", "status": "paused"},
        {"at": "intake", "command": "resume", "expect": "intake", "status": "active"},
        {"at": "intake", "command": "produce", "result": _result("intake"), "expect": "discovery", "status": "active"},
        {"at": "discovery", "command": "produce", "result": _result("discovery", outcome="blocked"), "expect": "discovery", "status": "blocked"},
        {"at": "discovery", "command": "cold-load", "expect": "discovery", "status": "blocked"},
        {"at": "discovery", "command": "resume", "expect": "discovery", "status": "active"},
        {"at": "discovery", "command": "produce", "result": _result("discovery"), "expect": "research", "status": "active"},
        {"at": "research", "command": "produce", "result": _result("research"), "expect": "spec", "status": "active"},
        {"at": "spec", "command": "produce", "result": _result("spec"), "expect": "spec", "status": "active"},
        {"at": "spec", "command": "pause", "expect": "spec", "status": "paused"},
        {"at": "spec", "command": "cold-load", "expect": "spec", "status": "paused"},
        {"at": "spec", "command": "resume", "expect": "spec", "status": "active"},
        {"at": "spec", "command": "finish-improve", "receipt": _receipt("spec"), "final_result": _result("spec", outcome="blocked"), "expect": "spec", "status": "blocked"},
        {"at": "spec", "command": "resume", "expect": "spec", "status": "active"},
        {"at": "spec", "command": "produce", "result": _result("spec"), "expect": "spec", "status": "active"},
        {"at": "spec", "command": "finish-improve", "receipt": _receipt("spec", marker="retry"), "expect": "test-strategy", "status": "active"},
    ]
    cases["synthetic-v3-pause-blocked-cold-recovery"] = _synthetic_case(
        "synthetic-v3-pause-blocked-cold-recovery", paused_steps, {"stage": "test-strategy", "status": "active"}
    )

    repeat_prefix = _v3_path_steps(_V3_PRELUDE + ("select-work",), terminal_target="step-plan")
    repeat_steps = repeat_prefix + [
        {"at": "step-plan", "command": "produce", "result": _result("step-plan", outcome="repeat"), "expect": "step-plan", "status": "active"},
        {"at": "step-plan", "command": "finish-improve", "receipt": _receipt("step-plan"), "final_result": _result("step-plan", outcome="repeat"), "expect": "step-plan", "status": "active"},
        {"at": "step-plan", "command": "produce", "result": _result("step-plan"), "expect": "step-plan", "status": "active"},
        {"at": "step-plan", "command": "finish-improve", "receipt": _receipt("step-plan"), "expect": "test-spec", "status": "active"},
    ]
    cases["synthetic-v3-repeat"] = _synthetic_case(
        "synthetic-v3-repeat", repeat_steps, {"stage": "test-spec", "status": "active", "owner": "W1"}
    )

    corrective_prefix = _v3_path_steps(
        _V3_PRELUDE + _V3_INNER + ("system-test-author",), terminal_target="system-test"
    )
    corrective_steps = corrective_prefix + [
        # system-test is not a checkpoint: its corrective replan applies directly.
        {"at": "system-test", "owner": "root", "command": "produce", "result": _result("system-test", outcome="replan", work_items=[{"id": "W2", "title": "Corrective synthetic item"}]), "expect": "select-work", "expect_owner": "W2", "status": "active"},
        *_v3_path_steps(_V3_INNER + _V3_OUTER, active_owner="W2"),
    ]
    cases["synthetic-v3-corrective-replan"] = _synthetic_case(
        "synthetic-v3-corrective-replan", corrective_steps,
        {"stage": "done", "status": "done", "completed_work_items": ["W1", "W2"]}
    )

    error_steps = [
        {"at": "intake", "command": "stale-produce", "result": _result("intake"), "expect": "intake", "status": "active", "expect_error": "stale navigator action ID"},
        {"at": "intake", "command": "malformed-produce", "result": {"outcome": "done"}, "expect": "intake", "status": "active", "expect_error": "result requires outcome and summary"},
        {"at": "intake", "command": "produce", "result": _result("intake"), "expect": "discovery", "status": "active"},
    ]
    cases["synthetic-v3-stale-and-malformed"] = _synthetic_case(
        "synthetic-v3-stale-and-malformed", error_steps, {"stage": "discovery", "status": "active"}
    )
    # A negative control: intake truly advances to discovery, so this expected
    # edge must fail. A replay that reported it green would be a broken oracle.
    cases["synthetic-v3-wrong-edge-control"] = _synthetic_case(
        "synthetic-v3-wrong-edge-control",
        [{"at": "intake", "command": "produce", "result": _result("intake"), "expect": "research", "status": "active"}],
        {"stage": "discovery", "status": "active"},
        expected_failure="expected edge intake -> research/active, got discovery/active",
    )
    for case in cases.values():
        validate_case(case, origin=f"synthetic {case['id']}")
    return cases


def _source_fingerprint(skill_root: Path) -> dict[str, Any]:
    """Use the harness's full package closure manifest, including references."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from evidence import package_manifest  # local harness utility; no model or project work

    try:
        manifest = package_manifest(skill_root)
    except (OSError, ValueError) as exc:
        raise DagReplayError(f"cannot fingerprint selected skill root: {exc}") from exc
    return {
        "root": manifest["resolved_root"],
        "package_sha256": manifest["aggregate_sha256"],
        "file_count": len(manifest["files"]),
        "file_hashes": manifest["file_hashes"],
        "skipped": manifest["skipped"],
    }


def _fixture_after(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Rehash a file fixture without interpreting its retained provenance."""
    observed = dict(fixture)
    if fixture.get("kind") == "file":
        path = Path(str(fixture["path"]))
        try:
            observed["sha256"] = _file_hash(path)
        except OSError:
            observed["sha256"] = None
    return observed


def _load_navigator(skill_root: Path, package_fingerprint: Mapping[str, Any]) -> Any:
    """Import navigator only when every cached ShipLoop script resolves under root."""
    scripts = skill_root / "scripts"
    target = (scripts / "shiploop_navigator.py").resolve()
    if not target.is_file():
        raise DagReplayError("selected skill root has no shiploop_navigator.py")
    package_sha256 = package_fingerprint.get("package_sha256")
    if not isinstance(package_sha256, str) or len(package_sha256) != 64:
        raise DagReplayError("selected ShipLoop package fingerprint is invalid")
    root_key = str(skill_root.resolve())
    loaded_sha256 = _PROCESS_LOADED_PACKAGE_SHA256.get(root_key)
    if loaded_sha256 is not None and loaded_sha256 != package_sha256:
        raise DagReplayError(
            "selected ShipLoop package differs from the source first loaded in this process"
        )
    foreign = []
    for name, module in tuple(sys.modules.items()):
        if name in _ENGINE_MODULES:
            module_file = getattr(module, "__file__", None)
            if module_file and not _within(Path(module_file), scripts):
                foreign.append(name)
    if foreign:
        raise DagReplayError(
            "selected ShipLoop source conflicts with already-cached modules: " + ", ".join(sorted(foreign))
        )
    scripts_text = str(scripts.resolve())
    if scripts_text not in sys.path:
        sys.path.insert(0, scripts_text)
    importlib.invalidate_caches()
    navigator = importlib.import_module("shiploop_navigator")
    if Path(getattr(navigator, "__file__", "")).resolve() != target:
        raise DagReplayError("navigator import did not bind to selected skill root")
    for name, module in tuple(sys.modules.items()):
        if name in _ENGINE_MODULES and getattr(module, "__file__", None):
            if not _within(Path(module.__file__), scripts):
                raise DagReplayError(f"selected ShipLoop dependency did not bind to selected root: {name}")
    if loaded_sha256 is None:
        _PROCESS_LOADED_PACKAGE_SHA256[root_key] = package_sha256
    return navigator


def _packet(core: Any, navigator: Any, run_dir: Path, state: Mapping[str, Any], report_dir: Path,
            sequence: int, label: str) -> dict[str, Any]:
    packet = navigator.render(core, run_dir, state)
    packets = report_dir / "packets"
    packets.mkdir(parents=True, exist_ok=True)
    path = packets / f"{sequence:03d}-{label}.md"
    path.write_text(packet, encoding="utf-8")
    return {"path": str(path.relative_to(report_dir)), "sha256": _sha256(packet), "bytes": len(packet.encode("utf-8"))}


def _state_hash(state: Mapping[str, Any]) -> str:
    return _sha256(_json_bytes(state))


def _load_durable(navigator: Any, run_dir: Path) -> dict[str, Any]:
    try:
        state = navigator.store.read_record(run_dir / "state.md")
        navigator.validate(state)
    except (OSError, ValueError) as exc:
        raise DagReplayError(f"cold-load failed: {exc}") from exc
    if not isinstance(state, dict):
        raise DagReplayError("cold-load did not produce a navigator state object")
    return state


class _MockSession:
    """One bounded local subprocess per replay case; no shell is involved."""

    def __init__(self, case_dir: Path):
        if not MOCK_PATH.is_file():
            raise DagReplayError("mock_grok.py is unavailable")
        env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR") if key in os.environ}
        env["PYTHONIOENCODING"] = "utf-8"
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(MOCK_PATH)],
            cwd=case_dir,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self.stdout_lines: list[str] = []
        self._stdout_buffer = b""
        self._closed = False

    def _line(self) -> bytes:
        """Read exactly one complete JSONL record without blocking on a partial line."""
        if self.process.stdout is None:
            raise DagReplayError("mock callback transport stdout is unavailable")
        deadline = time.monotonic() + _MOCK_RESPONSE_TIMEOUT_SECONDS
        while b"\n" not in self._stdout_buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DagReplayError("mock callback transport timed out")
            ready, _, _ = select.select([self.process.stdout.fileno()], [], [], remaining)
            if not ready:
                raise DagReplayError("mock callback transport timed out")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                raise DagReplayError("mock callback transport closed before its complete response")
            self._stdout_buffer += chunk
        line, self._stdout_buffer = self._stdout_buffer.split(b"\n", 1)
        return line[:-1] if line.endswith(b"\r") else line

    def call(self, request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
        if self.process.stdin is None or self.process.stdout is None:
            raise DagReplayError("mock callback transport pipes are unavailable")
        raw = _json_bytes(request)
        self.process.stdin.write(raw + b"\n")
        self.process.stdin.flush()
        call_raw = self._line()
        update_raw = self._line()
        try:
            call = json.loads(call_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
            update = json.loads(update_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DagReplayError("mock callback transport emitted invalid JSON") from exc
        self.stdout_lines.extend((call_raw.decode("utf-8"), update_raw.decode("utf-8")))
        return call, update, _sha256(raw)

    def close(self) -> dict[str, Any]:
        if self._closed:
            return {"stdout": "\n".join(self.stdout_lines), "stderr": "", "returncode": None}
        self._closed = True
        try:
            if self.process.stdin is not None and not self.process.stdin.closed:
                self.process.stdin.close()
            try:
                returncode = self.process.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                self.process.kill()
                self.process.wait(timeout=5)
                raise DagReplayError("mock callback transport did not exit in time") from exc
            tail = self._stdout_buffer + (b"" if self.process.stdout is None else self.process.stdout.read())
            stderr = b"" if self.process.stderr is None else self.process.stderr.read()
            if not tail.endswith(b"\n"):
                raise DagReplayError("mock callback transport ended with a partial or missing terminal record")
            terminal_lines = [line for line in tail.splitlines() if line]
            if len(terminal_lines) != 1:
                raise DagReplayError("mock callback transport emitted unexpected terminal events")
            try:
                terminal = json.loads(terminal_lines[0].decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DagReplayError("mock callback transport terminal record is invalid JSON") from exc
            if not isinstance(terminal, dict) or terminal != {
                "type": "end", "synthetic": True, "modelCalls": 0, "modelUsage": {}
            }:
                raise DagReplayError("mock callback transport terminal record is incomplete or not synthetic")
            self.stdout_lines.append(terminal_lines[0].decode("utf-8"))
            return {
                "stdout": "\n".join(self.stdout_lines),
                "stderr": stderr.decode("utf-8", "replace"),
                "returncode": returncode,
                "terminal": terminal,
            }
        finally:
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()


def _validate_mock_binding(call: Any, update: Any, request: Mapping[str, Any], request_sha256: str) -> dict[str, Any]:
    if not isinstance(call, dict) or not isinstance(update, dict):
        raise DagReplayError("mock callback response must contain objects")
    callback_id = request["callback_id"]
    if call.get("type") != "tool_call" or call.get("toolCallId") != callback_id or call.get("synthetic") is not True:
        raise DagReplayError("mock tool_call does not bind the callback")
    if call.get("rawInput") != request:
        raise DagReplayError("mock tool_call did not preserve exact request binding")
    if update.get("type") != "tool_call_update" or update.get("toolCallId") != callback_id:
        raise DagReplayError("mock tool_call_update does not bind the callback")
    if update.get("status") != "completed" or update.get("synthetic") is not True:
        raise DagReplayError("mock callback update is not a completed simulation")
    output = update.get("rawOutput")
    if not isinstance(output, dict):
        raise DagReplayError("mock callback update lacks rawOutput")
    for key in ("callback_id", "action_id", "stage", "owner", "command"):
        if output.get(key) != request[key]:
            raise DagReplayError(f"mock callback binding mismatch for {key}")
    if output.get("schema") != MOCK_RESPONSE_SCHEMA or output.get("simulation_only") is not True:
        raise DagReplayError("mock callback output is not explicitly synthetic")
    if output.get("request_sha256") != request_sha256:
        raise DagReplayError("mock callback request hash does not match exact stdin bytes")
    for key in ("result", "receipt", "final_result"):
        if (key in output) != (key in request) or (key in request and output[key] != request[key]):
            raise DagReplayError(f"mock callback binding mismatch for {key}")
    return output


def _submitted_action(step: Mapping[str, Any], command: str, current_action: Mapping[str, Any],
                      last_accepted_action: str | None) -> str:
    mode = step.get("action", "current")
    if command in {"duplicate-finish-improve", "conflicting-finish-improve"}:
        mode = "last-accepted"
    elif command in {"stale-produce", "stale-finish-improve"}:
        mode = "stale"
    if mode == "current":
        return str(current_action["id"])
    if mode == "last-accepted" and last_accepted_action:
        return last_accepted_action
    if mode in {"last-accepted", "stale"}:
        # A syntactically valid but never-current action is enough to exercise
        # the real stale-action guard before any callback is accepted.
        return "nav-stale-" + _sha256(str(current_action["id"]))[:20]
    raise DagReplayError("unsupported fixture action selector")


def _apply_callback(navigator: Any, state: Mapping[str, Any], command: str, output: Mapping[str, Any]) -> dict[str, Any]:
    action_id = output["action_id"]
    if command in {"done", "produce", "stale-produce", "duplicate-produce", "conflicting-produce", "malformed-produce"}:
        return navigator.apply(state, action_id, output["result"])
    if command in {"finish-improve", "duplicate-finish-improve", "conflicting-finish-improve", "stale-finish-improve"}:
        return navigator.finish_improve(state, action_id, output["receipt"], output.get("final_result"))
    if command in {"pause", "resume", "halt"}:
        return navigator.control(state, command, "Synthetic DAG replay control event.")
    raise DagReplayError(f"unsupported replay command: {command}")


def _literal_checkpoint(before: Mapping[str, Any], stage: str, result: Any) -> bool:
    """Say whether this producer result must park for Improve, per the literal schedule."""
    if stage in _V3_PLANNING_CHECKPOINTS:
        return True
    if stage != "carry-forward" or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return False
    if "work_items" in result:
        return not result["work_items"]
    return before["work_index"] + 1 >= len(before["work_items"])


def _assert_v3_cursor_invariants(navigator: Any, before: Mapping[str, Any], after: Mapping[str, Any],
                                 command: str, submitted_action: str, result: Any = None) -> None:
    """Check packet-level v3 invariants the coarse stage oracle cannot see."""
    producer = {"done", "produce", "duplicate-produce", "conflicting-produce", "malformed-produce"}
    if command in producer:
        before_action = navigator.current_action(before)["id"]
        after_action = navigator.current_action(after)["id"]
        parked = before.get("active_improve")
        child = after.get("active_improve")
        if submitted_action in before.get("accepted", {}):
            if _state_hash(before) != _state_hash(after):
                raise DagReplayError("v3 producer replay changed an accepted action")
        elif parked is not None:
            if after_action != before_action or child != parked:
                raise DagReplayError("v3 producer replay replaced the parked Improve child")
        elif _literal_checkpoint(before, navigator.current_stage(before), result):
            if after_action != before_action:
                raise DagReplayError("v3 producer replaced the parent action instead of parking it for Improve")
            if not isinstance(child, Mapping) or child.get("action_id") != submitted_action:
                raise DagReplayError("v3 producer did not bind active Improve to the submitted parent action")
            if child.get("stage") != navigator.current_stage(before):
                raise DagReplayError("v3 producer bound Improve to the wrong stage")
        else:
            if child is not None:
                raise DagReplayError("v3 producer parked Improve outside a checkpoint")
            if after_action == before_action:
                raise DagReplayError("v3 producer did not accept its result outside a checkpoint")
    if command == "finish-improve" and before.get("active_improve") is not None:
        child = before["active_improve"]
        if child.get("action_id") != submitted_action:
            raise DagReplayError("v3 Improve completion was not bound to the active parent action")
        if after.get("active_improve") is not None:
            raise DagReplayError("v3 Improve completion did not clear the active child")
        if navigator.current_action(after)["id"] == navigator.current_action(before)["id"]:
            raise DagReplayError("v3 Improve completion did not create a successor action")
    if command == "cold-load" and _state_hash(before) != _state_hash(after):
        raise DagReplayError("cold-load did not restore the exact durable state")


def _expected_edge(index: int, step: Mapping[str, Any], state: Mapping[str, Any]) -> None:
    actual_stage = str(state.get("stage"))
    # The effective current stage is handled by the caller; this helper exists
    # only to produce a stable, calibration-friendly error after a transition.
    del actual_stage
    expected_status = step.get("status", "active")
    # Caller has already materialized the effective stage in a private field.
    got_stage = state["_replay_effective_stage"]
    if got_stage != step["expect"] or state["status"] != expected_status:
        raise DagReplayError(
            f"event {index}: expected edge {step['at']} -> {step['expect']}/{expected_status}, "
            f"got {got_stage}/{state['status']}"
        )
    if "expect_owner" in step and state["_replay_owner"] != step["expect_owner"]:
        raise DagReplayError(
            f"event {index}: expected owner {step['expect_owner']}, got {state['_replay_owner']}"
        )


def replay_case(case: Mapping[str, Any], *, fixture: Mapping[str, Any], output: Path,
                skill_root: Path | None = None, expected_source: Mapping[str, Any] | None = None,
                expected_harness: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Replay a validated case and write packet/state evidence under ``output``."""
    case = validate_case(dict(case), origin=str(fixture.get("path", case.get("id", "case"))))
    skill_root = (DEFAULT_SKILL_ROOT if skill_root is None else skill_root).expanduser().resolve()
    if not (skill_root / "SKILL.md").is_file():
        raise DagReplayError("selected skill root must contain SKILL.md")
    report_dir = output / "cases" / case["id"]
    report_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    source_before = _source_fingerprint(skill_root)
    harness_before = {"dag_replay.py": _file_hash(Path(__file__)), "mock_grok.py": _file_hash(MOCK_PATH)}
    report: dict[str, Any] = {
        "schema": "shiploop-e2e-dag-replay/1",
        "id": case["id"],
        "kind": case["kind"],
        "protocol_version": case["protocol_version"],
        "fixture": dict(fixture),
        "provenance": case["provenance"],
        "simulation_only": True,
        "model_calls": 0,
        "product_verdict": "not-assessed",
        "live_verdict": "not-assessed",
        "captured_command_execution": "none",
        "scope": SIMULATION_SCOPE,
        "transition_engine": str((skill_root / "scripts" / "shiploop_navigator.py").resolve()),
        "source_before": source_before,
        "harness_before": harness_before,
        "expected_source": dict(expected_source) if expected_source is not None else None,
        "expected_harness": dict(expected_harness) if expected_harness is not None else None,
        "events": [],
        "expected_final": case["expected_final"],
        "ok": False,
        "replay_status": "synthetic-apparatus-failed",
    }

    def invalid_preflight(reason: str, *, source_after: Mapping[str, Any] | None = None) -> dict[str, Any]:
        observed_source = dict(source_after or source_before)
        fixture_after = _fixture_after(fixture)
        report.update(
            error=reason,
            source_after=observed_source,
            harness_after=harness_before,
            fixture_after=fixture_after,
            source_stable=source_before == observed_source,
            harness_stable=True,
            fixture_stable=dict(fixture) == fixture_after,
            source_matches_expected=expected_source is None or source_before == expected_source,
            harness_matches_expected=expected_harness is None or harness_before == expected_harness,
            process_loaded_package_sha256=_PROCESS_LOADED_PACKAGE_SHA256.get(str(skill_root)),
            mock_transport={"subprocesses": 0, "status": "not-started"},
            ok=False,
            replay_status="synthetic-apparatus-invalid-drift",
            duration_seconds=time.monotonic() - started,
        )
        (report_dir / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return report

    if expected_source is not None and source_before != expected_source:
        return invalid_preflight("selected skill source drifted before this suite case")
    if expected_harness is not None and harness_before != expected_harness:
        return invalid_preflight("replay harness drifted before this suite case")
    try:
        navigator = _load_navigator(skill_root, source_before)
    except DagReplayError as exc:
        return invalid_preflight(str(exc))
    source_bound = _source_fingerprint(skill_root)
    if source_bound != source_before:
        return invalid_preflight("selected skill source changed while binding the navigator", source_after=source_bound)
    core = SimpleNamespace(PACKAGE_ROOT=skill_root, REF_DIR=skill_root / "references")
    run_dir = report_dir / "run"
    run_dir.mkdir()
    state = navigator.new_state(
        f"/simulation-only/dag-replay/{case['id']}",
        case.get("prompt", "Synthetic ShipLoop DAG replay fixture; no project work."),
        protocol_version=case["protocol_version"],
        improve_skill="",
    )
    navigator.save(run_dir, state)
    initial_state = _load_durable(navigator, run_dir)
    report["initial_state_sha256"] = _state_hash(initial_state)
    mock = _MockSession(report_dir)
    mock_summary: dict[str, Any] | None = None
    try:
        for index, step in enumerate(case["steps"], 1):
            command = step.get("command", "done")
            current_stage = navigator.current_stage(state)
            current_action = navigator.current_action(state)
            current_owner = _owner(state)
            if current_stage != step["at"]:
                raise DagReplayError(f"event {index}: expected current {step['at']}, got {current_stage}")
            if "owner" in step and current_owner != step["owner"]:
                raise DagReplayError(f"event {index}: expected current owner {step['owner']}, got {current_owner}")
            last_accepted = state["history"][-1]["action"] if state["history"] else None
            submitted_action = _submitted_action(step, command, current_action, last_accepted)
            callback_id = f"mock-{case['id']}-{index:03d}"
            request: dict[str, Any] = {
                "schema": MOCK_REQUEST_SCHEMA,
                "simulation_only": True,
                "callback_id": callback_id,
                "action_id": submitted_action,
                "stage": current_stage,
                "owner": current_owner,
                "command": command,
            }
            for key in ("result", "receipt", "final_result"):
                if key in step:
                    request[key] = step[key]
            pre_state = deepcopy(state)
            durable_before = _file_hash(run_dir / "state.md")
            event: dict[str, Any] = {
                "sequence": index,
                "command": command,
                "from": current_stage,
                "owner": current_owner,
                "current_action_id": current_action["id"],
                "submitted_action_id": submitted_action,
                "callback_id": callback_id,
                "pre_revision": state["revision"],
                "pre_state_sha256": _state_hash(state),
                "pre_packet": _packet(core, navigator, run_dir, state, report_dir, index, "pre"),
                "expected": {"stage": step["expect"], "status": step.get("status", "active"), "owner": step.get("expect_owner")},
            }
            call, update, request_sha256 = mock.call(request)
            output_value = _validate_mock_binding(call, update, request, request_sha256)
            event["request_sha256"] = request_sha256
            event["mock_tool_call_sha256"] = _sha256(_json_bytes(call))
            event["mock_tool_call_update_sha256"] = _sha256(_json_bytes(update))
            try:
                if command == "cold-load":
                    state = _load_durable(navigator, run_dir)
                else:
                    state = _apply_callback(navigator, state, command, output_value)
                if "expect_error" in step:
                    raise DagReplayError(f"event {index}: expected engine error was not raised")
            except (ValueError, KeyError, TypeError) as exc:
                message = str(exc)
                event["engine_error"] = message
                expected_error = step.get("expect_error")
                if not expected_error or expected_error not in message:
                    raise DagReplayError(f"event {index}: unexpected engine error: {message}") from exc
                if _state_hash(state) != event["pre_state_sha256"] or _file_hash(run_dir / "state.md") != durable_before:
                    raise DagReplayError("rejected callback mutated navigator state or durable state")
                event["expected_error_observed"] = True
                state = pre_state
            else:
                _assert_v3_cursor_invariants(navigator, pre_state, state, command, submitted_action,
                                             output_value.get("result"))
                if state != pre_state:
                    navigator.save(run_dir, state)
            effective_stage = navigator.current_stage(state)
            effective_owner = _owner(state)
            state_for_edge = dict(state)
            state_for_edge["_replay_effective_stage"] = effective_stage
            state_for_edge["_replay_owner"] = effective_owner
            event.update(
                to=effective_stage,
                next_owner=effective_owner,
                post_action_id=navigator.current_action(state)["id"],
                post_revision=state["revision"],
                post_state_sha256=_state_hash(state),
                post_packet=_packet(core, navigator, run_dir, state, report_dir, index, "post"),
                active_improve=state.get("active_improve") is not None,
                completed_work_items=list(state["completed_work_items"]),
            )
            report["events"].append(event)
            _expected_edge(index, step, state_for_edge)
        final_stage = navigator.current_stage(state)
        final_owner = _owner(state)
        expected_final = case["expected_final"]
        if final_stage != expected_final["stage"] or state["status"] != expected_final["status"]:
            raise DagReplayError(
                f"final mismatch: expected {expected_final['stage']}/{expected_final['status']}, "
                f"got {final_stage}/{state['status']}"
            )
        if "owner" in expected_final and final_owner != expected_final["owner"]:
            raise DagReplayError(f"final owner mismatch: expected {expected_final['owner']}, got {final_owner}")
        if "completed_work_items" in expected_final and state["completed_work_items"] != expected_final["completed_work_items"]:
            raise DagReplayError(
                "final completed work items mismatch: expected "
                f"{expected_final['completed_work_items']}, got {state['completed_work_items']}"
            )
        if case.get("expected_failure"):
            report.update(
                error="expected failure was not observed: " + case["expected_failure"],
                expected_failure_missing=True,
                ok=False,
                replay_status="synthetic-apparatus-failed",
            )
        else:
            report.update(
                final={"stage": final_stage, "status": state["status"], "owner": final_owner,
                       "revision": state["revision"], "state_sha256": _state_hash(state),
                       "completed_work_items": list(state["completed_work_items"])},
                ok=True,
                replay_status="synthetic-apparatus-passed",
            )
    except (DagReplayError, ValueError, KeyError, TypeError) as exc:
        message = str(exc)
        report["error"] = message
        expected_failure = case.get("expected_failure")
        if expected_failure and expected_failure in message:
            report.update(ok=True, expected_failure_observed=True, replay_status="synthetic-apparatus-expected-failure-observed")
        else:
            report["replay_status"] = "synthetic-apparatus-failed"
    finally:
        try:
            mock_summary = mock.close()
        except DagReplayError as exc:
            report.update(mock_close_error=str(exc), ok=False, replay_status="synthetic-apparatus-failed")
    source_after = _source_fingerprint(skill_root)
    harness_after = {"dag_replay.py": _file_hash(Path(__file__)), "mock_grok.py": _file_hash(MOCK_PATH)}
    report["source_after"] = source_after
    report["harness_after"] = harness_after
    fixture_after = _fixture_after(fixture)
    report["fixture_after"] = fixture_after
    report["source_stable"] = source_before == source_after
    report["harness_stable"] = harness_before == harness_after
    report["fixture_stable"] = fixture == fixture_after
    if not (report["source_stable"] and report["harness_stable"] and report["fixture_stable"]):
        report.update(ok=False, replay_status="synthetic-apparatus-invalid-drift")
    if mock_summary is not None:
        report["mock_transport"] = {"subprocesses": 1, **mock_summary}
        if mock_summary["returncode"] != 0 or "SHIPLOOP_E2E_SIMULATION_ONLY" not in mock_summary["stderr"]:
            report.update(ok=False, replay_status="synthetic-apparatus-failed")
    report["duration_seconds"] = time.monotonic() - started
    (report_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _default_cases() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(case, {"kind": "in-code-synthetic", "sha256": _canonical_fixture_digest(case)})
            for case in synthetic_cases().values()]


def _new_external_output(path: Path, skill_root: Path) -> Path:
    try:
        output = layout.validate_new_external_output(path, subject_root=skill_root)
    except ValueError as exc:
        raise DagReplayError(str(exc)) from exc
    output.mkdir(parents=True)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", type=Path, help="repeatable JSON case path; defaults to the in-code synthetic cases")
    parser.add_argument("--output", type=Path, required=True, help="new external output directory")
    parser.add_argument("--skill-root", type=Path, help="selected ShipLoop skill root to fingerprint and execute")
    args = parser.parse_args(argv)
    try:
        selected_root, subject_selection = layout.resolve_skill_binding(args.skill_root)
        suite_source = _source_fingerprint(selected_root)
        output = _new_external_output(args.output, selected_root)
        selected = [load_case(path.expanduser().resolve()) for path in args.case] if args.case else _default_cases()
        ids = [case["id"] for case, _fixture in selected]
        if len(ids) != len(set(ids)):
            raise DagReplayError("case ids must be unique in one replay")
        suite_harness = {"dag_replay.py": _file_hash(Path(__file__)), "mock_grok.py": _file_hash(MOCK_PATH)}
        reports = [replay_case(case, fixture=fixture, output=output, skill_root=selected_root,
                               expected_source=suite_source, expected_harness=suite_harness)
                   for case, fixture in selected]
        receipt = {
            "schema": "shiploop-e2e-dag-replay-suite/1",
            "simulation_only": True,
            "model_calls": 0,
            "scope": SIMULATION_SCOPE,
            "harness": {"root": str(HERE), "package_root": str(layout.PACKAGE_ROOT)},
            "selected_subject": {"root": suite_source["root"], "package_sha256": suite_source["package_sha256"],
                                 "file_count": suite_source["file_count"], "selection": subject_selection,
                                 "default_selection": layout.default_skill_binding()[1]},
            "reports": [{"id": report["id"], "ok": report["ok"], "replay_status": report["replay_status"]} for report in reports],
            "status": "synthetic-apparatus-passed" if all(report["ok"] for report in reports) else "synthetic-apparatus-failed",
            "product_verdict": "not-assessed",
            "live_verdict": "not-assessed",
        }
        (output / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))
        return 0 if all(report["ok"] for report in reports) else 2
    except DagReplayError as exc:
        print(f"DAG replay input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
