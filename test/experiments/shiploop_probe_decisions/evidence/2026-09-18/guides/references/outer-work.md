# Outer-work journal

`outer-work.md` is the one script-maintained Markdown record for required work
that an inner stage discovers but an outer stage must perform. It is a journal
of obligations, not deployment authority and not a command queue. Recording an
entry never publishes, deploys, sends, grants access, or completes the parent
action.

The pure model is `scripts/shiploop_outer_work.py`. The protocol owns its
transaction, action receipts, CLI paging, and the lifecycle transition that
uses it.

## Stages and blocking

An entry targets exactly one outer stage:

1. `quality`
2. `publish`
3. `handoff`

An unresolved `planned` entry blocks its own stage and every later stage. A
`publish` row therefore does not block `quality`; a `quality` row blocks all
three. The protocol must load the current journal before an inner-stage request
so it can reuse its stable dedupe key rather than create an avoidable second
obligation. Each outer stage must read the current full journal and act on all
rows due through that stage.

When a frozen lifecycle record is present, a `publish` request is accepted only
when that lifecycle explicitly uses `publish: outer-loop`. A lifecycle with
`publish: none` or `publish: dag` cannot gain an outer publication obligation
through this journal; use a compatible `quality` or `handoff` row, or obtain an
authorized lifecycle revision first.

`planned` is deliberately not `resolved`. There is no `waived`, `skipped`, or
implicit-deployment resolution status.

## Request record

The protocol issues a separate stable `request_id` in its packet. The parent
action remains open when this result is journaled, so submitting the same
request again can return the original receipt without completing that action.
The JSON shapes below are explanatory only: protocol callers must use the exact
script-generated append/resolve templates, including an `OW-` plus 32 lowercase
hex-character request ID. Never copy a sample ID or omit the `request_id` from
a resolve request.

```json
{
  "request_id": "OW-0123456789abcdef0123456789abcdef",
  "expected_revision": 4,
  "entry_id": "OW-RELEASE-001",
  "dedupe_key": "release-owner-approval",
  "required_action": "Obtain the release owner's explicit approval before publication.",
  "target_stage": "quality",
  "target_alias": "production-release",
  "prerequisites": ["The candidate revision remains the reviewed revision."],
  "expected_outcome": "The release owner records whether publication may proceed.",
  "evidence": "Current quality report and bound candidate revision are available.",
  "authority_limitations": "This journal does not authorize publication or deployment.",
  "rationale": "Production publication is outside the inner implementation authority."
}
```

Every request carries the current `expected_revision`. `entry_id` and
`dedupe_key` are stable safe identifiers and must remain paired. The other
fields are bounded, concrete, non-secret strings; prerequisites are a bounded
unique list. `authority_limitations` is required so the journal cannot be
mistaken for authorization.

The protocol supplies provenance separately and retains it in the event and
effective entry:

```json
{
  "parent_action": "A-INNER-001",
  "parent_step": "S1",
  "parent_stage": "verify"
}
```

`parent_step` may be `null` when the stage has no active plan step. This lets a
failed verify or planning stage create a dependency without pretending that the
dependency was completed.

## Receipts and deduplication

`append(ledger, request, provenance)` returns `(next_ledger, receipt)`. The
receipt contains its request ID, stable entry identity, resulting revision,
outcome, and whether it created an obligation.

- An exact replay of the same request ID returns the original receipt and does
  not append an event.
- A changed request with an already accepted request ID is rejected.
- A new request ID with identical dependency details appends an audit event and
  receives `duplicate`, but it creates no second effective entry.
- New details under the same stable identity update the effective entry. If it
  had been resolved, it becomes `planned` again with outcome `reopened`.

The record contains only `version`, `revision`, append-only `events`, and
deterministically derived `entries`. Validation reconstructs the effective
entries from the events; a hand-edited resolved entry is rejected.

## Resolution and reads

Only the target outer stage can resolve a planned row. Its result has exactly:

```json
{
  "request_id": "OW-0123456789abcdef0123456789abcdef",
  "entry_id": "OW-RELEASE-001",
  "expected_revision": 5,
  "evidence": "The release owner recorded the quality decision against the candidate revision.",
  "reason": "The required approval was obtained for the reviewed candidate."
}
```

`resolve(ledger, resolution, provenance)` requires current revision, retained
evidence, retained reason, and provenance whose `parent_stage` equals the
entry's target stage. It has no field that can waive, bypass, or infer external
permission.

Before an outer transition, the protocol binds its full paged journal read to:

```json
{
  "revision": 5,
  "digest": "sha256 of the current render(ledger) bytes",
  "target_stage": "quality"
}
```

`check_read` verifies this binding; protocol paging independently proves that
every byte of that current rendered record was read. `pending_for_stage` returns
only unresolved rows due at the requested stage or earlier.

## Safety limits

The journal is bounded to 128 events, 48 effective entries, 16 prerequisites
per entry, and ShipLoop's existing bounded text limit. All strings use the
existing knowledge and privacy screens, so credential-looking content is
rejected before it can be retained. The model is pure: it reads no filesystem,
does not inspect an environment, and has no external side effects.
