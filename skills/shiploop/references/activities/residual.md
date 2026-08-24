Session closer only. The spec is still **frozen**. Do not rewrite it. Do not invoke `/devloop`.

Do not open `/goal` until the bound repo’s Test command is green and the implementation commits are landed. Otherwise `/shiploop complete --blocked --resume-to residual --reason …`.

When green and landed, run review-coverage Phase B for the bound plan `{{BOUND_PLAN}}` under host `/goal`. One `/review-converge` per outer turn. Ledger: repo-root `{{LEDGER_PATH}}`.

Do not treat a foreign or unlanded ledger as success.
When the bound ledger is `complete` and landed, or the bound plan H2 has a real residual waiver:

1. **Quality test/fix `/goal`.** Read the frozen spec. If it asked for a quality pass on outer-loop completion (or the shipped surface still looks untested), run one host `/goal` to test and fix the completed product. If the spec said no, skip. Do not invoke `/devloop`.
2. **Outer-loop deploy/publish.** If the spec named deploy/publish as an outer-loop activity, do that now. Do not open a new DAG step.
3. Then go to When done invoke `--to done`. dest `done` writes the end-of-run walk-back at `{{RECAP_HTML}}` (HTML covering intent, the original spec, what was accomplished, what materially changed, the end result, the final outcome, and what was verified). Do not hand-author that file.

When the bound ledger is `stopped (...)`, invoke `--to halted`.
