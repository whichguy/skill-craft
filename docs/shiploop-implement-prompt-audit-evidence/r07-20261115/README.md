# R07 recorded-outcome continuity

**R07 is implemented for explicitly recorded outcomes. Thirteen complete affected suites passed 1,204 test executions at frozen `9ae4fc221e6876545be8b9a33a60eb6d6bf096db`.** Qualification preceded runtime edits. The [closure review](closure-review.md) approved that source by inspection. Current source `5d2e978614e4a100ffa04ee32e49ff054ce52dd2` also passes six full consumer modules and all twenty R07 regressions after the newer-main merge, with [independent merge approval](integration-review.md). [Acceptance record](acceptance.json). Earlier failed candidates and fixture mistakes remain separate evidence.

The change adds one optional result field, `settled`, required only when a submitted result removes a prior pending outcome. Each row has four fields: `requirement`, `outcome`, `basis` and `evidence_refs`. The rule is exact: settlement identities must equal prior pending identities minus submitted pending identities. Identity remains the existing normalized requirement/outcome pair. There is no new ledger, migration, cache key, loop, timer, schema version or default adoption.

| Admission boundary | Reproduced failure before repair | Current behavior and source |
|---|---|---|
| Revisited product acceptance | Actual callbacks reached terminal `done` after erasing both outcomes or only the unanswered outcome. | Attribute each removal; acceptance can settle an outcome early. [check_restated](../../../skills/shiploop/scripts/shiploop_unverified.py#L134). |
| A later due stage | Removing the row despite an unchanged partial reply reached terminal `done`. | Require its settlement at its previous due stage; carry or defer genuinely pending rows. [check_restated](../../../skills/shiploop/scripts/shiploop_unverified.py#L134). |
| Matching cached yes | A pre-rule answer bypassed continuity; later, deleting a nested local evidence file still admitted a real cached answer. A refused answer also retained a stale yes. | Recheck evidence and continuity before consuming the answer; record the current refusal as no. [Cached admission](../../../skills/shiploop/scripts/shiploop_navigator.py#L10363). |
| Improve result import | An explicit final result could drop pending rows. A settled seed could also import after its evidence file disappeared during review. | Validate the effective seed or explicit final result, then continuity, before acceptance. [Import admission](../../../skills/shiploop/scripts/shiploop_navigator.py#L10205). |

The existing marked-contract two-outcome partial/declined reply → add-work → remaining observation route and authorized scope-correction route passed before any delivery-guard repair. They remain positive controls. Their independent contract, authority, correction and fix-forward gates were preserved.

## The small prompt/result change

The earlier instruction allowed a due row to disappear when settled, but did not require an attributed settlement. The [current shared rule](../../../skills/shiploop/scripts/shiploop_navigator.py#L7552) asks the host to carry pending outcomes and record removed outcomes in `settled`; the [stage contract](../../../skills/shiploop/scripts/shiploop_stage_spec.py#L529) also recognizes explicit user correction on a revisit. A revisit [prefills the latest pending list](../../../skills/shiploop/scripts/shiploop_navigator.py#L5543), with an empty settlement list.

For one previously pending outcome, the old submission could be only `"unverified": []`. After a current observation, the new submission includes:

```json
{
  "unverified": [],
  "settled": [{
    "requirement": "R-1",
    "outcome": "A reader opens the generated export",
    "basis": "observed",
    "evidence_refs": ["RUN/reader-observation.md"]
  }]
}
```

This is an illustrative result excerpt, not evidence of a real observation. A row still awaiting observation stays in `unverified`. An explicit user correction uses `basis: "user-correction"` and references that correction. The [plan's before/after example](../../shiploop-implement-step-fix-plan-2026-10-17.md#recorded-acceptance-explicit-settlement-on-removal) shows the corresponding prompt and result excerpts. Neither form certifies initially omitted requirements or authenticates a declaration.

## Qualification, regressions and retained failures

The [initial qualification](qualification.json) ran six methods on baseline `781d5eca4b82dd3b9783147271f8281bfbc2e9a8`, with runtime hashes unchanged: three passes and three terminal-omission failures, with zero execution errors. One positive pass had inconsistent later-summary wording and was superseded. After fixture corrections, the two affected controls passed and the affected negative still reproduced the omission, before runtime edits. These attempts and the later strengthened assertions remain in [all test attempts](retained-attempts.json). Negative tests now assert the attempted deletion's specific refusal in both `check` and `complete` and unchanged accepted state; an unrelated later refusal cannot count.

There are [20 new regression method definitions](new-regression-methods.json). Coverage includes exact/duplicate/overlapping identities, invalid settlements, early observation/correction, due-stage settlement, mixed carry, deferral, first empty acceptance, latest-list revisits, reopening, honest pending handoff, nested references, cached completion and both Improve import forms. Save/load and reporting preserve accepted declarations and identify historical unattributed removals without inventing observations. [Report projection](../../../skills/shiploop/scripts/shiploop_unverified.py#L236).

Two independent reviews initially declined approval. The [first](final-review.md) identified missing cached evidence checks and stale yes records; the [repair handoff](review-repair-handoff.json) retains two valid red assertions and a passing unchanged-file control before repair, then nine passing targeted methods. The [second](approval-review.md) identified the seed-import evidence gap. The [recovery handoff](integration-recovery-handoff.json) separates the valid red reproduction from earlier invalid non-Git/identity fixture attempts, and records restored-file and unchanged-file controls after repair. One author session failed with an API Bad Request; a fresh session with the same requested Sol 6.1/medium controls completed the scoped work.

The [first established quick bank](first-validation/terminal-summary.json) ran at `dbd2a47f3dd52fc939620e6481cc64f486630075`: **41 selected/completed, 39 passed, two failed**, no skips or cancellations, 1,752.59 seconds wall. Its guide asserted the old empty-list wording and its generated-refusal classifier reported the new refusal as `other`. Both are repaired; the original FAIL remains frozen. The classifier adaptation is E2E apparatus reporting support, separate from generic runtime admission, and changes no historical trial verdict.

The reference is 8,189 bytes under the unchanged 8,192-byte bound. Oversized drafts and a new test-only subprocess lint finding were repaired and retained. Final differential Ruff reports no added diagnostics; raw nonzero exits and inherited findings are not called a clean whole-file lint run.

## Final validation

The [13-module bank](validation/handoff.json) completed at `9ae4fc221e6876545be8b9a33a60eb6d6bf096db`: 1,204 executions, no skips or retries, 1,104.543 seconds wall. Boundary returned explicit `OK`; R07-scoped whitespace passed. HEAD, all 12,980 tracked SHA256/mode entries and all twelve supplied hashes stayed fixed; ordinary and ignored status stayed clean, with no unexpected outputs. The [parent audit](full-bank-parent-audit.json) independently checks raw terminal counts and inventory equality.

| Full module | Executions | Result |
|---|---:|---|
| `shiploop-callback-contract` | 117 | PASS |
| `shiploop-actual-improve-cli` | 104 | PASS |
| `shiploop-consumer-delivery` | 34 | PASS |
| `shiploop-consumer-delivery-cli` | 5 | PASS |
| `shiploop-navigator-contract` | 149 | PASS |
| `shiploop-guidance` | 87 | PASS |
| `shiploop-e2e-analysis` | 299 | PASS |
| `shiploop-head-order` | 36 | PASS |
| `shiploop-package-integrity` | 11 | PASS |
| `shiploop-handoff` | 170 | PASS |
| `shiploop-knowledge` | 163 | PASS |
| `shiploop-rehydration` | 17 | PASS |
| `shiploop-stage-spec` | 12 | PASS |

Automatic quick selection at that integrated snapshot was 108 suites; that selection was recorded, not executed. The explicit bank is not a full repository, CI or live-host qualification. The [newer-main bank](integration-validation/terminal-summary.json) passes all nine commands: six complete affected consumer modules (350 executions) plus all twenty R07 definitions in three targeted commands, 370 executions total, in 308.709 seconds wall. No skips or retries; boundary explicitly reports `OK` and scoped whitespace passes. All 13,001 tracked hashes/modes and all twelve supplied source hashes stay fixed; ordinary/ignored status and private XDG directories remain clean. These counts describe executions and are not deduplicated across banks.

The closure and merge reviewers each used a separate fresh `shiploop-judge` session with explicit Astra/high launch controls, verified the supplied hashes before and after inspection, and ran no tests. [Closure launch](closure-review-launch.json), [closure exit](closure-review-exit.json), [merge launch](integration-review-launch.json), [merge exit](integration-review-exit.json). These records establish requested routing, not a separately attested provider-served model identity.

## Plan, integration and limits

The [plan](../../shiploop-implement-step-fix-plan-2026-10-17.md) marks recorded-outcome continuity implemented and keeps R05 inherited-procedure qualification next. All 22 recommendation IDs, eight considerations, fourteen Code craft rules and T1–T52 remain accounted for. The [current source map](source-map.json) refreshes 202 exact spans across 43 files; [anchor changes](anchor-changes.json) retain the old excerpts and relocation decisions.

The first main merge at `b0285785374570c88f534480cf361778030018ac` preserved all twelve R07-owned paths byte-identically, as [recorded](integration.json). The later published release `fe0e6ca39435d502bd0b8afd3ce300ff731e5683` is now integrated. [Post-release comparison](post-release-integration.json) preserves ten paths byte-identically; the two shared source files change only Backchain functions/instructions, with all R07 admission functions unchanged in AST comparison. Its starting-bytes knowledge fix is included in the final knowledge suite. Its E17 bare-worker study, release and new-skill plans retain their own scope and decisions; this change adopts neither a fan-out default nor those planned skills. Earlier R08/R21 receipts remain at their actual revisions.

References use existing root expansion and absolute local-file existence rules. URLs and other locators are not authenticated; an existing file does not prove truth, freshness, surface adequacy or user authority. The runtime preserves recorded pending outcomes; initially unrecorded outcomes and dishonest declarations remain review duties. An honestly pending outcome can still reach handoff. No live platform, installed host, deployment, publication, performance gain or prompt-quality comparison is claimed.

The [external manifest](external-evidence.json) hashes larger raw inventories and launch transcripts. Markdown was not visually rendered; the document validator checks links, fences, current source bytes and retained acceptance records. The [document-check result](document-check.json) is retained. It runs from the repository root with `python3 -B docs/shiploop-implement-prompt-audit-evidence/r07-20261115/validate_evidence.py .` and does not execute runtime tests.
