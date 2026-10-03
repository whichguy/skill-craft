# ShipLoop plan: Until Loop state headroom (F3) and the secret detector (F1)

Execute: inline

Grounded in `test/shiploop_e2e/LEARNINGS.md` (batch 1003 entries) and the evidence in
`/Users/dadleet/e2e-runs/20261003/`. Governed by the E2E specification
(`test/shiploop_e2e/SPEC.md`: ShipLoop is a general SDLC execution engine; scripts own graph
navigation and the model does one step) and by ShipLoop's own contract rule that every Until Loop
contract has one ShipLoop-owned shape (`shiploop_loop_contract.py`, S-10/S-12).

## Problem

**F3.** The Until Loop runtime persists its whole state (frozen contract, latest report, progress)
in at most 16,384 bytes (`MAX_STATE_BYTES`, `until_loop_ephemeral.py`). Nothing reserves room for the
reports the loop must later save:

- Improve children: ShipLoop freezes the contract from the model-written opening. On Sonnet the
  contracts are 5.5-6.8 KB. On Luna max they were 11.9, 12.1 and 15.7 KB (the opening's
  `Environment` section was 5.6 KB, `request` 3.8 KB), so the first report did not fit. A second
  Luna run (Codex xhigh, another session, 177707d8) had an Improve completion report refused for size.
- Backchain plan loop: the plan packet gives locators but no script, so the model hand-built the
  start contract; its state sat at 16,287 of 16,384 bytes, the first report was rejected twice
  ("state exceeds the small-file limit") and the plan stage could not close.

The refusal comes after all the review work is done and cannot be repaired; the same bytes could
have been refused at start, where the model can shorten its text.

**F1.** `shiploop_privacy.sensitive_text` flags any `auth|token|secret|signature|sig` label followed
by a value, including descriptions: `session token: opaque UUID`, `auth: none required`,
`secret=none`, `signature: n/a`. Luna's discovery completion was refused twice for a credential that
was not there.

## Changes

1. `shiploop_loop_contract.py`: `STATE_LIMIT` (16,384, equal to the runtime's constant, asserted by a
   test), `STATE_OVERHEAD` (1,024: the state's own keys, ids and receipt path, about 420 bytes measured),
   `REPORT_RESERVE` (6,144: Luna Backchain plan report 5,335 bytes, Improve child reports up to 2,928, a
   Codex xhigh child with a 12,448-byte contract refused for size), `CONTRACT_BUDGET` (9,216),
   `compact_bytes` (exactly the runtime's serialization, including its ASCII escaping of non-ASCII text)
   and `size_problem(contract, writable=, allowance=)`, whose refusal lists only the parts a model wrote,
   by the heading the model knows them by, says how far over the contract is and how many bytes remain.
2. `_improve_start`: refuse before any file is written or a stopped child is archived. The opening
   instruction packet prints the byte allowance of the four sections, computed from ShipLoop's own text
   for the run's paths; `improve-context.md` states the same limit (it had said "no quota").
3. `shiploop_prompts._backchain_guidance`: the plan stage (the only stage that starts a Backchain Until
   Loop child) states the same budget with a measuring command that matches the runtime's count.
4. `shiploop_test_loop.listing_problem` and the step-plan submission gate: the test loop contract
   embeds the model's command list and is written at a transition, so the list is refused where it is
   submitted when its contract could not fit.
5. `shiploop_privacy`: descriptive values pass (`none`, `n/a`, `opaque`, scheme words such as `oauth2`,
   punctuation and markdown around them, a masked `***`); real secrets after the same labels still match.

Revised after the adversarial review of the first draft (`a1ea32a9...`): the first `compact_bytes`
used UTF-8 length, so a Japanese opening of 8.7 KB (13.5 KB in the runtime) would have passed; the
overhead was missing; the test loop was unguarded; the reference text contradicted the packet; and the
privacy fix missed punctuation-adjacent forms.

## Impact on other spec items (checked before building)

- Sonnet contracts (5.2-6.8 KB) stay below the budget; the fixed ShipLoop text of an Improve contract
  is 4.2-4.9 KB with short paths (spec through plan, both routes), so an opening has about 4.3 KB.
  Quality loop fixed text is about 4.6 KB.
- A legitimate large opening is refused once and must name files for the detail; the refusal says how
  many bytes remain. The three Luna contracts of the batch (11.6, 11.8, 15.3 KB) would each be refused.
- The vendored Until Loop runtime is not changed (provenance hashes stay valid); the guards are ShipLoop's.
- The privacy change only widens documentation words; every existing credential test passes and new
  tests pin the false positives and the real secrets that sit next to them.

## Tests

Unit: contract size helpers, budget equality with the runtime constant, refusal text, fixed contracts
under budget. Navigator: `improve-start` refuses an oversized opening without writing `start.json`, a
receipt or archiving, accepts a normal one; the packets carry the budget. Privacy: false positives
pass, real secrets still flagged. Footprint run of the quick tier, then CI.

## Verification after release

`--preflight-only --host all`, the Sonnet hello gate, then Luna max battleship with `--timeout 36000`
to prove the plan stage closes (the run that exposed F3). Success: plan accepted as done, no state-size
refusal, no hand-built contract beyond the budget.

## Rollback

Revert the release commit; the change is additive guards and text.
