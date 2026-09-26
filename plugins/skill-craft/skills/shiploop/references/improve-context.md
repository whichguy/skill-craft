# Improve context ownership

Use this host-owned boundary for a bound navigator Improve
child using the ephemeral Until Loop runtime. At an Improve checkpoint, one
valid producer submission parks the invoking parent and binds the child for the **whole Improve invocation**. The child owns
its reviews, applicable experiments, and shared investigation allowance; do not
create a worker or a fresh context for each review iteration. The parent remains
ShipLoop's control channel and alone may run verified `improve-complete` after
the runtime has written the terminal packet to the receipt and every candidate writer has stopped. A parent
pause retains the child; an unfinished child route is not proof that its
executor stopped. A direct `/improve` call remains the normal standalone
entrypoint and needs no bound packet; this binding is only the automatic
internal handoff for an existing ShipLoop run.

## Route by the run's delegation

The run-level `delegation` setting in `state.md` selects who executes the
invocation:

- `delegation: inline` is the default that `init` and `workspace start` record
  for new runs. The invoking parent conversation runs the whole
  invocation itself; follow the default route below.
- `delegation: ask-agent` is the opt-in route, chosen by passing
  `--delegation ask-agent` to `init` or `workspace start`, or by switching an
  existing run with `delegation --set ask-agent`. One fresh native worker runs the invocation through Ask Agent; follow the
  delegated route at the end of this guide.

The setting is run configuration, not an owner record. Change it for an
existing run only with
`python3 "$CLI" delegation --run-dir "$RUN_DIR" --set inline|ask-agent`; a
retried `init` or `workspace start` cannot change it. The change applies from the next issued action: the action pending when you switch, including its Improve checkpoint, keeps the route it was issued with,
so a bound child keeps the route it started under; the CLI refuses it only on
halted or done runs. If a `host-owner.md` launch-intent,
native handle or other evidence shows that a child may already have been
delegated, recover it with the delegated recovery rules whatever the current
setting says. The workspace, context-first, completion and acceptance sections
apply to both routes.

## Default route: the parent runs Improve (`delegation: inline`)

INNER Improve packets begin with "Keep the invoking parent alive and run this
Improve invocation inline." PRELUDE and OUTER Improve packets carry the same
runtime lines without that prefix. The parent conversation runs the selected
Improve card's ShipLoop whole-skill subcall once, in the exact Child
workspace; its review iterations share this context. Do not hand the invocation
to Ask Agent, a native worker or an extra worktree, and write no `host-owner.md`.
Run its reviews and checks in this conversation too; start no reviewer,
test-runner or executor agent unless the user asked for independent review. Do
not clear, hand off or pause for a clear during the invocation. This
conversation is both executor and parent: the only candidate writer until the
runtime returns a terminal packet, then the sole submitter of ShipLoop
callbacks. No script checks who executes; `improve-complete` imports this child
from its receipt and completion evidence.

Before start, verify the process cwd and Git root against the packet and follow
the unchanged workspace and commit rules below. Freeze the exact candidate
scope, selected packages, explicit user/repository authority including any
no-commit override, and evidence paths; carry current approvals, declines and
pending decisions into `context.authority`. Write the context-first opening
below. Put the packet's binding line alone and first in the frozen
`context.request`, with the opening after it; import rejects a marker embedded
in a sentence. Include `context.resources` locators for the receipt, parent
`state.md`, completion evidence path and exact parent return instructions, so
the terminal packet can locate the parent return after context loss. An existing
invocation keeps its frozen authority.

Start the runtime once, before any review work, with `--receipt` set to the
printed **Child latest packet receipt**: the runtime writes every start, next and
done packet there itself, the terminal one before it deletes its state, so the
receipt survives a lost context. Do not write or edit it. Only after the runtime
has written the terminal packet, write
the completion evidence described below, then run the packet's parent return and
callback. Runtime completion alone never advances the action, and no ShipLoop
callback runs earlier. For the selected initial Plan Improve child, the
parent-only `improve-reconcile` route applies once the runtime has returned its
stopped packet in this conversation and no candidate write is in progress.

A later user decision in this conversation applies from the next review
iteration. Record its source, receipt and effect, and any already-performed
action, in the existing review notes and replacement handoff; keep the frozen
launch context unchanged and continue the same runtime. A decision arriving
after completion cannot retroactively change the saved receipt.

After interruption or lost context, run the Recovery command and read the
reprinted child receipt locator. For an active child use the saved receipt's
exact `next_argv` once; for a complete child validate and import without
rerunning Improve. Start another runtime for this action only through the
stopped-child restart route below. Missing
active-child ephemeral state, a lost terminal packet, or a start that may have
run before its packet was saved is incomplete, never success or permission to
start over. Recover in one conversation at a time; if an earlier conversation
may still be writing the candidate, confirm it stopped before continuing.

## One existing workspace and one writer

Use the exact **Child workspace** printed by the bound packet. Both routes
preserve ShipLoop's existing candidate identity; the delegated route also
isolates conversation context. Do not create, rebase, remove or switch to
another worktree, or rewrite receipt paths to make evidence from another
checkout appear local.

The executor, which is the parent on the default route and the worker on the
delegated route, has exclusive write ownership of the scoped candidate, child
runtime, packet receipt and review evidence until it and any delegates finish.
Every other writer must stop competing writes, including check/build commands
that generate files in that workspace. Continue only unrelated work that cannot
change the child's inputs. This is a scheduling rule, not a process sandbox or a
script-enforced lock over the executor's lifetime.

On the delegated route, use native launch cwd only if exposed. Otherwise, and
always on the default route, require the Child workspace as the operation
directory on **every** shell call, and absolute paths for file tools. Before
task work, verify actual process cwd and Git root against the packet; report a
mismatch instead of operating in the inherited parent cwd.
For a genuinely new child, after the meaningful checks required by its scope,
commit authorized scoped changed files, including tests, documentation,
configuration and skills when in scope. Never commit
runtime evidence or inherited unrelated staged work, and do not create an empty
commit unless an explicit audit-every-iteration rule authorizes it. An explicit
user- or repository-authorized no-commit instruction overrides this default.
An already frozen child contract keeps its recorded authority on recovery.
Record the exact scoped contribution SHA in the handoff, or the authorized
no-commit/no-change reason. The parent validates that handoff and performs the
existing guarded workspace return; a delegated worker does not execute a
callback or return itself.

## Prepare the context-first assignment

Before starting Improve on either route, the parent writes the opening
**Current context and desired improvements** section from its current
understanding of the task, repository and exact candidate worktree. Include
**Current learnings** inside that section: a compact current-state brief of
facts and corrections, decisions and their rationale, hypotheses, and execution
pitfalls, as short labeled bullets. Suggested improvements remain candidates to
assess, not findings or authorization. On the delegated route, put this
completed opening first in the native worker prompt, before the skill
invocation, route markers and orchestration details. The navigator supplies
instructions and locators; it cannot synthesize facts from the parent's
conversation. The parent must fill the opening with the actual context, not
freeze or forward an empty template.

Explain what the candidate is meant to achieve, what already changed, what
appears to need improvement and why, and what remains uncertain. Bring forward
material user corrections, repository conventions and design decisions with
their rationale, observed failures/checks with revision or content identity,
and worktree-specific pitfalls or inherited work to preserve. Read relevant
accepted results/run notes and any required excerpt locators before summarizing.
Distinguish facts, hypotheses and suggested next work. Retain material unresolved
findings and failed attempts; they can be more useful than successful lessons.
If context is unavailable on recovery, name that gap instead of inventing it.

Use this order, filling values from the current task:

```markdown
## Current context and desired improvements
<The intended outcome, present candidate state, and the parent's assessment of
what would improve it and why. Name the relevant repository/worktree.>

### Current learnings
- Facts/corrections: <observations and supporting locators>
- Decisions: <accepted choices, approval/decline implications and their reasons>
- Hypotheses: <unverified concerns to investigate, not assumed defects>
- Execution pitfalls: <relevant failed attempts, tool or worktree constraints>

## Execute Improve
Run /improve using <selected absolute Improve SKILL.md>.

## Workspace, authority, and return
<All four literal route/owner markers; exact candidate/root/base/HEAD/scope and
inherited state; selected card/runtime identities; actual stage checks; scoped
approvals, declines and pending decisions with sources and conditions; input and
output locators; receipt/evidence/owner outputs; and parent-only continuation
and cleanup.>
```

That whole template is the delegated worker prompt. On the default route there
is no worker prompt: the parent freezes the opening section in the child
contract, runs `/improve` with the selected card itself, and keeps the
workspace, authority and return facts in `context.authority` and
`context.resources`; the route/owner markers and owner outputs do not apply.

Omit empty learning categories, or state when none are known. Preserve essential
meaning inline with locators for supporting detail; there is no word or bullet
quota. Be concise by removing repetition, not consequential context. The opening
is orientation, not a second authority contract or an exhaustive review checklist.
Improve may reject a suggestion, investigate beyond the supplied hypotheses,
choose a better approach and make substantial warranted changes. Derive edit
scope from the actual task and explicit boundaries; do not invent a narrower
allowlist merely from the currently changed files. Explicit candidate exclusions
and an already frozen scope remain binding.

Retain this opening once near the start of the child's existing
`context.request`, alongside the canonical request and binding marker; the
marker stays on its own line, alone and first on the default route. Use the
existing handoff to retain, correct or retire learnings across iterations. For
planning this opening supplies the compact planning summary; keep full
packets and verbose logs behind their existing locators rather than copying
them into child context.

For the initial Plan Improve child, retain the packet's experiment objective
and exit criteria, applicable original constraints, current source/action
locators, and decision consequences in that compact context. Keep essential
findings and rationale inline; locators cannot replace critical reasoning.
Identify valid producer evidence, unresolved outcomes, remaining allowance,
pending cleanup, and the exact terminal condition for the parent return.
These are existing contract and handoff contents, not a new result schema.

## Complete assignment and return

Carry the current approval/decline decision record, which is Ask Agent's on the
delegated route, into the existing child `context.authority` before start.
Summarize its practical implications in the opening without reducing a binding
decline to a review suggestion. Existing approvals remain usable under their
conditions; pending approval is not consent. Keep action/target boundaries and
parent-only ownership explicit.

The executor runs `/improve` using the selected absolute Improve card once and
follows that card and its bound runtime, saving each exact raw packet. At
return, preserve edits and all evidence in place. The return, which is the
worker's native return on the delegated route and the parent's own completion
evidence and handoff on the default route, includes:

- Improve's cumulative completion summary inline: key implemented changes and
  why they matter, what was learned or corrected across the run, actual
  validation and remaining work; distinguish actual checks from claims. Only
  for a successful terminal `complete` child, put the outcome and key changes
  in the existing completion record's `summary`, and the learning synthesis in
  `lessons`. An incomplete child returns a partial summary in its return and
  retained handoff/evidence, following the existing recovery route without
  claiming or submitting successful completion.
- Observed workspace, binding marker, exact latest packet receipt and completion
  evidence paths, final trivial self-pass review/check locators and any revised producer
  result. Include the unchanged parent return instruction as a locator for the
  parent to execute, not a worker action.
- Confirmation that candidate writes and delegates have stopped, no parent
  callback or workspace return was executed, and which paths changed.
- Canonical candidate/target and Git root, initial/final HEAD, scoped diff or
  changed-content locators, exact scoped contribution SHA or authorized
  no-commit/no-change reason,
  inherited dirty-state preservation, and next owner/retention action. Distinguish
  the bound candidate from the original caller; no helper delivery receipt exists
  for this in-place route.

Keep bulky review logs in the named evidence files. A summary does not replace
the terminal JSON receipt, and two callbacks do not replace two real reviews.

## Parent acceptance and recovery

Only the parent may run `improve-complete`, and only after every candidate writer
has stopped and it verifies the candidate edits, current checks, and exact
successful terminal receipt against this action. On the delegated route, first
collect the actual native return and confirm the worker and its delegates
stopped. Check that newer user instructions and parent state still allow
acceptance. Missing, active, blocked or stopped evidence leaves the parent
incomplete; a paused parent still retains its child and an unfinished child
route does not prove its executor stopped. The only settlement exception is the
packet-issued `stopped` reconciliation route for the selected initial Plan
Improve child using the bundled ephemeral runtime; it still requires confirmed
owner evidence and the parent's `improve-reconcile`, never `improve-complete`.
On the default route that evidence is the stopped packet returned in this
conversation with no candidate write in progress. Resolve conflicting scope or
stale checks before acceptance; changes after convergence require fresh review
evidence, not an unchanged old receipt.
To continue after a stop that cannot be reconciled, once its blocker is resolved or the user authorizes continuing, confirm no candidate write is in progress (delegated route: the recorded owner stopped), rename `packet.json` to `packet.stopped-<UTC timestamp>.json` and the sibling `reviews` directory to `reviews.stopped-<same timestamp>`, record the decision in the new context opening and start a new child with the same binding line; its `review_refs` and `check_refs` must be files the new child writes. To pause instead, run the parent pause command and leave the child active; never report `cancelled` for a pause.
On the delegated route, append the actual acceptance outcome,
candidate/check/diff evidence, and any later caller-delivery outcome to
`host-owner.md`; retain earlier launch and stop events. This record is not
authorization to bypass the runtime's importer.

On success the edits are already in the bound candidate; there is no second
worker patch to merge. At final `handoff` in workspace mode, the parent performs
the packet's existing guarded workspace return before `improve-complete`.
For other stages it imports once using the exact parent callback, then follows
the returned packet. Do not report delivery to the caller just because Improve
or its worker finished: a failed return retains the candidate and is still
incomplete. Do not clean up the execution worktree when Improve completes.

Carry the accepted changes and learning synthesis into the parent-facing result
and subsequent relevant context. Reconcile the reported integration/deployment
state with the parent's actual return outcome; do not substitute receipt paths
for the substantive summary or report candidate completion as caller delivery.

Recover a default-route child as described in its section above. Recover a
delegated child, or any child that may already have been delegated, with the
delegated recovery rules below.

This host instruction does not add machine enforcement of agent identity,
collection, exclusive writers or semantic review quality. The existing importer
continues to validate binding, workspace and receipt structure. A durable Until
Loop runtime is not supported and is refused at bind and import.

## Opt-in delegated route: Ask Agent executor (`delegation: ask-agent`)

This route applies when the run's delegation is `ask-agent`, including a saved
run without the setting. Its INNER Improve packets begin "Keep the invoking
parent alive and follow Improve's selected context ownership." One fresh native
worker owns the whole invocation. The worker retains useful within-loop context
while the parent receives a compact return and durable locators. This reduces
parent-context growth, not necessarily total tokens or latency.

For a new delegated invocation, run the host-selected `improve-agent` card for
this bound child. That card resolves the host-selected Ask Agent card, requires
its declared `ask-agent/consumer-owned-workspace/v1` capability, selects
`workspace_route: consumer-owned` and `delivery_mode: in-place`, composes the
context-first assignment and the worker contract, and verifies the return. It
fails closed when the capability or a contract field is missing and never
substitutes Ask Agent's helper-managed extra worktree, which is not compatible
with this bound child. Do not guess a sibling checkout or use an older installed
wrapper. This section adds only what ShipLoop's bound child needs beyond that
card. This route is a Codex native pilot;
old helper-managed host results do not qualify this composition on Claude, Grok
or another host. Check actual capabilities and retain honest host-specific
evidence before making those claims.

### Select and retain the native owner

The `improve-agent` card owns the host capability check and the worker's
capabilities: one general-purpose worker with a regular coding agent's tools,
skills and the task's existing authorization, inheriting model settings unless
the user selected otherwise. A restricted reviewer that cannot apply fixes is
not an equivalent executor. If the host filters a needed capability, disclose
the specific gap and coordinate the authorized operation through the parent.
The parent-only ShipLoop control callbacks and workspace return below are
ownership boundaries, not a blanket prohibition on deployment or tool use.
The worker runs `/improve` inline and starts no reviewer, test-runner or
executor agent unless the user asked for independent review.

Prefer native background execution where supported, keeping the parent alive
to collect the return. A synchronous native fresh worker can isolate context
too; disclose that the parent cannot keep working during its call. If no usable
fresh route exists, disclose the limitation and use the existing same-context
Improve route only when separate context was not explicitly required. Otherwise
keep the action pending and report the missing capability. Do not shell-launch
models, invent an API, or silently use an inherited conversation. To make
same-context execution the normal route for later assignments, switch the run
to `delegation: inline`; the switch applies from the next issued action.

An existing bound parent packet or named source/evidence locator is an input:
verify that it exists and identifies the intended candidate and content before
relying on it, while keeping its essential meaning inline in the binding. The
printed **Child latest packet receipt** and completion-evidence locations are
output destinations for a genuinely new child; they need not exist before start
and must not be fabricated. Before dispatch, derive `host-owner.md` beside the
expected `packet.json` location in the same action directory and retain its
exact absolute locator with the existing ShipLoop recovery command in host-owned
durable handoff material. Create an append-only launch-intent entry before
dispatch containing the exact binding marker, Child workspace, packet receipt,
timestamp, package identities and parent recovery command. Also record the
initial HEAD, candidate inventory, inherited staged/unstaged/untracked ownership
and allowed writes. That entry means *possibly launched*, not not-launched:
interruption between the native launch and recording its returned handle leaves
ownership unknown. On recovery, the saved child receipt is required input and is
read with its sibling `host-owner.md` before work resumes.

Append the returned native job/thread handle, any host-exposed delegate identity,
and later collection or stopped evidence without replacing earlier entries. The
absence of a returned handle is never proof that launch did not happen. Keep the
raw child packet as exact runtime JSON; `host-owner.md` is a host coordination
record, not another runtime state machine, graph field, or success receipt.
Never change `state.md` to track the agent; its run-level `delegation` value is
run configuration, not an owner record. Announce the assignment and current
parent/child boundary.

### Supply the worker and forward decisions

Compose the assignment with the `improve-agent` card. For this bound child its
binding also carries the Child workspace's canonical Git root, the binding
marker, the exact frozen candidate/base and HEAD, scope and exclusions,
inherited staged/unstaged/untracked ownership, the selected absolute Ask Agent
and Improve cards with their runtime identities, the current producer result,
relevant work-item context and actual stage checks, explicit user/repository
authority including any no-commit override, the expected packet receipt and
completion-evidence paths, the exact `host-owner.md` locator, the exact parent
return instruction, and the cleanup owner. Keep these facts inline with
supporting locators; read full values at an existing input locator before
freezing the child contract. Include the host-owner locator in the frozen child
`context.resources` as parent coordination data; the worker may inspect it for
recovery orientation but does not update it or use it as authority to select a
parent transition. The consumer-owned route does not call helper `prepare`,
`inspect`, `check-context` or `close` for this workspace, invent a helper
receipt, or perform a second patch/commit transfer; read-only package `identity`
remains available. Route selection belongs to the parent, not Improve.
The packet's ShipLoop callbacks and workspace-return commands are **parent-only**.
Do not ask the worker to read the entire parent conversation or run another
ShipLoop instance. It may start the bound Until Loop once for a genuinely new
child; resume an existing child using its saved receipt, never by replacement.

When a relevant main-context decision changes, the parent appends its source,
action/target, conditions and forwarding status to `host-owner.md`, then forwards
the update through the native channel to the current worker. The worker honors
the latest applicable user instruction and records receipt, its effect and any
already-performed action in the existing review notes and replacement handoff.
The launch context stays immutable; do not rewrite it or restart the runtime to
carry a new approval or decline. On recovery, reconcile the launch authority with
these later source-bound decisions before dependent work resumes. If delivery or
an external outcome is unknown, resolve it before further dependent effects or
acceptance; a parent log entry alone does not prove the worker received it.
For a revocation, obtain worker acknowledgement before treating it as applied;
use native interruption if needed while receipt is unknown. Record a possibly
started operation as possibly performed and reconcile its actual outcome.
The owner record remains coordination evidence, never callback authority. A
decision arriving after completion cannot retroactively change the saved receipt.

### Worker execution and return

The worker runs `/improve` using the selected absolute Improve card once inside
its native context and follows that card and its bound runtime. It saves each
exact raw packet, must not recursively delegate the whole Improve invocation,
and starts no reviewer, test-runner or executor agent unless the user asked for
independent review. It returns the completion contents listed above without
executing a ShipLoop callback or workspace return; the parent collects that
native return before acceptance.

### Delegated recovery

After interruption, recover the parent with its saved `next` command, read the
reprinted child receipt locator, then derive and read its sibling `host-owner.md`
before assigning another writer. A launch-intent, partial record, missing returned
handle, or unknown collection outcome is *possibly launched* and blocks
replacement; it is never evidence that the original worker did not start. Use
the recorded host handle to collect the old worker or obtain host-specific proof
that it never launched or has stopped. Preserve every earlier handle and stop
evidence when appending that outcome. If it is still running, collect or confirm
it stopped; an unknown job status is not permission to spawn a replacement.
A missing owner record on recovery is also unknown ownership. Only a positively
known new binding in the continuing parent, with no prior dispatch, can acquire
its first owner. Do not label a recovered binding new because its files are absent.

Once sole ownership is established, recover the same parent with `next` and the
same child from its saved packet. For an active child use its exact `next_argv`;
for a complete child validate and import without rerunning Improve. Missing
active-child ephemeral state or a lost terminal packet is incomplete, never success or
permission to start over. A resumed host may recover the same invocation in a
fresh worker only after the old owner is confirmed stopped or never launched. No
automatic return is promised after the parent session ends.
