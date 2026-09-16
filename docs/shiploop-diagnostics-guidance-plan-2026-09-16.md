# ShipLoop diagnostic guidance plan

## Outcome and boundaries

Extend the existing implementation-quality indicator with opt-in debug
diagnostics and safe exception context. The host decides how to implement the
assignment using the target project's conventions. ShipLoop still returns one
current prompt, records completion in Markdown and traverses the same graph.
Improve retains its complete independent campaign within an assigned action.

Do not add a DAG node, result field, evidence validator, logging framework,
exception wrapper, or mandatory instrumentation of every function. This change
guides future code work; it does not add diagnostics to every existing product.

## Prompt audit and decisions

| Question | Current evidence and decision |
| --- | --- |
| Where must a cold context receive the rule? | `IMPLEMENTATION_QUALITY` in `shiploop_navigator_prompts.py` already reaches 12 planning, implementation, testing and review stages. Extend that shared block and keep its existing indicator. |
| What is missing? | Existing prompts require actionable errors and observable diagnostics, but do not select before/after state, debug behavior or pre-cleanup failure snapshots. Add explicit criteria and stage duties. |
| Does “all state in the message” help? | Unbounded dumps can expose secrets, hide useful detail and add overhead. Capture bounded, relevant, stable context; keep public messages audience-appropriate and correlate internal details where useful. |
| Which information survives with debug off? | Essential failure context and the original error remain available. Only verbose before/after tracing is opt-in. Diagnostics must not mask a primary failure. |
| Does a new rule require new traversal? | No. Existing prompt flags, one callback, protocol state and Improve ownership suffice. Fix the implementation duty's “both criteria” wording to encompass the expanded criteria. |
| What proves delivery? | Existing two-work-item and cold-CLI tests inspect semantic prompt anchors across both protocols. They prove packet delivery and unchanged state behavior, not universal model compliance or a target application's logging quality. |

Recommendations were checked against the
[OWASP logging guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html),
[OWASP error handling guidance](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)
and [OpenTelemetry exception guidance](https://opentelemetry.io/docs/specs/otel/trace/exceptions/).
These support relevant context, correlation, redaction and preserving useful
failures; they do not require adopting OpenTelemetry or another dependency.

## Execution sequence

1. Extend the shared criteria. Reuse logger/debug controls; emit bounded,
   redacted, correlated before/after summaries at selected major actions. Avoid
   expensive construction with debug off. Snapshot safe relevant values at
   failure detection before cleanup/mutation. Preserve original cause and
   traceback internally, redact emitted exception details, and prevent diagnostic
   failures from masking the original error.
2. Make `step-plan` select actions, fields, controls and expected observations;
   make `step-plan-improve` challenge their adequacy. Carry all criteria into
   delegated implementation. Refine tests for debug on/off, stable snapshots,
   redaction, causal preservation and diagnostic failures. Document controls and
   field meanings only where useful.
3. Update the skill contract and navigator reference, release as patch 0.10.2,
   and regenerate plugin views from canonical sources in the isolated worktree.
4. Extend existing prompt-delivery assertions without whole-prompt byte
   comparisons. Run both-protocol traversal, cold recovery and graph dry-runs;
   prove a missing diagnostic directive fails its targeted check. Run lint,
   package parity and core checks. Obtain independent review of the final diff.
5. Integrate only this change into main while preserving concurrent uncommitted
   work, push under existing authorization, and verify CI for the delivered SHA.

## Verification and learning limits

Commands: `python3 -B test/shiploop-navigator.test.py`,
`python3 -B test/shiploop-navigator-dry-run.test.py`,
`python3 -B skills/shiploop/scripts/shiploop graph-dry-run`,
`ruff check skills/shiploop/scripts/shiploop_navigator_prompts.py test/shiploop-navigator.test.py`,
`bash scripts/sync-plugin-views.sh --check`, and
`bash test/run-all.sh --group core` (private `TMPDIR` for hermetic temporary files).
The repository CI runs the complete ShipLoop group and aggregate gate.

Packet checks establish that the guidance reaches the responsible stage after a
cold restart. A host must still choose proportionate instrumentation and verify
the actual changed code; synthetic traversal completion is not proof that any
software implementation fulfills the guidance. Keep any measured observations
separate from illustrative examples and do not claim unmeasured token savings.
