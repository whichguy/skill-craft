# R05 inherited-procedure qualification

**Retain the current prompts. All 16 primary subjects passed procedure diagnosis and disposition; no R05 semantic miss justified a production repair.** Twelve also completed the real callback protocol; four original protocol results remain **INCOMPLETE**. Four separately registered fresh follow-ups use corrected qualification permissions. All four follow-ups independently pass diagnosis, disposition and real callback acceptance; they do not regrade the original bank.

The [plan](../../shiploop-implement-step-fix-plan-2026-10-17.md#r05--valid-inherited-procedures) now treats this scoped qualification as complete and puts R19 next. [Structured acceptance](acceptance.json), [independent judgments](judgments.json) and [exact subject inputs, native finals and execution receipts](native-results.json) keep semantic behavior separate from callback completion. No production code, prompt, default, schema or loop changed, so there is no new production regression test.

## What the qualification exercised

One neutral local record package exposes the same operations through its library and CLI. Its written rule requires an existing record for update/get/delete; a missing record returns `NotFound` without mutating state or revision. Normal setup creates `sample`; an optional setup flag then clears it. A separately declared owner-terminal observation is unavailable to the host; every underlying package operation remains callable.

The primary registration froze four situations × two actual boundaries × two fresh repetitions before subject calls. Subjects received the normal generated assignment, not a hand-written review-focus excerpt. Carry-forward assignments ran the real bound Improve runtime; release-verify assignments used normal check/complete or valid add-work callbacks. Predecessors were synthetic setup through the locked `apply` / `finish_improve` / [accept_effects seam](../../../skills/shiploop/scripts/shiploop_navigator.py#L10074), which explicitly does not establish full end-to-end execution.

| Situation | Behavior the subject had to establish | Primary diagnosis / disposition | Primary protocol |
|---|---|---:|---:|
| Changed setup | The old update/get observation really worked. Current setup clears the record; the first expected update cannot succeed. Correct the procedure or an optional setup choice, then obtain current evidence. | 4/4 PASS | 4/4 PASS |
| Unchecked helper | Deleting the record makes the next expected update invalid. A helper that blindly applies actions produces a plausible result but cannot establish permission. | 4/4 PASS | 3 PASS, 1 INCOMPLETE |
| Inherited review case | The same invalid sequence is inherited from a seeded earlier review artifact. Detect it without credit for inventing it. | 4/4 PASS | 2 PASS, 2 INCOMPLETE |
| Valid control | Preserve update/get and the legitimate expected missing-record rejection. Host success does not fabricate the separate owner observation. | 4/4 PASS | 3 PASS, 1 INCOMPLETE |

All eight release-verify assignments reached accepted correction routes or valid awaiting requests. Four carry-forward assignments completed acceptance in the primary bank; four stopped around snapshot/receipt handling. The latter are safe incomplete outcomes, not successful advancement. Some accepted primary reviews disclosed uncommitted edits; callback acceptance is not a committed-delivery claim.

The independent judges read complete tool traces, including shell and `node_repl` operations, and resulting records. A flaw found only by a judge cannot earn subject success. No prohibited sibling, private-proof, operator-analysis or unrelated-chat read was observed. The [supplemental locator screen](trace-audit.json) is a second check, not proof of OS isolation.

## The before and after decision

The [shared planning walk](../../../skills/shiploop/scripts/shiploop_prompts.py#L691) already requires deciding transitions to be permitted by specification rules, recomputes derived outcomes, rejects unchecked helpers and includes cases a review adds or changes. [Focus selection](../../../skills/shiploop/scripts/shiploop_navigator.py#L8212) gives carry-forward its own code-review focus instead of copying that walk.

**Before — an excerpt of the current final-review opening:**

```text
Across every executed work item's change, trace
each new or changed public entry point with a valid, a boundary and an invalid
input
```

**After — retain it verbatim.** This was the wording qualified through the real assignment. Missing an explicit copy of the walk did not reproduce a semantic miss. No before/after prompt-quality or token-efficiency comparison was run.

For release-verify, retain the existing [wrong-plan send-back duty](../../../skills/shiploop/scripts/shiploop_prompts.py#L1841) and [affected-observation invalidation duty](../../../skills/shiploop/scripts/shiploop_prompts.py#L1874). Their current wording includes:

```text
A release plan that is wrong or missing a step ... is a send-back

A material change to code, tests, fixtures, configuration or target invalidates
the observations it affects
```

These are shortened excerpts; the [source map](source-map.json) retains exact full spans. The qualification supports keeping the shared planning rule and existing later-stage duties. It does not support another procedure schema, symbolic grammar, result form or nested loop.

A concrete generic fixture illustrates the required distinction:

| Recorded procedure or evidence | Current checked interpretation |
|---|---|
| Earlier setup created `sample`; update/get showed `ready`. | Valid historical lower-layer evidence, not an owner observation. |
| Current setup clears `sample`, but the inherited procedure still expects update to succeed. | First invalid expectation: update. `NotFound` is the specified behavior. |
| Delete `sample`, then use unchecked replay to predict successful update/get. | Reject that oracle. Repair prerequisites or expected rejection, preserving the existing-key rule. |
| A repaired local procedure now passes. | Current local semantics can be recorded. The separate required owner-session observation stays unperformed. |

## Why four callbacks were incomplete

The [original interrupted attempt](registration/registration.json) launched six of sixteen subjects: three have complete execution receipts, three were interrupted, and ten were not launched. Installed whole-run keepalive kept scoped workers going after their assigned boundary. The controller stopped only its own processes and preserved all output. Two completed cells received independent passing judgments; these do not replace the primary bank. The second registration used the existing per-run `SHIPLOOP_KEEPALIVE=off` control, honored by [disabled](../../../skills/shiploop/scripts/shiploop_keepalive.py#L91) and [run_hook](../../../skills/shiploop/scripts/shiploop_keepalive.py#L654). No global hook or setting changed.

The full primary bank then collected all sixteen subjects in 1,230.531 seconds wall. Four Improve callbacks reported “no bind snapshot” and did not reach accepted parent completion. Frozen inventories show that all four initial bindings actually existed. Some original judge explanations repeated the diagnostic as a missing initial binding; the inventory and focused probes correct that causal interpretation without changing the original protocol scores. [review_changes](../../../skills/shiploop/scripts/shiploop_improve_changes.py#L157) also returns unknown when the **current** snapshot fails; the [snapshot helper](../../../skills/shiploop/scripts/shiploop_improve_changes.py#L50) catches that failure, and [improve-commit](../../../skills/shiploop/scripts/shiploop_navigator.py#L9405) refuses unknown changes.

Two focused disposable probe pairs reproduced the cause: `workspace-write` denied inserting a new file into the Git object database with `Operation not permitted`; `danger-full-access` wrote the private snapshot successfully. A private index protects the user's index but [still needs Git object writes](../../../skills/shiploop/scripts/shiploop_lint.py#L494). The production [Codex harness launcher](../../../test/shiploop_e2e/hosts.py#L469) already supplies `danger-full-access` and `approval_policy="never"`. The qualification launcher was corrected to match it for four fresh, owned disposable fixtures. It changed no shipped launcher or product gate.

[Transport evidence](transport.json) preserves raw errors, existing-bind checks, both probe pairs and the first probe controller's reporting failure. Both first-pair CLI calls completed; a process-global stdout redirect made the controller fail afterward. The corrected sequential-seed controller repeated both probes successfully. Setup/preflight failures remain in [retained attempts](retained-attempts.json); none is counted as a behavioral miss.

The [follow-up registration](registration/registration-003.json) covers only `cell-05`, `cell-09`, `cell-10` and `cell-14` with fresh repositories/runs and unchanged semantic source/scoring. All four completed in 544.714 seconds wall; fresh independent judgments pass all three axes. Each real runtime reached `complete`, the parent accepted the final result and advanced to `system-test-author`, and the owner observation remained unperformed. It is not a new all-green sixteen-cell primary bank, and it is not a performance comparison or an in-place retry.

## Source identity, checks and limits

Subjects used frozen source `e596e6734f59590e2b4c6e65bea71a868675924f`. [Pre/post inventories](source-stability.json) cover all 13,337 tracked hashes and modes in each completed bank, with HEAD/status unchanged. Independent judges also retained identical pre/post evidence hashes. Explicit fresh CLI controls requested Sol 6.1/medium for subjects and Astra/high for judgments. Named profiles were requested but absent in local readback; explicit model/effort arguments governed. These are launch controls, not a separately attested provider-served model identity.

The separate evidence checkout integrates published-main checkpoint `4df66f687caf24b9919238c63ba579a2d871eaef` at `59d4af8524f24c3c20a9dd90aa194167342663e1`. [Integration comparison](integration.json) verifies every pre-existing skill file unchanged from qualification. Of 43 previously anchored files, 42 are byte-identical; one background E18 registration README changes its full-file hash while retaining the cited A14/E17 excerpt. The [current source map](source-map.json) verifies **211 spans across 46 files**: the earlier 202 spans plus nine qualification-transport anchors. All 22 recommendation IDs, eight considerations, fourteen craft rules and T1–T52 remain accounted for; R07/R08/R21 evidence directories are unchanged. The incoming Closed Loop 0.1.0 leaf/release is separate upstream work; its ShipLoop adapter remains future work and R05 adopts no new orchestrator. The [first integration](integration-001.json) and [release integration](integration-002.json) remain separately recorded. E18 has registered a separate recovery replay, not a scored comparison or ShipLoop policy decision.

The fresh [closure review](closure-review.md) approves the scoped decision at `e123ec86156ad659dcc19cfa4c46cf5398b78a51` and independently verifies all 211 spans against both source identities. Its [launch](closure-review-launch.json) and [exit](closure-review-exit.json) retain the requested Astra/high controls and unchanged evidence hashes. The later published-main merge changes none of those code spans or pre-existing skill bytes; the parent refreshed source pins, the background README hash/location and the release/registration-status sentences, preserving the reviewer's actual inspected revision.

Existing [ProcedureFixtureTests](../../../test/shiploop-guidance.test.py#L3047) remain deterministic coverage; they are not counted as these model observations. No production regression or broad unchanged suite was rerun for this documentation-only decision. The [document check](document-check.json) verifies current code excerpts/hashes, registrations, outcomes, subject input hashes, callback evidence, source stability, local links and plan references. [Validator](validate_evidence.py). Markdown was not visually rendered.

This qualifies one package, one host and the registered boundaries. The seeded prior-review artifact is not a case invented by the subject. The synthetic owner-session requirement qualifies preparation/awaiting only; no person response, deployment, authenticated service, isolated delivery or installed-host distribution was observed. There is no statistical efficacy or performance claim. Reopen R05 for a coherent semantic miss or a new boundary that the evidence needs to cover. Larger raw transcripts and inventories stay at the hashed local locators in the [external manifest](external-evidence.json).
