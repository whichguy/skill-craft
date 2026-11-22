#!/usr/bin/env python3
"""List parentless `node` processes whose working folder is one of the E2E harness's base-check folders
(base-tests-*, pristine-*, suite-*). Read-only: stops nothing. Prints one JSON line per process."""
import json, os, re, subprocess

FOLDER = re.compile(r"/(base-tests-|pristine-|suite-)[^/]*")

def out(argv):
    return subprocess.run(argv, capture_output=True, text=True).stdout

def seconds(etime):
    days, _, rest = etime.partition("-") if "-" in etime else ("0", "", etime)
    parts = [int(p) for p in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return int(days) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]

rows = []
for line in out(["ps", "-axo", "pid=,ppid=,etime=,comm="]).splitlines():
    bits = line.split(None, 3)
    if len(bits) < 4:
        continue
    pid, ppid, etime, comm = bits
    if os.path.basename(comm.strip()) != "node":
        continue
    cwd = ""
    for field in out(["lsof", "-a", "-d", "cwd", "-p", pid, "-Fn"]).splitlines():
        if field.startswith("n"):
            cwd = field[1:]
    ports = sorted({field[1:] for field in out(["lsof", "-a", "-iTCP", "-sTCP:LISTEN", "-P", "-n", "-p", pid, "-Fn"]).splitlines()
                    if field.startswith("n")})
    rows.append({"pid": int(pid), "ppid": int(ppid), "age_s": seconds(etime), "etime": etime, "cwd": cwd,
                 "harness_folder": bool(FOLDER.search(cwd)), "ports": ports,
                 "lstart": out(["ps", "-o", "lstart=", "-p", pid]).strip(),
                 "command": out(["ps", "-o", "command=", "-p", pid]).strip()[:160]})
for row in sorted(rows, key=lambda r: -r["age_s"]):
    print(json.dumps(row))
