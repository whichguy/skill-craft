---
Execute: ask
---

# Plan: commit learnings, look-back and spec merge in ShipLoop

This plan merges the design with its three adversarial audits. Nothing in the checkout has been changed and nothing has run. I re-read the code these decisions rest on at `62b76c09` (worktree `b1011z-aaa47e`):
- `knowledge_home.CLOSES`, `STAGE_FILES`, `check`, `commit`, `stage_lines` and `recent_commits`
- `navigator._knowledge_close` and its three callers
- the authority text in `improve_start_contract`
- the planning branch of `_render_improve`
- `improve_changes.commit_refusal`
- `workspace.follow_up_knowledge_return`
- `STATE_VERSION = 4`

## 0. Engineer's critique (2026-10-10) and the revised plan of action

**This section supersedes the order in section 5 and the release bundling in section 6; the rest of the plan stands.** A critique of the plan as it was approved for decision, written before any code. Each point was checked against the repository where it could be.

### Critique

1. **Unpublished work sits on the critical path (blocker).** The canonical checkout `/Users/dadleet/src/skill-craft` is 263 commits behind `origin/main` and holds 1,148 uncommitted lines across 19 files from earlier sessions (Oct 6 to 8): a storage-and-recovery change (`shiploop_store.py` +282, `shiploop_protocol.py`, `shiploop_navigator.py`, `scripts/shiploop`, four test suites, `changes/shiploop/storage-and-recovery-audit.md`). They are the files this plan edits, and `STATE_VERSION` lives in that area. The plan called this "slice 0 housekeeping"; it is the first task and it is also data at risk (one disk, no commit).
2. **The frozen Improve contract may not have room (blocker until measured).** The audit found the spec contract at 8,775 of 9,216 bytes; slice 1 adds about 350. The budget is derived from the vendored runtime and cannot be raised. Measure every contract's headroom before committing to "put the rule in the frozen contract"; the carrier may have to be the Improve card or the work string.
3. **Three kinds of change in one release.** Gates that refuse, packet content, and a text diet, released together, cannot be told apart in a live run, and a same-build cell already ranges 1.75 times in cost. Success must be mechanical counters (refusals by first line, commits with and without a lessons section, citations, packet bytes, calls to re-orient), never cost or wall time, and each change should ship alone.
4. **Refusals before evidence.** 12 of 13 recent Improve commits already carry all labels on their own; 91% of knowledge commits are subject-only because the script builds them. Split the two kinds of change: *the script adds content* (a body from sections it already holds, trailers; no refusal, no false-refusal risk) and *the model must write content* (a refusal costs a turn and invites filler). Keep the one refusal you asked for (an Improve commit needs Key learnings); make the delivery-stage and plan-ID checks **notices that are counted for one release**, then decide from the counts.
5. **The look-back block costs bytes in every packet and its value is unmeasured.** In a fresh repository (every E2E example) the last commits are subject-only knowledge commits, so the block is noise exactly where it is tested. It also works against the packet diet. Show it only when a lesson-bearing commit exists, and count citations as the "was it used" signal.
6. **Spec merge by replacement assumes one run at a time.** Freeze-and-replace refuses (or loses) a legitimate concurrent edit to the living spec. The plan already records the living spec's blob when the copy is made, so a three-way merge (`git merge-file` with that base, the living spec now, and the feature spec) is nearly free and keeps concurrent edits; a conflict stops with a named fix. Evaluate it in the spike instead of the freeze.
7. **The `STATE_VERSION` bump is not shown to be necessary.** The base blob and planned commit are run-directory files, not state keys. If nothing in slice 3 adds a state key or changes the graph, there is no bump, no refusal of in-flight runs, and no need to wait for the live batch. The plan asserts the bump without naming what forces it.
8. **The feature index is unaudited** (D7; the review is running). The smallest option that closes the gap may be the script maintaining the feature list inside the README, not a new generated file that every run rewrites (noisy diffs, concurrent-run conflicts).
9. **No test of the goal itself.** Nothing shows that a later run reuses a lesson. Add a hermetic scenario on a toy repository (run one records a lesson; run two's packet shows it and its result cites it) and measure citations that name an earlier run's commit in the first live pair.
10. **The maintainer loop is not covered.** The cheapest way to make our own loop commit with lessons is a `release.py` preflight, not ShipLoop code.

### Revised plan of action

| Step | What | Gate to start | Released as | Measured by (no thresholds) |
|---|---|---|---|---|
| 0 | **Preserve and reconcile the unpublished work**: commit the canonical checkout's changes to a branch (no reset, no stash, main untouched), port them onto current main, decide ship or drop. **Owner decision.** | Owner says whose it is | n/a | The branch exists; the suites it touches pass on current main |
| 0b | **Spike** (read-only, no release): every Improve contract's byte headroom; what, if anything, forces a `STATE_VERSION` bump; look-back bytes on three real repositories; three-way merge on a toy living spec | Step 0 started | n/a | A table in the journal; D6 and the merge choice decided from it |
| A | **Packet diet**: Improve wording only where an Improve child runs; status once; callback and result path once; the eight binding rules as invariants; policy links filtered to the stage; a Locators table in `context-index.md`; path variables only after a trial | 0b | its own minor release | Packet bytes per stage; the cleared-context probe before and after (6 to 7 calls, 16 to 21 s today) |
| B | **Commits slice 1**: script-built bodies and trailers; Improve commit needs Key learnings and resolves `Learned-from:`; look-back only when lesson-bearing commits exist; notices for model-typed commits without lessons | A, and the contract carrier chosen in 0b | its own minor release | Commits with a lessons section; refusals by first line; citations; bypasses (`model_commits`); packet bytes |
| C | **Commits slice 2**: delivery-stage lessons (notice first), integrate lessons (D5), remote-change commit with no files | B | its own minor release | Delivery commits with lessons; empty-diff commits and their trailers |
| D | **Spec lifecycle and index**: working copy, merge at handoff (three-way or replace, per 0b), cleanup, index; the bump only if 0b says so | 0b, C | its own release | Merge commit trailers; feature spec recoverable at Planned; handoff attempts; refusals at spec, plan, prepare |
| M | **Maintainer preflight**: `release.py` refuses a release with no `LEARNINGS.md` commit since the last release, unless the range carries `No-E2E-Round: <reason>` | none | with any release | Releases refused and overridden |

Every step: fail-first hermetic tests, one adversarial review of the diff, one live pair measured by the counters above, a journal entry in the same commit, and a change note. Release order is the table order; none waits for another to be "bundled".

### Decisions changed by the critique

D6 becomes "decided by the spike (0b)", not "yes". D5 stays yes. D7 stays open until the index review finishes. New: **D8**, whose work is the uncommitted change set in the canonical checkout, and whether it ships.

## 0a. YAGNI and KISS review (2026-10-10) and the plan of action v3

**This section supersedes section 0's table and sections 5 and 6 where they differ.** The question for each part: what observed failure does it fix, and what is the smallest change that fixes it? Where the repository had a fact, it was checked.

### What the evidence does and does not support

- **Supported:** Improve commits often lack lessons; 91% of the engine's own knowledge commits are subject-only; packets are large and the model never opens the 33 reference files they list (0 reads in two Sonnet runs); a later run cannot find an old feature folder (the name is not derivable and the README is model-written free text).
- **Not supported by any observed failure:** that the model corrupts the living spec. `knowledge_home.check` already refuses a run that drops a requirement ID the committed spec had, the spec prompt already says "change it in place, move a dropped requirement under Retired", and 24 of 26 saved feature specs show models doing exactly that. The working copy, the freeze, the base and planned blobs, replace-at-handoff, the plan-names-every-ID check, the trailer set and the state bump are all fixes for a failure nobody has seen.
- **Not supported yet:** that a remote system was ever changed by a local case (the planned measure expects 0); that a look-back block is used (unmeasured).

### Keep, cut, defer

| Part | Verdict | Why | Build it when |
|---|---|---|---|
| Improve commit needs a Key learnings section | **Keep** | Your explicit rule; one refusal | n/a |
| `Learned-from:` citations | **Keep, minimal** | Validate that each cited ID is a real commit; leave the message as written | n/a |
| Moving citations into trailers; `ShipLoop-Run/-Stage/-Action` trailers; joining `Co-Authored-By` blocks | **Cut** | No consumer reads them (Run Review and the harness do not) | Run Review reads commit trailers |
| Script-built bodies for knowledge, item and leftovers commits (from sections the script already holds) | **Keep** | Fixes the 91% with no refusal | n/a |
| Lesson refusals at delivery stages; the `learning` result key | **Cut** | A new schema and a new refusal for a gap the script-built body already fills | A delivery stage keeps omitting lessons in counted runs |
| Remote change as a commit with no files | **Keep one path**: `improve-commit` accepts an empty commit that has a Remote change section | Meets your ask in one place | n/a |
| `learning.remote_changes` schema, duplicate guard, changed follow-up return | **Defer** | No local case makes one | The first real remote case (the Salesforce test on the todo list) |
| Look-back in every producer packet | **Keep, small** | Reuse the existing last-commits function: last 2 messages, their lessons sections only, scan the last 10 commits (not 500: chosen, never measured) | n/a |
| Spec working copy, freeze, base/planned blobs, replace, three-way merge, plan ID check, `STATE_VERSION` 5 | **Defer all** | No observed failure; the existing guard covers the loss case | A run loses or garbles a requirement, or two runs edit one repository's spec |
| **Retire step at handoff** (new, small) | **Keep** | The script checks that every ID the feature spec says it adds or modifies is in the living spec, removes the feature spec (only when the run's commits reach the branch) and commits, citing the prepare commit as the planned record | n/a |
| A new feature index file | **Cut** | A new artifact every run rewrites; conflicts and noise | n/a: use a script-owned marker block inside `README.md` listing each feature: folder, request title, IDs, planned commit |
| Packet diet: Improve negatives, duplicate status, duplicate callback and result path, the policy-link block replaced by one pointer line | **Keep** | About 11K of 42K characters removed, no guidance rewritten, no new file | n/a |
| Locators table, the invariants rewrite, path variables, a per-stage filter of generic paragraphs | **Cut** | Rewrites that change behaviour for a gain the deletions already deliver | A probe shows a model confused by the shorter packet |
| Spike | **Shrink** | Two measurements: every Improve contract's byte headroom; look-back bytes on one real repository. The state-bump and three-way-merge questions disappear | n/a |
| Maintainer release preflight | **Keep, last, optional** | About 20 lines; the override trailer handles docs-only releases | n/a |
| Verification | **Proportionate** | Byte counts plus the cleared-context probe for the diet; a live pair only where a model must do something new (the Improve commit rule, the retire step) | n/a |

Rough size, from the plan's own lists: the spec lifecycle went from about 13 named tests and ten new functions with a state bump to about 4 tests and 3 functions with no state change. These are estimates, not measurements.

### Plan of action v3

1. **D8 snapshot** of the uncommitted work in the main checkout (non-destructive: `git stash create` into a branch, plus a copy of the untracked files). Owner OK.
2. **Spike** (two measurements). Decide the carrier of the Improve commit rule (frozen contract, card or work string).
3. **A. Packet diet (deletions only)**, own release.
4. **B. Commits**: Key learnings, citation validation, script-built bodies, empty commit for a remote change via `improve-commit`, the small look-back; own release.
5. **D. Retire the feature spec and the README features block**; own release; no state change.
6. **M. Maintainer preflight**, with any release.
7. **Deferred, each with its trigger** (table above).

### Owner decisions left

Four: **D8** (snapshot the unpublished work), **D3** (remove the feature spec only when the run's commits reach the branch), **D4** (an Improve pass that changes nothing makes no commit), **D5** (integrate's product commit gets a script-built body). D1, D2 and D6 are moot or deferred; D7 resolves to the README block.

## 1. What you asked for

| # | Requirement | Answer |
|---|---|---|
| R1 | Improve commits cite the other commits whose learnings helped this one | **Built.** Citations are `Learned-from: <full commit ID> <what it contributed>` lines. The script checks that each one names a real commit reachable from HEAD and says how it helped. Citations are optional: there is no quota and no "none cited" filler line. Only Improve commits carry them, because those are the commits you named. |
| R2 | One spec for this run, one long-lived spec of everything in force; the run's spec becomes the historical record once it is committed with the plan | **Built differently.** The run's spec is a working copy of the living spec, and the run edits it in place. Models already work this way: 24 of 26 saved feature specs ignored the designed delta format. The script records the commit made at the planning close and names it in the merge commit (`ShipLoop-Spec-Planned`). That commit is the record of what the run set out to do. |
| R3 | The plan implements the spec; at the end the result merges into the persistent spec, is committed, and the run's file is removed; the merge handles add, change and remove | **Built.** The plan must name every requirement ID the run adds or changes. At handoff the script (not the model) merges the copy, removes it and commits, with the IDs that were added, modified or retired. A removed requirement moves under a Retired heading, and IDs are never reused. One exception: on the working-tree return route the file is kept, because no commit of the run reaches your branch (decision D3). |
| R4 | Every Improve commit and every CD commit carries lessons learned | **Built** for Improve commits: a commit with no Key learnings section is refused. **Built** for delivery-stage knowledge commits: release-plan through operations are refused without lessons when a commit will happen. The integrate stage's product commit is your call (D5; I recommend yes). Mechanical commits are excluded. An Improve pass that changes nothing still makes no commit (D4). |
| R5 | A lesson about a remote-system change with no file change still gets a commit, with no files | **Built.** The script makes this commit, and only from a declared remote change that has lessons and an evidence locator. It never replaces a file commit. |
| R6 | Every step references at least the last couple of commits, so their learnings are reused | **Built.** Every producer packet lists the 2 latest commits, plus the lesson sections of the 2 latest commits that record lessons. Improve children already read seven messages under the Improve card, so they get no second block. |

## 2. The design in its smallest form

### 2.1 What changed from the reviewed design, and why

| Design | Plan | Why |
|---|---|---|
| Feature spec is a delta (`## Added/Modified/Removed`); the model merges it into the living spec at handoff; strict per-entry checks | Feature spec is a **working copy** of the living spec; the **script** replaces the living spec with it at handoff | Two files of requirements, plus a merge done by meaning, at the last stage (T2). The merge edit could be absorbed by the leftovers commit (T3). Per-entry comparisons gave false refusals (F9, C2). Models already edit in place (T2). This also removes the model's merge task, the delta and merge checks, and the "apply the delta in your head" line. |
| Run start S found by scanning the log for a `ShipLoop-Run` trailer | The living spec's blob is **recorded when the copy is made** (run-dir `spec-base.md`) | A model's own commits break the scan (T6, F12), it reads all of history at every done (C4), and its restore command could discard user work (F5) |
| Planned = newest prelude-trailer commit; Delivered trailer; "Changed after planning" | Planned = HEAD after the prepare close (run-dir `spec-planned.md`); Delivered and "Changed after planning" dropped | The design's Planned was wrong when the planning child committed (F3). The other two are filler (T12). |
| `learning.learned_from` in stage results; `Learned-from: none cited`; an automatic citation on the merge commit | All three dropped | Stage citations rarely reach a commit (T8). "none cited" is filler and contradicts inline citations (T12, F20). A mechanical citation is what section F of the design itself rejects (T12). |
| Lesson ledger `lessons/<action>.md`, a retry on every dispatch, adoption, a self-check | Dropped; the commit with no files is made inside the existing `_knowledge_close` | They only guard against index-lock failures, and read verbs would make commits (T7, F18, C9) |
| `--remote-change` flag | A `Remote change` section in the message is the trigger | Removes a second declaration of the same fact (T10) |
| Improve rules printed only in the parent packet | The frozen child contract carries the `improve-commit` command; `commit_refusal` and the planning child are routed to it | The child was told never to run a callback, so 35% of Improve-window commits bypassed the gate (T1 blocker, F4, C3) |
| Look-back: an item-path query, also in the Improve parent packet, a `#`/`Label:`-only extractor, unbounded `-i` grep | No item-path query; not in the Improve parent packet; bare labels accepted; case-sensitive; non-empty sections only; newest 500 commits; credential lines dropped | T11, F8, F21, C4, F25 |
| Unmerged-spec listing, handoff link gate, Run Review fields | Listing dropped; link check becomes release-verify packet text; Run Review fields deferred | False for every existing repo (T5, F2, C10); costs turns and stales the return (T17, C6); not requested (T22) |
| Trailer paragraph appended; `[0-9a-f]{7,40}`; `<sha> (<subject>): <text>` | Git's own trailer handling (joins an existing `Co-Authored-By` block); single-line values; `{7,64}`; `Learned-from: <full ID> <text>`; `--cleanup=whitespace` | F7, F19, C13, F13 |

### 2.2 Commit contract: an Improve commit, before and after

Before (today the message is committed as written):
```
Fix the board edge check in placement

Review: placement accepted ships past column 10.
Changes: bounds check in place_ship; test for column 10.
```
After:
```
Fix the board edge check in placement

Review: placement accepted ships past column 10.
Changes: bounds check in place_ship; test for column 10.

Key learnings:
- The board is 0-based in code and 1-based in the spec's examples; convert in the parser.

Learned-from: 3f2a9c1e0b7d…(full ID) its column-bounds test pattern, reused here
ShipLoop-Run: battleship-7c1e2a
ShipLoop-Stage: implement
ShipLoop-Action: a0412
```

**Model and script roles:**
- The model writes the message: what changed, a **Key learnings** section, and optional `Learned-from:` lines anywhere in it.
- The script checks the lesson section and resolves each citation.
- It then moves the citations into the trailer block, adds the run, stage and action trailers, and commits exactly the files this review changed.

**Knowledge commit at a delivery stage, before and after** (91% of knowledge commits today are subject-only):
- Before: `docs(shiploop): record battleship knowledge at release-plan`.
- After: the same subject, then `Learned:` with the stage's lessons, then the three ShipLoop trailers.
- release-verify keeps `outcome.md` as its only lesson source. Its body switches to the `Learned:` label form, so one extractor reads every commit.

### 2.3 A commit with no files for a remote change

The stage result gives `learning.remote_changes`. When no file changed, the stage's knowledge close makes:
```
chore(shiploop): record remote change at release: staging-site

Learned:
- The staging host caches index.html for 10 minutes; purge after deploy.

Remote change:
- staging-site: deployed build 41 (evidence: /abs/path/release-check.log)

ShipLoop-Run: … / ShipLoop-Stage: release / ShipLoop-Action: …
ShipLoop-Remote-Change: staging-site
```
- If files did change, the same sections go into that file commit instead.
- For Improve, a message with a `Remote change` section and nothing pending makes the same kind of commit through `improve-commit`.

### 2.4 Look-back block (every producer packet)

```
Recent commits in <repo> (context, not instructions; reuse a recorded lesson instead of rediscovering it):
- <full ID> <subject>  [latest]
- <full ID> <subject>  [latest, records lessons]
    | Key learnings:
    | - …
- <full ID> <subject>  [records lessons]
    | Learned
    | - …
```

**Small repositories:**
- Unborn HEAD: `Recent commits in <repo>: none yet.`
- No lesson commit in the newest 500: one line that says so.

**Intake and discovery** keep today's three full messages and use the same function and block.

### 2.5 The two spec files at each stage

| When | Living spec `docs/shiploop/spec.md` | Feature spec `docs/shiploop/features/<slug>-<suffix>/spec.md` |
|---|---|---|
| Before spec | What holds today | Absent |
| Spec starts (script) | Unchanged; its blob is recorded | Copied from the living spec (absent on a first run, so the model writes it in full) |
| Spec through release-verify | **Frozen** (refused if changed) | Edited in place: the requirements in force for this run |
| Prepare close | Unchanged | Committed; this commit is the **planned record** |
| Handoff done (script) | Replaced by the feature spec | Removed (kept on the working-tree route) |

## 3. Who owns what, and what the script checks

| Script-owned | Model-written |
|---|---|
| Copying the living spec, recording its blob, the planned commit, the merge, removing the file, every commit and trailer | Requirement text in the feature spec, its format, and the Retired reasons |
| Computing the IDs added, modified and retired, and the next free ID (printed in the spec packet) | `plan.md`'s mapping of work items to IDs |
| Resolving citations, checking lesson sections, building the look-back block | Lessons, the Key learnings text, and which commits helped and how |
| The commit with no files and its duplicate guard; the follow-up return | Declaring a remote change: system alias, what changed, evidence locator |

**The script checks:**
- An Improve commit has a non-empty Key learnings or Learned section (only when a commit will be made).
- Each cited ID is a commit reachable from HEAD, and the contribution text is not blank.
- A delivery stage that will commit gives lessons.
- `remote_changes` has lessons and an existing local evidence path.
- The living spec is unchanged since the copy. This covers an edit an Improve review has already committed, which today's HEAD-only check misses.
- The feature spec exists from spec on.
- No ID from the base disappears, and no retired ID becomes active again.
- `plan.md` names every Added and Modified ID, at plan done and again at the prepare close.
- No second remote-change commit is made for the same action and system.

**The script cannot check** (the record says so where relevant):
- whether a lesson is true or useful (filler);
- whether a cited commit really helped;
- whether a remote change happened, or one went undeclared;
- semantic contradictions between requirements;
- whether a work item really implements its ID;
- a child's raw `git commit` (visible, not prevented);
- a squash merge that drops the cited and Planned SHAs.

## 4. The spec lifecycle, step by step

1. **intake, discovery, research.** The living spec is untouched. Knowledge commits work as today.
2. **The transition into `spec`** (a post-save hook beside `_knowledge_close`, idempotent):
   - `knowledge.start_feature_spec` copies `docs/shiploop/spec.md` to `<feature>/spec.md` if the copy does not exist.
   - It writes `<run>/spec-base.md` with the living spec's blob (`git hash-object -w`, so it can be restored), or `absent`.
   - The spec packet prints the next free ID: the highest ID in the living spec and in any `features/*/spec.md`, plus one.
3. **spec done.** The checks are: freeze, feature spec present, no dropped or revived ID. Then the existing knowledge commit `docs(shiploop): record <feature> knowledge after spec`, which now holds the copy.
4. **test-strategy and plan** (including the planning Improve child).
   - The plan packet prints the IDs the script computed: "This run adds R-12 and changes R-4."
   - Plan done refuses a `plan.md` that omits one: `plan.md does not name R-12, R-4, which this run adds or changes in <feature spec>. Name the work item that implements each, then run the same <verb> command again.`
5. **prepare close.**
   - The existing commit `… at prepare` runs, and the plan check runs again.
   - `_knowledge_close` writes `<run>/spec-planned.md` = HEAD. That commit holds the planned feature spec, whoever committed it.
6. **Inner stages** (implement … document). `document` reconciles requirements in the **feature spec** (prompt changed). Each stage that changes it gets a knowledge commit.
7. **release-plan through release-verify.**
   - Lessons commits as in section 2.2.
   - The release-verify packet says to link the living spec and the feature directory (not the feature spec file) from `docs/shiploop/README.md` and `SHIPLOOP.md`. This is packet text, not a gate.
   - The workspace return happens before handoff, as today.
8. **handoff done** (`_knowledge_close(terminal=True)`, which fails closed):
   1. Commit any pending knowledge changes (today's commit).
   2. `knowledge.merge_spec`: check the freeze, write the living spec with the feature spec's content, remove the feature spec (unless the route was working-tree), and commit `docs(shiploop): merge <feature> spec into the living spec`. The body is one line, `Requirement changes: Added R-12; Modified R-4; Retired R-7`. The trailers are `ShipLoop-Run/-Stage/-Action`, `ShipLoop-Spec-Merge: <feature dir>`, `ShipLoop-Spec-Added/-Modified/-Retired` and `ShipLoop-Spec-Planned: <full ID>`.
   3. The existing P11 follow-up return.
9. **Afterwards.**
   - `git show <Planned>:<feature spec>` is the planned record.
   - The merge commit's parent holds the delivered version.
   - `git log -E --grep='^ShipLoop-Spec-Modified:.*(^|[^0-9])R-4([^0-9]|$)'` finds the requirement's history, with no path filter and no `\b` (F14).
   - `plan.md`, `test-spec.md`, `system-tests.md`, `release-plan.md` and `outcome.md` stay as the per-feature record.

**Edge cases:**
- **Retry after a refused handoff** (F1, C1). The merge counts as done when:
  - the living spec equals the feature spec (the working-tree route), or
  - the feature spec's last change in history (a path-limited log) is a deletion that carries `ShipLoop-Spec-Merge: <feature>`.

  In either case the check and the merge do nothing.
- **First run.** The base is `absent`. The model writes the full spec into the feature spec, and handoff creates the living spec. The progress page says "created at handoff", not "missing".
- **No requirement changes.** The copy equals the base. The merge only removes the file.
- **Feature spec deleted by the model.** Refused at that stage's done: `restore with git -C <repo> checkout HEAD -- <path>`.
- **Living spec edited after the copy.** The refusal is: `The living spec <path> changed after this run copied it. Move the change into <feature spec>, then restore the living spec with: git -C <repo> cat-file -p <blob> > <path> (delete it if this run started without one); then run the same <verb> command again.` It never prints a `checkout` that could drop someone else's edit (F5).
- **Run that stops before handoff.** The living spec stays untouched and the feature spec stays. The next run starts from the living spec and does not inherit the unmerged changes. This goes into the non-regression statement (T23).
- **Non-Git checkout.** Exempt. The handoff line says so.

## 5. Slices, smallest valuable first

**Slice 0: prerequisites (no release).**
- Reconcile the canonical checkout's uncommitted edits to `shiploop_navigator.py`, `shiploop_protocol.py`, `shiploop_store.py` and `metrics.py` (C17), following the AGENTS.md policy: never reset or stash.
- Base the worktree on the freshly verified `origin/main`.
- Release nothing until the current live E2E batch finishes.

**Every slice follows the same process:**
- SPEC change admission: adversarial evaluation, anchors (S-5, S-6, S-9, S-11, S-12, S-14), a non-regression statement, hermetic tests, then one live run.
- Run only the footprint suites, and register any new top-level suite (none is planned).
- Add a journal entry in the same commit.
- Commit messages use Key learning / Evidence / Related commits.
- Use `git -C <repo>`, and never edit `skills/improve/runtime/until-loop/**`.

### Slice 1: Improve commits carry lessons and citations; every packet shows recent lessons

This slice makes no state change and refuses no saved run.

**Files and symbols:**
- `shiploop_git.commit_paths`:
  - an empty commit with no paths uses `--allow-empty --only`, so a staged unrelated file stays staged;
  - always pass `--cleanup=whitespace`;
  - support trailers through Git's trailer handling.
- New in `shiploop_git`: `lesson_sections` (reuses the `knowledge_home._sections` parsing and accepts `## Label`, `Label:` and a bare label line), `resolve_citations` and `LESSON_LABELS`.
- `navigator._improve_commit`:
  - "nothing to commit" comes first;
  - then the lesson check;
  - citations are resolved and normalised to single lines, then moved into the trailers;
  - the run, stage and action trailers are added;
  - the success line lists the citations.
- `improve_start_contract`:
  - **authority**: `The child never runs a ShipLoop callback except improve-commit: commit each iteration's changes only with <command>, message at <path> with a 'Key learnings' section, optional 'Learned-from: <full commit ID> <what it contributed>' lines.`
  - **work**: points at it.
- The planning branch of `_render_improve` gets the same commit line.
- `improve_changes.commit_refusal` names the `improve-commit` command; its signature gains the command.
- `improve-complete` prints a **notice**, not a refusal, for commits made since the bind that have no lesson section.
- `knowledge_home.look_back` replaces `recent_commits` and uses `shiploop_git.git`. `stage_lines` adds the look-back block for every stage.
- Repeat packets: if the fail-first test shows a `repeat` packet does not name the previous attempt's result, add one line that does. Revise and replan already have delta lines.

**Cards and docs:**
- `skills/improve/SKILL.md` "Commit policy", `references/callback-evidence.md` (citations become `Learned-from:` lines) and the README rows.
- ShipLoop `SKILL.md`, and `references/project-knowledge.md` "Learnings commit and read-back".

**Fail-first tests:**
- `shiploop-knowledge`:
  - `test_an_empty_commit_leaves_staged_files_staged`
  - `test_every_producer_packet_lists_recent_commits_and_their_lessons`
  - `test_look_back_reads_bare_heading_and_colon_labels_but_not_learned_from`
  - `test_look_back_in_unborn_and_one_commit_repositories`
  - `test_look_back_leaves_out_credential_lines`
  - update `test_intake_quotes_the_last_three_commit_messages`
- `shiploop-actual-improve-cli`:
  - `test_improve_commit_needs_a_key_learnings_section` (refused, the named fix applied, then accepted)
  - `test_improve_commit_resolves_learned_from` (unknown or ambiguous prefix refused; prefix expanded to the full ID; joins an existing `Co-Authored-By` block; no "none cited")
  - `test_nothing_pending_without_lessons_still_says_nothing_to_commit`
  - `test_markdown_headings_survive_cleanup_strip`
  - an import test showing `commit_refusal` names `improve-commit`
  - the `improve-complete` notice test
- `DEFAULT_COMMIT_AUTHORITY` pins in `shiploop-full-runtime`; `shiploop-guidance` card clauses; `improve-plugin` and `improve-runtime` pins.
- `shiploop-packet-completeness` (add a Git fixture), plus `shiploop-packet-bounds` and `shiploop-delegation`: raise the bounds if they trip, never trim.
- The repeat-packet test.

**Change notes:**
- `changes/shiploop/commit-learnings-and-look-back.md`, **minor**.
- `changes/improve/learned-from-commit-format.md`, **patch**.

**Main green means:**
- the footprint suites above pass;
- `check-release-boundary` passes;
- the CI quick tier is green;
- the improve-start size check stays within the unraisable `CONTRACT_BUDGET`, or the contract text is shortened. The budget is derived from the vendored runtime, so here "raise the bound" does not apply.

### Slice 2: delivery commits carry lessons; remote changes become commits with no files

This slice also makes no state change. It needs slice 1.

**Files and symbols:**
- `_RESULT_KEYS` gains `learning` = `{lessons: [str], remote_changes: [{system, change, evidence}]}`.
- Shape check in `_canonical_result`: non-blank, single-line `system`, and `remote_changes` requires lessons.
- The template is unchanged, so no placeholder refusals (C5). The shape is printed in the delivery packet line.
- `knowledge.DELIVERY` = release-plan, release-check, release, operations, plus integrate if D5 is yes.
- `knowledge.check(state, stage, result)`: when a commit will happen (home changed, or `remote_changes` non-empty), lessons are required. The refusal names the verb that actually ran (T15, F22).
- `knowledge.commit(state, stage, result)`:
  - writes the `Learned:` and `Remote change:` sections and the trailers;
  - makes a commit with no files when the home is unchanged and `remote_changes` is non-empty;
  - keeps today's failure posture: a stderr notice, and the run continues.
- `_knowledge_close` reads `after["accepted"][action]` (T14, C8). It already runs in `improve-complete`, so release-plan is covered.
- `_item_commit` adds lessons and trailers from integrate's result.
- `_improve_commit`: a `Remote change` section with nothing pending makes a commit with no files. The guard refuses a second commit with the same Action and Remote-Change since the bind (T20, F17).
- `workspace.follow_up_knowledge_return` counts commits that change no paths as knowledge-only (F18). Today it returns None when `changed` is empty.
- The Improve card extends its one empty-commit rule.

**Packet line (delivery stages):**

> When this stage's done commits (a change under docs/shiploop/, or a remote change you list), ShipLoop writes `learning.lessons` into that commit: give what this stage learned that a later run should reuse. List each remote system this stage changed in `learning.remote_changes` as `{"system": "<alias>", "change": "…", "evidence": "<locator>"}`; ShipLoop records it as a commit with no files when no file changed. Do not run git commit yourself.

**Fail-first tests:**
- `shiploop-knowledge`:
  - `test_a_delivery_stage_that_commits_needs_lessons`, through the real `complete` CLI and through `improve-complete` for release-plan
  - `test_knowledge_commits_carry_lessons_and_trailers`
  - `test_a_remote_change_without_a_file_change_is_a_commit_with_no_files`
  - `test_a_remote_change_beside_a_docs_change_rides_in_the_knowledge_commit`
  - update the release-verify body test
- `shiploop-navigator-v4`: `test_learning_field_shape`
- `shiploop-actual-improve-cli`: `test_improve_commit_records_a_remote_change_once`
- `shiploop-workspace`: `test_a_commit_with_no_files_after_the_return_is_returned`
- `shiploop-callback-contract`: the Checked-by pairing for the new gate (C7)
- The fixtures in `shiploop-full-runtime` and `shiploop-test-loop` supply lessons.

**Change notes:**
- `changes/shiploop/delivery-lessons-and-remote-change-commits.md`, **minor**.
- An improve **patch** note.

**Main green** means the same as slice 1, plus the full-runtime drive to handoff.

### Slice 3: spec working copy and merge at handoff

`STATE_VERSION` goes from 4 to 5, so saved runs are refused by name. This slice needs only slice 1's trailer helper, so it can run beside slice 2.

**Preconditions:**
- D1, D2, D3 and D6 are answered.
- The SPEC S-11 amendment is its own commit (`No-Change-Note: harness spec amendment`): *per-feature plan, test and outcome records; the feature spec is the run's working copy of the living spec, merged into it at handoff and removed once the run's commits reach the user's branch; Git keeps every version*. It supersedes the 09-26 S7 decision and the spec part of the "planning knowledge retained" rule.

**Files and symbols:**
- `knowledge_home`:
  - `STAGE_FILES["spec"] = ("{feature}/spec.md",)`;
  - `CLOSES["prepare"]` drops `spec.md`;
  - new: `start_feature_spec`, `requirement_entries` (a list of entries per ID; whitespace and table padding normalised; a bullet entry ends at a blank line; F9, C2), `spec_changes`, `freeze_refusal`, `id_refusal`, `plan_refusal` and `merge_spec`;
  - `check`: the dropped-ID check moves to the feature spec.
- navigator:
  - a post-save hook calls `start_feature_spec`;
  - `_knowledge_close` writes `spec-planned.md` at prepare;
  - the terminal close calls `merge_spec`;
  - `_improve_commit` refuses the living spec among pending paths;
  - `STATE_VERSION = 5`.
- `shiploop_prompts.py`: the "document" and "spec" prompts point at the feature spec (T4).
- `stage_lines` gets the texts for spec, the stages after it, plan, release-verify and handoff.
- `shiploop_progress_data`: a first run shows "created at handoff"; a merged run shows "merged at <sha12>".
- Docs:
  - `references/project-knowledge.md`: steps 2–4, "Choose one authoritative home" (per D2), the knowledge-home table;
  - `references/current-system-baseline.md` "Retain across runs" (F11);
  - `SKILL.md`, `references/navigator.md` and `references/workspace-lifecycle.md`.

**Packet text:**
- **spec:**

  > This run's spec is `<feature spec>`: ShipLoop copied the living spec `<living>` there (or: there is no living spec yet; write the full spec there). Edit it in place in its own format: change an entry to modify it, add entries from `R-<next>`, move a requirement this run removes under a 'Retired' heading with its reason. Keep every ID and never reuse or revive one. Do not edit `<living>`: it is what holds today, ShipLoop refuses a change to it, and it merges this file into it at handoff. The version committed when planning ends is this run's record of what to do.

- **Stages after spec:**

  > Requirements in force: `<feature spec>`. Change a requirement there, never in `<living>`.

- **handoff:**

  > On done ShipLoop replaces the living spec with this run's feature spec, removes the feature spec once this run's commits reach your branch, and commits both. Do not edit either file at handoff.

**Fail-first tests:**
- `test_the_spec_stage_starts_from_a_copy_of_the_living_spec`: bullet, bold bullet, table and heading fixtures, plus a first run.
- `test_the_living_spec_is_frozen_after_the_copy`: a working-tree edit, an Improve-committed edit and a deleted feature spec are each refused.
- `test_a_dropped_or_revived_requirement_id_is_refused`
- `test_plan_must_name_each_added_and_modified_id`: plan done, via `improve-complete`, and at the prepare close.
- `test_handoff_merges_and_removes_the_feature_spec`: one commit, its trailers, and `git show <Planned>:<path>`.
- `test_handoff_retry_after_a_refused_guard_is_accepted`: CLI route of complete, then guard refusal, then return, then complete (F1).
- `test_a_run_with_no_requirement_changes_removes_its_feature_spec`
- `test_a_first_run_creates_the_living_spec_at_handoff`
- `test_the_working_tree_route_keeps_the_feature_spec`
- `test_an_id_with_a_heading_and_a_table_row_is_compared_as_a_list`
- `shiploop-workspace`: the follow-up return carries the merge, on both routes.
- `shiploop-progress-data`
- `shiploop-navigator-v4`: `test_a_saved_version_4_run_is_refused_by_name`
- `shiploop-cross-run` regex pins.
- `shiploop_knowledge_support.write` and the full-graph fixtures (`full-runtime`, `return-review`, `run-review`, e2e `knowledge_facts`).
- A neutral replay of a saved in-place bullet spec plus an old stub feature spec: a new run copies it with no reformat.

**Change note:** `changes/shiploop/feature-spec-working-copy-merge.md`, **minor**.

**Main green** means slices 1 and 2 are green, plus the above. Release it only after the live batch, because the version bump refuses resumed v4 runs.

### Deferred (not part of this approval)

The Run Review `commits` and `specMerge` fields (a shiploop-run-review **minor**). Until then, the first live runs are measured from `work/` and `git log`.

## 6. Defaults for unknowns, and your decisions

**Defaults** (an unattended run proceeds on these):

| Unknown | Default |
|---|---|
| "CD commit" | Commits accepted at release-plan, release-check, release, release-verify and operations, plus integrate if D5 is yes. Leftovers, the empty baseline, chain merges and the spec merge are mechanical. |
| "Improve commit" | ShipLoop Improve child commits are enforced. The standalone card is text only. The maintainer `improve-loop` and `iterate.py` are out of scope. |
| "Every step iteration" | Every producer packet: each accepted action, implement visit, repeat, revise and replan. Until Loop runtime packets are vendored, so they rely on the card's seven-message read. |
| How many commits | 2 latest, plus 2 latest with lessons. Intake and discovery keep 3 full messages. |
| Look-back scan window | Newest 500 commits. This is chosen, not measured, and it is a scan window, not a prompt cap. |
| Who decides a remote change happened | The model declares it with evidence. The script checks the record, not the remote system. |
| Merge position | Handoff terminal close, the only point no replan can follow. |
| Feature spec after planning | Recorded, not frozen. The Planned trailer names the planned version. |
| Model-typed commits without lessons | A notice plus a count; not refused. |
| `--no-commit` receipt route, `commit.gpgsign`, hex IDs in prose | Unchanged, unchanged, not checked. |
| Planning child through `improve-commit` | Applied. If the reconcile flow conflicts, the slice 1 test shows it and the gap is recorded instead. |
| P11 on the working-tree route | Covered test-first in slice 3. If it does not carry the merge, the handoff guard asks for a full return, as today. |
| Timing | Hold until the live batch finishes; one release per batch. |

**Your decisions** (also in the JSON at the end):
- **D1.** Should the run's spec be a full working copy that the script merges, rather than a delta file the model merges? *Recommended: working copy.*
- **D2.** Should `docs/shiploop/spec.md` be the only merge target, with a team-owned requirements file linked from it rather than merged? This amends "Choose one authoritative home". *Recommended: yes.*
- **D3.** Should cleanup remove only `features/<slug>/spec.md`, and only when the run's commits reach your branch (kept on the working-tree route), with S-11 amended and S7 superseded? *Recommended: yes.*
- **D4.** Should an Improve pass that changes nothing still make no commit, with its lessons going to the `improve-complete` notes? *Recommended: no commit.*
- **D5.** Should integrate's `feat: W…` product commit require lessons? *Recommended: yes.*
- **D6.** Should we ship `STATE_VERSION` 5, refusing in-flight v4 runs by name, after the live batch? *Recommended: yes.*

## 7. Not built, with reasons

- **A commit per implement visit or test-loop pass.** The loop contracts say "Do not commit", and it would put red states into history.
- **Gates for message length or the six Improve labels.** Only Key learnings is enforced (12 of 13 recent `improve-commit` commits already carry all six labels).
- **Required or mechanical citations, citations in stage results, "none cited", and validating hex in prose.**
- **A model-run merge, a delta format, strict per-entry merge checks, or a script that rewrites the spec into a fixed format.**
- **Renumbering, true deletion or reuse of IDs; "pending verification" markers.**
- **A new `spec-merge` stage, or a merge at release-verify or product-acceptance.** The first means pin churn across 34 stages; at the other two a replan can still follow.
- **A listing of unmerged feature specs.** It would be false for every existing repo.
- **The handoff link gate.** It costs turns and stales the return.
- **The lesson ledger, its retry on every dispatch, adoption and self-check.**
- **The `--remote-change` flag.**
- **Requiring `remote_changes` or an N/A at release** (F27). This is a KISS call; the gap is in the risks.
- **Listing tests that still name a retired ID.**
- **Look-back in the Improve parent packet or in Until Loop packets; the item-path query.**
- **A commit-msg hook.** ShipLoop disables hooks on purpose.
- **Run Review fields.** Deferred.
- **Harness `commit_forms` changes.** Script commits never appear there (C15).
- **Detecting ID collisions between concurrent runs.** The return-drift refusal already blocks the second run.

## 8. Risks and what the first live run measures

**Risks:**
1. The frozen contract grows by about 350 bytes against an unraisable budget. A spec contract has already used 8,775 of 9,216 bytes, so improve-start size refusals may follow.
2. Lesson gates may produce filler lessons.
3. Children may still type raw `git commit` (today 14 of the 20 commits models typed themselves fell in Improve windows).
4. Model habit of editing the living spec in place will trigger freeze refusals until the prompts land.
5. Formatting churn may count as "Modified" and add friction at the plan check.
6. Look-back cost in large repositories, and growth in packet bytes.
7. Undeclared remote changes cannot be detected.
8. Squash merges lose the Planned and cited SHAs.
9. A run that stops after release leaves the living spec stale.
10. The v4 refusal affects in-flight runs.

**Measured from the run folder and `git log`, against the same case and host's previous baseline row** (no thresholds):

| Area | Measures |
|---|---|
| Commits | Number of `improve-commit` commits; how many have a Key learnings section; how many cite with `Learned-from` |
| Refusals | Count by first line, and whether the same first line repeats |
| Bypasses and contract size | `fidelity.model_commits` (gate bypasses), improve-start size refusals, and the printed allowance |
| Packets and timing | `packetBytes` and `improvePacketBytes` per stage; timeline seconds for `next` and `complete` |
| Slice 2 | Delivery commits with lessons; commits with an empty `diff-tree` plus their `ShipLoop-Remote-Change` trailers (expect 0 on local cases) |
| Slice 3 | The `ShipLoop-Spec-Merge` commit on the source branch; the feature spec absent but recoverable at Planned; refusals at spec, plan, prepare and handoff; handoff `complete` attempts; retention check #4 |

## 9. Audit findings and their disposition

T = tenet and owner rules, F = failure modes, C = cost and blast radius.

| ID | Severity | Disposition | Why |
|---|---|---|---|
| T1, F4, C3 | blocker/major | **Fixed** (slice 1) | The frozen contract names `improve-commit`; `commit_refusal` and the planning child are routed to it; `improve-complete` gives a notice |
| T2 | major | **Fixed**, needs D1 | Working copy plus a script-run merge |
| T3 | major | **Fixed** | The merge is script-run at the terminal close; the model never edits the living spec |
| T4 | major | **Fixed** | Prompts and both references are added to the slice 3 file list |
| T5, F2, C10 | major/minor | **Dropped** | The unmerged listing would be false for existing repos |
| T6, F12 | major/minor | **Fixed** | A recorded base blob; no history scan |
| T7, F18, C9 | major/minor | **Dropped** | Folded into `_knowledge_close`; no retry, so no commits from read verbs |
| T8 | major | **Fixed** | `learned_from` removed from stage results |
| T9 | major | **Owner decision D5** | I recommend yes |
| T10 | minor | **Fixed** | The section is the trigger; no flag |
| T11 | minor | **Fixed** | One function; not in the Improve parent packet; no item-path query |
| T12, F20 | minor | **Fixed (partly)** | Dropped "none cited", the merge citation, Delivered and "changed after planning"; kept Planned, because it is R2's record |
| T13 | minor | **Fixed** | release-verify reads `outcome.md` only |
| T14, C8 | minor | **Fixed** | Read `after["accepted"]`; the `improve-complete` path is already covered; the P11 rule handles commits after the return |
| T15, F22 | minor | **Fixed** | The refusal names the verb that ran |
| T16, F16, F24, F26 | minor | **Moot** | A wholesale script merge has no fallback, no duplicate application and no model edit at handoff; the wording says only what is checked |
| T17, C6 | minor | **Dropped as a gate** | Release-verify packet text that names only `docs/shiploop/README.md` and `SHIPLOOP.md` |
| T18 | minor | **Fixed** | "Retired" in both files and in the trailer |
| T19, F23 | minor | **Fixed (partly)** | The next free ID is printed and counts `features/*/spec.md`; the test listing is not built |
| T20, F17 | minor | **Fixed** | A duplicate guard on Action plus Remote-Change |
| T21 | minor | **Accepted** | The 43% and 40% claims are removed; the `--no-commit` route is stated; `commit_forms` is untouched |
| T22 | minor | **Deferred** | Run Review fields |
| T23 | minor | **Accepted** | Stated in the non-regression statement |
| F1, C1 | blocker/major | **Fixed** | An idempotent handoff check plus a CLI route test |
| F3 | major | **Fixed** | Planned = HEAD after the prepare close |
| F5 | major | **Fixed** | The base includes earlier uncommitted edits; the refusal moves the change and restores from the blob, never with `checkout`; a first run gets "delete" |
| F6 | major | **Fixed (partly)**, needs D3 | The file is kept on the working-tree route; the squash limit is stated |
| F7 | major | **Fixed** | Git's trailer handling; single-line values |
| F8 | major | **Fixed** | Bare labels accepted |
| F9 | major | **Fixed** | Blob comparison is filter-aware; the entry parser normalises |
| F10 | major | **Fixed (partly)** | Revise and replan already name the result that sent the step back; repeat gets a fail-first test and one line if it is missing |
| F11 | major | **Owner decision D2** | Both references are in the doc list |
| F13, F19, C13 | minor | **Fixed** | `--cleanup=whitespace`; `{7,64}`; `Learned-from: <full ID> <text>` |
| F14 | minor | **Fixed** | The query has no path filter and no `\b` |
| F15 | minor | **Fixed** | Deleting the feature spec is refused at that stage |
| F21 | minor | **Fixed** | No `-i`; only non-empty sections |
| F25 | minor | **Fixed** | Lines flagged by `privacy.sensitive_text` are dropped |
| F27 | minor | **Not built** | KISS; listed as a risk |
| C2 | major | **Fixed** | A list of entries per ID |
| C4 | major | **Fixed** | No run-start scan; the look-back is limited to the newest 500 commits |
| C5 | major | **Fixed** | No placeholder in the template |
| C7 | minor | **Accepted** | The extra suites are in the slice test lists |
| C11 | minor | **Fixed** | First-run progress text; migrations happen in the feature spec |
| C12 | minor | **Fixed** | Lessons are checked only when a commit will be made |
| C14 | minor | **Accepted, mitigated** | Only the command and one rule go into the contract; measured |
| C15 | minor | **Accepted** | No `commit_forms` or `GLUE_COMMIT` change |
| C16 | minor | **Fixed** | Reuse `_sections` and `shiploop_git.git`; no second credential screen |
| C17 | minor | **Accepted** | Slice 0 plus the batch hold |

## owner_decisions

```json
[
  {"id": "D1", "question": "Should the run's spec be a full working copy of the living spec that ShipLoop copies at spec and merges at handoff, instead of an Added/Modified/Removed delta file the model merges?", "recommended": "Yes, working copy", "why": "Models already edit specs in place (24 of 26 saved feature specs ignored the delta format); a script-run merge avoids two requirement files, the leftovers-commit absorption and the false refusals of per-entry checks", "blocks": "Slice 3"},
  {"id": "D2", "question": "Should docs/shiploop/spec.md be the only merge target, with a team-owned requirements file linked from it rather than merged (amending 'Choose one authoritative home' in project-knowledge.md)?", "recommended": "Yes", "why": "The checks are already hard-wired to docs/shiploop/spec.md and no state key names another home; a second target needs detection the script cannot do reliably", "blocks": "Slice 3"},
  {"id": "D3", "question": "Should cleanup remove only features/<slug>/spec.md, and only when the run's commits reach your branch (fast-forward or in-place), keeping it on the working-tree return route, with SPEC S-11 amended and the 09-26 S7 decision superseded for spec.md?", "recommended": "Yes", "why": "On the working-tree route no run commit reaches your branch, so the file is the only record there; the plan, test and outcome files stay as per-feature records", "blocks": "Slice 3"},
  {"id": "D4", "question": "Should an Improve pass that changes nothing still make no commit, with its lessons going to the improve-complete notes?", "recommended": "Yes, no commit", "why": "Audit-only commits flooded history before (daa6bab, 4363650, 3d7ab97, 9562ac0) and the 09-14 plan dropped them; commits with no files stay limited to declared remote changes", "blocks": "Nothing (the default applies)"},
  {"id": "D5", "question": "Should integrate's per-item product commit (feat: W… title) require lessons like the delivery-stage commits?", "recommended": "Yes", "why": "It is the most frequent commit in a run and the natural home for implementation lessons; the risk is filler lessons, which the first live run measures", "blocks": "Slice 2 scope"},
  {"id": "D6", "question": "Should STATE_VERSION 5 ship, refusing in-flight version 4 runs by name, released only after the current live E2E batch finishes?", "recommended": "Yes", "why": "Under one-supported-version, an old run's in-place spec edits would otherwise get stuck at the freeze or at handoff; holding the release protects --resume-run in the batch", "blocks": "Slice 3 release"}
]
```