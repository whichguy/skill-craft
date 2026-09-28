"""Read-only run observer: publish a portable HTML snapshot, never drive a run.

The observer lock owns all progress output. The separate run lock is held only
while sampling, without recovery. A browser reloads the complete HTML file;
there is no HTTP listener, model call, or writable workflow mirror.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid

import shiploop_store as store

PAGE = "progress.html"
LOCK = ".progress.lock"
STATUS = "progress-observer.json"
STOP = ".progress-stop"
DISABLED = ".progress-disabled"
HEARTBEAT = 10.0
STALE_AFTER = 30.0
IDLE_TIMEOUT = 1800.0


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def checked_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("progress needs an existing, non-symlink run directory")
    root = path.resolve()
    try:
        root.relative_to(Path(__file__).resolve().parents[1])
    except ValueError:
        pass
    else:
        raise ValueError("progress cannot write inside the skill package")
    return root


def _regular(path: Path, *, missing: bool = False) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing:
            return False
        raise
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"progress requires a regular unlinked file: {path.name}")
    return True


def _read_json(path: Path) -> dict:
    if not _regular(path, missing=True):
        return {}
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 16_384:
            raise ValueError("invalid progress control file")
        value = json.loads(handle.read(16_385))
    if not isinstance(value, dict):
        raise ValueError("invalid progress control record")
    return value


def _write(root: Path, name: str, text: str) -> None:
    # Do not recreate an archived/deleted run, follow a link, or replace a device.
    checked_root(root)
    _regular(root / name, missing=True)
    store.atomic_write_text(root / name, text)


@contextmanager
def _lock(root: Path, name: str, *, shared: bool = False, create: bool = False):
    path = root / name
    _regular(path, missing=create)
    flags = (os.O_RDWR if create else os.O_RDONLY) | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    if create:
        flags |= os.O_CREAT
    fd = os.open(path, flags, 0o600)
    acquired = False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"invalid {name} lock")
        try:
            fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError:
            pass
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def running(root: Path) -> bool:
    if not (root / LOCK).exists():
        return False
    with _lock(root, LOCK) as acquired:
        return not acquired


def sample(root: Path) -> dict | None:
    import shiploop_progress_data as data

    with _lock(root, ".lock", shared=True) as acquired:
        if not acquired or os.path.lexists(root / store.JOURNAL_NAME):
            return None
        return data.build_snapshot(root)


def publish(root: Path, snapshot: dict, *, mode: str, interval: float,
            final: bool = False, error: str = "") -> None:
    import shiploop_progress_render as renderer

    value = dict(snapshot)
    value["observer"] = {"mode": mode, "interval_seconds": interval,
                         "refresh_seconds": 5, "stale_after_seconds": STALE_AFTER,
                         "final": final, "error": error}
    _write(root, PAGE, renderer.render(value))


def observe(root: Path, *, watch: bool, interval: float = 2.0,
            idle_timeout: float = IDLE_TIMEOUT, instance: str = "") -> int:
    root = checked_root(root)
    # Validate identity before creating even the display lock.
    _regular(root / "state.md")
    instance = instance or uuid.uuid4().hex
    with _lock(root, LOCK, create=True) as acquired:
        if not acquired:
            return 0 if watch else 2
        last = None
        fingerprint = None
        published = 0.0
        changed = time.monotonic()
        terminal_since = None
        code = 0
        reason = "stopped"
        try:
            while True:
                if not root.is_dir():
                    return 0
                if watch and _regular(root / DISABLED, missing=True):
                    reason = "stopped by request"
                    break
                stop = _read_json(root / STOP)
                if stop.get("instance") == instance:
                    reason = "stopped by request"
                    break
                clock = time.monotonic()
                try:
                    current = sample(root)
                    if current is None:
                        # Busy/incomplete transactions cannot refresh observation time.
                        if not watch:
                            reason, code = "run busy or transaction pending", 2
                            break
                    else:
                        source_key = current["source_fingerprint"]
                        if source_key != fingerprint:
                            changed, terminal_since = clock, None
                        terminal = current["run"]["status"] in ("done", "halted")
                        if terminal and terminal_since is None:
                            terminal_since = clock
                        # Two stable observations reconcile documents and return receipt.
                        final = terminal and watch and clock - terminal_since >= interval
                        if source_key != fingerprint or clock - published >= HEARTBEAT or final or not watch:
                            publish(root, current, mode="watch" if watch else "snapshot",
                                    interval=interval, final=final)
                            published = clock
                        last, fingerprint = current, source_key
                        _write(root, STATUS, json.dumps({
                            "schema": "shiploop-progress-observer/v1", "instance": instance,
                            "pid": os.getpid(), "run_id": current["run"]["id"],
                            "revision": current["run"]["revision"], "observed_at": current["observed_at"],
                            "status": "final" if final else "watching" if watch else "snapshot",
                        }, sort_keys=True) + "\n")
                        if final or not watch:
                            reason = "final" if final else "snapshot"
                            break
                except (OSError, ValueError, KeyError, TypeError, store.StorageError) as exc:
                    reason = "observation unavailable: " + str(exc)
                    # Keep last good content and its old observed_at; errors are not progress.
                    if last is not None and clock - published >= HEARTBEAT:
                        publish(root, last, mode="watch", interval=interval, error=reason)
                        published = clock
                    if not watch or last is None:
                        code = 2
                        break
                if clock - changed >= idle_timeout:
                    reason = "idle timeout; next ShipLoop packet can restart the observer"
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            reason = "stopped by interrupt"
        finally:
            if root.is_dir():
                try:
                    if last is not None and reason not in ("final", "snapshot"):
                        publish(root, last, mode="snapshot", interval=interval, error=reason)
                except (OSError, ValueError, TypeError, KeyError, store.StorageError):
                    reason += "; final display publication failed"
                # Status cleanup is independent of rendering the final page.
                try:
                    record = _read_json(root / STATUS)
                    if record.get("instance") == instance:
                        record.update(status=reason, stopped_at=now())
                        _write(root, STATUS, json.dumps(record, sort_keys=True) + "\n")
                except (OSError, ValueError, TypeError, store.StorageError):
                    pass  # Released lock plus stale heartbeat still exposes shutdown.
        return code


def start(root: Path, *, interval: float = 2.0, idle_timeout: float = IDLE_TIMEOUT) -> bool:
    root = checked_root(root)
    _regular(root / "state.md")
    if running(root):
        return True
    previous_instance = _read_json(root / STATUS).get("instance")
    instance = uuid.uuid4().hex
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--run-dir", str(root),
               "--watch", "--interval", str(interval), "--idle-timeout", str(idle_timeout),
               "--instance", instance]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
    # Bounded startup: don't make workflow completion depend on viewer health.
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if running(root):
            record = _read_json(root / STATUS)
            fresh_owner = record.get("instance") == instance or (
                process.poll() == 0 and record.get("instance") not in (None, previous_instance))
            if fresh_owner and _regular(root / PAGE, missing=True):
                return True
        if process.poll() is not None:
            record = _read_json(root / STATUS)
            return (process.returncode == 0 and record.get("instance") == instance
                    and _regular(root / PAGE, missing=True))
        time.sleep(0.02)
    return False


def ensure(root: Path) -> None:
    """Best-effort default after a successful packet and after releasing run lock."""
    if os.environ.get("SHIPLOOP_PROGRESS", "watch").lower() == "off":
        return
    try:
        root = checked_root(root)
        if os.path.lexists(root / DISABLED):
            return
        if not start(root):
            print("ShipLoop progress observer unavailable; use view --start to retry.", file=sys.stderr)
    except (OSError, ValueError, store.StorageError) as exc:
        print(f"ShipLoop progress observer unavailable: {exc}", file=sys.stderr)


def stop(root: Path) -> None:
    _write(root, DISABLED, "Automatic observation stopped by view --stop. Use view --start to resume.\n")
    record = _read_json(root / STATUS)
    if running(root) and record.get("instance"):
        _write(root, STOP, json.dumps({"instance": record["instance"]}) + "\n")


def _positive(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value) or value < 0.1:
        raise argparse.ArgumentTypeError("must be a finite number of at least 0.1 seconds")
    return value


def main(argv=None, *, core=None) -> int:
    parser = argparse.ArgumentParser(prog="shiploop view", description=__doc__)
    parser.add_argument("--run-dir", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--watch", action="store_true", help="observe in this foreground process")
    mode.add_argument("--start", action="store_true", help="start one detached observer")
    mode.add_argument("--stop", action="store_true", help="stop observation and disable automatic restarts")
    mode.add_argument("--status", action="store_true", help="read observer status without modifying state")
    parser.add_argument("--interval", type=_positive, default=2.0)
    parser.add_argument("--idle-timeout", type=_positive, default=IDLE_TIMEOUT)
    parser.add_argument("--instance", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        root = checked_root(Path(args.run_dir).expanduser())
        if core is not None:
            core.refuse_package_path(root)
        if args.status:
            print(json.dumps({**_read_json(root / STATUS), "running": running(root),
                              "path": str(root / PAGE)}, sort_keys=True))
            return 0
        if args.stop:
            stop(root)
            print("Progress stop requested; ShipLoop execution is unchanged.")
            return 0
        if (args.start or args.watch) and not args.instance:
            if _regular(root / DISABLED, missing=True):
                (root / DISABLED).unlink()
        if args.start:
            code = 0 if start(root, interval=args.interval, idle_timeout=args.idle_timeout) else 2
        else:
            code = observe(root, watch=args.watch, interval=args.interval,
                           idle_timeout=args.idle_timeout, instance=args.instance)
        print(str(root / PAGE))
        return code
    except (OSError, ValueError, KeyError, TypeError, store.StorageError) as exc:
        print(f"ShipLoop progress unavailable: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
