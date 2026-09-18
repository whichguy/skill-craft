# Improve review 1 — material plan correction

## Candidate and scope

Initial candidate: the non-Git Field Notes fixture plus
`<study>/candidate-status-complete/evidence/w1-step-plan.md`
SHA-256 `2f24189fc28715fc246f0740e3b9bbede9888ea9653485651a7455860ef0c2c4`.
Only that planning artifact changed in this review; current SHA-256 is
`7c8b8fa5e06e37a53979b69b399345586a949457d3a36f0f6bdf5313d4d5f8ce`.
The product baseline stayed byte-identical: `app.js`
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`index.html` `f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`,
and `styles.css` `cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.
No product code, product documentation, test, Git, install, remote, deployment,
commit, or W2 change occurred.

## History and review

`git --no-optional-locks -C product -c diff.autoRefreshIndex=false log -7`
was attempted for this cycle and exited as a non-Git fixture; its raw result is
`review-1-git-history.raw.txt`. There are no reachable Git messages to apply.

The fresh independent review record is
`reviewer-one.md`. Its three material findings were accepted: missing
equal-revision rehydration after an account return, an overbroad no-POST test,
and undefined loading/empty/retry accessibility behavior. A source-consistency
triage then found that the interim plan had silently strengthened the frozen
contract by rejecting generic integer revisions, duplicate job IDs, and long
labels. Those are not external prerequisites: W1 can make an explicit client
presentation choice while accepting contract-valid responses.

## Plan and changes

The W1 plan now defines four visible status states, a bounded aggregate-status
presentation, named retry behavior, separate persistent summary and polite
announcement, and same-account error retention versus cross-account clearing.
It scopes the negative request assertion to observer-originated GETs, preserving
the existing note-save POST. It also makes comparison state local to a contiguous
active account view: clearing that view clears its held revision, so a first
matching response after an account return establishes the empty view without
reclassifying an equal held revision. The plan preserves every contract-valid
integer with exact decimal comparison, aggregates statuses without using job IDs
or labels, and adds focused cases proving that these unused fields do not cause
a hidden rejection.

## Checks and learning

After the plan correction, the controlled probe, `node --check product/app.js`,
and `node --test` all exited 0. The raw records are
`review-1-probe.raw.json`, `review-1-node-check.raw.txt`, and
`review-1-node-test.raw.txt`; Node discovered zero tests, so it is a baseline
limit rather than feature coverage. Frozen producer/oracle inputs still matched
the preregistered manifest in `review-1-inputs.raw.json`.

This was a non-trivial review because the interaction/recovery/test contract
changed materially. It resets the trivial-review streak to zero. Two distinct
current qualifying reviews remain required. The fixture is still planning-only:
it does not establish a live host authorization bridge, deployed artifact,
rendered-browser behavior, or persistent-draft capability.
