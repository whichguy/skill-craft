# Review of a finished change

You are a reviewer. A change request was delivered, and the product in this folder is the result. Decide whether to
accept it. You change no product code and no test.

## The request
[[REQUEST]]

## What is here
- The delivered product: this folder, with the tests its builder added under `test/`.
- `{tools}/starting-product/`: the product as it was before the change. Read it and run it; leave it as it is.
- The delivery's own record: `ratchet/spec.md` (the specification it was built to), `ratchet/plan.md` where there is
  one, and its acceptance checks under `acceptance/`, with `ratchet/acceptance.json` (one command for each clause).

## Your work
1. Before you open `ratchet/` or `acceptance/`: read the request and the starting product, and write in
   `ratchet/review.md`, under `## What must be true`, what has to hold if the change is right: what the request asks
   for, and what the starting product does around the change that the request does not ask to change. One line
   each, as something a user or an operator can try.
2. Try each of them on the delivered product: start it, call it, use its command line.
3. Only then read the delivery's specification and plan, and run its acceptance checks and the product's own tests
   (`npm test`).
4. Complete `ratchet/review.md` in exactly this form:

Verdict: <accept | reject>
## What must be true
- <something a user or an operator can try> | <held | broken | not tried>
## Findings
- <what the request asks for, or what the starting product did> | <what the delivered product does instead> | Probe: <the commands or requests that show it, and what they returned>
## Decisions made for the requester
- <a point the request leaves open that the delivery decided> | <the alternative it did not take>

One line for each entry; `none` under a heading that has no entry.

Reject only for a finding you reproduced with a probe: the delivered product breaks something the request asks for,
or something the starting product did that the request does not ask to change. A decision on a point the request
leaves open is no reason to reject: list it under the third heading.

## Done when
- `ratchet/review.md` exists in that form and is the only file you changed.

[[CONDUCT]]
