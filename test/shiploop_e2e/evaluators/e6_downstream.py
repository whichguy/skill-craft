"""E6 R3 (downstream): was the item delivered, and what did its steps cost?

From the records only: the slice's slice-result.json (its verdicts: process, inner_loop, no_overshoot, assembled and
checks, and the item's history), its metrics.json (per-stage seconds and turns, Improve children and passes, the peak
input tokens) and the accepted step plan. ``value`` is 1 when the slice passed: the item was carried forward, its
product assembled and its case checks pass; else 0. The cost fields say what the plan's size cost downstream: the
steps planned, the implement packets done with their seconds (in all and per step), the item's minutes (the slice's
span), the Improve children and passes, the send-backs in the item's history, the turns and the peak input tokens.
Quality comes first (``value``), then tokens, then time (memory eval-decision-priority).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

BINARY = True  # a slice passes or not


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def cost(metrics: dict, result: dict) -> dict:
    """The downstream cost fields of one slice from its metrics and result records."""
    implement = [s for s in metrics.get("stages") or () if isinstance(s, dict) and s.get("stage") == "implement"
                 and s.get("outcome") == "done"]
    seconds = [s["seconds"] for s in implement if isinstance(s.get("seconds"), (int, float))]
    span = metrics.get("span") or {}
    item = (span["ended"] - span["started"]) if isinstance(span.get("ended"), (int, float)) and \
        isinstance(span.get("started"), (int, float)) else None
    reviews = metrics.get("improve_reviews") or {}
    history = result.get("item_history") or []
    return {"implement_steps": len(implement), "implement_seconds": round(sum(seconds), 1) if seconds else None,
            "implement_seconds_per_step": round(sum(seconds) / len(seconds), 1) if seconds else None,
            "item_minutes": round(item / 60, 1) if item is not None else None,
            "improve_children": metrics.get("improve_children"), "improve_passes": reviews.get("passes"),
            "send_backs": sum(1 for row in history if isinstance(row, dict) and row.get("outcome") == "send-back"),
            "turns": metrics.get("turns"), "input_peak": (metrics.get("tokens") or {}).get("input_peak")}


def score(sample: Path) -> dict:
    sample = Path(sample)
    result = _read(sample / "slice-result.json")
    if result is None:
        return {"value": None, "why": "no slice-result.json"}
    plans = [r for r in common.results(common.run_dir(sample), "step-plan")
             if (r.get("result") or {}).get("outcome") == "done"]
    steps = len((plans[-1]["result"].get("steps") or ())) if plans else None
    return {"value": int(bool(result.get("pass"))), "verdicts": result.get("verdicts"), "steps": steps,
            **cost(_read(sample / "metrics.json") or {}, result)}


def verify() -> list[dict]:
    rows = []
    stages = [{"stage": "step-plan", "outcome": "done", "seconds": 400.0},
              *({"stage": "implement", "outcome": "done", "seconds": s} for s in (100.0, 200.0, 300.0)),
              {"stage": "implement", "outcome": None, "incomplete": True, "seconds": 5.0}]
    metrics = {"stages": stages, "span": {"started": 1000.0, "ended": 2800.0}, "improve_children": 4,
               "improve_reviews": {"passes": 6}, "turns": 90, "tokens": {"input_peak": 120000}}
    history = [{"stage": "implement", "outcome": "done"}, {"stage": "implement", "outcome": "send-back"}]
    passed = {"pass": True, "verdicts": {"process": True, "inner_loop": True, "no_overshoot": True, "assembled": True,
                                         "checks": True}, "item_history": history}
    failed = {**passed, "pass": False, "verdicts": {**passed["verdicts"], "checks": False}}
    with tempfile.TemporaryDirectory(prefix="e6-downstream-") as temp:
        for name, result, expect in (("planted delivered item", passed, 1), ("planted item failing its checks", failed, 0)):
            folder = Path(temp) / name.replace(" ", "-")
            folder.mkdir()
            (folder / "slice-result.json").write_text(json.dumps(result))
            (folder / "metrics.json").write_text(json.dumps(metrics))
            found = score(folder)
            ok = (found["value"] == expect and found["implement_steps"] == 3 and found["implement_seconds"] == 600.0
                  and found["implement_seconds_per_step"] == 200.0 and found["item_minutes"] == 30.0
                  and found["send_backs"] == 1 and found["improve_passes"] == 6 and found["steps"] is None)
            rows.append({"record": name, "expect": f"value {expect}, 3 implement steps, 600 s", "got": found, "ok": ok})
        empty = Path(temp) / "unfinished"
        empty.mkdir()
        found = score(empty)
        rows.append({"record": "planted unfinished slice", "expect": "value None", "got": found,
                     "ok": found["value"] is None})
    return rows
