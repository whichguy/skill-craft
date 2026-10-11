# Live pair on the 8-stage build: journal (started 2026-10-10 evening)

Question: does the build that carries the commit contract, the spec retire step, `architecture.md` and the 8-stage inner loop run a normal case end to end, and what do the new counters show? Method: `python3 test/shiploop_e2e/run.py --case hello --host claude --source checkout` on `13d278dd` (skill-craft 1.27.0 tree plus the unreleased changes), Claude Sonnet 5.5, output `/Users/dadleet/e2e-runs/20261010/hello-8stage-13d278dd` (not committed; compact extract in `docs/experiments/live-runs-20261011/hello-8stage-13d278dd.json`). The Checkers run follows when A2 (section-heading notice) is on main.

## hello (smoke), 13d278dd

**Status: firm for what happened in this one run; no change claim against 1.27.0** (a same-build hello cell on 1.27.0 ranged $3.06 to $5.35 and 126 to 196 turns, n=5; a single run cannot show a difference).

| Measure | This run |
|---|---|
| Outcome | PASS: `shiploop done`, both case checks pass, committed |
| Cost, turns, wall | $2.69, 148 turns, 491 s (planning window closed at test-spec after 3.8 min) |
| Commits in the product repo | 12, all ShipLoop's own (`script` class), 1 with a lessons section (release-verify's `Learned`); 0 Improve commits (the 5 Improve children changed nothing); 0 model commits |
| Knowledge home at the end | `README.md`, `architecture.md`, `environment.md`, `spec.md`, `test-strategy.md`, `features/README.md`, one feature folder without `spec.md` |
| ShipLoop command failures | 3, none repeated: `evidence_refs` cite loop files that do not exist; a result path that was not the current generated path; focused command ids with no `### <ID>` entry in the test-spec file |
| Packet heads measured | 2 of 49 (the model pipes most replies) |

## Findings

1. **The retire step ran.** The terminal close committed `docs(shiploop): retire <folder> spec: checked its requirement IDs against the living spec`, printed that the removal was committed and returned (fast-forward), and the feature folder ends without `spec.md`. `architecture.md` was written at plan and accepted at the prepare close with no refusal.
2. **Defect, observed once: the model wrote `docs/shiploop/features/README.md` itself, so ShipLoop's generated list never existed.** The model wrote it at the spec stage (`1c57117`, "record ... knowledge after spec": a two-line `# Features` list). ShipLoop then left it alone, as designed for a file that does not begin with its mark, and printed the "left ... as it is" notice at the close (twice in the event stream). Cause, from the packets: the intake, plan and release-verify packets say to link the feature list `features/README.md` from `docs/shiploop/README.md`, and at that point the target does not exist yet, so a careful model creates it. Consequence: the four commands that find a requirement ID in the features and the "removed at handoff" header are missing from this run's list. **Fix proposed (two parts, neither built):** (a) packet text owned by the inner-loop session: the link sentence should say "ShipLoop writes that file at its next knowledge commit; do not create or edit it"; (b) engine, mine: decide whether `write_feature_list` should adopt a list the model wrote earlier in the same run (a hand-written file at that path is indistinguishable from a model-written one without run state). Trigger for (b): the packet fix does not stop it in the next pair.
3. **Packets mention the retire and list correctly**, with absolute paths; no prepare refusal; the `ShipLoop knowledge notice:` section notices do not exist yet (A2).
4. The three command failures belong to the inner-loop session's area (loop contract evidence, result path, test-spec command ids); reported to it.

## Checkers (web service, two-player), 88d412e9

Build: `88d412e9` (the 8-stage inner loop, the commit contract, the retire step, `architecture.md`, and the inner-loop session's three fixes from the hello findings, including the feature-list sentence). Claude Sonnet 5.5, `--source checkout`, output `/Users/dadleet/e2e-runs/20261010/checkers-8stage-88d412e9` (compact extract: `docs/experiments/live-runs-20261011/checkers-8stage-88d412e9.json`).

**Status: firm for this one run; single-run differences from the earlier Checkers row are inside the noise of a same-build cell (a hello cell ranged 1.75x in cost), so no claim of change.**

| Measure | This run |
|---|---|
| Outcome | PASS: `shiploop done`, all case checks, held-out 6 of 6, committed; mutation 71 of 107 caught (`js-1`, ratio 0.66, 4 timeouts, 4 port refusals) |
| Cost, turns, wall | $4.27, 215 turns, 1,080 s (planning window closed at test-spec after 6.3 min); previous row: $3.72, 201 turns |
| Commits in the product repo | 20: 12 ShipLoop's own (1 with a lessons section: release-verify's `Learned`), **8 Improve commits, all 8 carrying lessons, 0 citing an earlier commit**, 0 model commits (`other` n=0) |
| Knowledge home at the end | `README.md`, `architecture.md`, `environment.md`, `spec.md`, `test-strategy.md`, `features/README.md` (ShipLoop's generated list), one feature folder without `spec.md` |
| Kept-notices / section notices | 0 / not built yet |
| ShipLoop command failures | 3: `assumptions are allowed only on a done plan result` (twice, the only repeat), `open plan assumptions A3 name W1 as consumer; add an expectation ... from ...` |
| Stage turns vs the previous row | system-test-author 6 to 26 (0.5 to 4.3 min), test-spec 5 to 20, implement 16 to 30, step-plan 8 to 16, verify 3 to 8; stages only in this run: test, validate-existing |

**What it shows against the plan's measures**
1. **Commit contract: the bypass is gone in this run.** All 8 Improve commits went through `improve-commit` and carry `Key learnings`; the model made no commit of its own. The audit measured 14 of 40 Improve-window commits bypassing the gate on the earlier build, and the saved-run baseline has 74 of 136 Improve commits with a lessons section under the shared reader. By construction a commit that passes the gate has lessons, so the informative number is "no commit around the gate", not "8 of 8 have lessons".
2. **Citations did not appear: 0 of 8.** `Learned-from:` is optional and the first run on a fresh repository has few earlier commits worth crediting (the Improve card already makes the child read seven messages). The look-back block (deferred in plan v5 until a baseline existed) is the lever; whether it is worth its bytes needs a follow-on run on this repository, where `cited_earlier_run` can be non-zero. **Next measurement proposed, not run:** a second feature on this same repository, then compare `improve.cited` and `cited_earlier_run`.
3. **The feature-list defect from the hello run did not recur.** With the sentence "ShipLoop writes that feature list at its next knowledge commit; do not create or edit it" the model left the file alone; `features/README.md` is ShipLoop's generated list with the four header commands and was refreshed inside five knowledge commits and the retire commit.
4. **Retire step again made and returned** (`81ae5b0`).
5. **Cost of the 8-stage graph on a larger case is not yet visible as a saving**: the stage-level turns grew in the planning and system-test stages (above); the inner-loop session's own slices found the 8 stages "correct but slower than the 17-stage slices". One run each; the same-build spread must be measured (three or more runs of this cell) before reading this as a change.

## Pair on 1ac83089: section notices, the test-stage mutation gate, commit contract (Checkers, then hello)

Build `1ac83089`: A2 (section constants, one-line-per-file counted notice), the inner-loop session's 8-stage loop with the test-stage mutation gate and prompt coherence, the commit contract, the retire step, `architecture.md`. Claude Sonnet 5.5, `--source checkout`; runs `checkers-sections-1ac83089` and `hello-sections-1ac83089` under `/Users/dadleet/e2e-runs/20261010/`; compact extract `docs/experiments/live-runs-20261011/pair-sections-1ac83089.json`. CI on the pushed commit: green.

| | Checkers | hello |
|---|---|---|
| Outcome | PASS; held-out 6 of 6; mutation **71 of 82 caught (0.866)** | PASS |
| Cost, turns, wall | $4.09, 208 turns, 1,277 s | $3.92, 231 turns, 828 s |
| Previous 8-stage row | $4.27, 215 turns, mutation 71 of 107 (0.664) | $2.69, 148 turns |
| ShipLoop command failures | 0 | 2, not repeated (improve-complete needs the check output; a result path slip) |
| Commits | 19: 5 Improve (all with lessons), 14 script, 0 model | 15: 5 Improve (all with lessons), 10 script, 0 model |
| Citations | 0 of 5 | **1 of 5** (see below) |
| Section notices | **0** | **0** |
| Retire commit | made and returned | made and returned |

**Findings (firm for these two runs; no change claim from single runs).**
1. **Quoting the headings was enough: the counted notice never fired.** In the Checkers run all 21 headings of `spec.md`, `environment.md`, `architecture.md` and `test-strategy.md` were present by the prepare close; in the earlier runs and the saved homes they were a minority (environment "Commands" 1 of 27, test strategy "ID convention" 0 of 27). The measure planned for the counted notice (does quoting `SECTIONS` in the packets make models write the headings) is answered for this case: yes, with no refusal and no notice. Do not turn the notice into a refusal on this evidence; it stays a notice until a run shows a miss.
2. **The test-stage mutation gate moved the mutation score in Checkers from 0.664 (71 of 107) to 0.866 (71 of 82)** (the inner-loop session's change; the harness's own measure, `js-1`), at about the same cost and turns. One run each; the inner-loop session's cause (the base run passed on load failures alone) explains the direction.
3. **First live citation.** In the hello run an Improve commit (`9dfc6cc`) carries `Learned-from: fb1d3f5113a7... first fixed the ID rule in plan.md only.`, a full id that git resolves, crediting the step-plan commit that first fixed the rule and drawing the lesson "when a rule is corrected mid-run, grep every knowledge-home file for the old wording". The commit contract's citation requirement works end to end; `cited_earlier_run` stays 0 until a second feature runs on an earlier run's repository.
4. **hello cost is inside the old range but the turns are not.** $2.69 and $3.92 sit inside the 1.27.0 same-build range ($3.06 to $5.35, n=5); the turns (148 and 231) straddle its 126 to 196. Stage turns that grew in the second run: step-plan 19 to 38, carry-forward 6 to 18 (it rewrote `test-strategy.md` and `architecture.md` to fix a rule it had changed). **Two runs of the 8-stage hello cell do not show a change; run three more on this build before any claim**, because hello cost rising is a standing concern.

## Next
Checkers (source=checkout) once A2 is on main and the build includes the packet fix for finding 2, then the counters (`metrics.commits`), kept-notices, `ShipLoop knowledge notice:` lines and the hello and Battleship deltas are read for both runs.
