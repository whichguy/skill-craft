#!/usr/bin/env python3
"""Product checks for the `seat-reservations` case (style: stateful-service).

Run from the case's work directory: `python3 seat_service.py <check>`. Each check
starts `python3 server.py` with its own PORT and a DATA_FILE in a temporary
directory, exercises the HTTP contract the case prompt states, stops the
server, and exits 0 on pass. Nothing is written into the work directory. The
concurrency check asserts an invariant (never more seats than capacity), not
timing, so it cannot flake on a correct service.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import contextlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def fail(reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(1)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def server(data_file: Path, port: int | None = None):
    port = port or free_port()
    env = dict(os.environ, PORT=str(port), DATA_FILE=str(data_file))
    proc = subprocess.Popen([sys.executable, "server.py"], env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if proc.poll() is not None:
                fail("server.py exited early: " + (proc.stderr.read() or "")[-400:])
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            fail("server.py did not listen on PORT within 10 seconds")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def call(base: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"{}")
        except ValueError:
            return error.code, {}


def expect(got: tuple[int, dict], status: int, what: str, **fields) -> dict:
    code, body = got
    if code != status:
        fail(f"{what}: want HTTP {status}, got {code} {body}")
    for key, value in fields.items():
        if body.get(key) != value:
            fail(f"{what}: want {key}={value}, got {body}")
    return body


def unit() -> None:
    done = subprocess.run([sys.executable, "-m", "unittest"], capture_output=True, text=True, timeout=300)
    ran = re.search(r"Ran (\d+) tests?", done.stderr)
    if done.returncode != 0 or not ran or int(ran.group(1)) < 1:
        fail("python3 -m unittest must pass and run at least one test:\n" + done.stderr[-800:])


def contract() -> None:
    with tempfile.TemporaryDirectory() as tmp, server(Path(tmp) / "data.db") as base:
        expect(call(base, "POST", "/events", {"id": "show", "capacity": 10}), 201, "create")
        expect(call(base, "POST", "/events", {"id": "show", "capacity": 5}), 409, "duplicate create")
        expect(call(base, "POST", "/events/show/reservations", {"seats": 3}), 201, "reserve 3",
               reserved=3, remaining=7)
        expect(call(base, "POST", "/events/show/reservations", {"seats": 8}), 409, "over capacity")
        expect(call(base, "GET", "/events/show"), 200, "read", id="show", capacity=10, reserved=3, remaining=7)
        expect(call(base, "POST", "/events/none/reservations", {"seats": 1}), 404, "unknown event")
        expect(call(base, "POST", "/events/show/reservations", {"seats": 0}), 400, "zero seats")
        expect(call(base, "POST", "/events/show/reservations", {"seats": "two"}), 400, "non-integer seats")
        expect(call(base, "GET", "/events/show"), 200, "state unchanged by rejected requests", reserved=3)


def restart() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data.db"
        with server(data) as base:
            expect(call(base, "POST", "/events", {"id": "gig", "capacity": 5}), 201, "create")
            expect(call(base, "POST", "/events/gig/reservations", {"seats": 2}), 201, "reserve 2", reserved=2)
        with server(data) as base:
            expect(call(base, "GET", "/events/gig"), 200, "after restart", capacity=5, reserved=2, remaining=3)


def concurrency() -> None:
    with tempfile.TemporaryDirectory() as tmp, server(Path(tmp) / "data.db") as base:
        expect(call(base, "POST", "/events", {"id": "rush", "capacity": 20}), 201, "create")
        with ThreadPoolExecutor(max_workers=25) as pool:
            codes = list(pool.map(lambda _: call(base, "POST", "/events/rush/reservations", {"seats": 1})[0],
                                  range(50)))
        if codes.count(201) != 20 or codes.count(409) != 30:
            fail(f"50 concurrent 1-seat requests on capacity 20: want 20x201 and 30x409, got "
                 f"{ {c: codes.count(c) for c in set(codes)} }")
        expect(call(base, "GET", "/events/rush"), 200, "after the rush", reserved=20, remaining=0)


CHECKS = {"unit": unit, "contract": contract, "restart": restart, "concurrency": concurrency}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        sys.exit("usage: seat_service.py " + "|".join(CHECKS))
    try:
        CHECKS[sys.argv[1]]()
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        fail(f"{type(exc).__name__}: {exc}")
    print("ok")
