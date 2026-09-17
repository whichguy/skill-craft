# Delivery authority follow-up — implementation and validation

## Plan and implemented scope

1. Keep the existing graph, action callbacks, Markdown ledger, and opt-in
   delivery-contract schema. Add no remote executor or approval parser.
2. Route every navigator packet to one shared authority-readiness reference.
   Resolve missing approval early once the target/operation is concrete; retain
   the decision in the existing environment note and carry its reference.
3. Reuse only explicitly user-approved standing policy after current scope and
   binding checks. Keep one-off approvals, access, delivery necessity, remote
   effect, identity, and consumer behavior distinct.
4. Challenge required/optional contradictions in the existing Improve campaign;
   prevent an unverified required consumer outcome from being called delivered.
5. Add declaration regressions, cold/relocated packet checks, and a bounded
   interpretation study. Keep generated plugin content synchronized.

All five items are implemented. No product approval, push, deployment, or
standing policy for an actual repository was created by this change.

## Interpretation study (2026-09-16)

Parent-authored assessment of actual read-only subagent responses, not generated
expected answers or live execution. `authority_cold_interpretation` received the
eight cases, current stage prompts and the shared reference, with no parent
history, oracle, or permission to inspect a product/contact a destination. It
interpreted the cases in one batch; these were **not eight isolated model calls**.
The separate `authority_timing_interpretation` received only the conflict case
and revised instructions, again without the oracle or prior response.

| Case | Observed interpretation |
| --- | --- |
| standing-current | Revalidate and reuse U-1; no duplicate approval or discovery-time sync. |
| one-off-only | Ask now; old approval/receipt cannot authorize the new run. Carry the downstream gate. |
| standing-target-drift | Account/target mismatch needs a new disposition; do not follow the generated reuse plan. |
| unanswered-request | Do not duplicate the question or infer consent/source-only scope. Independent discovery can finish. |
| explicit-source-only | Current no-push request overrides standing sync permission; verify locally. |
| required-optional-conflict | Initial response caught the material contradiction but unnecessarily held outer Improve for downstream approval. Clarified the correction-versus-scope-change distinction; the fresh follow-up correctly restores required scope, asks approval, and gates release-plan/write rather than review convergence. |
| sync-without-behavior | Retain sync/identity, request browser access, block required behavior verification, do not repush. |
| same-target-broader-effects | Matching target/operation is insufficient for excluded public-access/data effects; release planning stays incomplete pending disposition. |

The initial batch met seven complete scenario criteria and exposed one timing
ambiguity. The affected scenario passed the focused follow-up after its wording
fix. This is a qualitative pilot, not an A/B performance claim, Grok execution,
proof of remote behavior, or a guarantee of future model compliance. The fixture
generator offers two repetitions; this record does **not** claim both were run.
Some fixtures omit literal account/access names; the interpreter retained
placeholders instead of inventing them. A real question must use observed names.

## Executable checks

- Cold/relocated auth-readiness packet tests: 4 passed, including both navigator
  protocols, INNER/OUTER traversal, pause/block/resume and unchanged state on `next`.
  The new locator assertions failed before implementation, then passed.
- Consumer-delivery guard: 22 passed. New cases reject missing policy approval
  references and mismatched target/operation, retain old obligations on rejected
  downgrades, and show fresh runs do not inherit one-off grants.
- Delivery prompt/fixture tests: 7 passed. The new authority generator test
  failed before wiring, then passed; oracles stay out of interpreted packets.
- Navigator 26, navigator dry-run 5, consumer-delivery CLI 6, cross-run 7,
  environment lifecycle 5, reference routing 5, protocol 35, test groups 10:
  passed. Total across these focused Python suites: 132 tests.
- Ruff, repository frontmatter checks (18 skills), generated ShipLoop plugin
  parity, and `git diff --check`: passed.

The machine's default Git is blocked by its Xcode license; Git-backed checks
were rerun successfully using the available fallback Git on PATH. The generic
skill-creator quick validator could not start because PyYAML is unavailable;
the repository's own portable-skill frontmatter checker passed instead. No
dependency was installed. The full aggregate suite and live Grok/cloud delivery
were not run. Declaration checks cannot authenticate policy provenance or
consumer evidence. Ordinary unmarked runs still rely on host compliance with
the prompts; the existing declaration guard remains an explicit opt-in.
