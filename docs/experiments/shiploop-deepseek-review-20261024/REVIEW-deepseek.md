# Outside review: ShipLoop, skill-craft 2.9.0 (`origin/main` at 31933a73)

Reviewer: outside review requested by the owner. Scope: the ShipLoop skill and the one Improve file it
binds. No commit, no push, no edit to the repository — this file is the only artifact, and the probes it
cites live in a session scratchpad (paths in the appendix, with their source so they can be re-created).

What I did: read the navigator, test loop, mutation check, loops, prompts, stage spec and the references;
wrote and ran an offline dry run of the two-work-item scenario (42 packets, 546 KB) and measured every
printed head; read `test/shiploop_e2e/LEARNINGS.md` in full; ran the whole test-loop module
(`test/shiploop-test-loop.test.py`, **161 tests, OK, 404.6 s**); and wrote two probes that drive the real
navigator path and count what ShipLoop actually executes.

Each claim below is marked **[observed]** (I ran it, or I read the line and quote it) or **[inferred]**
(follows from the code but no run shows it). Where a claim is inferred I say what would confirm it.

Ranking rule used: gain in speed or code quality on an *ordinary* run of *any* project, against cost and
risk. Items that only touch a review or audit surface are in "considered and rejected", not here.

## Summary

| # | Recommendation | Main effect | Size |
|---|---|---|---|
| 1 | Reuse a passed base run and mutation check the way the candidate run is already reused | ~50% of the test stage's command runs, per item, before counting 4–11 check-only calls | ~80 lines + tests |
| 2 | Give the Improve review a materiality bar for planning documents | Planning Improve is the largest single block of a run (46.6 of 78.8 min, 34 of 48 min); 4 of 36 passes were material | ~6 lines of prompt |
| 3 | Take dependency directories from the platform card, not three hardcoded names | Base runs work on projects whose dependencies are not in `node_modules`/`.venv`/`venv`; removes an ecosystem name from a core script | ~25 lines + 4 card lines |
| 4 | A base-run `not-run` refusal says when the command never reached the tests | One wasted round trip per start failure, and it stops the model rewriting a test that was never wrong | ~10 lines |
| 5 | The base-run `unread` refusal names three ecosystems; point at the platform card instead | Tenet 3 in a refusal the model reads | 2 lines deleted |

---

## 1. Reuse the base run and the mutation check the way the candidate run is already reused

**Problem.**

`complete --check-only` at the test stage runs three gates, and two of them redo work already done
minutes earlier on the same tree.

- `skills/shiploop/scripts/shiploop_navigator.py:_test_loop_gate` (4291), check-only branch: it calls
  `test_loop.red_check(...)` (which is `_base_run`), then `loop_run(..., count=False)`, then
  `mutation_check(..., count=False)`. The ordinary branch calls `base_check`, `loop_run`,
  `mutation_check`. **[observed — the code]**
- `shiploop_test_loop.py:_base_run` (1769) has no reuse: it builds a `_BaseTree` (1539 — a
  `git worktree add --detach` plus a copy of the item's test files), runs every command, writes a new
  record. `base_check` (1867) and `red_check` (1924) both go through it. **[observed]**
- `shiploop_mutation.py:_check` (288) has no reuse either: it recomputes `_current_tree`, the changed
  product lines, the deterministic sample (`sample`, 212) and then runs the focused commands once
  unmutated and once per mutant. **[observed]**
- Reuse exists only for the *candidate* run: `shiploop_test_loop.py:_reused` (1152), used by `verify`
  (1203); `loop_run` then prints `candidate: reused the passed check-only run of <created_at> ...`
  (1399). `state-files.md:30` documents that reuse and the step-Proof reuse, and says nothing
  about the base run or the mutation check. **[observed]**
- `shiploop_loops.py:WORK["test"]` (79, text at 82) tells the model that check-only "runs the base run,
  the candidate run and the mutation check without counting", and `REPEAT["test"]` (124, text at 126)
  makes "a check-only refusal" a repeat condition. `shiploop_prompts.py:1463` tells the model to run
  "every recorded command, the red-check command and the lint command" after *each* change. So the base
  run is instructed after every edit, again on every check-only, and again at `complete`. **[observed]**

What that costs, measured on the real navigator path with the tree unchanged between the three calls —
probe 1 in the appendix, which drives `red_check` → `complete_output(check_only=True)` →
`complete_output(check_only=False)` through the fixture's own loop:

```
red-check (the packet's own command): 2 command runs (0 in the checkout, 2 elsewhere)
complete --check-only:                8 command runs (2 in the checkout, 6 elsewhere)
complete (the real callback):         6 command runs (0 in the checkout, 6 elsewhere)
```

**[observed]** Sixteen command runs for one pass. The candidate's own two run once (that is the reuse that
exists, at `complete`), but the base run executes three times — 6 command runs plus three
`git worktree add` checkouts — and the mutation check twice, 8 command runs. Eight of the sixteen are
therefore repeats of work already done in the same pass: four base-command runs and four mutant runs. The
4-runs-per-mutation-check split is one unmutated run plus one per mutant of this fixture's `calc.py`
**[inferred from `_check`]**.

Scale it with the journal's own count — "runs `complete --check-only` (4-11 calls per item)"
(`test/shiploop_e2e/LEARNINGS.md:2131`) **[observed, quoted]** — and `N` check-only calls give `N+1`
mutation checks and `N + (red-checks) + 1` base runs per item. The mutation check executes a project's
focused commands once per mutant (up to `MUTANT_SAMPLE = 8`, `shiploop_mutation.py:49`) under a 600 s
budget (`MUTATION_BUDGET_SECONDS`, 56); the base run executes the focused *and regression* commands
under a 1,800 s budget (`STAGE_BUDGET_SECONDS`, `shiploop_test_loop.py:88`) **[observed — constants]**.
These are the only places ShipLoop runs the project's own commands repeatedly, so the waste is the
project's suite length multiplied by the calls that repeat it. **[inferred]**

**Plan.**

1. `shiploop_test_loop.py`: factor the reuse key and lookup out of `_reused` (1152) into one helper, then
   call it from `_base_run` (1769) before `_BaseTree` is built. The key is what the base run's result
   depends on, all of it already in the record or derivable:
   `{base_tree, base_commit, red_na, retired_tests, commands: [{command, suite, ids}], test_files:
   [{path, blob}]}` — the blob per test file is the point: the base run copies the item's *test files*
   into the base worktree (`_BaseTree._make`, 1560-1595), so an edit to a test file must invalidate the
   record, and an edit to product code must not.
   Search the latest record among `tests/<action>-base*.md` and `tests/<action>-red-check.md` with
   `passed: true`; on a hit return the record with `reused = {path, created_at, key}`. Never reuse a
   failed record. Mirror the `candidate: reused …` line so `complete` prints
   `base: reused the passed run of <created_at> (<path>)`.
2. `shiploop_mutation.py:_check` (288): the same lookup with
   `{base_tree, base_commit, candidate_tree, product_files, focused commands, sample_size, remote_commands_skipped}`.
   `sample` is deterministic (**[observed]**, its docstring says so and it has no RNG), so a record with
   the same key is the same check. Search `tests/<action>-mutation*.md` and
   `tests/<action>-mutation-check-only.md`.
3. `shiploop_navigator.py:_test_loop_gate` (4291), check-only branch: drop the `mutation_check` call. It
   is the most expensive gate, and on a half-written draft it is the one most likely to refuse for the
   wrong reason (it refuses when no mutant was killed at all, `shiploop_mutation.py:414`), so its early
   signal is mostly noise; `complete` runs it once on the finished candidate. Keep the base gate and the
   candidate gate there — `LEARNINGS.md:2501` records that the one check-only refusal that mattered was
   the base run **[observed, quoted]**.
4. Documentation: `state-files.md:30` and `references/test-loop.md` (base run, line 27 ff.) say in one
   clause that a passed base-run or mutation-check record is taken again when the base, the item's test
   files, the candidate and the commands are unchanged.
5. Tests, in `test/shiploop-test-loop.test.py` beside the existing candidate-reuse pair (2179, 2197):
   (a) an unchanged tree reuses the base run and the mutation check and both records say `reused`;
   (b) one byte changed in a *test* file reruns the base run (its copied test file changed) and the
   mutation check (the candidate changed); (c) one byte changed in a *product* file reruns the mutation
   check but not the base run; (d) a failed record is never reused, for either gate.

**Expected effect.** On the measured pass: 16 → 8 command runs, and three base-worktree checkouts → one.
Per item with one red-check and four check-only calls: base runs 6 → 1–2 (2 if the test files changed
between drafts, 1 if not) and mutation checks 5 → 1. Run time falls in proportion to the project's own
suite, which is the only suite ShipLoop runs, so on a project whose suite takes minutes the saving is
tens of minutes per item. **[inferred from the probe + LEARNINGS:2131]** No effect on tokens or on what is
judged. Rough size: ~80 lines in two scripts, one helper moved, plus tests.

**Cost and risk.** The risk is a stale reuse: the key must cover everything the record depends on. The
test-file blob hashes and `base_commit` cover the base run; `candidate_tree` plus `product_files` cover
the mutation check. The same class of risk the candidate reuse already accepts (environment, network) is
unchanged. Second risk: dropping the mutation check from check-only means a mutation refusal can arrive
one call later; that is one extra `complete` for the item in which it happens, against one saved
mutation run per item always. Cost: one helper refactor and a careful key.

**Verify by.** The four tests above (script-run, hermetic). Then the E2E measure: in `metrics.json`,
compare the test stage's seconds and its command counts per item with run 4's, and count the
`<action>-base*.md` and `<action>-mutation*.md` records per item — they should fall from `N+2` and `N+1`
to 1–2 and 1.

**Tenets touched.** Tenet 2 (scripts own decisions): this is the scripts deriving from recorded state, the
same pattern `_reused` already uses. Tenet 6 (evidence is a script-run test): the reuse is proven by the
existing `counting_runner` mechanism (2124) plus the new tests. Tenet 5 (no shims): no old record is
migrated; a record without a key is simply not reused. Tenets 1, 7, 8 are untouched — no packet text is
moved, no duty is dropped, no new term is introduced (`reused` already means this, `state-files.md:30`).

---

## 2. Give the Improve review a materiality bar for planning documents

**Problem.** The largest measured block of a live run is Improve on planning stages, and its stop rule
cannot be reached by classifying a document change as trivial, because the rule is written in terms of
behaviour.

- `skills/improve/references/shiploop-route.md:23-27`, "Trivial classification": *"Trivial work is
  non-semantic spelling, formatting or explanatory polish with evidence that behavior is unchanged. A
  one-line bug fix, public-contract change, security or data-integrity correction, or missing required
  regression coverage is material."* **[observed, quoted]** A `spec.md` or a plan has no behaviour, so
  the trivial branch cannot be satisfied by any document edit; a reviewer applying this rule strictly has
  to call every document finding material.
- The stop rule needs the opposite: `skills/improve/references/review-policy.md:69` — "only trivial
  findings and fixes, or no changes, no unresolved material finding" (owner decision 2026-10-20: a second
  confirming cycle added time without results) **[observed, quoted]**. With no trivial branch available
  for documents, a pass that finds a wording problem must fix it, which forces another pass.
- The journal names both halves: *"The stop rule … forces at least two more passes after any edit, and
  the review focus has no materiality bar. Across 36 passes up to 174 min, 4 were material."*
  (`LEARNINGS.md:2472`) **[observed, quoted]**
- Measured cost: planning 78.8 min of a 240-minute cap, of which "5 Improve children tak[e] 46.6 of
  those minutes" (`LEARNINGS.md:2507`) **[observed, quoted]**; battleship planning 48 min against 17–20
  with planning review off, "Improve took 34 (spec 3 passes, test-strategy 7, plan 4)"
  (`LEARNINGS.md:2472`) **[observed, quoted]**; run 2 "Improve 49% of time and output (21 passes over
  five stages: 8 material, 10 made no change)" (`LEARNINGS.md:2283`) **[observed, quoted]**.
- And the direction is already proven: "**Improve on the first item, with one trivial pass, pays.** Its
  passes halved." (`LEARNINGS.md:2534`) **[observed, quoted]**

**Plan.**

1. `skills/improve/references/shiploop-route.md`, the "Trivial classification" bullet: add one sentence
   for documents, naming what a planning document *is* made of, and keep it behaviour-free:
   *"In a planning document — a specification, a test strategy, a plan, a packet — trivial work is
   wording, formatting or explanatory polish that changes no requirement, acceptance line, test ID,
   step, decision, ordering or scope, and the review quotes the text that shows it; a changed or missing
   requirement, acceptance line, test ID, step, decision or scope is material."*
2. Same file, "A pass" (36): one clause that a planning-document review reads the document's normative
   content, not its prose.
3. No new term: "trivial" and "material" are Improve's own words, defined in this route and required by the
   binding (`review-policy.md:16`); ShipLoop's `references/glossary.md` carries no entry for them and needs
   none, so tenet 8 is untouched.

**Expected effect.** Planning Improve passes fall toward the two the stop rule requires (the edit and the
confirming pass) instead of 3/7/4. If the planning block falls by a third — the conservative reading of
"its passes halved" — that is 15–26 minutes on a run of the size of runs 3 and 4, plus the output tokens
of the passes not made. Code quality is unchanged in direction: the same reviewer reads the same
document, with a stated bar for what it must fix. Rough size: about six lines of prompt in one file.

**Cost and risk.** The risk is over-classification: a reviewer calls a real requirement change trivial and
leaves it. The sentence above bounds it two ways — it names the normative items exhaustively (a changed
or missing requirement, acceptance line, test ID, step, decision, scope) and it requires evidence quoted
from the document, and the existing line already keeps uncertain impact unresolved until investigated.
Cost is one prompt paragraph; there is no script, no state and no new file.

**Verify by.** The E2E measure, not judgement: re-run the chess case with planning review on (`stage`, the
harness default) and compare `metrics.json` — Improve children per planning stage and Improve minutes
against run 4 (`LEARNINGS.md:2507`, 46.6 of 78.8 min) and run 2 (`LEARNINGS.md:2283`, 21 passes, 8
material). Second, a text assertion in Improve's own tests that the route states the document clause, so
a later edit cannot silently drop it.

**Tenets touched.** Tenet 7 (concise, keep every obligation): this adds one clause and removes no duty —
"material findings get fixed" stands. Tenet 4 (KISS): no guard, no new mechanism; it is the classification
rule the route is already required to state (`review-policy.md:16`). Tenet 3: the sentence names no
language or platform. Tenet 1: no packet grounding moves. Tenet 8: no new term. Tenet 2 is untouched —
this is a rule for the reviewer, which is Improve's own prompt, not a ShipLoop script decision.

---

## 3. Take dependency directories from the platform card, not three hardcoded names

**Problem.** The base run copies the item's test files into a fresh worktree of the base commit and
symlinks dependency directories in from the checkout so the commands can start; the mutation check makes a
temporary detached worktree of the candidate with the same rule (`shiploop_mutation.py:17, 28`). Which
directories are linked is a constant in a core script, and it is three ecosystems' names.

- `skills/shiploop/scripts/shiploop_test_loop.py:DEPENDENCY_DIRS` (94): `("node_modules", ".venv", "venv")`
  **[observed, the line]**, used by `_BaseTree._make` (1592) **[observed]**.
- The module's own docstring states the limit: *"Known limits of the base run: ignored files are not in
  the worktree, so only the dependency directories named in `DEPENDENCY_DIRS` are linked in from the
  checkout"* (`shiploop_test_loop.py:35-36`) **[observed, quoted]**, repeated in
  `shiploop_mutation.py:28` **[observed]**.
- A project whose dependencies live anywhere else — a `vendor/`, a `deps/`, a `.tox/`, a `Pods/`, a
  `_build/` — has those directories absent from both copies, so its commands fail to start there. On the
  base the focused command's IDs all read `missing`, the row is `not-run`, and the refusal is advice about
  writing the test (**[observed — probe 2 reproduces exactly this refusal shape for a command that never
  starts]**; that a missing dependency directory produces it is **[inferred]** from the same path). In the
  mutation copy every mutant survives and the check refuses with `killed == 0` **[inferred from `_check`]**.
  Either way the item cannot pass the test stage until a person works out why. A regression command that
  fails for the same reason does *not* refuse — `_judge_base` marks a non-focused row `counted` whatever
  its exit **[observed]** — so the failure surfaces as the focused gate or the mutation check.
- Tenet 3 says platform specifics live only in `skills/shiploop/references/platforms/`. The knowledge is
  already there — `references/platforms/python.md:34` names `.venv/`, `node-express.md:47` names
  `node_modules/` **[observed]** — and the core script duplicates it, which is the shape the tenet
  forbids.
- The card mechanism the fix needs already exists:
  `shiploop_mutation.py:remote_test_commands` (66) parses `## Remote tests` bullets from
  `references/platforms/*.md` (`PLATFORM_CARDS`, 62) and `remote_card` (80) matches a command against
  them **[observed]**.

**Plan.**

1. `shiploop_mutation.py` (next to `remote_test_commands`, 66): `dependency_directories(cards=PLATFORM_CARDS)`
   reading `## Dependency directories` bullets of backticked names with the same `_REMOTE_PREFIX` shape.
   Keep it in one place; `test_loop` imports `shiploop_mutation` lazily already.
2. `shiploop_test_loop.py`: delete `DEPENDENCY_DIRS` (94); `_BaseTree._make` (1592) loops over
   `mutation.dependency_directories()` instead. Update the two docstrings (test_loop 35-36, mutation 28).
3. Cards: `python.md` gains `.venv`, `venv`; `node-express.md` gains `node_modules`; each new stack card
   that needs one gains its own. A card that names none behaves exactly as today for that stack.
4. State the limit in each card's section: list only directories whose contents are *inputs* to a
   command, never build output — a linked `target/` or `dist/` would let the base run see the candidate's
   compiled products and turn a real RED into a false `passes-on-base`.

**Expected effect.** Base runs start on projects outside the three named layouts, so items that
currently cannot pass the test stage at all can. Code quality: one ecosystem name leaves a core script
and lives where the tenet puts it. Run time: unchanged on Node and Python projects; on others it removes
a whole stuck item. Rough size: ~25 lines in two scripts, four card lines, tests.

**Cost and risk.** The build-output hazard above is the real risk, and it is a documentation rule on the
cards rather than something a script can enforce. Second: a project whose dependencies are in an unusual
place still needs its card written — but that is one line in the right file, and the alternative today is
a stuck run. There is no fallback list to keep (tenet 5), because the cards carry the names now.

**Verify by.** A hermetic test in `test/shiploop-test-loop.test.py`, modelled on the existing platform-card
tests — `test_the_salesforce_card_lists_its_remote_test_commands_and_a_local_one_still_runs` (1670) reads
the real cards, and 1225/1233/1640 patch `remote_test_commands` to stand one in **[observed]** — but pointing
the new reader at a temporary cards directory whose card names `vendor`, building an item whose focused
command needs a file under `vendor/`, and asserting the base run passes (today it would refuse); plus a test
that `DEPENDENCY_DIRS` no longer exists in the module, so the name cannot grow back.

**Tenets touched.** Tenet 3 is the reason for the change. Tenet 2 (derive from state): card plus checkout
is the derived answer. Tenet 5: no alias or fallback is added; the constant is removed, not wrapped.
Tenet 4: no adversarial guard — the hazard is a documented card rule, and a card written wrongly fails
loudly. Tenets 1, 6, 7, 8: untouched.

---

## 4. A base-run `not-run` refusal should say when the command never reached the tests

**Problem.** When a focused command exits non-zero without printing a test line, the base run classifies
every declared ID as `missing` and refuses with advice about how to write the test. The command's exit
code never appears, so a command that could not start (wrong interpreter, wrong working directory, an
absent dependency directory, a bad flag) reads exactly like a test that ran and did not fail.

- `shiploop_test_loop.py:_judge_base` (1674): IDs absent from the output are `missing`, and an all-`missing`
  focused row with no load failure naming an added file is `status = "not-run"` **[observed]**.
- `shiploop_test_counts.py:outcomes` (268): *"`missing` when no line names it (it did not run, or the file
  holding it failed to load)"* **[observed, quoted]** — the two cases are already known to be
  indistinguishable at that point.
- `shiploop_test_loop.py:_explain_base` (1744), `not-run` branch (1760): the advice is about RED
  ("A new test must fail on the base because the behaviour it asserts is missing…"), plus one sentence
  about printing the ID on every exit **[observed, quoted]**. The run's exit code is not in it; the
  output tail is printed only when the command produced output.
- Probe 2 (appendix) drives exactly this with `python3 -c "import sys; sys.exit(3)"` and gets:
  `- [focused] python3 -c "import sys; sys.exit(3)" -> did not run test_tc1 on the base, and no load
  failure in its output names a file this item adds. A new test must fail on the base…`
  **[observed — script-run]** The exit code 3 is nowhere in the refusal.

**Plan.** In `_judge_base` (1674), record the exit code on the row for `not-run` and `unread`
(`verdict["exit"] = code`); in `_explain_base` (1744), open the `not-run` branch with the distinction when
it holds — *"The command exited <n> and printed no test line, so it never reached the tests: check that it
starts in a clean checkout (interpreter, working directory, dependency directory, flags) before reading
this as a test that does not fail."* — and keep the existing test advice after it. Same for `unread`
when the exit is non-zero. Nothing else changes: same status, same refusal, same counting.

**Expected effect.** One round trip saved for each start failure, and it stops the model from rewriting a
correct test. Start failures are the common shape of a new project's first test stage, and in a live run a
single unexplained refusal costs a model turn plus a re-run of the gates (**[inferred]**; run 4 counted 13
refusals, `LEARNINGS.md:2530` **[observed, quoted]**). Rough size: ~10 lines.

**Cost and risk.** Low. The status and the acceptance decision do not change; only the explanation gets a
case it already knows about. Residual risk: a command that legitimately exits non-zero while printing
nothing and whose IDs are still expected to fail on base — but that command cannot be judged at all, so
the refusal stands either way; only its wording improves.

**Verify by.** Turn probe 2 into a test: record a focused command `python3 -c "import sys; sys.exit(3)"`
with one ID, call `red_check`, and assert the refusal matches `never reached the tests` and names
`exit 3`. A second test keeps the current wording for a command that prints IDs and fails (exit non-zero
with `--- FAIL`-style output), so the new sentence cannot swallow the real RED case.

**Tenets touched.** Tenet 6 (evidence, not judgement): the refusal becomes more precise about what the
script observed. Tenet 2: it derives from the exit code the script already has. Tenet 7: it adds one
sentence to an existing refusal and drops nothing. Tenet 3: the sentence names no language — it says
"interpreter, working directory, dependency directory, flags". Tenets 1, 4, 5, 8: untouched.

---

## 5. The base-run `unread` refusal names three ecosystems; point at the platform card instead

**Problem.** `shiploop_test_loop.py:_explain_base` (1744), `unread` branch (1755-1759), tells the model:
*"Use a reporter that marks each test's outcome on the line that names it (pytest -v; python -m unittest
-v; jest --verbose). Another runner's readable reporter is in the platform card under
references/platforms/."* **[observed, quoted]**

This is a core script naming three frameworks in a refusal the model reads on a normal run, and it gives
the same three suggestions to a Rust, Go or .NET project. The same paragraph already names the sanctioned
home, so the parenthetical adds nothing except the tenet-3 leak; the recent commit 6051924c ("the
file-guard rule names no language's file API, only the shell forms") removed the same kind of text from
another rule.

**Plan.** Delete the parenthetical and lead with the card: *"Use a reporter that marks each test's outcome
on the line that names it; the platform card under references/platforms/ names the readable reporter for
this stack."* Check the neighbouring refusals in the same two branches for a stray ecosystem name while
there.

**Expected effect.** Tenet 3 clean in a refusal; no change to any decision. Size: two lines.

**Cost and risk.** None that I can see — the card is where the answer already lives, and cards exist for
every stack ShipLoop supports.

**Verify by.** The existing refusal tests for `unread` (the module has them beside the base-run tests)
match on the advice sentence; update one and add an assertion that the refusal contains no ecosystem name
from a short list. That list lives in the test only, not in a script.

**Tenets touched.** Tenet 3 is the change. Tenet 7: the obligation ("use a reporter that marks each
outcome") is kept; only the examples go.

---

## Considered and rejected

- **Trim the packets.** Measured every printed head in the two-work-item dry run: no packet repeats a
  sentence inside itself; the only intra-head repetition is the CLI path (3–4 times), which is what makes
  each command copy-pasteable. Inter-packet repetition is deliberate (tenet 1). Nothing to cut.
- **Move grounding out of packets into a file the packet names.** Tenet 1 forbids it, and run 2 measured
  that the model read `reference.md` and `context-index.md` **0 times** (`LEARNINGS.md:2283`).
- **Raise `HEAD_LIMIT` / `PRINT_LIMIT`.** The 20,000 cut is the host's, with `HEAD_REQUIRED_END = 19_500`
  (`shiploop_navigator.py:1942, 1946`); heads already sit at 19,899 (`head_table.json`). The mechanism and
  its trade-off are journaled and tested (`shiploop-head-order`).
- **Guard against forged packets, racing callbacks or a model that edits the contract.** Tenet 4 forbids
  adversarial guards; nothing here breaks or misleads a normal run.
- **A shim or migration so old run directories keep working** with any change above. Tenet 5 forbids it;
  the reuse lookup simply does not match an old record.
- **Make `graph-dry-run` write the loop contracts, so its packets stop printing "The loop contract is
  missing; report outcome blocked naming this path."** (`shiploop_loops.py:invoke_lines`, 655 and 672 —
  **[observed]** in all 42 packets of my dry run, because `dry_run.run_scenario` calls `render` and never
  `emit`, and `emit` (1954) is what writes the contract). A real defect and a cheap fix (write the
  contract in the dry-run path, or suppress the line when the dry run is the caller), but it touches no
  ordinary run, so it does not earn a place by the ranking rule. Worth a separate small ticket.
- **Raise the mutation gate's floor above "no mutant was killed"** (`shiploop_mutation.py:414`, refuse only
  when `killed == 0`). Changing it to a fraction would refuse ordinary items that contain an equivalent
  mutant — changing a constant or an operator that no test can observe — and the journal shows the
  opposite failure, a refusal for a reason the code was not at fault for (`LEARNINGS.md:2501`). No live
  run shows a shallow test slipping through this floor; the harm is **[inferred]** only.
- **Widen the mutant sample beyond 8** (`MUTANT_SAMPLE`, 49; `sample`, 212, gives one mutant per file
  once an item touches more than eight product files). Real coverage argument, but no evidence it breaks or
  misleads a normal run, and every extra mutant costs a focused-command run under a 600 s budget.
- **Cut `complete --check-only` calls per item (4–11, `LEARNINGS.md:2131`).** The call count is the model
  doing what the loop tells it to; recommendation 1 removes the cost of each call instead, which does not
  depend on the model behaving differently.
- **Stop instructing `red-check` after each change** (`shiploop_prompts.py:1463`). With recommendation 1
  the instruction becomes nearly free (a no-op on an unchanged base and test files), and without it the
  instruction is the check the stage exists for.
- **Default Improve to `first-item` on more stages** (`shiploop_stage_spec.py:IMPROVE_RULES`, 66;
  `implement` is `step` by owner decision 2026-10-10). That is an owner scheduling decision, already
  measured ("Improve on the first item, with one trivial pass, pays", `LEARNINGS.md:2534`), not a defect.
- **Drop the `reference` / `context-index` pointer lines from packets** to reclaim ~100–200 head
  characters (`LEARNINGS.md:2283`, read 0 times; `head_table.json` `_comment`, an optional block dropped
  for want of 62 characters). Tempting, but the evidence is n=1, and those files are the run's memory
  across context clears.
- **Shorten absolute paths in packets** (14% of packet bytes, `LEARNINGS.md:2283`) with a `RUN=`
  shell-variable convention. The callback reason forbids shell variables in a printed command
  (`shiploop_prompts.py:CALLBACK_REASON`, 146) and a copy-pasteable command must carry its real path.
- **Reduce the base run's 1,800 s budget or the mutation check's 600 s.** They bound a run that is
  already reused under recommendation 1; shrinking them would turn slow suites into `UNAVAILABLE`
  refusals, which accept the stage's remedy and lose the evidence.
- **Speed up the per-step Proof (~24 min, `LEARNINGS.md:2472`).** It already reuses a passed record on an
  unchanged tree (`shiploop_test_loop.py:step_proof`, 1427); the cost is that each step really does change
  the candidate. That is the design.
- **Re-propose the run-5 deferred items** (IDs on focused commands, a code item needing a new ID, revisit
  lines) or the run-insights E-series packet work. Already decided or shipped; the tree at 31933a73
  contains them.
- **Make `Improve`'s child copy the repository once per child.** I looked for a copy or a worktree per
  child in `shiploop_standalone_improve.py` and found none (`_workspace`, 191, validates the path; there
  is no `copytree` and no `worktree add`). The claim could not be confirmed, so it is dropped.

---

## Appendix: what I ran

**Full module.** The whole test-loop module, `test/shiploop-test-loop.test.py` — **161 tests, OK,
404.6 s**.

**Probe 1 — base-run and mutation-check reuse.** Subclasses the module's own fixture, drives an item to
the test stage with a real assertion, then calls `test_loop.red_check`, `complete_output(done,
check_only=True)` and `complete_output(done, check_only=False)` with `test_loop.lint.run_argv` wrapped to
count every command run and its working directory. Source:
`<scratchpad>/probe_base_mutation_reuse.py`; output:

```
red-check (the packet's own command): 2 command runs (0 in the checkout, 2 elsewhere)
complete --check-only: 8 command runs (2 in the checkout, 6 elsewhere)
complete (the real callback): 6 command runs (0 in the checkout, 6 elsewhere)
records: [...-base1.md, ...-check-only.md, ...-mutation-check-only.md, ...-mutation1.md,
          ...-red-check.md, ...-verify1.md]
```

**Probe 2 — a base command that never starts.** Same fixture; the item's focused command is replaced by
`python3 -c "import sys; sys.exit(3)"` with one declared ID, and `test_loop.red_check` is called. Source:
`<scratchpad>/probe_base_start_failure.py`; output:

```
red_check ok = False
   | base: [focused] python3 -c "import sys; sys.exit(3)" -> not-run
   | ShipLoop base run: test is not done. …
   | - [focused] python3 -c "import sys; sys.exit(3)" -> did not run test_tc1 on the base, and no load
     failure in its output names a file this item adds. A new test must fail on the base because the
     behaviour it asserts is missing …
```

**Heads.** An offline dry run of the two-work-item scenario (42 packets) with `navigator.render` spied and
`navigator.printed_text` applied per packet, to compare printed heads with `PRINT_LIMIT` (16,000),
`HEAD_LIMIT` (20,000) and `HEAD_REQUIRED_END` (19,500) and to test for intra-packet repetition.

**Every `path:symbol` cited above was re-opened at 31933a73 before this file was written**; the line
numbers are from that commit.
