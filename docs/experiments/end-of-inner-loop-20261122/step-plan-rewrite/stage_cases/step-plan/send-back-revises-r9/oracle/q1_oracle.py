#!/usr/bin/env python3
"""The step-boundary replay's Q1 oracle, run by the stage suite as ``python3 "$STAGE_ORACLE/q1_oracle.py" <check>``.

Reads the sample's result (``$STAGE_RESULT``) and the registered ``expected.json`` beside this file. Script-only:
- ``fidelity``: outcome done; ``steps`` begins with the registered done rows exactly (marks included) and no other row
  is marked done;
- ``correction``: the case's registered predicate, one of:
  - ``no_focused_search``: no test command recorded ``focused`` only searches text (classified here independently of
    the ShipLoop code under test, with shell quoting);
  - ``step_proof_runs``: the named step's Proof differs from the recorded one and exits 0 in the sample's tree.
Exit 0 passes; any other exit fails, with the reason on stderr.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SEARCH = {"grep", "egrep", "fgrep", "rg", "ag", "ack"}


def fail(reason: str) -> None:
    print(reason, file=sys.stderr)
    raise SystemExit(1)


def programs(command: str) -> list:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    found, words = [], []
    try:
        tokens = list(lexer) + [";"]
    except ValueError:
        return []
    for token in tokens:
        if token and all(character in ";&|\n" for character in token):
            while words and (words[0] in ("!", "env", "command", "exec", "time") or "=" in words[0].split("/")[0]):
                words = words[1:]
            if words and words[0] != "cd":
                found.append(words[0].rsplit("/", 1)[-1].lower())
            words = []
        else:
            words.append(token)
    return found


def main(check: str) -> None:
    result = json.loads(Path(os.environ["STAGE_RESULT"]).read_text())
    expected = json.loads(Path(__file__).with_name("expected.json").read_text())
    if result.get("outcome") != "done":
        fail("outcome is " + repr(result.get("outcome")))
    steps = result.get("steps") or []
    if check == "fidelity":
        rows = expected["done_rows"]
        if steps[:len(rows)] != rows:
            fail("the plan does not start with the done rows exactly")
        extra = [row.get("id") for row in steps[len(rows):] if row.get("done") is True]
        if extra:
            fail("rows marked done that are not done: " + ", ".join(map(str, extra)))
        if len(steps) == len(rows):
            fail("no step left to run")
        return
    correction = expected["correction"]
    if correction["kind"] == "no_focused_search":
        bad = [row["command"] for row in result.get("test_commands") or []
               if row.get("suite") == "focused" and programs(row["command"])
               and all(program in SEARCH for program in programs(row["command"]))]
        if bad:
            fail("a focused command still only searches text: " + bad[0][:120])
        return
    if correction["kind"] == "step_proof_runs":
        row = next((row for row in steps if row.get("id") == correction["step"]), None)
        if row is None or not row.get("proof"):
            fail("step " + correction["step"] + " has no proof")
        if row["proof"] == correction["recorded_proof"]:
            fail("step " + correction["step"] + "'s proof is the recorded one")
        done = subprocess.run(["/bin/sh", "-c", row["proof"]], capture_output=True, text=True, timeout=110)
        if done.returncode:
            fail("the amended proof exits " + str(done.returncode) + ": " + (done.stderr or done.stdout)[-400:])
        return
    fail("unknown correction kind " + repr(correction.get("kind")))


if __name__ == "__main__":
    main(sys.argv[1])
