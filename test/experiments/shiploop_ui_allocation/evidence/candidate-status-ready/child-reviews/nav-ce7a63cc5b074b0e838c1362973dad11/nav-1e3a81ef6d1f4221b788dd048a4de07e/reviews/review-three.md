# Improve review three - W1 step-plan

## Candidate and history

Reviewed the current W1 planning candidate at
`<study>/candidate-status-ready/evidence/w1-step-plan.md`
against the permitted Field Notes sources, controlled schema, raw baseline
evidence, current child reviews, and frontend guidance. The required
`git --no-optional-locks -c diff.autoRefreshIndex=false log -7 --format='%H%n%s%n%b%n---'`
read exited 128 because this fixture is not a Git repository. No repository was
initialized and no Git action was taken.

## Fresh independent review and material correction

A fresh read-only independent reviewer found that the plan incorrectly treated
the local note selector as an export authorization transition. The controlled
schema scopes `GET /api/exports` by host authorization, while the current
`switchAccount` implementation changes only local `state.account`; no permitted
source supplies an identity/epoch or event that connects those two scopes. The
same review also found that the visibility test lacked the race in which a
request started while visible resolves after the document becomes hidden.

Accepted both findings and corrected only the allowed W1 plan. It now blocks W1
implementation until the host/API owner supplies a documented, testable
authorization-context bridge; it does not invent one or relabel host status as
Alpha or Beta. The conditional future design uses an opaque verified epoch,
generic current-authorized copy, and a clear-on-authorization-mismatch rule.
TC-W1-00 records the prerequisite, TC-W1-03 keeps selector changes separate
from authorization epochs, TC-W1-04 covers a fulfilled-after-hide response,
and TC-W1-05 covers epoch/authentication clearing. The bounded summary also
uses a neutral aggregate for an initial or multi-change snapshot, avoiding a
fabricated chronology.

The plan's current SHA-256 is
`9821d94324bd34cd54ed095eef608aa2e792c4591be9b59d5ed5e8dec2012ce3`.
Product `app.js`, `index.html`, and `styles.css` remain unchanged at
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`, and
`cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.
No product source, test, documentation, configuration, host observation,
package, account, remote target, deployment, or parent run state changed.

## Checks, disposition, and next review

Current command results are retained in [checks.md](checks.md). `node --check
app.js` passed. `node --test` exited 0 with zero discovered tests, so it is a
baseline coverage gap rather than feature evidence. The environment probe still
reports controlled fixture facts only; no browser, live deployment, or consumer
claim is made.

Classification: **non-trivial**. The former ready-to-implement plan had an
unsafe account-attribution assumption, and the corrected plan now truthfully
blocks W1 implementation on an external host/API contract. This is a planning
disposition, not product implementation or proof of the future control. Improve
remains active for two later distinct complete no-change reviews of this corrected
plan. Those reviews must preserve the non-Git history limit, rerun current local
checks, avoid source changes, and confirm that the external prerequisite is not
mistaken for fulfilled evidence.
