# ShipLoop: one-action host, durable objective loops

## Approved outcome

Implement the user's accumulated requests in the existing Markdown-authoritative
harness. One skill invocation starts/resumes a run. Each reply supplies one
action, its current environment/context, required evidence/result shape, and an
exact completion call. The host does that action and calls back; only scripts
advance state. A new host context may begin at every action boundary.

The successful terminal packet says `It's all complete.` and links a generated,
offline HTML achievement report. Paused, failed, halted, or unverified work must
never use that success message.

## Audit and decisions

| Priority | Gap and decision | Verification |
| --- | --- | --- |
| Critical | The large skill card carries workflow knowledge that a cold host cannot be assumed to retain. Move operational instructions into stage-local packets and their explicitly selected resources. | Cold packet tests across every stage; no unstated result fields or missing callback. |
| High | Step inputs/produces imply readiness/completion but do not define a complete explicit contract. Require versioned per-step Ready and Done criteria, exact outcomes and verification obligations. | Missing/invalid criteria refused; evidence-bound completion; no silent upgrade of old DAGs. |
| High | Until-loop policy is shared only by execution planning. Use the same completed-pass decision for all substantive quality objectives with phase-specific rubrics. | Material resets, two genuine trivial passes, pending findings, stale checks and duplicate receipts. |
| High | History gates request seven commits and SHA collection does not establish full-message delivery. Require ten full messages, paged with current-action/current-HEAD bindings and a concrete assessment. | Subject-only, partial, stale and changed-history requests rejected. |
| High | Sequence, readiness, broader-plan and outer quality need explicit iterative review, while finite commands and external side effects must not recursively repeat. | Generic objective lifecycle tests; side effects occur only on authorized operation path. |
| High | Final handoff is Markdown only. Generate an evidence-derived HTML result with TLDR, timeline, checks, limitations and improvement proposals. | Escaping, incomplete/corrupt records, halted outcomes, deterministic rendering, browser inspection. |

### Design questions

1. **Who owns progress? (information gain 1.0)** The script alone, under the
   existing lock/Markdown transaction. Results are evidence submissions, not
   permission to choose a next stage. Identical completion replay is idempotent.
2. **Does every command need two reviews? (0.9)** No. Every substantive quality
   objective does; commands are bounded actions within that objective. Explicitly
   declared nested loops have distinct counters and cannot close a parent.
3. **How does a small context read ten verbose commits? (0.9)** Bounded pages
   with immutable identities and durable assessments. Read all required messages;
   keep only relevant decisions in the next prompt. Audit commits do not replace
   inspection of relevant older product history.
4. **What counts as trivial? (0.9)** Non-semantic polish, after actual review.
   New transitions, guards, expected outcomes, missing tests, dependencies and
   changed assumptions are material regardless of diff size. Apply trivial fixes
   before counting the pass and verify the final candidate again.
5. **Is HTML another state store? (0.8)** No. It is a derived presentation of
   accepted Markdown evidence, clearly distinguishing machine checks from
   host-reported/external assertions. Missing evidence is never manufactured.

## Implementation slices and ownership

1. Core objectives/history: shared pure until policy, phase adapters, Markdown
   receipts, replay/repair/legacy behavior, exact last-ten history gate.
2. Step contracts: normalized Ready/Done criteria and evidence validators;
   separate ready-to-plan, ready-to-code, integrated and deployment-verified.
3. Packets/thin skill: stage-local actionable instructions and callbacks,
   result schema, bounded context, accepted/replayed/recovery status.
4. Report: deterministic stdlib HTML builder and focused safety/evidence tests.
5. Integration: completion alias, contract gates, atomic report generation,
   fixture migrations, README/workflow/state/protocol documentation.
6. Verification: relevant module suites, full ShipLoop suite, lint, plugin-view
   consistency, independent review, and cold-start/HTML checks.

## Invariants retained

- Authoritative state stays in Markdown; no standalone until-loop JSON session.
- Preserve unrelated work, credentials, provider/writer authority and host-neutral
  packaging. No external deployment/install/push is authorized by this task.
- Real lint and tests run every accepted iteration. Failed/stale/unrun checks do
  not satisfy Done. Source edits invalidate affected evidence.
- Each completed improvement pass has a distinct verbose learning commit.
  Audit-only passes must not stage unrelated work; product passes commit scoped
  changes. Git history explains decisions, not current environmental truth.
- Findings remain durable until resolved; two trivial passes permit fresh final
  validation rather than proving semantic perfection.
- Broader-step knowledge and generic ShipLoop proposals remain separate and
  visible after restart. Only compatible pending DAG steps can be revised.
- A blocker or exhausted budget is unfinished, not an alternative success path.

## Verification record

Implementation is complete and the scoped verification below is recorded.
There are 224 distinct Python test cases verified across full suites and
affected targeted reruns, plus the independent cold-operator trial and a
retained successful terminal walkthrough. This is implementation evidence,
not a claim that a downstream application was deployed or that every host was
certified.

### Initial history assessment

Read all ten complete messages from `01c5cd722033df5ad4f523ccbfbff8c4301cdb66`
back through `3422dc7b7e880d78f3dc4ee8afa1d663810c3ff6`. Applicable learnings:

- `01c5cd7`: real client/service invocation is distinct from routing; preserve
  the generic interface producer and test the actual calling path.
- `68324cf`: cold hosts previously failed on unstated result/commit schemas;
  packets must include every enforced shape and explicit correction path.
- `f68f033`: preserve the destination writer's documented constraints without
  importing a vendor-specific recipe into the generic harness.
- `daa6bab`, `4363650`, `3d7ab97`, `9562ac0`: review audit commits can dominate
  recent history. Retain all ten and follow relevant product-decision references.
- `2c45165`, `7304fed`: the lint oracle belongs in recovered environment packets
  even when no exclusive writer exists; reuse available checkers, do not install
  a new one merely for the loop.
- `3422dc7`: pointer-only environment guidance was insufficient. Inline compact
  current writer/reserved-path/lint constraints and page further evidence.

### Validation

| Check | Result |
| --- | --- |
| Storage / evidence / validators | 7 / 8 / 39 passed |
| Closure and pending-map boundaries | 10 passed |
| Generic objectives / embedded until policy | 15 / 7 passed |
| Contract schema / contract protocol adapters | 10 / 10 passed |
| Delivery / HTML report | 6 / 8 passed |
| Protocol / cold action packets | 29 / 14 passed |
| Step planning | 17 passed |
| Research, behavior, and specification planning | 28 passed: 27 in full run, 1 assertion-only wording migration verified by targeted rerun |
| Carry-forward knowledge integration | 4 passed in corrected full-suite rerun |
| Public-CLI action walks and fixture lint regression | 12 passed across full run and affected targeted reruns; retained terminal walkthrough with genuine planning lint passed |
| Canonical ShipLoop scripts and Python tests Ruff | Passed |
| Repository skill-frontmatter validator | Passed, 17 skills |
| ShipLoop plugin mirror consistency | Passed, scoped to ShipLoop |
| Shell harness syntax / Git whitespace checks | Passed |
| Implementation-summary HTML | Static links/anchors/offline checks passed; browser visual preview blocked by URL policy, no workaround attempted |

The generic skill-creator quick validator could not run because its PyYAML
dependency is absent in both available Python runtimes; no dependency was
installed. The repository's own frontmatter validation passed. No push,
deployment, credential change, or new persistent integration was performed.

### Review-driven corrections

- A subject-only history index cannot stand in for delivered full message pages;
  one-message pages must accumulate coverage without losing the ten-message gate.
- A semantic objective candidate replacement is conservatively material even
  when the host labels it trivial. The script cannot prove semantic perfection.
- Ready/Done use script-owned identities and retain exact verification records.
  Current-step knowledge changes invalidate them; scheduling a future obligation
  does not. A staged blob hidden by restored working-tree bytes is rejected.
- Post-inner audit commits may rebind only through the actual unchanged-tree
  ancestry. Changed-then-reverted product commits still require new verification.
- The report stays derived and its success rendering is part of the terminal
  transaction; a terminal cursor alone cannot emit the success phrase.
- Final verification rejects late commits and staged source changes after
  convergence. Outer closure is anchored to integrated step receipts; product
  corrections must re-enter planned work instead of slipping through quality.
- Lifecycle declarations and marked DAG activities must agree. `none`,
  `preparation: outer-before`, and `publish: outer-loop` cannot also authorize
  a DAG step for the same activity.
- Objective packets must include real reference anchors, the complete manifest
  shape, diagnostic evidence paths, and the exact verbose commit structure.
  Check commands must read immutable inputs directly, not recursively call the
  locked ShipLoop CLI against the same run.
- End-to-end acceptance fixtures must not label a no-op process as lint.
  Planning/objective/step-plan fixtures now execute direct Markdown structural,
  fenced-JSON, and whitespace checks; a negative case proves malformed input
  fails. Product fixtures retain real Python syntax and exact-output checks.

An independent source reviewer found no remaining actionable issue in the
targeted objective/closure gates. Synthetic report desktop (1440 px) and mobile
(390 px) rendering were inspected with installed Chrome in an isolated
headless session, with no document overflow. This fixture is not a product
achievement or a live deployment claim. Initial integration failures were
corrected test expectations/fixtures: an updated sequence proof error message
and dynamic corrective-step contract lookup. The affected cases passed on
rerun; the knowledge suite also passed a corrected full run. The later lint
fixture accepted the actual raw-Markdown versus state-record formats without
inventing a terminal-newline requirement. Nine authored candidate shapes and
the retained complete walk passed with the genuine lint commands.

### Independent cold-operator trial

The opaque-CLI trial reached `validate-spec / survey` (revision 13) in
`/private/tmp/shiploop-cold-user.ly2dJU/.shiploop` after two unchanged, verified
approach passes and fresh final verification. Same-tree audit commits were
`8c6f83bf73f76f66b6bf0e04eabae6a1d0a6e1d9` and
`24fa4eb81ee6ed4a6b2028e0f92693719b412f3d`. It stopped at survey; this is not a
claim of a completed product or an end-to-end trial on every supported host.

The trial found the missing manifest schema and a same-run CLI check that
deadlocked on the active lock. Both packet gaps were corrected and the direct
immutable-candidate check passed. The operator's earlier full-reference read
is retained as a trial limitation: the test did not prove a fixed token ceiling
or physically clear the conversation after every action.

### Retained terminal proof

The real two-step public-CLI walkthrough completed 223 accepted actions and
produced `report.html` (106,844 bytes). Its final state is `done / done`, with
`evidence_complete: true`; the HTML SHA-256 matches the recorded value
`dab4e1e012e72dd04e5c362f749ad180119bf64262eddd93c395f17dd57442d5`.
Read-only `status` prints the exact `It's all complete.` message and no further
completion callback.

Inspection evidence is retained at
`/tmp/shiploop-terminal-proof.o3D7d5/run`. This is a copy made after terminal
success, before normal test cleanup: the original temporary product checkout
was removed, so this copy is an inspection artifact, not a relocated resumable
run. The earlier lint failure is retained alongside it for audit. The permanent
human-readable implementation summary is
[shiploop-implementation-report.html](shiploop-implementation-report.html).

### Remaining limits

Two stable passes are a convergence heuristic, not semantic perfection. Full
commit bodies still have no byte-level paging; legacy migration cannot recover
an absent original prompt; and merge-intent reconciliation may need operator
direction. Incompatible changes to frozen scope or authority require explicit
direction rather than automatic rebasing. See the README for current recovery
boundaries. These limitations are not alternative success paths.
