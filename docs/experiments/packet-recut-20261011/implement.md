# implement: re-cut draft (worker B)

The owner called today's packet "far too elaborate". Inline keeps 7 short items; ask-agent adds item 8.

## 1. Goal (R1)

Make this step's change on its paths in WORKTREE, record each check's exit code in RUN/notes/<action>.md, and list
in the result the behaviours no test case covers (`not_covered`) and each step skill's use (summary).

## 2. Duty

1. **Scope.** Do only this step: edit its paths to meet its criteria, and do no work no criterion asks for. Earlier
   steps are accepted. Write no tests and start no later step. Leave everything outside the step's paths as it is:
   no reformatting, no reverting. Existing tests, check scripts, golden or fixture files and thresholds are checks;
   change one only when a criterion says to.
2. **Build.** Each iteration edits first. Follow the plan note's Coding decision selection, reading only its
   matching sections, and check the current code, versions and consumers before reusing or augmenting a unit.
   Read history or earlier reviews only when a check fails or a question needs one section. Apply Code craft and
   the House-style guidance. Use each listed step skill for its stated purpose (invoke it, or read its SKILL.md and
   follow it); in the summary, say for each whether you used it, and why not.
3. **Check.** After each edit, run every recorded check command and `shiploop lint --action`, and write each exit
   code in RUN/notes/<action>.md. Fix a failure by changing the work, never the check, its expected result or the
   command. A lint finding that must stay goes in `lint_waivers` as `{"id": "<printed ID>", "reason": "<why>"}`.
   Use only what is present: never download, install or fetch a tool, runtime or dependency. Record the best
   evidence available and what would confirm more.
4. **Hand off.** List in `not_covered` each behaviour the change added that no test-spec case covers, or leave it
   empty. Record a departure from HOME/architecture.md as a new AD-<n> under ## Decisions, and a newly working
   command in HOME/environment.md ## Commands.
5. **Services.** For a service change, apply the accepted contract and the Service discovery guidance. Revalidate
   the target state and authority before any effect. Keep unrelated remote fields and existing operational owners.
   Unresolved cache access or async completion uses its recorded safe fallback or correction.
6. **Unachievable as planned.** Stop the loop blocked and report revise, naming the criterion or command and the
   case, when:
   - a criterion contradicts another criterion, the item or a protected file, shown by a check after all compatible
     work is done, with the existing behaviour kept at the conflict point;
   - confirming it needs an absent tool, runtime, access or authority, and the plan did not mark it
     `Confirm by: unconfirmable here`;
   - satisfying it would exceed the item;
   - the same check still fails after GENUINE_FIX_ATTEMPTS genuine fix attempts;
   - the change invalidates a recorded command (a moved module, a new dependency or runtime; see Target-native test
     selection) or needs a new prerequisite or authority boundary.

   Report blocked, with blocked_by, only when the user, an access grant or an outside dependency must resolve it.
7. **Inline.** Do the one step on the packet's Step line in this conversation. Bind no chain and dispatch no worker.
8. **Ask-agent chain** (replaces 7).
   - If the step plan says no parallel chain, or the item context says its steps write the same tree, use one writer
     in the execution checkout, bind no chain, and cite that locator in the result.
   - Otherwise, for a reviewed graph with safe independent steps, bind the default parallel mode (Parallel-chain
     guide) when the Plan Dispatcher and Ask-Agent contracts are compatible and native slots are observed free.
     Capacity is the observed user or host slot limit, not the fallback default. If it cannot start, record the
     concrete compatibility, capacity, resource, readiness or recovery blocker. Serial mode is only for an explicit
     user or host limit; it runs one ready step in the main context without agents.
   - Both modes use external sibling worktrees and one acceptance route: Ask-Agent creates each worker worktree;
     you verify and adopt it, import its results, check the combination, merge into the invoking branch, accept the
     step and remove the worktree. Keep conflicts and cleanup blockers; never repeat accepted work because removal
     failed. Keep the combined status observable. Only accepted steps are done.
   - On the first frontier and after every callback, refresh at once and start every safe listed candidate up to
     capacity; a branch may become ready after a serial prefix. Never wait on a reconciliation, preparation,
     verification or collection while an independent safe worker can start. Defer only a candidate with a recorded
     blocker.
   - Finish before this stage's callback: every required step accepted and the combined return verified, or a
     recorded incomplete blocker.

## 3. Checked by

- The lint gate refuses done once after applying an auto-fix: keep or revert it, rerun the checks, submit again.
- For an item with no test command and only non-code paths: a change to a code or test path, or to an undeclared
  path.

## 4. Guides to keep

Coding decision guide; House-style guidance; Service discovery guidance; Target-native test selection;
Parallel-chain guide (ask-agent only).
Drop: Repeatable test-suite guide, Implementation constitution (Code craft is printed whole; the constitution adds
nothing this duty cites).

## 5. Loop Work (shiploop_loops.WORK["implement"])

"Do duty items 1-4 of {run}/packets/{action}.md for {step_change}. Write no tests and start no later step."
(The exit-code recording and change-the-work rule move to duty item 3, their one home.)

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| Earlier steps are accepted; no work no criterion asks for | 1 |
| Departure from architecture.md as new AD-<n> | 4 |
| Newly working command in environment.md | 4 |
| Coding decision guide: reopen plan and relevant sections; check code, versions, consumers before reuse | 2 |
| Use each step skill for its purpose (invoke or read SKILL.md) | 2 |
| Each iteration writes first; read history only when a check fails or a question needs it | 2 |
| Apply planned behaviour and Code craft | 2 |
| An edit alone verifies nothing | 3 ("After each edit, run ...") |
| Preserve unrelated work: no reformatting or reverting outside paths | 1 |
| Existing tests, scripts, goldens, thresholds are checks; change only when a criterion says | 1 |
| Never download, install or fetch; record best evidence and what would confirm more | 3 |
| Lint waiver shape | 3 |
| Listed skill not used: result says why | 2 |
| Unachievable (a)-(d) | 6 |
| Invalidated recorded command or new prerequisite/authority is unachievable too (Target-native test selection) | 6 |
| Stop loop blocked and report revise naming criterion/command and case; not blind retry | 6 |
| Blocked with blocked_by only for user, access, outside dependency | 6 |
| Improve child reviews the step after accept | CUT: advance Improve mention (R3, R7) |
| Service changes: contract, Service discovery, revalidate before effects, preserve remote fields and owners, cache/async fallback | 5 |
| _IMPLEMENT_INLINE: one step on Step line; in this conversation; ShipLoop issues next step and then test | 7 ("ShipLoop issues the next step" CUT: the shared rule "ShipLoop owns the next step") |
| _IMPLEMENT_INLINE: no later step, no chain, no Ask Agent or native workers; chains only in ask-agent | 7 |
| _IMPLEMENT_CHAIN: no-chain conditions, one writer, cite locator | 8 |
| _IMPLEMENT_CHAIN: bind default parallel mode when contracts compatible and slots observed | 8 |
| _IMPLEMENT_CHAIN: record concrete blocker; serial only on explicit limit | 8 |
| _IMPLEMENT_CHAIN: parallel uses Ask-Agent; serial one step in main context without agents | 8 |
| _IMPLEMENT_CHAIN: capacity is observed slot limit; branch may become ready after serial prefix | 8 |
| _IMPLEMENT_CHAIN: sibling worktrees, same acceptance; create, verify, adopt, import, check, merge, accept, remove | 8 |
| _IMPLEMENT_CHAIN: keep conflicts and cleanup blockers; never repeat accepted work | 8 |
| _IMPLEMENT_CHAIN: observable combined status; only accepted steps are done | 8 |
| _IMPLEMENT_CHAIN: continue until all accepted and return verified, or blocker; finish before callback | 8 |
| _IMPLEMENT_CHAIN: claim and start every safe candidate; refresh after callback; never wait; defer only with blocker | 8 |
| Consideration Develop: execution checkout, one step at a time, house style | 1, 2 |
| Consideration Test: rerun checks after each edit; change work not check; tests at the test stage | 3, 1 |
| Consideration Tools: lint after each edit; gate at complete on every step | 3; Checked by |
| Loop Work: step change, paths, criteria, house style, Code craft | 1, 2 |
| Loop Work: run checks and lint, record exit codes in notes | 3 |
| Loop Work: find cause; change work, never check, expected result or command | 3 |
| Loop Work: write no tests, start no later step | 1 and the new Work line |
| CODE_CRAFT | Printed whole, unchanged, under "What you work from" |

## 7. Size

- Today: duty 5,132 (ask-agent; 3,889 inline) + considerations 310 + Work 448 = 5,890 characters (ask-agent).
- New: 3,200 characters inline (items 1-7); 5,000 ask-agent (items 1-6 and 8). Today's inline equivalent is
  3,889 + 310 + 448 = 4,647.


## Tightened (pass 2)

Duty size (inline): 3,022 -> 2,893 characters (-5%). Goal: "Make this step's change on its paths in WORKTREE; exit codes go to RUN/notes/<action>.md, uncovered behaviour to `not_covered`."; short goal: 'implement this step'.

Text now in `DUTIES['implement']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. **Scope.** Do only this step: edit its paths to meet its criteria, nothing no criterion asks for. Earlier steps are
   accepted. Write no tests, start no later step, and leave everything outside the step's paths as is (no
   reformatting, no reverting). Existing tests, check scripts, golden or fixture files and thresholds are checks:
   change one only when a criterion says to.
2. **Build.** Each iteration edits first. Follow the step plan's Coding decision selection (Coding decision guide),
   reading only its matching sections; check current code, versions and consumers before reusing or augmenting a
   unit. Read history or earlier reviews only when a check fails or a question needs one section. Apply Code craft
   and House-style guidance. Use each listed step skill for its purpose (invoke it, or read its SKILL.md and follow
   it); the summary says per skill whether you used it, and why not.
3. **Check.** After each edit run every recorded check command and `shiploop lint --action`; write each exit code in
   RUN/notes/<action>.md. Fix a failure by changing the work, never the check, its expected result or the command.
   A lint finding that must stay goes in `lint_waivers` as `{"id": "<printed ID>", "reason": "<why>"}`. Use only
   what is present: download, install or fetch nothing. Record the best evidence available and what would confirm
   more.
4. **Hand off.** `not_covered`: each behaviour the change added that no test-spec case covers, else empty. Record a
   departure from HOME/architecture.md as a new AD-<n> under ## Decisions, and a newly working command in
   HOME/environment.md ## Commands.
5. **Services.** Apply the accepted contract and Service discovery guidance; revalidate target state and authority
   before any effect; keep unrelated remote fields and existing operational owners. Unresolved cache access or async
   completion uses its recorded safe fallback or correction.
6. **Unachievable as planned.** Stop the loop blocked and report revise, naming the criterion or command and the
   case, when:
   - a criterion contradicts another, the item or a protected file, shown by a check after all compatible work is
     done, with existing behaviour kept at the conflict point;
   - confirming it needs an absent tool, runtime, access or authority, and the criterion text does not say
     `Confirm by: unconfirmable here`;
   - satisfying it would exceed the item;
   - the same check still fails after 7 genuine fix attempts;
   - the change invalidates a recorded command (moved module, new dependency or runtime; Target-native test
     selection) or needs a new prerequisite or authority boundary.
   Report blocked, with blocked_by, only when the user, an access grant or an outside dependency must resolve it.
7. **Inline.** Do the one step on the packet's Step line in this conversation. Bind no chain and dispatch no worker.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
