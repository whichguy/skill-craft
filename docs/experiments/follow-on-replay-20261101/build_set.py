"""Build the replay set for M1 of the follow-on design (docs/shiploop-follow-on-run-design-2026-10-31.md, section 7).

The set is the 25 strict rows of the 2026-10-31 peek (frozen: ../follow-on-peek-20261031/peek.json and its
classification.json) plus every strict row of a finished run that is not in that snapshot: runs under the experiment
roots the peek skipped (-xr, -s7, -pf, -multipass and the roots added since) and runs finished under ~/e2e-runs after the
snapshot.  Each row carries its full ``Open for the next run`` text and the id of its request; each request is stored once
as its numbered sentences (the ``request.md`` of the run).

Row ids: F01..F25 are the frozen rows in the peek's order; N1..N7 are the new rows in run-label order.  No label of any
reader is stored here.  Usage: ``python3 -B build_set.py [--out rows.json]``; the archives live outside the repository
(``~/e2e-runs*``), so the command reproduces only on the owner's machine.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PEEK_DIR = HERE.parent / "follow-on-peek-20261031"


def load_peek():
    spec = importlib.util.spec_from_file_location("peek", PEEK_DIR / "peek.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["peek"] = module
    spec.loader.exec_module(module)
    return module


def request_sentences(run_dir: Path) -> list[tuple[int, str]]:
    text = (run_dir / "request.md").read_text(encoding="utf-8")
    return [(int(number), sentence) for number, sentence in re.findall(r"^- S(\d+): (.*)$", text, re.MULTILINE)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=str(HERE / "rows.json"))
    args = parser.parse_args()
    peek = load_peek()
    home = os.path.expanduser("~")

    snapshot = json.loads((PEEK_DIR / "peek.json").read_text(encoding="utf-8"))
    classification = json.loads((PEEK_DIR / "classification.json").read_text(encoding="utf-8"))
    frozen = snapshot["strict"]
    assert [row["run"] for row in frozen] == [entry["run"] for entry in classification["entries"]], "classification is stale"
    frozen_runs = {row["run"] for row in snapshot["rows"]}

    new = []
    for root in sorted(glob.glob(home + "/e2e-runs*")):
        for path in sorted(glob.glob(root + "/**/.shiploop-runs/*/run/state.md", recursive=True)):
            if "/test/fixtures/" in path or "/slice/" in path:
                continue
            run_dir = Path(path).parent
            row = peek.read_run(run_dir)
            if row is None or row["run"] in frozen_runs or not row["has_release_verify"] or row["open_next"] is None:
                continue
            text = row["open_next"]
            if text.strip().lower() in peek.LOOSE_NONE or peek.STRICT_NONE.match(text):
                continue
            new.append({"run": row["run"], "root": Path(root).name, "handoff": row["handoff"], "text": text})
    new.sort(key=lambda row: row["run"])

    rows, requests, by_hash = [], {}, {}
    entries = [(f"F{number:02d}", "frozen", row) for number, row in enumerate(frozen, 1)]
    entries += [(f"N{number}", "new:" + row["root"], row) for number, row in enumerate(new, 1)]
    for row_id, stratum, row in entries:
        run_dir = Path(row["run"].replace("~", home))
        sentences = request_sentences(run_dir)
        key = hashlib.sha256("\n".join(f"{n}:{s}" for n, s in sentences).encode("utf-8")).hexdigest()
        if key not in by_hash:
            by_hash[key] = f"R{len(by_hash) + 1:02d}"
            requests[by_hash[key]] = [{"s": n, "text": s} for n, s in sentences]
        rows.append({"id": row_id, "stratum": stratum, "run": row["run"], "request": by_hash[key],
                     "handoff": row.get("handoff", True), "text": row["text"]})
    out = {"snapshot": "docs/experiments/follow-on-peek-20261031/peek.json (125 runs, 2026-10-31)",
           "frozen_rows": len(frozen), "new_rows": len(new), "rows": rows, "requests": requests}
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows ({len(frozen)} frozen, {len(new)} new); {len(requests)} distinct requests -> {args.out}")
    for row in rows[len(frozen):]:
        print(f"  {row['id']} [{row['stratum']}] handoff={row['handoff']} {row['run']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
