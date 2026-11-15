#!/usr/bin/env python3
"""The `ticket-due-times` probe's own servers with a port another process holds: what `checks/due_times_probe.py` does when the
number `serve.free_port()` hands a server is already taken (journal Round 6, the update on the probe).

One run, one probe mode, in a process of its own (the probe keeps its failures in a module global):

    python3 due_times_held_port.py ONE TREE DELIVERY MODE CONDITION [--tag TAG]

TREE is a `test/shiploop_e2e` folder: this checkout's, or an older one cut with `git archive` (its `checks/` and `fixtures/` and
`listeners.py` are all the probe reads); DELIVERY is a delivery of the case (`test/fixtures/quality/reference_due_times.py DEST
--variant reference|base` writes one); MODE is one of the probe's six modes. CONDITION is `none`, the control (nothing is changed),
or `held`: this process keeps one listening socket on every address (a dual-stack IPv6 wildcard, which no later bind of the number
can share), and the FIRST `free_port()` of every `Server` the probe makes hands that number out, the later ones real free ports.
That is what the race looks like from the probe: a number that another process holds is handed out although it is not free.

Everything else is the probe's own: its `main()` runs from DELIVERY, builds its data file, starts `node src/server.js` (and the base,
1.4.0, where the mode needs it) and prints its verdict. Prints one JSON line: the exit code, how many `FAIL:` lines, how many servers
the probe made and how many starts (free ports taken) that took, whether a server "did not start", how many retry lines went to
stderr, the first FAIL line and the seconds.

All the combinations, one JSON line each appended to OUT, the trees and deliveries given by name:

    python3 due_times_held_port.py ALL OUT TREE_NAME=PATH... -- DELIVERY_NAME=PATH...
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

MODES = ("migrate", "restart", "switch", "rollback", "off", "cli")


def one(tree: Path, delivery: Path, mode: str, condition: str, tag: str) -> dict:
    sys.path.insert(0, str(tree / "checks"))
    import due_times_probe as probe  # the tree's own probe, which imports the tree's own serve.py

    held, number = None, None
    if condition == "held":
        held = socket.socket(socket.AF_INET6)
        held.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        held.bind(("::", 0))
        held.listen()
        number = held.getsockname()[1]
    seen = {"servers": 0, "starts": 0, "first": False}
    real_free_port, real_init = probe.serve.free_port, probe.Server.__init__

    def free_port() -> int:
        seen["starts"] += 1
        if seen["first"]:
            seen["first"] = False
            return number
        return real_free_port()

    def init(self, *args, **kwargs) -> None:
        seen["servers"] += 1
        seen["first"] = held is not None
        try:
            real_init(self, *args, **kwargs)
        finally:
            seen["first"] = False

    probe.serve.free_port, probe.Server.__init__ = free_port, init
    os.chdir(delivery)
    out, err = io.StringIO(), io.StringIO()
    began = time.monotonic()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = probe.main([mode])
    fails = [line for line in out.getvalue().splitlines() if line.startswith("FAIL:")]
    return {"tag": tag, "mode": mode, "condition": condition, "exit": code, "fail_lines": len(fails),
            "servers": seen["servers"], "starts": seen["starts"], "did_not_start": "did not start)" in out.getvalue(),
            "retry_lines": err.getvalue().count("starting the"), "first_fail": fails[0][:200] if fails else "",
            "seconds": round(time.monotonic() - began, 1), "platform": sys.platform, "load1": round(os.getloadavg()[0], 1)}


def every(out: Path, trees: dict[str, Path], deliveries: dict[str, Path]) -> None:
    for tree_name, tree in trees.items():
        for delivery_name, delivery in deliveries.items():
            for condition in ("none", "held"):
                for mode in MODES:
                    tag = f"{tree_name}/{delivery_name}"
                    done = subprocess.run([sys.executable, __file__, "ONE", str(tree), str(delivery), mode, condition, "--tag", tag],
                                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
                    line = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""
                    try:
                        json.loads(line)
                    except ValueError:
                        line = json.dumps({"tag": tag, "mode": mode, "condition": condition, "driver_failed": done.returncode,
                                           "stderr": done.stderr[-400:]})
                    with out.open("a") as handle:
                        handle.write(line + "\n")
                    print(line, flush=True)


def named(items: list[str]) -> dict[str, Path]:
    return {name: Path(path).resolve() for name, _, path in (item.partition("=") for item in items)}


if __name__ == "__main__":
    if sys.argv[1] == "ONE":
        print(json.dumps(one(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), sys.argv[4], sys.argv[5],
                             sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "")))
    else:
        divider = sys.argv.index("--")
        every(Path(sys.argv[2]), named(sys.argv[3:divider]), named(sys.argv[divider + 1:]))
