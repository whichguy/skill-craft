"""Claude Code CLI transport for optional supervised ShipLoop owner sessions.

Each turn is a short-lived ``claude -p`` process.  A generated session UUID
starts a fresh Claude conversation; later turns use ``--resume`` with the same
UUID.  The CLI does not expose a writable-root or network sandbox equivalent
to Codex's app-server policy, so callers must leave those arguments unset or
receive a controlled capability error rather than a misleading enforcement
claim.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
import uuid
from typing import Any, Dict, Iterable, Optional

from shiploop_host import HostError


TransportError = HostError


class ClaudeTransport:
    """Subscription-authenticated Claude CLI session transport.

    Native Claude Code settings and permissions remain in force.  This class
    deliberately does not use ``--bare``, bypass-permission options, or any
    global configuration changes.
    """

    def __init__(
        self,
        cwd: str | Path,
        *,
        writable_roots: Optional[Iterable[str | Path]] = None,
        timeout: float = 3600,
        network_access: Optional[bool] = None,
    ) -> None:
        root = Path(cwd).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise HostError("Claude host cwd must be a directory")
        if writable_roots is not None:
            raise HostError(
                "Claude CLI cannot enforce requested writable roots; "
                "use native host permissions or select a host with a writable-root sandbox"
            )
        if network_access is False:
            raise HostError(
                "Claude CLI cannot enforce requested network denial; "
                "use native host permissions or select a host with a network sandbox"
            )
        if isinstance(timeout, bool) or timeout <= 0:
            raise ValueError("timeout must be positive")

        self.cwd = str(root)
        self.timeout = timeout
        self.network_access = network_access
        self._closed = False
        self._known_threads: set[str] = set()
        self._new_threads: set[str] = set()

    def __enter__(self) -> "ClaudeTransport":
        self._require_open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def capabilities(self) -> Dict[str, Any]:
        """Machine-readable host facts for receipts and operator diagnosis."""
        return {
            "host": "claude",
            "fresh_context": "new-session-id",
            "session_resume": "claude -p --resume",
            "literal_clear": "not-invoked-by-transport",
            "writable_roots": "unsupported",
            "network_access": "unsupported",
        }

    @property
    def permission_metadata(self) -> Dict[str, Any]:
        """Describe the actual permission model without claiming isolation."""
        return {
            "mode": "existing-native-claude-cli-permissions",
            "requested_network_access": self.network_access,
            "enforced_writable_roots": False,
            "enforced_network_access": False,
            "uses_bare_mode": False,
            "uses_permission_bypass": False,
        }

    def _require_open(self) -> None:
        if self._closed:
            raise HostError("Claude transport is closed")

    @staticmethod
    def _validate_thread_id(thread_id: str) -> str:
        if not isinstance(thread_id, str) or not thread_id:
            raise HostError("Claude session id must be a non-empty UUID string")
        try:
            uuid.UUID(thread_id)
        except (AttributeError, ValueError) as exc:
            raise HostError("Claude session id must be a UUID") from exc
        return thread_id

    def start_thread(self, repo: str | Path) -> str:
        """Allocate a fresh persistent Claude session identity for ``repo``."""
        self._require_open()
        target = Path(repo).expanduser().resolve(strict=True)
        if not target.is_dir():
            raise HostError("Claude repository must be a directory")
        if str(target) != self.cwd:
            raise HostError("Claude session repository must match its configured cwd")
        thread_id = str(uuid.uuid4())
        self._known_threads.add(thread_id)
        self._new_threads.add(thread_id)
        return thread_id

    def resume_thread(self, thread_id: str) -> str:
        """Attach a persisted session ID; its first local turn uses ``--resume``."""
        self._require_open()
        thread_id = self._validate_thread_id(thread_id)
        self._known_threads.add(thread_id)
        self._new_threads.discard(thread_id)
        return thread_id

    def _result(
        self,
        *,
        status: str,
        thread_id: str,
        turn_id: Optional[str] = None,
        text: str = "",
        usage: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        elapsed_seconds: float,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "thread_id": thread_id,
            "turn_id": turn_id,
            "text": text,
            "usage": usage,
            "error": error,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "capabilities": self.capabilities,
            "permission_metadata": self.permission_metadata,
        }

    @staticmethod
    def _short_error(value: object, fallback: str) -> str:
        text = str(value or "").strip()
        return (text or fallback)[:2000]

    def run_turn(self, thread_id: str, prompt: str) -> Dict[str, Any]:
        """Run one owner turn and return a completed/failed receipt dictionary."""
        self._require_open()
        thread_id = self._validate_thread_id(thread_id)
        if thread_id not in self._known_threads:
            raise HostError("Claude session is unknown; call start_thread or resume_thread first")
        if not isinstance(prompt, str):
            raise TypeError("prompt must be text")

        is_new = thread_id in self._new_threads
        # Mark it attempted before launch.  A timeout or transport failure can
        # leave a server-side session behind, so automatic retry must resume it.
        self._new_threads.discard(thread_id)
        argv = ["claude", "-p", prompt, "--output-format", "json"]
        argv.extend(["--session-id" if is_new else "--resume", thread_id])
        started = time.monotonic()
        try:
            completed = subprocess.run(
                argv,
                cwd=self.cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                check=False,
                env={**os.environ, "SHIPLOOP_CONTEXT_HOST_WORKER": "1"},
            )
        except subprocess.TimeoutExpired:
            return self._result(
                status="failed",
                thread_id=thread_id,
                error=(f"Claude CLI timed out after {self.timeout} seconds; "
                       "do not automatically replay the owner"),
                elapsed_seconds=time.monotonic() - started,
            )
        except OSError as exc:
            return self._result(
                status="failed",
                thread_id=thread_id,
                error=self._short_error(exc, "Claude CLI could not start"),
                elapsed_seconds=time.monotonic() - started,
            )

        elapsed = time.monotonic() - started
        try:
            payload = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            return self._result(
                status="failed",
                thread_id=thread_id,
                error=self._short_error(
                    completed.stderr,
                    "Claude CLI did not return one JSON result object",
                ),
                elapsed_seconds=elapsed,
            )
        if not isinstance(payload, dict):
            return self._result(
                status="failed",
                thread_id=thread_id,
                error="Claude CLI did not return one JSON result object",
                elapsed_seconds=elapsed,
            )

        actual_thread = payload.get("session_id")
        turn_id = payload.get("uuid") if isinstance(payload.get("uuid"), str) else None
        text = payload.get("result") if isinstance(payload.get("result"), str) else ""
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else None
        if actual_thread != thread_id:
            return self._result(
                status="failed",
                thread_id=thread_id,
                turn_id=turn_id,
                text=text,
                usage=usage,
                error="Claude CLI returned a different session identity",
                elapsed_seconds=elapsed,
            )

        success = (
            completed.returncode == 0
            and payload.get("is_error") is False
            and payload.get("subtype", "success") == "success"
        )
        if success:
            return self._result(
                status="completed",
                thread_id=thread_id,
                turn_id=turn_id,
                text=text,
                usage=usage,
                elapsed_seconds=elapsed,
            )
        error = payload.get("api_error_status") or payload.get("result") or completed.stderr
        return self._result(
            status="failed",
            thread_id=thread_id,
            turn_id=turn_id,
            text=text,
            usage=usage,
            error=self._short_error(error, f"Claude CLI exited {completed.returncode}"),
            elapsed_seconds=elapsed,
        )

    def close(self) -> None:
        """Mark this short-lived-process transport closed; persistent sessions remain resumable."""
        self._closed = True
