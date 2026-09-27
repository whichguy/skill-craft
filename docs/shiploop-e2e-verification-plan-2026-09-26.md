# ShipLoop E2E verification plan (2026-09-26)

Execute: inline

Goal: use the E2E harness (`test/shiploop_e2e/`) to verify ShipLoop's own
behavior, not only the product it builds, and turn what the runs show into
generic ShipLoop fixes. Built on runs 1-5 (`test/shiploop_e2e/LEARNINGS.md`)
and commits c262451b, 9347f40a and 8c40b2fa.

## Evidence this plan starts from

- Run 5 (ShipLoop 0.35.0) passed in one session: 314 turns, $25.09, 93 min.
  Implementation took about 3 minutes of that. Planning (research 3.5, spec 8,
  test-strategy 7 min) and release planning (7 min) and product acceptance
  (4 min) dominated. Grok cut 17 tool outputs; one auto-compaction.
- Run 5's source checkout ends with one commit (the empty baseline) and every
  product and `docs/shiploop/` file untracked: the release was a working-tree
  return, and the knowledge-home commits live only on the execution branch
  (`codex/shiploop-<id>`, a Codex branch prefix on a Grok run). Whether a later
  run inherits that knowledge was never tested.
- The harness grades the product and the final state only. It cannot say where
  turns and cost went, whether ShipLoop's commands failed, or whether a second
  feature builds on the first run's spec and architecture.

## Phase 1 - harness: measure ShipLoop's behavior

1. **Timeline and metrics.** The runner stamps arrival time on every
   non-streaming host event (`timeline.jsonl`). A new `metrics.py` derives, per
   run: sessions and how each ended, turns, tokens, cost, auto-compactions,
   host truncations, ShipLoop CLI failures (non-zero `shiploop` commands),
   test runs, Improve children, keepalive decisions, and per accepted stage its
   duration, turns, tool calls and estimated cost share. Written to
   `metrics.json`, summarized in `result.json` and the printed report.
2. **Behavior facts.** `grade_shiploop` also reports the knowledge home
   (`docs/shiploop/spec.md` present in the source checkout; tracked on HEAD or
   not), the return form (commits on HEAD vs. untracked files) and the
   execution branch name. Informational until the owner decides the intended
   return behavior (see Phase 3).
3. **Progress monitor in the harness.** The scratch monitor becomes
   `test/shiploop_e2e/progress.py`, built on `metrics.py`; it never prints
   packet text or run markers.
4. **Follow-on feature case (P53).** `--continue-from <prior output>` copies
   the prior run's source checkout (with its `.git`, minus stale worktree
   records) into a new output directory and runs a follow-on case there. Case
   `battleship-scoring` (`follows: battleship`) asks for a small, material
   feature: name the sunk ship, count shots and hits, show accuracy. Its checks:
   - regression: every check of the case it follows;
   - feature: the new API fields and page text;
   - retention (with `$PRIOR_WORK` pointing at the prior checkout): every
     prior tracked or product file still exists, no dependencies added, the
     passing test count grew, the living spec keeps every prior requirement ID
     and gains new ones.
   The report compares turns and cost with the prior run.
5. Self-tests for all of the above (no model), registered suite unchanged.

## Phase 2 - runs

6. Run 6: `battleship`, marketplace 1.4.0 (ShipLoop 0.37.0), fresh directory.
7. Run 6b: `battleship-scoring --continue-from <run 6>`.
   After each: learnings entry + detailed commit, read the last three commits.

## Phase 3 - ShipLoop fixes (generic, from run evidence)

Each item is re-verified against current code before work; items another
session already fixed are dropped.

8. Right-size small local work: skill stages only when the repository has a
   skill package (script-proven), a single work item skips the separate
   integrate stage, and planning/release packets scale to the request.
9. Return and knowledge: the owner decides whether a working-tree return
   should leave the product and `docs/shiploop/` committed on the source branch;
   the execution branch prefix follows the host (not `codex/` on Grok).
10. Improve child start as one ShipLoop command (receipt directory at bind).
11. Keepalive observe binds only to runs this session started.
12. Whatever runs 6/6b show (retention gaps, failed commands, truncations).

Release each shipped fix (`scripts/release.py`, push, refresh hosts), then
rerun through the marketplace gate.
