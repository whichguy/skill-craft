"""Replay the harness's text reader of verify records, before and after the string-aware scan, over every retained record.

    python3 -I replay_rows.py --repo REPO --base BASE_COMMIT ROOT [ROOT ...]

``metrics._RUN_ROWS`` counts the ``"command":`` keys inside a verify record's ``runs`` array.  The BASE commit's version
(read with ``git show`` and executed alone: it needs only ``re``) counted every bracket, strings included; REPO's version
reads JSON strings as strings.  For each distinct verify record (``*-verify*.md``, deduplicated by content) under the
ROOTs this prints how many records the two count differently, in which direction and where, and checks the new count
against the JSON reader (``fidelity._verify_record``: the ``runs`` list of a ``shiploop-test-loop/v1`` record) on every
record that reader can read.  Then it reads the 2026-11-14 trial's run directory through both public readers.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

TRIAL = Path("/Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/run/.shiploop-runs/"
             "work-20261114-161603-238276/run")


def base_reader(repo: str, base: str):
    source = subprocess.run(["git", "-C", repo, "show", base + ":test/shiploop_e2e/metrics.py"], check=True,
                            capture_output=True, text=True).stdout
    found = re.search(r"^def _RUN_ROWS\(.*?(?=^\S)", source, re.S | re.M)
    space: dict = {"re": re}
    exec(compile(found.group(0), "base _RUN_ROWS", "exec"), space)  # noqa: S102 - the base commit's own function
    return space["_RUN_ROWS"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("roots", nargs="+")
    args = parser.parse_args()
    sys.path[:0] = [str(Path(args.repo) / "test/shiploop_e2e"), str(Path(args.repo) / "skills/shiploop/scripts")]
    import fidelity  # noqa: E402
    import metrics  # noqa: E402
    old = base_reader(args.repo, args.base)
    seen, changed, directions = set(), collections.defaultdict(list), collections.Counter()
    json_read = json_agree = 0
    disagree = []
    for root in args.roots:
        for path, _dirs, files in os.walk(root):
            for name in files:
                if not re.search(r"-verify\d*\.md$", name):
                    continue
                file = Path(path) / name
                text = file.read_text(errors="replace")
                digest = hashlib.sha256(text.encode()).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                before, after = len(old(text)), len(metrics._RUN_ROWS(text))
                if before != after:
                    directions["up" if after > before else "down"] += 1
                    changed[str(file).split("/run/tests/")[0]].append((name, before, after))
                record = fidelity._verify_record(file)
                if record is not None:
                    json_read += 1
                    rows = sum(isinstance(row, dict) for row in record["runs"])
                    if rows == after:
                        json_agree += 1
                    else:
                        disagree.append((str(file), after, rows))
    print("base", args.base)
    print("distinct verify records:", len(seen), "| counted differently:", sum(directions.values()), dict(directions))
    for directory, entries in sorted(changed.items()):
        print("   ", directory)
        for name, before, after in entries:
            print("       ", name, before, "->", after)
    print("records the JSON reader reads:", json_read, "| the new count agrees on:", json_agree)
    for entry in disagree[:20]:
        print("    disagrees:", entry)
    if TRIAL.is_dir():
        text_reader, json_reader = metrics.verifications(TRIAL), fidelity.validation(TRIAL)
        print("the trial: text reader", text_reader["commands"], "| JSON reader", json_reader["runs"],
              "| disagreement:", fidelity.reader_disagreement(json_reader, text_reader))
    return 0 if not disagree else 1


if __name__ == "__main__":
    sys.exit(main())
