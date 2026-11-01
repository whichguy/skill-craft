#!/usr/bin/env python3
"""The release round's scorer (README.md, "Release round, as it runs"): per delivery under RUNS, the harness verdict, the hidden
checks, and every send-back with its stage, summary and class.

    python3 -I score_release.py ~/e2e-runs-sp/20261101/round2-release --out release_scores.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
LATER = re.compile(r"forbid|prohibit|may not write|cannot write|unwritten|not yet written|later stage|test stage|written later|"
                   r"writes (?:that file|them) later|until test|zero (?:tests|cases)|has no tests|0 cases", re.I)


def klass(stage: str, text: str) -> str:
    """The send-back's class, read as corpus/sendback_classes_127plus.jsonl was."""
    low = text.lower()
    if stage == "test-spec" and re.search(r"behavio(?:u)?r(?:al|-based)? red|loadable seam|missing executable|missing file as failure", low):
        return "red-empty-base"
    if LATER.search(text) and re.search(r"\bC\d+\b[^.;]{0,60}?\b(?:say|says|still|requires?|demands?|needs?)\b", text):
        return "f31-confirm-by"
    if LATER.search(text) and re.search(r"\bproof\b", low):
        return "proof-needs-unwritten-test"
    if re.search(r"focused (?:command|test).{0,40}\bids?\b|test case ids|named cases", low):
        return "focused-id-short"
    return "other"


def score(folder: Path) -> dict:
    row = {"run": folder.name, "finished": (folder / "result.json").is_file()}
    if not row["finished"]:
        return row
    result = json.loads((folder / "result.json").read_text())
    row["verdict"] = result.get("pass", result.get("verdict"))
    checks = result.get("checks") or result.get("case_checks") or []
    row["checks"] = [{"command": str(c.get("command"))[-60:], "exit": c.get("exit", c.get("returncode"))} for c in checks
                     if isinstance(c, dict)]
    row["checks_passed"] = sum(1 for c in row["checks"] if c["exit"] == 0)
    run = next(iter(folder.glob(".shiploop-runs/work-*/run")), None)
    sendbacks = []
    if run is not None and (run / "trace.jsonl").is_file():
        for line in (run / "trace.jsonl").read_text().splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            for kept in event.get("accepted") or ():
                if isinstance(kept, dict) and kept.get("outcome") == "send-back":
                    path = run / "results" / f"{kept['action']}.md"
                    body = json.loads(STATE.search(path.read_text()).group(1))["result"] if path.is_file() else {}
                    text = str(body.get("headline") or "") + " " + str(body.get("summary") or "")
                    sendbacks.append({"stage": kept.get("stage"), "class": klass(str(kept.get("stage")), text), "text": text[:400]})
    row["sendbacks"] = sendbacks
    span = result.get("span") or {}
    if span.get("started") and span.get("ended"):
        row["minutes"] = round((float(span["ended"]) - float(span["started"])) / 60, 1)
    row["turns"] = (result.get("metrics") or {}).get("turns")
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("runs", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    rows = [score(folder) for folder in sorted(p for p in args.runs.expanduser().iterdir() if p.is_dir())]
    args.out.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    for row in rows:
        classes = [s["class"] for s in row.get("sendbacks") or ()]
        print(row["run"], "finished" if row["finished"] else "running", row.get("verdict"),
              f"checks {row.get('checks_passed')}/{len(row.get('checks') or [])}", "send-backs", classes or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
