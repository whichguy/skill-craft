#!/usr/bin/env python3
"""Cut the saved pass-1 and pass-2 runs of the ticket pair into this folder: their three living files and their delta ledgers.

    python3 cut_saved_pairs.py RUNS_ROOT

RUNS_ROOT holds the run folders ``<prefix>-ticket-assignment`` (pass 1, a run on the base fixture) and
``<prefix>-ticket-escalation`` (pass 2, a follow-on that continued from it) for each prefix in PREFIXES; the 2026-10-29
brownfield rounds are ~/e2e-runs-brownfield/20261029. Writes:

    saved-pairs/<prefix>/pass1/{spec,environment,architecture}.md   the files as the first run left them
    saved-pairs/<prefix>/pass2/{spec,environment,architecture}.md   the files as the follow-on left them
    ledger-saved-pairs.json                                         test/shiploop_e2e/delta.py's block for all eight runs

The files carry no machine path, address or credential (checked when they were cut); the ledger carries commit ids only.
test/shiploop-e2e-delta.test.py reads both, so the instrument is pinned to the evidence it was built from.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
import delta  # noqa: E402

PREFIXES = ("bf-codex-r1", "bf-codex-r2", "hooks-before", "hooks-after")
LIVING = ("spec.md", "environment.md", "architecture.md")


def main(root: Path) -> int:
    ledger = {}
    for prefix in PREFIXES:
        for passed, case in (("pass1", "ticket-assignment"), ("pass2", "ticket-escalation")):
            run = root / f"{prefix}-{case}"
            target = HERE / "saved-pairs" / prefix / passed
            target.mkdir(parents=True, exist_ok=True)
            for name in LIVING:
                shutil.copyfile(run / "work" / "docs" / "shiploop" / name, target / name)
            ledger[run.name] = delta.saved(run)
    (HERE / "ledger-saved-pairs.json").write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]).expanduser().resolve()))
