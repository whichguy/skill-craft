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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import stat
import sys
import threading
import time
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit
import zlib

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
        _stat_mtime(run_dir / "progress-observer.json"),
        _stat_mtime(run_dir / "callback-attempts"),
        _stat_mtime(run_dir / "owner-notes"),
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


def hub_runs_payload(
    extra_roots: Sequence[Path | str] = (),
    *,
    cache: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] | None = None,
    viewer_info: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the JSON payload for ``GET /api/runs`` and ``shiploop runs --json``."""
    import shiploop_navigator as navigator
    import shiploop_privacy as privacy
    import shiploop_progress as progress
    import shiploop_progress_data as data
    import shiploop_registry as registry
    import shiploop_story as story_data

    discovered = registry.discover_runs(extra_roots=extra_roots)
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

    runs_out.sort(key=lambda row: (
        row["priority_bucket"],
        -(len(row["attention_reasons"])),
        str(row["inflight"].get("last_event_at") or ""),
        row["run_id"],
    ))
    # Within each bucket, show newest activity first.
    runs_out.sort(key=lambda row: row["priority_bucket"])

    counts = {
        "total": len(runs_out),
        "attention": sum(1 for r in runs_out if r["priority_bucket"] == 0),
        "active": sum(1 for r in runs_out if r["display_status"] in ("active", "reviewing")),
        "paused": sum(1 for r in runs_out if r["display_status"] == "paused"),
        "done": sum(1 for r in runs_out if r["display_status"] in ("done", "halted")),
    }
    return {
        "schema": "shiploop-hub/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "viewer": dict(viewer_info) if viewer_info else registry.active_viewer(),
        "shared_repo_conflicts": conflicts,
        "counts": counts,
        "runs": runs_out,
    }


_HUB_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>ShipLoop Hub · Concurrent Runs</title>
<style>
:root{--bg:#f3f6f2;--panel:#fff;--ink:#15231f;--muted:#63736b;--line:#dce5df;--green:#206b50;--soft:#e9f3ed;--amber:#946418;--amber-bg:#fbf3df;--rose:#a23b43;--rose-bg:#fbe8ea;--blue:#1e4762;--blue-bg:#e8f2f9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 22px 56px}
.masthead{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}
.brand{font-size:.78rem;letter-spacing:.16em;font-weight:750;color:var(--green)}
.hero{padding:24px 28px;background:#143d32;color:#f7fbf8;border-radius:18px;box-shadow:0 16px 36px #193c2b18}
.hero h1{margin:4px 0 6px;font-size:1.65rem;letter-spacing:-.03em}.hero p{margin:0;color:#d6e6dc;font-size:.9rem}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
.stat{background:#ffffff1a;border:1px solid #ffffff29;border-radius:99px;padding:5px 12px;font-size:.82rem;font-weight:650}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0 20px;padding:12px 14px;background:var(--panel);border:1px solid var(--line);border-radius:12px}
.controls input[type=search]{flex:1;min-width:210px;padding:7px 10px;border:1px solid #cddbd1;border-radius:8px;font:inherit}
.btn{font:inherit;font-size:.82rem;font-weight:650;border:1px solid #cddbd1;background:#fff;color:#244c3d;border-radius:8px;padding:6px 11px;cursor:pointer}
.btn:hover{background:var(--soft)}.btn.active{background:#143d32;color:#fff;border-color:#143d32}
.meta-clock{font-size:.78rem;color:var(--muted);margin-left:auto}
.banner{padding:12px 16px;border-radius:12px;margin-bottom:16px;background:var(--amber-bg);border:1px solid #e6cf98;color:#62430c;font-size:.88rem}
.section-title{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:22px 0 10px;font-weight:750}
.grid{display:grid;gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:grid;gap:10px}
.card.attention{border-left:4px solid var(--amber)}
.card.blocked{border-left:4px solid var(--rose)}
.card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.card-title{margin:0;font-size:1.05rem;line-height:1.35;overflow-wrap:anywhere}
.subline{font-size:.82rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 14px}
.pill{display:inline-flex;align-items:center;border-radius:99px;padding:3px 10px;font-size:.74rem;font-weight:700;background:#edf1ee;color:#4a5a52;white-space:nowrap}
.pill-active{background:#e1f1e7;color:#1b5c3e}.pill-reviewing{background:var(--blue-bg);color:var(--blue)}
.pill-awaiting,.pill-service,.pill-paused{background:var(--amber-bg);color:var(--amber)}
.pill-blocked,.pill-halted{background:var(--rose-bg);color:var(--rose)}.pill-done{background:#e1f1e7;color:#1b5c3e}
.where{font-size:.86rem;background:#f5f8f6;border-left:3px solid var(--green);padding:8px 11px;border-radius:0 8px 8px 0;overflow-wrap:anywhere}
.next-line{font-size:.82rem;color:#3d5046;overflow-wrap:anywhere}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{font-size:.73rem;padding:2px 8px;border-radius:7px;background:#eef3ef;color:#354b40}
.chip.warn{background:var(--amber-bg);color:#754f0f;font-weight:650}.chip.danger{background:var(--rose-bg);color:var(--rose);font-weight:650}
.phases{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.phase{background:#f8faf8;border:1px solid #e6ede8;border-radius:8px;padding:6px 9px;font-size:.74rem}
.bar{height:4px;border-radius:99px;background:#e3ebe5;margin-top:4px;overflow:hidden}.bar span{display:block;height:100%;background:var(--green)}
.links{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding-top:4px}
.links a{font-size:.8rem;font-weight:650;text-decoration:none;color:var(--green);border:1px solid #cddbd1;border-radius:7px;padding:4px 10px;background:#fff}
.links a:hover{background:var(--soft)}
.empty{background:var(--panel);border:1px dashed var(--line);border-radius:12px;padding:20px;color:var(--muted);text-align:center}
@media(max-width:680px){.phases{grid-template-columns:1fr}.meta-clock{margin-left:0}}
</style>
</head>
<body>
<main>
  <div class="masthead"><span class="brand">SHIPLOOP / MULTI-RUN HUB</span><span id="hub-status" class="meta-clock">Loading…</span></div>
  <section class="hero">
    <h1>Concurrent ShipLoop Runs</h1>
    <p>Read-only live view across active, waiting, paused, and finished runs on this machine.</p>
    <div class="stats" id="stats"></div>
  </section>
  <section class="controls">
    <input id="q" type="search" placeholder="Filter by repo, goal, run ID, stage…">
    <button class="btn active" data-filter="all" type="button">All</button>
    <button class="btn" data-filter="attention" type="button">Needs attention</button>
    <button class="btn" data-filter="active" type="button">Active</button>
    <button class="btn" data-filter="done" type="button">Finished</button>
    <button class="btn" id="toggle-live" type="button">Pause polling</button>
    <button class="btn" id="refresh-now" type="button">Refresh now</button>
  </section>
  <div id="conflicts"></div>
  <div id="runs-root"><div class="empty">Scanning runs…</div></div>
</main>
<script>
(() => {
  "use strict";
  let filter = "all", query = "", paused = false, timer = null, lastData = null;
  const el = (tag, attrs, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") node.className = v;
      else node.setAttribute(k, v === true ? "" : String(v));
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  };
  const age = (stamp) => {
    if (!stamp) return "time unknown";
    const d = new Date(stamp);
    if (Number.isNaN(d.getTime())) return String(stamp);
    const s = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.floor(s / 60) + "m ago";
    return Math.floor(s / 3600) + "h ago";
  };
  const phaseNode = (p) => {
    const total = Number(p.total) || 0, done = Number(p.done) || 0;
    const pct = p.state === "done" ? 100 : (total > 0 ? Math.min(100, Math.round(100 * done / total)) : 0);
    const label = p.state === "done" ? "done" : (total > 0 ? (p.done_label + "/" + total) : (p.state === "current" ? "active" : "pending"));
    return el("div", {class: "phase"},
      el("div", {}, el("strong", {}, p.name), " · ", label),
      el("div", {class: "bar"}, el("span", {style: "width:" + pct + "%"})));
  };
  const card = (r) => {
    const inf = r.inflight || {};
    const chips = [
      el("span", {class: "chip"}, "rev " + r.revision),
      el("span", {class: "chip"}, r.delegation || "inline"),
      r.host ? el("span", {class: "chip"}, r.host) : null,
      inf.step_id && inf.step_total ? el("span", {class: "chip"}, "Step " + inf.step_id + " (" + inf.step_number + "/" + inf.step_total + ")") : null,
      inf.loop_iteration ? el("span", {class: "chip"}, "Loop pass " + inf.loop_iteration) : null,
      inf.plan_sandboxes ? el("span", {class: "chip"}, "Sandboxes " + inf.plan_sandboxes) : null,
      inf.plan_questions ? el("span", {class: "chip"}, "Exp Qs " + inf.plan_questions) : null,
      inf.improve_active ? el("span", {class: "chip"}, "Improve " + (inf.improve_review_mode || "") + (inf.improve_passes ? " · pass " + inf.improve_passes : "")) : null,
      typeof inf.last_check_yes === "boolean" ? el("span", {class: "chip"}, "Check: " + (inf.last_check_yes ? "yes" : "no")) : null,
      (inf.open_notes || inf.carried_notes) ? el("span", {class: "chip warn"}, (inf.open_notes || 0) + " open note(s)") : null,
      ...(r.attention_reasons || []).map((why) => el("span", {class: r.display_status === "blocked" ? "chip danger" : "chip warn"}, why)),
    ];
    const cls = "card" + (r.display_status === "blocked" || r.display_status === "halted" ? " blocked" : (r.priority_bucket === 0 ? " attention" : ""));
    const links = el("div", {class: "links"},
      el("a", {href: r.urls.progress}, "Progress view →"),
      el("a", {href: r.urls.trace}, "Run trace →"),
      r.urls.report ? el("a", {href: r.urls.report}, "Final report →") : null);
    return el("article", {class: cls},
      el("div", {class: "card-top"},
        el("div", {},
          el("h3", {class: "card-title"}, r.goal || r.run_id),
          el("div", {class: "subline"},
            el("span", {}, "Repo: ", el("strong", {}, r.repo_name || r.repo)),
            el("span", {}, "Run: ", r.run_id),
            el("span", {}, "Last event: ", age(inf.last_event_at)),
            el("span", {}, r.observer && r.observer.running ? "Observer: live" : "Observer: idle/off"))),
        el("span", {class: "pill pill-" + (r.display_status || "active")}, r.display_label || r.status)),
      el("div", {class: "where"}, r.where || r.stage),
      el("div", {class: "next-line"}, (r.next_label || "Next") + ": " + (r.next_text || "")),
      r.reason ? el("div", {class: "next-line"}, "Reason: " + r.reason) : null,
      el("div", {class: "phases"}, (r.phases || []).map(phaseNode)),
      el("div", {class: "chips"}, chips),
      links);
  };
  const render = (data) => {
    lastData = data;
    const c = data.counts || {};
    document.getElementById("stats").replaceChildren(
      el("span", {class: "stat"}, (c.total || 0) + " total"),
      el("span", {class: "stat"}, (c.attention || 0) + " needs attention"),
      el("span", {class: "stat"}, (c.active || 0) + " active"),
      el("span", {class: "stat"}, (c.paused || 0) + " paused"),
      el("span", {class: "stat"}, (c.done || 0) + " finished"));
    const conflicts = data.shared_repo_conflicts || {};
    const conflictNodes = Object.entries(conflicts).map(([repo, ids]) =>
      el("div", {class: "banner"}, "Shared source repo warning: ", el("strong", {}, repo),
        " has " + ids.length + " concurrent non-terminal runs (" + ids.join(", ") + "). "
        + "Each builds in an isolated worktree; the second workspace return will reconcile against the first."));
    document.getElementById("conflicts").replaceChildren(...conflictNodes);
    const needle = query.trim().toLowerCase();
    const visible = (data.runs || []).filter((r) => {
      if (filter === "attention" && r.priority_bucket !== 0) return false;
      if (filter === "active" && !["active", "reviewing"].includes(r.display_status)) return false;
      if (filter === "done" && !["done", "halted"].includes(r.display_status)) return false;
      if (!needle) return true;
      return [r.goal, r.run_id, r.repo_name, r.source_repo, r.where, r.display_label].join(" ").toLowerCase().includes(needle);
    });
    const groups = [
      ["Needs attention", visible.filter((r) => r.priority_bucket === 0)],
      ["Active & Reviewing", visible.filter((r) => r.priority_bucket === 1)],
      ["Paused", visible.filter((r) => r.priority_bucket === 2)],
      ["Completed & Halted", visible.filter((r) => r.priority_bucket === 3)],
    ];
    const nodes = [];
    for (const [title, rows] of groups) {
      if (!rows.length) continue;
      nodes.push(el("h2", {class: "section-title"}, title + " (" + rows.length + ")"));
      nodes.push(el("div", {class: "grid"}, rows.map(card)));
    }
    if (!nodes.length) nodes.push(el("div", {class: "empty"}, "No ShipLoop runs match the current filter."));
    document.getElementById("runs-root").replaceChildren(...nodes);
    document.getElementById("hub-status").textContent = "Updated " + age(data.generated_at) + (paused ? " · polling paused" : "");
  };
  const poll = async () => {
    try {
      const resp = await fetch("/api/runs", {cache: "no-store"});
      if (resp.ok) render(await resp.json());
    } catch (_) {}
  };
  const schedule = () => {
    if (timer) clearInterval(timer);
    timer = paused ? null : setInterval(poll, 3000);
  };
  document.getElementById("q").addEventListener("input", (e) => { query = e.target.value; if (lastData) render(lastData); });
  document.querySelectorAll("[data-filter]").forEach((btn) => btn.addEventListener("click", () => {
    filter = btn.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((b) => b.classList.toggle("active", b === btn));
    if (lastData) render(lastData);
  }));
  document.getElementById("toggle-live").addEventListener("click", (e) => {
    paused = !paused;
    e.target.textContent = paused ? "Resume polling" : "Pause polling";
    if (!paused) poll();
    schedule();
  });
  document.getElementById("refresh-now").addEventListener("click", poll);
  poll();
  schedule();
})();
</script>
</body>
</html>
"""


class _HubServer(ThreadingHTTPServer):
    daemon_threads = True
    extra_roots: tuple[Path, ...]
    cache: dict[str, tuple[tuple[Any, ...], dict[str, Any]]]
    viewer_info: dict[str, Any]
    _lock: threading.Lock
    _run_map: dict[str, Path]

    def allowed_hosts(self) -> frozenset[str]:
        port = self.server_address[1]
        return frozenset({f"{HOST}:{port}", f"localhost:{port}", f"[::1]:{port}"})

    def resolve_run_dir(self, run_key: str) -> Path | None:
        with self._lock:
            found = self._run_map.get(run_key)
        if found is not None and found.is_dir() and not found.is_symlink():
            return found
        import shiploop_registry as registry
        mapping = {item["run_key"]: Path(item["run_dir"])
                   for item in registry.discover_runs(extra_roots=self.extra_roots)}
        with self._lock:
            self._run_map = mapping
            return self._run_map.get(run_key)


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
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, _HUB_HTML.encode("utf-8"), head=head, kind=HTML, policy=HUB_POLICY)
        if path == "/api/runs":
            payload = hub_runs_payload(self.server.extra_roots, cache=self.server.cache,
                                       viewer_info=self.server.viewer_info)
            with self.server._lock:
                self.server._run_map = {row["run_key"]: Path(row["run_dir"]) for row in payload["runs"]}
            raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            return self._send(200, raw, head=head, kind=JSON, policy=HUB_POLICY)
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
        server._lock = threading.Lock()
        server._run_map = {}
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
    server = bind_hub(extra_roots=extra_roots, port=port)
    actual_port = server.server_address[1]
    server.viewer_info["port"] = actual_port
    server.viewer_info["url"] = f"http://{HOST}:{actual_port}"
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
