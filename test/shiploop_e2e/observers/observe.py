#!/usr/bin/env python3
"""Run a case's observers on a delivered tree and write their records together. Opt-in: no run calls this.

An observer records something the case's checks do not look at. It changes no check, no verdict and no baseline, and
lives outside the files a run's `boundary` digests cover (the harness's top-level code, `checks/`, `fixtures/` and the
case entry), so adding or changing one leaves earlier results comparable. Each prints one JSON object of schema
`shiploop-e2e-observation/v1` with its own `version`; raise it when what an observer records changes.

Usage: python3 observe.py CASE DELIVERED_TREE [--out FILE]
       CASE is `ticket-due-times` or `shared-expenses`. Prints, and writes to FILE when given, one JSON object:
       {"schema": "shiploop-e2e-observations/v1", "case", "tree", "observations": [...]}.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OBSERVERS = {"ticket-due-times": ("ticket_return.py", "suite_elsewhere.py"),
             "shared-expenses": ("expense_inputs.py", "suite_elsewhere.py")}


def main(argv: list[str]) -> int:
    out_file = None
    if "--out" in argv:
        at = argv.index("--out")
        out_file, argv = argv[at + 1], argv[:at] + argv[at + 2:]
    if len(argv) != 2 or argv[0] not in OBSERVERS or not Path(argv[1]).is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    case, tree = argv[0], str(Path(argv[1]).resolve())
    records = []
    for script in OBSERVERS[case]:
        done = subprocess.run([sys.executable, str(HERE / script), tree], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)
        try:
            records.append(json.loads(done.stdout.strip().splitlines()[-1]))
        except (ValueError, IndexError):
            records.append({"schema": "shiploop-e2e-observation/v1", "observer": script,
                            "summary": "not measured: the observer printed no record",
                            "exit": done.returncode, "stderr": done.stderr[-300:]})
    result = {"schema": "shiploop-e2e-observations/v1", "case": case, "tree": tree, "observations": records}
    text = json.dumps(result, indent=1)
    if out_file:
        Path(out_file).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
