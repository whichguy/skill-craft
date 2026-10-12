# validate-existing: re-cut draft (worker B)

## 1. Goal (R1)

Resolve each expectation that did not match on the item base: fix the environment or a known small defect in
WORKTREE, or report revise with `failed_expectations` naming each mismatch and what is true.

## 2. Duty

1. **Find the cause.** ShipLoop ran each expectation's check, and each open plan assumption this item settles, on the
   unchanged item base; the results are below. Read the step plan's steps and paths for each mismatched
   expectation. With one small discriminating observation, find whether the fact or the check is wrong.
2. **Route it:**
   - The check is wrong and the fact holds: report revise. Never edit or weaken a check here.
   - A `works` expectation is broken and the fix is known and small: fix it in the working tree, touching only that
     expectation's paths. Commit nothing; ShipLoop commits it on accept as one preparatory commit, separate from the
     item's change.
   - The environment lacks a tool, service or setting: fix the environment and record it in HOME/environment.md
     ## Commands or ## Targets and runtimes.
   - An `absent` expectation finds something, a `broken` one does not reproduce, or the fix is not known: report
     revise with what is true. The step plan reshapes the steps; a needed repair becomes an earlier step.
   - The fix lies outside this run (another system, a person's access): report blocked, blocked_by external or
     access, naming what is needed.
3. **Never start the item's own change here.**
4. **Revise shape.** Name each mismatch in `failed_expectations`: `[{"id": "E1", "actual": "<what is true>",
   "route": "check" | "steps"}]`. Route `check` when the check is wrong (`actual` gives the corrected check);
   `steps` when the plan must change.

On re-entry after implement, ShipLoop runs the checks in a temporary worktree at the item base (after any
preparatory commit), so checkout edits cannot change them; a mismatch there is a revise.

## 3. Checked by

- A changed file outside the paths of an expectation that did not match.
- A revise without `failed_expectations` naming each expectation and what is true.

## 4. Guides to keep

Baseline-test guidance; Current-system baseline guide.
Drop: Repeatable test-suite guide (not cited).

## 5. Loop Work (shiploop_loops.WORK["validate-existing"])

"Take the first expectation whose check does not match its state and do duty items 1-2 of
{run}/packets/{action}.md for it; then rerun every expectation's check."

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| ShipLoop ran each check and each settled assumption on the unchanged base; results listed | 1 |
| This packet exists because one did not match | CUT: implied by the goal |
| Once an iteration found whether fact or check is wrong | 1 |
| Check wrong: revise with corrected check; never edit or weaken a check | 2, 4 |
| Works broken, known small fix: fix in tree, only its paths; commit nothing; preparatory commit | 2 |
| Environment lacks something: fix and record in environment.md | 2 |
| Absent found / broken not reproducing / unknown fix: revise with what is true; repair becomes earlier step | 2 |
| Fix outside run: blocked external or access | 2 |
| Never start the item's own change | 3 |
| Re-entry: temporary worktree at base after preparatory commit; mismatch is a revise | Closing paragraph |
| Revise names each in failed_expectations, shape, route check/steps | 4 |
| Read the step plan (steps and paths) and the plan's assumptions | 1 (assumptions: "each open plan assumption this item settles") |
| Consideration Develop: change no product file except known small fix; own commit; never start item change | 2, 3 |
| Consideration Test: ShipLoop runs checks; all match means no packet | 1; "no packet" CUT: describes ShipLoop routing, no duty |
| Loop Work: first mismatch, discriminating observation, fix env or known fix, rerun all | New Work line + 1-2 |

## 7. Size

- Today: duty 2,259 + considerations 288 + Work 434 = 2,981 characters.
- New: 2,100 characters.


## Tightened (pass 2)

Duty size (inline): 1,772 -> 1,579 characters (-11%). Goal: 'Resolve each expectation that mismatched on the item base: fix it in WORKTREE or report revise with `failed_expectations`.'; short goal: 'validate the item base'.

Text now in `DUTIES['validate-existing']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. ShipLoop ran each expectation's check, and each open plan assumption this item settles, on the unchanged item
   base; results are below. For each mismatch read the step plan's steps and paths, and with one small
   discriminating observation find whether the fact or the check is wrong (Baseline-test guidance, Current-system
   baseline guide).
2. Route each mismatch:
   - check wrong, fact holds: report revise. Never edit or weaken a check here.
   - `works` expectation broken, fix known and small: fix it in the working tree, touching only that expectation's
     paths, and commit nothing (ShipLoop commits it on accept as a separate preparatory commit).
   - environment lacks a tool, service or setting: fix it and record it in HOME/environment.md ## Commands or
     ## Targets and runtimes.
   - `absent` finds something, `broken` does not reproduce, or the fix is unknown: report revise with what is true
     (the step plan reshapes the steps; a needed repair becomes an earlier step).
   - fix lies outside this run (another system, a person's access): report blocked, blocked_by external or access,
     naming the need.
3. Start none of the item's own change.
4. Revise names each mismatch in `failed_expectations`: `[{"id": "E1", "actual": "<what is true>", "route":
   "check" | "steps"}]`; `check` when the check is wrong (`actual` gives the corrected check), `steps` when the
   plan must change.

On re-entry after implement, ShipLoop runs the checks in a temporary worktree at the item base (after any
preparatory commit); a mismatch there is a revise.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
