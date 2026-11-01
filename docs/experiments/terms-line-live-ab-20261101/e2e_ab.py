#!/usr/bin/env python3
"""Read the live A/B runs of the terms-and-references line (README.md): Codex harness, Terra 6.1 high, all tools; arm A =
ShipLoop at origin/main, arm B = the same plus the K12 change.  Per run: the harness verdict (result.json `pass`), wall
minutes, tokens, refused callbacks (all stages, and at intake by the text that names question_categories), the intake
ledger as stored (its categories, the K12 row, the K12 questions) and as the model submitted it, the intake stage's seconds
and tool calls, and whether the run asked a person.  Then the registered rules L1 to L5 over the six runs of each arm.
Writes scores.json beside this file.  Usage: e2e_ab.py [GLOB, default ~/e2e-runs-tl/20261101/[AB]-*]
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store  # noqa: E402

CATEGORIES = [f"K{number}" for number in range(1, 13)]
VERBS = ("check", "complete")


def mean(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 3) if values else None


def submitted_ledger(run, action):
    """The ledger as the model wrote it (inbox/<action>.md), before the gate or the store touched it."""
    inbox = run / "inbox" / f"{action}.md"
    if not inbox.is_file():
        return {}
    found = re.search(r"```shiploop-state\s*(\{.*\})\s*```", inbox.read_text(encoding="utf-8"), re.S)
    try:
        return json.loads(found.group(1)) if found else {}
    except ValueError:
        return {}


def read(out):
    arm, rest = out.name.split("-", 1)
    case, sample = rest.rsplit("-s", 1)
    row = {"run": out.name, "arm": arm, "case": case, "sample": int(sample)}
    result = json.loads((out / "result.json").read_text()) if (out / "result.json").is_file() else {}
    row["pass"] = result.get("pass")
    row["local_head"] = (result.get("versions") or {}).get("local_head")
    row["plugin_sha256"] = (result.get("versions") or {}).get("plugin_sha256")      # the tree the host loaded
    metrics = json.loads((out / "metrics.json").read_text()) if (out / "metrics.json").is_file() else {}
    row["tokens"] = (metrics.get("tokens") or {}).get("processed")
    row["turns"] = metrics.get("turns")
    row["asked_user"] = metrics.get("asked_user")
    intake_stage = next((s for s in metrics.get("stages") or [] if s.get("stage") == "intake"), {})
    row["intake_seconds"] = intake_stage.get("seconds")
    row["intake_tool_calls"] = intake_stage.get("tool_calls")
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
    intake_row = next((h for h in history if h.get("stage") == "intake"), None)
    stored = (accepted.get(intake_row["action"]) if intake_row else None) or {}
    categories = stored.get("question_categories") or []
    ids = sorted((str(c.get("id")) for c in categories if isinstance(c, dict)), key=lambda k: (len(k), k))
    row["ledger_categories"] = len(ids)
    row["ledger_complete"] = ids == CATEGORIES
    k12 = next((c for c in categories if isinstance(c, dict) and c.get("id") == "K12"), None)
    row["k12_applies"] = (k12 or {}).get("applies")
    row["k12_reason"] = (k12 or {}).get("reason")
    questions = stored.get("questions") or []
    row["intake_questions"] = len(questions)
    row["k12_questions"] = [{key: q.get(key) for key in ("id", "question", "route", "default")}
                            for q in questions if isinstance(q, dict) and q.get("category") == "K12"]
    row["routes"] = {r: sum(1 for q in questions if isinstance(q, dict) and q.get("route") == r)
                     for r in ("inspect", "research", "experiment", "default", "person")}
    submitted = submitted_ledger(run, intake_row["action"]) if intake_row else {}
    row["submitted_categories"] = len(submitted.get("question_categories") or [])
    trace = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines() if line.strip()] \
        if (run / "trace.jsonl").is_file() else []
    refused = [t for t in trace if t.get("kind") == "command" and t.get("verb") in VERBS
               and t.get("exit") not in (0, None)]
    row["refusals"] = len(refused)
    row["intake_refusals"] = [(t.get("error") or "")[:160] for t in refused
                              if ((t.get("stage") or [None])[0]) == "intake"]
    row["intake_category_refusals"] = sum("question_categories" in (t.get("error") or "") for t in refused
                                          if ((t.get("stage") or [None])[0]) == "intake")
    row["send_backs"] = [{"stage": h.get("stage"),
                          "summary": str((accepted.get(h["action"]) or {}).get("summary") or "")[:160]}
                         for h in history if h.get("outcome") == "send-back"]
    return row


def rules(rows):
    a = [r for r in rows if r["arm"] == "A"]
    b = [r for r in rows if r["arm"] == "B"]
    count = lambda rs, key: sum(1 for r in rs if r.get(key))  # noqa: E731
    out = {"runs": {"A": len(a), "B": len(b)}}
    out["L1"] = {"B ledgers with all of K1-K12": count(b, "ledger_complete"), "B runs with a question_categories refusal at intake":
                 sum(1 for r in b if r.get("intake_category_refusals")),
                 "holds": count(b, "ledger_complete") >= 5 and sum(1 for r in b if r.get("intake_category_refusals")) <= 1}
    pa, pb = count(a, "pass"), count(b, "pass")
    out["L2"] = {"A pass": pa, "B pass": pb, "holds": pb >= 5 and pb >= pa - 1}
    ra, rb = mean([r.get("refusals") for r in a]), mean([r.get("refusals") for r in b])
    out["L3"] = {"A refused callbacks per run": ra, "B": rb, "holds": ra is not None and rb is not None and rb <= ra + 1.5}
    ta, tb = mean([r.get("tokens") for r in a]), mean([r.get("tokens") for r in b])
    out["L4"] = {"A mean processed tokens": ta, "B": tb, "ratio": round(tb / ta, 3) if ta and tb else None,
                 "holds": bool(ta and tb and tb <= 1.25 * ta)}
    asked = lambda r: len(r["asked_user"]) if isinstance(r.get("asked_user"), list) else (r.get("asked_user") or 0)  # noqa: E731
    asked_a = sum(asked(r) for r in a)
    asked_b = sum(asked(r) for r in b)
    blocked = [r["run"] for r in b if r.get("status") == "blocked"]
    out["L5"] = {"A asked a person": asked_a, "B asked a person": asked_b, "B blocked runs": blocked,
                 "holds": not blocked and asked_b <= asked_a}
    out["all_hold"] = all(out[k]["holds"] for k in ("L1", "L2", "L3", "L4", "L5"))
    out["descriptive"] = {
        arm: {"minutes": mean([r.get("minutes") for r in rs]), "intake seconds": mean([r.get("intake_seconds") for r in rs]),
              "intake tool calls": mean([r.get("intake_tool_calls") for r in rs]),
              "intake questions": mean([r.get("intake_questions") for r in rs]),
              "K12 applies yes": sum(1 for r in rs if r.get("k12_applies") == "yes"),
              "K12 questions": sum(len(r.get("k12_questions") or []) for r in rs)}
        for arm, rs in (("A", a), ("B", b))}
    return out


def replication(rows):
    """R2-1 (README.md, "Round 1 as read"): over the new hello runs s3 to s6, B has at least 2 more runs with a send-back than A.
    Also the pooled send-back counts over every run, descriptive only."""
    new = [r for r in rows if r["case"] == "hello" and 3 <= r["sample"] <= 6]
    runs = lambda rs, arm: [r for r in rs if r["arm"] == arm]  # noqa: E731
    with_sb = lambda rs: sum(1 for r in rs if r.get("send_backs"))  # noqa: E731
    out = {"R2 runs": {"A": len(runs(new, "A")), "B": len(runs(new, "B"))},
           "R2 runs with a send-back": {"A": with_sb(runs(new, "A")), "B": with_sb(runs(new, "B"))}}
    out["B minus A"] = out["R2 runs with a send-back"]["B"] - out["R2 runs with a send-back"]["A"]
    out["complete (4 runs a side)"] = out["R2 runs"] == {"A": 4, "B": 4}
    out["replicates"] = out["B minus A"] >= 2
    stages = {}
    for r in rows:
        for sb in r.get("send_backs") or []:
            stages.setdefault(r["arm"], {}).setdefault(sb["stage"], 0)
            stages[r["arm"]][sb["stage"]] += 1
    out["pooled (descriptive)"] = {arm: {"runs": len(runs(rows, arm)), "runs with a send-back": with_sb(runs(rows, arm)),
                                         "send-backs by stage": stages.get(arm, {})} for arm in ("A", "B")}
    return out


def markdown(rows, verdict):
    """The tables of README.md "Results": every run, then each arm's means."""
    fmt = lambda v, nd=1: "n/a" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))  # noqa: E731
    out = ["| Run | pass | minutes | tokens (M) | refused callbacks | send-backs | ledger categories | K12 | intake questions | intake s / tool calls |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tokens = None if r.get("tokens") is None else r["tokens"] / 1e6
        out.append(f"| {r['run']} | {fmt(r.get('pass'))} | {fmt(r.get('minutes'))} | {fmt(tokens)} | {fmt(r.get('refusals'))} | "
                   f"{', '.join(sb['stage'] for sb in r.get('send_backs') or []) or '-'} | {r.get('ledger_categories')} | {fmt(r.get('k12_applies'))} | {r.get('intake_questions')} | "
                   f"{fmt(r.get('intake_seconds'))} / {fmt(r.get('intake_tool_calls'))} |")
    for title, subset in (("Round 1, the registered 12-run design (samples 1 and 2; 11 finished)", [r for r in rows if r["sample"] <= 2]),
                          ("All runs, round 1 and R2 (samples 1 to 6)", rows)):
        out += ["", f"{title}:", "",
                "| Arm | runs | passed | minutes | tokens (M) | refused callbacks | runs with a send-back | intake questions | intake seconds | intake tool calls | K12 applies yes |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
        for arm in ("A", "B"):
            rs = [r for r in subset if r["arm"] == arm]
            tokens = mean([r.get("tokens") for r in rs])
            out.append(f"| {arm} | {len(rs)} | {sum(1 for r in rs if r.get('pass'))} | {fmt(mean([r.get('minutes') for r in rs]))} | "
                       f"{fmt(None if tokens is None else tokens / 1e6)} | {fmt(mean([r.get('refusals') for r in rs]), 2)} | "
                       f"{sum(1 for r in rs if r.get('send_backs'))} | {fmt(mean([r.get('intake_questions') for r in rs]))} | "
                       f"{fmt(mean([r.get('intake_seconds') for r in rs]))} | {fmt(mean([r.get('intake_tool_calls') for r in rs]))} | "
                       f"{sum(1 for r in rs if r.get('k12_applies') == 'yes')} |")
    return "\n".join(out)


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "~/e2e-runs-tl/20261101/[AB]-*"
    rows = [read(Path(p)) for p in sorted(glob.glob(os.path.expanduser(pattern))) if Path(p).is_dir()]
    verdict = rules([r for r in rows if r["sample"] <= 2])      # L1-L5 are registered over the 12-run design, not over R2's runs
    verdict["R2"] = replication(rows)
    (HERE / "scores.json").write_text(json.dumps({"rows": rows, "rules": verdict}, indent=2) + "\n")
    (HERE / "results-tables.md").write_text(markdown(rows, verdict) + "\n")
    for r in rows:
        print(f"{r['run']:26} pass={r.get('pass')} min={r.get('minutes')} status={r.get('status')} tokens={r.get('tokens')} "
              f"refusals={r.get('refusals')} cats={r.get('ledger_categories')}/{r.get('submitted_categories')} "
              f"K12={r.get('k12_applies')} q={r.get('intake_questions')} intake={r.get('intake_seconds')}s/"
              f"{r.get('intake_tool_calls')} asked={r.get('asked_user')}")
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
