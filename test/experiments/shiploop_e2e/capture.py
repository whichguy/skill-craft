#!/usr/bin/env python3
"""Bounded, redacted subprocess capture for ShipLoop E2E experiment runs.

This deliberately knows nothing about a run's success criteria.  It records
process and stream observations so the caller can decide whether the resulting
repository and ShipLoop records satisfy its own contract.
"""

from __future__ import annotations

import codecs
import datetime as dt
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any, BinaryIO


CHUNK_BYTES = 16 * 1024
TICK_INTERVAL_SECONDS = 1.0
POST_EXIT_DRAIN_SECONDS = 0.40
TERM_GRACE_SECONDS = 0.50
KILL_DRAIN_SECONDS = 1.50
DEFAULT_MAX_EVENT_LINE_CHARS = 4 * 1024 * 1024
_NORMAL_HOLD_CHARS = 256
_REDACTED = "[redacted]"


_FIELD_NAME = (
    r"api[-_]?key|apikey|secret(?:[-_]?key)?|password|passwd|token|"
    r"access[-_]?token|refresh[-_]?token|client[-_]?secret|"
    r"private[-_]?key|auth(?:orization)?|credential|key"
)
_FIELD_PREFIX = re.compile(
    rf"(?i)(?<![A-Za-z0-9_-])(?:[\"'](?:{_FIELD_NAME})[\"']|(?:{_FIELD_NAME}))"
    r"\s*[:=]\s*(?P<quote>[\"']?)"
)
_FIELD_NAMES = frozenset(
    {
        "api-key",
        "api_key",
        "apikey",
        "secret",
        "secret-key",
        "secret_key",
        "password",
        "passwd",
        "token",
        "access-token",
        "access_token",
        "refresh-token",
        "refresh_token",
        "client-secret",
        "client_secret",
        "private-key",
        "private_key",
        "auth",
        "authorization",
        "credential",
        "key",
    }
)
_BEARER_PREFIX = re.compile(r"(?i)\bbearer[ \t]+")
_RAW_TOKEN_PREFIX = re.compile(r"(?i)(?<![A-Za-z0-9_])(?:sk|xai)[_-]")
_SECRET_DELIMITERS = frozenset(" \t\r\n,;\"'`<>()[]{}&#")


def _utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _utf8_prefix(data: bytes, limit: int) -> bytes:
    """Return a valid UTF-8 prefix no longer than ``limit`` bytes."""
    if limit <= 0:
        return b""
    if len(data) <= limit:
        return data
    end = limit
    while end:
        try:
            data[:end].decode("utf-8")
        except UnicodeDecodeError:
            end -= 1
            continue
        return data[:end]
    return b""


class _StreamingSanitizer:
    """Redact common credential forms without retaining an unbounded token.

    In normal mode, a small tail is retained to detect prefixes split between
    pipe reads.  Once a credential prefix is found, its value is discarded as
    it arrives until a safe delimiter closes the token.
    """

    def __init__(self) -> None:
        self._pending = ""
        self._secret_quote: str | None = None
        self._secret_escape = False

    def feed(self, text: str) -> str:
        if not text:
            return ""
        self._pending += text
        output: list[str] = []
        while self._pending:
            if self._secret_quote is not None:
                self._consume_secret(output)
                continue
            match, kind = self._next_prefix()
            if match is None:
                line_end = self._safe_complete_line_end()
                if line_end:
                    output.append(self._pending[:line_end])
                    self._pending = self._pending[line_end:]
                    continue
                safe_length = max(0, len(self._pending) - _NORMAL_HOLD_CHARS)
                if safe_length:
                    output.append(self._pending[:safe_length])
                    self._pending = self._pending[safe_length:]
                break
            output.append(self._pending[: match.start()])
            prefix = match.group(0)
            if kind == "raw_token":
                output.append(_REDACTED)
                self._secret_quote = ""
            else:
                output.append(prefix)
                output.append(_REDACTED)
                self._secret_quote = match.groupdict().get("quote") or ""
            self._secret_escape = False
            self._pending = self._pending[match.end() :]
        return "".join(output)

    def finish(self) -> str:
        """Flush a normal tail; an unfinished credential remains redacted."""
        if self._secret_quote is not None:
            self._pending = ""
            self._secret_quote = None
            self._secret_escape = False
            return ""
        output = self._pending
        self._pending = ""
        return output

    def _next_prefix(self) -> tuple[re.Match[str] | None, str | None]:
        candidates: list[tuple[re.Match[str], str]] = []
        for pattern, kind in (
            (_FIELD_PREFIX, "field"),
            (_BEARER_PREFIX, "bearer"),
            (_RAW_TOKEN_PREFIX, "raw_token"),
        ):
            match = pattern.search(self._pending)
            if match is not None:
                candidates.append((match, kind))
        if not candidates:
            return None, None
        return min(candidates, key=lambda item: (item[0].start(), item[0].end()))

    def _safe_complete_line_end(self) -> int:
        """Return the first flushable newline boundary in normal mode.

        A complete line normally breaks a token, so it can be made visible to
        a live observer immediately.  ``_FIELD_PREFIX`` deliberately permits
        whitespace between a field name and ``:`` or ``=``, including a
        newline.  Retain a possible field name until a non-whitespace next
        character proves it cannot become that prefix.
        """
        newline = self._pending.find("\n")
        if newline < 0:
            return 0
        if not self._unfinished_field_name(self._pending[:newline]):
            return newline + 1
        continuation = self._pending[newline + 1 :]
        if continuation and not continuation.isspace():
            return newline + 1
        return 0

    @staticmethod
    def _unfinished_field_name(line: str) -> bool:
        candidate = line.rstrip(" \t\r")
        if candidate.endswith(("'", '\"')):
            candidate = candidate[:-1]
        match = re.search(
            r"(?i)(?<![A-Za-z0-9_-])(?:[\"'])?(?P<name>[A-Za-z_-]+)$",
            candidate,
        )
        if match is None:
            return False
        fragment = match.group("name").casefold()
        return any(name.startswith(fragment) for name in _FIELD_NAMES)

    def _consume_secret(self, output: list[str]) -> None:
        quote = self._secret_quote
        if quote:
            index = 0
            while index < len(self._pending):
                character = self._pending[index]
                if self._secret_escape:
                    self._secret_escape = False
                elif character == "\\":
                    self._secret_escape = True
                elif character == quote:
                    output.append(character)
                    self._pending = self._pending[index + 1 :]
                    self._secret_quote = None
                    self._secret_escape = False
                    return
                index += 1
            self._pending = ""
            return

        for index, character in enumerate(self._pending):
            if character in _SECRET_DELIMITERS:
                output.append(character)
                self._pending = self._pending[index + 1 :]
                self._secret_quote = None
                return
        self._pending = ""


def _sanitize_text(value: str) -> str:
    sanitizer = _StreamingSanitizer()
    return sanitizer.feed(value) + sanitizer.finish()


class _BoundedLog:
    """A bounded UTF-8 writer that never leaves a partial code point on disk."""

    def __init__(self, handle: BinaryIO, maximum: int) -> None:
        self._handle = handle
        self._maximum = maximum
        self._lock = threading.Lock()
        self.written_bytes = 0
        self.dropped_bytes = 0
        self.truncated = False

    def write_text(self, text: str) -> None:
        if not text:
            return
        data = text.encode("utf-8", errors="replace")
        with self._lock:
            available = self._maximum - self.written_bytes
            kept = _utf8_prefix(data, available)
            if kept:
                self._handle.write(kept)
                self._handle.flush()
                self.written_bytes += len(kept)
            if len(kept) != len(data):
                self.dropped_bytes += len(data) - len(kept)
                self.truncated = True


class _EventLog:
    """Bound events by whole NDJSON records so the file stays parseable."""

    def __init__(self, handle: BinaryIO, maximum: int) -> None:
        self._handle = handle
        self._maximum = maximum
        self._lock = threading.Lock()
        self.written = 0
        self.dropped = 0
        self.written_bytes = 0
        self.dropped_bytes = 0
        self.truncated = False

    def write_event(self, value: dict[str, Any]) -> None:
        data = (
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
            + "\n"
        ).encode("utf-8", errors="replace")
        with self._lock:
            if len(data) <= self._maximum - self.written_bytes:
                self._handle.write(data)
                self._handle.flush()
                self.written += 1
                self.written_bytes += len(data)
                return
            self.dropped += 1
            self.dropped_bytes += len(data)
            self.truncated = True


class _StreamCapture:
    def __init__(
        self,
        name: str,
        log: _BoundedLog,
        events: _EventLog,
        max_event_line_chars: int,
    ) -> None:
        self.name = name
        self.log = log
        self.events = events
        self._max_event_line_chars = max_event_line_chars
        self.sanitizer = _StreamingSanitizer()
        self._line = ""
        self._line_dropped_characters = 0
        self._lock = threading.Lock()
        self.received_bytes = 0
        self.lines = 0
        self.invalid_json_lines = 0
        self.line_truncations = 0
        self.line_dropped_characters = 0

    def received(self, size: int) -> None:
        with self._lock:
            self.received_bytes += size

    def consume(self, text: str) -> None:
        safe = self.sanitizer.feed(text)
        self._consume_safe(safe)

    def finish(self) -> None:
        self._consume_safe(self.sanitizer.finish())
        if self._line or self._line_dropped_characters:
            self._emit_line()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "received_bytes": self.received_bytes,
                "written_bytes": self.log.written_bytes,
                "dropped_bytes": self.log.dropped_bytes,
                "truncated": self.log.truncated,
                "lines": self.lines,
                "invalid_json_lines": self.invalid_json_lines,
                "line_truncations": self.line_truncations,
                "line_dropped_characters": self.line_dropped_characters,
            }

    def _consume_safe(self, safe: str) -> None:
        if not safe:
            return
        self.log.write_text(safe)
        fragments = safe.split("\n")
        for fragment in fragments[:-1]:
            self._append_line(fragment)
            self._emit_line()
        self._append_line(fragments[-1])

    def _append_line(self, text: str) -> None:
        if not text:
            return
        remaining = self._max_event_line_chars - len(self._line)
        if remaining > 0:
            self._line += text[:remaining]
        if len(text) > remaining:
            self._line_dropped_characters += len(text) - max(remaining, 0)

    def _emit_line(self) -> None:
        line = self._line[:-1] if self._line.endswith("\r") else self._line
        dropped = self._line_dropped_characters
        self._line = ""
        self._line_dropped_characters = 0
        record: dict[str, Any] = {
            "received_at": _utc_now(),
            "stream": self.name,
            "line": line,
        }
        with self._lock:
            self.lines += 1
            if dropped:
                self.line_truncations += 1
                self.line_dropped_characters += dropped
        if dropped:
            record["line_truncated"] = True
            record["line_dropped_characters"] = dropped
        if line:
            try:
                # Preserve native event values unchanged, including unfamiliar
                # event ``type`` values.  This helper never assigns meaning.
                record["payload"] = json.loads(line)
            except json.JSONDecodeError:
                with self._lock:
                    self.invalid_json_lines += 1
        self.events.write_event(record)


class _CaptureError:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: str | None = None

    def set(self, source: str, exc: BaseException) -> None:
        message = _sanitize_text(f"{source}: {type(exc).__name__}: {exc}")[:1000]
        with self._lock:
            if self._value is None:
                self._value = message

    def value(self) -> str | None:
        with self._lock:
            return self._value


def _signal_group(process: subprocess.Popen[bytes], sig: signal.Signals) -> bool:
    try:
        if os.name == "posix":
            os.killpg(process.pid, sig)
        elif sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
        return True
    except (ProcessLookupError, OSError):
        return False


def _alive(readers: list[threading.Thread]) -> bool:
    return any(reader.is_alive() for reader in readers)


def _join_for(readers: list[threading.Thread], seconds: float) -> None:
    end = time.monotonic() + seconds
    for reader in readers:
        remaining = end - time.monotonic()
        if remaining <= 0:
            return
        reader.join(remaining)


def _stop_and_drain(
    process: subprocess.Popen[bytes],
    readers: list[threading.Thread],
    stop_readers: threading.Event,
    pipes: list[BinaryIO],
) -> dict[str, bool]:
    """Terminate the private group, then reap and drain for bounded periods."""
    receipt = {"term_sent": _signal_group(process, signal.SIGTERM), "kill_sent": False}
    term_deadline = time.monotonic() + TERM_GRACE_SECONDS
    while time.monotonic() < term_deadline and (process.poll() is None or _alive(readers)):
        _join_for(readers, 0.05)
        time.sleep(0.01)
    if process.poll() is None or _alive(readers):
        receipt["kill_sent"] = _signal_group(process, signal.SIGKILL)
    try:
        process.wait(timeout=KILL_DRAIN_SECONDS)
    except subprocess.TimeoutExpired:
        # The caller still returns a bounded observation.  Daemon reader
        # threads cannot keep the host interpreter alive in this case.
        pass
    _join_for(readers, KILL_DRAIN_SECONDS)
    if _alive(readers):
        stop_readers.set()
        for pipe in pipes:
            try:
                pipe.close()
            except OSError:
                pass
        _join_for(readers, 0.20)
    return receipt


def _reader(
    pipe: BinaryIO,
    stream: _StreamCapture,
    stop_readers: threading.Event,
    errors: _CaptureError,
) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    try:
        while not stop_readers.is_set():
            read1 = getattr(pipe, "read1", None)
            raw = read1(CHUNK_BYTES) if read1 is not None else pipe.read(CHUNK_BYTES)
            if not raw:
                break
            stream.received(len(raw))
            stream.consume(decoder.decode(raw, final=False))
        if not stop_readers.is_set():
            stream.consume(decoder.decode(b"", final=True))
    except (OSError, ValueError) as exc:
        if not stop_readers.is_set():
            errors.set(f"{stream.name}_reader", exc)
    except Exception as exc:  # retain the observation and stop the group safely
        errors.set(f"{stream.name}_reader", exc)
    finally:
        try:
            stream.finish()
        except Exception as exc:
            errors.set(f"{stream.name}_finish", exc)


def _validate_arguments(
    argv: list[str],
    timeout_seconds: float,
    max_log_bytes: int,
    env: dict[str, str] | None,
    max_event_line_chars: int,
) -> None:
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("argv must be a non-empty list of non-empty strings")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive number")
    if isinstance(max_log_bytes, bool) or not isinstance(max_log_bytes, int) or max_log_bytes < 0:
        raise ValueError("max_log_bytes must be a non-negative integer")
    if (
        isinstance(max_event_line_chars, bool)
        or not isinstance(max_event_line_chars, int)
        or max_event_line_chars <= 0
    ):
        raise ValueError("max_event_line_chars must be a positive integer")
    if env is not None and (
        not isinstance(env, dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in env.items())
    ):
        raise ValueError("env must be a string-to-string dictionary or None")


def capture_process(
    argv: list[str],
    cwd: Path,
    output: Path,
    timeout_seconds: float,
    env: dict[str, str] | None = None,
    on_tick: Callable[[], object] | None = None,
    max_log_bytes: int = 50_000_000,
    should_stop: Callable[[], bool] | None = None,
    max_event_line_chars: int = DEFAULT_MAX_EVENT_LINE_CHARS,
) -> dict[str, Any]:
    """Capture one argv process without assigning a semantic result.

    ``stdout.log``, ``stderr.log``, and ``events.jsonl`` are created under
    ``output``.  The return value contains process facts and capture bounds;
    callers must independently judge repository changes, run state, and
    delivery outcomes.  All persisted process text is redacted before write.
    ``should_stop`` is an optional observer-controlled boundary; when it
    returns true while the process is live, the private process group is
    terminated and the resulting observation is marked ``requested_boundary``.
    """
    _validate_arguments(argv, timeout_seconds, max_log_bytes, env, max_event_line_chars)
    cwd_path = Path(cwd).resolve()
    output_path = Path(output).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    stdout_path = output_path / "stdout.log"
    stderr_path = output_path / "stderr.log"
    events_path = output_path / "events.jsonl"
    started_at = _utc_now()
    started_monotonic = time.monotonic()
    capture_errors = _CaptureError()
    process: subprocess.Popen[bytes] | None = None
    readers: list[threading.Thread] = []
    stop_readers = threading.Event()
    termination_reason: str | None = None
    timed_out = False
    group_termination = {"term_sent": False, "kill_sent": False}

    with (
        stdout_path.open("wb") as stdout_file,
        stderr_path.open("wb") as stderr_file,
        events_path.open("wb") as events_file,
    ):
        stdout_stream = _StreamCapture(
            "stdout",
            _BoundedLog(stdout_file, max_log_bytes),
            _EventLog(events_file, max_log_bytes),
            max_event_line_chars,
        )
        # Both streams share the same event file and its lock; use the stdout
        # event writer as the common event ledger.
        stderr_stream = _StreamCapture(
            "stderr",
            _BoundedLog(stderr_file, max_log_bytes),
            stdout_stream.events,
            max_event_line_chars,
        )
        try:
            process = subprocess.Popen(
                argv,
                cwd=os.fspath(cwd_path),
                env=None if env is None else dict(env),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except Exception as exc:
            capture_errors.set("spawn", exc)
            termination_reason = "capture_error"
        else:
            assert process.stdout is not None and process.stderr is not None
            pipes: list[BinaryIO] = [process.stdout, process.stderr]
            readers = [
                threading.Thread(
                    target=_reader,
                    args=(process.stdout, stdout_stream, stop_readers, capture_errors),
                    name="shiploop-e2e-stdout",
                    daemon=True,
                ),
                threading.Thread(
                    target=_reader,
                    args=(process.stderr, stderr_stream, stop_readers, capture_errors),
                    name="shiploop-e2e-stderr",
                    daemon=True,
                ),
            ]
            for reader in readers:
                reader.start()
            deadline = started_monotonic + float(timeout_seconds)
            last_tick = started_monotonic
            parent_exited_at: float | None = None
            try:
                while True:
                    now = time.monotonic()
                    if capture_errors.value() is not None:
                        termination_reason = "capture_error"
                        group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                        break
                    if now >= deadline:
                        timed_out = True
                        termination_reason = "timeout"
                        group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                        break
                    exit_code = process.poll()
                    if exit_code is not None:
                        if not _alive(readers):
                            break
                        if parent_exited_at is None:
                            parent_exited_at = now
                        elif now - parent_exited_at >= POST_EXIT_DRAIN_SECONDS:
                            termination_reason = "descendant_pipe_holders"
                            group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                            break
                    elif should_stop is not None:
                        try:
                            requested_stop = should_stop()
                        except Exception as exc:
                            capture_errors.set("should_stop", exc)
                            termination_reason = "capture_error"
                            group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                            break
                        if requested_stop:
                            termination_reason = "requested_boundary"
                            group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                            break
                    if on_tick is not None and now - last_tick >= TICK_INTERVAL_SECONDS:
                        try:
                            on_tick()
                        except Exception as exc:
                            capture_errors.set("on_tick", exc)
                            termination_reason = "capture_error"
                            group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                            break
                        last_tick = now
                    time.sleep(0.02)
            except BaseException as exc:
                capture_errors.set("capture", exc)
                termination_reason = "capture_error"
                group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
            finally:
                if termination_reason is None:
                    _join_for(readers, KILL_DRAIN_SECONDS)
                    if _alive(readers):
                        termination_reason = "descendant_pipe_holders"
                        group_termination = _stop_and_drain(process, readers, stop_readers, pipes)
                for pipe in pipes:
                    try:
                        pipe.close()
                    except OSError:
                        pass

        finished_at = _utc_now()
        duration_seconds = round(time.monotonic() - started_monotonic, 6)
        streams = {"stdout": stdout_stream.snapshot(), "stderr": stderr_stream.snapshot()}
        events = stdout_stream.events
        result: dict[str, Any] = {
            "argv": [_sanitize_text(item) for item in argv],
            "cwd": str(cwd_path),
            "output": str(output_path),
            "pid": None if process is None else process.pid,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration_seconds,
            "exit_code": None if process is None else process.returncode,
            "termination_reason": termination_reason,
            "timed_out": timed_out,
            "capture_error": capture_errors.value(),
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
            "events_file": str(events_path),
            "capture_limits": {
                "max_log_bytes": max_log_bytes,
                "max_event_line_chars": max_event_line_chars,
            },
            "streams": streams,
            "events": {
                "written": events.written,
                "dropped": events.dropped,
                "written_bytes": events.written_bytes,
                "dropped_bytes": events.dropped_bytes,
                "truncated": events.truncated,
            },
        }
        result["invalid_json_count"] = sum(row["invalid_json_lines"] for row in streams.values())
        result["truncated"] = bool(
            events.truncated or any(row["truncated"] or row["line_truncations"] for row in streams.values())
        )
        result["dropped_bytes"] = events.dropped_bytes + sum(row["dropped_bytes"] for row in streams.values())
        result["group_termination"] = group_termination
        return result


__all__ = ["capture_process"]
