# Source-aware native caller contract — `backchain-caller/v1`

This optional native capability keeps the existing Backchain plan JSON and schema unchanged. It is selected only when a host prepares an original-request/source companion packet for a request that needs source/spec verification. Normal native Backchain remains available without it.

## Scope and authority

The unedited `original_request` and applicable source clauses are the completeness authorities. `requirements` is an indexing aid, never a complete or controlling specification. An auditor independently reads the original request and each available source clause to discover material obligations absent from that index.

A source's `authority` describes its role: `normative` controls required outcomes; `descriptive` supports factual claims; `mixed` does both. `provenance` (`primary`, `repository`, `user-provided`, etc.) and a `current` label are descriptive metadata, not automatic proof that a source is adequate, applicable, or correct.

Source/caller metadata and review findings are companion artifacts. They must never be added to the plan JSON. Record the mode/interface outside the plan.

## Packet

The host provides one caller-owned packet, rendered as data to every selected template. Relative locators resolve against the declared `locator_base`; actual observed absolute locators are allowed. Reusable prompts must not hardcode author-machine paths.

```json
{
  "interface": "backchain-caller/v1",
  "action": "plan | review | repair",
  "stage": "draft | audit | revise",
  "action_id": "caller-generated stable action identity",
  "owner": "host or workflow identity responsible for this action",
  "workflow_stage": "standalone | shiploop:plan | shiploop:step-plan | caller-defined actual stage",
  "locator_bases": [{ "id": "caller-root", "observed_absolute_locator": "/actual/root" }],
  "original_request": "unedited request including source clauses",
  "selection": { "skill_locator": "path", "skill_sha256": "hex or unavailable" },
  "candidate": {
    "id": "string",
    "input_kind": "existing | new-draft",
    "locator": "relative or observed absolute path",
    "locator_base": "locator_bases[].id or URL base",
    "resolved_locator": "observed resolved path or unavailable",
    "input_sha256": "candidate bytes before action | unavailable only for new-draft",
    "output_sha256": "serialized candidate bytes after action or unavailable"
  },
  "sources": [
    {
      "id": "SRC-1",
      "locator": "relative path, observed absolute path, or stable URL",
      "locator_base": "locator_bases[].id or URL base",
      "resolved_locator": "observed resolved path or unavailable",
      "authority": "normative | descriptive | mixed | unknown",
      "provenance": "primary | user-provided | repository | derived | unknown",
      "currentness": "current | dated | unknown",
      "revision": "version, commit, timestamp, or unknown",
      "sha256": "hex or unavailable",
      "excerpt": "optional bounded excerpt",
      "superseded_by": "SRC-id only after inspected supersession evidence"
    }
  ],
  "requirements": [{ "id": "R-1", "text": "verbatim indexed obligation", "source_ids": ["SRC-1"] }],
  "lens_findings": [{ "lens": "name", "trigger": "observed applicability", "question": "dependency question" }],
  "dependency_neighborhood": { "included_step_ids": ["S1"], "included_edge_keys": ["S2<-S1"] },
  "evidence": [{ "id": "E-1", "claim": "observed fact", "source_ids": ["SRC-1"], "verified": true }],
  "open_questions": ["unknown that can change coverage or a relationship"],
  "edit_bounds": {
    "provisional_step_ids": ["D1"],
    "provisional_edge_keys": ["S3<-D1"],
    "allow_new_steps": false,
    "allow_new_edges": false,
    "protected_step_ids": ["S1"],
    "protected_edge_keys": ["S2<-S1"],
    "protected_facts": ["accepted fact"],
    "running_or_completed_step_ids": ["S4"]
  },
  "prior_findings": []
}
```

`locator_bases` records the actual observed absolute roots used to resolve every relative locator; do not infer a base from the selected skill root or current working directory. A `new-draft` has no existing candidate input and may use `input_sha256: "unavailable"`; after serialization it records its observed output digest. Audit/revise require an existing input candidate. If existing candidate identity, action binding, resolved base, or required source identity is stale, missing, or rejected, return an honest unchanged/rejected disposition with `output_sha256` equal to the verified input digest when available, and record the issue unresolved. Never invent a replacement hash.

An applicable normative source that is unavailable, stale, or ambiguous forces `source_review_status: "incomplete"`, unless the reviewer inspected and recorded adequate supersession evidence. No obligation discovered from it is required to disappear merely because its content is inaccessible.

## Selected Until Loop binding

Whole-skill `plan/draft` and `repair/revise` always bind the
frozen candidate to the selected actual Until Loop card under
`references/convergence.md`. Include this marker in the child request:

```text
Backchain standalone Until Loop binding: <binding-id>
```

Resolve and read in full the selected Until Loop `SKILL.md` and its package-relative
`references/runtime-ephemeral.md`, then retain absolute observed locators for them and the
ephemeral runtime script. The child scope is plan artifacts and their permitted companion evidence only:
preserve original request, sources, lenses, action/action ID/owner/workflow stage,
candidate identity, all edit bounds, and parent request/latest-packet/return-route/printed
terminal-receipt locators in `context.resources`; do not commit, push, merge, execute the
project, or broaden scope. Until Loop is the sole counter,
resume/recovery, resource/stop, and terminal authority. Authorized in-scope revisions and
new evidence are recorded in reports/handoffs and remain in the same run; their material
classification resets Until Loop's gate. Only an external/unapproved baseline substitution,
changed request/scope/bounds, or newer contradictory governing source uses existing
cancel/rebind behavior; no state is carried into that changed binding. Backchain must not inject a `max_passes`, derive pass IDs/streaks, or run a
parallel controller.

A source-aware child uses audit/revise only as Backchain primitives within one Until Loop callback. Legacy elaboration remains separate and preserves inherited seed/null edges,
`goal_needs`, and step `confirm` entries; an authorized revise may remove or rewire only exact provisional edges
and carries each `confirm` entry to any produce text it rewrites.
An explicit `review/audit` stays read-only and never starts the Until Loop binding.

Final `{plan, review}` restores outer caller action/stage/ID and original input identity,
records actual final output digest and final source assessment, and stores an opaque
`review.convergence` binding record. It may say converged planning only with the exact
Until Loop terminal `complete` receipt plus candidate-specific domain evidence. Missing or
stale selection/candidate/source/bounds resources, `blocked`/`stopped`/cancelled Until Loop,
or absent domain evidence is incomplete. Do not infer terminal state from copied text,
structural validity, or a model-written count.
Preserve access to both original qualifying review records since the run began or latest
reset, whichever is later, and their observed identities in the final handoff/domain
evidence under `references/convergence.md`; a
terminal receipt with only the latest review recoverable is incomplete planning.

## Operations

### `plan` / `draft`

The host gives the generator the original request plus selected source snapshots as `RAW_PROMPT` data and retains the same packet/lens findings for dependency review and elaboration. Return `{ "plan": <existing Backchain plan>, "review": <review object> }`. Backchain always binds the enriched candidate to selected Until Loop and returns the final source assessment with its opaque `review.convergence` record, or an honest incomplete result. It does not self-certify execution or structural validity.

### `review` / `audit`

Compare the candidate against the original request, source clauses, indexed map, selected technical lenses, and relevant dependency neighborhood. Find material omitted obligations, missing suppliers, false relationships, unsupported claims, source inadequacy, and stale identities. Do not mutate plan JSON, invent facts, or treat a listed requirement map as exhaustive. Return the review object only. This explicit diagnostic does not run repairs or establish planning convergence; label convergence `not_evaluated` outside the plan if reporting it.

### `repair` / `revise`

This is separate from legacy elaboration. Legacy elaboration continues to preserve inherited seed/null edges and `goal_needs`. An authorized revise may remove or rewire an exact provisional edge only within explicit bounds.

Running/completed steps are always protected. Accepted facts/evidence and listed protected items remain protected. Existing items may change only if their exact ID/key is provisional. New steps require `allow_new_steps: true`; new edges require `allow_new_edges: true`; adding/changing an edge to an existing consumer also requires that consumer to be provisional and not running/completed. Each removal, split, replacement, or rewire needs an old-to-new mapping and source-linked reason. An active selected Until Loop callback may apply authorized revisions through the one-revision `prompts/revise.prompt.md`; Until Loop classifies cycles and owns recurrence. A blocked or out-of-bounds necessary repair stays incomplete.

A revised plan must emit `parallel_groups: []`. Set `structural_plan_status: "unknown"` until an actual deterministic packaging/validation receipt for this exact `output_sha256` is recorded; never carry stale waves or structural status forward.

## Review object

Draft and revise return `{ "plan", "review" }`; a whole selected Until Loop binding may add the opaque convergence record in `review.convergence`. Audit returns only `review` without a successful convergence claim. The shared single-pass review shape below is also used by audit/revise primitives; it does not show that the whole skill finished.

```json
{
  "interface": "backchain-caller/v1",
  "action": "plan | review | repair",
  "stage": "draft | audit | revise",
  "action_id": "same caller action identity",
  "owner": "caller action owner",
  "workflow_stage": "actual standalone or workflow stage",
  "locator_bases": [{ "id": "caller-root", "observed_absolute_locator": "/actual/root" }],
  "candidate": {
    "id": "string", "input_kind": "existing | new-draft", "locator": "path", "locator_base": "locator_bases[].id",
    "resolved_locator": "path or unavailable", "input_sha256": "hex or unavailable",
    "output_sha256": "hex or unavailable", "disposition": "changed | unchanged | rejected | unresolved"
  },
  "sources_inspected": [{
    "id": "SRC-1", "authority": "normative", "provenance": "primary",
    "currentness": "current", "revision": "string", "sha256": "hex or unavailable",
    "resolved_locator": "path or unavailable", "disposition": "used | unavailable | stale | ambiguous | inadequate | superseded"
  }],
  "requirement_map": [{
    "requirement_id": "R-1 | discovered:stable-id", "source_ids": ["SRC-1"],
    "disposition": "supported | unsupported | unaddressed | unresolved", "candidate_refs": ["S2", "S3<-S2"],
    "reason": "source-linked explanation"
  }],
  "findings": [{
    "id": "F-1", "material": true,
    "kind": "missing_supplier | false_edge | omitted_requirement | unindexed_obligation | unsupported_claim | stale_source | identity_mismatch | other",
    "source_ids": ["SRC-1"], "candidate_refs": ["S2"], "recommended_change": "bounded change or empty"
  }],
  "proposed_changes": [{
    "kind": "add | remove | split | replace | rewire | none", "within_edit_bounds": true,
    "old_to_new": [{ "old": "S3<-D1", "new": ["S3<-D2"] }], "source_ids": ["SRC-1"], "reason": "why required"
  }],
  "unresolved": ["source, identity, dependency, or edit-bound issue"],
  "planning_gaps": ["unknown or missing planning obligation that prevents a qualifying pass"],
  "execution_blockers": ["accurately modeled future prerequisite, not asserted satisfied"],
  "coverage": {
    "structural_plan_status": "unknown | valid | invalid",
    "source_review_status": "incomplete | complete",
    "verification_status": "not_planned | planned | applicable_observation_recorded",
    "execution_evidence_status": "none | scoped_receipt_recorded",
    "experiments": [{
      "id": "EXP-1", "condition_id": "stable requirement or condition ID",
      "affected_consumer_refs": ["S3"], "target_identity": "artifact/version/config/target",
      "hypothesis": "string", "acceptance_criterion": "string",
      "outcome": "not_run | planned | observed | passed | failed | invalid | inconclusive",
      "result_to_plan_disposition": "does not change plan | revise required | unresolved",
      "evidence_refs": ["E-1"],
      "positive_receipts": [{ "ref": "E-1", "scope": "exact checked artifact/behavior", "fidelity": "directness to the exact condition" }]
    }]
  }
}
```

`source_review_status` is `complete` only when every indexed or independently discovered material obligation is supported, no applicable normative source is unavailable/stale/ambiguous without inspected supersession, and no material finding remains unresolved. `supported` means adequate source-grounded planned work plus planned verification, or an applicable recorded observation; it does not require global execution. A receipt supports only its exact scope/fidelity. An experiment is `passed` only when evidence meets its exact `condition_id` acceptance criterion for the stated `target_identity`; merely running it is at most `observed`, and malformed execution/result is `invalid`.


`planning_gaps` and `execution_blockers` separate plan adequacy from runtime readiness.
Classify every unresolved issue; do not copy all plan `unresolved` entries into planning
gaps indiscriminately. A known external approval may map to `supported` when its exact
consumer, external authority, and future verification are honestly modeled, while the
approval remains in plan `unresolved` and review `execution_blockers`. This can permit
complete source review and converged planning, but execution stays incomplete. Missing
normative source content, unavailable edit authority for a necessary repair, unclear
relationships, and architecture-determining unknowns remain `planning_gaps`. A planned
experiment supports only the evidence-producing work and gated consumer relationship;
it is not a positive receipt for the condition. Retain failed/inconclusive outcomes and
replan affected assumptions before qualifying. Do not relabel gaps to force convergence.
