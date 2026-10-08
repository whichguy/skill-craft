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

## BC1: the plan packet says the Backchain child is a choice, and the graph check names its schema

Status: interim (the text is built and pinned; whether it changes what models do is unmeasured).

Question. The one-pass plan packet says the host "may request exactly one action `plan` / stage `draft`" and, a few lines
later, "Write the child's start contract ... verbatim". Lenses disagreed on whether the child is required (F5 and F11 read it
as permissive, F12 as required). The printed `backchain-check` is unconditional yet accepts only a Backchain-schema JSON graph.

Evidence. Both round-1 Sonnet plans had one work item and skipped the child, and said so in the accepted summary
(battleship: "The whole-operation Backchain Until Loop child was not run: linear 4-step graph"; checkers:
"backchain-check expects a JSON graph so it was not applicable to this one-item markdown plan"). Checkers got "could not run: not
JSON" (event 139) and recorded "not applicable"; battleship read `shiploop_backchain_graph.py` (events 170-180) to learn the
schema, which only Backchain SKILL.md "Plan document shape" documents. Source: round-1 analysis lenses (stage-fidelity F11,
tenet-packets F5 and F7, waste W-PLAN-DETOUR, checkers F12 and EV-7).

Decision. Say what the script enforces and nothing more: the child is the host's choice, nothing refuses a plan without it,
ShipLoop cannot see whether it ran, the planning guide's dependency audit is not optional on either route, the result's
summary names the route taken, and the printed `backchain-check` reads a Backchain plan graph (named by its SKILL.md section),
not a prose plan. The graph-check failure for a candidate that is not JSON names the same section.

Audit corrections applied. (1) The failure message does not list `goal, initial_state, steps`: that is 3 of the 5 required
top-level keys (`parallel_groups` and `unresolved` too) and a graph with exactly those three fails 8 invariants; it points at
the section. (2) "The documented owner position" is overstated. The sources are an observation ("Backchain is optional and
unchecked", `docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md`: Luna ran two loops, four Sonnet runs ran none)
and a validator-increment risk row marked Accepted; the same plan's decision table keeps "require it at plan above a measured
size" open pending its I4 and I5 comparison. The packet and the references therefore describe today's behaviour ("nothing
refuses a plan without it"), not a policy. This text change confounds plan-stage baselines across versions. (3) The retained
audit statement is `backchain-planning.md` "Retain the audit in ordinary plan notes ...", not the interaction-design duty's
"Keep these as ordinary notes, not new result fields".

Mode decision (the audit left it open). The lead prints only with the one-pass gate. That gate holds the imperative ("Write
the child's start contract ... verbatim") that reads as an order; the `converge` gate text has no such sentence, and an owner
who passes `--backchain-passes converge` has chosen the heavier route, which a statement that the child is optional would
dilute. The audit stages and a `none` run offer no whole child. A guard test pins all of that.

Not built. A structured `backchain` result field. A prototype broke the plan fixtures of at least 9 test files (quality,
callback-contract, actual-improve-cli, assumptions, improve-schedule, test-loop, lint, full-runtime) and would add a gate, a
Checked-by clause, a template key, a context-index line and about 215 characters to the plan head, for a claim that cannot be
verified under S-9 because no script reads the child's Until Loop state. Revisit only if the next Run Review needs
declared-versus-observed and the prose route proves unreliable. Making the child required (an invented policy; the Luna
one-pass child cost 23.5 minutes against the 30-minute planning ceiling; its value is unmeasured, `docs/planning-time-analysis-2026-10-06.md`).

Tests. `test/shiploop-navigator-dry-run.test.py` `BackchainStageTextTests`: the one-pass plan packet carries each of seven
phrases once, through the library text and through the dry-run CLI route, and the choice precedes the gate it qualifies
(red on the unmodified tree); a guard that audit stages, converge and none do not print it. `test/shiploop-backchain-check.test.py`
`test_exit_codes_follow_lint`: every not-JSON input names "Backchain SKILL.md, "Plan document shape"" and "not a prose plan"
(red on the unmodified tree). `BACKCHAIN_CHECK` (131 bytes, pinned) is untouched. The text sits after the status block, so the
kept head does not move.

Unknowns. Reach: the lead sits deep in a large plan packet and models read little of it (W-PLAN-DETOUR and W-PACKET-USE: 2 of
44 packets read in full; the checkers model read a slice and a grep), so the failure message is the surer channel. Whether
Luna or Grok skip the 23.5-minute child now: read the next looped Luna run for whether the child ran, its summary reason and
the plan-stage minutes. Whether models write the route in `summary`: scan the next two accepted plan summaries (both Sonnet
runs did unprompted); if prose proves unreliable, build the structured field.

## B1a: `init` records the Improve card installed beside ShipLoop (B1b not built)

Status: interim (built and pinned through the real CLI; the effect on a live run is unmeasured).

Question. The bind packet printed `--skill-card=/absolute/path/to/selected/improve/SKILL.md`, a template, and both round-1
Sonnet runs assembled the real path by hand from the CLI's own location (battleship events 60-67:
`IMP=.../skills/improve/SKILL.md; ls $IMP`, then `improve-bind`; checkers events 56-61: the same with `IC=`). The Grok `none`
run had the card path typed into its prompt by the operator. ShipLoop already knows the path: the next packet prints it, and
its Backchain and Until Loop resources are resolved from the same plugin install (`backchain_skills_root`). That violates SPEC
S-4 (copy printed values) and S-5 (the script decides what it can).

Built (B1a only). One helper in `shiploop_protocol.py` (`_new_run_card`): the explicit `--improve-skill` wins, else the card at
`shiploop_prompts.installed_improve_card()` (beside `backchain_skills_root`, so the plugin-skills-dir definition stays single,
S-12) when `shiploop_standalone_improve.resolve_skill` validates it, else nothing. It is recorded in the existing
`improve_skill` key at `init`; `workspace start` passes its flag through to `init`, so it needs no code. No new flag, state key,
migration or alias; a saved run loads unchanged. The navigator's two bind sites (`_first_callback_lines`, `_render_improve`)
print the recorded card, or, when none is recorded, a marked blank (`IMPROVE_CARD_BLANK`, not path-shaped, refused by the bind as
"skill card path must be absolute") and a sentence that names where ShipLoop looks and does not claim the file is absent. The
graph dry run records a simulation-only card, as `init` would.

Why record at init. A render-time resolution in the two navigator sites would also fix the stage defect and is smaller, but it
records nothing in `state.md` (the ledger is the authority) and cannot serve a `none` run; recording is justified by the ledger
rule and by B1b, not by the stage defect alone.

Not built (B1b). Relaxing `--planning-review none` so it needs no flag edits the SPEC S-10 2026-10-05 clause ("refused without
it") and four document pins in `test/shiploop-navigator-contract.test.py`; that clause is owner-decision text. `none` stays
strict: `_require_card_for_unreviewed_planning` still receives the explicit flag, so a `none` run or harness still types the path,
and the LEARNINGS 2026-10-05 handoff ("any E2E cell that runs --planning-review none must also pass --improve-skill") stays in
force. When the owner accepts B1b the change is `_require_card_for_unreviewed_planning(args.planning_review, _new_run_card(...))`
plus those documents; its refusal message must then distinguish "no card found at <path>" from "found at <path> but cannot be
used: <reason>" (the audit reproduced the misreport with only `skills/improve/SKILL.md` beside ShipLoop and no runtime directory).

Audit corrections applied. (1) The stage path never swallows the resolve error into a "not found" claim: the not-recorded sentence
names the path looked at, and a test covers the present-but-unusable case (a SKILL.md with no runtime directory). (2) The stale
document sentences were updated (SKILL.md, README twice, navigator.md, commands/shiploop.md); the `none` sentences stay because
`none` is unchanged. (3) The dry-run acceptance is stronger than "0 of 574 packets print the literal": the dry run now mirrors
`init`, and the test requires every `--skill-card=` value in every packet of every scenario and both delegations to be absolute,
with one labelled not-recorded sample (the dry run used `improve_skill=''` before, so 106 of 574 packets printed an unrunnable
value). The real gate is `InstalledCardCliTests`, which runs the printed command exactly as printed.

Tests, fail first. `test/shiploop-improve-schedule.test.py`: `InstalledCardCliTests` (a stage run started with no flag records the
installed card and the printed bind runs as printed; a guard that an explicit flag wins) and `NoInstalledCardCliTests` (a copy of
the ShipLoop package alone in a temporary `skills/` directory, run through its own CLI: nothing recorded, the honest blank, the bind
refusal, then the real bind; and the present-but-unusable case), the rewritten lead test (blank branch) with a recorded-card
sibling, and the one `none`-test line that said a stage run records nothing. `test/shiploop-navigator-dry-run.test.py`
`BindCommandTests`. The git-lfs lesson applies to every real-git test here: `CliRunCase` sets `GIT_CONFIG_NOSYSTEM` and
`GIT_CONFIG_GLOBAL`.

Coordination. `test/fixtures/run-review/state-stage.md` carries `improve_skill: ''` and `test/shiploop-run-review.test.py` says
"none resolves the card at init". After B1a a genuine stage state records the card at init, so the Run Review session (it owns
`skills/shiploop-run-review/**`) should refresh that fixture; no edit was made here.

Unknowns. The quality and test-loop terminal gates read `improve_skill` and skip when it is empty, so they are active from the
first item instead of only after `spec` binds; in real stage runs the bind happens at `spec` anyway and no suite depended on the
skipped gate. A hard-linked install fails `_safe_file` (`st_nlink` must be 1) and falls to the honest blank; none observed. Codex's
plugin cache holds one version, so a mid-run plugin update removes both the CLI path and the recorded card (every packet command
already points into that directory). The retained lazy bind (a blank plus a sentence) is the one place the one-supported-version
rule is arguable; it is pre-existing and documented, and the choice of refusing `stage` init when nothing resolves is the owner's.
The audit ran `resolve_skill` on every skill-craft layout on this machine (not re-run here): the Claude cache (1.0.0 to 1.24.0),
Claude marketplaces, the Codex cache (1.24.0), Cursor local, Grok installed-plugins and marketplace cache, and the OpenCode
symlink; the old claudecraft plugin's improve card is rejected, which supports resolving by location and not by name.

## P4: the test-strategy probe runs against a stand-in page

Status: interim (the duty text is built and pinned; whether a host now surfaces its access gap in planning is unmeasured).

Question. The 2026-10-07 Grok run's strategy probe was `Chrome --version` and the gap surfaced at W2 implement, about 50 minutes in
(`test/shiploop_e2e/LEARNINGS.md`, "The Grok block, what is proven"). The duty was then changed to ask for a probe that "loads a
local page and reads its title back". Did that wording work?

Evidence. In the 2026-10-08 round-1 Grok `none` run (`/Users/dadleet/e2e-runs/20261008/r1-battleship-grok-none`, its
`.shiploop-runs/*/worktree/docs/shiploop/test-strategy.md`, section "What is out of the default suite") the probe was: "`curl` to
`http://127.0.0.1:3000/` exited 7 (connection refused). No page title could be read. This session has no browser MCP. TC-16 stays
unobserved until system test, after a local server exists." At test-strategy time there is no product and no server, so the request
fails whatever the browser can do; the strategy concluded "no browser", and the access gap that mattered (headless Chrome stayed on
`about:blank` in the Grok host) surfaced at `system-test-author` after a 21-minute, 71-turn Chrome flag iteration (LEARNINGS
2026-10-08 and commit 847fa64e). The earlier fix had named the right probe (load a local page and read its title) but not that the
page has to be one the stage writes itself.

Change. `DUTIES['test-strategy']`, the paragraph "Settle these now": the case is probed by doing its first step, not its version;
the product does not exist yet, so the probe runs against a stand-in and not the product's own address; for a browser, a one-line
page written in the run's scratch directory (a directory every packet prints), opened by `file:` URL or from a throwaway static
server stopped afterwards, with its title read back by the tool as the case will use it; for an account or a service, a harmless
read the tool can make today. A failed probe is still an access gap recorded now with the requirement it leaves unobserved, and the
case still keeps its own opt-in command. The paragraph is after the status block, so the kept head does not grow
(`test/shiploop-status-display.test.py` passes); `CaseEndStateTests` and the other `SettledFactTests` pins pass unchanged.

Test, fail first. `SettledFactTests.test_test_strategy_probes_a_host_tool_against_a_stand_in_because_the_product_does_not_exist_yet`
in `test/shiploop-guidance.test.py` pins the stand-in obligations, the obligations that must stay, and the rendered packet under both
delegations (eight subtests red on the unmodified tree).

Not verified. Whether a host now writes the stand-in page and records the access gap during planning; read the next Grok and Luna
`test-strategy.md` files (the probe line and the "What is out of the default suite" section) for a probe that loaded a page and read
its title. A host with no way to open any page still records the gap; the change moves when it is learned, not whether it can be fixed.
