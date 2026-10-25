"""E3: which top-level metrics.json blocks of a run does any reader name (run.py, which writes them, excluded)? Read-only.
usage: python3 -B e3_consumers.py <skill-craft checkout> <run folder> [extra reader folder ...]"""
import json, re, sys
from pathlib import Path
root, run = Path(sys.argv[1]), Path(sys.argv[2])
metrics = json.loads((run / "metrics.json").read_text())
readers = [root / "test/shiploop_e2e" / n for n in ("owner_page.py", "flow.py", "review.py", "progress.py", "iterate.py")]
for folder in ["skills/shiploop-run-review", "skills/shiploop-e2e-audit"]:
    readers += [p for p in (root / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".md", ".html", ".js")]
for extra in sys.argv[3:]:
    readers += list(Path(extra).glob("*.py"))
texts = {p: p.read_text(errors="ignore") for p in readers if p.exists()}
rows = []
for key, value in metrics.items():
    pattern = re.compile(r"['\"]" + re.escape(key) + r"['\"]")
    rows.append({"block": key, "bytes": len(json.dumps(value)), "readers": sorted({p.name for p, t in texts.items() if pattern.search(t)})})
unread = [r for r in rows if not r["readers"]]
print(json.dumps({"run": run.name, "blocks": len(rows), "bytes": sum(r["bytes"] for r in rows), "unread_blocks": len(unread),
                  "unread_bytes": sum(r["bytes"] for r in unread), "rows": sorted(rows, key=lambda r: -r["bytes"])}, indent=1))
