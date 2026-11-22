# Salesforce planning entries proposed from the run journals (ingest trial, 2026-11-22)

One Opus session, by hand, no model called and no run started. Input: the five platform facts the plan audit
(`../evidence/plan-audit-report.md`, sections 2 and 4) found missing from
`skills/shiploop/references/platforms/salesforce.md`. The rule applied (journal section 7): an entry names when the
fact applies, the decision it changes and the observation that could prove that decision wrong; one reviewed source
each; and only facts a model cannot be expected to know.

Result: **two of the five earn an entry, three do not.** The section below is written as a card's `## Planning`
section, so `entry_lint.py --sourced --repo <worktree root>` reads this file directly; Source paths are relative to
the worktree root.

## Planning

- **SF-ANON-AURA** [api, observability] When anonymous Apex (`sf apex run`) calls an `@AuraEnabled` method that
  throws `AuraHandledException`, the platform does not raise that exception: it raises `System.LimitException` ("Can
  only throw this exception type from VisualForce or Aura context"), which no `catch` takes, and the script stops. So
  an anonymous script cannot drive such a method down its error path. Decision: where each invalid-input case is
  proved (on the class that holds the rule, which throws its own exception type) and that an anonymous-Apex proof or
  check calls the controller only with valid input; the controller's error contract is written knowing this. Proof:
  on the target org, an anonymous script that calls the controller with invalid input catches the
  `AuraHandledException` as itself; then the fact no longer holds there and the controller's error path can be proved
  directly. Applies when: the step plan records a command containing `sf apex run` (anonymous Apex, not
  `sf apex run test`) and the design reports a controller error with `AuraHandledException`. A script can test the
  first half from the recorded commands; the second is in code the plan has not written, so at plan time only a
  person (or a later search of the source) can tell. Source: `docs/e2e-salesforce-chess-journal.md` F7.4, "the
  platform raises an uncatchable `System.LimitException". Kind: hard constraint.
- **SF-ASSIGN-AGAIN** [switchover, security] `sf org assign permset --name <Set>` fails (a "Duplicate
  PermissionSetAssignment" row and a non-zero exit) when the user already holds the set: assigning is not idempotent.
  A Proof that assigns therefore fails the second time it runs, although the access is right; and a Proof does run
  more than once (ShipLoop runs a step's Proof itself, and a send-back runs it again). Decision: whether the
  assignment is one release step planned by name (the card already separates the deploy from each visibility step),
  with a read-only Proof that reads the assignment back from `PermissionSetAssignment`; or, if a Proof must assign,
  that it queries first and assigns only when the row is absent. Proof: the planned Proof, run twice in a row against
  the same org, passes both times. Applies when: a command the plan or step plan records (a Proof, a test or check
  command, a release step) contains `sf org assign permset`; a script can test this from the recorded commands.
  Source: `docs/experiments/platform-knowledge-20261122/evidence/plan-audit-report.md` section 2, "`sf org assign
  permset` fails when the assignment already exists". Kind: hard constraint.

## Not entered

- **Region mode** (chess journal F7.2: an app page rejected for mode `REPLACE` without a parent region). A build
  detail: seen once, in the harness's own hand-written probe page, not in a delivery; the check-only deploy names the
  fault in its own message; no plan decides a page template's region mode.
- **HTML-escaped debug log** (chess journal F7.3: `sf apex run --file` returned `RESULT&#124;probe&#124;1`). A harness
  fact, seen once, and narrower than written: the harness read `result.logs` from `--json` output (the retired
  `test/shiploop_e2e/checks/chess_salesforce.py` at `2cd119d12^`, whose `sf()` appends `--json`), while the plain output
  of the same command in a later run shows the debug lines with literal pipes (saved run `ui-live-3`, verify record
  `nav-dee1451229a14f8b9ddd61e2407a49e4-verify1.md`). It changes how a check parses output, not a plan decision; at most
  a `## Testing` line, after one probe of both formats.
- **Removal order and an unprefixed permission set** (battleship journal, "Cleanup order", the 2026-10-17 self-test,
  and "What the fake models" item 7). Harness cleanup facts. The order is enforced by the platform's own refusal (an
  assigned permission set cannot be deleted), confirmed once; no delivery in the record plans to remove a permission
  set, so no `migrate-after` decision used it. The org's own unprefixed permission set was seen once, with no known
  cause: nothing a plan can decide or check. It would earn a `migrate-after` entry only when a delivery plans a
  rollback that removes an assigned permission set.

## What was hard

- **One org, few runs.** Every observation comes from one Developer Edition org (alias `de`) within two weeks.
  SF-ANON-AURA rests on one rehearsal (F7.4, 2026-10-16) and one model run that met it again (F11, 2026-10-20, where
  the model rewrote a spec requirement over it and the spec gate refused twice). SF-ASSIGN-AGAIN rests on three runs
  (the battleship run of 2026-10-30 and `ui-live-2` and `ui-live-3` of 2026-10-31), all on the same org and CLI.
- **Versions.** Exception handling in Apex and the CLI's output are version-bound (the chess journal records
  `@salesforce/cli/2.154.4`; the runs of 2026-10-31 deployed v62.0 metadata through the v68.0 API). The entry form has
  no place for "seen with version X on date Y", so an entry cannot say when it should be checked again. F7.3 shows the
  cost: a fact written without its output format is already ambiguous a month later.
- **Applies when.** SF-ASSIGN-AGAIN is testable: a substring of a recorded command. SF-ANON-AURA is only half
  testable at plan time, because the condition that matters (the controller throws `AuraHandledException`) is in code
  not yet written; the spec's error contract might say it, but no field carries it.
- **Authority of the source.** SF-ASSIGN-AGAIN's only source inside the repository is the audit report, which the
  journal marks as a subagent's reading. I checked the raw record myself: the real-org error row (Salesforce IDs, a
  period after "Duplicate PermissionSetAssignment", unlike the fake's colon) is in the `events.jsonl` of the three
  runs above, and in the battleship run it came back through "ShipLoop step proof: step S3's Proof did not pass"
  (exit 1). Those files are outside the repository and hold an org user name, so they cannot be cited or committed
  as they are. The rule's "one reviewed source" is met only if the ingester's own check counts as the review, which
  is the weakest point of this trial.
- **No concern for proofs.** Both entries change how something is proved; the fifteen concerns have no testing
  concern, so their brackets name the nearest ones (`api` and `observability`; `switchover` and `security`).
- **Overlap with the card.** SF-ASSIGN-AGAIN's decision half overlaps a sentence the card already holds ("Separate the
  deploy from each visibility step"); what it adds is the failure on a repeat. Finding overlap was reading, not a check.
