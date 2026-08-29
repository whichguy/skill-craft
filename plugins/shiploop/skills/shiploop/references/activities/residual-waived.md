Session closer only. The spec is still **frozen**. Do not rewrite it. Do not
invent a new state-machine phase.

Review-coverage is **waived** on the bound plan `{{BOUND_PLAN}}`. Do not open
review-coverage Phase B. Do not treat a missing `{{LEDGER_PATH}}` as failure.

Follow this order. Each `/goal` below is a new outer-loop turn, not a nested
`/goal` and not a DAG step.

1. Do not open `/goal` until the bound repo’s Test command is green and the
   implementation commits are landed. Otherwise `/shiploop complete --blocked
   --resume-to residual --reason …`.
2. Skip review-coverage Phase B (waiver).
3. Read the frozen spec's three placement answers and finish only what it
   named:

   1. **Quality test/fix `/goal`.** If the spec said yes on outer-loop
      completion, run one host `/goal` to test and fix the completed
      product (the check it named). If the spec said no, skip. The spec is
      SoT — do not override a no.
   2. **Outer-loop deploy/publish.** If the spec named deploy/publish as
      **outer-loop**, do that now. If it said **dag** or **none**, skip
      (dag already ran in the walk). Do not open a new DAG step.
   3. Then invoke `/shiploop complete`. dest `done` writes the
      end-of-run walk-back at `{{RECAP_HTML}}` (HTML covering intent, the
      original spec, what was accomplished, what materially changed, the
      end result, the final outcome, and what was verified). Recap
      Verified reports the waiver; it does not witness this quality
      `/goal` or treat `done_sentence` as harness-verified. Do not
      hand-author that file.
