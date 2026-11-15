#!/usr/bin/env python3
"""What a candidate does when the port serve.py hands it is already taken, by what kind of socket: the deterministic half of the study.

    python3 pinned_port_demo.py DELIVERY_DIR [SERVE_PY]

DELIVERY_DIR is a built delivery of the ticket-comments case (`reference_ticket_comments.build(dir, "reference")`); SERVE_PY defaults to
test/shiploop_e2e/checks/serve.py of the checkout this file sits in. For each kind of holder a separate process takes a port, then the
real serve.py is run with that port pinned (E2E_SERVE_PORT, the variable its own regression uses to put a sibling on the port first)
and `--start "node src/server.js" -- true` (the case's own start command and a check that does nothing), and the candidate is run once more by itself on the same port with its whole stderr kept. Prints one JSON
line per holder: serve.py's exit code and what it printed, the candidate's exit code, the error line and `code:` its stderr names, and the
length of its whitespace-collapsed stderr (serve.py keeps the last 600 characters of that, and the calibration test prints the first 300
of the check's output).
"""

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

DELIVERY = Path(sys.argv[1]).resolve()
SERVE = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e" / "checks" / "serve.py"

PY_HOLDER = r'''
import socket, sys, time
kind = sys.argv[1]
if kind == "py-client-source-port":
    server = socket.socket(); server.bind(("127.0.0.1", 0)); server.listen()
    client = socket.socket(); client.connect(server.getsockname()); conn, _ = server.accept()
    print("PORT", client.getsockname()[1], flush=True)
else:
    family = socket.AF_INET6 if kind in ("py-v6-loopback", "py-v6-any-v6only") else socket.AF_INET
    sock = socket.socket(family)
    if kind == "py-v6-any-v6only":
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    host = {"py-v4-loopback": "127.0.0.1", "py-v4-any": "0.0.0.0", "py-v6-loopback": "::1", "py-v6-any-v6only": "::",
            "py-v4-bound-only": "127.0.0.1"}[kind]
    sock.bind((host, 0))
    if kind != "py-v4-bound-only":
        sock.listen()
    print("PORT", sock.getsockname()[1], flush=True)
time.sleep(600)
'''
NODE_HOLDER = "const s=require('net').createServer().listen(0,()=>{console.log('PORT',s.address().port)});setTimeout(()=>{},600000)"

HOLDERS = {
    "node-wildcard": ["node", "-e", NODE_HOLDER],
    **{kind: [sys.executable, "-c", PY_HOLDER, kind] for kind in (
        "py-v4-loopback", "py-v4-any", "py-v6-loopback", "py-v6-any-v6only", "py-v4-bound-only", "py-client-source-port")},
}


def collapse(text: str) -> str:
    return " ".join(text.split())


def one(kind: str) -> dict:
    holder = subprocess.Popen(HOLDERS[kind], stdout=subprocess.PIPE, text=True, start_new_session=True)
    try:
        line = holder.stdout.readline()
        port = int(line.split()[1])
        env = dict(os.environ, E2E_SERVE_PORT=str(port))
        began = time.monotonic()
        done = subprocess.run([sys.executable, str(SERVE), "--start", "node src/server.js", "--", "true"], cwd=DELIVERY, env=env,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        serve_seconds = round(time.monotonic() - began, 2)
        alone = subprocess.Popen(["node", "src/server.js"], cwd=DELIVERY, env=dict(os.environ, PORT=str(port)), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            out, err = alone.communicate(timeout=3)
            alone_rc = alone.returncode
        except subprocess.TimeoutExpired:
            os.killpg(alone.pid, signal.SIGKILL)
            out, err = alone.communicate()
            alone_rc = "still running after 3 s (it listened)"
        first = next((ln for ln in err.splitlines() if "listen" in ln.lower() or "Error" in ln), "")
        code = re.search(r"code: '([A-Z_]+)'", err)
        return {"holder": kind, "port": port, "serve_rc": done.returncode, "serve_seconds": serve_seconds,
                "serve_said": collapse(done.stdout)[:420], "candidate_rc": alone_rc, "candidate_error_line": first.strip()[:140],
                "candidate_code": code.group(1) if code else None, "candidate_stderr_collapsed_chars": len(collapse(err))}
    finally:
        os.killpg(holder.pid, signal.SIGKILL)
        holder.wait()


if __name__ == "__main__":
    for kind in HOLDERS:
        print(json.dumps(one(kind)), flush=True)
