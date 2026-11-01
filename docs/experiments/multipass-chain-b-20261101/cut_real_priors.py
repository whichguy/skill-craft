#!/usr/bin/env python3
"""Cut the living files of saved, real pass-1 runs of `user-listing` into this folder, as the real priors chain B's cases are written from.

    python3 cut_real_priors.py

Chain B (docs/shiploop-multipass-journal.md, Round 5) is user-listing and three links that follow it. The journal's Round 3 method learning is
that a retention word and a ledger pattern written from the request, with a synthetic prior, were wrong on the first real prior (E3).
These are real priors: pass-1 deliveries of Codex gpt-6.1-terra on `user-listing`, made by several ShipLoop builds between 2026-10-29 and
2026-11-01 for other experiments, left on this machine. Writes:

    real-priors/<name>/{spec,architecture}.md   the files as the run left them
    real-priors/provenance.json                 per run: host, model, effort, plugin and ShipLoop version, source, verdict

The files carry no machine path, address or credential (checked when they were cut: the script refuses a file that names /Users/).
test/shiploop-e2e-user-directory.test.py reads them, so the words and patterns of the three links are pinned to the evidence they came from.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
HOME = Path.home()
RUNS = {
    "bf-codex-r1": HOME / "e2e-runs-brownfield/20261029/bf-codex-r1-user-listing",
    "bf-codex-r2": HOME / "e2e-runs-brownfield/20261029/bf-codex-r2-user-listing",
    "hooks-before": HOME / "e2e-runs-brownfield/20261029/hooks-before-user-listing",
    "hooks-after": HOME / "e2e-runs-brownfield/20261029/hooks-after-user-listing",
    "qr-A-s3": HOME / "e2e-runs-qr/20261031/A-user-listing-s3",
    "qr-B-s1": HOME / "e2e-runs-qr/20261031/B-user-listing-s1",
    "tl-M-s1": HOME / "e2e-runs-tl/20261101/M-user-listing-s1",
}
LIVING = ("spec.md", "architecture.md")


def main() -> int:
    provenance = {}
    for name, run in RUNS.items():
        target = HERE / "real-priors" / name
        target.mkdir(parents=True, exist_ok=True)
        for living in LIVING:
            text = (run / "work" / "docs" / "shiploop" / living).read_text()
            if "/Users/" in text:
                print(f"refused: {name}/{living} names a machine path", file=sys.stderr)
                return 1
            (target / living).write_text(text)
        invocation = json.loads((run / "invocation.json").read_text())
        result = json.loads((run / "result.json").read_text())
        versions = invocation.get("versions") or {}
        provenance[name] = {"folder": run.name, "host": invocation.get("host"), "model": invocation.get("model"),
                            "effort": invocation.get("effort"), "skill_craft": versions.get("plugin_version"),
                            "shiploop": versions.get("shiploop_version"), "source": versions.get("source"),
                            "pass": result.get("pass")}
    (HERE / "real-priors" / "provenance.json").write_text(json.dumps(provenance, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    shutil.rmtree(HERE / "real-priors", ignore_errors=True)
    raise SystemExit(main())
