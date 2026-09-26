---
name: improve-agent
description: >-
  Use when Improve should run in a fresh native agent instead of this
  conversation: start one agent that runs /improve in its own context, keep
  useful parent work going, then verify and relay its result. For Improve in
  this conversation, use improve.
version: 0.1.1
license: MIT
platforms:
  - linux
  - macos
metadata:
  short-description: Run Improve in a fresh native agent
  skill_craft:
    kind: prompt-only
---

# improve-agent

This card delegates one Improve invocation to one fresh native agent. The
selected `improve` card owns the review-and-improvement algorithm and runs
inline wherever it is invoked; this card owns only the dispatch, the assignment,
the worker contract and the parent's verification. The host-selected Ask Agent
card owns native launch, workspace preparation and delivery mechanics.

Do not run the Improve loop in this conversation, and never start a second
Improve writer for the same candidate. When the user wants Improve without an
agent, use `improve` instead.

## Resolve the selected cards and host

Resolve the absolute paths of the **selected, loaded** `improve/SKILL.md` and
Ask Agent `SKILL.md` supplied by the host, expanding any selected skill-root
alias. Do not guess a sibling checkout, an older installed wrapper, `PATH`, or a
same-named skill. Read the Ask Agent card's route selection, current-learnings,
approval and result sections before launch.

Check the live host schema, following Ask Agent's host-capabilities reference:
the agent needs fresh context without the inherited conversation, access to the
workspace and the selected skills, the tools the task needs, and a native result
collection route. If a card or a required capability is missing, report the gap
and stop. Do not substitute inherited context, a shell-launched model, an
external runner, or an inline run of Improve; running inline instead is the
user's choice.

## Choose the workspace route

- **Standalone request.** Use Ask Agent's helper-managed default route. Its
  helper prepares an isolated worktree from the current candidate snapshot.
  Choose the delivery mode before launch: `commits` when Improve's ordinary
  commit policy applies, `patch` for an explicit no-commit request, and
  `report-only` for a preview or dry-run request.
- **Consumer-bound child.** When a consumer such as a ShipLoop
  `delegation: ask-agent` Improve packet supplies a complete consumer-owned
  contract, use Ask Agent's consumer-owned workspace route with
  `workspace_route: consumer-owned` and `delivery_mode: in-place`. It requires
  the selected Ask Agent card's `ask-agent/consumer-owned-workspace/v1`
  capability. The parent writes the consumer's `host-owner.md` record as that
  route describes. If the capability or any contract field is missing, fail
  closed: keep the action pending with its locators and never fall back to the
  helper-managed route or a second worktree.

## Compose the assignment

Write the native assignment in this order, keeping essential facts and actual
decisions inline with locators for supporting detail. The worker must not need
this card, a whole parent packet or a consumer reference to begin.

1. **Current context and desired improvements**, with **Current learnings**
   nested inside it, following Ask Agent's current-learnings rule: what is known,
   what already changed, and what should be improved or investigated next.
   Keep facts, decisions and hypotheses visibly distinct; suggested fixes are
   candidates to assess, not findings or authorization.
2. `Run /improve using <selected absolute improve SKILL.md>`, once.
3. The binding:
   - the workspace's absolute path and Git root, and the route markers;
   - the candidate scope or inventory, its exclusions, and the base or HEAD;
   - authority: commit, no-commit and push rules, the current approvals,
     declines and pending decisions with their sources and conditions, and any
     explicit independent-review request (without one, the worker's Improve
     run keeps its inline self-review default);
   - the evidence root and, for a consumer-bound child, the exact child packet
     receipt, completion evidence and `host-owner.md` locators and the binding
     marker the consumer printed;
   - the return route in [Worker contract](#worker-contract), and the
     parent-only continuation it must leave unexecuted.

A consumer-bound assignment also carries these literal markers after the
opening:

```text
workspace_route: consumer-owned
delivery_mode: in-place
execution_role: improve-executor
delegation_owner: parent
```

## Worker contract

Give the worker these rules in the assignment:

- Verify the process `pwd` and `git rev-parse --show-toplevel` against the
  assigned workspace before task work and after any directory change, and use
  that workspace as the operation directory for every shell call. A mismatch is
  a blocker to return, not something to work around.
- Run the selected Improve card once, inline in your own context, under the
  frozen authority. Its standalone binding, including any ShipLoop whole-skill
  subcall section the assignment names, applies unchanged.
- Be the only candidate writer. Do not dispatch Improve again, create another
  worktree, or start reviewer, test-runner or executor agents unless the
  assignment carries an explicit independent-review request. Collect any
  delegate before returning.
- Do not execute a parent callback, workspace return, merge, push beyond the
  stated authority, caller delivery or cleanup. Read `host-owner.md` for
  orientation only; the parent alone appends to it.
- Save each runtime packet at the given receipt path, finish all writes, and
  return inline:
  - Improve's completion summary: key implemented changes, what was learned,
    validation and remaining work;
  - the observed workspace and Git root, initial and final HEAD, changed paths,
    and scoped commit SHAs or the explicit no-commit or no-change reason;
  - the checks run and the review-record locators, and the terminal packet and
    completion-evidence locators;
  - the runtime's terminal status (`complete`, or the incomplete `stopped` or
    `blocked` state with its blocker), and a statement that no parent-owned
    step was executed.

## While the agent runs

Continue useful parent work that neither writes the candidate nor runs
input-mutating checks in it. Forward a later user decision to the existing
worker through native messaging; for a consumer-bound child, also append its
source, scope and receipt status to `host-owner.md`. A lost, running or unknown
worker blocks replacement until it is collected or the host shows it stopped or
never launched, as Ask Agent's recovery rules describe.

## Verify and relay the result

Collect the actual native return, then check it against the candidate:

- the terminal packet or receipt exists at the stated locator and its status
  matches the claim;
- the workspace identity, changed paths and scope match the assignment, and
  each reported commit SHA exists in the candidate;
- the reported checks and review records exist; rerun a check only when its
  record is missing or stale.

For the helper-managed route, integrate the result through the chosen delivery
mode under Ask Agent's result rules. For a consumer-bound child the edits are
already in place; the consumer verifies them and runs its own continuation.
Relay Improve's completion summary with the observed delivery state. A worker's
completion is not caller delivery. A stopped, blocked or unverifiable result is
reported as partial, with its blocker and recovery action.
