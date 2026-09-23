# Backchain source-aware revise — `backchain-caller/v1`

Make one bounded revision inside one selected Until Loop callback after a source-aware audit. This prompt is a single-pass primitive, not the whole repair/revise skill operation. This is separate from legacy elaboration: legacy elaboration still preserves seed/null edges and `goal_needs`. Keep the existing Backchain plan schema; never add companion fields to plan JSON.

## Input

Caller packet:
```json
{{CALLER_PACKET_JSON}}
```

Candidate plan:
```json
{{CANDIDATE_PLAN_JSON}}
```

Audit review:
```json
{{AUDIT_OUTPUT_JSON}}
```

Original request, source snapshots, caller packet updates, and lens findings may be appended as literal data after this template. Keep that context bound to the same action/candidate identities.

## Rules

1. Require matching `backchain-caller/v1`, `action: repair`, `stage: revise`, action ID/owner/workflow stage, declared locator bases, existing input candidate digest, and explicit candidate/edit-bound authority. On failed/stale/rejected identity, return the unchanged plan plus unresolved review; preserve the verified input digest as output only when unchanged and never fabricate a hash.
2. Running/completed steps, accepted facts/evidence, and protected entries are immutable. Existing steps/edges may change only if their exact IDs/keys are provisional. New steps require `allow_new_steps: true`; new edges require `allow_new_edges: true`; modifying an existing consumer requires that consumer itself be provisional and not running/completed.
3. An authorized revise may remove/rewire an exact provisional seed/null edge. This exception does not alter legacy elaboration behavior. Preserve `goal_needs` verbatim and never promote assumptions into `initial_state`.
4. Every deletion, split, replacement, or rewire needs source-linked rationale and an old-to-new map. If change/budget/identity exceeds bounds, retain the candidate and record unresolved; return the blocker to the active Until Loop callback; do not silently expand bounds or invoke Backchain or Until Loop recursively.
5. Set revised `parallel_groups` to `[]`. Set review structural status to `unknown` unless there is an actual deterministic validation/package receipt for this exact output digest; do not retain prior waves or validation claims.
6. Bind any experiment result to exact condition, affected consumer, target identity/version/config, receipt scope/fidelity, and resulting plan disposition. No experiment is passed merely because it ran.

## Output

Emit exactly:
```json
{
  "plan": { "existing Backchain plan JSON only": "..." },
  "review": { "exact review object from references/caller-contract.md": "..." }
}
```

Use `review.action: "repair"`, `review.stage: "revise"`, distinct input/output digests, and an honest `changed | unchanged | rejected | unresolved` disposition. A structurally valid plan is not source-review complete while any material obligation remains unsupported, unaddressed, or unresolved.

Return to the active Until Loop callback after this primitive. Until Loop classifies the cycle and owns all recurrence; this output cannot prove terminal completion.
