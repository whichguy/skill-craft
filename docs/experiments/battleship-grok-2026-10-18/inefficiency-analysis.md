# Battleship on Grok, 2026-10-18: where the time went

Status: **interim**. The run was still active when this was written (W2 implement S1 had reached its Improve stage at 00:19Z).
Snapshot taken 2026-10-19 00:19Z. The analysis was read-only: nothing under the run directory was written.

- Run: `/Users/dadleet/e2e-runs/2026-10-18/battleship-1`. Host Grok `grok-4.7`, effort medium. Published skill-craft 2.6.0 / ShipLoop 1.6.0. `planning_review: stage`, inline delegation.
- The harness ran with `--timeout 7200` (its default is 10800) and `--max-resumes 20`. The first attempt was killed at 2 h; it was resumed with `--resume-run` ([battleship-1-resume.log](/Users/dadleet/e2e-runs/2026-10-18/battleship-1-resume.log)).
- ShipLoop run dir: `.shiploop-runs/work-20261018-212526-5fb41b/run`, which this report calls RUN. The product worktree is `.../worktree`, which it calls WT.
- Elapsed at the snapshot: 174 min from `started` (21:25:26Z), plus 1.7 min of host time before `workspace start`. The run had **1,090 host tool calls**, 635k output and 354k reasoning tokens, 10 auto-compactions and 6 host sessions.
- Comparison runs:
  - Grok r3/v1230 ran with planning reviews off. Planning took 17–20 min, step-plan 56–117 s and test-spec 28–51 s (`metrics.json` stages).
  - The latest Claude Sonnet baseline (ShipLoop 1.4.0, planning review on) finished the **whole run** in 36 min, with 711 s of planning ([baselines.jsonl](/Users/dadleet/src/skill-craft/test/shiploop_e2e/baselines.jsonl), case battleship, 2026-10-16).

## Method

- **Stage windows.** Each stage runs from the previous action's accept time to its own accept time, both from RUN/timeline.json. The history order comes from RUN/state.md. The current stage runs from 00:10:56 to the mtime of events.jsonl. Host time before `workspace start` counts toward intake.
- **Drafting vs Improve.** The Improve window starts at the mtime of `RUN/improve/<action>-bind.md` and ends at the accept time. Drafting is the rest of the window. The pass count is the number of rows in `RUN/improve/<action>/passes.md`.
- **Event times.** `timeline.jsonl` gives a wall time for an events.jsonl line number. Each event gets the time of the nearest earlier timestamped line. Session boundaries come from `sessions.jsonl` `events_line`.
- **Tokens.** Tokens are the sum of the `usage` events (one per model call) inside each window. `output_tokens` and `reasoning_tokens` are reported as recorded.
- **Call categories.** Each `tool_call` is classified by tool name and `rawInput`:
  - **src reads:** read_file, grep or list_dir under `installed-plugins/.../skills/` (ShipLoop or Improve source), or a shell command that reads it.
  - **CLI:** `scripts/shiploop <sub>` (complete, with `--check-only` counted separately; improve-pass; next; lint; improve-commit; red-check) and `until_loop_ephemeral.py`.
  - **run-dir r/w:** RUN/packets, results, inbox, notes, state.md and loops.
  - **knowledge r/w:** WT/docs/shiploop and SHIPLOOP.md.
  - **product r/w:** other WT files.
  - **Improve files:** WT/.shiploop-improve.
  - **test & cmds:** node --test, node, git and other shell.
  - **scratch:** RUN/scratch writes and runs.
  - **refused:** a run_terminal_command whose update says "User cancelled the execution", which matches stderr.txt "permission required".
- **Idle.** Idle is the sum of gaps longer than 45 s between consecutive timestamped events. Such gaps are long generations (big file writes) or compactions.
- **Minutes per category.** Each tool call is charged the interval since the previous call (capped at 300 s, with compaction time removed). This is an approximation used only to rank sinks.

The analysis was ad hoc Python over these files; the numbers below can be re-derived with the same rules.

## 1. Per-stage table

The CLI column counts real complete / check-only / improve-pass / next / until-loop / other.

| # | stage | WI | accepted (UTC) | wall min | draft min | Improve min | passes | calls | out tok | reasoning tok | src reads | CLI | run-dir r/w | knowledge r/w | product r/w | Improve files | test & cmds | scratch | refused | idle >45 s min | compactions (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | intake |  | 21:26 | 1.0 | 1.0 | 0.0 |  | 14 | 6,139 | 3,120 | 3 | 1 / 1 / 0 / 0 / 0 / 3 | 1/2 | 0/0 | 0/0 | 0 | 2 | 0 | 1 | 0.0 | 0 |
| 1 | discovery |  | 21:28 | 1.8 | 1.8 | 0.0 |  | 20 | 6,610 | 1,870 | 5 | 1 / 1 / 0 / 0 / 0 / 0 | 1/4 | 2/2 | 0/0 | 0 | 3 | 1 | 0 | 0.0 | 0 |
| 2 | research |  | 21:31 | 2.9 | 2.9 | 0.0 |  | 21 | 9,487 | 3,385 | 2 | 1 / 1 / 0 / 1 / 0 / 0 | 1/3 | 2/3 | 0/0 | 0 | 2 | 4 | 1 | 0.0 | 0 |
| 3 | spec |  | 21:37 | 6.4 | 2.2 | **4.2** | 3 | 37 | 22,225 | 10,469 | 2 | 2 / 1 / 3 / 0 / 4 / 0 | 0/1 | 4/4 | 0/0 | 9 | 5 | 2 | 0 | 1.8 | 0 |
| 4 | test-strategy |  | 21:57 | 19.7 | 2.3 | **17.4** | 7 | 117 | 79,939 | 35,356 | 5 | 2 / 1 / 7 / 1 / 6 / 5 | 0/2 | 12/35 | 0/0 | 26 | 13 | 2 | 0 | 6.9 | 1 (1.1) |
| 5 | plan |  | 22:12 | 15.1 | 2.7 | **12.5** | 4 | 87 | 57,907 | 32,069 | 15 | 2 / 1 / 4 / 1 / 6 / 3 | 4/5 | 7/7 | 0/0 | 18 | 12 | 2 | 0 | 3.1 | 1 (1.5) |
| 6 | prepare |  | 22:13 | 1.4 | 1.4 | 0.0 |  | 15 | 5,914 | 3,163 | 4 | 1 / 1 / 0 / 0 / 0 / 0 | 0/2 | 2/3 | 0/0 | 0 | 1 | 1 | 0 | 0.0 | 0 |
| 7 | step-plan | W1 | 22:30 | 17.1 | **9.8** | 7.3 | 5 | 127 | 65,677 | 35,614 | **56** | 2 / 3 / 5 / 1 / 6 / 0 | 8/1 | 5/0 | 0/0 | 7 | 7 | 26 | 0 | 8.0 | 1 (1.3) |
| 8 | test-spec | W1 | 22:43 | 12.4 | 6.2 | 6.2 | 4 | 69 | 41,536 | 25,352 | 23 | 2 / 3 / 4 / 1 / 7 / 0 | 7/4 | 5/0 | 0/0 | 6 | 6 | 1 | 0 | 4.2 | 1 (1.4) |
| 9 | validate-existing | W1 | 22:43 | 0.0 | 0.0 | 0.0 |  | 0 | 0 | 0 | 0 | 0 / 0 / 0 / 0 / 0 / 0 | 0/0 | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0.0 | 0 |
| 10 | implement S1 | W1 | 22:55 | 12.1 | 5.6 | 6.5 | 3 | 59 | 41,549 | 26,356 | 2 | 2 / 0 / 3 / 1 / 7 / 4 | 6/4 | 3/0 | 4/3 | 10 | 8 | 2 | 0 | 2.1 | 1 (1.3) |
| 11 | implement S2 | W1 | 22:57 | 2.3 | 1.2 | 1.1 | 1 | 17 | 7,424 | 2,992 | 0 | 2 / 0 / 1 / 0 / 4 / 1 | 0/2 | 0/0 | 0/0 | 3 | 3 | 1 | 0 | 0.0 | 0 |
| 12 | implement S3 | W1 | 23:01 | 4.3 | 1.7 | 2.7 | 1 | 20 | 11,018 | 4,631 | 0 | 2 / 0 / 2 / 1 / 4 / 1 | 0/2 | 1/0 | 0/1 | 1 | 4 | 1 | 0 | 1.1 | 1 (1.1) |
| 13 | implement S4 | W1 | 23:06 | 4.6 | 2.1 | 2.5 | 1 | 34 | 16,337 | 8,316 | 1 | 1 / 0 / 1 / 0 / 4 / 2 | 6/2 | 1/0 | 4/2 | 5 | 3 | 2 | 0 | 0.0 | 0 |
| 14 | test | W1 | 23:10 | 3.4 | 3.4 | 0.0 |  | 19 | 12,959 | 7,191 | 0 | 2 / 2 / 0 / 0 / 2 / 2 | 3/2 | 2/0 | 0/1 | 0 | 2 | 1 | 0 | 1.4 | 0 |
| 15 | document | W1 | 23:12 | 2.1 | 2.1 | 0.0 |  | 35 | 10,175 | 3,276 | 0 | 1 / 0 / 0 / 0 / 2 / 0 | 0/2 | 10/17 | 1/0 | 0 | 1 | 1 | 0 | 0.0 | 0 |
| 16 | verify | W1 | 23:13 | 1.4 | 1.4 | 0.0 |  | 10 | 5,442 | 2,648 | 0 | 1 / 1 / 0 / 0 / 2 / 0 | 2/2 | 0/0 | 0/0 | 0 | 1 | 1 | 0 | 0.0 | 0 |
| 17 | carry-forward | W1 | 23:18 | 5.4 | 5.4 | 0.0 |  | 52 | 15,405 | 6,669 | 14 | 1 / 1 / 0 / 1 / 3 / 0 | 5/3 | 8/9 | 0/0 | 0 | 5 | 2 | 0 | 1.4 | 1 (1.4) |
| 18 | step-plan | W2 | 23:56 | **37.1** | **31.7** | 5.4 | 3 | 200 | 138,990 | 91,372 | **81** | 2 / 1 / 3 / 4 / 8 / 0 | 18/1 | 12/0 | 5/0 | 8 | 11 | **44** | 2 | 18.0 | 1 (3.1) |
| 19 | test-spec | W2 | 00:10 | 14.8 | 9.3 | 5.6 | 3 | 82 | 52,591 | 33,549 | 21 | 2 / 2 / 3 / 1 / 6 / 0 | 19/6 | 5/0 | 1/0 | 5 | 10 | 1 | 0 | 4.6 | 1 (1.2) |
| 20 | validate-existing | W2 | 00:10 | 0.0 | 0.0 | 0.0 |  | 0 | 0 | 0 | 0 | 0 / 0 / 0 / 0 / 0 / 0 | 0/0 | 0/0 | 0/0 | 0 | 0 | 0 | 0 | 0.0 | 0 |
| 21 | implement S1 (current) | W2 | (00:19) | 8.7+ | 5.9 | 2.8+ |  | 55 | 27,570 | 16,950 | 6 | 1 / 1 / 1 / 1 / 3 / 2 | 10/2 | 4/0 | 4/2 | 6 | 6 | 6 | 0 | 2.3 | 1 (1.4) |

### Rollups

| span | wall min | of which Improve | earlier Grok (reviews off) | notes |
|---|---|---|---|---|
| Outer planning, intake through prepare | 48.3 | 34.1 | 17–20 | Drafting was 14.2 min, which is **faster** than before. The whole regression is Improve. |
| Inner planning, step-plan and test-spec for W1 and W2 | 81.4 | 24.5 | about 2–5 for both items | Drafting was 57 min, of which about 20 min is restarts and compaction (section 4). |
| W1 build, implement S1–S4 | 23.3 | 12.8 | – | Improve found one real defect (section 3). |
| W1 test, document, verify, carry-forward | 12.3 | 0 | – | |
| All Improve | 74.2 | | | 11 bound reviews, 36 passes. |
| Source reads | 240 calls (22 %) | | | 201 ShipLoop, 37 Improve/until-loop, 2 shell. |

### Corrections to the "already known" figures

- **Planning.** 48 min is confirmed (48.3).
- **Improve passes.** Spec 3 (4.2 min) and test-strategy 7 (17.4 min) are confirmed. Plan had **4** passes, not 5 (12.5 min); see `RUN/improve/nav-9f56…/passes.md`.
- **Tool calls.** The count has grown to 1,090, and 240 are ShipLoop or Improve source reads, not about 210.
- **W2 step-plan drafting.** 31.7 min is confirmed. It includes the **harness 2 h kill at 23:23:45**, which was not a refused command. A *fresh* host session followed, then two refusal restarts.
- **CLI failures.** Both CLI failures are confirmed, and each cost seconds (section 4).

## 2. Top time sinks, ranked by minutes

### S1. Improve on planning-choice stages: 58.6 min (spec, test-strategy and plan 34.1; inner step-plan and test-spec 24.5)

**Evidence**

- Pass seconds by review (from `passes.md`):

  | review | pass seconds |
  |---|---|
  | test-strategy | 495 / 152 / 76 / 118 / 71 (non-trivial), 39 / 51 (trivial) |
  | plan | 425 / 162, then 74 / 65 |
  | spec | 104, then 70 / 59 |
  | step-plan W1 | 202 (non-trivial), 73 (trivial), **60 (non-trivial, which reset the streak)**, 39 / 41 |
  | test-spec W1 | 170 / 84, then 47 / 38 |
  | step-plan W2 | 181, then 53 / 35 |
  | test-spec W2 | 224, then 55 / 33 |

- Confirmation-only passes (trivial, no edit) on these seven reviews took **12.9 min** of pass time, before improve-pass and bookkeeping overhead.
- The test-strategy draft took 2.3 min and its Improve took 17.4: Improve, not the stage, wrote the strategy. Review 1 says "names replay inputs for TC-1 through TC-12 and TC-B1" (WT/.shiploop-improve/test-strategy-700d1520/reviews/review-1.md).
- Each test-strategy pass found a *new* precision gap rather than a defect left by the previous pass. Review 4 found "TC-9 named the shared cell and not the other cells", then added a `[integer, integer]` log regex and the five ship names.

**Root cause in ShipLoop**

- **Mode default.** `DEFAULT_PLANNING_REVIEW = "stage"` (`shiploop_stage_spec.py` `reviewed_stages`) starts an Improve child on spec, test-strategy, plan, step-plan and test-spec. Earlier comparable runs used `none`.
- **Stop rule.** `required_trivial_reviews=2` (`shiploop_navigator.py`) means every review that changes anything costs at least two more passes. That floor is about 1.5–2.5 min per review even when nothing more is found.
- **Open-ended focus.** The Improve handoff's planning focus (`handoff.md`, "What this review looks for") includes "a step, example or expected result that cannot be replayed exactly: name the concrete inputs, values, identifiers" and "a weaker stand-in would pass". For a 12-case test strategy, a further case can always be made more exact. The focus has no materiality bar such as "would a later stage build or test the wrong thing?". So every tightening was classified non-trivial and reset the count (the test-strategy reviews 2–5 each say the change counts as non-trivial because it changed an oracle).
- **Self-edits as non-trivial.** On inner step-plan and test-spec, the review edits only the inbox result. passes.md shows "non-trivial | tree changed **n**", and the model still classifies those self-edits non-trivial. Step-plan W1 pass 3 reset the streak by tightening a throwaway check script ("C4 and S4 now require the accepted ships to come back in input order").

### S2. Bespoke per-step `check` programs in step-plan: about 24 min of drafting (W1 about 6, W2 about 18 net of restarts), plus Improve passes spent tightening them

**Evidence**

- The accepted W2 step-plan result (`RUN/results/nav-b60de39abbe64570920b3124246fe99a.md`) is **53 KB**. Its six step `check` values are one-line programs of **6,404 / 5,689 / 5,909 / 7,376 / 4,558 / 6,433 bytes**, 36 KB of minified JavaScript in total. The product at that point was game.js plus an 87-line server.js. W1's four checks were 0.8–1.3 KB each.
- Scratch time charged to step-plan: W1 5.3 min (26 scratch calls), W2 **11.2 min (44 calls)**. Thoughts from the W2 step-plan:
  - "I need to rewrite checks to be async without Atomics.wait" (events line 24603, 23:38:43).
  - "Port 1 is blocked by an EACCES permission error" (line 23600).
  - "Step checks must be one nonblank line" (line 25235).
  - "Minifying JS to one line for the node command" (line 20749).
- The first draft of the checks (23:19–23:23, scratch/w2-s1..s4-check.js) was lost to the harness kill. The fresh session rebuilt them under scratch/w2-plan.
- These checks are what step-plan Improve then reviewed and tightened (step-plan W1 reviews 1 and 3; step-plan W2 review 1, "S4 accepted any element with id=\"new-game\"").

**Root cause (step-plan packet duty 4, `RUN/packets/nav-b60de39….md` lines 109–123)**

- Duty 4 requires each step's `check` to be "the one command … that proves the step's criteria with only this step and accepted earlier ones. It needs no later step, unwritten test".
- It also says "Tests are not a step … a step changing only test files is refused".
- Together, these force the model to write a private test harness (spawning servers, polling ports, parsing HTML) as a shell one-liner for every HTTP step. It is thrown away once the test stage writes the real node:test files.
- The `test ! -e`/`;`/quoting rules ("no pipe, redirect, \";\" or shell variable" in the callback line, and the one-line requirement) add shell-escaping work on top.

### S3. Reverse-engineering ShipLoop and Improve source: 240 calls, about 28 min (cluster A 11.2, B 5.4, C 3.9, references 3.0, D 1.8, E 1.3)

What the model searched for, by cluster:

**A. Result gate and schema: 94 calls (step-plan W1 23, W2 50, test-spec 18, carry-forward 3)**

- Symbols searched: `check_step_plan`, `_normalise_steps`, `normalise_test_commands`, `check_na`, `min_tests`, the strings "criterion no command names" and "unlisted", `normalise_expectations`, `EXISTING_STATES`, `write_problem`, `_FORBIDDEN`, `_SEPARATORS`, `HANDOFF_PLACEHOLDERS`, `RESULT_KEYS`, `_DONE_ONLY_FIELDS`, `OPEN_ITEM_STAGES`, `HEADLINE_LIMIT`, `requirement_ids`, and `shiploop-state` fence parsing in `shiploop_store.py` / `shiploop_protocol.py`.
- The model was looking for which keys are required or allowed, whether an expectation check may use `!`, the headline limit, and how the inbox fence is parsed.
- Quote: "The message is in the packet's checked-by text." (line 8367, 22:14:29). The model grepped scripts for the refusal sentences that the packet's **"Checked by"** paragraph lists.
- **Should have said it:** the step-plan and test-spec packets.
  - **Missing:** a complete key schema with types, allowed and optional keys, `headline` ≤ 100, and that `check` must be one line.
  - **Missing:** a pointer to the item's prior accepted result as a worked example.
  - **Missing:** one sentence: "do not read scripts/; run `complete --check-only` on a draft, and its refusal names the fix".
- No `--check-only` call in this run was refused for its content. Of 21 calls, the only failure was the missing-inbox error at the test stage. So the reading was pre-emptive and avoidable.

**B. Test-loop judging: 36 calls (step-plan W1 16, W2 20)**

- Symbols searched in `shiploop_test_loop.py` and `shiploop_test_counts.py`: base-run semantics ("New test IDs must not pass on the base branch"), `BASE_ACCEPT`, `no-tests`, `def outcomes`, `RUNNERS`, whole-word ID matching, and focused/regression folding.
- What the model was solving: the TC-7 title exists in both the W1 rules test and the planned W2 HTTP test. Thought: "Listing TC-7 in focused IDs would fail the base run because rules TC-7 passes" (line 20083).
- **Should have said it:** step-plan duty 5 (`test_commands`). It mentions only "A listed ID counts only as its own word". It does not say that:
  - the test stage copies new test files onto the base tree and requires focused IDs to fail there;
  - an ID that is already passing from an earlier item collides;
  - identical focused and regression commands fold.

**C. Improve and until-loop: 37 calls (`improve/SKILL.md` ×11, `references/shiploop-route.md` ×16 — 47 KB, `until_loop_ephemeral.py` `required_trivial`/`trivial_streak`/`exit_assessment` ×8)**

- The Improve packet is 1.5 KB and only points to the skill. The handoff says "Open ROUTE once per context and after a reset". With 10 compactions, that meant about one re-read per Improve stage.
- The model searched the until-loop runtime to learn the stop rule and the done-report fields.
- **Should have said it:** the Improve packet or handoff, in three lines: the stop rule (two consecutive trivial passes; one if the first pass leaves the tree unchanged) and the done-report JSON keys.

**D. Assumptions: 18 calls**

- Symbols searched: `canonical`, `allowed_consumers`, `disposition`, and "consumer: W2".
- The step-plan packet already said "open items for W2: none open", but duty 6 says "An open plan assumption this item consumes becomes an expectation". The model verified the "none" in source.
- **Should have said it:** the packet, by printing "open plan assumptions consumed by this item: none (checked by ShipLoop)" next to duty 6.

**E. Skills decision and stage table: 8 calls (carry-forward, test-spec W2, current implement)**

- Symbols searched: `_SKILL_DECISIONS`, `OUTER`, `stage_spec` stage names, and "skill call recorded".
- The model was looking for the shape the carry-forward skills decision needs, and whether a Skill call is enforced on Grok (`skill-calls.jsonl` says "not enforced" on non-Claude hosts).
- **Should have said it:** the carry-forward packet; and the Improve packet should state that skill-call recording is not enforced on this host.

**F. ShipLoop SKILL.md re-reads: 8 calls, each right after a compaction or a new session**

### S4. Context compaction: 10 compactions, 14.7 min of waiting plus about 4.4 min of re-orientation

**Evidence**

- `auto_compact_started` (at 80 %) and `auto_compact_completed` pairs at 21:41, 22:00, 22:17, 22:32, 22:45, 23:00, 23:13, 23:40 (3.1 min), 23:56 and 00:11. That is one about every 15 min.
- Each was followed by `shiploop next` and, usually, by re-reading SKILL.md or the Improve route (1–11 calls, 0.2–0.8 min).
- The compaction at 23:00:35 led to the first CLI failure (section 4).

**Root cause**

- Packets are printed whole and are 28–44 KB each from step-plan onwards (`RUN/packets`; W2 implement 44.6 KB). Each repeats knowledge-file contents, references and narrative.
- On top of that come the 47 KB Improve route and source chunks of `shiploop_navigator.py` (491 KB file, read in 40–250-line slices 36 times).
- Grok's window fills at the 80 % threshold in about 15 min.

### S5. Restarts: about 20 min (harness kill 12, refusal #4 plus compaction 6.3, other refusals about 1.4)

Details are in section 4. The 2 h harness kill was the single costliest event: it lost the in-progress W2 step-plan context mid-draft.

### Smaller sinks

- **Test-spec drafting, 15.5 min (W1 6.2, W2 9.3).** The test-spec stage re-specifies oracles already fixed by test-strategy and its 7-pass Improve. The W2 test-spec result is 16.7 KB for 8 cases. It made 44 source reads (cluster A/D).
- **Carry-forward, 5.4 min.** It made 14 source reads for the skills-decision shape (cluster E) and a skill trial note for "Skill decision none".
- **Shell refusals and CLI failures.** These were small (section 4).

## 3. What the Improve passes changed: material or over-specification?

The classification asks whether a normal Battleship build would have shipped a wrong product or a failing test without the change.

| review | pass | change (commit) | verdict |
|---|---|---|---|
| spec | 1 | R-3 must call /api/new and /api/fire and show "Fleet sunk"; R-6 names the destroyer sequence (5289f30) | **Partly material.** It ties R-6 to a behavioural test. "Fleet sunk" text is invented UI copy (over-spec). |
| test-strategy | 1 | HTTP tests use exported `start(0)`, not PORT=0, which R-2 rejects. The TC-1 pattern is anchored so it does not match TC-10–12. Replay inputs added for 13 cases (8612c28) | **Material** (port fixture conflict and pattern collision). Replay inputs for every case are over-spec for this size. |
| test-strategy | 2 | TC-6 no longer reads hidden ships. TC-3 counts 100 grid buttons plus a separate control. TC-7 is split into in-process and HTTP. `env -u PORT`; ship shape `{name, cells}` (6273872) | **Material:** TC-6 and TC-3 contradicted the spec. The ship shape is design leaking into the test strategy. |
| test-strategy | 3 | `createGame` returns `{game, ships}` so TC-8 can check five runs (3b38eab) | **Over-spec.** It shapes the API for the test. A union-of-cells check plus length counts suffices for a toy fleet. |
| test-strategy | 4 | TC-2 checks that a game id dies with the process. The TC-9 cell list. A log-privacy regex for `[integer, integer]` and ship names (8b87338) | **Over-spec.** None of these is in the request. |
| test-strategy | 5 | TC-1 requires `server.js` to import `./game.js` with no second copy (82b4da3) | **Marginal.** It enforces the request's "rules in a module the server uses". One grep would do. |
| plan | 1 | Tests require `../game.js` rather than `./game.js` from test/ (59cb150). W1's in-process TC-7 must not import server.js | **Material but cheap.** A wrong require path fails loudly on the first `node --test`, so implement would have found it in seconds. |
| plan | 2 | The citation path of the probe file; the TC-7 split wording (7bbc8cc) | **Polish.** |
| step-plan W1 | 1, 3 | Throwaway step checks tightened: two cruisers, the `Contract:` substring, input order | **Over-spec.** These are scripts that die at the test stage. |
| test-spec W1 | 1, 2 | TC-8 rejects a sixth ship or a gapped run. TC-10 compares ships one by one | **Over-spec** for this request. |
| step-plan W2 | 1 | S4 requires an `id="new-game"` button with no `data-row` | **Over-spec**, on a throwaway check. |
| test-spec W2 | 1 | TC-7 lists the exact bad bodies. TC-2's stopped-id 400 must be JSON | **Minor.** |
| implement W1 S1 | 1 | A repeated shot returned the *first* shot's gameOver. Fixed to return the current fleet-sunk state (9cb3f03) | **Material, the most valuable catch of the run.** The case's fourth E2E check fires again after game over and requires `gameOver` true. |
| implement W1 S2–S4 | 1 each | No change. One trivial pass each (49 / 63 / 135 s) | Cheap; the one-pass exit worked. |
| implement W2 S1 (current) | 1 | Dropped an eight-seed retry fallback that swallowed `createGame`'s error (66f9f62) | **Small but real** code-quality fix. |

**Net.** Of 36 passes, 4 made material corrections. Three of the four would have surfaced quickly at implement or test: the port fixture, the require path and the TC-6 hidden-ship read. The one catch that protected the delivered result came from **implement** Improve, not planning Improve.

- About 75 % of planning-Improve edits added precision that this request did not ask for: oracles, extra cases, privacy regexes, and API shape chosen for tests.
- That added precision then *increased* downstream cost. The test-spec and step-plan checks had to honour it. For example, the 7.4 KB S4 check enforces the button rules from test-strategy pass 2.

## 4. Restarts and refusals

Sessions are from `sessions.jsonl`. A refused command ends the headless Grok turn: its update reads "User cancelled the execution for tool `run_terminal_command`", and the session exits with rc 0. The harness `resume-loop` then continues the same host session.

| # | ended (UTC) | trigger | events line | refused command (head) | next session | re-orientation before productive work | minutes lost |
|---|---|---|---|---|---|---|---|
| 1 | 21:25:11 | refusal | 85 | `SKILL_ROOT="…/shiploop"` `CLI=…` `python3 "$CLI" workspace start --repo … --prompt='…'`. An identical `SKILL_ROOT=` prefix with `--help` was allowed at line 39. | continued | 2 source reads, 1 shell. Workspace start re-ran at 21:25:20. | about 0.3 |
| 2 | 21:28:50 | refusal | 814 | `cd …/run/scratch` then `node --input-type=module << 'EOF' > probe-http.txt` | continued | Re-ran as `node …/probe-http.mjs > …` at 21:29:25. | about 0.6 |
| 3 | 23:23:45 | **harness timeout** (rc −9). The `--timeout 7200` cap of the first attempt fell mid W2 step-plan. | **fresh** (`resume-run`, no host session) | 34 source reads, 9 run reads, 5 knowledge reads, 5 product reads. The model re-derived the gate and base-run semantics that session 3 had worked out at 23:19–23:20. First write at 23:36:02, 11.9 min after start. The 4.7 min of draft checks from 23:18:59 were redone. | about 12 |
| 4 | 23:37:13 | refusal | 24310 | `cd …/w2-plan && rm -rf probe && mkdir probe && cp …/game.js probe/ && cp stub…` | continued | `next` and until-loop once, then reruns at 23:37:42. | about 0.5 |
| 5 | 23:40:50 | refusal | 24878 | `BASE="…/w2-plan"` `cd "$BASE/probe"` `python3 - << 'PY' …subprocess…` | continued | **auto-compaction 23:40:56–23:44:00 (3.1 min)**, then 21 source reads (SKILL.md, `_normalise_steps`, test_loop base logic, `_SEPARATORS`, the store fence) until the prove run at 23:47:11 | about 6.3 |

**Refusal pattern.** All four refused commands combine a variable assignment or `cd` with a write, a delete or a heredoc subprocess. Similar `cd … && node --test > file` commands were allowed, so the auto-mode classifier is inconsistent. Every refused command was a **scratch probe or helper**, not a ShipLoop call.

- **Packet side.** The packet RULES restrict only ShipLoop commands ("no pipe, redirect, \";\" or shell variable"). Nothing tells the model to keep scratch work as one plain command per call, or to write a script file and run it.
- **Harness side.** Each refusal costs a session exit, and with a near-full context a resume can coincide with a compaction (#5).

**The two ShipLoop CLI failures were benign.**

- **"This review loop has already ended."** `improve-pass` at 23:01:54 (stage 12, implement S3) came right after the 23:00:35 compaction. The model ran `next`, saw Improve, and ran `improve-pass`. The error told it to complete, and it did 2 s later. About 0.1 min lost.
- **"no result file at RUN/inbox/nav-469a….md".** `complete --check-only` at 23:09:09 (test stage) ran before the inbox was written. The model wrote it and re-ran at 23:09:20. About 0.2 min lost.
- **Root cause.** The test packet's order lets the model call check-only before writing the result. The CLI message is good; no fix is needed beyond the wording.

**Total restart and refusal loss: about 20 min.** The harness kill cost 12 of those minutes.

## 5. Fixes

The minute estimates are for this run, and they overlap: do not add S1 and S2 savings blindly.

| # | fix | type | where | est. minutes saved here |
|---|---|---|---|---|
| F1 | Run Grok timing cases with `--planning-review none`, as the comparable r3/v1230 runs did. Keep implement Improve, which caught the only delivery-relevant defect. | **quick** (harness flag) | `test/shiploop_e2e/run.py --planning-review none` | **about 55** (58.6 of planning-choice Improve, minus about 3–5 to discover the port and require-path issues at implement or test) |
| F2 | Use the default `--timeout 10800`, not 7200, for Grok runs. Better still: make `--resume-run` continue the last host session (`resumed_session`) instead of starting fresh. | **quick** (flag); session continuity is a harness change | `run.py` resume path | about 12 |
| F3 | Planning Improve stop rule: for planning documents and inner planning results, **one** confirming trivial pass after a change. Count an edit to RUN/inbox only (tree unchanged) as trivial unless it changes a criterion's meaning. | **engine** | `required_trivial_reviews=2` in `shiploop_navigator.py`; until-loop contract | about 7 with reviews on (seven second-trivial passes of 33–65 s plus overhead) |
| F4 | Add a materiality bar to the planning Improve focus: "Material = a later stage would build, test or deliver the wrong thing. More exact oracles, extra cases, log regexes, or API shape chosen for a test are polish: classify trivial and do not edit." | **prompt** | Improve handoff "What this review looks for" (`shiploop_prompts.py` planning focus) | about 10–12 (test-strategy 5→2 non-trivial passes; plan 2→1) |
| F5 | Step `check`: permit a short check of an in-process export, and let HTTP and multi-process behaviour be proven by the test stage. Make `check_na: proven at test stage by <TC ids>` acceptable for a step whose behaviour needs a spawned server. Cap a check at one short line (for example 400 chars) and say so. Do not have Improve review step checks as product. | **engine** (gate) + **prompt** (duty 4) | step-plan duty 4; `check_step_plan` | about 18–20 (W2 scratch 11.2 + W1 5.3 + the step-check tightening passes) |
| F6 | Make the step-plan and test-spec packets self-sufficient about the gate. | **prompt** (+ small engine for the schema command) | step-plan and test-spec packets; new CLI `schema` | about 11 (cluster A) |
| F7 | Add a five-line "How the test stage will judge `test_commands`" block. | **prompt** | step-plan duty 5 | about 5 (cluster B) |
| F8 | Improve handoff: state the stop rule and done-report keys inline. Say "do not read until_loop scripts". Re-open ROUTE only for recovery or a stopped child, not after every compaction. Say whether skill-call recording is enforced on this host. | **prompt** | Improve packet and handoff | about 4 (cluster C plus a share of E) |
| F9 | Print packets compactly (heads and pointers; knowledge-file contents only on demand). Stop printing knowledge-file outlines and the reference list in every inner packet. | **engine** (renderer) | `shiploop_prompts.py` packet renderer | about 8–10 (halving 10 compactions × about 1.9 min) |
| F10 | A RULES line for scratch work: "Scratch probes: write a script file in RUN/scratch with a file tool, then run it with one plain command. No `cd …&&`, variable assignments, `rm -rf` or heredocs; headless hosts refuse them and end the session." | **prompt** | packet RULES block | about 7 (refusals 1, 2, 4 and 5, including the compaction that followed #5) |
| F11 | The test packet order: write the inbox result before `--check-only` (already in the error message). | **prompt** (one word) | test packet Result line | under 0.5 |
| F12 | Carry-forward packet: give the skills-decision record shape inline. | **prompt** | carry-forward packet | about 1–2 |

F6 changes the step-plan and test-spec packets in three ways:

- (a) Replace the long "Checked by" refusal prose with "Run `complete --check-only` on a draft as early as you like. Its refusal names the fix. Do not read scripts/."
- (b) Add an exact key schema (required, optional, types, headline ≤ 100, one-line `check`), or a `shiploop schema <stage>` command that prints it.
- (c) Name the item's last accepted step-plan result as a worked example.

F7 tells the model that the test stage:

- copies new test files onto the base tree;
- requires every focused ID to be red there and green on the candidate;
- matches IDs as whole words in titles;
- treats a title already passing from an earlier item as a collision (use `TC-7 HTTP`);
- folds identical focused and regression commands.

**Expected effect.** With F1 + F2 + F10 alone (two harness flags and one RULES line), this run's 174 min to W2 implement drops by about 75 min, to about 100 min. Adding the F5–F9 prompt and engine work would bring inner planning back towards the earlier 2–5 min per item. It would also cut compactions roughly in half.
