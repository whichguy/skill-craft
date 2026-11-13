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
