#!/usr/bin/env python3
"""Copy the comparison's compact evidence from the runs root into this folder's evidence/. No model.

    python3 export.py ROOT [EVIDENCE_DIR]

Writes EVIDENCE_DIR (default: evidence/ beside this file): source.json (the checkout both arms ran from), runs.json
(each run's launch record: arm, case, command, attempts, times), measures/LABEL.json (measure.py's record of each
run), judge/ (key.json, score.json, every answer, and the sha256 and size of every packet; the packets themselves
hold the products' code and stay in the runs root), and report/ (report.py's report.json and report.md, when made).
The runs themselves (work repositories, event streams, Codex homes) stay under ROOT, outside the repository.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    root = Path(argv[0]).expanduser().resolve()
    out = Path(argv[1]).resolve() if len(argv) > 1 else HERE / "evidence"
    (out / "measures").mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "source.json", out / "source.json")
    runs = {}
    for path in sorted(root.glob("*.launch.json")):
        record = json.loads(path.read_text())
        runs[record["label"]] = record
    (out / "runs.json").write_text(json.dumps(runs, indent=1) + "\n")
    for path in sorted((root / "measure").glob("*/measures.json")):
        shutil.copy2(path, out / "measures" / f"{path.parent.name}.json")
    judge = root / "judge"
    if judge.is_dir():
        (out / "judge").mkdir(exist_ok=True)
        packets = {}
        for name in ("key.json", "score.json"):
            if (judge / name).exists():
                shutil.copy2(judge / name, out / "judge" / name)
        for folder in sorted(path for path in judge.iterdir() if path.is_dir()):
            for path in sorted(folder.glob("answer-*.json")):
                shutil.copy2(path, out / "judge" / f"{folder.name}-{path.name}")
            for path in sorted(folder.glob("packet-*.md")):
                data = path.read_bytes()
                packets[f"{folder.name}/{path.name}"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        (out / "judge" / "packets.json").write_text(json.dumps(packets, indent=1) + "\n")
    report = root / "report"
    if report.is_dir():
        (out / "report").mkdir(exist_ok=True)
        for name in ("report.json", "report.md"):
            if (report / name).exists():
                shutil.copy2(report / name, out / "report" / name)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
