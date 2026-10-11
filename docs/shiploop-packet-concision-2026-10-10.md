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
