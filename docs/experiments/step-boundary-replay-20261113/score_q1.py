#!/usr/bin/env python3
"""Score the step-boundary replay's Q1 samples by the registered measures (README, revision 1). Script only.

Usage: score_q1.py RESULTS_ROOT [--json OUT]. RESULTS_ROOT is a ``stages.py live --out`` folder.
Per sample (``step-plan/<scenario>/<n>/``):
- M1 accepted: stage-result.json's process verdict is stage-complete and the result's outcome is done;
- M2 first-attempt copy: no fix-forward refusal text anywhere in events.jsonl or transcript.md (each counted);
- M3 fidelity / M4 correction: the oracle's own checks in stage-result.json (q1_oracle.py fidelity / correction);
- other refusals: distinct refusal reasons from complete ("ShipLoop navigator:") or check ("the check says no.") that are
  not fix forward's, counted separately (an events log echoes a reason more than once, so distinct reasons are counted).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FIX_FORWARD = [r"are done \(reviewed and committed\) and stay as they are", r"done step \S+ differs from its accepted row",
               r"no step of \S+ is done, so no step carries", r"every step is done: an amendment keeps",
               r"whose cases are due at done step", r"no step still to run lists"]
# A refusal from complete ("ShipLoop navigator: ...") or from check ("the check says no. ..."); the reason that follows.
REFUSAL = re.compile(r"(?:ShipLoop navigator: |the check says no\. )([^\n\"\\]{0,100})")


def sample_rows(root: Path) -> list:
    rows = []
    for verdict in sorted(root.glob("step-plan/*/*/stage-result.json")):
        folder = verdict.parent
        data = json.loads(verdict.read_text())
        text = "".join((folder / name).read_text(errors="replace") for name in ("events.jsonl", "transcript.md")
                       if (folder / name).is_file())
        fix_forward = sum(len(re.findall(pattern, text)) for pattern in FIX_FORWARD)
        others = [match for match in REFUSAL.findall(text) if not any(re.search(p, match) for p in FIX_FORWARD)]
        checks = data.get("checks") or []

        def proven(ident: str) -> bool | None:
            found = [check for check in checks if check.get("proves") == ident]
            return all(check.get("pass") for check in found) if found else None

        sessions = data.get("sessions") or []
        rows.append({"scenario": folder.parent.name, "sample": folder.name,
                     "process": sessions[-1].get("status") if sessions else None,
                     "outcome": data.get("outcome"), "result_source": data.get("result_source"),
                     "m1_accepted": None, "m2_clean_first": fix_forward == 0, "fix_forward_refusals": fix_forward,
                     "other_refusals": len(set(others)), "other_refusal_heads": sorted(set(o[:60] for o in others))[:5],
                     "m3_fidelity": proven("P1"), "m4_correction": proven("P2"),
                     "apparatus_overshoot": data.get("overshoot"),
                     "minutes": round(sum(float(s.get("seconds") or 0) for s in sessions) / 60, 1)})
    for row in rows:
        row["m1_accepted"] = row["outcome"] == "done" and row["process"] == "stage-complete"
    return rows


def main(argv: list) -> None:
    root = Path(argv[0])
    rows = sample_rows(root)
    for row in rows:
        print(json.dumps(row))
    total = len(rows)
    for key in ("m1_accepted", "m2_clean_first", "m3_fidelity", "m4_correction"):
        print(f"{key}: {sum(1 for row in rows if row[key])} of {total}")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
