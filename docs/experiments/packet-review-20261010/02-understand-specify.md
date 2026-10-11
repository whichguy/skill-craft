# Packet review report: understand-specify

Verbatim final report of one read-only reviewer (2026-10-10). Packets: checkers-1, battleship-1, s6-after-spec (ShipLoop 0.58.0, release 1.26.0) and older runs. Scratch analysis scripts were not kept; counts are the reviewer's.

REVIEW OF PACKET KINDS: intake, discovery, research, spec, test-strategy, and the Improve parent packets for spec and test-strategy

How I read them. Packets: checkers-1, battleship-1, s6-after-spec (a planning_review none run), plus the older runs' sizes. I diffed each packet against the previous stage's after normalising ids and paths, and the checkers and battleship packets differ only in the request text and the stage results quoted in them. I also read the transcripts and events.jsonl to see what the models actually read.

Findings about how packets are used:
- Only the intake packet was read whole in checkers-1.
- Discovery, research and test-strategy were run from the printed head (goal, done-when, template) plus one grep of the file for "keeps these up to date".
- In spec, checkers-1 ran one sed over the guidance section, and battleship-1 grepped for the docs paths.
- The head and stage_spec.done_when are the effective instruction. A duty obligation that is not in done_when and not in the head is usually unread.
- All locator anchors I checked (52 paths/anchors across these packets) exist. Under S-6 I do not count cross-packet repetition as waste.

Refusals and rework in the 14 runs:
- Intake, discovery and research drew 0 refusals in the 3 runs that have per-stage counts. In the older runs, 1 intake refusal (r1-battleship-sonnet: evidence_refs cited a notes/intake.md that did not exist) and 4 credential-screen refusals at spec/test-strategy (docs/shiploop/spec.md lines in 3 older runs) are visible; they cannot be mapped to a stage.
- In the 2 newest runs that have per-stage counts, spec and test-strategy drew 1 refusal each (battleship-1: improve-commit; a zsh parse error). Neither is an engine refusal of a producer result.
- The Improve child changed the spec in 9 of 9 stage-mode Sonnet runs (git log of docs/shiploop/spec.md). It changed test-strategy in 6 of 9.

========================================================================
STAGE intake (packets read: 14, bytes 27,322-29,553; duty text 1.7 KB)
Accurate: issues - the text is true, but three sentences describe other stages.
Grounded: yes - the request block, counts (0/7, 0/9), paths and the clean-main return route all match the worktree and workspace.md.
Sufficient: yes, with about 4 KB irrelevant to intake.

P-intake-1 (low). COMMON says "so the next Improve packet can recover them", but the same packet ends "no Improve child runs for this stage". Source: shiploop_prompts.COMMON. Fix: print the clause only for stages in reviewed_stages.
P-intake-2 (low). The _PLANNING_HANDOFF paragraph ("At plan and step-plan, consolidate...") is carried by every prelude stage (560 bytes). The result-template note also names fields intake never has ("work_items, assumptions, steps, test_commands"). Fix: scope both to plan and step-plan.
P-intake-3 (low). "This stage keeps these up to date: docs/shiploop/README.md" comes from STAGE_FILES["intake"]. The README is not gated until prepare, never defined at intake, and checkers-1 skipped it (evidence_refs: []). Fix: say what README.md holds, or drop it from intake.
P-intake-4 (low). "the last 1 commit messages" (knowledge_home.stage_lines needs a singular form).
P-intake-5 (low). The return block is 2,572 bytes of workspace, plan-return and review-return commands (13 lines) in all five prelude packets, and "workspace return" is unavailable until release. Four test-guide locators (Consumer testing, Repeatable test-suite, Selected-case reconciliation, Real-boundary selection) add about 0.7 KB. Neither helps intake or discovery. Fix: print the return block from prepare onward, or only the line "return is unavailable until release".

========================================================================
STAGE discovery (packets read: 14, bytes 40,721-43,722; duty 5.9 KB plus the 3.1 KB interaction block)
Accurate: issues - the allowance is named with no size, and some wording points to later stages.
Grounded: issues - one locator names a path that does not exist.
Sufficient: both - 0 refusals, but the allowance size and the notebook are unspecified.

P-discovery-1 (medium). The packet says "One investigation allowance spans...discovery and research", but never gives its size. The default is 15 active minutes, 64 host actions and 3 experiments (research-loop.md "Budget, stopping, and convergence"). The packet's anchor, #recursive-discovery-and-experiments, is a 340-line parent section. Fix: add one clause with the numbers and point the anchor at #budget-stopping-and-convergence (shiploop_navigator.py around line 3457).
P-discovery-2 (medium). "Planning investigation notebook: .../.shiploop-improve/<run>/planning-investigation.md" does not exist in checkers-1, and no packet says when to create it. The duty says "retain the plan and its outcome in the existing note". Fix: say "create it if a plan trigger applies", or name environment.md.
P-discovery-3 (low). The packet lists the stage itself under "Current planning sources" as "no current accepted result; do not reuse an invalidated result". Nothing was invalidated. It also lists the plan-stage "Planning experiments guide".
P-discovery-4 (low). INTERACTION_DESIGN (also in research and spec) says to put locators "in each affected work-item context...for the normal Improve handoff". Neither exists at discovery or research. In none mode only the Improve phrase is swapped; "work-item context" stays.
P-discovery-5 (medium). The State and information lifecycle paragraph (about 2 KB, identical in discovery, research and spec) says "decide and state" but names no place to record the decisions. No done_when item checks it. checkers-1 got it right only because intake answered it.

========================================================================
STAGE research (packets read: 14, bytes 35,702-39,226; 83% identical to discovery's, 6.0 KB new)
Accurate: issues - it points to a record that does not exist.
Grounded: issues - the same missing destination.
Sufficient: insufficient on the assumption list, excessive on carried blocks.

P-research-1 (medium-high). The duty says "List each load-bearing assumption in that decision note...The plan's assumption list starts from it". Research has no STAGE_FILES entry, so the packet prints no "keeps these up to date" file. The done_when has only two items and does not mention assumptions. The full checkers-1 research result has no assumption list, and evidence_refs: [] in checkers-1. 0 of the 3 full results I read (checkers-1 plus the summaries) list assumptions. Fix: set STAGE_FILES["research"] to the file that holds the decision note and add a done_when item, so the plan's claim is true.
P-research-2 (low). The 3.1 KB interaction block plus the service, cache and async paragraphs are carried although the discovery result says "no services". They are conditional ("affected service choices") but 10 or more lines long.

========================================================================
STAGE spec (packets read: 14, bytes 38,326-41,963; duty 1.9 KB plus 2.3 KB Backchain)
Accurate: issues
Grounded: yes - the feature directory, run suffix and Backchain locators check out.
Sufficient: both - an optional Backchain budget of about 1.2 KB, while the instruction a spec needs is missing.

P-spec-1 (high). The producer packet says the Improve child "checks the result against the Done-when conditions above". The Improve packet actually applies PLANNING_REVIEW_FOCUS (replayable concrete values, weaker stand-ins, commands run once, dropped IDs, unsourced claims). Evidence: Improve changed the spec in 9 of 9 stage-mode Sonnet runs. Commits include "pin error-response shape and route set" (checkers-1), "pin row/col indexing and response shapes" (battleship-1), "give every requirement a Confirm method" (r3-checkers), and "pin HTTP methods and last-ship response" (r2-battleship). That failed an existing done_when item ("says how it will be confirmed"). Fix: copy the PLANNING_REVIEW_FOCUS bullets into DUTIES["spec"] and DUTIES["test-strategy"], and change _improve_line in shiploop_navigator.py to say both. S-6 asks the producer packet to say how it is reviewed.
P-spec-2 (medium). The spec-level Backchain instruction is only in backchain-planning.md ("At spec, check outcomes and missing prerequisites without authoring future receipts"). The packet instead carries repair/revise machinery plus the Until Loop budget, and tells the model to hand-write a contract. That contradicts S-4/S-5, an open item (a02) the SPEC acknowledges. No recent run used any of it. The packet also says "Run the printed backchain-check after each candidate revision", but that tool reads a Backchain plan graph, not a prose spec; the explanatory sentence is printed only at plan. Fix: print the spec-level sentence and a one-line pointer to the audit route, and drop the budget text outside plan.
P-spec-3 (medium). The spec output path is not in the head. battleship-1 grepped for the docs paths; the checkers-1 model used sed over the guidance section. The "keep every R-<n>" rule is file-only and appears only when the knowledge-home lines are printed. Fix: add the "keeps these up to date" line and the ID rule to packet_head in shiploop_navigator.py.
P-spec-4 (low-medium). "Checked by" lists only the common gates. knowledge_home.check also screens every docs/shiploop/*.md for credential-like key:value lines and refuses a dropped R-ID. The older runs got "These knowledge lines look like credentials" at docs/shiploop/spec.md (4 refusals in 3 runs). Fix: add a clause in _stage_gates for stages in knowledge.STAGE_FILES.
P-spec-5 (low). In none mode, COMMON's "so the next Improve packet can recover them" and the spec duty's "planning and Improve" are not in _NO_REVIEW_SWAPS.

========================================================================
STAGE test-strategy (packets read: 14, bytes 36,360-39,882; duty 4.9 KB plus the 1 KB facility handoff)
Accurate: issues
Grounded: issues - stale summary and one omitted input.
Sufficient: both - the ID rule and the UI decision are missing; carried facility and baseline text is heavy.

P-ts-1 (high). The duty says "say which test ids it may print" and "A passing command names the test IDs", but never states the whole-word rule that shiploop_test_counts enforces later (ID_WORD_RULE). That rule appears in step-plan and test-spec duties only. Evidence: the Improve child committed "require TC ids in test titles...ShipLoop confirms listed ids by their appearance in the runner output" in checkers-1 (57201cf). Fix: append ID_WORD_RULE to the "Settle these now" paragraph.
P-ts-2 (medium-high). The packet says "For browser-based UI criteria, plan browser actions...HTTP success alone does not validate them", but also calls the tools "capability examples, not a mandatory tool checklist", and the done_when item is conditional ("each case that needs a host tool"). Sonnet decided "no browser needed" in 5 of 9 UI runs: checkers-1 ("no host tool needed...real-browser play...unverified"), battleship-1, r2, r3-battleship, v1230. Grok and r3-checkers planned a browser case (r3-checkers only after the Improve commit "add UI click-through check"). Fix: state which of the two applies when the request names a page people use: either a browser-run case or a recorded unverified outcome with owner and due stage.
P-ts-3 (medium). "Results this stage builds on" lists spec and research only (stage_spec reads=("spec","research")). The duty says "consume the observed initial baseline", which is discovery's result. "Current planning sources" does list discovery. Fix: add "discovery" to reads for test-strategy.
P-ts-4 (medium). "Last accepted" shows the pre-Improve summary: "spec (reviewed by Improve): ...R-1..R-14", while the spec at that point had R-15 (d171177). Fix: have improve-complete append the changed files and commit ids to the accepted summary shown.
P-ts-5 (low). "Repeatable test-suite guide" is listed twice: whole file (25.7 KB) and the anchored section. The duty says "Read the Repeatable test-suite guide" while the head says never read a whole reference. "Settle these now" has no clear antecedent.
P-ts-6 (low-medium). "Checked by" has no mention of test-strategy.md, which is gated only at prepare (CLOSES), two stages later. Fix: name the gate at this stage.

========================================================================
STAGE Improve parent packets for spec and test-strategy (packets read: 10 spec, 10 test-strategy; bytes 45,278-48,339)
Accurate: issues - minor wording; also one packet I could not read.
Grounded: yes - the receipts, opening path, run id and state fields all exist; the 9,216 and 4,892 byte figures are computed.
Sufficient: both - insufficient at the top, about 3.5 KB of the 9.5 KB duty irrelevant to spec.

P-improve-1 (medium). The improve-commit command and the exact commit-message path sit at byte about 30,390 of 47,225, far below improve-start (about 26 KB). battleship-1's model wrote opening and a review pass, ran `improve-commit --help`, then wrote commit-message.txt instead of the printed .md path and was refused ("commit message must be the printed file...").
It had also written "Authority: commit via improve-commit if the packet prints it". checkers-1 grepped for the command. Fix: move the commit paragraph beside improve-start in _render_improve (start_lines).
P-improve-2 (low-medium). The spec Improve duty carries paragraphs for UI planning ambition, repository-local skills, remote-resident tests, test facilities and "RED-stage handoff...release/verification" (about 3.5 KB). The Backchain owner paragraph (about 0.9 KB) talks about "active_backchain child, nested Until Loop, retry dispatcher" and has nothing a spec reviewer can act on. Fix: gate these by stage.
P-improve-3 (low). "Each reviewed step's task/ready/done criteria remain its sole assignment" is stale at spec and test-strategy (no steps yet).
P-improve-4 (low). The improve-bind packet, the first Improve packet a model reads, is overwritten by the improve-start one (same file name, packet_path); the model read the file at both phases.

========================================================================
FIVE FINDINGS TO FIX FIRST
1. P-spec-1: put the reviewer's PLANNING_REVIEW_FOCUS into the spec and test-strategy producer packets, and fix the "checks against Done-when" sentence (9 of 9 spec rewrites, 6 of 9 test-strategy).
2. P-ts-1 and P-ts-2: add the whole-word ID rule and the explicit browser-or-record decision to the test-strategy duty.
3. P-spec-3 (and the same gap for test-strategy): put the output file locators and the R-ID rule in the printed head.
4. P-improve-1: move improve-commit and its exact message path up with improve-start.
5. P-research-1: give research a named decision-note file and a done_when item for the assumption list.

QUESTIONS I COULD NOT ANSWER
- Content of the improve-bind packet (overwritten; see P-improve-4).
- The Improve child's own packets (the runtime writes them, not the navigator).
- Whether a brownfield repo makes the unread discovery duty text (service, MCP, connected knowledge) insufficient; all 14 runs are greenfield.
- Which stage the 4 older credential refusals belonged to; the run docs carry no stage for them.
- Only 3 of 14 runs have fidelity.refusals.byStage, so refusal counts for the older 11 are from failure lines only.
