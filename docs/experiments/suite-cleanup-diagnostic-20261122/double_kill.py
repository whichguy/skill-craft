#!/usr/bin/env python3
"""Count what the runner's own group-kill does when it is sent twice in a row to a real suite group.

    python3 -B double_kill.py REPO TRIALS [DELAY_SECONDS]

Each trial starts a leader and a child in a new session with the runner's own process class (run_suites._SuiteProcess),
then calls its _signal_group(SIGKILL) twice, DELAY_SECONDS apart, as the end of _terminate_process_group followed by
_abort_process's final KILL does. It records what the exit probe and killpg answered each time, and the warnings the
runner recorded. Then it lets the runner reap the leader (wait), which sends one more group KILL, and records that too.
Nothing in REPO is changed.
"""
import collections
import json
import os
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
repo, trials = sys.argv[1], int(sys.argv[2])
delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
sys.path.insert(0, os.path.join(repo, "test"))
import run_suites

CHILD = ("import signal,sys,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
         "sys.stdout.write('c\\n'); sys.stdout.flush(); time.sleep(120)")
LEADER = f"""
import os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen([sys.executable, '-B', '-c', {CHILD!r}], stdout=subprocess.PIPE)
child.stdout.readline()
os.write(1, b'ready\\n')
time.sleep(120)
"""

real_killpg = os.killpg
events = []


def killpg(group, sig):
    try:
        real_killpg(group, sig)
    except OSError as error:
        events.append(("killpg", type(error).__name__))
        raise
    events.append(("killpg", "ok"))


def group_states(pgid):
    out = subprocess.run(["/bin/ps", "-A", "-o", "pid=,pgid=,stat="], capture_output=True, text=True,
                         check=False).stdout
    return sorted(row.split()[2] for row in out.splitlines() if len(row.split()) == 3 and row.split()[1] == str(pgid))


shapes = collections.Counter()
examples = {}
started = time.monotonic()
for trial in range(trials):
    process = run_suites._SuiteProcess([sys.executable, "-B", "-c", LEADER], stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, start_new_session=True)
    assert process.stdout.readline() == b"ready\n"
    real_probe = process._probe

    def probe(pid, real_probe=real_probe):
        answer = real_probe(pid)
        events.append(("probe", "exited" if answer else "not-exited"))
        return answer

    process._probe = probe
    events.clear()
    os.killpg = killpg
    try:
        process._signal_group(signal.SIGKILL)
        if delay:
            time.sleep(delay)
        mark = len(events)
        process._signal_group(signal.SIGKILL)
        second = tuple(events[mark:])
        after_second = list(process.cleanup_warnings)
        states = group_states(process.pid) if after_second else None
        mark = len(events)
        process.wait(timeout=10)
        reap = tuple(events[mark:])
        after_reap = list(process.cleanup_warnings)[len(after_second):]
    finally:
        os.killpg = real_killpg
        process.stdout.close()
    shape = (" ".join(f"{what}={answer}" for what, answer in second), "WARNING" if after_second else "quiet",
             "reap: " + " ".join(f"{what}={answer}" for what, answer in reap), "WARNING" if after_reap else "quiet")
    shapes[shape] += 1
    examples.setdefault(shape, {"trial": trial, "warnings": after_second + after_reap, "group_states_after_second": states})

print(json.dumps({"trials": trials, "delay_seconds": delay, "seconds": round(time.monotonic() - started, 1),
                  "python": sys.version.split()[0], "load": os.getloadavg()[0]}))
for shape, count in shapes.most_common():
    print(count, "|", " | ".join(shape), "|", json.dumps(examples[shape]))
