#!/usr/bin/env python3
"""Score the E2E round of the stage-prompt fixes against the same cases' runs on main before them.

Per run, from ``RUN/trace.jsonl``, ``result.json`` and the returned ``work/docs/shiploop/environment.md``:
- ``check_yes_refused``: a complete refused right after a check said yes to the same action (fix 1);
- refusals by the message each fix targets: intake citation (9), expectation ``from`` (11), empty ``red_na`` (3),
  spec mark (4), restate ``unverified`` (6), primary ``lower_layer_check`` (10);
- every refused callback (complete or check), and accepted send-backs;
- ``placeholder_rollback``: the returned environment.md still holds ``<kept paths>`` (7);
- hidden checks (result.json ``pass``) and wall minutes from the trace.
Usage: ``python3 e2e_round.py [--json OUT] RUN_FOLDER ...`` (each a case run folder holding result.json).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

TARGETS = {
    "intake_cite": "summary cites no",
    "from_field": ("expectations cite from", "name W", "open plan assumptions"),
    "empty_red_na": ("red_na is a non-empty list", "retired_tests is a non-empty list"),
    "spec_mark": "without the step's mark",
    "restate": "restates unverified",
    "lower_layer": "lower_layer_check names no test",
}


def matches(error: str, needle) -> bool:
    return any(part in error for part in ((needle,) if isinstance(needle, str) else needle))


def score(folder: Path) -> dict:
    traces = [p for p in glob.glob(str(folder) + "/**/.shiploop-runs/*/run/trace.jsonl", recursive=True)
              if "/slice/" not in p]
    row: dict = {"run": str(folder).replace(os.path.expanduser("~"), "~")}
    result = folder / "result.json"
    if result.is_file():
        data = json.loads(result.read_text())
        row["pass"] = data.get("pass")
        row["checks"] = data.get("checks", {}).get("pass") if isinstance(data.get("checks"), dict) else None
    if not traces:
        return {**row, "error": "no trace"}
    rows = [json.loads(line) for line in Path(traces[0]).read_text().splitlines() if line.strip()]
    stamps = [float(r["ts"]) for r in rows if "ts" in r]
    row["minutes"] = round((max(stamps) - min(stamps)) / 60, 1) if stamps else None
    counts = {key: 0 for key in TARGETS}
    refused = check_yes_refused = sendbacks = 0
    last_yes: set = set()
    for r in rows:
        if r.get("kind") != "command" or r.get("verb") not in ("complete", "check"):
            continue
        if r["verb"] == "check" and not r.get("exit"):
            last_yes.add(r.get("action"))
        if r.get("exit"):
            refused += 1
            error = str(r.get("error") or "")
            for key, needle in TARGETS.items():
                counts[key] += matches(error, needle)
            if r["verb"] == "complete" and not r.get("check_only") and r.get("action") in last_yes:
                check_yes_refused += 1
        for accepted in r.get("accepted") or ():
            sendbacks += accepted.get("outcome") == "send-back"
            last_yes.discard(accepted.get("action"))
    env = next(iter(glob.glob(str(folder) + "/work/docs/shiploop/environment.md")), None)
    text = Path(env).read_text(errors="replace") if env else ""
    return {**row, "refused": refused, "check_yes_refused": check_yes_refused, "send_backs": sendbacks, **counts,
            "placeholder_rollback": ("<kept paths>" in text) if env else None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folders", nargs="+")
    parser.add_argument("--json")
    args = parser.parse_args()
    rows = [score(Path(os.path.expanduser(folder))) for folder in args.folders]
    keys = ["pass", "minutes", "refused", "check_yes_refused", "send_backs", *TARGETS, "placeholder_rollback"]
    print("run".ljust(58) + " ".join(key[:10].rjust(10) for key in keys))
    for row in rows:
        print(row["run"][-58:].ljust(58) + " ".join(str(row.get(key, "")).rjust(10) for key in keys))
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
