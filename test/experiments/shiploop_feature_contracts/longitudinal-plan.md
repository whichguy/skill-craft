# Four-invocation retention dry run

Follow-up to the initial feature-contract study. This is a human/orchestrator-run
interpretation experiment, not another runtime or CI model dependency.

## Frozen design

1. Snapshot the candidate `maintained-product-requirements` policy. Freeze an
   independent oracle before starting fresh trials.
2. Give a fresh agent the policy, a minimal repo README, and this first request:
   browser-local notes; no network transmission; plain text, never HTML; confirm
   deletion and cancel leaves note/list unchanged; reject empty without mutation;
   refresh resets notes. Ask for maintained Markdown and proposed checks only.
3. Copy only that resulting repo to a second isolated directory. Give a fresh
   agent the same policy and a new request for case-insensitive text search.
4. Copy its resulting repo to a third directory. A new fresh agent receives only
   the new request to retain notes across reloads in the same browser tab.
5. Copy that resulting repo to a fourth directory. Add an explicitly unapproved
   design note proposing no delete confirmation and empty-note acceptance.
   A new fresh agent receives only the request to sort matching results
   newest-updated first.
6. An independent reader judges all original packets and resulting Markdown
   against the frozen oracle. Do not repair intermediate outputs before judging.

Each participant reads its current packet, policy and its own repository only;
the previous conversation and run folders are unavailable. No code, tests,
deployments, commits or actual ShipLoop/Improve calls are executed. This is an
instruction boundary, not a claim that tools were sandboxed. Use `apply_patch`
for trial Markdown. Preserve raw outputs and all input/policy/oracle versions.

Mandatory criteria: reuse a suitable existing authoritative home (fallback
`docs/requirements.md`); retain each accepted condition and meaningful subclause;
explicitly supersede only the requested rule; reject unapproved scope changes;
preserve useful decision-source summaries without old runs; provide useful test
pointers or honest gaps; do not claim unrun product checks passed. Score
PASS/FAIL/UNKNOWN per criterion and quote evidence. Report ambiguity between
oracle and policy rather than silently revising either after seeing results.

## Boundaries and decisions

One four-request chain cannot demonstrate reliability over arbitrary future
runs, other models/hosts, full graph execution, or deployed behavior. It can
expose concrete retention/supersession failures before adding more machinery.
Replan from observed failures; do not add a formal schema, state field or review
counter solely because a model can make mistakes. Existing Improve remains the
review owner in real runs; this experiment does not simulate its completion.

The actual 2026-09-17 run used fresh host-default Codex collaboration agents with
`fork_turns=none`, no model override. Exact backend version/temperature and token
billing were not exposed. Frozen candidate and oracle hashes, raw evidence
locator, review, implementation and verification are in the
[implementation report](../../../docs/shiploop-requirements-retention-2026-09-17.md).
