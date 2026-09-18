# Improve review 2 — material state-lifetime clarification

## Candidate and history

The action-1 corrected planning artifact entered this cycle at SHA-256
`7c8b8fa5e06e37a53979b69b399345586a949457d3a36f0f6bdf5313d4d5f8ce`.
This cycle changed only `evidence/w1-step-plan.md`; its current SHA-256 is
`46eac9978c26d15c187e6ca36b3bc79f79e55afcaf3815fefe4f294cffea8840`.
The product sources remain byte-identical to the frozen baseline: `app.js`
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`index.html` `f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`,
and `styles.css` `cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.
No product code, product documentation, tests, Git, install, remote,
deployment, commit, or W2 change occurred.

The required safe Git-history command was attempted again and recorded
`fatal: not a git repository` in `review-2-git-history.raw.txt`; no Git history
exists to apply for this fixture.

## Independent finding and source-grounded triage

The fresh independent record `reviewer-two.md` raised a credible concern that
clearing a held revision on account replacement would make a returning numeric
equal value contradict the equal-heartbeat rule. The frozen contract instead
requires clearing the prior account's snapshot on replacement
([controlled-status-identity-contract.md - account replacement: clear prior snapshot](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:59))
and compares only against a revision that is actually held for the same account
([controlled-status-identity-contract.md - acceptance rule: held revision comparison](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:52)).
It neither requires a per-account record to survive that cleared snapshot nor
authorizes a client cache workaround.

The plan therefore explicitly states the source-supported lifecycle: a held
revision exists only with an active snapshot; an account replacement clears both;
a returned account's first current matching response establishes a fresh active
view because no comparison value is held. An equal revision remains a no-change
heartbeat whenever a revision is held. The numeric value matching an earlier,
cleared view is not reclassified as a newer held revision. This removes the
ambiguous implementation reading without adding transient per-account cache
state, a host dependency, or an external clarification requirement.

## Checks and learning

After that plan clarification, `python3 product/scripts/probe_environment.py`,
`node --check product/app.js`, and `node --test` exited 0. Node still discovered
zero tests, which remains a baseline limitation rather than implementation
coverage. The frozen producer/oracle inputs still matched in
`review-2-inputs.raw.json`. The pre-clarification check output is preserved in
the `review-2-before-source-clarification-*` files; the current check output is
the matching `review-2-*` set.

This is non-trivial because the explicit state-lifetime rule is necessary to
prevent a future implementation from retaining a cross-account client cache or
misapplying the heartbeat comparison. It resets the qualifying-review streak.
The run remains planning-only controlled-fixture evidence, not proof of a live
host authorization bridge, deployment, browser rendering, or durable drafts.
