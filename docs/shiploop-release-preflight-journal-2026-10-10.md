# Release preflight: no ShipLoop release without an E2E round on record (batch 1012, task M, 2026-10-10)

Worktree `b1012m-1bbefb`, branch `batch1012m-1bbefb`, base `658ff4e3`. Plan: `docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md`, critique point 10
("the maintainer loop is not covered") and plan of action v5, row M. Maintainer tooling only: `scripts/release.py` is not a skill, so there is no change note and
no release of its own. Every claim below is marked firm (a test or a recomputed count), interim or exploratory.

## What was asked, and the rule that was built

**Question.** Nothing enforces that the owner's maintainer loop (an E2E round, its learnings journaled in `test/shiploop_e2e/LEARNINGS.md`) ran before a
release. The cheapest way to make our own loop leave lessons is a preflight in `scripts/release.py`, not ShipLoop code.

**Rule (firm; `release.e2e_round_missing`, called from `release.plan_all`).** A release whose pending notes include the `shiploop` leaf is refused unless, in the
range from the last `Skill-Craft-Release` commit to HEAD, either some commit touches `test/shiploop_e2e/LEARNINGS.md`, or some commit carries a
`No-E2E-Round: <reason>` trailer with a non-empty reason (git's own trailer parse: the final message paragraph). The refusal prints in the existing shape
(`release: <message>` on stderr, exit 1) and names both fixes, one sentence each:

```text
# example, from a scratch repository
release: shiploop would ship with no E2E round on record since the last release (430f9473).
  Add an entry to test/shiploop_e2e/LEARNINGS.md in a commit in that range, or
  add a 'No-E2E-Round: <reason>' trailer with a reason to a commit in that range (final message paragraph, next to Co-Authored-By).
```

**Scope: only a release that ships `shiploop` (firm as a decision, interim as a policy until a few more releases have run under it).** The journal is
ShipLoop's E2E loop, and of the 57 releases in history 49 shipped `shiploop` while the 8 that did not shipped leaves the loop does not gate (backchain,
plan-dispatcher, adversarial-review, rubric-eval, the E2E apparatus leaves), 5 of them with no journal commit in range, so a rule on every release would have
asked an `ask-agent` or `backchain` release for a ShipLoop round it has no reason to have. The rule is also the narrowest one that still covers the case the plan
names: the 2026-10-03 onward practice is 14 ShipLoop releases of 15 with a journal commit in range, so the rule describes what the owner already does, and the
trailer exists for the one in 15 that is a four-commit patch (`92910a26`).

**First release (no earlier `Skill-Craft-Release` commit): the range is all of history up to HEAD** (`span = "HEAD"`), so a journal commit anywhere in history
or a trailer anywhere passes, and a repository with neither is refused. This repository has 57 releases, so the case only arises in a fresh clone or fixture;
`test_the_first_release_looks_at_all_of_history` pins both outcomes. A release that is output-only (no notes) or ships other leaves is not asked.

**Dry run (firm).** `plan_all` already runs before `--dry-run` returns, and every other pending-note problem is a refusal there (`release-flow.test.sh` `dry_fails`),
so the preflight is a refusal in `--dry-run` too: exit 1, the same message, nothing written (`test_a_dry_run_shows_the_refusal_and_writes_nothing`). It is
deliberately not in `plan()`: `scripts/check-release-boundary.py` calls `release.plan()` on every ordinary push, and a push with a pending ShipLoop note must not
fail CI for a missing round.

## Evidence for the scope (exported, compact)

`docs/experiments/release-preflight-20261010/history_evidence.py` (read-only; run as `python3 history_evidence.py <repo>`) prints
`docs/experiments/release-preflight-20261010/history-evidence.txt`. For each release it takes the range the script would see with HEAD at that release's first
parent. Counts at base `658ff4e3` (firm, recomputed once):

| Question | Count |
|---|---|
| Releases in history | 57 |
| Ship `shiploop`, with a journal commit in range / without | 24 / 25 |
| Do not ship `shiploop`, with a journal commit in range / without | 3 / 5 |
| ShipLoop releases since the journal file existed (2026-09-26), without a journal commit | 15 of 39 |
| ShipLoop releases since 2026-10-03, without a journal commit | 1 of 15 (`92910a26`, 4 commits) |

Reading: the early burst (2026-09-26 and 27, ranges of 2 to 8 commits) is where a rule would have bitten; since the loop became routine only a small patch
release lacks a round, which is the case the trailer is for. The numbers count commits that touch the file, not the quality of the entry; see Open below.

## What was built

| Part | Where |
|---|---|
| One reader of the release trailer (S-12): `release_commits()` returns `[(sha, trailer value)]`; `released_versions()` now derives from it instead of a second `git log` parse | `scripts/release.py` |
| The rule | `scripts/release.py`: `E2E_LEAF`, `E2E_JOURNAL`, `NO_ROUND`, `e2e_round_missing`, called last in `plan_all` |
| Docstring paragraph and the AGENTS.md bullet "Release preflight" | `scripts/release.py`, `AGENTS.md`, one sentence in `test/README.md` |
| Suite | `test/release-preflight.test.py`, registered as `release-preflight` (core) in `test/suite_catalog.py`; pinned counts 40 core and 117 total, and the `scripts/release.py` quick-selection case now includes it, in `test/test-groups.test.py` |
| Real cut through the same entry point | `test/release-flow.test.sh` step 3b (refused as dry run and for real, checkout unchanged, then the trailer the refusal names, added with `git commit --amend`, clears it) |

## Tests, fail-first, and how they were checked

17 cases in `test/release-preflight.test.py`, each running the real `scripts/release.py` as a subprocess in a disposable repository with its own HOME,
`GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null`: refused with neither; accepted with a journal commit; accepted with a trailer; an empty and a
whitespace-only reason refused (git parses `No-E2E-Round:` as a trailer with an empty value, so this exercises the real value check); a trailer in the body, not
the final paragraph, refused; a journal commit or trailer before the last release does not count; the release commit itself does not count; another file named
`LEARNINGS.md` does not count; a journal commit merged from a side branch counts; a release shipping only `other` and an output-only release are not asked; the
first-release range; a refused dry run, an accepted dry run and a refused real run each leave HEAD and the tree untouched with the note still pending; and two
route cases that read the path and the trailer key out of the refusal's own text, apply that fix, and run the same entry point again to see it accepted.

- **Red first (firm).** Against the unmodified `release.py`: 11 of 17 failed. 10 with `0 != 1` (the release was planned, not refused) and 1 with the plan text on
  stdout where an empty stdout was expected. The 6 that passed are the acceptance and not-asked cases, which pass trivially before the rule; they are covered by
  the mutations below.
- **Mutations (firm).** Each broke the implementation and turned the suite red, then the good file was restored: no leaf scope (2 red: the `other` release and the
  output-only release), range = all history (2 red: the before-last-release cases), empty reason accepted (11 red), any file counts (11 red), a reason never
  counts (3 red), the journal never counts (4 red), the preflight skipped (11 red). With the preflight off, `release-flow.test.sh` fails at step 3b with
  "a ShipLoop release with no E2E round must be refused".
- **Green (firm).** `release-preflight` 17 tests, `release-flow`, `release-boundary`, `release-push`, `test-groups` all exit 0 (commands and exit codes are in the
  commit report).
- **Quick tier (firm).** `bash test/run-all.sh --group quick --changed-from 658ff4e3`: 20 suites selected, 19 passed, 1 failed:
  `shiploop-status-display`, `test_every_dry_run_packet_carries_the_block_inside_the_kept_head` (`8003 not less than 8000`). It is not caused by this change:
  `skills/` is untouched between the base and this branch, it failed again alone (second run, same assertion), and a pristine `git archive` of the base fails the same
  test (`8018 not less than 8000`). The packet head holds absolute paths, so the number moves with the checkout's path length; it is the packet-diet owner's, not this task's.
- `python3 scripts/release.py --dry-run` on this worktree: "no pending notes under changes/; nothing to release", exit 0, tree unchanged (read-only plan mode; the
  apply mode was never run against the real repository).

## Deviations from the brief

1. `test/release-flow.test.sh` (existing) was legitimately broken: its step 4 cuts a release that ships `shiploop` from a commit with no journal commit and no
   trailer. The fix is the trailer on the fixture's feature commit, which is also the real-gate route test (step 3b above). No other existing test changed except the
   pinned counts and the `scripts/release.py` selection set in `test/test-groups.test.py`, which a new `release-*` suite changes by design (the quick tier selects
   suites by name stem).
2. `released_versions()` was rewritten on top of `release_commits()` (one reader of the trailer, per S-12) rather than adding a second `git log` parse. The set it
   returns is unchanged (`release-flow` step 10, a released version is never reused, still passes).
3. `test/README.md` got one paragraph about the new suite. It is the file that lists the release suites, so it was kept current rather than left stale.

## Open, deferred, not measured

- **Touching the file is the whole check (interim).** A one-character edit to `LEARNINGS.md` satisfies it, and a trailer reason is free text. That is deliberate: a
  model-judged check of an entry's quality would be the unmeasured completion the owner's rules rule out. The plan's own measure is "releases refused and
  overridden". Overrides are countable from history: `git log --format='%h %(trailers:key=No-E2E-Round,valueonly)'`. **Refusals are not recorded anywhere** (the
  message goes to stderr), so the number of refusals is unknown, not zero.
- A release that ships `shiploop` together with `shiploop-run-review` or `shiploop-e2e-audit` is asked once; releasing those two alone is not. That follows the
  scope decision above; revisit if an apparatus-only release ever ships a harness change with no round.
- Not verified: the preflight against a merge-commit history with a rewritten LEARNINGS.md (a merge that is TREESAME to the main parent hides the side
  commit under git's default history simplification; the merged-from-branch test covers the normal case only).
