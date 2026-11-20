#!/usr/bin/env python3
"""Review yield from ShipLoop's own pass log (run/improve/<action>/passes.md), finished current-era runs.
Per reviewed stage: reviews, share whose passes edited anything (tree or result), lines edited, seconds.
Also writes samples.jsonl: one row per review that edited something, with the review's own Found/Changed text."""
import collections
import json
import pathlib
import re
import statistics
import sys

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"] and r["done"]]
out = pathlib.Path(sys.argv[2])
stats = collections.defaultdict(list)
samples = []
with_log = 0
modes = collections.Counter()
for run in runs:
    rundir = pathlib.Path(run["trace"]).parent
    try:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", (rundir / "state.md").read_text(), re.DOTALL).group(1))
        run["planning_review"] = state.get("planning_review")
    except (OSError, ValueError, AttributeError, KeyError):
        run["planning_review"] = None
    modes[str(run["planning_review"])] += 1
    logs = sorted((rundir / "improve").glob("nav-*/passes.md"))
    with_log += bool(logs)
    for log in logs:
        rows = []
        for line in log.read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 8 and cells[1].isdigit():
                rows.append({"stage": cells[0], "pass": int(cells[1]), "label": cells[2], "tree": cells[3] == "y",
                             "result": cells[4] == "y", "edited": cells[5] == "y",
                             "lines": int(cells[6]) if cells[6].isdigit() else 0,
                             "seconds": float(cells[7]) if re.fullmatch(r"[\d.]+", cells[7]) else 0.0})
        if not rows:
            continue
        stage = rows[0]["stage"]
        record = {"stage": stage, "passes": len(rows), "edited": any(r["edited"] for r in rows),
                  "tree": any(r["tree"] for r in rows), "result": any(r["result"] for r in rows),
                  "nontrivial": any(r["label"] != "trivial" for r in rows),
                  "lines": sum(r["lines"] for r in rows), "seconds": sum(r["seconds"] for r in rows),
                  "host": run.get("host"), "case": run.get("case")}
        stats[stage].append(record)
        if record["edited"] or record["nontrivial"]:
            texts = []
            for row in rows:
                if row["label"] == "trivial" and not row["edited"]:
                    continue
                review = log.parent / "reviews" / f"review-{row['pass']}.md"
                if review.exists():
                    body = review.read_text(errors="replace").split("## Handoff")[0]
                    keep = [l for l in body.splitlines() if re.match(r"(Found|Changed|Class|Checked):", l)]
                    texts.append({"pass": row["pass"], "label": row["label"], "tree_changed": row["tree"],
                                  "result_changed": row["result"], "lines": row["lines"], "text": "\n".join(keep)[:3500]})
            samples.append({"id": f"{len(samples) + 1:04d}", "stage": stage, "case": run.get("case"), "host": run.get("host"),
                            "lines": record["lines"], "passes": texts, "dir": str(log.parent)})
print(f"finished runs {len(runs)}; with a pass log {with_log}; planning_review values {dict(modes)}")
print(f"{'reviewed stage':<20}{'reviews':>8}{'edited':>8}{'non-trivial':>12}{'tree':>6}{'result':>8}{'median lines when edited':>26}{'median s':>10}{'mean s':>8}{'time in no-edit reviews':>25}")
total = idle = 0.0
for stage, group in sorted(stats.items(), key=lambda kv: -len(kv[1])):
    n = len(group)
    edited = [g for g in group if g["edited"]]
    seconds = sum(g["seconds"] for g in group)
    quiet = sum(g["seconds"] for g in group if not g["edited"])
    total += seconds; idle += quiet
    print(f"{stage:<20}{n:>8}{len(edited) / n:>8.0%}{sum(g['nontrivial'] for g in group) / n:>12.0%}"
          f"{sum(g['tree'] for g in group) / n:>6.0%}{sum(g['result'] for g in group) / n:>8.0%}"
          f"{statistics.median([g['lines'] for g in edited]) if edited else 0:>26.0f}"
          f"{statistics.median([g['seconds'] for g in group]):>10.0f}{seconds / n:>8.0f}{quiet / seconds if seconds else 0:>24.0%}")
print(f"all reviews: {sum(len(g) for g in stats.values())}; review seconds in reviews that edited nothing: {idle / total:.0%}")
out.write_text("\n".join(json.dumps(s) for s in samples) + "\n")
by = collections.Counter(s["stage"] for s in samples)
print("reviews that edited something or had a non-trivial pass (written to samples):", dict(by))
