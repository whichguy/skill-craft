**Approve the proposed approach.** At `2a6514d6219a60bea080b4114f3e3433eec0f774`, it closes the identified R08 bypasses without another version registry or history migration. This is a source review; no edits, suites, advisors, or delegation were performed.

The necessary changes are:

- **Keep errors out of `ran`.** In [`shiploop_test_counts.py — _pytest`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_test_counts.py:60), compute executed tests using the existing failed/passed/xfailed/xpassed terms, then add `errors?` only to `failed`. Simply enlarging `failed` before the existing `ran = failed + …` calculation would incorrectly inflate execution counts and floors.
- **Reject stale receipts at both reuse predicates.** Set `SCHEMA` to `shiploop-test-loop/v2`; require exact equality in [`_reused`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_test_loop.py:1389) and [`step_proof`’s `matched` selection](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_test_loop.py:1662). The latter must cover both check and numbered Proof receipts.
- **Include `test_loop.SCHEMA` in [`answer_key`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_check.py:42).** This is essential: [`complete`’s matching-answer branch](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_navigator.py:10334) bypasses both reuse predicates and evaluation entirely.

[`matching_yes`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_check.py:100) already compares the complete key. Therefore an old or missing schema key invalidates the answer even when package version, draft, tree, and state remain unchanged. [`take_check`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_test_loop.py:1370) needs no additional R08 change: its sole production caller reaches it only after that match. A guard that merely skips copying stale records there would be insufficient—the callback would still accept the cached yes.

Compatibility and history consequences are bounded:

- Leave [`judge`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_test_loop.py:836)’s ordering unchanged: zero tests, declared minimum, missing IDs, then masked failure. Historical floors are applied afterward only to otherwise-passing runs; do not move that logic.
- Preserve old records in `accepted_counts`, `action_counts`, and refusal history. Schema filtering belongs at **reuse**, not historical count readers. Since pytest’s `ran` calculation remains unchanged, retaining historical floors does not introduce error-count inflation.
- The shared parser also makes `_judge_base`’s no-ID path classify masked pytest errors as `red`. That follows the existing decision in full commit `b446994cfbf3ad40c08cfa4ed6b926213175623e`; it does not require a `BASE_SCHEMA` bump or new base policy.
- Rerun stale receipts rather than rejudge them: [`_run_command`](/Users/dadleet/src/skill-craft-r08-20261115/skills/shiploop/scripts/shiploop_test_loop.py:1324) judges full output but stores truncated streams.

The full messages of `5fb2978401b12278839670a9e1024a478989518e` and `5086baf688a611172003e0fac4417dba06bb4e0c` support preserving masked-failure refusal and valid check reuse respectively.

Use the existing callback fixtures around [candidate/whole-answer reuse](/Users/dadleet/src/skill-craft-r08-20261115/test/shiploop-test-loop.test.py:2750), [Proof reuse](/Users/dadleet/src/skill-craft-r08-20261115/test/shiploop-test-loop.test.py:2986), and [masked failures](/Users/dadleet/src/skill-craft-r08-20261115/test/shiploop-test-loop.test.py:4177):

| Fixture | Required result |
|---|---|
| Parser: `1 passed, 1 error`; `1 failed, 2 passed, 2 errors`; error-only | `(ran, failed)` = `(1,1)`, `(3,3)`, `(0,N)` |
| Mixed output, exit 0; focused, regression, check | Refused; `failed` when no earlier refusal applies. Clean pass still passes. |
| Error-only; mixed output below `min_tests`; mixed output missing an ID | Preserve `no-tests`, `too-few-tests`, `ids-missing` respectively. |
| Current-schema whole-answer yes | Callback advances with no command execution; counted receipts retain reuse provenance. |
| Current candidate receipt, whole-answer deliberately invalidated | `_reused` still avoids execution. Use a draft-only change to isolate this path. |
| Candidate receipt with literal v1 or absent schema | Callback runs commands; mixed output refuses, writes v2 without `reused`, and leaves acceptance state unchanged. |
| Proof receipt: check **and numbered**, each current/v1/absent schema | Bypass the whole-answer cache. Current receipts reuse; stale receipts rerun and mixed output refuses. Keep only the intended eligible receipt. |
| Whole-answer key with old or absent schema; unchanged package version | `matching_yes` misses and callback evaluates again. Seed stale subordinate receipts too, so the fixture proves actual execution and refusal. |
| Historical v1/schema-less count records | Existing accepted/action floors remain effective; schema change does not reset history. |

For stale-receipt fixtures, retain matching tree, command, step, and other bindings, and seed `passed=True`; otherwise they may pass without exercising the vulnerability.

R21 external freshness, other reporters, retry aggregation, and new prompt text remain deferred. No concrete R08 bypass found here requires expanding that scope.