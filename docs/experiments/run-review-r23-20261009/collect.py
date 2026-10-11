"""Freeze the post-batch-1011 record shapes the Run Review exporter reads (R23), as figures.json beside this script.

Two sources, nothing typed by hand:

* the seven saved runs of 2026-10-07/08 under /Users/dadleet/e2e-runs, read as a regrade at the merged harness head reads them.
  This reuses docs/experiments/batch-1011-run-review-handoff-20261009/generate.py `saved_records()`, which calls the harness's
  own read-only functions (metrics.collect, fidelity.safe_build, environment.result_block, run.outcome_class, run.folder_record)
  and starts no process and writes no file. Only the keys batch 1011 added are kept, per run: result (outcome, termination,
  environment, identity, span) and metrics (fidelity, fresh_starts, fresh_starts_unmeasured, unreported_sessions_at_least).
* the full-length examples the E2E session produced from the same merged code for keys no saved run has (a run that did not
  pass has product_at_stop; a quality phase had run on r3-checkers-sonnet only; a mixed-host run's fresh starts) and sent to
  the Run Review session on 2026-10-09; they are copied from `--examples` (a JSON file of that session's), not recomputed.

Run from the repository root:
    SHIPLOOP_PROGRESS=off python3 docs/experiments/run-review-r23-20261009/collect.py --examples <rr-examples-full.json>
Tests read figures.json, never /Users/dadleet/e2e-runs.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENERATE = HERE.parent / "batch-1011-run-review-handoff-20261009" / "generate.py"

# The example keys of the E2E session's file, and the name each is kept under.
EXAMPLES = {
    "fidelity.edits (whole, r1-battleship-sonnet)": "fidelityEditsR1Sonnet",
    "fidelity.improve_packets (r1-battleship-sonnet)": "improvePacketsR1Sonnet",
    "fidelity.improve_packets (r3-battleship-sonnet)": "improvePacketsR3Sonnet",
    "fresh_starts[] items (r3-battleship-grok-none)": "freshStartsR3GrokMeasured",
    "fresh_starts_unmeasured (r3-battleship-grok-none)": "freshStartsUnmeasuredR3Grok",
    "fresh_starts[] (r2-battleship-grok-none, mixed host)": "freshStartsR2MixedHost",
    "environment.overlap (r1-battleship-grok-none)": "overlapR1Grok",
    "environment (r2-battleship-grok-none, mixed host; start/end/environments)": "environmentR2MixedHost",
    "outcome_class examples": "outcomeClassExamples",
    "product_at_stop (code-generated against a temp worktree, checks: one pass, one fail)": "productAtStopRan",
    "product_at_stop (ran false)": "productAtStopNotRan",
}
QUALITY_KEY = "quality block (r3-checkers-sonnet, G5 committed example_block)"


def load_generate():
    spec = importlib.util.spec_from_file_location("batch1011_generate", GENERATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def saved_runs() -> dict:
    found = {}
    for name, record in load_generate().saved_records().items():
        result, metrics = record["result"], record["metrics"]
        found[name] = {
            "result": {key: result.get(key) for key in ("outcome_class", "outcome_basis", "termination", "environment",
                                                         "prompt_sha256", "host_build", "span", "identity_unmeasured", "versions")},
            "metrics": {key: metrics[key] for key in ("fidelity", "fresh_starts", "fresh_starts_unmeasured",
                                                       "unreported_sessions_at_least", "span") if key in metrics},
        }
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--examples", required=True, help="the E2E session's rr-examples-full.json")
    args = parser.parse_args()
    examples = json.loads(Path(args.examples).read_text())
    figures = {"savedRuns": saved_runs(), "examples": {}}
    for source, name in EXAMPLES.items():
        figures["examples"][name] = examples[source]
    quality = next(value for key, value in examples.items() if key.startswith(QUALITY_KEY[:20]))
    figures["examples"]["qualityBlockR3Checkers"] = quality["block"]
    (HERE / "figures.json").write_text(json.dumps(figures, indent=1, sort_keys=True) + "\n")
    print(f"wrote {HERE / 'figures.json'}: {len(figures['savedRuns'])} saved runs, {len(figures['examples'])} examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
