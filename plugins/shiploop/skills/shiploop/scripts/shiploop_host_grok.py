"""Grok ACP transport for optional supervised ShipLoop owner sessions.

``session/new`` supplies a fresh conversation.  ``session/load`` resumes the
saved one.  The transport deliberately preserves the user's configured Grok
permission mode, sandbox, hooks, and MCP configuration. It force-disables
only Grok's cross-session memory in its child process, because ACP 1.0.34 has
no session-clear RPC and that memory would defeat a fresh boundary. It also
exposes no per-session writable-root or network restriction this launcher can
prove.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time

from shiploop_host import HostError


TransportError = HostError


class _RemoteError(HostError):
    """A normal JSON-RPC error response from Grok."""


class _InteractionRequired(HostError):
    """Grok asked this non-interactive launcher to make a host decision."""


class GrokTransport:
    """A sequential, native-permission ACP client for one supervised run.

    ``network_access`` and ``writable_roots`` are intentionally unsupported.
    ``None`` preserves the host's existing permission configuration; any
    explicit request fails before a Grok process is started rather than
    silently weakening it.  The child process force-disables Grok's separate
    cross-session memory feature, because it would defeat a fresh-context
    boundary even when ACP creates a new session.
    """

    capabilities = {
        "fresh_context": "session/new",
        "resume": "session/load",
        "usage": "native-session-prompt-meta",
        "permission_mode": "native-configured",
        "writable_roots": "unsupported",
        "network_access": "unsupported",
        "approval_relay": "unsupported",
        "cross_session_memory": "disabled-for-supervised-child",
        "fresh_process": "one-local-agent-process-per-new-or-resumed-session",
    }

    def __init__(
        self,
        cwd,
        *,
        writable_roots=None,
        timeout=3600,
        network_access=None,
        telemetry_grace=0.2,
    ):
        if writable_roots is not None:
            raise HostError(
                "Grok ACP cannot enforce launcher writable_roots; use native host permissions"
            )
        if network_access is not None:
            raise HostError(
                "Grok ACP cannot enforce launcher network_access; use native host permissions"
            )
        if timeout <= 0:
            raise HostError("Grok transport timeout must be positive")
        if telemetry_grace < 0:
            raise HostError("Grok transport telemetry_grace must not be negative")

        self.cwd = str(Path(cwd).resolve(strict=True))
        self.timeout = timeout
        self.telemetry_grace = telemetry_grace
        self.permission_metadata = {
            "mode": "native-configured",
            "requested_writable_roots": None,
            "requested_network_access": None,
            "mcpServers_parameter": [],
            "note": (
                "Grok may load configured plugins or MCP servers despite the empty ACP parameter; "
                "the launcher does not claim to isolate them."
            ),
        }
        self.host_metadata = {
            "host": "grok",
            "permissions": self.permission_metadata,
            "capabilities": dict(self.capabilities),
        }
        self._messages = queue.Queue()
        self._pending = []
        self._sequence = 0
        self._sessions = {}
        self._active_session = None
        self._process = None
        self._stderr = None
        self._process_generation = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _start_process(self):
        if self._process is not None:
            raise HostError("Grok transport already owns an active process")
        self._messages = queue.Queue()
        self._pending = []
        self._sequence = 0
        self._stderr = tempfile.TemporaryFile(mode="w+t")
        try:
            process = subprocess.Popen(
                ["grok", "agent", "--no-leader", "stdio"],
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr,
                text=True,
                bufsize=1,
                env={
                    **os.environ,
                    "SHIPLOOP_CONTEXT_HOST_WORKER": "1",
                    # Grok documents this as a process-wide force-disable. It
                    # leaves the user's stored memory and configuration alone.
                    "GROK_MEMORY": "0",
                },
            )
            self._process = process
            self._process_generation += 1
            threading.Thread(target=self._read, args=(process, self._messages), daemon=True).start()
            self._initialize()
        except BaseException:
            self._close_process()
            raise

    def _restart_process(self):
        self._close_process()
        self._start_process()

    @staticmethod
    def _read(process, messages):
        try:
            for line in process.stdout:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    value = {"invalid_protocol": True}
                messages.put(value)
        except (OSError, UnicodeError):
            messages.put({"invalid_protocol": True})
        finally:
            messages.put(None)

    def _send(self, value):
        try:
            if self._process is None:
                raise ValueError("Grok ACP process is not running")
            self._process.stdin.write(json.dumps(value) + "\n")
            self._process.stdin.flush()
        except (OSError, ValueError, AttributeError) as exc:
            raise HostError("Grok ACP input closed; inspect the pending owner") from exc

    def _receive(self, timeout):
        try:
            value = self._messages.get(timeout=timeout)
        except queue.Empty as exc:
            raise HostError("Grok ACP operation timed out; do not automatically replay the owner") from exc
        if value is None:
            raise HostError("Grok ACP exited before completion")
        if not isinstance(value, dict) or value.get("invalid_protocol"):
            raise HostError("Grok ACP returned invalid JSON")
        # A request from the agent (not a notification) can be a permission,
        # user-input, authentication, or other interactive decision.  A generic
        # JSON-RPC error is safe for every unimplemented request shape and never
        # approves a tool or changes host state.
        if "method" in value and "id" in value:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": value["id"],
                    "error": {
                        "code": -32001,
                        "message": "ShipLoop cannot relay or auto-approve host interaction",
                    },
                }
            )
            raise _InteractionRequired(
                "Grok requires interactive host action: " + str(value["method"])
            )
        return value

    def _remember(self, value):
        if "method" in value:
            self._pending.append(value)

    def _wait(self, predicate, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while True:
            for index, value in enumerate(self._pending):
                if predicate(value):
                    return self._pending.pop(index)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HostError("Grok ACP operation timed out; inspect the pending owner")
            value = self._receive(remaining)
            if predicate(value):
                return value
            self._remember(value)

    def _rpc(self, method, params, *, timeout=60):
        self._sequence += 1
        request_id = self._sequence
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        response = self._wait(lambda value: value.get("id") == request_id, timeout=timeout)
        if "error" in response:
            error = response["error"]
            message = error.get("message", error) if isinstance(error, dict) else error
            raise _RemoteError(f"Grok {method} failed: {message}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise HostError(f"Grok {method} returned no object result")
        return result

    def _initialize(self):
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": 1,
                # Do not advertise client-owned filesystem or terminal support.
                # The supervisor has neither an ACP file-service implementation
                # nor authority to make interactive host decisions for the user.
                "clientCapabilities": {},
            },
        )
        capabilities = result.get("agentCapabilities")
        if not isinstance(capabilities, dict) or capabilities.get("loadSession") is not True:
            raise HostError("Installed Grok ACP does not advertise session/load support")
        meta = result.get("_meta")
        if isinstance(meta, dict):
            self.host_metadata["agent_version"] = meta.get("agentVersion")

    @staticmethod
    def _session_id(result, method):
        session_id = result.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            raise HostError(f"Grok {method} returned no session identity")
        return session_id

    def _discard_session_notifications(self, session_id):
        def other_session(value):
            params = value.get("params")
            return not isinstance(params, dict) or params.get("sessionId") != session_id

        self._pending = [
            value
            for value in self._pending
            if other_session(value)
        ]

    def start_thread(self, repo):
        repo = str(Path(repo).resolve(strict=True))
        self._restart_process()
        result = self._rpc("session/new", {"cwd": repo, "mcpServers": []})
        session_id = self._session_id(result, "session/new")
        self._sessions[session_id] = repo
        self._active_session = session_id
        self._discard_session_notifications(session_id)
        return session_id

    def resume_thread(self, thread_id):
        if not isinstance(thread_id, str) or not thread_id:
            raise HostError("Grok session identity must be a nonempty string")
        repo = self._sessions.get(thread_id, self.cwd)
        self._restart_process()
        result = self._rpc(
            "session/load",
            {"sessionId": thread_id, "cwd": repo, "mcpServers": []},
        )
        actual = result.get("_meta", {}).get("sessionId")
        if actual != thread_id:
            raise HostError("Grok resumed a different session identity")
        self._sessions[thread_id] = repo
        self._active_session = thread_id
        self._discard_session_notifications(thread_id)
        return thread_id

    def _settle(self):
        deadline = time.monotonic() + self.telemetry_grace
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                self._remember(self._receive(remaining))
            except HostError as exc:
                if "timed out" in str(exc):
                    return
                raise

    def _prompt_text(self, session_id, prompt_id):
        parts, keep = [], []
        for value in self._pending:
            if value.get("method") != "session/update":
                keep.append(value)
                continue
            params = value.get("params", {})
            if not isinstance(params, dict):
                keep.append(value)
                continue
            meta = params.get("_meta", {})
            if not isinstance(meta, dict):
                meta = {}
            if params.get("sessionId") != session_id or meta.get("promptId") != prompt_id:
                keep.append(value)
                continue
            update = params.get("update", {})
            if not isinstance(update, dict):
                continue
            content = update.get("content", {})
            if not isinstance(content, dict):
                continue
            if update.get("sessionUpdate") == "agent_message_chunk" and content.get("type") == "text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
        self._pending = keep
        return "".join(parts)

    def run_turn(self, thread_id, prompt):
        if not isinstance(thread_id, str) or not thread_id:
            raise HostError("Grok session identity must be a nonempty string")
        if not isinstance(prompt, str):
            raise HostError("Grok prompt must be text")
        if self._active_session != thread_id:
            raise HostError("Grok session is not attached in this supervised process; resume it first")
        started = time.monotonic()
        try:
            result = self._rpc(
                "session/prompt",
                {
                    "sessionId": thread_id,
                    "prompt": [{"type": "text", "text": prompt}],
                },
                timeout=self.timeout,
            )
        except _RemoteError as exc:
            return {
                "status": "failed",
                "thread_id": thread_id,
                "turn_id": None,
                "text": "",
                "usage": None,
                "error": str(exc),
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        self._settle()
        meta = result.get("_meta") if isinstance(result.get("_meta"), dict) else {}
        prompt_id = meta.get("promptId")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise HostError("Grok session/prompt returned no prompt identity")
        usage = meta.get("usage") if isinstance(meta.get("usage"), dict) else None
        stop_reason = result.get("stopReason")
        completed = stop_reason == "end_turn"
        return {
            "status": "completed" if completed else "failed",
            "thread_id": thread_id,
            "turn_id": prompt_id,
            "text": self._prompt_text(thread_id, prompt_id),
            "usage": usage,
            "error": None if completed else "Grok prompt stop reason: " + repr(stop_reason),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }

    def _close_process(self):
        process, self._process = self._process, None
        self._active_session = None
        if process is not None:
            try:
                if process.stdin:
                    process.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            try:
                if process.stdout:
                    process.stdout.close()
            except (OSError, ValueError):
                pass
        if self._stderr is not None:
            self._stderr.close()
            self._stderr = None

    def close(self):
        self._close_process()

    @property
    def process_generation(self):
        """Monotonic count of locally owned Grok agent processes started."""
        return self._process_generation
