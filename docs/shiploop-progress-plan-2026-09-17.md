# Clear progress in ShipLoop action packets

## Outcome and scope

Give the user a clear view of the cycle, what is recorded complete, the current
assignment, pending work and any blocker. Derive the view from `state.md`; keep
one current prompt/callback, existing graph routing, and Improve's internally
owned campaign. Work in `codex/shiploop-progress` from committed `ddca30d` and
preserve the original checkout's unrelated pending ShipLoop work.

## Prompt audit

### Q1: Who knows the progress? (information gain 0.9)

At the base, `shiploop_navigator.py:754-834` renders the effective action, latest
accepted result and a small work-item count. It does not provide a completed/
pending stage overview. The state already retains the required history and
queue. `SKILL.md:110-156` instructs execution and recovery but lacks a user-facing
progress cadence. Derive a bounded read-only snapshot; do not ask the LLM to
remember or persist a second graph position.

### Q2: What does completed mean? (information gain 0.9)

`shiploop_navigator.py:535-620` accepts all result outcomes, including `repeat`
and `blocked`, before deciding whether to advance. Only accepted `done` records
complete a stage; work-item completion has its own existing ledger. A selected
active action is not evidence that execution started. Pause, block and halt
need distinct labels. Completion remains a host declaration, not proof of test,
deployment or consumer behavior. Improve's internal iterations are absent from
script state and must stay absent.

### Q3: How much future work should be shown? (information gain 0.8)

`shiploop_navigator.py:226-238` branches after `document` and `:519-532` permits
queue replacement. Show the currently declared queue and bounded stage labels,
mark skill validation conditional until a document completion selects it, and
keep skipped separate from completed. Future status labels are context, not
additional assignments. Avoid a percentage or ETA over a changing graph.

## Evidence and options

- Adopt a derived snapshot and a concise reporting nudge. The existing state
  makes this possible without a schema or transition change.
- Pilot the cue with the [preregistered experiments](../test/experiments/shiploop_progress/preregistration.md).
- Reject a separate progress-state file, inferred Improve counters, global
  completion percentages and updates on every unchanged poll.
- Defer an auto-refreshing browser dashboard and new monitoring infrastructure;
  the requested gap is in current prompts and communication.

The [MCP progress specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress)
uses human-readable messages, allows unknown totals and recommends rate limiting.
This is design precedent, not a proposal to install an MCP server or adopt its
numeric counter. [NN/g's wait guidance](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/)
supports useful status detail during long waits. [Anthropic's long-running-agent
work](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
shows the value of durable progress and also describes premature completion
claims. Here the existing Markdown ledger already supplies continuity; another
agent-maintained progress artifact would add drift risk.

## Proposed implementation after the experiments

1. Add a pure bounded progress projection using effective protocol-1/2 state,
   accepted outcomes, current queue and graph constants. Retain phase totals,
   the current item, at most three completed and three queued titles (80 chars
   each), omitted counts and finite current-phase labels (at most 11). Keep the
   1,000-item snapshot within 2,200 characters; do not repeat raw context, summaries
   or evidence references. Do not parse prose.
2. Include it in every returned packet, including paused/blocked/halted/done,
   and reuse it in the on-demand HTML report. Keep storage/write cadence intact.
3. Prompt the host to share concise completed/current/pending/blocked updates at
   start or recovery, meaningful transitions, queue changes and material waits.
   Separate internal Improve observations from graph progress; do not invent
   work, timers, counters or evidence. Preserve host formatting discretion.
4. Extend semantic traversal and cold recovery tests; test conditional routes,
   queue changes, retries, truthful statuses, boundedness and HTML escaping.
5. Regenerate package views, lint, run focused and core checks, review independently,
   integrate only the owned change while preserving dirty work, and verify CI
   for the delivered commit. Record experiment outcomes and limitations below.

Observed checks: `python3 -B test/shiploop-navigator.test.py`,
`python3 -B test/shiploop-navigator-dry-run.test.py`,
`python3 -B skills/shiploop/scripts/shiploop graph-dry-run`,
`bash scripts/sync-plugin-views.sh --check`, `ruff check` on changed Python,
and `bash test/run-all.sh --group core` with a private temporary directory.
CI runs the three ShipLoop shards and required hermetic aggregate.

## Experiments and implementation

The [experiment report](../test/experiments/shiploop_progress/README.md) retains
the design decision, raw evidence and limitations. The state prototype passed
244 checks; the candidate won all three anonymous reporting comparisons, at an
estimated 500 additional packet-plus-report tokens per case. Timing was excluded
because individual dispatch times were not retained. This small trial supports
clearer orientation, not a general adherence or performance claim.

Main advanced to `a8b592c` (0.11.0) during the experiments. Its graph and cursor
semantics are unchanged; implementation uses that newer base and preserves its
workspace return-plan/receipt context. The production projection is read-only,
has no new state or routing, and is shared by the packet and HTML report. It
also fixes a prototype gap: the halted node remains visible as unfinished.
ShipLoop 0.11.1 carries the guidance and regression coverage. Final validation
results are recorded with the delivery response and CI for the delivered commit.

Local validation passed: 32 navigator tests, 5 graph dry-run tests, all 8 public
graph simulation routes, 25 workspace tests, the core hermetic group, Ruff,
generated-package consistency and whitespace checks. Final independent review
found no remaining source issue. A hostile-text ordering assertion caught the
HTML report's full reason appearing before the context label; the shared
snapshot now precedes that reason, and all 32 navigator tests passed again.
