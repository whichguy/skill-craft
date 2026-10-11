# verify: re-cut draft (worker B)

## 1. Goal (R1)

Accept the item: confirm each criterion with a command run after the last edit, trace every changed public entry
point and review the item's diff, writing exit codes and traces in RUN/notes/<action>.md and each open later-phase
check in `assumptions`. This is item acceptance, not a claim that integration or release has happened.

## 2. Duty

Each review iteration does items 1-7 in order.

1. **Run.** Run every recorded command (the Test rerun list) and write each exit code and test count in
   RUN/notes/<action>.md.
2. **Confirm.** For each criterion, name the passing command or the inspection that confirms it now. Stale, skipped
   or missing evidence is not a confirmation, and neither is evidence for another candidate, command, configuration
   or target. Keep diagnostic scores apart from that decision. A criterion reported `inspected` or `unconfirmable`
   whose `Confirm by:` needs execution: report revise.
3. **Reconcile cases** (Test-case planning guidance). Classify every test-spec case passed, failed, blocked, not-run or justified N/A. Reconcile
   each affected requirement clause with its case, required surface and due phase, the checked surface, the
   candidate, status and evidence. A pass on another surface only supports. Source, HTTP or DOM structure alone
   cannot close a rendered interaction. A case not yet due keeps its phase, owner and prerequisites; already-due
   evidence that is missing stays incomplete. Check for dropped clauses or cases. Never claim every requirement met
   while required observations remain unrun.
4. **Trace.** From the change inventory RUN/lint/<action>-inventory.md, list every new or changed public entry point
   (exported function, CLI, request or event handler, callback). Walk one valid, one boundary and one invalid input
   to its return, error or side effect, and write one trace line per path in RUN/notes/<action>.md. A wrong,
   unhandled or untested path is a finding. A test added for an untested path is titled `<ID> (<letter>)` under the
   case it extends. An entry point in the diff but missing from the inventory has not been traced.
5. **Review.** Review the whole item's diff against the step plan's steps, paths and justified revisions, its
   affected consumers, Code craft and HOME/architecture.md. Look for: missing argument checks or contract
   docstrings at an entry point; missing error paths; silent failures; comments that restate or are stale; dead
   code; user text that is concatenated or bypasses the catalog; names outside the planned namespace or exported
   wider than needed; stored data off the planned schema; a near-copy of existing logic; a plain interaction where
   the plan called for a rich one; a deviation from HOME/architecture.md with no new AD-<n>. Reconcile tests,
   documentation, error behaviour, diagnostics, dependencies and known limitations. On entry ShipLoop linted and
   auto-fixed safe formatting once: keep or revert each auto-fix the lint record names. The lint record supports
   this review; it does not replace it.
6. **Services.** For the item's selected service and observability contracts (Service discovery guidance), verify
   the due outcomes, including safe fallback and failure cases. Keep local simulation apart from required remote
   readback, permission enforcement, completion and event retrieval.
7. **Classify and fix.** Material: wrong behaviour on a traced path; a missing or wrong argument check, contract,
   error path or test; a failing command; a misleading comment; logic that should have been composed. Trivial:
   wording, ordering, a sharper name. Do not reopen a finding an earlier iteration fixed unless its code changed.
   Fix every finding within scope by changing the work, never a check or its expected result; change a test only
   to fix a finding. If anything changed, rerun item 1.
8. **Assembly.** Ask-agent: if implement used a bound chain, confirm its finish commit is an ancestor of the
   execution checkout HEAD and record it, then inspect the combined diff, conflicts and the shared interfaces
   between steps (Workspace integration guidance). Otherwise, and inline: confirm the item's candidate is assembled in the execution checkout under
   workspace and repository policy. The original branch returns only at the final workspace return.
9. **Later checks.** Each system, release or real-boundary check the criteria need is an open item in `assumptions`
   with its consumer (the stage it is due at) and owner; add any missing one. A boundary a local test cannot prove
   stays pending with its owner in HOME/test-strategy.md ## Real-boundary checks (Real-boundary test guidance).
10. **Commit.** Keep run state, raw logs, credentials and generated artifacts out of the product commit.
    ITEM_COMMITS + item_left(execution mode), printed here (today in the Develop consideration).
11. **Summary.** Give the entry points traced, each trace that found an issue and its fix, each command with its
    exit code, any required check not run and why, and the known limitations.
12. Report revise when a criterion or check proves unachievable as planned, naming it. Report blocked, with
    blocked_by, only when the user, an access grant or an outside dependency must unblock it.

## 3. Checked by

- The lint gate refuses done once after applying an auto-fix, and while a new finding on a changed line has no
  waiver.
- ShipLoop's own rerun is the evidence: a criterion is confirmed by its passing command, not by the summary.
- `assumptions` missing, or an open item whose consumer is not a later outer stage or this item's carry-forward.

## 4. Guides to keep

Service discovery guidance; Test-case planning guidance; Real-boundary test guidance; Workspace integration guidance.
Drop: Coding decision guide, House-style guidance, Repeatable test-suite guide, Iteration and verification guidance
(not cited by the new duty; Code craft carries the review rubric). **Unsure:** `_improve_prompt` adds a Coding
decision paragraph for verify by stage name, not by label, so dropping the label leaves that paragraph pointing at a
guide the packet no longer prints. Keep "Coding decision guide" if the verify Improve paragraph stays.

## 5. Loop Work (shiploop_loops.WORK["verify"])

Today's Work is the numbered review procedure, about 2,000 characters, and restates the duty. Replace it with:
"Do duty items 1-7 of {run}/packets/{action}.md in order; the review gate needs one complete iteration that finds
only trivial issues." The material and trivial definitions move to duty item 7, their one home.

## 6. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| _LOOP_DUTY (4 sentences) | Shared "What to execute" section |
| Work-item acceptance, not integration or release | Goal |
| Test stage got every command green: confirm and review; change a test only to fix a finding | 7 |
| A boundary a local test cannot prove stays pending with owner in Real-boundary checks | 9 |
| On entry ShipLoop linted, auto-fixed once, wrote inventory | 5 |
| Keep or revert each auto-fix; lint record supports, does not replace | 5 |
| Work's numbered steps; "this adds to them" | 1-7 (merged; the Work line points here) |
| 1. Recorded commands are the Test rerun list | 1 |
| 2. Evidence for another candidate/command/config/target is not confirmation; keep scores apart | 2 |
| 2. inspected/unconfirmable needing execution: revise | 2 |
| 2. Classify every case by the reconciliation | 3 |
| 3. Test for untested path is `<ID> (<letter>)`; entry point missing from inventory not traced | 4 |
| 4. Review against justified revisions and affected consumers | 5 |
| 5. _VERIFY_ASSEMBLY / _VERIFY_ASSEMBLY_INLINE | 8 |
| Reconcile tests, docs, errors, diagnostics, dependencies, limitations | 5 |
| Service discovery: due outcomes, fallback, failure; local vs remote readback, permissions, completion, events | 6 |
| Later-phase checks are open items in assumptions with consumer and owner; add missing; "system-test-author picks them up" | 9; the pickup CUT (R3) |
| Keep run state, logs, credentials, artifacts out of the product commit | 10 |
| Summary contents | 11 |
| Revise when unachievable; not blind retry | 12 |
| Blocked only for user, access, outside dependency | 12 |
| SELECTED_CASE_RECONCILIATION (all sentences) | 3 (verify's copy); the shared block stays for the outer stages that carry it |
| Consideration Develop: whole diff for what per-step reviews missed; assemble chained work | 5, 8 |
| Consideration Develop: item commit rule | 10 |
| Consideration Test: confirm each criterion; reconcile every case | 2, 3 |
| Consideration Tools: inventory, entry lint, done lint and rerun | 5; Checked by |
| Work 1: run every command, record exit code and count | 1 |
| Work 2: name passing command or inspection; stale evidence; classify cases; other surface supports | 2, 3 |
| Work 3: inventory, entry points, trace three inputs, one line per path, finding, add test | 4 |
| Work 4: review list | 5 |
| Work 5: chained work assembly | 8 |
| Work 6: material vs trivial; do not reopen | 7 |
| Work 7: fix within scope, never the check; rerun step 1 | 7 |

## 7. Size

- Today: duty 3,181 + SELECTED_CASE_RECONCILIATION 665 + considerations 358 (plus the commit rule) + Work 2,036 =
  6,240 characters.
- New: 5,600 characters. The Work line drops from 2,036 to about 170.
