#!/usr/bin/env python3
"""Collect anonymized, evidence-first dossiers from completed capability trials.

The study directory is private.  This utility deliberately keeps the public-to-a-
grader surface small: ``private/blind`` contains opaque dossier IDs and sanitized
evidence, while ``private/blind-map.json`` is the only arm-to-ID map.  It never
reads prompts and never copies packet/common-instruction or skill-body material.

Run repeatedly as arms finish.  A completed runner metadata receipt is sufficient
to collect a failed or incomplete worker outcome; a worker exit code of zero is
not required.
"""

from __future__ import annotations

import argparse
import dataclasses
import getpass
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "shiploop-capability-blind-bundle-v1"
SUPPLEMENT_SCHEMA = "shiploop-capability-blind-receipt-supplement-v1"
SUPPLEMENT_VERSION = 1
MAX_TEXT_BYTES = 64 * 1024
ALLOWED_CASES = {"ENV", "OUTER", "OUTER_HOLDOUT", "GAS"}
TIMING_CASES = {"ENV": "TIMING_STABLE", "OUTER_HOLDOUT": "TIMING_CHANGED"}
COMMON_INSTRUCTION_BASENAMES = {
    "agents.md",
    "capabilities.md",
    "case.md",
    "coordinator.md",
    "packet.md",
    "platform_tools.json",
    "preregistration.md",
    "prompt.md",
    "prompt2.md",
    "readme.md",
    "spec.md",
}
EXCLUDED_TEXT_NEEDLES = (
    "prompt.md",
    "prompt2.md",
    "skill.md",
    "skills/",
    "shiploop/",
    "shiploop-state",
    "packet.md",
    "case.md",
    "spec.md",
    "readme.md",
    "capabilities.md",
    "platform_tools.json",
)
SENSITIVE_KEY_PARTS = (
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
    "scriptid",
    "script_id",
    "deploymentid",
    "deployment_id",
    "projectid",
    "project_id",
    "spreadsheetid",
    "spreadsheet_id",
    "drivefileid",
    "drive_file_id",
)
UNTRUSTED_BODY_KEYS = {
    "argv", "code", "command", "content", "input", "message", "output", "prompt", "script", "stderr", "stdout", "text",
}
USAGE_TELEMETRY_KEYS = {"input_tokens", "output_tokens", "cached_input_tokens"}
# ``1...`` is also a common prefix for an ordinary SHA-256 digest.  Exact
# selected IDs come from keyed workspace configuration; only the distinctive
# Apps Script deployment form is safe to redact by pattern alone.
SCRIPT_ID_RE = re.compile(r"\bAKfy[A-Za-z0-9_-]{16,}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
LINE_REFERENCE_RE = re.compile(r":\d+(?::\d+)?$")
PATH_TOKEN_RE = re.compile(
    r"(?<![\w/])(?:/?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:jsonl?|txt|log|md|py|html))(?:\:\d+(?:\:\d+)?)?"
)
MARKDOWN_LINK_RE = re.compile(r"\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
TOOL_ITEM_TYPES = {"mcp_tool_call", "command_execution", "exec_command", "write_stdin", "apply_patch", "file_change"}
RESULT_METADATA_KEYS = (
    "bytes", "call", "elapsed_seconds", "exit_code", "phase", "timed_out", "truncated",
    "input_tokens", "output_tokens", "cached_input_tokens",
)
SERVICE_HTTP_RECEIPT_FILE = "service-http-receipts.jsonl"
SERVICE_HTTP_RECEIPT_KEYS = {
    "event", "receipt_id", "method", "route", "actor_class", "status", "error", "version_before", "version_after",
}
SERVICE_HTTP_METHODS = {"GET", "POST"}
SERVICE_HTTP_ROUTES = {"/", "/api/state", "/api/meta", "/api/move", "other"}
SERVICE_HTTP_ACTORS = {"red", "black", "invalid"}
SERVICE_HTTP_STATUSES = {200, 400, 403, 404, 405, 409, 422, 500}
SERVICE_HTTP_ERRORS = {
    "invalid_json", "invalid_actor", "invalid_expected_version", "invalid_idempotency_key", "invalid_coordinate",
    "unplayable_square", "mutation_token_required", "invalid_token", "scope_required", "actor_mismatch",
    "not_your_turn", "source_not_owned", "target_occupied", "illegal_move", "capture_required",
    "forced_capture_origin", "idempotency_conflict", "version_mismatch", "not_found", "method_not_allowed",
    "internal_error",
}
RECEIPT_ID_RE = re.compile(r"^http-[0-9]{6,}$")


class CollectionError(RuntimeError):
    """A source could not be collected without concealing the failure."""


@dataclasses.dataclass(frozen=True)
class ArmSource:
    arm_dir: Path
    workspace: Path
    run: Path
    metadata: dict[str, Any]
    case_type: str
    input_manifest: dict[str, Any]


@dataclasses.dataclass
class BuiltDossier:
    dossier_id: str
    case_type: str
    dossier: dict[str, Any]
    evidence: list[tuple[str, dict[str, Any]]]
    private_map: dict[str, Any]
    errors: list[str]
    redacted_values: set[str]


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise CollectionError(f"cannot read {label}: {error.__class__.__name__}: {error}") from error
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CollectionError(f"cannot parse {label}: JSON decode error at line {error.lineno}") from error
    if not isinstance(value, dict):
        raise CollectionError(f"cannot use {label}: expected a JSON object")
    return value


def read_text(path: Path, *, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise CollectionError(f"cannot read {label}: {error.__class__.__name__}: {error}") from error


def is_completed_metadata(metadata: dict[str, Any]) -> bool:
    status = str(metadata.get("status", "")).lower()
    return bool(metadata.get("finished_at")) or status in {"completed", "complete", "finished"} or isinstance(metadata.get("contexts"), list)


def derive_case_type(arm_dir: Path, manifest: dict[str, Any]) -> str | None:
    raw_case = manifest.get("case")
    style = manifest.get("style")
    arm_name = arm_dir.name.lower()
    if style == "timing" or arm_name.startswith("timing-"):
        if raw_case in TIMING_CASES:
            return TIMING_CASES[raw_case]
        if "env" in arm_name:
            return "TIMING_STABLE"
        if "outer_holdout" in arm_name or "holdout" in arm_name:
            return "TIMING_CHANGED"
        return None
    if raw_case in ALLOWED_CASES:
        return str(raw_case)
    if "gas" in arm_name:
        return "GAS"
    if "outer_holdout" in arm_name or "holdout" in arm_name:
        return "OUTER_HOLDOUT"
    if "outer" in arm_name:
        return "OUTER"
    if "env" in arm_name:
        return "ENV"
    return None


def source_arms(study: Path) -> tuple[list[ArmSource], list[str]]:
    arms_root = study / "arms"
    if not arms_root.is_dir():
        raise CollectionError("study has no readable arms directory")
    sources: list[ArmSource] = []
    errors: list[str] = []
    for arm_dir in sorted(path for path in arms_root.iterdir() if path.is_dir()):
        run = arm_dir / "run"
        metadata_path = run / "metadata.json"
        if not metadata_path.is_file():
            continue
        try:
            metadata = read_json(metadata_path, label="runner metadata")
        except CollectionError as error:
            errors.append(f"{arm_dir.name}: {error}")
            continue
        if not is_completed_metadata(metadata):
            continue
        manifest_path = arm_dir / "input-manifest.json"
        try:
            manifest = read_json(manifest_path, label="input manifest") if manifest_path.is_file() else {}
        except CollectionError as error:
            errors.append(f"{arm_dir.name}: {error}")
            continue
        case_type = derive_case_type(arm_dir, manifest)
        if case_type is None:
            continue
        workspace = arm_dir / "workspace"
        if not workspace.is_dir():
            errors.append(f"{arm_dir.name}: completed runner metadata has no readable workspace")
            continue
        sources.append(ArmSource(arm_dir, workspace, run, metadata, case_type, manifest))
    return sources, errors


def is_instruction_path(raw_path: str) -> bool:
    normalized = raw_path.replace("\\", "/").strip().lower()
    if not normalized:
        return False
    parts = [part for part in normalized.split("/") if part]
    basename = parts[-1] if parts else normalized
    if basename in COMMON_INSTRUCTION_BASENAMES or basename == "skill.md":
        return True
    return any(part in {"skills", "shiploop", "shiploop-state"} for part in parts)


def command_mentions_excluded_material(arguments: Any) -> bool:
    try:
        text = json.dumps(arguments, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        text = str(arguments).lower()
    return any(needle in text for needle in EXCLUDED_TEXT_NEEDLES)


def result_text(item: dict[str, Any]) -> str:
    try:
        return json.dumps({"error": item.get("error"), "result": item.get("result")}, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(item.get("error")) + " " + str(item.get("result"))


def is_private_cli_failure(item: dict[str, Any]) -> bool:
    text = result_text(item).lower()
    return "operation not permitted" in text and "/private" in text


def item_failed(item: dict[str, Any]) -> bool:
    if item.get("error") not in (None, ""):
        return True
    return str(item.get("status", "")).lower() in {"failed", "error", "cancelled"}


def item_status(item: dict[str, Any]) -> str:
    status = item.get("status")
    if isinstance(status, str) and status:
        return status
    return "failed" if item_failed(item) else "completed"


def path_basename(raw_path: Any) -> str | None:
    if not isinstance(raw_path, str) or not raw_path:
        return None
    basename = Path(raw_path.replace("\\", "/")).name
    return basename or None


def decoded_result_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Return structured result metadata without returning any result body."""
    result = item.get("result")
    if not isinstance(result, dict):
        return {}
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    content = result.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                continue
            try:
                decoded = json.loads(block["text"])
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
    return result


def result_metadata(item: dict[str, Any], *, redactor: Redactor, include_result_path: bool = True) -> dict[str, Any]:
    payload = decoded_result_payload(item)
    metadata: dict[str, Any] = {}
    for key in RESULT_METADATA_KEYS:
        if key not in payload:
            continue
        value = payload[key]
        if value is None or isinstance(value, (str, int, float, bool)):
            metadata[key] = redactor.value(value, key=key)
    result_path = path_basename(payload.get("path"))
    if include_result_path and result_path is not None:
        metadata["result_path_basename"] = redactor.text(result_path)
    return metadata


def worker_document_basename(raw_path: Any) -> str | None:
    basename = path_basename(raw_path)
    if basename is None:
        return None
    if basename.lower() in {"report.md", "phase1_note.md"}:
        return basename
    return None


def command_argv(arguments: dict[str, Any]) -> list[str]:
    argv = arguments.get("argv")
    if isinstance(argv, list):
        return [str(value) for value in argv]
    if isinstance(argv, str):
        return [argv]
    return []


def argv_metadata(arguments: dict[str, Any]) -> dict[str, Any]:
    metadata = arguments.get("argv_metadata")
    if not isinstance(metadata, dict):
        return {}
    output: dict[str, Any] = {}
    path = metadata.get("execution_path")
    if path in {"direct_cli", "python_wrapper_cli", "opaque_argv"}:
        output["execution_path"] = path
    verb = metadata.get("cli_verb")
    if isinstance(verb, str) and verb in {"next", "complete", "resume", "pause", "status"}:
        output["cli_verb"] = verb
    argc = metadata.get("argc")
    if isinstance(argc, int) and not isinstance(argc, bool) and 0 <= argc <= 64:
        output["argc"] = argc
    return output


def cli_execution_metadata(arguments: dict[str, Any]) -> dict[str, Any]:
    """Classify a direct or opaque Python wrapper without retaining argv/code."""
    metadata = argv_metadata(arguments)
    if metadata.get("execution_path") in {"direct_cli", "python_wrapper_cli"}:
        return metadata
    argv = command_argv(arguments)
    for index, value in enumerate(argv):
        if path_basename(value) != "shiploop":
            continue
        output: dict[str, Any] = {"execution_path": "direct_cli", "argc": len(argv)}
        for candidate in argv[index + 1 :]:
            verb = candidate.lower()
            if verb in {"next", "complete", "done", "resume", "pause", "status"}:
                output["cli_verb"] = "complete" if verb == "done" else verb
                break
        return output
    if argv and path_basename(argv[0]).lower().startswith("python") and "-c" in argv:
        code_index = argv.index("-c") + 1
        code = argv[code_index] if code_index < len(argv) else ""
        if "shiploop" in code.lower():
            output = {"execution_path": "python_wrapper_cli", "argc": len(argv)}
            matched = re.search(r"\b(next|complete|done|resume|pause|status)\b", code, flags=re.IGNORECASE)
            if matched:
                output["cli_verb"] = "complete" if matched.group(1).lower() == "done" else matched.group(1).lower()
            return output
    return {}


def normalized_cli_result(item: dict[str, Any], *, redactor: Redactor) -> dict[str, Any]:
    """Keep process metadata while refusing to infer acceptance from stdout."""
    return {
        "packet_body_omitted": True,
        "result_metadata": result_metadata(item, redactor=redactor),
        "acceptance_basis": "not_established_by_command_receipt",
    }


def operation_metadata(arguments: dict[str, Any]) -> dict[str, Any]:
    """Retain only body-free operation details that an auditor can interpret."""
    metadata: dict[str, Any] = {}
    path = arguments.get("path")
    basename = path_basename(path)
    if basename is None:
        supplied = arguments.get("path_basename")
        basename = supplied if isinstance(supplied, str) else None
    if basename is not None:
        metadata["path_basename"] = basename
    argv = argv_metadata(arguments)
    if argv:
        metadata["argv"] = argv
    timeout = arguments.get("timeout_seconds")
    if isinstance(timeout, int) and not isinstance(timeout, bool):
        metadata["timeout_seconds"] = timeout
    return metadata


def command_mentions_worker_document(arguments: dict[str, Any]) -> list[str]:
    try:
        text = json.dumps(arguments, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        text = str(arguments).lower()
    return [name for name in ("PHASE1_NOTE.md", "REPORT.md") if name.lower() in text]


def is_excluded_instruction_access(arguments: dict[str, Any]) -> bool:
    raw_path = arguments.get("path")
    return is_instruction_path(raw_path if isinstance(raw_path, str) else "") or command_mentions_excluded_material(arguments)


def result_mentions_excluded_material(item: dict[str, Any]) -> bool:
    payload = decoded_result_payload(item)
    values: list[str] = []
    for key in ("stdout", "stderr", "text"):
        value = payload.get(key)
        if isinstance(value, str):
            values.append(value)
    result = item.get("result")
    content = result.get("content") if isinstance(result, dict) else None
    if isinstance(content, list):
        values.extend(block["text"] for block in content if isinstance(block, dict) and isinstance(block.get("text"), str))
    return any(any(needle in value.lower() for needle in EXCLUDED_TEXT_NEEDLES) for value in values)


def item_has_excluded_instruction_access(item: dict[str, Any], arguments: dict[str, Any]) -> bool:
    return is_excluded_instruction_access(arguments) or result_mentions_excluded_material(item)


class Redactor:
    def __init__(self, study: Path, arm_names: Iterable[str], workspace: Path, extra_private_files: Iterable[Path] = ()) -> None:
        self.study = study.resolve(strict=False)
        self.workspace = workspace.resolve(strict=False)
        self.arm_names = sorted({name for name in arm_names if name}, key=len, reverse=True)
        self.usernames = {name for name in (getpass.getuser(), os.environ.get("USER", "")) if name}
        self.extra_private_files = tuple(extra_private_files)
        self.sensitive_values = self._collect_local_sensitive_values()

    def _collect_local_sensitive_values(self) -> set[str]:
        values: set[str] = set()
        paths: list[Path] = []
        for raw_root, directories, filenames in os.walk(self.workspace):
            directories[:] = sorted(
                name for name in directories if name not in {"vendor", "skills", "shiploop", "node_modules", "__pycache__"}
            )
            paths.extend(Path(raw_root) / name for name in sorted(filenames) if name.endswith(".json"))
        paths.extend(path for path in self.extra_private_files if path.suffix.lower() == ".json")
        for path in paths:
            try:
                if path.stat().st_size > 512 * 1024:
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            values.update(self._sensitive_values_in(data))
        return {value for value in values if len(value) >= 8}

    def _sensitive_values_in(self, value: Any, parent_key: str = "") -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, child in value.items():
                found.update(self._sensitive_values_in(child, str(key)))
        elif isinstance(value, list):
            for child in value:
                found.update(self._sensitive_values_in(child, parent_key))
        elif isinstance(value, str) and self.is_sensitive_key(parent_key):
            found.add(value)
        return found

    @staticmethod
    def is_sensitive_key(key: str) -> bool:
        lowered = key.lower().replace("-", "_")
        if lowered in USAGE_TELEMETRY_KEYS:
            return False
        return any(part in lowered for part in SENSITIVE_KEY_PARTS)

    def text(self, value: str) -> str:
        text = value
        for original, replacement in ((str(self.workspace), "<workspace>"), (str(self.study), "<study>")):
            if original:
                text = text.replace(original, replacement)
        for arm_name in self.arm_names:
            text = text.replace(arm_name, "<arm>")
        for username in self.usernames:
            text = re.sub(re.escape(username), "<user>", text, flags=re.IGNORECASE)
        for sensitive in sorted(self.sensitive_values, key=len, reverse=True):
            text = text.replace(sensitive, "<redacted>")
        text = SCRIPT_ID_RE.sub("<redacted-script-id>", text)
        text = EMAIL_RE.sub("<redacted-email>", text)
        text = re.sub(r"https?://127\.0\.0\.1(?::\d+)?", "<loopback-service>", text)
        text = re.sub(r"/(?:private/)?var/folders/[^\s`'\"\])}]+", "<private-path>", text)
        text = re.sub(r"/Users/[^\s`'\"\])}]+", "<user-path>", text)
        text = re.sub(r"/tmp/[^\s`'\"\])}]+", "<temp-path>", text)
        text = re.sub(r"\b(?:candidate|current)\b", lambda match: "proposed" if match.group(0).lower() == "candidate" else "observed", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:mutant|oracle)\b", "<excluded-evaluator>", text, flags=re.IGNORECASE)
        return text

    def bounded(self, text: str) -> str | dict[str, Any]:
        encoded = text.encode("utf-8")
        if len(encoded) <= MAX_TEXT_BYTES:
            return text
        half = MAX_TEXT_BYTES // 2
        # Slice characters rather than bytes so JSON remains valid UTF-8.
        head = text[:half]
        tail = text[-half:]
        return {
            "text": head + "\n… <content truncated by blind collector> …\n" + tail,
            "truncated": True,
            "original_utf8_bytes": len(encoded),
            "sanitized_content_sha256": sha256_text(text),
        }

    def value(self, value: Any, *, key: str = "") -> Any:
        if self.is_sensitive_key(key):
            return "<redacted>"
        if isinstance(value, dict):
            return {self.text(str(name)): self.value(child, key=str(name)) for name, child in value.items()}
        if isinstance(value, list):
            return [self.value(child, key=key) for child in value]
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(("{", "[")) and len(value) <= 1024 * 1024:
                try:
                    parsed = json.loads(value)
                except json.JSONDecodeError:
                    pass
                else:
                    return self.bounded(stable_json(self.value(parsed)).rstrip("\n"))
            if key.lower() in UNTRUSTED_BODY_KEYS:
                return "<omitted-untrusted-body>"
            return self.bounded(self.text(value))
        return value

    def document(self, text: str) -> str | dict[str, Any]:
        kept: list[str] = []
        omitted_section_level: int | None = None
        did_emit_omission = False
        for line in text.splitlines(keepends=True):
            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                level = len(heading.group(1))
                title = heading.group(2).lower()
                if omitted_section_level is not None and level <= omitted_section_level:
                    omitted_section_level = None
                if any(word in title for word in ("procedure", "skill", "local guidance")):
                    omitted_section_level = level
                    if not did_emit_omission:
                        kept.append("\n[Procedure and common-instruction material excluded from this blind dossier.]\n")
                        did_emit_omission = True
                    continue
            if omitted_section_level is not None:
                continue
            lowered = line.lower()
            if any(
                token in lowered
                for token in (
                    "prompt.md",
                    "prompt2.md",
                    "candidate checkpoint instruction",
                    "public cli packet",
                    "skill.md",
                    "skills/",
                    "shiploop/",
                )
            ):
                if not did_emit_omission:
                    kept.append("\n[Procedure and common-instruction material excluded from this blind dossier.]\n")
                    did_emit_omission = True
                continue
            kept.append(line)
        return self.bounded(self.text("".join(kept)))


def shared_ledger_bounds(metadata: dict[str, Any], redactor: Redactor) -> dict[str, Any]:
    ledger = metadata.get("gateway_ledger")
    ledger_bounds: dict[str, Any] = {}
    if isinstance(ledger, dict):
        ledger_bounds = {
            key: ledger.get(key)
            for key in ("version", "call_limit", "exploration_limit", "tool_calls")
            if key in ledger
        }
    observed = metadata.get("observed_actions")
    observed_bounds: dict[str, Any] = {}
    if isinstance(observed, dict):
        observed_bounds = {
            key: observed.get(key)
            for key in ("observed_unique", "stop_reason")
            if key in observed
        }
    return redactor.value({"gateway_ledger": ledger_bounds, "observed_actions": observed_bounds})


def sanitized_metadata(metadata: dict[str, Any], redactor: Redactor) -> dict[str, Any]:
    contexts: list[dict[str, Any]] = []
    for raw in metadata.get("contexts", []):
        if not isinstance(raw, dict):
            continue
        item = {
            key: raw.get(key)
            for key in ("context", "status", "exit_code", "elapsed_seconds", "termination_reason", "final_present")
            if key in raw
        }
        cleanup = raw.get("cleanup")
        if isinstance(cleanup, dict) and "exit_code" in cleanup:
            item["cleanup_exit_code"] = cleanup.get("exit_code")
        contexts.append(redactor.value(item))
    service_raw = metadata.get("service")
    service: dict[str, Any] = {}
    if isinstance(service_raw, dict):
        service = {
            key: service_raw.get(key)
            for key in ("status", "revision", "exit_code", "error")
            if key in service_raw
        }
        cleanup = service_raw.get("cleanup")
        if isinstance(cleanup, dict) and "exit_code" in cleanup:
            service["cleanup_exit_code"] = cleanup.get("exit_code")
    return {
        "record_type": "runner_completion_receipt",
        "worker_outcome_note": "A runner completion receipt can contain a failed worker outcome; it does not establish a successful task result.",
        "deadline_seconds": metadata.get("deadline_seconds"),
        "cutoff_seconds": metadata.get("cutoff_seconds"),
        "gateway_isolation_status": metadata.get("gateway_only_status"),
        "isolation_claim": metadata.get("isolation_claim"),
        "shared_ledger_bounds": shared_ledger_bounds(metadata, redactor),
        "contexts": contexts,
        "service": redactor.value(service),
    }


def receipt_for_item(item: dict[str, Any], *, context: int, sequence: int, redactor: Redactor) -> dict[str, Any] | None:
    tool_type = str(item.get("type", ""))
    arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
    operation = str(arguments.get("operation") or tool_type or "tool_operation")
    failed = item_failed(item)
    status = item_status(item)
    cli = cli_execution_metadata(arguments) if operation == "exec" else {}
    if is_private_cli_failure(item):
        return {
            "context": context,
            "sequence": sequence,
            "operation": "local_cli_handoff",
            "status": "failed",
            "failure": "The local CLI was denied access to the private study path; no accepted handoff outcome was observed.",
            "body_omitted": True,
            "result_metadata": result_metadata(item, redactor=redactor),
            "acceptance_basis": "not_established_by_command_receipt",
        }
    path = arguments.get("path")
    raw_path = path if isinstance(path, str) else str(arguments.get("path_basename") or "")
    document = worker_document_basename(raw_path)
    if document is not None and operation in {"read", "write"}:
        return {
            "context": context,
            "sequence": sequence,
            "operation": operation,
            "record_class": "worker_document",
            "status": status,
            "path_basename": redactor.text(document),
            "body_omitted": True,
            "result_metadata": result_metadata(item, redactor=redactor),
        }
    if operation == "exec" and cli:
        receipt: dict[str, Any] = {
            "context": context,
            "sequence": sequence,
            "operation": "local_cli_handoff",
            "status": status,
            "execution_path": cli.get("execution_path"),
            "cli_verb": cli.get("cli_verb"),
        }
        receipt.update(normalized_cli_result(item, redactor=redactor))
        return receipt
    if item_has_excluded_instruction_access(item, arguments):
        receipt = {
            "context": context,
            "sequence": sequence,
            "operation": "excluded_instruction_access",
            "status": status,
            "body_omitted": True,
            "result_metadata": result_metadata(item, redactor=redactor, include_result_path=False),
        }
        if failed:
            receipt["failure"] = "An excluded prompt, packet, common-instruction, or procedure access failed; its contents are not included."
        return receipt
    document_names = command_mentions_worker_document(arguments) if operation == "exec" else []
    if document_names:
        receipt = {
            "context": context,
            "sequence": sequence,
            "operation": operation,
            "record_class": "worker_document_command",
            "status": status,
            "path_basenames": document_names,
            "body_omitted": True,
            "result_metadata": result_metadata(item, redactor=redactor),
        }
        if failed:
            receipt["failure"] = "The tool action did not complete successfully; command and output bodies are omitted."
        return receipt
    if operation == "list":
        receipt = {
            "context": context,
            "sequence": sequence,
            "operation": "list",
            "status": status,
            "listing_body_omitted": True,
            "result_metadata": result_metadata(item, redactor=redactor),
        }
        if failed:
            receipt["failure"] = "The tool action did not complete successfully; listing bodies are omitted."
        return receipt
    if tool_type not in TOOL_ITEM_TYPES:
        return None
    receipt = {
        "context": context,
        "sequence": sequence,
        "operation": operation,
        "status": status,
        "body_omitted": True,
        "operation_metadata": operation_metadata(arguments),
        "result_metadata": result_metadata(item, redactor=redactor),
    }
    if failed:
        receipt["failure"] = "The tool action did not complete successfully; command and output bodies are omitted."
    return receipt


def collect_event_stream(path: Path, *, context: int, redactor: Redactor) -> tuple[dict[str, Any], list[str]]:
    receipts: list[dict[str, Any]] = []
    errors: list[str] = []
    accounting: dict[str, Any] = {
        "completed_tool_actions": 0,
        "by_operation": {},
        "by_status": {},
        "excluded_instruction_accesses": {"count": 0, "by_operation": {}, "by_status": {}},
    }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return {
            "record_type": "tool_receipts",
            "context": context,
            "status": "unreadable",
            "error": redactor.text(f"{error.__class__.__name__}: {error}"),
            "receipts": [],
            "action_accounting": accounting,
            "exclusion_note": "Prompt, packet, common-instruction, and procedure-body access is intentionally excluded.",
        }, [f"context {context}: event stream unreadable"]
    for line_number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"context {context}: invalid event JSON at line {line_number}")
            continue
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        tool_type = str(item.get("type", ""))
        arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        operation = str(arguments.get("operation") or tool_type or "tool_operation")
        status = item_status(item)
        if tool_type in TOOL_ITEM_TYPES:
            accounting["completed_tool_actions"] += 1
            accounting["by_operation"][operation] = accounting["by_operation"].get(operation, 0) + 1
            accounting["by_status"][status] = accounting["by_status"].get(status, 0) + 1
            if item_has_excluded_instruction_access(item, arguments) and not (
                operation == "exec" and bool(cli_execution_metadata(arguments))
            ):
                excluded = accounting["excluded_instruction_accesses"]
                excluded["count"] += 1
                excluded["by_operation"][operation] = excluded["by_operation"].get(operation, 0) + 1
                excluded["by_status"][status] = excluded["by_status"].get(status, 0) + 1
        receipt = receipt_for_item(item, context=context, sequence=line_number, redactor=redactor)
        if receipt is not None:
            receipts.append(receipt)
    accounting["retained_receipts"] = len(receipts)
    accounting["body_omitted_receipts"] = sum(1 for receipt in receipts if receipt.get("body_omitted"))
    payload: dict[str, Any] = {
        "record_type": "tool_receipts",
        "context": context,
        "observation_note": "These are sanitized completed tool receipts. A worker narrative is not execution proof by itself.",
        "receipts": receipts,
        "action_accounting": accounting,
        "exclusion_note": "Prompt, packet, common-instruction, and procedure-body access is intentionally excluded.",
    }
    if errors:
        payload["stream_errors"] = errors
    return payload, errors


def valid_service_http_receipt(value: Any) -> dict[str, Any] | None:
    """Allow only the fixed, service-owned HTTP receipt vocabulary."""
    if not isinstance(value, dict) or set(value) != SERVICE_HTTP_RECEIPT_KEYS:
        return None
    receipt_id = value.get("receipt_id")
    method = value.get("method")
    route = value.get("route")
    actor = value.get("actor_class")
    status = value.get("status")
    error = value.get("error")
    before = value.get("version_before")
    after = value.get("version_after")
    if value.get("event") != "http_request" or not isinstance(receipt_id, str) or not RECEIPT_ID_RE.fullmatch(receipt_id):
        return None
    if method not in SERVICE_HTTP_METHODS or route not in SERVICE_HTTP_ROUTES or actor not in SERVICE_HTTP_ACTORS:
        return None
    if not isinstance(status, int) or isinstance(status, bool) or status not in SERVICE_HTTP_STATUSES:
        return None
    if status == 200 and error is not None:
        return None
    if 400 <= status < 500 and (not isinstance(error, str) or error not in SERVICE_HTTP_ERRORS):
        return None
    if status != 200 and error is not None and error not in SERVICE_HTTP_ERRORS:
        return None
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in (before, after) if item is not None):
        return None
    return {
        "event": "http_request",
        "receipt_id": receipt_id,
        "method": method,
        "route": route,
        "actor_class": actor,
        "status": status,
        "error": error,
        "version_before": before,
        "version_after": after,
    }


def collect_service_http_receipts(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Collect coordinator-owned HTTP outcomes, never the workspace observation copy."""
    payload: dict[str, Any] = {
        "record_type": "coordinator_http_outcome_receipts",
        "trust_note": "These allowlisted records were written by the fixture service to the coordinator run path outside the gateway workspace. Workspace runtime-observations are inspection-only and are not used for actor/status claims.",
        "observation_limits": [
            "version_before and version_after are nullable service observations; null means unresolved.",
            "Differing version observations can reflect concurrent requests and do not establish a causal state effect or identify a specific worker action.",
        ],
        "receipts": [],
    }
    if not path.is_file() or path.is_symlink():
        payload["status"] = "absent"
        return payload, []
    errors: list[str] = []
    receipts: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        payload.update({"status": "unreadable", "error_class": exc.__class__.__name__})
        return payload, ["coordinator HTTP receipt file is unreadable"]
    for number, line in enumerate(lines, start=1):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"coordinator HTTP receipt has invalid JSON at line {number}")
            continue
        receipt = valid_service_http_receipt(parsed)
        if receipt is None:
            errors.append(f"coordinator HTTP receipt has an invalid allowlisted shape at line {number}")
            continue
        receipts.append(receipt)
    payload["status"] = "present" if receipts else "invalid"
    payload["receipts"] = receipts
    if errors:
        payload["collection_errors"] = errors
    return payload, errors


def collect_lifecycle_receipt(path: Path) -> dict[str, Any]:
    """Keep only the runner-owned state-backed acceptance facts."""
    if not path.is_file() or path.is_symlink():
        return {"record_type": "state_backed_lifecycle_receipt", "status": "absent"}
    try:
        value = read_json(path, label="runner lifecycle receipt")
    except CollectionError as exc:
        return {
            "record_type": "state_backed_lifecycle_receipt",
            "status": "unreadable",
            "error_class": exc.__class__.__name__,
        }
    allowed = {
        key: value.get(key)
        for key in (
            "schema", "status", "state_backed", "expected_action", "initial_revision", "final_revision",
            "accepted_outcome", "history_contains_expected_action", "note", "reason",
        )
        if key in value
    }
    return {"record_type": "state_backed_lifecycle_receipt", **allowed}


def extract_references(text: str, *, workspace: Path, run: Path) -> set[Path]:
    candidates: set[str] = set(MARKDOWN_LINK_RE.findall(text))
    candidates.update(BACKTICK_RE.findall(text))
    candidates.update(PATH_TOKEN_RE.findall(text))
    resolved: set[Path] = set()
    for raw in candidates:
        candidate = raw.strip().strip("<>").strip("'\"")
        if not candidate or "://" in candidate:
            continue
        candidate = LINE_REFERENCE_RE.sub("", candidate)
        path = Path(candidate)
        if not path.is_absolute():
            path = workspace / path
        path = path.resolve(strict=False)
        if not (path_is_within(path, workspace) or path_is_within(path, run)):
            continue
        try:
            relative = str(path.relative_to(workspace)) if path_is_within(path, workspace) else str(path.relative_to(run))
        except ValueError:
            continue
        if is_instruction_path(relative):
            continue
        if path.name.lower() in {"report.md", "phase1_note.md"}:
            continue
        resolved.add(path)
    return resolved


def artifact_class(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "workspace_code"
    if suffix in {".json", ".jsonl"}:
        return "structured_workspace_artifact"
    if suffix in {".txt", ".log"}:
        return "execution_log"
    if suffix in {".md", ".html"}:
        return "workspace_artifact"
    return "workspace_file"


def collect_artifact(path: Path, *, redactor: Redactor) -> tuple[dict[str, Any], str | None]:
    payload: dict[str, Any] = {
        "record_type": "referenced_workspace_artifact",
        "artifact_class": artifact_class(path),
        "observation_note": "The artifact is supplied because a collected worker record referenced it. It proves execution only when a tool receipt independently shows that execution.",
    }
    try:
        raw = path.read_bytes()
    except OSError as error:
        payload.update({"status": "unreadable", "error": redactor.text(f"{error.__class__.__name__}: {error}")})
        return payload, "referenced artifact unreadable"
    if b"\0" in raw:
        payload.update({"status": "binary_omitted", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        return payload, None
    text = raw.decode("utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            payload.update({"status": "present", "content": redactor.value(json.loads(text))})
            return payload, None
        except json.JSONDecodeError:
            pass
    if path.suffix.lower() == ".jsonl":
        parsed: list[Any] = []
        bad_lines: list[int] = []
        for index, line in enumerate(text.splitlines(), start=1):
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                bad_lines.append(index)
        if not bad_lines:
            payload.update({"status": "present", "content": redactor.value(parsed)})
            return payload, None
        payload["jsonl_parse_errors"] = bad_lines
    content = redactor.document(text) if path.suffix.lower() == ".md" else redactor.value(text)
    payload.update({"status": "present", "content": content})
    return payload, "referenced artifact has invalid JSON lines" if path.suffix.lower() == ".jsonl" else None


def append_evidence(evidence: list[tuple[str, dict[str, Any]]], kind: str, payload: dict[str, Any]) -> str:
    evidence_id = f"E{len(evidence) + 1:03d}"
    evidence.append((evidence_id, {"schema": SCHEMA, "evidence_id": evidence_id, "kind": kind, **payload}))
    return evidence_id


def safe_dossier_id(study: Path, source: ArmSource) -> str:
    private_key = f"{study.resolve(strict=False)}\0{source.arm_dir.name}\0{source.case_type}"
    token = hashlib.sha256(private_key.encode("utf-8")).hexdigest()[:12]
    return f"case-{source.case_type.lower()}-{token}"


def relevant_rubric(rubric: dict[str, Any], case_type: str, redactor: Redactor) -> dict[str, Any]:
    section = rubric.get(case_type)
    if not isinstance(section, dict):
        raise CollectionError(f"semantic rubric has no {case_type} section")
    return redactor.value(
        {
            "mandatory_observations": section.get("mandatory", []),
            "required_decision": section.get("decision"),
        }
    )


def build_dossier(source: ArmSource, *, study: Path, arm_names: list[str], rubric: dict[str, Any]) -> BuiltDossier:
    redactor = Redactor(study, arm_names, source.workspace, extra_private_files=(source.arm_dir / "gateway.json",))
    dossier_id = safe_dossier_id(study, source)
    evidence: list[tuple[str, dict[str, Any]]] = []
    errors: list[str] = []
    append_evidence(evidence, "runner_metadata", sanitized_metadata(source.metadata, redactor))

    raw_documents: list[tuple[str, str]] = []
    for filename, kind in (("REPORT.md", "worker_report"), ("PHASE1_NOTE.md", "phase_note")):
        path = source.workspace / filename
        if not path.is_file():
            append_evidence(
                evidence,
                kind,
                {
                    "record_type": kind,
                    "status": "absent",
                    "claim_note": "No worker prose artifact was available at collection time.",
                },
            )
            continue
        try:
            raw = read_text(path, label=filename)
        except CollectionError as error:
            errors.append(str(error))
            append_evidence(evidence, kind, {"record_type": kind, "status": "unreadable", "error": redactor.text(str(error))})
            continue
        raw_documents.append((kind, raw))
        append_evidence(
            evidence,
            kind,
            {
                "record_type": kind,
                "status": "present",
                "claim_note": "This is worker prose and must be corroborated by receipts or artifacts before it supports a finding.",
                "text": redactor.document(raw),
            },
        )

    for final_path in sorted(source.run.glob("final-*.md")):
        try:
            raw = read_text(final_path, label="worker final response")
        except CollectionError as error:
            errors.append(str(error))
            append_evidence(evidence, "final_worker_response", {"record_type": "final_worker_response", "status": "unreadable", "error": redactor.text(str(error))})
            continue
        raw_documents.append(("final_worker_response", raw))
        append_evidence(
            evidence,
            "final_worker_response",
            {
                "record_type": "final_worker_response",
                "status": "present",
                "claim_note": "This is a worker final narrative, not a substitute for executed evidence.",
                "text": redactor.document(raw),
            },
        )

    seen_contexts: set[int] = set()
    for event_path in sorted(source.run.glob("events-*.jsonl")):
        match = re.search(r"events-(\d+)\.jsonl$", event_path.name)
        context = int(match.group(1)) if match else len(seen_contexts) + 1
        seen_contexts.add(context)
        payload, stream_errors = collect_event_stream(event_path, context=context, redactor=redactor)
        errors.extend(stream_errors)
        append_evidence(evidence, "tool_receipts", payload)
    lifecycle = collect_lifecycle_receipt(source.run / "lifecycle-receipt.json")
    append_evidence(evidence, "state_backed_lifecycle_receipt", lifecycle)
    service_receipts, service_errors = collect_service_http_receipts(
        source.run / SERVICE_HTTP_RECEIPT_FILE
    )
    errors.extend(service_errors)
    append_evidence(evidence, "coordinator_http_outcome_receipts", service_receipts)
    expected_contexts = source.metadata.get("contexts")
    if isinstance(expected_contexts, list) and not seen_contexts:
        append_evidence(
            evidence,
            "tool_receipts",
            {
                "record_type": "tool_receipts",
                "status": "absent",
                "observation_note": "Runner metadata listed contexts but no event stream was available to collect.",
                "receipts": [],
            },
        )

    references: set[Path] = set()
    for _kind, raw in raw_documents:
        references.update(extract_references(raw, workspace=source.workspace, run=source.run))
    for path in sorted(references, key=lambda item: str(item)):
        if not path.is_file():
            append_evidence(
                evidence,
                "referenced_workspace_artifact",
                {
                    "record_type": "referenced_workspace_artifact",
                    "status": "missing",
                    "observation_note": "A collected worker record named a workspace artifact that was unavailable at collection time.",
                },
            )
            continue
        payload, artifact_error = collect_artifact(path, redactor=redactor)
        if artifact_error:
            errors.append(artifact_error)
        append_evidence(evidence, "referenced_workspace_artifact", payload)

    dossier = {
        "schema": SCHEMA,
        "dossier_id": dossier_id,
        "case_type": source.case_type,
        "collection_status": "completed_with_collection_errors" if errors else "completed",
        "grading_contract": relevant_rubric(rubric, source.case_type, redactor),
        "evidence": [
            {
                "evidence_id": evidence_id,
                "kind": payload["kind"],
                "path": f"evidence/{evidence_id}.json",
            }
            for evidence_id, payload in evidence
        ],
        "blinding_note": "Prompt content, arm labels, procedure availability, common instructions, evaluator-only material, absolute paths, selected script identifiers, and private user data are excluded or redacted.",
    }
    private_map = {
        "dossier_id": dossier_id,
        "arm": source.arm_dir.name,
        "case_type": source.case_type,
        "source_metadata_sha256": hashlib.sha256((source.run / "metadata.json").read_bytes()).hexdigest(),
    }
    return BuiltDossier(dossier_id, source.case_type, dossier, evidence, private_map, errors, redactor.sensitive_values)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(stable_json(payload), encoding="utf-8")
    temporary.replace(path)


def index_entry_from_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    dossier_id = dossier.get("dossier_id")
    case_type = dossier.get("case_type")
    evidence = dossier.get("evidence")
    if not isinstance(dossier_id, str) or not isinstance(case_type, str) or not isinstance(evidence, list):
        raise CollectionError("existing blind dossier has an invalid index shape")
    return {
        "dossier_id": dossier_id,
        "case_type": case_type,
        "collection_status": dossier.get("collection_status"),
        "evidence": evidence,
    }


def existing_index_entries(blind: Path) -> dict[str, dict[str, Any]]:
    index_path = blind / "index.json"
    if not index_path.exists():
        return {}
    index = read_json(index_path, label="existing blind index")
    entries = index.get("dossiers")
    if not isinstance(entries, list):
        raise CollectionError("existing blind index has no dossier list")
    output: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("dossier_id"), str):
            raise CollectionError("existing blind index has an invalid dossier entry")
        output[entry["dossier_id"]] = entry
    return output


def existing_map_entries(map_path: Path) -> dict[str, dict[str, Any]]:
    if not map_path.exists():
        return {}
    private_map = read_json(map_path, label="existing private blind map")
    entries = private_map.get("entries")
    if not isinstance(entries, list):
        raise CollectionError("existing private blind map has no entries list")
    output: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("dossier_id"), str):
            raise CollectionError("existing private blind map has an invalid entry")
        output[entry["dossier_id"]] = entry
    return output


def write_new_dossier(blind: Path, built: BuiltDossier) -> bool:
    """Create one new dossier atomically without rewriting an existing dossier."""
    destination = blind / built.dossier_id
    if destination.exists():
        return False
    temporary = blind / f".{built.dossier_id}.tmp-{os.getpid()}"
    if temporary.exists():
        shutil.rmtree(temporary)
    evidence_dir = temporary / "evidence"
    evidence_dir.mkdir(parents=True)
    try:
        write_json(temporary / "dossier.json", built.dossier)
        for evidence_id, payload in built.evidence:
            write_json(evidence_dir / f"{evidence_id}.json", payload)
        try:
            temporary.replace(destination)
        except FileExistsError:
            return False
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return True


def install_bundles(study: Path, dossiers: list[BuiltDossier], rubric: dict[str, Any]) -> tuple[Path, Path, list[str]]:
    private = study / "private"
    if not private.is_dir():
        raise CollectionError("study has no writable private directory")
    blind = private / "blind"
    if blind.exists() and not blind.is_dir():
        raise CollectionError("blind output exists but is not a directory")
    blind.mkdir(exist_ok=True)
    index_entries = existing_index_entries(blind)
    map_path = private / "blind-map.json"
    map_entries = existing_map_entries(map_path)
    added: list[str] = []
    for built in sorted(dossiers, key=lambda item: item.dossier_id):
        destination = blind / built.dossier_id
        if write_new_dossier(blind, built):
            added.append(built.dossier_id)
            index_entries[built.dossier_id] = index_entry_from_dossier(built.dossier)
            map_entries.setdefault(built.dossier_id, built.private_map)
        elif built.dossier_id not in index_entries:
            existing = read_json(destination / "dossier.json", label="existing blind dossier")
            index_entries[built.dossier_id] = index_entry_from_dossier(existing)
            map_entries.setdefault(built.dossier_id, built.private_map)
    if not added:
        return blind, map_path, added
    index = {
        "schema": SCHEMA,
        "rubric_version": rubric.get("version"),
        "dossiers": [index_entries[key] for key in sorted(index_entries)],
        "blinding_note": "Dossier IDs are stable opaque tokens. The arm map is private and is not part of this index.",
    }
    write_json(blind / "index.json", index)
    write_json(
        map_path,
        {
            "schema": SCHEMA,
            "map_scope": "private_only",
            "entries": [map_entries[key] for key in sorted(map_entries)],
        },
    )
    return blind, map_path, added


def write_new_json(path: Path, payload: dict[str, Any]) -> bool:
    """Create a supplementary record once without replacing an earlier version."""
    if path.exists():
        return False
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(stable_json(payload), encoding="utf-8")
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
    except OSError as error:
        raise CollectionError(f"cannot write supplementary evidence: {error.__class__.__name__}: {error}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return True


def dossier_needs_receipt_supplement(blind: Path, entry: dict[str, Any]) -> bool:
    found_receipts = False
    evidence = entry.get("evidence")
    if not isinstance(evidence, list):
        raise CollectionError("existing timing dossier has no evidence list")
    dossier_id = entry.get("dossier_id")
    if not isinstance(dossier_id, str):
        raise CollectionError("existing timing dossier has no dossier ID")
    for item in evidence:
        if not isinstance(item, dict) or item.get("kind") != "tool_receipts":
            continue
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str):
            raise CollectionError("existing timing dossier has an invalid tool-receipt index")
        found_receipts = True
        receipt = read_json(blind / dossier_id / "evidence" / f"{evidence_id}.json", label="existing timing receipt")
        if "action_accounting" not in receipt:
            return True
    return not found_receipts


def timing_supplement_context(payload: dict[str, Any]) -> dict[str, Any]:
    receipts = payload.get("receipts")
    if not isinstance(receipts, list):
        receipts = []
    document_receipts = [
        receipt
        for receipt in receipts
        if isinstance(receipt, dict) and str(receipt.get("record_class", "")).startswith("worker_document")
    ]
    cli_receipts = [
        receipt
        for receipt in receipts
        if isinstance(receipt, dict) and receipt.get("operation") == "local_cli_handoff"
    ]
    output: dict[str, Any] = {
        "context": payload.get("context"),
        "action_accounting": payload.get("action_accounting", {}),
        "worker_document_receipts": document_receipts,
        "cli_receipts": cli_receipts,
    }
    if "stream_errors" in payload:
        output["stream_errors"] = payload["stream_errors"]
    return output


def write_timing_supplements(study: Path, *, blind: Path, map_path: Path) -> tuple[Path, list[str], list[str]]:
    """Add v1 receipt corrections only for frozen timing dossiers that lack them."""
    private = study / "private"
    supplement_dir = private / "blind-supplements"
    if supplement_dir.exists() and not supplement_dir.is_dir():
        raise CollectionError("blind supplementary evidence output exists but is not a directory")
    supplement_dir.mkdir(exist_ok=True)
    sources, source_errors = source_arms(study)
    source_by_arm = {source.arm_dir.name: source for source in sources}
    arm_names = [path.name for path in (study / "arms").iterdir() if path.is_dir()]
    index_entries = existing_index_entries(blind)
    map_entries = existing_map_entries(map_path)
    errors = list(source_errors)
    added: list[str] = []
    for dossier_id, entry in sorted(index_entries.items()):
        case_type = entry.get("case_type")
        if not isinstance(case_type, str) or not case_type.startswith("TIMING_"):
            continue
        try:
            needs_supplement = dossier_needs_receipt_supplement(blind, entry)
        except CollectionError as error:
            errors.append(f"{dossier_id}: {error}")
            continue
        if not needs_supplement:
            continue
        map_entry = map_entries.get(dossier_id)
        arm_name = map_entry.get("arm") if isinstance(map_entry, dict) else None
        source = source_by_arm.get(arm_name) if isinstance(arm_name, str) else None
        if source is None:
            errors.append(f"{dossier_id}: completed source arm is unavailable for timing supplement")
            continue
        redactor = Redactor(study, arm_names, source.workspace, extra_private_files=(source.arm_dir / "gateway.json",))
        contexts: list[dict[str, Any]] = []
        stream_errors: list[str] = []
        seen_contexts: set[int] = set()
        for event_path in sorted(source.run.glob("events-*.jsonl")):
            match = re.search(r"events-(\d+)\.jsonl$", event_path.name)
            context = int(match.group(1)) if match else len(seen_contexts) + 1
            seen_contexts.add(context)
            payload, errors_for_stream = collect_event_stream(event_path, context=context, redactor=redactor)
            contexts.append(timing_supplement_context(payload))
            stream_errors.extend(errors_for_stream)
        expected_contexts = source.metadata.get("contexts")
        if isinstance(expected_contexts, list):
            for raw_context in expected_contexts:
                number = raw_context.get("context") if isinstance(raw_context, dict) else None
                if isinstance(number, int) and number not in seen_contexts:
                    contexts.append(
                        {
                            "context": number,
                            "status": "event_stream_absent",
                            "action_accounting": {
                                "completed_tool_actions": 0,
                                "by_operation": {},
                                "by_status": {},
                                "excluded_instruction_accesses": {"count": 0, "by_operation": {}, "by_status": {}},
                            },
                            "worker_document_receipts": [],
                            "cli_receipts": [],
                        }
                    )
        supplement = {
            "schema": SUPPLEMENT_SCHEMA,
            "supplement_version": SUPPLEMENT_VERSION,
            "dossier_id": dossier_id,
            "case_type": case_type,
            "scope_note": "This body-free receipt accounting supplements a frozen dossier; it does not replace its original evidence.",
            "runner_bounds": {
                "deadline_seconds": source.metadata.get("deadline_seconds"),
                "cutoff_seconds": source.metadata.get("cutoff_seconds"),
                "shared_ledger_bounds": shared_ledger_bounds(source.metadata, redactor),
            },
            "contexts": sorted(contexts, key=lambda value: (value.get("context") is None, value.get("context"))),
            "blinding_note": "Prompt bodies, worker-document bodies, CLI packets, arm labels, procedure availability, and absolute paths are omitted or redacted.",
        }
        if stream_errors:
            supplement["collection_errors"] = stream_errors
        output_path = supplement_dir / f"{dossier_id}.json"
        if write_new_json(output_path, supplement):
            added.append(dossier_id)
    return supplement_dir, errors, added


def public_bundle_errors(blind: Path, *, forbidden: Iterable[str]) -> list[str]:
    errors: list[str] = []
    try:
        index = read_json(blind / "index.json", label="blind index")
    except CollectionError as error:
        return [str(error)]
    dossiers = index.get("dossiers")
    if not isinstance(dossiers, list):
        return ["blind index has no dossier list"]
    for entry in dossiers:
        if not isinstance(entry, dict):
            errors.append("blind index contains a non-object dossier entry")
            continue
        dossier_id = entry.get("dossier_id")
        if not isinstance(dossier_id, str):
            errors.append("blind index dossier has no ID")
            continue
        dossier_path = blind / dossier_id / "dossier.json"
        if not dossier_path.is_file():
            errors.append(f"missing dossier file for {dossier_id}")
            continue
        try:
            dossier = read_json(dossier_path, label="blind dossier")
        except CollectionError as error:
            errors.append(str(error))
            continue
        if dossier.get("dossier_id") != dossier_id:
            errors.append(f"dossier ID mismatch for {dossier_id}")
        for evidence in entry.get("evidence", []):
            if not isinstance(evidence, dict) or not isinstance(evidence.get("evidence_id"), str):
                errors.append(f"invalid evidence index for {dossier_id}")
                continue
            evidence_path = blind / dossier_id / "evidence" / f"{evidence['evidence_id']}.json"
            if not evidence_path.is_file():
                errors.append(f"missing evidence {evidence['evidence_id']} for {dossier_id}")
    forbidden_values = {value for value in forbidden if value}
    forbidden_values.update({"prompt.md", "prompt2.md", "SKILL.md", "candidate.md", "input-manifest.json"})
    for path in blind.rglob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"cannot audit public bundle file {path.name}: {error.__class__.__name__}")
            continue
        for value in forbidden_values:
            if value in text:
                errors.append(f"public bundle contains forbidden source marker {value!r}")
        if re.search(r"\b(?:candidate|current)\b", text, flags=re.IGNORECASE):
            errors.append("public bundle contains an unblinded arm label")
        if re.search(r"/(?:private/)?var/folders/|/Users/", text):
            errors.append("public bundle contains an absolute private or user path")
    return errors


def supplementary_bundle_errors(supplement_dir: Path, *, forbidden: Iterable[str]) -> list[str]:
    if not supplement_dir.exists():
        return []
    errors: list[str] = []
    forbidden_values = {value for value in forbidden if value}
    forbidden_values.update({"prompt.md", "prompt2.md", "SKILL.md", "candidate.md", "input-manifest.json"})
    for path in supplement_dir.glob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"cannot audit supplementary evidence {path.name}: {error.__class__.__name__}")
            continue
        for value in forbidden_values:
            if value in text:
                errors.append(f"supplementary evidence contains forbidden source marker {value!r}")
        if re.search(r"\b(?:candidate|current)\b", text, flags=re.IGNORECASE):
            errors.append("supplementary evidence contains an unblinded arm label")
        if re.search(r"/(?:private/)?var/folders/|/Users/", text):
            errors.append("supplementary evidence contains an absolute private or user path")
    return errors


def collect(study: Path) -> tuple[Path, Path, list[BuiltDossier], list[str], list[str], list[str]]:
    try:
        study = study.resolve(strict=True)
    except OSError as error:
        if str(study).startswith("/private"):
            raise CollectionError(
                "the supplied private study path is inaccessible to this CLI; sandbox access must be restored before collection"
            ) from error
        raise CollectionError("the supplied study path is inaccessible") from error
    rubric = read_json(study / "private" / "semantic_rubric.json", label="private semantic rubric")
    sources, source_errors = source_arms(study)
    arm_names = [path.name for path in (study / "arms").iterdir() if path.is_dir()]
    built: list[BuiltDossier] = []
    errors = list(source_errors)
    for source in sources:
        try:
            dossier = build_dossier(source, study=study, arm_names=arm_names, rubric=rubric)
        except CollectionError as error:
            errors.append(f"{source.arm_dir.name}: {error}")
            continue
        built.append(dossier)
        errors.extend(f"{source.arm_dir.name}: {error}" for error in dossier.errors)
    blind, map_path, added = install_bundles(study, built, rubric)
    forbidden = [str(study), *arm_names, getpass.getuser(), os.environ.get("USER", "")]
    forbidden.extend(value for dossier in built for value in dossier.redacted_values)
    return blind, map_path, built, errors, forbidden, added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path, help="Prepared private study root")
    parser.add_argument("--check", action="store_true", help="Re-read the generated public bundle and reject contamination")
    parser.add_argument(
        "--write-timing-supplements",
        action="store_true",
        help="Add body-free receipt-accounting supplements for frozen timing dossiers only",
    )
    args = parser.parse_args()
    try:
        blind, map_path, built, errors, forbidden, added = collect(args.study)
    except CollectionError as error:
        print(f"collect_blind: {error}", file=sys.stderr)
        return 2
    supplement_dir = blind.parent / "blind-supplements"
    added_supplements: list[str] = []
    if args.write_timing_supplements:
        try:
            supplement_dir, supplement_errors, added_supplements = write_timing_supplements(
                args.study.resolve(strict=True), blind=blind, map_path=map_path
            )
        except CollectionError as error:
            errors.append(str(error))
        else:
            errors.extend(supplement_errors)
    if args.check:
        errors.extend(public_bundle_errors(blind, forbidden=forbidden))
        errors.extend(supplementary_bundle_errors(supplement_dir, forbidden=forbidden))
    summary = {
        "schema": SCHEMA,
        "bundle_dir": "private/blind",
        "private_map": "private/blind-map.json",
        "supplement_dir": "private/blind-supplements" if supplement_dir.exists() else None,
        "dossiers": [{"dossier_id": item.dossier_id, "case_type": item.case_type} for item in sorted(built, key=lambda item: item.dossier_id)],
        "added_dossiers": sorted(added),
        "added_timing_supplements": sorted(added_supplements),
        "errors": errors,
    }
    print(stable_json(summary), end="")
    if errors:
        for error in errors:
            print(f"collect_blind: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
