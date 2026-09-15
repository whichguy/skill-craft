# Per-work-item state and independent Improve trial

This opt-in experiment uses the public CLI to prepare two work items. Setup is
synthetic, including all W1 actions and the prefix of W2. A fresh agent receives
only a durable locator, recovers W2, and performs one real Improve campaign.
The fixture reuses the correct `clean_lines` implementation and four tests from
the earlier entry/recovery trial; unnecessary edits are not an acceptance criterion.

Run from the repository root with a new output directory:

```sh
python3 -B test/experiments/shiploop_inner_state/prepare.py --output=/tmp/shiploop-inner-state-trial
```

Use the host's normal Git environment. On the current macOS test machine the
existing Command Line Tools require a per-command
`DEVELOPER_DIR=/Library/Developer/CommandLineTools` override; no global setting
or license acceptance is part of the experiment.

## Criteria fixed before execution

1. Cold `next` returns W2's saved `product-improve` action, unchanged by recovery.
2. W1 remains `{stage: done, action: null}` while root is `inner-loop` with no action.
3. The agent performs the full review campaign under the printed owner binding,
   reads available Git history each cycle, runs meaningful checks and records
   two distinct consecutive clean reviews after any material corrections.
4. An independent reviewer examines the actual final fixture; its scope and
   limitations are recorded. Reviewer agreement is not a substitute for tests.
5. ShipLoop remains on the same action throughout the internal reviews. One
   accepted completion returns W2 `integrate`; no Improve subphase/counter is
   persisted and no returned stage is executed.
6. Root grades the final fixture with the existing independent 12-case oracle,
   reruns unit tests, and checks the before/after state and result ledger.

Keep the immutable source specification and synthetic setup labels. Retain the
initial/final state, result, campaign notes, reviewer record and actual grading
output. No source release or host-installation conclusion follows from this toy
fixture. This checks recovery and ownership, not Improve's incremental efficacy.

After the agent's one callback, run `python3 -B
test/experiments/shiploop_inner_state/assess.py /tmp/shiploop-inner-state-trial`.
The assessor checks state/results and fixture behavior; the trial owner must
separately inspect the actual campaign and independent review notes.
