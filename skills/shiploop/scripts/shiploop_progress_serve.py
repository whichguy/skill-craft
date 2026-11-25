"""Opt-in read-only viewer: serve one run or the multi-run hub on 127.0.0.1 for a browser.

The user starts it in their own terminal with ``shiploop view --serve`` (or
``shiploop view --serve --background``); ShipLoop never starts it implicitly, so
every command stays visible to the user and the host's hooks. It answers GET and
HEAD only, reads run files without modifying workflow state, and keeps strict
loopback, Host-header, and Content-Security-Policy guards.
"""
from __future__ import annotations

from datetime import datetime, timezone
import errno
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import stat
import sys
import threading
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qs, urlsplit
import zlib

from shiploop_hub_page import HUB_HTML as _HUB_HTML

HOST = "127.0.0.1"
# Single-run default port comes from the run directory; the multi-run hub uses a stable default port.
PORT_BASE = 40000
PORT_SPAN = 20000
PORT_TRIES = 50
DEFAULT_HUB_PORT = 41730

HTML = "text/html; charset=utf-8"
SCRIPT = "text/javascript; charset=utf-8"
JSON = "application/json; charset=utf-8"
PAGES = {
    "/": ("progress.html", HTML),
    "/progress.html": ("progress.html", HTML),
    "/trace.html": ("trace.html", HTML),
    "/report.html": ("report.html", HTML),
    "/progress-version.js": ("progress-version.js", SCRIPT),
    "/progress-content.js": ("progress-content.js", SCRIPT),
    "/trace-content.js": ("trace-content.js", SCRIPT),
}
# Per-run pages are self-contained and only load their sibling update scripts.
POLICY = (
    "default-src 'none'; script-src 'unsafe-inline' 'self'; style-src 'unsafe-inline'; img-src data:; "
    "font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
# The hub dashboard fetches /api/runs on the same loopback origin only.
HUB_POLICY = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; "
    "font-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def default_port(root: Path) -> int:
    """The port one run's single-run viewer tries first."""
    return PORT_BASE + zlib.crc32(str(root).encode("utf-8")) % PORT_SPAN


def read_page(root: Path, name: str) -> bytes:
    """The bytes of one published page; FileNotFoundError when absent, ValueError when it is not a plain file."""
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(root / name, flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ValueError(f"{name} is not a regular file") from exc
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"{name} is not a regular unlinked file")
        return handle.read()


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    root: Path

    def allowed_hosts(self) -> frozenset[str]:
        port = self.server_address[1]
        return frozenset({f"{HOST}:{port}", f"localhost:{port}", f"[::1]:{port}"})


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    server_version = "ShipLoopViewer"
    sys_version = ""

    def version_string(self) -> str:
        return self.server_version

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        pass  # the terminal shows the address, not a line per check

    def _send(self, status: int, body: bytes, *, head: bool, kind: str = "text/plain; charset=utf-8",
              allow: str = "", policy: str = POLICY, extra_headers: Mapping[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", policy)
        if allow:
            self.send_header("Allow", allow)
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _serve(self, *, head: bool) -> None:
        # A page on another site that resolves its own name to 127.0.0.1 would otherwise read these pages.
        if (self.headers.get("Host") or "").lower() not in self.server.allowed_hosts():
            return self._send(403, b"Unknown host\n", head=head)
        name, kind = PAGES.get(urlsplit(self.path).path, (None, ""))
        if name is None:
            return self._send(404, b"Not found\n", head=head)
        try:
            body = read_page(self.server.root, name)
        except FileNotFoundError:
            return self._send(404, f"{name} is not published yet\n".encode(), head=head)
        except (OSError, ValueError):
            return self._send(403, f"{name} is not a plain file\n".encode(), head=head)
        self._send(200, body, head=head, kind=kind)

    def do_GET(self) -> None:  # noqa: N802
        self._serve(head=False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(head=True)

    def _read_only(self) -> None:
        self._send(405, b"This viewer is read-only\n", head=False, allow="GET, HEAD")

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only


def bind(root: Path, port: int | None) -> _Server:
    """A listening server for ``root`` on 127.0.0.1."""
    ports = [port] if port is not None else [default_port(root) + step for step in range(PORT_TRIES)]
    for candidate in ports:
        try:
            server = _Server((HOST, candidate), _Handler)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE or candidate == ports[-1]:
                raise
            continue
        server.root = root
        return server
    raise OSError(errno.EADDRINUSE, "no free port to serve on")


def _install_sigterm_handler() -> Any:
    """Raise KeyboardInterrupt on SIGTERM in the main thread so cleanup runs cleanly."""
    if threading.current_thread() is not threading.main_thread():
        return None
    previous = signal.getsignal(signal.SIGTERM)

    def _handle(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle)
    return previous


def _restore_sigterm_handler(previous: Any) -> None:
    if previous is not None and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, previous)


def _register_viewer(mode: str, port: int, run_dir: Path | None = None, run_id: str = "") -> int | None:
    """Acquire viewer.lock if free and publish viewer.json; returns lock fd or None."""
    try:
        import shiploop_registry as registry
        lock_fd = registry.acquire_viewer_lock()
        if lock_fd is None:
            return None
        registry.write_viewer_info({
            "pid": os.getpid(),
            "host": HOST,
            "port": port,
            "url": f"http://{HOST}:{port}",
            "mode": mode,
            "run_dir": str(run_dir) if run_dir is not None else "",
            "run_id": run_id,
            "started_at": registry.now_utc(),
            "cli": str(Path(__file__).resolve().parent / "shiploop"),
        })
        return lock_fd
    except OSError:
        return None


def _release_viewer(lock_fd: int | None) -> None:
    if lock_fd is None:
        return
    try:
        import shiploop_registry as registry
        registry.clear_viewer_info(os.getpid())
    except OSError:
        pass
    try:
        import fcntl
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(lock_fd)
    except OSError:
        pass


def serve(root: Path, *, port: int | None = None, out: Callable[[str], None] | None = None) -> int:
    """Serve ``root``'s pages until interrupted; the address is announced once it is listening."""
    server = bind(root, port)
    actual_port = server.server_address[1]
    lock_fd = _register_viewer("single", actual_port, run_dir=root)
    previous_sigterm = _install_sigterm_handler()
    say = out or (lambda text: print(text, flush=True))
    say(f"ShipLoop viewer: http://{HOST}:{actual_port}/ (read-only, this machine only; Ctrl-C stops it)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _restore_sigterm_handler(previous_sigterm)
        _release_viewer(lock_fd)
        server.server_close()
    return 0


# ---------------------------------------------------------------- Multi-run hub

def _stat_mtime(path: Path) -> int:
    try:
        return path.lstat().st_mtime_ns
    except OSError:
        return 0


def _stat_size(path: Path) -> int:
    try:
        return path.lstat().st_size
    except OSError:
        return 0


def _read_json_safe(path: Path, limit: int = 256 * 1024) -> dict[str, Any]:
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return {}
    try:
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                return {}
            data = json.loads(handle.read(limit + 1).decode("utf-8"))
            return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, ValueError):
        return {}


def _experiments_mtime(run_dir: Path) -> int:
    exp_dir = run_dir / "experiments"
    latest = _stat_mtime(exp_dir)
    try:
        if exp_dir.is_dir() and not exp_dir.is_symlink():
            for child in sorted(exp_dir.iterdir())[:24]:
                if child.is_symlink():
                    continue
                latest = max(latest, _stat_mtime(child))
                if child.is_dir():
                    latest = max(latest, _stat_mtime(child / "decision.md"), _stat_mtime(child / "meta.json"))
    except OSError:
        pass
    return latest


def _run_cache_key(run_dir: Path, state: Mapping[str, Any]) -> tuple[Any, ...]:
    action_id = ""
    try:
        import shiploop_navigator as navigator
        cur = navigator.current_action(state)
        if isinstance(cur, Mapping):
            action_id = str(cur.get("id") or "")
    except Exception:  # noqa: BLE001
        pass
    return (
        state.get("revision"),
        state.get("status"),
        _stat_mtime(run_dir / "state.md"),
        _stat_mtime(run_dir / "timeline.json"),
        _stat_mtime(run_dir / "trace.jsonl"),
        _stat_size(run_dir / "trace.jsonl"),
        _stat_mtime(run_dir / "progress-observer.json"),
        _stat_mtime(run_dir / "callback-attempts"),
        _stat_mtime(run_dir / "owner-notes"),
        _experiments_mtime(run_dir),
        _stat_mtime(run_dir / f"loops/{action_id}-terminal.json") if action_id else 0,
        _stat_mtime(run_dir / f"checks/{action_id}.md") if action_id else 0,
        _stat_mtime(run_dir / "report.html"),
    )


def _priority_bucket(display_status: str) -> int:
    if display_status in ("awaiting", "service", "blocked"):
        return 0
    if display_status in ("active", "reviewing"):
        return 1
    if display_status == "paused":
        return 2
    return 3


def _parse_iso_ts(stamp: Any) -> float:
    if not isinstance(stamp, str) or not stamp:
        return 0.0
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def hub_runs_payload(
    extra_roots: Sequence[Path | str] = (),
    *,
    cache: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] | None = None,
    state_cache: dict[str, tuple[int, int, Mapping[str, Any]]] | None = None,
    viewer_info: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the JSON payload for ``GET /api/runs`` and ``shiploop runs --json``."""
    import shiploop_hub_model as hub_model
    import shiploop_navigator as navigator
    import shiploop_privacy as privacy
    import shiploop_progress as progress
    import shiploop_progress_data as data
    import shiploop_registry as registry
    import shiploop_story as story_data

    discovered = registry.discover_runs(extra_roots=extra_roots, state_cache=state_cache)
    conflicts = registry.shared_source_repo_conflicts(discovered)
    runs_out: list[dict[str, Any]] = []
    seen_dirs: set[str] = set()

    for entry in discovered:
        run_dir_str = entry["run_dir"]
        seen_dirs.add(run_dir_str)
        run_path = Path(run_dir_str)
        state = entry["state"]
        cache_key = _run_cache_key(run_path, state)
        cached = cache.get(run_dir_str) if cache is not None else None
        if cached is not None and cached[0] == cache_key:
            projected = dict(cached[1])
        else:
            try:
                navigator.validate(state)
            except Exception:  # noqa: BLE001
                continue
            display_status, display_label = navigator.display_status(state)
            timeline = {}
            tl_raw = registry._read_regular_bytes(run_path / "timeline.json", 1024 * 1024)
            if tl_raw is not None:
                try:
                    timeline, _ = story_data.normalise_timeline(json.loads(tl_raw.decode("utf-8")))
                except (UnicodeError, ValueError):
                    timeline = {}
            facts = navigator.narrative_facts(state, timeline or None)
            where = navigator._status_where(state)
            next_label, next_text = navigator._status_next(state)
            inflight = data.inflight_activity(run_path, state, timeline=timeline)
            goal = navigator._status_text(navigator._title_from_prompt(state.get("prompt") or ""), 110)
            goal = privacy.redact_text(goal)
            reason = privacy.redact_text(str(state.get("status_reason") or ""))
            obs_record = _read_json_safe(run_path / progress.STATUS, 16 * 1024)
            obs_running = False
            try:
                obs_running = progress.running(run_path)
            except (OSError, ValueError):
                obs_running = False
            planning_summary = ""
            try:
                import shiploop_planning_status as planning_status
                obs = planning_status.plan_observability(run_path, state)
                planning_summary = " · ".join(
                    " ".join(line.split()) for line in planning_status.status_lines(obs) if line.strip()
                )
            except Exception:  # noqa: BLE001
                planning_summary = ""
            extras = hub_model.run_summary_extras(run_path, state, timeline, entry)
            terminal = state.get("status") in ("done", "halted")
            has_report = terminal and (run_path / "report.html").is_file()
            key = entry["run_key"]
            projected = {
                "run_id": entry["run_id"],
                "run_key": key,
                "run_dir": run_dir_str,
                "repo": entry["repo"],
                "source_repo": entry["source_repo"],
                "repo_name": Path(entry["source_repo"] or entry["repo"]).name or entry["repo"],
                "workspace_root": entry["workspace_root"],
                "execution_mode": entry["execution_mode"],
                "delegation": entry["delegation"],
                "host": entry["host"],
                "status": state.get("status"),
                "display_status": display_status,
                "display_label": display_label,
                "priority_bucket": _priority_bucket(display_status),
                "goal": goal,
                "revision": state.get("revision"),
                "stage": navigator.current_stage(state),
                "where": where,
                "next_label": next_label,
                "next_text": next_text,
                "reason": reason,
                "planning_summary": planning_summary,
                "phases": facts["phases"],
                "inflight": inflight,
                "observer": {
                    "running": obs_running,
                    "status": obs_record.get("status", ""),
                    "observed_at": obs_record.get("observed_at", ""),
                },
                "urls": {
                    "progress": f"/runs/{key}/progress.html",
                    "trace": f"/runs/{key}/trace.html",
                    "report": f"/runs/{key}/report.html" if has_report else None,
                },
                **extras,
            }
            if cache is not None:
                cache[run_dir_str] = (cache_key, projected)

        # Keep live owner liveness & shared-repo conflict tags fresh even when state files are cached.
        source_abs = os.path.abspath(str(projected.get("source_repo") or projected.get("repo") or ""))
        conflict_peers = [rid for rid in conflicts.get(source_abs, ()) if rid != projected["run_id"]]
        attention: list[str] = []
        ds = projected["display_status"]
        if ds == "awaiting":
            attention.append("Waiting on you")
        elif ds == "service":
            attention.append("Waiting on service")
        elif ds == "blocked":
            attention.append("Blocked")
        if projected["status"] == "active" and entry["owner_alive"] is False:
            attention.append("Host owner process not running")
        if conflict_peers:
            attention.append(f"Shares source repo with {', '.join(conflict_peers)}")
        projected = {
            **projected,
            "run_key": entry["run_key"],
            "model": entry.get("model") or projected.get("model", ""),
            "effort": entry.get("effort") or projected.get("effort", ""),
            "urls": {
                "progress": f"/runs/{entry['run_key']}/progress.html",
                "trace": f"/runs/{entry['run_key']}/trace.html",
                "report": (f"/runs/{entry['run_key']}/report.html"
                           if projected["urls"].get("report") else None),
            },
            "keepalive": {
                "owner": entry["keepalive_owner"],
                "alive": entry["owner_alive"],
            },
            "shared_repo_peers": conflict_peers,
            "attention_reasons": attention,
        }
        if attention and projected["priority_bucket"] > 0 and projected["status"] not in ("done", "halted"):
            projected["priority_bucket"] = 0
        runs_out.append(projected)

    if cache is not None:
        for stale in list(cache):
            if stale not in seen_dirs:
                del cache[stale]

    # Within each priority bucket, show highest attention count and newest activity first.
    runs_out.sort(key=lambda row: (
        row["priority_bucket"],
        -len(row["attention_reasons"]),
        -_parse_iso_ts(row["inflight"].get("last_event_at")),
        row["run_id"],
    ))

    counts = {
        "total": len(runs_out),
        "attention": sum(1 for r in runs_out if r["priority_bucket"] == 0),
        "active": sum(1 for r in runs_out if r["display_status"] in ("active", "reviewing")),
        "paused": sum(1 for r in runs_out if r["display_status"] == "paused"),
        "done": sum(1 for r in runs_out if r["display_status"] in ("done", "halted")),
    }
    version_basis = json.dumps(
        {"counts": counts, "conflicts": conflicts, "runs": runs_out},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    runs_version = hashlib.sha256(version_basis).hexdigest()[:16]
    return {
        "schema": "shiploop-hub/v1",
        "runs_version": runs_version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "viewer": dict(viewer_info) if viewer_info else registry.active_viewer(),
        "shared_repo_conflicts": conflicts,
        "counts": counts,
        "runs": runs_out,
    }


class _HubServer(ThreadingHTTPServer):
    daemon_threads = True
    extra_roots: tuple[Path, ...]
    cache: dict[str, tuple[tuple[Any, ...], dict[str, Any]]]
    state_cache: dict[str, tuple[int, int, Mapping[str, Any]]]
    detail_cache: dict[str, tuple[tuple[Any, ...], str, dict[str, Any]]]
    viewer_info: dict[str, Any]
    _lock: threading.RLock
    _run_map: dict[str, Path]
    _run_entries: dict[str, dict[str, Any]]

    def allowed_hosts(self) -> frozenset[str]:
        port = self.server_address[1]
        return frozenset({f"{HOST}:{port}", f"localhost:{port}", f"[::1]:{port}"})

    def _update_run_index(self, runs: Sequence[Mapping[str, Any]]) -> None:
        with self._lock:
            self._run_map = {str(row["run_key"]): Path(str(row["run_dir"])) for row in runs}
            self._run_entries = {str(row["run_key"]): dict(row) for row in runs}

    def get_runs_payload(self) -> dict[str, Any]:
        with self._lock:
            payload = hub_runs_payload(
                self.extra_roots,
                cache=self.cache,
                state_cache=self.state_cache,
                viewer_info=self.viewer_info,
            )
            runs = payload["runs"]
            self._update_run_index(runs)
            seen_dirs = {str(row["run_dir"]) for row in runs}
            for stale in list(self.detail_cache):
                if stale not in seen_dirs:
                    del self.detail_cache[stale]
            return payload

    def resolve_run_dir(self, run_key: str) -> Path | None:
        with self._lock:
            found = self._run_map.get(run_key)
        if found is not None and found.is_dir() and not found.is_symlink():
            return found
        import shiploop_registry as registry
        with self._lock:
            discovered = registry.discover_runs(extra_roots=self.extra_roots, state_cache=self.state_cache)
            self._run_map = {item["run_key"]: Path(item["run_dir"]) for item in discovered}
            self._run_entries = {item["run_key"]: dict(item) for item in discovered}
            return self._run_map.get(run_key)

    def _load_state_cached(self, run_dir: Path) -> Mapping[str, Any]:
        run_dir_str = str(run_dir)
        state_path = run_dir / "state.md"
        info = state_path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("state.md is not a regular file")
        with self._lock:
            cached = self.state_cache.get(run_dir_str)
        if cached is not None and cached[0] == info.st_mtime_ns and cached[1] == info.st_size:
            return cached[2]
        import shiploop_hub_model as hub_model
        state = hub_model.load_state_safe(run_dir)
        with self._lock:
            self.state_cache[run_dir_str] = (info.st_mtime_ns, info.st_size, state)
        return state

    def get_run_detail(self, run_key: str) -> tuple[str, dict[str, Any]] | None:
        run_dir = self.resolve_run_dir(run_key)
        if run_dir is None:
            return None
        import shiploop_hub_model as hub_model
        with self._lock:
            entry = self._run_entries.get(run_key)
        try:
            state = self._load_state_cached(run_dir)
            sig = hub_model.detail_watch_signature(run_dir, state, entry=entry)
        except (OSError, ValueError):
            return None
        ver = hub_model.detail_version_digest(sig)
        run_dir_str = str(run_dir)
        with self._lock:
            cached = self.detail_cache.get(run_dir_str)
        if cached is not None and cached[0] == sig:
            return cached[1], dict(cached[2])
        try:
            detail = hub_model.build_run_detail(run_dir, entry=entry)
        except (OSError, ValueError):
            return None
        with self._lock:
            self.detail_cache[run_dir_str] = (sig, ver, detail)
        return ver, detail


class _HubHandler(BaseHTTPRequestHandler):
    server: _HubServer
    server_version = "ShipLoopHub"
    sys_version = ""

    def version_string(self) -> str:
        return self.server_version

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass

    def _send(self, status: int, body: bytes, *, head: bool, kind: str = "text/plain; charset=utf-8",
              allow: str = "", policy: str = HUB_POLICY, extra_headers: Mapping[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", policy)
        if allow:
            self.send_header("Allow", allow)
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _send_json(self, status: int, payload: Any, *, head: bool) -> None:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send(status, raw, head=head, kind=JSON, policy=HUB_POLICY)

    def _serve_run_page(self, run_dir: Path, subpath: str, *, head: bool) -> None:
        name, kind = PAGES.get("/" + subpath.lstrip("/"), (None, ""))
        if name is None:
            return self._send(404, b"Not found\n", head=head, policy=POLICY)
        if not head and name in ("progress.html", "trace.html"):
            try:
                import shiploop_progress as progress
                if not progress.finished(run_dir) and not (run_dir / progress.DISABLED).exists():
                    if not (run_dir / name).exists():
                        progress.observe(run_dir, watch=False)
                    if not progress.running(run_dir):
                        progress.ensure(run_dir)
            except Exception:  # noqa: BLE001 - best-effort wakeup when viewing a run
                pass
        try:
            body = read_page(run_dir, name)
        except FileNotFoundError:
            return self._send(404, f"{name} is not published yet\n".encode(), head=head, policy=POLICY)
        except (OSError, ValueError):
            return self._send(403, f"{name} is not a plain file\n".encode(), head=head, policy=POLICY)
        self._send(200, body, head=head, kind=kind, policy=POLICY)

    def _serve(self, *, head: bool) -> None:
        if (self.headers.get("Host") or "").lower() not in self.server.allowed_hosts():
            return self._send(403, b"Unknown host\n", head=head)
        parsed = urlsplit(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            return self._send(200, _HUB_HTML.encode("utf-8"), head=head, kind=HTML, policy=HUB_POLICY)
        if path == "/api/runs":
            payload = self.server.get_runs_payload()
            return self._send_json(200, payload, head=head)
        if path == "/api/poll":
            qs = parse_qs(parsed.query, keep_blank_values=True)
            req_run = (qs.get("run") or [""])[0].strip()
            auto_select = (qs.get("auto") or [""])[0].strip() == "1"
            client_runs_v = (qs.get("runs_v") or [""])[0].strip()
            client_run_v = (qs.get("run_v") or [""])[0].strip()

            runs_payload = self.server.get_runs_payload()
            runs_version = str(runs_payload.get("runs_version") or "")
            runs_changed = client_runs_v != runs_version

            if not req_run and auto_select and runs_payload["runs"]:
                req_run = str(runs_payload["runs"][0]["run_key"])

            detail_res = self.server.get_run_detail(req_run) if req_run else None
            detail_missing = bool(req_run and detail_res is None)
            run_version = detail_res[0] if detail_res is not None else ""
            detail_changed = bool(detail_res is not None and client_run_v != run_version)

            if not runs_changed and not detail_changed and not detail_missing:
                return self._send_json(200, {
                    "schema": "shiploop-hub-poll/v1",
                    "unchanged": True,
                    "selected_run": req_run,
                    "runs_version": runs_version,
                    "run_version": run_version,
                    "generated_at": runs_payload["generated_at"],
                }, head=head)

            body: dict[str, Any] = {
                "schema": "shiploop-hub-poll/v1",
                "unchanged": False,
                "selected_run": req_run,
                "runs_version": runs_version,
                "run_version": run_version,
                "generated_at": runs_payload["generated_at"],
            }
            if runs_changed:
                body["runs_payload"] = runs_payload
            if detail_changed and detail_res is not None:
                body["detail"] = detail_res[1]
            elif detail_missing:
                body["detail_error"] = "not_found"
            return self._send_json(200, body, head=head)

        if path.startswith("/api/runs/"):
            rest = path[len("/api/runs/"):]
            run_key, sep, sub = rest.partition("/")
            if not sep or not run_key:
                return self._send(404, b"Not found\n", head=head)
            if sub == "detail":
                res = self.server.get_run_detail(run_key)
                if res is None:
                    return self._send(404, b"Unknown run\n", head=head)
                return self._send_json(200, res[1], head=head)
            if sub == "artifact":
                run_dir = self.server.resolve_run_dir(run_key)
                if run_dir is None:
                    return self._send(404, b"Unknown run\n", head=head)
                qs = parse_qs(parsed.query, keep_blank_values=True)
                scope = (qs.get("scope") or ["run"])[0].strip()
                rel_path = (qs.get("path") or [""])[0]
                if not rel_path or scope not in ("run", "repo"):
                    return self._send(400, b"Invalid artifact parameters\n", head=head)
                import shiploop_hub_model as hub_model
                import shiploop_observation_io as obs_io
                try:
                    st = self.server._load_state_cached(run_dir)
                    artifact = hub_model.read_run_artifact(run_dir, st, scope, rel_path)
                except FileNotFoundError:
                    return self._send(404, b"Artifact not found\n", head=head)
                except (PermissionError, obs_io._UnsafeSource, ValueError) as exc:
                    return self._send(403, (str(exc) + "\n").encode("utf-8"), head=head)
                except OSError:
                    return self._send(403, b"Artifact unavailable\n", head=head)
                return self._send_json(200, artifact, head=head)
            return self._send(404, b"Not found\n", head=head)

        if path.startswith("/runs/"):
            rest = path[len("/runs/"):]
            if "/" not in rest:
                return self._send(302, b"", head=head, extra_headers={"Location": f"/runs/{rest}/"})
            run_key, _, sub = rest.partition("/")
            run_dir = self.server.resolve_run_dir(run_key)
            if run_dir is None:
                return self._send(404, b"Unknown run\n", head=head, policy=POLICY)
            return self._serve_run_page(run_dir, sub, head=head)
        self._send(404, b"Not found\n", head=head)

    def do_GET(self) -> None:  # noqa: N802
        self._serve(head=False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(head=True)

    def _read_only(self) -> None:
        self._send(405, b"This viewer is read-only\n", head=False, allow="GET, HEAD")

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only


def bind_hub(extra_roots: Sequence[Path | str] = (), port: int | None = None) -> _HubServer:
    """Bind the multi-run hub server on 127.0.0.1."""
    ports = [port] if port is not None else [DEFAULT_HUB_PORT + step for step in range(PORT_TRIES)]
    for candidate in ports:
        try:
            server = _HubServer((HOST, candidate), _HubHandler)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE or candidate == ports[-1]:
                raise
            continue
        server.extra_roots = tuple(Path(os.path.abspath(os.fspath(item))) for item in extra_roots)
        server.cache = {}
        server.state_cache = {}
        server.detail_cache = {}
        server._lock = threading.RLock()
        server._run_map = {}
        server._run_entries = {}
        server.viewer_info = {
            "pid": os.getpid(),
            "host": HOST,
            "port": server.server_address[1],
            "url": f"http://{HOST}:{server.server_address[1]}",
            "mode": "hub",
        }
        return server
    raise OSError(errno.EADDRINUSE, "no free port to serve on")


def serve_hub(
    *,
    extra_roots: Sequence[Path | str] = (),
    port: int | None = None,
    out: Callable[[str], None] | None = None,
) -> int:
    """Serve the multi-run ShipLoop hub until interrupted."""
    import shiploop_registry as registry

    combined_roots: list[Path | str] = list(extra_roots)
    for root in registry.default_cwd_roots():
        if root not in combined_roots:
            combined_roots.append(root)
    server = bind_hub(extra_roots=combined_roots, port=port)
    actual_port = server.server_address[1]
    server.viewer_info["port"] = actual_port
    server.viewer_info["url"] = f"http://{HOST}:{actual_port}"
    try:
        registry.prune_registry()
    except Exception:  # noqa: BLE001
        pass
    lock_fd = _register_viewer("hub", actual_port)
    previous_sigterm = _install_sigterm_handler()
    say = out or (lambda text: print(text, flush=True))
    say(f"ShipLoop hub: http://{HOST}:{actual_port}/ (read-only, all runs, this machine only; Ctrl-C stops it)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _restore_sigterm_handler(previous_sigterm)
        _release_viewer(lock_fd)
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit("run it through `shiploop view --serve`")
