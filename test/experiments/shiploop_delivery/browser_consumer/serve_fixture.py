#!/usr/bin/env python3
"""Serve one static consumer fixture on loopback until interrupted."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import signal
import threading


ROOT = Path(__file__).resolve().parent
CASES = {
    "working": ROOT / "served-working",
    "broken": ROOT / "served-broken",
    "stale": ROOT / "served-stale",
    "login": ROOT / "served-login",
}


class QuietHandler(SimpleHTTPRequestHandler):
    """Keep an interactive fixture from adding request noise to stdout."""

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class LoopbackFixture:
    """Context manager used by the static check and available to manual callers."""

    def __init__(self, case: str) -> None:
        self.case = case
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "LoopbackFixture":
        directory = CASES[self.case]
        handler = partial(QuietHandler, directory=str(directory))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    @property
    def url(self) -> str:
        if self.server is None:
            raise RuntimeError("fixture server is not running")
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/"

    def __exit__(self, *_unused) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    args = parser.parse_args()
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    with LoopbackFixture(args.case) as fixture:
        print(f"Fixture case: {args.case}")
        print(f"Open in a browser: {fixture.url}")
        stop.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
