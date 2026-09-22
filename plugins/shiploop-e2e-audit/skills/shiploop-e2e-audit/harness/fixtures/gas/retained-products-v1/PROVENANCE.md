# Recorded GAS source-closure regression fixtures

These source files were generated in the September 17, 2026 ShipLoop E2E runs
`shiploop-e2e-20260917-ttt-full-80m/products/tic-tac-toe` and
`shiploop-e2e-20260917-checkers-full-80m/products/checkers`. They were copied
unchanged from the retained local products on September 22, 2026.

The tic-tac-toe case includes its served template and literal JavaScript include.
The checkers case preserves a served page with a raw relative `engine.js` route
and the sibling file that does not make that route valid for Apps Script.
Only these six source files are needed for the regression. Deployment settings,
Git state, run logs and browser evidence are excluded.

The test checks source assembly and resource closure without a model, network
request or deployment. These recorded inputs preserve a historical regression;
they do not qualify a current generated application or prove hosted behavior.
Fixed fixture contents do not constrain current runtime or toolchain versions.

| File | Bytes | SHA-256 |
|---|---:|---|
| `tic-tac-toe/Code.gs` | 372 | `445dbd4aac83e8d72f4af7cb69fc278c541651478422015b1792cdb0f0e2ccdf` |
| `tic-tac-toe/Index.html` | 3523 | `1e4c66f3ec2df04bec6a7fabe9172a756c8b39dd4eba2c0beaf3011f93179478` |
| `tic-tac-toe/JavaScript.html` | 3824 | `5d179326531c82cab387cc8c52b1778c30a109f1f0a4e2bcb50eec98e9b42ab7` |
| `checkers/Code.gs` | 98 | `9abf5855049e259bc7acc9e5131acf4f6703b40ac2b6b7fd7653256c60665b11` |
| `checkers/Index.html` | 5661 | `aa14d12f3d77487ec2daac6bc894c11d2f52c7f56751cb6ee21733728f0c43eb` |
| `checkers/engine.js` | 8125 | `dd775e03a90b46083a7f028e9b4c643e7f70aa9bd24dd5fbfd9bc78c864c90a1` |
