# Advisors final: ShipLoop Improve schedule proposal (2026-10-25)

**Run:** `20261025T211947Z-fadb`.
- **Pass 1:** 2 of 4 seats answered (Astra at max, Kimi at its persona default). Opus hit its 100-turn limit before
  answering. Grok refused `--effort max` (its highest level is `xhigh`; the host's flag error).
- **Pass 2:** 4 of 4 answered, at `xhigh` with 200 turns.
- **Independence caveat:** Opus and Grok had no pass-1 position, so their pass 2 is a check of the other two seats'
  claims against code and records, not an independent first read.
- Every seat checked claims in the repository (HEAD 49aebb77) and the run folders; no seat edited anything.
- **Convergence: converged** on every proposal's disposition. Two wording points stay open (D2, D3).

## Agreements, with dispositions

| Proposal | Disposition | Agreed rule |
|---|---|---|
| P1 pass-log edit count | **Keep, telemetry only; re-specified** | Record the content identity of the candidate result under review at bind and after each pass. That is the in-place inbox result, not `<action>-final-result.md`, which appears only at the parent return. Use the frozen producer result as the baseline. Record `tree_changed`, `result_changed` and `edited` separately, and missing evidence as `unknown`, not unchanged. Record separately whether the accepted result differs from the producer result: pass activity is not net change. `metrics.improve_reviews` needs its own change. It never reads `passes.md`, and it times a review as last note minus first note, so a one-pass review reports 0 s; time from bind to import instead. **The stop threshold does not change** (D1). |
| P2 replay of derived results | **Keep, rewritten** | It must validate each transition under the spec's rules, not just recompute a final state, and it must cover cases the review itself adds or changes. A helper that applies inputs without checking they are permitted is not validation, and the product under test is not the only authority for its own expected result. Name the rule for each decisive transition. Record the case, method, intermediate states and result, plus whether the evidence is new, reused or unresolved. Reuse a valid replay across the five planning reviews. `NOT-REPLAYED: <reason>` is an honest exit that does not satisfy the obligation. No stack-flavoured examples ("moves"). |
| P3 test-spec re-review after a send-back | **Change: no skip, a narrower re-review** | After a send-back, review the changed, added and dropped cases, the cases that depend on them, and whether previously accepted requirements are preserved. Skip only when a script shows the reviewed case contract and its premises unchanged. Kimi's row diff against `spec_before` is that script's input, not the whole rule. Implementation: the current predicate is "first item or any item with a send-back", so deleting the send-back clause alone still re-reviews W1. |
| P4 implement-step trigger (IMP-4) | **Drop as a schedule; shadow mode** | Review each changed implement action. Each `passes.md` records "would skip under IMP-4" and why, while the review still runs. Adopt one cut now: reuse a completed review when a reissued step's candidate (its diff from the step-entry snapshot, not the cumulative lint scope), its contract and its evidence are unchanged. Specify the ask-agent route, which builds every step in one action. Re-decide only after another multi-step run, preferably in another domain. |
| P5 surviving mutants | **Change: disposition at the test stage, audit at the end** | Before accepting an item, require an evidence-backed disposition for each in-scope surviving mutant: killed by a new behavioural test (with a rerun as execution evidence), or equivalent under the contract, outside product scope, or not exercisable by this runner. This is not a 100% kill rate. A change to the disposition text alone is rechecked without rerunning valid executions. The end-of-work review reconciles the dispositions against the final candidate. Pilot it with the cost measured. Strike "remove weak-assertion hunting from test-spec": that focus item made most of test-spec's edits. |
| P6 spec review | **Keep** | The corrected count is 10 edited passes: 2 DEFECT, 7 STRENGTHEN, 1 POLISH, one of the DEFECTs being a repair of wording an earlier pass of the same review introduced. Drop "4.6 min per STRENGTHEN" as a price. Account in three buckets (producer defect, strengthen, repair of a review-introduced defect). On later runs, record whether each STRENGTHEN prevented a downstream defect or send-back. |

## Additions the proposal missed

1. **Net value, not only finds.**
   - Count defects a review introduces beside those it finds (Opus, from Codex).
   - Run 5b's test-strategy review added TC_28 with its illegal line and ratified it with a no-legality helper
     (`test-strategy-edacefd5/reviews/review-1.md`, `checks.md`; `oracle_replay.py` "No legality"). That cost the
     W1 send-back and a deploy.
   - The table books test-strategy as 3 DEFECT finds with no debit.
2. **Result-only check evidence is lost (Codex).** `_improve_pass` replaces `checks.md` with the producer-check
   summary whenever the git tree is unchanged, so a result-only review keeps "producer checks: none recorded". The
   rule: preserve authored check evidence, and bind it to the result's content identity. Without this, P2's
   recorded replays would not survive the callback. This one changes behaviour, so measure it apart from P1.
3. **A stale planning hand-off line (Codex, Grok).** "The two existing qualifying reviews"
   (`shiploop_navigator.py`, planning experiment exit) contradicts the one-trivial-pass contract. Fix it for
   consistency; no saving is claimed.
4. **A candidate new trigger, n=1.** Review a newly introduced, unevidenced runtime or oracle premise on a later item.
   Run 5b's W2 send-back, a wrong exception assumption in a plan that got no review, is the only case. Log "would
   review" before scheduling it.
5. **The end-of-work review is not guaranteed.** It runs only when no work items remain, and run 3 never reached
   it. No rule may rely on it as the only catcher.
6. **The missing counterfactual.** An edit-free review is not proof of no value. Only prospective would-skip and
   would-review logging plus a downstream-defect counter can price what P3 and P4 remove.

## Disagreements

- **D1, P1 and the stop rule.**
  - *Type:* mechanism.
  - *Positions:* Kimi (pass 1) said `unchanged_first_pass` is tree-only and must count result edits, or result-only
    edits close a review wrongly. Opus, Grok and Codex rejected that.
  - *Decisive criterion:* the code. With `IMPROVE_TRIVIAL_REVIEWS = 1`, a trivial first pass completes on the ordinary
    streak (`until_loop_ephemeral.py`), and the flag is written only when the streak is below the requirement. So it
    never decides anything. The real stop is the model's trivial/non-trivial label, and run 5b's result-only
    test-spec review took a second pass because pass 1 was labelled non-trivial.
  - *Resolution:* P1 stays telemetry-only; the threshold is untouched (owner decision 2026-10-20). Kimi revised to
    "audit the detection paths". The flag and the git-only restart gate are dead code under this setting, and
    removing them is cleanup with no measured gain.
- **D2, P2 and scripts.**
  - *Type:* method.
  - *Positions:* Kimi wants mechanical cases recomputed by a short script, with its output pasted. Grok calls script
    output the failure mode, since run 5b's script recomputed an illegal line.
  - *Decisive criterion:* the evidence. The failing replay was a script.
  - *Resolution:* a script is allowed only as a validator that checks the permission rules. The record names which
    rules the method checks, and pasted output alone does not satisfy the item.
- **D3, where P2's wording goes.**
  - *Type:* placement.
  - *Positions:* the proposal appends to focus item 1. Grok says amend the existing procedure walk instead.
  - *Decisive criterion:* the shared constant `shiploop_prompts.PROCEDURE_WALK` already asks "can each action occur
    in the state the preceding actions leave". It feeds the planning focus item and test-spec duty 4. The gap is
    that it doesn't cover derived expected results, review-introduced cases or non-validating helpers.
  - *Resolution (host):* amend `PROCEDURE_WALK` and `_PROCEDURE_ITEM`, not item 1. That is one place, printed
    everywhere the walk is.
  - *Open:* the exact wording and its head cost (more than +200 characters) await a fail-first fixture.
- **D4, P3's skip condition.** Kimi's verbatim-row rule against Codex's contract-and-premises rule. Resolved to
  Codex's rule, with Kimi's row diff as an input; Grok and Opus agree.
  - Codex's diff of run 5b's two re-reviews shows both had changed cases: TC_28 `oracle`/`green`, and TC_19
    `oracle`/`red`/`green`.
  - So both would still run, and 234 s of P3's 344 s saving disappears. P3 becomes a scope narrowing, with little
    time saved.
- **D5, P4.** Kimi (pass 1) kept the trigger with a narrower exclusion. In pass 2 Kimi flipped to shadow mode with
  reuse of unchanged reviews. Converged.
- **D6, P5's placement.** Kimi (pass 1) put it at end of work only. In pass 2 Kimi flipped to a test-stage
  disposition with an end-of-work reconciliation. Converged.

## Combined answer

**Keep Improve, and make it more selective by evidence of change, not by position.**
- **Measure correctly (P1):** count result edits, review-introduced defects and net change.
- **Make its planning check validate, not narrate (P2):** amend the procedure walk.
- **Narrow re-reviews to what changed (P3).**
- **Reuse a review whose candidate didn't change (P4's safe half).** Run the position trigger in shadow mode only.
- **Move surviving mutants to a recorded disposition at the test stage (P5).**
- **Keep the spec review (P6).**

**Expected effect.**
- Time saved now is small: P3's narrowing plus P4's reuse is a fraction of the 21.6 minutes the original P3 and P4
  pooled over three runs.
- The quality gain is the replay validation (one send-back avoided per occurrence, n=1) and survivor dispositions.
- Most of the value is measurement that makes the next schedule decision possible.
