# Improve review five - W1 step-plan

## Candidate and history

Reviewed the corrected blocked W1 plan and all permitted current source/evidence
locators. The required
`git --no-optional-locks -c diff.autoRefreshIndex=false log -7 --format='%H%n%s%n%b%n---'`
read exited 128 because this fixture is non-Git. No repository was initialized.

## Fresh independent finding and correction

A fresh independent read-only review found that the prior epoch contract could
not safely bootstrap the initial request or refetch after a host transition:
the plan required every response to match an already verified epoch but supplied
an epoch only in that response. That would leave no trusted epoch for the first
GET or for post-transition replacement.

Corrected only the allowed W1 plan. The external prerequisite now requires the
host/API owner to provide an initial opaque epoch before the first GET, echo it
in every complete snapshot, and send a replacement epoch with the host transition
signal before refetch. A response never establishes or replaces an epoch itself.
TC-W1-00, TC-W1-01, TC-W1-03, and the harness lifecycle now cover bootstrap,
matching-epoch first response, replacement epoch B after transition, and stale
old-epoch A response rejection. The current fixture provides none of this, so
W1 remains honestly blocked rather than relying on an invented bridge.

The plan's current SHA-256 is
`ea6875069881f33fa2c05bb8cd85829c9a4100dad87aadd1dd9ab25c76286836`.
Product `app.js`, `index.html`, and `styles.css` remain unchanged at
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`, and
`cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.

## Checks and assessment

Current command results are retained in [checks.md](checks.md). `node --check
app.js` passed. `node --test` exited 0 with zero discovered tests, so it remains
a baseline coverage gap. The environment probe is controlled fixture evidence
only. No implementation, dependency, Git, remote, deployment, browser, or
consumer claim is made.

Classification: **non-trivial**. The correction closes a material safety gap in
the conditional host contract and resets the Improve trivial-review count. Two
subsequent distinct full reviews must now find no material plan defect before
the runtime can complete; the final disposition remains that W1 implementation
is blocked until the host/API owner supplies the actual bootstrap and transition
contract.
