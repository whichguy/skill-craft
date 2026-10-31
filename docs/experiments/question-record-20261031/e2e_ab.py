#!/usr/bin/env python3
"""Read the live A/B runs (README.md, "Live A/B"): Codex harness, Terra 6.1 high, all tools; arm A = ShipLoop at main
3ae78af7, arm B = the changed ShipLoop.  Per run: the harness verdict (result.json `pass`), wall minutes (timeline.jsonl),
implement send-backs and why, step-plan refusals the run's trace records (a `check` or `complete` at step-plan with a
nonzero exit, and its first words), the proof-order refusal among them, packets, and the intake result's question
count.  Writes ../scores-e2e-ab.json.  Usage: e2e_ab.py [GLOB, default ~/e2e-runs-qr/20261031/[AB]-*]
"""
import glob
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import SKILL_SCRIPTS  # noqa: E402

sys.path.insert(0, str(SKILL_SCRIPTS))
import shiploop_store as store  # noqa: E402

PROOF_ORDER = "which the item base does not have"


def read(out: Path) -> dict:
    arm, rest = out.name.split("-", 1)
    case, sample = rest.rsplit("-s", 1)
    row = {"run": out.name, "arm": arm, "case": case, "sample": int(sample)}
    result = out / "result.json"
    row["pass"] = json.loads(result.read_text()).get("pass") if result.is_file() else None
    times = [json.loads(line).get("t") for line in (out / "timeline.jsonl").read_text().splitlines() if line.strip()] \
        if (out / "timeline.jsonl").is_file() else []
    times = [t for t in times if isinstance(t, (int, float))]
    row["minutes"] = round((max(times) - min(times)) / 60, 1) if times else None
    runs = sorted(out.glob("work/.shiploop")) + sorted(out.glob(".shiploop-runs/*/run"))
    if not runs:
        return {**row, "state": "no run folder"}
    run = runs[0]
    state = store.read_record(run / "state.md")
    accepted = state.get("accepted") or {}
    history = state.get("history") or []
    row["status"] = state.get("status")
    row["implement_send_backs"] = [str((accepted.get(h["action"]) or {}).get("summary") or "")[:200]
                                   for h in history if h.get("stage") == "implement" and h.get("outcome") == "send-back"]
    row["step_plans"] = sum(1 for h in history if h.get("stage") == "step-plan" and h.get("outcome") == "done")
    intake = next((accepted.get(h["action"]) for h in history if h.get("stage") == "intake"), None) or {}
    row["intake_questions"] = len(intake.get("questions") or [])
    trace = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines() if line.strip()] \
        if (run / "trace.jsonl").is_file() else []
    refusals = [t for t in trace if t.get("kind") == "command" and t.get("verb") in ("check", "complete")
                and t.get("exit") not in (0, None) and "step-plan" in (t.get("stage") or [None])[:1]]
    row["step_plan_refusals"] = len(refusals)
    row["proof_order_refusals"] = sum(PROOF_ORDER in (t.get("error") or "") for t in refusals)
    row["refusal_heads"] = [(t.get("error") or "")[:120] for t in refusals]
    row["packets"] = sum(1 for t in trace if t.get("kind") == "packet")
    return row


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "~/e2e-runs-qr/20261031/[AB]-*"
    rows = [read(Path(p)) for p in sorted(glob.glob(os.path.expanduser(pattern))) if Path(p).is_dir()]
    (HERE / "scores-e2e-ab.json").write_text(json.dumps({"rows": rows}, indent=2) + "\n")
    for r in rows:
        print(f"{r['run']:28} pass={r.get('pass')} min={r.get('minutes')} status={r.get('status')} "
              f"implement_send_backs={len(r.get('implement_send_backs') or [])} step_plans={r.get('step_plans')} "
              f"step_plan_refusals={r.get('step_plan_refusals')} proof_order={r.get('proof_order_refusals')} "
              f"intake_q={r.get('intake_questions')}")
        for text in r.get("implement_send_backs") or []:
            print("    send-back:", text[:160])


if __name__ == "__main__":
    main()
