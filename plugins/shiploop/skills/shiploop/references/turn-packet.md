# Action packet and cold-context handoff

The host skill invocation is deliberately thin: it starts or resumes ShipLoop,
then the script packet owns the current action. A packet supplies the current
phase/stage and action capability, the bounded context needed for that action,
the result schema location, the check/history commands that are required now,
and the exact **When done** command plus its explicit `done` alias. It does not paste the README, every prior
pass, or an unbounded repository snapshot into the model window. Durable
Markdown remains the complete current state.

Treat the printed packet as the operational source for this turn. After a
context reset, call `next`, page only the named context sections, and follow
the newly printed action rather than replaying a remembered plan. A paused,
halted, legacy, or uncertified-terminal packet omits both completion callbacks
and prints `Recovery:` instead. That remains unfinished state; do not infer a
closer from a prior packet.

~~~text
ShipLoop 0.9.0 | <phase> / <stage> | revision <n>
Run: <absolute run directory>
State: <run>/state.md
Journal: <run>/shiploop-improvements.md
Action: <run-scoped action id>
Stage: <phase> / <stage>
Worktree: <repo or active worktree>
Current task: <active step / receipt / iteration when applicable>
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
When done: shiploop complete --action <id> --result <path>
Call this when done: shiploop done --action <id> --result <path>
~~~

The packet points to the relevant approach, environment, spec, lifecycle, and
plan records; it does not copy their bodies. Read only the sections required
for the action. After cold context loss, use context section prompt first, then
the current step or iteration. The active step's stored prompt and exact
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

There are no packet headings for a hidden parent loop, no full frozen-context
echo, and no inferred closer. Do not run bare complete, complete-step, update,
start-step, clear-step, or inject-step; those are pre-0.9 interfaces. Do not
call a transition complete because a chat response says it is done. Persist the
requested result and execute the packet's exact command.
