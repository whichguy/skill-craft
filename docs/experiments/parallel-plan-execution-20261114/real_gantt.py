#!/usr/bin/env python3
"""real_gantt.py: one lane per task for an E17 trial, every attempt drawn (the scorer's own Gantt forgets earlier attempts), with the landing and each
integration marked. Reads evidence/e17-<host>-<cell>/ledger.jsonl (or a trial folder's work/run/ledger.jsonl).

  python3 real_gantt.py TRIAL_OR_EVIDENCE_FOLDER...       text, one block per trial
  python3 real_gantt.py --json FOLDER                     the lanes as JSON (for a drawing)

Legend: attempt 1 is `#`, attempt 2 `=`, attempt 3 or later `-`; a fix attempt is drawn with `f` in place of its digit; marks on the line below a lane:
L the landing, M a merge, C a textual conflict, R a red re-test (the merge undone).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

WIDTH = 78


def load(folder: Path) -> list:
    for rel in ("ledger.jsonl", "work/run/ledger.jsonl"):
        p = folder / rel
        if p.is_file():
            return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    raise SystemExit(f"no ledger in {folder}")


def lanes(events: list) -> dict:
    t0 = events[0]["ts"]
    out: dict = {"t0": t0, "end": events[-1]["ts"] - t0, "tasks": {}, "landed": None}
    open_: dict = {}
    fix: dict = {}
    for e in events:
        s, k, d = e["step"], e["kind"], e["detail"]
        if k == "workspace":
            fix[(s, d.get("attempt"))] = bool(d.get("fix"))
        elif k == "start":
            open_[s] = [e["ts"] - t0, None, None]
        elif k in ("end", "fail") and s in open_ and open_[s][1] is None:
            open_[s][1] = e["ts"] - t0
            lane = out["tasks"].setdefault(s, {"attempts": [], "marks": []})
            n = len(lane["attempts"]) + 1
            lane["attempts"].append({"n": n, "start": round(open_[s][0], 1), "end": round(open_[s][1], 1), "fix": fix.get((s, n), False)})
        elif k == "landed":
            out["landed"] = round(e["ts"] - t0, 1)
        elif k in ("merged", "conflict", "redtest"):
            out["tasks"].setdefault(s, {"attempts": [], "marks": []})["marks"].append({"kind": {"merged": "M", "conflict": "C", "redtest": "R"}[k], "at": round(e["ts"] - t0, 1)})
    return out


def render(name: str, data: dict) -> str:
    span = max(data["end"], 1.0)
    col = lambda t: min(WIDTH - 1, max(0, int(t / span * WIDTH)))
    lines = [f"{name}   (whole {span:.0f} s; one column = {span / WIDTH:.1f} s)"]
    for step in sorted(data["tasks"]):
        lane = data["tasks"][step]
        row = [" "] * WIDTH
        for a in lane["attempts"]:
            ch = "f" if a["fix"] else ("#" if a["n"] == 1 else ("=" if a["n"] == 2 else "-"))
            for c in range(col(a["start"]), max(col(a["start"]) + 1, col(a["end"]) + 1)):
                if c < WIDTH:
                    row[c] = ch
        marks = [" "] * WIDTH
        for m in lane["marks"]:
            marks[col(m["at"])] = m["kind"]
        if data["landed"] is not None:
            marks[col(data["landed"])] = marks[col(data["landed"])] if marks[col(data["landed"])] != " " else "L"
        detail = ", ".join(f"{a['n']}{'f' if a['fix'] else ''}: {a['end'] - a['start']:.0f}s" for a in lane["attempts"])
        lines.append(f"{step:<3}|{''.join(row)}| {detail}")
        lines.append(f"   |{''.join(marks)}|")
    if data["landed"] is not None:
        lines.append(f"   landing at {data['landed']:.0f} s (L)")
    return "\n".join(lines)


def main(argv: list) -> int:
    if argv and argv[0] == "--json":
        print(json.dumps(lanes(load(Path(argv[1]))), indent=1))
        return 0
    for arg in argv:
        folder = Path(arg)
        print(render(folder.name, lanes(load(folder))) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
