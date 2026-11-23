#!/usr/bin/env python3
"""Stop exactly the processes a listing names, each only if it is still the process the listing describes.

    python3 -I stop_named.py LISTING.json

LISTING.json is a list of {"pid", "started", "cwd", "command", "argv_contains"}: a process id, its start time as
`ps -o lstart=` prints it, its working folder, the basename of its executable as `ps -o comm=` prints it (for example
`node` or `Python`; required), and optionally a text its full command line (`ps -ww -o command=`; macOS `ps` prints
each newline of a `python -c` program as the four characters `\\012`, so a text spanning lines must use that) must
contain. An entry without "command" is an error for the whole run: it is
named and the script exits 2 before touching any process. A process is stopped only if, at this moment, its command is
the listed one, its command line contains the listed text (when one is given), and it has no parent (ppid 1), that start
time, that working folder and no children. Anything else is left alone and reported. A stopped process gets SIGTERM, then
SIGKILL if it is still there after 5 seconds. Exit 0: every listed process is gone. Exit 1: at least one was left alone
because it no longer matched. Exit 2: at least one is still alive after SIGKILL, or the listing has an entry without
"command".
"""

import json
import os
import signal
import subprocess
import sys
import time


def ps(pid: int, field: str) -> str:
    return subprocess.run(["ps", "-ww", "-o", f"{field}=", "-p", str(pid)], capture_output=True, text=True, check=False).stdout.strip()


def cwd_of(pid: int) -> str:
    out = subprocess.run(["lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn"], capture_output=True, text=True, check=False).stdout
    return next((line[1:] for line in out.splitlines() if line.startswith("n")), "")


def children_of(pid: int) -> list[str]:
    rows = subprocess.run(["ps", "-axo", "pid=,ppid="], capture_output=True, text=True, check=False).stdout.splitlines()
    return [row.split()[0] for row in rows if len(row.split()) == 2 and row.split()[1] == str(pid)]


def alive(pid: int) -> bool:
    return bool(ps(pid, "pid"))


def mismatch(entry: dict) -> str:
    """Why this process is not the one the listing describes, or '' when it is."""
    pid = entry["pid"]
    if not alive(pid):
        return "no such process now"
    command, parent, started, folder, children = ps(pid, "comm"), ps(pid, "ppid"), ps(pid, "lstart"), cwd_of(pid), children_of(pid)
    if os.path.basename(command) != entry["command"]:
        return f"its command is {command!r}, not {entry['command']!r}"
    if "argv_contains" in entry and entry["argv_contains"] not in ps(pid, "command"):
        return f"its command line does not contain {entry['argv_contains']!r}"
    if parent != "1":
        return f"it has a parent ({parent})"
    if started != entry["started"]:
        return f"it started {started!r}, not {entry['started']!r}"
    if folder != entry["cwd"]:
        return f"its working folder is {folder!r}"
    if children:
        return f"it has children ({', '.join(children)})"
    return ""


def main() -> int:
    with open(sys.argv[1]) as listing_file:
        listing = json.load(listing_file)
    for number, entry in enumerate(listing, 1):
        if "command" not in entry:
            print(f"entry {number} ({json.dumps(entry)}) has no \"command\"; nothing touched")
            return 2
    left_alone = still_alive = 0
    for entry in listing:
        pid = entry["pid"]
        why = mismatch(entry)
        if why:
            left_alone += 1
            print(f"{pid}: LEFT ALONE, {why}")
            continue
        print(f"{pid}: {entry['command']}, no parent, started {entry['started']}, {ps(pid, 'pcpu')}% of a processor, in {entry['cwd']}")
        os.kill(pid, signal.SIGTERM)
        print(f"{pid}: SIGTERM sent")
        deadline = time.monotonic() + 5
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.2)
        if alive(pid):
            os.kill(pid, signal.SIGKILL)
            print(f"{pid}: still there after 5 s, SIGKILL sent")
            time.sleep(2)
        if alive(pid):
            still_alive += 1
            print(f"{pid}: STILL ALIVE")
        else:
            print(f"{pid}: gone")
    print(f"listed {len(listing)}, left alone {left_alone}, still alive {still_alive}")
    return 2 if still_alive else 1 if left_alone else 0


if __name__ == "__main__":
    sys.exit(main())
