#!/usr/bin/env python3
"""Run ONE pass of chain B on the Codex host from the published marketplace, retrying while another session holds the port lease.

    python3 chain_b_driver.py PASS ROOT

PASS is B1, B2, B3 or B4 (user-listing, user-roles, user-team-listing, user-page-size); ROOT is the folder the four run folders go under. Pass 1 is a fresh run on
fixtures/node-base; each later pass continues from the folder the pass before it left (``--continue-from``), so the driver refuses to start a pass whose
predecessor has no result.json. One pass per invocation on purpose: Round 5 reads the next link against the real prior (chain_b_gate.py) before it runs,
and a FAILED pass is triaged by a person before the chain goes on (a base test of a delivery can lose a port to another project's server, journal F17).

The harness takes a machine-wide lease on every port the case declares, for the whole run: chain B's cases declare 3000 (node-base's default), not the ticket
service's 4180, so they wait for another session's node-base runs and not for its ticket runs. A refusal ("is leased by the harness of ...") starts no host
and leaves no run folder; the driver tries again every 45 seconds, without limit (the owner's rule: no turn, spend, time or retry limit by default), and logs
each try. Any other early end without a result is left alone: the driver stops and says so.

Writes ROOT/driver-log.txt (appended) and ROOT/<name>.log (the harness's output). Defaults of the harness are the subject: Codex gpt-6.1-terra at xhigh, hooks on,
``--source marketplace``, the baseline row appended to the checkout's test/shiploop_e2e/baselines.jsonl.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PASSES = {"B1": "user-listing", "B2": "user-roles", "B3": "user-team-listing", "B4": "user-page-size"}
ORDER = list(PASSES)
RETRY_SECONDS = 45


def log(root: Path, text: str) -> None:
    line = f"{datetime.now().strftime('%H:%M:%S')} {text}"
    print(line, flush=True)
    with (root / "driver-log.txt").open("a") as handle:
        handle.write(line + "\n")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in PASSES:
        print(__doc__)
        return 2
    key, root = argv[0], Path(argv[1]).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    case = PASSES[key]
    name = f"{key}-{case}"
    out = root / name
    command = [sys.executable, "test/shiploop_e2e/run.py", "--case", case, "--host", "codex", "--source", "marketplace", "--output", str(out)]
    if key != "B1":
        previous = root / f"{ORDER[ORDER.index(key) - 1]}-{PASSES[ORDER[ORDER.index(key) - 1]]}"
        if not (previous / "result.json").is_file():
            log(root, f"REFUSED {name}: the pass before it ({previous.name}) has no result.json")
            return 2
        command += ["--continue-from", str(previous)]
    if (out / "result.json").is_file():
        log(root, f"{name} already has a result; nothing to do")
        return 0
    tries = 0
    while True:
        tries += 1
        log(root, f"START {name} (case {case}, try {tries}): {' '.join(command[1:])}")
        with (root / f"{name}.log").open("a") as handle:
            done = subprocess.run(command, cwd=REPO, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT)
        text = (root / f"{name}.log").read_text(errors="replace")[-4000:]
        if (out / "result.json").is_file():
            log(root, f"END {name}: exit {done.returncode}, result.json written")
            return 0
        if "is leased by the harness" in text:
            holder = next((line.strip() for line in text.splitlines() if "is leased by the harness" in line), "")
            log(root, f"{name} try {tries}: {holder[:200]}")
            time.sleep(RETRY_SECONDS)
            continue
        log(root, f"STOP {name}: exit {done.returncode} with no result.json and no lease refusal; see {name}.log")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
