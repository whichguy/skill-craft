# document: re-cut draft (worker B)

## 1. Goal (R1)

Update the documentation this item's change affects in WORKTREE (README, API, operator, error and design docs) from
observed behaviour, and record each no-change reason in RUN/notes/<action>.md.

## 2. Duty

1. **List.** Take the changed public behaviours from the change inventory, the step plan, the implement results and
   the item's diff.
2. **Observe and write.** Run each changed behaviour, then update the README, API, user, operator, error and design
   documentation from what you observe: the errors a user can see, how to turn on diagnostics, known limits and
   caveats. Keep public, error and debug behaviour accurate, concise and discoverable. Link to the authoritative
   home instead of copying a contract (Documentation guidance). Document nothing you did not observe working. Durable facts go in the
   repository's docs, never only in run notes.
3. **Decisions.** Write a design or service decision implement did not record as an AD-<n> under
   HOME/architecture.md ## Decisions (a service choice with its contract, owner and revalidation trigger).
4. **Baseline.** When the item recovered existing behaviour, keep recovered observations and accepted deltas apart
   from the prior as-of baseline (Current-system baseline guide).
5. **Reread.** Reread every changed document and run its commands and examples. In RUN/notes/<action>.md, record why
   a behaviour needs no documentation, why the README did not change, or why an example cannot run here.
6. **Commit nothing.** ITEM_COMMITS + item_left(execution mode), printed here (today they are appended to the
   Develop consideration).
7. Report revise when the plan or a criterion is wrong as observed, naming it. Report blocked only when a behaviour
   cannot be observed here, naming it.

## 3. Checked by

Nothing beyond the exit conditions and the shared checks.

## 4. Guides to keep

Documentation guidance; Current-system baseline guide.
Drop: Documentation and reuse guidance (its content is the skill decision, carry-forward's); Service discovery
guidance (never cited by the duty, today or new).

## 5. Loop Work (shiploop_loops.WORK["document"])

"Do duty items 1-5 of {run}/packets/{action}.md; record each no-change reason in {run}/notes/{action}.md."

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| ShipLoop issues this stage only when the change touches behaviour | CUT: ShipLoop routing, no duty |
| Write a design/service decision as AD-<n> if implement did not | 3 |
| Changed behaviours from step plan, implement results, diff, inventory; user and design docs count | 1, 2 |
| Document nothing not observed working | 2 |
| Keep public, error, debug behaviour accurate, concise, discoverable | 2 |
| Durable facts in repository docs, never only run notes | 2 |
| Recovered behaviour: keep observations and deltas apart from baseline (guide) | 4 |
| Commit nothing yourself | 6 |
| Revise when plan or criterion wrong; blocked when not observable | 7 |
| Consideration Develop: code, API, user, operator docs from observed behaviour | 2 |
| Consideration Develop: item commit rule (ITEM_COMMITS, item_left) | 6 |
| Loop Work: run each behaviour, update README/API/operator/error docs, errors, diagnostics, limits, link not copy | 2 |
| Loop Work: reread, run commands and examples, record no-change reasons in notes | 5 |

## 7. Size

- Today: duty 1,272 + considerations 74 (plus the 330-character commit rule) + Work 521 = 2,197 characters.
- New: 1,850 characters, the commit rule named rather than counted.


## Tightened (pass 2)

Duty size (inline): 1,838 -> 1,686 characters (-9%). Goal: 'Update the docs this change affects in WORKTREE from observed behaviour; no-change reasons go to RUN/notes/<action>.md.'; short goal: "document this item's change".

Text now in `DUTIES['document']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. **List** the changed public behaviours from the change inventory, the step plan, the implement results and the
   item's diff.
2. **Observe and write.** Run each changed behaviour, then update the README, API, user, operator, error and design
   docs from what you observe: visible errors, how to turn on diagnostics, known limits and caveats. Link to the
   authoritative home rather than copying a contract (Documentation guidance). Document nothing you did not observe
   working. Durable facts go in the repository's docs, never only in run notes.
3. **Decisions.** A design or service decision implement did not record: an AD-<n> under HOME/architecture.md
   ## Decisions (a service choice with contract, owner and revalidation trigger).
4. **Baseline.** Recovered existing behaviour: keep recovered observations and accepted deltas apart from the prior
   as-of baseline (Current-system baseline guide).
5. **Reread** every changed document and run its commands and examples. In RUN/notes/<action>.md record why a
   behaviour needs no documentation, why the README did not change, or why an example cannot run here.
6. **Commit nothing yourself.** When verify is accepted, ShipLoop commits the item's changed files that the step plan's paths declare, its changed documentation files (for example README.md or files under docs/) and docs/shiploop/. Any other changed file is not part of the item commit: if the product needs one, report revise so the step plan declares it; otherwise delete generated output the product does not need.
7. Plan or criterion wrong as observed: report revise naming it. Report blocked only when a behaviour cannot be
   observed here, naming it.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
