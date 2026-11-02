#!/usr/bin/env python3
"""Cut the compact evidence of the four chain B runs into this folder, once they have run (journal Round 5).

    python3 chain_b_harvest.py ROOT

ROOT holds ``B1-user-listing``, ``B2-user-roles``, ``B3-user-team-listing`` and ``B4-user-page-size`` (chain_b_driver.py). Writes:

    passes/<B1..B4>/{spec,architecture,environment}.md   the three living files as the pass left them (the real priors of the next pass, and of any later case words)
    chain-b-ledgers.json                                 per pass: the ledger's block (test/shiploop_e2e/delta.py), the verdict and checks, the hidden acceptance rows,
                                                         cost and the versions it ran on
    chain-b-commits.txt                                  per pass: the commits of the three living files, oldest first, so a reader can see which stage wrote an entry

The runs themselves stay outside the repository (a few hundred megabytes with their transcripts); the files carry no machine path or credential (the script refuses a file that
names /Users/).
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain_b_readout as readout  # noqa: E402

delta = readout.delta
LIVING = ("spec.md", "architecture.md", "environment.md")


def main(root: Path) -> int:
    ledgers, commits = {}, []
    for key, name in readout.PASSES.items():
        folder = root / name
        if not (folder / "result.json").is_file():
            print(f"{name}: no result yet, skipped")
            continue
        target = HERE / "passes" / key
        target.mkdir(parents=True, exist_ok=True)
        for living in LIVING:
            text = (folder / "work" / "docs" / "shiploop" / living).read_text()
            if "/Users/" in text:
                print(f"refused: {name}/{living} names a machine path", file=sys.stderr)
                return 1
            (target / living).write_text(text.rstrip("\n") + "\n")  # byte for byte but for trailing blank lines, which git diff --check refuses
        saved = delta.saved(folder) or {}
        result = json.loads((folder / "result.json").read_text())
        metrics = json.loads((folder / "metrics.json").read_text())
        invocation = json.loads((folder / "invocation.json").read_text())
        acceptance = (result.get("quality") or {}).get("acceptance") or {}
        ledgers[name] = {
            "delta": saved.get("delta"), "line": delta.line(name, saved).split(": ", 1)[-1] if saved else None,
            "pass": result.get("pass"), "elapsed_seconds": (result.get("process") or {}).get("elapsed_seconds"),
            "checks": [{"pass": row.get("pass"), "command": row.get("command", "")[:90]} for row in result.get("checks") or []],
            "hidden": [{"id": row.get("id"), "pass": row.get("pass"), "note": row.get("note", "")[:200]} for row in acceptance.get("checks") or []],
            "model_calls": metrics.get("model_calls"), "tokens": metrics.get("tokens"), "turns": metrics.get("turns"),
            "versions": {key_: (invocation.get("versions") or {}).get(key_) for key_ in ("plugin_version", "shiploop_version", "source")},
            "host": {key_: invocation.get(key_) for key_ in ("host", "model", "effort", "host_build")},
        }
        # The commits of the living files that this pass made: those after the head the pass before it ended on (all of them for the first pass).
        before = list(readout.PASSES.values())[list(readout.PASSES.values()).index(name) - 1] if key != "B1" else None
        span = []
        if before and (root / before / "work").is_dir():
            head = subprocess.run(["git", "-C", str(root / before / "work"), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            span = [f"{head}..HEAD"]
        log = subprocess.run(["git", "-C", str(folder / "work"), "log", "--reverse", "--format=%h %s", *span, "--",
                              "docs/shiploop/spec.md", "docs/shiploop/architecture.md", "docs/shiploop/environment.md"], capture_output=True, text=True)
        commits.append(f"== {name}\n{log.stdout}")
    (HERE / "chain-b-ledgers.json").write_text(json.dumps(ledgers, indent=1, sort_keys=True) + "\n")
    (HERE / "chain-b-commits.txt").write_text("\n".join(commits))
    return 0


if __name__ == "__main__":
    shutil.rmtree(HERE / "passes", ignore_errors=True)
    raise SystemExit(main(Path(sys.argv[1]).expanduser().resolve()))
