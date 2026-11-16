# Adapter gaps: the question for the run reviewer

Add this to the run reviewer's questions, separately from findings about the subject. It is how the loop keeps calling out what must
be specific while it runs.

> What could you not determine from the evidence of this run because the adapter does not record it or does not expose it?
> For each gap: what you wanted to know, which finding it would have changed or settled, and the smallest record, probe or
> comparator that would show it.

How to file an answer:

- It is a finding about the **adapter** (the evaluator), never about the subject. Give it `target: adapter` (a harness that already
  has `target: harness` keeps that word; the adapter's `records` command presents it as `adapter`).
- Never route it to the improver. Adapter findings are worked between scopes by re-running the definer and `readiness` for the
  affected claim; the change starts a new identity.
- Say what you inspected, so the gap is not a failure to look: which stages, files and journals you read, which you did not, and
  what you could not see.
- No quota: an empty answer is valid.
