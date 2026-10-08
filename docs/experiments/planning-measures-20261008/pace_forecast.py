#!/usr/bin/env python3
"""Forecast against actual: the narrative's "about N min left in <scope>" (ShipLoop 0.55.0 and earlier) in recorded runs.

  python3 docs/experiments/planning-measures-20261008/pace_forecast.py [/Users/dadleet/e2e-runs] > pace-forecast.json

For each Pace row a run printed in its packets (run/packets/*.md) it takes the forecast, the step count it was made
at and the scope, and compares the forecast with the minutes that really passed between that step's accept stamp and the
end of the scope (the accept of the scope's last stage: `prepare` for preparation, the last inner stage of the last work item
for the work items, the final accept for release). Reads, never writes, the run folders.
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import metrics  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
RUNS_USED = ["20261005/v1210-battleship-grok-medium", "20261006/v1220-battleship-grok-medium-none",
             "20261006/v1220-battleship-sonnet", "20261007/v1230-battleship-grok-none", "20261007/v1230-battleship-sonnet"]
PACE = re.compile(r"\*\*⏱ Pace\*\* — (\d+) steps? in .*? · about (?:(\d+) h ?)?(?:(\d+) min|under a minute) left in "
                  r"(preparation|the work items|release)")
SCOPE_OF = {"preparation": "prelude", "the work items": "inner", "release": "outer"}


def forecast_minutes(hours, minutes, text: str) -> float:
    return 1.0 if "under a minute" in text else int(hours or 0) * 60 + int(minutes or 0)


def one(folder: str) -> dict:
    out = RUNS / folder
    run_dir = next(p.parent for p in sorted(out.rglob("state.md")) if p.relative_to(out).parts[0] not in ("home", "build"))
    state = metrics.engine_state(run_dir)
    stamps = metrics.acceptance_stamps(run_dir)
    prelude, inner, outer = navigator.graph(state)
    groups = {"prelude": set(prelude), "inner": set(inner), "outer": set(outer)}
    history = [(row["stage"], stamps.get(row["action"])) for row in state["history"]]
    ordered = [t for _, t in history if t is not None]
    ends = {name: max((t for stage, t in history if stage in stages and t is not None), default=None)
            for name, stages in groups.items()}
    # A scope's end is known only once the run has left it: a later scope has an accepted row, or the run is done.
    reached = [name for name in ("prelude", "inner", "outer") if any(stage in groups[name] for stage, _ in history)]
    for number, name in enumerate(("prelude", "inner", "outer")):
        left = (state.get("status") == "done") if name == "outer" else any(
            later in reached for later in ("prelude", "inner", "outer")[number + 1:])
        if not left:
            ends[name] = None
    seen, rows = set(), []
    for packet in sorted((run_dir / "run" / "packets").glob("*.md")) if (run_dir / "run" / "packets").is_dir() else \
            sorted((run_dir / "packets").glob("*.md")):
        for match in PACE.finditer(packet.read_text(errors="replace")):
            steps, scope = int(match.group(1)), match.group(4)
            if (scope, steps) in seen or steps > len(ordered):
                continue
            seen.add((scope, steps))
            line = match.group(0)
            made_at = ordered[steps - 1]
            end = ends[SCOPE_OF[scope]]
            rows.append({"scope": scope, "steps_done": steps,
                         "forecast_min": forecast_minutes(match.group(2), match.group(3), line),
                         "actual_min": round((end - made_at) / 60, 1) if end is not None and end >= made_at else None})
    return {"run": folder, "rows": sorted(rows, key=lambda r: (r["scope"], r["steps_done"]))}


if __name__ == "__main__":
    print(json.dumps({"runs": [one(folder) for folder in RUNS_USED]}, indent=1))
