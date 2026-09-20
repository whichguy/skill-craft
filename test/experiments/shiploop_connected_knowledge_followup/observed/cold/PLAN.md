# W1 Conditional Retry UI — conditional plan

## Decision now

Treat CASE-17 as an Orion Review Gateway case. The source-backed policy is to resubmit the existing case to manual review; retry must never automatically approve it. Avery Cole is the available engineering-ownership signal. ADR-042 is the governing approved synthetic decision. The pinned synthetic source snapshot corroborates the intended state (`queued_for_manual_review`) but is not a verified live interface or implementation target.

## Gate before implementation

Do not edit product code, choose an API payload, or claim a test passes until the Gateway and reviewer-experience owners provide current evidence for all of the following:

1. The real retry endpoint/interface, authorization, durable-acceptance boundary, and a read-back/status contract for the existing case.
2. Idempotency and recovery rules for repeated clicks, stale case state, rejection, timeout, and unknown/partial completion.
3. Existing review UI components, design and accessibility guidance, and acceptance criteria for pending, queued, failure, and follow-up states.
4. A real integration test route that can verify the reviewer-visible result against Gateway state.

## Conditional implementation sequence

When those gates are evidenced and accepted, map the confirmed interface to the established review UI. Keep authoritative case state in Gateway; limit the UI to transient pending and feedback state. Submit only the existing case identifier, render queued only after the confirmed acknowledgement/read-back boundary, render failures truthfully, and provide a recovery path defined by the confirmed idempotency contract. Add focused integration coverage for success, authorization/rejection, duplicate action, stale state, and ambiguous outcome; then perform the agreed reviewer-visible validation. Revalidate ADR-042, the Gateway revision, ownership, and UI/test contracts immediately before execution.

## Evidence limits

The baseline is one passing synthetic case-ID edge test with unchanged fixture hashes; it proves neither a retry UI nor Gateway behavior. Receipt evidence shows fictional local discovery only: no real account, network, callback, product change, runtime verification, or Teams evidence. Synthetic traversal setup and accepted transport results do not establish project work completion.

## Actual files opened

`cold/LAUNCH.md`; `transport/collection.json`; `run/chains/nav-04257b452f9a4e00b80689b2cb560b3b/planning-brief.md`; `workspace/DISCOVERY.md`; `workspace/SHIPLOOP.md`; `workspace/BASELINE.txt`; `case/receipts.jsonl`; `run/results/nav-4a684446ff0d4d38b83ea83e58400d9c.md` (all beneath `/Users/dadleet/tmp/shiploop-discovery-followup-20260920/sample/`).
