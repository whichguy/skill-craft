#!/usr/bin/env python3
"""The Sonnet cost rise between the two batch runs, decomposed from the recorded run folders.

  python3 docs/experiments/batch-1007-live-20261007/cost_decomposition.py [/Users/dadleet/e2e-runs] > cost-decomposition.json

Reads, never writes, the two run folders (outside the repository, as the SPEC requires):

  old  20261006/v1220-battleship-sonnet   (238 turns, $6.54, Claude Code 2.1.291)
  new  20261007/v1230-battleship-sonnet   (294 turns, $9.65, Claude Code 2.1.292)

`inputs` is what the script reads from them (the host's own usage totals, the cost, and one number per model call);
`recomputed` is `decompose(inputs)`, so a test can rebuild every recomputed figure from the committed JSON alone
(`SonnetCostDecompositionTest` in test/shiploop-e2e.test.py). `from_the_audit` is what the batch 1008 audit derived from
the same folders with ad-hoc scripts that are NOT in the repository: per-stage growth, the packet-growth bound and the
byte counts. Those figures are labelled derived and are not recomputed here; they use the fitted rates below.

The rates are a fit, not a published price: they reproduce both sessions' `total_cost_usd` from `usage` exactly.
Status: interim (one run on each side).
"""
import json
from pathlib import Path
import sys

RUNS = {"old": "20261006/v1220-battleship-sonnet", "new": "20261007/v1230-battleship-sonnet"}
# Dollars per million tokens. Fitted: input 2, cache write (1 h) 4, cache read 0.2, output 10.
RATES = {"input_tokens": 2.0, "cache_creation_input_tokens": 4.0, "cache_read_input_tokens": 0.2, "output_tokens": 10.0}


def read_run(root: Path) -> dict:
    """What one run folder gives: the host's usage totals, its cost, and the context of each model call, in order."""
    metrics = json.loads((root / "metrics.json").read_text())
    invocation = json.loads((root / "invocation.json").read_text())
    session = metrics["sessions"][0]
    calls, seen, version = [], set(), None
    for line in (root / "events.jsonl").read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            version = event.get("claude_code_version")
        elif event.get("type") == "assistant":
            message = event["message"]
            if message.get("id") not in seen:  # one API call writes one assistant event per content block
                seen.add(message.get("id"))
                used = message.get("usage") or {}
                calls.append([used.get("cache_read_input_tokens", 0),
                              sum(used.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                           "cache_read_input_tokens"))])
    return {"folder": str(root.relative_to(root.parent.parent)),
            "claude_code_version": version, "turns": metrics["turns"], "cost_usd": session["cost_usd"],
            "usage": {k: session["usage"][k] for k in RATES},
            "versions": {k: invocation["versions"].get(k) for k in ("plugin_version", "shiploop_version", "local_head")},
            "cache_read_per_call": [c[0] for c in calls], "context_per_call": [c[1] for c in calls]}


def cost(usage: dict) -> float:
    return sum(usage[k] * RATES[k] for k in RATES) / 1e6


def decompose(inputs: dict) -> dict:
    """Every figure here is arithmetic on `inputs`: the fit, the rise by component, and the quadratic split."""
    old, new = inputs["old"], inputs["new"]
    out: dict = {}
    for name, run in (("old", old), ("new", new)):
        usage = run["usage"]
        out[name] = {"fitted_cost_usd": round(cost(usage), 7),
                     "fit_error_usd": round(abs(cost(usage) - run["cost_usd"]), 9),
                     "cache_read_share_of_cost": round(usage["cache_read_input_tokens"] * RATES["cache_read_input_tokens"]
                                                       / 1e6 / run["cost_usd"], 3),
                     "model_calls": len(run["cache_read_per_call"]),
                     "mean_context_per_call": round(sum(run["context_per_call"]) / len(run["context_per_call"])),
                     "peak_context": max(run["context_per_call"]),
                     "cache_read_tokens_summed_over_calls": sum(run["cache_read_per_call"])}
    rise = round(new["cost_usd"] - old["cost_usd"], 4)
    components = {k: round((new["usage"][k] - old["usage"][k]) * RATES[k] / 1e6, 4) for k in RATES}
    out["rise_usd"] = rise
    out["rise_by_component_usd"] = components
    # The run is one session that is never cleared: every token added is read again by every later call, so the cost
    # grows with the square of the work. Price the new run's first len(old) calls at the old run's length, and the rest apart.
    same = len(old["cache_read_per_call"])
    first, extra = new["cache_read_per_call"][:same], new["cache_read_per_call"][same:]
    increase = new["usage"]["cache_read_input_tokens"] - old["usage"]["cache_read_input_tokens"]
    out["quadratic"] = {
        "first_calls_of_the_new_run": same,
        "cache_read_tokens_of_those_calls": sum(first),
        "against_the_old_run": round(sum(first) / old["usage"]["cache_read_input_tokens"] - 1, 3),
        "extra_calls": len(extra),
        "cache_read_tokens_of_extra_calls": sum(extra),
        "cache_read_increase_tokens": increase,
        "share_of_the_increase_in_the_extra_calls": round(sum(extra) / increase, 3),
    }
    return out


# What the batch 1008 audit derived from the same folders (events.jsonl, timeline.jsonl, state.md history, the engine
# diff of the two builds) with scripts outside the repository. Not recomputed here. Cost figures use the fitted rates and
# the input side of each call only (the output count in an event is a streaming snapshot).
FROM_THE_AUDIT = {
    "status": "derived, interim (n=1 per side); not recomputed by cost_decomposition.py",
    "stage_growth_cost_rise_usd": {
        "note": "each call's context growth priced by how many later calls re-read it; design figure / the audit's reproduction",
        "spec": [0.86, 0.84], "plan": [0.32, 0.33], "static-checks": [0.16, 0.18], "implement": [0.12, 0.11],
        "intake": [0.13, None], "carry-forward": [0.07, None], "get-next-work-item": [0.065, None], "regression": [0.06, None]},
    "extra_work_seen": [
        "spec: 4 Improve review passes against 3, and a Skill load of improve (+11.3k tokens)",
        "static-checks: 3 quality-loop iterations against 2",
        "nine stages that took 1 call each in the old run took 17 calls in the new one",
        "the new run's product is larger: 26,030 to 34,983 bytes outside docs (+34%), model-authored tool-input bytes "
        "165,335 to 229,933 (+39%)",
        "the old run was not a clean baseline: 46 accepted rows including one test-refine revise (the uncounted `node --test` "
        "refusal), against 38 rows and no revise in the new run"],
    "packet_text_bound": {
        "bytes_added": "the Checked by line, 7,514 bytes over 45 packets; three duty additions, 660 bytes",
        "upper_bound_usd": "about 0.051 plus 0.007, if every added byte entered context at its stage and stayed for every later call",
        "share_of_the_rise": "at most about 2%",
        "caveat": "a bound on bytes. The behavioural effect of the new text (the Checked by line, the new duties, the "
                  "-improve.md split) is not excluded: the Checked by line reached the model in 28 tool results and was "
                  "never quoted in a tool input or assistant text, which is no proof that it changed nothing"},
    "uncontrolled_variables": [
        "the Claude Code build differs between the runs (see inputs.*.claude_code_version)",
        "both runs carry plugin_version 1.22.0 and shiploop_version 0.54.0 although their code differs (local_head differs); "
        "'same build' cannot be read from the version string",
        "the work-item decomposition differs (3 implement steps in the old first pass, 5 in the new run), unmeasured as a "
        "spread under a fixed prompt"],
}


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
    inputs = {name: read_run(root / folder) for name, folder in RUNS.items()}
    print(json.dumps({"question": "Why did the same-prompt Node Battleship run on Sonnet 5.5 cost $3.11 more on 2026-10-07 "
                                  "than on 2026-10-06?",
                      "status": "interim: one run on each side; the packet-text bound is firm, the cause is not",
                      "rates_usd_per_million_tokens": RATES, "rates_note": "fitted to both sessions' total_cost_usd, "
                      "not a published price", "inputs": inputs, "recomputed": decompose(inputs),
                      "from_the_audit": FROM_THE_AUDIT}, separators=(",", ":")))


if __name__ == "__main__":
    main()
