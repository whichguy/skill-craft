#!/usr/bin/env python3
"""How often does serve.py's candidate exit before it listens, with neighbours binding ports around it? The rate half of the study.

    python3 serve_race_probe.py DELIVERY_DIR CALLS WORKERS TAG [--serve SERVE_PY] [--churn KIND[:ARG]]...

Runs the suite's own serve.py (imported, not copied: `main()` of test/shiploop_e2e/checks/serve.py, so `free_port()`, the
Popen of `node src/server.js` with PORT set, and `wait_for_candidate()` with its lsof ownership check are the real ones) CALLS times
from WORKERS threads, with `-- true` as the check, against DELIVERY_DIR (a built `ticket-comments` reference delivery). Two things are
changed only inside this probe: `serve.fail` raises instead of printing and exiting, and `serve.tail` returns the whole whitespace-
collapsed stderr instead of its last 600 characters, so every early exit is classified from the candidate's own text.

--churn starts neighbours for the length of the run (each in a process group of its own, ended afterwards):
  node-listen:RATE[:HOLD_MS]  a Node process that opens `net.createServer().listen(0)` RATE times a second and closes each after HOLD_MS (20)
  py-bind:RATE[:HOLD_MS]      a Python process that binds an unconnected socket to 127.0.0.1:0, as free_port() does, RATE times a second
  node-test:N                 N loops of the fixture's own `node --test` (the base of the ticket cases, 128 tests, each with a server)
                              in copies of --fixture (default: test/shiploop_e2e/fixtures/node-tickets of this checkout)

Prints one JSON line: how many calls passed (and how many of those only after serve.py chose the port again, once serve.py has its retry),
exited early (and with what error code), found a foreign listener, or timed out; each early
exit's port, its error code and the window (seconds from the port being released to the first time serve.py saw the candidate listen, an
upper bound on the time another socket had to take the port); the window's quantiles over the calls that passed; the load average.
"""

import argparse
import collections
import concurrent.futures
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time

NEIGHBOUR_NODE = """
const net = require('net');
const [rate, hold] = [Number(process.argv[2]), Number(process.argv[3])];
setInterval(() => {
  const burst = Math.max(1, Math.round(rate / 100));          // a tick every 10 ms
  for (let i = 0; i < burst; i += 1) {
    const s = net.createServer().on('error', () => {}).listen(0);
    s.on('listening', () => setTimeout(() => s.close(), hold));
  }
}, 10);
"""
NEIGHBOUR_PY = """
import collections, socket, sys, time
rate, hold = float(sys.argv[1]), float(sys.argv[2]) / 1000
live = collections.deque()
per_tick = max(1, round(rate / 100))                          # a tick every 10 ms
while True:
    now = time.monotonic()
    for _ in range(per_tick):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        live.append((now + hold, sock))
    while live and live[0][0] <= now:
        live.popleft()[1].close()
    time.sleep(0.01)
"""
NEIGHBOUR_TEST = """
import shutil, subprocess, sys, tempfile
from pathlib import Path
fixture, copies = Path(sys.argv[1]), int(sys.argv[2])
root = Path(tempfile.mkdtemp(prefix="node-test-churn-"))
import concurrent.futures
def loop(i):
    target = root / f"c{i}"
    shutil.copytree(fixture, target, ignore=shutil.ignore_patterns("node_modules", ".git"))
    while True:
        subprocess.run(["node", "--test"], cwd=target, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
with concurrent.futures.ThreadPoolExecutor(copies) as pool:
    list(pool.map(loop, range(copies)))
"""


class Failed(Exception):
    pass


def start_neighbour(spec: str, fixture: Path) -> subprocess.Popen:
    kind, *args = spec.split(":")
    if kind == "node-listen":
        argv = ["node", "-e", NEIGHBOUR_NODE, args[0], args[1] if len(args) > 1 else "20"]
    elif kind == "py-bind":
        argv = [sys.executable, "-c", NEIGHBOUR_PY, args[0], args[1] if len(args) > 1 else "20"]
    elif kind == "node-test":
        argv = [sys.executable, "-c", NEIGHBOUR_TEST, str(fixture), args[0]]
    else:
        raise SystemExit(f"unknown churn kind {kind}")
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("delivery")
    parser.add_argument("calls", type=int)
    parser.add_argument("workers", type=int)
    parser.add_argument("tag")
    parser.add_argument("--serve", default=str(Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e" / "checks" / "serve.py"))
    parser.add_argument("--fixture", default=str(Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e" / "fixtures" / "node-tickets"))
    parser.add_argument("--churn", action="append", default=[])
    args = parser.parse_args()

    sys.path.insert(0, str(Path(args.serve).resolve().parent))
    import serve  # the suite's own helper

    live, started = {}, threading.Lock()  # the candidates this probe has started and not yet reaped, by pid

    class TrackedPopen(subprocess.Popen):
        """serve.py's Popen, with the pids of the candidates that are alive kept: whether a foreign listener is another of them."""
        def __init__(self, *popen_args, **popen_kwargs):
            super().__init__(*popen_args, **popen_kwargs)
            with started:
                live[self.pid] = time.monotonic()

        def wait(self, *wait_args, **wait_kwargs):
            try:
                return super().wait(*wait_args, **wait_kwargs)
            finally:
                with started:
                    live.pop(self.pid, None)

    class Tracking:
        def __getattr__(self, name):
            return getattr(subprocess, name)
        Popen = TrackedPopen

    serve.subprocess = Tracking()
    seen_at_failure = threading.local()

    def holders_of(port: int) -> list[dict]:
        """Whoever holds `port` in any TCP state when serve.py gives up (lsof, read-only): pid, command and socket name."""
        try:
            text = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-Fpcn"], capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.TimeoutExpired):
            return [{"unobserved": True}]
        found = []
        for line in text.splitlines():
            if line.startswith("p"):
                found.append({"pid": int(line[1:]), "command": "", "names": []})
            elif found and line.startswith("c"):
                found[-1]["command"] = line[1:]
            elif found and line.startswith("n"):
                found[-1]["names"].append(line[1:])
        return found

    def sockets_on(port: int) -> list[str]:
        """Every TCP socket in any state whose local port is `port` (TIME_WAIT included, which lsof does not show): netstat on macOS,
        /proc/net/tcp and tcp6 on Linux."""
        found = []
        try:
            if sys.platform == "darwin":  # no -p: `-p tcp` leaves the IPv6 sockets out. Addresses are reduced to a class, not kept.
                text = subprocess.run(["netstat", "-an"], capture_output=True, text=True, timeout=10).stdout

                def kind(endpoint: str) -> str:
                    host = endpoint.rsplit(".", 1)[0]
                    return "wildcard" if host == "*" else "loopback" if host in ("127.0.0.1", "::1") else "an address"
                if not any(line.startswith("tcp") for line in text.splitlines()):
                    return ["unobserved: netstat gave this process no TCP rows (in the sandboxed shell it did not; see bad_ports.py)"]
                for line in text.splitlines():
                    fields = line.split()
                    if len(fields) >= 6 and fields[0].startswith("tcp") and fields[3].rsplit(".", 1)[-1] == str(port):
                        found.append(f"{fields[0]} local {kind(fields[3])} -> remote {kind(fields[4])}:{fields[4].rsplit('.', 1)[-1]} {fields[5]}")
            else:
                states = {"01": "ESTABLISHED", "02": "SYN_SENT", "03": "SYN_RECV", "04": "FIN_WAIT1", "05": "FIN_WAIT2", "06": "TIME_WAIT",
                          "07": "CLOSE", "08": "CLOSE_WAIT", "09": "LAST_ACK", "0A": "LISTEN", "0B": "CLOSING"}
                for table in ("/proc/net/tcp", "/proc/net/tcp6"):
                    for line in open(table).read().splitlines()[1:]:
                        fields = line.split()
                        if int(fields[1].rsplit(":", 1)[1], 16) == port:
                            found.append(f"{Path(table).name} {fields[1]} -> {fields[2]} {states.get(fields[3], fields[3])}")
        except (OSError, subprocess.TimeoutExpired):
            return ["unobserved"]
        return found[:6]

    def fail(reason: str) -> None:
        early = re.search(r"exited \(rc \d+\) before it listened on PORT=(\d+)", reason)
        seen_at_failure.holders = {"lsof": holders_of(int(early.group(1))), "sockets": sockets_on(int(early.group(1)))} if early else None
        pids = re.search(r"answered by pid ([0-9, ]+), not by the candidate", reason)
        if pids:  # taken at the moment serve.py gives up, before the other candidate's own worker ends it
            with started:
                seen_at_failure.alive = {int(pid): int(pid) in live for pid in pids.group(1).replace(" ", "").split(",") if pid}
        raise Failed(reason)

    serve.fail = fail
    serve.tail = lambda path: " ".join(path.read_text(errors="replace").split()) or "(no stderr)"
    stamps = threading.local()
    real_free_port = serve.free_port

    def free_port() -> int:
        port = real_free_port()
        stamps.released = time.monotonic()
        stamps.calls = getattr(stamps, "calls", 0) + 1  # a second call inside one main() is a retry
        return port

    # serve.py before its retry waits through wait_for_candidate; with the retry, main() waits through candidate_problem.
    waiting = "candidate_problem" if hasattr(serve, "candidate_problem") else "wait_for_candidate"
    real_wait = getattr(serve, waiting)

    def wait_for_candidate(proc, port, stderr):
        try:
            return real_wait(proc, port, stderr)
        finally:
            stamps.seen = time.monotonic()

    serve.free_port = free_port
    setattr(serve, waiting, wait_for_candidate)
    os.chdir(args.delivery)
    for variable in ("E2E_SERVE_PORT", "PORT"):
        os.environ.pop(variable, None)

    neighbours = [start_neighbour(spec, Path(args.fixture)) for spec in args.churn]
    time.sleep(3 if neighbours else 0)  # let the neighbours reach their steady state
    results, lock = [], threading.Lock()
    remaining = [args.calls]

    def worker() -> None:
        while True:
            with lock:
                if remaining[0] <= 0:
                    return
                remaining[0] -= 1
            stamps.released = stamps.seen = None
            stamps.calls = 0
            row = {"outcome": None}
            try:
                code = serve.main(["--start", "node src/server.js", "--", "true"])
                row["outcome"] = ("passed" if stamps.calls == 1 else "passed after retry") if code == 0 else f"check exited {code}"
            except Failed as why:
                text = str(why)
                found = re.search(r"PORT=(\d+)", text) or re.search(r"port (\d+)", text)
                row["port"] = int(found.group(1)) if found else None
                if "exited (rc 0)" in text and "listening on" in text:
                    row["outcome"] = "stopped from outside"  # the server logged that it listens and exited 0: a SIGTERM the probe did not send
                elif "exited (rc" in text:
                    row["outcome"] = "early exit"
                    named = re.search(r"code: '([A-Z_]+)'", text) or re.search(r"\b(E[A-Z]{3,})\b", text)
                    row["code"] = named.group(1) if named else None
                    row["error_line"] = text[text.find("Error"):][:120] if "Error" in text else text[:160]
                    row["holders_when_serve_py_gave_up"] = getattr(seen_at_failure, "holders", None) or {}
                elif "answered by pid" in text:
                    row["outcome"] = "foreign listener"
                    alive = getattr(seen_at_failure, "alive", {})
                    row["foreign_pids"] = sorted(alive)
                    row["foreign_is_a_live_candidate_of_this_probe"] = bool(alive) and all(alive.values())
                elif "did not listen" in text:
                    row["outcome"] = "timeout"
                else:
                    row["outcome"] = "other: " + text[:160]
            if stamps.released and stamps.seen:
                row["window"] = round(stamps.seen - stamps.released, 3)
            with lock:
                results.append(row)

    began = time.monotonic()
    try:
        with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
            for future in [pool.submit(worker) for _ in range(args.workers)]:
                future.result()
    finally:
        for proc in neighbours:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    outcomes = collections.Counter(row["outcome"] for row in results)
    windows = sorted(row["window"] for row in results if "window" in row and row["outcome"] == "passed")
    quantile = (lambda q: windows[min(len(windows) - 1, int(q * len(windows)))]) if windows else (lambda q: None)
    early = [row for row in results if row["outcome"] == "early exit"]
    foreign = [row for row in results if row["outcome"] == "foreign listener"]
    print(json.dumps({"tag": args.tag, "churn": args.churn, "calls": len(results), "workers": args.workers, "outcomes": dict(outcomes),
                      "early_exit_codes": dict(collections.Counter(row.get("code") for row in early)),
                      "window_s": {"median": quantile(0.5), "p95": quantile(0.95), "max": windows[-1] if windows else None},
                      "early_exits": early[:20], "foreign_listeners": foreign[:20], "seconds": round(time.monotonic() - began, 1), "load1_at_end": os.getloadavg()[0],
                      "platform": sys.platform}), flush=True)


if __name__ == "__main__":
    main()
