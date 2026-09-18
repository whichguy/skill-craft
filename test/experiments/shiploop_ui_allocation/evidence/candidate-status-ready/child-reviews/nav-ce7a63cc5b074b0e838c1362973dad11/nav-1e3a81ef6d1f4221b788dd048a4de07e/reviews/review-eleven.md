# Improve review eleven — W1 step plan

## Candidate and history

Completed a fresh full source-truthfulness review of the W1 plan and permitted
locators. The required
`git --no-optional-locks -c diff.autoRefreshIndex=false log -7 --format='%H%n%s%n%b%n---'`
read exited 128 because this fixture is non-Git. No repository was initialized.

## Fresh independent finding and scoped correction

A fresh independent reviewer found that the plan inaccurately said the account
selector changed only local `state.account`. The actual `switchAccount()` also
reloads the account-scoped note list. That does not establish export
authorization, but the narrower distinction must be stated accurately.

Corrected only the allowed W1 plan: it now records the local note-state/list
reload and preserves the actual blocker that no permitted source attributes,
changes, or invalidates the export host-authorization scope through the selector.
The no-selector-for-export rule, owner-artifact gate, and no-implementation
scope are unchanged.

The corrected plan SHA-256 is
`33f8edb38afb747c1dfcf82d73d62790a5bb3796ff99b1766b855833b14913cd`.
Product `app.js`, `index.html`, and `styles.css` remain unchanged at
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`, and
`cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.

## Checks and assessment

Current command results are retained in [checks.md](checks.md). `node --check
app.js` passed. `node --test` exited 0 with zero discovered tests, so it remains
a baseline coverage gap rather than W1 feature evidence. The environment probe
records controlled fixture facts only. No implementation, dependency, Git,
remote, deployment, browser, or consumer claim is made.

Classification: **trivial**. This is explanatory polish: the source wording now
names the existing note-list reload, while the proposed export behavior, scope,
owner obligation, blocker, contracts, and checks are unchanged. The runtime
determines the qualifying-review streak after the exact callback.
