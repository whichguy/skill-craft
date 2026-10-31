"""Opt-in read-only viewer: serve a run's published HTML pages on 127.0.0.1 for a browser.

The user starts it in their own terminal with ``shiploop view --serve``; ShipLoop never starts it, so every command
stays visible to the host's hooks. It answers GET and HEAD for three files of the run directory and nothing else. It
reads those files and never writes, so it cannot change a run; the observer (``shiploop_progress``) still owns every
page. While it runs, any process on this machine can read the pages.
"""
from __future__ import annotations

import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import stat
import sys
from typing import Callable
from urllib.parse import urlsplit
import zlib

HOST = "127.0.0.1"
# The default port comes from the run directory, so one run keeps its address across restarts and two runs rarely
# collide; a taken port moves on to the next one.
PORT_BASE = 40000
PORT_SPAN = 20000
PORT_TRIES = 50
# The pages a run publishes. Nothing else in the run directory is reachable.
PAGES = {"/": "progress.html", "/progress.html": "progress.html", "/trace.html": "trace.html",
         "/report.html": "report.html"}
# The pages are self-contained: inline script and style, data: images and fonts, no network.
POLICY = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; "
          "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def default_port(root: Path) -> int:
    """The port this run's viewer tries first."""
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

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the stdlib signature
        pass  # the terminal shows the address, not a line per refresh

    def _send(self, status: int, body: bytes, *, head: bool, html: bool = False, allow: str = "") -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if html else "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", POLICY)
        if allow:
            self.send_header("Allow", allow)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _serve(self, *, head: bool) -> None:
        # A page on another site that resolves its own name to 127.0.0.1 would otherwise read these pages.
        if (self.headers.get("Host") or "").lower() not in self.server.allowed_hosts():
            return self._send(403, b"Unknown host\n", head=head)
        name = PAGES.get(urlsplit(self.path).path)
        if name is None:
            return self._send(404, b"Not found\n", head=head)
        try:
            body = read_page(self.server.root, name)
        except FileNotFoundError:
            return self._send(404, f"{name} is not published yet\n".encode(), head=head)
        except (OSError, ValueError):
            return self._send(403, f"{name} is not a plain file\n".encode(), head=head)
        self._send(200, body, head=head, html=True)

    def do_GET(self) -> None:  # noqa: N802 - the stdlib's handler names
        self._serve(head=False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(head=True)

    def _read_only(self) -> None:
        self._send(405, b"This viewer is read-only\n", head=False, allow="GET, HEAD")

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only


def bind(root: Path, port: int | None) -> _Server:
    """A listening server for ``root`` on 127.0.0.1. ``port`` None tries the run's default port, then the next ones;
    an explicit port (0 lets the system pick) is taken as given."""
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


def serve(root: Path, *, port: int | None = None, out: Callable[[str], None] | None = None) -> int:
    """Serve ``root``'s pages until interrupted; the address is announced once it is listening."""
    server = bind(root, port)
    say = out or (lambda text: print(text, flush=True))
    say(f"ShipLoop viewer: http://{HOST}:{server.server_address[1]}/ (read-only, this machine only; Ctrl-C stops it)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit("run it through `shiploop view --serve`")
