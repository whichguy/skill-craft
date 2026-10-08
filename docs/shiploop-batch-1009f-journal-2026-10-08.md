# ShipLoop batch 1009f journal (2026-10-08)

Scope: the audited groups G2 (step-plan: S1; S2 dropped) and G4 (plan and Improve: BC1 smaller, B1a only), plus P4 (the
test-strategy stand-in probe). Source analysis: `docs/experiments/batch-1009-round1-analysis-20261008/analysis.json` (the
four-lens round-1 analysis and synthesis) and the round-1 evidence in `docs/experiments/round1-20261008/evidence.json`.
Base: origin/main 847fa64e (587cd90d is the 1.24.0 release; abc47622 the CI Git-config fix). Each entry names its status
(firm, interim, exploratory, superseded) and its citations. Edit an entry later rather than deleting it.

Rule for every item here: the change makes ShipLoop more faithful to its stages, to `test/shiploop_e2e/SPEC.md` and to the
main tenet, and it is generic (no sample-app text, threshold or guard). A new state key would be optional; none is added.

## S1: the step plan no longer promises a route its gate refuses

Status: firm (the contradiction was reproduced through the real CLI; the fix is text and message only).

Question. The step-plan duty said to mark a criterion that no check can confirm as `Confirm by: unconfirmable here`, while
the same packet's Checked-by line (built from the recorded gate) says a criterion no command names is refused. Which wins?

Finding. The script wins (SPEC S-3). Commit 153160e1 made "a passing test is the evidence" the owner's rule and removed the
model-judged confirmation; the step-plan prose never caught up. A step plan with a criterion `Confirm by: unconfirmable here
- needs a person` that no command names was refused with only "every criterion needs a test command that confirms it ...;
uncovered: C2" and no exit named.

Audit corrections applied (they override the design). (1) The `Confirm by: <command, observation, or inspection>` shape stays:
the same paragraph also serves an item that records no test command (`test_commands_na`, accepted with no `criteria` at
all), an ask-agent graph step's `contract.done` (inline swaps the graph paragraph out, ask-agent keeps it) and the
entry-point example two paragraphs later. Only the unconfirmable sentence is scoped: a `criteria` entry needs a command, so
a condition no command can confirm is an open item in the result's summary; elsewhere (a plan note, a graph step's done
item) the `unconfirmable here` marker stays. (2) The implement Done-when row names no field and no route ("each completion
criterion this step's work covers is confirmed after the last edit"): a "recorded test command" wording would be false for
an item with no tests and for a graph step. (3) No promise that the handoff lists the open item: the handoff packet reads
intake, spec, plan, product-acceptance, release-verify and operations, not the step-plan result, and no structured home
exists for a step-plan open item yet. That gap is a known limit. (4) The refusal names the exit and keeps the substrings
the existing tests assert.

Changes. `DUTIES['step-plan']` (the authoring paragraph, after the status block so the kept head does not grow);
`_normalise_criteria` (message only; it accepts exactly the inputs it accepted); the `implement` row of `STAGE_SPEC`;
`references/execution-planning.md` and SKILL.md "Confirmation is a passing command" (one sentence each). Not built: a
Confirm-by template shape, a blank-clause refusal, a command-less accepted unconfirmable route (it would confirm nothing
and be listed unverified; the honest reason to defer is that no structured sink exists), and the S2 item below.

Tests (fail first, through the real CLI with Git config isolated). `RefusalRouteTests` in
`test/shiploop-callback-contract.test.py`: (a) a step plan whose extra criterion no command names is refused with
`uncovered: C2` and an open-item exit read from the reply, the correction (drop the listed ids, record the open item in the
summary) is accepted and the recorded criteria are `[C1]`; the packet's own sentence about such a condition names the same
exit. Red on the unmodified tree at the packet assertion and, once the packet was fixed, at the reply. (b) An item with
`test_commands_na` driven to implement through the CLI has a Done-when that names neither `Confirm by` nor a recorded
command. Red on the unmodified tree. One authoring pin in `test/shiploop-navigator-contract.test.py` for the new sentence.

Not verified. Whether models given the exit record a person-only condition as an open item rather than a vacuous `true` or
`test -f` command: read the next live runs' step-plan results (count, no threshold). Whether a handoff model finds the open
item (it depends on the model reading the ledger). Whether the checkers-style miss (a step plan with no Confirm-by clause)
causes a wrong confirmation downstream: none observed in two runs; both verify receipts key on criterion id plus bound
command.

Evidence. Round-1 runs `r1-checkers-sonnet` (results/nav-bf8832119c2c4776b0e3c8a0bb4c3e73.md: 7 criteria, 0 `Confirm by`,
all bound through `test_commands[].criteria`) and `r1-battleship-sonnet` (nav-9fe188b40bb54af2acaddee7cfd54f20.md: C1-C3 with
blank Confirm-by commands, from an unquoted heredoc in event 224), and the unfinished Grok run (nav-f9010cf5ef344cd89fb0c0fbd72fd730.md,
7 of 7 clauses). The audit corrected one citation: `callback-attempts` is a counter file (55 in the battleship run), not
empty; the support for "no run hit the unconfirmable refusal" is the transcripts. Related commits: 153160e1, 8af12178.

## S2: skill_na default (dropped)

Status: firm (a decision, not a change).

`skill_na` uptake with prose-only guidance is 2 of 3 live step plans (battleship Sonnet yes, checkers Sonnet no, Grok
battleship yes in a run that did not finish, `result.json` pass false). The one miss cost skill-assess 4.0 s with 2 turns and
skill-validate 3.0 s with 1 turn of 776.0 summed stage seconds and 185 turns; tokens per stage are unmeasured. Running the
two skill stages is the faithful default, so this is an efficiency item. The template deliberately omits the key (commit
8af12178: "a copied placeholder would be a false opt-out") and a guard test pins that. Reopen only if a later live set shows
a host that never records `skill_na` on repositories with no skill index; the follow-up is then a gate-required choice or an
observation-derived default, not a template placeholder.
