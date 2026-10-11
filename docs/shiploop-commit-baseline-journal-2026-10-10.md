# Packet and commit counters: the harness build and the baseline of the saved runs (2026-10-10)

Journal of batch 1012 task H (the harness counters and the regrade). Plan of record:
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md`, sections 0d and "Plan of action v5", step 0b: *build `metrics.packets` and
`metrics.commits` first, regrade the saved runs, so a baseline exists before any slice changes what ShipLoop commits or prints*. The
owner approved the plan on 2026-10-10. Evidence is in `docs/experiments/commit-baseline-20261010/`; the code is
`test/shiploop_e2e/counters.py`; the tests are `test/shiploop-e2e-commit-counters.test.py`; the keys are documented in
`test/shiploop_e2e/README.md` ("Packet and commit counters") and named in `test/shiploop_e2e/SPEC.md` (two rows of "How the harness
checks the clauses", their own commit `44fa9671`).

An independent review of the first version (`2b149561`) is answered in section 10; the figures and sentences it corrected are
marked where they stand.
Task I (2026-10-10) replaced the harness's own lessons reader with ShipLoop's `shiploop_lessons` and regraded the baseline (section 11);
the claims it supersedes are marked where they stand.

Status words: **firm** (counted from the saved runs by code that is committed and tested), **interim** (a reading of those counts
that one more run or a live probe could change), **exploratory**, **superseded**.

## 1. The question, and the rule that bounds it

The commit-and-spec plan will change what ShipLoop commits and what its packets print. A same-build cell already ranges 1.75 times
in cost (LEARNINGS.md, "First live runs of the batch 1011 harness"), so no later slice can be judged by cost or wall time. It needs
counters that are mechanical, record-only and in place before anything changes: *how many commits carry a lessons section, how many
cite an earlier commit, how large the printed head and the packet file are, by stage*. Absent means unknown (null and a reason, never
0); no threshold, no verdict, nothing in `result.json`, a baseline row or the exit code. `review.py` was not touched.

## 2. What was built (symbols, not lines)

| Part | Where |
|---|---|
| SPEC rows (anchor S-7 and S-6 for `packets`; S-11 and S-5 for `commits`; the adversarial evaluation is in the commit message) | `test/shiploop_e2e/SPEC.md`, commit `44fa9671` |
| The one reader of replies | `metrics.ToolLog.replies` and `metrics.KEPT_REPLY`, filled in `ToolLog.result` for every host (each call's first result only) |
| `packets` block | `counters.packets`, `counters.head_or_why` (the head, or why a reply is not whole), `counters.heads` |
| `commits` block | `counters.history` (one row per commit: the classification), `counters.commits` (counts the rows), `counters.lessons`, `counters._starting_point`, `counters._objects`, `counters._item_prefixes` |
| Wiring | `counters.safe_build` called in `run._main` beside `fidelity.safe_build`; so `--resume-run <dir> --grade-only` adds the four keys to a run that has none |
| Regrade | `docs/experiments/commit-baseline-20261010/regrade.py` writes `baseline.json`; read-only |
| Tallies (review round, section 10) | `docs/experiments/commit-baseline-20261010/tallies.py` writes `tallies.json`: the head replies by reason (F2) and the commits by author (F6); read-only |
| Mutation record | `docs/experiments/commit-baseline-20261010/mutants.py` and `mutants-result.json` |
| Fixtures | `test/fixtures/commit-counters/` (`cut_fixtures.py`, five extracts, `messages.json`) |
| Registration | `test/suite_catalog.py` (the suite, its duration, the fixture and evidence prefixes), `test/test-groups.test.py` (76 ShipLoop suites, 117 in all, the E2E family gains it) |

### Shapes written (metrics.json only)

```
packets:            null | [ {action: str, stage: str|null, file_bytes: int, head_bytes: int|null}, ... ]   run order, one per packets/*.md
packets_unmeasured: {} | {"head_bytes": "<hosts>: N of M packets have no whole print ..."} | {"packets": "<why the block is null>"}
commits:            null | {improve: {n, with_lessons, cited, cited_earlier_run}, script: {n, with_lessons}, other: {n, with_lessons},
                          counted: int, start_head: str|null}
commits_unmeasured: {} | {"commits": "<why the block is null>"}
```

`counters.history` (not written to metrics.json) returns `{work, start, commits: [{id, kind, author, subject, message, knowledge}]}`,
the rows the `commits` block counts; `regrade.py` and `tallies.py` read it. `tallies.json` is `{schema, harness_head, reads, runs,
head_replies: {all, by_host}, other_commits: {all, by_host}, commits_by_author: {by_host: {host: {improve, script, other: {author: n}}}},
per_run}`: counts only, with no commit id, message or packet text.

`action` is the packet file's name without `.md`, so it is the unique key: a stage visited again (repeat, revise, replan) is a new
action with its own file, and the second packet of a bound Improve child is its own file, `<action>-improve`, with the same stage
(strip the suffix to join to `state.md`'s history). `start_head` is null for a fresh run (its whole history is the run's) and the
recorded head for a `--continue-from` or `--seed-at` run (only later commits count). `other` and `counted` were added to the brief's
shape so that the classes sum to the commits counted and nothing is dropped.

### What a "head" and a class are

- **Head.** A reply holds ShipLoop's whole head only from its `ShipLoop navigator |` line to its own closing line (the status
  block's end, then the narrative block's when one follows), with the packet's `Full packet:` line naming the file and the callback
  and keepalive lines unshortened. What comes before (a command's own output, Grok's `exit: 0` line) and after (the host's cwd note,
  output the model chained) is not counted. A call that names a packet file is the model reading it, never a print. The first whole
  print counts. Otherwise `head_bytes` is null.
- **Improve commit.** The commit ShipLoop's own `improve-commit` reply names. **Script commit**: the work item's commit (its reply, or
  its subject `feat: <work item id> <title>` with an id of the run's `state.md`) and the commits whose subject only ShipLoop writes
  (`docs(shiploop): record <feature> knowledge at|after <stage>`, `Empty baseline for the first ShipLoop run`, the leftovers commit,
  a chain's prepared merge). **Other**: everything else, which is the model's own `git commit`.
- **Lessons.** A non-empty `Key learnings` (the Improve card's label) or `Learned` (the knowledge home's release-verify body)
  section. Presence only. **Cited**: an Improve commit with a `Learned-from: <id>` line at a line's start whose id resolves to a
  commit; **cited_earlier_run**: a cited commit reachable from `start_head`.
- **Lessons reader.** No ShipLoop code reads a commit message's sections: `shiploop_knowledge_home._sections` parses `#`-headed
  markdown files (outcome.md). So `counters.lessons` is the one reader in the harness (a few lines; the brief asked for a one-paragraph
  justification and this is it). It takes the knowledge home's label from `knowledge_home.LEARNING_SECTIONS` (a test pins that
  `Learned` is one of them) and the Improve card's from `skills/improve/SKILL.md`. When slice B gives ShipLoop a reader of commit
  sections, `counters.py` imports it and this one goes.
  **Superseded 2026-10-10 (section 11):** `shiploop_lessons` is that reader and `counters.py` imports it; `counters.lessons` is gone.

## 3. How it was built (fail-first, mutants)

| Step | What was run first | Result |
|---|---|---|
| Packets | 29 tests against a stub that listed the packet files and measured no head | 16 failed, 6 errored (missing `ToolLog.replies`, `KEPT_REPLY`, constants), 7 passed (null is what the stub returned); all 29 pass with the code |
| Commits | the commit tests against a placeholder returning null and `lessons` of "" | of the 52 tests then in the file, 22 failed (14 failures, 8 errors) and the 30 packet tests passed; all pass with the code |
| Work item subject | the signature change alone, with the new test | `(5, 5)` where `(6, 4)` was expected; passes with the rule |
| Wiring | four mutants of `run._main` | line removed and unguarded `build` were killed at once; an empty tool log and no run directory survived until a test pinned what the builder is handed |
| Mutants of `counters.py` and `metrics.py` | 32 one-line mutants, first round | 3 survived: a host-note strip that proved redundant (deleted), a whole head with no `Full packet:` line given to the first file, a citation anywhere in a line; each got a test or was removed |
| Final | `mutants.py` (36 mutants) | 36 of 36 killed, `mutants-result.json` |
| Review round (section 10) | 8 new tests for `head_or_why` and `history`, 9 for the regrade and the tallies, 1 for the work item subject, each run before its code; `mutants.py` again | 40 of 40 killed (36 patterns kept or updated, 4 mutants added) |

Process safety: the tests start no host, model, server or browser; git runs in temporary repositories with their own HOME and
`GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`; the counters read a run's repository with `rev-list`, `cat-file`,
`rev-parse`, `merge-base` only (no `status`, nothing that writes an index); the regrade opens saved runs read-only and skipped a run
whose harness was alive (below).

## 4. Findings

**F1. Improve commits cannot be told by their message (firm).** 63 of the 132 distinct commits that `improve-commit`'s reply names,
in the saved runs, carry none of the six `Review:`, `Plan:`, `Changes:`, `Validation:`, `Key learnings:`, `Remaining work:` lines
(v1230 Sonnet 6 of 6 are free prose; r1 Checkers 4 of 4), and a model's own `git commit` can carry several of them (the four raw
commits of the 2026-10-03 Battleship run carry three or four of the six). Author identity does not separate them either: ShipLoop commits as the
repository's configured identity when there is one (the Grok and Codex runs have one `shiploop-e2e` identity for the model and
ShipLoop alike). So the discriminator is ShipLoop's own reply, a line the host's tool result records. The brief and the plan expected
a message shape; this is the deviation that matters most. Evidence: `baseline.json` (`improve` n against `with_lessons`),
`test/fixtures/commit-counters/messages.json` (the real label-free and six-label messages), the ClassifyTest cases.

**F2. A head is measurable only where the model did not slice the reply (firm).** Sonnet pipes `complete` through `head`, `sed -n`
and `cut` in most calls, so the recorded reply is the model's slice, not ShipLoop's print. Whole is told from the output, not the
command: a pipe elsewhere in a compound command does not hide a whole head, and a script of the model's own that slices inside
leaves no pipe to see. Coverage in the 38 saved runs: Claude 125 of 1,190 packets (10.5%; the intake head of every run, 28 of 28),
Grok 90 of 159 (56.6%), Codex 73 of 75 (97.3%), the mixed-host run 13 of 52. Every run has at least one head measured; a few Codex
and Grok runs have all of them (v1200 Luna 4 of 4, v1210 Luna xhigh 24 of 24, r3 Grok 16 of 16). Of the 1,559 heads the recorded
replies start (a reply can hold more than one), 437 are whole, 1,082 end before a closing line, 38 open the narrative and end
inside it, and 2 keep every line with a shortened callback line (a cut by column); by host, Claude 153 whole of 1,204, Codex 151 of
151, Grok 117 of 168 and the mixed-host run 16 of 36 (`tallies.json`, committed in the review round of section 10; these count
heads, reprints included, where the 125, 73, 90 and 13 above count packets with a measured head). Status: firm. The consequence for the baseline: a Claude "printed heads shrank" comparison rests on the intake head and on a few
uncut replies; Grok and Codex carry the rest. A script-written record of each head ShipLoop prints (one file per action, written by
the script that prints it) would make `head_bytes` exact on every host. That is a ShipLoop change, outside this task and the fork's
packet pass, and it is the open item below.

**F3. Grok is recoverable (firm).** The brief expected Grok to leave nothing; its final `tool_call_update` records the reply as
`output_for_prompt` after an `exit: N` line and carries its own `total_bytes`. The measured head equals `total_bytes` where the head
is the command's whole output (6,344 and 6,027 bytes in the two extracts) and equals it minus the command's own first lines where it
is not (the intake extract). That agreement is an independent check of the byte count.

**F4. The packet file's header is not on line 1 (firm).** 24 of the fork's 46 packets open with the delegation preamble, so the
`ShipLoop navigator | <stage> | revision N` line is line 1, 12 or 16, and a Claude "Continue in this context" or an Improve "Keep the
invoking parent alive" preamble sits above it. `stage` is read from the first header line anywhere in the file. The `-improve` file
of a bound Improve child is a second packet for one action and the largest in its stage (the baseline reports it as its own row).

**F5. The lessons shares (firm for the counts; interim as a reading).** Of 331 knowledge-home commits, 30 (9%) carry a lessons
section: the release-verify commit of each of the 28 finished Claude runs, and one Grok and the mixed-host run. The plan's 91%
subject-only holds. Of 132 Improve commits, 68 carry one (Claude 38 of 81, Codex 13 of 34, Grok 17 of 17); the plan's "12 of 13 carry
every label" holds for Grok and for some Claude runs (r2 and r3 Checkers 8 of 8 and 6 of 6) and not for others (v1230 Battleship 0
of 6, r1 Checkers 0 of 4, 20261010 Battleship 0 of 5). **Counted with the narrow reader on 38 runs; the shared reader on 39 runs counts 74 of
136 Improve commits (Claude 44 of 85), section 11.3.** Nothing cites: `cited` and `cited_earlier_run` are 0 of 132, measured (the field
is defined, the history was read, nothing writes `Learned-from:`).

**F6. Reading what a classifier left over (firm).** The first classification left 40 commits in `other`; 5 were ShipLoop's own work
item commits whose reply the model had cut, now matched by subject. The 35 that remain are all the model's own `git commit`, none
ShipLoop's. In Claude and mixed-host runs ShipLoop commits as its workspace identity (`ShipLoop Workspace` on all 357 improve and
script commits of the 28 Claude runs, and on 4 of the 20 script commits of the mixed-host run, the other 16 being `ShipLoop E2E`)
while the model's raw `git commit` falls back to the machine's Git identity (32 commits: 22 Claude, 10 mixed-host), so no `other`
commit there shares an identity with a ShipLoop commit. In Grok and Codex runs, which configure one identity (`ShipLoop E2E`) for the
model and ShipLoop alike, the 3 `other` commits (Codex 2, Grok 1) are told by git's own `[branch sha] subject` line for their
abbreviated id in the events (3 of 3). Evidence: `tallies.json` (`other_commits`, `commits_by_author`; the author names are the Git
identities the commits carry). Two Codex commits
that looked like Improve commits (no labels, the `shiploop-e2e` identity) are bypasses, shown by that confirmation line.

**F7. Item commits are announced only when the reply survives (firm).** `ShipLoop committed W1's declared changes as <sha>` is cut
along with the rest of a piped reply, so the work item rule also reads `state.md`'s `work_items`; a model commit that starts `feat:`
but names no work item stays `other`.

**F8. A live run was left alone (information).** `20261010/pc1i-checkers-sonnet` belongs to another session and its harness held the
case lock (`listeners.case_alive`) while this regrade ran, so its record was still being written; the regrade lists it under
`not_regraded` and counts nothing from it. The run ended before this journal was finished, and a regrade run after that
reads 39 runs (identical across two repeats) and differs from the committed file by that run and the `harness_head` stamp, so
`baseline.json` is the regrade of the 38 finished runs that existed when the work was done, not of whatever the folder holds later.

## 5. The brief's questions, with counts

### Per host (38 finished runs; the mixed-host run, `20261008/r2-battleship-grok-none`, Grok first and then Claude, is its own row)

| Host | Runs | Packets | Heads measured | Runs with any head | File bytes median (min-max) | Head bytes median (min-max) |
|---|---|---|---|---|---|---|
| claude | 28 | 1,190 | 125 (10.5%) | 28 | 37,145 (14,647-63,859) | 4,841 (1,317-6,985) |
| codex | 4 | 75 | 73 (97.3%) | 4 | 45,288 (24,304-67,223) | 4,756 (4,035-6,289) |
| grok | 5 | 159 | 90 (56.6%) | 5 | 39,897 (18,976-60,068) | 5,895 (2,943-7,126) |
| mixed host (grok then claude) | 1 | 52 | 13 (25.0%) | 1 | 40,042 (19,150-57,301) | 6,129 (3,409-7,147) |

| Host | Commits | Improve n / lessons / cited / cited earlier | Script n / lessons | of which knowledge n / lessons | Other n / lessons |
|---|---|---|---|---|---|
| claude | 379 | 81 / 38 / 0 / 0 | 276 / 28 | 214 / 28 | 22 / 1 |
| codex | 74 | 34 / 13 / 0 / 0 | 38 / 0 | 33 / 0 | 2 / 0 |
| grok | 96 | 17 / 17 / 0 / 0 | 78 / 1 | 67 / 1 | 1 / 0 |
| mixed host (grok then claude) | 30 | 0 / 0 / 0 / 0 | 20 / 1 | 17 / 1 | 10 / 0 |

Per host+model+effort cells (all one model per host except Codex, `max` against `xhigh`) are in `baseline.json` under
`summary.by_cell`, with the per-stage figures.

### Per run and per class

`I` = Improve commits and how many carry lessons; `S` = script commits and how many carry lessons, with the knowledge home's own
commits in brackets; `O` = other. Cited is 0 everywhere. Heads = measured / packets.

| Run | Hosts | Engine | I n / lessons | S n / lessons (knowledge) | O n / lessons | Heads |
|---|---|---|---|---|---|---|
| 20261003/batch-sonnet/battleship | claude | done | 3 / 0 | 8 / 1 (5 / 1) | 4 / 0 | 10 / 49 |
| 20261003/batch-sonnet/battleship-scoring | claude | done | 6 / 0 | 7 / 1 (6 / 1) | 0 / 0 | 9 / 37 |
| 20261003/batch-sonnet/hello | claude | done | 2 / 2 | 9 / 1 (7 / 1) | 0 / 0 | 5 / 36 |
| 20261003/batch-sonnet/seat-reservations | claude | done | 4 / 0 | 12 / 1 (9 / 1) | 1 / 0 | 9 / 58 |
| 20261003/battleship-luna | codex | blocked | 4 / 2 | 5 / 0 (4 / 0) | 0 / 0 | 6 / 7 |
| 20261003/hello | claude | done | 2 / 2 | 10 / 1 (8 / 1) | 0 / 0 | 3 / 36 |
| 20261003/seat-reservations | claude | done | 3 / 0 | 13 / 1 (10 / 1) | 3 / 0 | 5 / 37 |
| 20261003/v1161-battleship-luna | codex | blocked | 18 / 6 | 19 / 0 (17 / 0) | 2 / 0 | 39 / 40 |
| 20261003/v1161-hello | claude | done | 0 / 0 | 12 / 1 (10 / 1) | 0 / 0 | 2 / 36 |
| 20261004/v1180-hello-sonnet | claude | done | 5 / 0 | 10 / 1 (7 / 1) | 0 / 0 | 2 / 35 |
| 20261004/v1190-hello-sonnet | claude | done | 3 / 0 | 10 / 1 (8 / 1) | 0 / 0 | 4 / 35 |
| 20261004/v1190-hello-sonnet-2 | claude | done | 5 / 5 | 12 / 1 (10 / 1) | 0 / 0 | 2 / 48 |
| 20261004/v1200-battleship-luna | codex | active | 0 / 0 | 3 / 0 (2 / 0) | 0 / 0 | 4 / 4 |
| 20261004/v1200-hello-sonnet | claude | done | 0 / 0 | 11 / 1 (9 / 1) | 0 / 0 | 7 / 36 |
| 20261005/v1210-battleship-grok-medium | grok | active | 15 / 15 | 9 / 0 (8 / 0) | 0 / 0 | 11 / 12 |
| 20261005/v1210-battleship-luna-xhigh | codex | active | 12 / 5 | 11 / 0 (10 / 0) | 0 / 0 | 24 / 24 |
| 20261006/v1220-battleship-grok-medium-none | grok | done | 1 / 1 | 22 / 1 (18 / 1) | 0 / 0 | 16 / 53 |
| 20261006/v1220-battleship-sonnet | claude | done | 6 / 6 | 9 / 1 (8 / 1) | 3 / 1 | 2 / 47 |
| 20261007/v1230-battleship-grok-none | grok | blocked | 0 / 0 | 24 / 0 (21 / 0) | 1 / 0 | 20 / 50 |
| 20261007/v1230-battleship-sonnet | claude | done | 6 / 0 | 10 / 1 (7 / 1) | 1 / 0 | 2 / 47 |
| 20261008/r1-battleship-grok-none | grok | blocked | 1 / 1 | 13 / 0 (11 / 0) | 0 / 0 | 27 / 28 |
| 20261008/r1-battleship-sonnet | claude | done | 3 / 0 | 12 / 1 (9 / 1) | 0 / 0 | 2 / 44 |
| 20261008/r1-checkers-sonnet | claude | done | 4 / 0 | 7 / 1 (5 / 1) | 2 / 0 | 2 / 45 |
| 20261008/r2-battleship-grok-none | grok+claude | done | 0 / 0 | 20 / 1 (17 / 1) | 10 / 0 | 13 / 52 |
| 20261008/r2-battleship-sonnet | claude | done | 2 / 2 | 10 / 1 (7 / 1) | 1 / 0 | 2 / 43 |
| 20261008/r2-checkers-sonnet | claude | done | 8 / 8 | 10 / 1 (8 / 1) | 0 / 0 | 2 / 46 |
| 20261008/r3-battleship-grok-none | grok | active | 0 / 0 | 10 / 0 (9 / 0) | 0 / 0 | 16 / 16 |
| 20261008/r3-battleship-sonnet | claude | done | 3 / 3 | 10 / 1 (8 / 1) | 2 / 0 | 6 / 45 |
| 20261008/r3-checkers-sonnet | claude | done | 6 / 6 | 9 / 1 (6 / 1) | 0 / 0 | 2 / 47 |
| 20261009/s6-after-spec | claude | done | 0 / 0 | 8 / 1 (6 / 1) | 3 / 0 | 27 / 39 |
| 20261009/s6-inside-implement | claude | done | 0 / 0 | 9 / 1 (7 / 1) | 0 / 0 | 3 / 37 |
| 20261009/s6-inside-implement-k2 | claude | done | 1 / 0 | 9 / 1 (7 / 1) | 0 / 0 | 2 / 39 |
| 20261009/s6-inside-implement-mtime | claude | done | 0 / 0 | 9 / 1 (7 / 1) | 0 / 0 | 5 / 39 |
| 20261009/s6-inside-implement-write | claude | done | 1 / 1 | 8 / 1 (6 / 1) | 0 / 0 | 2 / 39 |
| 20261009/s6-inside-test-strategy | claude | done | 0 / 0 | 12 / 1 (10 / 1) | 0 / 0 | 2 / 59 |
| 20261009/s6-inside-test-strategy-2 | claude | done | 0 / 0 | 11 / 1 (9 / 1) | 0 / 0 | 2 / 39 |
| 20261010/battleship-1 | claude | done | 5 / 0 | 11 / 1 (8 / 1) | 0 / 0 | 2 / 46 |
| 20261010/checkers-1 | claude | done | 3 / 3 | 8 / 1 (7 / 1) | 2 / 0 | 2 / 46 |
| 20261010/pc1i-checkers-sonnet | claude | not regraded (live) | | | | |

### Median and range per stage, Claude (28 runs, one model, bytes; Improve packets are their own rows)

Medians are rounded to a whole byte the way the harness rounds (Python `round`, half to even); `baseline.json` holds the exact
value, which ends in .5 where two sizes straddle it (the first version of this table truncated them: 8 cells were one byte low,
corrected in the review round).

| Stage | Packets | file_bytes median (min-max) | Heads measured | head_bytes median (min-max) |
|---|---|---|---|---|
| baseline | 32 | 30,922 (27,823-32,759) | 1 | 5,184 (5,184-5,184) |
| carry-forward | 31 | 39,077 (37,296-56,985) | 5 | 2,863 (2,650-5,172) |
| carry-forward [Improve packet] | 17 | 52,670 (51,212-53,929) | 6 | 3,121 (3,079-3,663) |
| discovery | 28 | 41,290 (38,601-43,908) | 3 | 5,181 (5,173-6,352) |
| document | 31 | 35,440 (31,947-36,715) | 3 | 4,003 (3,811-5,335) |
| done | 28 | 16,454 (14,647-17,889) | 0 | - |
| get-next-work-item | 17 | 30,112 (29,452-30,771) | 1 | 5,700 (5,700-5,700) |
| handoff | 28 | 33,118 (29,401-35,409) | 0 | - |
| implement | 86 | 40,454 (36,768-43,123) | 6 | 5,207 (4,429-6,021) |
| intake | 28 | 27,759 (25,087-28,979) | 28 | 5,489 (4,314-5,643) |
| integrate | 31 | 35,266 (32,281-37,504) | 3 | 5,224 (5,191-6,317) |
| integration-verify | 31 | 37,212 (33,763-39,288) | 2 | 4,466 (4,002-4,930) |
| operations | 28 | 30,442 (27,657-32,146) | 0 | - |
| plan | 28 | 55,880 (53,621-63,859) | 1 | 6,985 (6,985-6,985) |
| plan [Improve packet] | 9 | 58,120 (56,605-59,136) | 0 | - |
| prepare | 28 | 31,176 (28,211-32,756) | 1 | 6,057 (6,057-6,057) |
| product-acceptance | 28 | 35,918 (32,497-37,504) | 2 | 6,162 (5,503-6,820) |
| regression | 30 | 41,373 (37,262-43,077) | 3 | 5,014 (4,841-6,292) |
| release | 28 | 30,825 (27,954-32,499) | 1 | 5,257 (5,257-5,257) |
| release-check | 28 | 30,942 (28,101-34,186) | 2 | 5,500 (5,412-5,589) |
| release-plan | 28 | 40,683 (36,856-49,720) | 2 | 6,330 (5,697-6,964) |
| release-plan [Improve packet] | 16 | 50,702 (47,709-53,080) | 0 | - |
| release-verify | 28 | 34,884 (31,262-36,523) | 0 | - |
| research | 28 | 36,218 (33,759-37,680) | 2 | 4,962 (4,952-4,971) |
| select-work | 14 | 28,154 (26,406-29,716) | 0 | - |
| skill-assess | 27 | 30,798 (27,846-32,570) | 3 | 4,099 (3,938-5,093) |
| skill-validate | 27 | 29,951 (26,589-31,350) | 1 | 5,014 (5,014-5,014) |
| spec | 28 | 40,124 (38,326-51,926) | 12 | 3,694 (3,527-5,021) |
| spec [Improve packet] | 9 | 47,258 (45,278-48,033) | 9 | 4,019 (3,529-4,644) |
| static-checks | 31 | 43,109 (38,030-44,347) | 2 | 4,656 (4,227-5,085) |
| step-plan | 33 | 53,227 (49,253-56,881) | 5 | 2,814 (1,317-6,402) |
| step-plan [Improve packet] | 9 | 53,520 (52,004-54,528) | 0 | - |
| system-test | 32 | 33,980 (30,341-35,851) | 0 | - |
| system-test-author | 31 | 37,107 (34,621-46,187) | 4 | 5,336 (3,962-6,922) |
| system-test-author [Improve packet] | 17 | 46,625 (45,186-47,630) | 1 | 3,938 (3,938-3,938) |
| test-author | 32 | 37,832 (33,890-39,271) | 3 | 4,281 (2,685-5,570) |
| test-green | 32 | 37,802 (33,958-39,807) | 3 | 5,550 (2,741-5,602) |
| test-red | 32 | 36,118 (32,739-38,297) | 2 | 4,658 (4,258-5,058) |
| test-refine | 32 | 39,146 (35,523-40,824) | 3 | 2,090 (1,966-4,937) |
| test-spec | 32 | 36,620 (34,174-49,531) | 2 | 4,258 (2,298-6,217) |
| test-spec [Improve packet] | 9 | 47,855 (46,470-48,852) | 0 | - |
| test-strategy | 28 | 38,615 (36,360-47,979) | 1 | 6,417 (6,417-6,417) |
| test-strategy [Improve packet] | 9 | 47,849 (45,602-48,339) | 0 | - |
| verify | 31 | 43,465 (38,057-46,313) | 2 | 4,620 (4,130-5,110) |

Small heads (1,317 to about 3,100 bytes) are the Improve-parent shape (`Next command (bind the selected Improve ...)`), which has no
Goal or Done-when lines, and loop stages with short Done-when lists; they are whole by the same rule.

### Which runs could not be regraded

One: the live run above. Every other folder had its work directory, a Git repository, its events and its run directory (none was
deleted or moved), so none was lost to missing data. `20261003/battleship-luna`, `v1161-battleship-luna`, `20261004/v1200-battleship-luna`
and `20261005/v1210-battleship-luna-xhigh` (Codex) read their packets from the run folder like the others and their events through the
harness translator; `r2-battleship-grok-none` is named mixed-host by `runrecord` (Grok launched it, Claude finished it) and is
summarised alone. The regrade covers 38 finished runs, a superset of the brief's list (it also has the 2026-10-03 batch, the hello
cells of 10-03 and 10-04, and the 10-06 runs).

### Anything surprising

F1 (the discriminator), F2 (Claude's heads are mostly unmeasurable), F3 (Grok is measurable), F6 (five ShipLoop commits hid in
`other`), and the `Next command (bind the selected ...)` head shape. Not surprising: every Claude run's intake head is whole.

## 6. Decisions and deviations from the brief

- `head_bytes` for Grok and Codex is measured, not null (F3). The null reason is written once, with the host named and counts.
- The Improve class is named by ShipLoop's reply, not a message shape (F1); `script` has two sources (a reply, a ShipLoop-owned
  subject); an `other` class and `counted` and `start_head` were added to the block (the brief asked that nothing be dropped).
- Regrade is a script beside the evidence (`regrade.py`), not a second CLI flag: `--grade-only` rewrites `metrics.json` and
  `result.json` in place (forbidden here) and `--baseline-report` reads saved `metrics.json` files, which lack the new keys. The script
  calls the same functions (`run.run_folders`, `run.grade_shiploop`, `metrics.collect`, `counters.build`), so it is not a second parser.
- `counters.lessons` is a small reader of its own (section 2), because no importable one exists. **Superseded 2026-10-10 (section 11):**
  `shiploop_lessons` exists and the harness imports it.
- The README states the first-print and one-byte limits and the cut-by-column limit; the packets block is not printed in the run
  report (record-only).
- The knowledge-commit share (9%) is a subtotal of `script` kept in `baseline.json` (`knowledge_commits`) and is not a key of a run's
  `metrics.json` (review round, finding 5; the reviewer offered adding it or saying so). The plan names `script {n, with_lessons}`, an
  extra or nested key changes what the Run Review fork reads, and slice B moves `script.with_lessons` whether or not the subtotal is a
  key. So a later run is compared with the baseline through `script.with_lessons` over `script.n` (Claude 28 of 276 here), or through
  `regrade.py` for the knowledge share itself.
- `improve` is a lower bound (SPEC row amended in `6b9a4247`): it is the commits ShipLoop's own `improve-commit` reply names in the
  host's events (open item 6).
- Nothing outside `test/`, `docs/` and this branch changed: no `skills/` edit, so no change note; `review.py`, `render()`,
  `packet_head()`, `DUTIES` and the knowledge-home code were not touched.

## 7. Deferred and open

1. **A script-written head record.** If ShipLoop wrote each head it prints to `run/packets/<action>.head` (or recorded its size in
   `state.md`), `head_bytes` would be exact on Claude too. It changes ShipLoop and the fork owns the packet pass: a recommendation,
   not built.
2. **Slice B imports the commit-section reader** when ShipLoop has one; `counters.lessons` is removed then. **Done 2026-10-10 (section 11,
   `4d423333`).**
3. **`Learned-from:` is measured at zero**; the first run after slice B is the first that can move `cited`. `cited` counts Improve
   commits only, as the brief defined it.
4. The cut-by-column test catches a shortened callback or keepalive line only; other columns of a `cut -c` are not told (2 of the
   439 replies that were complete line for line, in r2 Grok and an s6 Claude run, were cut that way and are null).
5. `baseline.json` is not refreshed by CI; it is the 2026-10-10 baseline. Re-run `regrade.py` after the next batch of runs and keep
   the old file.
6. **The `improve` class after slice B (review round, finding 3; unverified).** Plan v5 slice B moves `improve-commit` into the frozen
   Improve child contract. The class exists only where the parent session's tool results hold ShipLoop's `improve-commit` reply
   (`counters.history`). If a host does not record a sub-agent's tool results in the stream the harness saves, those replies vanish,
   `improve.n` falls toward 0 and the commits land in `other` with no null and no reason. What a child's results look like in the
   parent's stream is not known: no saved stream shows one (the 29 Claude run folders, one of them the run that was live at the regrade: 15,570 events, no `Task` or `Agent` tool call; the 35
   events that carry a `parent_tool_use_id` are `tool_progress` heartbeats of a Bash call), and checking needs a live host, which this
   task may not start. The reviewer suggested classifying by the `ShipLoop-Action` / `ShipLoop-Stage` trailers once slice B writes
   them, but the plan **cut** those trailers (its table of cut items: "No consumer reads them", reversed if Run Review reads commit
   trailers), so this is an owner decision and nothing here assumes them. Until a classifier has something of its own to read, a
   comparison across slice B reads `other` beside `improve`. The SPEC row, the README and the `counters` docstring say so.
7. **The 9% knowledge share is comparable only through `regrade.py`** (section 6), or through `script.with_lessons` over `script.n`.
8. **Slips in four commit messages, not rewritten** (history stays as committed): `8c436507` says `baseline.json` is "62 KB" (it is
   68,136 bytes); `63d6882d` says the mutants and the regrade "are in the journal commit" (they are in `8c436507`, the journal is
   `2b149561`); `44fa9671` says a pipe-cut reply "is documented as the cut size", which `6b9a4247` supersedes; and `6b9a4247` itself says
   a comparison across slice B reads `other` "until the commits carry a trailer", while the plan cut those trailers (item 6).

## 8. For the E2E fork (the exporter reads `metrics.json` generically)

The exact keys are in section 2. `packets` is a list in run order, null when the run has no run directory or no `packets/` folder;
`packets_unmeasured.head_bytes` is one string, present only when some `head_bytes` is null. `commits` is null with
`commits_unmeasured.commits` when the repository, the starting head or `events.jsonl` cannot be read. The Run Review figures this
could feed: printed-head bytes by stage (measured where non-null; Grok and Codex mostly, Claude's intake), packet file bytes by
stage, commits by class with `with_lessons` and `cited`. A reader must treat `head_bytes: null` as unknown and not 0, and should
join an `-improve` action to its stage's action by stripping the suffix.

## 9. Verification record (first round, at `2b149561`)

Run on 2026-10-10 in the worktree of branch `batch1012h-1bbefb` (base `658ff4e3`), `SHIPLOOP_PROGRESS=off`, machine load average about
5 (other sessions share it). Exit codes are the commands' own, captured without a pipe.

| Command | Exit | Note |
|---|---|---|
| `python3 test/shiploop-e2e-commit-counters.test.py` | 0 | 68 tests OK, 12 s |
| `python3 test/test-groups.test.py` | 0 | 28 tests OK (76 ShipLoop suites, 117 in all) |
| `bash test/run-all.sh --group quick --changed-from 658ff4e3` (the quick tier: 3 core, 28 ShipLoop, the mock replay) | 1 | 32 of 33 suites passed: `shiploop-e2e` 404 tests (112 s), `-runrecord`, `-fidelity`, `-reorientation`, `-environment`, `-baseline`, `-quality`, `-commit-counters`, `-run-review` (which reads the SPEC), `shiploop-navigator-contract`, `test-groups` and the rest; **`shiploop-status-display` failed** |
| `python3 test/shiploop-status-display.test.py` on this branch, and on an export of `658ff4e3` | 1, 1 | The same single failure on both: `test_every_dry_run_packet_carries_the_block_inside_the_kept_head` (delegation `ask-agent`, scenario `revise`, sequence 20): the status block's end is at character 8003 on this branch (8023 in the export, a longer path) and the hook window is 8000. No `skills/` or `agents/` file differs from the base (`git diff 658ff4e3 --stat -- skills agents` is empty), so it is not caused by this branch; not mine to fix here (packet heads are the E2E fork's pass) |
| `python3 docs/experiments/commit-baseline-20261010/mutants.py` | 0 | 36 of 36 mutants killed |
| `python3 docs/experiments/commit-baseline-20261010/regrade.py`, run twice at a time | 0, 0 | the two outputs were byte-identical (twice with 38 regraded and 1 skipped, the committed file; twice again with 39 regraded after the live run had ended) |
| `python3 scripts/check-release-boundary.py --base 658ff4e3 --head HEAD` | 0 | `check-release-boundary: OK` |

A timing-sensitive failure was not seen, so no rerun was needed. Not run: the full hermetic tier (it runs in CI on a release commit),
any live E2E run, any host CLI or model. The new suite is not slow enough to leave the quick tier (13 s against 120 s).

## 10. The independent review of 2026-10-10 and the fix round

An independent reviewer read `2b149561` and returned six findings (one major, five minor). Each was reproduced or checked before
anything was changed; the rows say what was found and done.

| # | Severity | Finding | Reproduced | Disposition | Where |
|---|---|---|---|---|---|
| 1 | major | The SPEC `packets` row says a pipe-cut reply "shows the cut size", that the head runs "to the end of the reply" and that `stage` is the file's first line; the code, README, docstring and tests say the opposite on all three | `grep` of the row; `test_a_head_the_model_cut_after_its_keepalive_line_is_null_not_zero_and_not_the_cut_size` asserts null | **Fixed.** The row is amended in its own `docs(shiploop-e2e-spec)` commit and says: a cut reply is null, the head ends at its closing line, `stage` is the first navigator line anywhere in the file. No test was written first: it is a document defect and the code's behaviour was already pinned | `6b9a4247` |
| 2 | minor | The work item subject `feat: <id> <title>` is the one ShipLoop text the classifier reads that no test pins to ShipLoop's source | In a scratch export, `"feat: "` changed to `"item(W): "` in `_item_commit`: 68 tests OK, exit 0 | **Fixed.** The new test calls `_item_commit` (the commit replaced) and requires its message to start with `counters._item_prefixes`; it fails on that mutant and passes on the real navigator | `98748ef2` |
| 3 | minor | `improve` exists only where the parent's tool results hold the `improve-commit` reply; slice B moves the command into the Improve child, whose results may not be in the stream, and then `improve.n` falls to 0 and its commits land in `other` with no null | Not reproducible without a live host: no saved stream holds a sub-agent (29 Claude runs, 15,570 events, no `Task`/`Agent` call; the 35 events with a `parent_tool_use_id` are heartbeats) | **Documented, classification change deferred** (open item 6). SPEC row, README and the `counters` docstring now say `improve` is a lower bound and a comparison across slice B reads `other` beside it. The reviewer's trailer classifier is not assumed: the plan cut those trailers | `6b9a4247`, `58adf273`, this journal |
| 4 | minor | The guard `found != commit_id` in the citation list is dead code | Replaced by `if found]` in a scratch copy: 68 tests OK, the one survivor | **Fixed.** A commit's id is the hash of its message, so a message cannot contain its own id: deleted (no test can reach it) and the mutant pattern updated | `aa989046` |
| 5 | minor | `regrade.figures` repeats `run._stats`; `knowledge_commits` re-ran the classification with counters' private helpers, and its 9% exists only in `baseline.json` | Read | **Fixed** for both duplications: `figures` is `run._stats` (one decimal, so a half byte is kept), `knowledge_commits` reads `counters.history`, which `commits` also counts, so there is one classification. The old and new `regrade.py` write byte-identical files on the same 39 folders (diff in a scratch export; only `harness_head` differs), so `baseline.json` is unchanged. **Disagreed** with putting a knowledge subtotal in the block (section 6); the 9% is comparable only through `regrade.py` or through `script.with_lessons` over `script.n` (open item 7) | `58adf273`, `5d1779d2` |
| 6 | minor | (a) medians truncated, not rounded; (b) the F2 and F6 tallies are in no committed file; (c) "62 KB" for a 68,136-byte file; (d) a commit message puts the mutants and the regrade in the wrong commit | (a) compared every cell of the stage table with `baseline.json` under `round`: 8 of 44 rows differed; (b) recomputed: 1,559 heads, 437 whole, 1,082, 38, 2; 35 other commits, 32 and 3; (c), (d) read | (a) **Fixed**: the 8 cells are corrected and the rule is stated above the table. (b) **Fixed**: `tallies.py` and `tallies.json` (section 4, F2 and F6). (c), (d) **Not rewritten**: commit messages stay as committed and the slips are listed in open item 8 | `5d1779d2`, this journal |

What did not change: `baseline.json` (regrade equality above), the shape of `packets` and `commits` in a run's `metrics.json`, `review.py`,
anything under `skills/`. What is new: `counters.head_or_why` and `counters.history` (public), the `author` of a commit in a history row,
`tallies.py` and `tallies.json`, the `improve` limit in the SPEC row.

One slip in this round's own messages: `58adf273` says "5 mutants are added" and lists four plus an updated pattern (4 were added:
36 to 40).

### Verification record (review round)

Run on 2026-10-10 in the worktree of branch `batch1012h-1bbefb` (base `658ff4e3`), `SHIPLOOP_PROGRESS=off`, machine load average
about 5. Exit codes are the commands' own, captured without a pipe.

| Command | Exit | Note |
|---|---|---|
| `python3 test/shiploop-e2e-commit-counters.test.py` | 0 | 86 tests OK, 14 s (68 at the first round) |
| `python3 test/test-groups.test.py` | 0 | 28 tests OK; no new top-level test file, so the pinned counts (76 ShipLoop suites, 117 in all) are unchanged |
| `bash test/run-all.sh --group quick --changed-from 658ff4e3` | 1 | 32 of 33 suites passed, `shiploop-e2e` and `shiploop-e2e-commit-counters` and `shiploop-run-review` (which reads the SPEC row amended in `6b9a4247`) among them; **`shiploop-status-display` failed**, the same single case as the first round (`test_every_dry_run_packet_carries_the_block_inside_the_kept_head`, scenario `revise`, sequence 20) |
| `python3 test/shiploop-status-display.test.py` here, and on an export of `658ff4e3` | 1, 1 | `8003 not less than 8000` here and `8031 not less than 8000` on the base export (the length depends on the checkout path); `git diff 658ff4e3 HEAD --stat -- skills agents` is empty, so it is not this branch's and not mine to fix (packet heads are the E2E fork's pass) |
| `python3 docs/experiments/commit-baseline-20261010/mutants.py` | 0 | 40 of 40 killed, no survivor, none not applicable |
| `regrade.py` of the parent commit (scratch export) and of this branch, same folders | 0, 0 | byte-identical output except `harness_head`; 38 of the 39 rows equal the committed `baseline.json`'s (the 39th was `not_regraded` there) |
| `python3 docs/experiments/commit-baseline-20261010/tallies.py`, written to a scratch file | 0 | equal to the committed `tallies.json` except `harness_head` |
| `python3 scripts/check-release-boundary.py --base 658ff4e3 --head HEAD` | 0 | `check-release-boundary: OK`, at `2e9df5e2`; run again after the commit that carries this table (see the report of the fix round) |

A timing-sensitive failure was not seen, so no rerun was needed beyond the two `shiploop-status-display` runs above. Not run: the full
hermetic tier (CI runs it on a release commit), any live E2E run, any host CLI or model, any browser or server.

## 11. Task I (2026-10-10): the harness reads lessons and citations through ShipLoop's one reader, and the baseline is regraded with it

Journal of batch 1012 task I. Question: does "a commit carries lessons" mean one thing, in the gate and in the harness (SPEC S-12), and
what does that change in the saved runs' counts? Base `8f3d4cbe`; commits `4d423333` (the replacement, with its tests and docs),
`11d1aba5` (the regraded baseline and `reader_change.py`), `453bbc03` (the suite's measured seconds), `3382477f` (the label tally),
`1d237e59` (the mutation record), `21384c6e` (the LEARNINGS entry), then this journal. Evidence: `docs/experiments/commit-baseline-20261010/` (`baseline.json`, `tallies.json`,
`reader-change.json`, `reader_change.py`, `mutants.py`, `mutants-result.json`). The older sections are kept as written; where a claim in
them is superseded a note says so in place.

### 11.1 What was built

| Part | Where |
|---|---|
| The harness's own reader is gone: `lessons`, `LESSON_LABEL`, `SECTION_END`, `LEARNED_FROM`, `LEARNED`, `KEY_LEARNINGS` and the `knowledge_home` import only they used | `test/shiploop_e2e/counters.py` |
| `with_lessons` = `shiploop_lessons.lessons` finds a non-empty section; `cited` = `shiploop_lessons.citations` has a token that is a commit ID and resolves to a commit in the repository | `counters.commits`, `counters._cited_commit`, `counters.COMMIT_ID` |
| The shape of an ID is the gate's (7 to 64 hexadecimal digits), checked before Git is asked; the harness still resolves with Git and does not use the gate's reachable-from-HEAD rule | `counters.COMMIT_ID`, pinned to `shiploop_git._COMMIT_ID` by `CitationTest.test_the_shape_of_an_id_is_the_gates` |
| `regrade.py` counts the knowledge home's lessons through the shared reader | `regrade.knowledge_commits` |
| Old reader vs shared reader, per commit, on the same runs | `reader_change.py` (`old_reader` loads `counters.py` from Git at `--old-ref`, `compare`, `records`, `tally`), `reader-change.json` |
| Mutation rows at the import seam | `mutants.py` (43 rows; the five rows that targeted deleted code are replaced by eight at the seam) |
| README and SPEC describe the counters by the shared reader | `test/shiploop_e2e/README.md` ("Packet and commit counters"), `SPEC.md` (the `commits` row of "How the harness checks the clauses") |

No metrics key was added or changed; `result.json`, the baseline row, `review.py` and everything under `skills/` and `agents/` are
untouched, so there is no change note.

### 11.2 Fail-first record

| Step | Result |
|---|---|
| The new reader tests against the old reader (`counters.py` unchanged) | 94 tests: 48 failures, 1 error, each for the intended reason. Red: the heading form, a bold or bulleted label, `Lessons:`, the singular `Key learning:`, lower-case labels, a label alone then a blank line then the body, `Root-cause:` and `Follow-up:` lesson lines, and 6 of the 15 shapes the gate's own fixtures pin (`test/fixtures/commit-contract`); a backtick, bracket, quote, bullet, bold or lower-case `Learned-from` line; the seam tests; and the two reverse cases (punctuation-only `Key learnings: -`, and a heading right after an empty `Key learnings:`, which the old reader counted and the gate does not). My first two runs were red for a wrong reason (an empty event stream makes the block null; the knowledge subject classifies a commit as `script`; an empty message cannot be committed) and were fixed in the tests before this record. |
| Guards (pass before and after, by design) | `Key learnings: none`; the trailer-only heading (the old reader never read headings, so it was empty before too); the one-paragraph message; `Learned-from: <id>: text` and an upper-case id (the old regex already read both: **the brief's "a trailing colon" is not a difference**); the not-an-ID cases |
| The import without the ID-shape check | 4 failing subtests of `test_a_token_that_is_not_a_commit_id_cites_nothing_even_when_git_would_resolve_it`: a branch named `notes`, `HEAD`, `HEAD~1` and a six-digit prefix are counted as citations. The shared reader returns any token and Git resolves names, where the old regex only ever offered hexadecimal text |
| With the change | 94 tests OK, then 99 with `ReaderChangeTest` (written before `reader_change.py`: red on `setUpClass`; 5 one-line breaks of the script, 3 red at once, 1 survivor got a test, 1 was a redundant guard and was removed; the label tally later: 2 breaks red, 1 redundant filter removed) |
| Tests deleted | `LessonsSectionTest` (three tests of the old reader, including `learned: lower case` being no label, which the shared reader reads) and the `counters.LEARNED` pin. Replaced by `LessonsReaderTest` (8 tests, each commits a message in a real repository and reads the count the block reports, including one over every fixture the gate is pinned with) and 4 `CitationTest` tests |

### 11.3 Before and after, per class and host

Three readings of the same counts. **Old, committed**: `baseline.json` as task H wrote it, 38 runs (the 39th was live). **Old, 39 runs**:
the old reader on the runs folder as it is now (`pc1i-checkers-sonnet`, finished since, is the 39th; `regrade.py` before the change,
kept in the scratchpad). **Shared**: the shared reader on the same 39 runs (the committed `baseline.json` and `reader-change.json`).
`with_lessons` is "commits with lessons / commits"; `cited` is 0 in every cell of the three readings.

| Class / host | Old, committed (38 runs) | Old, 39 runs | Shared, 39 runs | Why the cell is what it is |
|---|---|---|---|---|
| improve / claude | 38 / 81 | 42 / 85 | **44 / 85** | +4 / +4 from the 39th run (all four Improve commits of `pc1i-checkers-sonnet` carry `Key learnings:`); **+2 from the reader**: the two release-plan Improve commits of `20261003/seat-reservations` write `Key learning:` (singular) |
| improve / codex | 13 / 34 | 13 / 34 | 13 / 34 | none; 5 of these commits are counted by both readers with a different text (below) |
| improve / grok | 17 / 17 | 17 / 17 | 17 / 17 | none |
| improve / mixed host | 0 / 0 | 0 / 0 | 0 / 0 | no Improve commit |
| script / claude | 28 / 276 | 29 / 286 | 29 / 286 | +1 / +10 from the 39th run (its release-verify knowledge commit, `Learned`); reader: none |
| script / codex | 0 / 38 | 0 / 38 | 0 / 38 | none |
| script / grok | 1 / 78 | 1 / 78 | 1 / 78 | none; the one counted commit's text differs (below) |
| script / mixed host | 1 / 20 | 1 / 20 | 1 / 20 | none |
| other / claude | 1 / 22 | 1 / 22 | **2 / 22** | **+1 from the reader**: the model's own commit "Add system tests ST-1 and ST-2 ..." of `20261008/r2-battleship-sonnet` writes `Key learning:` (singular) before its `Co-Authored-By` trailer |
| other / codex | 0 / 2 | 0 / 2 | 0 / 2 | none |
| other / grok | 0 / 1 | 0 / 1 | 0 / 1 | none |
| other / mixed host | 0 / 10 | 0 / 10 | 0 / 10 | none |
| all, improve | 68 / 132 | 72 / 136 | 74 / 136 | |
| all, script | 30 / 412 | 31 / 422 | 31 / 422 | |
| all, other | 1 / 35 | 1 / 35 | 2 / 35 | |

**Does any previously counted commit stop counting? No.** `lost` is 0 in every class and host of the 593 commits; `gained` is 3, and
`reader-change.json` lists them (`changed`): the three above, each with the label `Key learning` and no other. So the whole effect of the
reader is one label, the singular of the Improve card's `Key learnings`, which the old reader did not know and ShipLoop's grammar does.
The messages I opened use these forms: the two `seat-reservations` commits are a subject, then a paragraph that starts `Key learning:`
and runs six lines, then a paragraph `Evidence: ... Related commits: <ids>.` (the ids are prose, not a `Learned-from` line); the
`r2-battleship-sonnet` commit is a subject, one `Key learning:` paragraph of three lines, a blank line and the trailer.

Which labels the 107 counted commits use (`reader-change.json`, `all.<class>.labels`): `Key learnings` 73 (72 Improve, 1 model),
`Learned` 31 (all knowledge-home release-verify commits, `script`), `Key learning` 3. Nothing else: no heading, no bold, no bullet, no
`Lessons:`, no lower-case label in any saved run (status: firm for these 593 commits). Those forms are guarded by the tests, not by
data, and the first live pair after the commit contract is the first data on them.

Six commits are counted by both readers with a different text (`text_differs`; the count is the same): 5 Codex Improve commits whose
old text ran on through a bare `Remaining work` label and its lines (the old reader ended a section only at a `Label:` line; the shared
reader ends a colon or bare body at a blank line), and 1 Grok knowledge commit whose old text ran past a blank line. The harness never
judges the text.

### 11.4 Citations and `none`

- `cited` and `cited_earlier_run` stay measured zeros: 0 of 593 commits hold a line that matches `learned.?from` in any case
  (`reader-change.json`, `learned_from_any_form`). The reader's tolerance (a backtick, quote, bracket, `commit <id>`, a trailing
  colon or comma, a bullet or bold label, any case) cannot move a number yet; the tests cover it. The first run after the commit
  contract is the first that can move `cited`.
- **Counted lessons that are exactly `none`** (case-insensitive, punctuation stripped; descriptive, in this journal only, no metrics
  key): **0 of 107** (`exactly_none` is 0 in every class). One counted lesson starts with the word, "none new beyond commit ..." (the
  `20261010/checkers-1` Improve commit that `test/fixtures/commit-contract/none-counts.md` is modelled on), which is more than `none`.
  The gate counts `Key learnings: none` (a measured presence, not a judged lesson), so after the commit contract this figure is the
  first to show how often a model answers with it.

### 11.5 Decisions, deviations, corrections to the brief

- **An ID-shape check was added** (`counters.COMMIT_ID`), which the brief did not mention: with the tolerant tokens of the shared reader
  a branch, `HEAD` or `HEAD~1` resolves in Git and would be counted as a citation the gate refuses (red record above). The harness still
  resolves with Git and does not apply the gate's reachable-from-HEAD rule, as the brief said.
- **The brief's "a trailing colon" is not a difference** between the readers (11.2, guards); a backtick, a quote, a bracket, a leading
  `commit`, a bullet or bold label and a lower-case label are.
- **The run set changed under the reader.** The committed baseline listed `20261010/pc1i-checkers-sonnet` as live; it has finished, so
  `baseline.json` now holds 39 regraded runs and `tallies.json`, which is built from the baseline's run list, was regenerated with it
  (1,597 heads: 438 whole, 1,116 end before the closing line, 41 inside the narrative, 2 cut by column; 35 `other` commits: 32 by the
  user's Git identity, 3 confirmed by Git's own line). Section 4 F2 and F6, the section 5 tables and the per-stage table keep their 38-run
  figures as written; the 39-run totals are in `baseline.json` and `tallies.json` (Claude: 29 runs, 1,242 packets, 126 measured heads,
  file bytes median 37,225.5, head bytes median 4,885.5). To keep the reader's effect separate from that, `reader_change.py` counts every
  commit with both readers on the same 39 runs, and the middle column of 11.3 is the old reader on them.
- `regrade.py` ran twice, byte-identical (68,330 bytes), as did `reader_change.py`; `baseline.json`'s `harness_head` is `4d423333`, the
  commit of the counters code.
- `counters.history` (the classification) and the shape of the metrics keys are unchanged; `tallies.py` is unchanged.
- The suite is 24.1 s, not 15 (the recorded value in `test/suite_catalog.py` is updated, `453bbc03`): the new tests commit one message at a
  time to a real repository.

### 11.6 Superseded in the sections above

- Section 2, "Lessons reader" (no ShipLoop code reads a commit message's sections, `counters.lessons` is the one reader): superseded
  2026-10-10. `shiploop_lessons` is that reader and the harness imports it.
- Section 6, "`counters.lessons` is a small reader of its own": superseded 2026-10-10, same reason.
- Section 7, open item 2 ("Slice B imports the commit-section reader"): done, `4d423333`.
- Section 4, F5, and the section 5 per-host tables: the lessons shares are counted with the narrow reader on 38 runs; the 39-run figures
  with the shared reader are in 11.3 (Improve commits with lessons: 74 of 136, Claude 44 of 85).
- Section 6, "the knowledge-commit share (9%) is a subtotal of `script`": unchanged by the reader (29 of 221 knowledge commits in Claude
  runs, 1 of 67 in Grok, 0 of 33 in Codex, 1 of 17 in the mixed-host run).

### 11.7 Open and deferred

1. **`Learned` with no text, then the knowledge home's next section.** `shiploop_lessons` knows the lesson labels, the Improve card's six,
   `Learned-from`, `Remote change` and four trailers, but not the knowledge home's `Key considerations` and `Open for the next run`, so
   `Learned` + a blank line + `Key considerations` reads the section name as the lesson (the old reader ended there). ShipLoop's own
   knowledge commit cannot write it (it writes a section only when it has text), and no saved commit differs, so nothing here is wrong;
   it is an engine-side choice (add the two names to the known labels, or leave it). Not changed: nothing under `skills/` is mine.
2. The reader is case-insensitive, so a line that starts `learned: ...` in prose counts as a lessons section. No saved commit does.
3. The `none` figure above is the baseline for "a model says `none`"; a later run that reports many is a finding about the contract, not a
   fault of the count.
4. `baseline.json` and `tallies.json` are the 2026-10-10 baseline of 39 runs; re-run `regrade.py`, `tallies.py` and `reader_change.py`
   after the next batch of runs.
5. `CitationTest.test_the_shape_of_an_id_is_the_gates` reads `shiploop_git._COMMIT_ID`, a private name, so a rename in the gate turns the
   test red and says where to look; the alternative (a public name) is a `skills/` change.

### 11.8 Status of the findings

| Finding | Status |
|---|---|
| The reader change moves 3 of 593 commits, all gained, none lost; the one difference is the singular `Key learning:` | Firm (reader-change.json, regenerated twice byte-identical; commit messages opened) |
| No saved commit uses a heading, bold, bulleted, `Lessons:` or lower-case lesson form; `Learned-from` appears in none | Firm for the 593 commits |
| A tolerant citation token must be checked for the shape of an ID before Git is asked | Firm (4 failing subtests without it) |
| 0 of 107 counted lessons are exactly `none` | Firm as a count; interim as a baseline (the contract has not run live) |
| `Learned` then `Key considerations` is read as a lesson by the shared reader | Firm for the reader (shown); no saved data affected; the choice is the engine's |

### 11.9 Verification record

Run on 2026-10-10 in the worktree of branch `batch1012i-1bbefb` (base `8f3d4cbe`), `SHIPLOOP_PROGRESS=off`, machine load average about
6 (sibling worktrees share it). Exit codes are the commands' own, captured without a pipe.

| Command | Exit | Note |
|---|---|---|
| `python3 test/shiploop-e2e-commit-counters.test.py` | 0 | 99 tests OK (task H's 86, minus 4 that pinned the old reader, plus 8 `LessonsReaderTest`, 4 `CitationTest` and 5 `ReaderChangeTest`); 24.1 s the faster of two serial runs at load average about 6, 30.8 s in the last run at about 11 |
| `python3 test/test-groups.test.py` | 0 | 28 tests OK; no new top-level test file, so the pinned counts (76 ShipLoop suites, 117 in all) are unchanged |
| `bash test/run-all.sh --group quick --changed-from 8f3d4cbe` (at `21384c6e`) | 1 | 26 suites: 25 OK, **`shiploop-status-display` failed, the only red suite**: `test_every_dry_run_packet_carries_the_block_inside_the_kept_head` (delegation `ask-agent`, scenario `revise`, sequence 20), `8003 not less than 8000`, the same single case task H recorded (its length depends on the checkout path, 8031 on another). `git diff 8f3d4cbe HEAD --stat -- skills agents` is empty, so `skills/` is the base's and the failure is not this branch's. `shiploop-e2e`, `shiploop-e2e-commit-counters`, `shiploop-run-review` (which reads the SPEC row edited here) and `release-preflight` (which reads `LEARNINGS.md`) are among the 25 |
| the same tier at `453bbc03`, before the label tally, the mutation record, the LEARNINGS entry and this journal | 1 | 25 suites: 24 OK and the same single failure (`release-preflight` was not in that selection: `LEARNINGS.md` had not changed yet). A run of the tier at `21384c6e` started as a detached subshell was gone when its shell ended and left no result; it was run again as a task of its own (the row above) |
| `python3 docs/experiments/commit-baseline-20261010/mutants.py` | 0 | 43 of 43 killed, no survivor, none not applicable; `counters.py`, `metrics.py` and `run.py` clean in Git after |
| `python3 docs/experiments/commit-baseline-20261010/regrade.py --runs /Users/dadleet/e2e-runs`, twice | 0, 0 | byte-identical (68,330 bytes); 39 runs, 0 not regraded; now the committed `baseline.json` |
| `python3 docs/experiments/commit-baseline-20261010/reader_change.py`, twice (after each change of the script) | 0, 0 | byte-identical; 39 runs, 593 commits, 3 counted differently |
| `python3 docs/experiments/commit-baseline-20261010/tallies.py` | 0 | 39 runs |
| `python3 scripts/check-release-boundary.py --base 8f3d4cbe --head HEAD` | 0 | `check-release-boundary: OK` (at `21384c6e`, and again after this journal's commit) |

A timing-sensitive failure was not seen, so no rerun was needed beyond the quick tier above. Not run: the full hermetic tier (CI runs it on
a release commit), any live E2E run, any host CLI or model, any browser or server. Ollama and OrbStack were left stopped.

## 12. Drift found by the first release-commit CI (2026-10-10): ShipLoop reworded the work item's announcement

**Status: firm.** Release 1.27.0 (`6f86c8cf`) reworded the line ShipLoop prints when it commits a work item, from "ShipLoop committed W1's declared changes as <sha>" to "ShipLoop committed W1's changes (its declared paths and documentation) as <sha>" (`shiploop_navigator._item_commit`, because an item's documentation now rides in its commit). The full tier on that commit failed `shiploop-e2e-commit-counters`: `ShipLoopOwnedSubjectsTest` reads ShipLoop's source and pins the wording `counters.py` matches, so the test did its job.

What it showed beyond the one failing assertion:
- `counters.ITEM_COMMITTED` no longer matched a new run's announcement, so a work item's commit would have been classified by its subject alone (still `script`, but only while the model's pipe leaves the subject legible).
- `metrics.KEPT_REPLY`, the filter that decides which replies the counters see at all, held a second copy of the old wording, so a new-wording reply would have been dropped before `counters.py` ever read it. That is a second copy of one concern (S-12).

Fix (this commit): `ITEM_COMMITTED` reads both wordings, because saved runs hold the old one and new runs the new; `KEPT_REPLY` keeps only the coarse prefix `ShipLoop committed \S+'s ` and leaves the precise match to `counters.py`; the source pin names the new text; a test reads both wordings; the kept-reply test lists both.

Why the quick tier on the push did not catch it: the quick tier ran before the fork's rewording was on main (the rewording and the counters landed from two branches, merged by the fork). The release commit's full tier is the first run that sees both. **Learning:** a harness pattern that matches ShipLoop's printed wording needs a test that reads the wording from ShipLoop's source (this one did), and the pattern must live in one place.
