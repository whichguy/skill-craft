#!/usr/bin/env python3
"""Which port numbers does the kernel hand out, by each way this harness asks for one? The pool a collision is drawn from.

    python3 port_pool.py [N]

N times (default 2000): a Python socket bound to 127.0.0.1:0 and closed (checks/serve.py free_port, quality.free_port); a Node
`net.createServer().listen(0)` (what a test server and a candidate that is told PORT=0 do); and a connect() to a local listener, whose source
port is read (what a client of a check gets). Prints, for each, the lowest and highest port, the share of odd numbers, and the share
in the lower half of the range; the range is the kernel's own (/proc/sys/net/ipv4/ip_local_port_range, or macOS's net.inet.ip.portrange).
"""

import json
import socket
import subprocess
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000


def summarize(label: str, ports: list[int], low: int, high: int) -> dict:
    half = low + (high - low + 1) // 2
    return {"way": label, "n": len(ports), "min": min(ports), "max": max(ports), "distinct": len(set(ports)),
            "odd_share": round(sum(p % 2 for p in ports) / len(ports), 3), "lower_half_share": round(sum(p < half for p in ports) / len(ports), 3)}


def kernel_range() -> tuple[int, int]:
    try:
        low, high = map(int, open("/proc/sys/net/ipv4/ip_local_port_range").read().split())
    except OSError:
        low, high = (int(subprocess.run(["sysctl", "-n", f"net.inet.ip.portrange.{k}"], capture_output=True, text=True).stdout)
                     for k in ("first", "last"))
    return low, high


low, high = kernel_range()
bound = []
for _ in range(N):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        bound.append(sock.getsockname()[1])
node = json.loads(subprocess.run(
    ["node", "-e", f"const net=require('net');const out=[];let left={N};(function next(){{const s=net.createServer().listen(0,()=>{{out.push(s.address().port);s.close(()=>{{if(--left)next();else console.log(JSON.stringify(out))}})}})}})()"],
    capture_output=True, text=True, check=True).stdout)
listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen()
sources = []
for _ in range(N):
    client = socket.socket()
    client.connect(listener.getsockname())
    accepted, _ = listener.accept()
    sources.append(client.getsockname()[1])
    client.close()
    accepted.close()
print(json.dumps({"kernel_range": [low, high], "platform": sys.platform}))
for label, ports in (("python bind(0) then close", bound), ("node listen(0)", node), ("connect() source port", sources)):
    print(json.dumps(summarize(label, ports, low, high)))
