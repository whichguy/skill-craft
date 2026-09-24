---
name: improve
description: >-
  Use when a repository candidate needs a deliberate review-and-improvement
  loop: use recent Git history, make warranted changes, run meaningful checks,
  and require two consecutive trivial-only review passes. Supports a read-only
  interpretation preview; not a one-off code review.
version: 0.3.0-rc.3
license: MIT
platforms:
  - linux
  - macos
metadata:
  short-description: Review and improve until two clean passes
  skill_craft:
    kind: script-backed
---

# improve

Use the shared [Improve review policy](references/review-policy.md) to turn
“improve these changes” into a bounded review-and-improvement contract. This
standalone card binds that reusable policy to Until Loop's single-file callback
runtime. It does not create a second state machine or invoke `/goal`.

Read the shared policy in full before interpreting or executing this skill. It
defines the reusable review-cycle obligations. The sections below supply this
standalone consumer's binding, preview behavior, and callback evidence.

Improve is an execution-capable coding agent, not an audit-only role. Within the
selected entrypoint's task and authority, use the available tools, MCP
interactions and skills to investigate, produce or revise code, tests, documents
and configuration, and perform authorized deployments or other operations.
Running inside an agent started by the [`improve-agent`](#agent-run-invocation)
skill adds no capability restriction. Carry existing authorization forward and
disclose actual host capability gaps. Parent-only control callbacks remain with
their owner.

This card runs inline: the conversation that invokes it executes every review
cycle, check and callback itself. It never hands the invocation, a review or a
check run to another agent unless an independent review is explicitly requested
(see [Agents and independent review](#standalone-owner-binding)). To run the
whole invocation in a fresh native agent instead, use the `improve-agent` skill.

Use your judgment to find worthwhile improvements, including consequential
issues the initiating context did not anticipate. Suggested fixes are starting
points, not an exhaustive checklist or a ceiling on review depth or change size.
Choose the investigation and implementation needed for the candidate; preserve
the actual scope and accepted requirements. Complete meaningful checks, commit
authorized changed files according to the binding, and continue after material
changes until the selected loop's completion condition is met.

For the standalone entrypoint, this package bundles its Until Loop runtime at
[runtime/until-loop/ADAPTER.md](runtime/until-loop/ADAPTER.md). Resolve symlinks
to this card's physical directory before resolving relative links. Read that
bound card in full and follow its current adapter. The package-relative binding
is authoritative: do not substitute a separately installed runtime, an older
card, or an ambient same-named skill.

## Installed package binding

Start with the absolute path of the **selected, loaded** `SKILL.md` supplied by
the host. If the host exposes a selected skill-root alias, expand that alias
first. Keep that logical `SKILL_ROOT` as the host's selected identity; it is not
the target repository cwd, an author checkout, `PATH`, a same-named skill, or a
guessed cache. Claude Code may render `${CLAUDE_SKILL_DIR}` in card text where
supported, but it is not a portable shell environment variable.

```sh
# Replace this illustrative path with the selected absolute location before running.
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
RUNTIME_SCRIPT="$SKILL_ROOT/runtime/until-loop/scripts/until_loop_ephemeral.py"
```

The exact package-relative script locator for a standalone run is
`runtime/until-loop/scripts/until_loop_ephemeral.py`. The bound adapter is the
only CLI caller: it translates natural-language intent into its internal
contract, starts or resumes the selected run, and consumes the exact callback
it returns. Do not make the user supply JSON or fixed runtime arguments. A
skill-directory or marketplace installation must keep this entire package tree
together; the nested runtime is an internal dependency, not a second standalone
parent.

Standalone runs use that per-run temporary callback state. Do not replace
`RUNTIME_SCRIPT` with an ambient Until Loop installation. If Python, the
bundled file, or a repository prerequisite is missing, report that condition
rather than silently changing runtimes.

## ShipLoop whole-skill subcall

When a ShipLoop v3 or v4 packet names a selected actual Improve card and prints a
`ShipLoop standalone Improve binding: <binding-id>` marker, this is a
**standalone whole-skill subcall**. Read and run this card's standalone owner
binding with this card's bound Until Loop runtime. Preserve the exact binding
marker in the child `context.request`. The ShipLoop packet supplies the bounded
candidate scope, permitted paths, current producer result, relevant work-item
`context`, evidence/reference locators, return route, and authority constraints;
retain those as frozen child-contract constraints rather than inventing an
alternate ShipLoop review protocol.

Treat a parent-provided candidate inventory as scope separately from Git
history. Retain every named included path, including relevant untracked product
or requirements artifacts, when the initial commit is empty or `HEAD` does not
move. Keep explicitly excluded scratch or pre-existing user paths outside that
candidate. When the inventory is large, retain one exact inventory locator
rather than recopying every path into each review record.

The child `context.resources` must retain the parent latest-packet receipt
location, the exact parent return instruction or callback locator, and the
printed host receipt path for the child response. These locators make a terminal
child packet sufficient for a fresh host to save its exact response at the
required receipt path and then return through the parent route. Do not infer a
different route from a remembered parent state.

The ShipLoop child follows the standalone binding's ordinary commit policy: after
required checks pass, commit authorized scoped changes in the bound candidate
worktree and retain the commit SHA in its handoff. Stage only intended paths;
never include runtime receipts or unrelated inherited staging. An explicit
user- or repository-authorized no-commit override, including a frozen override
from an existing invocation, remains binding. Commit authority does not grant
merge, push, parent callback, or broader scope authority. Improve owns its review iterations and
temporary Until Loop handle; ShipLoop keeps the parent graph action pending and
imports accepted child evidence once. Reopen only relevant parent locators for
cold recovery, and retain concise current decision/revalidation locators in the
child handoff. Do not use an ambient Until Loop runtime for this ShipLoop route.

For an `active` or `blocked` child response, do not call a parent callback.
Follow the child packet or report its incomplete state through the recorded
recovery route. For `stopped`, preserve the exact terminal packet and evidence
and return their locators. Only when a ShipLoop v4 packet explicitly prints its
parent-only stopped-child reconciliation callback may the parent, after
collecting or confirming the worker stopped, use that exact callback. The worker
never executes it; no other stopped child advances the parent. After a successful
`complete` response is saved exactly at the printed host receipt path, the parent
may use its exact normal return route.

## Agent-run invocation

This card never dispatches itself. The `improve-agent` skill starts one fresh
native agent and has it run this card there; its card owns that dispatch, the
assignment layout, the worker contract and the parent's verification. A native
assignment marked `execution_role: improve-executor` and
`delegation_owner: parent` is such an agent: follow the worker contract its
assignment carries, composed from the `improve-agent` card, and run this card
inside that agent exactly as a direct inline invocation, in the assignment's
workspace and under its frozen authority. Do not dispatch the invocation again.

## Standalone owner binding

For every standalone cycle, read and apply the
[decision rationale and learning guidance](references/callback-evidence.md#decision-rationale-and-learning)
while reviewing, planning, and recording. It combines detailed influences and
original learnings with selective references to prior commits in one account.

- **History window:** at the start of every active callback, read the last
  seven reachable Git commit messages in full (IDs, subjects, and bodies), or
  all available messages if fewer exist. Re-read the window for every distinct
  review and retain useful prior lessons in that review's host record. History
  is evidence of prior intent, not the current diff range, current truth, or
  permission to undo a change.
- **Scope:** retain any named branch range, candidate inventory/files, or
  baseline. A named candidate inventory controls scope separately from Git
  history: its included paths remain in scope, including relevant untracked
  product or requirements artifacts when the initial commit is empty or `HEAD`
  does not move; its explicit scratch or pre-existing-user exclusions remain
  outside scope. When that inventory is long, retain one exact inventory
  locator instead of recopying the whole list in every cycle. Otherwise freeze
  the initial Git HEAD and review the initial staged, unstaged, and relevant
  untracked changes together with this run's later edits. If no more specific
  candidate is supplied and the worktree is clean, use the latest commit's
  change as a disclosed default. Inspect adjacent consumers only as needed to
  assess the candidate. In an unborn repository, disclose that history is
  absent; execution that requires commits remains incomplete until that
  constraint is resolved.
- **Trivial classification:** classify impact semantically. Trivial work is
  non-semantic spelling, formatting, or explanatory polish with evidence that
  behavior is unchanged. A one-line bug fix, public-contract change,
  security/data-integrity correction, or missing required regression coverage
  is material. Uncertain impact remains unresolved until investigated.
- **Agents and independent review:** this binding does not select independent
  review by default. Perform every review, check and commit in this
  conversation; start no reviewer, test-runner or executor agent, and record
  each review as `self-review (inline default)`. Select a fresh read-only
  independent reviewer only when the user or the invoking parent explicitly
  asks for independent review; freeze that request in `context.authority` and
  apply the shared policy's independent-review rules to it. A host's standing
  permission or preference to start agents does not select one here.
- **Evidence location:** retain each review in the host-visible task record:
  the candidate identity and ownership-aware scope, seven-message history read,
  findings, plan or no-change reason, actual changes, commands and results,
  lessons, and commit receipt when required. For each substantive cycle, retain
  concrete locators for material actually read and whether it was the inline
  self-review or a requested independent review (and, if a requested reviewer
  was unavailable, the disclosed limitation). Repeated templated wording is an
  audit cue only: neither equal nor unequal bytes prove an independent review.
  Before `done`, summarize those observations truthfully in its concise
  `evidence` field and retain complete continuation facts in `handoff`, as
  described in [callback evidence](references/callback-evidence.md). The
  script retains only its current contract, latest report, and trivial-review
  counter; it cannot turn a callback claim into proof.
- **Commit policy:** after required checks pass, commit authorized scoped files
  changed by a completed iteration with the required learning-oriented record.
  Its body must include Review, Plan, Changes, Validation, Key learnings, and
  Remaining work, including the classification and resulting streak. Explain
  the consequential influences, how they shaped decisions, and what was newly
  learned within those sections. Cite prior commits when they materially
  informed a decision; explain original learnings fully when none did. A
  no-change review gets an honest host record, not a manufactured edit or empty
  commit. An explicit audit-commit-every-iteration request requires one
  authorized audit record commit for every completed review; a no-change review
  uses an identified empty audit commit with no unrelated staged content. An
  explicit no-commit request preserves the host record without committing.
  Use a scoped commit such as `git commit --only -- <authorized paths>` so
  unrelated inherited staging is excluded; narrowly add selected new paths
  first when required. Never reset the user's index or absorb unrelated work.
  In a dirty snapshot, a selected file may include inherited caller hunks: its
  private checkpoint SHA is not a pure contribution range. Deliver only the
  baseline-relative delta through the parent's declared return route.
- **One callback is one full cycle:** for every active packet, complete one
  ordered review cycle before the exact `done_argv`: read the history and
  candidate, plan worthwhile authorized work, implement it when warranted, run
  applicable meaningful checks, retain the record, and make any authorized
  commit. An empty plan is valid only after that substantive review finds no
  worthwhile change. A callback, retry, diagnostic command, or repeated test
  is not another review. Do not privately perform several reviews before one
  callback.
- **Assessment and finalization:** after that full cycle, call the returned
  `done_argv` with a truthful classification: `trivial` only for a distinct
  complete trivial/no-change review with current applicable checks;
  `non-trivial` for a material finding or behavior change, even if fixed; and
  `unresolved` if work, evidence, required commit, or assessment is incomplete.
  Report the substantive exit assessment and whether continuation is allowed,
  blocked, or cancelled. The configured gate is two consecutive qualifying
  trivial reviews; a material or unresolved report resets it. Only the runtime
  can accept a terminal transition. A blocker, requested stop, exhausted
  budget, failed required commit, stale check, or unresolved evidence remains
  incomplete rather than satisfying the review policy.

Runs are ephemeral across an abandoned host session: the per-run file
survives only while it exists and is deleted at a terminal transition. Separate
run files permit separate callbacks, but they do not coordinate edits, tests,
or Git commits in one checkout. Use separate worktrees or otherwise coordinate
that shared project work.

## Continue after context loss

Before `start`, freeze the actual initial HEAD/base or named range, the exact
candidate inventory and staged/unstaged/untracked ownership boundaries in
`context.scope`. Keep its named inclusions and exclusions distinct from the
history window; an empty initial commit or unchanged `HEAD` does not select a
new candidate. A later commit or clean worktree does not select a new candidate.
For a long inventory, `context.scope` may cite an exact resource locator instead
of repeating every path.
Before `start`, reconcile every required output locator with the frozen scope
and authority. Preserve any exact output path explicitly authorized by the
invoking assignment, including a completion record outside the product candidate,
as a narrow write exception. Naming a resource alone does not grant write access;
writing a completion record does not authorize callbacks, integration, or delivery.

Put the actual commit/no-commit, push/no-push and audit-commit rules in
`context.authority`. Preserve these record sections and the full ordered cycle
in the contract; reloading a changed card must not replace accepted user rules.
Include inherited approvals, declines and pending decisions with the affected
action or approach, target/scope, conditions and authorization source. Act on
applicable approvals without asking again, honor declines, and never treat a
pending request as consent. These are binding decisions, not optional learning
suggestions; the opening may summarize their practical implications.
For a later source-bound parent update, honor the latest applicable user
instruction and retain the decision, receipt and effect in the existing handoff.
The parent confirms that the update is covered by the frozen work, exit/repeat
conditions and review gate, and coordinates any newly authorized write paths.
Preserve the user's selected automatic-approval mode. This owner coordination
does not require the user to reapprove already authorized actions.
Keep the launch context immutable and continue the same runtime; reconcile it
with received later decisions on recovery. If those loop conditions must change,
return the conflict through the parent's supported route; do not independently
replace the child or carry a qualifying streak across changed criteria.
An unresolved conflict or unknown
delivery/effect blocks the affected operation, not unrelated authorized work.
Name the selected Improve card, bound Until Loop card, review policy and any
required evidence/output locations in `context.resources` with resolved
locators. Record environment-specific Git/Python paths and actual check commands
in `context.environment` when needed. The canonical request goes in
`context.request`.

Retain the parent-supplied **Current context and desired improvements** opening,
including **Current learnings**, once at the start of `context.request`, alongside
the canonical request and any required binding marker.
For a direct invocation, distill the current understanding and relevant learnings
already in context before `start`. Include material unresolved hypotheses and
failed attempts as well as verified conclusions. Use them to inform the first
review and plan, checking candidate-dependent
claims against current artifacts and evidence. Keep facts, decisions and
unverified assumptions distinct; inherited learnings do not establish a completed
review, a passing check, or broader authority. Carry still-relevant learnings
and any corrections into the normal `handoff` below.

Before each `done`, compare the replacement handoff with `context.request` and
the prior `last_report.handoff`. Keep still-applicable corrections, unresolved
hypotheses, and execution pitfalls explicit inline, with evidence locators for
supporting detail. A pointer to a past review does not replace the essential
lesson. If a prior item no longer applies, note that briefly rather than silently
dropping it; put that explanation in the handoff itself. Cross-check any restated
scope or authority against the immutable context: neither add permissions nor
turn authorized scoped work into a prohibition.

Use compact Markdown inside the existing `context.request` and `handoff` strings;
the runtime packet and callback envelope remain JSON. Organize a replacement
handoff under **State and remaining work**, **Current learnings**, and **Evidence**.
In Current learnings, use short labeled bullets for facts/corrections, decisions,
hypotheses, and execution pitfalls. Reconcile each prior learning explicitly:
retain its essential meaning, or include a **Retired** bullet explaining why it
no longer applies. Include expired one-off instructions in that reconciliation.
Omit empty categories. Refer to immutable scope and authority rather than
reconstructing a competing permissions list. Use normal JSON serialization for
the Markdown strings; do not add fields or send bare Markdown as the callback.

Every `done` report must include a complete compact `handoff`: current candidate
HEAD and scoped edits, all still-relevant changes and decisions, actual check
results, commit receipts or why no commit exists, pending issues, and evidence
locators. Copy necessary findings from earlier cycles forward; never assume the
next executor can read earlier conversation. The script's returned progress
remains the authority for the streak, not a model-written number in the handoff.
The task record can still hold detailed output; essential continuity facts belong
in the packet, without introducing another state file or requiring a new log.

Resume from the bound card's latest full return and exact `next_argv`. Recheck
current artifacts and instructions. Preserve the original scope even when this
run already made a commit; do not blindly repeat fixes, commits or callbacks.
If required context or evidence cannot be recovered, report the gap as
unresolved and stop incomplete when it prevents useful authorized progress.

## Completion summary

Include preparing a cumulative summary in the standalone execution contract.
Before each `done`, retain the key implemented changes and still-relevant lessons
from the whole run in the existing `handoff`; the last two no-change reviews must
not reduce that account to “nothing changed.” After the runtime returns
`complete`, return a self-contained summary to the caller; inside an
[agent-run invocation](#agent-run-invocation), return it inline in the native
result:

- **Key implemented changes:** what changed, why it matters, and the relevant
  paths and commit receipts. Distinguish this run's contributions from inherited
  work; say explicitly if no change was warranted.
- **What was learned:** consequential discoveries, corrected assumptions and
  useful failed approaches, with their evidence and applicability limits.
  Distinguish newly learned facts from inherited lessons that were confirmed,
  corrected or retired; keep unresolved hypotheses labeled.
- **Validation and remaining work:** actual checks and review outcome, unresolved
  issues, and the observed commit, integration and deployment state. Name any
  next owner or action without claiming a parent-owned return already happened.

Synthesize from the final handoff and retained evidence across all cycles, not
only the last review. Retain material parent corrections and current
approval/decline implications that affect subsequent work; do not discard them
as orchestration detail. Keep essential conclusions inline and link to supporting
detail; use the space needed to make the result useful without copying the whole
iteration log. Preserve the exact terminal receipt separately. For the ShipLoop
whole-skill subcall, populate the existing completion record's `summary` with the outcome
and key changes, and `lessons` with the learning synthesis. Do not add runtime
fields, reopen a completed loop, or issue another callback to format this report.
A blocked, stopped or interrupted run returns the same useful account labeled
partial, with its blocker or recovery action; it is not completion.

## Preview before execution when requested

“Dry run,” “preview,” “show how you interpret this,” and “do not execute” select
interpretation only when they refer to the improvement workflow; a prohibition
on executing a particular command remains a constraint on that action. Inspect
permitted repository context read-only, derive the shared policy plus this
standalone binding into a natural-language execution, exit, and continuation
contract, and use the bound Until Loop card's preview procedure. Stop after
presenting it. Do not start or resume a run, create a temporary state file or
loop note, edit product files, execute tests/verifiers, stage changes, or create
a commit. If the user forbids all writes, return the interpretation in the
conversation; saving an artifact elsewhere is optional only when permitted. A
preview neither achieves the proposed objective nor authorizes later execution.

For Git inspection during preview, use the documented no-optional-locks,
no-index-refresh, no-external-diff, and no-text-conversion options so status
and working-tree reads do not change the index or invoke configured external
processors. Preserve the distinction between the chosen edit scope and adjacent
files inspected for context.

Show the scope and history window, planned work, continuation and success
rules, incomplete stops, assumptions with their basis, evidence needed for each
rule, and the first action that would be taken. Explain the proposed commit
policy. Label unknown evidence and hypothetical decisions; do not claim tests
or review iterations occurred. An actual execution request must recheck current
context.

## Execution handoff

Preserve the shared policy and every standalone binding above in the interpreted
contract, including conditional commit overrides and negative constraints. The
execution condition must contain the complete ordered review cycle; the exit
condition must include current evidence plus two consecutive qualifying reviews;
and the continuation condition must retain useful authorized work and incomplete
stops. Before start, check that required exit outcomes can be achieved during
execution. If the task requires an authorized deployment or other external
operation, include its result and verification in the exit assessment and
perform it at the appropriate authorized point within the loop. Do not invent a
rule deferring an exit prerequisite until after completion, or replay an
unchanged effect merely for another review. Preserve the actual approval's
conditions and timing instead of adding new approval or review prerequisites.
Then follow the latest returned packet exactly. Execute its full work
before calling `done`; consume the whole result and execute the next returned
instruction while it is active. Do not add a nested plan-convergence loop or
invent a successor, counter, or terminal decision.

The runtime validates action identity and applies reported state transitions,
including the two-review gate. It does not independently verify that a commit
was made, a test ran, or a semantic judgment is correct. The callback evidence
is a concise handoff record, not fabricated proof.
