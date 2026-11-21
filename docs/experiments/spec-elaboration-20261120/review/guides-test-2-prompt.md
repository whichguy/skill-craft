You reviewed the design of a small experiment and returned "fix first" with thirteen findings. Your report is
`docs/experiments/spec-elaboration-20261120/review/guides-test-review.md`; the brief you had is
`review/guides-test-prompt.md` beside it. The author has amended the design and rewritten the driver. Check the
amendment. You report; you change nothing. Read only; write no file. Be adversarial.

## What changed

- Section 40 of `docs/spec-elaboration-journal.md` (the last section; in the working tree) replaces section 39's
  arms, samples, readings, bar, outcomes and predictions.
- `docs/experiments/spec-elaboration-20261120/guides_test.py` is rewritten (`overlays`, `prepare`, `sort`, `run`,
  `collect`, `judge`, `score`, `replay`).
- `overlays/guides-cue.json` and `overlays/guides-excerpt.json` replace `overlays/guides-read.json`.
- `evidence/guides-test/replay-of-two-existing-runs.txt` is the output of `replay` on two run folders that exist.

## What to do

1. For each of your thirteen findings say `resolved`, `partly` or `not resolved`, with the evidence (`file:line`) and,
   where it is not resolved, the smallest change that would resolve it.
2. Read the rewritten driver line by line against the harness code it calls (`test/shiploop_e2e/run.py`,
   `run_choice.py`, `metrics.py`, `overlay.py`, `brownfield.py`) and against ShipLoop's records as section 40 describes
   them. Report anything that would break at run time or mislead: in the launch argv, the stop loop, the choice of
   run, the snapshot from the commit and from the bind tree, the pairing of tool calls with their results for both
   hosts, the classification of endings, the blind copies, the judging call into `grade.py`, the scoring, the sort.
3. Judge what the amendment introduced: the three arms and whether C is a fair control for X; the cue's wording; the
   choice of two guide sections and the claim about the packet's size and the host's limit; the sort's instruction
   text (`SORT_PROMPT`) and whether it will sort these 21 items usefully for this base; the rule of "at least 4 items,
   net at least 4" against the item-level noise the section reports; the blind reading for added capability; the
   seven predictions.
4. Say whether step 0 (two sorter sessions) and step 1 (one set of three Sol runs) are worth running as they stand.

You may run read-only commands (git, grep, python that only reads). Do not run the harness, a model, or anything that
starts a server or writes a file. Do not open anything under the user's home configuration folders.

## What to return

First a table of your thirteen findings with their status. Then new findings, most serious first, each with a
severity (P1: the result would be wrong or unreadable; P2: it weakens the result; P3: minor), the evidence and a
change in one or two sentences. Then one line, exactly one of: `VERDICT: RUN STEP 0 AND STEP 1`, `VERDICT: FIX FIRST`
(list what must be fixed) or `VERDICT: DO NOT RUN` (say why).
