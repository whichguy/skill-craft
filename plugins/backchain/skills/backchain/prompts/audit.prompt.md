# Backchain source-aware audit — `backchain-caller/v1`

Audit a candidate Backchain plan against caller-provided original request, source snapshots, caller packet, and selected lens findings. This is an explicit native capability; do not modify plan JSON and do not claim execution, deployment, global completion, or experiment success from structural validity.

This is one read-only audit primitive. Backchain invokes it within each source-aware
convergence pass; an explicitly requested diagnostic may also use it alone. One clean
audit does not prove the whole planning invocation converged.

## Input

Caller packet:
```json
{{CALLER_PACKET_JSON}}
```

Candidate plan:
```json
{{CANDIDATE_PLAN_JSON}}
```

The original request, source snapshots, and selected lens findings may be appended as literal data after this template. Read them all. The requirements map is an index, not the completeness authority.

## Method

1. Require `backchain-caller/v1`, matching `action: review`, `stage: audit`, action ID/owner/workflow stage, declared locator bases, and existing candidate input identity. If identity is stale, missing, or rejected, return an unchanged/unresolved disposition without inventing an output hash.
2. Independently derive material obligations from original request and every available applicable source clause. Record obligations absent from `requirements` as `discovered:*` mappings/findings.
3. Treat source authority correctly: normative sources control required outcomes; descriptive sources support claims. Primary provenance/current labels do not prove adequacy. An applicable normative source that is unavailable, stale, or ambiguous leaves source review incomplete unless inspected supersession evidence is recorded.
4. Examine source-linked dependency relationships and relevant lens findings for material omitted suppliers, false edges, unsupported claims, or affected consumers. Do not invent facts or suppliers. Report as a finding each produce with no `confirm` entry, each confirmation two people could not run separately and be forced to agree on, each confirmation that checks only part of its produce, and each `unconfirmable` marker on a produce that an available check could in fact confirm or whose `by` does not name what would confirm it; revise repairs these on steps this cycle may change. A step this cycle may change is one whose exact ID is provisional in the caller `edit_bounds` and that is not running, completed, or protected; with no caller `edit_bounds`, it is any step that is not running or completed. On any other step, report them as advisory findings; they are not planning gaps or forbidden necessary repairs.
5. For every experiment bind outcome to `condition_id`, affected consumer refs, target identity/version/config, evidence receipt scope/fidelity, and result-to-plan disposition. `passed` requires evidence for that exact condition; a run alone is only `observed`; malformed result is `invalid`.
6. Classify unresolved issues into `planning_gaps` versus `execution_blockers` using the caller contract. A correctly modeled external approval may be supported planned coverage while execution remains blocked. Missing normative sources, forbidden necessary repairs, and architecture-determining unknowns remain planning gaps, never deferred execution work.
7. Respect all bounds/protected/running/completed state. Audit proposes but does not mutate.

## Output

Emit only the review object in `references/caller-contract.md`, with `action: "review"` and `stage: "audit"`. Include every indexed and independently discovered material obligation. Source review cannot be complete while a material mapping is unsupported/unaddressed/unresolved or an applicable normative source is inadequately available/current.
