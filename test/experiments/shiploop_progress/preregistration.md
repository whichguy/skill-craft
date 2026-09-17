# ShipLoop progress reporting experiments

Base: `ddca30defddb2de092930c1173b4f3f348c54974`. Synthetic navigator runs only;
no product implementation, external operation or real delivery callback.

## Question and candidate

Can a bounded snapshot derived from existing Markdown state, plus a short user
reporting cue, improve cold-context status orientation without another state
model, misleading completion claims, or a full future-action prompt?

The prototype shows the effective phase/owner/current assignment, accepted
`done` stages and items, current queued work, pending stages, conditional or
skipped skill validation, and paused/blocked/halted/terminal status. An active
assignment is not proof work has started. Improve remains one opaque campaign.

## Experiment 1: state and rendering matrix

Drive the real navigator with synthetic outcomes for both protocol versions.
Independently assert initial state, W1-to-W2 progress, repeated Improve, blocked
and resumed work, pause/halt, optional skill choices, plan/queue replacement and
terminal completion. Confirm reports are read-only, expose one current action,
do not count accepted `repeat` or `blocked` as completed stages, and do not
carry removed queue entries forward. Stress long titles, 1,000 queued items and
repeat histories to check bounded output. Retain phase totals, the current item,
at most three completed and three queued item titles (80 characters each), and
the finite current-phase stage labels (at most 11). Do not duplicate raw context,
summaries, evidence references or the complete history. Target no more than 2,200
characters for the snapshot in the 1,000-item stress case. Show an omitted count
and leave the complete queue in authoritative state. Record failures and refinements.

Success requires correct recorded progress and no schema/callback/route changes.
A rendering assertion does not establish that an agent follows the guidance.

## Experiment 2: fresh-context reporting comparison

Use three cases: W2 verification after W1 completion; blocked Improve after a
repeat; and plan improvement after a queue replacement with unresolved optional
skill routing. A receives the existing packet; B receives the same packet with
the candidate snapshot and reporting cue. Both receive the same user request to
report progress. Run A and B in separate fresh agents using the host default
model. Read only their assigned packet and allowed local state/result files.
No implementation, callbacks, Git, network or external actions are allowed.

Retain raw responses. Give independent judges anonymized, randomly ordered
pairs, their prompts, and a separate fixed truth oracle. Grade current owner,
phase/status, completed versus merely accepted reports, pending queue, optional
routing, next-action conditions, and separation of state from verification.
Compare task adherence, factual accuracy, completeness, instruction following,
structural clarity, precision and conciseness. A factual error cannot be offset
by style. Quality takes priority over character/4 token estimates, then measured
spawn-to-completion wall time. Timing includes orchestration and is indicative.

A case with a failed run is excluded from pairwise judgment and explicitly
reported; a malformed judge is recorded as missing evidence, not a win. With
three cases and one run per variant, results are directional, not a compliance
rate or production benchmark. Preserve the experiment artifacts rather than
removing the only reproduction evidence.

## Decision rule

Adopt the smallest correct snapshot if the state experiment passes and fresh
reports expose no unresolved material reporting error. Use pairwise quality to
refine the reporting cue; do not claim measured improvement if results tie or
are incomplete. Reject percentages/ETAs, child Improve counters, persisted
progress copies and duplicate announcements on unchanged recovery/polls.
