"""E1: does environment.overlap see the runs that overlap chess run 5? Read-only."""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import environment, metrics
run = Path(sys.argv[2]); root = Path(sys.argv[3])
same = environment.overlap(run)
own = metrics.span(run / "timeline.jsonl"); own = (own["started"], own["ended"])
seen = {r["folder"] for r in same.get("runs", [])}
cross = []
for tl in root.rglob("timeline.jsonl"):
    folder = tl.parent
    if folder == run: continue
    s = metrics.span(tl); other = (s["started"], s["ended"])
    if metrics.spans_overlap(own, other):
        cross.append((str(folder.relative_to(root)), round(min(own[1], other[1]) - max(own[0], other[0])),
                      folder.parent == run.parent))
print(json.dumps({"run": str(run.relative_to(root)), "span_minutes": round((own[1]-own[0])/60,1),
  "same_parent_rule_sees": sorted(seen),
  "overlapping_anywhere": len(cross), "missed_by_rule": sum(1 for c in cross if not c[2]),
  "overlap_seconds_total": sum(c[1] for c in cross),
  "examples": sorted(cross, key=lambda c: -c[1])[:8]}, indent=1))
