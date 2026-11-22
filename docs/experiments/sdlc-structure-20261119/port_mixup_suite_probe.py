#!/usr/bin/env python3
"""Run the ticket fixture's own tests many times, as they are and with the test server on 127.0.0.1, and count the runs that fail.

    python3 port_mixup_suite_probe.py AS_IS_DIR BOUND_DIR PRELOAD_JS OUT_JSON [CONCURRENCY] [ROUNDS] [LIMIT_SECONDS]

AS_IS_DIR is a copy of test/shiploop_e2e/fixtures/node-tickets; BOUND_DIR is a copy with the change under test. Each round runs
`node --test` in CONCURRENCY copies of one folder at once, then in CONCURRENCY copies of the other, never both together: a server
of the changed copy holds a port number on 127.0.0.1, which is the very thing an unchanged copy's server can be handed too. The
order of the two alternates by round.

For every run it keeps the port numbers its servers were given (PRELOAD_JS writes them) and compares them with the numbers that
other programs held on 127.0.0.1 when the round began (read with lsof). A run that does not end within LIMIT_SECONDS is stopped
whole, by its process group, and counted as hung. It writes OUT_JSON and temp folders beside it (removed).
"""

import collections
import concurrent.futures
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HANDED_OUT_FROM = 49152  # net.inet.ip.portrange.first on this machine
ARMS = ("as_is", "bound")

folders = {"as_is": Path(sys.argv[1]).resolve(), "bound": Path(sys.argv[2]).resolve()}
preload = Path(sys.argv[3]).resolve()
out_path = Path(sys.argv[4]).resolve()
concurrency = int(sys.argv[5]) if len(sys.argv) > 5 else 16
rounds = int(sys.argv[6]) if len(sys.argv) > 6 else 100
limit = float(sys.argv[7]) if len(sys.argv) > 7 else 30.0

root = Path(tempfile.mkdtemp(prefix="mixup-probe-", dir=out_path.parent))
copies = {arm: [] for arm in ARMS}
for arm in ARMS:
    for index in range(concurrency):
        target = root / arm / f"c{index}"
        shutil.copytree(folders[arm], target, ignore=shutil.ignore_patterns("node_modules", ".git"))
        copies[arm].append(target)


def held_on_loopback() -> dict[int, str]:
    """Port numbers other programs hold on 127.0.0.1 itself, in the range the system hands out, with the program's name."""
    listing = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True, check=False).stdout
    held = {}
    for row in listing.splitlines()[1:]:
        cells = row.split()
        if len(cells) < 9 or cells[4] != "IPv4" or not cells[8].startswith("127.0.0.1:") or cells[0] == "node":
            continue  # node on 127.0.0.1 could be a server of this probe's changed copies; no other node listener was there
        port = int(cells[8].rsplit(":", 1)[1])
        if port >= HANDED_OUT_FROM:
            held[port] = cells[0]
    return held


def one(arm: str, folder: Path, held: dict[int, str]) -> dict:
    log = folder / "listens.txt"
    log.write_text("")
    output = folder / "output.txt"
    env = {**os.environ, "LISTEN_LOG": str(log), "NODE_OPTIONS": f"--require {preload}"}
    began = time.monotonic()
    with output.open("w") as sink:
        run = subprocess.Popen(["node", "--test"], cwd=folder, stdout=sink, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               start_new_session=True, env=env)
        try:
            code = run.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            os.killpg(run.pid, signal.SIGKILL)  # the runner is this process's child and not yet collected: the group is its own
            run.wait()
            code = None
    seconds = round(time.monotonic() - began, 2)
    text = output.read_text(errors="replace")
    counts = {kind: int(number) for kind, number in re.findall(r"^ℹ (tests|pass|fail) (\d+)$", text, re.M)}
    listens = [line.split() for line in log.read_text().splitlines() if line.strip()]
    ports = [int(cells[2]) for cells in listens]
    drew = sorted({port for port in ports if port in held})
    result = {"arm": arm, "rc": code, "seconds": seconds, "tests": counts.get("tests"), "pass": counts.get("pass"),
              "fail": counts.get("fail"), "listens": len(ports), "addresses": sorted({f"{c[0]} {c[1]}" for c in listens}),
              "drew": drew, "drew_from": sorted({held[port] for port in drew})}
    if code != 0:
        result["failed_tests"] = re.findall(r"^\s*✖ (.+?) \(", text, re.M)[:8]
        result["error_lines"] = [line.strip()[:240] for line in text.splitlines()
                                 if re.search(r"Error:|code:|ECONN|EADDR|hang up|ETIMEDOUT|timed out|!==|actual:|expected:", line)][:16]
    return result


def signature(result: dict) -> str:
    if result["rc"] is None:
        return "did not end"
    blob = " ".join(result.get("error_lines", []))
    if re.search(r"hang up|ECONNRESET", blob):
        return "connection dropped (socket hang up, ECONNRESET)"
    if re.search(r"ECONNREFUSED|EADDRINUSE|ETIMEDOUT|timed out", blob):
        return "refused, in use or timed out"
    if "ERR_ASSERTION" in blob or "!==" in blob:
        return "wrong answer (a failed assertion)"
    return "other"


results = []
snapshots = []
started = time.monotonic()
for number in range(rounds):
    order = ARMS if number % 2 == 0 else ARMS[::-1]
    for arm in order:
        held = held_on_loopback()
        snapshots.append(len(held))
        with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
            for result in pool.map(lambda folder: one(arm, folder, held), copies[arm]):
                result["round"] = number
                results.append(result)

summary = {}
for arm in ARMS:
    mine = [r for r in results if r["arm"] == arm]
    bad = [r for r in mine if r["rc"] != 0]
    summary[arm] = {
        "runs": len(mine),
        "passed": len(mine) - len(bad),
        "failed": len([r for r in bad if r["rc"] is not None]),
        "did_not_end": len([r for r in bad if r["rc"] is None]),
        "servers_started": sum(r["listens"] for r in mine),
        "listening_on": sorted({address for r in mine for address in r["addresses"]}),
        "runs_given_a_number_another_program_held": len([r for r in mine if r["drew"]]),
        "of_those_failed_or_did_not_end": len([r for r in bad if r["drew"]]),
        "failed_or_did_not_end_without_such_a_number": len([r for r in bad if not r["drew"]]),
        "programs_reached": dict(collections.Counter(name for r in mine for name in r["drew_from"])),
        "signatures": dict(collections.Counter(signature(r) for r in bad)),
        "median_seconds": sorted(r["seconds"] for r in mine)[len(mine) // 2] if mine else None,
    }
report = {"concurrency": concurrency, "rounds": rounds, "limit_seconds": limit, "seconds": round(time.monotonic() - started, 1),
          "load_at_end": os.getloadavg()[0], "held_on_loopback_min_max": [min(snapshots), max(snapshots)], "summary": summary,
          "not_passed": [r for r in results if r["rc"] != 0], "given_a_held_number_and_passed": [r for r in results if r["drew"] and r["rc"] == 0]}
out_path.write_text(json.dumps(report, indent=1) + "\n")
shutil.rmtree(root, ignore_errors=True)
print(json.dumps({key: report[key] for key in ("concurrency", "rounds", "seconds", "load_at_end", "held_on_loopback_min_max", "summary")}, indent=1))
