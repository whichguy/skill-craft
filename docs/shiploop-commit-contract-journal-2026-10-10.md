# The commit contract, engine side: journal (2026-10-10, batch 1012 task B1)

Plan v5 step B, first series. Base `658ff4e3`, branch `batch1012b-1bbefb`. The plan is
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md` (sections 0d and "Plan of action v5"). Packet text, card text, `render()`,
`packet_head()`, `DUTIES`, `stage_lines`, `_render_improve` and `_checked_line/_stage_gates` belong to the E2E fork and were not edited;
what they need to print is under "Lines for the fork" below.

## Question

Can ShipLoop make every Improve commit carry what the iteration learned, check the commits it cites, and record a change to a remote
system as a commit with no files, without a refusal costing a cleared model more than one turn, and without a packet-text change?

## What was built

| Concern | Where |
|---|---|
| The one reader of the commit-message grammar: lessons, a remote change, cited commits | `skills/shiploop/scripts/shiploop_lessons.py` (`sections`, `lessons`, `remote_change`, `citations`, `with_full_ids`, `LESSON_LABELS`); imports nothing from ShipLoop |
| `--cleanup=whitespace` on every ShipLoop commit; an empty commit that keeps the index; Git-resolved commit IDs | `shiploop_git.commit_paths`, `shiploop_git.resolve_commit` |
| `improve-commit`: file checks, bind refusals with a remedy, nothing to commit, credentials, lessons and citations in one refusal, commit | `shiploop_navigator._improve_commit`, `_credential_refusal`, `_lessons_and_citations_refusal` |
| `improve-commit ... --remote-change` | `shiploop_protocol` (the argument), `_improve_commit` (the path) |
| The refusal for uncommitted review edits names `improve-commit`, and the `improve-complete` command to run again and with `--no-commit` | `shiploop_improve_changes.uncommitted`, `commit_refusal`; `shiploop_navigator._improve_change_gate` (now takes `core`) |
| The frozen contract lets the child run `improve-commit` and points at `parent-return.md` | `shiploop_navigator.improve_start_contract` (the authority) |
| The command and the message rules for a cleared child | `shiploop_navigator._improve_start` (`parent-return.md`) |
| References | `project-knowledge.md` (Learnings commit and read-back), `improve-context.md`, `state-files.md`, and the Improve skill's `references/callback-evidence.md` (citations go on a `Learned-from:` line) |

`knowledge_home.learnings()` (the release-verify gate on `outcome.md`) stays on its own heading-only parse; nothing about that gate changed.

## Decisions on the design and its three audits

The audits (yagni, tenet, code lenses) converged on "build a smaller version"; `task-b1.md` decided where they and the design disagreed.
The design and audits are kept whole in `docs/experiments/commit-contract-design-20261010/design-and-audits.json`.

| Finding | Disposition |
|---|---|
| yagni 1: a `Remote change: none` label must not make an empty commit or skip the nothing-to-commit rule (D4) | Fixed by construction: the empty commit needs the explicit flag; without it the section changes nothing (test `test_a_remote_change_section_without_the_flag_changes_nothing`, a guard) |
| yagni 2, code 2: the bind `head` key tolerates old artifacts, against "one supported version" | Cut with its only users: no `head` key, no `window_commits`, no `messages_since`, no improve-complete notice, no already-recorded guard (the message file is consumed on success; a duplicate empty commit is harmless) |
| yagni 3, tenet 2, code 1 and 2: the grammar refused real lessons (label alone then a blank line; a first body line `Word: text`) and accepted a heading that holds only `Co-Authored-By:` | A closed list of known labels ends a body; the first line after an empty label is body unless it is a known label or a heading; a heading body is clipped at other sections and at a known trailer; tests with fixtures in `test/fixtures/commit-contract/`. **Superseded in part 2026-10-10 (review round 1, R2):** the first draft also clipped the last paragraph as a trailer block by its shape (`Hyphenated-Token: value`), which read a lesson written as `Root-cause:` lines as empty; a trailer is now known by name (`Co-Authored-By`, `Signed-off-by`, `No-Change-Note`, `Skill-Craft-Release`) |
| yagni 5, code: inline form and fence tracking | Cut (false-silence risk; 5 of 398 saved commits). The one-paragraph form is refused once, naming the forms that are read |
| tenet 1: the fork's `develop`/`deploy` lines for stage summaries | Not needed: the script-built bodies (Result blocks, the integrate `Learned:` block, the leftovers file list) were cut, so the engine copies no summary into a commit and adds no packet text of its own. **Softened 2026-10-10 (R10):** `knowledge_home.recent_commits` quotes the last three commit messages in full and without a bound, so the intake and discovery packets grow in later runs by what those messages carry (a lesson, a `Learned-from:` line with a 40-digit ID and its contribution), though not by anything the engine writes into a packet |
| tenet 3: `commit_refusal` kept a stale exit and no command | Line 1 is the fix and the command, last on the line; the exit for "the user said not to commit" is `improve-complete --no-commit`, and a test submits it through the real gate |
| tenet 3 and code: a refusal whose command is not on line 1 | One shared helper in `ImproveCommitContractTests` parses line 1 of every refusal and runs the command it ends with after the fix |
| code: a secret in a `Learned-from` token was echoed; the screen flags ordinary prose | Credentials are screened first and per line; the refusal names line numbers, never the text, and says to reword (`the lesson stays, only the value goes`) |
| code: `--disambiguate` clamps a token longer than any ID | `resolve_commit` requires the resolved ID to start with the token |
| code: the module alias `lessons` collides with a local name in the navigator | Imported as `commit_lessons` |
| yagni, tenet: `Section.form/.line`, trailers, the `learning` result schema, look-back | Not built |
| Contract option A | Built as a directive (see the byte arithmetic): commit only with `improve-commit`, never `git commit`; the child runs no callback except `improve-commit`; the command and rules are in `parent-return.md` |

## Method and evidence

Fail-first for each behaviour: the test was written and run, seen to fail for the intended reason, then the code was written. Tests that
pass before the change are labelled guards in their docstrings (the all-forms-accepted test, a remote-change section without the flag, the
thinnest-contract fit; the nothing-to-commit test is not a pure guard: it fails on the base source for its last assertion, the message file
being consumed, and its docstring says so. **Corrected 2026-10-10 (R10):** the first version of this paragraph listed it as a guard).
Run against the base source `658ff4e3` (copied from `git archive` into the scratchpad), 21 of the 25 tests in `ImproveCommitContractTests` fail
and 4 pass: the all-forms guard, the thinnest-contract guard, the no-notice-without-a-section guard and the hyphenated-lesson route test (the base
has no lessons check, so it accepts any message; that test is red against the first draft's grammar, see the mutation rows). Every real-Git test sets `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null` and its own `HOME`.

| Evidence | File | Result |
|---|---|---|
| Parser table over message shapes taken from saved runs | `test/fixtures/commit-contract/` (15 messages and `expected.json`), `LessonsGrammarTests` in `test/shiploop-knowledge.test.py` | 14 tests (11 at the first draft) |
| Git helper in real repositories | `CommitHelperTests` in the same file | 11 tests (9 at the first draft); the file holds 47 and passes (the first draft's "42" was the whole file) |
| improve-commit through the real CLI | `ImproveCommitContractTests` in `test/shiploop-actual-improve-cli.test.py` | 25 tests (21 at the first draft); the first draft's 17 improve-commit tests failed 15 before the change (2 were guards); today 21 of 25 fail on the base source |
| Mutation check: 28 one-line breaks of the code, each must turn its tests red | `docs/experiments/commit-contract-engine-20261010/mutation_check.py` and `mutations.json` | 42 of 42 one-line breaks turned their suite red (run to completion on 2026-10-10 after the review round; the three source files were clean in Git before and after) |
| What the grammar reads in saved runs | `docs/experiments/commit-contract-engine-20261010/scan_saved_commits.py` and `saved-commits-scan.json` | 398 commits in 35 repositories: Improve-style 46, of which 41 are read and 5 (all from `20261010/battleship-1`) write every label in one paragraph and are not; script `docs(shiploop):` commits 236, of which 29 carry lessons; other 116, of which 2; Remote change 0; citation lines 0 |
| Contract bytes with the real builder | `docs/experiments/commit-contract-engine-20261010/contract_bytes.py` and `contract-bytes.json` | see below |

The design's own figure (72 of 384 commits read, 42 of 42 Improve-style) used the inline form; with that form cut the same commits read 41 of 46,
and the 5 misses are one run's habit. If the fork's packet line shows the format, the first message is right; otherwise the first message is
refused once with "on a line of its own".

## Byte arithmetic (step 5)

The frozen commit-policy clause is 448 bytes without its path against 312 for the clause it replaced: **+136 bytes at every stage and route**.
Against the spike's measurements (`b1012s`): the pointer wording was +234, the full rule +874 to +950. The thinnest saved contract is a
carry-forward child of the Grok run `r1-battleship-grok-none`, 8,135 of 9,216 bytes (1,081 left). Rebuilt with the real builder at that size
and the new clause: **8,271 bytes inline (945 left) and 8,540 on the delegated route (676 left)** for each of the eight Improve stages. The
opening allowance printed to the model drops by 136 (spec, inline: 4,828 to 4,692). `parent-return.md` is a run file (3,085 bytes in the test
fixture, whose paths are long) and costs no contract bytes: the contract already lists it as a resource.

**Path sensitivity (added 2026-10-10, R11).** The thin-case figures above use the test fixture's path lengths. The clause delta (+136) does not depend on
paths; the delegated route's resource row does: 269 bytes in the fixture, 275 to 290 on the spike's saved paths (288 for the thin case), so the
delegated thin case has about 657 bytes left on saved paths, not 676. With the checkout and run paths 100 characters longer, the spike's pointer
wording (+234, -53 left) would be 98 bytes cheaper here, about 45 bytes left inline for the thinnest saved child. None of this changes a verdict: every
stage still fits both routes with the saved paths of the 92 sampled children.

"No empty commit" became "no empty commit except a recorded remote change": the bytes allow it (the whole clause costs 136), and without it
the authority would contradict a path that exists.

## Deviations from `task-b1.md`

- `improve_changes.commit_refusal` has a new shape: `uncommitted(changes, receipt)` returns the owed paths (the one owner of the `no_commit` rule),
  and `commit_refusal(paths, message_path, command, complete_command)` builds the text (the fourth argument is the review-round addition, R6). The gate builds the command only when it refuses, because a child that has no
  edits to commit may be a stub in a unit test. The one call site and the unit test were updated.
- The new parser tests and the git tests live in `test/shiploop-knowledge.test.py` (no new top-level suite, so `test/suite_catalog.py` has no new
  entry); only the recorded seconds of `shiploop-actual-improve-cli` (45.762 to 62.0) and `shiploop-knowledge` (3.64 to 4.5) changed.
- `--allow-empty --only` was kept; the `commit-tree` fallback was not written (see the risks).
- The Improve card's ShipLoop subcall paragraph already says "do not use ... `git commit` for it", so the card was not edited; its Commit policy
  bullet still says `git commit --only` (card and fork owned).
- `improve_start_contract` keeps the card's "scoped-commit policy" reference: dropping it would also drop the card's record body (Review, Plan,
  Changes, Validation, Key learnings, Remaining work), which `improve-commit` does not check.

## Existing tests changed because the behaviour changed on purpose

- `test_improve_commit_commits_only_the_reviews_uncommitted_changes` (`shiploop-actual-improve-cli`): its message had no lessons, and it relied on a
  no-op leaving the message file; it now asserts the no-op consumes the file and writes a message with `Key learnings:` before the real commit.
- `shiploop-improve-changes`: `commit_refusal`'s new shape (`uncommitted`), and the calls to `_improve_change_gate` pass `core` (`None`).
- Nothing else changed: the quick tier and the footprint suites pass (see the report).

## Review round 1 (2026-10-10, the fix round)

Two independent reviewers (code and tenet lenses) read head `479a01af` and returned 12 findings (1 major, 11 minor). Method: reproduce each through the
real CLI or the module, write the failing test first where it is a code defect, fix, see it pass, then break the fix and see the test go red (the
new mutation rows). Fix commits: `7d9e4255` (grammar), `77b5de03` (resolve_commit tests), `387c5937` (refusals), `4a928eeb` (column-1 wording).

| # | Finding (lens, severity) | Disposition | Evidence |
|---|---|---|---|
| R1 | No test cites a strict ancestor of HEAD, so a resolver accepting only HEAD, or asking merge-base the wrong way round, stayed green (code, major) | **Fixed** (tests; the code was right) | `CommitHelperTests` older commit, ahead-of-HEAD, Git-failure tests; CLI test with an older and an ahead commit. Mutants "HEAD only" and "arguments swapped" red in both layers (the swap was caught only by the CLI class before) |
| R2, R8a | A lesson that is a final paragraph of `Hyphenated-Token: value` lines (`Root-cause:`, `Follow-up:`, `Re-run:`) read as the trailer block: the section came out empty and the refusal said "has no text" (code and tenet, minor) | **Fixed** | Trailer is known by name; `_trailer_start` and its shape regex are gone. Fail-first: 12 failures and 4 errors before, 0 after. `scan_trailer_shapes.py` / `trailer-shapes.json`: 895 final paragraphs over 1,706 commits (36 repositories) are all trailer-shaped and every one holds a known trailer, so saved data never misfired, and 17 other hyphenated line starts (`Non-regression:` 17, `Self-test:`, `Fail-first:`, `Mutation-checked:`...) show the shape is also how lessons are written. `scan_saved_commits.py` over the 398 saved run commits is byte-identical after the change. One deliberate change: a `No-Change-Note:` line directly under lesson text now ends the lesson |
| R3 | A real `Remote change:` section with no flag and no pending file is dropped silently (code, minor) | **Fixed**, optional half **disagreed** | The no-op now prints that the section changes nothing without `--remote-change` and the exact command (conditional wording, since the file is consumed and a `none` writer must not be pushed to the flag). Disagreed: refusing a section that is just `none` when the flag is passed would need a word list (invented judgement, against "no invented thresholds"); with the explicit flag the model asked for the record, the audit's blocker was the flagless path, and a duplicate empty commit is harmless |
| R4 | `re.IGNORECASE` matched dotless i and long s, then `KeyError` (code, minor) | **Fixed** | `IGNORECASE \| ASCII` on the label and heading patterns (the citation pattern has no foldable letter). Fail-first: 4 errors and 1 failure (the Kelvin sign was read as a `k`) before. The ASCII flag dropped from either pattern is red |
| R5 | Surviving mutants: a bare label word ending a body, trailer continuation lines, the Git other-error branch (code, minor) | **Fixed** | Pins for the first and third; the second no longer exists (it was part of the shape rule). New rows in `mutation_check.py` |
| R6 | The uncommitted-edits refusal did not print the improve-complete command; two refusals' named exits were not run (code, minor) | **Fixed** | `commit_refusal` takes the command and prints it to run again and with `--no-commit "<their instruction>"`; the CLI tests parse those lines out of the refusal and submit them to the real gate; the empty-lessons-label and empty-remote-commit tests now run their named exit |
| R7 | Near-miss spellings are refused or ignored: `Learned from:`, an indented `Learned-from:`, `Learned-from: commit: abc`, `Learned-from: none`, indented or numbered labels (code, minor) | **Deferred** (by design) | An indented label is a quote or a code block in a commit message (tested: `    Key learnings: x` is not read); a space for the hyphen is not a citation and is not counted; the rest are refused once with the fix on line 1 (deleting a citation line is always valid). The refusal, `parent-return.md` and the reference now say "starting in column 1". Trigger to tolerate more: the live pair shows first-turn refusals by first line |
| R8b | A bare known label does not end a body although the docstring said it did; indented labels and `Key takeaways:` are not read (tenet, minor) | **Fixed** (docstring) | Code kept on purpose: a lone `Plan` or `- Review` can be a lesson's own words, and the cost of the other direction is a truncated lesson (a false refusal); the accepted direction is an extra line in a lesson. Pinned by a test; the docstring now says "a known label with its colon" |
| R9 | The no-bind-snapshot refusal told the bound child to run `improve-complete`, which its contract forbids (tenet, minor) | **Fixed** | Line 1 says the bound child stops and the parent imports the review ("Parent, run: ..."); the command stays last on line 1; the test asserts both |
| R10 | Overclaims in the change note and this journal (tenet, minor) | **Fixed** | (1) a Git failure inside `improve-commit` now says "Git could not make the commit: fix the repository problem named below, then run: <command>" (tested with a real `index.lock`), so "every refusal puts the fix and the command on line 1" is true; (2) the guard list, (3) the test counts and (4) the packet-growth claim are corrected above, each marked; (5) see the Deferred table; (6) accepted: the citation refusal names the file, says to delete a line and lists the failing lines below |
| R11 | Headroom figures lack their path sensitivity (tenet, minor) | **Fixed** | Paragraph "Path sensitivity" under the byte arithmetic. `contract_bytes.py` rerun: the clause delta is +136 at every stage and route, unchanged |
| R12 | A docstring re-wrap in `_improve_change_gate` is diff noise next to the fork's file (tenet, minor) | **Fixed** | Reverted to the base wrapping |

Key learning of the round: shape is a poor test for "is this a trailer", because the shape a trailer has is also the shape a model gives a lesson line;
names are cheap and the history says which names there are. And a test that builds the exit command itself proves the command exists, not that
the refusal names it: parse the command out of the text and run that.

## Deferred, with the trigger

| Cut | Trigger to build it |
|---|---|
| improve-complete notice counting commits without lessons, bind `head` key | The first live pair shows the harness count (`fidelity.model_commits` with `metrics.commits`, task H) is not enough |
| Script-built bodies (Result blocks, the integrate `Learned:` block, the leftovers file list) | Counted runs show stage summaries that carry a `Lessons:` line; carry-forward runs after integrate, so its lessons could reach git only through its own knowledge commit |
| A stage-level remote-change commit (release, release-verify, operations run no Improve child) | The first real remote case (the Salesforce developer-org test on the owner's list); then also `follow_up_knowledge_return` carrying a commit with no files |
| A `commit-tree` fallback for the empty commit | CI refusing `git commit --allow-empty --only` |
| A content check on lessons | Never by word list; the harness records the lesson text and `none` descriptively |
| A `Remote change` commit with no files on the patch-apply return route (a delegated child's commit travelling back to the parent's checkout) | Untested: the commit is made in the checkout the child works in, and a fast-forward return carries a commit with no files like any other, but no test returns one. The first delegated remote case, or the Salesforce developer-org test, should include the return |
| Tolerating indented labels, `Learned from:` and `Learned-from: commit: <id>` | The live pair shows them as first-turn refusals (R7) |

## Lines for the fork

None of this is edited here. Exact text and the symbol where it should appear.

1. `shiploop_navigator._render_improve`, the inline (not `planning_reconcile`) `runtime_lines` entry that starts "To commit a review iteration's
   changes, write the commit message (what the review fixed) to": replace the whole entry with the text below, and end the line with the command (the
   current entry prints " ." after it):

   > To commit a review iteration's changes, write the commit message to {message_path} with a file-writing tool. It needs a line `Key learnings: <what this iteration taught that a later iteration or run should reuse>` (`Key learnings: none` if it taught nothing new; a review that changed no file makes no commit). Optional: a line `Learned-from: <commit id> <what it contributed>` credits a commit that helped (ShipLoop checks the ID and writes the full one). For a change to a remote system that left no file change, add `Remote change: <system alias>, <what changed>, <where its evidence is>` and append `--remote-change` to the command. Each goes on a line of its own starting in column 1, not inside one paragraph. Do not write the message with a shell heredoc or run git commit yourself: a hand-typed commit skips these checks. Then run: {improve-commit command}

2. `shiploop_navigator._render_improve`, the `planning_reconcile` branch of `runtime_lines` (it has a "Commit policy:" line and no improve-commit
   entry, 0 of 8 saved plan-stage packets print the command): add after the "Commit policy:" line, with `{parent_return}` =
   `standalone.receipt_path(child).with_name("parent-return.md")`:

   > To commit a review iteration's changes, run the improve-commit command in {parent_return}; its message rules are there. ShipLoop commits exactly the files this review changed. Do not run git commit yourself.

   The frozen contract and `parent-return.md` already carry the command and rules for this child, so this line is belt and braces.

3. `shiploop_navigator._checked_line/_stage_gates`, where the Improve parent packet lists what its callbacks refuse:

   > improve-commit refuses a message with no `Key learnings:` line, a `Learned-from:` line that names no commit reachable from HEAD, or credential-looking text; improve-complete refuses a review whose edits are uncommitted (commit them with improve-commit, or pass `--no-commit` with the user's instruction; its refusal prints both improve-complete commands).

4. Card owner, `skills/improve/SKILL.md` (needs `changes/improve/<slug>.md`, bump patch): the Commit policy bullet's "Use a scoped commit such as
   `git commit --only -- <authorized paths>`" should add "(inside a ShipLoop run use the improve-commit command in parent-return.md)", and the
   ShipLoop whole-skill subcall paragraph's "When the ShipLoop packet prints an `improve-commit` command" should read "prints, or parent-return.md
   lists, an `improve-commit` command".

## Open risks, and what was not verified

- **Linux git.** `git commit --allow-empty --only` with no paths was tested on Apple Git 2.54.0 only. If CI's git refuses it the remote-change tests
  fail first; the fallback is `commit-tree HEAD^{tree} -p HEAD` plus `update-ref`, which never touches the index.
- **First-turn refusals.** Until the fork's packet line shows the format, a child may be refused once on its first iteration (no lessons, or a
  one-paragraph message). Each refusal puts the fix, the path and the command on line 1, and "or none" is on line 1, so the cheapest answer is not
  a filler lesson. Not measured on a live model; the live pair measures refusals by first line.
- **Filler lessons.** The gate checks presence, never substance; `Key learnings: none` counts. The harness records the text.
- **Raw `git commit` cannot be prevented** (hooks are disabled on purpose). The route is made available and named in the contract, the refusal and
  `parent-return.md`; whether it removes the 35% bypass is unmeasured.
- **The credential screen flags ordinary prose** (`the session token: it expires hourly`); the refusal says to reword, and names the line.
- **Rebase surface with the fork's release A:** both touch `shiploop_navigator.py`. This series edits only `_improve_commit` (and two helpers
  before it), `_improve_change_gate`, the `improve-complete` call to it, the authority string in `improve_start_contract` and the
  `parent-return.md` text in `_improve_start`.
- **S-14 (unattended):** every refusal is fixable by the model and none waits on stdin.

## Status of the findings

| Finding | Status |
|---|---|
| A closed list of known labels, not a generic `Word:` pattern, must end a body (else a lesson whose first line is `Pitfall: x` is refused and the refusal asks for what is already there) | Firm (a test and a mutation) |
| The empty commit needs an explicit flag; a section is not a statement that something happened | Firm |
| A pointer in the frozen authority plus a file the contract already names carries the rule for +136 bytes and reaches the planning child | Firm for the bytes; interim for whether a model reads it (no live run) |
| The one-paragraph habit of one saved run (5 of 46 Improve-style commits) is refused once | Interim |
| `--allow-empty --only` on the Linux CI git | Unverified |
| A trailer is known by name, not by shape (`shiploop_lessons._TRAILERS`) | Firm (895 of 895 shape-trailer paragraphs hold a known name in saved data; the shape also carries lesson lines; a test and four mutants) |
| Every `improve-commit` refusal puts the fix and the command on line 1 (the Git failure included) | Firm for the refusals tested through the real CLI; interim for how a model behaves on them (no live run) |
| The engine lowers the raw-git bypass | Exploratory (unmeasured) |

## Commits

`e80b11bf` the grammar module; `71e47321` the git helper; `b8a315da` improve-commit checks and `commit_refusal`; `22498a3d` `--remote-change`;
`9e56a59c` the contract authority and `parent-return.md`; `88b1e710` the credential refusal counts lines like the grammar; `479a01af` the
journal. Review round 1: `7d9e4255` the trailer is known by name and labels match as ASCII; `77b5de03` resolve_commit tests on an older commit,
a commit ahead of HEAD and a Git failure; `387c5937` the refusals (improve-complete commands, the bound child, the forgotten flag, a Git failure,
column 1); `4a928eeb` column 1 in `parent-return.md` and the reference; then the evidence commit.
