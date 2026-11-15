# Backchain value study: results (2026-11-15)

The owner asked "whether Backchain is as effective with the most recent models or it's not nearly as valuable", on
Grok 4.6 xhigh, GPT Sol 6.1 medium and Sonnet 5.5 high. This file reports the study registered in
[PROTOCOL.md](PROTOCOL.md) (amendments A1-A4 included), by the rule fixed there before any attempt ran. Readings that
the rule does not cover are kept on their own lines below and rescore nothing.

## Answer

On these 10 planning cases, Backchain 0.7.0 does not make better plans than the same model without it, on any of
the three models. All three readings are **no meaningful edge**: each 95% interval lies wholly below the owner's
margin δ = 5. Backchain costs 10-15 times the processed tokens and 2-3 times the wall time.

| Model | Pairs | Quality Δ, Backchain minus no skill [95%] | Reading | Tokens Δ per case (Backchain higher in) | Seconds Δ per case |
|---|---|---|---|---|---|
| Grok 4.6 xhigh | 10 | +0.7 [−0.6, +2.0] | no meaningful edge | +2,333,036 (10 of 10) | +252 |
| Sol 6.1 medium | 10 | +0.5 [−3.4, +4.8] | no meaningful edge (high end +4.8) | +965,947 (10 of 10) | +128 |
| Sonnet 5.5 high | 10 | −0.2 [−1.3, +1.1] | no meaningful edge | +985,952 (10 of 10) | +87 |

Quality is the blind Opus grade, in points out of 100, averaged over 2 passes; the difference is taken per case and
its mean and 95% percentile bootstrap interval over the 10 cases (`cohort.py` `bootstrap`, seeded per call).

## What ran

- **Freeze**: 2026-11-15 13:09:52 PST, before the first study attempt. Backchain and its bundled Until Loop came from
  b0285785374570c88f534480cf361778030018ac (Backchain 0.7.0). Frozen file digests are in
  [evidence/freeze.json](evidence/freeze.json); `value.py` (8fa5b570…) and `PROTOCOL.md` (1c191d6d…) still match them
  at this commit.
- **Attempts**: 60 (10 cases × 2 arms × 3 models), one per cell, 13:10-15:05 PST, three model lanes side by side.
  0 contaminated, 0 infrastructure failures, so nothing was rerun or dropped.
- **Hosts**: grok 1.0.77 (50ca579fa996) with grok-4.6 at `xhigh`; codex-cli 0.169.0 with gpt-6.1-sol at `medium`;
  Claude Code 2.1.325 serving claude-sonnet-5-5 at `high` (read from each attempt's init event). Grok and Claude ran
  with `bypassPermissions`, Codex with full access (A2). The Claude subjects loaded only the built-in `cc-plugin-*`
  plugins, and no skill named like Backchain, skill-craft or Until Loop was visible to them in either arm.
- **Grading**: 120 grades, all served by Opus at medium effort with no fallback, 0 malformed. Grading began at 13:38
  while the Grok and Sol lanes were still running; the grader sees no arm, model or run record, and each grade is
  written once (`grade_one` skips a graded attempt), so the order changes nothing.

## Secondary outcomes

| | Grok BC | Grok none | Sol BC | Sol none | Sonnet BC | Sonnet none |
|---|---|---|---|---|---|---|
| Mean score | 92.2 | 91.5 | 96.1 | 95.6 | 93.8 | 94.0 |
| Structurally valid plans (released `check`) | 10 | 10 | 10 | 10 | 10 | 9 |
| Final status complete | 9 | 9 | 7 | 9 | 9 | 7 |
| Critical criterion missed in both passes | 1 | 1 | 0 | 0 | 1 | 1 |
| Mechanical keys, 4 former held-out cases (descriptive) | 32/34 | 29/34 | 28/34 | 31/34 | 27/34 | 27/34 |
| Median processed tokens | 2,555,857 | 171,178 | 1,034,517 | 95,640 | 1,029,779 | 99,844 |
| Median fresh input tokens | 130,538 | 30,922 | 76,519 | 10,892 | 74,528 | 16,076 |
| Median cached input tokens | 2,372,480 | 111,360 | 952,704 | 80,704 | 946,382 | 79,974 |
| Median output tokens | 33,106 | 16,388 | 6,556 | 2,894 | 12,676 | 4,254 |
| Median seconds | 460 | 198 | 205 | 83 | 105 | 32 |

- Grader pass-to-pass difference, mean per attempt: Grok 1.47, Sol 1.45, Sonnet 1.61 points.
- Every critical miss is `store-split-from-docs` on orders-cancel-rpc, and on Grok and Sonnet both arms missed it.
- Fresh input counts uncached input plus cache writes (Claude, Grok) or input minus cache reads (Codex), following
  `value.py` `session_tokens`. Most of Backchain's extra cost is cached input (12-21×); fresh input is 4-7× and
  output 2-3×.
- Wall time was measured on a machine shared with other sessions (load average 7 to 170 during the run), so the
  seconds are a rough guide; token counts do not depend on load.

## Per case (Backchain minus no skill)

| Case | Grok | Sol | Sonnet |
|---|---|---|---|
| billing-late-fee | +3.3 | 0 | 0 |
| bounded-source-edge-repair | +3.6 | 0 | 0 |
| independent-inspection-scopes | 0 | 0 | −3.8 |
| known-external-approval-blocker | +3.8 | 0 | 0 |
| legacy-draft-discovers-mapping | −1.8 | +16.1 | −1.8 |
| library-reminders | 0 | 0 | +3.6 |
| missing-normative-redaction-source | +1.9 | 0 | −1.9 |
| orders-cancel-rpc | −1.7 | −10.0 | 0 |
| revenue-export-lineage | 0 | −7.1 | 0 |
| stale-build-receipt-identity | −1.9 | +5.8 | +1.9 |

14 of the 30 pairs tie exactly. Only Sol has differences beyond 5 points, two each way (+16.1 and +5.8; −10.0 and
−7.1).

## Readings outside the registered rule (each on its own line; none rescores a case)

- **Ceiling.** Both arms score 92-96 on average. These cases, built to tell Backchain versions apart, leave current
  models little room, so a large edge could not have shown here. That is a property of the case set as much as of
  Backchain.
- **orders-cancel-rpc on Sol.** Backchain stopped incomplete and named both gaps, the bundled S2 and the frozen S3
  confirmation, which owner decision D-B (PROTOCOL.md, study change 2) counts as correct. The grader still marked
  `terminal-disposition` and `dependency-logic` partial in both passes and two more criteria partial in pass 2 (90
  against the no-skill plan's 100). Part of Sol's −10 there is the grader not fully crediting the allowed stop.
- **A naming prime in the no-skill arm, seen on Grok.** Every workspace directory was named `backchain-cohort-…`
  (cohort.py's temporary-directory prefix), and the caller packets of the caller cases keep
  `"interface": "backchain-caller/v1"`. Grok's no-skill subject reasoned in backchaining terms in 4 of its 10
  attempts ("reframed as a backward-chaining", "This follows a backchain"). The no-skill reasoning of Sol and
  Sonnet never does. No no-skill subject read a Backchain file or ran its toolkit (A3's contamination rule, 0 of
  30). A rerun should rename the directory and drop the field from the no-skill packet.
- **What the cost buys.** Backchain's plans were valid 30 of 30 against 29 of 30, and its stops and completions came
  out even on the whole (25 complete against 25). On these cases the extra tokens buy no measurable plan quality.

## What it does not establish

- Downstream value: whether a Backchain plan changes what gets built (plans were graded, not executed).
- Harder cases than these 10, where unaided models fail more often.
- Models or efforts other than the three above, and Backchain inside ShipLoop, where the host plans with ShipLoop's
  own guide either way.

## Evidence

- [evidence/analysis.json](evidence/analysis.json) and [evidence/analysis.md](evidence/analysis.md): `value.py
  analyze` output, per model, per case and per attempt.
- [evidence/attempts.json](evidence/attempts.json): every attempt's summary (plan check, final record, keys, cost,
  contamination flag).
- [evidence/plans.json](evidence/plans.json): each attempt's final plan and final record, so the grading can be
  redone from the repository alone.
- [evidence/grades.json](evidence/grades.json): both blind passes for every attempt, with per-criterion grades,
  quotes and the grader's reported model, effort and fallback.
- [evidence/extras.json](evidence/extras.json): the cost by token class, the per-case table, grader identity counts
  and final statuses above.
- [evidence/pilots.json](evidence/pilots.json): the two harness pilots' attempt summaries, which A1-A4 cite (not
  analysed).
- [evidence/freeze.json](evidence/freeze.json) and [evidence/MANIFEST.json](evidence/MANIFEST.json): the freeze record
  and the sha256 of every evidence file.
- Raw event streams, Backchain run directories and grader replies stay in the private results directory
  `backchain/results/backchain-value-20261115/` (22 MB).
