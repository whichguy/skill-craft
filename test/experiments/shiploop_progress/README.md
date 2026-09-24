# Clear progress reporting: two experiments

> **Historical (ShipLoop 0.23.0).** This experiment drives navigator
> protocols 1 and 2 (the `PRELUDE`/`_IMPROVE_STAGES` tables and `*-improve`
> stages), which ShipLoop 0.23.0 removed; its scripts no longer run against
> the current `skills/shiploop` package. The preregistration, evidence and
> results remain the record of what was observed. Reproduce it only from a
> checkout that predates 0.23.0.

Decision: adopt a bounded derived snapshot and a reporting cue. Keep Markdown
state and traversal authoritative, with one current action and no new progress
state. Improve continues to own its internal campaign.

## 1. State projection

The prototype passed **244 total synthetic assertions** at `ddca30d`: 116 for
protocol 1, 116 for protocol 2, and 12 cold packet/state checks.
The 30 fixtures cover initial state, a second work item, repeated/blocked/resumed
Improve, pause/halt, conditional/selected/skipped skill validation, replacement
queues, terminal completion, 1,000 queued items and repeated outcomes.
The public `next` command left each of the three cold-trial states unchanged.
See [raw checks](evidence/experiment1-results.json).

Review exposed a prototype omission: a halted node was not included in pending
stage labels. Production retains the stopped node as unfinished and includes it
in pending work, while clearly stating no action is runnable. Early prototype
review also corrected paused/blocked wording, explicit ownership/continuation
conditions and completed-item labels. One experiment assertion was narrowed:
bounded blocking reasons are useful state, so excluding all result-summary text
was too broad. Raw work-item context and evidence references stay excluded.

The source prototype and matrix are retained here. Frozen packets/state/results
for the three reporting trials are under [cold trials](evidence/cold-trials).
Result copies are archived as `accepted-results/`; empty runtime locks/inboxes
are omitted. Original packet paths remain unchanged as historical input data.
Large stress fixtures remain reproducible rather than copied into the repository.
No real product work or delivery occurred.

## 2. Fresh-context report comparison

Six fresh agents used the host default model: A received the existing packet,
B received that same packet plus the snapshot and cue. The common request asked
for a concise report of cycle position, completed/current/pending work, blockers
and what can happen next, within 180 words. Each runner could read only its
assigned packet and that case's state/result files, and write its own response.
It could not execute an action, inspect other trials, or use the oracle.

Three further fresh judges received anonymous pairs, their supplied prompts,
the [fixed oracle](evidence/truth-oracle.json) and state. Position was randomized
and balanced to include both orders (one pair swapped, two not); results were
remapped with the retained [mapping](evidence/judge-mapping.json). All six runs
and all three judge outputs completed; none were excluded.

| Criterion | A wins | B wins | Ties |
| --- | ---: | ---: | ---: |
| Task adherence | 0 | 3 | 0 |
| Factual accuracy | 0 | 3 | 0 |
| Completeness | 0 | 3 | 0 |
| Instruction following | 0 | 3 | 0 |
| Structural clarity | 0 | 3 | 0 |
| Precision | 0 | 3 | 0 |
| Conciseness | 1 | 0 | 2 |

B won **3/3 overall comparisons**; no candidate material errors were identified
in those three judgments under this rubric.
For example, baseline 3A asserted that plan improvement was “in progress” and
reassessing the plan, though the state only established an assigned action.
B distinguished assignment from observed execution and included remaining
outer work. Both variants sometimes omitted conditional/skipped skill status;
the snapshot therefore keeps that information available explicitly. Raw
[responses](evidence/response-3a.md), [judgments](evidence/judge-3.json), and
[all metrics](evidence/comparison-results.json) retain the evidence.

Mean packet-plus-report size was approximately **2,389 → 2,889 tokens**, estimated
as characters/4: about 500 extra estimated tokens (20.9% relative to A; 17.3%
using the comparison skill's larger-value denominator). This is an orientation
tradeoff, not a token-saving claim. Estimates exclude additional state-file
reads, system/tool context, reasoning and judge cost; actual usage was not measured.

**Deviation from preregistration:** individual dispatch timestamps were not
retained, so no per-variant latency comparison is valid. A batch observation is
retained, but timing is excluded from the verdict. Quality determined adoption.

## Limits and implementation decision

This is N=3, one run per variant, with host-default runners and judges. It is
directional evidence, not a compliance rate, latency benchmark or independent
model-family validation. Session names and dispatch instructions are retained as
coordinator records, not independent provider receipts or exact model-version
attestations. Judges were strict about unqualified “complete” claims;
such wording is not universally a factual error in ordinary conversation. The
candidate also retains some completion shorthand that judges did not flag.
The
stronger local evidence is the fabricated live activity in baseline 3A and the
missing outer-stage context in baseline reports. The trials did not test a long
live campaign, reporting cadence, interruptions or repeated-poll verbosity.

Experiments were frozen at `ddca30d`. Before production implementation, main
advanced to `a8b592c` with ShipLoop 0.11.0. Its effective cursor, graph, optional
branch and queue semantics are unchanged. Production is based on that newer
commit, condenses duplicated prototype wording, corrects halted pending work,
and preserves workspace plan/receipt locators. Regression tests exercise the
final renderer and workspace mode; the fresh-agent score belongs only to the
frozen prototype packets, not every subsequent wording change.

Adopt the bounded projection and cue, retain explicit conditional status, and
avoid adding counters, percentages, ETA, periodic timers or persisted progress.
A useful later trial is a real long-running Improve action with an interruption,
checking whether updates remain grounded and useful without repeating unchanged
state. That experiment is not represented as completed here.

## Reproduction

Use a detached checkout at `ddca30defddb2de092930c1173b4f3f348c54974` for the
historical prototype. Set `SHIPLOOP_PROGRESS_REPO` to its root and
`SHIPLOOP_PROGRESS_OUTPUT` to a new, nonexistent scratch directory, then run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B test/experiments/shiploop_progress/experiment1.py
```

The script refuses to replace existing output. The production unit tests are
`python3 -B test/shiploop-navigator.test.py`; they cover current semantics rather
than requiring old packet bytes. Historical packet paths are inert experiment
data; never run their printed callbacks. For a fresh model comparison, generate
new packets with usable scratch paths and use separate report-only sessions.
