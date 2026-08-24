Session closer only. The spec is still **frozen**. Do not rewrite it. Do not invoke `/devloop`.

Do not open `/goal` until the bound repo’s Test command is green and the implementation commits are landed. Otherwise `/shiploop complete --blocked --resume-to residual --reason …`.

When green and landed, run review-coverage Phase B for the bound plan `{{BOUND_PLAN}}` under host `/goal`. One `/review-converge` per outer turn. Ledger: repo-root `{{LEDGER_PATH}}`.

Do not treat a foreign or unlanded ledger as success.
When the bound ledger is `complete` and landed, or the bound plan H2 has a real residual waiver, go to When done invoke `--to done`.
When the bound ledger is `stopped (...)`, invoke `--to halted`.
