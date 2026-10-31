# Review group A-front: intake, discovery, research, spec (2026-10-31)

Corpus: `stage-health.txt` (96 traced runs), plus my own read-only scans of the same archive roots, with `/seed/`
runs left out (their prelude is scripted, with 87-character summaries). That leaves 65 runs, which give the minutes
below. Code read at main `441b1b3b` (2.26.0). The archived runs ran 2.21.0 to 2.25.1.

### intake — verdict: improve
Signals: 96 runs, 98 packets. 10 refusals in 8 runs, of which 5 are live (IN1). The rest are retired: 2 for the
headline cap (removed in 232689c5) and 3 for DeepSeek shape slips on 10-28. Median 0.17 min, total 21 min.
Findings:
- **Long requests: IN1 refused all of them (3/3).** The gym case has 69 sentences and 7,589 characters. All three of
  its intakes were refused first (`~/e2e-runs/2026-10-31/shiploop-gym-salesforce-91y7tnl1/gym-published-baseline-0{1,2,3}`).
  The causes differ:
  - In gym-01 the first attempt was a good summary of seven ranges ("S1–S6: … S42–S47: …"). But it used the model's
    **own** count of 47 sentences, while RUN/request.md numbers 69. The refusal is in the
    `events.jsonl` tool call `item_14`.
  - gym-02 cited up to S48, also refused.
  - gym-03 cited no S<n> at all.
  — live in current code: yes. `shiploop_request.check` is unchanged since 70d88d37. Duty 1 still says "cited S<n>
  (S1 is the first)", which invites the model to count for itself.
- **Two of the three repairs copied the whole request.** The refusal says "give each the outcome … with its S<n>".
  gym-01 and gym-03 then pasted all 66 eligible sentences word for word. gym-03 tagged every one "(fact; delivery
  criterion or scope boundary)", through a python heredoc. Those summaries are 8,377 and 11,379 characters. gym-02
  re-cited by ranges in 1,141 characters. Duty 1 says "do not copy it" (2be02de1). The copy defeats the mapping, and
  every stage that opens intake's result carries it. — evidence: transcripts of gym-01 and gym-03, plus my scan of
  all 96 intake results. Copying occurs only in these two runs. Live: yes.
- **The model is never told that ranges count.** `_CITED` has accepted "S2-S4", "S2 to S4" and "S2..S4" since U17
  (1eea76fb). The duty, the template placeholder (`SUMMARY_PLACEHOLDERS['intake']`) and the refusal do not say so.
  Live: yes.
- **Since 2.26.0, the request leaves the printed head sooner.** The intake packet grew by about 2.8K characters at
  2.26.0. For the same request it went from 12,667 to 15,466, and from 12,918 to 15,704, in A/B runs under
  `~/e2e-runs-qr/20261031`. Any request longer than about 1.8K characters now passes `PRINT_LIMIT` (16,000). The
  request block is FILE_ONLY (`_run_context_lines` → `_request_lines`), so it then appears only in the packet file.
  There, `_request_block` cuts it at 6,000 characters, and its note says the full text is in "RUN/state.md; field
  prompt", not RUN/request.md. 6 of 64 non-seed requests are longer than 1.8K, all of them Salesforce cases. Live: yes.
  ffea2956's Checked-by line now names "each S<n> of RUN/request.md". That probably fixes the gym-03 form (no
  citations at all), but not the self-numbering form or copying on repair.
- The other 2 live IN1 refusals were a short request's last sentences, left out: S5 of 5, and S25–S26 of 26. Each
  repair took one round. The gate works as designed there.
- The ledger (duty 9) was built, A/B-tested and kept (ffea2956, e7e0bc3c, 45f9752e). Items 2 and 6 overlap it but
  were inside the measured arm B, and item 6 has its own evidence (E3 of 0e7adbca). No change to either.

Proposal: wording only, plus one mechanism line.
- Duty 1. Replace "Cover each request sentence in `summary`, do not copy it: one clause each, cited S<n> (S1 is the
  first), as the template's summary says." with:
  > Cover every request sentence in `summary` without copying it: one clause per sentence or per run of related
  > sentences, cited as RUN/request.md numbers them (S<n>, or a range S<a>-S<b>), as the template's summary says.
- Template placeholder:
  > `<one clause per request sentence or range (S<n>, S<a>-S<b>, numbered as in RUN/request.md): the outcome,
  > boundary, default or open question it maps to>`
- IN1 refusal: after "give each", insert "(or a range S<a>-S<b> that holds it, numbered as in RUN/request.md; do not
  copy the sentences)".
- `_request_block`: the excerpt note names RUN/request.md, the verbatim file with its index, instead of
  `state.md; field prompt`.

Gain / risk:
- On any project with a long request, this removes one refusal round and an 8–11K summary copied into the result
  that discovery, research, spec and plan open. A copy maps nothing, so the gain is quality as well as tokens.
- Risk: a lazy model may write "S1-S69: build it". IN1 already accepts that today; the model just doesn't know.
  Short requests (all of X1/X2's cases) are unaffected.
- Optional confirmation, scored by script with no judge:
  - corpus: the 6 archived long-request intake packets, rendered at main with arm A (now) and arm B (proposed), with
    RUN/request.md inlined (the X1-T no-tool harness, `docs/experiments/question-record-20261031/run.py`);
  - samples: Terra 6.1 high, 4 per arm, 48 calls;
  - each refused output gets the arm's refusal text as a second turn;
  - measures: first-attempt `shiploop_request.check` pass, sentences copied word for word after the repair, and
    summary characters;
  - adopt B if its first-attempt pass rate is at least A's and it copies less.
History respected: 2be02de1 (no copy), 1eea76fb and 70d88d37 (ranges and IN1 kept), ffea2956 and e7e0bc3c (the
ledger untouched and kept optional), 232689c5 (the cap refusals stay retired).

### discovery — verdict: no-change
Signals: 64 runs, 66 packets. 1 refusal: malformed JSON from a model slip (bf-ds-ticket-assignment, 10-28).
Median 0.33 min (p90 1.56), total 38 min. The packet is about 17.9K characters and never prints whole (0/66).
Findings:
- **Done-when #1 holds in practice.** 57 of 64 discovery results cite a baseline output file, and the other 7 are
  empty checkouts recorded as missing coverage. A failing baseline was caught and classified rather than fixed
  (`…/qualification-full-ui/runs/config-control`). — evidence: my scan of results/ evidence_refs. Live: yes.
- **The ledger questions get answered without a prompt change.** In 3 of the 4 B runs that store a ledger, discovery
  answers the questions by Q-id. In the 4th it answers their content (`~/e2e-runs-qr/20261031/B-*-s{2,3}`).
  Numbering questions as a record was tested and rejected (X2, goal 2 of
  `docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md`).
- At 5.7K characters, the duty is the longest in the prelude. But it prints once per run, and no item is shown to
  mislead. Trimming it buys few tokens and risks the conditional items (service, connected knowledge) that real
  projects need.
Proposal: none.
Gain / risk: n/a.
History respected: 7c8ee3d1 (D1 record), 45f9752e (the verdicts).

### research — verdict: no-change
Signals: 64 runs, 68 packets. 1 refusal (the headline cap, retired in 232689c5). Median 0.18 min, total 24 min.
Prints whole 67/67 (about 14.5K).
Findings:
- RUN/notes/research.md exists in 63 of 64 runs, and 62 have the `## Assumptions` section that plan builds on (duty
  11). — evidence: my file scan. Live: yes.
- Research is usually a single write on Terra; for example, B-ticket-assignment-s3 `transcript.md` line 30. It
  produces no defect downstream: none of the 39 send-backs points at a research gap (see spec).
- Ideas already closed:
  - the research frontier Until Loop (goal 3, its prerequisite rejected);
  - the 2026-09-21 research cue, which tied 4 of 4 (b992183d).
- The written allowance (15 min, 64 actions, 3 experiments; D5) is a limit and stays the owner's. It is flagged
  only, not proposed (7c8ee3d1 finding 6).
Proposal: none.
Gain / risk: n/a.
History respected: b992183d, 7c8ee3d1, ffea2956 (D5 stays the owner's).

### spec — verdict: no-change
Signals: 63 runs, 63 packets. 1 refusal (the headline cap, retired). Median 0.22 min, total 24 min. The packet is
about 20.2K characters and never prints whole (0/61).
Findings:
- **No send-back traces to spec.** I read all 39 accepted send-back, add-work and blocked outcomes. None blames a
  spec defect:
  - 28 are a step Proof or focused-command fault;
  - the other 11 are test layers, the system-test plan, delivery, one block, and one test-spec oracle error.
  So the live test that §4 of the verdicts doc proposed for the spec duty line (goal 6: a +5 acceptance gain below
  the 10-point bar) has no signal in this corpus. — evidence: the trace `accepted` rows plus results/ summaries.
  Live: yes.
- **The request is never in the printed spec head.** It is missing from 63 of 63 spec heads, and from 63 of 63 plan
  heads, although D2 makes spec a REQUEST_WHOLE_STAGE. The head's "Full packet" line points at the file, which has
  the request cut at 6,000 characters. I found no harm: hosts don't clear context, and the gym specs that passed and
  failed don't differ on this. Live: yes. Not proposed (KISS). The intake excerpt-note fix covers spec too.
- Items 6 (polished interface) and 10 (replay checks) come from recent owner and evidence commits (5a65d62c,
  7d372c5a). They are acted on: 12 of 62 spec.md files mention replay, and 3 mark a case NOT-REPLAYED.
Proposal: none. Close goal 6's live measure; the corpus cannot show a gain.
Gain / risk: this saves an experiment that cannot decide anything.
History respected: 7d372c5a, 5a65d62c, X2 goal 6 in the verdicts doc (45f9752e), D2 (1eea76fb / ab515869).

**Group top picks**
1. **The intake range-and-numbering wording** (duty 1, the placeholder, the IN1 refusal text) **and the excerpt note
   pointing at RUN/request.md.**
   - Gain: on any long request, no refusal round from self-numbering, and no verbatim copy of the request in
     intake's result. The evidence is 3 of 3 refused and 2 of 3 copied.
   - Cost: four string edits; updates to the guard, placeholder and RequestIndex tests; a patch change note.
     Optionally, the 48-call scripted replay above.
2. **None to build.** Discovery, research and spec show no live defect. The one free decision is to close the spec
   duty-line live measure, which has no signal in 39 of 39 outcomes.
