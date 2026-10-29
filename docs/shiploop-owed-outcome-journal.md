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
| E6 | Where do models dry-run `complete --check-only`, and is a `complete` refused after a passing one? (2026-10-28) | [trace_check_pairs.py](shiploop-owed-outcome-evidence/trace_check_pairs.py) over the run traces of arm A, the owner-note hello run and the six arm B slices | Inner stages: about one dry run per `complete`, and every inner `complete` accepted (arm A 35 of 35). Outer stages: a dry run before each `complete` (arm A 29, hello 17). Refused right after a passing dry run: 5; 4 outer in the full runs, and 1 inner in arm B owed 1 (test-spec, an outcome the stage does not allow: that rule is in `check_terminal`, which the dry run skips) ([output](shiploop-owed-outcome-evidence/trace_check_pairs.out)) | firm counts, two full runs and six slices |

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

## Intent audit: what the code does today (2026-10-28)

Each intention from this work and the owner rules it rests on, anchored in code at `04c45dce`. Evidence that ran:
`test/shiploop-loops.test.py` (58 tests OK), `test/shiploop-keepalive.test.py` (61 OK),
`test_wrong_action_is_named_before_path_or_format_checks` (OK), the floor test named in F15 (OK, pinning today's
divergence) and a new probe, [retry_carry_probe.py](shiploop-owed-outcome-evidence/retry_carry_probe.py)
([output](shiploop-owed-outcome-evidence/retry_carry_probe.out)).

| # | Intention (source) | Anchor | Evidence | Status |
|---|---|---|---|---|
| I1 | A skipped loop report never gets past the step (owner, 2026-10-27) | `shiploop_loops.check_terminal`, `check_loop_packet` | loops suite: missing receipt, active receipt, mismatched receipt, complete supports done only | Holds |
| I2 | A skipped callback is noticed and the model asked for it (owner, 2026-10-27) | `shiploop_keepalive.stop`, `_decide`, `_continue_reason`, `observe` | keepalive suite; E4 (memory wiped by `next`); F3, F4, F10 | Partly: noticed, but the ask is generic and the release is inconsistent. Phase A |
| I3 | The model needs no knowledge of its step or stage (owner, 2026-10-27; 2026-10-11 TODO) | packets per action; `hook_status` returns the `next` command | `SKILL.md` still asks the model to keep the run directory and `next` command in its summaries | Partly; the 2026-10-11 stateless audit has not started |
| I4 | The model names what happened; the script picks one next node (owner, 2026-10-27; ShipLoop purpose) | `_canonical_result`, `_apply_result`, `shiploop_stage_spec.send_back_target` | wrong-action test; navigator suites in the quick tier | Holds |
| I5 | Each step is one Until Loop with the step's prompt and exit conditions (v3; owner 2026-10-10) | `shiploop_loops.WORK`, `REPEAT`, `contract_writes`; `shiploop_loop_contract.contract` | loops suite | Holds |
| I6 | Criteria not met: plan, then loop back to the same step (owner, 2026-10-27) | runtime `_transition`, `next_packet` | probe: the next instruction opens "Resolve the evidence gap in the latest report"; the gap is quoted in it, the plan travels in `last_report.handoff` but is not quoted | Holds; the plan is carried, not restated |
| I7 | A supervisor or person can intervene, and only their reply resumes (owner, 2026-10-27) | `AWAITING_KINDS` (answer, present, service); `resume --answer`/`--observed` | keepalive suite (the quiet stop, the person's reply, service waits) | Holds |
| I8 | The loop ends only when the check says yes (iterate until a check confirms; owner 2026-09-24/26) | contract has no exit checks (F8, F16); check-only is advice | F15's floor test passes, pinning today's disagreement | Not yet. Phases B, C |
| I9 | `shiploop check` and "the check says yes" (owner, 2026-10-27) | none in code | journal only | Not yet. Phase B |
| I10 | No iteration counts (owner, 2026-10-11) | `GENUINE_FIX_ATTEMPTS` in prompt text; `shiploop-drive --max-sessions` | F14, F17, F11 | Partly. Phase A |
| I11 | Every command a model triggers is visible to host hooks (owner, 2026-10-11) | loop `start`/`done`/`record` run in the host shell; ShipLoop runs each recorded test command itself, `/bin/sh -c` in `shiploop_test_loop._run_command`, inside `complete` | code read | Partly: hooks see `shiploop complete`, not the test commands. ShipLoop's own test runs are also an owner decision (2026-10-10), so the owner must say which rule governs; phases A-C do not change it |
| I12 | Each packet works after a reset and stays concise (owner, 2026-09-26 and 2026-10-18) | packet renderer; `PRINT_LIMIT` | F12 (all inner packets over 16,000 characters), F7 (no action line in the last 43%) | Partly. Phase C (S4) |
| I13 | Simplify without losing a feature (owner, 2026-10-27) | — | — | Not yet. Phases A-C |

## Phase A, part 1: the stop hook names the owed report (2026-10-28)

Built on branch `feat/owed-phase-a-573963`. Status: firm for what the tests cover; not yet exercised in a live run.

- `hook_status` reads the innermost Until Loop (`shiploop_protocol._loop_receipt`: an active Improve review's receipt,
  else the current inner stage's) and adds `loop`, `callback` (`shiploop_navigator.complete_command`, the packet's
  own callback text) and `delegation`; `progress` becomes `<revision>.<callback attempts>.<loop iteration>` (F4).
- `shiploop_keepalive._owed_report` gives the refusal its ask: an active loop's next iteration report, or a finished
  stage loop's step callback; otherwise, and under ask-agent, "run `next`" as before (F3).
- `observe` keeps `last_block_progress` and `turn_blocks` when it binds the same run again, and drops the unused
  `last_block_rev` (F5). The release now fires after two refusals with no progress, whether or not the model ran
  `next` between them.
- Tests: `test/shiploop-keepalive.test.py` 65 OK (new: `test_running_next_between_two_stops_is_not_progress`,
  `test_each_reported_loop_iteration_is_progress`, three `OwedReportTests`); package-integrity 11, navigator-contract
  134, loops 58 and stage-spec 12 OK.
- **Held back on the owner's instruction (2026-10-28: "before you put any limits, check with me").** Replacing the
  driver's `--max-sessions` (default 20) with a wall-clock ceiling, and releasing a turn whose model does nothing
  twice while the same background task runs (F10, F11), were drafted, then reverted.
- **Owner decisions, 2026-10-28.** F11: the driver gets no default ceiling; `--max-sessions` is removed and an
  optional `--max-minutes` bounds the drive only when given (part 2 below). F10: keep refusing every stop while a
  background task runs; no change, and F10 is closed as the owner's choice.

## Phase A, part 2: no default ceiling for the driver (2026-10-28)

`shiploop_keepalive.drive` and `_drive_sessions` run until the run stops being active, a host fails without
advancing it, or two sessions in a row make no progress; `max_minutes`, when given, sets a wall-clock deadline and
cuts the last session's timeout to the time left. Tests: the driver suite's 10 tests OK, among them
`test_there_is_no_ceiling_by_default` (21 sessions, past the old default of 20),
`test_max_minutes_cuts_the_last_session_to_the_time_left` and `test_the_session_count_flag_is_gone`; the whole
keepalive file 68 OK.

## Phase A, part 3: the stuck rule becomes a criterion (2026-10-28)

The owner approved the wording ("Use the criterion"): a step reports send-back when the same check still fails in
the same way after a genuine fix, and the fix taught nothing new about why. It replaces the seven-attempt count.

- One source: `shiploop_stage_spec.STUCK_FIX` (the full rule) and `STUCK_FIX_ANCHOR` ("in the same way after a
  genuine fix", which every prose copy carries); the implement duty, `shiploop_loops.REPEAT["implement"]`,
  `REPEAT_STEP` and the chain contract print it; the skill card, test-loop.md, parallel-chain.md and
  execution-planning.md carry the anchor; SPEC S-10 is amended; the card ledger anchors on the new phrase.
- The skill card was already at its 30,500-byte bound, so its copy is the short form ("keeps failing in the same way
  after a genuine fix", linking the step exit criteria) and two words elsewhere in that item were trimmed; no bound
  was raised there. The implement packet's printed head grew 53 characters on both routes; `head_table.json` records
  the new values with the reason (every head still fits the 20,000 cut and the 19,500 required-text bound).
- Tests that judge what the model actually receives, added on the owner's request (2026-10-28: "update unit tests or
  mock tests as needed to help adjudicate whether the prompt, feedback, or scripts are actually all correct"):
  `test_no_count_stop_remains_and_every_copy_of_the_stuck_rule_carries_its_anchor` (stage-spec: no count in any
  source; the rule in both Repeat conditions, the implement duty and the chain contract; the anchor in every prose
  copy); `test_the_implement_packet_and_its_loop_carry_the_stuck_rule` (loops: the rendered implement packet and the
  Until Loop's own instruction); `test_the_stop_hook_names_the_loops_report_then_the_steps_own_callback` (loops, a
  real run: no loop yet gives the generic ask; an active loop's named command is its real read-only `next`, returning
  the same packet; a finished loop's named callback is the packet's own). Neither end-to-end test passes on main.
- Evidence: the quick tier with `--changed-from c076485c` passed, 67 suites, after two expected fixes: test-groups
  (a keepalive change now also selects shiploop-loops) and the head table above.

## Phase A E2E round: plan (2026-10-28, awaiting the owner's go)

Purpose: verify phase A live before its release (the release preflight needs a LEARNINGS.md entry), and answer the
owner's question with a live model: when a step's report is owed and the model stops, does the hook's text get it
reported.

Facts the plan rests on:
- The two latest live runs (`/Users/dadleet/e2e-runs/20261027/v2170-ds-battleship-759a03`, `v2180-sonnet-battleship-
  36036c`) each logged one hook event, "allow: run is done": no model ended a turn early, so a natural run alone would
  likely leave phase A's stop text unexercised, as the 1.12.0 and 1.13.1 traces did.
- The clear probe (`slice.py --clear-at <stage>:inside`) already stops a host inside a stage and continues it; hosts
  accept `resume=<session id>` for the same session; `run.py --source checkout` tests unreleased code.
- Latest DeepSeek baseline (`baselines.jsonl`): battleship, host claude, backend ollama,
  `deepseek-v4.1-flash:1017-cloud`, ShipLoop 1.16.0: PASS 4 of 4 checks, about 166 minutes (39 planning), 3,870 turns,
  32 refused callbacks; launched with `--timeout 14400`. Ollama 0.40.12 answers on :11434.

| Arm | What | Measures |
|---|---|---|
| A, natural run | battleship, host claude, backend ollama, DeepSeek v4.1 flash, `--source checkout` (main with phase A), permission mode auto; one run as a background task, resumed in place (`--resume-run`) when the task is killed near 120 minutes | the 4 case checks and the baseline's minutes, turns and refusals; every hook event in `RUN/trace.jsonl` with its text class (loop report, step callback, generic) and what the model ran next; any send-back citing the stuck criterion; any loop that repeats on one failing check |
| B, emulated refused stop | the clear probe stops the host at `implement:inside` (the loop started, its iteration unreported), then resumes the same session with the stop hook's text: treatment = phase A's text from the real code (`shiploop hook-status` + `_continue_reason`), control = the pre-phase-A sentence "run `next` and follow the packet it prints"; case hello, same host and model | whether the model runs the named loop command and reports the iteration (treatment) or reprints the packet first (control); redone work (the probe's S-6 `redone`); turns and seconds from the resume to the next loop report or accepted callback; any second stop |

Arm B needs a small harness addition (a same-session `hook-reason` continue condition with a `hook-generic` control),
admitted under SPEC "Change admission" with its tests. A kill is not the same as a model ending its turn; resuming the
same session with the hook's own text is the closest emulation available without a host API that forces a stop.

Before the release, phase A gets the SPEC change-admission record its commits lack (adversarial evaluation, anchor,
non-regression for each of the three changes); it is written with the round's results.

Owner decisions, 2026-10-28: both arms; no wall-clock timeout on arm A; three samples per arm B condition.

Arm A launched 2026-10-28 from a detached worktree at `337b09c5` (`.claude/worktrees/e2e-phase-a-4ed4e3`) as a
background task: output `/Users/dadleet/e2e-runs/20261028/pa-ds-battleship-4ed4e3`, `--source checkout` (the
candidate build; a checkout run skips the marketplace version gate, which refuses while phase A's notes are
unreleased).

Arm B blocker, found while building it: the Claude host runs every session with `--no-session-persistence` and its
`argv` ignores `resume` (`hosts.py`, Claude host `argv`), so a stopped Claude session cannot be resumed in place, and
`:inside` positions fire only on Claude's stream. Two designs: B1, continue in a fresh session whose prompt is the stop
hook's text (a small `slice.py` change; tests whether the text alone gets the report, the driver's situation); B2,
persist the Claude session and resume it with the hook's text (a Claude host change; the faithful emulation of a
refused stop, but resuming a killed `claude -p` session is unproven).

**Folded in, 2026-10-28 (owner via the progress-status session, "Fold them in"; main `1575832b`).** Every run's three
trace checks (keepalive_text, packet_reprint, owner_note; "not exercised" is not a pass) are recorded for this round.
Arms A and B started from `337b09c5`, before that commit: arm A is regraded with main's `run.py --grade-only
--resume-run` when it finishes, and arm B's slices get `run_trace.checks` computed over their traces. One extra case
run with `--owner-note-at implement` (not a baseline arm) waits for the owner's go on its case, host and model;
owner_note is read after the step that follows any held callback.

**Harness defect found launching the owner-note run (2026-10-28, firm).** `run.py` refused to start: SPEC "The
resource lifecycle" flagged arm B's live slice host (pid 46499, parent `slice.py` pid 45632) and four hosts of another
session's E6D2 slices as orphans "whose harness is not running", and suggested `lifecycle.py cleanup`, which would have
killed live runs (not run). Cause: `listeners.case_alive` judges a harness alive by the case lock `.harness-lock`, which
`run.py` holds (`listeners.hold_case`) but `slice.py` never takes, so every live slice reads as orphaned and blocks any
`run.py` launch under the same runs root.
**Fixed 2026-10-28 by `98e7aff0` (another session):** a slice now holds its case lock while it runs. Slices already
running from older worktrees hold none until they end, and for those a separate runs root is still the workaround.

**Owner's choice, 2026-10-28: "Separate runs root".** The owner-note run was launched at 19:45Z from main `4e1c8df0`:
hello, Claude host, DeepSeek flash on Ollama, `--source checkout --owner-note-at implement`, no timeout. Its output is
`/Users/dadleet/e2e-runs-owner-note/20261028/pc-ds-hello-note-b45e87`, with
`SHIPLOOP_E2E_RUNS_ROOT=/Users/dadleet/e2e-runs-owner-note`, so the orphan scan sees only its own root. Caveat: the
same root decides which runs count as its neighbours, so this run's environment record does not see arms A and B
running at the same time; its overlap figures understate the load on the machine.

**Laptop sleep, 2026-10-28 20:00:24Z–20:47:39Z (47 min 15 s; firm, from `pmset -g log`).** The battery ran out ("Low
Power Sleep … Charge:1%", then a wake from hibernate when the owner plugged it in). Every process paused and resumed.
- Excluded from timings: any duration that spans the gap. The Live Run Card marks it as a timeline band on every job.
  The builder's finish estimates (`status_card` progress `eta`) still count it, so they run about 47 min late.
- Arm A: the W2 implement Improve submission (`shiploop complete`, 20:00:26Z) was in flight. On wake, auto mode's
  safety check timed out against the model backend and refused it. The model retried at 20:48:31Z (a `--check-only`,
  then the real call) and was accepted: test, revision 27. At 20:49:16Z the host auto-compacted the context (168,006
  → 27,664 tokens); that came from context size, not the sleep. The model then re-opened the packet file and started
  the test loop. A natural lost-context event for this round's trace checks. Evidence: arm A `events.jsonl` lines
  485634–485709.
- Arm B generic 3: paused in test-spec, before its clear. The clear and the fresh session came after the wake, so its
  continuation timings are unaffected.
- Owner-note run: paused in test-strategy. No errors; the note fires at implement, after the wake.
- The other session's E6D2 slices on this machine paused too; their wall-clock times include the gap.

### Arm B results (2026-10-28, interim: n = 3 per condition, one case, one model)

Setup: node-fix-bug, Claude host, DeepSeek flash on Ollama; seed at step-plan, clear at `implement:inside`. A fresh
session continues with the stop hook's text as its prompt: `hook-owed` is phase A's text, `hook-generic` the
sentence it replaced. The plugin is built from `fd65120f`, plus the harness fixes `b2a53912` and `c8bcb464`. Every
sample was cleared with the stage loop active and iteration 1 unreported.

| sample | first command | loop reported | implement accepted | commands to accept | redone | pass |
|---|---|---|---|---|---|---|
| owed 1 | the named loop `next` | 115 s | 179 s | 15 | 0 | yes |
| owed 2 | the named loop `next` | 101 s | 105 s | 9 | 0 | yes |
| owed 3 | the named loop `next` | 103 s | 165 s | 17 | 0 | yes |
| generic 1 | `shiploop next` | 91 s | 105 s | 10 | 0 | yes |
| generic 2 | `shiploop next` | 84 s | 105 s | 10 | 0 | yes |
| generic 3 | `shiploop next` | 111 s | 156 s | 10 | 0 | yes |

Medians: owed reports at 103 s and is accepted at 165 s after 15 commands; generic reports at 91 s and is accepted at
105 s after 10 commands. No sample had a refused callback. Set aside: generic 1 (seed defect), the first owed 3
(owner defect; its first move was the loop `next`, report 77 s, accepted 102 s), and the cut owed 2 and generic 3.

Findings:
- **B1-o1 (interim).** The owed text changes the first move: 3 of 3 samples ran the exact loop command it names.
- **B1-g1 (interim).** The old sentence reaches the same outcome. `shiploop next` reprints the implement packet,
  and the packet carries the loop's own `done` command and the callback. All 3 samples rechecked, reported and were
  accepted with nothing redone.
- **Phase A's text is not shown to help on this model.** Both conditions reached the report in every sample. The
  owed samples took more commands, and two of three spent one on a `--check-only` dry run. The accept times overlap
  (owed 105–179 s, generic 105–156 s), so n = 3 cannot separate them. No harm to outcomes was seen either.
- **Not tested.** A model that ignores `next`. A stop the hook continues within the same session: no valid sample
  stopped, so `keepalive_text` is "not exercised" everywhere. The owed text's other branch, "loop finished, callback
  owed". Hosts other than Claude.
- **Trace checks** (`arm-b-trace-checks.json`, computed with main's `run_trace.checks`): keepalive_text,
  packet_reprint and owner_note are "not exercised" on every slice, and "not exercised" is not a pass.
  packet_reprint counts only identical reprints (same action and hash, `shiploop_trace`). The fresh session's
  `next` reprint is 52 characters longer than the first print (19,471 vs 19,419), so it is traced as a new packet with
  its own kept copy.
- Evidence: `docs/shiploop-owed-outcome-evidence/arm-b-results.json` (written by `arm_b_metrics.py` from each slice's
  `sessions.jsonl` and `events.jsonl`) and `arm-b-trace-checks.json`.

### Owner-note run: owner_note passes live (2026-10-28, firm, n = 1)

hello, Claude host, DeepSeek flash, `--owner-note-at implement`, main `4e1c8df0`. The run went as the design
(`shiploop_owner_notes`) says:
- 21:13:11Z: the implement packet was printed.
- 21:13:12Z: the harness wrote N1. It came after the packet, so the packet does not quote it.
- 21:16:04Z: the `--check-only` callback was held once, and the hold printed N1.
- 21:16:23Z: implement was accepted. Its summary cites the note: "Owner note N1 (21:13Z) was read and changes
  nothing about the step".
- A held callback shows a note but never delivers it, since only a packet survives a context clear. So the test
  packet (`nav-1c83…`) quoted N1 again.
- 21:22:14Z: the test step delivered it (step 12), and its summary cites N1.

`run_trace.checks` owner_note: **pass**, "N1 delivered by nav-1c83…, cited". This is the first live pass of any of
the three trace checks.

Cost of the design: the model was asked twice, and it cited the note in two summaries. Not a defect; the design pays
that cost so the note survives a clear.

Result (run end 22:18Z): **PASS**. Every verdict passed, ShipLoop reached done, and both of the case's checks pass.
- Clock time 9,178.6 s (153 min); about 106 min active, since the 47-min sleep is inside it.
- 12 ShipLoop refusals, none repeated. Among them are `--check-only` field-length bounds, one improve-pass called
  before the improve skill ran, and one improve-pass with an unknown `--final-result` flag.
- Trace checks from the run's own `run.py` (main `4e1c8df0`):
  - owner_note **pass**.
  - packet_reprint **pass**: one identical reprint, of the `done` packet at 22:17:58Z, names its kept copy
    `packets/sent/2f29e721….md`. The first live pass of this check.
  - keepalive_text not exercised: no stop was continued.
- Evidence: `/Users/dadleet/e2e-runs-owner-note/20261028/pc-ds-hello-note-b45e87.log`, and under that folder
  `metrics.json`, the run's `run/trace.jsonl`, `results/nav-a6c8….md` and `results/nav-1c83….md`.

### Arm A: battleship passes; the hook continues once, at a stage boundary (2026-10-28, firm, n = 1)

battleship, Claude host, DeepSeek flash, built from the phase A checkout (`337b09c5`), no timeout. The run started
17:32Z and ended about 23:45Z.

Result: **PASS**. Every verdict passed, ShipLoop reached done, and all four battleship checks pass, including HTTP play
against the served game.
- Clock time 22,355.5 s (372 min); about 325 min active, since the 47-min sleep is inside it.
- Work: 48 stages; 15 Improve children with 37 passes; 49 ShipLoop refusals, 25 of them `--check-only` dry runs.
- Mutation: 122 of 261 caught.
- Release-verify ran the released tree and returned `add-work`: the README said an invalid PORT exits non-zero, but
  spec R-2.3 and `server.js` resolve it to 3000. The corrective item W4 ran its own inner loop. W4's test sent its plan
  back once, because its floor of 4 focused tests was unreachable (ST-1 is opt-in). Then the release stages ran again.
- Through the sleep: on wake, auto mode's safety check refused one `complete`. The model retried and was accepted. A
  host auto-compaction at 20:49Z was recovered from the packet.
- Trace checks, regraded with main's `run.py --grade-only` (`35ec5366`):
  - **keepalive_text pass.** One continuation with its text, at 23:35:20Z, at release-check (revision 68). The hook
    gave the generic "run `next`" text: release-check has no stage loop, so phase A's owed text would have added
    nothing. The run went on to done, and the final stop at 23:44:39Z was allowed ("run is done").
  - packet_reprint not exercised.
  - owner_note not exercised (no note was written).
- Correction: at 15:31 local I reported that arm A's stop hook "never fired". That held for the first 252 active
  minutes only; the continuation above came later.
- Evidence: `/Users/dadleet/e2e-runs/20261028/pa-ds-battleship-4ed4e3.log` and `.regrade.log`, and that run's
  `run/trace.jsonl` (hook events) and `results/nav-a6292ace….md` (the add-work result).

### shiploop 1.18.0 shipped phase A before these results (2026-10-28)

Release `6828acb9`, at 16:40 local, under the owner's git identity but not from this session, shipped all three phase
A notes: the owed-report stop text, the driver's lifted ceiling, and the stuck-rule criterion. The release preflight
passed on earlier LEARNINGS entries. This round's results (above) arrived after it. The trims plan
(`docs/shiploop-trims-plan-2026-10-28.md`, approved by the owner) removes the owed text in the next release, under a new
change note, because the release consumed the old one.

**Owner's choice, 2026-10-28: B1.** Change admission for the harness addition (SPEC "Change admission"), on branch
`feat/e2e-hook-text-232e69`:

- **Change.** `slice.py` gains two `--resume-prompt` conditions. `hook-owed`: the stop hook's reason as the plugin
  under test writes it (its own `shiploop_keepalive._continue_reason` on the run's `hook-status`). `hook-generic`:
  the pre-phase-A sentence ("run `next` and follow the packet it prints", from `_continue_reason` at `04c45dce`),
  filled from the same `hook-status` fields. Both continue in a fresh session, as `names-next` and `withheld` do;
  `sessions.jsonl` `told` records the condition and the loop state and callback at the continuation.
- **Adversarial evaluation.**
  - Weakens S-6? It measures redone work after the clear exactly as before; the condition is recorded in
    `invocation.json` and `told`, the default stays `names-next`. Mitigated; tested by the parser test.
  - Tests the wrong text? `hook-owed` is built by the plugin build under test, in a subprocess whose path is that
    build's scripts directory, never the harness checkout's import. Mitigated; a test compares it with the plugin's
    own function.
  - Fails silently? A `hook-status` failure, or a text the plugin cannot build, ends the slice with the reason; a hook
    condition never falls back to another prompt. Mitigated; tested.
  - Uninformative samples: when the clear fires before the loop starts, both conditions print the generic ask. Accepted
    and made visible: `told` records the loop state, and the analysis counts such samples separately.
  - Other hosts: `:inside` fires on Claude only (unchanged); the conditions themselves need only the CLI. Accepted.
  - Cost, secrets, user work: two local subprocess calls per clear; no network, no repository writes. Accepted.
  - Gamed: both conditions read the same `hook-status`, and the control is a frozen copy of the old text. Mitigated.
- **Anchor.** The owner's question (2026-10-27: does a stopped step get its report made) and S-6's clear probe; evidence:
  the two latest live runs logged no stop-hook continuation, so phase A's text is unexercised live.
- **Non-regression.** `names-next` and `withheld` are unchanged; the parser's default is unchanged; the slice suite and
  the release-slice suite pass.

**Arm B seed defect (2026-10-28, firm; my launch error, not ShipLoop).** Arm B first ran with `--seed-at test-spec`.
node-fix-bug has no `seed_records` (`step_cases.json`), so the seed recorded step-plan with no steps
(`results/nav-bb73570b….md`: outcome done, a synthetic summary, no `steps`). `shiploop_loops.current_step` then returns
None, implement cannot build its loop, and every done result is refused.
- hook-generic 1 (18:11Z) ended with implement **blocked**. The model named the cause correctly: "W1's accepted step
  plan records no implement step". `told.hook.loop` was `{}`.
- hook-owed 1 is kept as a valid sample. Its test-spec sent the plan back, so step-plan ran for real and implement had a
  step and a loop: loop iteration 1 was active at the clear.
- Set aside as evidence: `pb-hook-generic-1-232e69.seed-defect` and `pb-hook-owed-2-232e69.seed-defect-cut` (stopped
  in test-spec).
- The batch was relaunched at 18:25Z with `--seed-at step-plan` (same case, host and model), which runs the real
  step-plan.
- Harness change, on branch `feat/e2e-hook-text-232e69`: `slice.seed_gap` refuses, before anything is built, a seed
  past step-plan whose merged records give step-plan no steps.
- Tests: three `SeedGapTests` (refused through `main` with no output folder made; seeds up to step-plan pass; every
  test-spec experiment in `experiments.json` still passes, each giving one step). The slice suite passes, 67 tests;
  ruff findings match HEAD. No fail-first run: without the guard, `main` would build and start a real host session.
  Commit `b2a53912`.

**Arm B keepalive-owner defect (2026-10-28, firm; harness, not ShipLoop).** hook-owed 3 (19:16Z) failed `process`.
- What the fresh session did: it ran the named loop `next` first, found the fix not yet made (the clear came before
  the first session edited anything), made it, reported at 77 s, and implement was accepted at 102 s.
- Where it stopped: at the implement Improve packet, the model ended its turn with a status narrative (`end_turn`).
  The keepalive Stop hook fired but allowed the stop: `run/trace.jsonl` records `"decision": "allow", "why":
  "another session owns this run"`.
- Cause: the keepalive keeps only the run's owner going (`shiploop_keepalive.claim_owner`). A claim ends when the
  owner's turn ends normally, when the driver finishes a session (`drive` calls `release_owner` after every
  session), or after `OWNER_STALE_SECONDS` (30 min) with no activity. The slice kills the cleared session with
  SIGKILL, so its claim stayed: `~/.local/state/shiploop/keepalive/runs/f4cc1c6b….json` still named the first
  session, last seen 19:23:49Z. (The Claude host keeps the real HOME, so slice keepalive state is the user's own.)
- Effect on earlier samples: none. Owed 1–2 and generic 1–2 never stopped before the slice ended them.
- For the stop-text measures, owed 3 still counts: its first move, report and acceptance match owed 1–2. Its pass
  verdict does not count.
- Fix (`c8bcb464`, branch `feat/e2e-hook-text-232e69`): `slice.release_keepalive_owner` runs the build's own
  `release_owner` at every clear, in the hooks' environment, as the driver does. Tests: a clear frees a dead
  session's claim (1 failure with the release patched out); with no clear the claim stays. Slice suite 69 OK.
- Owed 3 and the cut generic 3 are set aside (`*.owner-defect`, `*.owner-defect-cut`). Both reran at 19:35Z on the
  fixed harness.
- Same exposure for arm A: `run.py --resume-run` starts a new session while the killed one may still hold the claim.
  Before any arm A resume, release its owner the same way (record it here).
- **Open for the owner.** Outside the driver, a crashed or killed session leaves the next session unkept for up to
  30 minutes. That is the documented trade-off, which stops two live sessions fighting over a run. Should a
  session that runs a driving command (`next`, `complete`) take over a claim whose owner process is gone? Not
  changed; it needs a decision. **Decided 2026-10-28 (owner: "a session that died should be taken over"); built in
  batch 2, below.**

## Batch 2 (2026-10-28, owner: "Start batch 2"; branch `feat/shiploop-batch2-b384be`)

**Release preflight (`eba6d983`, firm).** Each ShipLoop change a release ships now needs an E2E round committed after
it, or its own `No-E2E-Round` reason. Ancestry decides "after". Replayed on history: the rule refuses 1.18.0, naming
the three phase A commits. It would also refuse 1.19.0 as cut, naming T1 and T2. That release was already cut, so the
rule applies from the next one. Tests: release-preflight 19 OK; the two new refusal tests fail on the old rule.

**Slice case lock (`98e7aff0`, firm; landed by another session the same evening).** A slice holds
`<out>/.harness-lock` while it runs, as `run.py` does, so lifecycle's orphan check no longer flags live slices. The
separate runs root used for the owner-note run is no longer needed. This session's own version of the same fix was
dropped in favour of it: it also closes the lock in a `finally` and tests the orphan scan itself.

**Dead-session takeover (firm for Claude; other hosts fall back safely).**
- **Design.** A claim records the owner's host process: the nearest ancestor of the hook that is not a shell or
  launcher, when it started at least 2 seconds before the hook. A different session takes the run over as soon as
  that process is gone, or its pid is reused (the start time differs). A live owner keeps the run until
  `OWNER_STALE_SECONDS`. With no process found, only time frees a claim, and the owner's next hook looks again.
- **Rejected along the way:** "take over when the claimant runs in the same host process" (to cover `/clear`). Two
  live sessions in one host process would fight. `/clear` and normal exits are better covered by a host session-end
  hook (Claude `SessionEnd`), which ShipLoop does not register yet: a follow-up, once each host's equivalent is known.
- **Probe on a real Claude session** (`docs/shiploop-owed-outcome-evidence/host_process_probe.py`, `.out`):
  - a `claude -p` session on Ollama with PostToolUse and Stop hooks;
  - both hooks found the session's own `claude` process (pid and start time);
  - Claude runs a hook directly under `claude`, which was 2 seconds old at its first hook;
  - from this desktop-app session, the walk also stops at the session's own `claude` (pid 98461), not the app.
  So the first draft's 10-second floor would have skipped a fresh host and recorded the process above it. Hence the
  2-second floor, measured against the hook's own start, plus a retry while unknown.
- **Why it is safe on other hosts:** a launcher starts with its hook, so it is never recorded. If something above the
  host is recorded, it outlives the host, so the owner reads as alive and the time rule decides, as before.
- **Tests:** shiploop-keepalive 72 OK. New: `OwnerProcessTests`, 7 tests. Fail-first: with only the time rule, the two
  takeover tests fail.
- **Flake found and fixed:** the keepalive suite's "Directory not empty" cleanup error (4 of 7 direct runs today) came
  from the detached progress observer that `shiploop init` starts, which rewrites the run folder every 2 seconds. The
  suite now sets `SHIPLOOP_PROGRESS=off`, as run_suites.py already does for the tier.

**Correction (2026-10-29, firm): the takeover shipped in 1.20.0, not "with the next round".** Release `3d7b83a3`
(skill-craft 2.21.0, shiploop 1.20.0, 2026-10-28 20:08) shipped `f82da379` on that commit's own `No-E2E-Round` trailer:
"host process lookup checked live on a real Claude session (host_process_probe.out); the takeover rule is unit-tested;
no E2E case crashes a session". The release deleted `changes/shiploop/keepalive-dead-owner-takeover.md`, and Claude,
Codex and Grok each have 2.21.0 installed.
- **What said otherwise.** `917e0c2b` (20:16: "its change note is pending and release.py's preflight (eba6d983) refuses
  a release until a LEARNINGS commit descends from it") was written from a check made minutes before that release
  landed. A rebase before the push pulled the release in and the claim was not rechecked. `1961f4c5` repeats it ("as
  the owner chose for the takeover"). The owner's "Ship with next batch's round" (2026-10-28) rested on that premise.
- **What is still owed.** Live evidence for the takeover: a run whose dead owner's claim is left in place, and the next
  session taking it at once. It is earned in the evidence round shared with the session-end hook (`1961f4c5`, below).
  `run.py --interrupt-at` already kills a host and leaves its claim in place (`run.py` never frees one); a slice clear
  frees the claim itself, so it cannot show the takeover.
- **Open for the owner.** Keep the takeover live and earn that evidence (recommended: with no process found, only the
  30-minute rule frees a claim, and it fixes a stall seen in the phase A round), or revert it.

## Session end releases the run (2026-10-28, owner: "Yes, build it"; firm for Claude, constructed for the others)

The follow-up named in batch 2. A `/clear` or a normal exit leaves the host process alive, so the process check cannot
free the run; the host's own session-end event can.
- **Host support, from the installed binaries:**
  - Codex 0.165.0 has `hooks/src/events/session_end.rs` and "failed to flush transcript before SessionEnd hook";
  - Grok 1.0.70 lists `SessionEnd` among its known hook events, and its validator rejects only unknown names, so the
    shared Claude-format `hooks/hooks.json` stays valid for Grok;
  - cursor-agent 2026.09.23 knows `sessionEnd`;
  - Claude Code runs `SessionEnd`, as the owner's own global hooks already use.
- **Probe on a real Claude session** (`docs/shiploop-owed-outcome-evidence/session_end_probe.py`, `.out`): a `claude -p`
  session's `SessionEnd` hook fired on exit with `session_id`, `prompt_id`, `transcript_path` and `reason: "other"`. That
  payload is the test fixture. The Codex, Grok and Cursor fixtures are constructed, as their README says.
- **Change:**
  - `shiploop_keepalive.session_end` drops the session's binding and releases the run only when that session owns it.
    It looks the session id up under every host, because a Codex session-end payload may lack the `turn_id` that tells
    Codex apart;
  - the plugin declares a `session-end` hook (`host-hooks.json`, new generator event mapped to `SessionEnd` and Cursor
    `sessionEnd`);
  - `shiploop-hook install` writes the same entries.
- **Tests** (shiploop-keepalive, 75 OK; package-integrity 11 OK; skill-frontmatter PASS):
  - each host's session end releases its own run;
  - the next session takes it at once;
  - another session's end, a subagent's, or an unbound session's changes nothing;
  - the installer writes and removes the entries;
  - each host's generated hooks file runs the session-end script and releases.
  - Fail-first: with `session_end` stubbed, all three behaviour tests fail.

## Phases B and C: plan (2026-10-28, awaiting the owner's approval)

[The plan](shiploop-check-phases-bc-plan-2026-10-28.md) names every file, symbol, test and removal for B (one
evaluator, `shiploop check`) and C (the loop ends when the check says yes), the measure and the decisions D1-D8.

- **F18, firm (E6).** A dry run before an inner `complete` is already the norm, and no inner `complete` was refused
  in arm A. The `verify_script` that C makes mandatory takes the dry run's place, so commands per inner step should
  not fall; the plan pre-registers M1 as unchanged within ±1. The repeated gates are at the outer stages, where the
  callback line (`shiploop_prompts.CALLBACK_REASON`) invites a dry run before every `complete` (plan decision D3).
- **F19, firm.** No live ShipLoop run has run an Until Loop `verify_script` (0 `UNTIL-LOOP-RECORDED` lines in arm A's
  and arm B's event streams), so C's mechanism is untested on any model; the plan puts a one-slice pilot before
  C's batch.

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
- 2026-10-28: intent audit I1-I13 added, anchored in code with four test files and the new retry-carry probe.
- 2026-10-28: corrected the experiments' provenance: E3-E5 were rerun at `821db5c0` before the commit, not only run
  at `b0d29284`; four commits from other sessions had landed on main in between, none touching the traced code.
- 2026-10-28: E6 (dry runs per stage, from the run traces), F18-F19 and the phases B and C plan added.
- 2026-10-29: correction: the dead-session takeover shipped in 1.20.0 (`3d7b83a3`) on its own `No-E2E-Round`; `917e0c2b` and `1961f4c5` said it was pending. Live evidence still owed.
