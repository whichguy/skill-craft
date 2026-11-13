# Step-boundary replay (registered 2026-11-13, before any sample)

Owner: "Replay first (Recommended)" (2026-11-12), then "Build, replay after (Recommended)", then "Go" (2026-11-13) on
starting the replay. Earlier evidence: `docs/experiments/step-boundary-replan-20261112/` (E1-E9). Fix forward shipped
in shiploop 1.34.0 (f7a1b450b205ae854a60e149328126252bb44005). Status: **registered; design under Astra max review**.

## Questions

- **Q1, amendment fidelity (fix forward's open question).** After a late send-back, does a model given the shipped
  step-plan packet write an amendment that keeps the done rows exactly (the fix-forward gate passes), and does it amend
  the step that failed? The smoke round had no send-back, so this has run only in hermetic tests.
- **Q2, the forward-impact question (candidate A, modified by Astra).** At the document of the step before a later
  step's Proof fault, does one added duty line make the model flag that fault, without false alarms at clean
  boundaries?

## Apparatus

- The stage suite (`test/shiploop_e2e/stage_suite/stages.py live`) replays one packet against a built state. It runs on
  Codex gpt-6.1-terra at xhigh, the owner's runner.
- Needed first: a builder route (`seed_route`). It is an ordered list of stage results, each with an optional worktree
  overlay, applied after the default seed. It lets a scenario reach a document boundary or a step-plan after a late
  send-back. It is E2E apparatus, not ShipLoop.
- Cases are reconstructed from the late send-backs of `docs/experiments/step-boundary-replan-20261112/late.out`:
  - the item's accepted step plan and test spec, as recorded;
  - each done step's change from its step commit;
  - for Q1, the send-back result as recorded.
  The cases whose run kept Git step commits come first; Salesforce cases need no org, since neither stage deploys.

## Registered measures, predictions and decisions

Q1, one arm (the shipped packet), 4 samples a case, pilot on 2 cases, then the rest:
- Script measures:
  - whether the first `check` of a sample's result passes the fix-forward gate (`_fix_forward_refusal`; refusal
    texts kept);
  - whether the stage is accepted within its loop;
  - whether the failing step's row changed;
  - how many refusals came before acceptance.
- Prediction: at least 90% of samples accepted, and at least 70% passing the fix-forward gate on the first check.
- Decision: below 90% accepted, or below 50% on first check, the packet or route changes. One candidate is a script
  copy of the done rows, Astra's first preference. Otherwise it is kept.

Q2, two arms, B (shipped document packet) and T (B plus one forward-impact duty line), 3 samples per arm per case:
- Cases: the boundary before each Proof fault a planner could have caught, and as many matched clean boundaries (a
  multi-step item with no later fault, from the same runs).
- Oracle, script only:
  - a hit is a send-back, or a recorded amendment, that names the failing step's ID and that case's token,
    registered before its first sample;
  - a false alarm is a send-back or amendment at a clean boundary.
- Prediction: T hits at least 2 more fault cases than B, with at most 1 false alarm in all its clean samples.
- Decision: adopt the line only on both. Even then, it pairs with the deferred route "document done plus an amendment
  request". A document send-back comes before the step commits, so as things stand it still redoes the current step.

No rescoring after the data. A better reading is its own line.

## Revision 1, after Astra's review and before any sample (frozen 2026-11-13)

Astra max (`astra-review.md`): run a revised Q1 pilot; defer Q2. Changes adopted:

- **Q2 is deferred.** Its late faults are planning mistakes, so a hit would show another chance to catch them, not
  that learning from a done step improves the plan. Its clean controls would need new-information cases and validated
  fault-free boundaries. Even a positive result could only justify piloting the deferred route "document done plus an
  amendment request".
- **Defect found and fixed first.** The shipped focused-search refusal missed p0's exact command: the classifier split
  at `;` inside quotes. Fixed in 67f0a329, which is the ShipLoop under test here.
- **Cases, both local, one done step each, contrasting correction types:**
  - `step-plan/replay-p0-late-send-back`: the correction is an item-wide command, focused to check;
  - `step-plan/replay-ticket-comments-late-send-back`: the correction is the failing step's own Proof.
  The longer-prefix late cases are all Salesforce; they are a stated gap.
- **Reconstruction (`reconstruct.py`, manifests in `manifests/`):**
  - the tree when S1 began, knowledge home included (not the neutral seed home);
  - the real planning fields (`seed_from`);
  - the real accepted results through S1, with S1's committed change split by kind and laid at the stage that wrote
    it;
  - the interrupted step's draft left uncommitted, and the recorded send-back.
  `evidence_refs` are emptied so the old run's paths cannot leak.
- **Calibration** on fresh builds (`calibration.txt`). For each case, the real gate (`shiploop check`) and the oracle
  (`q1_oracle.py`) were run on the historical amendment with S1 marked done, and on wrong variants. Every verdict
  went the intended way. The gate accepts a ticket amendment that keeps S2's broken Proof, and only the oracle's
  executable predicate catches it.

Runner: `stages.py live`, Codex gpt-6.1-terra at xhigh, `--ref` the commit that adds this revision, 4 samples a case,
2 at once, fresh sessions. The endpoint is the producer's step-plan result accepted by `complete`. The amendment's
Improve review comes after it and is out of scope here; `finish_improve` rechecks fix forward, as tested in
shiploop-step-edges.

Script measures per sample, every sample reported per case and pooled:
- **M1, accepted:** the producer's result accepted with outcome done (stage-complete), against blocked, timeout or
  crash.
- **M2, first-attempt copy:** no fix-forward refusal text in the sample's events or transcript before acceptance.
  Counted: "are done (reviewed and committed)", "done step ... differs", "no step of ... is done", "every step is
  done". Other gates' refusals are counted separately.
- **M3, fidelity:** `q1_oracle.py fidelity` on the accepted result.
- **M4, correction:** `q1_oracle.py correction`. For p0, no focused command only searches. For ticket-comments, the
  amended S2 Proof differs from the recorded one and exits 0 in the sample's tree.

Predictions over 8 samples:
- M1: at least 7.
- M2: at least 6 (the registered 70%).
- M3: equals M1, since the gate enforces it.
- M4: at least 6.

Decisions:
- M2 at 3 or fewer (below 50%): pilot a prefilled done prefix as a separate arm, prepared before submission, as
  Astra suggested.
- M2 of 4 or 5 keeps the packet despite the missed prediction. A copy slip costs one refusal that prints the rows to
  copy, not a replay.
- M1 below 7: diagnose the cause (copying, another gate, environment) before any change.

Retry policy: a sample that ends for an apparatus reason (host crash, harness timeout, authentication) is rerun once
under a new number and reported. Failures the model causes count. These are development screens, not reliability
estimates: 8 of 8 is a one-sided 95% lower bound near 69%.

Continuation (Astra): after the pilot, one accepted amendment per case is continued through the real CLI with
synthetic later results: test-spec, implement, test, document and commit. The continuation asserts that the done
commit is kept, the cursor names S2, the frozen cases hold, the floors carry and the last step runs the full
regression. Its claim is limited to the route, not a model's continuation.

## Results, Q1 pilot (2026-11-13; firm for these two cases)

Ran `stages.py live` with Codex gpt-6.1-terra at xhigh, `--ref d778b50a` (fix forward plus the classifier fix 67f0a329),
4 samples per case, 2 at once (`~/e2e-runs-sp/20261113/replay-q1-pilot`). Scored by `score_q1.py`
(`q1-pilot-scores.json`); each sample's amendment and verdict are exported in `pilot-samples/`.

| Measure | Prediction | p0 | ticket-comments | Pooled |
| --- | --- | --- | --- | --- |
| M1, accepted done (stage-complete) | at least 7 of 8 | 4 of 4 | 4 of 4 | 8 of 8 |
| M2, no fix-forward refusal before acceptance | at least 6 of 8 | 4 of 4 | 4 of 4 | 8 of 8 |
| M3, fidelity (oracle) | equals M1 | 4 of 4 | 4 of 4 | 8 of 8 |
| M4, correction (oracle) | at least 6 of 8 | 4 of 4 | 4 of 4 | 8 of 8 |

Each sample took 0.9 to 1.3 minutes. Every prediction held. The decision rule keeps the shipped packet and route: no
prefilled-prefix arm is needed.

What the models did:
- All 8 copied the done S1 row exactly, marked done, on the first submission.
- p0: all 4 moved the rg docstring search to suite `check`. Three of them first kept the plan's `check_na`, met one
  refusal ("test_commands has a check row, so drop check_na"), and fixed it. That refusal is unrelated to fix forward.
  It also served as M2's positive control: a check refusal reaches the logs by the same channel a fix-forward refusal
  would.
- ticket-comments: all 4 rewrote S2's Proof. Each new Proof exits 0 against S2's draft in the sample's tree, and none
  added a step.

Continuation (`continuation.py`, `q1-pilot-continuation.txt`): each sample's own amendment was carried through the
route with no model. That covers the review import (`finish_improve` rechecks fix forward), test-spec with the
accepted cases, and validate-existing. All 8 passed every assert:
- the frozen cases were accepted;
- the cursor names S2, with done and built both 1;
- S1's commit is still HEAD;
- S2's draft is still uncommitted;
- where S2 is the last step (p0, 4 of 4), the full regression is due there.

Apparatus finding: the runner graded all 8 samples "overshoot". That was a false positive from `seed_route`:
`stage_live.overshoot` counted the later-stage rows the seed itself recorded. Each sample's history ends with the
seeded send-back, and the amendment parked at its review (checked per sample). Fixed after the pilot: the seed reports
`history_length`, and overshoot ignores rows up to it (shiploop-e2e-stage-live, a new test). The pilot's own records
predate that fix and keep their overshoot verdict; the registered measures do not use it.

Limits:
- Two cases, both with one done step and both local. The longer-prefix and Salesforce cases are not run.
- 8 of 8 is a development screen: the one-sided 95% lower bound is about 69%.
- The continuation is the route's, not a model continuing the item.
- Q2 stays deferred.
