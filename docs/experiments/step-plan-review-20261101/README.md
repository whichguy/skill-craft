# Step-plan review: evidence (2026-11-01)

Read-only measurements of ShipLoop's `step-plan` stage over every saved run with a trace on this machine, for the review
in [docs/shiploop-step-plan-review-2026-11-01.md](../../shiploop-step-plan-review-2026-11-01.md). No model ran.

## Corpus

`traces.txt`: 112 `RUN/trace.jsonl` files with more than 30 events, from `~/e2e-runs` (2026-10-25 to 11-01) and its
sibling folders (`~/e2e-runs-brownfield`, `-hostonly`, `-multipass`, `-owner-note`, `-pf`, `-qr`, `-xr`). Paths under
`docs/shiploop-run-trace-evidence/`, Grok marketplace caches and seed slices are left out. Hosts and models: Codex
`gpt-6.1-terra` (high and xhigh) in most runs; DeepSeek v4.1 flash, Grok 4.7 and Sonnet 5.5 in a few. ShipLoop 1.12.0
to 1.26.1; read a version from each run's `invocation.json` (`versions.shiploop_version`).

## Rerun

```sh
python3 -I step_plan_review.py traces.txt .     # runs, sendbacks, replay_ids, improve_passes (.jsonl) + headlines
python3 -I replay_proofs.py traces.txt replay_proofs.jsonl
```

`step_plan_review.py` imports the shipped `shiploop_test_loop.criteria_without_ids`, so `replay_ids.jsonl` is the gate
this review adds, replayed on every accepted step plan.

## Files

| File | Rows | What |
|---|---|---|
| `runs.jsonl` | 112 | per run: case, model, effort, ShipLoop version, elapsed seconds; per step-plan action its authoring and Improve seconds, checks and refusals |
| `sendbacks.jsonl` | 50 | every send-back to step-plan: sending stage, headline, summary (cut), minutes wasted downstream and minutes to redo the step plan |
| `sendback_classes.jsonl` | 50 | the class of each send-back, read from its headline and summary (legend below) |
| `replay_ids.jsonl` | 175 | every accepted step plan: the criteria left without a focused ID, and the next test-spec's outcome |
| `replay_proofs.jsonl` | 376 | every step: which candidate Proof rule (N1-N4) flags it, and its implement outcome |
| `improve_passes.jsonl` | 239 | every step-plan Improve pass (label, whether it changed the plan, seconds) |
| `replay_rule_c.jsonl` | 171 | side replay (`replay_rule_c.py`): plans with a recorded lint item base, whether Rule C flags the first step's Proof (a whole segment that is a focused command whose IDs no tracked base file holds), and S1's implement outcome |

Live checks: `launch_sp1.sh` and `score_sp1.py` (SP1, whole deliveries), `launch_sp2.sh` and `score_sp2.py` (SP2, step-plan
slices, arm B against arm T), `launch_sp3.sh` (SP3, slices on the wording fix, read by `score_sp2.py`); pre-registered in the
review's §7 and run on Codex Terra 6.1 xhigh. Scores: `sp2_scores.jsonl` (16 slices), `sp3_scores.jsonl` (4); results in the
review's §7a.

Send-back classes: `proof-test-path` (the Proof runs a test file the test stage writes later; refused at step-plan since
ShipLoop 1.25.0), `proof-test-no-path` (the same need without a file path: `npm test`, unittest discovery, an Apex class
name, or a criterion that asks for the test at implement), `focused-id-short` (fewer focused IDs than the criteria a
focused command names), `proof-command-defect` (quoting, a wrong API or setup, a non-portable flag),
`proof-not-repeatable` (a Proof that creates state, such as a permission-set assignment, fails when run again),
`runner-ids-or-floor` (IDs the runner cannot print, or a floor it cannot reach), `needs-later-step` (a minimum
regression or a case needs a later step's work), `other`.

## Headlines

| Measure | Value |
|---|---|
| step-plan actions | 178 in 112 runs |
| step-plan share of a run's elapsed time | median 11.3% |
| authoring minutes (packet to accept) | median 0.61, mean 1.16 |
| Improve review minutes (157 reviews) | median 0.55, mean 0.95 |
| checks / refusals in the step-plan loop | 275 / 141 |
| send-backs to step-plan | 50 (implement 32, test-spec 12, test 6) |
| send-backs on ShipLoop >= 1.25.0 (and the A/B's refusal arm) | 19: focused-id-short 8, proof-command-defect 4, proof-test-no-path 3, proof-not-repeatable 2, needs-later-step 2 |
| focused-ID rule on 175 accepted plans | refuses 24: 9 came back from test-spec, 15 folded a criterion into another's case; 0 refusals of a plan whose every criterion had its own case |
| step-plan Improve reviews that changed the plan | 62 of 155; 22 of the 24 short plans had a review, and the shortage survived each |
| candidate no-path Proof rules (steps flagged: send-back / done / no implement) | N1 10/12/18, N2 7/11/23, N3 4/2/3, N4 7/30/11 |
