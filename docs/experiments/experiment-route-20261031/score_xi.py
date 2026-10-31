#!/usr/bin/env python3
"""Score XI's live runs (README.md, "XI") by the pre-registered rule.

Per run (~/e2e-runs-xr/20261031/<arm>-ticket-import-s<n>): passes when every held-out acceptance check passed
(result.json ``quality.acceptance``); a run with no observed acceptance (ShipLoop not done) is a non-pass. Also kept: the
failed checks, ShipLoop's end state, wall minutes (timeline.jsonl), the intake questions routed `experiment`, research's
``experiments`` rows as stored, and, for each probe row, whether its command appears in the host's event stream.
Rule: adopt B iff its pass rate beats A's with an exact one-sided permutation p < 0.05, no B run fails a pass-to-pass check
that every A run passed, and the probe commands appear in the event stream of at least 4 of the 6 B runs.
Writes scores-xi.json.  Usage: score_xi.py [GLOB]
"""
import glob
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "question-record-20261031"))
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
from stats import mean, permutation_p  # noqa: E402
import shiploop_store as store  # noqa: E402

P2P = {"ticket-lifecycle-unchanged", "listing-unchanged", "notifications-unchanged", "restart-keeps-state",
       "cli-raw-columns", "old-data-loads"}


def minutes(folder: Path):
    try:
        rows = [json.loads(line) for line in (folder / "timeline.jsonl").read_text().splitlines() if line.strip()]
        stamps = [row.get("t") or row.get("seconds") or row.get("elapsed") for row in rows]
        stamps = [s for s in stamps if isinstance(s, (int, float))]
        return round((max(stamps) - min(stamps)) / 60, 1) if stamps else None
    except OSError:
        return None


def score(folder: Path) -> dict:
    arm, sample = folder.name.split("-ticket-import-s")
    row = {"run": folder.name, "arm": arm, "sample": int(sample)}
    result = json.loads((folder / "result.json").read_text())
    accept = (result.get("quality") or {}).get("acceptance") or {}
    ids, passed = accept.get("ids") or [], set(accept.get("passed") or [])
    row.update(observed=bool(accept.get("observed")), failed=[i for i in ids if i not in passed],
               passes=bool(accept.get("observed")) and bool(ids) and not [i for i in ids if i not in passed],
               end=result.get("outcome_class"), basis=(result.get("outcome_basis") or "")[:200],
               minutes=(result.get("span") or {}).get("minutes") or minutes(folder))
    runs = sorted(folder.glob(".shiploop-runs/*/run"))
    if runs:
        state = store.read_record(runs[0] / "state.md")
        accepted = state.get("accepted") or {}
        for entry in state.get("history") or ():
            if entry.get("outcome") != "done":
                continue
            found = accepted.get(entry.get("action")) or {}
            if entry.get("stage") == "intake":
                row["routed"] = [q.get("id") for q in found.get("questions") or () if q.get("route") == "experiment"]
            if entry.get("stage") == "research":
                row["experiments"] = found.get("experiments")
        events = (folder / "events.jsonl").read_text(errors="ignore") if (folder / "events.jsonl").is_file() else ""
        probes = [e for e in row.get("experiments") or () if isinstance(e, dict) and e.get("check")]
        row["probes_in_events"] = [bool(e["check"].strip()) and e["check"].strip()[:60] in events for e in probes]
    return row


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "~/e2e-runs-xr/20261031/[AB]-ticket-import-s*"
    rows = [score(Path(p)) for p in sorted(glob.glob(os.path.expanduser(pattern)))
            if Path(p).is_dir() and (Path(p) / "result.json").is_file()]
    arms = {}
    for arm in ("A", "B"):
        mine = [r for r in rows if r["arm"] == arm]
        arms[arm] = {"n": len(mine), "passes": sum(r["passes"] for r in mine),
                     "minutes": mean(r["minutes"] for r in mine if r["minutes"] is not None) if mine else None}
    a = [1.0 if r["passes"] else 0.0 for r in rows if r["arm"] == "A"]
    b = [1.0 if r["passes"] else 0.0 for r in rows if r["arm"] == "B"]
    held_by_a = P2P - {c for r in rows if r["arm"] == "A" for c in r["failed"]}
    regress = sorted({c for r in rows if r["arm"] == "B" for c in r["failed"] if c in held_by_a})
    probed = sum(1 for r in rows if r["arm"] == "B" and r.get("probes_in_events") and all(r["probes_in_events"]))
    p = permutation_p(a, b) if a and b else None
    rule = {"p_one_sided": p, "b_pass_to_pass_regressions": regress, "b_runs_with_probes_in_events": probed,
            "adopt": bool(p is not None and p < 0.05 and not regress and probed >= 4 and len(b) >= 6 and len(a) >= 6)}
    report = {"rows": rows, "arms": arms, "rule": rule}
    (HERE / "scores-xi.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    for r in rows:
        print(r["run"], "PASS" if r["passes"] else "non-pass", r["end"], r["minutes"], "failed", r["failed"],
              "routed", r.get("routed"), "experiments", len(r.get("experiments") or []), "in events", r.get("probes_in_events"))
    print(json.dumps({"arms": arms, "rule": rule}, indent=1))


if __name__ == "__main__":
    main()
