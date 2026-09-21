---
name: improve
description: >-
  Use when a repository candidate needs a deliberate review-and-improvement
  loop: use recent Git history, make warranted changes, run meaningful checks,
  and require two consecutive trivial-only review passes. Supports a read-only
  interpretation preview; not a one-off code review.
version: 0.2.0-rc.5
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
standalone consumer's binding, preview behavior, callback evidence, and legacy
continuation boundary.

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

The exact package-relative script locator for a new standalone run is
`runtime/until-loop/scripts/until_loop_ephemeral.py`. The bound adapter is the
only CLI caller: it translates natural-language intent into its internal
contract, starts or resumes the selected run, and consumes the exact callback
it returns. Do not make the user supply JSON or fixed runtime arguments. A
skill-directory or marketplace installation must keep this entire package tree
together; the nested runtime is an internal dependency, not a second standalone
parent.

New standalone runs use that per-run temporary callback state. They must not
call `scripts/capture_evidence.py`, create `.until-loop/working.md`, or use the
durable v1/v2 adapters. Those retained files apply only to an explicitly
selected legacy run under [the legacy standalone binding](references/legacy-standalone.md).
Do not replace `RUNTIME_SCRIPT` with an ambient Until Loop installation or call
`managed_controller.py` as a standalone runtime. If Python, the bundled file,
or a repository prerequisite is missing, report that condition rather than
silently changing runtimes.

## ShipLoop v3 whole-skill subcall

When a ShipLoop v3 packet names a selected actual Improve card and prints a
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
different route from a durable `.until-loop` directory or from a remembered
parent state.

The v3 default no-commit constraint overrides the standalone binding's ordinary
commit policy: retain review records and validation evidence, but do not commit,
merge, push, or broaden the parent scope unless the packet supplies an explicit
user- or repository-authorized exception. Improve owns its review iterations and
temporary Until Loop handle; ShipLoop keeps the parent graph action pending and
imports accepted child evidence once. Reopen only relevant parent locators for
cold recovery, and retain concise current decision/revalidation locators in the
child handoff. Do not use `managed_controller.py`, a `managed-improve` callback,
or an ambient Until Loop runtime for this v3 route.

For an `active`, `blocked`, or `stopped` child response, do not call a parent
callback. Follow the child packet or report its incomplete state through the
recorded recovery route. Only after a successful `complete` child response is
saved exactly at the printed host receipt path may the host use the exact parent
return route.

For a native assignment marked `execution_role: improve-executor` and
`delegation_owner: parent`, execute this entire bound loop in the exact Child
workspace. The parent selects the Ask Agent route; this card does not dispatch
itself. Do not delegate the whole invocation again, create another worktree, or
execute a ShipLoop callback or workspace return. Scoped independent reviewers
and test workers remain available with only one candidate writer. Retain the
explicit no-commit override and the parent-owned `host-owner.md` locator in the
frozen context. Read that record for orientation; only the parent appends owner,
acceptance and delivery events. Save the exact child packets and completion
evidence, finish all writes and collect delegates, then return their absolute
locators, changed paths, actual checks, stopped status, and the unchanged parent
continuation. Only the parent verifies and executes that continuation. Edits
remain in the bound candidate; native completion is not caller delivery.

This executor assignment applies only to the explicit ShipLoop v3 whole-skill
subcall. Standalone dispatch, other owner-managed entrypoints, and active legacy
invocations retain their existing ownership and commit policies.

## Other owner-managed consumer entrypoint

An owner-managed consumer other than the explicit ShipLoop v3 whole-skill
subcall above must read [the shared review policy](references/review-policy.md)
and that owner's explicit binding in full. It must not run this standalone card
or this card's Until Loop adapter. The other owner supplies its own history
window, scope, classification rule, evidence location, commit policy,
phase/callback, and finalization authority.

## ShipLoop managed-subrun entrypoint

[ShipLoop's managed consumer binding](references/managed-consumer.md) is a
separate consumer of the same shared policy. It applies only when a ShipLoop
run has selected the versioned managed Improve protocol and printed a
`managed-improve` packet. It does not replace the standalone owner binding
for a v3 whole-skill subcall above or change an existing ShipLoop run that lacks
that protocol marker.

Read the managed-consumer binding and the parent-supplied child packet in full.
The managed controller owns the child phase sequence, its completed review
records, material reset, and two-consecutive-trivial assessment. ShipLoop owns
the parent action, delivery DAG, run lock, Markdown transaction, and consumer
release. While the child is active, do not invoke the standalone card or its
bundled Until Loop adapter, create an ambient `.until-loop` directory, call a
legacy per-phase ShipLoop callback, or start another Improve invocation to
improve the child's own plan.

The parent action remains fixed at `managed-improve` while the child progresses
in its namespaced Markdown records. Follow only the printed child continuation
or import route. A terminal child status of `blocked`, `needs-prerequisite`,
`needs-replan`, or `stopped` is incomplete; it keeps the parent action and
binding for recovery. Only a current, validated `converged` certificate can
release the parent to its stated return stage.

The managed binding must state the child action ID, profile, frozen
candidate/context inputs, scope, history, policy/executor digests, checks,
explicit `audit-every-iteration` commit policy, evidence/certificate
requirements, independent-review rule, and parent return conditions. The shared
policy asks for an independent reviewer when available. If this binding makes
independent review mandatory, it must explicitly say whether a recorded
self-review fallback is allowed; absent that authorization, unavailable
independent review blocks the child. The controller must never infer a fallback
from availability or a desire to finish.

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
- **Evidence location:** retain each review in the host-visible task record:
  the candidate identity and ownership-aware scope, seven-message history read,
  findings, plan or no-change reason, actual changes, commands and results,
  lessons, and commit receipt when required. For each substantive cycle, retain
  concrete locators for material actually read and whether an independent
  reviewer was used or, if unavailable, the permitted self-review fallback and
  its rationale. Repeated templated wording is an audit cue only: neither equal
  nor unequal bytes prove an independent review. Before `done`, summarize those
  observations truthfully in its concise `evidence` field and retain complete
  continuation facts in `handoff`, as described in
  [callback evidence](references/callback-evidence.md). New runs must not call
  `scripts/capture_evidence.py`, create `.until-loop/working.md`, or create
  `.until-loop/evidence/`. The script retains only its current contract,
  latest report, and trivial-review counter; it cannot turn a callback claim
  into proof.
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
  Never reset the user's index or absorb unrelated staged or unstaged work.
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

New runs are ephemeral across an abandoned host session: the per-run file
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
Put the actual commit/no-commit, push/no-push and audit-commit rules in
`context.authority`. Preserve these record sections and the full ordered cycle
in the contract; reloading a changed card must not replace accepted user rules.
Name the selected Improve card, bound Until Loop card, review policy and any
required evidence/output locations in `context.resources` with resolved
locators. Record environment-specific Git/Python paths and actual check commands
in `context.environment` when needed. The canonical request goes in
`context.request`.

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

## Execution handoff and legacy continuation

Preserve the shared policy and every standalone binding above in the interpreted
contract, including conditional commit overrides and negative constraints. The
execution condition must contain the complete ordered review cycle; the exit
condition must include current evidence plus two consecutive qualifying reviews;
and the continuation condition must retain useful authorized work and incomplete
stops. Then follow the latest returned packet exactly. Execute its full work
before calling `done`; consume the whole result and execute the next returned
instruction while it is active. Do not add a nested plan-convergence loop or
invent a successor, counter, or terminal decision.

The runtime validates action identity and applies reported state transitions,
including the two-review gate. It does not independently verify that a commit
was made, a test ran, or a semantic judgment is correct. The callback evidence
is a concise handoff record, not fabricated proof.

An explicit continuation of a pre-existing version-1 or version-2 Improve run
uses [the legacy standalone binding](references/legacy-standalone.md) and the
matching legacy Until Loop adapter. Do not discover old state and silently use
it for a new Improve request, and do not migrate a legacy run into a new
temporary callback file.
