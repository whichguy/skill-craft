#!/usr/bin/env python3
"""One-tool, workspace-only MCP gateway for ShipLoop capability trials.

The gateway deliberately gives a trial worker one operation surface: ``workspace``.
It validates file paths below the assigned workspace, blocks hidden and credential-like
files, and runs argv-only commands through macOS ``sandbox-exec``.  The persistent
ledger is shared by a first and optional second fresh context in the same trial.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "shiploop-capability-workspace"
SERVER_VERSION = "0.1.0"
MAX_BYTES = 256 * 1024
MAX_LIST = 200
MAX_ARGV = 64
MAX_ARG_CHARS = 4096
MAX_EXEC_SECONDS = 120
DEFAULT_CALL_LIMIT = 64
DEFAULT_EXPLORATION_LIMIT = 56
DEFAULT_EXPLORATION_SECONDS = 780
SECRET_NAME = re.compile(r"(?:^|[._-])(env|secret|token|credential|password|passwd|private[_-]?key|id_rsa|id_ed25519)(?:[._-]|$)", re.I)
SECRET_VALUE = re.compile(r"(?i)((?:token|secret|password|authorization|cookie)\s*(?:=|:)\s*)([^\s,;]+)")
PLATFORM_METHODS = {"metadata", "source_metadata", "status", "guide", "auth_status", "source_body"}
PLATFORM_FORBIDDEN_KEYS = {"scriptid", "script_id", "token", "authorization", "credential", "secret", "apikey", "api_key"}


class GatewayError(ValueError):
    """A deliberately small, safe message for the model."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8", errors="replace")
    return hashlib.sha256(value).hexdigest()


def redact(value: str) -> str:
    return SECRET_VALUE.sub(r"\1<redacted>", value)


def platform_key_forbidden(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return (
        normalized in PLATFORM_FORBIDDEN_KEYS
        or "script_id" in normalized
        or "scriptid" in normalized
        or any(part in normalized for part in ("token", "secret", "credential", "authorization", "password"))
    )


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "<redacted>" if platform_key_forbidden(key) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact(value)
    return value


def result(payload: dict[str, Any], *, error: bool = False) -> dict[str, Any]:
    value: dict[str, Any] = {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}]}
    if error:
        value["isError"] = True
    return value


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def is_hidden(relative: Path) -> bool:
    return any(part.startswith(".") for part in relative.parts)


def is_sensitive(relative: Path) -> bool:
    return is_hidden(relative) or bool(SECRET_NAME.search(relative.name))


def quoted(value: str) -> str:
    """JSON strings are valid quoted SBPL strings for the paths used here."""
    return json.dumps(value)


def sandbox_profile(root: Path) -> str:
    """Allow system runtimes plus this workspace, local loopback only, and no dotfiles."""
    root_text = str(root)
    hidden_pattern = "^" + re.escape(root_text) + r"/(?:[^/]+/)*\.[^/]+(?:/|$)"
    permitted_system_roots = (
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/usr/libexec",
        "/usr/local/bin",
        "/usr/local/lib",
        "/opt/homebrew",
    )
    lines = [
        "(version 1)",
        "(deny default)",
        '(import "system.sb")',
        "(allow process*)",
        # Python resolves a Homebrew symlink through / and /opt before it opens
        # the executable.  Metadata-only access permits that pathname lookup;
        # file data still needs one of the explicit roots below.
        '(allow file-read-metadata (literal "/"))',
        '(allow file-read-metadata (subpath "/opt"))',
        '(allow file-read-metadata (subpath "/private"))',
        "(allow file-read* file-map-executable (subpath " + quoted(root_text) + "))",
        "(allow file-write* (subpath " + quoted(root_text) + "))",
    ]
    for item in permitted_system_roots:
        lines.append("(allow file-read* file-map-executable (subpath " + quoted(item) + "))")
    # The imported system profile does not grant general TCP access.  Permit
    # loopback for the local HTTP fixture only; external network remains denied.
    lines.extend(
        [
            '(allow network-outbound (remote ip "localhost:*"))',
            '(allow network-inbound (local ip "localhost:*"))',
            "(deny file-read* (regex #" + quoted(hidden_pattern) + "))",
            "(deny file-write* (regex #" + quoted(hidden_pattern) + "))",
        ]
    )
    return "\n".join(lines)


class Ledger:
    """A flock-protected per-arm budget shared across gateway processes."""

    def __init__(self, path: Path, *, start_epoch: float, deadline_epoch: float, cutoff_epoch: float,
                 call_limit: int, exploration_limit: int) -> None:
        self.path = path
        self.start_epoch = start_epoch
        self.deadline_epoch = deadline_epoch
        self.cutoff_epoch = cutoff_epoch
        self.call_limit = call_limit
        self.exploration_limit = exploration_limit
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_initial()

    def _initial(self) -> dict[str, Any]:
        return {
            "version": 1,
            "started_epoch": self.start_epoch,
            "exploration_cutoff_epoch": self.cutoff_epoch,
            "hard_deadline_epoch": self.deadline_epoch,
            "call_limit": self.call_limit,
            "exploration_limit": self.exploration_limit,
            "tool_calls": 0,
            "records": [],
        }

    def _write_initial(self) -> None:
        try:
            with self.path.open("x", encoding="utf-8") as handle:
                json.dump(self._initial(), handle, sort_keys=True)
                handle.write("\n")
        except FileExistsError:
            pass

    def snapshot(self) -> dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def consume(
        self,
        *,
        operation: str | None,
        path: str | None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Count every admissible tools/call before dispatching it."""
        with self.path.open("r+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    state = json.load(handle)
                except json.JSONDecodeError as exc:
                    raise GatewayError("trial ledger is invalid") from exc
                now = time.time()
                calls = state.get("tool_calls")
                if not isinstance(calls, int) or calls < 0:
                    raise GatewayError("trial ledger is invalid")
                if now >= float(state["hard_deadline_epoch"]):
                    return None, "hard_deadline"
                phase = "exploration" if now < float(state["exploration_cutoff_epoch"]) else "report_only"
                if calls >= int(state["call_limit"]):
                    return None, "call_limit"
                if phase == "exploration" and calls >= int(state["exploration_limit"]):
                    return None, "exploration_call_limit"
                state["tool_calls"] = calls + 1
                record: dict[str, Any] = {
                    "at": utc_now(),
                    "call": calls + 1,
                    "phase": phase,
                    "operation": operation,
                    "path": path,
                }
                state["records"].append(record)
                handle.seek(0)
                json.dump(state, handle, sort_keys=True)
                handle.write("\n")
                handle.truncate()
                return state, phase
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Gateway:
    def __init__(self, args: argparse.Namespace) -> None:
        try:
            self.root = args.workspace.resolve(strict=True)
        except OSError as exc:
            raise GatewayError("workspace is unavailable") from exc
        if not self.root.is_dir():
            raise GatewayError("workspace is not a directory")
        self.log_path = args.log
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = self.log_path.open("a", encoding="utf-8")
        self.platform_config = self.load_platform_config(args.config)
        self.platform_module: Any | None = None
        self.ledger = Ledger(
            args.ledger,
            start_epoch=args.start_epoch,
            deadline_epoch=args.deadline_epoch,
            cutoff_epoch=args.cutoff_epoch,
            call_limit=args.call_limit,
            exploration_limit=args.exploration_limit,
        )

    def close(self) -> None:
        if self.platform_module is not None:
            close = getattr(self.platform_module, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        self.log.close()

    def load_platform_config(self, config_path: Path | None) -> dict[str, Any] | None:
        """Only a fixed sibling reader may receive an arm's private GAS config."""
        if config_path is None:
            return None
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GatewayError("gateway configuration is unavailable") from exc
        if not isinstance(config, dict):
            raise GatewayError("gateway configuration is invalid")
        gas = config.get("gas")
        if gas is None:
            return None
        if not isinstance(gas, dict):
            raise GatewayError("gas configuration is invalid")
        selected = gas.get("selectedScriptId", gas.get("selected_script_id"))
        if not isinstance(selected, str) or not selected:
            raise GatewayError("gas configuration must pin selectedScriptId")
        # The reader keeps the private evidence log host-side.  The worker only
        # receives the returned, redacted observation.
        return gas

    def audit(self, event: str, details: dict[str, Any]) -> None:
        self.log.write(json.dumps({"at": utc_now(), "event": event, **details}, sort_keys=True) + "\n")
        self.log.flush()

    def tool_schema(self) -> dict[str, Any]:
        operations = ["list", "read", "write", "exec"]
        if self.platform_config is not None:
            operations.append("platform")
        return {
            "tools": [
                {
                    "name": "workspace",
                    "description": (
                        "The only trial operation. Use argv (never shell text) for exec. "
                        "Files must be visible, non-secret paths below the assigned workspace. "
                        "After the exploration cutoff, only reads/lists and writing REPORT.md are allowed."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "operation": {"type": "string", "enum": operations},
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "argv": {"type": "array", "items": {"type": "string"}},
                            "timeout_seconds": {"type": "integer", "minimum": 1},
                            "request": {"type": "object"},
                        },
                        "required": ["operation"],
                        "additionalProperties": False,
                    },
                    "annotations": {
                        "title": "Bounded workspace operation",
                        "readOnlyHint": False,
                        "destructiveHint": False,
                        "idempotentHint": False,
                        "openWorldHint": False,
                    },
                }
            ]
        }

    def relative_path(self, supplied: Any, *, allow_root: bool = False, must_exist: bool = False) -> tuple[Path, Path]:
        if supplied is None:
            if allow_root:
                return self.root, Path(".")
            raise GatewayError("path is required")
        if not isinstance(supplied, str) or not supplied or "\x00" in supplied:
            raise GatewayError("path must be a non-empty relative string")
        candidate = Path(supplied)
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            raise GatewayError("path must stay below the workspace")
        if is_sensitive(candidate):
            raise GatewayError("hidden or credential-like paths are unavailable")
        raw_target = self.root
        for part in candidate.parts:
            raw_target = raw_target / part
            if raw_target.is_symlink():
                raise GatewayError("symbolic links are unavailable")
        target = (self.root / candidate).resolve(strict=False)
        if not within(target, self.root):
            raise GatewayError("path escapes the workspace")
        if must_exist and not target.exists():
            raise GatewayError("path does not exist")
        if target.exists() and target.is_symlink():
            raise GatewayError("symbolic links are unavailable")
        return target, candidate

    def allow_phase(self, phase: str, operation: str, path: Any) -> str | None:
        if phase != "report_only":
            return None
        if operation in {"list", "read"}:
            return None
        if operation == "write" and path == "REPORT.md":
            return None
        return "after the exploration cutoff, only list/read and writing REPORT.md are allowed"

    def list_files(self, supplied: Any) -> dict[str, Any]:
        target, relative = self.relative_path(supplied, allow_root=True, must_exist=True)
        if not target.is_dir():
            raise GatewayError("list requires a directory")
        values: list[dict[str, Any]] = []
        for item in sorted(target.iterdir(), key=lambda p: p.name):
            child_relative = item.relative_to(self.root)
            if is_sensitive(child_relative) or item.is_symlink():
                continue
            values.append({"path": str(child_relative), "kind": "directory" if item.is_dir() else "file"})
            if len(values) >= MAX_LIST:
                break
        return {"path": str(relative), "entries": values, "truncated": len(values) >= MAX_LIST}

    def read_file(self, supplied: Any) -> dict[str, Any]:
        target, relative = self.relative_path(supplied, must_exist=True)
        if not target.is_file():
            raise GatewayError("read requires a regular file")
        if target.stat().st_size > MAX_BYTES:
            raise GatewayError("file exceeds the read limit")
        try:
            value = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise GatewayError("file is not UTF-8 text") from exc
        return {"path": str(relative), "text": redact(value), "sha256": digest(value), "bytes": len(value.encode("utf-8"))}

    def write_file(self, supplied: Any, content: Any) -> dict[str, Any]:
        target, relative = self.relative_path(supplied)
        if not isinstance(content, str):
            raise GatewayError("write content must be a string")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise GatewayError("content exceeds the write limit")
        # resolve() above detects a final existing symlink.  Resolve the parent
        # again after mkdir to close the common parent-symlink escape route.
        target.parent.mkdir(parents=True, exist_ok=True)
        parent = target.parent.resolve(strict=True)
        if not within(parent, self.root) or is_hidden(parent.relative_to(self.root)):
            raise GatewayError("write parent is unavailable")
        if target.exists() and target.is_symlink():
            raise GatewayError("symbolic links are unavailable")
        target.write_text(content, encoding="utf-8")
        return {"path": str(relative), "bytes": len(encoded), "sha256": digest(encoded)}

    def valid_argv(self, value: Any) -> list[str]:
        if not isinstance(value, list) or not value or len(value) > MAX_ARGV:
            raise GatewayError("exec argv must be a non-empty array of at most 64 strings")
        if any(not isinstance(part, str) or not part or "\x00" in part or len(part) > MAX_ARG_CHARS for part in value):
            raise GatewayError("exec argv must contain short, non-empty strings")
        return list(value)

    def platform_read(self, value: Any) -> dict[str, Any]:
        if self.platform_config is None:
            raise GatewayError("platform access is not configured for this arm")
        if not isinstance(value, dict):
            raise GatewayError("platform request must be an object")
        supplied = dict(value)
        if any(platform_key_forbidden(key) for key in supplied):
            raise GatewayError("platform requests may not override the selected script or credentials")
        method = supplied.get("method", supplied.get("operation"))
        arguments = supplied.get("arguments", supplied.get("args", {}))
        if method not in PLATFORM_METHODS or not isinstance(arguments, dict):
            raise GatewayError("platform method must be metadata, source_metadata, status, guide, auth_status, or source_body")
        # Drop unknown keys before entering the host-side reader.  The fixed
        # reader owns the pin and the only permitted upstream command.
        request = {"method": method, "arguments": arguments}
        try:
            encoded = json.dumps(request)
        except (TypeError, ValueError) as exc:
            raise GatewayError("platform request must be JSON") from exc
        if len(encoded) > MAX_BYTES:
            raise GatewayError("platform request exceeds the size limit")
        if self.platform_module is None:
            try:
                self.platform_module = importlib.import_module("gas_reader")
            except Exception as exc:
                raise GatewayError("authorized platform reader is unavailable") from exc
        call = getattr(self.platform_module, "call", None)
        if not callable(call):
            raise GatewayError("authorized platform reader is unavailable")
        try:
            response = call(request, self.platform_config)
            json.dumps(response)
        except Exception as exc:
            raise GatewayError("authorized platform reader returned no safe result") from exc
        return {"method": method, "result": redact_value(response)}

    def run_argv(self, argv: list[str], timeout_seconds: Any, *, validate_deadline: bool = True) -> dict[str, Any]:
        if validate_deadline:
            remaining = int(self.ledger.snapshot()["exploration_cutoff_epoch"] - time.time())
            if remaining <= 0:
                raise GatewayError("the exploration command window has closed")
        else:
            remaining = MAX_EXEC_SECONDS
        if timeout_seconds is None:
            requested = MAX_EXEC_SECONDS
        elif isinstance(timeout_seconds, int) and not isinstance(timeout_seconds, bool) and timeout_seconds > 0:
            requested = timeout_seconds
        else:
            raise GatewayError("timeout_seconds must be a positive integer")
        timeout = max(1, min(requested, MAX_EXEC_SECONDS, remaining))
        sandbox = Path("/usr/bin/sandbox-exec")
        if not sandbox.is_file():
            raise GatewayError("macOS sandbox-exec is unavailable; command execution is disabled")
        env = {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "TMPDIR": str(self.root / "tmp"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NO_PROXY": "localhost,127.0.0.1,::1",
            "no_proxy": "localhost,127.0.0.1,::1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        # Keep the real HOME path if one is present.  It is deliberately not
        # repointed to the fixture, and the sandbox profile does not grant it
        # readable paths.  The clean environment otherwise omits credentials.
        if "HOME" in os.environ:
            env["HOME"] = os.environ["HOME"]
        (self.root / "tmp").mkdir(exist_ok=True)
        (self.root / "cache").mkdir(exist_ok=True)
        started = time.monotonic()
        proc = subprocess.Popen(
            [str(sandbox), "-p", sandbox_profile(self.root), *argv],
            cwd=self.root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = proc.communicate()
        return {
            "argv": argv,
            "exit_code": proc.returncode,
            "timed_out": timed_out,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout": redact(stdout.decode("utf-8", errors="replace")[:MAX_BYTES]),
            "stderr": redact(stderr.decode("utf-8", errors="replace")[:MAX_BYTES]),
            "sandbox": "macos-sandbox-exec-loopback-only",
        }

    def call(self, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict) or params.get("name") != "workspace" or not isinstance(params.get("arguments"), dict):
            return result({"error": "workspace is the only available operation"}, error=True)
        arguments = params["arguments"]
        operation = arguments.get("operation")
        path = arguments.get("path")
        if not isinstance(operation, str):
            return result({"error": "operation is required"}, error=True)
        state, phase = self.ledger.consume(
            operation=operation,
            path=path if isinstance(path, str) else None,
        )
        if state is None:
            self.audit("budget_rejected", {"operation": operation, "reason": phase})
            return result({"error": phase, "budget": self.ledger.snapshot()}, error=True)
        phase_error = self.allow_phase(phase, operation, path)
        if phase_error:
            self.audit("phase_rejected", {"operation": operation, "call": state["tool_calls"]})
            return result({"error": phase_error, "call": state["tool_calls"], "phase": phase}, error=True)
        try:
            if operation == "list":
                payload = self.list_files(path)
            elif operation == "read":
                payload = self.read_file(path)
            elif operation == "write":
                payload = self.write_file(path, arguments.get("content"))
            elif operation == "exec":
                payload = self.run_argv(self.valid_argv(arguments.get("argv")), arguments.get("timeout_seconds"))
            elif operation == "platform":
                payload = self.platform_read(arguments.get("request"))
            else:
                raise GatewayError("operation must be list, read, write, exec, or configured platform")
            payload.update({"call": state["tool_calls"], "phase": phase})
            self.audit("workspace_call", {"operation": operation, "path": path, "call": state["tool_calls"], "phase": phase})
            return result(payload)
        except GatewayError as exc:
            self.audit("workspace_rejected", {"operation": operation, "path": path, "call": state["tool_calls"], "reason": str(exc)})
            return result({"error": str(exc), "call": state["tool_calls"], "phase": phase}, error=True)

    def handle(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return rpc_error(None, -32600, "JSON-RPC request must be an object")
        request_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            return rpc_error(request_id, -32600, "JSON-RPC method is required")
        if "id" not in message or method.startswith("notifications/"):
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": self.tool_schema()}
        if method == "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": self.call(message.get("params")),
            }
        return rpc_error(request_id, -32601, "method not found")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--start-epoch", type=float, default=time.time())
    parser.add_argument("--deadline-epoch", type=float)
    parser.add_argument("--cutoff-epoch", type=float)
    parser.add_argument("--call-limit", type=int, default=DEFAULT_CALL_LIMIT)
    parser.add_argument("--exploration-limit", type=int, default=DEFAULT_EXPLORATION_LIMIT)
    parser.add_argument("--config", type=Path, help="trusted per-arm gateway configuration")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--deny-canary", type=Path)
    args = parser.parse_args()
    if args.deadline_epoch is None:
        args.deadline_epoch = args.start_epoch + 900
    if args.cutoff_epoch is None:
        args.cutoff_epoch = min(args.start_epoch + DEFAULT_EXPLORATION_SECONDS, args.deadline_epoch - 120)
    if not (0 < args.exploration_limit <= args.call_limit <= 64):
        parser.error("limits must satisfy 0 < exploration-limit <= call-limit <= 64")
    if not (args.start_epoch < args.cutoff_epoch < args.deadline_epoch):
        parser.error("start, cutoff, and deadline must be ordered")
    return args


def direct_preflight(args: argparse.Namespace) -> int:
    """Prove both gateway path validation and the command sandbox reject a canary."""
    if args.deny_canary is None:
        print(json.dumps({"ok": False, "error": "--deny-canary is required for --self-test"}))
        return 2
    gateway = Gateway(args)
    try:
        canary = args.deny_canary.resolve(strict=True)
        path_rejected = False
        try:
            gateway.relative_path(str(canary), must_exist=True)
        except GatewayError:
            path_rejected = True
        sandbox_result = gateway.run_argv(["/bin/cat", str(canary)], 10, validate_deadline=False)
        sandbox_rejected = sandbox_result["exit_code"] != 0 and canary.name not in sandbox_result["stdout"]
        payload = {
            "ok": path_rejected and sandbox_rejected,
            "gateway_path_rejected": path_rejected,
            "sandbox_rejected": sandbox_rejected,
            "sandbox_exit_code": sandbox_result["exit_code"],
            "sandbox_stderr": sandbox_result["stderr"],
        }
        gateway.audit("self_test", payload)
        print(json.dumps(payload, sort_keys=True))
        return 0 if payload["ok"] else 1
    finally:
        gateway.close()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return direct_preflight(args)
    try:
        gateway = Gateway(args)
    except GatewayError as exc:
        print(f"gateway startup failed: {exc}", file=sys.stderr)
        return 2
    try:
        for raw in sys.stdin:
            raw = raw.rstrip("\r\n")
            if not raw:
                continue
            try:
                response = gateway.handle(json.loads(raw))
            except json.JSONDecodeError as exc:
                response = rpc_error(None, -32700, f"parse error: {exc.msg}")
            if response is not None:
                print(json.dumps(response, sort_keys=True), flush=True)
    finally:
        gateway.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
