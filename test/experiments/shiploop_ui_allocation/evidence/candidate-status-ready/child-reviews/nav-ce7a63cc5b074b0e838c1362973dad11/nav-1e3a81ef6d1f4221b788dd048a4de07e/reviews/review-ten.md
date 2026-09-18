# Improve review ten — W1 step plan

## Candidate and history

Completed a fresh full source-truthfulness review of the W1 plan and permitted
locators. The required
`git --no-optional-locks -c diff.autoRefreshIndex=false log -7 --format='%H%n%s%n%b%n---'`
read exited 128 because this fixture is non-Git. No repository was initialized.

## Fresh independent finding and scoped correction

A fresh independent reviewer found a material internal gate inconsistency: the
plan blocked implementation until both authorization semantics and the complete
response contract existed, but the TC-W1-00/harness wording could bootstrap
feature tests after authorization evidence alone.

Corrected only the allowed W1 plan. The prerequisite, TC-W1-00, and harness
lifecycle now uniformly require both owner artifacts and their controlled fixture
before product edits or feature-test bootstrap. This does not choose any
authorization mechanism, relax the missing external dependency, or create
implementation work.

The corrected plan SHA-256 is
`ab082b6d7d5eb468e7e2c6322fd0af9a55dee1f74b669c99f339e4aae4e3d2e3`.
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

Classification: **non-trivial**. The uniform readiness gate is a material plan
correction and resets the Improve trivial-review count. Two subsequent distinct
source-truthfulness reviews must now find no material plan defect before the
runtime can complete; W1 remains blocked on both host/API owner artifacts.
