Session closer only. The spec is still **frozen**. Do not rewrite it. Do not
invent a new state-machine phase.

Follow this order. Each `/goal` below is a new outer-loop turn, not a nested
`/goal` and not a DAG step.

1. Do not open `/goal` until the bound repo’s Test command is green and the
   implementation commits are landed. Otherwise `/shiploop complete --blocked
   --resume-to residual --reason …`.
2. When green and landed, run review-coverage Phase B for the bound plan
   `{{BOUND_PLAN}}` under host `/goal`. One `/review-converge` per outer
   turn. Ledger: repo-root `{{LEDGER_PATH}}`. Do not treat a foreign or
   unlanded ledger as success.
3. When the bound ledger is `complete` and landed, or the bound plan H2 has
   a real residual waiver, read the frozen spec's three placement answers
   and finish only what it named:

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
      end result, the final outcome, and what was verified). Do not
      hand-author that file.

When the bound ledger is `stopped (...)`, invoke `--to halted`.
