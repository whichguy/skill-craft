# D-step-work: implement, test, document (reviewed 2026-10-31)

**A gap in the evidence, which affects every group.** `stage_health.py` counts only `complete` callbacks. Since
8bf10c64 (2026-10-29), `shiploop check` has been its own verb, so its refusals are missing from the `chk` column:
113 refused checks across the 96 traces (step-plan 53, test 52, document 5, improve 3). With them, test has 86
refusals, not 34. My analysis scripts are offline and read only; they are in the session scratchpad and are not
retained.

### implement — verdict: no-change
Signals: 85 runs; 251 packets for 229 actions; 11 real refusals and 6 check-only ones (and 0 of 19 `check` calls);
23 send-backs and 2 blocked; 310 minutes (median 1.5).

Findings:
- **The high packet count comes from the loop's structure, not from the prompt.**
  - 22 of the 251 packets are a second trace row for the same action, written right after the previous stage's
    accepted `complete`.
  - In the 19 runs from the era before per-step iteration (consecutive implement actions, before 2.23.0 / 1.22.0), the
    traces hold 100 implement actions against 30 test actions.
  - In the other 66 runs it is 129 against 110. The excess is about the number of send-back reruns.
  - Evidence: trace.jsonl of all runs. Live in current code: n/a.
- **17 of the 23 send-backs are the proof-order fault.** The step's Proof runs a test file that the later test stage
  writes (for example ~/e2e-runs-qr/20261031/A-user-listing-s1, bf-codex-r1-ticket-assignment,
  ds-flash-978478-battleship).
  - Implement handled every case correctly: it sent the step back and never edited the Proof.
  - ffea2956 fixed this upstream with the step-plan `proof_order_refusal`. The live A/B (45f9752e): 4 of 6 arm A runs
    lost a loop to the fault, against 0 of 6 in arm B (p 0.030).
  - Two of the 17 (bf-codex-r1-user-listing) name no test path (`npm test`). That form is still open
    (docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md §4).
  - Live in current code: the refusal is live; the no-path form is open.
- **5 send-backs are broken Proof commands, and 1 is a genuine failure.** The broken commands:
  - unescaped shell quotes (A-ticket-assignment-s2, 10-31);
  - `.sort()` checked against declaration order (gate-2132 grok-web/battleship);
  - BSD `grep -P` (trace-verify-4fd9f1);
  - `fs.rmSync(force:1)` (bf-codex-r2-ticket-escalation);
  - a permission assignment that fails when repeated (shiploop-salesforce-battleship).

  Duty item 6 routed each one correctly. The fix belongs at step-plan: it is §4's "proof-command dry run". The genuine
  failure is gym-published-baseline-01. Live in current code: yes, upstream.
- **Refusals.**
  - 7 of the 17 were the 1,200-character `decisions` cap, retired by 232689c5. Live in current code: no.
  - 3 were step-proof failures: the gate working as intended.
  - The rest are rare slips: 2 `not_covered` shape errors (last on 10-27), 2 missing result files, 2 wrapper or fence
    slips, and 1 spec-mark refusal (see document).

Proposal: none for the implement prompt. Hand the two open items (the no-path form and the proof dry run) to the
step-plan reviewer.
Gain / risk: n/a.
History respected: ffea2956, 45f9752e, 232689c5, and 12151c49 (whose duty line alone did not stop the fault).

### test — verdict: improve
Signals: 82 runs; 143 packets; 86 refusals (1 real, 33 check-only `complete`, 52 `check`); 4 send-backs; 240 minutes
(median 1.2).

Findings:
- **51 of the 86 refusals are the mutation check's per-survivor refusal, and that gate works.**
  - They span 34 runs and 46 actions. 41 actions were resolved after one refusal.
  - From first refusal to acceptance took a median 0.5 minutes, 50 minutes in all.
  - Of 99 distinct survivors, 40 got a disposition and 59 never reappeared (killed by stronger tests).
  - This is working as designed (3f8a0a7b; E7 §3c).
- **The packet misstates this gate.**
  - `_CHECK_TEXT["test-loop"]` (shiploop_navigator.py, unchanged since 3c99addc on 10-11) says ShipLoop "refuses when
    the focused tests catch none".
  - Since 3f8a0a7b (10-25), the gate refuses every surviving mutant that has no killing test and no
    `mutant_dispositions` entry.
  - All 51 refusals are the per-survivor form; none is the zero-kill form the packet describes.
  - The wording appears verbatim in the 10-31 packet
    ~/e2e-runs-qr/20261031/B-user-listing-s1/.shiploop-runs/work-20261031-153236-aa17d8/run/packets/sent/21c278c075ad17fc.md.
    references/test-loop.md says the same.
  - Live in current code: yes.
- **17 of the 86 refuse an empty `red_na` or `retired_tests` list** ("red_na is a non-empty list of {id, reason, ...}").
  - They come from 16 runs, on DeepSeek flash and Codex Terra; the latest was on 10-31 in arm B, which runs current
    code.
  - ~/e2e-runs-qr/20261031/B-user-listing-s1/events.jsonl shows the model writing `'red_na':[]`, then popping both
    keys after the refusal.
  - `_records` (from d7388043, which gives no reason) requires a non-empty list, while implement's `not_covered`
    accepts `[]`.
  - Live in current code: yes.
- **The remaining 18 are other gates working, or rare slips.**
  - 5 missing result files, 4 base-run refusals and 4 test-run refusals: gates working.
  - 4 implement fields copied into a test result (the last on 10-29), and 1 loop still active.

Proposal:
- **(a) Mechanism.** In the `_RECORD_FIELDS` loop, treat an empty list as absent for `red_na` and `retired_tests`. This
  adds no prompt text.
- **(b) Wording, about the same length.** Make `"test-loop"` read: "…then mutates a sample of the changed product lines
  and refuses each surviving mutant that no focused test kills and no `mutant_dispositions` entry explains (the
  refusal lists them with the entry's shape)". Make the same edit in references/test-loop.md. Add nothing to the
  duty: E7 §6e rules out restating the gates.

Gain / risk:
- (a) removes about one refusal round in every five runs that reach test, on every subject. An empty list asserts
  nothing, so nothing is lost.
- (b) stops the packet contradicting its own gate. The measured time gain is small.
- Risks: the test head budget (18,820 of 20,000 characters at the reference install), and the callback-contract
  guard list that pairs each Checked-by phrase with its refusal.

History respected:
- 3f8a0a7b: dispositions are kept.
- E7 (docs/shiploop-test-stage-prompt-design-2026-10-30.md §7b, §6e): no arm was adopted, and this proposes no
  test-writing arm.
- 1787e264: packets state what their gates refuse.
- d7388043.

### document — verdict: improve
Signals: 74 runs; 129 packets for 124 actions; 9 refusals (3 real, 1 check-only, 5 `check`); 0 send-backs;
137 minutes (median 0.7).

Findings:
- **6 of the 9 refusals, plus 1 at implement, come from the spec write-back check** `step_spec_refusal`
  (shiploop_knowledge_home.py, d1f63406).
  - All 3 "without the step's mark" refusals rejected a correct line that ended "(W1/S1)." — a period after the
    mark. They were B-user-listing-s1 and shiploop-sf-qualified development-01 (both 10-31) and bc-final-2 (at
    implement, 10-29).
  - The check is `line.rstrip().endswith("(" + marker + ")")`. Nothing else in the scripts reads the mark.
  - Live in current code: yes.
- **The other 4 ("outside an R-<n> entry") all come from the E2E harness's seeded spec** (pilot-terra-*-32f436 and
  p0-terra-*). There, R-1 is a single paragraph rather than an `### R-1` heading. This is an artifact of the test
  setup, not a stage defect.
- **The remaining refusals are retired or generic:** the headline length cap is gone; an unterminated fence and a
  missing result file.

Proposal: accept trailing sentence punctuation after the mark, for example
`re.search(r"\(" + re.escape(marker) + r"\)[.;]?$", line.rstrip())`. No prompt change.
Gain / risk: removes a check round in about 1 of every 25 runs that reach these stages, at both implement and
document. No risk: the mark must still be present and inside an R entry the committed spec holds.
History respected: d1f63406 (the lines-only write-back is kept) and 232689c5.

**Group top picks**
1. **Stop two refusals of correct values.** Accept an empty `red_na` or `retired_tests` list, and a period after the
   spec mark: two one-line script changes, each with a route test. Together they remove 19 of the 95 test and
   document refusals, plus 1 implement refusal, on every subject.
   Cost: under an hour plus a patch change note. A release that ships shiploop needs an E2E round or a
   `No-E2E-Round` trailer.
2. **Correct the test packet's mutation Checked-by line, and test-loop.md, to the per-survivor rule.**
   Cost: one string, its callback-contract pairing, and re-journalling the head table
   (`render_diff --emit-table --write`).
