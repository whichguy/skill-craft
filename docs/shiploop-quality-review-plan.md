# ShipLoop quality review and corrections

**Completed historical review — delivered in `2153514`.** Q1–Q7 are closed;
the findings below describe the original baseline, not current defects.
[Review closeout](#review-closeout-and-generic-lessons) preserves the evidence;
the [proposal disposition index](shiploop-proposal-closeout.md) identifies later work.

Baseline: `f47dcfa0c3fd145d88a76999bdd70777dac7d1bf`. Scope: review the
recent ShipLoop increments against Markdown authority, cold action boundaries,
evidence-backed iteration, and truthful completion; implement concrete defects
and commit only this work. Unrelated Review Coverage edits remain untouched.

## Findings and implementation plan

| ID | Confirmed gap | Correction and acceptance evidence |
| --- | --- | --- |
| Q1 | General environment and acceptance-contract projections can print unbounded fields. | Bound dynamic displays, mark truncation explicitly, retain paged durable-context navigation and exact-ID result shapes. Preserve script-authored planning instructions. Test very large Unicode fields and exact full-context recovery. |
| Q2 | Environment/discovery strings can contain obvious credentials despite non-secret instructions. | Reject recognizable credential patterns in new records; defensively redact old packet projections. Positive ordinary-reference and negative credential URL/Bearer/CLI tests. No claim of exhaustive secret detection. |
| Q3 | Git bodies can impersonate callback/continuation instructions. | Quote every body line as untrusted evidence, including legacy full output; preserve raw archival bytes and paging digests. Hostile body regression verifies only the real continuation is unquoted. |
| Q4 | Context continuation guidance says bytes although offsets count Unicode characters. | Correct guidance and test non-ASCII context paging. |
| Q5 | External route revalidation is requested but no action-bound result is required. | New-run versioned host-reported probe attestations bound to action, environment digest and selected platform/trigger; reject absent, stale, blocked, mismatched or credential-bearing evidence. Preserve old-run compatibility and clearly distinguish attestation from independent live proof. |
| Q6 | Migration accepts unsafe legacy run IDs, then creates an unreadable authority. | Reject invalid legacy identity before any migration writes; prove no backup or Markdown side effects. |
| Q7 | Ready platform declarations allow contradictory nonempty blocked paths. | Reject blocked explanations when no routes are blocked; document that blocked entries are aggregate narrative, not exhaustive typed per-route proof. |

Ordering: Q1/Q2 coordinate through a shared pure privacy helper; Q3/Q4/Q6
are independent. Q5 consumes the existing discovery schema and Q2's guard.
After implementation: independent review, full ShipLoop suite coverage,
lint/frontmatter/shell/whitespace checks, canonical-to-plugin synchronization,
and a scoped verbose learning commit. A failing required test is not waived.

## Evidence and limits

Three independent read-only reviews inspected platform/risk contracts,
recovery/state integrity, and cold packets/history/reporting. Reviewers
reproduced unsafe migration and accepted credential-bearing discovery records;
existing focused suites were green, demonstrating missing negative cases.

[OWASP logging guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
supports excluding credentials and sanitizing event data. The
[MCP maintainers' trust-boundary discussion](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/)
distinguishes descriptive hints from enforcement. These corroborate the local
reproductions, not a reason to add tooling. Quoting untrusted data and detecting
known secret patterns are defense in depth, not complete semantic/security
oracles. Host attestations cannot prove a remote operation occurred or grant
new authority. No live connectors, credentials, deployment, updater or scheduler
are in scope.

## Verification ledger

All 24 ShipLoop suites have passing results across the broad isolated run and
corrected targeted reruns: 309 distinct unittest methods, including all 12
action-walk cases. The method count excludes the risk suite's `test_case`
fixture helper, which is not a runnable test.

| Check | Observed result |
| --- | --- |
| Broad isolated snapshot | 35 jobs / 304 tests; 33 jobs passed. Two older synthetic fixtures failed as described below. Inputs remained unchanged throughout execution. |
| Corrected protocol fixtures | 34 tests passed. A strengthened missing-environment negative was then rerun and passed. |
| Corrected external preparation fixture | All 8 revalidation tests passed in the final isolated snapshot. |
| Latest packet projection and paging | 27 tests passed against the current checkout after the final packet clarification. |
| Final affected-boundary snapshot | Privacy, discovery, packets, revalidation, revalidation context, history pages, migration, objectives, and the complete terminal action walk passed. Its old protocol fixture failed and was superseded by the corrected 34-test run above. Inputs remained unchanged. |
| Long-running integration coverage | All 12 action walks passed; step planning 17, overall planning 28, and knowledge carry-forward 4 tests passed. The complete terminal action walk also passed again on the final affected-boundary snapshot. |
| Static and packaging checks | Ruff `F,E9`, all 17 package-frontmatter checks, shell syntax, `git diff --check`, and canonical/plugin parity passed. |

The two fixture repairs did not relax production checks. Protocol fixtures
that manually jumped into execution now supply a frozen local environment;
legacy scenarios explicitly opt into legacy state. The external preparation
fixture now declares its selected writer in step Tools metadata. Added
negative coverage proves a current run without a frozen environment still
blocks and prints no valid completion callback.

Raw evidence is retained under `/tmp/shiploop-quality-review.FxzS6z/`:
`summary.json`, per-suite logs, `final-logs/summary.json`, and
`protocol-corrected.log`. Both original batch summaries truthfully retain
exit 1 for their superseded fixture failures. This is complete ShipLoop suite
coverage assembled across runs, not a claim that one uninterrupted invocation
of `test/shiploop.test.sh` or the full repository test runner passed. No live
platform deployment or cross-host runtime certification was performed.

## Review closeout and generic lessons

Q1–Q7 are implemented. Final independent reviews of packet/history,
privacy/discovery, and recovery/probe-receipt boundaries found no remaining
concrete issue in the reviewed scope. This does not certify semantic perfection
or a live platform. Additional review passes caught and corrected premature
truncation, terminal controls, and overly broad credential-placeholder rules.

- Bound dynamic displays without rewriting authoritative criteria. Keep the
  executable result shape and static phase instructions intact. A bounded
  sample must explicitly direct the caller to complete paged bindings; the
  validator still requires every original criterion/route.
- Operation evidence and review evidence have different lifetimes. Reviewing
  an earlier external operation must not fabricate a new probe or repeat the
  operation. Preserve its original action-bound receipt through convergence.
- Validate migration identifiers before writing new authority; successful
  conversion is not sufficient if the next cold read cannot use the result.
- Preserve raw history bytes/digests while safely quoting display data,
  including Unicode line separators and terminal controls. Data that resembles
  a callback is still data.
- Secret screening needs both negative credential cases and positive ordinary
  documentation cases. Known-pattern filtering is not an exhaustive detector.
- New protocol opt-ins require explicit legacy test fixtures. Correct fixture
  prerequisites and add fail-closed negatives rather than weakening the gate
  to make old synthetic stage jumps pass.

## Interoperability review

Classification: script-backed portable skill. Contract: one action/result,
Markdown authority, explicit unfinished states and derived HTML. Prompts: thin
router with phase-selected references. Scripts: stdlib, one CLI family, separate
package/run/product roots. Binding: canonical package plus derived plugin view;
installed skill discovery is not proof of multi-host execution.

| Host | Package route | Runtime claim in this review |
| --- | --- | --- |
| Grok | Canonical skill-directory link | Local Python/Git fixture tests only |
| Codex | Canonical skill-directory link | Local Python/Git fixture tests only |
| Claude Code | Derived plugin view / skill directory | Content parity, not live host certification |
| Hermes | Managed materialized copy via repository installer | No installation or runtime certification performed |

Migration is limited to the corrections above. No divergent host prompt copy,
model pin, transport fallback or new integration is introduced.
