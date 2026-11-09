"""Strict raw JSONL evidence reader. Parse success only establishes structural integrity."""
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import stat

# The ShipLoop writer stops appending at this size.
TRACE_LIMIT = 32 * 1024 * 1024


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError(f"non-JSON constant {value}")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number exceeds the finite float range")
    return result


def _parse_object(text: str) -> dict:
    value = json.loads(text, object_pairs_hook=_object, parse_constant=_nonfinite, parse_float=_float)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def read_trace(path: Path) -> dict:
    """Return raw object rows with one-based source lines and a SHA-256 of retained bytes.

    No skipped lines or partial results. The file must be a stable regular file,
    below the writer cap, with at least one newline-terminated UTF-8 JSON object.
    The caller must establish lifecycle coverage from the recorded facts.
    """
    result = {"status": "unavailable", "rows": [], "sha256": None, "reason": None}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                return dict(result, status="invalid", reason="source is not a regular file")
            if before.st_size >= TRACE_LIMIT:
                return dict(result, status="invalid", reason="source reached the trace size cap")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                data = handle.read(TRACE_LIMIT)
            after = os.fstat(fd)
            named = path.lstat()
            if (len(data) != before.st_size
                    or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                    or (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino)):
                return dict(result, status="invalid", reason="source changed during read")
        finally:
            os.close(fd)
    except OSError as exc:
        status = "invalid" if exc.errno == errno.ELOOP else "unavailable"
        # Some nonregular paths (such as sockets) cannot be opened for fstat.
        try:
            if not stat.S_ISREG(path.lstat().st_mode):
                return dict(result, status="invalid", reason="source is not a regular file")
        except OSError:
            pass
        return dict(result, status=status, reason=f"source cannot be read ({exc.strerror})")
    except ValueError as exc:
        return dict(result, status="invalid", reason=f"invalid source path ({exc})")

    result["sha256"] = hashlib.sha256(data).hexdigest()
    if not data:
        return dict(result, reason="source is empty")
    if not data.endswith(b"\n"):
        return dict(result, status="invalid", reason="source has an unterminated final line")
    rows = []
    for number, line in enumerate(data[:-1].split(b"\n"), 1):
        try:
            record = _parse_object(line.decode("utf-8"))
        except (ValueError, RecursionError) as exc:
            return dict(result, status="invalid", reason=f"line {number}: {exc}")
        rows.append({"line": number, "record": record})
    return dict(result, status="ok", rows=rows)
