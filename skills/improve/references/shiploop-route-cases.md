# Improve: ShipLoop cases of a pass

Each section is one case [the core](shiploop-route.md#cases-read-only-when) names. Read a section only when its case holds for this pass; a normal pass reads none of them.

## Independent review

Read when the user or the invoking parent explicitly asked for an independent reviewer.

- **Agents and independent review.** None by default: perform every review, check and commit in
  this conversation, start no reviewer, test-runner or executor agent, and record each review as
  `self-review (inline default)`. Select a fresh read-only independent reviewer only when the
  user or the invoking parent explicitly asks (freeze that in `context.authority`); a host's
  standing permission to start agents does not. Give it the scope, artifacts, evidence and
  criteria without saying the desired result is trivial, and triage its suggestions like any
  finding: accept one only on a failure, a violated requirement or a concrete in-scope benefit,
  and record the basis. If a requested reviewer is unavailable, disclose the limitation and the
  fallback rationale. Repeated or templated review text is an audit cue, not proof either way:
  matching or different bytes, hashes or wording establish neither independent nor substantive
  review, and no hash gate, counter or schema judges review quality. One Git check differs in
  kind: it asks whether the review changed anything, not whether it was good.

## Later decisions and frozen context

Read when a user decision arrives during the review, a write outside the product candidate is needed, an inherited approval or decline applies, or the loop conditions must change.

- **Frozen context and later decisions.** ShipLoop froze `context.scope`, `context.authority`
  (the commit or no-commit, push and audit-commit rules; a reloaded card never replaces them),
  the environment and the resources. Preserve an exact output path the invoking assignment
  authorized (a review or check file outside the product candidate) as a narrow write exception:
  naming a resource grants no write access, and writing a review or check file authorizes no
  callback, integration or delivery. Inherited approvals, declines and pending decisions name
  the action, target, conditions and source: act on an applicable approval without asking again,
  honor a decline, treat a pending request as no consent. For a later source-bound user update,
  honor the latest applicable instruction and record decision, receipt and effect in the handoff;
  the parent confirms the frozen work, conditions and review gate still cover it and coordinates
  any new write path. Keep the user's automatic-approval mode. The launch context stays
  immutable and the same runtime continues. If the loop conditions must change, return the
  conflict through the parent's route; do not cancel and replace the child, carry a
  qualifying streak across changed criteria, or fabricate a restart, callback or
  completion. An unresolved conflict or unknown effect blocks the affected operation, not
  unrelated authorized work. An authority update is not itself a qualifying review, and a
  handoff or owner note records authority without inventing any. If a higher-priority
  instruction forbids a cleanup write, report the remaining file.

## External operations and conflicts

Read when the task needs an authorized deployment or other external operation, or when requirements conflict.

If the task needs an authorized deployment or other external operation, include its result and
verification in the exit assessment and do it at the authorized point inside the loop; never defer
an exit prerequisite until after completion, replay an unchanged effect for another review, or add
approval or review prerequisites the approval did not state. If requirements conflict, never drop or
reword an outcome: do the work that does not depend on the conflict (anything the request asks for
when stopping incomplete included), then report `blocked` and name the conflict.

## `verify_script`

Read when a returned packet carries a `verify_script` (the contract's exit checks).

- **`verify_script`.** If a returned packet carries one (the contract's exit checks), run it once,
  unchanged, after the last change, by passing its text itself as your shell command (not saved
  to a file, read from a variable or run through another interpreter: the host's prompt and
  hooks inspect that text). The runtime refuses `satisfied` without a recorded run for the
  current action or after a later workspace change, and refuses completion while a recorded
  check failed. A check whose command misstates its own clause is repaired through the report's
  `check_repairs` with the reason and an unsatisfied exit; the clause never changes.

## A `final_result`

Read when this review changed a decision or decision-relevant evidence a successor needs.

If Improve changes decisions or decision-relevant evidence needed by a successor, include final_result: a complete step result with the same fields as the Step result record in the handoff (outcome done, blocked, send-back at the INNER stages test-spec to verify, or add-work at OUTER stages; never reconcile), preserving authority; with outcome done at plan or carry-forward, list the complete intended queue in work_items whenever the step result proposed one. When the step result is unchanged, omit final_result: ShipLoop reuses the result already submitted, so do not restate it. Preserve existing registered evidence_refs and add every planning file produced or revised, plus a compact decision note and required supporting evidence. Record the finding, applicable original constraints, affected decision and consumer, conclusion, limits and source locators. Ordinary qualifying review/check evidence belongs in the review-<n>.md files and checks.md; it alone does not require final_result. Do not register all scratch output or copy the whole mutable notebook into every context (inline route) or every worker (ask-agent route). Retain key planning decisions, constraints and acceptance expectations as reference statements with source locators. The step definition remains the execution prompt; do not substitute the original user request or a second consolidated directive. Write such a final_result as a step-result record to the path the handoff names and pass --final-result with that path.
