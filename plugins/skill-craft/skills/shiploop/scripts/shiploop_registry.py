#!/usr/bin/env python3
"""Best-effort, sandbox-safe run registry and viewer discovery for ShipLoop.

Nothing written here is workflow authority: ``state.md`` in each run directory
remains the single source of truth.  Registry entries and ``viewer.json`` live
under ``SHIPLOOP_STATE_HOME`` (else ``${XDG_STATE_HOME:-~/.local/state}/shiploop``)
so strict tool sandboxes that deny writes there fail open without affecting
workflow transitions, while host hooks (``shiploop-keepalive-observe``) or
``discover_runs()`` still discover runs from keepalive records and
``.shiploop-runs`` parents.
"""
from __future__ import annotations

from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping, Sequence

import shiploop_store as store


REGISTRY_SCHEMA = "shiploop-run-registry/v1"
VIEWER_SCHEMA = "shiploop-viewer/v1"
_SAFE_KEY = re.compile(r"^[A-Za-z0-9._-]+$")
_MAX_KEY_LEN = 96
_MAX_CONTROL_BYTES = 64 * 1024
_MAX_STATE_BYTES = 4 * 1024 * 1024


def now_utc() -> str:
    """Current UTC time as an ISO-8601 string to the second."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def state_home() -> Path:
    """State root: ``SHIPLOOP_STATE_HOME``, else ``${XDG_STATE_HOME:-~/.local/state}/shiploop``."""
    override = os.environ.get("SHIPLOOP_STATE_HOME")
    if override:
        return Path(override)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "shiploop"


def registry_dir() -> Path:
    return state_home() / "registry"


def viewer_lock_path() -> Path:
    return state_home() / "viewer.lock"


def viewer_info_path() -> Path:
    return state_home() / "viewer.json"


def safe_run_key(run_id: str | None, run_dir: Path | str) -> str:
    """URL- and filename-safe run slug; falls back to a deterministic hash of ``run_dir``."""
    candidate = str(run_id or "").strip()
    if candidate and len(candidate) <= _MAX_KEY_LEN and _SAFE_KEY.fullmatch(candidate) and candidate not in (".", ".."):
        return candidate
    digest = hashlib.sha256(os.path.abspath(os.fspath(run_dir)).encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"run-{digest}"


def _read_regular_bytes(path: Path, limit: int) -> bytes | None:
    """Read up to ``limit`` bytes from a non-symlink, single-link regular file; None otherwise."""
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                return None
            return handle.read(limit + 1)[:limit]
    except OSError:
        return None


def _read_json_file(path: Path, limit: int = _MAX_CONTROL_BYTES) -> dict[str, Any] | None:
    raw = _read_regular_bytes(path, limit)
    if raw is None:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        return None
    return data if isinstance(data, dict) else None


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(data), indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _workspace_metadata(root: Path, state: Mapping[str, Any]) -> tuple[str, str]:
    """Return ``(source_repo, workspace_root)`` for a run; falls back to ``state['repo']``."""
    repo = str(state.get("repo") or "")
    if state.get("execution_mode") == "navigator-worktree" and root.name == "run":
        manifest_path = root.parent / "workspace.md"
        raw = _read_regular_bytes(manifest_path, 512 * 1024)
        if raw is not None:
            try:
                manifest = store.loads(raw.decode("utf-8"))
                if isinstance(manifest, Mapping) and isinstance(manifest.get("source_repo"), str):
                    return manifest["source_repo"], str(root.parent)
            except (UnicodeError, store.StorageError, ValueError, RecursionError):
                pass
        return repo, str(root.parent)
    return repo, ""


def register_run(root: Path, state: Mapping[str, Any], *, host: str | None = None) -> bool:
    """Best-effort write of a run registry record; never raises on sandbox/IO refusals."""
    try:
        resolved = Path(os.path.abspath(os.fspath(root)))
        if resolved.is_symlink() or not resolved.is_dir():
            return False
        run_id = str(state.get("run_id") or "").strip()
        if not run_id:
            return False
        key = safe_run_key(run_id, resolved)
        entry_path = registry_dir() / f"{key}.json"
        existing = _read_json_file(entry_path)
        if existing and existing.get("run_dir") and os.path.abspath(str(existing["run_dir"])) != str(resolved):
            # Disambiguate rare key collision across distinct run directories.
            suffix = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:8]
            key = f"{key[:_MAX_KEY_LEN - 9]}-{suffix}"
            entry_path = registry_dir() / f"{key}.json"
            existing = _read_json_file(entry_path)
        source_repo, workspace_root = _workspace_metadata(resolved, state)
        stamp = now_utc()
        record = {
            "schema": REGISTRY_SCHEMA,
            "run_id": run_id,
            "run_key": key,
            "run_dir": str(resolved),
            "repo": str(state.get("repo") or ""),
            "source_repo": source_repo,
            "workspace_root": workspace_root,
            "execution_mode": str(state.get("execution_mode") or "navigator"),
            "delegation": str(state.get("delegation") or "inline"),
            "host": host or (existing.get("host") if isinstance(existing, Mapping) else None) or "",
            "registered_at": (existing.get("registered_at") if isinstance(existing, Mapping) else None) or stamp,
            "updated_at": stamp,
        }
        _atomic_write_json(entry_path, record)
        return True
    except (OSError, ValueError, TypeError):
        return False


def register_from_hook(run_dir: Path, *, host: str | None = None) -> bool:
    """Read ``state.md`` safely and register ``run_dir`` (called from host keepalive hooks)."""
    try:
        resolved = Path(os.path.abspath(os.fspath(run_dir)))
        raw = _read_regular_bytes(resolved / "state.md", _MAX_STATE_BYTES)
        if raw is None:
            return False
        state = store.loads(raw.decode("utf-8"))
        if not isinstance(state, Mapping):
            return False
        return register_run(resolved, state, host=host)
    except (OSError, UnicodeError, ValueError, TypeError, store.StorageError, RecursionError):
        return False


def _keepalive_home() -> Path:
    override = os.environ.get("SHIPLOOP_KEEPALIVE_HOME")
    if override:
        return Path(override)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "shiploop" / "keepalive"


def _scan_run_parent(parent: Path) -> list[Path]:
    """Return candidate run directories directly under a ``.shiploop-runs``-style parent."""
    found: list[Path] = []
    try:
        if parent.is_symlink() or not parent.is_dir():
            return found
        if (parent / "state.md").exists():
            found.append(parent)
            return found
        for child in sorted(parent.iterdir()):
            if child.is_symlink() or not child.is_dir():
                continue
            if (child / "run" / "state.md").exists():
                found.append(child / "run")
            elif (child / "state.md").exists():
                found.append(child)
    except OSError:
        pass
    return found


def default_cwd_roots() -> tuple[Path, ...]:
    """Return existing non-symlink ``.shiploop-runs`` directories near ``cwd`` unless ``SHIPLOOP_STATE_HOME`` isolates discovery."""
    if os.environ.get("SHIPLOOP_STATE_HOME"):
        return ()
    found: list[Path] = []
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        return ()
    for base in (cwd, cwd.parent):
        candidate = base / ".shiploop-runs"
        try:
            if candidate.is_dir() and not candidate.is_symlink():
                resolved = Path(os.path.abspath(os.fspath(candidate)))
                if resolved not in found:
                    found.append(resolved)
        except OSError:
            continue
    return tuple(found)


def discover_runs(
    *,
    extra_roots: Sequence[Path | str] = (),
    include_keepalive: bool = True,
    state_cache: dict[str, tuple[int, int, Mapping[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Discover ShipLoop runs across the registry, keepalive records, and run-root scans.

    Each returned item describes a verified local run directory with a regular,
    readable ``state.md`` (never following symlinks or exposing malformed runs).
    """
    candidates: dict[str, dict[str, Any]] = {}
    learned_parents: set[Path] = set()

    def add_candidate(
        run_dir: Path,
        *,
        host: str = "",
        registered_at: str = "",
        updated_at: str = "",
        model: str = "",
        effort: str = "",
        model_at: str = "",
    ) -> None:
        try:
            if run_dir.is_symlink():
                return
            resolved = Path(os.path.abspath(os.fspath(run_dir)))
        except OSError:
            return
        key = str(resolved)
        row = candidates.setdefault(key, {
            "run_dir": key,
            "host": "",
            "registered_at": "",
            "updated_at": "",
            "keepalive": None,
            "model": "",
            "effort": "",
            "model_at": "",
        })
        if host and not row["host"]:
            row["host"] = host
        if registered_at and not row["registered_at"]:
            row["registered_at"] = registered_at
        if updated_at and updated_at > row["updated_at"]:
            row["updated_at"] = updated_at
        if model and (not row["model"] or (model_at and model_at >= row["model_at"])):
            row["model"] = model
            row["effort"] = effort
            row["model_at"] = model_at
        if resolved.name == "run" and resolved.parent.parent.name == ".shiploop-runs":
            learned_parents.add(resolved.parent.parent)

    # 1. Explicit registry entries.
    reg_dir = registry_dir()
    if reg_dir.is_dir() and not reg_dir.is_symlink():
        try:
            for path in sorted(reg_dir.glob("*.json")):
                entry = _read_json_file(path)
                if not entry or not isinstance(entry.get("run_dir"), str):
                    continue
                add_candidate(
                    Path(entry["run_dir"]),
                    host=str(entry.get("host") or ""),
                    registered_at=str(entry.get("registered_at") or ""),
                    updated_at=str(entry.get("updated_at") or ""),
                )
        except OSError:
            pass

    # 2. Keepalive runs & bindings (captures runs even when tool sandbox blocked registry writes).
    keepalive_owners: dict[str, dict[str, Any]] = {}
    if include_keepalive:
        kh = _keepalive_home()
        runs_dir = kh / "runs"
        if runs_dir.is_dir() and not runs_dir.is_symlink():
            try:
                for path in sorted(runs_dir.glob("*.json")):
                    owner = _read_json_file(path)
                    if not owner or not isinstance(owner.get("run_dir"), str):
                        continue
                    rdir = os.path.abspath(owner["run_dir"])
                    add_candidate(Path(rdir))
                    keepalive_owners[rdir] = owner
            except OSError:
                pass
        bindings_dir = kh / "bindings"
        if bindings_dir.is_dir() and not bindings_dir.is_symlink():
            try:
                for path in sorted(bindings_dir.glob("*.json")):
                    binding = _read_json_file(path)
                    if not binding or not isinstance(binding.get("run_dir"), str):
                        continue
                    add_candidate(
                        Path(binding["run_dir"]),
                        host=str(binding.get("host") or ""),
                        model=str(binding.get("observed_model") or "").strip(),
                        effort=str(binding.get("observed_effort") or "").strip(),
                        model_at=str(binding.get("updated_at") or binding.get("observed_at") or ""),
                    )
            except OSError:
                pass

    # 3. Caller-specified roots + learned .shiploop-runs parents.
    scan_roots: list[Path] = [Path(os.path.abspath(os.fspath(item))) for item in extra_roots]
    for parent in sorted(learned_parents):
        if parent not in scan_roots:
            scan_roots.append(parent)
    for parent in scan_roots:
        for found_dir in _scan_run_parent(parent):
            add_candidate(found_dir)

    # Check keepalive process liveness at most once across all runs.
    proc_table: dict[int, dict[str, Any]] | None = None
    if keepalive_owners:
        try:
            import shiploop_keepalive as keepalive
            proc_table = keepalive._processes()
        except Exception:  # noqa: BLE001
            proc_table = None

    results: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    seen_dirs: set[str] = set()
    for run_dir_str, meta in sorted(candidates.items()):
        seen_dirs.add(run_dir_str)
        run_path = Path(run_dir_str)
        if run_path.is_symlink() or not run_path.is_dir():
            continue
        state_path = run_path / "state.md"
        state: Mapping[str, Any] | None = None
        if state_cache is not None:
            try:
                info = state_path.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > _MAX_STATE_BYTES:
                continue
            cached_entry = state_cache.get(run_dir_str)
            if cached_entry is not None and cached_entry[0] == info.st_mtime_ns and cached_entry[1] == info.st_size:
                state = cached_entry[2]
            else:
                raw = _read_regular_bytes(state_path, _MAX_STATE_BYTES)
                if raw is None:
                    continue
                try:
                    loaded = store.loads(raw.decode("utf-8"))
                except (UnicodeError, store.StorageError, ValueError, RecursionError):
                    continue
                if isinstance(loaded, Mapping):
                    state = loaded
                    state_cache[run_dir_str] = (info.st_mtime_ns, info.st_size, loaded)
        else:
            raw = _read_regular_bytes(state_path, _MAX_STATE_BYTES)
            if raw is None:
                continue
            try:
                loaded = store.loads(raw.decode("utf-8"))
            except (UnicodeError, store.StorageError, ValueError, RecursionError):
                continue
            if isinstance(loaded, Mapping):
                state = loaded
        if not isinstance(state, Mapping) or not isinstance(state.get("run_id"), str):
            continue
        run_id = state["run_id"]
        key = safe_run_key(run_id, run_path)
        if key in used_keys:
            suffix = hashlib.sha256(run_dir_str.encode("utf-8")).hexdigest()[:8]
            key = f"{key[:_MAX_KEY_LEN - 9]}-{suffix}"
        used_keys.add(key)

        source_repo, workspace_root = _workspace_metadata(run_path, state)
        owner_info = keepalive_owners.get(run_dir_str)
        owner_alive: bool | None = None
        owner_label = ""
        if isinstance(owner_info, Mapping):
            owner_label = str(owner_info.get("owner") or "")
            proc = owner_info.get("process")
            if proc_table and isinstance(proc, Mapping) and isinstance(proc.get("pid"), int):
                row = proc_table.get(proc["pid"])
                owner_alive = row is not None and row.get("start") == proc.get("start")
        results.append({
            "run_id": run_id,
            "run_key": key,
            "run_dir": run_dir_str,
            "repo": str(state.get("repo") or ""),
            "source_repo": source_repo,
            "workspace_root": workspace_root,
            "execution_mode": str(state.get("execution_mode") or "navigator"),
            "delegation": str(state.get("delegation") or "inline"),
            "host": meta["host"] or (owner_label.split(":", 1)[0] if ":" in owner_label else ""),
            "model": meta["model"],
            "effort": meta["effort"],
            "registered_at": meta["registered_at"],
            "updated_at": meta["updated_at"],
            "keepalive_owner": owner_label,
            "owner_alive": owner_alive,
            "state": state,
        })
    if state_cache is not None:
        for stale in list(state_cache):
            if stale not in seen_dirs:
                del state_cache[stale]
    return results


def shared_source_repo_conflicts(runs: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Return ``{source_repo: [run_id, ...]}`` when 2+ non-terminal runs target the same source repo."""
    by_repo: dict[str, list[str]] = {}
    for row in runs:
        state = row.get("state")
        status = (state.get("status") if isinstance(state, Mapping) else row.get("status")) or ""
        if status in ("done", "halted"):
            continue
        source_repo = str(row.get("source_repo") or row.get("repo") or "").strip()
        if not source_repo:
            continue
        by_repo.setdefault(os.path.abspath(source_repo), []).append(str(row.get("run_id") or row.get("run_key") or ""))
    return {repo: ids for repo, ids in by_repo.items() if len(ids) >= 2}


# ---------------------------------------------------------------- viewer discovery

def acquire_viewer_lock() -> int | None:
    """Acquire the exclusive viewer lock non-blocking; returns its fd, or None when held."""
    path = viewer_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError(errno.ELOOP, "viewer lock cannot be a symlink")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            os.close(fd)
            raise OSError(errno.EINVAL, "viewer lock must be a regular unlinked file")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        os.close(fd)
        return None
    except BaseException:
        os.close(fd)
        raise


def write_viewer_info(info: Mapping[str, Any]) -> None:
    """Write ``viewer.json`` atomically while the caller holds ``viewer.lock``."""
    payload = {"schema": VIEWER_SCHEMA, **dict(info)}
    _atomic_write_json(viewer_info_path(), payload)


def clear_viewer_info(pid: int | None = None) -> None:
    """Remove ``viewer.json`` if it belongs to ``pid`` (or unconditionally when ``pid`` is None)."""
    path = viewer_info_path()
    try:
        if pid is not None:
            current = _read_json_file(path)
            if current is not None and current.get("pid") not in (None, pid):
                return
        path.unlink(missing_ok=True)
    except OSError:
        pass


def active_viewer() -> dict[str, Any] | None:
    """Return the active viewer server record when its lock is live, else None (strictly read-only)."""
    try:
        lock_path = viewer_lock_path()
        info_path = viewer_info_path()
        if lock_path.is_symlink() or not lock_path.exists():
            return None
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(lock_path, flags)
        locked = False
        try:
            stat_info = os.fstat(fd)
            if not stat.S_ISREG(stat_info.st_mode) or stat_info.st_nlink != 1:
                return None
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
                return None  # lock was free -> server is not running
            except BlockingIOError:
                locked = True
        finally:
            os.close(fd)
        if not locked:
            return None
        record = _read_json_file(info_path)
        if not record or record.get("schema") != VIEWER_SCHEMA:
            return None
        if not isinstance(record.get("pid"), int) or not isinstance(record.get("url"), str):
            return None
        return record
    except (OSError, ValueError):
        return None


def prune_registry() -> list[str]:
    """Remove stale or malformed ``registry/*.json`` files whose run directory or ``state.md`` no longer exists."""
    pruned: list[str] = []
    reg_dir = registry_dir()
    try:
        if reg_dir.is_symlink() or not reg_dir.is_dir():
            return pruned
        for path in sorted(reg_dir.glob("*.json")):
            if path.is_symlink():
                continue
            entry = _read_json_file(path)
            remove = False
            if not entry or not isinstance(entry.get("run_dir"), str):
                remove = True
            else:
                try:
                    rdir = Path(os.path.abspath(entry["run_dir"]))
                    state_path = rdir / "state.md"
                    if rdir.is_symlink() or not rdir.is_dir() or state_path.is_symlink():
                        remove = True
                    else:
                        info = state_path.lstat()
                        if not stat.S_ISREG(info.st_mode):
                            remove = True
                except OSError:
                    remove = True
            if remove:
                try:
                    path.unlink(missing_ok=True)
                    pruned.append(path.stem)
                except OSError:
                    pass
    except OSError:
        return pruned
    return pruned
