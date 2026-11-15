"""Bounded no-follow observation primitives; no workflow writes or recovery."""
from __future__ import annotations
import os
import stat
from pathlib import Path
import hashlib
import math
from datetime import datetime, timezone
import shiploop_store as store
import shiploop_privacy as privacy

class _UnsafeSource(ValueError):
    """An optional source is unsafe, unstable, or outside its read bound."""


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, name, None) == getattr(right, name, None)
        for name in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    )


def _directory_fd(path: Path) -> int:
    """Open one trusted base directory without following its final component."""
    target = Path(os.path.abspath(os.fspath(path)))
    try:
        before = os.lstat(target)
    except OSError as exc:
        raise _UnsafeSource("base directory is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise _UnsafeSource("base path is not a regular directory")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(os.fspath(target), flags)
    except OSError as exc:
        raise _UnsafeSource("base directory cannot be opened safely") from exc
    after = os.fstat(descriptor)
    if not stat.S_ISDIR(after.st_mode) or not _same_identity(before, after):
        os.close(descriptor)
        raise _UnsafeSource("base directory changed while opening")
    return descriptor


def _relative_parts(relative: str | Path) -> tuple[str, ...]:
    value = os.fspath(relative)
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise _UnsafeSource(f"unsafe relative path {value[:80]!r}")
    path = Path(value)
    parts = path.parts
    if path.is_absolute() or not parts or any(part in ("", ".", "..") for part in parts):
        raise _UnsafeSource(f"unsafe relative path {value[:80]!r}")
    return parts


def _parent_fd(base: Path, parts: tuple[str, ...]) -> int:
    descriptor = _directory_fd(base)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        for part in parts:
            try:
                before = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
                    raise _UnsafeSource("parent component is not a regular directory")
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                raise
            except _UnsafeSource:
                raise
            except OSError as exc:
                raise _UnsafeSource("parent component cannot be opened safely") from exc
            after = os.fstat(child)
            if not stat.S_ISDIR(after.st_mode) or not _same_identity(before, after):
                os.close(child)
                raise _UnsafeSource("parent component changed while opening")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_beneath(base: Path, relative: str | Path, max_bytes: int, *, identity=False) -> tuple[bytes, int]:
    """Read one stable, single-link regular file through no-follow dirfds."""
    parts = _relative_parts(relative)
    shown = os.fspath(relative)  # how the file is named in any error below
    directory = _parent_fd(base, parts[:-1])
    descriptor = -1
    name = parts[-1]
    try:
        try:
            before = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise _UnsafeSource("file metadata is unavailable") from exc
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _UnsafeSource("file is not a regular single-link file")
        if before.st_size > max_bytes:
            raise _UnsafeSource(f"{shown!r} is {before.st_size:,} bytes, over its read limit of {max_bytes:,}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            descriptor = os.open(name, flags, dir_fd=directory)
        except OSError as exc:
            raise _UnsafeSource("file cannot be opened safely") from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or not _same_identity(before, opened):
            raise _UnsafeSource(f"{shown!r} changed while opening")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise _UnsafeSource(f"{shown!r} grew past its read limit of {max_bytes:,} bytes while reading")
        after = os.fstat(descriptor)
        try:
            named_after = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except OSError as exc:
            raise _UnsafeSource(f"{shown!r} changed while reading") from exc
        if (not stat.S_ISREG(after.st_mode) or after.st_nlink != 1
                or not _same_identity(opened, after) or not _same_identity(after, named_after)):
            raise _UnsafeSource(f"{shown!r} changed while reading")
        return (b"".join(chunks), after.st_mtime_ns, (after.st_dev, after.st_ino)) if identity else (b"".join(chunks), after.st_mtime_ns)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        os.close(directory)



def screen(value):
    """Screen keys as well as values before display serialization."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, str):
        return privacy.redact_text(value)
    if isinstance(value, dict):
        return {screen(str(key)): screen(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [screen(item) for item in value]
    return value


def read_absolute(path, limit):
    path = Path(os.path.abspath(os.fspath(path)))
    return _read_beneath(Path(path.anchor), path.relative_to(path.anchor), limit)


def capture(root, relative, limit, observed_at, previous=None):
    source = {"id": relative, "path": relative, "status": "ok", "observed_at": observed_at,
              "changed_at": None, "last_event_at": None, "rows": 0, "omitted": 0, "message": ""}
    try:
        raw, stamp, file_id = _read_beneath(root, relative, limit, identity=True)
        digest = hashlib.sha256(raw).hexdigest()
        # IDs remain stable across append; replacement is a new source generation.
        generation = f"{file_id[0]}:{file_id[1]}"
        if previous and previous.get("generation") != generation:
            source["message"] = "Source replaced; this is a new generation."
        source.update(sha256=digest, changed_at=datetime.fromtimestamp(stamp / 1_000_000_000, timezone.utc).isoformat())
        return {"raw": raw, "source": source, "generation": generation, "mtime_ns": stamp}
    except FileNotFoundError:
        source.update(status="missing", message="Source missing.")
    except (_UnsafeSource, OSError) as exc:
        message = str(exc)
        transient = not isinstance(exc, _UnsafeSource) or isinstance(exc.__cause__, OSError) or "changed while" in message or "grew past" in message
        capped = "over its read limit" in message
        source.update(status="partial" if capped else "unavailable" if transient else "unsafe", message=message,
                      omitted=None if capped else 0)
    # Never retain data after an unsafe path or deliberate deletion. Transient I/O
    # failures retain the original observation time, independently of fresh core.
    if previous and previous["source"].get("sha256") and source["status"] == "unavailable":
        source = dict(previous["source"], status="stale", message="Read failed; retained last good capture.")
        return dict(previous, source=source)
    return {"raw": b"", "source": source, "generation": "missing"}


def stream(captured):
    rows, coverage = store.parse_jsonl_bytes(captured["raw"], coverage=True)
    source = captured["source"]
    source.update(rows=len(rows))
    if captured["raw"]:
        source["omitted"] = coverage["damaged"]
    if source["status"] == "ok" and (coverage["damaged"] or coverage["unterminated_tail"] or coverage["invalid_utf8"]):
        source.update(status="partial", message=(f"Interior damaged records: {coverage['interior_damage']}; "
                      f"unfinished tail: {coverage['partial_tail']}; final newline absent: {coverage['unterminated_tail']}; "
                      f"invalid UTF-8: {coverage['invalid_utf8']}."))
    return rows
