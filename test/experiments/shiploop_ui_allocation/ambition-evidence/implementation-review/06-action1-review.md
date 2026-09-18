# Action 1 — full bounded Improve review

**Candidate reviewed:** `3d45d186e8caf605660e1f49efded1fb3d31dffa` plus the root-owned 0.15.2 working-tree delta.  The review was confined to the contract’s three ShipLoop source files, their generated package copies and metadata, and the permitted helper/test consumers.  `README.md`, `.grok-plugin/marketplace.json`, all documentation (including the concurrently appearing untracked design-ambition document), fixtures, snapshots, study artifacts, and root-owned work were not edited or treated as this review’s candidate scope.

## History and independent review

Read the seven full commit messages retained in `02-action1-history.txt`: `3d45d186`, `be3ed4db`, `bf6fe176`, `5a073503`, `10733eee`, `f2c891a6`, and `061ad490`.

The fresh independent reviewer found no contradiction, routing defect, overclaim, or source/generated mismatch.  Its only proposed P2 was static regression assertions for each new guide phrase.  This review did not implement that proposal: the immutable contract expressly excludes a new test that merely mirrors prompt wording, and the existing guidance suite is correctly scoped to packet/routing behavior rather than claiming to mechanically prove model interpretation.  No concrete behavioral failure, loss of a required boundary, or generated drift makes that proposed static wording check material.

## Findings

The new guide is internally bounded:

* ambition is limited by the user’s goals, accepted scope, target constraints, and proportional expected value;
* reuse, evolution, and an upgrade/new tool are alternatives rather than a forced migration; a dependency remains a candidate until fit is established;
* the decision records uncertainty, checks/probes, compatibility, performance/accessibility, maintenance, and a rough estimate without fabricating availability or results;
* a local preview is explicitly weaker than deployed compatibility;
* primary design material supplies adaptable principles, never a brand-copy or dependency mandate; and
* existing application, design/build/test, and browser facilities stay authoritative.  The guide forbids a parallel UI stack or duplicate harness and carries the accepted decision forward unless new evidence warrants reconsideration.

The global-plan and step-plan prompt paths each request the decision, rough effort/benefit, compatibility check, unaffected-scope reuse, and existing facilities.  The normal Improve prompt independently reopens those concerns for an affected consequential choice.  This keeps the work in the existing handoff rather than adding a state-machine stage, scheduler, or nested review campaign.

Both live Google Design URLs resolved at review time; their results are recorded in `03-action1-link-validation.md`.  They support the guide’s limited references to usable hierarchy, purposeful motion, clarity, familiar patterns, and user control.  They do not justify any product-specific capability, estimate, or deployment claim.

## Checks and outcome

* `git diff --check HEAD` — passed.
* Source/generated file comparisons — exact for the three ShipLoop source files and their plugin copies.
* Version metadata — source and all three plugin manifests report `0.15.2`.
* `python3 -B test/shiploop-v3-guidance.test.py` — passed, 18 tests; raw output: `04-action1-guidance.stdout.txt`.
* `./scripts/sync-plugin-views.sh --check` — passed; raw output: `05-action1-plugin-parity.stdout.txt`.

No source, generated package, test, documentation, artifact, commit, push, merge, publication, deployment, install, or broad aggregate action was performed by this review.  Root-owned base CI `35383508418` is deliberately not claimed as validation of this new candidate.

**Classification:** trivial.  The full review found no material defect after checking the new source and its consumers; the next distinct full review is still required before the runtime can decide its two-review exit gate.
