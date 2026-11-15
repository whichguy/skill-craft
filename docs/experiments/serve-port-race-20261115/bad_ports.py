#!/usr/bin/env python3
"""Why did the same port numbers fail in every run on macOS? Try each kind of bind on them, and name what holds them (addresses not kept).

    netstat -an | python3 bad_ports.py PROBE_RESULTS.jsonl [more.jsonl ...]

`netstat -an` is piped in because a Python subprocess of this machine's sandboxed shell gets no TCP rows from it (the pipeline of the shell does).

Reads the ports of the early exits from serve_race_probe.py's JSON lines, and for each prints whether a TCP bind of the kind free_port() makes
(IPv4 loopback) and of the kinds a candidate makes (IPv6 wildcard, dual-stack with SO_REUSEADDR, as Node's listen(PORT) does; the IPv6 wildcard
alone) succeeds now, and every TCP socket in any state that has the port as its local port, from `netstat -an` on stdin, with its addresses reduced to a
class (wildcard, loopback, an address) and the remote port kept.
"""

import json
import socket
import sys

ports = []
for path in sys.argv[1:]:
    for line in open(path):
        ports += [e["port"] for e in json.loads(line).get("early_exits", []) if e.get("port")]
ports = sorted(set(ports))


def bind(family: int, host: str, port: int, reuse: bool = False, v6only: int | None = None) -> str:
    with socket.socket(family) as sock:
        try:
            if reuse:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if v6only is not None:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, v6only)
            sock.bind((host, port))
            return "ok"
        except OSError as why:
            return "EADDRINUSE" if why.errno in (48, 98) else f"error {why.errno}"


def kind(endpoint: str) -> str:
    host = endpoint.rsplit(".", 1)[0]
    return "wildcard" if host == "*" else "loopback" if host in ("127.0.0.1", "::1") else "an address"


table = sys.stdin.read().splitlines()
print(f"{len(ports)} ports; a bind of each kind, and the TCP sockets that have the port as their local port, now")
print(f"{'port':>6} {'IPv4 127.0.0.1':>15} {'IPv6 :: dual-stack':>19} {'IPv6 :: only':>13}   held by")
for port in ports:
    holders = []
    for row in table:
        fields = row.split()
        if len(fields) >= 6 and fields[0].startswith("tcp") and fields[3].rsplit(".", 1)[-1] == str(port):
            holders.append(f"{fields[0]} local {kind(fields[3])} -> remote {kind(fields[4])}:{fields[4].rsplit('.', 1)[-1]} {fields[5]}")
    print(f"{port:>6} {bind(socket.AF_INET, '127.0.0.1', port):>15} {bind(socket.AF_INET6, '::', port, True, 0):>19} "
          f"{bind(socket.AF_INET6, '::', port, False, 1):>13}   {'; '.join(holders) or 'nothing now'}")
