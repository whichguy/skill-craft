# Improve review one — material plan correction

## Candidate and review basis

This is the first distinct Improve review for the frozen W1 `step-plan` result.
It reviewed the preserved producer plan, the parent seed result, the current
product requirements and UI/environment/API sources, and the first-review
commands in `checks.md`. The original producer inventory is in
`source-inventory.md`; neither the producer plan nor parent state was changed.

The applicable accepted requirements remain:

- `README.md`: reload-recoverable drafts, preserved list/detail/edit/save/cancel/back
  journeys and visual identity, account-to-account unreadability after logout,
  and local pending drafts distinct from confirmed notes.
- `docs/design.md#UI identity`: the native account selector, stable textarea,
  focus/touch/narrow-layout and navy/amber identity remain preserved premises;
  its v1 storage statement is historical only.
- `docs/platform.md`: static same-origin target, host-owned identity, no deployed
  Node/server runtime, and no remote deployment access in this fixture.
- `docs/api.md`: documented export contracts and an explicit absence of a
  draft-storage endpoint.

The selected interaction/state guidance and the W1 environment note still make
the durable provider and authenticated account boundary a prerequisite. The
probe verifies neither exists for `fieldnotes-embedded-v2`; source checks do
not substitute for the required same-account reload and cross-account/logout
browser checks. The retained plan correctly keeps that product outcome blocked.

## History attempt

The required `git -C product log -7 --format=fuller` attempt returned exit 128
because the archive has no `.git`. There are no reachable commit messages to
use in this review. Git was not initialized. This limitation is repeated per
review rather than treated as a pass or as a product blocker.

## Finding and correction

**Material finding:** the producer plan says `product/docs/api.md has note-save
and export contracts` and later relies on an `existing note-save contract`.
Current `docs/api.md` only documents `/api/exports` and explicitly says there
is no draft-storage endpoint. `app.js` *observes* a GET/POST account-note route,
a `baseRevision`, and an expected `payload.record`, but source code is not an
accepted target API contract.

**Plan-only correction:** retain the W1 outcome as `blocked`, but replace that
false premise in the final reviewed plan with this boundary:

> The existing save journey is an accepted README behavior and `app.js` is an
> observed client implementation. Before W1 implementation or its SAVE/FAIL/
> STALE cases can be treated as executable, the target/platform supplier must
> provide a current contract for the same account-note read/save route or an
> approved replacement. It must state authorized account identity, record and
> revision/conflict response semantics, failure behavior, and how its confirmed
> result relates to the supplied durable draft carrier. This is a revalidation
> requirement; it does not turn the observed client endpoint into proof of a
> deployed service or authorize a new endpoint.

The original durable-carrier blocker remains first: a provider/draft API with
account isolation, retention, static invocation and real browser verification
is still absent. The note-route contract gap is a second prerequisite for the
future plan's server-save cleanup/conflict claims. The existing environment
supplier/recovery route remains the target/platform owner or an authorized user
instruction; no supplier was invented.

## Plan and application

The authorized plan was to correct only the planning evidence and final parent
result, preserve all source files, and record current checks. It was applied by
creating this child review evidence only. No product source, test, dependency,
configuration, documentation, Git state, remote target, or deployment changed.

## Classification and handoff basis

Classification is **non-trivial** because a material source-of-authority error
in the plan was found and corrected in the reviewed final result. It resets the
trivial-review streak. A fresh second review is required. Independent reviewer
availability: no separate fresh independent reviewer was dispatched for this
single assigned fixture child; this record is a disclosed self-review.

Cold-recovery locators: the frozen contract is in `../packet.json`; original
producer source is the absolute path in `source-inventory.md`; current checks
are in `checks.md`; the parent packet and exact import route are frozen in the
child context/resources.
