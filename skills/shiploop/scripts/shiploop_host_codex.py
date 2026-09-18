"""Codex app-server transport for optional supervised ShipLoop sessions.

Fresh threads discard previous conversational input. This module does not change
the current desktop task or install/configure a host integration.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import tempfile
import threading
import time
from pathlib import Path


from shiploop_host import HostError

TransportError = HostError


class CodexTransport:
    _TURN_EVENTS = {
        "item/completed", "turn/completed", "thread/tokenUsage/updated",
    }

    def __init__(self, cwd, *, writable_roots=None, timeout=3600, network_access=False,
                 telemetry_grace=0.2):
        self.cwd = str(Path(cwd).resolve(strict=True))
        self.writable_roots = [str(Path(p).resolve(strict=True))
                               for p in (writable_roots or [self.cwd])]
        self.timeout = timeout
        self.network_access = network_access
        if telemetry_grace < 0:
            raise ValueError("telemetry_grace must not be negative")
        self.telemetry_grace = telemetry_grace
        self._messages = queue.Queue()
        self._sequence = 0
        self._pending = []
        self._totals = {}
        self._completed_turns = set()
        self._stderr = tempfile.TemporaryFile(mode="w+t")
        self._process = None
        try:
            self._process = subprocess.Popen(
                ["codex", "app-server", "--stdio"], cwd=self.cwd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                text=True, bufsize=1,
                env={**os.environ, "SHIPLOOP_CONTEXT_HOST_WORKER": "1"},
            )
            threading.Thread(target=self._read, daemon=True).start()
            self._rpc("initialize", {
                "clientInfo": {"name": "shiploop_context_host", "title": None, "version": "0.14.0"},
                "capabilities": None,
            })
            self._send({"method": "initialized"})
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _read(self):
        try:
            for line in self._process.stdout:
                try:
                    self._messages.put(json.loads(line))
                except json.JSONDecodeError:
                    self._messages.put({"invalid_protocol": True})
        except (OSError, UnicodeError):
            self._messages.put({"invalid_protocol": True})
        finally:
            self._messages.put(None)

    def _send(self, value):
        try:
            self._process.stdin.write(json.dumps(value) + "\n")
            self._process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise TransportError("Codex app-server input closed; inspect the pending owner") from exc

    def _receive(self, timeout):
        value = self._messages.get(timeout=timeout)
        if value is None:
            raise TransportError("Codex app-server exited before completion")
        if "invalid_protocol" in value:
            raise TransportError("Codex app-server returned invalid JSON")
        if "method" in value and "id" in value:
            self._send({"id": value["id"], "error": {
                "code": -32601, "message": "The context host cannot relay approvals or user input",
            }})
            raise TransportError("Codex requires host interaction: " + value["method"])
        return value

    def _remember(self, value):
        method = value.get("method")
        if "id" not in value and method not in self._TURN_EVENTS | {"error"}:
            return
        params = value.get("params", {})
        if (method in self._TURN_EVENTS
                and (params.get("threadId"), params.get("turnId")) in self._completed_turns):
            return
        self._pending.append(value)

    def _wait(self, predicate, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while True:
            for index, value in enumerate(self._pending):
                if predicate(value):
                    return self._pending.pop(index)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransportError("Codex operation timed out; do not automatically replay the owner")
            try:
                self._remember(self._receive(remaining))
            except queue.Empty as exc:
                raise TransportError("Codex operation timed out; inspect the pending owner") from exc

    def _collect_completed_turn_events(self, thread_id, turn_id):
        deadline = time.monotonic() + self.telemetry_grace
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                self._remember(self._receive(remaining))
            except queue.Empty:
                break

        relevant, keep = [], []
        for event in self._pending:
            params = event.get("params", {})
            if params.get("threadId") == thread_id and params.get("turnId") == turn_id:
                relevant.append(event)
            elif (event.get("method") in self._TURN_EVENTS
                  and params.get("threadId") == thread_id
                  and params.get("turnId") is not None):
                # This transport runs one owner at a time. A prior turn's late
                # notification cannot change the current turn's accounting.
                continue
            else:
                keep.append(event)
        self._pending = keep
        self._completed_turns.add((thread_id, turn_id))
        return relevant

    def _rpc(self, method, params):
        self._sequence += 1
        request_id = self._sequence
        self._send({"id": request_id, "method": method, "params": params})
        response = self._wait(lambda value: value.get("id") == request_id, timeout=60)
        if "error" in response:
            error = response["error"]
            raise TransportError(f"{method} failed: {error.get('message', error)}")
        return response["result"]

    def start_thread(self, repo):
        result = self._rpc("thread/start", {
            "cwd": str(Path(repo).resolve(strict=True)),
            "approvalPolicy": "never", "sandbox": "workspace-write", "ephemeral": False,
        })
        thread_id = result["thread"]["id"]
        self._totals[thread_id] = {
            name: 0 for name in ("totalTokens", "inputTokens", "cachedInputTokens",
                                "cacheWriteInputTokens", "outputTokens", "reasoningOutputTokens")
        }
        return thread_id

    def resume_thread(self, thread_id):
        result = self._rpc("thread/resume", {
            "threadId": thread_id, "excludeTurns": True,
            "approvalPolicy": "never", "sandbox": "workspace-write",
        })
        actual = result["thread"]["id"]
        if actual != thread_id:
            raise TransportError("Codex resumed a different task identity")
        # On reconnect the prior cumulative telemetry is unknown, not zero.
        self._totals.pop(thread_id, None)
        return actual

    def run_turn(self, thread_id, prompt):
        started = time.monotonic()
        previous = self._totals.get(thread_id)
        result = self._rpc("turn/start", {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt, "text_elements": []}],
            "sandboxPolicy": {
                "type": "workspaceWrite", "writableRoots": self.writable_roots,
                "networkAccess": self.network_access,
                "excludeTmpdirEnvVar": True, "excludeSlashTmp": True,
            },
        })
        turn_id = result["turn"]["id"]
        completed = self._wait(lambda value: (
            value.get("method") == "turn/completed"
            and value["params"].get("threadId") == thread_id
            and value["params"]["turn"]["id"] == turn_id
        ))
        relevant = self._collect_completed_turn_events(thread_id, turn_id)
        items = [event["params"]["item"] for event in relevant
                 if event.get("method") == "item/completed"]
        tokens = [event["params"]["tokenUsage"] for event in relevant
                  if event.get("method") == "thread/tokenUsage/updated"]
        usage = None
        if tokens:
            latest = tokens[-1]
            total = latest["total"]
            delta = None if previous is None else {
                name: total[name] - previous[name] for name in total if name in previous
            }
            if delta is not None and any(n < 0 for n in delta.values()):
                delta = None
            usage = {"last_model_call": latest["last"], "thread_total": total,
                     "turn_delta": delta, "model_context_window": latest.get("modelContextWindow")}
            self._totals[thread_id] = dict(total)
        else:
            # A later cumulative total would span this unmeasured turn as well.
            self._totals.pop(thread_id, None)
        turn = completed["params"]["turn"]
        return {
            "status": turn["status"], "thread_id": thread_id, "turn_id": turn_id,
            "text": "\n".join(item["text"] for item in items if item["type"] == "agentMessage"),
            "usage": usage, "error": turn.get("error"),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }

    def close(self):
        process = self._process
        if process is not None:
            try:
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
            if process.stdout:
                process.stdout.close()
        self._stderr.close()
