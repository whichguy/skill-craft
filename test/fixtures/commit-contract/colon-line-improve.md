docs: pin error-response shape and route set in the spec (R-15)

Review: self-review 1 of the spec result; non-trivial, streak 0.
Plan: close the contract gap between R-5/R-6 and the request's response fields.
Changes: docs/shiploop/spec.md adds R-15.
Validation: docs only; grep confirms R-15 present.
Key learnings: the request says illegal moves return ok:false and leave the turn unchanged, so clients must read the turn from the failure body; the earlier text left that implicit.
Remaining work: second no-change review needed for exit.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
