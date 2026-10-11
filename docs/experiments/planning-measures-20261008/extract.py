#!/usr/bin/env python3
"""Compact extracts of recorded planning windows, for the hermetic reproduction tests of metrics.collect's `planning` block.

  python3 docs/experiments/planning-measures-20261008/extract.py [/Users/dadleet/e2e-runs]

Reads, never writes, the recorded run folders (outside the repository) and writes one JSON file per run beside this
script: the accepted rows of the planning window with their stamps, the engine's start, the Improve children and the
modification times of their bind files, the host's first event and, for the token figure, the per-call (time, output,
reasoning) rows of the window and a margin around it. Action ids are renamed a1, a2, ...; no run text is kept.
The figures the tests expect are the ones the 2026-10-05 planning-time account and the batch 1008 audit reported.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import metrics  # noqa: E402
import rollouts  # noqa: E402

RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
HERE = Path(__file__).resolve().parent
MARGIN_BEFORE, MARGIN_AFTER = 60, 600
CASES = {
    "luna-xhigh-1.21.0": ("20261005/v1210-battleship-luna-xhigh", "codex"),
    "grok-none-1.22.0": ("20261006/v1220-battleship-grok-medium-none", "grok"),
    "sonnet-1.23.0": ("20261007/v1230-battleship-sonnet", "claude"),
}


def extract(name: str, folder: str, host: str) -> dict:
    out = RUNS / folder
    run_dir = next(p.parent for p in sorted(out.rglob("state.md")) if p.relative_to(out).parts[0] not in ("home", "build"))
    state = metrics.engine_state(run_dir)
    stamps = metrics.timeline(out / "timeline.jsonl")
    first_event = min(stamps.values())
    accepted = metrics.stage_results(run_dir, state)
    rows = []
    for row in accepted:
        rows.append(row)
        if row["stage"] == "test-spec" and row["outcome"] == "done":
            break
    end = rows[-1]["t"]
    alias = {row["action"]: f"a{number}" for number, row in enumerate(rows, 1)}
    results = state.get("improve_results") or {}
    data = {"run": folder, "host": host, "started": metrics.run_started(run_dir),
            "first_event": first_event, "end": end,
            "rows": [{"action": alias[r["action"]], "stage": r["stage"], "outcome": r["outcome"], "t": r["t"]} for r in rows],
            "improve": {alias[a]: (run_dir / "improve" / f"{a}-bind.md").stat().st_mtime for a in alias if a in results}}
    if host == "grok":
        data["usage"] = [[stamps[n], e["usage"].get("output_tokens"), e["usage"].get("reasoning_tokens")]
                         for n, e in metrics.events(out / "events.jsonl")
                         if e.get("type") == "usage" and n in stamps
                         and first_event - MARGIN_BEFORE < stamps[n] <= end + MARGIN_AFTER]
    if host == "codex":
        data["rollouts"] = []
        for path in rollouts.rollout_files(out):
            found = rollouts._read(path)
            requests = {r for r, _, _, _, _ in found["tokens"]} & {c for c, _ in _compacted(path)}
            data["rollouts"] += [[t, output, reasoning, "main" if main else "sub", response in requests]
                                 for response, t, output, reasoning, main in found["tokens"]
                                 if t is not None and first_event - MARGIN_BEFORE < t <= end + MARGIN_AFTER]
    return data


def _compacted(path: Path):
    for record in rollouts._records(path):
        if record.get("type") == "compacted":
            yield (record.get("payload") or {}).get("compaction_response_id"), None


def main() -> None:
    for name, (folder, host) in CASES.items():
        data = extract(name, folder, host)
        (HERE / f"{name}.json").write_text(json.dumps(data, separators=(",", ":")) + "\n")
        print(name, len((HERE / f"{name}.json").read_text()), "bytes")


if __name__ == "__main__":
    main()
