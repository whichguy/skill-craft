---
bump: minor
---

# Archive every Improve review pass, not only the terminal one

## What was wrong

An Improve import archives the review files its receipt names. The receipt names the
*trivial streak* the loop ended on, and a converging review ends on the pass that found
nothing. Measured over the saved corpus (`test/shiploop_e2e/LEARNINGS.md`, 2026-11-04):

| | count |
| --- | --- |
| Improve children with review notes | 1,854 |
| multi-pass | 601 |
| **edited at a non-final pass** | **447 (74%)** |

So in three quarters of multi-pass reviews the archived prose reads `Changed: none`
while the earlier passes had rewritten the artifact. `passes.md` records *that* those
passes edited (label, lines, seconds) but not *what* they found, and `review-<n>.md`
lives in the worktree, which is not kept.

This misled a reader of saved runs five separate times in one session: each time the
terminal review said "no changes", and each time the earlier passes had made material
edits — `spec` finding malformed API boundaries, `test-strategy` finding a browser
verification route that did not exist, `step-plan-affaf60f` editing on passes 1, 2 and 3
of 4. An audit trail that preserves the finish line and discards the work is worse than
none, because it reads as evidence of idleness.

## What changed

`_review_pass_archives` copies every `review-<n>.md` the child left into
`improve/<action>/reviews/review-<n>.md` at import. The receipt's own numbered evidence
copies keep their existing names and contents, so nothing already recorded moves.

Cost is small: non-final passes add a median of 2,632 bytes per multi-pass child (mean
4,168) across the 601 measured children.

## What this does not do

It does not change the receipt contract, the convergence gate, or what counts as
satisfied. It archives prose the run already produced; it proves nothing new about
whether a review was genuine.
