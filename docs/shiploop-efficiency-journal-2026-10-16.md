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
