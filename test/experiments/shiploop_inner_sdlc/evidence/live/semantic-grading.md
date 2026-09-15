# Live semantic grading

Parent assessment after worker completion against the five predeclared criteria
per case in `../../preregistration.md`. This is a qualitative evidence review,
separate from the reserved behavior oracle; no runtime state gate consumes it.

| Case | Criteria 1–5 | Supporting evidence |
| --- | --- | --- |
| misleading-green | All 5 satisfied on the final candidate | Immutable spec/diff; available Git history in run notes; failing remainder regression then correct code; updated plan and tests; current 5-test suite and 11/11 reserved outcomes; independent P2 triage and re-review; two distinct clean reviews recorded; one callback to integrate. |
| delegation-conflict | All 5 satisfied | Explicit synthetic provenance; actual km/metre mismatch in adapter; scoped conversion repair and immutable spec; 4 passing unit tests and 7/7 reserved outcomes; reconsidered material-review disposition and independent review; one callback to carry-forward. |
| repeated-failure | All 5 satisfied | Recorded deterministic failing APP_PORT test; fresh-process APP_PORT/PORT observation challenges stale cache claim; corrected setting selection and explicit-None validation; 4 passing unit tests and 14/14 reserved outcomes; factual verification record and one callback to product-improve. |

The allocation pilot did not pass review on its first candidate: independent
review found inadequate durable contract coverage despite correct behavior.
It added tests and obtained a second independent look. A post-run record review
also found that the note placed the material edit in the next clean cycle's
section. The worker clarified that the edit/check/commit preceded the separate
no-edit review and corrected only that note, appending the clarification. The
original ambiguous note is preserved as `before-postrun-cycle-clarification.md`.
The candidate and callback did not change. The clean-cycle conclusion relies on
that factual host record plus independently inspected final checks; this archive
is not a complete execution transcript or an automated proof of internal review.

Final candidates: allocation `851e205`, integration `a5e5b13`, and configuration
seed HEAD `31e23a1` plus its explicitly recorded working-tree edits. The
configuration fixture was not committed; the source repository archive retains
its final files and diff. Integration's pre-existing untracked bytecode directory
was left outside the snapshot. Neither detail changes the executed behavior.
