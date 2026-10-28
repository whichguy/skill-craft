# ShipLoop owed outcome: journal and design

Started 2026-10-27. Living record for one question and the design it led to. Edit in place; mark superseded claims
with the date and the reason rather than deleting them.

## The question

The owner's worry: a packet's work gets executed and the model never reports back, so the run stops at an edge
nobody took. In the owner's words: "the context only matters. It doesn't need to know what step or stage it's in
... if it didn't call `done` with the appropriate condition, then I think that would be a problem. In reality, it's
the edge state in a graph. It's like path A, B, or C: `done` would sort of default to A, which would mean next step."

## Experiments

Each line: question, conditions, result, evidence. E3-E5 first ran at skill-craft `b0d29284` and were rerun at
`821db5c0` just before the journal was committed, with the same results; the `.out` files hold the rerun. The
ShipLoop scripts, the Until Loop runtime and the keepalive fixtures are unchanged from `0ed6ce38`, where the session
began, through `c59c4809`.

| ID | Question | Conditions | Result | Status |
|---|---|---|---|---|
| E1 | How often does the stop hook act on real runs? | `~/.local/state/shiploop/keepalive/decisions.log` on this machine, 2026-09-25 to 2026-10-27, 12,287 decisions | 31 continue, 2 "no progress", about 11,950 "no run bound" (sessions that were not running ShipLoop) | firm counts; the log stays outside the repo |
| E2 | How do recorded runs move between steps? | `docs/shiploop-run-trace-evidence/2026-10-25-hello-claude-1.12.0` and `-1.13.1`, Claude, tiny "hello" case | 5 of 97 `complete` calls refused, each fixed and resubmitted; gap between commands median 11-13 s, max 73 s; one hook event per run, `allow: run is done` | firm; small case, not representative |
| E3 | Where does a packet tell the model to call back? | [packet_position.py](shiploop-owed-outcome-evidence/packet_position.py), `graph-dry-run --scenario delivery --format markdown`, W1 verify packet | 18,317 characters; callback at 5%; 7 mentions, all at or before 57%; nothing after the RULES block repeats it ([output](shiploop-owed-outcome-evidence/packet_position.out)) | firm for the dry-run rendering |
| E4 | Does a ShipLoop command between two stops reset the hook's memory? | [rebind_repro.py](shiploop-owed-outcome-evidence/rebind_repro.py), real run in a temp dir, recorded Claude payloads, no live host | Yes: `shiploop next` between stops empties the binding's `last_block_progress` and `turn_blocks`, so the next stop blocks again; a loop-runtime command does not, so the next stop is released ([output](shiploop-owed-outcome-evidence/rebind_repro.out)) | firm |
| E5 | Can the Until Loop runtime tell finished work from work not started? | [loop_next_probe.py](shiploop-owed-outcome-evidence/loop_next_probe.py), real `start --receipt`, work done without `done` | No: `next_argv` returns a byte-identical instruction; it is execute-then-report with a "recheck artifacts" guard ([output](shiploop-owed-outcome-evidence/loop_next_probe.out)) | firm |

## Findings

- **F1, firm.** The script catches a skipped report it can see. `complete` checks the Until Loop receipt before
  every other gate (`shiploop_loops.check_terminal`, called from `shiploop_navigator.dispatch`): a missing receipt
  ("has not run ... Start it with"), an active one ("still active: run the receipt's next_argv") and a missing
  result file ("no result file at ...") are each refused with the fix. The 1.12.0 trace holds a "still active"
  refusal.
- **F2, firm.** A callback that never arrives is invisible to the script. Only the host stop hook
  (`shiploop_keepalive.stop`) or `scripts/shiploop-drive` can notice it, and only at a turn end.
- **F3, firm.** The stop hook does not know what is owed. `_continue_reason` sends one sentence, "run `shiploop
  next`", so the iteration's report prompt arrives three commands later (`next`, the receipt's `next_argv`, the
  runtime's instruction).
- **F4, firm.** Stage Until Loop iterations are not progress. `hook_status` progress is
  `revision.callback_attempts.improve_pass`; only the Improve child's receipt is read (`_improve_pass`).
- **F5, firm (E4).** `observe` rebuilds the binding on every driving command and keeps only the unused
  `last_block_rev`, so `last_block_progress` and `turn_blocks` are lost. The "no progress" release therefore fires
  only when no ShipLoop command ran between two stops, and Grok's per-turn continuation count restarts after each
  `next`, so its warning near the cap seldom shows.
  - *Superseded 2026-10-27:* the earlier claim in this session that F4 releases a productive loop after one block
    assumed the model did not run `shiploop next` after the block. With today's reason text it normally does, which
    resets the memory. F4 bites only when the model goes straight to the loop runtime.
- **F6, firm (E5).** The runtime has no "work done, report pending" state, so a recovery prompt cannot be
  report-only; the model must recheck and decide from its context.
- **F7, firm for the rendering, effect unmeasured (E3).** The packet's last 43% is reference material with no
  action line. Whether that makes a model stop without reporting is a hypothesis.

## Design: owed outcome

### The model

Each action is a node. Its outgoing edges are its outcomes; `done` is the default edge (A, the next step),
`blocked` (B) waits for a person, `send-back` (C) reruns an earlier stage, `add-work` adds work items. The model's
whole job at a node is to do the work from its context and name one edge with its evidence, by running a command.
The script owns everything else.

Two properties, kept apart:

- **Safety: is the edge the model named allowed?** Each edge has a script-checked guard. `done` needs a satisfied
  loop receipt and passing gates; `blocked` needs `awaiting`; `send-back` needs a stopped loop or an opened route.
  This exists today (F1).
- **Liveness: was any edge named at all?** Nothing the model does tells the script it skipped the edge, so the only
  signal is silence at a turn end. This is the owner's worry, and only the stop hook or the driver can see it (F2).

### Owed outcome

From the moment a packet prints until its outcome is accepted, exactly one report is owed. It is the innermost
pending one, found from files alone:

1. an active Until Loop receipt for the current action (the Improve child's, or the stage loop's) owes an
   iteration report: its `done_argv` with the five fields;
2. otherwise a current action not yet accepted owes its outcome: the result file and the packet's callback;
3. otherwise nothing is owed (paused, blocked on a person, halted, done).

The hook needs no stage, step or graph knowledge: it asks "is something owed?" and relays the one prompt the
navigator renders for it. The prompt states the fact, gives the exact command and lists the edges with `done`
first, for example:

> You stopped without reporting the outcome of the step you were doing. If its work is finished, report `done`;
> if a person must act, `blocked`; if an earlier record is wrong, `send-back`. Write the result to <path> and run:
> <callback>. If you lost context, run <next>.

For an iteration: "Iteration 3 of this step's loop is unreported. Exit: <exit words>. Recheck the artifacts and
report with <done_argv>; if any work is incomplete, classify it `unresolved` and name the gap."

### What it does not do

- **No default edge taken by the script.** `done` needs evidence the model writes, and its gates rerun tests that
  take minutes, while hooks time out at 10-30 s (`host-hooks.json`). A hook running `complete` would also run
  commands the host never sees. "Default A" stays an ordering in the prompt.
- **No reading of the model's prose.** `last_assistant_message` reaches the hook on Claude, Codex and Grok, not
  Cursor; it is a claim, not evidence, and the edge must still come as a command.
- **No change for delegated runs.** Under `delegation: ask-agent` a worker owes the iteration report; the parent
  keeps today's text.

### Release valve

Ask twice. The memory is the outcome activity since the last ask: the revision, callback attempts and the
innermost receipt's iteration number. A `shiploop next` is not activity, so it no longer resets the count (F5).
A model that keeps reporting is never released (no caps); one that answers two asks with no report is released,
with a notice and a trace event.

## Options

| Option | For | Against |
|---|---|---|
| O1 Leave as is | Works when the model obeys "run next"; no change | Liveness depends on two indirect hops; F4 and F5 make the release inconsistent |
| O2a Static edge question in the stop text, plus F4 and F5 fixes | One sentence and two small code fixes; no new state read beyond the receipt's counter | The model must find the callback in its context; after compaction it may not |
| O2b Owed-outcome prompt rendered by the navigator | Exact command and edges in the ask; works after compaction; one renderer, unit-testable | One new `hook-status` field and a renderer; more text per ask |
| O3 Closing action line at the packet's end | Cheap; tests F7 directly | Hypothesis only; adds a line to every packet |
| O4 Script takes `done` by default | No model action needed | Rejected: evidence, hook timeouts, hidden commands |
| O5 Collapse the loop's final report and `complete` into one edge | One report per step | Contracts carry no install path, and results have stage-specific fields; parked |

## Plan, if approved

1. **Fix the memory and the counter (F4, F5).** `observe` keeps `last_block_progress` and `turn_blocks` for the
   same run and drops `last_block_rev`; `hook_status` adds the innermost receipt's `progress.action_number`.
   Tests: E4's three sequences become keepalive tests, plus one where a reported iteration keeps the run blocked.
2. **Ask for the owed outcome (O2a first).** Replace `_continue_reason`'s sentence with the edge question; keep the
   lost-context fallback. Prompt commit with a verbose message.
3. **Escalate to O2b only if step 2's measurement shows models failing to find the callback.**
4. **Trace it.** Each hook event records what was owed; `shiploop trace` shows it.
5. **Measure.** Per run: stops with something owed, the share followed by a report before the next stop, releases,
   and the commands or edits between the ask and the report (a redo shows up there). A hermetic probe forces a stop
   at each owed state; E2E runs give the natural rate.

Process: change note under `changes/shiploop/`, tests in `test/shiploop-keepalive.test.py`, the quick group with
`--changed-from`, release through `scripts/release.py` on the owner's go.

## Open decisions

- D1. Accept the split: the script guards edges, the hook only notices a missing one, and no edge is taken by
  default.
- D2. O2a first, or straight to O2b.
- D3. The release valve as "two asks with no report", with `shiploop next` no longer resetting it.
- D4. Run O3 as an experiment arm.
- D5. Park O5.

## Design v3: the step is an Until Loop (draft, 2026-10-27)

The owner, after the conflicts below: "I think I may have kind of defined the Until Loop itself. If true, then I
should just let the Until Loop handle this, and the step just calls the Until Loop with the exit conditions and the
desired prompt of what to execute on." This matches the owner's 2026-09-24 "loop vehicle" idea: work = the step,
exit = all criteria confirmed, a proven-unachievable exit routes back to planning.

The owner's three edges are the loop's own states: `active` is retry (the next iteration under the same contract),
`complete` is exit, `stopped` (blocked) is intervene or replan. ShipLoop already starts one loop per inner stage
with the stage's prompt as Work and its done-when as Exit. Three gaps remain:

1. **The checks are not in the contract (F8).** The loop's exit is self-reported, and ShipLoop re-checks with its
   gates only after the loop ends; step-plan, test-spec and test tell the model to run `complete --check-only`
   inside the loop, but nothing enforces it. Fix: make `shiploop check` the contract's exit check, so the loop ends
   only when the check says yes on the current files, and a failing gate keeps the loop going instead of refusing
   after it ends. The check runs in the host shell, where hooks see it. Constraint: contracts name no install path
   (`shiploop_loops` module docstring), so a check that calls ShipLoop needs a stable per-run path, for example a
   small launcher written into the run directory. Not yet designed or verified.
2. **The loop does not hand back by itself.** By the card's rule the step's callback stays a second command after
   the loop ends. Options: a small runtime addition that prints a return command the parent passes at `start`
   (outside the contract), or keep the second command and rely on the stop hook.
3. **The stop hook does not know which report is owed** (F3). Fix as in the owed-outcome draft: the loop's report
   while its receipt is active, the step's callback once it is terminal; plus the memory fix (F5) and the
   background-task fix (F10).

**Two layers (owner's framing, 2026-10-27; firm, read from `shiploop_navigator._apply_result`).**

- Inside a step, the Until Loop has one loop-back edge (`active`) and two exits (`complete`, `stopped`); the runtime
  picks among them from the model's report and the checks.
- Between steps, the model names one label from the stage's allowed set (`shiploop_stage_spec`: for example
  implement allows done, blocked, send-back), and the script turns the label plus run state into exactly one next
  node: `send-back` to `send_back_target` (step-plan, or the outer plan writer); `add-work` to new items, then the
  inner loop; `done` at implement to the next step while steps remain; `done` at carry-forward to the next item or,
  with none left, the next outer stage; Improve inserted by its rule; stages that do not apply skipped by
  `_record_not_applicable`. One accepted result takes one edge; parallel chains live inside one implement action.
- So the model judges what happened, never where to go; the loop's exit already fixes most of the label
  (`complete` allows only done), which is what S2 uses.

What stays the step's job: the graph and the next node, the contract's content, the result fields later stages
read (steps, test cases, assumptions), mapping the loop's end to an edge (`complete` to done; `stopped` to blocked
or send-back, the target named in the result), and acceptance side effects (commits, knowledge home, Improve).

Trade-off against v2: v3 keeps the owner's decisions and one loop engine and resolves C1-C6, since nothing replaces
the loop. It simplifies the concept more than the code: little is deleted, and the second command at a step's end
remains unless the runtime gains a return command.

### Simplifications in the current implementation (draft, 2026-10-27)

Measured with `graph-dry-run --scenario delivery --format markdown` (the four W1 inner packets) and read from the
code at `b0d29284`.

- **F12, firm.** Every inner packet measured is over the 16,000-character whole-print limit, so each prints as a
  head: implement 20,078, verify 18,321, test 18,827, step-plan 22,330 characters. Each names the receipt 8-10
  times, the callback 5-7 times, `check-only` 2-4 times and the recovery `next` command twice.
- **F13, firm.** Three of `check_terminal`'s four ways past the receipt check exist because ShipLoop's gates run
  after the loop has ended: `open_send_back` ("the step's Until Loop has completed by the time a done is submitted,
  and a completed loop supports only done"), `_verify_refused` ("verify's review loop has already ended") and
  `_remedy_open` (a test run that could not reach a verdict). The fourth, `blocked` before the loop started, is a
  real case.
- **F14, firm.** The last iteration count in ShipLoop is `GENUINE_FIX_ATTEMPTS = 7` (`shiploop_stage_spec`, printed
  by `shiploop_prompts`); every other limit is a size bound in bytes or characters.

Today a model runs this at an inner stage: start the loop; per iteration, work, sometimes `complete --check-only`,
then the loop's `done`; write the result and choose its outcome; `complete`; and, on a gate refusal, fix with the
loop already ended and run `complete` again. With S1 and S2 below it becomes: start the loop; per iteration, work,
`shiploop check` (through the loop's check script), the loop's `done`; the loop ends when the check says yes; then
`complete`.

| # | Change | Removes | Keeps | Size and risk |
|---|---|---|---|---|
| S1 (revised below) | `shiploop check` becomes the contract's exit check (v3 gap 1) | The three receipt exemptions (F13), the result line's "if that refuses for the loop, start again", most of the "Checked by" gate prose, gate fixes made after the loop ended | Every gate, now run in the host shell where hooks see it; check-only's reuse of test runs | Medium; needs the stable per-run launcher so contracts name no install path |
| S2 | `complete` reads the outcome from the loop's end: `complete` is done, `stopped` needs only a target (blocked or send-back) | The model's outcome choice where only one answer is valid, and the refusals for a mismatch | The four outcomes and their routes | Small |
| S3 | One owed report for the stop hook (F3), memory kept across `next` (F5), background tasks bounded (F10), the unused `last_block_rev` dropped | The generic "run next" detour and two inconsistent release paths | The release valve, owner claims, host adapters | Small |
| S4 | Inner packets end on the action and say each mechanic once, the loop's own instructions carrying the receipt details | Repeated receipt, callback and recovery text (F12) | Every rule needed to run the step, once per packet (owner, 2026-09-26) | Small to medium; measured by packet size and the E3 positions |
| S5 (revised below) | `GENUINE_FIX_ATTEMPTS` becomes a criterion: the same recorded checks fail on an unchanged tree in consecutive iterations, so the loop stops blocked for a replan; `shiploop-drive` gets a wall-clock ceiling in place of `--max-sessions` (F11) | The last iteration count (F14) and the driver's session count | Unbounded loops that are making progress | Small once S1 records check results |
| S6 | Separate decision: the Improve stage as an ordinary step whose loop runs the Improve skill | Most of the Improve plumbing (F9: five verbs, about 1,100 lines plus 121 navigator lines) | Improve's reviews and records | Large; not part of this change |

Kept as they are: `delegation` inline or ask-agent, the run options and chains, which are owner-chosen alternatives,
not versions.

#### Revised after Astra's v3 review (2026-10-27)

Three facts, checked in the code, change S1 and S5:

- **F15, firm.** Today's check-only does not give the same answer as `complete`. `test_a_check_only_run_below_the_floor_
  the_base_run_sets_at_complete_is_run_again_not_taken` (`test/shiploop-test-loop.test.py`) pins a check-only run of
  2 tests passing, then `complete` refusing because its base run counts 3. `base_check` always runs the base
  (`_base_run`); check-only returns before anything is applied (`shiploop_navigator.dispatch`).
- **F16, firm.** `check_loop_packet` compares no `exit_checks`, results or repairs (0 references), so a receipt
  from a weakened check list would pass today.
- **F17, firm.** `GENUINE_FIX_ATTEMPTS` appears only in prompt text (`shiploop_loops.REPEAT`, `shiploop_prompts`);
  no code enforces it. `awaiting` has three kinds, `answer`, `present` and `service`, so "intervene" also covers an
  outside service.

Revised order. Each phase leaves a working ShipLoop, and the one-supported-version rule applies at release:

| Phase | Change | Why first | Removes |
|---|---|---|---|
| A | Stop hook (S3): one owed-report text, memory kept across `next`, no blanket background-task bypass, stage-loop iterations counted while stage loops exist; `shiploop-drive` on a wall-clock ceiling | Small, independent, fixes the owner's worry now | The "run next" detour, two release paths, the session count |
| A | S5 as wording only: the "7 genuine fix attempts" sentence becomes a criterion (the same check still fails the same way after a fix, with no new evidence: report send-back); no forced routing, since a fingerprinted stuck rule is unsound as a gate (oscillation, paraphrase, unrelated edits) | Prompt-only today (F17) | The last count |
| B | S1a: `shiploop check` becomes its own verb, replacing `complete --check-only`. It and `complete` run the same code and record one answer, yes or no with reasons, tied to the action, contract, result draft, candidate tree, base run and floors; `complete` accepts a matching yes instead of re-running the gates, and asks again if the files changed since | Removes F15, and is a simplification on its own | The flag, the divergence between the check and `complete`, and the reuse special cases |
| C | S1b: `shiploop check` becomes the loop's exit check, called through `<run>/shiploop`, a symlink to the selected entrypoint (the entrypoint resolves its real path, so imports still work); the loop ends when the check says yes; `check_loop_packet` confirms the contract's exit check and its passing result (F16) | Only safe after B | The three receipt exemptions (F13), the check-only reminders, repeated report-field text and restart-after-refusal prose (S4), post-loop gate fixes |
| C | S2: `complete` reads the outcome from the loop's end; `stopped` names a target (blocked, with any `awaiting` kind, or send-back) | Needs C's binding | The outcome choice where only one answer is valid |
| later | S6: the Improve stage; the hand-back return-command option | Separate decisions | — |

**Plain names (owner, 2026-10-27: "check only" and "the verdict passes" were confusing).** The design has one
question, "would ShipLoop accept this step now?", answered yes, or no with reasons. Adopted by the owner on
2026-10-27 for the whole design and phase B ("use `shiploop check` for the question and 'the check says yes' for
the exit rule"):

| Today | Plain meaning | Adopted |
|---|---|---|
| `complete --check-only` | Ask the question; change nothing | `shiploop check` (its own verb) |
| "the verdict passes" | The check said yes | "the check says yes" |
| exit `satisfied` | The model says it is finished | Allowed only after the check said yes on the current files |
| `complete` | Ask, and on yes accept the step and print the next | Unchanged: accepts the last yes, asking again only if the files changed since |

The loop's exit rule then fits in one line: the loop ends when `shiploop check` says yes, or when the model reports
the step blocked. Today the model decides when it is finished and check-only is advice (its pass message ends "The
action is not completed").

Kept deliberately: the step's per-edit checks during implement (`shiploop_prompts._IMPLEMENT_CHECK_INLINE`),
which an exit check alone would not replace, and the second command at a step's end.

## Design v2: one `done`, three edges (draft, 2026-10-27)

*Superseded 2026-10-27 by design v3: the owner judged the three edges to be the Until Loop itself, so ShipLoop
should not run its own step loop. Kept for its findings (F8, F9) and the strictness table.*

The owner's clarification, verbatim: "we could call 'done' with the edge conditions that might have different
vectors of where 'done' should head ... 'We can fully exit.' 'Any human or supervisor intervention.' 'Didn't meet
the conditions and replanning required,' in which it would basically say, 'Provide a plan to resolve ... to try to
meet the exit conditions, and then execute on it.' It's a bit of a 'continue iterating' kind of deal, looping back
to the same state itself." Plus: simplify the code a lot without losing key features.

### More findings

- **F8, firm.** ShipLoop's stage loop contracts carry no `exit_checks`
  (`shiploop_loop_contract.contract`: workspace, work, exit_condition, repeat_condition, required_trivial_reviews,
  context), and only `verify` asks for a trivial final pass (`shiploop_loops.TRIVIAL_REVIEWS`, 1 for verify, 0
  elsewhere). The runtime's recorded exit checks, its strongest anti-fabrication feature, are not used by stages.
  What the stage loop adds is: conditions restated each iteration, a script-counted iteration number, a
  self-reported exit, and a terminal receipt that `complete` checks before its own gates.
- **F9, firm.** Size today: ShipLoop's scripts are 46,569 lines; the stage-loop layer is `shiploop_loops.py` (914)
  and `shiploop_loop_contract.py` (43), plus 188 navigator lines that name loops or receipts; the Improve child
  plumbing is `shiploop_standalone_improve.py` (872), `shiploop_improve_changes.py` (217), 121 navigator lines and
  five verbs (`improve-bind`, `-start`, `-commit`, `-pass`, `-reconcile`) of the CLI's 26; 85 test files name loops
  or receipts. The vendored Until Loop runtime is 1,926 lines.
- **Context.** `repeat` was removed as a stage outcome because it "was never used in 1,845 results"
  (`shiploop_stage_spec`, comment above `OUTCOMES`): the stage Until Loop did all the repeating inside a stage.
  v2 moves that repeat up to the step, where it is the most used edge, not a revived dead one.

### The step machine

One command per iteration, `shiploop done --run-dir R --action A`, reads `inbox/<action>.md`, whose `edge` is:

| Edge | The model says | Required fields | The script does |
|---|---|---|---|
| `exit` | every exit condition holds | today's stage result fields | runs the step's guards; all pass: accept, next step; any fails: takes `retry` itself, with the failures as the gap |
| `intervene` | a person must act | `awaiting`, as today | blocks on the person; only their reply resumes |
| `retry` | an exit condition is unmet | `gap` (each unmet condition and what shows it), `plan` (what the next iteration does); optional `target`: `step` (default), `plan` (today's send-back), `work` (today's add-work, outer stages) | counts the iteration, prints the next packet with the gap and the plan by value |

A malformed report stays an input error: refused, nothing counted. The retry packet restates the step's goal and
exit conditions unchanged, then the gap and plan, then "execute the plan, then report `done`".

Stuck rule, replacing the `GENUINE_FIX_ATTEMPTS = 7` count the owner dislikes: two retries in a row with the same
gap and no change to the working tree make the next packet offer only `retry` with target `plan`, or `intervene`.
This is a proposal and needs the owner's decision.

### Strictness kept

The owner's 2026-09-26 decision: Until Loops are the strictness mechanism. Each property and where it goes:

| Property | Today | v2 |
|---|---|---|
| Frozen exit conditions | contract rebuilt from state, compared at `complete` | held in state, restated in every packet |
| Script-counted iterations | runtime `action_number` | iteration counter in state |
| Conditions restated each iteration | runtime instruction | retry packet |
| Exit checked by the script | receipt status, then gates at `complete` | guards on every `exit` claim |
| Recorded model exit checks | runtime feature, unused by stages (F8) | nothing lost; ShipLoop's gates stay |
| Verify's clean final pass | self-reported `trivial` | the final iteration changed no file (Git tree), checked by the script |
| Recovery after lost context | receipt `next_argv` and `handoff` | `next` reprints the iteration packet with the gap and plan |
| No caps | no iteration limit | unchanged; the stuck rule is a repeated state, not a count |

### What collapses, what stays

- Collapses: stage Until Loops (the 957-line layer, the loop block in every inner packet, the receipt check, the
  resume lines, part of the 188 navigator lines and their tests); the two reports at a step's end become one;
  refusal and repeat become one path, so the stop hook's progress is the iteration count and the owed report is
  always `done` for the current action.
- Stays: the graph, the gates, the test loop, lint, chains, the workspace, the Until Loop runtime (Improve and
  `/until-loop` use it) and, unless the owner decides otherwise, the Improve child.
- Optional second phase: the Improve stage as a three-edge step too, which would remove most of the Improve
  plumbing in F9. It touches the Skill-call gate and Improve's own records, so it is a separate decision.

### Risks

- It reverses a recorded owner decision (stage Until Loops) unless the strictness table above is accepted as
  equivalent.
- It is a large change in a 46,569-line system with one supported version: saved runs from before it are refused.
- The model writes a plan at every retry; that is text the Until Loop's `handoff` already asked for, so the cost
  should be similar, but it is unmeasured.

### Phases

0. Now, and kept by v2: stop `observe` wiping the hook's memory (F5) and make the stop text the edge question.
   Skip the stage-loop counter (F4) if v2 is approved, since stage receipts go away.
1. Spec: the report schema, the guard table per stage, the two packet templates, the stuck rule, the verb name,
   the hook text; `graph-dry-run` scenarios for every edge.
2. Build it in the navigator, remove the stage loops, update tests, then an E2E round before the release.
3. Separate decision: the Improve stage as a three-edge step.

### Decisions for the owner

- V1. Accept the three edges, with `send-back` and `add-work` as `retry` targets.
- V2. A failed `exit` claim becomes the script's own `retry` instead of a refusal.
- V3. Accept the strictness table as replacing stage Until Loops.
- V4. The stuck rule in place of the fix-attempt count.
- V5. Rename `complete` to `done`, everywhere in one commit, or keep `complete`.

## Where v2 conflicts with the Until Loop (2026-10-27)

v2 changes no Until Loop code: the runtime stays, Improve and `/until-loop` keep using it. It conflicts with the
Until Loop's rules (cited from its card, `skills/improve/runtime/until-loop/ADAPTER.md`) and with the owner's
decisions about using it.

| # | Until Loop rule or owner decision | v2 as drafted | Kind | Way out |
|---|---|---|---|---|
| C1 | The model reports facts; "neither selects the next state. Do not supply a decision, next action, successor" (card, `done` section) | The model names the edge | Design | Keep the report as facts (exit met or not, can continue or blocked, evidence, plan); the script derives exit, retry or intervene |
| C2 | "Until Loops are the strictness mechanism" (owner, 2026-09-26); every inner stage runs one Until Loop (owner, 2026-10-10; `references/inner-loop.md`) | Inner stages stop running one | Owner decision | Only the owner can reverse it |
| C3 | "a parent must not run a second state machine, synthesize callbacks" (card, last section) | ShipLoop grows its own iteration loop beside the runtime, which Improve still uses | Architecture | Accept two loop engines with one vocabulary, or keep stage loops |
| C4 | `done` means "this action is finished", not success; `trivial` allows trivial changes (card, report fields) | `done` with `exit` means success; verify exits only if no file changed | Words and rule | Name v2's verb differently (for example `report`); decide whether a final verify pass may make trivial edits |
| C5 | Never carry a clean-review streak across changed criteria (card, user corrections) | Conditions live in state and can change on a replan | Rule to add | Reset the iteration count and streak whenever the step's conditions change |
| C6 | Recorded exit checks run in the host shell, so hooks see them (until-loop 0.8.0) | Exit is checked by ShipLoop's in-process gates | Future tension | None today (F8: stages never used them); it closes one route for adopting them later |

What v2 gains that the loop does not give today: one owed report per step, so a missed report is always the same
thing to ask for; and a failed gate becomes the next iteration instead of a refusal. Inferred from
`check_terminal` and the packet's result line, not traced through every gate: when a stage gate refuses after the
loop's receipt is complete, the fix happens with the loop already finished, outside its iteration count.

The alternative that avoids C1-C5: keep the stage Until Loop and read the step's edge from its terminal receipt
(complete is exit, stopped is intervene or replan, active is retry). It keeps the owner's decisions and one loop
engine, but it simplifies little code and still leaves two commands at a step's end, since the card forbids a
parent from synthesizing the loop's callback.

## Review: Astra at max effort on the owed-outcome draft (2026-10-27)

Model `gpt-6-astra`, effort max, through the `ask` agent; question and answer in
[astra-review-1-owed-outcome.md](shiploop-owed-outcome-evidence/astra-review-1-owed-outcome.md). Its code claims
checked here: the background-task bypass, the driver's
session ceiling, the Improve handoff's parent-only completion and the runtime symbols it cites all match the code.
Its claim that Claude's own stop-hook continuation cap resets after tool calls cites Claude's documentation and was
not checked.

- **Agrees:** derive the owed report from state, not from what was printed; no default edge on silence; never read
  the model's prose; the strongest single change is the exact owed instruction in place of "run next".
- **Adds:** an ask-agent parent should be told to collect the worker, not given the worker's callback; "innermost"
  must come from recorded ownership (receipt paths derived from state), not a scan for the newest active receipt; a
  piped or backgrounded callback may already have succeeded, so the recovery prompt says to reread state before
  resubmitting.
- **Disagrees with the draft's release memory:** key it by what is owed (action, receipt, iteration number and
  status), reset it only on an accepted report, and do not let raw callback attempts refill it. A repeated identical
  refusal should use up the asks without clearing what is owed. v2's stuck rule covers the same case.
- **On collapsing the levels (the draft's O5):** keep them separate for the missing-callback fix alone; fusion is
  possible with a ShipLoop-owned command but needs recovery when loop acceptance passes and stage validation fails.
  v2 has no separate loop acceptance, so that case becomes an ordinary retry; Astra has not yet reviewed v2.
- **Measurement:** three paired arms (today, memory fix alone, memory fix plus the targeted prompt); injected stops
  after work before the loop report, after a terminal receipt before `complete`, and after an accepted `complete`
  whose output was lost; also rereads, repeated refusals, compaction, worker collection, waits on a person and
  headless driving. Metrics: recovery rate, false advancement, duplicate work, premature parent submission, false
  stalls, asks per recovery, tokens and latency, with denominators and intervals, plus a long valid run proving the
  asks never act as a cap.

New findings from checking it:

- **F10, firm (code).** A running background task skips the "no progress" release (`_decide`: `... and not
  waiting`), so a session with a long-lived background task (a dev server, a watcher) is blocked at every stop.
  Grok's host cap ends that after 8; on Claude it is untested.
- **F11, firm (code).** `shiploop-drive` stops at `--max-sessions` (`drive` requires at least 1), a session count;
  the owner accepts only dollar or wall-clock ceilings.

## Review: Astra at max effort on v2 and v3 (2026-10-27)

Two runs, `gpt-6-astra`, effort max, no fallback; questions and answers in
[astra-review-2-design-v2.md](shiploop-owed-outcome-evidence/astra-review-2-design-v2.md) and
[astra-review-3-design-v3.md](shiploop-owed-outcome-evidence/astra-review-3-design-v3.md). Checked here: F15,
F16, F17, the entrypoint's real-path resolution and `_IMPLEMENT_CHECK_INLINE`. Not checked: what the runtime's
tree hash excludes.

- **v3, strongest recommendation:** "Adopt v3 around one shared stage evaluator whose verdict binds the action,
  contract, draft, candidate, base and floors. Let Until Loop enforce that verdict and `complete` consume it.
  Establish this equivalence before deleting gates or extending the hand-back API." Adopted as phases B and C.
- **v3, other points:** keep the second command at a step's end for now; a printed return command would not break
  the card's rule but changes its wording; keep the per-edit checks; lint auto-fix belongs in the Work, before the
  final check.
- **v2 (superseded), points that still apply:** a mandatory stuck rule is unsound, pilot it as a warning at most;
  "intervene" must keep service waits; a watcher does not prove progress, so drop the blanket background-task
  bypass; consider counting accepted reports, not raw callback attempts, as progress (a change to the owner's
  2026-10-24 rule, so the owner's call); release one coherent protocol with no dual runtime.

## Change log

- 2026-10-27: created with E1-E5, F1-F7 and the owed-outcome draft. An independent design review by Astra at max
  effort was requested; its result is recorded below when it returns.
- 2026-10-27: design v2 (one `done`, three edges) added after the owner's clarification, with F8, F9 and the
  strictness table. Astra's review was asked about the owed-outcome draft; v2 still needs its own review.
- 2026-10-27: conflicts C1-C6 between v2 and the Until Loop recorded, with the keep-the-loop alternative.
- 2026-10-27: design v3 (the step is an Until Loop, with exit checks in the contract) added; v2 marked superseded.
- 2026-10-27: simplification list S1-S6, two-layer framing, then Astra's v2 and v3 reviews; S1 split into one
  evaluator (B) and exit checks (C), S5 reduced to wording; F12-F17 added.
- 2026-10-27: owner adopted `shiploop check` and "the check says yes"; design sections and phases B and C reworded.
  Findings about today's code keep the current name, `complete --check-only`, until phase B renames it in code,
  references and glossary in one commit.
- 2026-10-28: corrected the experiments' provenance: E3-E5 were rerun at `821db5c0` before the commit, not only run
  at `b0d29284`; four commits from other sessions had landed on main in between, none touching the traced code.
