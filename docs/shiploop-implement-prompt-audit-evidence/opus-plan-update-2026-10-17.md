# Opus review of the generic lifecycle plan update

Read-only consultation, 2026-10-17 (America/Los_Angeles). The coordinator supplied the immutable prior plan, the proposed change brief and retained-run audit. This is advice on that proposal, not a review of implemented code.

```json
{
  "exit": 0,
  "model_used": "opus",
  "served_model": "claude-opus-5-5",
  "fallback": false,
  "model_verification": "verified",
  "effort": "xhigh",
  "profile": "consult"
}
```

Expected current Opus release was checked against [Anthropic’s Opus page](https://www.anthropic.com/claude/opus); the runner served `claude-opus-5-5`.

Original envelope: `/tmp/shiploop-plan-update-20261017/opus.json` (SHA256 `016a3c46d7b42c2b49087caee6bdb82fccee636a7fbaf4f75b75cdadc00f1ef4`). Transcript directory: `/tmp/shiploop-plan-update-20261017/transcript`.

Brief: `/tmp/shiploop-plan-update-20261017/review-brief.md`. Prior plan: `/tmp/shiploop-plan-update-20261017/plan-before.md`. The current plan’s §10.3 owns the disposition; the answer below is preserved verbatim.

---

I reviewed this read-only: no edits, no tests run, no models launched, no Salesforce contact. I checked every claim below against the source at HEAD 17ddec36 and the retained run evidence.

Shorthand: `S=skills/shiploop/scripts`, `RUN=…/salesforce-chess-int-802e29-audit-20261018T0040Z/evidence/.shiploop-runs/work-20261017-204618-70708c`.

## 1. Goal
Change the implement-step plan so each step has a proof it can actually pass at that step, and acceptance procedures are valid before anyone runs them. All of it must stay generic, keep D1–D10, and add no new schema, platform dependency or launch.

## 2. Material issues

**M1. Revision 3 fixes `test_cases`, but the impossible procedure was never a test case.**
- **Where it actually lived:** test-strategy wrote it into architecture.md `## Real-boundary checks`, owned by release-verify and marked "Not in the default suite" (`RUN/worktree/docs/shiploop/architecture.md:78, 97-104`).
- **Why it can't be a test case:**
  - `check_test_cases` requires case IDs to equal the item's focused-command IDs in both directions (`S/shiploop_expectations.py:460-470`).
  - Test-strategy item 11 requires browser cases to be opt-in, outside the default command (`S/shiploop_prompts.py:929-930`).
  - So the run's test cases cover C1–C11 (Apex) only, and the test-spec result says the board "cannot be played here" (`RUN/run/results/nav-028b79b1….md:16`). Reviewing test cases in test-spec would never have seen the bad sequence.
- **Why the existing review condition missed it:** the first entry of `_REVIEW_FOCUS_ITEMS` asks whether a step "cannot be replayed exactly" (`S/shiploop_prompts.py:685`). The promotion sequence was perfectly replayable; it was just illegal.
- **Access was knowable at planning:** the recorded grant ruled out a permission set (`RUN/worktree/docs/shiploop/environment.md:212-213`), while the platform card says visibility needs one (`references/platforms/salesforce.md:52-54`).
- **Schema answer:** yes, it fits without a big schema, but only as prose. `normalise_test_cases` refuses any key outside `TEST_CASE_KEYS` (`:418`). Procedure elements go in `oracle`/`red`/`green` text, or in the real-boundary check's procedure text.
- **Fix:** add one domain-neutral condition to `_REVIEW_FOCUS_ITEMS`. It is a single source, so it reaches the spec and test-strategy duties through `_duty_focus` and also `PLANNING_REVIEW_FOCUS`. Suggested wording: "an ordered procedure with an action that is impossible in the state the earlier actions leave, or whose actor cannot reach its start under the recorded authority: walk it from its stated start, note the visible state after each action, replay it through an existing local check where one exists, and record an unreachable start as an open item now." In revision 3, change "test-spec/Improve" to "test-strategy and its Improve".
- **Validation:**
  - A hermetic test that the condition appears in all three consumers.
  - A test that a test case with an extra `procedure` key is still refused, which pins "no schema growth".

**M2. The S1 failure comes back unless every "run every recorded check" text is replaced.**
- **Root cause:** implement runs the item's `suite: check` rows after every step. The C12 grep of board files was the only check row (`RUN/run/results/nav-fbfbbd6d….md:14`).
- **That rule appears in six places:**
  - implement duty 3 (`S/shiploop_prompts.py:1205`);
  - the stage's done_when (`S/shiploop_stage_spec.py:363`) and its test text (`:369`);
  - `REPEAT["implement"]` (`S/shiploop_loops.py:98-99`);
  - the step Improve focus, which ends "rerun the step's recorded check commands" (`S/shiploop_prompts.py:2269-2273`);
  - `stage_commands`: "every item stage runs every command" (`S/shiploop_test_loop.py:217`).
- **What the plan misses:** it replaces some of these, but Method 4's "relevant checks" and the Improve focus's closing rerun line survive. Item check rows also stay mandatory under `_check_check_suite` (`S/shiploop_expectations.py:397`), so C12-style rows will keep existing.
- **Fix:** state outright: "In implement and its step Improve, ShipLoop requires only the step's Proof; the item's check rows run at test and verify." List all six sites in §5.
- **Validation:** a fixture item with a check row naming a file only S3 creates. Assert that S1's packet, contract and Improve focus neither list that row nor say "recorded check commands".

**M3. Revisions 1 and 2 together leave no valid proof on targets that can only run remotely.**
- **The run:** every Apex check that executes behaviour is `sf project deploy start … && sf apex run test …` (`RUN/worktree/docs/shiploop/environment.md:52-122`). It runs against an org that already holds unrelated `Chess` metadata (`:210`).
- **The conflict:** revision 2 keeps shared remote state and doesn't trust dry-run. That leaves only `ls`/grep checks, which revision 1 calls vacuous. A correct engine step then either blocks or gets a vacuous check.
- **"Read-only" today means something narrower:** `expectations.run` only compares local `git status` before and after (`:498-563`).
  - It cannot see remote effects, so "changes no remote system" is not something the script checks. The plan must say that.
  - It flags tool files that aren't git-ignored; the run's `.sf` tracking files ended up in history (`environment.md:139`).
  - Its 60 s timeout (`:76`) can't hold a deploy plus test; the test loop allows 600 s (`S/shiploop_test_loop.py:83`).
- **Fix:**
  - A step proof may use exactly the execution route and authority the item's recorded test commands already use, and nothing wider: no release, visibility, permission or data actions.
  - Where no authorized route can run the behaviour, step-plan words that step's criteria at what it can observe, and assigns the behaviour criterion to the step that can run it. It is never left as an "unconfirmed current" criterion.
  - "Declared disposable artifacts" means git-ignored paths, which need no new field.
  - Run the proof with the test-loop time budget and keep the git-status comparison.
- **Validation (hermetic):**
  - A check that writes an ignored file is accepted.
  - A check that writes an untracked, non-ignored file is refused, naming the file.
  - A step case with a remote-route proof renders its authority line and is not refused on its command text.

**M4. Vacuous success is the model's natural repair, and no script sees it.**
- **Evidence:** the rejected S1 result proposed "runs the C12 grep only when slChessBoard.html exists" (`nav-fbfbbd6d….md:14`).
- **Why the gate can't catch it:** once per-step paths are optional (D3), the step-plan gate can't cross-check later steps' new paths either. Revision 1's "non-vacuous probe" must be labelled reviewer-judged.
- **Minimum fix:** add to the step-plan Improve condition: "a check that passes when what it proves is absent (an existence guard, an ignored exit status, a skip)".
- **Optional, needs owner OK:** record the proof's exit code on the step-entry tree, which revision 4 already introduces as the diff base. Do it only for local routes. Show "the Proof also exited 0 before this step; name what it now establishes" in the Improve handoff as a prompt, not a gate, because refactor steps legitimately pass beforehand.
- **Validation:** `test ! -e b || grep -q x b` on a fixture produces that line; a real red-to-green proof does not.

**M5. Per-step Improve edits code after the proof is accepted, and nothing reruns the proof.**
- **The gap:** the focus tells the Improve child to fix and commit (`S/shiploop_prompts.py:2245-2274`). The step proof runs only at implement complete (plan §2.2).
- **Consequence:** an Improve regression makes S1's acceptance stale. S2's proof then fails, S2 looks impossible, and the revise lands on the wrong step.
- **Precedent:** the end-of-work Improve already reruns recorded commands when `review_changes` reports a changed tree (`S/shiploop_improve_changes.py:13-15, 65-85`).
- **Fix:** apply the same rule to a step's Improve: if the tree changed, rerun that step's proof before import.
- **Validation:** a real-CLI case in `shiploop-test-loop`: an Improve commit that breaks the proof is refused; an unchanged tree reruns nothing.

**M6. Under D4, the head size becomes a hard gate.**
- **What revision 4 retires:** keeping the loop last rules out the previous plan's §8(c), the head clause of T10, and the prior Opus head ordering. Say so explicitly.
- **Why the loop is at risk:** the head's protected lines end with the loop command (`S/shiploop_navigator.py:1669`), and only the consumer lines can be dropped (`:1672-1674`). §8 itself predicts a code step's head passes 20,000 characters, which is what the host would cut.
- **Fix:** T16 asserts, for every step case, that the printed head is at most 20,000 characters with both the `INVOKE /until-loop` block and `HEAD_END` inside it.
- **If it fails, two levers remain:**
  - move the status block and narrative to the file;
  - print Code craft as rule titles plus its locator, with the full text in the file.
  
  The second only works if "Code craft choices retained" and "keep all guides in full" mean "in full in the file". That needs an owner ruling.

## 3. Minor nits
- Revision 5: "state-version compatibility explicit" should read "a v6 state is refused with the version message; no migration" (`S/shiploop_navigator.py:55`, one supported version).
- done_when 1, "evidence observed after the last change", is reviewer-judged, not script-checked. Say so.
- "Accepted deps": the inline checkout holds every earlier step. Say the proof may rely only on declared deps, so it survives the deferred chain route.
- D3: the Improve focus's "fix, within those paths" and "a file changed outside the step's paths" (`:2245-2251`) amount to a path fence in review. Rewrite them in terms of item paths plus the diff base.
- The before/after examples should include one example labelled wrong (an existence-guarded proof), so they don't model vacuity.
- Update the §6 table: T2 now asserts that identical command text is accepted.
- Test-strategy's stand-in browser probe (`:925-928`) proves the tool works, not the procedure. Don't count it as validation.

## 4. Open unknowns
- Owner ruling: does the run's "this run only, non-destructive deploy" grant cover test execution for a step proof on a remote-only target?
- Whether a `loop-terminal` refusal reprints the `/until-loop` invocation. That decides whether a cut head costs one round trip or stalls the step.
- The measured implement head size on a code step. It has still not been measured.
- Whether tool artifacts such as `.sf/` are git-ignored in typical projects. M3's definition depends on it.

## 5. If I were implementing tomorrow
1. Write the M2 sentence and its six-site list into §5. This is the actual fix for the S1 failure.
2. Write the M3 route-and-authority rule, define "disposable" as git-ignored, and state plainly that remote effects are not script-checked.
3. Add the one `_REVIEW_FOCUS_ITEMS` condition (M1) and the step-plan vacuity condition (M4). Move revision 3's target from test-spec to test-strategy.
4. Add the proof rerun after a step's Improve when the tree changed (M5).
5. Make T16 the head-budget gate (M6) and get the owner's ruling on the levers before writing guidance text.
6. In revision 6, add a no-model replay fixture built from this run's recorded replanned step plan. It should assert that the head, file, Improve handoff and contract name the same step and proof. State that model behaviour (non-vacuous proofs, legal procedures) stays unqualified until the paired pilot.
