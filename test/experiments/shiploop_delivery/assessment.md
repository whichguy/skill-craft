# Consumer-delivery teachback assessment

**Assessor:** independent read-only review

**Date:** 2026-09-15

## Scope and method

I read every raw response under `responses/A`, `responses/B`, and
`responses/B2`, and compared it to the corresponding frozen packet under
`packets/<variant>` and the fixed primary requirements in `oracles.json`.
This is a qualitative, predeclared-oracle grading record. It does not treat a
filename, an asserted outcome, or the number of requested agents as evidence of
success.

The primary score checks only each scenario's `must` and `must_not` facts. The
release-plan timing test discovered after the A/B preregistration is reported
separately. In particular, an interpreter is not penalized in the primary
score merely because the read-only exercise cannot perform later release work.

| Variant | Primary sentinel result | Exploratory release-plan phase order |
| --- | --- | --- |
| A | 12/12 passed | 0/4 passed; 4 timing conflations |
| B | 12/12 passed | 0/4 passed; 4 timing conflations |
| B2 | 4/4 passed (two retained scenarios) | 4/4 passed |
| C | 2/2 packet-specific recovery observations passed | Not a release-plan phase-order sample |
| C2 | 1/1 current-renderer recovery observation passed | Not a release-plan phase-order sample |

Thus the frozen B wording did not change the primary six-sentinel outcome in
this small sample. The strengthened B2 release-plan wording corrected the
separate planning-versus-later-execution interpretation in all four follow-up
responses. This is not a statistical result or proof of real deployment
behavior.

## Per-response primary grading

`P` is the fixed primary oracle. `Phase` is only the later exploratory
release-plan criterion; `—` means it is not one of its two scenarios. Excerpts
are short locating context, not substitutes for the raw responses.

| Variant | Scenario / repetition | P | Phase | Evidence from raw response |
| --- | --- | --- | --- | --- |
| A | ambiguous-existing-hosted-ui r1 | Pass | — | Asks whether the work is local-only or must reach the private page; asks for target/authority; no remote action. |
| A | ambiguous-existing-hosted-ui r2 | Pass | — | Calls the hosted page a decision point and requests scope, target, and remote authority. |
| A | approved-private-sync r1 | Pass | Fail | Plans only `private-development-head`, preserves the interaction check, and excludes promotion/public access; but says `done` requires the later sync and visual evidence. |
| A | approved-private-sync r2 | Pass | Fail | Retains the permitted sync and post-sync interaction check; nevertheless blocks plan completion on later effect/behavior evidence. |
| A | explicit-source-only r1 | Pass | — | Calls hosted release non-applicable and limits work to local source/tests/docs. |
| A | explicit-source-only r2 | Pass | — | Retains source-only scope and says no target/rollback plan is authorized. |
| A | identity-without-visual-verification r1 | Pass | — | States that sync, identity, and source strings do not establish interaction; visual observation remains needed. |
| A | identity-without-visual-verification r2 | Pass | — | Requires an actual page interaction tied to candidate identity; does not call it verified. |
| A | login-after-upload r1 | Pass | — | Preserves successful sync/identity, requests a permitted login path, and says not to repeat synchronization. |
| A | login-after-upload r2 | Pass | — | Keeps behavior unobserved due to login and rejects an unsupported re-upload retry. |
| A | necessary-delivery-missing-authority r1 | Pass | Fail | Retains hosted delivery and asks for target/operation/authority; but says completion follows completed release/consumer checks rather than a scoped plan. |
| A | necessary-delivery-missing-authority r2 | Pass | Fail | Blocks on target/operation/authority, but makes plan `done` depend on later consumer-delivery evidence. |
| B | ambiguous-existing-hosted-ui r1 | Pass | — | Asks the high-value hosted-versus-source-only question and refuses to invent authorization. |
| B | ambiguous-existing-hosted-ui r2 | Pass | — | Identifies the likely hosted consumer, leaves scope/authority unresolved, and proposes no remote operation. |
| B | approved-private-sync r1 | Pass | Fail | Uses only `private-development-head`, excludes promotion/access changes, and retains interaction verification; it still says sync and visual proof are required before plan `done`. |
| B | approved-private-sync r2 | Pass | Fail | Correctly scopes the private sync and visual check, but treats future release evidence as a release-plan blocker. |
| B | explicit-source-only r1 | Pass | — | Calls remote release non-applicable and does not invent a remote target. |
| B | explicit-source-only r2 | Pass | — | Keeps a local-only change and defers any activation decision until evidence requires it. |
| B | identity-without-visual-verification r1 | Pass | — | Separates sync/artifact strings from the required interactive visual check. |
| B | identity-without-visual-verification r2 | Pass | — | Keeps the behavior observation required and does not report consumer success. |
| B | login-after-upload r1 | Pass | — | Retains update/identity facts, marks the login boundary, and rejects re-synchronization. |
| B | login-after-upload r2 | Pass | — | Requires authorized access and a current behavior observation; no blind retry or N/A downgrade. |
| B | necessary-delivery-missing-authority r1 | Pass | Fail | Blocks for exact hosted target/operation/authority, but says `done` follows the authorized update and consumer evidence. |
| B | necessary-delivery-missing-authority r2 | Pass | Fail | Retains the necessary hosted obligation and asks for authority, but again ties plan completion to later update/behavior evidence. |
| B2 | approved-private-sync r1 | Pass | Pass | Explicitly says this is a non-executing plan; later `release` owns synchronization and `release-verify` owns visual behavior. |
| B2 | approved-private-sync r2 | Pass | Pass | Says missing future effect/behavior does not block release-plan completion and keeps all exclusions. |
| B2 | necessary-delivery-missing-authority r1 | Pass | Pass | Blocks solely because target/operation/authority prevent safe plan scope; later effect is not demanded now. |
| B2 | necessary-delivery-missing-authority r2 | Pass | Pass | Requires only authority/target/operation facts to scope the plan and leaves release/verification as later actions. |

## Meaningful failure excerpts and context

The eight exploratory failures all share the same phase-order error rather than
an authorization or consumer-boundary failure.

- `responses/A/approved-private-sync-r1.md` says, “Submit done only after the
  authorized sync and current visual evidence.” Its frozen packet's current node
  is `release-plan`; the later sync and interaction are assigned to `release`
  and `release-verify`.
- `responses/A/necessary-delivery-missing-authority-r1.md` says, “Submit done
  only after an authorized release plan and completed review/check cycles
  establish the intended hosted-app effect.” The required block is correct, but
  a future hosted effect is not a planning completion requirement.
- `responses/B/approved-private-sync-r2.md` says the missing “authorized
  synchronization receipt and a target-specific post-update visual interaction
  result” cause `blocked` now. Those are required later, not prerequisites for
  an otherwise scoped release plan.
- `responses/B/necessary-delivery-missing-authority-r2.md` says `done` follows
  “the authorized update and the required current evidence.” The target,
  operation, and authority are sufficient reasons to block the plan; the later
  update is not.

The B2 packet wording directly names this distinction, and all four B2 raw
responses preserve it. That is evidence of a useful wording improvement for
this fixed follow-up, not proof that the wording is universally reliable.

## C guarded-recovery follow-up

C is a separate two-packet fresh-context follow-up, not part of the A/B primary
comparison and not described by the six scenario keys in `oracles.json`. I
therefore graded each response against its frozen packet's explicit recovery
conditions rather than assigning it an A/B oracle score.

| Packet / response | Result | Packet-specific evidence |
| --- | --- | --- |
| `login-after-upload-recovery.md` | Pass | Preserves the declared earlier pre-check, update effect, and identity as unverified prior records; keeps `visual-drag` blocked/unverified; rejects re-upload; and does not call the synthetic fixture complete. |
| `post-plan-candidate-change-recovery.md` | Pass | Keeps the `release` action blocked, recognizes the candidate-v2 post-plan drift as requiring explicit direction for a new planning run, does not create a back-edge or substitute run, and does not perform an effect. |

Neither C response claims a live upload, consumer interaction, or independently
verified prior record. The first response correctly distinguishes retained
declared effect/identity from the missing behavior observation. The second
correctly treats all candidate-v2 obligations as unreported and does not let a
completed work-item count certify a release.

### C limitations

- Both C packets expressly describe synthetic fixtures with no target,
  credential, network, consumer, or deployment. The responses' non-execution
  and blocked conclusions are therefore safe interpretations of the fixture;
  they do not establish what a host would do when real target access is
  authorized.
- C has one response per recovery condition, not independent repeated samples.
  It measures orientation to packet state only and does not validate the guard's
  runtime behavior; the deterministic guard controls are a separate artifact.
- The C raw responses also lack independently auditable interpreter provenance,
  token/time metrics, and tool records in their bodies. Those values remain
  unavailable here.

## C2 current-renderer follow-up

C2 is one additional current-renderer packet reading. It is separately labeled
so it does not alter the historical C score above.

| Packet / response | Result | Packet-specific evidence |
| --- | --- | --- |
| `post-plan-candidate-change-current-renderer.md` | Pass | Identifies `release` as the current action rather than a planning node; retains the post-plan candidate-v2 drift and stale `pre-drag` receipt as blockers; requires an explicitly directed new planning run; does not invent a back-edge, successful observation, upload, or N/A completion. |

The response also correctly treats the prior work-item completion, policy,
contract, and history as declarations rather than independent proof. It says
the present action is `blocked`, not `done` or `repeat`, and preserves the
fixture's no-operation boundary.

### C2 provenance and limits

`responses/provenance.md` now records originating task labels and the
`fork_turns: none` constraint for the response set. That supports a limited
claim about how the independent interpretations were requested; it is not a
raw transcript, tool-use audit, fresh-context proof, deployment receipt, or
per-response token/time/model record. The C2 packet remains synthetic and
prohibits target operations, so this one pass tests packet interpretation only.

## Limits

- Every response follows the synthetic read-only restriction. Many answer
  `blocked` because inspection, checks, updates, callbacks, and target access
  were forbidden. That is a constraint of the teaching exercise, not evidence
  that real ShipLoop release planning should require a live mutation.
- The raw responses do not contain the provenance block requested by
  `responses/README.md` (session identity, fresh-context attestation, tools,
  and timestamp). Variant/repetition/path are inferable from filenames and
  parent-provided execution context only. Treat independence and freshness as
  asserted, not auditable from these files.
- No token counts, elapsed times, model identifiers, tool-use records, or
  complete execution metadata are recorded in the raw files. They are
  unavailable and are not estimated here.
- These are 31 synthetic, text-only interpretations: 12 A, 12 B, 4
  exploratory B2, 2 C recovery readings, and 1 C2 current-renderer reading.
  They do not run the navigator, validate a delivery contract, inspect a
  repository, authenticate authority, update a remote system, or establish
  real consumer behavior.
- Primary success means only that each raw response met the listed primary
  semantic checks. It does not certify exact callback validity, full Improve
  convergence, or external completion.
