#!/usr/bin/env python3
"""Score FX's live runs (README.md, "FX") by its pre-registered rule, and report the same measures for XI's runs.

Per run (~/e2e-runs-xr/20261031/<arm>-ticket-import-s<n>): every held-out check passed or not; ShipLoop's end state; each
open plan assumption due at a work item and the route the item's last accepted step plan cites it by (a criterion's
`from`, an expectation's `from`, or none); the trace's refusals of this rule (an uncited open item, or a `from` naming
none). Rule: adopt iff F passes at least as many runs as P, and in the F runs whose plan leaves an item open the step plan
cites it through a criterion in at least 3 (fewer than 2 such runs: not exercised live). Reported beside the rule, not
part of it: wall minutes, every send-back with its stage and summary, and for each open item the confirm text of the last
step plan that cites it (a probe the item runs at implement, or the test stage's test). Writes scores-fx.json.
Usage: score_fx.py [GLOB]
"""
import glob
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store  # noqa: E402

REFUSALS = ("as due_item; add an expectation", "as due_item; settle each here", "cite from")


def minutes(folder: Path):
    """Wall minutes from the harness's timeline (as score_xi.py reads them)."""
    try:
        rows = [json.loads(line) for line in (folder / "timeline.jsonl").read_text().splitlines() if line.strip()]
    except OSError:
        return None
    stamps = [row.get("t") or row.get("seconds") or row.get("elapsed") for row in rows]
    stamps = [s for s in stamps if isinstance(s, (int, float))]
    return round((max(stamps) - min(stamps)) / 60, 1) if stamps else None


def score(folder: Path) -> dict:
    arm, sample = folder.name.split("-ticket-import-s")
    result = json.loads((folder / "result.json").read_text())
    accept = (result.get("quality") or {}).get("acceptance") or {}
    ids, passed = accept.get("ids") or [], set(accept.get("passed") or [])
    row = {"run": folder.name, "arm": arm, "sample": int(sample), "end": result.get("outcome_class"),
           "passes": bool(accept.get("observed")) and bool(ids) and passed >= set(ids), "open": {}, "refusals": 0,
           "failed": sorted(set(ids) - passed), "minutes": (result.get("span") or {}).get("minutes") or minutes(folder),
           "send_backs": [], "settled_by": {}}
    runs = sorted(folder.glob(".shiploop-runs/*/run"))
    if not runs:
        return row
    state = store.read_record(runs[0] / "state.md")
    accepted = state.get("accepted") or {}
    opened, step_plans = {}, {}
    for entry in state.get("history") or ():
        if entry.get("outcome") == "send-back":
            row["send_backs"].append({"stage": entry.get("stage"), "summary": str(entry.get("summary") or "")[:300]})
        if entry.get("outcome") != "done":
            continue
        found = accepted.get(entry.get("action")) or {}
        if entry.get("stage") == "plan":
            opened = {a["id"]: a.get("due_item") for a in found.get("assumptions") or ()
                      if isinstance(a, dict) and a.get("disposition") == "open" and a.get("due_item")}
        if entry.get("stage") == "step-plan":
            step_plans[entry.get("action")] = found
    # Every accepted step plan counts (revisions and send-backs included): an item is cited by a criterion when any of
    # them cites it so, else by an expectation when one does.
    routes = {}
    for found in step_plans.values():
        for key, route in (("criteria", "criterion"), ("expectations", "expectation")):
            for rowx in found.get(key) or ():
                if isinstance(rowx, dict) and rowx.get("from"):
                    routes.setdefault(rowx["from"], set()).add(route)
                    # The last step plan's row wins: what the item finally ran to settle the open assumption.
                    row["settled_by"][rowx["from"]] = (route + ": " + str(rowx.get("text") or rowx.get("check")
                                                                         or rowx.get("command") or ""))[:300]
    row["open"] = {ident: ("criterion" if "criterion" in routes.get(ident, ()) else
                           "expectation" if "expectation" in routes.get(ident, ()) else "none") for ident in opened}
    trace = runs[0] / "trace.jsonl"
    if trace.is_file():
        row["refusals"] = sum(1 for line in trace.read_text(errors="ignore").splitlines()
                              if any(marker in line for marker in REFUSALS))
    return row


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "~/e2e-runs-xr/20261031/*-ticket-import-s*"
    rows = [score(Path(p)) for p in sorted(glob.glob(os.path.expanduser(pattern)))
            if Path(p).is_dir() and (Path(p) / "result.json").is_file()]
    arms = {}
    for arm in sorted({r["arm"] for r in rows}):
        mine = [r for r in rows if r["arm"] == arm]
        exercised = [r for r in mine if r["open"]]
        arms[arm] = {"n": len(mine), "passes": sum(r["passes"] for r in mine), "with_open_item": len(exercised),
                     "criterion_route": sum(1 for r in exercised if all(v == "criterion" for v in r["open"].values())),
                     "refusals_of_the_rule": sum(r["refusals"] for r in mine)}
    p, f = arms.get("P"), arms.get("F")
    rule = None
    if p and f:
        exercised = f["with_open_item"] >= 2
        rule = {"no_harm": f["passes"] >= p["passes"],
                "mechanism": (f["criterion_route"] >= 3) if exercised else "not exercised live",
                "adopt": bool(f["passes"] >= p["passes"] and (f["criterion_route"] >= 3 if exercised else True)
                              and p["n"] >= 4 and f["n"] >= 4)}
    report = {"rows": rows, "arms": arms, "rule": rule}
    (HERE / "scores-fx.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    for r in rows:
        print(r["run"], "PASS" if r["passes"] else "non-pass", r["end"], r["minutes"], "min; open", r["open"],
              "refusals", r["refusals"], "send-backs", [b["stage"] for b in r["send_backs"]])
    print(json.dumps({"arms": arms, "rule": rule}, indent=1))


if __name__ == "__main__":
    main()
