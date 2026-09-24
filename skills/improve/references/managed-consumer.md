# Managed Improve consumer contract

`scripts/managed_controller.py` is a pure controller for a consumer that
persists Improve child state in its own durable store. It has no CLI, no
filesystem backend, no Git calls, and no dependency on the standalone Improve
until-loop runtime. A ShipLoop consumer keeps Markdown authoritative and uses
this controller only for child phase routing, convergence, and certificate
validation.

## Binding and child ownership

Create an immutable binding with `new_binding(...)`. It requires a stable
`parent_action`, `child_action_id`, profile, input identity, policy digest,
executor digest, explicit `audit-every-iteration` commit policy, and
independent-review policy. The controller adds `binding_sha256` over all of
those fields. A changed input, policy, executor, parent action, or profile is a
new child, not a resume.

Create the child with `new_child(binding)`. Persist that returned object under
the consumer's own namespace. The controller permits exactly one
adapter-owned execution projection:

```json
{
  "phase": "review phase or null",
  "stage": "consumer stage projection",
  "action": "consumer action projection",
  "completed_actions": [],
  "overlay": {}
}
```

`execution.phase` must equal the controller's `current_phase`. The controller
does not count `completed_actions` or inspect `overlay` when it decides whether
the child converged. Its separate `paused` boolean is controller-owned: it
keeps an active carry-forward or required step-plan disposition child waiting
without turning that wait into a successful or terminal result.

## Profiles and legal routes

Each planning subject is a separate child. No route crosses from research to
behavior or specification.

| Profile | Ordered phases |
| --- | --- |
| `research` | `research-review` → `research-plan` → `research-apply` → `research-verify` → `research-commit` → `research-finalize` |
| `behavior` | `behavior-review` → `behavior-plan` → `behavior-apply` → `behavior-verify` → `behavior-commit` → `behavior-finalize` |
| `spec` | `spec-review` → `spec-plan` → `spec-apply` → `spec-verify` → `spec-commit` → `spec-finalize` |
| `objective` | `objective-review` → `objective-plan` → `objective-apply` → `objective-verify` → `objective-commit` → `objective-finalize` |
| `step-plan` | `step-plan-review` → conditional `step-plan-disposition` → `step-plan-revise` → `step-plan-verify` → `step-plan-commit` → `step-plan-finalize` |
| `product` | `review` → `improve-plan` → `improve-plan-verify` → `improve-apply` → `test-refine` → `test-author` → `iteration-document` → conditional `skill-validate` → `verify` → `carry-forward` → `commit` → `final-verify` |

Call `route(profile, current_stage, ...)` or `apply(child, event)`; do not
provide a caller-selected successor. At `step-plan-review`, record exactly one
route flag: `{"disposition": "required"}` routes through disposition and then
starts a fresh review pass; `{"disposition": "not-required"}` routes to
revision. At product `iteration-document`, record both
`documentation_disposition` (`updated` or `not-needed`) and
`skill_disposition` (`validate` or `not-needed`). These decisions cannot be
silently skipped.

At product `carry-forward`, record exactly
`{"disposition":"continue"}`, `{"disposition":"pause"}`, or
`{"disposition":"repair"}`. Continue routes to commit. Pause retains the
same active carry-forward phase and records `paused: true`. Repair routes to
the product review phase and begins a new convergence epoch. The old phase
records remain durable history, but their completed passes cannot contribute to
the new clean-pass streak.

An adapter may end any active phase with `blocked`, `needs-prerequisite`,
`needs-replan`, or `stopped`, with evidence refs and a reason. Those statuses
are terminal but never successful. The parent keeps the child binding and
handles resumption or an allowed replan; it must not release consumers.
When the recorded condition is resolved, call
`resume(child, reason=..., evidence_refs=[...])`; it restores the same child at
its interrupted phase. It also clears an active controller-owned pause while
preserving that phase; neither form records a successful transition. A paused
child cannot submit a `complete` event until this explicit resume record exists.
A direct repair may still interrupt any active phase and resets the current
epoch without deleting history. Repairs for every profile other than `step-plan`
use empty flags and return to that profile's review phase. A step-plan repair may use
`{"disposition":"not-required"}` to return to `step-plan-review`, or
`{"disposition":"required"}` to wait at `step-plan-disposition` with
`paused: true`. The latter is a recovery record, never a fabricated successful
review: after resumption clears the pause, the consumer must still submit the
disposition's own explicit result before the fresh review can start.

## Evidence events

The consumer validates typed receipts and external effects before calling
`apply`. Every event has nonempty `evidence_refs`, its exact current `phase`,
and no generic `done` field. Normal completion is:

```json
{"kind":"complete","phase":"current phase","evidence_refs":["durable-ref"],"flags":{}}
```

At a commit phase, add `audit_commit`, `completed_pass`, and `open_findings`.
The completed pass is:

```json
{
  "id": "stable-pass-id",
  "outcome": "material or trivial",
  "verified": true,
  "commit": "40-or-64-lowercase-hex-sha",
  "evidence_ref": "durable-pass-ref"
}
```

The audit commit must match the pass commit. The controller appends the pass to
the canonical `child.passes` counter, derives its streak with `decide`, and
either loops to the profile review stage or admits the final fresh-check phase.
The consumer may mirror that record into legacy receipts, but must not maintain
a second convergence counter.

The managed binding selects independent review whenever a reviewer is
available, whether or not it is required. If the binding requires independent
review, each completed pass records either a performed reviewer evidence ref
or, only when the binding explicitly permits it, an unavailable reviewer plus a
recorded `self-review` fallback and reason. An unavailable required reviewer
without that explicit fallback cannot count.

At a final phase, supply no new pass. Supply an output identity with a
64-character `identity_digest` and fresh evidence:

```json
{
  "binding_sha256": "binding digest",
  "action": "fresh-check-action",
  "identity_digest": "same output identity digest",
  "checks": [{"id":"check-id","result":"passed","evidence_ref":"durable-check-ref"}],
  "evidence_ref": "durable-final-result-ref",
  "result": "passed"
}
```

This proves that current evidence was supplied by the adapter; the controller
does not trust a generic success flag. Finalization is legal only after two
distinct verified trivial passes and no open findings.

## Certificate import

`terminal_certificate(child)` works only for `converged` children. Its digest
binds the binding, output identity, completed passes, and all evidence refs.
It explicitly records an empty `open_findings` inventory and supplies a stable
replay key. Import it with
`assert_terminal_certificate(child, certificate)` after the consumer atomically
checks the active binding and current output identity. A wrong binding, stale
certificate, duplicate pass/commit, unresolved finding, missing fresh check,
or incomplete child result is rejected.
