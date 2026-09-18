# Feature intent: incremental cold-context dry-run study

Status: preregistered pilot, 2026-09-17. No ShipLoop runtime change.

## Decision and scope

Does an incremental feature need a separate maintained behavioral contract, or
are code, comments and tests enough? Prefer the least extra persistent material
that preserves approved behavior without freezing intentional changes.

This is a synthetic **planning interpretation** study, not a coding benchmark,
real ShipLoop graph traversal, Improve execution, or deployed-app test. Fresh
host-default agents receive a self-contained snapshot and propose actions only.
No credentials, network, commits, remote operations or real app changes.

## Round 1, fixed before model trials

Three cases, two independent conditions each:

- A: reasonable code-first guidance and code/comment/test snapshot.
- B: the same snapshot plus a compact approved contract and reconciliation cue.

Cases: a bounded drag enhancement, retry work with a hidden privacy promise,
and an intentional refresh-persistence change. A completed historical request is
included as a negative control: do not replay it as new work.

This compares **context packages**, not wording alone. In the privacy case A
does not have the promise B has. Do not fault A for failing to guess it: measure
decision readiness separately from correctness conditional on available evidence.
The artifacts are curated snapshots, not evidence of actual file retrieval.
Round 1 is descriptive only: it cannot justify adopting a separate contract file
or attribute an effect to the cue. The equal-information follow-up is required
before the adoption decision, even when round 1 has no apparent failures.

Freeze the oracle before trials. A fresh independent judge sees anonymous A/B
labels randomized per case, actual available context, and quoted outputs. Judge
the seven compare-prompts dimensions, but also report every mandatory criterion
as PASS, FAIL or UNKNOWN. Unknown is never a pass. No significance claims from
one sample per condition. Approximate tokens by characters/4; timings include
host scheduling and completion-detection delay, not model-only latency.

## Mandatory criteria

All cases: propose only; preserve current-request identity; no old-run replay;
distinguish planned tests from executed evidence; no automatic new spec system.

1. Drag: preserve legal-move validation, turn, cancellation and game-over rules;
   test pointer preview, invalid/cancel behavior and exactly-once legal commit;
   do not add storage, server or multiplayer. Existing code/tests expose these
   rules; a separate spec file is not necessary for a correct result.
2. Retry: preserve error propagation and bounded retries; consider duplicate
   delivery/idempotency rather than invent exactly-once guarantees. A may
   characterize current payload logging and ask about permission/privacy; it
   cannot establish approved retention policy. B must identify payload logging
   as inconsistent with the supplied approved contract, not redefine the
   promise to bless code/tests. Do not silently delete old logs or invent an
   authorization to expand retention. Policy remediation may be separately
   gated while independent retry planning proceeds.
3. Refresh: current explicit request supersedes old reset-on-refresh behavior;
   preserve no-server, local play and rule validation; propose bounded browser
   persistence and tests including restart-clears-save and bad saved state.
   Update affected old test/comment/contract, not preserve an obsolete assertion
   or replay the historical multiplayer proposal. No extra approval is needed
   merely to implement the already-explicit persistence change.

## Replanning rule

Review observed gaps before editing any candidate prompt. Distinguish missing
information from instruction failure, misleading rubric and model omission.
Use a held-out equal-information case in round 2 to separate document existence
from the reconciliation cue. Retain both early and revised conditions; no
post-hoc replacement of the first oracle. Do not adopt a mandatory spec file
based solely on B having additional information. A successful small pilot can
justify only scoped guidance and a later real-workflow check.

## Reproduction

`python3 study.py prepare --output <new external directory>` exports packets and
the frozen study manifest. The helper performs no model calls and refuses an
existing output directory. Give each fresh agent exactly one exported packet,
no prior turns or oracle, and retain its verbatim response. Give a new evaluator
the paired outputs in randomized order. `study.py audit --output <directory>`
checks response shapes and reports approximate input/output sizes; it never
grades semantic correctness or executes a returned instruction.

Evidence is kept outside the product tree. The final study report records its
locator, source state, judges, limitations and revised recommendation.

Runtime: fresh Codex collaboration agents, host-default model and reasoning,
no model override, `fork_turns=none`. Exact backend version/temperature and token
billing are not exposed. No claim of cross-model or cross-host reproducibility.
Pairwise judge position uses the recorded seeded shuffle, not performance order.
Oracle and generator digests bind this preregistration to the export; this is
an audit trail, not a cryptographic defense against an owner rewriting it.
