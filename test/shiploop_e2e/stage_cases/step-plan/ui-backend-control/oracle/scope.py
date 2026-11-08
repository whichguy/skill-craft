"""Narrow scope proxy: planned paths must not select the protected presentation files."""
import json, os, pathlib
if "STAGE_RESULT" not in os.environ:
    raise SystemExit("No accepted stage result is available.")

r=json.loads(pathlib.Path(os.environ["STAGE_RESULT"]).read_text())
paths=[p for step in r.get("steps",[]) for p in step.get("paths",[])]
if not paths:
    raise SystemExit("No planned paths to assess")
if any(p.startswith("assets/") or p == "docs/shiploop/architecture.md" for p in paths):
    raise SystemExit("Presentation work added to a pagination repair")
