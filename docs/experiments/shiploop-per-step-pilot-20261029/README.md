# Per-step iteration pilot, 2026-10-29

The pilot design T §9.1 asked for (step 5 of the build order; the "proposed pilot" of 2c-3): one step slice with at least two
steps on the ask-agent route, and the same case inline as the control. Run on Codex with `gpt-6.1-terra` at xhigh (owner,
2026-10-29, after the Ollama monthly limit), not on the E2E default subject. A third run, the same case on the item-level
ask-agent route that existed before the 2c build, is the baseline the new route replaces.

| run | route | ShipLoop at | output (not kept; evidence below) |
|---|---|---|---|
| `inline/` | inline, the control | `f0127708` | `~/e2e-runs/20261029/pilot-terra-inline-32f436` |
| `ask-agent/` | ask-agent, one implement action per step (2c) | `f0127708` | `~/e2e-runs/20261029/pilot-terra-ask-agent-32f436` |
| `ask-agent-old/` | ask-agent, item level (before 2c-1) | `a949ee29` | `~/e2e-runs/20261029/pilot-terra-ask-agent-OLD-32f436` |

Case `stand-in-parser` (`test/shiploop_e2e/step_cases.json`): "add `parseRecords` and `select` in `src/records.js`", planned as two
steps in every run. Command (from a detached worktree at the commit above):

```sh
python3 -B test/shiploop_e2e/slice.py --case stand-in-parser --host codex --model gpt-6.1-terra --effort xhigh \
  --delegation <inline|ask-agent> --timeout 14400 --output <new dir>
```

## What each directory holds

- `slice-result.json`, `metrics.json`, `packet-report.md`, `invocation.json`: the slice harness's own output, unchanged.
- `run-review-facts.md`: Run Review's exporter (`skills/shiploop-run-review/scripts/export.py <output> --no-html`) on the run.
- `product-commits.txt`, `iteration-ledger.json`: the product worktree's commits, and ShipLoop's per-step ledger (base and commit
  of each step).
- `threads.json`: `tally_threads.py <output>`, which reads the Codex threads under `<output>/home/.codex`: how many, what each
  cost, and the workers the parent started (`task_name`, and `fork_turns`: "none" is a fresh context).

## Numbers

| | inline | ask-agent (per step) | ask-agent (old, item level) |
|---|---|---|---|
| verdicts (process, inner loop, no overshoot, assembled, checks) | all pass | all pass | all pass |
| first accept to last accept | 5.3 min | 21.6 min | 17.3 min |
| main-thread model calls | 74 | 124 | 110 |
| Codex threads (parent + workers) | 1 | 14 | 9 |
| input tokens (cached) | 8.06 M (7.89 M) | 23.11 M (22.23 M) | 19.94 M (19.30 M) |
| output tokens | 23.5 k | 105.2 k | 85.1 k |
| packets printed | 221.0 KB | 254.0 KB | 181.9 KB |
| ShipLoop refusals (run trace) | 3 (`check`) | 0 | 6 (`check` 4, `complete` 2) |
| Improve children / review passes | 4 / 5 | 4 / 9 | 3 / 6 |
| commits on the product | `feat(W1/S1)`, `feat(W1/S2)` | `feat(W1/S1)`, `feat(W1/S2)`, one review fix | one `feat: W1 ...` item commit, one review fix |

The new route against the old: 1.25x the time, 1.16x the input tokens, 1.24x the output tokens, 13 workers against 8. Against the
control: 4.1x the time, 2.9x the input tokens, 4.5x the output tokens.

The new route's 13 workers all started with `fork_turns: none`. Per step there are four (implement, test, document and the step's
review), so 8 for two steps ("4n"); the other five are the step plan, its review, the test spec, carry-forward and the final
review. The old route's 8 workers were the step plan, its review, the test spec, one test stage, one document stage, its review,
carry-forward and its review. It started no separate implement worker (the item's implement is not a thread of its own).

## Limits

- One case, one run per arm, two steps: the verdicts and the commit shape are firm for this case; the cost ratios are indicative.
- The "model calls", "context peak" and "seconds" figures are the main thread's. The workers' cost is in `threads.json`.
- The messages between agents are encrypted on this host, so what a worker was told (context fidelity) cannot be read.
- No run had a preparatory fix or a send-back, so the bases after those are not exercised here (unit tests cover them).
- The crash windows inside the commit stage and a killed implement worker cannot be provoked from the slice harness.
- The old run was saved before state version 11, so Run Review says its executed steps are "not measured" (it still reads it).
