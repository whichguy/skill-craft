# ShipLoop efficiency work: journal (2026-10-16 to 2026-10-17)

Consumer: the owner and the next session that merges the remaining branches. Read it before touching `feat/shiploop-eff-packets-6afcbc`, `-loop-` or `-stop-`.
The plan these branches implement is `docs/shiploop-efficiency-plan-2026-10-16.md` (Execute: ask). The evidence is the live Salesforce chess run
(`docs/e2e-salesforce-chess-journal.md` F9) and the studies under `docs/experiments/shiploop-audit-20261016/` and `docs/experiments/shiploop-loop-block-20261016/`.

## Why: what the measurements said (status: interim, one Grok 4.7 medium run, installed 2.4.0 renderer)

- Of 5.09 MB that entered the model's context, 75% was file reads and 9.6% printed packet heads; the 16 context breaks (12 compactions, 4 restarts) cost 41%.
  The entry card (`skills/shiploop/SKILL.md`, 80 KB) was the first read after each of the last 9 compactions. Absolute paths are 11.8% of producer-packet bytes.
- The model never opened `reference.md`, `context-index.md` or `status.md` (0 of 1,219 tool calls), so a conditional "open this if unsure" pointer is not followed;
  an imperative command with the value is (`next` after a break, 13 of 14 breaks that carried a resume prompt; that rate is largely the harness's prompt).
- The stop-rule study (on the `-stop-` branch, `docs/experiments/improve-stop-rule-20261016/`) rests on the five planning stages only; it says not to extend its result to implement-step code reviews.

## Branches (all based on `398466a3`, the packet-essentials branch; none pushed except what is marked released)

| Branch | Commits | What | State |
|---|---|---|---|
| `feat/shiploop-eff-cred-6afcbc` | `f1f38850`, `d4d08351` | No credential-pattern refusal anywhere; no silent credential skip in `commit_paths` | **Released** in 2.5.0 / 1.5.0 (`da9e2e75`); branch and worktree removed |
| `feat/shiploop-eff-hook-6afcbc` | `996a378c` | Claude PostToolUse `Skill` hook writes `skill-calls.jsonl`; the Improve stage's `complete` requires a recorded improve call | **Released**, with fixes `5d028aee` and `d56904e2`; removed |
| `feat/shiploop-eff-stop-6afcbc` | `60018152`, `3b9ca9c9` | Improve stops on one trivial pass that leaves the content tree unchanged (SPEC S-10 carve-out) | **Not releasable**: 3 P1 findings, one an owner call (below) |
| `feat/shiploop-eff-loop-6afcbc` | `0d462ca4` | Every packet's Until Loop block says RUN the skill, shows the argument between BEGIN/END markers, the literal start command, the result line | **Not releasable alone**: pushes the step-plan head over the host cut with the packets branch |
| `feat/shiploop-eff-packets-6afcbc` | `f3f6a6bc`, `0eeb68e2`, `c8d49b01` | Owner rule and master-index pointer under the first line; new-file diff and followed-entry pointers; prose paths as `RUN`/`HOME`/`WORKTREE`/guide symbols | **Not releasable alone**: head over the cut at a normal install, decisions open |

Reviews: each branch had one adversarial reviewer (read-only, with evidence). For the two released branches a second, independent reviewer ran on the merged tree before release.

## Released: 2.5.0 / 1.5.0 (2026-10-17, origin/main `da9e2e75`, CI green on all jobs)

Release path: the two branches were merged (`--no-ff`) into a worktree off main; the only conflict was the suite-count assertion in `test/test-groups.test.py` (87 ShipLoop
suites, 140 total with the new hook suite). The first release attempt was refused because `No-E2E-Round:` sat in its own paragraph (git reads trailers only in the final one);
the trailer was moved next to `Co-Authored-By:`. `origin/main` moved before the push (the E2E-audit session landed `a7c1fdb2`), so the unpushed release commit was dropped,
`origin/main` merged in and `release.py` re-run. Quick tier `--changed-from origin/main` passed (exit 0), plus the E2E-harness suites on the merged tree. All three hosts were
refreshed to 2.5.0. The canonical checkout's fast-forward was blocked by 45 untracked files the audit session had since committed; they were byte-identical to main, so they were
copied to `/Users/dadleet/src-archive/2026-10-16/skill-craft-untracked-duplicates/`, removed, and main fast-forwarded. `p_step.txt` (untracked, not in main) was left.

### Findings on the released work and what was done

Credential removal (review by the branch's reviewer, then by the release reviewer):

| Finding | Status |
|---|---|
| Change note said the status views still redact; only the progress page and lint output do (release review, P2) | **Fixed** in `320a526e`: the note says the terminal status, narrative and run files print what was submitted |
| `commit_paths` now commits `.env`-like files; the remaining protection is the review-return choice and a duty (release review, P2) | Owner rule; stated in the change note |
| SPEC S-9 listed a "credential screen" (P3) | **Fixed** in `320a526e` |
| CR-1: no acceptance test for the Improve-opening path (a reviewed stage whose summary holds `Auth: sf login (alias de)` must start its Improve child) | **Open** |
| CR-4: the retired phrase is not guarded in the `shiploop reference` text or the SKILL.md/references edits | **Open** |
| CR-5: the commit message's byte savings do not reproduce (32 per inner stage, 65 for step-plan, 289 over the 12 packets, not 345) | **Open** (record here instead of rewriting the commit) |
| CR-6: a run-review test comment says "the screen of this checkout still refuses it"; `docs/shiploop-artifact-flow-2026-10-11.md` line 72 says "credential screen" | **Open** (the dated doc is history) |
| CR-2/CR-3: the progress page now withholds whole documents/summaries that contain credential-like text that used to be refused; the new progress-data test passes on the old source (it guards the display redaction only) | **Open**, known |

Skill-call hook:

| Finding | Status |
|---|---|
| P1 (release review): Codex/Cursor/OpenCode started from a bound Claude shell inherit `CLAUDECODE` and are gated with no Skill tool to satisfy it | **Fixed** in `5d028aee` for Codex and Cursor (`NESTED_NON_CLAUDE`); an OpenCode marker is unknown, so OpenCode from a bound Claude shell is **still gated** |
| The refusal's named command dropped `--final-result`, `--notes`, `--no-commit`; closed or non-text stdin made the hook exit 1 | **Fixed** in `5d028aee` |
| HK-3: `read_records` split on U+2028/U+0085 and lost a made call; HK-4: `evilplugin:improve` counted; HK-1: no cross-session isolation test; catalog comment said 25 tests | **Fixed** in `d56904e2` (suite is 30 tests) |
| `skill_hook` is judged from the configuration on disk, not from what the live session registered; calls before binding, a subagent with its own session id, and a user-typed `/improve` leave no record; `start.json` rewritten after the call voids it; the 2,000-character cut | Known limits (journal `docs/shiploop-skill-call-hook-journal-2026-10-16.md`), not changed |
| HK-2 (quote tolerance redundant, prefer deletion), HK-5 (switches are env vars), HK-7 (Grok shares the Claude `hooks.json`), HK-8 (two tolerances beyond the brief) | Accepted or documented; not changed |

Live round still owed: whether a Claude model refused by the gate follows the named exit, and the invocation rate against 1 of 4.

## Not released: findings that block each branch

### Stop rule (`-stop-`)
- **F1 (P1, owner call).** The one-pass rule is applied to every Improve child, including implement-step code reviews, which the study said not to extend to (only the five
  planning stages were measured). The live run has a case where it would have cut a code defect. Options: the unchanged gate for the five planning stages only, and two
  unchanged passes for step and last-item stages; or the owner accepts the wider scope.
- **F2 (P1).** `test/installed-skill-invocation.test.py` (two tests) is red on the branch and green on its base: the fixtures start a gate-2 contract in a directory that is not Git.
  The quick tier with `--changed-from` does not select it; a changed-from mapping for `skills/improve/runtime/**` is missing.
- **F3 (P1).** A non-Git in-place run can never start its first Improve review (the runtime refuses an unmeasurable gate; the error is swallowed; the restart route fails the same way).
- F4 (P2): a non-ignored file a check rewrites each pass keeps the loop open with no cap and no hint which file. F5 (P2): Backchain converge now stops on the label alone when the plan
  is outside the worktree. F6 to F9 (P3): untested branches, the kept field names (the published until-loop plugin refuses unknown fields; upstream first), the receipt takes the last
  review file on disk, a contradictory exit sentence in `skills/improve/SKILL.md`.
- Owner gates the worker raised: the gate name `required_trivial_reviews` stays (2 now means "trivial and unchanged"); Git is required for any gate-2 start; old runtime state files
  are refused; its change notes mix `minor` and `patch` for one skill, which `release.py` refuses until aligned.

### Loop block (`-loop-`) and packets (`-packets-`), together
- Merged together (clean text merge) they are red: `shiploop-packet-recut` 2 failures (inline step-plan printed head 20,504 against the 20,000 host cut; ask-agent 22,186 against
  22,000) and `shiploop-packet-completeness` 68 failures (the symbols guard flags the loop block's literal `Work:` lines). The plan's Step 1.0 owns the reconciliation.
- Loop block: +4,256 characters over the 7 argument-bearing stages at a 79-character run dir (+28%, about 470 characters plus twice the run-dir length per block); inline step-plan
  head 19,974 of 20,000. LP-1 (P2): at a live-length run dir the cut removes the new start command and Result line; suggested fix: put the block before Full packet, Progress view,
  Recovery and Pause in `packet_head`. LP-3 (P3): after the loop starts the packet file still hands over a copy-ready start command.
- Packets: the callback moves from line 2 to line 4 (owner decision); PK-1 (P2) the head test uses a bare `shiploop` so it cannot see that a plugin-cache install (95-character CLI path)
  crosses the cut; PK-2 two command cards still say the callback is on the line after the header; PK-3 `symbolic()` has no left boundary; PK-4 the CLI locator can print as a symbol;
  PK-5 an old-format `context-index.md` is not regenerated; PK-6 two surviving mutants; PK-7 a domain word in a test docstring.
- Per-step measurements (offline, node-fix-bug): PK1 +12,643 characters over 48 packets, PK3 -12,101, net +542 (+0.1%); whole inline renders -2.9%; printed heads grow.

## Decisions waiting for the owner
1. Stop-rule scope (F1): planning stages only, or all Improve children.
2. Callback placement (line 4 after the owner lines, or after the callback line).
3. The step-plan head over the host cut: trim about 500 characters, reorder the head (put the block before the lines a cut can take), or raise nothing (the plan's D-27).
4. Whether OpenCode needs the same inherited-marker exemption (its environment marker is unknown here).
5. Whether to run the next live ShipLoop round on the released 2.5.0 first (it measures the hook and the credential removal) before merging the head changes.

## Process learnings
- Two tests in a quick-tier selection can be missed by `--changed-from` when a change reaches a suite only through a runtime path (the stop branch's F2); add the mapping with the change.
- A trailer paragraph, a moved `origin/main` and an untracked-file duplicate each stopped a release step; each was detected by the tool, not by the plan. The guarded push
  (`scripts/release-push.py` with the expected head, tree and base) re-checks the remote base before it pushes; here a `git fetch` showed the move first.
- A reviewer found a real deadlock (the hook gating a host that has no Skill tool) that the worker's 26 tests missed: the fixture environment had been made to look like "Claude only".
  Probe the neighbouring hosts' inherited environment whenever a gate is keyed on an environment variable.

## Unit rows, wave 1 (2026-10-17; folded from docs/experiments/shiploop-eff-journal-rows/)

### U1

# Journal row: U1 base and tranche-1 landing (2026-10-17)

**Consumer.** The integrator who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md`, and every later unit that needs the
landed base (U2 merges the stop branch onto it; U7 tightens the head table; U5 reads the evidence copy). **Status.** firm for the counts, the
merge and the green suites; interim for the head table (one offline case, `node-fix-bug`, no model). **Snapshot.** INT
`feat/shiploop-eff-int-c5f79b`, code at `119dbcca` (reconciliation), based on main `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0).
**Fixture.** offline `node-fix-bug` (`test/shiploop_e2e/step_cases.json`), routes inline and ask-agent. **Run-dir length.** 83 (reference) and 163.
**Unit.** U1. **Evidence.** `docs/experiments/shiploop-eff-evidence-20261017/` (README there maps every `SP/` input; `u1/` holds this unit's numbers).

## What landed on INT (all local; nothing pushed, released or tagged)

| Step | Commit | Note |
|---|---|---|
| INT created off main | `da9e2e75` | `feat/shiploop-eff-int-c5f79b`, worktree `.claude/worktrees/shiploop-eff-int-c5f79b` |
| docs branch merged (`--no-ff`) | `6e8ec6d2` (90fa2ca0) | run-2 journal F9, rev 4 plan, branch journal, 16 `LEARNINGS.md` lines |
| run-2 baseline row, own commit | `e6f9f622` | the one row left uncommitted in `sf-chess-fb04a2`, copied unchanged (its `output` field still names the scratchpad folder, now also archived) |
| packets branch merged | `30b178be` (f3f6a6bc, 0eeb68e2, c8d49b01) | textual merge clean |
| loop branch merged | `7f2dfc80` (0d462ca4) | textual merge clean |
| reconciliation | `119dbcca` | below |
| evidence copy and this row | the commit after `119dbcca` | 2.4 MB on disk (bound 3 MB) |

The run-2 folder `SP/sfchess/live2` was copied with `rsync -a` to `/Users/dadleet/src-archive/2026-10-17/shiploop-live2-run2/`
(`du -sk` 173,172 source, 173,128 copy: 0.03% apart; `diff -rq` empty).

## The unreconciled merge (measured on INT before the reconciliation)

| Suite | Failures | Cause |
|---|---|---|
| `shiploop-packet-recut` | 2 | inline step-plan printed head 20,392 > 20,000 (`PrintedHeadTests.HOST_CUT`); ask-agent step-plan > 22,000 |
| `shiploop-packet-completeness` | 68 | the symbols guard read the loop block's argument by its old four-space indent; the new `Work:` line (BEGIN/END markers, no indent) held a literal RUN path in 68 packets |
| `shiploop-step-packets` | 1 | `test_the_printed_head_fits_the_host_output_limit`: 20,368 > 20,000 |
| `shiploop-rehydration` | 1 | `MasterIndexTests`: `skill-calls.jsonl` missing from the master index map |

These are the plan's counts (2, 68, 1, 1) reproduced on a fresh merge. Raw outputs: `u1/unreconciled-summary.txt` in the evidence copy.

## The reconciliation (no obligation lowered)

| Change | Why | Fail-first |
|---|---|---|
| `prose_lines` (packet-completeness) exempts the lines from `loops.ARGUMENT_BEGIN` to `ARGUMENT_END` and the loop's start command; every other literal path still fails | the argument and start command are read verbatim by hooks and the runtime | `ProseLineGuardTests` (2 tests): the old `prose_lines` fails the first (`u1/failfirst-prose-guard.txt`) |
| `MAP_ROWS` row for `skill-calls.jsonl` (`shiploop_context_index`) | every Claude Code run has the file since the Skill-call hook (996a378c) | the rehydration test itself (red before, green after) |
| head tests: constant 20,000 replaced by `test/shiploop_e2e/head_table.json` (per route, per stage, head and whole) read through `test/shiploop_head_budget.py` | at a plugin-cache install the inline step-plan head is 20,638 and the ask-agent one 22,320: a constant either fails or hides growth; a head not in `over_the_cut` may not cross 20,000 | lowering any value by 1 fails the recut and step-packets tests; emptying `over_the_cut.inline` fails the cut check (`u1/failfirst-head-table.txt`) |
| docs and the improve-schedule helper name the callback by its label (`Callback for this stage`; an Improve child: `Next command (` or `2. When the improve skill has completed, run:`) | the owner rule and pointer already sit between the header and the callback and U7/U8 add more lines | `git grep -n -E "line after (its\|the) (packet \|navigator )?header" -- skills/shiploop test` finds nothing (it found `commands/shiploop-next.md`; `shiploop-complete.md` wraps the phrase across two lines, found by hand) |

The hard test (loop start, callback, Keepalive marker all end before character 19,500 at 83 with the CLI path padded) is U7's: it fails on this tree
until the print is reordered (the loop start command ends at 19,924 of 20,484 raw per the plan; the Grok view keeps the first and last ~10,000, `plan/ADDENDUM-cut.md`).

**Learning.** A head over `PRINT_LIMIT` drops its quoted knowledge (about 400 characters, `implement` and `test`), so a head's length depends on the
machine's path lengths twice: by the paths themselves and by this switch. A ceiling keyed to a raw length is flaky between a laptop and CI. The helper
pins the temp directory so the run directory is 83 characters (when the system temp directory is at most 47 characters; macOS: 48, no pad needed) and
rewrites the skill root (to 63) and the bare `shiploop` (to 96 characters) by arithmetic. Verified: the table is identical at skill roots of 19 and 125
characters with a 19-character temp dir; under an unpinnable 235-character temp dir the values are lower (the ceiling still holds) and the existing
Improve packet ceiling (3,000, raw) fails by 150 to 320 characters, a path dependence that was there before (`IMPROVE_CEILING` in `shiploop-packet-recut`).

## Head table: printed head and whole text per stage, reference install (root 63, CLI 96)

The first four columns are the table's values (`head_table.json` carries 83). The last two are `fv_heads.py` on the INT tree (raw: bare CLI, root path 72 characters,
so each is below the reference by about 260 for a head that carries the CLI three times); at 163 `fv_heads.py` pads the temp dir to 128 characters.
"whole" is the full packet (what the file holds); "head" is what a packet over `PRINT_LIMIT` (16,000) prints.

**inline**

| stage | 83: head | 83: whole | 163: head | 163: whole | `fv_heads.py` at 83: whole / printed | at 163: whole / printed |
|---|---|---|---|---|---|---|
| step-plan | 20,638 | 24,448 | 22,078 | 25,968 | 24,044 / 20,392 | 25,564 / 21,832 |
| test-spec | 12,268 | 14,419 | 13,628 | 15,779 | 14,085 / 14,085 | 15,445 / 15,445 |
| validate-existing | 11,891 | 14,860 | 13,251 | 16,220 | 14,526 / 14,526 | 15,886 / 15,886 |
| implement | 15,436 | 18,057 | 16,000 | 19,017 | 17,714 / 15,181 | 18,674 / 15,745 |
| test | 15,798 | 20,005 | 16,919 | 21,525 | 19,680 / 15,561 | 21,200 / 16,682 |
| document | 11,400 | 13,710 | 12,840 | 15,150 | 13,376 / 13,376 | 14,816 / 14,816 |
| verify | 15,973 | 20,203 | 17,333 | 21,563 | 19,869 / 15,727 | 21,229 / 17,087 |
| carry-forward | 16,877 | 21,799 | 18,317 | 23,319 | 21,395 / 16,631 | 22,915 / 18,071 |

**ask-agent**

| stage | 83: head | 83: whole | 163: head | 163: whole | `fv_heads.py` at 83: whole / printed | at 163: whole / printed |
|---|---|---|---|---|---|---|
| step-plan | 22,320 | 27,776 | 23,760 | 29,296 | 27,372 / 22,074 | 28,892 / 23,514 |
| test-spec | 12,268 | 15,987 | 13,628 | 17,347 | 15,653 / 15,653 | 17,013 / 13,382 |
| validate-existing | 11,891 | 16,428 | 13,251 | 17,788 | 16,094 / 11,645 | 17,454 / 13,005 |
| implement | 16,550 | 21,213 | 17,510 | 22,173 | 20,870 / 16,295 | 21,830 / 17,255 |
| test | 15,798 | 21,573 | 16,919 | 23,093 | 21,248 / 15,561 | 22,768 / 16,682 |
| document | 11,400 | 15,278 | 12,840 | 16,718 | 14,944 / 14,944 | 16,384 / 12,594 |
| verify | 16,172 | 21,970 | 17,532 | 23,330 | 21,636 / 15,926 | 22,996 / 17,286 |
| carry-forward | 18,080 | 24,570 | 19,520 | 26,090 | 24,166 / 17,834 | 25,686 / 19,274 |

Reading: at 83, inline `step-plan` (20,638) and ask-agent `step-plan` (22,320) are the only heads above 20,000 (`over_the_cut`). At 163 inline `step-plan` is 22,078,
ask-agent `step-plan` 23,760 and ask-agent `carry-forward` 19,520 (within 480 of the cut; the table value at 83 is 18,080). Head-to-whole flip, as the plan expected:
`validate-existing` inline at 163 is a head of 11,756 on main and prints whole (15,886 raw) on this tree, because its whole text fell under `PRINT_LIMIT`; `test-spec` (15,445 raw at 163,
inline) and `document` (14,816) sit under the same cliff, 555 and 1,184 characters below it.

## Exit items

| # | Item | Result |
|---|---|---|
| 1 | `git merge-base --is-ancestor <sha> HEAD` for da9e2e75, 90fa2ca0, c8d49b01, 0d462ca4 | all four exit 0 |
| 2 | every suite of G-SUITES exits 0, the four red ones included; the unreconciled counts are journaled | 26 of 26 exit 0 (below); counts above |
| 3 | bundle verifies; live2 copy within 1%; `git worktree list` shows neither `packet-order-255e57` nor `m16/m`; evidence directory committed and under 3,072 KB | live2: 173,128 vs 173,172 KB; both worktrees removed after `git status --porcelain` was empty and `git merge-base --is-ancestor <head> INT` exited 0 (the branch ref `feat/packet-essentials-first-255e57` is kept); evidence 2.4 MB; bundle `/Users/dadleet/src-archive/2026-10-17/shiploop-eff-int-c5f79b.bundle`, made from the commit after this row (INT, the three feature branches, the docs branch) and checked with `git bundle verify` (result in the unit report) |
| 4 | the grep finds nothing; the head table is journaled at both lengths, inline and ask-agent | grep exit 1 (no match); tables above |

## G-SUITES on INT (`SHIPLOOP_PROGRESS=off python3 -B test/shiploop-<t>.test.py`, one run each)

| suite | tests | result |
|---|---|---|
| packet-recut | 21 tests in 1.472s | rc=0 secs=2 |
| step-packets | 9 tests in 0.274s | rc=0 secs=1 |
| packet-bounds | 10 tests in 0.543s | rc=0 secs=1 |
| packet-completeness | 43 tests in 4.292s | rc=0 secs=4 |
| e2e-packet-anatomy | 20 tests in 0.177s | rc=0 secs=0 |
| e2e-commit-counters | 105 tests in 30.145s | rc=0 secs=31 |
| status-display | 15 tests in 5.694s | rc=0 secs=6 |
| keepalive | 58 tests in 54.204s | rc=0 secs=55 |
| narrative | 11 tests in 0.508s | rc=0 secs=0 |
| reference | 4 tests in 0.027s | rc=0 secs=1 |
| reference-routing | 4 tests in 0.565s | rc=0 secs=0 |
| rehydration | 17 tests in 1.427s | rc=0 secs=2 |
| navigator-contract | 110 tests in 55.412s | rc=0 secs=56 |
| navigator-dry-run | 34 tests in 14.102s | rc=0 secs=14 |
| guidance | 62 tests in 3.413s | rc=0 secs=4 |
| quality | 11 tests in 11.271s | rc=0 secs=11 |
| navigator-v4 | 18 tests in 2.180s | rc=0 secs=2 |
| delegation | 52 tests in 9.846s | rc=0 secs=10 |
| improve-schedule | 33 tests in 17.991s | rc=0 secs=18 |
| actual-improve-cli | 68 tests in 109.953s | rc=0 secs=110 |
| chain | 43 tests in 445.814s | rc=0 secs=446 |
| package-integrity | 7 tests in 0.251s | rc=0 secs=1 |
| loops | 33 tests in 26.872s | rc=0 secs=27 |
| test-loop | 123 tests in 251.964s | rc=0 secs=252 |
| skill-calls | 30 tests in 32.044s | rc=0 secs=32 |
| run-review | 657 tests in 55.741s | rc=0 secs=56 |

Also run (footprint, not in G-SUITES): `shiploop-stage-spec` 10, `shiploop-planning-handoff` 7, `shiploop-callback-contract` 61, `shiploop-e2e-fidelity` 131, `test-groups` 29, `ci-policy` 10, `skill-frontmatter` (node) 23 skills, all exit 0;
`python3 -B scripts/check-release-boundary.py --base main` OK.

**Skipped, with the reason.** The quick group and the e2e family (the unit's exit names G-SUITES, and `test/shiploop_e2e/head_table.json` is data read only by the two head tests);
`installed-skill-invocation`, `improve-runtime` and `until-loop-vendor` (nothing under `skills/improve/runtime/**` changed; U2 runs them); any live host (offline unit).
No suite was run on unchanged main (memory testing-scope-to-change).

## Key learning

1. Merging the three tranche-1 branches is textually trivial; the cost is four pinned assertions that encoded a layout (an indent, a line number, a constant). Each was fixed by
   naming the thing the assertion meant (the argument block by its markers, the callback by its label, a head by its journaled value), not by loosening it.
2. A packet-length ceiling needs the path lengths pinned, because the head builder's own switch (quoted knowledge on or off at `PRINT_LIMIT`) makes length a step function of them.
3. The run-2 evidence lived only under `/private/tmp` (169 MB) and a 2.4 MB compact copy of every plan input now lives in the repository: later units read the copy, not `SP/`.

### U20

# Journal row: U20, OpenCode marker and host table test

Consumer: the integrator, who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md` when U20 merges into INT.

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Status | firm (offline, deterministic test; one external fact is a binary string check, see Evidence) |
| Unit | U20, wave W1, base `main` = `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0); branch `feat/shiploop-eff-U20-e18190` |
| Snapshot | `da9e2e75` plus the U20 commit on that branch |
| Fixture | the existing `GateFixture` (a synthetic ShipLoop run at its first Improve stage, bound to a Claude session through the real hook); no packet text touched |
| Run-dir length | not applicable (no packet, no render) |
| Finding acted on | D-24 (R6) in the plan; open item in `docs/shiploop-skill-call-hook-journal-2026-10-16.md` ("an OpenCode marker is not known ... (open)") |

## What changed

- `skills/shiploop/scripts/shiploop_keepalive.py`: `NESTED_NON_CLAUDE` gains `"OPENCODE"`; the comment names Grok's pair (`SESSION_ENV`, read first) and the OpenCode fact.
- `test/shiploop-skill-calls.test.py`: the marker loop of `test_codex_or_cursor_started_from_a_bound_claude_shell_is_not_gated` gains `OPENCODE`; a table `NESTED_HOST_MARKERS` plus `test_every_non_claude_host_has_a_nested_marker_that_beats_an_inherited_claude_session`, which derives the host list from `keepalive.HOSTS`, requires the table to cover exactly the non-Claude hosts, and requires `skill_gate` to refuse to enforce for each marker over an inherited Claude session (control: the inherited Claude environment alone enforces).
- `changes/shiploop/opencode-nested-marker.md` (`bump: patch`; base `main` has no pending note, so no kind to match).
- `docs/shiploop-skill-call-hook-journal-2026-10-16.md`: the "(open)" OpenCode claim marked superseded, dated, with the reason (edited, not deleted).

## Exit items

| # | Item | Result |
|---|---|---|
| 1 | `SHIPLOOP_PROGRESS=off python3 -B test/shiploop-skill-calls.test.py` exits 0 (30 tests plus new) | met: exit 0, `Ran 31 tests` (30 + 1 new), OK |
| 2 | with `OPENCODE=1` and the element removed the test fails (recorded on main) | met: source unchanged from main with the new tests, exit 1, 2 failures (`marker='OPENCODE'` in the existing loop; `host='opencode'` in the new test), both `AssertionError: True is not false` |
| 3 | G-NOTE | met: change note present; this row; the superseded claim marked in the skill-call hook journal |

## Evidence

- Fail-first (tests added, source untouched): `Ran 31 tests`, `FAILED (failures=2)`.
- Mutations of the finished source (each restored byte for byte, `cmp` clean): dropping `CURSOR_PLUGIN_ROOT` from the tuple fails both tests (`marker='CURSOR_PLUGIN_ROOT'`, `host='cursor'`); adding a sixth host `newhost` to `keepalive.HOSTS` fails the new test at the table comparison (`['codex', 'cursor', 'grok', 'newhost', 'opencode'] != [...]`); removing the Grok row from `SESSION_ENV` fails the new test at `host='grok'`.
- External fact: OpenCode 1.18.31 (`/opt/homebrew/Cellar/opencode/1.18.31/bin/opencode`, Mach-O) contains `process.env.AGENT="1",process.env.OPENCODE="1"` and builds child environments as `env:{...process.env,...}` (a `grep -a` over the binary; the process was not launched). Not measured: a live OpenCode shell printing `$OPENCODE` (needs a model session); the marker rests on the string check.
- Suites run: `bash test/run_suites.py --group quick --changed-from main` (the selection for `shiploop_keepalive.py` and the doc edit: 18 suites, including `shiploop-keepalive`, `shiploop-skill-calls`, `shiploop-stage-spec`, `shiploop-status-display`, `shiploop-navigator-contract`, `skill-frontmatter`, `test-groups`, `ci-policy`) exit 0; `shiploop-actual-improve-cli` (a caller of the gate through `complete`) 68 tests OK, run alone.
- Suites skipped, with reason: G-SUITES whole (only U1, U2 and U30 run it); the pin suites for packet text (no packet text or order changed); `shiploop-packet-obligations` and the efficiency-journal test (added by U5, not in this base); full tier (never locally).

## Learning

The gate keys on environment markers, so every host the installer knows needs one that wins over the inherited Claude session; the table was open for OpenCode because nothing tied the host list to the markers. The structural test ties them: adding a host to `keepalive.HOSTS` now fails until its nested marker is recorded and read.
Risk accepted, same direction as Codex and Cursor: a Claude Code session started from an OpenCode shell inherits `OPENCODE=1` and is not gated (no enforcement, never a refusal).

### U27

# Journal row: U27 keep-on-cap rule and the resume line

Consumer: the integrator, who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md` when U27 merges into INT; the owner
reads the result in the journal and in `test/shiploop_e2e/README.md` ("Keeping what a run made").

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Status | firm (offline, fake-host tests; the live behaviour is first exercised by U32 or U33) |
| Unit | U27 (wave 1, base main) |
| Snapshot | worktree branch `feat/shiploop-eff-u27-f63c5d`, base `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0) |
| Fixture | fake `grok` and `claude` executables plus one tiny platform command (`test/shiploop-e2e-platform.test.py`); the Salesforce case only as a parsed `cases.json` entry (no `sf`, no org) |
| Run-dir length | not applicable (no packet text, no render) |
| Evidence | `SP/eff2/u27-*.txt` (fail-first and green runs), `SP/eff2/u27-source.patch` (the source diff used for the fail-first), `SP/eff2/u27-receipts/quick/receipt.json` (G-QUICK receipt); counts below |

## What changed

- `test/shiploop_e2e/run.py`: `keep_refusal` split into `keep_blocker` (a person's stop, stop file, signal, `process.status` stopped,
  an invalid trial, a failed earlier cleanup: never kept) and the finished-delivery refusals; new `keep_decision` returns
  `KEPT_FINISHED`, `KEPT_UNFINISHED` or a refusal. An unfinished run (ShipLoop not done, or the host timed out) is kept when the
  platform declares `keep_checks` and every word names a check that passed; `platform.kept_unfinished: true`, `pass: false`
  (an explicit verdict), the line `platform KEPT (--keep-platform), ShipLoop did not finish: NOT a pass`, a banner that says so.
- A resume of a run whose cleanup record says `kept_unfinished` skips the case's own `preflight` command (recorded
  `platform.preflight.skipped`; home links, wrappers and per-shell proof still run) and gets `resume_note_kept` instead of
  `resume_note`. A resume after a cleaned ending, and a resume after a segment hard-killed in between (pending record), run the
  preflight as before.
- `resume_command` prints `--source checkout` for a checkout run (with `--plugin-dir` where given).
- `cases.json` `chess-salesforce`: `platform.keep_checks` = `deployed`, `tests`, `rules` (not `project`), `platform.resume_note_kept`.
- `refuse_unmatched_keep_checks`: a keep word that names no check, or more than one, is refused before any model starts.
- README: hook table rows `resume_note_kept`, `keep_checks`; "Keeping what a run made" gets the unfinished-run bullet, the resume
  bullet and the statement that a kept app makes the case's preflight refuse the next run until the printed removal command runs or
  another prefix is used.

## Exit items

| # | Item | Result |
|---|---|---|
| 1 | `shiploop-e2e-platform`, `shiploop-e2e-chess-salesforce`, `shiploop-e2e` exit 0 with the listed tests | met: 192/157/431 `def test_` in the files; all three green in the quick group receipt (platform 76 s, chess 135 s, e2e 126 s at load 6 to 8) |
| 2 | timeout + valid + org checks pass keeps, records "not a pass" | `KeepUnfinishedTest.test_a_host_that_timed_out_with_a_working_platform_is_kept_and_recorded_not_a_pass` |
| 3 | timeout + failing org check cleans; invalid trial cleans; user stop cleans | `test_a_failing_keep_check_cleans_and_says_why` (stuck and hang), `test_a_person_s_stop_and_an_invalid_trial_clean_even_when_the_platform_works`, pure `test_the_keep_decision_is_a_pure_function_of_how_the_run_ended` |
| 4 | resume of a `kept_unfinished` run starts without the "not clean" refusal and prints `resume_note_kept`; resume after a cleaned ending runs the preflight as before | `test_a_resume_of_a_kept_unfinished_run_skips_the_case_preflight_and_is_told_the_work_is_still_there`, `test_a_resume_after_a_cleaned_ending_still_runs_the_case_preflight`, `test_a_resume_without_the_flag_skips_the_preflight_but_cleans_at_its_end`, `test_a_segment_killed_hard_after_a_kept_one_leaves_a_pending_record_so_the_preflight_runs_again` |
| 5 | ShipLoop done + all checks keeps as before | `test_a_finished_delivery_of_a_case_with_keep_checks_is_kept_as_a_finished_one` and the 22 `KeepPlatformTest` tests, unchanged |
| 6 | printed resume command round-trips for marketplace, checkout, plugin-dir | `ResumeCommandTest.test_the_printed_command_round_trips_for_a_marketplace_a_checkout_and_a_plugin_dir_run` (also with `--keep-platform`) |
| 7 | `grep -n "not a pass" test/shiploop_e2e/README.md` finds the bullet | met (line of the "A run that did not finish is kept too" bullet); pinned by `test_the_readme_states_the_rule_and_what_a_kept_app_does_to_the_next_run` |
| 8 | G-QUICK (e2e family) | `bash test/run-all.sh --group quick --changed-from main` exit 0, 29 suites passed (the whole e2e family included); `bash test/run-all.sh --group shiploop-composition` exit 0 (16 suites; run although no packet file changed, because G-QUICK names it); `test-groups` and `ci-policy` re-run green after the catalog estimate edit |
| 9 | G-NOTE | `No-Change-Note:` trailer: only `test/` and `docs/` files change, no `skills/` or `agents/` file |

Fail-first (source diff of `run.py` and `cases.json` reverted, tests kept): 12 failures and 4 errors of 21 in
`KeepUnfinishedTest` plus `SchemaTest`, 3 of 4 in `ResumeCommandTest`, 1 of 10 in `TestCaseDefinition`; the README pin fails against the
old README. The tests that pass without the change are regression pins of the unchanged behaviour (a finished keep, no flag cleans, a
stop or an invalid trial cleans, a crash cleans, a resume after a cleaned ending runs the preflight).

## Suites run and skipped

- Run: the three named suites (inside the quick group), `bash test/run-all.sh --group quick --changed-from main` (29 suites), under
  `env -i HOME=<empty dir> PATH=<python>:/usr/bin:/bin:/usr/sbin:/sbin` so no real `sf` resolves.
- Skipped: the packet pin suites of G-FOOT (packet-recut, step-packets, packet-completeness, reference, navigator-contract,
  delegation, loops, test-loop): no packet text, order or generator file changed. The release suites: no `skills/` change.

## Key learning

The default contract kept only a finished delivery, so a run that hit its session cap with a working app removed the app: run 2
had `deployed`, `tests` and `rules` passing at the 7,200 s cap and its cleanup reset the org. The fix has to cover two places, not
one: the decision (keep when the case's org checks pass) and the next segment's preflight, which refuses any prefixed item and so
would refuse the run's own kept app. A keep word that silently matched no check would clean a working app at hour 4 of a long run, so
it is refused at load.

### U28

## 2026-10-17 U28 Salesforce follow-ups (parts 1 to 3, offline)

- Status: firm for parts 1 and 2 (tests only, one guard line); interim for part 3 (the card's `--result-format tap` claim is
  unverified until part 4 reads one real TAP output; the human-table half is measured from the recorded live run).
- Snapshot: base main da9e2e75 (skill-craft 2.5.0, ShipLoop 1.5.0); branch `feat/shiploop-eff-U28-a906d6`.
- Fixture: offline only. Part 1 drives the real CLI on the synthetic `ImproveCliFixture`; part 2 drives the guard against
  `test/shiploop_e2e/fake_sf.py`; part 3 uses the table `sf apex run test --result-format human` printed in the recorded run
  (`SP/sfchess/live2/events.jsonl`, class name made neutral). No `sf`, no org, no model.
- Run-dir length: not applicable (no packet generator text or order changed; `_explain_base` is a refusal that prints only on an
  unread base run, the card is a reference file).
- Unit: U28 (plan section 5.7; P4, D-25, TD-11, CR-1).
- Evidence: this branch; fail-first outputs in the session scratchpad (`u28-cr1-failfirst.txt`, `u28-gitkeep-failfirst.txt`,
  `u28-ff-counts.txt`, `u28-ff-guid.txt`, `u28-mut-tap.txt`).

### Exit items

| Exit item | Result |
|---|---|
| CR-1 test exits 0 | met: `test_a_reviewed_stage_whose_summary_looks_like_a_credential_still_starts_its_improve_child` (inline and Ask-Agent class), 2 tests OK. Fail-first: with the removed refusal put back in `improve_start_contract` (a temporary mutation of `shiploop_navigator.py`, restored) both fail with "the producer's complete started no Improve child". |
| default-scope deploy of a directory holding only `.gitkeep` allowed, everything else still refused | met: `test_a_gitkeep_placeholder_is_not_a_component_and_only_that_exact_name_is_forgiven` (default scope, `--source-dir`, `-d`, the file itself, `validate`, every generated folder, through the wrapper to the fake sf). Refused as before: `.gitignore`, `.gitkeep.bak`, `x.gitkeep`, `.GITKEEP`, `gitkeep`, `classes/.gitkeep.cls`, `classes/.gitkeep.cls-meta.xml`, a link named `.gitkeep` that leads outside the project. Fail-first: without the guard line the first assertion fails. The 91 older guard tests still pass. |
| `grep -n "reporter" skills/shiploop/references/platforms/salesforce.md` finds the line | met (line 102). Guard: `test_the_salesforce_card_names_the_reporter_shiploop_reads_and_the_red_na_route`; fail-first without the card paragraph. |
| real-org selftest exits 0 and every reference test ID reads pass | NOT RUN here (part 4 belongs to the main session). If it fails, the adapter code of D-25 opens as its own plan. |
| `shiploop-reference-routing` exits 0 | met (4 tests OK). |
| G-STD | G-FOOT met (suites below), G-NOTE met (`changes/shiploop/salesforce-reporter-card.md`, bump patch); G-LEDGER and G-REVIEW do not apply (U5 not built; the unit does not name G-REVIEW). |

### Suites

Run, all exit 0, under `env -i`, an empty HOME and a PATH with no `sf` or `sfdx`: `shiploop-e2e-sf-guard` 92, `shiploop-test-counts` 43,
`shiploop-guidance` 63, `shiploop-test-loop` 123, `shiploop-actual-improve-cli` 70, `shiploop-reference-routing` 4, `shiploop-reference` 4,
`shiploop-packet-completeness` 32, `shiploop-e2e-chess-salesforce` 191, `shiploop-e2e-platform` 143, `shiploop-e2e-fidelity` 129, then
`run-all.sh --group quick --changed-from main` (45 suites OK, exit 0; a first attempt on a PATH without node and jq failed on tool-missing errors, not on the change, and was discarded: the clean PATH is every Homebrew binary except `sf` and `sfdx`). Skipped: `--group shiploop-composition` and the
full tier (the footprint is a guard line, a refusal sentence, a card paragraph and tests; G-QUICK is U27's exit); G-RENDER (no packet
text or order changed).

### Key learning

- Part 3 is grounded in a real sample. In the recorded Salesforce run the model followed the case prompt and ran
  `sf apex run test ... --result-format human`; every row names the test and puts `Pass` after the name, which no pass mark of
  `shiploop_test_counts.outcomes` matches, so 11 ids read `shown` and the base run was refused as `unread` (the plan counts 21 occurrences of that sentence in the live stream, TD-11). The same run's
  prompt names that format, so the card is where a model learns that the recorded command may differ from the one it reads.
- An org-run test runs the code already in the org: on the item's base it cannot fail unless the command deploys the tree, so the
  honest route is `red_na` with that reason (the candidate run and the mutation check carry the proof). The card now says so.
- The `.gitkeep` refusal (`sf-calls.jsonl`, call 9fa2228c) was a guard false positive on a placeholder with no metadata suffix; the
  fix is one skip of the exact name after the project-boundary check, so a link named `.gitkeep` that leaves the project is still refused.
- CR-1 is a regression test of the credential-pattern removal (f1f38850, d4d08351) on the one place no acceptance test drove: the
  Improve opening, which quotes the reviewed stage's summary.
- Open for the main session (part 4): `python3 test/shiploop_e2e/checks/chess_salesforce.py selftest --org de --prefix SLChess --reference`,
  then pipe one `sf apex run test --result-format tap` output of the reference tests into `shiploop_test_counts.outcomes` with the test ids.
  Until it runs, the card's "an `ok` or `not ok` line per test" is the generic TAP shape, not an observed Apex output.

Related commits: f1f38850, d4d08351 (credential-pattern removal), 996a378c, 5d028aee, d56904e2 (Skill-call hook), a7c1fdb2 (audit
fixes), da9e2e75 (base).

### U3

# Journal row: U3, seeded slices run the real gates (2026-10-17)

Consumer: the integrator, who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md`, and the session that re-takes the slice baselines (U6 part 2). Read it before the A/A pair.

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Status | firm for the seed, the two lines and the tests (offline, run); interim for what the change does to a live slice (not measured: no model ran) |
| Snapshot | base `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0), branch `feat/shiploop-eff-U3-9c09b0` |
| Fixture | `node-fix-bug` on `test/shiploop_e2e/fixtures/node-base` (the real case), and a synthetic item (`a.py`, `check.sh`) for the end-to-end contrast |
| Run-dir length | not applicable: no packet text or order changed (the offline probes ran at about 150 characters under the scratchpad) |
| Unit | U3 (plan rev 6, section 5.1; findings X-2, TD-5, SP-7a) |
| Evidence | `docs/experiments/shiploop-eff-journal-rows/U3-evidence/` (`failfirst.txt`, `ab-synthetic.txt`, `ab-node-fix-bug.txt`), the tests named below |

## What changed

- `test/shiploop_e2e/run.py` `SEED_SCRIPT`: when the plan's item enters its inner loop the seed writes `lint/items/<item>.md` with `shiploop_lint.capture_base`, in the same `nav.save` transaction as the state (what `lint.on_transition` does on a real run). `seeded.item_bases` names the items.
- `run.seed_run` (`seed_home`): commits a neutral `docs/shiploop/spec.md` (`R-1` = the request) and `environment.md` (`## Commands` = the case's checks) into the seed repository before the baseline commit, so the worktree starts clean and the base already holds them. `--seed-without-home` (slice.py, and run.py with `--seed-at`) is the flagged no-home variant; the item base is recorded either way. `seeded.home` names the files written.
- `fidelity.gates_not_exercised` and `packets.gates_line`: the test stage's base-run and mutation-check records that say `skipped` are named in the fidelity validation line (only when there are some, so the five-line cap and the pinned lines hold) and in the packet report (always: `none`, the skipped gates, or `not measured` when the test stage was not reached).

## Exit items (all met; the commands and counts)

1. `python3 -B test/shiploop-e2e-slice.test.py` exits 0 with new tests: after seeding, `lint/items/W1.md` exists and `docs/shiploop/spec.md` holds `R-1` (`SeedTests`); it fails when the write is removed (`failfirst.txt` section 1: 6 failures of 12 tests; section 2, the home write removed: 2 failures).
2. `shiploop-e2e-fidelity` and the e2e family (packet-anatomy included) exit 0; the line is asserted in `ValidationTest` (fidelity) and `GatesNotExercisedLineTests` (packet report). They fail on the base source (`failfirst.txt` section 3: 4 and 4). `packet_anatomy.py` measures packet text, not run records, so the packets.py report is where the line is asserted.
3. G-QUICK: `bash test/run-all.sh --group quick --changed-from main` exit 0 (29 suites, 1,996 tests, the whole e2e family included: `shiploop-e2e-slice` 41 tests, 13 new; `shiploop-e2e-fidelity` 133, 4 new; `shiploop-e2e-packet-anatomy` 18) and `--group shiploop-composition` exit 0 (16 suites, 371 tests), both on the committed tree `608ceb6c`, under `env -i` with a PATH that has no `sf`.
4. `No-Change-Note:` trailer: no `skills/` or `agents/` file changed.

## The measurement behind it (offline, no model)

One drive of a harness-seeded item through the real `complete` to carry-forward, once as main's seed left it and once with this unit's seed (`ab-synthetic.txt`, and the permanent test `SeededRunsRunTheGatesTests`):

| Gate | main's seed (no item base) | this unit's seed |
|---|---|---|
| base run (`tests/*-base1.md`) | `skipped: no item base was recorded`, `disposition: passed` | ran: the focused command `red` on the base, the regression command `counted` |
| mutation check (`*-mutation1.md`) | `skipped: no item base was recorded` | ran: 3 mutants, 3 killed, 0 survived (with bytecode writing off, see Key learning) |
| change inventory (`lint/*-inventory.md`) | `status: unavailable` | `status: ok`, the changed files listed |
| item commit | no `feat: W1` commit | `feat: W1 ...` committed |

The real case on its own fixture (`ab-node-fix-bug.txt`, and the test `SeededCaseFixtureRunsTheGatesTests`): a correct `paginate()` fix is accepted by the real gates; the base run is red for the new test and counted for the suite; the mutation check says `no mutants: no changed product line matched an operator` (`Math.ceil(items.length / size)` has no operator candidate: the TD-4 gap, now visible in the line instead of hidden behind a skip); `feat: W1 Fix paginate() dropping the last partial page` is committed. The stop condition "the real gates refuse the fixtures" did not occur, so no fixture was changed.

## Key learning

- Every earlier slice baseline (`baselines.jsonl`, the A/A inputs, run 2's Salesforce row if it was seeded) covers four gates fewer than it claims; U6 part 2 re-takes them (plan N2). Offline `packets.py --offline` still renders without a base or a home, so its packet sizes differ from a live seeded slice by what the quoted `spec.md` and `environment.md` add (a few hundred characters at test-spec and later stages: not measured).
- **A latent false refusal in the mutation check, found while testing (not fixed here).** The check writes each mutant into a temporary copy of the candidate right after the unmutated run in the same copy. When the test command writes bytecode, a same-size one-token mutant (`2` to `3`) written within the same second as the compiled file's recorded source time loads the stale `.pyc`, so every mutant "survives" and the gate refuses "the tests catch none of these changes". Measured: the same synthetic Python item, driven through the real `complete`, passes with `PYTHONDONTWRITEBYTECODE=1` (3 of 3 mutants killed) and is refused under `env -i` without it (3 of 3 survive); with `python3 -B` and an ignored `__pycache__` in the fixture it passes either way. It did not show on this machine's runs because the owner's environment sets `PYTHONDONTWRITEBYTECODE=1` (also noted in `docs/experiments/batch-1008-design-audit-20261008/design-audit.json`); on a machine without it, a Python item whose repository does not ignore `__pycache__` is wrongly refused until the item goes back to its step plan. Per KISS it is recorded, not fixed in this unit (U3 only makes seeded slices reach the gate); a fix is one line in `shiploop_mutation._check` (`PYTHONDONTWRITEBYTECODE=1` in the `environment` of the mutant runs) and the integrator decides.
- The test that ties the unit to the engine borrows `TestLoopTests` from `test/shiploop-test-loop.test.py` (as `WorktreeItemCommitTests` already does in that file): a change to that driver's helper names will break `RealCompleteDriver` in the slice suite.

## Suites run and skipped

Run (all under `env -i HOME=<empty dir> PATH=<dir with only python3 and node>:/usr/bin:/bin:/usr/sbin:/sbin`, so no real `sf` resolves, `SHIPLOOP_PROGRESS=off`): the 29 suites `--group quick --changed-from main` selects (the 13 e2e suites, `test-groups`, `ci-policy`, `skill-frontmatter`, and the ShipLoop suites that match the changed paths) and the 16 of `--group shiploop-composition`; the seed, fidelity and slice suites alone while iterating; the fail-first runs in `U3-evidence/failfirst.txt`.
Skipped: G-SUITES whole (U1/U2/U30 only), the packet pin suites by name (`packet-recut`, `step-packets`, `packet-completeness`, `reference`, `delegation`, `loops`, `test-loop` are not selected: no packet text, order or `skills/` file changed; `delegation` ran inside the composition group; `test-loop` did not run, the slice suite only loads its driver), the full tier. The first quick run had one failure, my own end-to-end test on a machine without `PYTHONDONTWRITEBYTECODE` (the bytecode finding above); the test was fixed, not the gate, and the whole group re-run.

## Results of the final G-QUICK run (commit `608ceb6c`)

| Command | Result |
|---|---|
| `bash test/run-all.sh --group quick --changed-from main` | exit 0, receipt status `passed`, 29 suites OK, 1,996 tests |
| `bash test/run-all.sh --group shiploop-composition` | exit 0, receipt status `passed`, 16 suites OK, 371 tests |

Not measured: a live slice (no model ran); the size effect of the seeded `spec.md` and `environment.md` on later packets; whether U6's A/A shows the seeded gates changing turns or time.

### u4

# U4 journal row: several clears per slice, and the resume-prompt condition

Consumer: the integrator, who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md`, and U5/U6/U31, which read `clear.json` and `slice-result.json` for the S-6 battery.

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Status | firm for the harness behaviour (fake-host tests, no model); the live S-6 battery that uses it is not run (U6, U31) |
| Unit | U4 of `SP/eff2/aggregate-plan-final.md` (3.2 row "P2 (clear.py)"; rev 4 Step 1.3, the several-clears part) |
| Snapshot | base `main` `da9e2e75`; branch `feat/shiploop-eff-u4-3ecdb2` (the commit that adds this file) |
| Fixture | synthetic: `FAKE_HOST` and the new `FAKE_CLAUDE` in `test/shiploop-e2e-slice.test.py` over `test/shiploop_e2e/fixtures/node-base`; no model, no packet text read |
| Run-dir length | not applicable: no packet text, order or head changed (G-RENDER not applicable) |
| Evidence | `test/shiploop-e2e-slice.test.py` (45 tests; new classes `ClearSpecTests`, `ResumePromptTests`, `ClearRecordTests`, `ClearThroughMainTests`, plus new cases in `ClearMetricTests`, `ClearTriggerTests`, `ClearProbeTests`); the README section "The clear probe (S-6)" in `test/shiploop_e2e/README.md` |

## What changed (all under `test/`)

- `clear.py`: `parse_spec` takes the repeated flag and returns a list (`label` names a position); `trigger` gets the Improve position (`improve`, `improve:inside`) and `since` (an inside position counts only the packet and calls after the earlier clear's stop line); `redone` gets `until_line`, so a redo is counted against the clear it follows and not the earlier ones; `point` reports stage `improve` with the Improve stage's own action while a review runs.
- `slice.py`: `--clear-at` repeats; `drive()` ends each session at the next position not yet cleared and appends to `clear.json`, which is a list; `clear_facts` returns one entry per clear with `redone` from its own stop line; `--resume-prompt {names-next,withheld}` (`continue_prompt`: today's `run.resume_prompt`, or "Continue the ShipLoop work for the repository in this directory."); `invocation.json` records `clear_at` and `resume_prompt`; `sessions.jsonl` `told` records what each resume prompt named (null for withheld); `slice-result.json` gains `clear_unfired`; `main` runs one loop in which a clear is not a resume (it does not use `--max-resumes`) and a resumed Grok or Codex session still has the remaining positions in force.
- `flow.py` and `flow_viewer.html`: `clear` is a list; the page shows each clear and one divider per clear at the first event after its stop line (before, every later phase repeated the one divider).
- `README.md`: the probe, its positions, the two prompt conditions and the records. `suite_catalog.py`: the slice suite's duration estimate (33 s to 81 s, 45 tests).

## Exit items

| # | Item | Result |
|---|---|---|
| 1 | `shiploop-e2e-slice` exits 0 | met: 45 tests, exit 0 (two runs: alone, and inside the quick group, 63.9 s) |
| 2 | `shiploop-e2e-reorientation` exits 0 | met: 120 tests, exit 0 |
| 3 | three sequential clears give three records | met: `ClearProbeTests.test_each_session_ends_at_the_next_position_not_yet_cleared_and_three_clears_give_three_records` (the `drive` loop, boundaries implement, test, verify) and `ClearThroughMainTests` (through `slice.main` with a fake `claude`: implement, implement:inside, improve) |
| 4 | a stream redoing a call after the second clear fails that clear only | met: `ClearRecordTests.test_a_stream_redoing_a_call_after_the_second_clear_fails_that_clear_only` (pass flags `[True, False, True]`, verdict `no_redo` False) and `ClearMetricTests.test_a_redo_is_counted_in_the_window_of_the_clear_it_follows_and_no_other` |
| 5 | `--clear-at implement:inside --clear-at test --clear-at improve` parses | met: `ClearSpecTests`, `ResumePromptTests.test_the_command_line_collects_every_position_and_offers_the_two_conditions` |
| 6 | non-Claude `:inside` stays recorded, not gated | met, as this reading: the position is accepted (not refused), recorded as requested in `invocation.json` `clear_at` and listed in `clear_unfired`; it never fires on a stream the harness cannot read (`ClearTriggerTests.test_a_stream_the_harness_cannot_read_stops_at_a_boundary_and_never_inside`, a guard that held before the change) |
| 7 | G-QUICK (e2e family) | met: `run-all.sh --group quick --changed-from main` exit 0 (29 suites, the whole e2e family included) and `--group shiploop-composition` exit 0 (16 suites), both under `env -i` with a PATH holding only python3 and node (no `sf`); also `ci-policy`, `test-groups` and `scripts/check-release-boundary.py --base main` OK |
| 8 | `No-Change-Note:` | met: the commit carries the trailer (no `skills/` or `agents/` file changed) |

## Fail-first (source diff reverted, tests kept)

17 of the 28 selected clear tests failed (14 errors, 3 failures; 20 failure records counting the four sub-cases of the parse test): every new behaviour test failed on `main`'s `clear.py`, `slice.py`, `flow.py` and `flow_viewer.html`, most with `AttributeError` or `TypeError` because the API they pin did not exist (`label`, `continue_prompt`, `clear_records`, `since`, `until_line`, the list form). Three failed on an assertion: `ClearTriggerTests.test_inside_an_improve_stage_waits_for_its_packet_and_a_completed_call_that_is_not_shiploops`, `ResumePromptTests.test_the_command_line_collects_every_position_and_offers_the_two_conditions` (the flag kept only the last value) and `ClearThroughMainTests.test_the_default_condition_names_next_and_the_record_says_what_it_named`. Held before the change (guards, not counted): the non-Claude `:inside` test and the existing boundary and inside trigger test.

## Suites

Run: `shiploop-e2e-slice` (45), `shiploop-e2e-reorientation` (120), the quick group `--changed-from main` (29 suites: core, the e2e family, `shiploop-mock-replay`), `shiploop-composition` (16; none of them reads the files changed here, so it can only confirm), `ci-policy`, `test-groups`. Callers found by `git grep` of `parse_spec`, `clear_facts`, `CLEAR_RECORD`, `clear.trigger`, `clear.redone`, `clear.point`, `--clear-at`, `resume-after-clear`, `slice-result`: `slice.py`, `flow.py`, `flow_viewer.html`, the slice suite; the Run Review exporter reads only `verdicts`. Skipped: the full tier (owner rule), packet pin suites (no packet text changed).

## Key learning

- A repeated flag needs an order and a window, or the metric lies: with positions firing in the order given, each clear is measured from its own stop to the next clear's, so a redo after clear 2 of an op done before clear 1 fails clear 2 only; unbounded, it would also fail clear 1.
- Strict order means a position that cannot fire blocks the later ones. The result says so (`clear_unfired`, printed after the slice) so a probe that stopped less often than asked is visible; `no_redo` stays "every clear that fired passed" (absent with none).
- The Improve stage is its own position: while a review runs the reviewed stage is not at its boundary, and `improve` fires at the first review after the previous clear (the order of the flags picks which one).
- The condition (R0) is part of the run record: `invocation.json` `resume_prompt`, `sessions.jsonl` `told`.
- Found, not changed: `sessions.jsonl` labels the post-clear session `continued` (the doc says a cleared context is `fresh`), so `metrics.fresh_starts` lists no slice clears. U5's `orientation_bytes` reads `clear.json` and the stream, so it does not need it; making the session `fresh` is one argument in `drive` plus a test, and it adds blocks to `metrics.json`.
- Found, not changed: on Grok and Codex `redone` is always empty (their translated streams hold no Claude-shaped calls), so a boundary clear there is recorded with a vacuous pass. The plan already runs those hosts at boundaries only; the verdict there is "the run continued", not "nothing was redone".

### U5a

# U5 part A: render tooling (packets.py text render, render_diff.py, packet_anatomy.py)

Consumer: the integrator, who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md`, and every unit worker that
runs G-RENDER (`packets.py --offline ... --text-dir`, then `render_diff.py OLD NEW --unit Un`).

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Status | firm for the tooling (offline, no model); the head-table values are interim: they are today's heads on main, and U1 (merged branches) and U7 (allocation) re-baseline them in their own commits |
| Snapshot | main `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0) plus the commit of branch `feat/shiploop-eff-U5a-1d5098`; no file under `skills/`, `agents/` or `plugins/` changed, so no packet changed by one byte |
| Fixture | offline walk of step case `node-fix-bug` (`test/shiploop_e2e/step_cases.json`), inline and ask-agent; the saved live packets of the Salesforce chess run 2 (`SP/pk/live`, 18 files, read only) for the anatomy exit |
| Run-dir length | 83 (a normal install) and 163 (the live run), CLI path 96 (plugin-cache install) |
| Unit | U5 part A (part B: `metrics.py`, `arms.py`, `clear.py`, `step_cases.json`, obligation and journal tests, fixtures, N5) |
| Evidence | `docs/experiments/shiploop-eff-journal-rows/U5a-evidence/` (anatomy before and after on the live packets, the four head-table renders, the `render_diff.py` exit demonstration); `test/shiploop_e2e/packet_head_table.json` |

## What was built

- `packets.py --offline CASE --text-dir DIR [--delegation ...] [--run-dir-length N] [--cli-path-length N]`: each packet as
  `<NN>-<stage>.printed.txt` and `.whole.txt` plus `manifest.json` (case, route, lengths, `text_format`, sizes, commit). The
  run directory and the CLI path have exactly the requested length (a real directory chain of that length; the CLI path is a
  symlinked package root, so the references still resolve). The text is fixed: ids from a counter, the run directory and the
  package root as `/home/render/w...` and `/home/install/i...` of the same length, the checkout root as a 63-character install
  root, the interpreter as `/usr/bin/python3`. Whole or head is decided on that text. `offline_packets` (the default walk the
  other suites use) keeps this machine's paths and random ids.
- `render_diff.py OLD NEW --unit Un`: every added and removed line with its size, per stage and per form (printed, whole); exit
  1 when an added line has no entry in `packet_changes.json` for a named unit (prefix; stages; routes; exactly one of `offset`
  (removed lines of the same stage that pay for it, one removed line pays for one entry) or `approval` (the decision)), or a
  printed text passes `packet_head_table.json`, or the table has no value (`--no-head-table` skips it by name); exit 2 when the
  renders were made with other options or the allowlist is malformed. `--emit-table DIR [--write]` records a render's sizes.
- `packet_changes.json`: one empty list per unit U1 to U35, one key per line, so units that add entries edit different lines.
- `packet_anatomy.py`: reads the quoted knowledge files, the hand-off values (open items, lists, quoted cases, followed
  requirements), the consumer-delivery block and the excerpt marker; the printed head (References, result template and
  pointer lines no longer count as the stage duty; the numbered duties under a one-sentence opening are the duty); the packets
  branch top lines (index pointer, owner rule, `GUIDES/` paths) and the final layout (pointer lines, style line, loop block that
  ends at "Call an exit condition satisfied only when", `HEAD_END`); `--glob` (read a text-dir) and `--max-unclassified` (exit 1).

## Exit items (part A)

| Item | Result |
|---|---|
| 3 (anatomy): at most 5% unclassified on `SP/pk/live/` (was 49.3%) | met: 0.2% (1,470 of 662,400 bytes); the base file measures 49.1% (325,409 bytes) on the same 18 files; `packet_anatomy.py SP/pk/live --max-unclassified 0.05` exits 0. Also 0 unclassified bytes on all 96 render files of the head table (4 keys, printed and whole, 12 packets each) and on the 192 files of `SP/eff2/final-verify` (main and merged tree, 83 and 163, both routes); the base file leaves 1.1% to 1.8% on main's renders and 4.1% (printed) to 5.4% (whole) on the merged tree's |
| 3 (render): `--run-dir-length 83` and `163` render reproducibly | met: two renders at each length are byte-identical (`diff -r`, 25 files each); the same text under another `TMPDIR`, and from a second copy of the tree (`git archive` of `skills` and `test/shiploop_e2e` into a directory with a longer name) all 25 files are byte-identical but the manifest's commit; every `--run-dir` in the text is exactly 83 (163) characters; every CLI path exactly 96 |
| 5 (render_diff): non-zero on a planted extra line, zero on an allowlisted change | met: planted line in a real implement head, empty allowlist: exit 1, line and size named; the same line with an approval entry: exit 0 with `--no-head-table`, exit 1 with the table (it passes the implement ceiling by 50); a shortened line with an offset entry and the shipped table: exit 0 (`render-diff-exit-demonstration.txt`) |
| 3, audit probes at `2686b427` (375,278 / 276,270 / 79,647) | not part A |

## Head table seeded from main (printed characters, CLI 96)

| Key | step-plan | implement | test | verify | carry-forward | largest |
|---|--:|--:|--:|--:|--:|--:|
| inline/83 | 19,692 | 15,053 | 14,891 | 15,555 | 15,915 | 19,692 |
| inline/163 | 20,892 | 15,933 | 15,852 | 16,135 | 17,115 | 20,892 |
| ask-agent/83 | 21,374 | 16,167 | 14,891 | 15,754 | 17,118 | 21,374 |
| ask-agent/163 | 22,574 | 17,047 | 15,852 | 16,334 | 18,318 | 22,574 |

These are measured with the CLI padded to 96 and the install root fixed at 63 characters, so they are not the plan's bare-CLI
numbers (`fv_heads.py`: step-plan 19,395 / 21,077 at 83): about +300 on step-plan from the CLI path and the fixed root. Main
already has step-plan over the 20,000 host cut for ask-agent at 83 and for both routes at 163.

## Suites

Run once each from the worktree (`SHIPLOOP_PROGRESS=off python3 -B test/<name>.test.py`), all exit 0: `shiploop-e2e-packet-anatomy`
(27 tests, 9 new), `shiploop-e2e-render-diff` (43 tests, new), `test-groups` (29; the pins moved from 87 to 88 ShipLoop suites,
140 to 141 in all, and the E2E family list gains the new suite), `ci-policy` (10), `shiploop-packet-completeness` (32),
`shiploop-packet-recut` (16), `shiploop-step-packets` (8), `shiploop-e2e-commit-counters` (105), `shiploop-e2e-slice` (28),
`shiploop-status-display` (15), `shiploop-e2e` (427; flow.py imports `packets.py`). The six fast ones were run again after the
last edit. `git grep` callers of the changed symbols: `offline_packets` (completeness, recut, step-packets, commit-counters),
`archive_packets`/`build`/`write_report` (slice, flow.py), `packet_anatomy` (its own suite). The default `offline_packets`
output is identical to the base's modulo ids and temp names (both routes, whole and printed; checked against the base file).

Skipped: the rest of the E2E family (`shiploop-e2e-environment`, `-baseline`, `-quality`, `-fidelity`, `-reorientation`,
`-runrecord`, `-chess-salesforce`, `-platform`, `-sf-guard`): they do not import `packets.py`, `render_diff.py` or
`packet_anatomy.py`, and `run.py`, `metrics.py`, `clear.py` were not touched (G-FOOT by the caller rule: `git grep` of the
changed symbols). No G-QUICK run (the unit's exit does not ask for it). `bash test/run-all.sh` and the full tier: not run.

Fail-first (revert only the source change, run the test, restore): the base `packet_anatomy.py` fails the new anatomy
tests (27 tests: 61 failing subtests and 3 errors); 6 mutations of `packets.py` (padding off by one, ids not fixed, CLI not
padded, run dir off by one, checkout root not canonicalised, head decided on the real text) are each caught by 1 to 5 tests; 11
mutations of `render_diff.py` (nothing unallowlisted, table never exceeded, missing table value passes, offset never short, a
removed line pays twice, other-option renders compared, every unit applies, offset and approval both, short prefix, offset need
not name a removed line, blank lines listed) and 8 of `packet_anatomy.py` rules are each caught by 1 to 7 tests.

## Key learning

1. A packet render is not comparable across checkouts as it stands: the temporary directory name, the ids, the checkout root
   (reference paths, the red-check script, the loop runtime) and the interpreter all print into it, so head sizes depend on the
   worktree's path length and two renders never diff clean. G-RENDER needs the fixed text; the 83/163/96 lengths then mean one
   thing on every machine.
2. The anatomy tool was blind to a whole class of live packets: the quoted knowledge files, hand-offs and consumer-delivery
   block were 49% of the bytes of the Salesforce run's packets, and in a printed head the References block, result template and
   pointer lines were counted as the stage duty. Its limit test (3% on the engine's own walk) could not see it because the
   walk has no knowledge files.
3. A head table that CI does not enforce is only as good as the commit that edits it: U1 and U7 re-baseline it with
   `render_diff.py --emit-table DIR --write` in the commit that journals the values; no other unit raises it.

Related commits: `da9e2e75` (base), `a7c1fdb2` (baseline row of the audit-fix run), `2686b427` (the audit probes' commit).

### U5b

### 2026-10-17 U5b measurement, arms.py, ledger, journal test (part B of U5)
- status: interim
- snapshot: da9e2e75
- fixture: claude-step-slice (the recorded Claude Sonnet 5.5 node-fix-bug slice, ShipLoop 1.3.0) and grok-long-run (the recorded Grok 4.7 run, 33,833 events), both as compact extracts under test/fixtures/efficiency and measured on the raw saved runs; the three node-seeded-* cases on node-base; the generated long (16/14/6 KB) and small (a few hundred characters) knowledge homes; the dry-run delivery walk (33 packets, 24 stages) and the offline step slice, inline and ask-agent
- run-dir length: n/a
- unit: U5b
- evidence: `docs/experiments/shiploop-eff-u5b-20261017/`, `test/shiploop_e2e/arms.py`, `test/shiploop_e2e/packet_obligations.json`, `test/fixtures/efficiency/`
- exit items: (1) met: on the raw live2 events the report reproduces the S5 snapshot at the first 29,668 events exactly (packet files 40, Improve handoff 19, improve/SKILL.md 14, ADAPTER.md 12, shiploop SKILL.md 8) and the whole file (46, 21, 16, 14, 10); 14 compactions; the first call after each of the last 9 was the shiploop SKILL.md read (0 of the first 5); `next` within 12 calls after 9. On the raw Claude slice: 20 of 20 completes piped, 19 of 20 with the run directory built through a variable (20 with any variable), the status display could read 1 of 21 commands, the packet file opened in 3 of 8 producer stages (step-plan whole, test-spec and carry-forward by slice), 4 skipped gates (base, mutation, inventory, item commit), the improve skill invoked in 1 of 4 Improve stages, the cut lengths N = 50, 30, 30, 40, 14, 30, 25; the bucket totals add to the run's 134,265 tool-result characters plus the 28,410-character skill text that arrives as a user message (prints 54,709, packet files 37,444, child handoffs 7,479, ADAPTER 2,550). (2) met: `arms.py` on a fixture folder of two arms prints DECISION: candidate and exits 0 (arms-chooses) and exits 2 inside the A/A spread (arms-inside-spread); exit 3 with no spread. (3) met: the obligation test exits 0 on unmodified code (14 tests, 11 rows) and 1 with one anchor taken out of source (Checked by: in shiploop_navigator.py: 3 failures, 64 violations; restored, exit 0); the journal test (11 tests, reads the journal when present and the row fragments) and test-groups (29 tests, counts 90 ShipLoop suites and 143 in all) exit 0; the audit probes reproduce 375,278 / 276,270 / 79,647 characters at 2686b427 exactly (a git archive of that commit, sizes read at the audit's 30-character root and its run and repository path lengths: unadjusted the same tree prints 402,410 and 299,064 because a packet prints the checkout path many times). packet_anatomy (5% unclassified) and `--run-dir-length` are U5a. (4) met, measured: the plan-stage authoring time of the live2 run is 201.4 s of its 4,661.0 s planning window, 4.3 percent (stage 612.0 s less its Improve child's 410.6 s), and the span of the plan-stage calls that name Backchain is 170.9 s, 3.7 percent (8 calls); the Luna study's figure for the same quantity was 17 percent (64.1 of 375.9 minutes). (5) seeded half met: each of the three planted-defect cases (a locale-aware comparator where the request says case-sensitive, a sort with no comparator, a mean with no empty guard) passes its own check commands and fails its probe on the unreviewed tree and passes both on the fixed tree; render_diff.py is U5a.
- suites run: shiploop-e2e-efficiency (74 tests), shiploop-packet-obligations (14), shiploop-efficiency-journal (11), test-groups (29); the footprint of the changed symbols, once each, all exit 0: shiploop-e2e-slice (28), -reorientation (120), -fidelity (129), -packet-anatomy (18), -commit-counters (105), -baseline (143), -runrecord (6), -quality (128), shiploop-e2e (427), shiploop-step-packets (8), shiploop-packet-recut (16), shiploop-packet-completeness (32)
- suites skipped: shiploop-e2e-environment, -chess-salesforce, -platform and -sf-guard (65, 115, 55 and 20 s; they call none of the changed symbols and reach the org's `sf` only through fakes; the import path of metrics.py and clear.py is exercised by the twelve family suites run); the whole quick group and the full tier (G-QUICK is not an exit item of this unit); no shiploop-chain or improve suite (no skills/ file changed)
- key learning: a packet's size depends on the length of the checkout path it prints, so a measurement at another path is read against the audit only after the path is normalised (the audit's own figures reproduce exactly that way); "variable-built" is only 19 of 20 if it means the run directory argument, because the CLI path in `$SC` also makes a command unreadable to the status display (20 of 20); an equivalent mutant (a filter applied twice) survived the first fail-first sweep and was replaced, so the fail-first record is 18 mutations that bite; the plan-stage Backchain child is 4.3 percent of the live2 planning window against 17 percent on the Luna run (one run each, so it prices the 30-minute bar differently by host and is not a constant to plan with)

### 2026-10-17 · step-scoped check commands (firm)
- question: why did the chess run's step plan (S1 engine, S2 controller, S3 board) collapse into one step?
- evidence: `/Users/dadleet/e2e-runs/20261017/salesforce-chess-int-802e29` step 16 (implement S1, outcome revise): the packet's "Check commands (run each after every edit)" listed the C12 grep for the board, tab and app files that only S3 creates; it exited 2 on S1's tree and the revise's repair was a one-step plan of 11 paths (step 17), so 1 implement and 1 Improve ran instead of 3 of each. Cause: `_step_lines` took every `suite: check` row of the item and ignored its `criteria`. Owner (2026-10-17): the per-step series is the intent; fix it.
- change: `shiploop_navigator.step_checks` splits the item's checks into those due at the step (no criteria, or every criterion's last listing step at or before it) and those due later (named on the packet with their step); the step-plan check duty and the implement exit condition say so.
- tests: new `shiploop-delegation` case `test_a_check_runs_from_the_step_that_finishes_its_criteria` (a 3-step plan: the board check is due only at S3, lint at every step); fail-first: on the previous navigator it reports the board check due at all three steps, the run's failure. Suites run once after the last edit, all OK: shiploop-delegation (59), -head-order (33, the fixture's expected check list now uses `step_checks`), -packet-recut (30, after raising three head values by 18 to 117 characters in head_table.json), -loops (51), -navigator-contract (110), -callback-contract (72), -step-packets (9), -packet-completeness (62), -packet-obligations (15), -reference (8), -reference-routing (4), -test-loop.
- open: the gate does not yet refuse a step plan whose check cannot be satisfied by any prefix of the steps; a live run with a multi-step plan should show one implement and one Improve per step in order (owner TODO, memory todo-step-series-order).
