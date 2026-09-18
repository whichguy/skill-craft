#!/usr/bin/env python3
"""Run bounded, fresh-context capability trials through the workspace MCP gateway.

The study directory is intentionally prepared outside the repository.  Each arm owns
``arms/<name>/workspace`` and one or two prompt files.  This runner only launches a
second fresh context after the first exits normally, and both contexts use the same
gateway ledger and absolute 900-second budget.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from runtime_validation import (  # noqa: E402 - sibling is part of the frozen runtime
    RUNTIME_MANIFEST,
    RUNTIME_VERSION,
    RuntimeSnapshotError,
    validate_runtime_snapshot,
)
PYTHON = sys.executable
MODEL = "gpt-6-astra"
REASONING = "medium"
HARD_CALL_LIMIT = 64
EXPLORATION_CALL_LIMIT = 56
EXPLORATION_SECONDS = 780
SERVICE_READY_SECONDS = 10
ACTION_TYPES = {"mcp_tool_call", "command_execution", "exec_command", "write_stdin", "apply_patch", "file_change"}
MCP_SERVER = "shiploop_workspace"
MCP_TOOL = "mcp__shiploop_workspace__workspace"
STATE_FENCE_OPEN = "```shiploop-state"
SENSITIVE_KEY_PARTS = ("authorization", "credential", "password", "secret", "token", "api_key", "apikey")
USAGE_TELEMETRY_KEYS = {"input_tokens", "output_tokens", "cached_input_tokens"}
BODY_KEYS = {"argv", "code", "command", "content", "input", "message", "output", "prompt", "script", "stderr", "stdout", "text"}
SAFE_TEXT_KEYS = {
    "actor_class", "event", "execution_path", "method", "operation", "phase", "route", "server",
    "status", "tool", "type", "cli_verb", "sandbox", "receipt_id", "error_code",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def utc_from_epoch(epoch: float) -> str:
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_directory(study: Path) -> Path:
    """Resolve and validate the frozen runtime used for this follow-up study."""
    local_manifest = HERE / RUNTIME_MANIFEST
    runtime = HERE if local_manifest.is_file() else study / "frozen" / "runtime-v3"
    try:
        validate_runtime_snapshot(runtime)
    except RuntimeSnapshotError as exc:
        raise ValueError("missing or invalid frozen runtime-v3 metadata") from exc
    return runtime


def runtime_summary(runtime: Path) -> dict[str, Any]:
    metadata = json.loads((runtime / RUNTIME_MANIFEST).read_text(encoding="utf-8"))
    return {
        "runtime_version": metadata.get("runtime_version"),
        "runtime_manifest_sha256": sha256(runtime / RUNTIME_MANIFEST),
        "source_revision": metadata.get("source_revision"),
    }


def sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if lowered in USAGE_TELEMETRY_KEYS:
        return False
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def direct_cli_verb(argv: list[str]) -> str | None:
    for index, value in enumerate(argv):
        if Path(value).name != "shiploop":
            continue
        for candidate in argv[index + 1 :]:
            lowered = candidate.lower()
            if lowered in {"next", "complete", "done", "resume", "pause", "status"}:
                return "complete" if lowered == "done" else lowered
        return None
    return None


def argv_metadata(value: Any) -> dict[str, Any]:
    """Retain only non-secret execution classification, never command bodies."""
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return {"execution_path": "opaque_argv", "argc": 0}
    argv = list(value)
    executable = Path(argv[0]).name if argv else ""
    direct = direct_cli_verb(argv)
    if direct is not None:
        return {"execution_path": "direct_cli", "cli_verb": direct, "argc": len(argv)}
    is_python = executable.lower().startswith("python")
    if is_python and "-c" in argv:
        code = argv[argv.index("-c") + 1] if argv.index("-c") + 1 < len(argv) else ""
        # This only labels an opaque wrapper.  Its source is never persisted
        # and the label is not evidence that the CLI accepted a transition.
        if "shiploop" in code.lower():
            matched = re.search(r"\b(next|complete|done|resume|pause|status)\b", code, flags=re.IGNORECASE)
            metadata: dict[str, Any] = {"execution_path": "python_wrapper_cli", "argc": len(argv)}
            if matched:
                verb = matched.group(1).lower()
                metadata["cli_verb"] = "complete" if verb == "done" else verb
            return metadata
    return {"execution_path": "opaque_argv", "argc": len(argv), "executable_basename": executable}


def redacted(value: Any, *, key: str = "") -> Any:
    """Persist safe event structure while omitting arbitrary command/output bodies.

    A JSON-encoded structured result is parsed before redaction, so stable fields
    such as exit status survive.  Plain text command/output is never retained
    based on a best-effort secret regex.
    """
    if sensitive_key(key):
        return "<redacted>"
    if isinstance(value, dict):
        if key == "arguments":
            safe: dict[str, Any] = {}
            operation = value.get("operation")
            if isinstance(operation, str):
                safe["operation"] = operation
            path = value.get("path")
            if isinstance(path, str):
                safe["path_basename"] = Path(path).name
            timeout = value.get("timeout_seconds")
            if isinstance(timeout, int) and not isinstance(timeout, bool):
                safe["timeout_seconds"] = timeout
            if "argv" in value:
                safe["argv_metadata"] = argv_metadata(value["argv"])
            return safe
        return {str(name): redacted(item, key=str(name)) for name, item in value.items()}
    if isinstance(value, list):
        return [redacted(item, key=key) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                pass
            else:
                return redacted(parsed, key=key)
        if key in BODY_KEYS:
            return "<redacted-body>"
        if key in SAFE_TEXT_KEYS:
            return value
        if key == "path":
            return Path(value).name
        return "<redacted-text>"
    return value


def json_toml(value: Any) -> str:
    """JSON literals are accepted TOML literals for strings and string arrays."""
    return json.dumps(value, ensure_ascii=False)


def signal_group(proc: subprocess.Popen[bytes], sig: signal.Signals) -> bool:
    if proc.poll() is not None:
        return False
    try:
        os.killpg(proc.pid, sig)
        return True
    except ProcessLookupError:
        return False


def cleanup_group(proc: subprocess.Popen[bytes]) -> dict[str, Any]:
    receipt = {"term_sent": signal_group(proc, signal.SIGTERM), "kill_sent": False}
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        receipt["kill_sent"] = signal_group(proc, signal.SIGKILL)
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            pass
    receipt["exit_code"] = proc.returncode
    return receipt


def child_environment(workspace: Path, *, service_receipts: Path | None = None) -> dict[str, str]:
    """A small environment for trusted fixture services and the gateway process."""
    tmp, cache = workspace / "tmp", workspace / "cache"
    tmp.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"),
        "TMPDIR": str(tmp),
        "XDG_CACHE_HOME": str(cache),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
    }
    # Preserve the host HOME location only for runtimes which require it.  It
    # is never redirected to the trial workspace or copied into logs.
    if "HOME" in os.environ:
        env["HOME"] = os.environ["HOME"]
    if service_receipts is not None:
        receipt_path = service_receipts.resolve(strict=False)
        if is_below(receipt_path, workspace.resolve(strict=True)):
            raise ValueError("authoritative service receipt path must stay outside the gateway workspace")
        env["SHIPLOOP_CAPABILITY_SERVICE_RECEIPTS"] = str(receipt_path)
    return env


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def start_fixture_service(workspace: Path, run: Path) -> tuple[subprocess.Popen[bytes] | None, dict[str, Any]]:
    """Start an arm-owned loopback fixture and require its current ready receipt."""
    workspace = workspace.resolve(strict=True)
    command_path = workspace / "service-command.json"
    if not command_path.is_file():
        return None, {"status": "not_configured"}
    try:
        config = load_json(command_path)
    except ValueError as exc:
        return None, {"status": "invalid_command", "error": str(exc)}
    argv = config.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item or "\x00" in item for item in argv):
        return None, {"status": "invalid_command", "error": "service-command argv must be a non-empty string array"}
    raw_cwd = config.get("cwd", ".")
    if not isinstance(raw_cwd, str) or "\x00" in raw_cwd:
        return None, {"status": "invalid_command", "error": "service-command cwd must be a string"}
    cwd = (workspace / raw_cwd).resolve(strict=False)
    if Path(raw_cwd).is_absolute() or not is_below(cwd, workspace) or not cwd.is_dir():
        return None, {"status": "invalid_command", "error": "service-command cwd must stay in workspace"}
    ready = workspace / "service-ready.json"
    authoritative_receipts = run / "service-http-receipts.jsonl"
    stdout_path, stderr_path = run / "service.stdout.txt", run / "service.stderr.txt"
    stdout = stdout_path.open("wb")
    stderr = stderr_path.open("wb")
    started = time.monotonic()
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
                env=child_environment(workspace, service_receipts=authoritative_receipts),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    except OSError as exc:
        stdout.close()
        stderr.close()
        return None, {"status": "start_failed", "error": str(exc), "stdout": str(stdout_path), "stderr": str(stderr_path)}
    receipt: dict[str, Any] = {
        "status": "starting",
        "pid": proc.pid,
        "argv": argv,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "authoritative_http_receipts": {
            "path": str(authoritative_receipts),
            "owner": "coordinator",
            "workspace_copy": "inspection_only",
        },
    }
    try:
        while time.monotonic() - started < SERVICE_READY_SECONDS:
            if proc.poll() is not None:
                receipt.update({"status": "exited_before_ready", "exit_code": proc.returncode})
                return None, receipt
            try:
                ready_data = load_json(ready)
            except ValueError:
                ready_data = None
            if isinstance(ready_data, dict) and ready_data.get("pid") == proc.pid:
                url = ready_data.get("url")
                if isinstance(url, str) and url.startswith("http://127.0.0.1:"):
                    authoritative = ready_data.get("authoritativeHttpReceipt")
                    configured = authoritative.get("configured") if isinstance(authoritative, dict) else False
                    available = authoritative.get("available") if isinstance(authoritative, dict) else False
                    receipt["authoritative_http_receipts"]["service_status"] = {
                        "configured": configured,
                        "available": available,
                        "error": authoritative.get("error") if isinstance(authoritative, dict) else "receipt_status_missing",
                    }
                    if configured is not True or available is not True:
                        receipt.update({"status": "authoritative_receipts_unavailable"})
                        return None, receipt
                    receipt.update({"status": "ready", "url": url, "revision": ready_data.get("revision")})
                    return proc, receipt
            time.sleep(0.05)
        receipt["status"] = "ready_timeout"
        return None, receipt
    finally:
        if receipt["status"] != "ready":
            receipt["cleanup"] = cleanup_group(proc)
        stdout.close()
        stderr.close()


class ActionWatch:
    """An observed-action guard; the gateway is the stricter pre-dispatch guard."""

    def __init__(self, *, start_epoch: float, cutoff_epoch: float, deadline_epoch: float) -> None:
        self.start_epoch = start_epoch
        self.cutoff_epoch = cutoff_epoch
        self.deadline_epoch = deadline_epoch
        self.lock = threading.Lock()
        self.seen: set[str] = set()
        self.records: list[dict[str, Any]] = []
        self.by_type: Counter[str] = Counter()
        self.stop_reason: str | None = None

    def observe(self, context: int, event: dict[str, Any]) -> str | None:
        if event.get("type") not in {"item.started", "item.completed"} or not isinstance(event.get("item"), dict):
            return None
        item = event["item"]
        kind = str(item.get("type") or "")
        if kind not in ACTION_TYPES:
            return None
        token = f"{context}:{item.get('id') or json.dumps(item, sort_keys=True, default=str)}"
        with self.lock:
            if token in self.seen:
                return self.stop_reason
            self.seen.add(token)
            self.by_type[kind] += 1
            self.records.append(
                {
                    "context": context,
                    "event": event.get("type"),
                    "type": kind,
                    "server": item.get("server"),
                    "tool": item.get("tool"),
                }
            )
            now = time.time()
            count = len(self.seen)
            if count > HARD_CALL_LIMIT:
                self.stop_reason = "observed_hard_action_limit"
            elif now < self.cutoff_epoch and count > EXPLORATION_CALL_LIMIT:
                self.stop_reason = "observed_exploration_action_limit"
            elif now >= self.cutoff_epoch and kind != "mcp_tool_call":
                self.stop_reason = "post_cutoff_non_gateway_action"
            return self.stop_reason

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "observed_unique": len(self.seen),
                "by_type": dict(self.by_type),
                "records": list(self.records),
                "stop_reason": self.stop_reason,
            }


def codex_command(workspace: Path, run: Path, ledger: Path, log: Path, start_epoch: float,
                  deadline_epoch: float, cutoff_epoch: float, context: int, gateway_config: Path | None,
                  gateway_path: Path) -> list[str]:
    args = [
        str(gateway_path),
        "--workspace", str(workspace),
        "--log", str(log),
        "--ledger", str(ledger),
        "--start-epoch", str(start_epoch),
        "--deadline-epoch", str(deadline_epoch),
        "--cutoff-epoch", str(cutoff_epoch),
        "--call-limit", str(HARD_CALL_LIMIT),
        "--exploration-limit", str(EXPLORATION_CALL_LIMIT),
    ]
    if gateway_config is not None:
        args += ["--config", str(gateway_config)]
    disabled = ["exec_command", "write_stdin", "apply_patch", "shell", "web_search"]
    return [
        "codex", "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check", "--json",
        "--disable", "shell_tool", "--disable", "unified_exec", "-s", "workspace-write", "-C", str(workspace),
        "-o", str(run / f"final-{context}.md"), "-m", MODEL,
        "-c", f"model_reasoning_effort={json_toml(REASONING)}",
        "-c", "web_search=\"disabled\"",
        "-c", "features.shell_tool=false",
        "-c", "features.unified_exec=false",
        "-c", f"tools.enabled_tools={json_toml([MCP_TOOL])}",
        "-c", f"tools.disabled_tools={json_toml(disabled)}",
        "-c", f"mcp_servers.{MCP_SERVER}.command={json_toml(PYTHON)}",
        "-c", f"mcp_servers.{MCP_SERVER}.args={json_toml(args)}",
        "-c", f"mcp_servers.{MCP_SERVER}.startup_timeout_sec=20",
        "-",
    ]


def stream_context(cmd: list[str], prompt: str, *, context: int, run: Path, watch: ActionWatch,
                   deadline_epoch: float) -> dict[str, Any]:
    events_path = run / f"events-{context}.jsonl"
    stderr_path = run / f"stderr-{context}.txt"
    reason = {"value": None}
    lock = threading.Lock()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    def stop(value: str) -> None:
        with lock:
            if reason["value"] is None:
                reason["value"] = value
                signal_group(proc, signal.SIGTERM)

    def read_stdout() -> None:
        assert proc.stdout is not None
        with events_path.open("w", encoding="utf-8") as output:
            for raw in iter(proc.stdout.readline, b""):
                text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                try:
                    event = json.loads(text)
                    output.write(json.dumps(redacted(event), sort_keys=True) + "\n")
                    observed = watch.observe(context, event) if isinstance(event, dict) else None
                    if observed:
                        stop(observed)
                except json.JSONDecodeError:
                    output.write(json.dumps({"type": "unparsed", "text": "<unparsed>"}) + "\n")
                output.flush()

    def read_stderr() -> None:
        assert proc.stderr is not None
        with stderr_path.open("w", encoding="utf-8") as output:
            for raw in iter(proc.stderr.readline, b""):
                output.write(raw.decode("utf-8", errors="replace"))
                output.flush()

    threads = [threading.Thread(target=read_stdout, daemon=True), threading.Thread(target=read_stderr, daemon=True)]
    for thread in threads:
        thread.start()
    assert proc.stdin is not None
    try:
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()
    except BrokenPipeError:
        pass
    started = time.monotonic()
    while proc.poll() is None and reason["value"] is None:
        if time.time() >= deadline_epoch:
            stop("hard_deadline")
            break
        time.sleep(0.05)
    cleanup = cleanup_group(proc)
    for thread in threads:
        thread.join(timeout=2)
    for pipe in (proc.stdout, proc.stderr):
        if pipe is not None:
            pipe.close()
    return {
        "context": context,
        "exit_code": proc.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "termination_reason": reason["value"],
        "final_present": (run / f"final-{context}.md").exists(),
        "events": str(events_path),
        "stderr": str(stderr_path),
        "cleanup": cleanup,
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def arm_paths(study: Path, name: str) -> tuple[Path, Path, Path, Path | None]:
    arm = study / "arms" / name
    workspace, prompt, run = arm / "workspace", arm / "prompt.md", arm / "run"
    gateway_config = arm / "gateway.json"
    if not workspace.is_dir() or not prompt.is_file():
        raise ValueError(f"arm {name!r} needs workspace/ and prompt.md")
    return workspace.resolve(strict=True), prompt, run, gateway_config if gateway_config.is_file() else None


def verify_arm_runtime_manifest_pin(study: Path, name: str, runtime: Path) -> str:
    """Require a prepared arm to use the frozen manifest it recorded at preparation.

    Runtime validation establishes only local snapshot self-consistency. This
    pin prevents a changed and rehashed local manifest from replacing the
    runtime after an arm was prepared; it is not an external signature.
    """
    manifest = load_json(study / "arms" / name / "input-manifest.json")
    expected = manifest.get("runtime_manifest_sha256")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("prepared arm has no valid frozen runtime manifest pin")
    actual = sha256(runtime / RUNTIME_MANIFEST)
    if actual != expected:
        raise ValueError("prepared arm frozen runtime manifest pin does not match")
    return actual


def ledger_snapshot(path: Path) -> dict[str, Any]:
    try:
        return load_json(path)
    except ValueError:
        return {"unavailable": True}


def parse_navigator_state_text(text: str) -> dict[str, Any]:
    """Parse the small Markdown-authoritative navigator state without importing it."""
    lines = text.splitlines()
    try:
        start = lines.index(STATE_FENCE_OPEN)
    except ValueError as exc:
        raise ValueError("navigator state has no state fence") from exc
    try:
        end = lines.index("```", start + 1)
    except ValueError as exc:
        raise ValueError("navigator state has an unterminated state fence") from exc
    try:
        state = json.loads("\n".join(lines[start + 1 : end]))
    except json.JSONDecodeError as exc:
        raise ValueError("navigator state JSON is invalid") from exc
    if not isinstance(state, dict):
        raise ValueError("navigator state is not an object")
    return state


def read_navigator_state(path: Path) -> dict[str, Any]:
    try:
        return parse_navigator_state_text(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read navigator state: {path}") from exc


def lifecycle_baseline(workspace: Path) -> dict[str, Any] | None:
    state_path = workspace / "shiploop-state" / "state.md"
    if not state_path.is_file() or state_path.is_symlink():
        return None
    try:
        state = read_navigator_state(state_path)
    except ValueError:
        return None
    action = state.get("action")
    action_id = action.get("id") if isinstance(action, dict) else None
    revision = state.get("revision")
    if not isinstance(action_id, str) or not isinstance(revision, int):
        return None
    return {
        "schema": "shiploop-capability-state-backed-lifecycle-v1",
        "state_path": "shiploop-state/state.md",
        "expected_action": action_id,
        "initial_revision": revision,
    }


def state_backed_lifecycle_receipt(workspace: Path, baseline: dict[str, Any] | None) -> dict[str, Any]:
    """Produce a narrow runner-owned acceptance receipt from durable state."""
    if baseline is None:
        return {
            "schema": "shiploop-capability-state-backed-lifecycle-v1",
            "status": "not_applicable",
            "reason": "no initial navigator state was available to bind an expected action",
        }
    state_path = workspace / baseline["state_path"]
    try:
        state = read_navigator_state(state_path)
    except ValueError as exc:
        return {
            **baseline,
            "status": "unavailable",
            "reason": str(exc),
        }
    expected = baseline["expected_action"]
    accepted = state.get("accepted")
    history = state.get("history")
    result = accepted.get(expected) if isinstance(accepted, dict) else None
    history_match = any(
        isinstance(item, dict) and item.get("action") == expected
        for item in history
    ) if isinstance(history, list) else False
    outcome = result.get("outcome") if isinstance(result, dict) else None
    verified = (
        isinstance(result, dict)
        and isinstance(outcome, str)
        and history_match
        and isinstance(state.get("revision"), int)
        and state["revision"] > baseline["initial_revision"]
    )
    return {
        **baseline,
        "status": "accepted" if verified else "not_accepted",
        "state_backed": verified,
        "accepted_outcome": outcome if isinstance(outcome, str) else None,
        "final_revision": state.get("revision") if isinstance(state.get("revision"), int) else None,
        "history_contains_expected_action": history_match,
        "note": "This receipt proves only the named action's persisted navigator acceptance; it does not infer acceptance from command argv or stdout.",
    }


class GatewayRpc:
    """Small JSON-RPC client for the same gateway executable used by workers."""

    def __init__(self, argv: list[str]) -> None:
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        self.next_id = 1

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("gateway RPC pipes are unavailable")
        request_id = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()
        response = self.proc.stdout.readline()
        if not response:
            stderr = self.proc.stderr.read() if self.proc.stderr is not None else ""
            raise RuntimeError(f"gateway exited before responding: {stderr[-300:]}")
        payload = json.loads(response)
        if payload.get("id") != request_id or "error" in payload or not isinstance(payload.get("result"), dict):
            raise RuntimeError("gateway returned an invalid RPC response")
        return payload["result"]

    def workspace(self, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        response = self.request("tools/call", {"name": "workspace", "arguments": arguments})
        content = response.get("content")
        if not isinstance(content, list) or not content or not isinstance(content[0], dict):
            raise RuntimeError("gateway workspace response has no content")
        text = content[0].get("text")
        if not isinstance(text, str):
            raise RuntimeError("gateway workspace response has no text payload")
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise RuntimeError("gateway workspace payload is not an object")
        return payload, bool(response.get("isError"))

    def close(self) -> dict[str, Any]:
        if self.proc.stdin is not None and not self.proc.stdin.closed:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cleanup = cleanup_group(self.proc)
        else:
            cleanup = {"term_sent": False, "kill_sent": False, "exit_code": self.proc.returncode}
        if self.proc.stdout is not None:
            self.proc.stdout.close()
        if self.proc.stderr is not None:
            self.proc.stderr.close()
        return cleanup


def write_service_receipt_fixture(workspace: Path, runtime: Path) -> None:
    """Write the smallest non-secret fixture needed for one denied HTTP request."""
    state = {
        "schemaVersion": 1,
        "board": {
            "b2": {"actor": "red", "king": False},
            "g7": {"actor": "black", "king": False},
        },
        "turn": "red",
        "version": 1,
        "forcedFrom": None,
        "history": [],
        "idempotency": {},
    }
    (workspace / "state.json").write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "client.html").write_text("<!doctype html><title>fixture</title>\n", encoding="utf-8")
    (workspace / "served-service-config.json").write_text(
        json.dumps({"service": "synthetic-checkers", "requiredScope": "checkers:admin", "cacheTtlSeconds": 0}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    command = {
        "argv": [
            PYTHON, str(runtime / "fixture-app.py"), "--workspace", str(workspace),
            "--config", str(workspace / "served-service-config.json"),
            "--revision", "runtime-preflight-fixture", "--port", "0",
            "--ready-file", str(workspace / "service-ready.json"),
        ],
        "cwd": ".",
    }
    (workspace / "service-command.json").write_text(json.dumps(command, sort_keys=True) + "\n", encoding="utf-8")


def snapshot_collector(runtime: Path) -> Any:
    """Load the frozen collector so the probe does not consult current source."""
    name = "shiploop_capability_frozen_collector_" + hashlib.sha256(str(runtime).encode("utf-8")).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, runtime / "collect_blind.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen collector is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def service_receipt_preflight(workspace: Path, run: Path, runtime: Path) -> dict[str, Any]:
    """Join local HTTP scope denial to a coordinator-owned, allowlisted receipt."""
    write_service_receipt_fixture(workspace, runtime)
    inside_workspace_rejected = False
    try:
        child_environment(workspace, service_receipts=workspace / "service-http-receipts.jsonl")
    except ValueError:
        inside_workspace_rejected = True
    proc, service = start_fixture_service(workspace, run)
    http_status: int | None = None
    request_error: str | None = None
    try:
        if proc is None or service.get("status") != "ready":
            request_error = "service_not_ready"
        else:
            url = service.get("url")
            if not isinstance(url, str):
                request_error = "service_url_unavailable"
            else:
                request = Request(
                    url + "/api/move",
                    data=json.dumps({
                        "actor": "red", "from": "b2", "to": "c3", "expectedVersion": 1,
                        "idempotencyKey": "runtime-preflight-scope-denied",
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": "Bearer red-fixture-token"},
                    method="POST",
                )
                try:
                    with urlopen(request, timeout=5) as response:  # noqa: S310 - local fixture URL from readiness receipt
                        http_status = response.status
                except HTTPError as exc:
                    http_status = exc.code
                except URLError:
                    request_error = "local_http_request_failed"
    finally:
        if proc is not None:
            service["cleanup"] = cleanup_group(proc)
    receipt_path = run / "service-http-receipts.jsonl"
    try:
        module = snapshot_collector(runtime)
        collected, collection_errors = module.collect_service_http_receipts(receipt_path)
    except Exception as exc:
        collected, collection_errors = {"status": "collector_unavailable"}, [exc.__class__.__name__]
    receipts = collected.get("receipts") if isinstance(collected, dict) else []
    denial = next(
        (
            item for item in receipts
            if isinstance(item, dict)
            and item.get("actor_class") == "red"
            and item.get("status") == 403
            and item.get("error") == "scope_required"
        ),
        None,
    )
    return {
        "receipt_target_inside_workspace_rejected": inside_workspace_rejected,
        "service_status": service.get("status"),
        "service_receipt_available": bool(
            isinstance(service.get("authoritative_http_receipts"), dict)
            and service["authoritative_http_receipts"].get("service_status", {}).get("available") is True
        ),
        "http_status": http_status,
        "request_error": request_error,
        "collector_status": collected.get("status") if isinstance(collected, dict) else "collector_unavailable",
        "collector_error_count": len(collection_errors),
        "scope_denial_receipt": denial is not None,
        "receipt_observation_limit": "The service receipt is an uncorrelated observation; it does not identify a worker action or prove a causal state effect.",
    }


def successful_exec(events_path: Path, expected_output: str) -> bool:
    """Require the worker's argv operation to have actually completed successfully."""
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            event = json.loads(line)
            item = event.get("item", {})
            if event.get("type") != "item.completed" or item.get("type") != "mcp_tool_call":
                continue
            if item.get("arguments", {}).get("operation") != "exec":
                continue
            content = item.get("result", {}).get("content", [])
            if not content or not isinstance(content[0], dict):
                continue
            payload = json.loads(content[0].get("text", "{}"))
            if payload.get("exit_code") == 0 and expected_output in str(payload.get("stdout", "")):
                return True
        except (AttributeError, TypeError, json.JSONDecodeError):
            continue
    return False


def preflight_canary_checks(events_path: Path, canary: Path) -> dict[str, bool]:
    """Confirm the worker itself attempted, and was denied, both canary routes."""
    checks = {"read_attempted": False, "read_rejected": False, "exec_attempted": False, "exec_rejected": False,
              "proof_read": False}
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return checks
    for line in lines:
        try:
            event = json.loads(line)
            item = event.get("item", {})
            if event.get("type") != "item.completed" or item.get("type") != "mcp_tool_call":
                continue
            arguments = item.get("arguments", {})
            operation = arguments.get("operation")
            content = item.get("result", {}).get("content", [])
            payload = json.loads(content[0].get("text", "{}")) if content and isinstance(content[0], dict) else {}
            rejected = bool(item.get("error")) or bool(payload.get("error"))
            if operation == "read" and arguments.get("path") == str(canary):
                checks["read_attempted"] = True
                checks["read_rejected"] = rejected
            elif operation == "exec" and arguments.get("argv") == ["/bin/cat", str(canary)]:
                checks["exec_attempted"] = True
                checks["exec_rejected"] = rejected or payload.get("exit_code") != 0
            elif operation == "read" and arguments.get("path") == "proof.txt":
                checks["proof_read"] = not rejected
        except (AttributeError, TypeError, json.JSONDecodeError):
            continue
    return checks


def canary_contents_leaked(paths: list[Path], canary_contents: str) -> bool:
    needle = canary_contents.encode("utf-8")
    for path in paths:
        try:
            if needle in path.read_bytes():
                return True
        except OSError:
            continue
    return False


def run_arm(study: Path, name: str, *, deadline_seconds: int, no_new_trials_epoch: float | None,
            hard_deadline_epoch: float | None, preflight_status: str) -> dict[str, Any]:
    if no_new_trials_epoch is not None and time.time() >= no_new_trials_epoch:
        return {"arm": name, "status": "not_started_after_global_cutoff"}
    if hard_deadline_epoch is not None and time.time() + 120 >= hard_deadline_epoch:
        return {"arm": name, "status": "not_started_without_120_second_report_window"}
    runtime = runtime_directory(study)
    try:
        verify_arm_runtime_manifest_pin(study, name, runtime)
    except ValueError:
        return {"arm": name, "status": "not_started_runtime_manifest_pin_mismatch"}
    gateway_path = runtime / "gateway.py"
    workspace, prompt_path, run, gateway_config = arm_paths(study, name)
    if run.exists():
        return {"arm": name, "status": "run_directory_exists"}
    run.mkdir()
    prompt = prompt_path.read_text(encoding="utf-8")
    prompt_hashes = {"prompt.md": sha256(prompt_path)}
    prompt2 = prompt_path.with_name("prompt2.md")
    if prompt2.is_file():
        prompt_hashes["prompt2.md"] = sha256(prompt2)
    if gateway_config is not None:
        prompt_hashes["gateway.json"] = sha256(gateway_config)
    start_epoch = time.time()
    deadline_epoch = min(start_epoch + deadline_seconds, hard_deadline_epoch) if hard_deadline_epoch is not None else start_epoch + deadline_seconds
    cutoff_epoch = min(start_epoch + EXPLORATION_SECONDS, deadline_epoch - 120)
    ledger = run / "gateway-ledger.json"
    gateway_log = run / "gateway.jsonl"
    watch = ActionWatch(start_epoch=start_epoch, cutoff_epoch=cutoff_epoch, deadline_epoch=deadline_epoch)
    contexts: list[dict[str, Any]] = []
    service_proc, service = start_fixture_service(workspace, run)
    lifecycle_before = lifecycle_baseline(workspace)
    try:
        if service["status"] not in {"ready", "not_configured"}:
            contexts.append({"context": 1, "status": "not_started_service_unavailable"})
            if prompt2.is_file():
                contexts.append({"context": 2, "status": "not_started_service_unavailable"})
        else:
            first = stream_context(
                codex_command(workspace, run, ledger, gateway_log, start_epoch, deadline_epoch, cutoff_epoch, 1, gateway_config, gateway_path),
                prompt,
                context=1,
                run=run,
                watch=watch,
                deadline_epoch=deadline_epoch,
            )
            contexts.append(first)
            if prompt2.is_file() and first["exit_code"] == 0 and first["termination_reason"] is None and time.time() < deadline_epoch:
                contexts.append(
                    stream_context(
                        codex_command(workspace, run, ledger, gateway_log, start_epoch, deadline_epoch, cutoff_epoch, 2, gateway_config, gateway_path),
                        prompt2.read_text(encoding="utf-8"),
                        context=2,
                        run=run,
                        watch=watch,
                        deadline_epoch=deadline_epoch,
                    )
                )
            elif prompt2.is_file():
                contexts.append({"context": 2, "status": "not_started_after_first_context"})
    finally:
        if service_proc is not None:
            service["cleanup"] = cleanup_group(service_proc)
    lifecycle = state_backed_lifecycle_receipt(workspace, lifecycle_before)
    (run / "lifecycle-receipt.json").write_text(
        json.dumps(lifecycle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    metadata = {
        "arm": name,
        "started_at": utc_from_epoch(start_epoch),
        "deadline_seconds": round(deadline_epoch - start_epoch, 3),
        "cutoff_seconds": round(cutoff_epoch - start_epoch, 3),
        "model": MODEL,
        "reasoning_effort": REASONING,
        "workspace": str(workspace),
        "prompt_hashes": prompt_hashes,
        "runtime": runtime_summary(runtime),
        "gateway_only_status": preflight_status,
        "isolation_claim": "gateway_only" if preflight_status == "verified" else "exploratory_observed_bound",
        "contexts": contexts,
        "service": service,
        "observed_actions": watch.snapshot(),
        "gateway_ledger": ledger_snapshot(ledger),
        "lifecycle_receipt": lifecycle,
        "finished_at": utc_now(),
    }
    (run / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"arm": name, "status": "completed", "run": str(run), "contexts": len(contexts), "observed": watch.snapshot()["observed_unique"]}


def preflight(study: Path, *, deadline_seconds: int) -> dict[str, Any]:
    """Run a no-agent lifecycle canary through the frozen gateway and sandbox.

    This is deliberately a direct public CLI exercise.  It proves a single
    persisted navigator acceptance for a known action, rather than treating a
    successful process exit or a command string as acceptance evidence.
    """
    runtime = runtime_directory(study)
    root = study / "reports" / "capability-runtime-preflight"
    if root.exists():
        root = study / "reports" / f"capability-runtime-preflight-retry-{int(time.time())}"
    workspace = root / "workspace"
    run = root / "run"
    private = root / "private"
    workspace.mkdir(parents=True)
    run.mkdir()
    private.mkdir()
    runtime_copy = workspace / "shiploop-runtime"
    shutil.copytree(runtime / "shiploop", runtime_copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    project = workspace / "project"
    project.mkdir()
    run_dir = workspace / "shiploop-state"
    run_dir.mkdir()
    canary = private / "gateway-deny-canary.txt"
    canary_contents = "DO NOT EXPOSE THIS CANARY\n"
    canary.write_text(canary_contents, encoding="utf-8")
    symlink = workspace / "forbidden-link"
    symlink.symlink_to(canary)
    start_epoch = time.time()
    effective_deadline = min(deadline_seconds, 300)
    deadline_epoch = start_epoch + effective_deadline
    cutoff_epoch = min(start_epoch + EXPLORATION_SECONDS, deadline_epoch - 120)
    ledger, log = run / "gateway-ledger.json", run / "gateway.jsonl"
    server_argv = [
        PYTHON,
        str(runtime / "gateway.py"),
        "--workspace", str(workspace),
        "--log", str(log),
        "--ledger", str(ledger),
        "--start-epoch", str(start_epoch),
        "--deadline-epoch", str(deadline_epoch),
        "--cutoff-epoch", str(cutoff_epoch),
        "--call-limit", str(HARD_CALL_LIMIT),
        "--exploration-limit", str(EXPLORATION_CALL_LIMIT),
    ]
    cli = runtime_copy / "scripts" / "shiploop"
    commands: list[dict[str, Any]] = []
    checks: dict[str, Any] = {
        "gateway_initialized": False,
        "outside_read_rejected": False,
        "symlink_read_rejected": False,
        "outside_exec_rejected": False,
        "symlink_exec_rejected": False,
        "init_exit_zero": False,
        "next_exit_zero": False,
        "result_written": False,
        "complete_exit_zero": False,
        "accepted_state": False,
        "exactly_one_complete": False,
    }
    error: str | None = None
    gateway_cleanup: dict[str, Any] | None = None
    rpc: GatewayRpc | None = None
    service_probe: dict[str, Any] = {}
    try:
        rpc = GatewayRpc(server_argv)
        initialize = rpc.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "runtime-preflight", "version": "1"}})
        checks["gateway_initialized"] = initialize.get("protocolVersion") == "2025-11-25"
        denied, denied_error = rpc.workspace({"operation": "read", "path": str(canary)})
        checks["outside_read_rejected"] = denied_error and isinstance(denied.get("error"), str)
        blocked_link, link_error = rpc.workspace({"operation": "read", "path": "forbidden-link"})
        checks["symlink_read_rejected"] = link_error and "symbolic links" in str(blocked_link.get("error", ""))
        outside_exec, outside_exec_error = rpc.workspace({
            "operation": "exec", "argv": ["/bin/cat", str(canary)], "timeout_seconds": 20,
        })
        checks["outside_exec_rejected"] = (
            not outside_exec_error
            and outside_exec.get("exit_code") != 0
            and canary_contents not in str(outside_exec.get("stdout", ""))
            and canary_contents not in str(outside_exec.get("stderr", ""))
        )
        symlink_exec, symlink_exec_error = rpc.workspace({
            "operation": "exec", "argv": ["/bin/cat", str(symlink)], "timeout_seconds": 20,
        })
        checks["symlink_exec_rejected"] = (
            not symlink_exec_error
            and symlink_exec.get("exit_code") != 0
            and canary_contents not in str(symlink_exec.get("stdout", ""))
            and canary_contents not in str(symlink_exec.get("stderr", ""))
        )
        init_argv = [
            PYTHON, "-B", str(cli), "init", "--run-dir", str(run_dir), "--repo", str(project),
            "--prompt", "Execute one disposable runtime lifecycle canary. Do not deploy.",
            "--execution-mode", "navigator",
        ]
        init, init_error = rpc.workspace({"operation": "exec", "argv": init_argv, "timeout_seconds": 45})
        commands.append({"verb": "init", "exit_code": init.get("exit_code"), "gateway_error": init_error})
        checks["init_exit_zero"] = not init_error and init.get("exit_code") == 0
        # This is an actual direct public CLI `next`, not a wrapper or a
        # fabricated packet.  Its output is intentionally not used as proof.
        next_payload, next_error = rpc.workspace({
            "operation": "exec",
            "argv": [PYTHON, "-B", str(cli), "next", "--run-dir", str(run_dir)],
            "timeout_seconds": 45,
        })
        commands.append({"verb": "next", "exit_code": next_payload.get("exit_code"), "gateway_error": next_error})
        checks["next_exit_zero"] = not next_error and next_payload.get("exit_code") == 0
        before_payload, before_error = rpc.workspace({"operation": "read", "path": "shiploop-state/state.md"})
        if before_error or not isinstance(before_payload.get("text"), str):
            raise RuntimeError("gateway could not read initialized navigator state")
        before = parse_navigator_state_text(before_payload["text"])
        action = before.get("action")
        expected_action = action.get("id") if isinstance(action, dict) else None
        if not isinstance(expected_action, str):
            raise RuntimeError("initialized navigator state has no current action")
        result_path = f"shiploop-state/inbox/{expected_action}.md"
        result_body = (
            "# Runtime lifecycle canary result\n\n```shiploop-state\n"
            + json.dumps({"outcome": "done", "summary": "Disposable runtime lifecycle canary.", "evidence_refs": []}, sort_keys=True)
            + "\n```\n"
        )
        write_payload, write_error = rpc.workspace({"operation": "write", "path": result_path, "content": result_body})
        checks["result_written"] = not write_error and write_payload.get("path") == result_path
        complete_payload, complete_error = rpc.workspace({
            "operation": "exec",
            "argv": [
                PYTHON, "-B", str(cli), "complete", "--run-dir", str(run_dir),
                "--action", expected_action, "--result", str(workspace / result_path),
            ],
            "timeout_seconds": 45,
        })
        commands.append({"verb": "complete", "exit_code": complete_payload.get("exit_code"), "gateway_error": complete_error})
        checks["complete_exit_zero"] = not complete_error and complete_payload.get("exit_code") == 0
        after_payload, after_error = rpc.workspace({"operation": "read", "path": "shiploop-state/state.md"})
        if after_error or not isinstance(after_payload.get("text"), str):
            raise RuntimeError("gateway could not read final navigator state")
        after = parse_navigator_state_text(after_payload["text"])
        accepted = after.get("accepted")
        history = after.get("history")
        accepted_result = accepted.get(expected_action) if isinstance(accepted, dict) else None
        checks["accepted_state"] = (
            isinstance(accepted_result, dict)
            and accepted_result.get("outcome") == "done"
            and isinstance(history, list)
            and sum(1 for item in history if isinstance(item, dict) and item.get("action") == expected_action) == 1
            and after.get("revision") == before.get("revision", -1) + 1
        )
        checks["exactly_one_complete"] = [command["verb"] for command in commands].count("complete") == 1
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        error = f"{exc.__class__.__name__}: {exc}"
    finally:
        if rpc is not None:
            gateway_cleanup = rpc.close()
    try:
        service_workspace = root / "service-workspace"
        service_run = root / "service-run"
        service_workspace.mkdir()
        service_run.mkdir()
        service_probe = service_receipt_preflight(service_workspace, service_run, runtime)
        checks["receipt_target_inside_workspace_rejected"] = service_probe.get("receipt_target_inside_workspace_rejected") is True
        checks["service_receipt_available"] = service_probe.get("service_receipt_available") is True
        checks["scope_denial_http_status"] = service_probe.get("http_status") == 403
        checks["scope_denial_receipt"] = service_probe.get("scope_denial_receipt") is True
    except (OSError, RuntimeError, ValueError) as exc:
        service_probe = {"status": "failed", "error_class": exc.__class__.__name__}
        checks["receipt_target_inside_workspace_rejected"] = False
        checks["service_receipt_available"] = False
        checks["scope_denial_http_status"] = False
        checks["scope_denial_receipt"] = False
    records = ledger_snapshot(ledger).get("records", [])
    operations = [item.get("operation") for item in records if isinstance(item, dict)]
    leaked = canary_contents_leaked([log, run / "gateway-ledger.json"], canary_contents)
    verified = error is None and all(bool(value) for value in checks.values()) and not leaked
    outcome = {
        "schema": "shiploop-capability-runtime-preflight-v1",
        "status": "verified" if verified else "failed",
        "runtime": runtime_summary(runtime),
        "commands": commands,
        "checks": checks,
        "gateway_operations": operations,
        "gateway_ledger": ledger_snapshot(ledger),
        "gateway_cleanup": gateway_cleanup,
        "service_receipt_probe": service_probe,
        "canary_contents_leaked": leaked,
        "error": error,
        "note": "The accepted-state check is the lifecycle proof. Command exit codes and argv labels are supporting transport evidence only.",
    }
    (root / "result.json").write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": outcome["status"], "path": str(root / "result.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--arms", help="comma-separated arm names; defaults to prepared arm directories")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--deadline-seconds", type=int, default=900)
    parser.add_argument("--preflight", action="store_true", help="run only the disposable no-agent lifecycle canary")
    args = parser.parse_args()
    if not (1 <= args.parallel <= 4):
        parser.error("--parallel must be 1 through 4")
    if not (180 <= args.deadline_seconds <= 900):
        parser.error("--deadline-seconds must be 180 through 900")
    study = args.study.resolve(strict=True)
    if args.preflight:
        outcome = preflight(study, deadline_seconds=args.deadline_seconds)
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0 if outcome["status"] == "verified" else 2
    manifest = load_json(study / "manifest.json")
    if manifest.get("model") != MODEL or manifest.get("reasoning_effort") != REASONING:
        raise SystemExit("manifest does not pin gpt-6-astra with medium reasoning")
    if args.arms:
        arms = [name for name in args.arms.split(",") if name]
    else:
        arms = sorted(path.name for path in (study / "arms").iterdir() if path.is_dir() and (path / "prompt.md").is_file())
    if not arms:
        raise SystemExit("no prepared arms")
    no_new_trials_epoch = parse_utc(manifest.get("no_new_trials_after_utc"))
    hard_deadline_epoch = parse_utc(manifest.get("hard_deadline_utc"))
    if hard_deadline_epoch is None:
        raise SystemExit("manifest requires hard_deadline_utc")
    preflight_result = preflight(study, deadline_seconds=args.deadline_seconds)
    if preflight_result["status"] != "verified":
        raise SystemExit(
            f"runtime preflight failed; no arms launched (receipt: {preflight_result['path']})"
        )
    preflight_status = "verified"
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.parallel, len(arms))) as pool:
        results = list(
            pool.map(
                lambda name: run_arm(
                    study,
                    name,
                    deadline_seconds=args.deadline_seconds,
                    no_new_trials_epoch=no_new_trials_epoch,
                    hard_deadline_epoch=hard_deadline_epoch,
                    preflight_status=preflight_status,
                ),
                arms,
            )
        )
    reports = study / "reports"
    reports.mkdir(exist_ok=True)
    summary = reports / f"capability-runner-summary-{int(time.time())}.json"
    summary.write_text(json.dumps({"at": utc_now(), "results": results}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
