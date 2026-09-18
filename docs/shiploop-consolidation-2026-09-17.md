# ShipLoop branch consolidation

This integration preserves useful ShipLoop changes without merging unrelated
local-only work or replaying superseded workflow designs. It changes no live
application deployment, marketplace pin, installed host profile, or credential.

## Included inputs

| Input | Treatment |
| --- | --- |
| Published baseline `8550406` | Preserve requirements retention, correlated references, and existing interaction/NFR guidance. |
| Runtime candidate `1f217d7` | Merge ancestry, including bounded packets, delivery recovery, actual-Improve fixture isolation, and atomic shared-gateway ledger repair. |
| Continuation policy `ff5846a` | Merge intermediate milestone reporting and continuation while preserving owner, authority, pause, and blocker boundaries. |
| NFR study `b583489` | Merge additive apparatus and report. The later `b5854f2` fixture fix is already represented by `85a9fee`. |
| Repeatable testing `bb84f1e`, `cacb778`, `6ff16e9` | Apply scoped deltas, retaining existing UI/requirements guidance and both cold-recovery test families. |
| E2E series `e68ae90`, `d2c42e0`, `2db1f21` | Import publication-reviewed apparatus content, not its unrelated ancestor history. Its runtime/support tests were already represented. |
| Ready E2E observer followup | Retain current-run-state checks, explicit exit evidence, and a real v3 intake observer-bridge regression. |
| Verified E2E terminal-exit correction | Ignore interim zero placeholders, retain explicit terminal exits, and align behavior diagnostics with both host exit-code spellings. |
| Published initial-baseline guidance `97b6269` | Preserve the repository-baseline evidence and prerequisite guidance alongside repeatable-test planning; keep both regression families. |
| Generalized discovery `004447f` | Import portable study apparatus and a publication-safe report, excluding private raw experiment evidence and original commit ancestry. |

Published main advanced to `b5854f2`, `eee78a0`, and then `97b6269` during
integration. The first two ancestry reconciliations needed no content changes;
the repository-baseline update combines its guidance and regression tests with
the repeatable-test material. Final publication must descend from the latest
remote main, not replace it.

Canonical `skills/` sources remain authoritative. Conflict resolution combines
compatible duties and assertions; `plugins/` copies are regenerated from those
sources rather than independently edited. No new ShipLoop graph nodes or parent
Improve counters are introduced by this consolidation.

## Evidence and publication boundaries

Local paths, temporary evidence locators, and run/session identifiers in empirical
artifacts are not portable public fixtures. Original raw artifacts remain local;
published summaries identify their evidence limits. Synthetic or transformed
fixtures must not be represented as untouched live observations.

The E2E apparatus and generalized-discovery study can be exercised without live
models. Their results establish test infrastructure and protocol properties, not
a successful Grok app build, consumer browser interaction, or remote deployment.
Optional retained external-product tests report skips when unavailable. See
[test runners](../test/README.md) for distinct offline and live invocation paths.

The observer correction was prompted by a failing synthetic regression derived
from an observed host-stream shape. Its fixtures distinguish an interim zero
from missing, failing, and successful terminal results. This repairs test
attribution; it does not establish that a live application run passed.

## Deliberately not imported

- Ask-agent/portable-delegation commits designated local-only.
- Original raw generalized-discovery evidence history.
- Older ShipLoop-owned review receipt/counter design superseded by standalone
  Improve and Until Loop ownership.
- Context-reset source snapshots, unapproved monitor/bootstrap branches, and
  obsolete DevLoop documentation.
- Active UI, context-clearing, test-pilot, and live E2E experiments without a
  stable completed handoff. Later outcomes remain separate changes.

Already merged or patch-equivalent branches need no additional merge merely to
clear a branch label. Dirty worktree content is separate from branch ancestry.
No source branch or worktree is deleted by this consolidation.

## Verification contract

Run affected navigator, packet, workspace, receipt, and study tests after scoped
integration. Then run the complete `core`, `shiploop-1`, `shiploop-2`, and
`shiploop-3` selections, generated-package parity, and unchanged-checkout guards.
Execute the offline E2E apparatus separately; live hosts are not CI dependencies.

The exact final candidate must pass all remote CI groups and aggregate
`hermetic` before advancing published main with a normal fast-forward push.
Recheck remote main and its post-push aggregate result. Running checks, selected
passes, and historical branch-green results do not establish final convergence.

Local recovery material is kept outside the repository. Shared uncommitted work
is preserved rather than reset or overwritten. If active work prevents local
checkout reconciliation, report that separately from successful publication.
