# Chain B of the multipass study (2026-11-01)

The same questions as the ticket chain's, asked of another product: `user-listing` on `fixtures/node-base` (174 lines, a user directory) and three links that follow it,
`user-roles`, `user-team-listing` and `user-page-size`. Question, bar, predictions and result: [the journal's Round 5](../../shiploop-multipass-journal.md); the
plan: [section 4, chain B](../../shiploop-multipass-plan-2026-10-31.md).

| file | what it is |
|---|---|
| `real-priors/`, `cut_real_priors.py` | the spec and architecture of seven saved real pass-1 deliveries (Codex gpt-6.1-terra, ShipLoop 1.20.0 to 1.26.4), `provenance.json` says which; the words and ledger patterns of the three cases were written from them and `test/shiploop-e2e-user-directory.test.py` reads them |
| `chain_b_readout.py`, `readout-calibration-output.txt` | the readout, written first: bar B1 to B6 and predictions P1 to P8 as `held`, `missed` or `unknown`, fed saved runs with known numbers (E1, E3, a saved `user-listing` run) |
| `chain_b_gate.py` | the gate between two passes: reads a link against the real prior the pass before it left (the retention word absent from the prior's spec, the ledger patterns finding their rules, the link's own and new hidden checks failing on the prior, the earlier checks passing), before the link runs |
| `chain_b_driver.py` | runs one pass from the marketplace on Codex, retrying while another session holds the port-3000 lease |

Cases, references, hidden acceptance and the calibration suite are under `test/` (`cases.json`, `test/fixtures/quality/reference_user_*.py`, `test/shiploop_e2e/checks/user_*_accept.py`,
`user_directory_probe.py`, `test/shiploop-e2e-user-directory.test.py`).

```sh
python3 chain_b_driver.py B1 ~/e2e-runs-multipass/20261101/chain-b      # then B2, B3, B4, each after python3 chain_b_gate.py LINK PRIOR_RUN
python3 chain_b_readout.py ~/e2e-runs-multipass/20261101/chain-b
```
