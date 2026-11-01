#!/usr/bin/env python3
"""Read the runs of replication R3 (README.md) and apply its registered rules.

Arm A = ShipLoop at the pinned base with the K12 change reverted, arm B = the pinned base; the case is shared-expenses, Codex
gpt-6.1-terra at high.  Per run the reader of the first A/B (../terms-line-live-ab-20261101/e2e_ab.py, `read`) supplies the verdict,
minutes, tokens, refused callbacks, send-backs (stage and summary), the stored intake ledger and the plugin tree digest; this file adds
the number of implement stages and the failed product checks, then applies R3-1 to R3-3, the arm check S1 and the delivery and cost
rules C1 to C3, and prints the missing-run sensitivity.  Writes scores.json and results-tables.md beside this file.
Usage: r3_reader.py [GLOB, default ~/e2e-runs-r3/20261101/[AB]-shared-expenses-s*]
"""
import glob
import json
import os
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "terms-line-live-ab-20261101"))
import e2e_ab  # noqa: E402

RUNS_PER_ARM = 10


def fisher_greater(a, n_a, b, n_b):
    """Exact one-sided p that arm B has at least b of the a + b runs with a send-back, if both arms had one rate."""
    k = a + b
    total = comb(n_a + n_b, k)
    return sum(comb(n_b, x) * comb(n_a, k - x) for x in range(b, min(n_b, k) + 1)) / total


def read(out):
    row = e2e_ab.read(out)
    result = json.loads((out / "result.json").read_text()) if (out / "result.json").is_file() else {}
    metrics = json.loads((out / "metrics.json").read_text()) if (out / "metrics.json").is_file() else {}
    row["implement_stages"] = sum(1 for s in metrics.get("stages") or [] if s.get("stage") == "implement")
    checks = result.get("checks")
    row["checks_failed"] = [c.get("command") for c in checks if isinstance(c, dict) and not c.get("passed", c.get("pass", True))] \
        if isinstance(checks, list) else None
    return row


def sends(rows):
    return sum(1 for r in rows if r.get("send_backs"))


def verdict(rows):
    a = [r for r in rows if r["arm"] == "A"]
    b = [r for r in rows if r["arm"] == "B"]
    out = {"runs": {"A": len(a), "B": len(b)}, "runs with a send-back": {"A": sends(a), "B": sends(b)}}
    p = fisher_greater(sends(a), len(a), sends(b), len(b)) if a and b else None
    out["one-sided exact p (B higher)"] = None if p is None else round(p, 4)
    out["R3-1 the excess repeats"] = bool(p is not None and p <= 0.05)
    out["R3-2 leaning, register a further round"] = bool(p is not None and 0.05 < p <= 0.20 and sends(b) > sends(a))
    out["R3-3 no excess seen"] = not out["R3-1 the excess repeats"] and not out["R3-2 leaning, register a further round"]
    # Missing or unscored runs, counted in the way worst for each reading (RUNS_PER_ARM a side were registered).
    miss_a, miss_b = max(0, RUNS_PER_ARM - len(a)), max(0, RUNS_PER_ARM - len(b))
    worst_null = fisher_greater(sends(a) + miss_a, RUNS_PER_ARM, sends(b), RUNS_PER_ARM)       # missing A runs have a send-back, missing B none
    worst_excess = fisher_greater(sends(a), RUNS_PER_ARM, sends(b) + miss_b, RUNS_PER_ARM)     # missing B runs have a send-back, missing A none
    out["sensitivity"] = {"missing": {"A": miss_a, "B": miss_b},
                          "p if the missing runs favour the null": round(worst_null, 4),
                          "p if the missing runs favour the excess": round(worst_excess, 4)}
    stages = {}
    for r in rows:
        for sb in r.get("send_backs") or []:
            stages.setdefault(r["arm"], {}).setdefault(sb["stage"], 0)
            stages[r["arm"]][sb["stage"]] += 1
    out["send-backs by stage"] = stages
    plugins = {arm: sorted({r.get("plugin_sha256") for r in rs}) for arm, rs in (("A", a), ("B", b))}
    leaks = [r["run"] for r in rows if not (r.get("ledger_categories") == (12 if r["arm"] == "B" else 11))]
    out["S1 the arms differ as designed"] = {
        "plugin tree digests": plugins, "one digest per arm and they differ": all(len(v) == 1 for v in plugins.values())
        and plugins["A"] != plugins["B"], "runs whose stored intake ledger has the wrong number of categories": leaks,
        "holds": all(len(v) == 1 for v in plugins.values()) and plugins["A"] != plugins["B"] and not leaks}
    out["C1 delivery"] = {"A pass": sum(1 for r in a if r.get("pass")), "B pass": sum(1 for r in b if r.get("pass"))}
    out["C1 delivery"]["holds"] = out["C1 delivery"]["B pass"] >= 8 and out["C1 delivery"]["B pass"] >= out["C1 delivery"]["A pass"] - 1
    ta, tb = e2e_ab.mean([r.get("tokens") for r in a]), e2e_ab.mean([r.get("tokens") for r in b])
    out["C2 tokens"] = {"A mean processed": ta, "B": tb, "ratio": round(tb / ta, 3) if ta and tb else None,
                        "holds": bool(ta and tb and tb <= 1.25 * ta)}
    ra, rb = e2e_ab.mean([r.get("refusals") for r in a]), e2e_ab.mean([r.get("refusals") for r in b])
    out["C2 refused callbacks"] = {"A per run": ra, "B per run": rb, "holds": ra is not None and rb is not None and rb <= ra + 1.5}
    asked = lambda r: len(r["asked_user"]) if isinstance(r.get("asked_user"), list) else (r.get("asked_user") or 0)  # noqa: E731
    blocked = [r["run"] for r in b if r.get("status") == "blocked"]
    out["C3 no stop for a person"] = {"A asked": sum(asked(r) for r in a), "B asked": sum(asked(r) for r in b),
                                      "B blocked runs": blocked,
                                      "holds": not blocked and sum(asked(r) for r in b) <= sum(asked(r) for r in a)}
    out["descriptive"] = {arm: {"minutes": e2e_ab.mean([r.get("minutes") for r in rs]),
                                "implement stages": e2e_ab.mean([r.get("implement_stages") for r in rs]),
                                "intake questions": e2e_ab.mean([r.get("intake_questions") for r in rs]),
                                "K12 applies yes": sum(1 for r in rs if r.get("k12_applies") == "yes"),
                                "K12 questions": sum(len(r.get("k12_questions") or []) for r in rs)}
                          for arm, rs in (("A", a), ("B", b))}
    return out


def markdown(rows):
    fmt = lambda v, nd=1: "n/a" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))  # noqa: E731
    lines = ["| Run | pass | minutes | tokens (M) | implement stages | refused callbacks | send-backs (stage: summary) | failed checks |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tokens = None if r.get("tokens") is None else r["tokens"] / 1e6
        sbs = "; ".join(f"{sb['stage']}: {sb['summary'][:90]}" for sb in r.get("send_backs") or []) or "-"
        failed = ", ".join(str(c).split("expense_service.py")[-1].strip('" ') for c in r.get("checks_failed") or []) or "-"
        lines.append(f"| {r['run']} | {fmt(r.get('pass'))} | {fmt(r.get('minutes'))} | {fmt(tokens)} | {fmt(r.get('implement_stages'))} | "
                     f"{fmt(r.get('refusals'))} | {sbs} | {failed} |")
    lines += ["", "| Arm | runs | passed | runs with a send-back | minutes | tokens (M) | refused callbacks | implement stages | K12 applies yes |",
              "|---|---|---|---|---|---|---|---|---|"]
    for arm in ("A", "B"):
        rs = [r for r in rows if r["arm"] == arm]
        tokens = e2e_ab.mean([r.get("tokens") for r in rs])
        lines.append(f"| {arm} | {len(rs)} | {sum(1 for r in rs if r.get('pass'))} | {sends(rs)} | "
                     f"{fmt(e2e_ab.mean([r.get('minutes') for r in rs]))} | {fmt(None if tokens is None else tokens / 1e6)} | "
                     f"{fmt(e2e_ab.mean([r.get('refusals') for r in rs]), 2)} | {fmt(e2e_ab.mean([r.get('implement_stages') for r in rs]))} | "
                     f"{sum(1 for r in rs if r.get('k12_applies') == 'yes')} |")
    return "\n".join(lines)


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "~/e2e-runs-r3/20261101/[AB]-shared-expenses-s*"
    rows = [read(Path(p)) for p in sorted(glob.glob(os.path.expanduser(pattern))) if Path(p).is_dir()]
    rows.sort(key=lambda r: (r["arm"], r["sample"]))
    result = verdict(rows)
    (HERE / "scores.json").write_text(json.dumps({"rows": rows, "rules": result}, indent=2) + "\n")
    (HERE / "results-tables.md").write_text(markdown(rows) + "\n")
    for r in rows:
        print(f"{r['run']:24} pass={r.get('pass')} min={r.get('minutes')} status={r.get('status')} tokens={r.get('tokens')} "
              f"impl={r.get('implement_stages')} refusals={r.get('refusals')} send_backs={[sb['stage'] for sb in r.get('send_backs') or []]} "
              f"cats={r.get('ledger_categories')}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
