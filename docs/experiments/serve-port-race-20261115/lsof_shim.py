#!/usr/bin/env python3
"""A stand-in for the one lsof call serve.py makes, for a Linux box that has no lsof (the container the probes ran in).

    lsof -nP -a -iTCP:PORT -sTCP:LISTEN -Fp        (checks/listeners.py listening_pids)

prints `p<pid>` for every process holding a TCP socket in LISTEN state on PORT, read from /proc/net/tcp, /proc/net/tcp6 and the
sockets under /proc/<pid>/fd. Anything else it is asked for exits 2. Not used on the machines that have lsof.
"""

import os
import re
import sys

args = sys.argv[1:]
match = next((re.fullmatch(r"-iTCP:(\d+)", a) for a in args if a.startswith("-iTCP:")), None)
if not match or "-sTCP:LISTEN" not in args or "-Fp" not in args:
    sys.exit(2)
port = int(match.group(1))
inodes = set()
for table in ("/proc/net/tcp", "/proc/net/tcp6"):
    try:
        lines = open(table).read().splitlines()[1:]
    except OSError:
        continue
    for line in lines:
        fields = line.split()
        if fields[3] == "0A" and int(fields[1].rsplit(":", 1)[1], 16) == port:
            inodes.add(fields[9])
pids = set()
for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        for fd in os.listdir(f"/proc/{pid}/fd"):
            try:
                target = os.readlink(f"/proc/{pid}/fd/{fd}")
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                pids.add(int(pid))
    except OSError:
        continue
for pid in sorted(pids):
    print(f"p{pid}")
sys.exit(0 if pids else 1)
