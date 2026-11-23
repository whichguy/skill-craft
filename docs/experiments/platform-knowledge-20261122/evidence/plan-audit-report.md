# Audit of the accepted plans in nine saved Salesforce deliveries: the subagent's report, as returned

Report of an Opus research subagent, 2026-11-22, read-only, no model run. Its brief asked, for three rules of
`skills/shiploop/references/platforms/salesforce.md` (A entry visibility, B the test route, C tool state): was the
fact missing when the decision was made, and what followed. The runs are the nine listed in
`salesforce-static-runs.txt`, numbered in that order except that this report numbers the Grok run 6. Two of its
claims were hand-checked by the main session before use (journal section 11): that the saved prompts state rules A
and B themselves, and what the current stage text says about a count ShipLoop cannot read. The rest is the
subagent's reading.

---

**Short answer: I found one case in the nine runs where a card fact was missing while the work could still change
and something went wrong because of it (run 7, rule C). It cost about 40 seconds.** In every run, rules A and B were
settled by the request prompt itself, not by the card. The card's rule B claim did not hold in these runs.

Two facts behind that:

- The battleship and gym prompts name the permission set, its grants and the exact `sf org assign permset` command,
  and say "A new tab is hidden from every user until a permission set or profile grants it".
- The chess prompts forbid creating or changing permission sets and profiles.
- Every prompt dictates `--result-format human`.

Each run's own copy of the card already held all three rules (checked under each run's `home/`).

## 1. Table

| Run | A (entry visibility) | B (test route) | C (tool state) |
|---|---|---|---|
| 1 | followed (the prompt names the grant). The proof failed on "Duplicate PermissionSetAssignment" and was sent back to step-plan, about 2.5 min | not followed (human, as prompted); ShipLoop marked it passed, no refusal | late: only `.sf/`, written at carry-forward. `.sf` files showed up in lint, base-run and Improve scopes; no refusal |
| 2 | followed (gym-ui browser check) | not followed; passed. One system-test refusal (host-dependent default suite, about 1.5 min) is unrelated to the reporter | not applicable: no `.sf` in the worktree |
| 3 | not applicable (prompt forbids grants). Gap noted at prepare as "Consumer tab visibility remains unproven"; no probe | not followed; passed | not followed: no .gitignore ever; `.sf` in base-run `added_files` and the Improve scope; no refusal |
| 4 | not applicable; left as a person task at handoff | not followed; passed. Two mutation refusals on Apex lines, about 20 s each | followed at prepare (`.sf/ .sfdx/`) |
| 5 | not applicable; person task | not followed; passed. One "fetch failed" (network) | late: added in W2/S1 |
| 6 (Grok, read the card) | followed in substance: gap named at discovery, carried as assumption A8 to handoff, user assignment probed at prepare | followed for the step-plan focused commands (tap); human for the prompt's own check commands | followed at prepare |
| 7 | followed; tab access left to a person | not followed; passed | not followed: the step proof failed (case 1 below) |
| 8 | followed (assignment read-back and browser game passed) | not followed; passed | not found: the work folder is not a git repo, which is why the run failed `committed` |
| 9 | followed. Duplicate-assignment proof failure, sent back, about 1 min | not followed; passed | followed at prepare |

## 2. Card fact missing, then a fault

1. **Run 7, implement W1/S1 (rule C).** Its plan named no .gitignore. The step proof `sf project deploy start`
   failed with "Error (NotFoundError): Could not find HEAD" (`trace.jsonl` 01:52:15;
   `run/tests/nav-525cb5d6f1ba44b598411167a33995d7-step-proof1.md`). The model found `.sf` empty, restored the two
   `localSourceTracking` files from a ShipLoop snapshot commit, and added `.sf/` to `.git/info/exclude` rather than
   .gitignore (`events.jsonl` around line 184). It recovered by 01:52:53, and the product shipped with no
   .gitignore. That ShipLoop's tree handling removed the unignored files is inferred.
2. **Weaker, no fault (runs 1, 3, 5, rule C).** `.sf/orgs/.../localSourceTracking` files were listed as changes in
   implement packets ("Changed, ShipLoop will not commit"), lint scopes, base-run `added_files` and Improve scopes.
   Nothing was refused. This is noise only.

Nothing else qualifies. The two duplicate-assignment send-backs (runs 1 and 9) come from a fact the card does not
hold: `sf org assign permset` fails when the assignment already exists.

## 3. Correct decisions without the card

- **Rule A, runs 1, 2, 7, 8 and 9:** relied on the prompt, which spells out the grant.
- **Rule A, chess runs 3 to 5:** relied on the prompt's ban plus general knowledge, e.g. run 4 release-verify:
  "Salesforce UI visibility depends on existing access, which this request forbids changing". They recognised the
  gap later and less specifically than run 6 did.
- **Rule C, runs 4 and 9:** wrote `.sf/ .sfdx/` at prepare, before any build. They relied on prepare packet item 8,
  which points to the card's "## Tool state" section but does not name the folders, plus general knowledge
  (inferred). Run 4's only look at the card, an `rg` over the platforms folder, came after this.
- **Rule B:** the prompt fixed the command. ShipLoop itself marked the Apex tests `remote` in its base runs.

## 4. Platform faults in the two journals

- `sf` hangs in an isolated HOME: macOS "Keychain Not Found" dialog (chess F1/F13). Build or environment detail.
  Covered: "The CLI encrypts its org logins…".
- A custom tab record has a null `DeveloperName` (F7.1). Build detail (harness code). Partly covered: "A Tooling
  query on `CustomTab.Name` returns INVALID_FIELD…".
- An app page was rejected: region mode `REPLACE` without a parent region (F7.2). Build detail. Not covered.
- `sf apex run --file` returns the debug log HTML-escaped (F7.3). Build detail. Not covered.
- `AuraHandledException` raised from anonymous Apex becomes an uncatchable `LimitException` (F7.4; battleship
  journal; F11). Planning (test and oracle design). Not covered.
- ShipLoop cannot read human-format Apex output (F9 "Open"). Planning. Covered: "ShipLoop judges a focused Apex
  test…".
- The mutation gate mutates a local copy while the tests run against the org (F10, battleship live run 1). The
  journal files this as an engine defect. Planning. Covered: "These commands test the code deployed to the org…".
- An Improve pass went wrong over changed `.sf` tracking files (F10, Grok run 3, 2026-10-19). Planning. Covered:
  "The `sf` CLI writes its own state…".
- Battleship live run 1 (2026-10-18) committed `.sf` files at the return and failed `committed`. Planning. Covered
  by the same Tool state line.
- A tab hidden for lack of a grant (the battleship journal cites a brief on chess run 2; chess lists it as
  unproven). Planning. Covered: "A deployed tab or app is hidden…".
- The org created an unprefixed permission set mid-rehearsal; an assignment must be deleted before its permission
  set. Build or cleanup detail. Not covered.
- Chrome keychain dialog (F14). Not Salesforce (host OS). Not covered.

## 5. Gaps and contrary evidence

- **The card's rule B claim did not hold.** It says a focused command using human format "is refused as unread". In
  all nine runs, human-format Apex runs got status `passed` (`counts: null`, `ids_missing: []`), with zero refusals.
  The current `shiploop_test_loop.py` passes a run when its test IDs are found in the output, so the reporter is not
  judged.
- **Rule C's stated harm was absent in these runs.** It appears only in older runs (chess F10, battleship run 1).
  Here ShipLoop already kept `.sf` out of its commits.
- **Run 6 shows the card made no difference to the outcome.** It is the only run that read the whole card at
  discovery. It followed all three rules, and its outcome matched the others: eight of the nine runs passed, and run
  8 failed for an unrelated reason.
- **Not verified:** whether the chess tabs were actually visible to the CLI user. No run queried
  `PermissionSetTabSetting`: run 6's eight hits and the single hits in runs 2 and 4 are card text the model read,
  not queries run. No chess check grades visibility. Also unverified: what deleted run 7's `.sf` files.
- I relied on your earlier count for what each model was shown, and used `events.jsonl` only for which commands ran.
