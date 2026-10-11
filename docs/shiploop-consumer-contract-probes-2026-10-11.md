# Consumer contract: probes and owner decisions (journal)

Plan: `docs/shiploop-consumer-contract-plan-2026-10-11.md`. This journal records steps 0 to 2, and the owner's decisions taken on 2026-10-11 in this session.

## Owner decisions (2026-10-11, answered in this session)

1. **Removals approved**, each incorporated or eliminated as plan section 3.2 lists.
2. **Test cases become a state field** (Option A): `test_cases` in the test-spec result, checked at its done, and quoted into the test and verify packets.
3. **No plan copy in the repository.** The plan lives in run state and appears in the report.
4. **Lessons are a release-verify field**, written into its knowledge commit and quoted at the next run's intake from that commit, found by subject.

The owner also agreed that this session's engine work and the inner-loop session's packet work land together on a shared branch, `integrate/refs-consumer-contract`, verified once on the combined result before one fast-forward of main.

## Step 0: consumer reads (done)

Evidence: `docs/experiments/consumer-reads-20261011/` (README with the table).
- The build and test stages barely open the files meant for them.
  - `architecture.md`: 1 read by implement in 7 runs.
  - The test strategy: 0 reads by any test stage.
  - `test-spec.md`: 0 reads by the test stage.
- Some feature files have real later readers, and their content must be quoted into those stages:
  - `plan.md` by step-plan;
  - `system-tests.md` by system-test and product-acceptance;
  - `release-plan.md` by release, release-check and operations.
- The prose hand-off path (`results/*.md`) was opened 4 times in 7 runs.

## Step 2: cleared-context consumer, three slices (done)

Setup:
- Case `node-add-function`, Claude Sonnet 5.5, build `28191c5b`, `slice.py --clear-at` at the implement boundary, inside test, and at the verify boundary.
- Outputs: `/Users/dadleet/e2e-runs/20261011/slice-clear-{implement,test-inside,verify}-28191c5b`.
- The fixture's knowledge home holds the current files, including `test-strategy.md` and `features/`.

| Clear point | Slice result | Redone work (S-6) | Calls after the clear | First calls of the fresh session |
|---|---|---|---|---|
| implement (boundary) | PASS | none | 42 | `next`, then a whole read of the packet file, then work on the product files |
| test (inside, after its first completed call) | PASS | none | 28 | `next`, the packet file, then the loop's terminal receipt and the product files |
| verify (boundary) | PASS | none | 27 | `next`, the packet file, then the Until Loop adapter card and the tests |

**Finding (firm for these three slices; one small one-item case):** a fresh session works from the packet plus the product files. In all three it re-read the whole packet file before acting. None of them opened `state.md`, `results/*.md` or the context index to re-orient. Knowledge files were opened only later and sparingly: `environment.md` a few times when verify recorded a command, `architecture.md` once. Nothing was redone.

So the packet is the consumer's real input after a clear. What the next stage needs must be in the packet, quoted, which is what the plan's `READS` quoting and hand-off fields provide. This one-item fixture does not show whether a larger item would need a living-file section the packet did not quote. Step 5 reruns these clears on the new build.

Cost: the slices record turns (107, 98, 105) but no dollar cost.

## Step 1: next-run consumer, Battleship then the scoring follow-on (running)

Fresh `battleship` on `28191c5b`, output `/Users/dadleet/e2e-runs/20261011/battleship-probe-28191c5b`; `battleship-scoring --continue-from` follows. Results are recorded here when both finish.
