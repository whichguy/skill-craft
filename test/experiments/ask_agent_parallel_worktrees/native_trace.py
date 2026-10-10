#!/usr/bin/env python3
"""Audit retained native Grok spawn and collection evidence for one fixture run.

This is an offline observer. It never starts Grok or treats generated worker
text as proof. Root tool calls come from the session-id-bound Grok updates log;
event times come only from the controller's observed.jsonl wrappers.
"""
from __future__ import annotations

import argparse
import ast
from diagnostics import emit_diagnostics, evidence_reference, make_diagnostic, report_check_diagnostics

from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import shlex
import sys
from typing import Any
from urllib.parse import quote


SCHEMA = "ask-agent-native-verification/v1"
ROOT_METHODS = {"session/update", "_x.ai/session/update"}
NONTERMINAL = {"", "pending", "running", "queued", "in_progress", "in-progress"}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class TraceError(RuntimeError):
    """The retained evidence is malformed or contradicts the requested claim."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise TraceError(f"{label} is not readable JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TraceError(f"{label} must contain a JSON object")
    return value


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise TraceError(f"could not read {label}: {exc}") from exc
    if not lines:
        raise TraceError(f"{label} is empty")
    result: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line:
            raise TraceError(f"{label} has an empty line at {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(f"{label} has invalid JSON at line {number}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise TraceError(f"{label} has a non-object record at line {number}")
        result.append(value)
    return result


def _finite_number(value: Any) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _locator(path: Path, line: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path.resolve())}
    if line is not None:
        result["line"] = line
    return result


def _check(status: str, detail: str, *evidence: dict[str, Any]) -> dict[str, Any]:
    return {"status": status, "detail": detail, "evidence": list(evidence)}


def _overall(checks: dict[str, dict[str, Any]]) -> str:
    statuses = {item["status"] for item in checks.values()}
    if "FAIL" in statuses:
        return "FAIL"
    if "INCOMPLETE" in statuses:
        return "INCOMPLETE"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "PASS"


def _session_updates_path(run: Path, launch: dict[str, Any], session_root: Path) -> Path:
    session_id = launch.get("session_id")
    cwd = launch.get("cwd")
    if not isinstance(session_id, str) or UUID_RE.fullmatch(session_id) is None:
        raise TraceError("launch.json has no Grok UUID parent session_id")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        raise TraceError("launch.json has no absolute parent cwd")
    # Grok stores sessions beneath a percent-encoded cwd directory. This exact
    # lookup binds one session and avoids searching unrelated session history.
    candidate = session_root / quote(str(Path(cwd).resolve()), safe="") / session_id / "updates.jsonl"
    if not candidate.exists():
        # Some versions encode a worktree path with the native session root as
        # the directory. A bounded exact-id lookup is still session-scoped.
        matches = list(session_root.glob(f"*/{session_id}/updates.jsonl"))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise TraceError("multiple Grok updates logs match the launch session id")
    return candidate


def _child_updates_path(cwd: str, session_id: str, session_root: Path) -> Path:
    if UUID_RE.fullmatch(session_id) is None or not Path(cwd).is_absolute():
        raise TraceError("native child binding lacks a UUID session id or absolute cwd")
    candidate = session_root / quote(str(Path(cwd).resolve()), safe="") / session_id / "updates.jsonl"
    if candidate.exists():
        return candidate
    matches = list(session_root.glob(f"*/{session_id}/updates.jsonl"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise TraceError(f"multiple Grok updates logs match child session {session_id}")
    return candidate


def _retain_transcript(source: Path, destination: Path) -> dict[str, Any]:
    """Keep one exact, session-bound updates log with the run for later audits."""
    same_path = source.resolve() == destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    source_bytes = source.read_bytes()
    if same_path:
        if not destination.is_file():
            raise FileNotFoundError(destination)
        source_digest = None
        matches_source = None
    elif destination.exists():
        if not destination.is_file():
            raise TraceError(f"retained transcript is not a regular file: {destination}")
        matches_source = source_bytes == destination.read_bytes()
        source_digest = hashlib.sha256(source_bytes).hexdigest()
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_bytes)
        matches_source = True
        source_digest = hashlib.sha256(source_bytes).hexdigest()
    retained = destination
    retained_digest = hashlib.sha256(retained.read_bytes()).hexdigest()
    return {
        "source": _locator(source) if source.exists() and not same_path else None,
        "retained": _locator(retained),
        "sha256": retained_digest,
        "source_sha256": source_digest,
        "retained_sha256": retained_digest,
        "matches_source": matches_source,
    }


def _retain_child_transcripts(run: Path, launches: list[dict[str, Any]],
                              session_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    retained_dir = run / "operator" / "native-evidence" / "children"
    reports: dict[str, Any] = {}
    missing: list[str] = []
    invalid: list[str] = []
    conflicts: list[dict[str, Any]] = []
    for launch in launches:
        child_id = launch.get("child_session_id")
        cwd = launch.get("cwd")
        worker = launch.get("worker_id")
        if not isinstance(child_id, str) or UUID_RE.fullmatch(child_id) is None or not isinstance(cwd, str):
            missing.append(str(worker or "?"))
            continue
        destination = retained_dir / child_id / "updates.jsonl"
        try:
            source = _child_updates_path(cwd, child_id, session_root)
            if not source.exists() and destination.exists():
                source = destination
            retention = _retain_transcript(source, destination)
            if retention.get("matches_source") is False:
                conflicts.append({
                    "worker_id": worker,
                    "child_session_id": child_id,
                    "source": retention.get("source"),
                    "retained": retention["retained"],
                    "source_sha256": retention["source_sha256"],
                    "retained_sha256": retention["retained_sha256"],
                })
            parsed = _root_updates(destination, child_id)
        except FileNotFoundError:
            missing.append(str(worker))
            continue
        except TraceError as exc:
            invalid.append(f"worker {worker}: {exc}")
            continue
        retention.update({"worker_id": worker, "child_session_id": child_id,
                          "update_count": len(parsed)})
        reports[child_id] = retention
    if invalid:
        return _check("FAIL", "; ".join(invalid)), reports
    if conflicts:
        evidence = [entry[key] for entry in conflicts for key in ("source", "retained") if entry.get(key)]
        return (_check("FAIL", "external child transcript differs from immutable retained evidence", *evidence)
                | {"conflicts": conflicts}), reports
    if missing:
        return _check("INCOMPLETE", "authoritative child updates unavailable for workers: " + ", ".join(missing)), reports
    if len(reports) != len(launches):
        return _check("UNKNOWN", "child transcript identity could not be established"), reports
    return _check("PASS", "each native child session log is identity-validated and retained with this run",
                  *[value["retained"] for value in reports.values()]), reports


def _root_updates(path: Path, session_id: str) -> list[dict[str, Any]]:
    records = _read_jsonl(path, "root updates")
    updates: list[dict[str, Any]] = []
    for number, record in enumerate(records, 1):
        if record.get("method") not in ROOT_METHODS:
            raise TraceError(f"root updates has unsupported method at line {number}")
        params = record.get("params")
        if not isinstance(params, dict) or params.get("sessionId") != session_id:
            raise TraceError(f"root updates has foreign or unlabelled parent at line {number}")
        update = params.get("update")
        if not isinstance(update, dict) or not isinstance(update.get("sessionUpdate"), str):
            raise TraceError(f"root updates has no typed sessionUpdate at line {number}")
        updates.append({"line": number, "update": update})
    return updates


def _observed(path: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(path, "observed stream")
    result: list[dict[str, Any]] = []
    for number, row in enumerate(rows, 1):
        epoch, elapsed, event = row.get("observed_epoch"), row.get("elapsed_s"), row.get("event")
        if _finite_number(epoch) is None or _finite_number(elapsed) is None:
            raise TraceError(f"observed stream has invalid typed time at line {number}")
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise TraceError(f"observed stream has no typed event at line {number}")
        result.append({"line": number, "epoch": float(epoch), "elapsed": float(elapsed), "event": event})
    return result


def _event_times(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        event = row["event"]
        call_id = event.get("toolCallId")
        if isinstance(call_id, str):
            index.setdefault((event["type"], call_id), []).append(row)
    return index


def _updates_for(updates: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [row for row in updates if row["update"].get("sessionUpdate") == kind]


def _terminal_update(call_id: str, updates: list[dict[str, Any]]) -> dict[str, Any] | None:
    terminal = [row for row in updates
                if row["update"].get("sessionUpdate") == "tool_call_update"
                and row["update"].get("toolCallId") == call_id
                and str(row["update"].get("status", "")).lower() not in NONTERMINAL]
    return terminal[-1] if terminal else None


def _unique_terminal_after(call_id: str, invocation_line: int,
                           updates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    terminal = [row for row in updates
                if row["update"].get("sessionUpdate") == "tool_call_update"
                and row["update"].get("toolCallId") == call_id
                and str(row["update"].get("status", "")).lower() not in NONTERMINAL]
    if len(terminal) != 1:
        return None, f"expected one terminal native result; found {len(terminal)}"
    result_line = terminal[0].get("line")
    if type(invocation_line) is not int or type(result_line) is not int:
        return None, "native invocation or terminal result has no retained line reference"
    if result_line <= invocation_line:
        return None, "terminal result does not follow its native command invocation"
    return terminal[0], None


def _packet_argument_check(run: Path, assignments: list[dict[str, Any]],
                           spawn_calls: list[dict[str, Any]], starts: dict[str, dict[str, Any]],
                           root_updates: list[dict[str, Any]], updates_path: Path,
                           root_session_dir: Path | None
                           ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Compare packet-treatment native arguments with the retained packet and script result."""
    operator = run / "operator"
    treatment_path = operator / "treatment.json"
    if not treatment_path.exists():
        return None, None
    try:
        treatment = _read_json(treatment_path, "treatment record")
    except TraceError as exc:
        return _check("UNKNOWN", f"treatment record cannot establish packet mode: {exc}",
                      _locator(treatment_path)), None
    if treatment.get("treatment") != "packet":
        return None, None

    packet_path = operator / "dispatch-packet.json"
    packet_evidence: dict[str, Any] = {"path": str(packet_path.resolve()), "sha256_at_audit": None}
    try:
        packet_bytes = packet_path.read_bytes()
    except FileNotFoundError:
        return (_check("INCOMPLETE", "packet treatment has no retained dispatch-packet.json",
                       _locator(treatment_path), _locator(packet_path), _locator(updates_path)),
                packet_evidence)
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()
    packet_evidence["sha256_at_audit"] = packet_sha
    try:
        packet = json.loads(packet_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return (_check("FAIL", f"dispatch packet is not valid UTF-8 JSON: {exc}",
                       _locator(treatment_path), _locator(packet_path), _locator(updates_path))
                | {"packet_sha256": packet_sha}, packet_evidence)

    expected_ids = [str(item.get("worker_id")) for item in assignments if isinstance(item, dict)]
    field_order = ("description", "prompt", "cwd", "background")
    field_names = set(field_order)
    issues: list[str] = []
    if not isinstance(packet, list):
        issues.append("dispatch packet must be a JSON list")
        packet_rows: list[Any] = []
    else:
        packet_rows = packet
    if len(packet_rows) != len(expected_ids):
        issues.append(f"dispatch packet has {len(packet_rows)} entries; expected {len(expected_ids)}")
    packet_by_worker: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(packet_rows):
        if not isinstance(entry, dict) or not isinstance(entry.get("worker_id"), str):
            issues.append(f"dispatch packet entry {index} has no string worker_id")
            continue
        if set(entry) != {"worker_id", "native_arguments"}:
            issues.append(f"dispatch packet entry {index} must contain only worker_id and native_arguments")
        worker = entry["worker_id"]
        native_arguments = entry.get("native_arguments")
        if worker in packet_by_worker:
            issues.append(f"dispatch packet repeats worker {worker}")
            continue
        if not isinstance(native_arguments, dict) or set(native_arguments) != field_names:
            issues.append(f"dispatch packet worker {worker} must have exactly description, prompt, cwd, and background")
            continue
        if (any(type(native_arguments.get(key)) is not str for key in ("description", "prompt", "cwd"))
                or type(native_arguments.get("background")) is not bool
                or native_arguments["background"] is not True):
            issues.append(f"dispatch packet worker {worker} has invalid argument value types or background=false")
            continue
        packet_by_worker[worker] = native_arguments
    if set(packet_by_worker) != set(expected_ids) or len(expected_ids) != len(set(expected_ids)):
        issues.append("dispatch packet worker IDs are not the unique manifest worker IDs")

    script_path = (operator / "briefs.py").resolve()
    run_path = str(run.resolve())
    script_calls: list[dict[str, Any]] = []
    for row in root_updates:
        update = row["update"]
        if update.get("sessionUpdate") != "tool_call" or update.get("title") != "run_terminal_command":
            continue
        raw = update.get("rawInput")
        command = raw.get("command") if isinstance(raw, dict) else None
        if not isinstance(command, str) or str(script_path) not in command:
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        script_positions = [index for index, token in enumerate(tokens)
                            if Path(token).is_absolute() and str(Path(token).resolve()) == str(script_path)]
        script_args = tokens[script_positions[0] + 1:] if len(script_positions) == 1 else []
        if (len(script_positions) == 1 and len(script_args) == 2
                and script_args[0] == "--run"
                and str(Path(script_args[1]).resolve()) == run_path):
            script_calls.append(row)
    packet_evidence["script_result"] = None
    script_result_row: dict[str, Any] | None = None
    if len(script_calls) != 1:
        issues.append("packet treatment requires exactly one typed briefs.py --run result")
    else:
        script_call = script_calls[0]
        call_id = script_call["update"].get("toolCallId")
        terminal = _terminal_update(str(call_id), root_updates) if isinstance(call_id, str) else None
        script_result_row = terminal
        if terminal is None:
            return (_check("INCOMPLETE", "typed briefs.py call has no terminal result",
                           _locator(treatment_path), _locator(packet_path), _locator(updates_path, script_call["line"]))
                    | {"packet_sha256": packet_sha},
                    packet_evidence | {"script_result": _locator(updates_path, script_call["line"])})
        script_output = terminal["update"].get("rawOutput")
        if terminal["update"].get("status") != "completed":
            return (_check("FAIL", "typed briefs.py command did not complete successfully",
                           _locator(treatment_path), _locator(packet_path), _locator(updates_path, script_call["line"]),
                           _locator(updates_path, terminal["line"])) | {"packet_sha256": packet_sha},
                    packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
        output_bytes: bytes | None = None
        stdout_evidence: list[dict[str, Any]] = []
        if isinstance(script_output, dict) and script_output.get("type") == "Bash":
            raw_output = script_output.get("output")
            if isinstance(raw_output, str):
                output_bytes = raw_output.encode("utf-8")
            elif (isinstance(raw_output, list)
                  and all(type(value) is int and 0 <= value <= 255 for value in raw_output)):
                output_bytes = bytes(raw_output)
            if type(script_output.get("exit_code")) is not int or script_output.get("exit_code") != 0:
                return (_check("FAIL", "typed briefs.py command returned a nonzero or untyped exit code",
                               _locator(treatment_path), _locator(packet_path), _locator(updates_path, script_call["line"]),
                               _locator(updates_path, terminal["line"])) | {"packet_sha256": packet_sha},
                        packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
            if script_output.get("truncated") is True:
                reported_path = script_output.get("output_file")
                total_bytes = script_output.get("total_bytes")
                if root_session_dir is None:
                    return (_check("INCOMPLETE", "truncated briefs.py stdout has no available authoritative parent session directory",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                call_id = script_call["update"].get("toolCallId")
                if (not isinstance(call_id, str) or not call_id or "/" in call_id or "\\" in call_id
                        or Path(call_id).name != call_id):
                    return (_check("FAIL", "briefs.py toolCallId is not a safe session terminal filename",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                expected_stdout_path = root_session_dir.resolve() / "terminal" / f"{call_id}.log"
                if not isinstance(reported_path, str) or reported_path != str(expected_stdout_path):
                    return (_check("FAIL", "truncated briefs.py output_file is not bound to this parent session and tool call",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "expected_output_file": str(expected_stdout_path),
                               "reported_output_file": reported_path},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                if type(total_bytes) is not int or not 0 < total_bytes <= 1024 * 1024:
                    return (_check("FAIL", "truncated briefs.py stdout has an invalid or oversized total_bytes value",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "total_bytes": total_bytes},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                if not isinstance(raw_output, list) or not all(type(value) is int and 0 <= value <= 255 for value in raw_output):
                    return (_check("FAIL", "truncated briefs.py stdout preview is not a byte list",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                preview = bytes(raw_output)
                if expected_stdout_path.is_symlink() or not expected_stdout_path.is_file():
                    return (_check("INCOMPLETE", "authoritative truncated briefs.py stdout file is missing or not a regular file",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "output_file": str(expected_stdout_path)},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                try:
                    source_size = expected_stdout_path.stat().st_size
                except OSError as exc:
                    return (_check("INCOMPLETE", f"cannot stat authoritative truncated briefs.py stdout file: {exc}",
                                   _locator(treatment_path), _locator(packet_path), _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                if source_size != total_bytes or source_size > 1024 * 1024:
                    return (_check("FAIL", "authoritative truncated briefs.py stdout size differs from total_bytes or exceeds 1 MiB",
                                   _locator(treatment_path), _locator(packet_path), _locator(expected_stdout_path),
                                   _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "total_bytes": total_bytes,
                               "source_bytes": source_size},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                retained_stdout_path = operator / "native-evidence" / "dispatch-packet-stdout.log"
                try:
                    stdout_retention = _retain_transcript(expected_stdout_path, retained_stdout_path)
                except (FileNotFoundError, TraceError) as exc:
                    return (_check("INCOMPLETE", f"cannot retain authoritative truncated briefs.py stdout: {exc}",
                                   _locator(treatment_path), _locator(packet_path), _locator(expected_stdout_path),
                                   _locator(updates_path, terminal["line"])) | {"packet_sha256": packet_sha},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                packet_evidence["script_stdout_retention"] = stdout_retention
                stdout_evidence = [_locator(expected_stdout_path), stdout_retention["retained"]]
                if stdout_retention.get("matches_source") is False:
                    return (_check("FAIL", "authoritative truncated briefs.py stdout differs from immutable retained evidence",
                                   _locator(treatment_path), _locator(packet_path), *stdout_evidence,
                                   _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha,
                               "source_sha256": stdout_retention["source_sha256"],
                               "retained_sha256": stdout_retention["retained_sha256"]},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                output_bytes = retained_stdout_path.read_bytes()
                if len(output_bytes) != total_bytes:
                    return (_check("FAIL", "retained truncated briefs.py stdout disagrees with total_bytes",
                                   _locator(treatment_path), _locator(packet_path), *stdout_evidence,
                                   _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "total_bytes": total_bytes,
                               "retained_bytes": len(output_bytes)},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                marker = b"\n\n... (output truncated) ...\n\n"
                preview_width = 10_000
                if (len(preview) != preview_width * 2 + len(marker)
                        or preview[preview_width:preview_width + len(marker)] != marker):
                    return (_check("UNKNOWN", "truncated briefs.py stdout preview does not match the observed 10,000-byte head/tail schema",
                                   _locator(treatment_path), _locator(packet_path), *stdout_evidence,
                                   _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "preview_bytes": len(preview),
                               "expected_preview_bytes": preview_width * 2 + len(marker),
                               "marker_matches": preview[preview_width:preview_width + len(marker)] == marker},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
                head_matches = output_bytes[:preview_width] == preview[:preview_width]
                tail_matches = output_bytes[-preview_width:] == preview[-preview_width:]
                if not head_matches or not tail_matches:
                    return (_check("FAIL", "retained truncated briefs.py stdout disagrees with typed head/tail preview",
                                   _locator(treatment_path), _locator(packet_path), *stdout_evidence,
                                   _locator(updates_path, terminal["line"]))
                            | {"packet_sha256": packet_sha, "total_bytes": total_bytes,
                               "retained_bytes": len(output_bytes), "head_matches": head_matches,
                               "tail_matches": tail_matches},
                            packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
        if output_bytes is None:
            return (_check("UNKNOWN", "typed briefs.py result has no complete supported stdout schema",
                           _locator(treatment_path), _locator(packet_path), _locator(updates_path, script_call["line"]),
                           _locator(updates_path, terminal["line"])) | {"packet_sha256": packet_sha},
                    packet_evidence | {"script_result": _locator(updates_path, terminal["line"])})
        packet_evidence["script_result"] = _locator(updates_path, terminal["line"])
        packet_evidence["script_stdout_sha256"] = hashlib.sha256(output_bytes).hexdigest()
        packet_evidence["script_stdout_bytes"] = len(output_bytes)
        try:
            printed_packet = json.loads(output_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append("typed briefs.py stdout is not one complete JSON packet")
        else:
            if printed_packet != packet:
                issues.append("typed briefs.py stdout differs from dispatch-packet.json")

    spawn_evidence = [_locator(updates_path, row["line"]) for row in spawn_calls]
    match_rows: list[dict[str, Any]] = []
    seen_workers: set[str] = set()
    for row in spawn_calls:
        raw = row["update"].get("rawInput")
        if not isinstance(raw, dict):
            issues.append(f"spawn call at line {row['line']} has no typed rawInput object")
            continue
        worker, bind_error, _ = _bind_spawn_to_probe(raw, assignments, starts)
        if worker is None:
            issues.append(f"spawn call at line {row['line']} cannot bind to one packet worker: {bind_error}")
            continue
        if worker in seen_workers:
            issues.append(f"multiple spawn calls bind to packet worker {worker}")
            continue
        seen_workers.add(worker)
        expected_arguments = packet_by_worker.get(worker)
        if expected_arguments is None:
            issues.append(f"spawn call at line {row['line']} has no valid packet entry for worker {worker}")
            continue
        field_matches: dict[str, bool] = {}
        for field in field_order:
            expected_value = expected_arguments[field]
            actual_value = raw.get(field)
            if field == "background":
                field_matches[field] = type(actual_value) is bool and actual_value is expected_value
            else:
                field_matches[field] = type(actual_value) is str and actual_value == expected_value
            if not field_matches[field]:
                issues.append(f"worker {worker} spawn field {field} differs from dispatch packet")
        match_rows.append({"worker_id": worker, "spawn_line": row["line"], "field_matches": field_matches})
    if seen_workers != set(expected_ids):
        issues.append("native spawn calls do not map one-to-one to packet worker IDs")
    check_metadata = {
        "packet_sha256": packet_sha,
        "script_stdout_sha256": packet_evidence.get("script_stdout_sha256"),
        "script_stdout_bytes": packet_evidence.get("script_stdout_bytes"),
        "worker_matches": match_rows,
    }
    if issues:
        status = "FAIL" if any("requires exactly one" not in item for item in issues) or len(script_calls) > 1 else "INCOMPLETE"
        return (_check(status, "; ".join(issues), _locator(treatment_path), _locator(packet_path),
                       _locator(updates_path), *stdout_evidence, *spawn_evidence,
                       *([_locator(updates_path, script_calls[0]["line"])] if len(script_calls) == 1 else []),
                       *([_locator(updates_path, script_result_row["line"])] if script_result_row else []))
                | check_metadata,
                packet_evidence | {"worker_matches": match_rows})
    return (_check("PASS", "each packet-treatment native spawn exactly matches its retained worker arguments and typed script result",
                   _locator(treatment_path), _locator(packet_path), _locator(updates_path), *stdout_evidence, *spawn_evidence,
                   *([_locator(updates_path, script_calls[0]["line"])] if script_calls else []),
                   *([_locator(updates_path, script_result_row["line"])] if script_result_row else []))
            | check_metadata,
            packet_evidence | {"worker_matches": match_rows})


def _task_rows(output: Any) -> list[dict[str, Any]]:
    if not isinstance(output, dict):
        return []
    if output.get("type") == "TaskOutput":
        multi = output.get("MultiResult")
        if isinstance(multi, dict) and isinstance(multi.get("results"), list):
            return [row for row in multi["results"] if isinstance(row, dict)]
        single = output.get("Result")
        if isinstance(single, dict):
            return [single]
    if output.get("type") == "TaskOutput.MultiResult" and isinstance(output.get("results"), list):
        return [row for row in output["results"] if isinstance(row, dict)]
    if isinstance(output.get("results"), list):
        return [row for row in output["results"] if isinstance(row, dict)]
    return []


def _completed_task_output_rows(terminal: dict[str, Any]) -> tuple[list[dict[str, Any]] | None, str | None]:
    update = terminal.get("update")
    if not isinstance(update, dict) or update.get("status") != "completed":
        return None, "collection call did not complete successfully"
    output = update.get("rawOutput")
    if not isinstance(output, dict) or output.get("type") != "TaskOutput":
        return None, "collection result is not the observed typed TaskOutput envelope"
    has_multi = "MultiResult" in output
    has_single = "Result" in output
    if has_multi == has_single:
        return None, "TaskOutput must contain exactly one MultiResult or Result payload"
    if has_multi:
        multi = output.get("MultiResult")
        if not isinstance(multi, dict) or not isinstance(multi.get("results"), list):
            return None, "TaskOutput.MultiResult.results is not a list"
        rows = multi["results"]
        if not all(isinstance(row, dict) for row in rows):
            return None, "TaskOutput.MultiResult.results contains a non-object row"
        return rows, None
    single = output.get("Result")
    if not isinstance(single, dict):
        return None, "TaskOutput.Result is not an object"
    return [single], None


def _row_id(row: dict[str, Any]) -> str | None:
    for key in ("task_id", "taskId", "subagent_id", "subagentId", "id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _probe_records(run: Path, assignments: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    starts: dict[str, dict[str, Any]] = {}
    finishes: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for task in assignments:
        worker = str(task["worker_id"])
        for phase, target in (("start", starts), ("finish", finishes)):
            path = run / "operator" / "probes" / f"worker-{worker}-{phase}.json"
            try:
                record = _read_json(path, f"worker {worker} {phase} probe")
            except FileNotFoundError:
                errors.append(f"missing {phase} probe for worker {worker}")
                continue
            except TraceError as exc:
                errors.append(str(exc))
                continue
            if record.get("worker_id") != worker or record.get("phase") != phase:
                errors.append(f"worker {worker} {phase} probe has mismatched identity")
                continue
            target[worker] = {"record": record, "path": path}
    return starts, finishes, errors


def _path_named(prompt: str, path: str) -> bool:
    path_pattern = r"(?<![A-Za-z0-9_.-])" + re.escape(path) + r"(?![A-Za-z0-9_/-]|\.[A-Za-z0-9_/-])"
    return re.search(path_pattern, prompt) is not None


def _probe_command_segment(value: str) -> str | None:
    """Return a command-shaped fixture probe segment, excluding explanatory prose."""
    line = value.strip()
    line = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", line)
    line = re.sub(r"^(?:run|execute)\s+(?=python(?:\d+(?:\.\d+)?)?\s)", "", line, flags=re.IGNORECASE)
    segments = re.split(r"\s+&&\s+", line)
    command_pattern = re.compile(
        r"^(?:python(?:\d+(?:\.\d+)?)?|(?:[^\s]*/)?(?:fixture|worker_phase)\.py)(?:\s|$)",
        re.IGNORECASE,
    )
    for segment in segments:
        candidate = re.sub(r"^(?:[A-Z_][A-Z0-9_]*=\S+\s+)+", "", segment.strip())
        if command_pattern.match(candidate):
            return candidate
    return None


def _explicit_probe_workers(prompt: str) -> tuple[dict[str, str], str | None, bool]:
    """Read worker IDs from typed start/finish probe commands in the prompt."""
    claims: dict[str, list[str]] = {"start": [], "finish": []}
    malformed = False

    def collect(command: str) -> None:
        nonlocal malformed
        command_segment = _probe_command_segment(command)
        if command_segment is None:
            return
        lowered = command_segment.lower()
        fixture_probe = re.search(r"(?:^|\s)(?:[^\s]*/)?fixture\.py\s+probe(?:\s|$)", lowered)
        worker_phase = re.search(r"(?:^|\s)(?:[^\s]*/)?worker_phase\.py(?:\s|$)", lowered)
        if fixture_probe is None and worker_phase is None:
            return
        if not re.search(r"--(?:worker|phase)(?:=|\s)", command_segment):
            malformed = True
            return
        phases = re.findall(r"(?:^|\s)--phase(?:=|\s+)(start|finish)\b", command_segment)
        workers = re.findall(r"(?:^|\s)--worker(?:=|\s+)([0-9]+)\b", command_segment)
        if len(workers) != 1 or len(phases) != 1:
            malformed = True
            return
        claims[phases[0]].append(workers[0])

    # Inline commands are separate claims even when several appear in one
    # paragraph. Remove them before scanning ordinary prompt lines to avoid
    # counting a command twice.
    spans = re.findall(r"`([^`]+)`", prompt)
    for span in spans:
        collect(span)
    plain_text = re.sub(r"`[^`]*`", " ", prompt)
    for line in plain_text.splitlines():
        collect(line)
    if malformed:
        return {}, "probe command has missing or duplicate worker/phase flags", True
    if not claims["start"] and not claims["finish"]:
        return {}, "typed prompt has no explicit start/finish probe worker IDs", False
    if not claims["start"] or not claims["finish"]:
        return {}, "typed prompt is missing an explicit start or finish probe command", False
    if len(claims["start"]) != 1 or len(claims["finish"]) != 1:
        return {}, "typed prompt has duplicate start or finish probe commands", True
    return {phase: values[0] for phase, values in claims.items()}, None, False


def _bind_spawn_to_probe(raw_input: dict[str, Any], assignments: list[dict[str, Any]],
                         starts: dict[str, dict[str, Any]]) -> tuple[str | None, str | None, bool]:
    """Bind a spawn by its cwd's unique probe root and corroborating task prompt."""
    prompt = raw_input.get("prompt")
    if not isinstance(prompt, str):
        return None, "typed spawn prompt is missing", False
    cwd = raw_input.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return None, "native spawn cwd is missing or not absolute", False
    resolved_cwd = str(Path(cwd).resolve())
    matches = []
    for worker, item in starts.items():
        root = item["record"].get("root")
        if isinstance(root, str) and Path(root).is_absolute() and str(Path(root).resolve()) == resolved_cwd:
            matches.append(worker)
    if len(matches) != 1:
        return None, f"native cwd matches {len(matches)} start probe roots; exactly one is required", False
    worker = matches[0]
    assignments_for_worker = [item for item in assignments
                              if isinstance(item, dict) and str(item.get("worker_id")) == worker]
    if len(assignments_for_worker) != 1:
        return None, f"probe root worker {worker} has no unique manifest assignment", True
    owned_path = assignments_for_worker[0].get("path")
    if not isinstance(owned_path, str) or not _path_named(prompt, owned_path):
        return None, f"typed prompt does not name the owned path for probe worker {worker}", True
    probe_workers, error, conflict = _explicit_probe_workers(prompt)
    if error:
        return None, error, conflict
    if any(value != worker for value in probe_workers.values()):
        return None, f"explicit probe worker IDs disagree with native cwd's probe worker {worker}", True
    return worker, None, False


def _check_source_work(run: Path, manifest: dict[str, Any], assignments: list[dict[str, Any]],
                       starts: dict[str, dict[str, Any]], finishes: dict[str, dict[str, Any]],
                       bindings: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    issues: list[str] = []
    by_worker = {item["worker_id"]: item for item in assignments}
    by_cwd = {item.get("cwd"): item for item in bindings if item.get("cwd")}
    initial_files = manifest.get("caller_snapshot", {}).get("working_tree", {}).get("files", {})
    for worker, task in by_worker.items():
        worker = str(worker)
        start = starts.get(worker)
        finish = finishes.get(worker)
        row: dict[str, Any] = {"worker_id": worker, "status": "INCOMPLETE"}
        if start is None or finish is None:
            row["detail"] = "start and finish probes are both required"
            results.append(row)
            issues.append(row["detail"])
            continue
        a, b = start["record"], finish["record"]
        root = a.get("root")
        if root != b.get("root") or not isinstance(root, str):
            row.update(status="FAIL", detail="probe root changed or is absent")
            results.append(row)
            issues.append(row["detail"])
            continue
        if b.get("run_id") != manifest.get("run_id") or a.get("run_id") != manifest.get("run_id"):
            row.update(status="FAIL", detail="probe run id does not match manifest")
            results.append(row)
            issues.append(row["detail"])
            continue
        binding = by_cwd.get(str(Path(root).resolve()))
        if binding is None or binding.get("worker_id") != worker:
            row.update(status="UNKNOWN", detail="no exact native cwd binding for this probe root and worker")
            results.append(row)
            issues.append(row["detail"])
            continue
        owned = task.get("path")
        start_files = a.get("working_tree", {}).get("files", {})
        finish_files = b.get("working_tree", {}).get("files", {})
        if not isinstance(owned, str) or not isinstance(start_files, dict) or not isinstance(finish_files, dict):
            row.update(status="UNKNOWN", detail="probe source snapshots are missing")
            results.append(row)
            issues.append(row["detail"])
            continue
        baseline = initial_files.get(owned) if isinstance(initial_files, dict) else None
        before, after = start_files.get(owned), finish_files.get(owned)
        changed = sorted(path for path in set(start_files) | set(finish_files)
                         if start_files.get(path) != finish_files.get(path))
        checks = b.get("checks")
        start_checks = a.get("checks")
        checks_ok = (isinstance(checks, dict) and all(value is True for value in checks.values())
                     and isinstance(start_checks, dict) and all(value is True for value in start_checks.values()))
        if (before != baseline or after == before or changed != [owned] or not checks_ok
                or a.get("errors") or b.get("errors")):
            row.update(status="FAIL", detail="child source change is not an isolated owned-file change from fixture baseline",
                       before_hash=before, baseline_hash=baseline, after_hash=after, changed_paths=changed)
        else:
            row.update(status="PASS", detail="bound child changed exactly its owned source from the fixture baseline",
                       before_hash=before, after_hash=after, changed_paths=changed)
        row["evidence"] = [_locator(start["path"]), _locator(finish["path"])]
        results.append(row)
        if row["status"] != "PASS":
            issues.append(row["detail"])
    if not assignments or len(results) != len(assignments):
        return _check("UNKNOWN", "worker source evidence could not be enumerated"), results
    states = {row["status"] for row in results}
    status = "FAIL" if "FAIL" in states else "INCOMPLETE" if "INCOMPLETE" in states else "UNKNOWN" if "UNKNOWN" in states else "PASS"
    detail = "all child changes are bound to their distinct native roots and fixture-owned files" if status == "PASS" else "; ".join(issues)
    return _check(status, detail), results


def _probe_overlap(starts: dict[str, dict[str, Any]], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    intervals: list[tuple[str, float, float, str]] = []
    for worker, item in starts.items():
        record = item["record"]
        begin = record.get("hold_started_at_utc")
        end = record.get("hold_finished_at_utc")
        binding = next((entry for entry in bindings if entry.get("worker_id") == worker), None)
        if not isinstance(begin, str) or not isinstance(end, str) or binding is None:
            continue
        try:
            lo = datetime.fromisoformat(begin.replace("Z", "+00:00")).timestamp()
            hi = datetime.fromisoformat(end.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if hi > lo:
            intervals.append((worker, lo, hi, str(binding.get("child_session_id"))))
    overlaps: list[dict[str, Any]] = []
    for i, first in enumerate(intervals):
        for second in intervals[i + 1:]:
            begin, end = max(first[1], second[1]), min(first[2], second[2])
            if end > begin:
                overlaps.append({"workers": [first[0], second[0]], "child_session_ids": [first[3], second[3]],
                                 "start_epoch": begin, "end_epoch": end, "overlap_seconds": end - begin})
    if not intervals:
        return {"status": "UNKNOWN", "detail": "no identity-bound child probe intervals", "overlaps": []}
    return {"status": "OBSERVED" if overlaps else "NOT_OBSERVED",
            "detail": "probe intervals establish task overlap only; they do not establish CPU concurrency",
            "overlaps": overlaps}


def _probe_work_overlap(starts: dict[str, dict[str, Any]], finishes: dict[str, dict[str, Any]],
                        bindings: list[dict[str, Any]], run_id: Any) -> dict[str, Any]:
    """Compare child start-to-finish probe timestamps, distinct from hold overlap."""
    intervals: list[dict[str, Any]] = []
    missing: list[str] = []
    for binding in bindings:
        worker = binding.get("worker_id")
        child = binding.get("child_session_id")
        start, finish = starts.get(str(worker)), finishes.get(str(worker))
        if not isinstance(worker, str) or start is None or finish is None:
            missing.append(str(worker or "?"))
            continue
        a, b = start["record"], finish["record"]
        root = a.get("root")
        if (a.get("phase") != "start" or b.get("phase") != "finish"
                or a.get("worker_id") != worker or b.get("worker_id") != worker
                or a.get("run_id") != run_id or b.get("run_id") != run_id
                or not isinstance(root, str) or root != b.get("root")
                or str(Path(root).resolve()) != binding.get("cwd")):
            missing.append(worker)
            continue
        try:
            begin = datetime.fromisoformat(str(a.get("recorded_at_utc", "")).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(b.get("recorded_at_utc", "")).replace("Z", "+00:00"))
            if begin.tzinfo is None or end.tzinfo is None or end <= begin:
                raise ValueError("probe interval must be positive and timezone-aware")
        except ValueError:
            missing.append(worker)
            continue
        intervals.append({"worker_id": worker, "child_session_id": child,
                          "start_epoch": begin.timestamp(), "end_epoch": end.timestamp(),
                          "start_evidence": _locator(start["path"]),
                          "finish_evidence": _locator(finish["path"])})
    overlaps: list[dict[str, Any]] = []
    for index, first in enumerate(intervals):
        for second in intervals[index + 1:]:
            begin = max(first["start_epoch"], second["start_epoch"])
            end = min(first["end_epoch"], second["end_epoch"])
            if end > begin:
                overlaps.append({"workers": [first["worker_id"], second["worker_id"]],
                                 "child_session_ids": [first["child_session_id"], second["child_session_id"]],
                                 "start_epoch": begin, "end_epoch": end,
                                 "overlap_seconds": end - begin})
    status = "UNKNOWN" if missing else "OBSERVED" if overlaps else "NOT_OBSERVED"
    detail = "recorded start-to-finish child task intervals; this is not CPU concurrency"
    if missing:
        detail += "; incomplete identity-bound probe intervals for workers: " + ", ".join(sorted(set(missing)))
    return {"status": status, "detail": detail, "intervals": intervals, "overlaps": overlaps}


def _compact_cli_calls(root_updates: list[dict[str, Any]], script: Path, run: Path,
                       action: str) -> list[dict[str, Any]]:
    calls = []
    for row in root_updates:
        update = row["update"]
        if update.get("sessionUpdate") != "tool_call" or update.get("title") != "run_terminal_command":
            continue
        raw = update.get("rawInput")
        command = raw.get("command") if isinstance(raw, dict) else None
        if not isinstance(command, str):
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        positions = [index for index, token in enumerate(tokens)
                     if Path(token).is_absolute() and Path(token).resolve() == script.resolve()]
        if len(positions) != 1:
            continue
        args = tokens[positions[0] + 1:]
        if action not in args:
            continue
        run_values = [args[index + 1] for index, value in enumerate(args[:-1]) if value == "--run"]
        if len(run_values) == 1 and Path(run_values[0]).expanduser().resolve() == run.resolve():
            calls.append({"row": row, "tokens": tokens, "args": args})
    return calls


def _compact_cli_result(call: dict[str, Any], root_updates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, int | None, str | None]:
    call_id = call["row"]["update"].get("toolCallId")
    if not isinstance(call_id, str):
        return None, None, "command has no typed tool-call ID"
    terminals = [row for row in root_updates
                 if row["update"].get("sessionUpdate") == "tool_call_update"
                 and row["update"].get("toolCallId") == call_id
                 and str(row["update"].get("status", "")).lower() not in NONTERMINAL]
    if len(terminals) != 1:
        line = terminals[-1]["line"] if terminals else None
        return None, line, f"command has {len(terminals)} terminal native results"
    terminal = terminals[0]
    call_line = call["row"].get("line") if isinstance(call.get("row"), dict) else None
    if type(call_line) is not int or type(terminal.get("line")) is not int:
        return None, terminal.get("line"), "command invocation or terminal result has no retained line reference"
    if terminal["line"] <= call_line:
        return None, terminal["line"], "terminal result does not follow its native command invocation"
    if terminal["update"].get("status") != "completed":
        return None, terminal["line"], "command did not complete successfully"
    output = terminal["update"].get("rawOutput")
    if not isinstance(output, dict) or output.get("type") != "Bash":
        return None, terminal["line"], "command result has no typed Bash output"
    if type(output.get("exit_code")) is not int or output.get("exit_code") != 0:
        return None, terminal["line"], "command exited nonzero or has an untyped exit code"
    if output.get("truncated") is not False:
        return None, terminal["line"], "command output is not explicitly marked complete and untruncated"
    raw = output.get("output")
    if isinstance(raw, str):
        payload = raw.encode("utf-8")
    elif isinstance(raw, list) and all(type(value) is int and 0 <= value <= 255 for value in raw):
        payload = bytes(raw)
    else:
        return None, terminal["line"], "command stdout is not a complete supported byte/string value"
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None, terminal["line"], "command stdout is not complete UTF-8 JSON"
    if not isinstance(value, dict):
        return None, terminal["line"], "command stdout JSON is not an object"
    return value, terminal["line"], None


def _fixture_verification_output_mode(treatment: dict[str, Any]) -> tuple[str, str]:
    """Classify the fixture verifier output contract declared by one treatment."""
    name = treatment.get("treatment")
    version = treatment.get("version")
    output = treatment.get("verification_output")
    if output == "summary-v1":
        declared = ((name == "compact" and type(version) is int and version in {2, 3})
                    or (name in {"baseline", "batched"} and type(version) is int and version == 5))
        if declared:
            return "summary-v1", "treatment requires complete fixture verification summary output"
        return "invalid", f"summary-v1 is not declared for treatment {name!r} v{version!r}"
    if output not in (None, "legacy"):
        return "invalid", f"unknown verification_output value: {output!r}"
    if name == "compact" and type(version) is int and version == 1:
        return "legacy", "legacy compact v1: parent complete-output proof NOT_MEASURED"
    if name in {"baseline", "batched"} and type(version) is int and version == 4:
        return "legacy", f"legacy {name} v4: parent complete-output proof NOT_MEASURED"
    legacy_packet_version = version is None or (type(version) is int and version == 4)
    if name in {"packet", "scripted"} and output in (None, "legacy") and legacy_packet_version:
        return "legacy", f"legacy {name} treatment: parent complete-output proof NOT_MEASURED"
    if name == "compact" and type(version) is int and version == 2:
        return "invalid", "compact v2 is missing verification_output: summary-v1"
    if name in {"baseline", "batched"} and type(version) is int and version == 5:
        return "invalid", f"{name} v5 is missing verification_output: summary-v1"
    if output == "legacy":
        return "invalid", "legacy verification output is not allowed for this treatment version"
    return "invalid", f"unsupported treatment verification contract: {name!r} v{version!r}"


def _compact_delivery_mode(manifest: dict[str, Any], treatment: dict[str, Any]
                           ) -> tuple[str | None, dict[str, Any]]:
    """Validate the compact delivery contract without inferring a new mode."""
    version = treatment.get("version")
    manifest_mode = manifest.get("delivery_mode")
    treatment_mode = treatment.get("delivery_mode")
    if type(version) is not int:
        return None, _check("FAIL", "compact treatment version must be an integer")
    if version == 1:
        if manifest_mode not in (None, "patch") or treatment_mode not in (None, "legacy", "patch"):
            return None, _check("FAIL", "legacy compact v1 cannot declare a non-patch delivery mode")
        return "patch-legacy", _check(
            "LEGACY", "compact v1 retains the legacy patch delivery gate; new delivery-mode proof NOT_MEASURED"
        )
    if version == 2:
        if treatment_mode != "patch" or manifest_mode not in (None, "patch"):
            return None, _check("FAIL", "compact v2 requires treatment delivery_mode=patch and a matching patch manifest mode")
        return "patch", _check("PASS", "compact v2 binds patch delivery in treatment and manifest")
    if version == 3:
        if (manifest_mode not in {"commits", "ephemeral"}
                or treatment_mode not in {"commits", "ephemeral"}
                or manifest_mode != treatment_mode):
            return None, _check(
                "FAIL", "compact v3 requires matching explicit commits or ephemeral delivery_mode in manifest and treatment"
            )
        return treatment_mode, _check("PASS", f"compact v3 binds {treatment_mode} delivery in manifest and treatment")
    return None, _check("FAIL", f"unsupported compact treatment version: {version!r}")


def _fixture_verify_invocations(root_updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find parent fixture verify commands using the same token model as compact CLI checks."""
    invocations: list[dict[str, Any]] = []
    for row in root_updates:
        update = row["update"]
        if update.get("sessionUpdate") != "tool_call" or update.get("title") != "run_terminal_command":
            continue
        raw = update.get("rawInput")
        command = raw.get("command") if isinstance(raw, dict) else None
        if not isinstance(command, str):
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        script_positions = [index for index, token in enumerate(tokens)
                            if Path(token).name in {"fixture.py", "probe-fixture.py"}]
        if any("verify" in tokens[index + 1:] for index in script_positions):
            invocations.append({"row": row, "tokens": tokens, "script_positions": script_positions})
    return invocations


def _fixture_verification_summary_check(run: Path, manifest: dict[str, Any], launch: dict[str, Any],
                                        treatment: dict[str, Any], root_updates: list[dict[str, Any]],
                                        updates_path: Path) -> dict[str, Any]:
    mode, mode_detail = _fixture_verification_output_mode(treatment)
    treatment_path = run / "operator" / "treatment.json"
    script = run / "operator" / "fixture.py"
    logical_report = run / "operator" / "verification.json"
    post_exit_paths = [run / "operator" / name for name in (
        "integrity-result.json", "post-exit-verification.json", "post-exit-result.json", "post-exit-verify.log",
    )]
    saved_report = run / "operator" / "parent-verification.json"
    has_post_exit_evidence = any(path.exists() for path in post_exit_paths)

    invocation_records = _fixture_verify_invocations(root_updates)
    evidence = [_locator(treatment_path), _locator(updates_path)]
    evidence.extend(_locator(path) for path in post_exit_paths if path.exists())
    evidence.extend(_locator(path) for path in (script, logical_report, saved_report) if path.exists())
    invocation_lines: list[dict[str, Any]] = []

    def result_line(call_row: dict[str, Any]) -> int | None:
        call_id = call_row["update"].get("toolCallId")
        if not isinstance(call_id, str):
            return None
        terminal = _terminal_update(call_id, root_updates)
        return terminal["line"] if terminal is not None else None

    for invocation in invocation_records:
        row = invocation["row"]
        invocation_lines.append({"call_line": row["line"], "result_line": result_line(row)})
        evidence.append(_locator(updates_path, row["line"]))
        if invocation_lines[-1]["result_line"] is not None:
            evidence.append(_locator(updates_path, invocation_lines[-1]["result_line"]))

    if mode == "legacy":
        return _check("LEGACY", mode_detail, *evidence) | {
            "verification_output": "legacy",
            "complete_output_proof": "NOT_MEASURED",
            "invocations": invocation_lines,
        }
    if mode == "invalid":
        return _check("FAIL", mode_detail, *evidence) | {
            "verification_output": treatment.get("verification_output"),
            "complete_output_proof": "NOT_ESTABLISHED",
            "invocations": invocation_lines,
        }

    def checked(status: str, detail: str, **fields: Any) -> dict[str, Any]:
        return _check(status, detail, *evidence) | {
            "verification_output": "summary-v1",
            "complete_output_proof": "ESTABLISHED" if status == "PASS" else "NOT_ESTABLISHED",
            "invocations": invocation_lines,
            **fields,
        }

    if not script.is_file() or script.is_symlink():
        return checked("INCOMPLETE", "frozen operator fixture.py is unavailable as a regular file")
    expected_script_hash = launch.get("apparatus_sha256", {}).get("fixture.py") \
        if isinstance(launch.get("apparatus_sha256"), dict) else None
    actual_script_hash = hashlib.sha256(script.read_bytes()).hexdigest()
    if not isinstance(expected_script_hash, str):
        return checked("INCOMPLETE", "launch record has no frozen fixture.py hash",
                       frozen_script_sha256=expected_script_hash,
                       actual_script_sha256=actual_script_hash)
    if expected_script_hash != actual_script_hash:
        return checked("FAIL", "fixture.py differs from the frozen launch apparatus",
                       frozen_script_sha256=expected_script_hash,
                       actual_script_sha256=actual_script_hash)

    if not invocation_records:
        return checked("INCOMPLETE", "no parent fixture.py verify invocation was retained",
                       invocation_count=0)
    if len(invocation_records) != 1:
        return checked("FAIL", f"expected exactly one parent fixture verify invocation; found {len(invocation_records)}",
                       invocation_count=len(invocation_records))

    invocation = invocation_records[0]
    positions = invocation["script_positions"]
    tokens = invocation["tokens"]
    if len(positions) != 1:
        return checked("FAIL", "fixture verify command contains zero or multiple fixture script paths",
                       invocation_count=1)
    script_index = positions[0]
    if tokens[:script_index] not in (["python3"], ["python3", "-B"]):
        return checked("FAIL", "fixture verify command is not a standalone python3 invocation",
                       invocation_count=1, command=shlex.join(tokens))
    command_script = Path(tokens[script_index]).expanduser()
    args = tokens[script_index + 1:]
    run_values = [args[index + 1] for index, value in enumerate(args[:-1]) if value == "--run"]
    exact_args = (args.count("verify") == 1 and args.count("--run") == 1
                  and args.count("--summary") == 1 and len(run_values) == 1)
    if exact_args:
        run_value = run_values[0]
        if run_value.startswith("-"):
            exact_args = False
        else:
            remaining = list(args)
            remaining.remove("verify")
            remaining.remove("--summary")
            remaining.remove("--run")
            remaining.remove(run_value)
            try:
                run_matches = Path(run_value).expanduser().resolve() == run.resolve()
            except (OSError, RuntimeError, ValueError):
                run_matches = False
            exact_args = not remaining and run_matches
    try:
        script_matches = command_script.resolve() == script.resolve()
    except (OSError, RuntimeError, ValueError):
        script_matches = False
    if not script_matches or not exact_args:
        return checked("FAIL", "parent fixture verify invocation is not bound to frozen fixture.py, this run, and --summary",
                       invocation_count=1, command=shlex.join(tokens))
    calls = _compact_cli_calls(root_updates, script, run, "verify")
    if len(calls) != 1 or calls[0]["row"]["line"] != invocation["row"]["line"]:
        return checked("FAIL", "fixture verify invocation did not resolve to one frozen-script CLI call",
                       invocation_count=1, bound_cli_call_count=len(calls))
    call_id = calls[0]["row"]["update"].get("toolCallId")
    terminal_results = [row for row in root_updates
                        if row["update"].get("sessionUpdate") == "tool_call_update"
                        and row["update"].get("toolCallId") == call_id
                        and str(row["update"].get("status", "")).lower() not in NONTERMINAL]
    if len(terminal_results) > 1:
        return checked("FAIL", "fixture verify invocation has duplicate terminal native results",
                       invocation_count=1,
                       result_lines=[row["line"] for row in terminal_results])
    if terminal_results:
        raw_output = terminal_results[0]["update"].get("rawOutput")
        if not isinstance(raw_output, dict) or raw_output.get("truncated") is not False:
            return checked("INCOMPLETE", "fixture verify result lacks an explicit untruncated output marker",
                           invocation_count=1, result_line=terminal_results[0]["line"])

    summary, terminal_line, error = _compact_cli_result(calls[0], root_updates)
    if error:
        return checked("INCOMPLETE", f"fixture verify summary result is incomplete: {error}",
                       invocation_count=1, result_line=terminal_line)
    if not isinstance(summary, dict):
        return checked("INCOMPLETE", "fixture verify summary stdout is not a typed JSON object",
                       invocation_count=1, result_line=terminal_line)

    if has_post_exit_evidence:
        if not saved_report.is_file() or saved_report.is_symlink():
            return checked("INCOMPLETE", "post-exit evidence exists but the original parent-verification.json is unavailable",
                           invocation_count=1, result_line=terminal_line,
                           saved_report_path=str(saved_report.resolve()))
    else:
        saved_report = logical_report
    if not saved_report.is_file() or saved_report.is_symlink():
        return checked("INCOMPLETE", "saved full fixture verification report is unavailable",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()))

    try:
        report_bytes = saved_report.read_bytes()
        report = json.loads(report_bytes.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return checked("FAIL", f"saved full fixture verification report is malformed: {type(exc).__name__}: {exc}",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()))
    if not isinstance(report, dict):
        return checked("FAIL", "saved full fixture verification report is not a JSON object",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()))

    manifest_run_id = manifest.get("run_id")
    expected_report_path = manifest.get("paths", {}).get("verification") \
        if isinstance(manifest.get("paths"), dict) else None
    if (logical_report.is_symlink() or not isinstance(expected_report_path, str)
            or not Path(expected_report_path).expanduser().is_absolute()
            or Path(expected_report_path).expanduser().resolve() != logical_report.resolve()):
        return checked("FAIL", "manifest verification path does not identify operator/verification.json",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()))
    if (not isinstance(manifest_run_id, str) or report.get("run_id") != manifest_run_id
            or report.get("run_path") != str(run.resolve())):
        return checked("FAIL", "saved verification report run identity differs from the frozen manifest",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()),
                       report_run_id=report.get("run_id"), report_run_path=report.get("run_path"))
    checks = report.get("checks")
    errors = report.get("errors")
    if (not isinstance(checks, dict) or not checks or any(not isinstance(name, str) for name in checks)
            or not isinstance(errors, list) or any(not isinstance(item, str) for item in errors)):
        return checked("FAIL", "saved verification report has malformed checks or errors fields",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()))
    failed_checks = sorted(name for name, value in checks.items() if value is not True)
    derived_passed = not errors and not failed_checks
    report_passed = report.get("passed")
    if type(report_passed) is not bool or report_passed is not derived_passed:
        return checked("FAIL", "saved verification report passed field contradicts its checks or errors",
                       invocation_count=1, result_line=terminal_line,
                       saved_report_path=str(saved_report.resolve()), failed_checks=failed_checks,
                       report_errors=errors)

    expected_summary = {
        "schema": "ask-agent-fixture-verification-summary/v1",
        "run_id": manifest_run_id,
        "passed": derived_passed,
        "errors": errors,
        "check_count": len(checks),
        "failed_checks": failed_checks,
        "report_path": str(logical_report.resolve()),
        "report_bytes": len(report_bytes),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
    }
    if set(summary) != set(expected_summary):
        return checked("FAIL", "native fixture summary has extra or missing fields",
                       invocation_count=1, result_line=terminal_line,
                       summary_fields=sorted(summary), saved_report_path=str(saved_report.resolve()))
    if summary != expected_summary:
        return checked("FAIL", "native fixture summary differs from the independently audited saved report",
                       invocation_count=1, result_line=terminal_line,
                       summary=summary, expected_summary=expected_summary,
                       saved_report_path=str(saved_report.resolve()))
    if (type(summary.get("check_count")) is not int or summary["check_count"] <= 0
            or any(value is not True for value in checks.values())
            or summary.get("passed") is not True or summary.get("errors") != []
            or summary.get("failed_checks") != []):
        return checked("FAIL", "fixture verification report does not pass every required check",
                       invocation_count=1, result_line=terminal_line,
                       failed_checks=failed_checks, report_errors=errors,
                       saved_report_path=str(saved_report.resolve()))
    return checked("PASS", "one complete native summary matches the immutable full report and every saved check passes",
                   invocation_count=1, result_line=terminal_line,
                   summary=summary, saved_report_path=str(saved_report.resolve()),
                   report_sha256=expected_summary["report_sha256"],
                   report_bytes=expected_summary["report_bytes"])


def _compact_dispatch_check(run: Path, assignments: list[dict[str, Any]],
                            spawn_calls: list[dict[str, Any]], starts: dict[str, dict[str, Any]],
                            root_updates: list[dict[str, Any]], updates_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    treatment_path = run / "operator" / "treatment.json"
    index_path = run / "operator" / "compact-dispatch" / "index.json"
    setup_path = run / "operator" / "setup-result.json"
    briefs_script = run / "operator" / "briefs.py"
    operations_script = run / "operator" / "operations.py"
    evidence_paths = [treatment_path, setup_path, index_path, updates_path]
    errors: list[str] = []
    missing: list[str] = []
    try:
        treatment = _read_json(treatment_path, "compact treatment")
        setup = _read_json(setup_path, "compact setup")
        index = _read_json(index_path, "compact dispatch index")
        manifest = _read_json(run / "manifest.json", "manifest")
    except (OSError, TraceError) as exc:
        return _check("INCOMPLETE", f"compact dispatch records are unavailable: {exc}",
                      *[_locator(path) for path in evidence_paths]), {"errors": [str(exc)]}
    expected_ids = [str(item.get("worker_id")) for item in assignments if isinstance(item, dict)]
    if treatment.get("treatment") != "compact" or setup.get("treatment") != "compact":
        errors.append("treatment and setup records must both identify compact mode")
    if index.get("schema") != "ask-agent.compact-dispatch/v1" or index.get("run_id") != manifest.get("run_id"):
        errors.append("compact dispatch index schema or run id does not bind to this manifest")
    rows = index.get("assignments")
    if not isinstance(rows, list) or [row.get("worker_id") for row in rows if isinstance(row, dict)] != expected_ids:
        errors.append("compact assignment index IDs or order differ from the manifest")
        rows = rows if isinstance(rows, list) else []
    setup_workers = {item.get("worker_id"): item for item in setup.get("workers", []) if isinstance(item, dict)}
    assignments_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("compact index contains a non-object assignment")
            continue
        worker = row.get("worker_id")
        if not isinstance(worker, str) or worker in assignments_by_id:
            errors.append("compact index contains a missing or duplicate worker ID")
            continue
        path = Path(str(row.get("path", "")))
        expected_path = run / "operator" / "compact-dispatch" / f"worker-{worker}.json"
        try:
            payload = path.read_bytes()
            entry = json.loads(payload.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"worker {worker} assignment cannot be read: {type(exc).__name__}: {exc}")
            continue
        if path.is_symlink() or path.resolve() != expected_path.resolve() or hashlib.sha256(payload).hexdigest() != row.get("sha256"):
            errors.append(f"worker {worker} assignment path or SHA-256 does not match the index")
        args = entry.get("native_arguments") if isinstance(entry, dict) else None
        worker_setup = setup_workers.get(worker)
        if (not isinstance(args, dict) or set(args) != {"description", "prompt", "cwd", "background"}
                or type(args.get("description")) is not str or type(args.get("prompt")) is not str
                or type(args.get("cwd")) is not str or args.get("background") is not True
                or entry.get("worker_id") != worker or args.get("cwd") != (worker_setup or {}).get("worktree")
                or entry.get("binding_sha256") != row.get("binding_sha256")
                or row.get("binding_sha256") != (worker_setup or {}).get("compact_binding_sha256")):
            errors.append(f"worker {worker} assignment content does not bind its setup worker and compact binding")
        if isinstance(args, dict):
            assignments_by_id[worker] = args

    retained_entries = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("worker_id"), str):
            continue
        try:
            retained_entries[row["worker_id"]] = json.loads(Path(row["path"]).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
            continue

    compact_builds = [call for call in _compact_cli_calls(root_updates, briefs_script, run, "--compact")
                      if "--emit-worker" not in call["args"]]
    if len(compact_builds) != 1:
        missing.append(f"one briefs.py --compact call (found {len(compact_builds)})")
    else:
        value, _, error = _compact_cli_result(compact_builds[0], root_updates)
        if error:
            missing.append(f"compact assignment builder result: {error}")
        elif (value.get("status") != "PREPARED" or value.get("worker_ids") != expected_ids
              or Path(str(value.get("index_path", ""))).resolve() != index_path.resolve()):
            errors.append("typed compact assignment builder result differs from the retained index")
    preparation_calls = [call for call in _compact_cli_calls(root_updates, operations_script, run, "prepare-batch")
                         if "--compact" in call["args"]]
    if len(preparation_calls) != 1:
        missing.append(f"one operations.py prepare-batch --compact call (found {len(preparation_calls)})")
    else:
        value, _, error = _compact_cli_result(preparation_calls[0], root_updates)
        if error:
            missing.append(f"compact setup command result: {error}")
        elif value.get("status") != "PREPARED" or value.get("treatment") != "compact":
            errors.append("typed compact setup command result does not report prepared compact setup")

    emitted: dict[str, dict[str, Any]] = {}
    for worker in expected_ids:
        calls = [call for call in _compact_cli_calls(root_updates, briefs_script, run, "--emit-worker")
                 if call["args"].count("--emit-worker") == 1
                 and call["args"][call["args"].index("--emit-worker") + 1:][:1] == [worker]]
        if len(calls) != 1:
            missing.append(f"one briefs.py --emit-worker {worker} call (found {len(calls)})")
            continue
        value, _, error = _compact_cli_result(calls[0], root_updates)
        if error:
            missing.append(f"worker {worker} assignment output: {error}")
        elif value != retained_entries.get(worker):
            errors.append(f"worker {worker} emitted JSON differs from its retained assignment file")
        else:
            emitted[worker] = value

    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in spawn_calls:
        raw = row["update"].get("rawInput")
        worker, issue, conflict = _bind_spawn_to_probe(raw, assignments, starts) if isinstance(raw, dict) else (None, "spawn has no typed arguments", False)
        if issue:
            (errors if conflict else missing).append(f"spawn at line {row['line']}: {issue}")
            continue
        if worker in seen:
            errors.append(f"worker {worker} has duplicate compact spawn arguments")
            continue
        seen.add(worker)
        expected = assignments_by_id.get(worker)
        actual = raw if isinstance(raw, dict) else {}
        fields = {name: actual.get(name) == expected.get(name)
                  for name in ("description", "prompt", "cwd", "background")} if expected else {}
        if not expected or not all(fields.values()):
            errors.append(f"native spawn arguments for worker {worker} differ from its emitted compact assignment")
        matches.append({"worker_id": worker, "spawn_line": row["line"], "field_matches": fields})
    if seen != set(expected_ids):
        missing.append("native compact spawn arguments do not cover every worker exactly once")
    evidence = [_locator(path) for path in evidence_paths]
    evidence.extend(_locator(row["path"]) for row in starts.values() if row.get("path"))
    status = "FAIL" if errors else "INCOMPLETE" if missing else "PASS"
    detail = "; ".join(errors or missing) if errors or missing else "each compact CLI output and native spawn matches the retained per-worker assignment and binding"
    return (_check(status, detail, *evidence, _locator(updates_path))
            | {"worker_matches": matches, "errors": errors, "missing": missing}), {
                "index": _locator(index_path), "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest()
                if index_path.is_file() else None,
                "emitted_worker_ids": sorted(emitted), "worker_matches": matches,
            }


_COMPACT_FIXTURE_TEST_OUTPUT = re.compile(
    r"runTest \(__main__\.FormulaCheck\.runTest\) \.\.\. ok\n\n"
    r"-{70}\nRan 1 test in \d+\.\d{3}s\n\nOK\n"
)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _compact_child_invocation(command: str, run: Path, worker: str, phase: str,
                              cwd: str, binding_path: str, *,
                              launch_cwd_verified: bool = False) -> dict[str, bool] | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if tokens[:3] == ["cd", cwd, "&&"]:
        body = tokens[3:]
    else:
        if not launch_cwd_verified:
            return None
        body = tokens

    commands: list[list[str]] = []
    current: list[str] = []
    for token in body:
        if token == "&&":
            if not current:
                return None
            commands.append(current)
            current = []
        elif token in {";", "||", "|", "&", ">", ">>", "<", "<<", "2>", "2>>"}:
            return None
        else:
            current.append(token)
    if not current:
        return None
    commands.append(current)
    fixture_test = False
    if len(commands) == 2 and phase == "finish" and commands[0] == [
        "PYTHONDONTWRITEBYTECODE=1", "python3", "-B", "checks.py", "--worker", worker,
    ]:
        fixture_test = True
        command_tokens = commands[1]
    elif len(commands) == 1:
        command_tokens = commands[0]
    else:
        return None
    if (len(command_tokens) != 12
            or command_tokens[:3] != ["PYTHONDONTWRITEBYTECODE=1", "python3", "-B"]):
        return None
    script_positions = [index for index, token in enumerate(command_tokens)
                        if Path(token).name == "worker_phase.py"]
    if len(script_positions) != 1:
        return None
    script_index = script_positions[0]
    if script_index != 3:
        return None
    script_path = Path(command_tokens[script_index])
    if not script_path.is_absolute():
        script_path = Path(cwd) / script_path
    if script_path.resolve() != (run / "operator" / "worker_phase.py").resolve():
        return None
    argv = command_tokens[script_index + 1:]
    if (len(argv) != 8 or argv[0] != "--run" or argv[2] != "--worker"
            or argv[3] != worker or argv[4] != "--phase" or argv[5] != phase
            or argv[6] != "--compact-binding"):
        return None
    run_value = Path(argv[1]).expanduser()
    if not run_value.is_absolute():
        run_value = Path(cwd) / run_value
    binding_value = Path(argv[7]).expanduser()
    if not binding_value.is_absolute():
        binding_value = Path(cwd) / binding_value
    if (run_value.resolve() != run.resolve()
            or binding_value.resolve() != Path(binding_path).resolve()):
        return None
    return {"fixture_test": fixture_test}


def _compact_wrapper_result(output: Any, *, fixture_test: bool) -> dict[str, Any] | None:
    if fixture_test:
        if not isinstance(output, list) or not all(type(value) is int and 0 <= value <= 255 for value in output):
            return None
        try:
            text = bytes(output).decode("utf-8")
        except UnicodeDecodeError:
            return None
        prefix = _COMPACT_FIXTURE_TEST_OUTPUT.match(text)
        if prefix is None:
            return None
        payload = text[prefix.end():]
        if not payload.startswith("{") or not payload.endswith("}\n"):
            return None
        payload = payload[:-1]
    elif isinstance(output, str):
        payload = output
    elif isinstance(output, list) and all(type(value) is int and 0 <= value <= 255 for value in output):
        try:
            payload = bytes(output).decode("utf-8")
        except UnicodeDecodeError:
            return None
    else:
        return None
    try:
        result = json.loads(payload, object_pairs_hook=_unique_json_object)
    except (json.JSONDecodeError, ValueError):
        return None
    return result if isinstance(result, dict) else None


def _native_git_action_calls(child_calls: list[dict[str, Any]], action: str) -> list[dict[str, Any]]:
    """Locate typed child terminal commands that attempt one git action."""
    matches: list[dict[str, Any]] = []
    for item in child_calls:
        command = item.get("command")
        if not isinstance(command, str):
            continue
        try:
            tokens = shlex.split(command)
        except ValueError:
            if re.search(rf"(?:^|\s)git\b.*(?:^|\s){re.escape(action)}(?:\s|$)", command):
                matches.append(item | {"tokens": None, "parse_error": True})
            continue
        git_positions = [index for index, token in enumerate(tokens) if token == "git"]
        if not git_positions:
            continue
        action_positions = [index for index, token in enumerate(tokens) if token == action]
        if any(any(position < action_index for position in git_positions) for action_index in action_positions):
            matches.append(item | {"tokens": tokens, "parse_error": False})
    return matches


def _native_terminal_output(call: dict[str, Any], child_updates: list[dict[str, Any]]) -> tuple[str | None, int | None, str | None]:
    call_id = call.get("tool_call_id")
    if not isinstance(call_id, str):
        return None, None, "native command has no typed tool-call ID"
    terminals = [row for row in child_updates
                 if row["update"].get("sessionUpdate") == "tool_call_update"
                 and row["update"].get("toolCallId") == call_id
                 and str(row["update"].get("status", "")).lower() not in NONTERMINAL]
    if len(terminals) != 1:
        return None, terminals[-1]["line"] if terminals else None, f"native command has {len(terminals)} terminal results"
    terminal = terminals[0]
    update = terminal["update"]
    output = update.get("rawOutput")
    if (update.get("status") != "completed" or not isinstance(output, dict)
            or output.get("type") != "Bash" or type(output.get("exit_code")) is not int
            or output.get("exit_code") != 0 or output.get("truncated") is not False):
        return None, terminal["line"], "native command did not complete with typed, untruncated exit code zero"
    raw = output.get("output")
    if isinstance(raw, str):
        text = raw
    elif isinstance(raw, list) and all(type(value) is int and 0 <= value <= 255 for value in raw):
        try:
            text = bytes(raw).decode("utf-8")
        except UnicodeDecodeError:
            return None, terminal["line"], "native command output is not complete UTF-8"
    else:
        return None, terminal["line"], "native command output is not a complete supported byte/string value"
    return text, terminal["line"], None


def _compact_native_worker_commit_check(child_calls: list[dict[str, Any]], child_updates: list[dict[str, Any]],
                                        *, worker: str, cwd: str, owned_path: str,
                                        expected_commit: Any, start_terminal_line: int | None,
                                        finish_call_line: int | None, updates_path: Path
                                        ) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    add_calls = _native_git_action_calls(child_calls, "add")
    commit_calls = _native_git_action_calls(child_calls, "commit")
    rev_parse_calls = _native_git_action_calls(child_calls, "rev-parse")
    issues: list[str] = []
    missing: list[str] = []
    if len(add_calls) != 1:
        issues.append(f"expected one native git add for worker {worker}; found {len(add_calls)}")
    if len(commit_calls) != 1:
        issues.append(f"expected one native git commit for worker {worker}; found {len(commit_calls)}")
    if len(rev_parse_calls) != 1:
        issues.append(f"expected one native git rev-parse HEAD for worker {worker}; found {len(rev_parse_calls)}")
    result_lines: dict[str, int | None] = {"add": None, "commit": None, "rev_parse": None}
    if len(add_calls) == 1:
        add = add_calls[0]
        evidence.append(_locator(updates_path, add.get("line") if type(add.get("line")) is int else None))
        expected_add = ["git", "-C", str(Path(cwd).resolve()), "add", "--", owned_path]
        if add.get("parse_error") or add.get("tokens") != expected_add:
            issues.append(f"worker {worker} native git add is not bound to its exact worktree and owned path")
        _, add_result_line, add_error = _native_terminal_output(add, child_updates)
        result_lines["add"] = add_result_line
        if add_error:
            issues.append(f"worker {worker} native git add result: {add_error}")
        if add_result_line is not None:
            evidence.append(_locator(updates_path, add_result_line))
    if len(commit_calls) == 1:
        commit = commit_calls[0]
        evidence.append(_locator(updates_path, commit.get("line") if type(commit.get("line")) is int else None))
        expected_commit_command = ["git", "-C", str(Path(cwd).resolve()), "commit", "-m",
                                   f"Ask Agent fixture worker {worker}"]
        if commit.get("parse_error") or commit.get("tokens") != expected_commit_command:
            issues.append(f"worker {worker} native git commit is not the exact standalone bound-worktree command")
        _, commit_result_line, commit_error = _native_terminal_output(commit, child_updates)
        result_lines["commit"] = commit_result_line
        if commit_error:
            issues.append(f"worker {worker} native git commit result: {commit_error}")
        if commit_result_line is not None:
            evidence.append(_locator(updates_path, commit_result_line))
    if len(rev_parse_calls) == 1:
        rev_parse = rev_parse_calls[0]
        evidence.append(_locator(updates_path, rev_parse.get("line") if type(rev_parse.get("line")) is int else None))
        expected_rev_parse = ["git", "-C", str(Path(cwd).resolve()), "rev-parse", "HEAD"]
        if rev_parse.get("parse_error") or rev_parse.get("tokens") != expected_rev_parse:
            issues.append(f"worker {worker} native git rev-parse is not the exact standalone bound-worktree HEAD command")
        output, rev_parse_result_line, rev_parse_error = _native_terminal_output(rev_parse, child_updates)
        result_lines["rev_parse"] = rev_parse_result_line
        if rev_parse_error:
            issues.append(f"worker {worker} native git rev-parse result: {rev_parse_error}")
        elif output is not None:
            values = [line.strip() for line in output.splitlines() if line.strip()]
            if (len(values) != 1
                    or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", values[0]) is None
                    or not isinstance(expected_commit, str)
                    or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_commit) is None
                    or values[0] != expected_commit):
                issues.append(f"worker {worker} native full HEAD SHA does not exactly match the helper commit proof")
        if rev_parse_result_line is not None:
            evidence.append(_locator(updates_path, rev_parse_result_line))
    if start_terminal_line is None or finish_call_line is None:
        missing.append(f"worker {worker} native start/finish call boundary is unavailable")
    elif len(add_calls) == len(commit_calls) == len(rev_parse_calls) == 1:
        action_calls = (add_calls[0], commit_calls[0], rev_parse_calls[0])
        action_lines = [item.get("line") for item in action_calls]
        result_order = [result_lines[action] for action in ("add", "commit", "rev_parse")]
        if (any(type(line) is not int for line in action_lines + result_order)
                or not (start_terminal_line < action_lines[0] < result_order[0]
                        < action_lines[1] < result_order[1] < action_lines[2]
                        < result_order[2] < finish_call_line)):
            issues.append(f"worker {worker} add, commit, and full-SHA readback did not complete in order between native start and finish")
    status = "FAIL" if issues else "INCOMPLETE" if missing else "PASS"
    detail = "; ".join(issues or missing) if issues or missing else f"worker {worker} committed its exact owned path and read back the helper-bound full SHA between successful native start and finish"
    return (_check(status, detail, *evidence) | {"errors": issues, "missing": missing},
            {"add_invocations": len(add_calls), "commit_invocations": len(commit_calls),
             "rev_parse_invocations": len(rev_parse_calls),
             "commit_sha": expected_commit if isinstance(expected_commit, str) else None,
             "start_terminal_line": start_terminal_line, "finish_call_line": finish_call_line,
             "add_result_line": result_lines["add"], "commit_result_line": result_lines["commit"],
             "rev_parse_result_line": result_lines["rev_parse"]})


def _compact_ephemeral_no_commit_check(child_calls: list[dict[str, Any]], worker: str, updates_path: Path
                                       ) -> tuple[dict[str, Any], dict[str, Any]]:
    commits = _native_git_action_calls(child_calls, "commit")
    evidence = [_locator(updates_path, item.get("line") if type(item.get("line")) is int else None)
                for item in commits]
    if commits:
        return (_check("FAIL", f"ephemeral worker {worker} transcript contains {len(commits)} git commit call(s)", *evidence),
                {"commit_invocations": len(commits)})
    return _check("PASS", f"ephemeral worker {worker} transcript contains no native git commit calls"), {"commit_invocations": 0}


def _compact_worker_phase_check(run: Path, assignments: list[dict[str, Any]], launches: list[dict[str, Any]],
                                child_transcripts: dict[str, dict[str, Any]], updates_path: Path, *,
                                native_cwd_probe_passed: bool = False, delivery_mode: str = "patch"
                                ) -> dict[str, Any]:
    setup_path = run / "operator" / "setup-result.json"
    issues: list[str] = []
    missing: list[str] = []
    try:
        setup = _read_json(setup_path, "compact setup")
        manifest = _read_json(run / "manifest.json", "manifest")
    except (OSError, TraceError) as exc:
        return _check("INCOMPLETE", f"compact setup is unavailable: {exc}", _locator(setup_path))
    setup_workers = {item.get("worker_id"): item for item in setup.get("workers", []) if isinstance(item, dict)}
    launch_by_worker = {str(item.get("worker_id")): item for item in launches if item.get("worker_id") is not None}
    details: list[dict[str, Any]] = []
    for task in assignments:
        worker = str(task.get("worker_id"))
        setup_worker = setup_workers.get(worker)
        launch = launch_by_worker.get(worker)
        binding_path = str(setup_worker.get("compact_binding_path", "")) if setup_worker else ""
        binding_sha = setup_worker.get("compact_binding_sha256") if setup_worker else None
        cwd = setup_worker.get("worktree") if setup_worker else None
        child_id = launch.get("child_session_id") if launch else None
        transcript_info = child_transcripts.get(child_id) if isinstance(child_id, str) else None
        retained_path = transcript_info.get("retained", {}).get("path") if isinstance(transcript_info, dict) else None
        transcript_path = Path(retained_path) if isinstance(retained_path, str) else None
        worker_detail = {"worker_id": worker, "child_session_id": child_id, "phases": {}}
        if setup_worker is None or launch is None or not isinstance(cwd, str) or not isinstance(binding_sha, str):
            missing.append(f"worker {worker} lacks a unique setup, launch, worktree, or binding")
            details.append(worker_detail)
            continue
        if launch.get("cwd") != cwd:
            issues.append(f"worker {worker} native cwd differs from compact setup worktree")
        child_calls: list[dict[str, Any]] = []
        attempts_by_phase: dict[str, dict[str, Any]] = {}
        native_result_lines: dict[str, int | None] = {}
        native_call_lines: dict[str, int | None] = {}
        native_result_values: dict[str, dict[str, Any]] = {}
        child_updates: list[dict[str, Any]] = []
        if transcript_path is None or not transcript_path.is_file():
            missing.append(f"worker {worker} retained native child transcript is missing")
        else:
            try:
                child_updates = _root_updates(transcript_path, str(child_id))
                for row in child_updates:
                    update = row["update"]
                    raw = update.get("rawInput")
                    command = raw.get("command") if isinstance(raw, dict) else None
                    if update.get("sessionUpdate") == "tool_call" and isinstance(command, str):
                        child_calls.append({"line": row["line"], "tool_call_id": update.get("toolCallId"),
                                            "command": command})
            except (OSError, TraceError) as exc:
                issues.append(f"worker {worker} child transcript is invalid: {exc}")
        for phase in ("start", "finish"):
            native_matches = []
            for item in child_calls:
                invocation = _compact_child_invocation(
                    item["command"], run, worker, phase, cwd, binding_path,
                    launch_cwd_verified=(native_cwd_probe_passed and launch.get("cwd") == cwd),
                )
                if invocation is not None:
                    native_matches.append(item | invocation)
            native_result_valid = False
            native_result_line = None
            if len(native_matches) == 1:
                call_id = native_matches[0].get("tool_call_id")
                terminal, terminal_error = (
                    _unique_terminal_after(call_id, native_matches[0].get("line"), child_updates)
                    if isinstance(call_id, str) else (None, "native wrapper has no typed tool-call ID")
                )
                if terminal is None:
                    missing.append(f"worker {worker} native {phase} wrapper result: {terminal_error}")
                else:
                    native_result_line = terminal["line"]
                    raw_output = terminal["update"].get("rawOutput")
                    output = raw_output.get("output") if isinstance(raw_output, dict) else None
                    result = _compact_wrapper_result(
                        output, fixture_test=native_matches[0].get("fixture_test") is True
                    )
                    production_check = ("production_worker_start_passed" if phase == "start"
                                        else "production_worker_finish_passed")
                    if phase == "start":
                        wrapper_checks = ("production_worker_start_passed", "helper_context_verified",
                                          "fixture_probe_passed", "phase_passed")
                    elif delivery_mode == "commits":
                        wrapper_checks = ("worker_check_passed", "production_worker_finish_passed",
                                          "fixture_probe_passed", "returned_patch_bound",
                                          "returned_commit_bound", "commit_delivery_bound", "phase_passed")
                    elif delivery_mode == "ephemeral":
                        wrapper_checks = ("worker_check_passed", "production_worker_finish_passed",
                                          "fixture_probe_passed", "ephemeral_findings_only", "phase_passed")
                    else:
                        wrapper_checks = ("worker_check_passed", "production_worker_finish_passed",
                                          "fixture_probe_passed", "returned_patch_bound", "phase_passed")
                    native_result_valid = (
                        terminal["update"].get("status") == "completed"
                        and isinstance(raw_output, dict) and raw_output.get("type") == "Bash"
                        and type(raw_output.get("exit_code")) is int and raw_output.get("exit_code") == 0
                        and raw_output.get("truncated") is False
                        and isinstance(result, dict) and result.get("status") == "PASSED"
                        and result.get("run_id") == manifest.get("run_id")
                        and result.get("worker_id") == worker and result.get("phase") == phase
                        and result.get("root") == cwd
                        and result.get("evidence") == str((run / "operator" / "worker-phases" / f"worker-{worker}-{phase}" / "attempt.json").resolve())
                        and isinstance(result.get("checks"), dict)
                        and all(result["checks"].get(name) is True for name in wrapper_checks)
                    )
                    if native_result_valid and phase == "finish" and delivery_mode == "commits":
                        setup_snapshot = setup_worker.get("snapshot") if isinstance(setup_worker, dict) else None
                        native_result_valid = (
                            isinstance(setup_snapshot, dict)
                            and result.get("commit_base") == setup_worker.get("commit_base") == setup_snapshot.get("commit")
                            and isinstance(result.get("contribution_commits"), list)
                            and len(result["contribution_commits"]) == 1
                            and isinstance(result["contribution_commits"][0], str)
                            and re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", result["contribution_commits"][0]) is not None
                        )
                    if native_result_valid and phase == "finish" and delivery_mode == "ephemeral":
                        native_result_valid = (
                            isinstance(result.get("ephemeral_audit"), dict)
                            and result.get("checks", {}).get("ephemeral_findings_only") is True
                            and not any(key in result for key in (
                                "returned_inspection", "patch_path", "patch_sha256", "commit_base",
                                "contribution_commits", "commit_sha", "delivery", "integration_strategy",
                            ))
                        )
                    if not native_result_valid:
                        issues.append(f"worker {worker} native {phase} wrapper terminal result is not a successful bound phase")
                    if isinstance(result, dict):
                        native_result_values[phase] = result
            attempt_path = run / "operator" / "worker-phases" / f"worker-{worker}-{phase}" / "attempt.json"
            try:
                attempt = _read_json(attempt_path, f"worker {worker} {phase} attempt")
            except (OSError, TraceError):
                attempt = None
            if isinstance(attempt, dict):
                attempts_by_phase[phase] = attempt
            native_call_lines[phase] = native_matches[0].get("line") if len(native_matches) == 1 else None
            native_result_lines[phase] = native_result_line
            label = "compact-worker-start" if phase == "start" else "compact-worker-finish"
            calls = [item for item in attempt.get("calls", []) if item.get("label") == label] if attempt else []
            command_valid = False
            call_path = None
            if len(calls) == 1:
                call_path = Path(calls[0].get("evidence", ""))
                try:
                    call_record = _read_json(call_path, f"worker {worker} {phase} production command")
                    result = call_record.get("json")
                    task_script = Path(manifest["paths"]["package"]).resolve() / "scripts" / "ask_agent_task.py"
                    expected_argv = [sys.executable, "-B", str(task_script.resolve()),
                                     "worker-start" if phase == "start" else "worker-finish",
                                     "--binding", str(Path(binding_path).resolve())]
                    try:
                        raw_result = json.loads(call_record.get("stdout", ""))
                    except (TypeError, json.JSONDecodeError):
                        raw_result = None
                    workspace = result.get("workspace_evidence", {}) if isinstance(result, dict) else {}
                    inspection = workspace.get("inspection", {}) if isinstance(workspace, dict) else {}
                    if not isinstance(inspection, dict):
                        inspection = {}
                    common_command_valid = (
                        not call_path.is_symlink() and call_record.get("argv") == expected_argv
                        and call_record.get("cwd") == cwd and call_record.get("exit_code") == 0
                        and call_record.get("status") == "COMPLETED"
                        and raw_result == result
                        and isinstance(result, dict) and isinstance(attempt, dict)
                        and attempt.get("status") == "PASSED" and attempt.get("worker_id") == worker
                        and attempt.get("phase") == phase and attempt.get("root") == cwd
                        and attempt.get("compact_binding_path") == str(Path(binding_path).resolve())
                        and attempt.get("compact_binding_sha256") == binding_sha
                        and result.get("binding_sha256") == binding_sha
                        and result.get("status") == ("WORKER_CONTEXT_READY" if phase == "start" else "READY_FOR_PARENT_ACCEPTANCE")
                        and (phase == "start" or result.get("command") == "worker-finish")
                    )
                    if phase == "start":
                        command_valid = (common_command_valid and inspection.get("status") == "prepared"
                                         and inspection.get("worktree") == cwd
                                         and inspection.get("receipt") == setup_worker.get("receipt"))
                    elif delivery_mode == "ephemeral":
                        ephemeral = workspace.get("ephemeral_audit") if isinstance(workspace, dict) else None
                        changed_paths = ephemeral.get("changed_paths") if isinstance(ephemeral, dict) else None
                        command_valid = (
                            common_command_valid and isinstance(workspace, dict)
                            and isinstance(ephemeral, dict) and ephemeral.get("status") == "ephemeral-audit"
                            and ephemeral.get("findings_only") is True
                            and ephemeral.get("scratch_retained") is True
                            and isinstance(changed_paths, list) and len(changed_paths) == 2
                            and all(isinstance(path, str) for path in changed_paths)
                            and set(changed_paths) == {task.get("path"), ".experiment-local/owner.txt"}
                            and isinstance(ephemeral.get("baseline_fingerprint"), str)
                            and isinstance(ephemeral.get("fingerprint"), str)
                            and not any(key in workspace for key in (
                                "inspection", "delivery", "contribution_patch", "commits", "commit_base",
                            ))
                        )
                    else:
                        command_valid = (
                            common_command_valid and inspection.get("status") == "returned"
                            and inspection.get("worktree") == cwd and inspection.get("receipt") == setup_worker.get("receipt")
                            and inspection.get("contribution_paths") == [task.get("path")]
                        )
                        if command_valid and delivery_mode == "commits":
                            returned_delivery = inspection.get("delivery")
                            commits = returned_delivery.get("commits") if isinstance(returned_delivery, dict) else None
                            command_valid = (
                                isinstance(returned_delivery, dict)
                                and returned_delivery.get("mode") == "commits"
                                and returned_delivery.get("base") == setup_worker.get("commit_base")
                                and isinstance(commits, list) and len(commits) == 1
                                and commits == attempt.get("contribution_commits")
                                and returned_delivery.get("commit_paths") == [task.get("path")]
                                and returned_delivery.get("residual_paths") == []
                            )
                except (OSError, KeyError, IndexError, TraceError, TypeError):
                    command_valid = False
            worker_detail["phases"][phase] = {
                "native_invocations": len(native_matches), "native_line": native_matches[0]["line"] if len(native_matches) == 1 else None,
                "native_result_valid": native_result_valid, "native_result_line": native_result_line,
                "production_command_valid": command_valid,
                "attempt": _locator(attempt_path) if attempt_path.exists() else None,
                "command": _locator(call_path) if call_path and call_path.exists() else None,
            }
            if not native_matches:
                missing.append(f"worker {worker} native transcript lacks its {phase} compact wrapper invocation")
            elif len(native_matches) != 1:
                issues.append(f"worker {worker} native transcript contains duplicate {phase} wrapper invocations")
            if not command_valid:
                if not attempt or len(calls) != 1:
                    missing.append(f"worker {worker} has no unique retained production {phase} command")
                else:
                    issues.append(f"worker {worker} production {phase} command or binding evidence does not match")
        details.append(worker_detail)
        if delivery_mode == "commits":
            finish_attempt = attempts_by_phase.get("finish")
            returned_inspection = finish_attempt.get("returned_inspection") if isinstance(finish_attempt, dict) else None
            delivery = returned_inspection.get("delivery") if isinstance(returned_inspection, dict) else None
            contribution_commits = finish_attempt.get("contribution_commits") if isinstance(finish_attempt, dict) else None
            commit_sha = contribution_commits[0] if isinstance(contribution_commits, list) and len(contribution_commits) == 1 else None
            commit_base = setup_worker.get("commit_base") if isinstance(setup_worker, dict) else None
            snapshot = setup_worker.get("snapshot") if isinstance(setup_worker, dict) else None
            helper_proof_errors: list[str] = []
            if (not isinstance(snapshot, dict) or snapshot.get("mode") != "private-commit"
                    or not isinstance(commit_base, str) or not commit_base
                    or snapshot.get("commit") != commit_base or type(snapshot.get("source_dirty")) is not bool
                    or not isinstance(snapshot.get("tree"), str)
                    or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", snapshot.get("tree", "")) is None
                    or type(snapshot.get("created")) is not bool
                    or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit_base) is None):
                helper_proof_errors.append("setup does not retain the private commit base and snapshot")
            worker_baseline = setup_worker.get("worker_baseline") if isinstance(setup_worker, dict) else None
            if (not isinstance(worker_baseline, dict) or worker_baseline.get("root") != cwd
                    or worker_baseline.get("head") != commit_base or worker_baseline.get("status") != {}):
                helper_proof_errors.append("setup worker baseline is not clean at the selected commit base")
            if not isinstance(finish_attempt, dict):
                helper_proof_errors.append("worker finish attempt is unavailable")
            else:
                attempt_checks = finish_attempt.get("checks")
                if not isinstance(attempt_checks, dict) or attempt_checks.get("returned_patch_bound") is not True \
                        or attempt_checks.get("returned_commit_bound") is not True \
                        or attempt_checks.get("commit_delivery_bound") is not True:
                    helper_proof_errors.append("finish attempt lacks the bound returned patch and commit checks")
            if (not isinstance(delivery, dict) or delivery.get("mode") != "commits"
                    or delivery.get("base") != commit_base
                    or delivery.get("commits") != contribution_commits
                    or delivery.get("commit_paths") != [task.get("path")]
                    or not isinstance(returned_inspection, dict)
                    or returned_inspection.get("commit_paths") != [task.get("path")]
                    or returned_inspection.get("contribution_paths") != [task.get("path")]
                    or delivery.get("per_commit_paths") != [{"commit": commit_sha, "paths": [task.get("path")]}]
                    or delivery.get("residual_paths") != []):
                helper_proof_errors.append("returned helper delivery does not bind the one ordered worker commit to its owned path")
            if not isinstance(contribution_commits, list) or len(contribution_commits) != 1 \
                    or not isinstance(commit_sha, str) or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit_sha) is None \
                    or commit_sha == commit_base:
                helper_proof_errors.append("finish attempt does not contain exactly one full contribution commit SHA")
            if (isinstance(snapshot, dict) and snapshot.get("source_dirty") is True):
                contribution_patch = delivery.get("contribution_patch") if isinstance(delivery, dict) else None
                patch_path = finish_attempt.get("patch_path") if isinstance(finish_attempt, dict) else None
                patch_sha = finish_attempt.get("patch_sha256") if isinstance(finish_attempt, dict) else None
                patch_matches = False
                if isinstance(contribution_patch, str) and contribution_patch == patch_path:
                    try:
                        contribution_path = Path(contribution_patch)
                        patch_matches = (contribution_path.is_file() and not contribution_path.is_symlink()
                                         and isinstance(patch_sha, str)
                                         and hashlib.sha256(contribution_path.read_bytes()).hexdigest() == patch_sha)
                    except OSError:
                        patch_matches = False
                if not patch_matches:
                    helper_proof_errors.append("dirty-source commit delivery does not retain its bound contribution patch")
            elif isinstance(delivery, dict) and "contribution_patch" in delivery:
                helper_proof_errors.append("clean-source commit delivery unexpectedly includes a contribution patch")
            finish_result = attempts_by_phase.get("finish")
            if isinstance(finish_result, dict):
                production_result = finish_result.get("compact_worker_result")
                workspace = production_result.get("workspace_evidence") if isinstance(production_result, dict) else None
                production_inspection = workspace.get("inspection") if isinstance(workspace, dict) else None
                if production_inspection != returned_inspection:
                    helper_proof_errors.append("finish attempt helper inspection differs from production worker-finish evidence")
                native_finish = native_result_values.get("finish")
                if (not isinstance(native_finish, dict)
                        or native_finish.get("commit_base") != commit_base
                        or native_finish.get("contribution_commits") != contribution_commits
                        or native_finish.get("returned_inspection") != returned_inspection
                        or native_finish.get("patch_path") != finish_result.get("patch_path")
                        or native_finish.get("patch_sha256") != finish_result.get("patch_sha256")):
                    helper_proof_errors.append("native finish output differs from the retained worker commit proof")
            if helper_proof_errors:
                issues.extend(f"worker {worker}: {error}" for error in helper_proof_errors)
            native_commit, native_commit_detail = _compact_native_worker_commit_check(
                child_calls, child_updates if transcript_path is not None and transcript_path.is_file() else [],
                worker=worker, cwd=str(cwd), owned_path=str(task.get("path")), expected_commit=commit_sha,
                start_terminal_line=native_result_lines.get("start"),
                finish_call_line=native_call_lines.get("finish"), updates_path=updates_path,
            )
            if native_commit.get("status") != "PASS":
                issues.append(f"worker {worker} native commit proof: {native_commit.get('detail')}")
            worker_detail["native_commit"] = native_commit_detail | {"status": native_commit.get("status"),
                                                                      "evidence": native_commit.get("evidence", [])}
        elif delivery_mode == "ephemeral":
            no_commit, no_commit_detail = _compact_ephemeral_no_commit_check(child_calls, worker, updates_path)
            worker_detail["native_commit"] = no_commit_detail | {"status": no_commit.get("status"),
                                                                  "evidence": no_commit.get("evidence", [])}
            if no_commit.get("status") != "PASS":
                issues.append(f"worker {worker} ephemeral mode forbids native commits: {no_commit.get('detail')}")
            finish_attempt = attempts_by_phase.get("finish")
            if isinstance(finish_attempt, dict):
                workspace_evidence = finish_attempt.get("ephemeral_audit")
                production_result = finish_attempt.get("compact_worker_result")
                production_workspace = production_result.get("workspace_evidence") if isinstance(production_result, dict) else None
                production_audit = production_workspace.get("ephemeral_audit") if isinstance(production_workspace, dict) else None
                expected_finish_fields = isinstance(workspace_evidence, dict) and (
                    set(workspace_evidence) == {
                        "status", "findings_only", "changed_paths", "baseline_fingerprint",
                        "fingerprint", "head", "branch", "scratch_retained", "actual_cwd",
                    }
                    and workspace_evidence.get("status") == "ephemeral-audit"
                    and workspace_evidence.get("findings_only") is True
                    and workspace_evidence.get("actual_cwd") == str(Path(cwd).resolve())
                    and workspace_evidence.get("scratch_retained") is True
                    and isinstance(workspace_evidence.get("changed_paths"), list)
                    and len(workspace_evidence.get("changed_paths")) == 2
                    and all(isinstance(path, str) for path in workspace_evidence.get("changed_paths"))
                    and set(workspace_evidence.get("changed_paths"))
                    == {task.get("path"), ".experiment-local/owner.txt"}
                    and isinstance(workspace_evidence.get("baseline_fingerprint"), str)
                    and isinstance(workspace_evidence.get("fingerprint"), str)
                    and workspace_evidence == production_audit
                )
                forbidden = {"returned_inspection", "patch_path", "patch_sha256", "commit_base",
                             "contribution_commits", "commit_sha", "delivery", "integration_strategy"}
                if not expected_finish_fields or any(key in finish_attempt for key in forbidden):
                    issues.append(f"worker {worker} ephemeral finish does not retain findings-only evidence without delivery fields")
                native_finish = native_result_values.get("finish")
                if (not isinstance(native_finish, dict)
                        or native_finish.get("ephemeral_audit") != workspace_evidence
                        or any(key in native_finish for key in forbidden)):
                    issues.append(f"worker {worker} native finish output does not bind findings-only evidence without delivery fields")
    status = "FAIL" if issues else "INCOMPLETE" if missing else "PASS"
    detail = "; ".join(issues or missing) if issues or missing else "each native child invoked both bound compact wrappers and retained the successful production checks"
    return _check(status, detail, _locator(setup_path), _locator(run / "operator" / "worker-phases"), _locator(updates_path)) | {
        "errors": issues, "missing": missing, "workers": details,
    }


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _contains_key(value: Any, keys: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in keys or _contains_key(item, keys) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_key(item, keys) for item in value)
    return False


def _ephemeral_audit_projection_matches(phase_audit: Any, returned_audit: Any,
                                       expected_cwd: Any) -> bool:
    shared_fields = {
        "status", "findings_only", "changed_paths", "baseline_fingerprint", "fingerprint",
        "head", "branch", "scratch_retained",
    }
    if not isinstance(phase_audit, dict) or not isinstance(returned_audit, dict):
        return False
    return (
        set(phase_audit) == shared_fields | {"actual_cwd"}
        and set(returned_audit) == shared_fields
        and {key: phase_audit[key] for key in shared_fields} == returned_audit
        and isinstance(expected_cwd, str)
        and phase_audit.get("actual_cwd") == expected_cwd
    )


def _ephemeral_finding_valid(run: Path, task: dict[str, Any], setup_worker: dict[str, Any],
                             return_record: dict[str, Any], phase: dict[str, Any],
                             finding: Any, finding_sha256: Any) -> tuple[bool, str]:
    worker = str(task.get("worker_id"))
    return_result = return_record.get("result")
    returned_workspace = return_result.get("workspace_evidence") if isinstance(return_result, dict) else None
    returned_audit = returned_workspace.get("ephemeral_audit") if isinstance(returned_workspace, dict) else None
    production_result = phase.get("compact_worker_result")
    production_workspace = production_result.get("workspace_evidence") if isinstance(production_result, dict) else None
    production_audit = production_workspace.get("ephemeral_audit") if isinstance(production_workspace, dict) else None
    phase_audit = phase.get("ephemeral_audit")
    phase_checks = phase.get("checks") if isinstance(phase, dict) else None
    worktree = setup_worker.get("worktree")
    if (not isinstance(phase_checks, dict)
            or phase.get("status") != "PASSED" or phase.get("worker_id") != worker
            or phase_checks.get("production_worker_finish_passed") is not True
            or phase_checks.get("ephemeral_findings_only") is not True
            or not isinstance(phase_audit, dict) or phase_audit != production_audit
            or not _ephemeral_audit_projection_matches(phase_audit, returned_audit, worktree)):
        return False, f"worker {worker} findings do not bind to successful finish and findings-only verify-return evidence"
    if (not isinstance(return_result, dict) or return_record.get("status") != "PASSED"
            or return_record.get("exit_code") != 0
            or return_result.get("status") != "READY_FOR_PARENT_ACCEPTANCE"
            or return_result.get("command") != "verify-return"
            or not isinstance(returned_workspace, dict) or set(returned_workspace) != {"ephemeral_audit"}
            or _contains_key(returned_workspace, {
                "inspection", "delivery", "contribution_patch", "patch_path", "patch_sha256",
                "commit_base", "contribution_commits", "commit_records", "integration_strategy",
            })):
        return False, f"worker {worker} verify-return is not findings-only"
    expected_paths = [task.get("path"), ".experiment-local/owner.txt"]
    changed_paths = phase_audit.get("changed_paths") if isinstance(phase_audit, dict) else None
    if (not isinstance(phase_audit, dict) or phase_audit.get("status") != "ephemeral-audit"
            or phase_audit.get("findings_only") is not True or phase_audit.get("scratch_retained") is not True
            or not isinstance(changed_paths, list) or len(changed_paths) != 2
            or not all(isinstance(path, str) for path in changed_paths)
            or set(changed_paths) != set(expected_paths)
            or not isinstance(phase_audit.get("baseline_fingerprint"), str)
            or not isinstance(phase_audit.get("fingerprint"), str)):
        return False, f"worker {worker} ephemeral audit lacks a bound findings-only scratch snapshot"
    if not isinstance(finding, dict) or set(finding) != {
            "worker_id", "path", "formula", "module_sha256", "oracle", "ephemeral_audit"}:
        return False, f"worker {worker} finalization findings have an unexpected shape"
    try:
        task_id = int(worker)
    except ValueError:
        return False, f"worker {worker} is not a numeric fixture task ID"
    if (finding.get("worker_id") != worker or finding.get("path") != task.get("path")
            or finding.get("formula") != f"({task_id}+1)*x+{task_id}*{task_id}"
            or finding.get("ephemeral_audit") != returned_audit):
        return False, f"worker {worker} finalization finding does not bind its assigned task and phase evidence"
    if not isinstance(worktree, str) or not Path(worktree).is_absolute():
        return False, f"worker {worker} findings do not name an absolute worktree"
    module_path = Path(worktree) / str(task.get("path"))
    try:
        if (module_path.is_symlink() or not module_path.is_file()
                or hashlib.sha256(module_path.read_bytes()).hexdigest() != finding.get("module_sha256")):
            return False, f"worker {worker} module bytes do not match the retained findings digest"
    except OSError:
        return False, f"worker {worker} module bytes are unavailable for findings verification"
    oracle = finding.get("oracle")
    inputs = [-10**30, -999, -7, -1, 0, 1, 9, 100, 10**30]
    expected_cases = [
        {"input": value, "expected": (task_id + 1) * value + task_id * task_id,
         "actual": (task_id + 1) * value + task_id * task_id, "passed": True}
        for value in inputs
    ]
    valid_oracle = isinstance(oracle, dict) and oracle.get("passed") is True
    cases = oracle.get("cases") if isinstance(oracle, dict) else None
    if valid_oracle and isinstance(cases, list) and len(cases) == len(expected_cases):
        for actual_case, expected_case in zip(cases, expected_cases):
            if (not isinstance(actual_case, dict) or set(actual_case) != {"input", "expected", "actual", "passed"}
                    or type(actual_case.get("input")) is not int
                    or type(actual_case.get("expected")) is not int
                    or type(actual_case.get("actual")) is not int
                    or actual_case.get("input") != expected_case["input"]
                    or actual_case.get("expected") != expected_case["expected"]
                    or actual_case.get("actual") != expected_case["actual"]
                    or actual_case.get("passed") is not True):
                valid_oracle = False
                break
    else:
        valid_oracle = False
    if not valid_oracle:
        return False, f"worker {worker} findings do not independently establish the expected task oracle"
    if (not isinstance(finding_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", finding_sha256) is None
            or _canonical_json_sha256(finding) != finding_sha256):
        return False, f"worker {worker} findings SHA-256 does not match canonical JSON"
    return True, ""


def _compact_parent_return_check(run: Path, assignments: list[dict[str, Any]], root_updates: list[dict[str, Any]],
                                 collect_calls: list[dict[str, Any]], updates_path: Path, *,
                                 delivery_mode: str = "patch", launches: list[dict[str, Any]] | None = None
                                 ) -> dict[str, Any]:
    script = run / "operator" / "operations.py"
    issues: list[str] = []
    missing: list[str] = []
    evidence = [_locator(run / "operator" / "compact-returns"), _locator(updates_path)]
    expected_ids = [str(item.get("worker_id")) for item in assignments if isinstance(item, dict)]
    if delivery_mode not in {"patch", "patch-legacy", "commits", "ephemeral"}:
        return _check("FAIL", "compact parent-return delivery mode is invalid", *evidence)
    mode = "patch" if delivery_mode == "patch-legacy" else delivery_mode
    legacy_patch = delivery_mode == "patch-legacy"
    calls_by_worker: dict[str, dict[str, Any]] = {}
    values_by_worker: dict[str, dict[str, Any]] = {}
    records_by_worker: dict[str, dict[str, Any]] = {}
    terminal_by_worker: dict[str, int] = {}
    setup_path = run / "operator" / "setup-result.json"
    try:
        manifest = _read_json(run / "manifest.json", "manifest")
        setup = _read_json(setup_path, "compact setup")
    except (OSError, TraceError) as exc:
        return _check("INCOMPLETE", f"compact return evidence is unavailable: {exc}", *evidence, _locator(setup_path))
    setup_workers = {item.get("worker_id"): item for item in setup.get("workers", []) if isinstance(item, dict)}
    all_return_calls = _compact_cli_calls(root_updates, script, run, "verify-return")
    if len(all_return_calls) != len(expected_ids):
        issues.append(f"expected exactly {len(expected_ids)} compact verify-return calls; found {len(all_return_calls)}")
    for worker in expected_ids:
        calls = [call for call in all_return_calls
                 if call["args"].count("--worker") == 1
                 and call["args"][call["args"].index("--worker") + 1:][:1] == [worker]]
        if len(calls) != 1:
            missing.append(f"one compact verify-return call for worker {worker} (found {len(calls)})")
            continue
        call = calls[0]
        expected_args = ["verify-return", "--run", str(run.resolve()), "--worker", worker]
        if call.get("args") != expected_args:
            issues.append(f"worker {worker} verify-return command has unexpected arguments")
        value, line, error = _compact_cli_result(call, root_updates)
        if error or not isinstance(value, dict):
            missing.append(f"worker {worker} verify-return result: {error or 'not a JSON object'}")
            continue
        record_path = run / "operator" / "compact-returns" / f"worker-{worker}.json"
        evidence.append(_locator(updates_path, call["row"]["line"]))
        if line is not None:
            evidence.append(_locator(updates_path, line))
        try:
            record = _read_json(record_path, f"worker {worker} compact return")
        except (OSError, TraceError) as exc:
            missing.append(f"worker {worker} compact return record is unavailable: {exc}")
            continue
        setup_worker = setup_workers.get(worker)
        binding_sha = setup_worker.get("compact_binding_sha256") if isinstance(setup_worker, dict) else None
        task = next((item for item in assignments if str(item.get("worker_id")) == worker), None)
        package_path = manifest.get("paths", {}).get("package") if isinstance(manifest.get("paths"), dict) else None
        binding_path = setup_worker.get("compact_binding_path") if isinstance(setup_worker, dict) else None
        task_script = (Path(package_path).resolve() / "scripts" / "ask_agent_task.py"
                       if isinstance(package_path, str) else None)
        expected_return_argv = ([sys.executable, "-B", str(task_script), "verify-return", "--binding",
                                 str(Path(binding_path).resolve())]
                                if task_script is not None and isinstance(binding_path, str) else None)
        expected_cwd = (str(Path(manifest["paths"]["caller"]).resolve())
                        if isinstance(manifest.get("paths"), dict)
                        and isinstance(manifest["paths"].get("caller"), str) else None)
        if (value.get("status") != "PASSED" or value.get("worker_id") != worker
                or (not legacy_patch and value.get("delivery_mode") != mode)
                or value.get("evidence_path") != str(record_path.resolve())
                or value.get("binding_sha256") != binding_sha
                or record_path.is_symlink()
                or record.get("status") != "PASSED" or record.get("exit_code") != 0
                or record.get("worker_id") != worker or record.get("binding_sha256") != binding_sha
                or record.get("evidence_path") != str(record_path.resolve())
                or (not legacy_patch and (record.get("argv") != expected_return_argv
                    or record.get("cwd") != expected_cwd
                    or (isinstance(task, dict) and value.get("contribution_paths") != [task.get("path")])))):
            issues.append(f"worker {worker} native verify-return output differs from its bound retained record")
        try:
            record_stdout = json.loads(record.get("stdout", ""), object_pairs_hook=_unique_json_object)
        except (TypeError, json.JSONDecodeError, ValueError):
            record_stdout = None
        if record_stdout != record.get("result"):
            issues.append(f"worker {worker} retained verify-return stdout is not its exact typed result")
        calls_by_worker[worker] = call
        values_by_worker[worker] = value
        records_by_worker[worker] = record
        if line is not None:
            terminal_by_worker[worker] = line

    worker_by_child = {item.get("child_session_id"): str(item.get("worker_id"))
                       for item in (launches or []) if item.get("child_session_id")}
    collection_lines: list[int] = []
    collected_ids: set[str] = set()
    requested_ids: set[str] = set()
    expected_children = set(worker_by_child)
    for call in collect_calls:
        raw_input = call["update"].get("rawInput")
        requested = raw_input.get("task_ids", raw_input.get("taskIds")) if isinstance(raw_input, dict) else None
        if (not isinstance(requested, list) or not requested
                or any(not isinstance(child, str) for child in requested)
                or len(set(requested)) != len(requested)
                or not set(requested) <= expected_children):
            issues.append(f"collection call at line {call.get('line')} does not request a unique subset of assigned children")
            continue
        requested_ids.update(requested)
        call_id = call["update"].get("toolCallId")
        terminal, terminal_error = (
            _unique_terminal_after(call_id, call.get("line"), root_updates)
            if isinstance(call_id, str) else (None, "collection call has no typed tool-call ID")
        )
        if terminal is None:
            missing.append(f"collection call at line {call.get('line')} result: {terminal_error}")
            continue
        collection_lines.append(terminal["line"])
        evidence.append(_locator(updates_path, terminal["line"]))
        rows, row_error = _completed_task_output_rows(terminal)
        if row_error:
            issues.append(f"collection call at line {call.get('line')} result: {row_error}")
            continue
        seen_children: set[str] = set()
        for row in rows:
            child = _row_id(row)
            worker = worker_by_child.get(child)
            if child is None or worker is None or child not in requested:
                issues.append(f"collection result at line {terminal['line']} contains an unknown or unrequested child row")
                continue
            if child in seen_children:
                issues.append(f"collection result at line {terminal['line']} contains a duplicate child row")
                continue
            seen_children.add(child)
            if row.get("status") == "completed" and type(row.get("exit_code")) is int and row.get("exit_code") == 0:
                collected_ids.add(worker)
    if not collection_lines:
        missing.append("no terminal parent collection result is available")
    elif requested_ids != expected_children:
        issues.append("parent collection requests do not cover exactly the assigned children")
    elif collected_ids != set(expected_ids):
        issues.append("typed terminal collection results do not cover exactly the assigned worker IDs")
    elif calls_by_worker and min(call["row"]["line"] for call in calls_by_worker.values()) <= max(collection_lines):
        issues.append("compact verify-return began before all parent collection results were terminal")

    for worker, record in records_by_worker.items():
        result = record.get("result")
        workspace = result.get("workspace_evidence") if isinstance(result, dict) else None
        setup_worker = setup_workers.get(worker)
        task = next((item for item in assignments if str(item.get("worker_id")) == worker), None)
        phase_path = run / "operator" / "worker-phases" / f"worker-{worker}-finish" / "attempt.json"
        try:
            phase = _read_json(phase_path, f"worker {worker} finish attempt")
        except (OSError, TraceError):
            phase = None
        if not isinstance(result, dict) or not isinstance(workspace, dict) or not isinstance(setup_worker, dict):
            missing.append(f"worker {worker} verify-return lacks its production result, workspace evidence, or setup")
            continue
        if mode == "commits":
            phase_inspection = phase.get("returned_inspection") if isinstance(phase, dict) else None
            if not isinstance(phase_inspection, dict):
                phase_inspection = phase.get("inspection") if isinstance(phase, dict) else None
            production_inspection = workspace.get("inspection")
            delivery = production_inspection.get("delivery") if isinstance(production_inspection, dict) else None
            phase_delivery = phase_inspection.get("delivery") if isinstance(phase_inspection, dict) else None
            setup_snapshot = setup_worker.get("snapshot")
            commit_base = setup_worker.get("commit_base")
            commits = delivery.get("commits") if isinstance(delivery, dict) else None
            strategy = result.get("integration_strategy")
            source_dirty = setup_snapshot.get("source_dirty") if isinstance(setup_snapshot, dict) else None
            expected_strategy = "preserve-parent patch from commits" if source_dirty is True else "eligible cherry-pick"
            if (not isinstance(setup_snapshot, dict) or type(source_dirty) is not bool
                    or setup_snapshot.get("mode") != "private-commit"
                    or setup_snapshot.get("commit") != commit_base
                    or not isinstance(delivery, dict) or delivery.get("mode") != "commits"
                    or delivery.get("base") != commit_base or delivery.get("commits") != commits
                    or not isinstance(commits, list) or len(commits) != 1
                    or not isinstance(commits[0], str)
                    or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commits[0]) is None
                    or delivery.get("commit_paths") != [task.get("path") if isinstance(task, dict) else None]
                    or delivery.get("residual_paths") != []
                    or phase_delivery != delivery
                    or not isinstance(strategy, dict)
                    or strategy.get("strategy") != expected_strategy
                    or strategy.get("source_dirty") is not source_dirty
                    or strategy.get("commit_base") != commit_base
                    or strategy.get("commits") != commits
                    or strategy.get("parent_target_revalidation_required") is not True):
                issues.append(f"worker {worker} verify-return commit proof does not match setup, finish, and integration strategy")
        elif mode == "ephemeral":
            phase_audit = phase.get("ephemeral_audit") if isinstance(phase, dict) else None
            returned_audit = workspace.get("ephemeral_audit")
            if (not isinstance(phase, dict) or not isinstance(phase_audit, dict)
                    or not _ephemeral_audit_projection_matches(
                        phase_audit, returned_audit, setup_worker.get("worktree")
                    )
                    or _contains_key(workspace, {
                        "inspection", "delivery", "contribution_patch", "patch_path", "patch_sha256",
                        "commit_base", "contribution_commits", "commit_records", "integration_strategy",
                    })):
                issues.append(f"worker {worker} verify-return is not bound to findings-only finish evidence")

    last_returns = max(terminal_by_worker.values()) if len(terminal_by_worker) == len(expected_ids) else None
    operation_calls = _compact_cli_calls(root_updates, script, run, "integrate-batch")
    ephemeral_calls = _compact_cli_calls(root_updates, script, run, "finish-ephemeral")
    legacy_commit_calls = _compact_cli_calls(root_updates, script, run, "integrate-commits")
    if mode == "ephemeral":
        if operation_calls or legacy_commit_calls:
            issues.append("ephemeral delivery contains a forbidden integration command")
        if len(ephemeral_calls) != 1:
            missing.append(f"one compact finish-ephemeral call (found {len(ephemeral_calls)})")
        elif last_returns is not None:
            call = ephemeral_calls[0]
            expected_args = ["finish-ephemeral", "--run", str(run.resolve())]
            for worker in expected_ids:
                expected_args.extend(["--collected-worker", worker])
            if call.get("args") != expected_args:
                issues.append("ephemeral finalization command does not bind the exact ordered worker IDs")
            if call["row"]["line"] <= last_returns:
                issues.append("ephemeral finalization began before all verify-return commands completed")
            value, _, error = _compact_cli_result(call, root_updates)
            if error or not isinstance(value, dict):
                missing.append(f"ephemeral finalization result: {error or 'not a JSON object'}")
            else:
                result_path = run / "operator" / "integration-result.json"
                try:
                    if result_path.is_symlink():
                        raise TraceError("ephemeral integration result is a symlink")
                    final = _read_json(result_path, "ephemeral integration result")
                except (OSError, TraceError) as exc:
                    final = None
                    missing.append(f"ephemeral finalization record is unavailable: {exc}")
                evidence.extend([_locator(updates_path, call["row"]["line"]), _locator(result_path)])
                baseline = manifest.get("caller_snapshot")
                baseline_sha = _canonical_json_sha256(baseline)
                if isinstance(final, dict):
                    expected_top = {
                        "schema": "ask-agent.integration-result/v2", "run_id": manifest.get("run_id"),
                        "status": "NO_INTEGRATION", "delivery_mode": "ephemeral",
                        "worker_ids": expected_ids, "caller_snapshot_sha256": baseline_sha,
                        "caller_unchanged": True,
                    }
                    if any(final.get(key) != expected for key, expected in expected_top.items()):
                        issues.append("ephemeral finalization record does not bind the frozen caller and exact worker set")
                    if final.get("caller_snapshot") != baseline or final.get("caller_snapshot_sha256") != _canonical_json_sha256(final.get("caller_snapshot")):
                        issues.append("ephemeral finalization caller snapshot digest does not match the frozen manifest")
                    rows = final.get("workers")
                    if not isinstance(rows, list) or len(rows) != len(expected_ids):
                        issues.append("ephemeral finalization record lacks one ordered findings row per worker")
                    else:
                        setup_by_id = setup_workers
                        for worker, row in zip(expected_ids, rows):
                            task = next((item for item in assignments if str(item.get("worker_id")) == worker), None)
                            record = records_by_worker.get(worker)
                            phase_path = run / "operator" / "worker-phases" / f"worker-{worker}-finish" / "attempt.json"
                            try:
                                phase = _read_json(phase_path, f"worker {worker} finish attempt")
                            except (OSError, TraceError):
                                phase = None
                            return_path = run / "operator" / "compact-returns" / f"worker-{worker}.json"
                            if (not isinstance(row, dict)
                                    or set(row) != {"worker_id", "verify_return_path", "worker_phase_path",
                                                    "collection_ref", "findings", "findings_sha256"}
                                    or row.get("worker_id") != worker
                                    or row.get("verify_return_path") != str(return_path.resolve())
                                    or row.get("worker_phase_path") != str(phase_path.resolve())
                                    or row.get("collection_ref") != {
                                        "worker_id": worker, "kind": "parent-collected-worker-assertion"}):
                                issues.append(f"ephemeral findings row for worker {worker} has incorrect evidence references")
                                continue
                            if not isinstance(record, dict) or not isinstance(phase, dict) or not isinstance(task, dict):
                                missing.append(f"ephemeral findings evidence for worker {worker} is incomplete")
                                continue
                            valid, detail = _ephemeral_finding_valid(
                                run, task, setup_by_id.get(worker, {}), record, phase,
                                row.get("findings"), row.get("findings_sha256"),
                            )
                            if not valid:
                                issues.append(detail)
                    forbidden = {
                        "patch", "patches", "patch_path", "patch_sha256", "contribution_patch", "commit_base",
                        "contribution_commits", "commit_records", "commits", "integration_strategy",
                        "applied_worker_ids", "applied_paths", "diff", "actions",
                    }
                    if _contains_key(final, forbidden):
                        issues.append("ephemeral finalization record contains forbidden integration or delivery fields")
                if (set(value) != {"schema", "status", "delivery_mode", "worker_ids",
                                   "result_path", "caller_snapshot_sha256"}
                        or value.get("schema") != "ask-agent.integration-result/v2"
                        or value.get("status") != "NO_INTEGRATION"
                        or value.get("delivery_mode") != "ephemeral"
                        or value.get("worker_ids") != expected_ids
                        or value.get("result_path") != str(result_path.resolve())
                        or value.get("caller_snapshot_sha256") != baseline_sha):
                    issues.append("ephemeral native summary does not match its retained no-integration record")
    else:
        if legacy_commit_calls:
            issues.append("compact run contains an unsupported integrate-commits command")
        if ephemeral_calls:
            issues.append("patch or commit delivery contains a forbidden finish-ephemeral command")
        if len(operation_calls) != 1:
            missing.append(f"one compact integrate-batch call (found {len(operation_calls)})")
        elif last_returns is not None:
            call = operation_calls[0]
            expected_args = ["integrate-batch", "--run", str(run.resolve()), "--delivery-mode", mode]
            for worker in expected_ids:
                expected_args.extend(["--collected-worker", worker])
            legacy_args = ["integrate-batch", "--run", str(run.resolve())]
            if legacy_patch and call.get("args") not in (
                    legacy_args,
                    legacy_args + [flag for worker in expected_ids for flag in ("--collected-worker", worker)],
            ):
                issues.append("legacy compact integration command has unexpected arguments")
            elif not legacy_patch and call.get("args") != expected_args:
                issues.append(f"compact integration command does not bind {mode} mode and the exact ordered worker IDs")
            if call["row"]["line"] <= last_returns:
                issues.append("compact integration began before all verify-return commands completed")
            value, _, error = _compact_cli_result(call, root_updates)
            if error or not isinstance(value, dict):
                missing.append(f"compact integration result: {error or 'not a JSON object'}")
            else:
                result_path = run / "operator" / "integration-result.json"
                if legacy_patch and not result_path.exists():
                    final = None
                else:
                    try:
                        if result_path.is_symlink():
                            raise TraceError("compact integration result is a symlink")
                        final = _read_json(result_path, "compact integration result")
                    except (OSError, TraceError) as exc:
                        final = None
                        missing.append(f"compact integration record is unavailable: {exc}")
                evidence.extend([_locator(updates_path, call["row"]["line"]), _locator(result_path)])
                expected_top = (value.get("status") == "INTEGRATED"
                                and (legacy_patch or value.get("delivery_mode") == mode)
                                and value.get("applied_worker_ids") == expected_ids)
                if not expected_top:
                    issues.append("compact integration summary does not report the exact accepted worker set and mode")
                if isinstance(final, dict):
                    if (final.get("status") != "INTEGRATED" or final.get("applied_worker_ids") != expected_ids
                            or (not legacy_patch and (type(final.get("schema_version")) is not int
                                or final.get("schema_version") != 1
                                or final.get("run_id") != manifest.get("run_id")
                                or final.get("delivery_mode") != mode
                                or final.get("integration_worker_ids") != expected_ids
                                or final.get("parent_asserted_collected_worker_ids") != expected_ids))):
                        issues.append("compact integration record does not bind the exact accepted worker set and mode")
                    if not legacy_patch and value.get("result_path") != str(result_path.resolve()):
                        issues.append("compact integration summary does not name its exact retained result record")
                    if mode == "commits":
                        expected_commit_records = []
                        setup_by_id = setup_workers
                        for worker in expected_ids:
                            task = next((item for item in assignments if str(item.get("worker_id")) == worker), None)
                            setup_worker = setup_by_id.get(worker)
                            record = records_by_worker.get(worker)
                            result_record = record.get("result") if isinstance(record, dict) else None
                            workspace = result_record.get("workspace_evidence") if isinstance(result_record, dict) else None
                            inspection = workspace.get("inspection") if isinstance(workspace, dict) else None
                            delivery = inspection.get("delivery") if isinstance(inspection, dict) else None
                            phase_path = run / "operator" / "worker-phases" / f"worker-{worker}-finish" / "attempt.json"
                            try:
                                phase = _read_json(phase_path, f"worker {worker} finish attempt")
                            except (OSError, TraceError):
                                phase = None
                            commit_base = setup_worker.get("commit_base") if isinstance(setup_worker, dict) else None
                            commits = delivery.get("commits") if isinstance(delivery, dict) else None
                            patch_sha = phase.get("patch_sha256") if isinstance(phase, dict) else None
                            if (not isinstance(task, dict) or not isinstance(setup_worker, dict)
                                    or not isinstance(delivery, dict) or delivery.get("mode") != "commits"
                                    or delivery.get("base") != commit_base or not isinstance(commits, list)
                                    or len(commits) != 1 or not isinstance(commits[0], str)):
                                issues.append(f"worker {worker} lacks verified helper commit records for integration")
                                continue
                            expected_commit_records.append({
                                "worker_id": worker, "commit_base": commit_base,
                                "commits": commits, "patch_sha256": patch_sha,
                            })
                        if (final.get("commit_records") != expected_commit_records
                                or value.get("commit_records") != expected_commit_records
                                or value.get("worker_ids") != expected_ids
                                or value.get("integration_strategy") != final.get("integration_strategy")):
                            issues.append("commit integration summary/record does not preserve ordered per-worker full commit proof")
    if mode in {"commits", "ephemeral"}:
        root_git_commits = _native_git_action_calls([
            {"line": row["line"], "tool_call_id": row["update"].get("toolCallId"),
             "command": ((row["update"].get("rawInput") or {}).get("command"))}
            for row in _updates_for(root_updates, "tool_call")
            if row["update"].get("title") == "run_terminal_command"
            and isinstance(row["update"].get("rawInput"), dict)
        ], "commit")
        if root_git_commits:
            issues.append("parent transcript contains a direct git commit call; commits must remain worker-owned and ephemeral work must remain uncommitted")
    status = "FAIL" if issues else "INCOMPLETE" if missing else "PASS"
    detail = "; ".join(issues or missing) if issues or missing else f"parent collected all workers before {mode} verify-return and delivery finalization"
    return _check(status, detail, *evidence, _locator(setup_path)) | {
        "errors": issues, "missing": missing,
        "delivery_mode": mode, "verify_return_workers": sorted(calls_by_worker),
        "verify_return_terminal_lines": terminal_by_worker,
    }


def _safe_parent_calculation(command: str, run_root: Path, caller_root: Path) -> bool:
    """Recognize one bounded read-only calculation with an external JSON output."""
    prefix = "python3 - << 'PY'\n"
    marker = "\nPY\n"
    if not command.startswith(prefix) or command[len(prefix):].count(marker) != 1:
        return False
    body, suffix = command[len(prefix):].split(marker, 1)
    expected_git = [
        ["git", "-C", str(caller_root), "rev-parse", "HEAD"],
        ["git", "-C", str(caller_root), "status", "--porcelain=v1"],
    ]
    try:
        git_commands = [shlex.split(line) for line in suffix.splitlines()]
        if git_commands != expected_git:
            return False
        tree = ast.parse(body)
    except (SyntaxError, ValueError):
        return False

    allowed_nodes = {
        ast.Module, ast.Import, ast.ImportFrom, ast.alias, ast.Assign, ast.Name,
        ast.Load, ast.Store, ast.Constant, ast.List, ast.Tuple, ast.Dict,
        ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.BinOp, ast.Add,
        ast.Mult, ast.USub, ast.UnaryOp, ast.Call, ast.Attribute, ast.keyword,
        ast.For, ast.Expr, ast.Subscript,
    }
    if any(type(node) not in allowed_nodes for node in ast.walk(tree)):
        return False
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    imports_from = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    if (len(imports) != 1 or [item.name for item in imports[0].names] != ["hashlib", "json"]
            or any(item.asname for item in imports[0].names)):
        return False
    if (len(imports_from) != 1 or imports_from[0].module != "pathlib"
            or imports_from[0].level != 0 or len(imports_from[0].names) != 1
            or imports_from[0].names[0].name != "Path" or imports_from[0].names[0].asname):
        return False
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1 or functions[0].name != "step" or functions[0].decorator_list:
        return False
    step_args = functions[0].args
    if ([argument.arg for argument in step_args.args] != ["value", "a", "b"]
            or step_args.posonlyargs or step_args.vararg or step_args.kwonlyargs
            or step_args.kw_defaults or step_args.kwarg or step_args.defaults):
        return False

    expected_paths = {
        "out": str((run_root / "operator" / "parent-expected.json").resolve()),
        "index": str((run_root / "primary" / ".git" / "worktrees" / "caller" / "index").resolve()),
    }
    path_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "Path"]
    bindings: dict[str, str] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target, value = statement.targets[0], statement.value
        if (isinstance(target, ast.Name) and target.id in expected_paths
                and isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id == "Path" and len(value.args) == 1 and not value.keywords
                and isinstance(value.args[0], ast.Constant) and isinstance(value.args[0].value, str)):
            if target.id in bindings:
                return False
            bindings[target.id] = str(Path(value.args[0].value).resolve())
    if len(path_calls) != 2 or bindings != expected_paths:
        return False
    if not Path(expected_paths["index"]).is_file():
        return False

    stores = [node.id for node in ast.walk(tree)
              if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)]
    if (stores.count("out") != 1 or stores.count("index") != 1
            or any(name in stores for name in ("Path", "hashlib", "json"))):
        return False
    if any(argument.arg in {"out", "index", "Path", "hashlib", "json"}
           for argument in (node for node in ast.walk(tree) if isinstance(node, ast.arg))):
        return False
    safe_names = {"Path", "enumerate", "step", "str", "print"}
    safe_attributes = {
        ("json", "dumps"), ("out", "write_text"), ("out", "read_text"),
        ("index", "read_bytes"), ("stages", "append"), ("traces", "append"),
        ("outputs", "append"), ("hashlib", "sha256"),
    }
    counts: dict[tuple[str, str], int] = {}
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        function = call.func
        if isinstance(function, ast.Name):
            if function.id not in safe_names:
                return False
        elif isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
            key = (function.value.id, function.attr)
            if key not in safe_attributes:
                return False
            counts[key] = counts.get(key, 0) + 1
        elif (isinstance(function, ast.Attribute) and function.attr == "hexdigest"
              and isinstance(function.value, ast.Call)
              and isinstance(function.value.func, ast.Attribute)
              and isinstance(function.value.func.value, ast.Name)
              and function.value.func.value.id == "hashlib"
              and function.value.func.attr == "sha256"):
            counts[("hashlib", "hexdigest")] = counts.get(("hashlib", "hexdigest"), 0) + 1
        else:
            return False
    if (counts.get(("out", "write_text")) != 1
            or counts.get(("out", "read_text")) != 1
            or counts.get(("index", "read_bytes")) != 1):
        return False
    return True


def _parent_source_writes_before_collection(tool_calls: list[dict[str, Any]],
                                           assignments: list[dict[str, Any]],
                                           manifest: dict[str, Any],
                                           collections: dict[str, list[dict[str, Any]]],
                                           bindings: list[dict[str, Any]],
                                           process_finished: bool,
                                           updates_path: Path,
                                           run_root: Path) -> dict[str, Any]:
    """Detect typed parent writes to owned files before all child returns."""
    caller = manifest.get("paths", {}).get("caller") if isinstance(manifest.get("paths"), dict) else None
    if not isinstance(caller, str):
        return _check("UNKNOWN", "caller root is absent from the manifest")
    caller_root = Path(caller).resolve()
    owned: dict[str, str] = {}
    for item in assignments:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            owned[str((caller_root / item["path"]).resolve())] = "caller"
    by_worker = {str(item.get("worker_id")): item for item in assignments if isinstance(item, dict)}
    for binding in bindings:
        worker = binding.get("worker_id")
        cwd = binding.get("cwd")
        task = by_worker.get(str(worker))
        if isinstance(cwd, str) and isinstance(task, dict) and isinstance(task.get("path"), str):
            root = Path(cwd).resolve()
            owned[str((root / task["path"]).resolve())] = str(worker)
    returned_lines = [item["update_line"] for rows in collections.values() for item in rows
                      if str(item.get("status", "")).lower() not in NONTERMINAL]
    if not returned_lines or any(not rows for rows in collections.values()):
        return _check("INCOMPLETE", "independent parent-source check requires terminal collection for every child",
                      _locator(updates_path))
    last_return = max(returned_lines)
    possible: list[dict[str, Any]] = []
    for row in tool_calls:
        update = row["update"]
        if row["line"] >= last_return:
            continue
        tool = update.get("title")
        raw = update.get("rawInput")
        if not isinstance(raw, dict):
            continue
        if tool in {"write", "search_replace", "edit_file", "write_file", "apply_patch"}:
            paths = [raw.get(key) for key in ("target_file", "path", "file_path", "file")]
            resolved = []
            for value in paths:
                if isinstance(value, str) and value:
                    path = Path(value)
                    resolved.append(str((path if path.is_absolute() else caller_root / path).resolve()))
            if any(path in owned for path in resolved):
                target = next(path for path in resolved if path in owned)
                possible.append({"line": row["line"], "tool": tool, "target": target, "worker_id": owned[target]})
        elif tool == "run_terminal_command":
            command = raw.get("command")
            if not isinstance(command, str):
                continue
            if _safe_parent_calculation(command, run_root.resolve(), caller_root):
                continue
            mentions_owned = any(path in command or str(Path(path).relative_to(caller_root)) in command
                                 for path, worker in owned.items() if worker == "caller")
            if not mentions_owned:
                continue
            mutating = any(marker in command for marker in (" >", ">>", "tee ", "sed -i", "perl -i", "cp ", "mv "))
            mutating = mutating or ("git apply" in command and "--check" not in command)
            possible.append({"line": row["line"], "tool": tool,
                             "classification": "write" if mutating else "unresolved source reference"})
    if possible:
        writes = [item for item in possible if item.get("classification") == "write" or item.get("target")]
        if writes:
            return _check("FAIL", "parent had a typed source-write action before all native child returns", _locator(updates_path)) | {"events": possible}
        return _check("UNKNOWN", "parent referenced an owned source file before all returns in a shell command whose effect is unclear", _locator(updates_path)) | {"events": possible}
    if not process_finished:
        return _check("INCOMPLETE", "no early source write is visible, but the live parent could still act", _locator(updates_path))
    return _check("PASS", "no typed parent source write preceded terminal collection of every child", _locator(updates_path))


def _filesystem_result_context(run: Path) -> dict[str, Any]:
    """Retain filesystem verifier history without folding it into native proof."""
    operator = run / "operator"
    paths = {
        "pre_relocation": operator / "verification-before-plugin-relocate.json",
        "parent_final": operator / "parent-verification.json",
        "final": operator / "verification.json",
        "post_exit": operator / "post-exit-verification.json",
    }
    snapshots: dict[str, Any] = {}
    for name, path in paths.items():
        try:
            record = _read_json(path, f"{name} filesystem verification")
        except (FileNotFoundError, TraceError):
            snapshots[name] = {"available": False, "passed": None, "false_checks": [], "evidence": None}
            continue
        check_values = record.get("checks", {})
        snapshots[name] = {
            "available": True,
            "passed": record.get("passed") if type(record.get("passed")) is bool else None,
            "false_checks": sorted(key for key, value in check_values.items() if value is False)
            if isinstance(check_values, dict) else [],
            "evidence": _locator(path),
        }
    current = snapshots["post_exit"] if snapshots["post_exit"]["available"] else snapshots["final"]
    if not current["available"]:
        current = snapshots["parent_final"]
    historical_failure = any(item["available"] and item["passed"] is False
                             for item in snapshots.values() if item is not current)
    if current["passed"] is False:
        status = "FAIL"
    elif current["passed"] is True:
        status = "RECOVERED" if historical_failure else "PASS"
    elif historical_failure:
        status = "INCOMPLETE_AFTER_FAILURE"
    else:
        status = "INCOMPLETE"
    snapshots["current_precedence"] = {
        "source": next((name for name in ("post_exit", "final", "parent_final")
                         if snapshots[name] is current), None),
        "passed": current["passed"],
    }
    return {"status": status, **snapshots,
            "interpretation": "Latest post-exit/current filesystem evidence takes precedence over earlier recovery; filesystem verification remains separate from native lifecycle evidence."}


def audit_run(run_path: str | Path, *, session_root: str | Path | None = None) -> dict[str, Any]:
    run = Path(run_path).expanduser().resolve()
    operator = run / "operator"
    evidence: dict[str, Any] = {"run": str(run)}
    checks: dict[str, dict[str, Any]] = {}
    metrics: dict[str, Any] = {}
    child_results: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    starts: dict[str, dict[str, Any]] = {}
    finishes: dict[str, dict[str, Any]] = {}
    try:
        manifest_path = run / "manifest.json"
        manifest = _read_json(manifest_path, "fixture manifest")
        evidence["manifest"] = _locator(manifest_path)
        workers = manifest.get("workers")
        assignments = manifest.get("task_assignments")
        if type(workers) is not int or workers not in {3, 5} or not isinstance(assignments, list) or len(assignments) != workers:
            checks["fixture_scope"] = _check("FAIL", "manifest must define exactly three or five workers")
            assignments = []
        elif {str(item.get("worker_id")) for item in assignments if isinstance(item, dict)} != {str(i) for i in range(1, workers + 1)}:
            checks["fixture_scope"] = _check("FAIL", "manifest worker ids must be exactly 1..N")
            assignments = []
        else:
            checks["fixture_scope"] = _check("PASS", f"manifest defines exactly {workers} workers", _locator(manifest_path))
        dispatch_mode = manifest.get("mode")
        if isinstance(dispatch_mode, str) and dispatch_mode in {"parallel", "sequential"}:
            checks["dispatch_mode"] = _check("PASS", f"manifest declares {dispatch_mode} dispatch", _locator(manifest_path))
        else:
            checks["dispatch_mode"] = _check("FAIL", "manifest mode must be exactly 'parallel' or 'sequential'; dispatch order cannot be inferred",
                                             _locator(manifest_path))
        launch_path = operator / "launch.json"
        launch = _read_json(launch_path, "launch record")
        evidence["launch"] = _locator(launch_path)
        session_id = launch.get("session_id")
        cwd = launch.get("cwd")
        expected_cwd = manifest.get("paths", {}).get("caller") if isinstance(manifest.get("paths"), dict) else None
        if not isinstance(session_id, str) or UUID_RE.fullmatch(session_id) is None or not isinstance(cwd, str) or not Path(cwd).is_absolute():
            checks["parent_binding"] = _check("FAIL", "launch record lacks a session id or absolute cwd", _locator(launch_path))
        elif expected_cwd is not None and str(Path(cwd).resolve()) != str(Path(expected_cwd).resolve()):
            checks["parent_binding"] = _check("FAIL", "launched parent cwd differs from fixture caller", _locator(launch_path))
        else:
            checks["parent_binding"] = _check("PASS", "launch session and cwd bind to the fixture caller", _locator(launch_path))
        root_dir = Path(session_root).expanduser().resolve() if session_root else Path.home() / ".grok" / "sessions"
        retained_root = operator / "native-evidence" / "root-updates.jsonl"
        root_session_dir: Path | None = None
        try:
            root_source = _session_updates_path(run, launch, root_dir)
            root_session_dir = root_source.parent.resolve()
        except TraceError:
            if not retained_root.exists():
                raise
            root_source = retained_root
        if not root_source.exists() and retained_root.exists():
            root_source = retained_root
        root_retention = _retain_transcript(root_source, retained_root)
        if root_retention.get("matches_source") is False:
            checks["root_transcript_retention_integrity"] = (
                _check("FAIL", "external root transcript differs from immutable retained evidence",
                       *[item for item in (root_retention.get("source"), root_retention["retained"]) if item])
                | {"source_sha256": root_retention["source_sha256"],
                   "retained_sha256": root_retention["retained_sha256"]}
            )
        updates_path = retained_root
        evidence["native_evidence_retention"] = {"root": root_retention, "children": {}}
        evidence["root_updates"] = _locator(updates_path)
        root_updates = _root_updates(updates_path, session_id)
        observed_path = operator / "observed.jsonl"
        observed = _observed(observed_path)
        evidence["observed_stream"] = _locator(observed_path)
        times = _event_times(observed)
        tool_calls = _updates_for(root_updates, "tool_call")
        spawn_calls = [row for row in tool_calls if row["update"].get("title") == "spawn_subagent"]
        collect_calls = [row for row in tool_calls if row["update"].get("title") == "get_command_or_subagent_output"]
        call_ids = {row["update"].get("toolCallId") for row in tool_calls}
        if not all(isinstance(value, str) and value for value in call_ids):
            raise TraceError("root tool calls contain missing toolCallId values")
        spawned = _updates_for(root_updates, "subagent_spawned")
        finished = _updates_for(root_updates, "subagent_finished")
        expected = workers if type(workers) is int else 0
        if len(spawn_calls) != expected or len(spawned) != expected:
            finished_run = (operator / "process-result.json").is_file()
            missing = len(spawn_calls) < expected or len(spawned) < expected
            count_status = "FAIL" if not missing or finished_run else "INCOMPLETE"
            checks["native_spawn_count"] = _check(count_status, f"expected {expected} launch calls and native spawn receipts; found {len(spawn_calls)} and {len(spawned)}", _locator(updates_path))
        else:
            checks["native_spawn_count"] = _check("PASS", f"exactly {expected} native background spawn candidates and receipts", _locator(updates_path))
        spawn_lines = [row["line"] for row in spawn_calls]
        collection_call_lines = [row["line"] for row in collect_calls]
        if dispatch_mode == "parallel":
            if len(spawn_lines) < expected or not collection_call_lines:
                missing_status = "FAIL" if (operator / "process-result.json").is_file() else "INCOMPLETE"
                checks["parallel_dispatch_order"] = _check(missing_status, "all dispatches and at least one parent collection call are required", _locator(updates_path))
            elif max(spawn_lines) < min(collection_call_lines):
                checks["parallel_dispatch_order"] = _check("PASS", "all native child launch calls precede the first collection call", _locator(updates_path))
            else:
                checks["parallel_dispatch_order"] = _check("FAIL", "a collection call began before all required native children were launched", _locator(updates_path))
        parent_ids = {session_id}
        by_child: dict[str, dict[str, Any]] = {}
        binding_errors: list[str] = []
        for row in spawned:
            update = row["update"]
            child = update.get("subagent_id")
            if not isinstance(child, str) or UUID_RE.fullmatch(child) is None:
                binding_errors.append(f"subagent_spawned at line {row['line']} has no subagent_id")
                continue
            if update.get("parent_session_id") not in parent_ids:
                binding_errors.append(f"subagent_spawned at line {row['line']} has wrong parent session")
                continue
            if update.get("child_session_id") != child:
                binding_errors.append(f"subagent_spawned at line {row['line']} has mismatched child session")
                continue
            if child in by_child:
                binding_errors.append(f"child {child} has duplicate native spawn receipts")
                continue
            description = update.get("description")
            by_child[child] = {"child_session_id": child, "parent_session_id": session_id,
                               "freshness": update.get("effective_context_source"),
                               "description": description,
                               "worker_id": None,
                               "agent_type": update.get("subagent_type"),
                               "duration_ms": None,
                               "spawn_locator": _locator(updates_path, row["line"])}
        if binding_errors:
            checks["parent_child_identity"] = _check("FAIL", "; ".join(binding_errors), _locator(updates_path))
        elif len(by_child) == expected:
            checks["parent_child_identity"] = _check("PASS", "every child id is bound to this exact live parent session", *[item["spawn_locator"] for item in by_child.values()])
        else:
            checks["parent_child_identity"] = _check("INCOMPLETE", "native parent-child bindings are missing", _locator(updates_path))
        fresh_values = [item["freshness"] for item in by_child.values()]
        resume_requested = any(
            isinstance(row["update"].get("rawInput"), dict)
            and row["update"]["rawInput"].get("resume_from") not in (None, "")
            for row in spawn_calls
        )
        if resume_requested:
            checks["fresh_context"] = _check("FAIL", "a typed spawn request supplied resume_from", _locator(updates_path))
        elif len(fresh_values) != expected or any(value is None for value in fresh_values):
            checks["fresh_context"] = _check("UNKNOWN", "effective_context_source is absent for one or more native children", _locator(updates_path))
        elif all(value == "new" for value in fresh_values):
            checks["fresh_context"] = _check("PASS", "all children have effective_context_source=new", _locator(updates_path))
        else:
            checks["fresh_context"] = _check("FAIL", "at least one child used a resumed or non-new context", _locator(updates_path))

        starts, finishes, probe_errors = _probe_records(run, assignments) if assignments else ({}, {}, ["manifest assignments unavailable"])
        launches: list[dict[str, Any]] = []
        launch_issues: list[str] = []
        launch_conflicts: list[str] = []
        for row in spawn_calls:
            update = row["update"]
            raw = update.get("rawInput")
            call_id = update.get("toolCallId")
            if not isinstance(raw, dict):
                launch_issues.append(f"spawn call at line {row['line']} has no rawInput object")
                continue
            cwd_values = [raw.get("cwd")] if raw.get("cwd") is not None else []
            background_values = [raw.get("background")] if raw.get("background") is not None else []
            worker, binding_issue, binding_conflict = _bind_spawn_to_probe(raw, assignments, starts)
            if binding_issue:
                (launch_conflicts if binding_conflict else launch_issues).append(
                    f"spawn call at line {row['line']}: {binding_issue}"
                )
            cwd_value = cwd_values[0] if len(cwd_values) == 1 and isinstance(cwd_values[0], str) else None
            background_value = background_values[0] if len(background_values) == 1 else None
            description = raw.get("description")
            matching_receipts = [entry for entry in by_child.values()
                                 if entry.get("description") == description]
            receipt = matching_receipts[0] if len(matching_receipts) == 1 else None
            child_id = receipt.get("child_session_id") if receipt else None
            launch_item = {"call_id": call_id, "line": row["line"], "child_session_id": child_id,
                           "worker_id": worker, "cwd": str(Path(cwd_value).resolve()) if cwd_value and Path(cwd_value).is_absolute() else None,
                           "description": description, "agent_type": receipt.get("agent_type") if receipt else None,
                           "background": background_value,
                           "evidence": _locator(updates_path, row["line"])}
            launches.append(launch_item)
            if worker is None or cwd_value is None or receipt is None or background_value is None:
                launch_issues.append(f"spawn call at line {row['line']} lacks a uniquely bound assignment, cwd, spawn receipt, or background flag")
            if receipt is not None and worker is not None:
                if receipt.get("worker_id") not in (None, worker):
                    launch_issues.append(f"spawn call at line {row['line']} reuses a native child receipt for another owned path")
                else:
                    receipt["worker_id"] = worker
            if raw.get("resume_from") not in (None, ""):
                launch_issues.append(f"spawn call at line {row['line']} requests a resumed context")
            if raw.get("isolation") == "worktree":
                launch_issues.append(f"spawn call at line {row['line']} requests host-managed worktree isolation")
        for child, binding in by_child.items():
            match = next((item for item in launches if item.get("child_session_id") == child), None)
            if match is None:
                launch_issues.append(f"native child {child} has no typed spawn call result")
                continue
            binding.update({"cwd": match.get("cwd"), "background": match.get("background")})
        child_transcript_check, child_transcripts = _retain_child_transcripts(run, launches, root_dir)
        checks["child_transcript_retention"] = child_transcript_check
        evidence["native_evidence_retention"]["children"] = child_transcripts
        treatment_path = operator / "treatment.json"
        if treatment_path.is_file():
            treatment_record = _read_json(treatment_path, "treatment record")
            checks["fixture_verification_summary"] = _fixture_verification_summary_check(
                run, manifest, launch, treatment_record, root_updates, updates_path
            )
            if treatment_record.get("treatment") == "compact":
                delivery_mode, delivery_contract = _compact_delivery_mode(manifest, treatment_record)
                checks["compact_delivery_mode"] = delivery_contract
                effective_delivery_mode = delivery_mode or "invalid"
                compact_dispatch, compact_dispatch_evidence = _compact_dispatch_check(
                    run, assignments, spawn_calls, starts, root_updates, updates_path
                )
                checks["compact_spawn_arguments"] = compact_dispatch
                evidence["compact_dispatch"] = compact_dispatch_evidence
                checks["compact_parent_return_order"] = _compact_parent_return_check(
                    run, assignments, root_updates, collect_calls, updates_path,
                    delivery_mode=effective_delivery_mode, launches=launches,
                )
        for row in finished:
            update = row["update"]
            child = update.get("subagent_id")
            binding = by_child.get(child) if isinstance(child, str) else None
            duration = update.get("duration_ms")
            if binding is not None:
                binding["finished_locator"] = _locator(updates_path, row["line"])
                binding["finished_status"] = update.get("status")
                binding["duration_ms"] = duration if type(duration) is int and duration >= 0 else None
        type_values = [item.get("agent_type") for item in launches]
        background_values = [item.get("background") for item in launches]
        type_ok = len(launches) == expected and all(value == "general-purpose" for value in type_values)
        background_ok = len(launches) == expected and all(value is True for value in background_values)
        if not type_values or any(value is None for value in type_values):
            checks["general_purpose_background"] = _check("UNKNOWN", "native spawn arguments do not expose a typed agent type", _locator(updates_path))
        elif not type_ok:
            checks["general_purpose_background"] = _check("FAIL", f"spawn agent types were {type_values!r}; expected general-purpose", _locator(updates_path))
        elif not background_values or any(value is None for value in background_values):
            checks["general_purpose_background"] = _check("UNKNOWN", "native spawn arguments do not expose a typed background flag", _locator(updates_path))
        elif not background_ok:
            checks["general_purpose_background"] = _check("FAIL", "one or more native spawns were not background launches", _locator(updates_path))
        else:
            checks["general_purpose_background"] = _check("PASS", "all native launches are general-purpose background workers", *[item["evidence"] for item in launches])
        if launch_issues or launch_conflicts:
            status = "FAIL" if launch_conflicts else "UNKNOWN"
            details = launch_conflicts + launch_issues
            checks["spawn_argument_bindings"] = _check(status, "; ".join(details), _locator(updates_path))
        elif len({item.get("worker_id") for item in launches}) != expected:
            checks["spawn_argument_bindings"] = _check("FAIL", "spawn arguments do not map one-to-one to fixture workers", _locator(updates_path))
        elif len({item.get("cwd") for item in launches}) != expected:
            checks["spawn_argument_bindings"] = _check("FAIL", "native spawn cwd values are not distinct", _locator(updates_path))
        else:
            checks["spawn_argument_bindings"] = _check("PASS", "each typed spawn binds one fixture worker to a distinct cwd", *[item["evidence"] for item in launches])

        packet_check, packet_evidence = _packet_argument_check(
            run, assignments, spawn_calls, starts, root_updates, updates_path, root_session_dir
        )
        if packet_check is not None:
            checks["packet_spawn_arguments"] = packet_check
        if packet_evidence is not None:
            evidence["dispatch_packet"] = packet_evidence

        probe_items: list[dict[str, Any]] = []
        probe_mismatch: list[str] = []
        for worker, item in starts.items():
            record = item["record"]
            probe_items.append({"worker_id": worker, "root": str(Path(record["root"]).resolve()) if isinstance(record.get("root"), str) else None,
                                "path": item["path"]})
        bound_cwds = [item.get("cwd") for item in launches if item.get("cwd")]
        probe_roots = [item.get("root") for item in probe_items if item.get("root")]
        for launch_item in launches:
            worker = launch_item.get("worker_id")
            probe = starts.get(worker) if worker else None
            if probe is None:
                probe_mismatch.append(f"worker {worker or '?'} has no start probe")
            elif launch_item.get("cwd") != str(Path(probe["record"].get("root", "")).resolve()):
                probe_mismatch.append(f"worker {worker} spawn cwd differs from probe root")
        if probe_errors:
            checks["cwd_probe_binding"] = _check("INCOMPLETE", "; ".join(probe_errors), _locator(run / "operator" / "probes"))
        elif probe_mismatch:
            checks["cwd_probe_binding"] = _check("FAIL", "; ".join(probe_mismatch), *[_locator(item["path"]) for item in probe_items])
        elif len(set(bound_cwds)) != expected or len(set(probe_roots)) != expected:
            checks["cwd_probe_binding"] = _check("FAIL", "spawn cwd or child probe roots are not distinct", *[_locator(item["path"]) for item in probe_items])
        else:
            checks["cwd_probe_binding"] = _check("PASS", "each distinct native cwd equals its bound child probe Git root", *[_locator(item["path"]) for item in probe_items])

        if "compact_spawn_arguments" in checks:
            checks["compact_worker_phases"] = _compact_worker_phase_check(
                run, assignments, launches, child_transcripts, updates_path,
                native_cwd_probe_passed=checks["cwd_probe_binding"]["status"] == "PASS",
                delivery_mode=effective_delivery_mode if treatment_path.is_file()
                and treatment_record.get("treatment") == "compact" else "patch",
            )

        collections: dict[str, list[dict[str, Any]]] = {child: [] for child in by_child}
        collection_lines: list[int] = []
        for row in collect_calls:
            update = row["update"]
            raw = update.get("rawInput")
            if not isinstance(raw, dict):
                continue
            requested = raw.get("task_ids", raw.get("taskIds"))
            if not isinstance(requested, list):
                continue
            call_id = update.get("toolCallId")
            terminal = _terminal_update(str(call_id), root_updates) if isinstance(call_id, str) else None
            if terminal is None:
                continue
            output = terminal["update"].get("rawOutput")
            rows = _task_rows(output)
            for result in rows:
                child = _row_id(result)
                if child in collections and child in requested:
                    collections[child].append({"worker_row": result, "call_line": row["line"],
                                               "update_line": terminal["line"], "call_id": call_id,
                                               "status": result.get("status")})
                    collection_lines.append(terminal["line"])
        missing_collection = [child for child, matches in collections.items()
                              if not any(str(item.get("status", "")).lower() not in NONTERMINAL for item in matches)]
        if missing_collection:
            missing_status = "FAIL" if (operator / "process-result.json").is_file() else "INCOMPLETE"
            checks["parent_collected_all_children"] = _check(missing_status, "parent lacks a typed terminal collection for: " + ", ".join(missing_collection), _locator(updates_path))
        else:
            checks["parent_collected_all_children"] = _check("PASS", "same launch-bound parent requested and received a terminal typed row for every native child", _locator(updates_path))
        if len({row["update"]["toolCallId"] for row in collect_calls}) == 0 and by_child:
            checks["collection_parent_identity"] = _check("INCOMPLETE", "no typed parent collection calls were retained", _locator(updates_path))
        else:
            checks["collection_parent_identity"] = _check("PASS", "collection calls are in the exact launch session updates log", _locator(updates_path))

        for item in launches:
            child = item.get("child_session_id")
            terminal_rows = collections.get(child, []) if child else []
            terminal_rows = [result for result in terminal_rows if str(result.get("status", "")).lower() not in NONTERMINAL]
            if terminal_rows:
                item["collection"] = {"status": "COLLECTED", "task_status": terminal_rows[-1].get("status"),
                                       "evidence": _locator(updates_path, terminal_rows[-1]["update_line"])}
            else:
                item["collection"] = {"status": "INCOMPLETE", "task_status": None}

        if dispatch_mode == "sequential":
            transitions: list[dict[str, Any]] = []
            ordering_failures: list[str] = []
            ordering_incomplete: list[str] = []
            ordering_evidence_lines: set[int] = set()
            if expected not in {3, 5} or len(launches) != expected or any(
                not isinstance(item.get("line"), int) or not isinstance(item.get("child_session_id"), str)
                for item in launches
            ):
                detail = "sequential order requires one typed spawn call and child receipt for every manifest worker"
                status = "FAIL" if (operator / "process-result.json").is_file() else "INCOMPLETE"
                checks["sequential_dispatch_order"] = _check(status, detail, _locator(updates_path))
            else:
                for previous, following in zip(launches, launches[1:]):
                    previous_child = previous["child_session_id"]
                    following_line = following["line"]
                    rows = collections.get(previous_child, [])
                    terminal_rows = [
                        item for item in rows
                        if type(item.get("call_line")) is int
                        and type(item.get("update_line")) is int
                        and item["call_line"] < item["update_line"]
                        and str(item.get("status", "")).lower() not in NONTERMINAL
                    ]
                    before_next = [item for item in terminal_rows if item["update_line"] < following_line]
                    if before_next:
                        collected = min(before_next, key=lambda item: item["update_line"])
                        ordering_evidence_lines.update((collected["call_line"], collected["update_line"], following_line))
                        transitions.append({
                            "previous_worker_id": previous.get("worker_id"),
                            "previous_child_session_id": previous_child,
                            "collection_call_line": collected["call_line"],
                            "terminal_collection_line": collected["update_line"],
                            "next_worker_id": following.get("worker_id"),
                            "next_spawn_line": following_line,
                        })
                        continue
                    message = (f"worker {previous.get('worker_id') or '?'} has no typed terminal collection "
                               f"before worker {following.get('worker_id') or '?'} spawn at line {following_line}")
                    ordering_evidence_lines.update((previous["line"], following_line))
                    for item in terminal_rows:
                        ordering_evidence_lines.update((item["call_line"], item["update_line"]))
                    if any(item["update_line"] >= following_line for item in terminal_rows):
                        ordering_failures.append(message)
                    elif (operator / "process-result.json").is_file():
                        ordering_failures.append(message)
                    else:
                        ordering_incomplete.append(message)
                if ordering_failures:
                    checks["sequential_dispatch_order"] = (
                        _check("FAIL", "; ".join(ordering_failures),
                               *[_locator(updates_path, line) for line in sorted(ordering_evidence_lines)])
                        | {"transitions": transitions}
                    )
                elif ordering_incomplete:
                    checks["sequential_dispatch_order"] = (
                        _check("INCOMPLETE", "; ".join(ordering_incomplete),
                               *[_locator(updates_path, line) for line in sorted(ordering_evidence_lines)])
                        | {"transitions": transitions}
                    )
                else:
                    checks["sequential_dispatch_order"] = (
                        _check("PASS", "each previous child has a typed terminal collection before the next native spawn",
                               *[_locator(updates_path, line) for line in sorted(ordering_evidence_lines)])
                        | {"transitions": transitions}
                    )

        # Every typed child id must be accounted for exactly once; generated text is ignored.
        if len(by_child) != expected or len(set(by_child)) != expected:
            checks["no_extra_or_missing_children"] = _check("FAIL" if len(by_child) > expected else "INCOMPLETE",
                                                               f"expected {expected} distinct children, observed {len(by_child)}", _locator(updates_path))
        else:
            checks["no_extra_or_missing_children"] = _check("PASS", f"exactly {expected} distinct native children were spawned", _locator(updates_path))

        # Child-process launch through a shell is an unwanted substitute for the
        # native spawn tool. Check only typed terminal commands in the parent log.
        shell_calls = [row for row in tool_calls if row["update"].get("title") == "run_terminal_command"]
        shell_launches: list[dict[str, Any]] = []
        for row in shell_calls:
            raw = row["update"].get("rawInput")
            command = raw.get("command") if isinstance(raw, dict) else None
            if isinstance(command, str):
                lowered = command.lower()
                if any(token in lowered for token in ("grok run", "grok --", "claude -p", "codex exec", "spawn_subagent")):
                    shell_launches.append({"line": row["line"], "command": command[:240]})
        if shell_launches:
            checks["no_shell_child_launch"] = _check("FAIL", f"found {len(shell_launches)} shell commands that appear to launch agents", _locator(updates_path))
        else:
            checks["no_shell_child_launch"] = _check("PASS", "no typed parent shell command uses a recognized child-agent launcher", _locator(updates_path))

        bindings = list(by_child.values())
        source_check, child_results = _check_source_work(run, manifest, assignments, starts, finishes, bindings)
        checks["independent_child_source_changes"] = source_check
        evidence["child_source_results"] = child_results
        evidence["native_launches"] = launches
        evidence["native_bindings"] = list(by_child.values())
        evidence["child_returns"] = {
            child: [{"task_id": item["worker_row"].get("task_id"),
                     "status": item["worker_row"].get("status"),
                     "exit_code": item["worker_row"].get("exit_code"),
                     "evidence": _locator(updates_path, item["update_line"])}
                    for item in rows]
            for child, rows in collections.items()
        }
        evidence["child_finished_event_count"] = len(finished)
        evidence["probe_files"] = [_locator(item["path"]) for item in probe_items]
        evidence["probe_errors"] = probe_errors

        launch_times: list[dict[str, Any]] = []
        for item in launches:
            candidates = times.get(("tool_call", item.get("call_id")), [])
            if len(candidates) == 1:
                event = candidates[0]["event"]
                if event.get("type") == "tool_call" and event.get("toolCallId") == item.get("call_id"):
                    launch_times.append({"worker_id": item.get("worker_id"), "child_session_id": item.get("child_session_id"),
                                         "call_id": item.get("call_id"), "epoch": candidates[0]["epoch"], "elapsed_s": candidates[0]["elapsed"],
                                         "evidence": _locator(observed_path, candidates[0]["line"])})
        if len(launch_times) == expected:
            first = min(launch_times, key=lambda row: row["epoch"])
            last = max(launch_times, key=lambda row: row["epoch"])
            metrics["start_to_first_launch_s"] = max(0.0, first["epoch"] - float(launch.get("started_epoch", first["epoch"])))
            metrics["launch_spread_s"] = max(0.0, last["epoch"] - first["epoch"])
            metrics["launch_times"] = launch_times
        else:
            metrics["start_to_first_launch_s"] = None
            metrics["launch_spread_s"] = None
            metrics["launch_timing_status"] = "UNKNOWN: typed observed times could not be joined to every native spawn call"
        finished_by_child: dict[str, dict[str, Any]] = {}
        for row in finished:
            update = row["update"]
            child = update.get("subagent_id")
            if isinstance(child, str):
                if child in finished_by_child:
                    finished_by_child[child] = {"duplicate": True}
                else:
                    finished_by_child[child] = {"status": update.get("status"),
                                                "duration_ms": update.get("duration_ms"),
                                                "tool_calls": update.get("tool_calls"),
                                                "turns": update.get("turns"),
                                                "locator": _locator(updates_path, row["line"])}
        missing_finished = sorted(set(by_child).difference(finished_by_child))
        extra_finished = sorted(set(finished_by_child).difference(by_child))
        duplicate_finished = sorted(child for child, value in finished_by_child.items() if value.get("duplicate"))
        if missing_finished:
            missing_status = "FAIL" if (operator / "process-result.json").is_file() else "INCOMPLETE"
            checks["native_child_finished"] = _check(missing_status, "missing native child finish events for: " + ", ".join(missing_finished), _locator(updates_path))
        elif extra_finished or duplicate_finished:
            checks["native_child_finished"] = _check("FAIL", "native finish events include extra or duplicate child identities", _locator(updates_path))
        elif any(finished_by_child[child].get("status") != "completed" for child in by_child):
            checks["native_child_finished"] = _check("FAIL", "one or more native children did not finish completed", _locator(updates_path))
        else:
            checks["native_child_finished"] = _check("PASS", "every bound native child has one completed finish event", *[finished_by_child[child]["locator"] for child in by_child])
        child_return_failures = []
        for child, rows in collections.items():
            terminal_rows = [item["worker_row"] for item in rows
                             if str(item.get("status", "")).lower() not in NONTERMINAL]
            if terminal_rows and not any(row.get("status") == "completed"
                                         and type(row.get("exit_code")) is int
                                         and row.get("exit_code") == 0 for row in terminal_rows):
                child_return_failures.append(child)
        if child_return_failures:
            checks["child_return_success"] = _check("FAIL", "terminal collection did not report completed exit_code 0 for: " + ", ".join(child_return_failures), _locator(updates_path))
        elif missing_collection:
            missing_status = "FAIL" if (operator / "process-result.json").is_file() else "INCOMPLETE"
            checks["child_return_success"] = _check(missing_status, "successful terminal collection evidence is missing", _locator(updates_path))
        else:
            checks["child_return_success"] = _check("PASS", "every collected child reports completed exit_code 0", _locator(updates_path))

        checks["parent_independent_source_work"] = _parent_source_writes_before_collection(
            tool_calls, assignments, manifest, collections, bindings,
            (operator / "process-result.json").is_file(), updates_path, run,
        )
        child_spans: dict[str, Any] = {}
        for item in launches:
            collected = item.get("collection", {})
            launch_row = next((row for row in launch_times if row.get("call_id") == item.get("call_id")), None)
            observed_return = None
            if collected.get("evidence"):
                line = collected["evidence"].get("line")
                # Root-log line numbers are intentionally not treated as observed
                # stream line numbers; the raw call id is the only valid join key.
                call_id = None
                for col in collect_calls:
                    cid = col["update"].get("toolCallId")
                    if isinstance(cid, str) and _terminal_update(cid, root_updates):
                        term = _terminal_update(cid, root_updates)
                        if term and term["line"] == line:
                            call_id = cid
                            break
                if call_id:
                    values = times.get(("tool_call_update", call_id), [])
                    if values:
                        observed_return = values[-1]
            start_row = next((row for row in launch_times if row.get("call_id") == item.get("call_id")), None)
            child = item.get("child_session_id")
            finished_event = finished_by_child.get(child, {}) if isinstance(child, str) else {}
            child_spans[child or str(item.get("worker_id"))] = {
                "status": "OBSERVED" if type(finished_event.get("duration_ms")) is int else "UNKNOWN",
                "duration_ms": finished_event.get("duration_ms") if type(finished_event.get("duration_ms")) is int else None,
                "native_status": finished_event.get("status"),
                "native_tool_calls": finished_event.get("tool_calls") if type(finished_event.get("tool_calls")) is int else None,
                "native_turns": finished_event.get("turns") if type(finished_event.get("turns")) is int else None,
                "spawn_to_collection_s": max(0.0, observed_return["epoch"] - start_row["epoch"])
                if start_row is not None and observed_return is not None else None,
                "evidence": [entry for entry in (item.get("evidence"), finished_event.get("locator"),
                                                  _locator(observed_path, observed_return["line"]) if observed_return else None) if entry],
                "interpretation": "native duration_ms is host child span; spawn_to_collection_s also includes queue and parent delay",
            }
        metrics["native_child_spans"] = child_spans
        end_events = [row for row in observed if row["event"].get("type") == "end"]
        process_path = operator / "process-result.json"
        if process_path.exists():
            process_result = _read_json(process_path, "parent process result")
            evidence["process_result"] = _locator(process_path)
            code = process_result.get("exit_code")
            if type(code) is int and code == 0 and len(end_events) == 1 and end_events[0]["event"].get("stopReason") == "end_turn":
                checks["parent_terminal"] = _check("PASS", "launch-bound parent process exited zero after one end_turn event", _locator(process_path), _locator(observed_path, end_events[0]["line"]))
            elif len(end_events) == 0:
                checks["parent_terminal"] = _check("FAIL", "process exited but no typed parent end event was captured", _locator(process_path), _locator(observed_path))
            else:
                checks["parent_terminal"] = _check("FAIL", "parent process or typed terminal event does not establish success", _locator(process_path), _locator(observed_path))
            if len(end_events) == 1:
                after_end = [row for row in observed[end_events[0]["line"]:]
                             if row["event"].get("type") in {"tool_call", "tool_call_update"}]
                if after_end:
                    checks["no_parent_tool_activity_after_end"] = _check("FAIL", "typed tool activity appears after the parent end event", _locator(observed_path, after_end[0]["line"]))
                else:
                    checks["no_parent_tool_activity_after_end"] = _check("PASS", "no typed tool activity follows the parent end event", _locator(observed_path, end_events[0]["line"]))
            finished_epoch = _finite_number(process_result.get("finished_epoch"))
            returns = [row for row in observed if row["event"].get("type") == "tool_call_update"
                       and row["event"].get("status") == "completed"
                       and isinstance(row["event"].get("rawOutput"), dict)
                       and row["event"]["rawOutput"].get("type") == "TaskOutput"
                       and isinstance(row["event"].get("toolCallId"), str)
                       and any(item.get("collection", {}).get("status") == "COLLECTED"
                               and any(col["update"].get("toolCallId") == row["event"].get("toolCallId") for col in collect_calls)
                               for item in launches)]
            if finished_epoch is not None and returns:
                last_return = max(returns, key=lambda row: row["epoch"])
                metrics["final_return_to_end_s"] = max(0.0, finished_epoch - last_return["epoch"])
                metrics["final_return_to_end_evidence"] = [_locator(observed_path, last_return["line"]), _locator(process_path)]
            else:
                metrics["final_return_to_end_s"] = None
                metrics["final_return_to_end_status"] = "UNKNOWN: final typed collection receipt or process end time is absent"
        else:
            checks["parent_terminal"] = _check("INCOMPLETE", "parent has not exited or process-result.json is missing", _locator(operator))
            metrics["final_return_to_end_s"] = None
            metrics["final_return_to_end_status"] = "INCOMPLETE: parent process has not ended"
        metrics["tool_counts"] = {name: sum(1 for row in tool_calls if row["update"].get("title") == name)
                                   for name in sorted({row["update"].get("title") for row in tool_calls if isinstance(row["update"].get("title"), str)})}
        metrics["native_tool_call_count"] = len(tool_calls)
        metrics["spawn_receipt_count"] = len(spawned)
        metrics["collection_call_count"] = len(collect_calls)
        metrics["native_child_tool_call_count"] = sum(
            value["native_tool_calls"] for value in child_spans.values()
            if type(value.get("native_tool_calls")) is int
        )
        metrics["child_probe_overlap"] = _probe_overlap(starts, bindings)
        metrics["child_task_work_overlap"] = _probe_work_overlap(starts, finishes, bindings, manifest.get("run_id"))

    except FileNotFoundError as exc:
        checks.setdefault("evidence_available", _check("INCOMPLETE", f"required evidence file is missing: {exc.filename}"))
    except TraceError as exc:
        checks.setdefault("evidence_valid", _check("FAIL", str(exc)))
    except (KeyError, TypeError, ValueError) as exc:
        checks.setdefault("evidence_valid", _check("UNKNOWN", f"unsupported or incomplete evidence schema: {type(exc).__name__}: {exc}"))
    native_status = _overall(checks) if checks else "INCOMPLETE"
    filesystem_context = _filesystem_result_context(run)
    component_statuses = {native_status, filesystem_context["status"]}
    if "FAIL" in component_statuses:
        combined = "FAIL"
    elif "INCOMPLETE" in component_statuses or "INCOMPLETE_AFTER_FAILURE" in component_statuses:
        combined = "INCOMPLETE"
    elif "UNKNOWN" in component_statuses or "UNKNOWN_FINAL_ONLY" in component_statuses:
        combined = "UNKNOWN"
    elif "RECOVERED" in component_statuses:
        combined = "RECOVERED"
    else:
        combined = "PASS"
    auditor_path = Path(__file__).resolve()
    auditor_identity = {
        "path": str(auditor_path),
        "sha256": hashlib.sha256(auditor_path.read_bytes()).hexdigest(),
        "scope": "post-hoc auditor implementation used for this report; launch-time implementation is not inferred",
    }
    return {"schema": SCHEMA, "status": combined, "passed": combined == "PASS",
            "native_status": native_status, "native_passed": native_status == "PASS",
            "auditor_implementation": auditor_identity,
            "combined_classification": combined, "checks": checks,
            "metrics": metrics, "evidence": evidence,
            "filesystem_result_context": filesystem_context,
            "limitations": ["Hold overlap uses only explicit hold intervals; task-work overlap uses recorded child start-to-finish intervals and is not CPU concurrency.",
                            "Filesystem fixture verification is independent and is not inferred from native returns.",
                            "Child narrative text is never used as success evidence."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.run.expanduser().resolve() / "operator" / "native-verification.json"
    report = audit_run(args.run)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if output.exists():
        previous = output.read_bytes()
        if previous != serialized:
            history_dir = output.parent / "audit-history"
            history_dir.mkdir(parents=True, exist_ok=True)
            previous_sha = hashlib.sha256(previous).hexdigest()
            history = history_dir / f"native-verification.{previous_sha}.json"
            if not history.exists():
                history.write_bytes(previous)
    output.write_bytes(serialized)
    print(json.dumps({"status": report["status"], "passed": report["passed"], "output": str(output)}, sort_keys=True))
    records=report_check_diagnostics(report,output,phase='native-audit')
    if not report['passed'] and not records:
        records=[make_diagnostic(code='RUN_NOT_ACCEPTED',severity='error',phase='native-audit',
            expected='Both native lifecycle and post-exit filesystem evidence pass',
            observed={'native':report['native_status'],'filesystem':report['filesystem_result_context']},
            rationale='Successful child returns cannot override failed or absent final filesystem evidence.',
            rationale_ref='CONTRACT.md#proof-precedence',evidence=[evidence_reference(output)],
            recovery='Inspect the final filesystem report and native checks; retain earlier reports.',
            retry_safety='Read-only re-audit is allowed; a new model attempt needs a new run.')]
    emit_diagnostics(records,jsonl_path=output.with_suffix('.diagnostics.jsonl'))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
