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

## Step 1: next-run consumer, Battleship then the scoring follow-on (done)

Runs:
- A fresh `battleship` on `28191c5b`: PASS, $3.62, 13 minutes, mutation 33 of 38 caught.
- `battleship-scoring --continue-from` it: PASS, $3.76, 193 turns, 16 minutes, 0 refused callbacks.
- Every retention check passed: earlier files kept, no dependency added, tests grew, every earlier requirement ID kept with new ones added (12 IDs).
- Outputs: `/Users/dadleet/e2e-runs/20261011/battleship-probe-28191c5b` and `battleship-scoring-probe-28191c5b`.

**What the cold next run read** (step 0's script on the follow-on; firm for this one pair):
- **The living files, at the right stages.** `spec.md` 8 reads (discovery 2, plan 2, spec 3, carry-forward 1), `architecture.md` 3 (discovery 1, plan 2), `test-strategy.md` 5, `environment.md` 2. It kept the earlier decisions `AD-1` to `AD-4` and added `AD-5`.
- **Three files of the earlier run's feature folder, as precedent:** `test-spec.md` (at test-spec), `system-tests.md` (at system-test-author) and `release-plan.md` (at release-plan).
- **The intake window:** it saw the earlier run's learnings commit second in the last-three-commits window. The order was retire, learnings, leftovers.
- **Citations:** `cited_earlier_run` was 0. The follow-on's Improve children made no commits.

**Finding that changes the contract.** Those three precedent reads are a real cross-run consumer. If the test cases, the system test catalog and the release steps live only in a run's state, the next run cannot read them, because run state is not in the repository. Their persistent part must land in a living file:
- the test ID convention and harnesses in `environment.md`, with the IDs in the test code;
- the system test catalog (command, purpose, requirement) in `environment.md`;
- the release steps and rollback in `environment.md`'s targets and access sections, or a named new section.

Each needs a named consumer: the next run's test-spec, system-test-author and release-plan stages. This was sent to the contract writer for step 3.

## Step 3 audit: three independent read-only audits of the contract (done)

Question: does revision 1 of `docs/shiploop-consumer-contract-2026-10-11.md` hold against the code, the inner-loop packet branch, the cleared slices and the saved runs?

Setup:
- Three Claude Opus 5.5 subagents, each with its own lens: routes (main tenet and gates), KISS (overbuilding and false refusals), and consumer fit.
- Evidence: 17 saved knowledge homes and 18 `state.md` files under `/Users/dadleet/e2e-runs/20261010` and `20261011`.
- Reports: `docs/experiments/consumer-contract-audits-20261011/{routes,kiss,consumer-fit}-audit.md`.

Findings (status: interim; every saved run had one work item):
- **Two blockers.**
  - The empty lessons commit is never returned on an isolated run (found by two audits independently; both step 1 probes would hit it).
  - The "Release and rollback" section gate refuses all 17 saved homes.
- **Heading-based quoting misses most real homes.** For example, "Commands" matched in 8 of 17 homes. The files are small (under 6 KB), so quoting whole files is the recommended fix.
- **Model-typed change lists duplicate a script fact and miss review edits.** The recommended fix is a script-derived diff from one run baseline.
- **Removing the last-commits window conflicts with the owner's 2026-10-10 requirement 4.** The window is kept, and the lessons quote is added beside it.

All corrections are in the contract's section 0A. X1 to X16 are adopted. D1 to D4 change the approved shape and await the owner.
