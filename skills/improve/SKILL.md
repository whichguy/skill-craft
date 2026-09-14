---
name: improve
description: >-
  Use when a repository candidate needs a deliberate review-and-improvement
  loop: use recent Git history, make warranted changes, run meaningful checks,
  and require two consecutive trivial-only review passes. Supports a read-only
  interpretation preview; not a one-off code review.
version: 0.1.0-rc.1
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
standalone card binds that reusable policy to until-loop; it does not create a
second state machine or invoke /goal.

Read the shared policy in full before interpreting or executing this skill. It
defines the reusable review-cycle obligations. The sections below supply only
this standalone consumer's binding, preview behavior, and adapter handoff.

This package bundles its Until Loop runtime at
[runtime/until-loop/ADAPTER.md](runtime/until-loop/ADAPTER.md). Resolve symlinks to
this card's physical directory before resolving relative links. Read that bound
card in full and follow its adapter. The package-relative binding is
authoritative: do not substitute a separately installed runtime, an older card,
or a runtime that lacks the requested preview behavior.

That bound card is the only CLI caller. Pass the following intent as natural
language, retaining the user's exact request and any more specific constraints.
Do not make the user supply internal arguments or JSON. A skill-directory or
marketplace installation must keep this entire package tree together; the
nested runtime is an internal dependency, not a second standalone parent.

## Owner-managed consumer entrypoint

An owner-managed consumer must read
[the shared review policy](references/review-policy.md) and that owner's
explicit binding in full. It must not run this standalone card or this card's
until-loop adapter. The other owner supplies its own history window, scope,
classification rule, evidence location, commit policy, phase/callback, and
finalization authority.

## Standalone owner binding

- **History window:** at the start of every completed review cycle, read the
  last seven reachable Git commit messages in full (IDs, subjects, and bodies);
  read all available messages if fewer exist. Re-read that window each cycle
  and retain useful prior lessons in the review record. History is evidence of
  prior intent, not the current diff range, current truth, or permission to
  undo a change.
- **Scope:** retain any named branch range, files, or baseline. Otherwise freeze
  the initial Git HEAD and review the initial staged, unstaged, and relevant
  untracked changes together with this run's later edits. If clean, use the
  latest commit's change as a disclosed default unless context establishes a
  more specific candidate. Inspect adjacent consumers only as needed to assess
  the candidate. In an unborn repository, disclose that history is absent;
  execution that requires commits remains incomplete until that constraint is
  resolved.
- **Trivial classification:** classify impact semantically. Trivial work is
  non-semantic spelling, formatting, or explanatory polish with evidence that
  behavior is unchanged. A one-line bug fix, public-contract change,
  security/data-integrity correction, or missing required regression coverage
  is material. Uncertain impact remains unresolved until investigated.
- **Evidence location:** retain the policy-required record for each distinct
  review in until-loop's checked .until-loop/working.md. Treat it as
  candidate-bound evidence to recheck, not a runtime-enforced streak counter.
  Follow [factual evidence capture](references/evidence-capture.md): use the
  bundled collector to retain candidate/history facts before review and check
  references before assessment. Read the captured full messages, label reviewer
  identity and check claims honestly, and keep semantic judgments in the review
  record. Report and investigate collection failures without inventing evidence.
- **Commit policy:** after required checks pass, commit authorized scoped files
  changed by a completed iteration with the required learning-oriented record.
  Its body must include Review, Plan, Changes, Validation, Key learnings, and
  Remaining work, including the classification and resulting streak.
  A no-change review gets a durable note, not a manufactured edit or empty
  commit. An explicit audit-commit-every-iteration request requires one
  authorized audit record commit for every completed review; a no-change review
  uses an identified empty audit commit with no unrelated staged content. An
  explicit no-commit request preserves the records without committing. Never
  reset the user's index or absorb unrelated staged or unstaged work.
- **Phase and callback:** the until-loop adapter owns the current packet,
  retries, and legal phase transitions. Complete only the packet's assigned
  phase and return its evidence-based assessment through that adapter; do not
  treat a callback, retry, or verification run as another review.
- **Finalization:** only the adapter may accept completion of the whole bound
  contract. A blocker, requested stop, exhausted budget, failed required
  commit, stale check, or unresolved evidence remains incomplete rather than
  satisfying the review policy.

## Preview before execution when requested

“Dry run,” “preview,” “show how you interpret this,” and “do not execute” select
interpretation only when they refer to the improvement workflow; a prohibition
on executing a particular command remains a constraint on that action. Inspect
permitted repository context read-only, derive the shared policy plus this
standalone binding into the proposed execution contract, and use until-loop's
preview procedure. Stop after presenting it. Do not initialize or resume a
run, write loop notes, edit product files, execute tests/verifiers, stage
changes, or create a commit. If the user forbids all writes, send serialized
input through preview's stdin path and return the output in the conversation.
Saving an artifact elsewhere is optional only when permitted. A preview neither
achieves the proposed objective nor authorizes later execution.

For Git inspection during preview, use the documented no-optional-locks,
no-index-refresh, no-external-diff, and no-text-conversion options so status
and working-tree reads do not change the index or invoke configured external
processors. Preserve the distinction between the chosen edit scope and
adjacent files inspected for context.

Show the scope and history window, planned work, continuation and success
rules, incomplete stops, assumptions with their basis, evidence needed for
each rule, and the first action that would be taken. Explain the proposed
commit policy. Label unknown evidence and hypothetical decisions; do not claim
tests or review iterations occurred. An actual execution request must recheck
current context.

## Execution handoff

Preserve the shared policy and every standalone binding above in the interpreted
contract, including conditional commit overrides and negative constraints. Then
follow until-loop's current packet and submit its evidence-based assessments.
Its generic runtime does not independently count this parent's review streak
or verify the truthfulness of commit/review claims. The frozen contract carries
these obligations to a fresh context. Do not add a nested plan-convergence loop
unless the user explicitly requests one. Stop only when the adapter accepts
completion of the whole contract, or report its actual incomplete state and
next condition.
