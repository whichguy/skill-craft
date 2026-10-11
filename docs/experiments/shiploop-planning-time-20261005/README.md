# Planning time investigation, 2026-10-05

The owner stopped a Luna xhigh battleship run at 9.8 h (planning alone 375.9 min) and asked where the time goes; the working
ceiling for planning is 30 minutes (the owner first said 7, then corrected: "anything where planning takes more than 30
minutes"). Evidence here:

| File | What it is |
|---|---|
| `ledger-account-final.json` | the reconciled account of a read-only eleven-agent ledger evaluation (seven analyses, synthesis, two attacks, revision) of the Luna xhigh run and the 1.16.1 max run: minutes by cause, token ledger, retries, compactions and kills, consumption, review passes, 18 levers with savings and rule tensions, unknowns. The raw per-response analyses were large and are not kept; every number in the account names its source |
| `stage-clock.md` | planning stage minutes for Grok medium, Luna xhigh and Luna max, with sources |
| `grok-medium-improve-children.json` | Improve passes and minutes per planning stage in the Grok probe, and the four-commit churn chain in its spec review |
| `run-doc-luna-xhigh-v1210.json`, `run-doc-grok-medium-v1210.json` | the two runs as Run Review documents (exporter 0.1.0 on copies of the run directories), as written to the draft Run Review page |

**Superseded 2026-10-08: lever L11 of `ledger-account-final.json`** ("about 100 model-written check scripts, 73.8 min, 35 to
55 savable"). Its raw per-response analyses were not kept and it could not be re-derived. The re-derivation for the Luna
xhigh run (22 pure document checks, 8.9 min of a 375 min window, an upper bound) is in
`docs/experiments/docheck-20261008/evidence.json`; it agrees with `docs/pending-work-plan-2026-10-06.md` (13 of 162
scripts, 7.5 min). The account's other levers are unchanged.

Labels in the account: [M] measured from a file, [I] inferred. Statuses are in test/shiploop_e2e/LEARNINGS.md ("Planning time").
