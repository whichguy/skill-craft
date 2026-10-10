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
| The refusal for uncommitted review edits names `improve-commit` and the `--no-commit` exit | `shiploop_improve_changes.uncommitted`, `commit_refusal`; `shiploop_navigator._improve_change_gate` (now takes `core`) |
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
| yagni 3, tenet 2, code 1 and 2: the grammar refused real lessons (label alone then a blank line; a first body line `Word: text`) and accepted a heading that holds only `Co-Authored-By:` | A closed list of known labels ends a body; the first line after an empty label is body unless it is a known label, a heading or the trailer; a heading body is clipped at the trailer block and other sections; tests with fixtures in `test/fixtures/commit-contract/` |
| yagni 5, code: inline form and fence tracking | Cut (false-silence risk; 5 of 398 saved commits). The one-paragraph form is refused once, naming the forms that are read |
| tenet 1: the fork's `develop`/`deploy` lines for stage summaries | Not needed: the script-built bodies (Result blocks, the integrate `Learned:` block, the leftovers file list) were cut, so the engine copies no summary into a commit and the packet-size claim "the engine adds 0 packet bytes" is true again (the intake and discovery packets quote the last three commit messages, which do not grow) |
| tenet 3: `commit_refusal` kept a stale exit and no command | Line 1 is the fix and the command, last on the line; the exit for "the user said not to commit" is `improve-complete --no-commit`, and a test submits it through the real gate |
| tenet 3 and code: a refusal whose command is not on line 1 | One shared helper in `ImproveCommitContractTests` parses line 1 of every refusal and runs the command it ends with after the fix |
| code: a secret in a `Learned-from` token was echoed; the screen flags ordinary prose | Credentials are screened first and per line; the refusal names line numbers, never the text, and says to reword (`the lesson stays, only the value goes`) |
| code: `--disambiguate` clamps a token longer than any ID | `resolve_commit` requires the resolved ID to start with the token |
| code: the module alias `lessons` collides with a local name in the navigator | Imported as `commit_lessons` |
| yagni, tenet: `Section.form/.line`, trailers, the `learning` result schema, look-back | Not built |
| Contract option A | Built as a directive (see the byte arithmetic): commit only with `improve-commit`, never `git commit`; the child runs no callback except `improve-commit`; the command and rules are in `parent-return.md` |

## Method and evidence

Fail-first for each behaviour: the test was written and run, seen to fail for the intended reason, then the code was written. Tests that
pass before the change are labelled guards in their docstrings (the all-forms-accepted test, the nothing-to-commit text, a remote-change
section without the flag, the thinnest-contract fit). Every real-Git test sets `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null` and its own `HOME`.

| Evidence | File | Result |
|---|---|---|
| Parser table over message shapes taken from saved runs | `test/fixtures/commit-contract/` (13 messages and `expected.json`), `LessonsGrammarTests` in `test/shiploop-knowledge.test.py` | 11 tests |
| Git helper in real repositories | `CommitHelperTests` in the same file | 42 tests in the file pass |
| improve-commit through the real CLI | `ImproveCommitContractTests` in `test/shiploop-actual-improve-cli.test.py` | 21 tests; the first draft's 17 improve-commit tests failed 15 before the change (2 were guards) |
| Mutation check: 28 one-line breaks of the code, each must turn its tests red | `docs/experiments/commit-contract-engine-20261010/mutation_check.py` and `mutations.json` | 28 of 28 red, 74 failing tests in all |
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

"No empty commit" became "no empty commit except a recorded remote change": the bytes allow it (the whole clause costs 136), and without it
the authority would contradict a path that exists.

## Deviations from `task-b1.md`

- `improve_changes.commit_refusal` has a new shape: `uncommitted(changes, receipt)` returns the owed paths (the one owner of the `no_commit` rule),
  and `commit_refusal(paths, message_path, command)` builds the text. The gate builds the command only when it refuses, because a child that has no
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

## Deferred, with the trigger

| Cut | Trigger to build it |
|---|---|
| improve-complete notice counting commits without lessons, bind `head` key | The first live pair shows the harness count (`fidelity.model_commits` with `metrics.commits`, task H) is not enough |
| Script-built bodies (Result blocks, the integrate `Learned:` block, the leftovers file list) | Counted runs show stage summaries that carry a `Lessons:` line; carry-forward runs after integrate, so its lessons could reach git only through its own knowledge commit |
| A stage-level remote-change commit (release, release-verify, operations run no Improve child) | The first real remote case (the Salesforce developer-org test on the owner's list); then also `follow_up_knowledge_return` carrying a commit with no files |
| A `commit-tree` fallback for the empty commit | CI refusing `git commit --allow-empty --only` |
| A content check on lessons | Never by word list; the harness records the lesson text and `none` descriptively |

## Lines for the fork

None of this is edited here. Exact text and the symbol where it should appear.

1. `shiploop_navigator._render_improve`, the inline (not `planning_reconcile`) `runtime_lines` entry that starts "To commit a review iteration's
   changes, write the commit message (what the review fixed) to": replace the whole entry with the text below, and end the line with the command (the
   current entry prints " ." after it):

   > To commit a review iteration's changes, write the commit message to {message_path} with a file-writing tool. It needs a line `Key learnings: <what this iteration taught that a later iteration or run should reuse>` (`Key learnings: none` if it taught nothing new; a review that changed no file makes no commit). Optional: a line `Learned-from: <commit id> <what it contributed>` credits a commit that helped (ShipLoop checks the ID and writes the full one). For a change to a remote system that left no file change, add `Remote change: <system alias>, <what changed>, <where its evidence is>` and append `--remote-change` to the command. Each goes on a line of its own, not inside one paragraph. Do not write the message with a shell heredoc or run git commit yourself: a hand-typed commit skips these checks. Then run: {improve-commit command}

2. `shiploop_navigator._render_improve`, the `planning_reconcile` branch of `runtime_lines` (it has a "Commit policy:" line and no improve-commit
   entry, 0 of 8 saved plan-stage packets print the command): add after the "Commit policy:" line, with `{parent_return}` =
   `standalone.receipt_path(child).with_name("parent-return.md")`:

   > To commit a review iteration's changes, run the improve-commit command in {parent_return}; its message rules are there. ShipLoop commits exactly the files this review changed. Do not run git commit yourself.

   The frozen contract and `parent-return.md` already carry the command and rules for this child, so this line is belt and braces.

3. `shiploop_navigator._checked_line/_stage_gates`, where the Improve parent packet lists what its callbacks refuse:

   > improve-commit refuses a message with no `Key learnings:` line, a `Learned-from:` line that names no commit reachable from HEAD, or credential-looking text; improve-complete refuses a review whose edits are uncommitted (commit them with improve-commit, or pass `--no-commit` with the user's instruction).

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
| The engine lowers the raw-git bypass | Exploratory (unmeasured) |

## Commits

`e80b11bf` the grammar module; `71e47321` the git helper; `b8a315da` improve-commit checks and `commit_refusal`; `22498a3d` `--remote-change`;
`9e56a59c` the contract authority and `parent-return.md`; `88b1e710` the credential refusal counts lines like the grammar; the journal
commit after them.
