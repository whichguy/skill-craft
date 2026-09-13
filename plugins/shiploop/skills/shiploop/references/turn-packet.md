# Action packet and cold-context handoff

The host skill invocation is deliberately thin: it starts or resumes ShipLoop,
then the script packet owns the current action. A packet supplies the current
phase/stage and action capability, the bounded context needed for that action,
the result schema location, the check/history commands that are required now,
and the exact **Call this when done** command (`complete` remains an alias).
It does not paste the README, every prior
pass, or an unbounded repository snapshot into the model window. Durable
Markdown remains the complete current state.

Treat the printed packet as the operational source for this turn. After a
context reset, call `next`, page only the named context sections, and follow
the newly printed action rather than replaying a remembered plan. A paused,
halted, legacy, or uncertified-terminal packet omits both completion callbacks
and prints `Recovery:` instead. That remains unfinished state; do not infer a
closer from a prior packet.

Each packet is sufficient after a reset; it need not insist that an intact
conversation be cleared. Retained context within the same owning quality loop
may help compare work, but current Markdown wins. “Quality loop” means any
review-and-improve loop, not just the outer stage named `quality`. A known
owning-loop breadcrumb locates the work; it is not another scheduler.

The original output is a candidate until reviewed. Distinguish it from the
first recorded assessment, latest candidate, and current checks. Historical
assessments may explain prior decisions but cannot certify changed work or
restore a repaired epoch's clean streak. Missing provenance is explicitly
unavailable, never reconstructed from chat.

~~~text
ShipLoop 0.9.0 | <phase> / <stage> | revision <n>
Run: <absolute run directory>
State: <run>/state.md
Journal: <run>/shiploop-improvements.md
Action: <run-scoped action id>
Stage: <phase> / <stage>
You are here: <phase, selected task, owning loop and current action>
Worktree: <repo or active worktree>
Broader purpose: <grounded original outcome, not inferred new scope>
Spec reference: <actual available file/section and bounded reader; status explicit>
Current task: <active step / receipt / iteration when applicable>
Why now: <how this assigned work contributes to the purpose and current gate>
Quality baseline: <candidate and recorded assessment status; historical is not current proof>
Objective: <the bounded outcome for this action>
Until: <the recorded terminal predicate for this loop/action>
Continue while: <what remains unfinished>
Evidence required: <current evidence and schema fields>
Environment: <frozen baseline and current overlay pointer>
Bounded context: <section commands and current digest pointers>
Result format: <result fields and linked protocol section>
Result template: <the inbox template / required field shape>
Write the result to: <absolute inbox path>
<only relevant check/history command(s)>
When done: exact callback only
Call this when done: <resolved CLI> done --run-dir <run> --action <id> --result <path>
~~~

This is an explanatory envelope, not a literal response or runnable template.
The result template uses the accepted `shiploop-state` fence. Its exact write
destination is the callback's `--result` path; do not substitute a product file.
When several guidance pages are selected, the packet prints one absolute
guidance directory and filenames/sections relative to that directory, not to
the product worktree. This removes repeated paths without dropping readings.
The packet points to the relevant approach, environment, spec, lifecycle, and
plan records; it does not copy their bodies. It connects this task with the
broader system purpose and provides an actual file reference for deeper insight.
Before an accepted spec exists, use the original request and distinguish any
draft from an approved contract. Consult broader rationale when resolving a
tradeoff; required acceptance criteria remain mandatory even when background
reading is optional. The reference grants no new writer, permission, or scope.
Read the packet's selected sections after context loss; consult its purpose
reader when the broader rationale needs clarification. Do not infer a required
reader that the packet has not made available. The active step's stored prompt and exact
produces live in backchain/plan.md; its receipt preserves prior iteration facts.

## Action use

- The Action value is required by complete, verify, history, journal, and
  repair. A stale ID is refused.
- A completed action can be replayed only with byte-equivalent structured
  content. The script then prints the current action instead of double-counting
  a transition.
- next and status reprint the same action. Neither silently advances an
  inner-loop stage.
- pause preserves the action with a non-success reason; resume reprints it.
  halt is terminal and its packet names the unfinished handoff.
- The packet does not prove semantic correctness, test adequacy, publication,
  or user acceptance. It reports script-verified state and host-reported
  evidence separately.
- Supporting context/history/check and plan-status responses identify their
  relationship to the current action. A page, handoff status, or check PASS is
  not a new assignment or overall completion. Context and history may record
  read receipts; they do not advance the action. Keep page digests and
  continuations intact and return through the printed current cursor.
- Paused, damaged-state and terminal responses use only safely available
  orientation. Do not load rejected evidence to fill a missing description,
  repeat a completed external operation, or invent a callback while blocked.

## Stage-specific commands

For implementation, Improve verification, final verification, and outer
quality, the packet prints:

~~~text
Checks: shiploop verify --run-dir <run> --action <id> --manifest <absolute-checks.md>
~~~

Every manifest has a concrete lint command and required test commands. If the
manifest changes for a current action, run `verify --reason='<why coverage changed>'`;
failed attempts remain in check-attempts/ and do not become
invisible.

For Improve and execution-plan review, the packet prints a bounded history
command. The default output is a compact SHA/subject index and a pointer to the
durable page. Read the required full commit bodies before completing review:
new runs require the latest seven, unmarked legacy runs retain ten, and a
shorter history uses all available commits. Follow the packet's bound policy.
Retrieve a specific full body without flooding the context:

~~~text
shiploop history --run-dir <run> --action <id> --limit 1 --skip <n> --full
~~~

For commit, the packet names the iteration ID. The primary commit must end
with ShipLoop-Iteration: <id> and include the review and application learning
text verbatim in its evidence-based body.

## Do not infer the old protocol

An explicit breadcrumb describes stored owning and nested loops, not a hidden
host parent loop. There is no full frozen-context echo or inferred closer.
Do not run bare complete, complete-step, update,
start-step, clear-step, or inject-step; those are pre-0.9 interfaces. Do not
call a transition complete because a chat response says it is done. Persist the
requested result and execute the packet's exact command.
