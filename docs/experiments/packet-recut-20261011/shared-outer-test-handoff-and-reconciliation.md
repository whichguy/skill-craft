# Shared OUTER_TEST_HANDOFF and SELECTED_CASE_RECONCILIATION: re-cut draft (worker C)

## Recommendation: fold, then print the shared text only where a stage does not fold it

Workers C and D folded both blocks into their stage duties (system-test-author, system-test, product-acceptance,
release-plan, release-verify), each keeping only the half that applies (R3). Folding is the better cut: at the plan
owners (system-test-author, release-plan) the consumer half does not apply, and at the stages that change nothing
(product-acceptance) the rerun half does not apply. The main session should:

1. Apply the folded duty text for every stage whose draft folds a block, and drop that block from its `prompt()`.
2. Print the concise shared text below only at a stage whose draft does not fold it. Check workers B and D: verify
   (reconciliation), release-check, release, operations and handoff (OUTER test plans, and reconciliation at
   handoff).
3. Under R7 the Improve packet carries neither block. `_improve_prompt`'s `outer_handshake` goes, and the
   `OUTER_TEST_HANDOFF.replace(... Improve child's context/notes ...)` variant in `prompt()` goes with it, since no
   remaining text mentions Improve.

## OUTER_TEST_HANDOFF (proposed)

```text
OUTER test plans (OUTER test-planning handshake): the current plans are the latest done system-test-author and
release-plan records after the most recent accepted replan; pending, repeat, and blocked results are not plan
authority, and earlier records are history to revalidate. Name the plan you rely on and put its action, result and
plan locators in `evidence_refs`. Revalidate it for the current candidate and target before relying on it. Recover
a missing plan or report the incomplete or corrective outcome; never guess a command, drop required coverage, or
deploy to make a check available. A plan is not execution evidence. A material change to code, tests, fixtures,
configuration or target invalidates the observations it affects: rerun them through the authorized route, and reuse
unaffected evidence only with its identity and relevance stated.
```

| Today's sentence (short) | New home |
|---|---|
| Current plans: latest done system-test-author and release-plan records after the most recent accepted replan | Sentence 1 (pinned phrase kept) |
| Earlier records are history to revalidate | Sentence 1 |
| Pending, repeat, and blocked results are not plan authority | Sentence 1 (pinned phrase kept) |
| Retain action, result and plan locators in this result and the Improve child's context/notes | Sentence 2; Improve half CUT: R3 advance Improve, R7 |
| The owning stage creates or reconciles the plan | CUT from the shared text: only the two owners do this, and their folded duties say it (system-test-author 8, release-plan 2-5) |
| A later stage names the plan and revalidates it for the current candidate and boundary | Sentences 2-3 |
| Recover a missing plan or report incomplete/corrective; never guess, drop coverage, deploy for a check | Sentence 4 |
| A plan is not execution evidence | Sentence 5 |
| Material change invalidates affected observations; rerun through the authorized route | Sentence 6 |
| Unaffected evidence reused only with identity and relevance shown | Sentence 6 |

Size: today 954 characters; proposed 857.

Pins: test/shiploop-guidance.test.py `test_outer_test_handshake_recovers_replan_aware_sources_cold` asserts the
three source phrases in every OUTER stage's `prompt()` and in `improve_prompt()`. The folded duties keep "latest
done ... record(s) after the most recent accepted replan" in spirit, but not the exact plural phrase "latest done
system-test-author and release-plan records" at system-test, product-acceptance and release-plan, and the
`improve_prompt` half fails by design under R7. A pin worker should re-point that test to the folded duty phrases
and to the reference section, and drop the Improve assertion, reporting it under R5.

## SELECTED_CASE_RECONCILIATION (proposed)

```text
Selected-case reconciliation: classify every selected case in `summary` as passed, failed, blocked, not-run, or
justified N/A. Reconcile each affected requirement clause with its case, its required surface and due phase, the
surface checked, the candidate, the status and the evidence. A pass on a different surface only supports; Source,
HTTP, or DOM structure alone cannot close a rendered interaction. A case not yet due keeps its phase, owner and
prerequisites; missing evidence for a case already due stays incomplete. Check the selected inventory for dropped
clauses or cases. Never claim every requirement met while a required observation is unrun.
```

| Today's sentence (short) | New home |
|---|---|
| Classify every selected case (five classes) | Sentence 1, now says where (`summary`) (R4) |
| Reconcile each clause with case, surface and phase, checked surface, candidate, status, evidence | Sentence 2 |
| A pass on a different surface is supporting evidence, not closure | Sentence 3 |
| Source, HTTP, or DOM structure alone cannot close a rendered interaction | Sentence 3 (pinned phrase kept) |
| Not-yet-due case keeps phase, owner, prerequisites; due and missing stays incomplete | Sentence 4 |
| Check the selected inventory for dropped clauses or cases | Sentence 5 |
| Never claim every requirement met while required observations remain unrun | Sentence 6 |

Size: today 665 characters; proposed 656.

Pins: test/shiploop-navigator-contract.test.py asserts "passed, failed, blocked, not-run, or justified N/A" and
"Source, HTTP, or DOM structure" in each reconciliation stage's packet. Both phrases survive verbatim in the shared
text and in the system-test and product-acceptance folds. Worker D's release-verify fold drops the Oxford commas
("not-run or justified N/A", "Source, HTTP or DOM"); either restore them there or re-point the pin.
