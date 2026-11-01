---
Execute: inline
Status: built (ffea2956, e7e0bc3c); live A/B on the Codex harness (Codex Terra 6.1 high, all tools) in §3
Opened: 2026-10-31
Consumer: the owner, who sees what each planning idea of 2026-10-30 became and can veto a build; later, a session that
  changes intake, spec or step-plan prompts or gates, which reads §1 for the evidence a change must beat and §4 for the
  better tests still open
Journal: docs/shiploop-question-driven-planning-journal.md (E5-E10, findings F13-F17)
Evidence: docs/experiments/question-record-20261031/ (README results table); the live A/B under ~/e2e-runs-qr/20261031/
Follows: docs/shiploop-planning-pipeline-2026-10-30.md (the proposal, §9 experiments, §10 decisions D1-D11)
Illustrated page: https://claude.ai/artifact/S5r3siGPAJWkAEszTqDwwT (Planning Verdicts; private to the owner)
---

# Planning verdicts and the improvement plan (2026-10-31)

The owner, 2026-10-31: "Yes, exhaustively continue with experiments, evaluation and replanning, anchoring each goal in a
conclusive verdict with evidence or determining a better isolated test to aide conclusions then produce an improvement
plan and implement/test end to end." During the work: "Focus using Terra 6.1 high for now"; "we would use codex harness
with terra high for testing how the models would run"; "It should have all tools available unless we have a specific
reason"; "If Terra high is too ineffective, bump it up in thinking levels if needed"; "My preference is to improve
shiploop to handle this, but if it doesn't change then increase the thinking level".

## 0. The answer in brief

- **Built: the step-plan proof-order refusal.** Nine of the twelve implement send-backs in the saved runs are a step
  Proof that needs a test the test stage writes later (eight on Codex Terra xhigh). The duty already forbade it; models
  did it anyway. ShipLoop now refuses such a plan at step-plan, where it costs one check, not an implement Until Loop.
- **Built: a key-question ledger at intake, with a category catalog.** On Terra 6.1 the shipped intake raised about half
  of what a vague request leaves open (49% at high, 51% at xhigh); with the ledger 91% (98%). The gain reaches the spec
  (+12 points of decisions carried) with no loss of agreement. Raising effort did not do it; the prompt did.
- **Not built: the question record and everything that hung on it.** A numbered record quoted into spec carried no more
  than prose (C 0.81, A 0.79), so phase 1, the research frontier loop and the question return lose their basis.
- **Built, small:** intake's Checked-by line names the check it already ran (IN1).
- **Closed without a change:** a step-plan prompt sentence (X4): no isolated design can measure it on Terra; the gate
  above is the fix the evidence supports.

## 1. Verdict per goal

| # | Goal (source) | Test, isolated where possible | Result | Verdict |
|---|---|---|---|---|
| 1 | Catch a Proof that needs a later stage's test (SG1, D6 of the SDLC gates proposal; F9) | SG1 replay on every saved plan, two corpora; the shipped function replayed at each plan's base; live A/B on Terra high | 9 of 12 saved implement send-backs are this fault; the rule refuses 7 of the 9 and no plan that passed by the rules; live, 0 of 6 B runs lost a loop to it against 4 of 6 A runs (p 0.030) | **built** (§2.1, §3) |
| 2 | One question record from intake to spec (D1, phase 1) | X2: spec as a no-tool exercise, intake prose (A) vs the record quoted (C) vs a duty line (D); Terra high, n = 16 | acceptance 0.635 / 0.650 / 0.687; carried 0.789 / 0.807 / 0.808 | **rejected** (C - A +1.5, p 0.44) |
| 3 | Research as a question-frontier Until Loop; experiment trigger moved; question return (D3, D4, D6) | depends on 2 | no record to loop over | **closed** (prerequisite rejected) |
| 4 | No catalog at intake (D2, from Sonnet) | X1-T on Terra high and xhigh; X2b: does B's ledger reach spec; X2b-S: does it hurt Sonnet's spec | recall A 0.49 / B 0.91 (xhigh 0.51 / 0.98); spec carried 0.776 → 0.897 (p 0.013), agreement 0.65 both; on Sonnet spec carries 1.000 either way, agreement 0.59 → 0.63 | **reversed: catalog built for every subject** (§2.2) |
| 5 | Raise effort instead (the owner's fallback) | X1-T at xhigh | A +2 points (0.49 → 0.51) for 4x the reasoning | **not the lever** at intake |
| 6 | Make defaults explicit at spec (a duty line) | X2 arm D | +5 acceptance, paired p 0.008; below the 10-point bar | **not adopted** (a small, consistent gain: §4) |
| 7 | A Proof-input question at step-plan (X4) | no-tool packets; step slices on the Codex harness | packets block (64/64); the slice copies its seeded clean proof | **closed** (no measurable isolated test; goal 1 covers it) |
| 8 | Intake's Checked-by line names IN1 (D11, F11) | by construction | the script refused it unnamed | **built** (§2.3) |
| 9 | Research's written allowance (D5) | — | a limit | **the owner's** (unchanged) |
| 10 | Spike items, durable request text, glossary (D7-D9) | — | no run needed them | **deferred**, as recommended |

## 2. What was built

### 2.1 Step-plan proof-order refusal

`shiploop_item_scope.proof_order_refusal(plan, exists)` and `command_paths(command)`; the navigator runs it at
step-plan's `check` and `complete` and on an Improve child's step plan, against the execution checkout. Rule A: a Proof
names a test-class path the base lacks that no earlier step declares (implement writes no tests; a step's test stage
writes them after its implement), unless the item is all tests. Rule B: a Proof names a path the base lacks that only a
later step declares. Paths outside the repository and absolute paths are skipped (a first version refused a script in
the run's scratch folder; the replay found it). The Checked-by line names it (+58 characters on the step-plan head,
journaled; inline 19,888 of the 20,000 cut).

### 2.2 Intake key-question ledger

Intake duty item 9 is X1's arm B item, byte for byte: a K1-K11 category catalog (`question_categories`: applies or not,
with a reason) and the `questions` ledger (id, category, question, what it changes, route, default, what it blocks). The
template prints both. The ledger is optional, as it was when measured, and checked for its shape when present: each
category once, a reason for a "no", unique Q-ids, a route of five, no placeholder; another stage may not carry it.

### 2.3 Intake's Checked-by line

It names IN1 (a summary that leaves a request sentence uncited) and the ledger check.

Tests: the Checked-by guard pairs each new phrase with its real refusal; a proof-order route test and a ledger test
(test/shiploop-callback-contract.test.py). The quick tier passed before the commit.

Shipped 2026-10-31 in skill-craft 2.26.0 / ShipLoop 1.25.0, release commit `441b1b3b`. The first cut (`b4c63c94`, over
`5919c0d5`) went stale when another session's empty learning commit `488ffbd9` reached main; the re-cut over it has the
same tree (`90b21df7`), and `release-push.py` re-ran the three checks (plugin views, marketplace packages, release
boundary) before its non-forced push. CI had passed on the source tree (runs 41221108457 on `5919c0d5`, 41226634137 on
`488ffbd9`). Hosts refreshed the same day: Claude and Grok 2.25.2 to 2.26.0, Codex 2.26.0 (a Claude session loads it on
restart); Cursor updates through its app and was not refreshed here.

## 3. Live A/B on the Codex harness

`run.py --host codex --model gpt-6.1-terra --effort high --source checkout`, all tools, hooks on; ticket-assignment and
user-listing (the brownfield cases where Terra xhigh hit the fault on 2026-10-29), 3 runs per arm per case, one lane per
port with the arms interleaved. Arm A is ShipLoop at main 3ae78af7; arm B is ffea2956 with e7e0bc3c (the first B run of
each case was built before e7e0bc3c, so its ledger was written but not stored).

| | Arm A (3ae78af7) | Arm B (the change) |
|---|---|---|
| hidden checks | 5 of 6 pass (ticket-assignment A3 paused at document, 1 of 3 checks) | 6 of 6 pass |
| runs that lost a stage loop to the proof-order fault | 4 of 6 (3 at implement, 1 at test-spec) | 0 of 6 (exact one-sided p 0.030) |
| proof-order refusals at step-plan | — | 3, each followed by an accepted plan |
| send-backs to step-plan, all causes | 5 | 1 (test-spec: one focused ID for three criteria) |
| median minutes, user-listing / ticket-assignment | 11.1 / 8.1 | 9.4 / 13.9 (no effect claimed: p 0.05 and 0.70) |
| intake ledger written | — | 6 of 6 (11 categories, 2-6 questions) |

The shipped rule replayed on arm A's 12 step plans refuses exactly the 4 that went on to the send-back and accepts the
other 8. Full table and reading: test/shiploop_e2e/LEARNINGS.md (the entry of 2026-10-31); journal E10.

## 4. Better tests for what stays open

- **The duty line at spec (goal 6).** A consistent +5 on a no-tool exercise. The test that would settle it is the live
  measure it aims at: defaulted decisions a later stage changes or a send-back blames on spec, counted from run traces.
  *Closed 2026-10-31 (owner, answer "3" to "apply the three defaults"): the stage-prompt review found no signal in 39 of 39
  outcomes (docs/experiments/prompt-template-review-20261031/README.md, section 3), so the live measure is not run. The +5 no-tool
  exercise stays the only evidence for the duty line.*
- **The proof-order fault's other form.** Two of the nine faults name no test path (`npm test`, or criteria that demand
  the test file). A replay of the criteria's Confirm-by commands against the same rule would measure whether a second
  rule pays.
  *Measured 2026-11-01 (docs/experiments/proof-coverage-replay-20261101, journal E17): it does not.*
  - *On the larger corpus, the shipped rule comes before 11 of 20 proof-order send-backs.*
  - *The registered second rule catches 3 more, but would refuse 5 plans whose Proof tests the step directly.*
  - *6 misses name the test by identifier, not path.*
  - *Each send-back costs about a minute, so no rule is added.*
  - *Superseded in part the same day (journal E18). The narrow form, for plain suite Proofs only, is built as rule C
    of the shipped refusal, for the Proof duty rather than for time.*
- **A proof-command dry run.** One baseline send-back on Terra high was a Proof with unescaped shell quotes (a
  SyntaxError before any assertion); no gate reads that today. *2026-11-01: 3 of the 35 implement send-backs in the
  saved runs are a Proof's shell quoting (`labels.jsonl` in the folder above). They are counted only; their cost was not
  measured.*
- **Subjects.** On Sonnet the catalog changes little downstream (X2b-S: spec carries every decision either way,
  agreement 0.59 → 0.63). DeepSeek flash, the E2E default, was at its monthly limit all day: re-run X1-T and X2b on it
  when it returns (the harness in the evidence folder takes a subject slug).
- **A proof-command dry run.** One baseline send-back on Terra high was a Proof with unescaped shell quotes (a
  SyntaxError before any assertion); no gate reads that today.

## 5. Unknowns

- Every intake and spec measure is a no-tool exercise; the live A/B (§3) is the tools-on check of the build, on two
  brownfield cases, with the hidden checks as the outcome.
- One judge (Opus) for the exercises; quotes are verified by script, judgements are not.
