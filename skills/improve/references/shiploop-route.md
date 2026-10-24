# Improve: the ShipLoop route

Read this core once per context for a ShipLoop review (the argument `ShipLoop Improve: <handoff
path>`) and again after a reset or a compaction. It holds the rules of every pass; with the handoff
(this review's result, `CHILD`, focus and commands) it is all a normal pass needs. Open a
[case file](#cases-read-only-when) only when its condition holds, and only its section. A
standalone `/improve` uses [standalone-route.md](standalone-route.md).

## Binding

ShipLoop is the owner: this core, the handoff and the frozen contract `CHILD/start.json` (work,
exit and repeat conditions, scope, authority, resources; it wins over any copy) bind the
[review policy](review-policy.md). Explicit user and repository constraints bind; history never
widens scope or overrides them.

- **History window.** At the start of every active callback read the last seven reachable Git
  commit messages in full (IDs, subjects, bodies), or all if fewer exist, and re-read them for
  every distinct review; keep the useful lessons in that review's record. History is evidence of
  prior intent, not the diff range, current truth or permission to undo a change.
- **Scope** is `context.scope`: an inventory's paths stay in (untracked ones too, even when `HEAD`
  does not move), its exclusions stay out; without one, the change since the frozen initial HEAD
  plus this run's edits. Inspect adjacent consumers only as far as needed.
- **Trivial classification.** Classify impact semantically. Trivial work is non-semantic
  spelling, formatting or explanatory polish with evidence that behavior is unchanged. A
  one-line bug fix, public-contract change, security or data-integrity correction, or missing
  required regression coverage is material. Uncertain impact remains unresolved until
  investigated.
- **No agents.** Do every review, check and commit here, never clearing or handing off; start no
  reviewer, test-runner or executor agent; record each review as `self-review (inline default)`.
- **One writer.** Only this conversation writes in the exact Child workspace until the receipt
  is final (stop competing writes there); on `Route: inline` it alone submits ShipLoop callbacks.
  Keep `.until-loop`, `.shiploop-improve` and runtime metadata out of the candidate and its
  commits, and temporary files in the handoff's scratch directory. Never read, decode, retain or
  report credential, session or authentication store contents.

## A pass

ShipLoop wrote the contract and started the runtime; the script owns state and transitions. Never
invoke `/goal`, nest a loop, start a second run, or edit or retype the contract. One callback is
one full cycle (steps 2 to 8, which the focus does not replace): a retry, diagnostic or rerun test
is no review; never run several reviews before one callback. Only the runtime decides, from the
contract and Git, whether another pass follows.

1. **Receipt.** Read `CHILD/packet.json`; never write it (the runtime rewrites it at every step).
   `active`: run its `next_argv` once and follow what it returns; `complete` or `stopped`:
   the loop is over. The latest return owns the next action: read its whole `instruction`,
   `work`, conditions, `context` and last `handoff`. Earlier reports, `CHILD/opening.md` and task
   text are claims to check against current artifacts, never proof or permission.
2. **Review** the candidate against the handoff's focus and done-when conditions, its consumers,
   the history and prior evidence (accepted lessons: `state.md` `improve_results`); note locators
   for what you read; investigate uncertain impact before classifying it.
3. **Plan** only worthwhile, authorized work, with its expected behavior and checks. An empty plan
   is valid after a substantive review; invent no cosmetic edits, rewrites or redundant tests.
4. **Apply** it within scope, preserving unrelated user work; recheck earlier work rather than
   reapplying a fix. A material finding or edit makes the pass `non-trivial` even when fixed.
5. **Check** after your last edit: run the applicable checks; refine meaningful tests where the
   stage allows; never weaken an assertion. A failed, stale or unrun check is no evidence. Remove
   an artifact only if this work made it, it is disposable and it holds no user work.
6. **Record** the pass as the handoff's Evidence line says (`CHILD/reviews/review-<n>.md`; after
   an edit, `checks.md` first). ShipLoop derives the outcome, key changes and check state from
   them; lessons for later steps go to `complete --notes`.
7. **Commit** what it changed ([below](#record-commit-and-learning)); a no-change pass makes none.
8. **Finish** with the handoff's `improve-pass`, then run the `done` it prints exactly as printed.
   `active`: report the facts and do the next pass (a passing test or a trivial review does not
   end the loop); `complete`: [return](#return-and-final_result); otherwise
   [recovery](shiploop-route-recovery.md). A blocked or stopped pass still records its partial
   account and its blocker.

Report status in Markdown from returned facts (done, remaining, findings, blockers, user action
needed), with script-reported counts only.

## The review file

Its front matter fills the runtime report; Read, Found, Changed, Checked and Class become
`evidence` (this iteration's observations, checks, changes and remaining gaps, never intended
actions or sample claims; link long output):

- `classification`: `trivial` only for a distinct completed review with only trivial or no
  changes, no material findings and applicable checks; `non-trivial` for behavioral changes or
  material findings, even if fixed in this action; `unresolved` if execution or assessment is
  incomplete. Classify this iteration's actual changes and findings, not line counts or
  earlier edits still in the diff.
- `exit`: `satisfied` only after checking every exit clause on its own, by its literal wording,
  against current artifacts after the last change, each named with its fresh observation; a
  clause not observed is `unknown`; `unresolved` cannot assert `satisfied`.
- `continuation`: `allowed`, `blocked` (name the blocker) or `cancelled` (a triggered
  user-prescribed stop).
- `## Handoff`: a compact summary replacing the previous one (HEAD and scoped edits, live
  decisions, check commands and results, commits or why none, open issues, locators) under
  **State and remaining work**, **Current learnings** (facts, decisions, hypotheses, pitfalls; a
  dropped one marked **Retired** with its reason) and **Evidence**. Copy findings forward; keep
  the run's key changes and lessons, never just "nothing changed".

Never fabricate a record to submit `trivial`: an incomplete pass is `unresolved`, its exit
`unknown` or `unsatisfied`, its gap named.

## Record, commit and learning

Commit only with the handoff's `improve-commit` (or `improve-pass`, same message file): never
`git commit` or a heredoc, never runtime receipts or unrelated staged work. The message rules are
in the handoff (plan stage: `CHILD/parent-return.md`). Make the record substantive: each
consequential decision with the influence behind it and a locator, the alternatives, observed
versus inferred, failed approaches; cite a commit (`Learned-from:`) only if you read it and it
helped ([full text](callback-evidence.md#decision-rationale-and-learning)). An audit-commit or
no-commit request, or a dirty snapshot: [long form](shiploop-route-rules.md#record-commit-and-learning).
Every rule here has a [long form](shiploop-route-rules.md), only for a question a rule here leaves.

## Return and `final_result`

Inline, run the handoff's callback (`complete`) only after the runtime returned `complete` and
wrote it to the receipt (ask-agent: the parent, after collecting the worker's result); if
incomplete, retain the child and do not call it. A refusal's first line is the fix. Omit
`final_result` when the step result is unchanged; if this review changed a decision or
decision-relevant evidence a successor needs, read [its rules](shiploop-route-cases.md#a-final_result).

## Review inputs

Reopen and revalidate only the parent-supplied sources this candidate needs; keep their locators,
not copies. Per the handoff's Maintained requirements and Reference handoff policies, review material
subclauses, not feature names; code, a passing test or a draft never redefines accepted intent;
keep verification gaps visible. A planning review (step-plan, test-spec) changes no product code
and needs no future check to pass; a release or verification review reconciles an uncertain
outcome, never replays it.

## Cases: read only when

- [Recovery](shiploop-route-recovery.md): an `error`, `stopped` or `blocked` return; a missing or
  damaged receipt or state; a pass an interruption may have left half done; a stopped child to
  pause, restart or reconcile. After a plain compaction, step 1 is the recovery.
- [Ask-agent route](shiploop-route-ask-agent.md): the handoff says `Route: ask-agent`.
- [Review inputs](shiploop-review-inputs.md), the matching section only: a planning result; tests
  or test evidence; interactions, events or UI; current-system recovery; a repository-local skill;
  identity or access discovery; quality criteria or baseline evidence.
- [Cases of a pass](shiploop-route-cases.md), the matching section only: a requested independent
  reviewer; a user approval, decline or later decision, a write outside the candidate or changed
  loop conditions; an external operation or conflicting requirements; a `verify_script`; a
  `final_result`.
- The handoff's `Improve context ownership:` line: recovery, a restart or a dispatch only.
