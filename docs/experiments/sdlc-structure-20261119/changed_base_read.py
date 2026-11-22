#!/usr/bin/env python3
"""Read the confirmation runs for the changed ticket base: per run, the base it started from, the grading digests, every
verdict and case check (a check that did not end is marked), and where the servers of the delivered suite listen.

    python3 -I changed_base_read.py SCRATCH NAME=RUN_FOLDER ...

For the last part it takes the delivered tree at the committed head out of the run's bundle into SCRATCH, runs its
`node --test` once with a preload that writes one line for every server that starts listening (family, address and the
script of the process that started it), under a 120-second limit in a process group of its own, and counts the lines by
address. It reads run folders and writes only under SCRATCH.
"""

import collections
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile

LIMIT = 120
VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
RECORDER = """'use strict';
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const listen = net.Server.prototype.listen;
net.Server.prototype.listen = function recorded(...args) {
  this.once('listening', () => {
    const address = this.address();
    if (address && typeof address === 'object') {
      const script = path.basename(process.argv[process.argv.length - 1] || '');
      fs.appendFileSync(process.env.LISTEN_LOG, `${address.family} ${address.address} ${script}\\n`);
    }
  });
  return listen.apply(this, args);
};
"""


def delivered_tree(folder: Path, head: str, scratch: Path) -> Path:
    clone = Path(tempfile.mkdtemp(prefix="clone-", dir=scratch))
    tree = Path(tempfile.mkdtemp(prefix="tree-", dir=scratch))
    subprocess.run(["git", "clone", "-q", str(folder / "delivery" / "work.bundle"), str(clone)], check=True)
    tar = subprocess.run(["git", "-C", str(clone), "archive", head], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(tree)], input=tar, check=True)
    return tree


def suite_addresses(tree: Path, scratch: Path) -> dict:
    """One run of the delivered suite: how it ended, its counts, and its servers by address and by starting script."""
    recorder = scratch / "record_listens.js"
    recorder.write_text(RECORDER)
    log = Path(tempfile.mkstemp(prefix="listens-", suffix=".txt", dir=scratch)[1])
    out = Path(tempfile.mkstemp(prefix="suite-output-", suffix=".txt", dir=scratch)[1])
    env = {**os.environ, "LISTEN_LOG": str(log), "NODE_OPTIONS": f'--require "{recorder}"'}
    with out.open("w") as sink:
        run = subprocess.Popen(["node", "--test"], cwd=tree, stdout=sink, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               start_new_session=True, env=env)
        try:
            code = run.wait(timeout=LIMIT)
        except subprocess.TimeoutExpired:
            os.killpg(run.pid, signal.SIGKILL)  # the runner is this process's child and not yet collected
            run.wait()
            code = None
    text = out.read_text(errors="replace")
    counts = {kind: int(number) for kind, number in re.findall(r"^ℹ (tests|pass|fail|skipped) (\d+)$", text, re.M)}
    rows = [line.split(" ", 2) for line in log.read_text().splitlines() if line.strip()]
    by_address = collections.Counter(f"{family} {address}" for family, address, _ in rows)
    elsewhere = collections.Counter(script for family, address, script in rows if address != "127.0.0.1")
    return {"ended": "did not end" if code is None else f"exit {code}", "counts": counts, "by_address": dict(by_address),
            "not_on_loopback_by_script": dict(elsewhere)}


def main(argv: list[str]) -> None:
    scratch = Path(argv[0]).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    for pair in argv[1:]:
        name, _, raw = pair.partition("=")
        folder = Path(raw)
        result = json.loads((folder / "result.json").read_text())
        span = result.get("span") or {}
        seconds = span["ended"] - span["started"] if span.get("started") and span.get("ended") else None
        cost = (result.get("metrics") or {}).get("cost_usd")
        verdicts = {key: (result.get(key) or {}).get("pass") if isinstance(result.get(key), dict) else result.get(key) for key in VERDICTS}
        checks = result.get("checks") or []
        print(f"== {name}")
        print(f"   case {result.get('case')} | {result.get('host')} {result.get('model')} {result.get('effort')} | pass {result.get('pass')} | "
              f"minutes {round(seconds / 60, 1) if seconds else None} | cost {cost}")
        print(f"   base {json.dumps(result.get('base'))}")
        print(f"   graded under {json.dumps(result.get('boundary'))}")
        print(f"   verdicts {verdicts}")
        print(f"   case checks: {sum(1 for check in checks if check.get('pass'))} of {len(checks)} pass")
        for check in checks:
            output = " ".join((check.get("output") or "").split())
            short = re.sub(r'python3 "\$E2E_CHECKS/', "", check.get("command", ""))[:60].replace('"', "")
            flag = "  <-- DID NOT END" if re.search(r"did not end|timeout", output) or check.get("returncode") is None else ""
            print(f"      {'pass' if check.get('pass') else 'FAIL'} | {short:44} | {output[:150]}{flag}")
        head = (result.get("committed") or {}).get("head")
        if head and (folder / "delivery" / "work.bundle").is_file():
            tree = delivered_tree(folder, head, scratch)
            seen = suite_addresses(tree, scratch)
            print(f"   the delivered suite at {head[:12]}, run once: {seen['ended']}, {seen['counts']}")
            print(f"   its servers by address: {seen['by_address']}")
            print(f"   servers not on 127.0.0.1, by the script that started them: {seen['not_on_loopback_by_script'] or 'none'}")
        else:
            print("   no committed head or no bundle: the delivered suite was not run")


main(sys.argv[1:])
