#!/usr/bin/env python3
"""What one test of the ticket fixture does when another program holds its port number on 127.0.0.1, by what that program does.

    python3 port_mixup_outcomes.py AS_IS_DIR BOUND_DIR [PORT] [LIMIT_SECONDS]

AS_IS_DIR is a copy of test/shiploop_e2e/fixtures/node-tickets; BOUND_DIR is a copy with the change under test (the service
listens on the address its settings name, and the test settings name 127.0.0.1). For each copy and each behaviour of the other
program (port_mixup_stranger.js: drops, json, text, silent) it starts the other program on 127.0.0.1:PORT, writes one test that
uses the fixture's own `withService` on that fixed port, runs `node --test` on it, and prints how the run ended and what it
reported. A run that does not end within LIMIT_SECONDS is stopped whole, by its process group. PORT is below the range the
system hands out, so no test run of anyone's can be given it. The test file it writes is removed afterwards.
"""

import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
folders = {"as it is": Path(sys.argv[1]).resolve(), "bound": Path(sys.argv[2]).resolve()}
port = sys.argv[3] if len(sys.argv) > 3 else "23131"
limit = float(sys.argv[4]) if len(sys.argv) > 4 else 8.0

TEST = f"""'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const {{ withService }} = require('./helpers');
test('lists no tickets on a new service', async () => {{
  await withService({{ port: {port} }}, async (api) => {{
    const res = await api.get('/tickets');
    assert.equal(res.status, 200);
  }});
}});
"""

print(f"One test, the fixture's own helper, on port {port}; another program listens on 127.0.0.1:{port} first. Limit {limit:g} s.")
for arm, folder in folders.items():
    test_file = folder / "test" / "zz-port-mixup.test.js"
    test_file.write_text(TEST)
    try:
        for behaviour in ("drops", "json", "text", "silent"):
            stranger = subprocess.Popen(["node", str(HERE / "port_mixup_stranger.js"), port, behaviour], stdout=subprocess.PIPE, text=True)
            stranger.stdout.readline()
            began = time.monotonic()
            run = subprocess.Popen(["node", "--test", "test/zz-port-mixup.test.js"], cwd=folder, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                out, _ = run.communicate(timeout=limit)
                ended = f"ended in {time.monotonic() - began:.1f} s, exit {run.returncode}"
            except subprocess.TimeoutExpired:
                os.killpg(run.pid, signal.SIGKILL)  # the runner is this process's child and not yet collected
                out, _ = run.communicate()
                ended = f"did not end within {limit:g} s (stopped)"
            stranger.kill()
            stranger.wait()
            marks = sorted(set(re.findall(r"^\s*([✔✖]) (.+?) \(", out, re.M)))
            reported = ", ".join(f"{mark} {name}" for mark, name in marks) or "nothing"
            error = next((line.strip() for line in out.splitlines() if re.search(r"Error: |not valid JSON", line)), "")
            print(f"  {arm:8} | the other program {behaviour:6} | {ended:34} | reported: {reported}{' | ' + error if error else ''}")
    finally:
        test_file.unlink(missing_ok=True)
