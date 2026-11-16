# R19: ordinary stage state belongs to its run

R19 is implemented at frozen source `053195ab37d5c9830d3d14a82ebcbf3e90a7505c` and integrated with new main at `541422e1e0b243579cb030cb09fc6422b28e7a4b`. The only production edit appends `--directory receipt.parent` in [start_command](../../../skills/shiploop/scripts/shiploop_loops.py#L481), reusing the existing `RUN/loops` directory. The formatter still creates no files or processes. No prompt, vendored runtime, schema, directory lifecycle or compatibility adapter changed. See the [production diff](author/production.diff) and [acceptance record](acceptance.json).

| Before | After |
|---|---|
| `start --receipt RECEIPT < CONTRACT` put live state in system temporary storage. | `start --receipt RECEIPT --directory RUN/loops < CONTRACT` keeps it beside its owning contract and receipt. |
| The receipt survived, but temporary backing-state loss prevented resume. | Exact generated commands resume the same live state in a fresh process; lost state still refuses completion. |

The script supplies shell-quoted absolute paths. The earlier plan's proposed `RUN/until-loop` directory was unnecessary: `RUN/loops` already exists for the contract and receipt. Random private files, token ownership, inode-specific terminal cleanup and fingerprint exclusions already support sharing that directory across distinct actions.

## Qualification and checks

| Check | Source and result |
|---|---|
| Original emitted-command red | Baseline `4ec9ac4bb7425724f41cf3abd5e1776e8fdbd596`: 1 test, 1 intended location failure, 0 errors. Formatter/runtime hashes unchanged; actual `state_file` was outside the owning run. [Receipt](author/red.json), [raw output](author/red.log). |
| First focused attempt | 6 tests, 1 failed fixture assertion, 0 errors. The author expected a history append; existing document completion instead increments the revision and opens Improve. The corrected test checks that actual transition. Production remained unchanged. [Receipt](author/focused-attempt-1.json), [raw output](author/focused-attempt-1.log). |
| Focused recovery and admission | All 6 touched methods pass, 0 failures/errors. Four new methods and two extensions execute real emitted launches, recovery and callbacks. [Receipt](author/green.json), [raw output](author/green.log). |
| Existing command consumer | On clean `f4055d2`, 2 tests, 1 exact-string failure, 0 errors/skips. The independent native probe retained the old expectation's failure. [Receipt](reader-pin-probe/receipt.json), [raw output](reader-pin-probe/stderr.log). |
| Consumer expectation repair | Only its expected command string changed; all glue/edit/commit/next classification assertions remain. Both methods pass, 0 failures/errors/skips; formatter hash unchanged. [Verification](pin-repair/verification.json), [diff](pin-repair/repair.diff). |
| Final affected bank | On clean `053195a`, all 8 full modules pass: 524 unittest executions, 0 skipped tests. Ruff F/E9 and scoped whitespace pass. No retries or source changes. [Native handoff](validation/handoff.json). |
| Independent source review | Fresh read-only Astra/high session: APPROVE, exit 0; its source snapshot unchanged. It ran no tests. [Review](final-review.md), [launch](final-review-launch.json), [exit](final-review-exit.json). |

| Full module at `053195a` | Passing executions |
|---|---:|
| `test/shiploop-loops.test.py` | 67 |
| `test/shiploop-e2e-fidelity.test.py` | 149 |
| `test/shiploop-callback-contract.test.py` | 117 |
| `test/shiploop-actual-improve-cli.test.py` | 104 |
| `test/shiploop-rehydration.test.py` | 17 |
| `test/shiploop-head-order.test.py` | 36 |
| `test/shiploop-packet-bounds.test.py` | 21 |
| `test/improve-runtime.test.py` | 13 |

The full-bank total counts executions, not deduplicated tests. The focused checks and pin repair overlap the final modules and are not added to that total. Native source inventories and raw stdout/stderr accompany the [validation record](validation/handoff.json); large original inventories and the subprocess trace stay external with hashes in [external-evidence.json](external-evidence.json).

The real `check` → exact runtime `done_argv` → parent `complete` control admits the producer once, increments its revision and opens the required document Improve checkpoint. It does **not** complete that review. Synthetic predecessor preparation and helpers that bypass the launcher remain fixture setup, not the state-location oracle.

Active restart refuses before replacing a receipt. After fixture-owned backing-state deletion, exact `next_argv` errors, restart still refuses, and parent completion leaves state unchanged. Two distinct live actions in one run and another run keep separate files/tokens; crossed tokens refuse, and ending one preserves the others' exact resume commands and bytes. Missing-contract recovery emits a working run-owned launch. Existing stale/failed-check, copied/live-receipt and unbounded-loop controls remain in the affected modules.

## Integrated main checkpoint

Main advanced during the frozen bank. Merge `541422e` integrates checkpoint `477542e` (skill-craft 2.42.1 / ShipLoop 1.37.1), preserving the source commits. Its production delta is the separately owned no-child Backchain graph-input wording fix; it changes no R19 runtime or receipt behavior. [Source continuity](integration-source.json) proves 13 reviewed runtime/test path hashes unchanged; [anchor continuity](integration-anchor-changes.json) retains all 220 frozen source excerpts exactly. The owner closed the fan-out study; the separate adapter remains unbuilt.

The merged-source checks pass **113 executions**: four full prompt/Backchain modules plus eight selected R19 methods, without skips. Release-boundary passes. The original integration bank is **FAIL** because its broad whitespace check reports an incoming adapter-plan blank line at EOF; its tests and source hygiene pass. The R19-only whitespace check is recorded separately. This preserves the original failure, without editing the other plan or relabeling the frozen 524 executions. [Native integration handoff](integration-validation/handoff.json). The fresh read-only [integration review](integration-review.md) approves this merged source and runs no tests.

## Source anchoring and limits

The [source map](source-map.json) rechecks every recommendation, eight considerations and fourteen Code craft rules: **222 spans across 48 files**. It retains 209 of 211 prior excerpts exactly; 28 prior anchors moved. The two changed excerpts are upstream `_prompt_parts` (Backchain child calls now optional) and R19 `start_command`. Seven regression anchors, two previously unmapped source links and two upstream decision/input-contract anchors are added. The [comparison](anchor-changes.json) records the changes; the [plan](../../shiploop-implement-step-fix-plan-2026-10-17.md) retains all 22 IDs and T1–T52. Earlier R05/R07/R08/R21 evidence is unchanged.

Run removal or absolute-path relocation still loses resumability. Same-receipt concurrent-start atomicity is not newly qualified; these tests cover distinct live receipts. The existing “second start resets” wording is misleading and remains untouched. Terminal cleanup still intentionally deletes the private backing file after retaining its receipt. R19 changes placement and proves the recorded boundaries; it does not reconstruct lost state or certify a deployed package, real person, installed host, CI, model reliability, speed or a full repository suite.

Implementation and pin repair used fresh explicit Sol 6.1/medium CLI sessions; design advice and final review used fresh Astra/high sessions. [Launch controls](model-controls.json) record actual flags and successful exits. They establish requested routing, not independent provider-served identity. No alternate model or fallback was used. The unrelated upstream E18 recovery experiment changes no ShipLoop policy here.

Next implementation is **R16**, then R15 and R17. Markdown links, anchored bytes and structure are checked; rendered Markdown appearance was not inspected. No push, release, deployment or host refresh occurred.

Final main checkpoint `038d678654affd134031ae3bf4a8dc37a4d592b0` changes only the E2E host scaffold and its tests/docs. The [final continuity record](final-source-continuity.json) preserves all 222 excerpt bytes and all 13 reviewed R19 file hashes, with the host anchor relocated. No fresh host/keychain/Chrome qualification is claimed by this R19 task.
