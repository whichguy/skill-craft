"""Read-only run observer: publish a portable HTML snapshot, never drive a run.

The observer lock owns all progress output. The separate run lock is held only
while sampling, without recovery. The pages are rewritten only when what they
show changes. Every sample rewrites one small version script instead; an open
page loads it in the background and, when its version moved, loads the content
script and swaps the changed blocks in place, so the browser never reloads the
page. There is no model call or writable workflow mirror. The one listener is the
opt-in read-only viewer of ``shiploop_progress_serve``, which the user starts
with ``view --serve``; the observer never starts it.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import uuid
from typing import Any, Sequence

import shiploop_store as store

PAGE = "progress.html"
# Sibling scripts of the pages, loaded by a <script> tag because a file: page cannot fetch. VERSION is tiny and
# rewritten at every sample; CONTENT carries the page's <main> and is rewritten with the page.
VERSION = "progress-version.js"
CONTENT = "progress-content.js"
LOCK = ".progress.lock"
STATUS = "progress-observer.json"
STOP = ".progress-stop"
DISABLED = ".progress-disabled"
STALE_AFTER = 30.0
IDLE_TIMEOUT = 1800.0


def now() -> str:
    """Current UTC time as an ISO-8601 string with a ``Z`` suffix, to the second."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def checked_root(path: Path) -> Path:
    """Resolve ``path`` as the run directory, refusing a symlink, a missing directory, or one inside the skill
    package.
    """
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
    """True when an observer holds the display lock."""
    if not (root / LOCK).exists():
        return False
    with _lock(root, LOCK) as acquired:
        return not acquired


def sample(root: Path, *, optional_cache=None) -> dict | None:
    """A snapshot of the run under a shared lock, or None when the run is busy or has a pending transaction."""
    import shiploop_progress_data as data

    with _lock(root, ".lock", shared=True) as acquired:
        if not acquired or os.path.lexists(root / store.JOURNAL_NAME):
            return None
        import shiploop_story as story
        core = story.capture_core(root)
    return data.build_snapshot(root, core=core, optional_cache=optional_cache)


def _call(name: str, value: Any) -> str:
    """One line of JavaScript that hands ``value`` to the open page's ``window.<name>``, when the page defines it."""
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
    return "window." + name + "&&window." + name + "(" + payload + ");\n"


def page_key(source: Any, mode: str, final: bool, error: str, trace_status: str) -> str:
    """The version of one published page: its displayed sources and the observer facts the page shows. The
    observer's clock is left out, so a sample that found nothing new keeps the key and rewrites no page.
    """
    value = json.dumps([source, mode, bool(final), error, trace_status], sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(value.encode("ascii")).hexdigest()[:32]


def publish(root: Path, snapshot: dict, *, mode: str, interval: float,
            final: bool = False, error: str = "", version: str = "") -> str:
    """Write the progress page and its content script for ``snapshot`` with the observer's mode, interval,
    finality and error; returns the page's version.
    """
    import shiploop_progress_render as renderer

    value = {key: value for key, value in snapshot.items() if not key.startswith("_")}
    publication = snapshot.get("trace_publication")
    version = version or page_key(snapshot.get("source_fingerprint"), mode, final, error,
                                  publication.get("status", "") if isinstance(publication, dict) else "")
    value["observer"] = {"mode": mode, "interval_seconds": interval,
                         "refresh_seconds": 5, "stale_after_seconds": STALE_AFTER,
                         "final": final, "error": error, "version": version}
    from shiploop_observation_io import screen
    # Preserve undecodable filename code points visibly without failing UTF-8 publication.
    title, main = (text.encode("utf-8", errors="backslashreplace").decode("utf-8")
                   for text in renderer.render_main(screen(value)))
    # The content script first: a page that reads the new version must find the new content.
    _write(root, CONTENT, _call("__shiploopProgress", {"version": version, "title": title, "main": main}))
    _write(root, PAGE, renderer.page(title, main))
    return version


def announce(root: Path, *, progress: str, trace: Any, observed_at: Any, status: str) -> None:
    """Rewrite the version script: the versions of both pages and the time of the observer's last good sample.
    This is the observer's heartbeat, so an idle run costs one small write per sample and no page rewrite.
    """
    _write(root, VERSION, _call("__shiploopVersion", {
        "schema": "shiploop-progress-version/v1", "progress": progress or "",
        "trace": trace[0] if isinstance(trace, tuple) and trace else "",
        "observed_at": observed_at, "status": status}))


def _refresh_trace(root: Path, key: Any, snapshot=None, *, mode: str = "snapshot",
                   final: bool = False, error: str = "", force: bool = False) -> Any:
    """Publish from the same captured core. Failures propagate to progress/status."""
    import shiploop_trace as trace
    model = trace.build(root, core=getattr(snapshot, "core", None) if snapshot else None,
                        captures=getattr(snapshot, "captures", None) if snapshot else None)
    if snapshot and "story" in snapshot:
        model["story"] = snapshot["story"]
    model["observer"] = {"mode": mode, "final": final, "error": error}
    texts = trace.page_texts(root, model)
    current = trace.source_key(root, model=model, texts=texts)
    if force or current != key:
        model["version"] = current[0]
        trace.write_live(root, model=model, texts=texts)
    return current


def observe(root: Path, *, watch: bool, interval: float = 2.0,
            idle_timeout: float = IDLE_TIMEOUT, instance: str = "") -> int:
    """Refresh the progress page until the run ends or goes idle (``watch``), or once; returns the exit code (0
    done or already observed, 2 not observing).
    """
    root = checked_root(root)
    # Validate identity before creating even the display lock.
    _regular(root / "state.md")
    instance = instance or uuid.uuid4().hex
    with _lock(root, LOCK, create=True) as acquired:
        if not acquired:
            return 0 if watch else 2
        last = None
        fingerprint = None
        trace_key = None
        activity_fingerprint = None
        optional_cache = {}
        published = ""  # the version of the progress page last written
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
                    current = sample(root, optional_cache=optional_cache)
                    if current is None:
                        # Busy/incomplete transactions cannot refresh observation time.
                        if not watch:
                            reason, code = "run busy or transaction pending", 2
                            break
                    else:
                        source_key = current["source_fingerprint"]
                        activity_key = current.get("activity_fingerprint", current.get("story", {}).get("activity_fingerprint", source_key))
                        if activity_key != activity_fingerprint:
                            changed = clock
                        if source_key != fingerprint:
                            terminal_since = None
                        optional_cache = getattr(current, "captures", {})
                        terminal = current["run"]["status"] in ("done", "halted")
                        if terminal and terminal_since is None:
                            terminal_since = clock
                        # The first terminal capture remains watchable until reconciliation.
                        final = terminal and watch and clock - terminal_since >= interval
                        mode = "watch" if watch else "snapshot"
                        trace_error = ""
                        try:
                            # Rewritten when the trace's own key moves; finality and mode are part of that key.
                            trace_key = _refresh_trace(root, trace_key, current, mode=mode,
                                                       final=final, force=not watch)
                        except (OSError, ValueError, KeyError, TypeError, store.StorageError):
                            trace_error = "Trace publication failed; retained trace page may be stale."
                            current.setdefault("warnings", []).append(trace_error)
                        current["trace_publication"] = {"status": "unavailable" if trace_error else "ok",
                                                         "observed_at": current["observed_at"], "message": trace_error}
                        key = page_key(source_key, mode, final, trace_error, current["trace_publication"]["status"])
                        if key != published or not watch:
                            published = publish(root, current, mode=mode, interval=interval, final=final,
                                                error=trace_error, version=key)
                        last, fingerprint = current, source_key
                        activity_fingerprint = activity_key
                        status = "final" if final else "watching" if watch else "snapshot"
                        _write(root, STATUS, json.dumps({
                            "schema": "shiploop-progress-observer/v1", "instance": instance,
                            "pid": os.getpid(), "run_id": current["run"]["id"],
                            "revision": current["run"]["revision"], "observed_at": current["observed_at"],
                            "status": status,
                            "trace_publication": current["trace_publication"],
                        }, sort_keys=True) + "\n")
                        # Last, so a page told of a version always finds that version's content already written.
                        announce(root, progress=published, trace=trace_key,
                                 observed_at=current["observed_at"], status=status)
                        if final or not watch:
                            reason = "final" if final else "snapshot"
                            break
                except (OSError, ValueError, KeyError, TypeError, store.StorageError) as exc:
                    from shiploop_observation_io import screen
                    reason = screen("observation unavailable: " + str(exc))
                    # Keep last good content and its old observed_at; errors are not progress. One publication
                    # per distinct failure shows it; the version script then tells open pages to take it.
                    if last is not None:
                        key = page_key(fingerprint, "watch", False, reason,
                                       last.get("trace_publication", {}).get("status", ""))
                        if key != published:
                            try:
                                trace_key = _refresh_trace(root, trace_key, last, mode="watch",
                                                           error=reason, force=True)
                            except (OSError, ValueError, KeyError, TypeError, store.StorageError):
                                pass  # The progress page still exposes the failure.
                            published = publish(root, last, mode="watch", interval=interval, error=reason,
                                                version=key)
                            announce(root, progress=published, trace=trace_key,
                                     observed_at=last["observed_at"], status="watching")
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
                        try:
                            trace_key = _refresh_trace(root, trace_key, last, mode="snapshot",
                                                       error=reason, force=True)
                            trace_error = ""
                        except (OSError, ValueError, TypeError, KeyError, store.StorageError):
                            trace_error = "Trace publication failed; retained trace page may be stale."
                        last["trace_publication"] = {"status": "unavailable" if trace_error else "ok",
                                                     "observed_at": last["observed_at"], "message": trace_error}
                        published = publish(root, last, mode="snapshot", interval=interval,
                                            error="; ".join(filter(None, (reason, trace_error))))
                        announce(root, progress=published, trace=trace_key,
                                 observed_at=last["observed_at"], status=reason)
                except (OSError, ValueError, TypeError, KeyError, store.StorageError):
                    reason += "; final display publication failed"
                # Status cleanup is independent of rendering the final page.
                try:
                    record = _read_json(root / STATUS)
                    if record.get("instance") == instance:
                        record.update(status=reason, stopped_at=now())
                        if last is not None:
                            record["trace_publication"] = last["trace_publication"]
                        _write(root, STATUS, json.dumps(record, sort_keys=True) + "\n")
                except (OSError, ValueError, TypeError, store.StorageError):
                    pass  # Released lock plus stale heartbeat still exposes shutdown.
        return code


def start(root: Path, *, interval: float = 2.0, idle_timeout: float = IDLE_TIMEOUT) -> bool:
    """Start one detached observer for the run; True when one is running afterwards."""
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


def finished(root: Path) -> bool:
    """True for a done or halted run: it has nothing left to observe."""
    return store.read_record(root / "state.md").get("status") in ("done", "halted")


def _pending_start_message(root: Path) -> str:
    return ("ShipLoop progress observer was running when checked; first fresh publication is pending "
            "confirmation. Wait, then use view --status. Target page (may not be ready): " + str(root / PAGE))


def ensure(root: Path) -> None:
    """Best-effort default after a successful packet and after releasing run lock."""
    if os.environ.get("SHIPLOOP_PROGRESS", "watch").lower() == "off":
        return
    try:
        root = checked_root(root)
        if os.path.lexists(root / DISABLED):
            return
        # A done or halted run has nothing left to observe, and printing its last packet is a read: starting an
        # observer there wrote .progress.lock and refreshed context-index.md (shiploop-cross-run, terminal recovery).
        if finished(root):
            return
        if not start(root):
            if running(root):
                print(_pending_start_message(root), file=sys.stderr)
            else:
                print("ShipLoop progress observer unavailable; use view --start to retry.", file=sys.stderr)
    except (OSError, ValueError, store.StorageError) as exc:
        print(f"ShipLoop progress observer unavailable: {exc}", file=sys.stderr)


def stop(root: Path) -> None:
    """Disable automatic observation and ask a running observer to stop."""
    _write(root, DISABLED, "Automatic observation stopped by view --stop. Use view --start to resume.\n")
    record = _read_json(root / STATUS)
    if running(root) and record.get("instance"):
        _write(root, STOP, json.dumps({"instance": record["instance"]}) + "\n")


def _positive(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value) or value < 0.1:
        raise argparse.ArgumentTypeError("must be a finite number of at least 0.1 seconds")
    return value


def _port(raw: str) -> int:
    value = int(raw)
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError("must be a TCP port from 0 to 65535")
    return value


def serve(root: Path, *, port: int | None, interval: float, idle_timeout: float) -> int:
    """``view --serve``: keep the observer going for a live run, then serve the run's pages until interrupted."""
    import shiploop_progress_serve as viewer

    try:
        if not finished(root) and not start(root, interval=interval, idle_timeout=idle_timeout):
            if running(root):
                print(_pending_start_message(root) + " Serving read-only; pages may not be published yet.",
                      file=sys.stderr)
            else:
                print("ShipLoop progress observer unavailable; serving the pages already published.", file=sys.stderr)
    except (OSError, ValueError, store.StorageError) as exc:
        print(f"ShipLoop progress observer unavailable: {exc}; serving the pages already published.",
              file=sys.stderr)
    return viewer.serve(root, port=port)


def main(argv: Sequence[str] | None = None, *, core: Any = None) -> int:
    """Entry point of ``shiploop view``."""
    parser = argparse.ArgumentParser(prog="shiploop view", description=__doc__)
    parser.add_argument("--run-dir", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--watch", action="store_true", help="observe in this foreground process")
    mode.add_argument("--start", action="store_true", help="start one detached observer")
    mode.add_argument("--stop", action="store_true", help="stop observation and disable automatic restarts")
    mode.add_argument("--status", action="store_true", help="read observer status without modifying state")
    mode.add_argument("--serve", action="store_true",
                      help="start the observer and serve the run's pages read-only on 127.0.0.1 until interrupted")
    parser.add_argument("--port", type=_port, default=None,
                        help="with --serve: the TCP port (default: one derived from the run directory; 0 lets the "
                             "system pick)")
    parser.add_argument("--interval", type=_positive, default=2.0)
    parser.add_argument("--idle-timeout", type=_positive, default=IDLE_TIMEOUT)
    parser.add_argument("--instance", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.port is not None and not args.serve:
        parser.error("--port needs --serve")
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
        if (args.start or args.watch or args.serve) and not args.instance:
            if _regular(root / DISABLED, missing=True):
                (root / DISABLED).unlink()
        if args.serve:
            return serve(root, port=args.port, interval=args.interval, idle_timeout=args.idle_timeout)
        if args.start:
            if not start(root, interval=args.interval, idle_timeout=args.idle_timeout):
                if running(root):
                    print(_pending_start_message(root))
                    return 0
                print("ShipLoop progress observer unavailable; use view --start to retry.", file=sys.stderr)
                return 2
            code = 0
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
