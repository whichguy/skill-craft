#!/usr/bin/env python3
"""Stop, by process id, the parentless `node` processes listed in a reviewed file (the output of list_leaked.py)
whose working folder is one of the E2E harness's base-check folders and which are at least an hour old (or the
number of seconds given as a second argument; a check ends within four minutes, so anything over ten is left over).
Each one is checked again just before it is stopped: still `node`, still parentless, same start time, same folder.
SIGTERM first; SIGKILL after 5 seconds for any that remain. Prints one line per process."""
import json, os, signal, subprocess, sys, time

def out(argv):
    return subprocess.run(argv, capture_output=True, text=True).stdout

def now(pid):
    line = out(["ps", "-o", "ppid=,comm=", "-p", str(pid)]).strip()
    if not line:
        return None
    ppid, comm = line.split(None, 1)
    cwd = ""
    for field in out(["lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn"]).splitlines():
        if field.startswith("n"):
            cwd = field[1:]
    return {"ppid": int(ppid), "comm": os.path.basename(comm.strip()), "cwd": cwd,
            "lstart": out(["ps", "-o", "lstart=", "-p", str(pid)]).strip()}

rows = [json.loads(line) for line in open(sys.argv[1])]
oldest = int(sys.argv[2]) if len(sys.argv) > 2 else 3600
chosen = [r for r in rows if r["ppid"] == 1 and r["harness_folder"] and r["age_s"] >= oldest]
sent = []
for row in chosen:
    seen = now(row["pid"])
    if seen is None:
        print(f'{row["pid"]} already gone')
        continue
    if (seen["ppid"], seen["comm"], seen["cwd"], seen["lstart"]) != (1, "node", row["cwd"], row["lstart"]):
        print(f'{row["pid"]} SKIPPED: no longer the listed process ({seen})')
        continue
    os.kill(row["pid"], signal.SIGTERM)
    sent.append(row)
deadline = time.time() + 5
while time.time() < deadline and any(now(r["pid"]) for r in sent):
    time.sleep(0.25)
for row in sent:
    seen = now(row["pid"])
    how = "SIGTERM"
    if seen is not None and seen["lstart"] == row["lstart"]:
        os.kill(row["pid"], signal.SIGKILL)
        how = "SIGKILL after SIGTERM"
    print(f'{row["pid"]} stopped ({how}): started {row["lstart"]}, port {",".join(p.split(":")[-1] for p in row["ports"]) or "-"}, {row["cwd"]}')
print(f"listed {len(chosen)}, signalled {len(sent)}")
