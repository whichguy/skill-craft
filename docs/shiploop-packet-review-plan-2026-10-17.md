Execute: inline (owner go 2026-10-17 with the decisions in section 4)

# ShipLoop packet review and plan (2026-10-17)

Consumer: the owner, read once to approve or amend each unit and the decisions in section 4; then the session that builds
the units. Evidence: [docs/experiments/packet-review-2026-10-17/](experiments/packet-review-2026-10-17/) (six reviewer
files `A-preparation.json` … `F-release.json`, one per group of steps, with every finding's quote, evidence, proposal,
source symbol and saving; `X-status-narrative.md` for the owner's two additions; `BRIEF.md` the rubric; `index.json` the
step table). Run: `/Users/dadleet/e2e-runs/20261017/salesforce-chess-int-802e29` (Grok 4.7 medium, 26 stages, 155.6 min,
11 Improve reviews, 573 calls, 8 compactions, 5 refusals; app works in org `de`). Page with every prompt:
https://claude.ai/artifact/E8GUBbJFgMLY95bm6TNhUx.

## 1. What the review found

Text written per run: 1,642 KB of packets and 771 KB of Improve hand-offs (2,413 KB). Scores per step (concise /
accurate / effective, 1-5) are in the reviewer files; the worst were release-plan (3/1/1), release-verify (1/3/2),
implement S1 (2/2/4) and verify (2/3/3); the best were research, spec, release and the Improve packets themselves.

| # | Finding | Evidence | Where it is generated |
|---|---|---|---|
| F1 | **Steps collapsed.** A check was run after every step regardless of its criteria; S1 got S3's board grep, revised, and the repair merged S1-S3 into one step (1 implement + 1 Improve instead of 3 + 3). **Fixed** in 603a709c. | B-build-1 BX-1, C-build-2 X4; step 16 result | `shiploop_navigator.step_checks`, `_step_lines` |
| F2 | **Knowledge files quoted whole** in every producer packet (53% of packet text, 828 KB) and again in every Improve hand-off (60-65 KB of each 68-98 KB hand-off). The quotes sit in the file-only part or Grok's cut middle; the model reopened the files directly anyway (it must, to edit them). | A AX-1, B BX-2/BX-3, C X5, E C-3, F X-2 | `reads_lines`, `READS_HEAD`, `_consumer_lines`, `improve_handoff_text`, `_spec_diff_lines` |
| F3 | **The head cites what it does not print**: guide labels without paths, "open items quoted below", the return route, delivery contract lines, the Backchain "Loop resources" line, the step's own criteria. The model grepped the packet file or concluded wrongly (product-acceptance thought Backchain repair was blocked). | A AX-2, B (criteria), E C-1 | `_producer_blocks`, `_run_context_lines`, `_select_head` |
| F4 | **Gates not stated in the packet**: the model read ShipLoop's Python 46 times in steps 29-33 (34 at release-plan, 8.2 min, a compaction) to learn accepted values. Examples: intake's authority operation/target must equal the contract's (2 refusals); release-plan refuses while delivery necessity is unresolved (not in Checked-by, no template field); `--notes` takes a file; verify must write the result before `--check-only` (refusal "navigator result is unavailable" names no file); release-verify's Checked-by says it reruns "every recorded test command" but reruns only `consumer_checks` (empty here). | A intake, E C-2 and step 33, D D-8/D-9, F worst inaccuracy, refusals.txt | `_stage_gates`, `_result_contract_lines`, `_CHECK_TEXT`, `shiploop_consumer_delivery._contract`, stage duties in `shiploop_prompts.py` |
| F5 | **Revisits do not say they are revisits.** step-plan's "why you are back" lines are file-only; test-spec, implement and their Improve hand-offs get none. Step 19 searched for its own earlier spec and resubmitted it byte-identical. Revisit packets share 94% of lines with the first visit. | C X1, X2 | `_revise_delta_lines`, `_sent_back_results`, `_producer_blocks` |
| F6 | **Status and narrative duplicate each other** (owner): 28 of 36 packets carry both (Where = Now, Done = Achieved, Next = Ahead); 8 of 11 Improve packets carry a narrative although Improve is not a milestone. 45 KB, but it sits in the printed head and asks for a verbatim output turn. | X-status-narrative.md, E C-5, F X-4 | `status_block`, `shiploop_narrative.py`, `improve_packet`, `shiploop_status_hook.py` |
| F7 | **Heads over Grok's 20,000 cut** at test (22.1 KB), document (22.3 KB), verify (24.2 KB): the guidance in the middle was cut and the model read the 74-102 KB file (twice at verify). Identical recorded commands printed twice (rows 7-9 = rows 1-3), the step-plan path list twice. | D DX-1 | `_producer_blocks`, `shiploop_test_loop.normalise_commands` |
| F8 | **Person-only observation asked as prose.** Seven steps with FENs, the "tab hidden" case last although it blocks all others; after a partial reply the stage blocked again instead of recording the unanswered cases as not run, against "do not loop on it". release-check could have found the hidden tab an hour earlier with a read-only query. | F X-1 | release-verify guidance item 6, release-check guidance |
| F9 | **Small stale or wrong lines in every packet**: the pointer says to open the file "for the duties or the template" (printed since 2026-10-16); platform-irrelevant duties (MCP, async, CommonJS/ESM on Apex; "ambitious, highly interactive" UI against "simple"); "earlier runs' spec … are there" on an empty run; the Improve packet's example is for Claude Code on a Grok host; a rollback recipe with an absolute path next to a "no absolute paths" rule; "Deploy not to unblock a test" while 3 of 4 commands deploy. | A AX-4/AX-6/AX-7, C X3, D, E | `packet_pointer`, `DUTIES`, `improve_packet` |
| F10 | **Duplicate org runs**: the model's own run, `--check-only`, and the real `complete` after a passing check-only on an unchanged tree each reran all 10 org commands (about 104 s each at verify). | D DX-2, D-11b | `shiploop_test_loop.verify` |
| F11 | **Improve recovery after compaction**: the reprinted Improve packet did not say a pass was already recorded, so the model redid it (390 s). | E step 30 | `improve_packet` |
| F12 | **"ShipLoop navigator" prefix** (owner): the result-template heading `# ShipLoop navigator result` is read by nothing (the store reads only the JSON block); the first line is read by the status hook (`HEADER`), the run-review export and template, five E2E harness patterns and about 20 tests; the refusal prefix is counted by `test/shiploop_e2e/metrics.py:REFUSAL_LINE` and about 89 test assertions. Keepalive keys on `SHIPLOOP-RUN`. | all six | one constant per string |

What worked and must stay: one command, one output file and one citation per guidance line (release-check, release: 0
refusals); the 2-3 KB Improve packet; Improve review focus lines ("a check a weaker stand-in would pass", the
replayability list) that found real defects; "Lost context? Run shiploop next" (every compaction recovered through it);
the open-item route for a case the host cannot run; the test stage's base-run rule; script-prefilled exact-match
fields.

## 2. Units

Each unit: work, exit (a test or measurement that must pass), tests by footprint (test-economy policy). Order is by value
per risk; U1-U3 are independent and can be built in parallel worktrees.

**U0 (done, 603a709c): step-scoped checks (F1).** Remaining: a live multi-step run must show one implement and one Improve
per planned step in plan order (owner TODO); verified in section 3.

**U1. Knowledge by locator (F2).** Replace the whole-file quotes in producer packets and Improve hand-offs with, per file:
path, size, and a table of contents (headings and R-/AD- IDs). Quote by value only the requirement and decision rows the
stage follows (from `follows` and the item's criteria) and, for a file changed since the previous packet, the changed
sections as a diff; release-verify's diff of new files becomes a pointer. Exit: offline render (`packets.py --offline`,
`render_diff.py`) shows packet text down at least 40% on the node and chess-shaped fixtures, no obligation lost
(`shiploop-packet-obligations`), every head ≤ 20,000 at the reference install. Saving (estimate): 1.3 MB of 2.4 MB per
run like this one. **Needs decision D1.**

**U2. Slim Improve hand-off (F2, F5).** The hand-off names the producer's packet and result files instead of re-quoting
their sources, and on a revisit names the previous accepted result and the revise result. Exit: hand-off ≤ 12 KB on the
chess fixture; `shiploop-improve-*` and handoff suites pass. Saving: about 660 KB per run.

**U3. Print what the duties cite (F3, F7).** Move into the head, when the stage's guidance names them: guide paths,
open items, the return route, delivery contract lines, the Backchain resources line, the step's own criteria. Make room
by merging identical recorded commands, printing the path list once and one-line pass and floor rules. Exit: a test that
every label a head's guidance cites resolves inside the head; heads for test, document and verify ≤ 20,000 at the
reference install.

**U4. Revisit packets (F5).** Print in the head of every revisited stage (step-plan, test-spec, implement) and its Improve
hand-off: why the stage is back (quoted from the revise result), the previous accepted result's path, IDs added, removed
or changed upstream, and "keep unchanged rows with their IDs". Exit: a revise test asserts the four lines in each head;
step 19's case (resubmitting an unchanged spec) is caught by the Improve focus or a gate.

**U5. One progress block (F6).** Milestone packets carry the narrative only; other packets one line (`Where … · Next …`);
Improve packets neither. The status hook reads Now/Achieved from the narrative; `status.md` and `shiploop status` keep the
full block. Exit: hook tests, `shiploop-status-display`, `-narrative`, packet suites; status-display.md updated.

**U6. Gates stated literally (F4).** For each refusal of this run, the packet states the rule before the gate does:
intake template uses one field for operation and target (or the script fills the authority from the contract);
release-plan's Checked-by names the delivery-necessity gate and the template has the field; `--notes` help says it takes
a file; verify duty 1 says to write the result first and the "result is unavailable" refusal names the missing path;
release-verify's Checked-by names what it reruns and how many. Exit: each of the five refusals has a test that submits
the refused input through the real gate (test-the-route rule) and the packet line that prevents it.

**U7. Answerable person observation (F8).** Release-verify item 6: step 1 is how to reach the entry and what to answer if it
is missing; the report is a fill-in list, one yes/no line per case; on a partial reply the unanswered cases are recorded
not-run with the reply quoted and the stage continues (handoff carries them). release-check runs a read-only visibility
probe where the platform reference has one (Salesforce: tab visibility for the running user's profile). Exit: a test
that a partial `--observed` reply completes release-verify with the open cases recorded; the platform probe lives in
`references/platforms/`.

**U8. Stale and platform-irrelevant lines (F9, F12).** Drop the pointer's "duties or the template" clause; drop
`# ShipLoop navigator result` from the template; make the platform-specific duties conditional on discovery's facts;
host-neutral Improve example; remove the absolute-path rollback recipe and the contradictory deploy line. Prefix: shorten
the first line and the refusal prefix to `ShipLoop` only if decision D4 says so, through one constant with every reader
(status hook, export, harness patterns, metrics) in the same commit. Exit: packet suites; `git grep` shows no reader of the
old strings.

**U9. Duplicate org runs (F10).** Merge byte-identical recorded commands at step-plan; let `complete` reuse a passed
`--check-only` record when the tree snapshot and command list are unchanged (decision D5). Exit: test-loop suite; verify on
the chess fixture runs the org suite once after a passing check-only.

**U10. Improve recovery (F11).** The reprinted Improve packet states the passes already recorded and the next command.
Exit: a compaction-recovery test.

## 3. Verification

1. Offline: render every stage on the node fixture and a chess-shaped fixture before and after (`render_diff.py`),
   record per-stage text, head and quoted-knowledge sizes in the journal; head tables updated with reasons.
2. Footprint suites once per unit; one `quick --changed-from <INT head at start>` at the integrator.
3. One live run on a different app (owner rule: vary the example; for instance checkers in the same org, or a Node app)
   with a step plan of at least three steps. Measure against this run: packet and hand-off KB, reads of ShipLoop source,
   refusals, compactions, minutes, and implement + Improve actions per planned step (must equal the step count, in order).

## 4. Decisions for the owner

Owner answers (2026-10-17): **D1** table of contents (U1 as written); **D2** yes, quote the request whole only at
intake, spec and plan, now (part of U1); **D3** no for now: implement keeps the full Code craft text; **D4** drop the
`# ShipLoop navigator result` heading now; the first line and the refusal prefix stay; **D5** yes, `complete` reuses a
passed check-only record on an unchanged tree and command list (U9).

The questions as asked:

- **D1 (U1):** Is quoting knowledge files whole a requirement of the main tenet (context is cleared between stages), or
  only the means? Recommendation: a table of contents plus the followed rows by value satisfies it; the model already
  reopens the files.
- **D2:** Quote the original request whole only at intake, spec and plan, and a pointer plus the exclusions line elsewhere
  (saves about 160 KB)? Recommendation: yes, after U1 is measured live.
- **D3:** Code craft as one-liners in implement too (saves about 3 KB per implement packet), against the 2026-10-11
  decision that implement keeps the full text. Recommendation: keep full text until a live run shows the head budget needs it.
- **D4 (U8):** Shorten `ShipLoop navigator | <stage> | revision N` and `ShipLoop navigator:` to `ShipLoop …`? Saves 10-30
  characters per packet; touches the status hook, export, harness and about 100 test pins. Recommendation: drop the result
  heading now; shorten the other two together in U8 only if you want the wording, not for size.
- **D5 (U9):** Let `complete` reuse a passed check-only record on an unchanged tree? Saves about 100 s of org time per
  stage; the gate's evidence is then as fresh as the check-only.
- Push and release of the integration branch, including 603a709c, stay held for your go.

## 5. Incorporated from the implement-step fix plan (2026-10-17)

Source: `/Users/dadleet/src/skill-craft/docs/shiploop-implement-step-fix-plan-2026-10-17.md` (another session's plan from
the same run, `Execute: ask`, with its own owner decisions D1-D12; untracked in the canonical checkout, cited by path).
The owner asked to consider it. Its priority order (executable step-specific checks, valid acceptance procedures,
consistent prompt surfaces, measured concision) matches this plan's findings F1, F3, F5 and F8. Disposition:

| Its section | Disposition here |
|---|---|
| §4.1, §5 six consumers, T1-T2, T6, T27, T33: a per-step `check` (the step Proof) written by step-plan, run by ShipLoop at implement done and rerun before importing a changed Improve; item checks leave implement | **Adopt as wave 2 unit W2-A.** It supersedes U0's criteria-scoped rule (603a709c), which stays as the interim fix until W2-A lands; then `step_checks` is removed (one supported version). All six consumers change together: implement duty 3, implement `done_when`, the stage's test text, `REPEAT["implement"]`, the step Improve focus's rerun sentence, and `test_loop.stage_commands`. Needs the next state version. |
| §2.2 F15, §3.1 (trimmed): one `step_block()` for `render()`, `packet_head()` and `improve_handoff_text()`; criteria and cases filtered to the step; step-entry review base for Improve; loop block last; no path fence (its D3) | **Adopt as W2-B**, building on U3/U4 (the U3 worker was told to use one function for render and head, filter to the step and keep the loop last). |
| §4.2: procedure validity (start, actions, oracle, observation, ownership, evidence) reviewed where the procedure originates, through the shared `_REVIEW_FOCUS_ITEMS` text; prepare establishes actor, entry route and access prerequisites | **Adopt as W2-C** (the review text, T25-T26, T34). The prepare prerequisite is folded into U7 now (the U7 worker was told). |
| §3.2, §3.5, §3.6: static guidance and Code craft read from reference files, eight considerations, `criterion_evidence`, Code craft rules 10-14 | **Adopt later as W2-D**, after U1 and W2-A/B are measured: it grows the implement head, and its §8 asks that growth be measured first. Consistent with D3 here (full Code craft text stays). |
| "Retain whole-file knowledge until selection is qualified"; selective knowledge loading deferred | **Not adopted:** the owner's D1 here (table of contents) is the later decision. Its "Anchored in" locator lines fit the table of contents and are used by W2-B. |
| Keep the 16,000-character head target, not 20,000 | **Adopted as a target to measure after U1**, not a new gate; the existing 20,000 cut and 19,500 required-text tests stay. |

Order: wave 1 (U1-U10) merges and is verified; wave 2 builds W2-A, W2-B and W2-C in parallel; W2-D after a measurement;
then the live checkers run checks the per-step series (one implement, one step Proof and one Improve per planned step).
