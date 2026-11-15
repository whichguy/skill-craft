Approve the bounded repair, with one qualification: **existing declarations support a conservative reuse policy, not proof of hermeticity.** HEAD matches `856938eb342a3da09156fe6c333439606c694a7b`. No files edited, tests run, advisors consulted, or agents spawned.

`shiploop_test_layers.canonical_targets` validates `keeps_state` and `base_state_route`; neither establishes that all inputs reside in the checkout. `keeps_state=no` describes persistence between runs, not locality. Conversely, rejecting every named target would unnecessarily reject named checkout targets. `f04cbdde` explicitly preserves target omission for checkout commands.

Use one shared predicate in `skills/shiploop/scripts/shiploop_test_loop.py`, evaluated against **current declarations before selecting any reusable record**:

- Always return false for `release-verify`.
- Reject the whole command set if any row is `host_dependent`, matches `shiploop_mutation.remote_card`, or names an unknown, conflicting, or `keeps_state=yes` target.
- Permit a named `keeps_state=no` target absent those vetoes, explicitly as declaration-based eligibility.
- Ordinary targetless command rows retain their documented checkout meaning.
- **Proof needs stricter contextual treatment:** `step_command` synthesizes only `{command, suite}` from free-text Proof; missing target there is not an affirmative checkout declaration. Deny Proof reuse when the strategy contains stateful targets or the item’s recorded commands identify host-dependent, remote, or unresolved targets. Retain reuse for checkout-only contexts.

This intentionally over-invalidates some local Proofs in mixed environments. It adds no mandatory field or command parser. Arbitrary undeclared external reads, ignored dependencies, and environment changes remain outside what these declarations can establish.

Apply the predicate at these boundaries:

| Boundary | Required change |
|---|---|
| [shiploop_test_loop.py — `verify` / `_reused`](/Users/dadleet/src/skill-craft-r21-20261115/skills/shiploop/scripts/shiploop_test_loop.py:1389) | Gate candidate check-receipt reuse using the actual supplied commands, including review overrides. One unsafe row reruns the whole record. |
| [shiploop_test_loop.py — `step_proof`](/Users/dadleet/src/skill-craft-r21-20261115/skills/shiploop/scripts/shiploop_test_loop.py:1639) | Gate selection from both check and numbered receipts; an older pass must not rescue an uncertain Proof. |
| [shiploop_navigator.py — `dispatch`](/Users/dadleet/src/skill-craft-r21-20261115/skills/shiploop/scripts/shiploop_navigator.py:10333) | Explicitly gate `shiploop_check.matching_yes` before `take_check`. Merely adding `eligible=False` to an equality key still permits two false keys to match. |
| [shiploop_mutation.py — `_reusable`](/Users/dadleet/src/skill-craft-r21-20261115/skills/shiploop/scripts/shiploop_mutation.py:429) | Additional reuse layer: apply eligibility to mutation observation inputs; preserve remote exclusion and local disposition-only reuse. |

Base execution has no separate reuse shortcut beyond `take_check`. `verify` also short-circuits `default_suite_drift`; the host-dependent veto must prevent that. `_document_rerun` and `_improve_change_gate` separately omit execution after unchanged source: those are scheduling rules, not receipt matching. Preserve them and bound the freshness claim to checks actually owed at completion.

Keep R08’s single v2 schema and existing tree, command, floor, draft, and provenance controls. Update the unconditional “callback takes this answer” explanation.

The smallest concrete acceptance matrix belongs beside the existing reuse tests in `test/shiploop-test-loop.test.py`:

| Fixture | Required observation |
|---|---|
| System-test: stateful target; repeat with whole answer present/deleted | Passing check; sibling target changes; real `dispatch(... complete)` executes and refuses. |
| Host-dependent, known-remote, unknown-target eligibility cases | Each independently prevents reuse; mixed local/external records rerun whole. |
| Targetless Proof in external context: check receipt / numbered receipt | Both rerun/refuse; use the existing later `_step_spec_refusal` pattern to retain the action for numbered receipts. |
| Release-verify, including returned-result fixture | Whole answer cannot hide changed external outcome; fresh observation recorded. |
| Authority fixture: allowed → permission-denied | Live nonzero denial surfaces; claim observed denial only, not semantic permission validation. |
| Unchanged checkout: unnamed / named `keeps_state=no` | Candidate, Proof and whole-answer reuse retain provenance; local mutation dispositions still reuse. |

Use a fixed command reading a sibling file outside the Git tree. Wrap the real runner to count executions. Hold action, draft bytes, repository tree, and command constant; assert unchanged state after refusal, fresh failed receipt, and absent `reused`. Retain existing R08 controls.
