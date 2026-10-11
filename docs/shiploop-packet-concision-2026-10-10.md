# ShipLoop packet concision: what each packet needs, and what it carries twice or needlessly (2026-10-10)

Status: **interim**. The figures are measured; the proposals are not yet implemented or tested by a clear-the-context
probe.

Question (owner): could each packet be more concise yet still functional, holding the necessary and sufficient
information? Repetition **across** packets stays: the context may be cleared between stages (SPEC S-6, the main
tenet). The target is repetition and inapplicable text **inside** one packet. A follow-up question asked whether
run-wide reference detail should live in one file that every packet links to.

## Evidence

- **The run.** The 22 packets of the `node-fix-bug` step slice (`test/shiploop_e2e/slice.py`; Claude Sonnet 5.5,
  inline, ShipLoop 0.58.0 from branch `exp/step-slice-32c6ee`). Paths are shortened (`<run>`, `<worktree>`,
  `<skills>`), so the sizes are slightly smaller than on disk.
- **Line classification**, by script, by how widely each line repeats across the 22 packets:
  - 31% of all packet text is identical in every packet;
  - 28% is in at least 60% of them;
  - 27% is in some;
  - only **11% is unique** to its packet.
- **Block sizes in the `baseline` packet** (25.5k):

  | kind | chars | share |
  |---|---|---|
  | run-constant (the same in every inner packet of the run) | 14.8k | 58% |
  | per-action state | 4.5k | |
  | result contract | 2.3k | |
  | about the baseline stage itself | 2.2k | 8% |

- **Per-packet review.** Three agents, one per stage group, each read their packets in full against the run's real
  behaviour (`flow.json`: what the model saw and did). For every proposal they name the source constant or function
  and give the replacement text. The findings are in
  `experiments/packet-concision-20261010/findings-{planning-improve,test-build,check-integrate}.json`. Spot checks
  confirmed the test-red Code craft contradiction and the head's lint command that cannot run.
- **What the model read.** It opened 1 of the 22 packet files, and worked from the printed head everywhere else.

## Result

The within-packet cuts alone take the 22 packets from **733k to 548k characters (25%)**, without dropping an
obligation. That covers 255 findings: 94 duplicates, 71 verbose passages, 63 inapplicable blocks and 27 missing
items. The review also found **54 necessary items that are missing or weak**, and those matter more than the
characters.

### Where the characters go (estimated savings by source, all 22 packets)

| source | saved | what |
|---|---|---|
| `_improve_prompt`, `_render_improve` | ~39k | "carry locators into the child's contract" said ~8 times per Improve packet, though the inline route freezes that contract; the opening template and the improve-start command printed twice; recovery/receipt prose; Backchain limits that do not apply to a review |
| `_run_rules`, `_outcome_shape_lines` | ~27k | the callback printed twice; the `awaiting` shape given twice with different fields (only one has `options`); run-to-completion prose |
| `COMMON` | ~13k | requirement-definition paragraphs in stages that only run tests; Improve sentences that say what does *not* happen (against the 2026-10-10 rule: mention Improve only as a directive) |
| workspace return block | ~13k | 1.9k of return commands in every inner stage, ending "The return operation is unavailable here" |
| `_accepted_test_source_lines` | ~9k | sources listed three times: "Results this stage builds on", "Current planning sources", and 6-line source blocks with "evidence references: none" |
| `CODE_CRAFT` via `stage_spec` | ~17k | the 3.7k rubric in test-red (whose own line says "Do not edit product code"), document, verify and integrate |
| `DUTIES[...]` | ~15k | repeats inside a stage: lint gate 5× in implement, "fail inside a test" 4× in test-red, queue rule 3× in carry-forward; step-plan's design-basis and interaction-design texts overlap |

### Necessary but missing (fix these first)

The model works from the **printed head** (`packet_head`), so a rule that lives only in the file body was not read.
These cases are grounded in the run:

1. **Operation lines are only in the body.**
   - Implement's current step: the model grepped the file for "S2".
   - The Until Loop start command and receipt: grepped at test-green, skipped at regression (the model's own
     `loop.sh` instead).
   - The expected-RED list, and test-refine's rerun list.
   - The step-plan `plan.md` note: the model never wrote it.
   - The test-spec file name: the first `complete` was refused for exactly that.
2. **The head's lint command cannot run as printed** (`shiploop lint --action`). The model never linted.
3. **The Improve heads carry no review focus, no ordered procedure and no "record each pass" rule.** That gap let
   `improve-cycle.sh` complete two Improve reviews with fixed text. A written rule alone will not stop a script,
   so it needs a script check: each `review-<n>.md` names the files opened, the commands run with their exit codes,
   and a finding or "none" per focus item.
4. **Stages lack the inputs their own Done-when refers to.**
   - Baseline and test-author never print the recorded test commands or case ids (`stage_commands()` already
     builds them).
   - Implement never prints its completion criteria, paths or focused tests.
   - `red_na` is missing from the test-red template.
   - The system-test-author template lacks the `check` suite and `host_dependent`.
5. **Contradictions.**
   - integrate: "commit the ones the product needs" against "commit nothing for the return"; and "into the working
     branch" against assembly in the execution checkout.
   - static-checks: "ShipLoop records the change inventory" against "none was recorded, build one".
   - `CASE_END_STATES` offers "replan", which no inner stage allows.
   - carry-forward Improve: its scope is "durable learning", but the body makes it the run's end-of-work code review.
6. **No operation line at all.** skill-assess and skill-validate have no Considerations line. The model submitted
   them through its own `done_()` after reading a 265-character head.

## Determination: one run-wide reference file

**Yes for lookup material. No for grounding.** The evidence points to the head as the bigger lever.

- **Section 0 of `docs/lifecycle-review-2026-10-07.md`** withdrew a run-level rules file because it moved
  *grounding* (what the stage is for, how it operates, how it is checked) out of the packet. That stays withdrawn.
  The same section keeps "reference cards ... to shrink what a packet points at, not what it says", and the
  2026-09-26 rule says packets should give labelled references instead of reprinting unchanged run rules.
- **Fits a reference file** (a link in every packet, the detail in `run/reference.md`, written once per run and
  rewritten when ShipLoop's version changes; about 3-4k per packet):
  - the locator catalogue: 17 policy and guide paths, 2.1k in every packet;
  - the full `awaiting` schemas;
  - the recovery-and-reconcile prose behind the one recovery command;
  - the source-block boilerplate.
- **Needs no file at all.** The workspace return procedure (1.9k) belongs only in integrate, release and handoff,
  so dropping it elsewhere is a within-packet cut.
- **Stays in every packet:**
  - the stage's goal, Done-when, Checked-by and operation lines;
  - the callback and the result contract with its allowed outcomes;
  - the recovery command;
  - the original request, in its fence;
  - the behaviour rules this stage can hit: unattended defaults, blocked with `awaiting` (short form),
    "never end the turn while a ShipLoop command runs", scratch rather than `/tmp`, and credentials.

  These change what the model does in this stage, which makes them grounding.
- **The run already behaves this way.** The model reads the head (~1-5k) and treats the packet file as the
  reference it rarely opens. Moving more text from the packet file to another file changes little of what is
  read. Moving each stage's operation lines **into the head** fixes the failures listed above.

## Recommended order

1. **Head content (effectiveness).** Put each stage's operation lines and actual inputs in the head, ahead of the
   result template, so they survive a host cutting the output short: the current step, the commands and case ids,
   the Until Loop start, the expected RED, the runnable lint command, and the Improve focus with the pass-evidence
   rule. Add a script check that refuses a `review-<n>.md` without that evidence.
2. **Fix the contradictions in item 5.**
3. **Within-packet cuts**, source by source, as in the table, using the replacement text in the findings JSON.
4. **`run/reference.md`** for the lookup material above.

Verify each step:
- `packets.py --offline <case>` for sizes, before and after;
- a clear-the-context probe at a stage boundary and inside a stage (S-6);
- the four step slices again, compared with `packets.py --compare` and `flow.py` against
  `evidence/step-slices-2026-10-10.json`. The same verdicts are required, with fewer scripted reviews and fewer
  grep-the-file calls.

## Open

- **Two caps that may conflict. SETTLED 2026-10-10.** The test loop's genuine-fix-attempt and refused-run caps
  (then 3 and 7), which lead to revise, seemed to conflict with the rule that ShipLoop's quality and test loops are
  unbounded.
  - The owner raised them ("more like 7 and 11") and kept them as bounds on a stage's acceptance gate. The Until
    Loop itself stays uncapped.
  - SPEC S-10 records this as the carve-out of 2026-10-10 (test/shiploop_e2e/SPEC.md).
  - The values are constants: `shiploop_test_loop.MAX_REFUSED_RUNS` = 11,
    `shiploop_stage_spec.GENUINE_FIX_ATTEMPTS` = 7, and `shiploop_keepalive.STUCK_CONTINUATIONS` = 22.
    `test/shiploop-stage-spec.test.py` pins every prose copy to them.
- **Risk in the merged UI/state text.** The merged step-plan UI/state text (design basis plus interaction design)
  keeps every obligation, but it should be rerun against the interaction-state experiment cases before shipping.

## 2026-10-11: within-packet dedupe, shared blocks and step-plan (recommended order item 3)

Status: **interim**. The sizes are measured, the 30 packet suites are green, and one live slice passes. The
clear-the-context probe has not run yet.

**Question.** The owner said: "the full packet file looks far too verbose ... consolidate the language and
deduplicate". They pointed at a live step-plan packet: 53k characters and 701 lines, with paths shortened.

**Where the step-plan characters went.** The measurement is docs/experiments/packet-dedupe-20261011/step-plan-live-before.md.

| Block | Share |
|---|---|
| Shared COMMON rules | 32% |
| Interaction and state lifecycle | 6% |
| Request plus 15 guide locators plus the workspace return block | 9% |
| The 17-line locator catalogue and recovery prose | 6% |
| The 115-line result template | 6.5% |
| Progress reporting | 5% |
| Backchain caller text and budget | 4% |

The callback was printed 3 times. The status was printed 3 times: the snapshot, the block and the narrative. The
step rules were printed 4 times: Checked-by, the exit conditions, the duty and STEP_SIZING.

**Owner decisions (2026-10-11, AskUserQuestion).** The owner approved all four moves out of the packet:
- the result template to a file. I implemented this as a compaction instead, because the tests and the model parse
  the template inline;
- the interaction and state text to a Design basis item plus its guide;
- the requirements rules to one bullet;
- the Backchain and workspace text: one optional audit line in inline step-plan, and the return route only at
  release and handoff.

**Change.** changes/shiploop/packet-dedupe.md lists it in full. A short `STAGE_RULES` list replaces COMMON,
REQUIREMENTS_RULES and PROGRESS_REPORTING, and their long forms stay in reference.md (#rules, #requirements,
#progress). Each duplicate was cut to one home.

**Lost obligations found by the pin workers, and restored.** Four workers updated about 430 pinned assertions. Each
assertion whose obligation was stated nowhere was reported instead of re-pointed. These were found and restored:
- step-plan item 4: the facility locator is carried into the item context and the Improve child's notes.
- item 7: the Design basis terms.
- item 9: "an unrecorded conversation is not a planning handoff" and the sole-directive sentence.
- item 1: carrying the test decision forward on a revise.
- The access-discovery rule ("non-mutating probes and sanitized evidence") is now in STAGE_RULES, with the
  Access-readiness locator at discovery and research.
- The untrusted notice for host-recorded labels. It came from the removed Progress snapshot and now sits above the
  status block.
- TEST_DECISION_HANDOFF named a source block that the dedupe no longer prints. It now names the "builds on" entry.

**Result** (docs/experiments/packet-dedupe-20261011/offline-sizes.json). On the offline node-fix-bug inner loop, inline, the total fell from 431k
to 270k characters. The step-plan packet fell from 58k to 33k (`packets.py offline_packets`, before ref
3c812fbd).

**Known limits.**
- Improve-child prose still says "the packet's Maintained requirements policy" and similar. Those locators are
  reachable only through the reference.md#policies line.
- The "*" no-review swap row for COMMON's schedule sentence now affects only reference.md.
- The test, verify and carry-forward packets (25-28k each) still carry TEST_FACILITY_HANDOFF and
  TEST_DECISION_HANDOFF, plus a second "fix and resubmit" line. This is the next pass.
- **Live step slice, run after the commit** (docs/experiments/packet-dedupe-20261011/live-slice.json; n=1 each, so a
  trend, not proof). Claude Sonnet 5.5, inline, on node-fix-bug:

  | | 8848cc65 | 348b5932 |
  |---|---|---|
  | Result | PASS | PASS |
  | Turns | 78 | 73 |
  | Model calls | 46 | 41 |
  | Packet characters written | 1.15M | 0.64M (-44%) |
  | Wall time | 228 s | 223 s |

  Every verdict passes.
- Not yet run: the S-6 clear-the-context probe. It should run before a release.

### Second pass (2026-10-11, same day)

After the first pass, no sentence repeats verbatim inside any offline packet (checked by a sentence-level count over
all 12). Two kinds of text remained: shared prose that overlapped in meaning, and gaps the pin workers reported.

- **Shortened:** TEST_FACILITY_HANDOFF, TEST_DECISION_HANDOFF, OUTER_TEST_HANDOFF and SELECTED_CASE_RECONCILIATION.
  The tests pin their key phrases, and the new wording keeps each one.
- **Inline carry-forward:** it gets the one-line Backchain audit, as step-plan does (`INLINE_AUDIT_STAGES`).
- **Improve-child packets:** they now locate the policies their review text names (`_named_policy_text`).
- **Tried and reverted, with the learning:**
  - **The previous stage's evidence references, printed as a count and a path instead of the list.** Tests showed
    the list is the hand-off route for locators that the next stage must open: the access-readiness note, the prior
    baseline section, and a UI review. It stays printed, bounded at 2,400 characters.
  - **The same cut for the test-source blocks:** reverted for the same reason.
  - **A step-plan gate that refuses a focused command without ids:** the engine supports id-less focused commands by
    design (counted by run size), and 50 test-loop fixtures use them. The live revise it was meant to prevent was the
    designed route working.
- **Result:** the 30 packet suites pass. Offline sizes move only slightly (the fixture's evidence lists are short).

### Verification before main (2026-10-11)

Evidence: docs/experiments/packet-dedupe-20261011/verification.json. Build fbabc74f, Claude Sonnet 5.5, inline, n=1 each.

**Live step slices.** All four pass with every verdict. The baseline is the 8-stage loop at 13d278dd.

| Case | Seconds | Turns |
|---|---|---|
| node-add-function | 315 → 239 | 98 → 78 |
| node-fix-bug | 243 → 224 | 71 → 75 |
| node-add-route | 249 → 233 | 82 → 83 |
| node-rename | 215 → 237 | 77 → 85 |

That is mixed at n=1: three cases are faster, rename is slower. Packet characters written are 0.54-0.74M per slice.
The quick group passes.

**S-6 clear-the-context probe at implement:inside.**

| Build | Probes | Result |
|---|---|---|
| fbabc74f | 2 | 1 fail, 1 pass |
| 3c812fbd (before the dedupe) | 1 | pass |

The one "redone" call was a verification rerun of `npm test`. The kill landed right after a single command that both
edited the code and ran the test, before any result was recorded. The fresh session then rechecked the claimed state
(git diff, tests, lint) before completing, as the rules require. The repeat on the same build passed with nothing
redone.

Status of this finding: **interim**. It is a timing-dependent limit of the probe's rule that "a test rerun with no
write between is redone". It is not a packet regression. A pass log written after each edit-and-test would give the
fresh session a record to trust.
