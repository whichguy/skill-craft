# Changelog

Written by scripts/release.py.

## 2026-10-08

### skill-craft 1.26.0

- Skills: shiploop 0.58.0

### shiploop 0.58.0

- ShipLoop now creates the directory of a bound Improve child's opening file whenever it prints the packet, so the printed step "write the opening file" needs no `mkdir`. A run bound earlier gets the directory on its next `next`.
- The return-route sentence that every worktree packet prints now says, right after its first sentence, that plan-return commits files left uncommitted, so a run commits nothing by hand for the return except a file plan-return reports as not committed (a credential-like one). The old wording could be read as needing a hand commit before the return, and its working-tree fallback now reads "still leaves a file uncommitted".
- ShipLoop now also refuses a test run of an item's command that ran fewer tests than the most any run of that command it accepted for the item has run since the item's latest step plan, so a test removed or newly skipped to pass is no longer a pass. The test-author probe sets the first number, test-refine (whose duty is to explain removed cases) is not held to it and restarts it, and a revised step plan starts it again; the refusal names both numbers and the stage's real exit, and the packets state the rule.
- The test-strategy stage's "Done when" list, which every run displays, now asks that each case needing a host tool (a browser, a device, an account, a service) names it and cites the output of probing it now against a stand-in while the product does not exist, and that only a failed probe is recorded as the access gap. The probe's how stays in the stage duty.
- ShipLoop's refusal for a listed test ID that the runner prints only inside a longer name (a test titled `TC-4a` for the listed `TC-4`) now states the whole-word rule, quotes the line and shows the rename, instead of telling the model to print test names. The rule is also stated once in the step-plan, test-author, test-red and test-loop packets.

### skill-craft 1.25.0

- Skills: shiploop 0.57.0

### shiploop 0.57.0

- Refusals a model reads through `head` or `cut` now say what to do on their first line: a knowledge-close refusal puts "Before <stage> is done, write:" and the absolute paths there, an invalid return-plan status names the allowed values and the `review-return` verb, and `backchain-check` tells a Markdown candidate that it must be the plan graph JSON and where that shape is defined.
- The one-pass plan packet now says the whole Backchain child is the host's choice (nothing refuses a plan without it, and ShipLoop cannot see whether it ran), that the dependency audit is not optional, and that the result's summary names the route taken. A `backchain-check` on a candidate that is not JSON now points at Backchain's "Plan document shape" instead of leaving the model to read the checker's source. The text describes today's behaviour, not a policy: requiring the child at plan stays open pending the Backchain validator comparison, and plan-stage timings are not comparable across this version.
- A stage whose done runs a knowledge check now lists every file that check requires, so test-spec and release-plan no longer meet a refusal for a file their packet never named.
- The packet a model re-reads while an Improve review runs now states the stage's goal and the Done-when conditions the review holds the result to, and the producer's packet says its Done-when is what that review checks.
- `init` and `workspace start` now record the Improve card installed beside ShipLoop when `--improve-skill` is not given and the card validates, so the first Improve bind packet prints a real path instead of a template. Where no installed card validates, the packet prints a marked blank and the place ShipLoop looked; `--improve-skill` still wins and `--planning-review none` still requires it. `--help` now says the same: the flag is required with `--planning-review none`, and a stage run without it records the installed card.
- The output of `workspace plan-return` and `review-return`, and the refusal of a blocked `return`, is now held to one print limit in all, not one per path list, so a very long list is cut at a path and the rest counted while the last line stays the next command. `review-return` counts the paths it excluded and no longer lists them a second time beside the excludes a review decided.
- Every isolated-run packet now states how the return will go, taken from `workspace.md` (replacing a generic sentence that was wrong for a clean start), the release-plan and release-check packets print tested rollback recipes for each return kind, and `review-return` reports the expected return once nothing is undecided, by the same rule `return` follows. The release-plan and release-check duties tell the model to write and verify the rollback against that route.
- `review-return` now refuses an absolute, `..` or empty `--keep`/`--exclude` path the way it refuses an unknown one, with the undecided paths and the command, and its rule says the paths are relative to the execution checkout. The rollback recipe for a fast-forward with later commits says it also undoes what those commits changed, and points to the diff recipe for keeping their work.
- New `shiploop workspace review-return --keep PATH... --exclude PATH...` records the return plan's keep/exclude decisions, so a model no longer hand-edits `return-plan.md`. `plan-return` now prints the tally, every undecided path and the exact command (and keeps the decisions already recorded for the same path on a fresh plan), a blocked `return` names the undecided paths and the verb on its first line, and a stale plan names `plan-return` as the next step.
- ShipLoop now creates the run's `notes/` directory beside `scratch/` when it prints a packet, so the pass log every packet names can be written (and an `evidence_refs` entry for it resolved) without a `mkdir` first. The log itself is still the model's to create.
- The `notes/` row of the state-files reference now says ShipLoop creates the empty directory when it prints a packet, and that the notes and the pass log stay the host's to write.
- The step plan no longer tells the model to mark a criterion `Confirm by: unconfirmable here` in `criteria`, a shape the gate refuses; it says a condition no command can confirm is recorded as an open item in the summary, and the refusal for an uncovered criterion names the same exit. The implement Done-when no longer names a `Confirm by` field that an item without tests does not hold.
- The test-strategy duty now says a host-dependent tool (a browser, a device, an account, a service) is probed against a stand-in, such as a one-line page opened by `file:` URL or from a throwaway static server, when the product does not exist yet; a request to the product's own address says nothing about the tool.
- Intake, discovery and research ask for a recorded default or open item instead of a person or a suite that may not exist, integrate no longer asks the model to commit (ShipLoop does) and an inline run no longer reads about bound chains, and the Improve packet no longer calls its own review independent.
- A done product-acceptance result now lists, in `unverified`, each request outcome no executed check observed, with its reason, owner and due stage (an empty list says every outcome was observed). ShipLoop refuses a missing list, an incomplete or placeholder entry and a due stage that is not a later stage, and prints each entry at its due stage, the whole list at handoff and a table in the report.

### skill-craft 1.24.0

- Skills: shiploop 0.56.0

### shiploop 0.56.0

- The Checked by line of a stage with no script-run check no longer says nothing automatic runs. It says ShipLoop refuses a result with a mechanical fault (no outcome or summary, an absolute evidence_refs path that does not exist, an explicit credential pattern, and at plan, step-plan, document, system-test-author, release-plan and the knowledge closes the extra faults those stages refuse, including a skill file beside a recorded skill_na at step-plan and a skill file changed after the step plan recorded skill_na at document), that a refusal does not advance the run so the fix is to correct the result and run the same complete command again, and that ShipLoop does not judge the work.
- The run narrative's Pace row now states what was recorded, the steps accepted and the time they took, and no longer adds an "about N min left" forecast. The forecast was an average of unequal steps and read 2.4 to 6.8 times too short after the second step of five recorded preparations. `references/status-display.md` shows the new row.
- The pass-log line in every packet and in the run context index is now one conditional rule that stays true whether or not the log exists: create it when the pass starts, append after each pass what you checked and what is left, and after a reset open it first if it exists. The durable-files reference now says which source is authoritative for the notes, inbox and results copies and for test commands.
- In an isolated run, `release-verify` now runs the consumer checks `release-plan` recorded in a clean copy of the result the workspace return delivered (read from the return receipt into `consumer-check` under the workspace root, never from or into your checkout), so a check that passes only because of a file the return excluded, an ignored file or a later commit is refused with the copy's location, its usual causes and the stage's one exit, `replan`. When no return has been made yet the checks run in the work area as before, and the packet, the test record (`observed`) and the handoff say that they did not observe your checkout. When the return state cannot be read (a corrupt receipt, a busy workspace), no command starts: the attempt is `could-not-run`, which does not count as a refused run, and the reply says so instead of blaming the item. In-place runs run where they always did, in the checkout, and now also record that in the test record and report it in the handoff. Every run's handoff packet carries one `Consumer checks (release-verify)` line saying where the checks ran, or that `release-plan` recorded none. The `release-plan`, `release-verify` and `handoff` duties, SKILL.md and the workspace lifecycle card say where the checks run and ask for paths relative to the directory a command starts in, checks that bring what a fresh consumer needs, and no writes into your checkout.
- A work item sent back to its step plan now gets a packet that names its previous step plan and the result that sent it back, and asks for an amendment rather than a new plan: criteria, steps, paths and test commands the evidence does not touch stay as written, and the summary says which rows are new or changed and which are carried over. No state, protocol or gate change.
- A done step-plan result may carry `skill_na`, the reason no repo-local skill is selected, created or changed for the item: ShipLoop then records skill-assess and skill-validate as not applicable to that item, with a history row and a result file whose text starts "Not applicable to this item" and carries that reason, instead of issuing them. A step plan that lists a skill file in `paths` is refused with `skill_na` (at `complete` and at `improve-complete`), and `document`'s done is refused when the item's real diff touches a skill file; without `skill_na`, or after either refusal, both stages run as before. The skill-file lists are the new `skill_surface` data in `references/path-classes.json`, not a path class.
- A result file that does not parse (no shiploop-state fence, invalid JSON, an unterminated fence or a duplicate key) is now refused as a rejected request, with the file path, the parser's reason and the instruction to fix the file and run the same command again. It no longer gets the lost-state recovery text that told the model not to infer a next action; real storage faults keep that text.

### skill-craft 1.23.0

- Skills: shiploop 0.55.0, shiploop-e2e-audit 0.7.1, shiploop-run-review 0.1.2

### shiploop 0.55.0

- The test stages now state when a test case is finished: a case ends validated (executed, and the observation matches), validated another way (the first method could not observe it, so the method changed and the new one was executed and passed, with what changed and why), or unachievable (a named reason and the requirement it leaves unverified, reported as blocked with `blocked_by access`, or revise/replan when the plan is wrong). A case written but not run, or recorded as not run, is not an end state. The rule is in the Test consideration of test-author, test-green, regression, system-test-author and system-test, and the system-test-author duty asks it to run each system command once while authoring.
- A test runner recorded as suite `check` is still counted: when a check command's output shows a runner summary, the record carries the counts and a zero-test run is refused (`no-tests`) instead of passing on its exit code. The test-strategy duty now asks for a capability probe of a host-dependent tool (for a browser, load a local page and read its title back, not the version) and for a failed probe to be recorded as an access gap with the requirement it leaves unobserved.
- The README now opens with ShipLoop's main tenet: context can be cleared or compacted between any two stages, so every packet restates what its stage is for, how it operates and how its result is checked, even when the previous packet said so too. Only repetition inside one packet is waste. No behaviour changes.
- The stage `select-work` is now `get-next-work-item`, in the stage table, the packets, the status and report labels, the references, README and SKILL.md, the dry-run graph and the audit harness replay. A run saved under the old name is refused with a message that names both names and says to start a fresh run (one supported version; no mapping). Committed history that records the old name (baselines, evidence files, journals) keeps it.
- A system command row may be marked `"host_dependent": true` (its cases need a host tool: a browser, a device, an account, a service). At `system-test` ShipLoop then also runs the accepted regression commands and refuses when any of that row's `ids` is shown, run or failed, in their output, with the remedy to give the case its own opt-in command or make it skip unless an opt-in setting is present. The system-test-author duty and SKILL.md say so. This is the script check behind the settled-fact line from the earlier test-strategy change: a delivered repo's plain `node --test` that needed macOS Chrome passed every gate.
- A packet printed while an Improve child owns the action is now written to `packets/<action>-improve.md`; the producer packet stays at `packets/<action>.md`. Before, the child's packet overwrote the producer's at the same path, so after a run the producer packet of every reviewed planning stage (spec, test-strategy, plan, step-plan, test-spec) could not be audited (10 of 46 visits in one real run).
- The test-loop and quality-loop duties no longer tell the model to save each returned packet to a "printed latest-packet path" and to write the terminal packet itself; the packet prints a receipt the runtime writes and says not to touch it, so the two now agree (the runtime's receipt carries `next_argv` for a resume). The plan duty asks each work item to state its module format and loadable seam, and the test-strategy duty asks the plan to say which test ids each command may print and to keep a host-dependent case (host browser, device, account, service) out of the project's default test command, after naming and probing its tool.
- The test counter now reads `node --test` (spec and TAP reporters, colour codes stripped), so `min_tests` is enforced and a test file that fails to load reads as zero tests instead of a failing test that ran. A test counts as skipped only by its runner's own marker (a skip glyph, `# SKIP`/`# TODO`, pytest `SKIPPED`, unittest `... skipped`, go `--- SKIP:`), never because its title contains `pending`, `skip` or `todo`; a TAP `# Subtest:` announcement no longer shows an id as run. The refusal text and the test-strategy packet name the node reporters that work (spec, tap) and the ones that do not (dot, junit). README and SKILL.md corrections: no packet or hook clears the conversation, `skill-assess` is the reuse/update/create decision, the default one-pass Backchain loop and `--planning-review` are described, and the test loop has no iteration limit.
- Every producer packet now has a `Checked by:` line under its Done-when list: the script checks ShipLoop runs when the stage reports done (lint gate, test-loop terminal packet and rerun, red probe, quality-loop terminal packet), or, for the stages with none, that nothing automatic runs beyond the result's form and the model confirms each Done-when condition. The Improve-phase packet gets a `Checked by:` line naming the `improve-complete` callback and what it validates and imports. A new hermetic suite, `shiploop-packet-completeness`, renders the real packet of every stage and every Improve-phase packet from a cold read of `state.md` and checks the five things the main tenet asks of a packet: what the stage is for, how it operates, how its result is checked, what it must produce, and how to recover.
- Two writes no reader used are gone. The lint pass no longer writes a `.err` log per tool call (stderr is quoted in the lint report) and writes the `.out` log only when the report cites it as a byte-exact copy; a real run had 72 such files, all empty and never opened. The context index no longer points a cleared model at a `-latest.json` loop packet that nothing writes; it points at the loop receipt the runtime writes.

### shiploop-e2e-audit 0.7.1

- The publication/freshness preflight now reads skill-craft's one-plugin layout: the released ShipLoop and Improve are the copies under `plugins/skill-craft/skills/<leaf>`, the catalog has one `skill-craft` entry whose version is the bundle's, and each skill keeps its own version. Before this, every live case was refused at the preflight with `required-package-tree-is-missing`, because the gate looked for a `plugins/<leaf>` per skill that the repository no longer publishes. A repository or catalog in the old per-skill layout is refused, not read.
- The replay oracles (`dag_replay`, `behavior_capture`, and the replay test) name the renamed ShipLoop stage `get-next-work-item` instead of `select-work`; no other behaviour changes.

### shiploop-run-review 0.1.2

- The Run Review exporter and page follow the engine's rename of the stage `select-work` to `get-next-work-item`: the phase table, the page's stage flow, the stage catalog (`defaults/stages.json`, regenerated) and the stage card name it `get-next-work-item` ("Get next work item"). The old name stays in one alias table, in the exporter and the page, so exports of runs of ShipLoop 1.22.0 and earlier, the committed evidence and the page's database still render, in the same phase and with the same catalog entry. Merge this change together with the engine's rename: against an engine that still names the stage `select-work`, the catalog and phase-table tests fail by design.
- The export reads the engine's new packet layout, in which an Improve child's packets go to their own file `packets/<action>-improve.md` and the producer packet that was sent stays intact in `packets/<action>.md`. A visit with both files gets its producer packet document as before and a second document `<runKey>--<action>-improve` (`kind` `improve`), and its stage row gets `improvePacketBytes` and `improvePacketDoc`; the packet checklist (`carried`) is read from the producer packet, so a reviewed stage's checklist is now a real one. A run of the old layout (ShipLoop 1.22.0 and earlier: one file per action, the child's packet replacing the producer's) is read as before and its visit keeps the `packetImprove` mark. `facts.md` counts both. SCHEMA.md documents both layouts and points to the E2E session's record register of 2026-10-07 as the place where record kinds are classified.
- The page's Specify expectation (`phase-1`) keeps its original sentence and now also says what the engine does under each `planning_review` mode, in the words of the SPEC's S-10 carve-out of 2026-10-05: `stage` starts an Improve child after each of the five planning results, `none` starts none and accepts each result without a review loop (the spec and test strategy are then committed unreviewed), and the Improve children after `system-test-author` and `release-plan` and the last `carry-forward` start in every mode. A `none` run is no longer read as a defect of Specify; until the default changes every new run is `stage`, so the added text describes the exception. The change is a revision recorded in `defaults/expectations.json` (finding o44, option a26); a page shows it after the defaults upgrade (`export.py --defaults --live`).
- The run export now records the plan and how the run went through ShipLoop's steps loop, and keeps each visit's packet text. A run document gains `workItems`: per work item its `stepPlans`, `loops` (the first pass plus one per accepted `revise`), `revises`, `repeats`, `implementVisits` by outcome, and the steps of its latest accepted step plan with the implement visit that executed each (`null` for a planned step no visit executed), plus the run's `stepsPlanned` and `stepsExecuted`; each stage row names its `workitem`, `loop` and, on an implement visit, its `step`. All of it is counted from `state.md` history and the accepted results, and a run whose records cannot tell (a seeded plan, the ask-agent route, a step plan with no readable steps) omits the number with its reason in `unmeasured`, never a 0. A new `packets` collection holds one document per visit with a packet file (`<runKey>--<action>`: size, sha256 and the text, cut at 150,000 bytes on a line boundary when longer); it is written under `docs/packets/` and listed last in `writes.json` for upload in batches of its own, and it is never part of the committed `review-export.json`. SCHEMA.md and SKILL.md document the fields, the definitions and the upload.
- Step 1 of the Run Review page gains a "Plan and execution" panel below the six cards: one row per work item with its title, a "steps loop once" or "steps loop x2" badge, a counts line (step plans, implement visits and their outcomes), and one cell per planned step, filled with its visit number when an implement visit executed it and outlined "not run" when none did, with the step tasks in a collapsed list and the run's "Steps planned N, executed M" line; a run whose document has no `workItems` reads "Not measured" with the exporter's reason, never 0. Tapping an item shades its visits in the picture; tapping a step selects the visit that ran it or says it was never executed. A tapped visit's detail names its work item, steps-loop pass and step, and gains a "Packet" box that reads the visit's `packets` document with one on-demand get when opened (the page never subscribes to the collection), shows it in a scroll box with Copy, its size, digest and any truncation, and says "packet not uploaded for this run" when the document is missing. The page needs one republish.
- The run export now records the run's `planning_review` option (ShipLoop 1.22.0) and says what it means for the Improve numbers. A run document gains `planningReview`, the value `state.md` recorded as written (`stage`, `none`, or any other value shown verbatim) and `not recorded` when the key is absent, never a default, and, only for a `none` run, `improveScope` ("planning stages skipped by design (planning_review none)"): under `none` no Improve child starts after spec, test-strategy, plan, step-plan or test-spec, so the run's Improve totals stay what its `improve/` directories hold and are no longer read as a missing measurement. `facts.md` gains a "Planning review option (state.md)" line and the Improve line carries the scope. The page's run header prints `planning review: none` (nothing for an older run, so it reads as before) and shows a chip on a `none` run; its Improve card keeps the measured passes and minutes, prints "no Improve at planning stages (planning_review none)" and no share of elapsed; and the detail of a planning visit in a `none` run says "Improve: not run by design (planning_review none)". SCHEMA.md documents both fields and the `general.review.json` bundle for findings that belong to no single run, and SKILL.md says that a finding spanning runs goes there. The page needs one republish.
- Step 1 of the page now shows a stage card for each visit: tap a column of the picture, or a row of the new "Stage cards" list below it (one row per visit with its stage, purpose, outcome, exit-check chip, minutes, packet size sent, result size written and how many stages declare reading it; a run of skipped visits is one row "xN skipped"). A stage is named by its stage name with the hyphens as spaces and the first letter upper-cased ("Get next work item"), with the raw name as the tooltip and, when it differs, as secondary text. The card has three labelled blocks. Sent: the stage's purpose and exit-check kind (script-run, review loop or model judgement, with the reason), the packet size, a tick or cross for each of seven items the packet text carried ("not found in the packet text" is a statement about the text, not about what the model needed; a visit that started an Improve child says its packet file is the child's and shows no checklist), the packet head (the first 12 non-empty lines, loaded on demand with the same single read as the Packet box) and the Packet box. Done: outcome, minutes and share, work item, steps-loop pass and step, the item's revise count, Improve passes and minutes, refusals ("not recorded per visit" with the run-level figure labelled as such) and context. Written: the result summary, whether the result file exists and its size, and the stages that declare reading it, labelled "declared by the stage spec" (the engine records no observed reads, so none is shown). Older run documents render with whatever fields they have, naming nothing as zero. The page also resolves `select-work` and `get-next-work-item` to one stage. The page needs one republish, and `export.py --defaults --live` writes the stage catalog (`config/stages`) the cards read.
- The stage card follows the engine's two packet files per visit. When a run's row has the Improve child's packet document, the Sent block shows its size and a second closed box "Improve child's packet", loaded on demand by the same single read and cache as the Packet box; the packet checklist beside it is then a real one for every reviewed stage. A run of the old layout (ShipLoop 1.22.0 and earlier) still says its packet file is the Improve child's and shows no checklist. The packet head on the card now starts at the first line beginning "ShipLoop navigator |", so its twelve lines show Goal, Done when, Checked by and the callback for an inline run instead of the delegation preamble; a packet with no such line shows its first twelve non-empty lines as before. The page needs one republish.
- The export now holds what the stage card needs. Each stage row may carry `summary` (the accepted result's summary, cut at 300 characters with `summaryTruncated`), `resultFile` (whether `results/<action>.md` exists), `carried` (which of seven labels the visit's packet text held: where, purpose, operates, checked, produces, recovery, inputs, read from the whole packet file; `checked` is also found by a line starting `Checked by:`, which a later engine prints) or, for a visit that started an Improve child and so keeps only the child's packet, `packetImprove`. A stage catalog, `defaults/stages.json`, is generated from the shiploop skill's stage table by `export.py --stages` (purpose, exit check, completed-by runs, readers; a test fails when it drifts from the table) and written to the page database as `config/stages` by `export.py --defaults`. The exit check of a stage is `script-run`, `review loop` or `model judgement`, by a rule that reads the stage row's own fields and the run's `planning_review` mode. `select-work` and its coming name `get-next-work-item` resolve to one phase through one alias table, so old evidence and new runs both read. SCHEMA.md documents the catalog, the rule, the aliases and the packet checklist, with the markers as the packets of every run on disk showed them; `facts.md` counts the labels.

## 2026-10-06

### skill-craft 1.22.0

- Skills: shiploop 0.54.0, shiploop-e2e-audit 0.7.0

### shiploop 0.54.0

- New run option `--planning-review stage|none` at `init` and `workspace start`, recorded as `planning_review` in `state.md` like `--backchain-passes` (default `stage`). `stage` starts an Improve child after each of the five planning results (`spec`, `test-strategy`, `plan`, `step-plan`, `test-spec`), as every run did before, and no packet changes. `none` starts none: those five results are accepted on ShipLoop's own checks at `complete` and the graph advances, so the planning window no longer includes five reviews. The children after `system-test-author` and `release-plan` and the last `carry-forward` start in both modes. In a `none` run the packets say so (the Improve line, the plan and step-plan duties and the shared handoff sentence name only the stages that hand off), the plan child's `improve-reconcile` route and plan-time experiments do not exist and are not printed, the spec and test strategy are committed to `docs/shiploop` when each is accepted with no review after, and the first Improve child is the last item's `carry-forward`, so a `none` run names its Improve card at the start: `init` and `workspace start` refuse `--planning-review none` without `--improve-skill=<absolute selected Improve SKILL.md>` and resolve it there (the first item's quality and test loops read the card, and no earlier child binds it). The inline step directive and the interaction guide no longer say a step or handoff is reviewed. `--planning-review none` with `--backchain-passes none` leaves no model-run second look at the plan graph; it is documented, not refused. A retry of `init` or `workspace start` cannot change the option and no verb changes it mid-run. A saved run without the key is refused with the fresh-run hint: start the request again in a fresh `--run-dir` or `--workspace-root`. `graph-dry-run` takes the same flag and simulates the selected schedule.
- `test-author` is now script-checked: on `done` ShipLoop runs the item's focused commands once and accepts only a run in which a test ran. Exit 0 needs a counted test (at least `min_tests`) with every listed ID shown; a non-zero exit needs a failing test inside a test. A run that stops before any test runs, for example because a file the tests load is missing, is refused at `test-author` with the rule for fixing it: create the smallest loadable placeholder at a path the step plan's `paths` names, or load it inside the test so a missing file fails that test and not the run. A unittest module the loader cannot import (`unittest.loader._FailedTest`) now counts as no test run, so the probe refuses it without listed IDs, and `test-red` and `test-green` read it the same way; a command that also runs a failing test, with a module that cannot load and no ID listed for it, is still accepted. A refusal for a run in which tests did run no longer says none ran (header "did not show a usable test run"; a passing run with a non-zero exit is told to exit 0 or fail inside a test). Before, only `test-red` could notice, and it forbids product edits. After 7 refused runs `done` is no longer accepted and `revise` is the named remedy; a command that reaches no verdict (timeout, cannot start) refuses without counting; `revise` and `blocked` are never gated. The `step-plan` duty gains one generic sentence and the `test-author` duty two, about where a loadable file comes from. Other packets are unchanged.

### shiploop-e2e-audit 0.7.0

- The DAG replay and the workflow review read ShipLoop's new run option `planning_review` (`stage` or `none`). Every replay case now declares it (a case without one is refused) and the oracle keeps one literal Improve schedule per value, so a `none` run's five planning producers must advance with no child while `system-test-author`, `release-plan` and the last `carry-forward` still park; `synthetic-none-full` replays one. The workflow review judges a run's Improve inventory against the schedule of the mode its state records, and reports a state that records no `planning_review` as unverified instead of comparable (a state that records `none` is judged against the `none` schedule and is comparable).

## 2026-10-05

### skill-craft 1.21.2

- Skills: shiploop 0.53.1, shiploop-run-review 0.1.1

### shiploop 0.53.1

- The refusal for an Improve opening that is too large now says how its byte counts are made: the sizes it lists and the room it states are counted escaped like JSON, so a newline or a quote costs 2 bytes and a non-ASCII character 6, and a file's byte size undercounts them. The stated room itself was already right; this only says what it measures, so a model that shortens the opening can measure it the same way and not be refused a second time.
- Every producer packet now prints, under the done template, the exact fields of each other outcome the stage allows (repeat, blocked with blocked_by and the awaiting wait, revise, replan), and says the result block holds the result object itself rather than the action and result wrapper the stored files under results/ use. The release-plan template now carries the consumer_entry its gate requires. The improve-start line in an Improve packet head names the four opening headings.
- A refused ShipLoop result now says how to fix it. A result that wraps its fields in action and result keys (the shape of the stored files under results/) is told to move the fields up and delete the named keys; a result missing outcome or summary is told which; a blocked, repeat, revise or replan result that still holds done-only fields (work_items, assumptions, steps, test_commands and the like) is refused once with every such field named; an awaiting wait without no_default is told where it goes, with the exact shape; unsupported fields are named; an Improve opening whose section heading is renamed is told the heading it must read and the headings it found. Each reply ends by telling the model to run the same command again. No check was loosened.
- The packet for the stage that records the whole-product test commands (system-test-author) now says which suite a command belongs in: a command that is not a test runner (a shell pipeline, a grep, a curl probe) is suite `check`, judged by its exit code, and `focused` and `regression` are for runners whose output ShipLoop can count. Before, the stage named the three suites without defining `check`, so a shell pipeline recorded as `focused` was refused at system-test ("could not read how many tests it ran") and could only be repaired by a replan.
- When a recorded test command exits 0 but ShipLoop cannot read how many tests it ran, the refusal now names the exit the running stage actually has. At system-test and release-verify, which run commands that system-test-author and release-plan recorded and cannot edit them, the reply says who recorded the command, that a command that is not a test runner (a shell pipeline, a grep, a probe) belongs in suite `check`, and to report replan now with one corrective work item that says to record the command as suite check in system_commands or consumer_checks; it no longer asks for ids and a runner flag or for a code fix that could not help. At the stages that run the step plan's commands the reply keeps the ids and runner flag and adds the `check` alternative. No check was loosened: a done is still refused until the command is counted or recorded as a check.
- At test-green, regression and static-checks, a result submitted before the bound Until Loop ran was told to list the loop's terminal packet in evidence_refs, a file that did not exist; citing it was then refused too. The refusal now says the loop has not run and names the exact start command the packet prints (the same text, from one definition), what to follow until the loop completes (or stops blocked, for revise), and then to list the receipt.

### shiploop-run-review 0.1.1

- The exporter now finds the Backchain loops that ShipLoop 1.21.0 keeps under `run/backchain/<action>/` (before, a 1.21.0 run read "Backchain loops: none found under scratch/"): each loop document gets its pass count, last outcome and trivial-streak requirement from the runtime receipt, its minutes from the start record to the receipt, and the loops under `scratch/` read as before. Each loop document also records, without enforcing anything, the run's `backchain_passes` option as `state.md` wrote it ("not recorded" when absent) and `candidateMatch`: whether the last `backchain-check` receipt is for the loop's final candidate (true, false or "unknown"). A one-pass loop's streak requirement of 0 reads "no trivial-streak requirement on this loop" instead of "0 of 0 required". An unreadable loop reports its passes as unknown, not 0. SCHEMA.md documents the new fields, the three layouts and why the first visit reads shorter than the harness's stage line.
- The prompt the Run Review page builds no longer names a review file after the page's primary run key (for example `hello-1190b.review.json`, which does not exist): a finding can span runs and is written in one run's review bundle, so the head now says "Review files: the *.review.json bundles in test/shiploop_e2e/evidence/", gives a `grep -l` line for the first ticked id and says to edit the bundle that holds it, and the report-back says to set the status "in the review file that holds it". The head's `Page:` part reads `config/page.artifactUrl`, which a draft page left empty because a page cannot read its own URL: `export.py --defaults --page-url URL` now sets it (keeping the page's own title and other fields), and the publish procedure in SKILL.md passes it. The page needs one republish.
- The Backchain pass strip on the Run Review page no longer says a one-pass loop "closes at 2": when a loop document's `trivialRequired` is 0 it draws no streak axis or target and says "no trivial-streak requirement on this loop"; a document with no `trivialRequired` (an older export) is drawn as before, with the target at 2. The loop card already lists the new `Backchain passes option` and `Candidate match` facts. The page needs one republish to show this.

### skill-craft 1.21.1

- Skills: adversarial-review 0.1.0, rubric-eval 0.1.0

### adversarial-review 0.1.0

- New skill: have a model from a different family than the change's author try to break the change, returning testable findings, each with the smallest experiment that would refute it, as findings.json for rubric-eval. Composes rubric-eval's isolated model call; reviewers are Grok, Sonnet or Opus.

### rubric-eval 0.1.0

- New skill: evaluate a prompt change against a rubric over a scenario catalog. Runs arms on Grok 4.7 (medium effort) by default, grades with one evidence-first judge per round (Opus 5.5, medium effort, by default), and decides by quality, then tokens, then time: scores are the percentage of analytic-rubric points earned, arms are compared paired with scenario-clustered bootstrap intervals and the Wilcoxon signed-rank test, equivalence is bounded by the judge's measured test-retest noise, and judges are accepted by Cohen's kappa (Landis–Koch substantial or better). Records tokens and seconds for every call. model_call.py gives Grok, Claude and Codex one interface (host:model@effort specs with pinned aliases grok, opus, sonnet, luna), each call in its own directory with reference files and read-only tools on request, and audits what each call touched outside it. Also adds a quote check and a value audit that weighs every item a review added or removed. Ships the architecture suites (up to 34 criteria and 23 scenarios across seven environments, including cross-runtime ones). SPEC.md is the reference for conditions, models, the ship rule, the change lifecycle and process hygiene for long runs.

## 2026-10-04

### skill-craft 1.21.0

- Skills: backchain 0.6.3, shiploop 0.53.0, shiploop-e2e-audit 0.6.1, shiploop-run-review 0.1.0

### backchain 0.6.3

- The review gate of a whole Backchain planning child is now selected by the caller. By default nothing changes: two consecutive distinct complete trivial/no-change dependency reviews, with both original qualifying review records kept. A caller that adds the line `Backchain passes: one` beside the binding marker in the child request gets one dependency review/fix/check cycle: `required_trivial_reviews: 0`, an exit condition naming the cycle, its repaired findings, the `Confirm by` rule on the steps the cycle may change (a weak clause on any other step stays advisory) and the `backchain-check` receipt, and the one review record plus that receipt as the terminal evidence set. `references/convergence.md`, `references/caller-contract.md`, the skill card and the evals say so, with a new eval for the marker path. Standalone Backchain keeps the default two reviews.

### shiploop 0.53.0

- The plan packet's Backchain text now follows the run's `backchain_passes` option. With the default `one` it tells the host to write the planning child's start contract with `required_trivial_reviews: 0` and a one-cycle exit condition (one review/fix/check cycle has run, every finding of it is repaired within the edit bounds, every `Confirm by` clause on a step this cycle may change meets the planning guide's Outcomes rule, the printed `backchain-check` is ok on the final candidate with its receipt cited, domain evidence saved), and to put the line `Backchain passes: one` beside the binding marker in the child request. A pass that completes that cycle reports `exit_assessment: satisfied` even when it repaired the candidate, and Until Loop then completes the child instead of asking for two more reviews. The audit stages (spec, step-plan, carry-forward, product-acceptance) tell the host that a repair/revise child runs one cycle and to put the same marker line beside the binding marker in the child request. `--backchain-passes converge` prints the previous two-review text unchanged. ShipLoop's skill guide and Backchain planning guide now point to the packet's printed gate instead of stating two consecutive reviews. Improve's loops, the quality and test loops and the vendored Until Loop are unchanged.
- New run option `--backchain-passes one|converge|none` at `init` and `workspace start`, recorded as `backchain_passes` in `state.md` like `--lint` (default `one`). It sets how many passes the Backchain planning child may take: one review/fix/check cycle, two consecutive trivial reviews, or no whole loop at `plan`. With `none` the `plan` packet prints the read-only audit route and the audit resource with the loop-resource status line, says no whole `plan`/`draft` is requested in this run, and omits the six-file Backchain and Until Loop resource block; the four audit stages say the same in place of "only at `plan`", and a `repair`/`revise` after a finding still runs one pass. `one` and `converge` print what they printed before. A retry of `init` or `workspace start` cannot change it and no verb changes it mid-run. A saved run without the key is refused with the fresh-run hint: start the request again in a fresh `--run-dir` or `--workspace-root`. Improve's review loops are not covered by the option.

### shiploop-e2e-audit 0.6.1

- The Run Review exporter, contract, defaults and page template moved to the new shiploop-run-review skill; this skill's after-every-run step now points to it.

### shiploop-run-review 0.1.0

- Adds the ShipLoop Run Review skill (`/skill-craft:shiploop-run-review`): it exports a ShipLoop E2E run's measured numbers, has Claude write findings, advice and options for the run into a review file that `export.py --check` validates (`advise`, `export`, `check`), and publishes both to the owner's Run Review page (`publish`). The exporter, data contract, starting defaults and page template move here from shiploop-e2e-audit. The export is now `run-review-export/v2`: a counter the host cannot measure (refusals and glue on a Claude run) is left out with its reason instead of reading 0, a `metrics.json` that predates that record is refused, and a stage with no accept time reads n/a instead of 0 min.

### skill-craft 1.20.0

- Skills: shiploop 0.52.0

### shiploop 0.52.0

- At system-test, a required case that only a person can run and that has no route on this host is recorded as an open item (owner a person, due at handoff or at the stage whose external effect it gates), and the stage reports done once every other due check and ShipLoop's rerun pass, instead of ending the run blocked. The handoff lists each open item as unverified with who reports what, and the stage-readiness reference says the same; prompt and reference text only.
- A ShipLoop test run that never reached a verdict about the product is no longer
  counted as a product failure.

  - A command that times out, cannot start (the process could not be spawned; a
    command the shell cannot find or execute exits 126 or 127 and is still a
    failure), or is skipped because the invocation's
    budget ran out is recorded `disposition: could-not-run`. It still refuses the
    stage — nothing is accepted on unrun tests — but it does not spend one of the 7
    refused runs, so an environment problem can no longer rewrite a work item's
    step plan. A real failing check beside a timeout is still a failure.
  - Fixed: a command that could not start (`OSError`) was recorded as `failed`.
    The `error` status was computed and then overwritten, so a spawn failure was
    indistinguishable from a failing test.
  - At the 7-refused-run gate the packet now names the outcome the stage actually
    allows: `revise` back to the step plan at an INNER stage, and `replan` with
    corrective work items at the outer `system-test` and `release-verify`, which
    have no step plan to revise and where the navigator rejects `revise`.
  - A timeout is reported as reaching no verdict rather than as a product failure,
    since it can mean a deadlock, a broken test, a suite too slow for the budget,
    or an external dependency.
  - Because those attempts no longer reach the gate, the refusal names the routes
    out explicitly: a hang in the item's own code, test or fixture is run-fixable
    and is not a blocker, a recorded command that is wrong or too slow to fit the
    run's budget takes the stage's remedy, and `blocked` is only for what the user,
    an access grant or an outside dependency must supply. A skipped command is
    named as such: it never started because the commands before it used the run's
    budget, and they run in the same order every time, so a retry skips it again.
  - That remedy is accepted. At `test-green`, `regression` and `static-checks` the
    navigator used to require a stopped Until Loop packet for `revise`, which a
    `could-not-run` attempt never produces, so the route the refusal named was
    refused (and at `static-checks`, `blocked` too). ShipLoop's own record now
    supports it: when its latest test run for the action is `could-not-run` (and,
    at `static-checks`, where it was never opened, after 7 refused runs too),
    `revise` (and `blocked` at `static-checks`) is accepted without a new loop
    packet; `replan` with corrective work items at the outer stages and `revise`
    at the other INNER stages were already accepted. An ordinary `done` still needs
    a complete loop packet, and a later failed run closes the route again.
  - The outer-stage rerun packet says which stage recorded its commands
    (`system-test-author`, `release-plan`) instead of the step plan, and the
    `test-red` text no longer asks for the item's own code to be fixed. The
    `end-of-work review` gate, which is not a graph stage and has no remedy outcome,
    no longer says that a failing run ends in `blocked`.
  - Keepalive's stuck release (14 continuations without an accepted result) keeps
    its value, which is no longer paired with the 7-run cap for a command that
    cannot run; its comment says so and its notice names the outcomes above.

  Known limits, kept on purpose: a timed-out command's partial output is not read,
  so a suite that prints failures and then hangs is `could-not-run`; and at the
  `end-of-work review` gate, which reruns every item's recorded commands for the
  Improve import, a recorded command that cannot run has no remedy outcome.

  The per-invocation command timeout (600s) and budget (1800s) are unchanged.

### skill-craft 1.19.2

- Skills: shiploop 0.51.2

### shiploop 0.51.2

- The chain guide's `finish` row and worked example no longer say finish needs every worker's worktree removed. Since 0.49.0 a retried or lost attempt's workspace is kept and listed under `retained_superseded`; the old wording could lead a model to remove it directly or to stop.

### skill-craft 1.19.1

- Skills: plan-dispatcher 0.6.2, shiploop 0.51.1

### plan-dispatcher 0.6.2

- The skill card no longer says to retry only after confirming the old worker stopped without exception: it names the lost-worker case (host session ended, handle unavailable) and points to the protocol's limits, matching the protocol since 0.6.0.

### shiploop 0.51.1

- On an Ask-Agent run, step-plan now asks for each change that does not need another to be its own step with `deps: []`, joined by a later step that needs them. Before, a request that did not ask for parallel work got a linear plan (two independent modules in one step), so the default parallel chain had nothing to run at the same time. Inline runs are unchanged.

### skill-craft 1.19.0

- Skills: shiploop 0.51.0, shiploop-e2e-audit 0.6.0

### shiploop 0.51.0

- New `shiploop backchain-check --candidate PATH`: checks a Backchain candidate plan against Backchain's seven structural invariants (a Python port of Backchain's reference validator, packaged first) and records a receipt and a snapshot under the run's `backchain/<action>/`. Backchain stages tell the host to run it after each candidate revision and to treat a failure as a loop finding; nothing is refused.
- Every stage that can start a Backchain Until Loop child now states the contract size budget (the plan stage and the repair/revise route at spec, step-plan, carry-forward and product-acceptance), and an `improve-start` refusal lists each opening section's own byte size beside the bytes the sections may use. A GPT-6 Luna run built an 11.9 KB step-plan Backchain contract because only the plan stage carried the budget, and the refusal had compared whole contract fields with a per-section allowance.
- The Backchain loop text and the Backchain and Until Loop resource list now print only at the plan stage, where a whole loop may start. Spec, step-plan, carry-forward and product-acceptance print the read-only audit route, the audit resource and one line saying whether the files a repair/revise request needs are all present or which are missing; the identity and digest instructions restated at plan and the Improve-owner text are shorter. Prompt text only: no command, state field or exit rule changes.

### shiploop-e2e-audit 0.6.0

- The Grok adapter credits ShipLoop's new `backchain-check` verb as a direct ShipLoop command.
- Adds the Run Review page: a static template with its data contract, starting defaults and an exporter, so every E2E iteration can add the run's data to the owner's page without redoing the template.

### skill-craft 1.18.0

- Skills: plan-dispatcher 0.6.1, shiploop 0.50.0

### plan-dispatcher 0.6.1

- The protocol states the limit of `retry` with `native_status: "unavailable"`: it keeps the step's accepted result correct, but relies on the lost worker having ended with its host session. A step sharing a checkout, port, database or other external resource with its replacement waits for proof that the old worker stopped.

### shiploop 0.50.0

- The final report lists what the run left in your repository — merged attempt branches, kept (rejected or lost) attempt worktrees, and the run's own branch and workspace — with the command to remove each, and the completion packet says how many there are. ShipLoop still never deletes them itself. Commands use `git branch -d` wherever the branch is merged (it refuses to lose work) and never `--force`; nothing is offered for removal before the run is returned.
- The chain guide states when retrying a lost worker without proof that it stopped is safe: when native workers end with their host session. A step holding something outside its worktree (a port, a database, a deployment) waits for proof instead.

### skill-craft 1.17.0

- Skills: plan-dispatcher 0.6.0, shiploop 0.49.0

### plan-dispatcher 0.6.0

- `retry` accepts a worker whose host session ended: `confirmed_stopped: false` with `native_status: "unavailable"`, for when the worker's handle can no longer be looked up and nobody can prove it stopped. The retry is recorded as unconfirmed; the old attempt's work is kept and its late report is refused, so the fresh attempt is safe.

### shiploop 0.49.0

- A run resumed after its host session was lost can recover its chain without a person. When a worker's handle can no longer be looked up, `chain retry` accepts `confirmed_stopped: false` with `native_status: "unavailable"`; the old workspace is kept as evidence, its late callbacks are refused, and the step gets a fresh worker. Previously the run paused to ask whether it could retry.
- A chain step that needed a retry no longer blocks the chain from finishing. The retried attempt's Ask-Agent workspace is still kept as evidence (never deleted); `chain finish` now completes and lists it under `retained_superseded` instead of refusing forever.

## 2026-10-03

### skill-craft 1.16.1

- Skills: shiploop 0.48.1

### shiploop 0.48.1

- The credential check no longer refuses a label followed by a plain description (`session token: opaque UUID`, `auth: none required`, `auth: oauth2`, `signature: n/a.`), including punctuation or markdown around it; real secrets after the same labels are still refused. A GPT-6 Luna discovery result was refused twice for text that held no credential.
- `improve-start` refuses an Improve contract over 9,216 bytes before anything is written, counting bytes the way the Until Loop does and telling the model how far over it is, which opening section to shorten and how many bytes the sections may use; the opening and Backchain packets state that budget, and a step plan whose test command list could not fit the test loop's contract is refused where it is submitted. The Until Loop saves its whole state in 16,384 bytes, so a larger contract can start yet fail to save its first review report. A GPT-6 Luna run wrote 12-16 KB contracts and its plan stage could not close.

### skill-craft 1.16.0

- Skills: backchain 0.6.2, improve 0.3.0-rc.11, shiploop 0.48.0, shiploop-e2e-audit 0.5.4

### backchain 0.6.2

- Honor a caller's explicitly selected bundled Until Loop adapter card and resolve its runtime relative to that card. This lets ShipLoop planning use its selected package without searching for a nonexistent separate skill card or substituting another installation.
- Clarify in the native procedure that an explicitly selected bundled Until Loop ADAPTER.md is the selected card, with its own package-relative reference and adapter.

### improve 0.3.0-rc.11

- Clarify that Improve's whole-skill subcall applies to the current ShipLoop packet regardless of navigator protocol label.

### shiploop 0.48.0

- Reaching the research investigation allowance stops exploration, never the run: the model records open gaps as assumptions or open items, submits the result and continues, instead of pausing an unattended run (a GPT-6 Luna run paused itself at the allowance).
- Backchain-stage packets print the resolved Backchain and Until Loop resources from ShipLoop's installed plugin, identify missing resources by path, and name Until Loop's `ADAPTER.md` card correctly.
- Per-step flow replies expose dispatcher control only through bridge navigation.
  Raw dispatcher actions and continuation instructions are removed from the public response.
- The execution-checkout locator in worktree packets says it is a working directory, never a `--result` value; a GPT-6 Luna run passed it as the result path.
- Rename the current prompt module and navigator contract suites to version-neutral names. Update active consumers and suite labels, and share duplicated design-basis guidance without changing rendered packets.
- Terminal handoffs retry knowledge commits and worktree follow-up returns before saving completion, leaving the handoff pending when either required operation fails.
- The Improve packet names the Until Loop root, where its card's relative links resolve; a GPT-6 Luna run resolved `references/runtime-ephemeral.md` under the Improve skill, found nothing and paused, believing the runtime missing.

### shiploop-e2e-audit 0.5.4

- Update the audit harness module list to load ShipLoop's version-neutral prompt module.

## 2026-09-28

### skill-craft 1.15.0

- Skills: shiploop 0.47.0, shiploop-e2e-audit 0.5.3

### shiploop 0.47.0

- Keep a self-contained progress.html current during each run using a read-only
  background observer. Visualize generated implementation steps, dependency edges,
  and recorded execution status. Show the accepted plan, recorded activity, and embedded
  specification and architecture drafts with source and freshness labels. Add
  explicit dependency lists to generated inline step plans while preserving saved
  plans that omit dependency metadata. Add
  view commands for snapshots, foreground watching, background start, stop and
  status; preserve the terminal report and Markdown workflow authority.
- Keep startup guidance compatible with package-reference validation by describing
  the link without a placeholder target. Preserve the actual progress-file path
  when run directories contain URL or Markdown delimiter characters.
- Introduce the progress HTML file in the first startup message with a clickable
  absolute link and an explanation that it tracks changes during the run. Keep the
  link available in action packets for later reference.

### shiploop-e2e-audit 0.5.3

- Recognize ShipLoop's progress-view CLI command in the Grok audit adapter's
  direct-command inventory, keeping it aligned with the current CLI help.
  Revalidate the retained host-command shapes against the updated parser while
  preserving their capture provenance and expected attribution.

## 2026-09-27

### skill-craft 1.14.0

- Skills: ask-agent 0.9.0, improve-agent 0.1.3, plan-dispatcher 0.5.1

### ask-agent 0.9.0

- The current workspace is now the default route. An ordinary delegation runs a fresh worker in your own checkout and branch, with no second worktree or repository: `in-place` within a write set declared from the request for file changes, `report-only` for questions, digests and reviews. A separate helper-managed worktree now needs an explicit selection (`workspace_route: helper-managed` or asking for a separate worktree).

### improve-agent 0.1.3

- A standalone request explicitly selects Ask Agent's helper-managed route, since Ask Agent's default is now the current checkout.

### plan-dispatcher 0.5.1

- Git tasks explicitly select Ask Agent's helper-managed route, since it is no longer Ask Agent's default.

### skill-craft 1.13.0

- Skills: shiploop 0.46.0

### shiploop 0.46.0

- `workspace start` now checks, before creating anything, that the host sandbox lets
  it write the `.shiploop-runs` parent and the repository's Git directory. When a
  sandbox refuses (Codex `workspace-write`, a Grok sandbox profile, Claude's Bash
  sandbox) it exits 3 with a `SHIPLOOP-GRANT-NEEDED` block naming the blocked
  paths, the repair intent, the grant for the detected host and the exact rerun
  command. Every later run-bound command rechecks, so a harness restarted without
  its grants stops before a commit fails. `--workspace-root` is now optional: the
  default is a new `<repo-parent>/.shiploop-runs/<repo>-<stamp>`, so one grant of
  that parent covers every later run.

### skill-craft 1.12.2

- Skills: shiploop 0.45.2

### shiploop 0.45.2

- A completion refused for naming the wrong result file now names the file to use.

### skill-craft 1.12.1

- Skills: shiploop 0.45.1

### shiploop 0.45.1

- On the Ask-Agent route, ShipLoop now writes the Improve child's contract and
  starts the child itself, as it already did on the inline route. The parent
  writes the opening and runs `improve-start`. The improve-agent worker then
  continues the started child from the receipt's `next_argv`; it no longer
  hand-builds the contract or copies the binding line.

  A stopped child restarts with `improve-start --restart-stopped` on both
  routes. The frozen contract lists the `host-owner.md` owner record for a
  delegated child.

### skill-craft 1.12.0

- Skills: improve 0.3.0-rc.10, improve-agent 0.1.2, shiploop 0.45.0

### improve 0.3.0-rc.10

- The ShipLoop subcall guidance describes the new completion: write `review-<n>.md` per pass and `checks.md`; ShipLoop imports them, with optional `--notes` and `--final-result`.

### improve-agent 0.1.2

- Names the child's reviews directory as the locator to return, matching ShipLoop's derived Improve completion.

### shiploop 0.45.0

- A ShipLoop record without exactly one `shiploop-state` JSON fence is refused with its path, the fence count and the expected shape, instead of a bare "exactly one fence" message.
- `improve-complete --action <id>` no longer takes a completion record. Each review pass writes `reviews/review-<n>.md` and the check output `reviews/checks.md`; ShipLoop imports the last two passes (the last one when the first pass changed nothing) and `checks.md`, and writes the summary itself. The model supplies only optional `--notes` (lessons), `--final-result` (when the review changed a decision) and `--no-commit`. `parent-return.md` is the one command. The `--result` flag of `improve-complete` is removed; stopped and reconcile receipts are unchanged.
- After a verified workspace return, ShipLoop returns its own later knowledge commit (for example at release-verify) by the same route when everything changed since that return is `docs/shiploop/` or `SHIPLOOP.md`, keeping the earlier reviewed dispositions; handoff no longer finds a stale receipt and asks the model for a manual follow-up. Anything else changed, or a moved source, leaves the follow-up to handoff as before.
- Every run has a scratch directory, `<run>/scratch/`, named in each packet's locators; the common rule and the Improve packet send temporary files there (including the report piped to the Until Loop runtime), because `/tmp` is shared with other runs and a fixed `/tmp` name can read another run's file.

### skill-craft 1.11.1

- Skills: shiploop 0.44.1

### shiploop 0.44.1

- ShipLoop now commits the repository knowledge index `SHIPLOOP.md` with `docs/shiploop/` after any accepted stage that changed it, screens it for credentials, and keeps it on the workspace return. The model no longer commits it by hand.
- `workspace plan-return` first commits product files still uncommitted in the candidate onto the run branch, so a reviewed return fast-forwards instead of falling back to uncommitted working-tree changes. Run evidence, protected paths, caller exclusions and files that look like credentials are never committed. A release plan whose `consumer_entry` sources are absolute paths is refused with a clear message instead of crashing.

### skill-craft 1.11.0

- Skills: shiploop 0.44.0

### shiploop 0.44.0

- Milestone packets now carry a script-rendered run narrative: the goal, a progress bar per phase, what has been achieved (each step's new one-line `headline`), what is happening now, what comes next, and the observed pace with a labelled forecast from `<run>/timeline.json`. Where the host shows hook messages (the Claude Code terminal CLI) the status hook shows it as plain text; everywhere else, including the Claude desktop app, the model pastes the Markdown narrative as written, once per milestone. Results accept an optional `headline` of at most 100 characters.

### skill-craft 1.10.0

- Skills: shiploop 0.43.0

### shiploop 0.43.0

- The lint gate now blocks only an item's last implement step. Earlier steps
  report their findings without auto-fix, since a later step may resolve them
  (for example, an import the next step uses).

  Once a loop's receipt exists, the loop packet says not to run Start again and
  to continue from the receipt's `next_argv`.

  Paused, halted and blocked packets longer than 16,000 characters now print a
  pointer to the full packet file and what fits, so they stay under hosts'
  shell-output limits.
- ShipLoop runs unattended by default. An open decision takes a recorded default
  (an assumption with its alternatives) and the run continues; a step only a
  person can do becomes an open item while every independent stage continues.
  The run prompts the user (`blocked` + `awaiting`) only when nothing further can
  proceed without them, and a new `awaiting` must carry `no_default`, the reason
  no default would do; ShipLoop refuses one without it. Saved runs that are
  already waiting load and resume as before. Stage duties, the release-plan and
  release-verify guidance, SKILL.md and the delivery references say so, and the
  release-verify example is platform-neutral.

### skill-craft 1.9.0

- Skills: ask-agent 0.8.0, plan-dispatcher 0.5.0, shiploop 0.42.0

### ask-agent 0.8.0

- New explicit route `workspace_route: current` ("in place", `--in-place`, "just use the current worktree"): a fresh worker runs in the caller's own checkout and branch, with no helper worktree, receipt or close. It defaults to `report-only`; `in-place` writes need a declared write set. The helper's new read-only `current-state` command records a baseline and reports `unchanged`, `changed-within-write-set` or `drift`. An explicitly requested cheaper model or read-only agent type is honored and disclosed. Plan Dispatcher, ShipLoop and improve-agent keep the helper-managed route.

### plan-dispatcher 0.5.0

- Every action now carries its exact `call`: the argv plus an input whose
  `"<...>"` placeholders the caller fills. The settle call pre-fills the receipt
  digest, and the claim and start responses carry the follow-up calls. A
  completed run returns no `next_argv`.

  `init` accepts an optional `capacity`. The claim action then offers only free
  slots, and an over-capacity claim fails with `ECAPACITY`.

  Planning-blocked steps are no longer offered for claim, and a claim for one is
  refused. Cleaning up a rejected attempt's workspace or evidence no longer
  breaks the run. Concurrent writers wait briefly for the lock instead of failing
  with `ELOCKED`.

### shiploop 0.42.0

- Inline Improve packets no longer restate steps ShipLoop now performs (binding
  inputs, the binding line, start inputs, the runtime start command, the planning
  repeat clause); each remaining obligation is stated once. The delegated route
  keeps its manual start instructions.
- One commit path for every ShipLoop commit (knowledge home, the integrate item
  commit, `improve-commit`, the empty-repository baseline): it stages exactly the
  named paths, leaves any text file that looks like it holds a credential
  uncommitted and names it (never its value), and uses the configured identity or
  else the workspace identity. The knowledge-home commit gains that fallback.
  ShipLoop now also commits `docs/shiploop/` after any accepted stage that changed
  it (not only at the four closes), with the same credential and requirement-ID
  checks; packets tell the model not to commit it itself.
- The test loop, quality loop and Improve child contracts are built and
  serialized by one module (the test and quality contracts are byte-identical to
  before). An Improve child's exit condition now also requires the reviewed
  stage's own done-when criteria, so a review loop ends on what that stage must
  achieve, not only on two quiet passes.

### skill-craft 1.8.0

- Skills: plan-dispatcher 0.4.0, shiploop 0.41.0

### plan-dispatcher 0.4.0

- A verified BLOCKED result now routes the run to replanning. Settle it with
  `verification.disposition: "replan"` (only with `passed: false`). The run then
  starts no new work:

  - `claim`, a fresh `start` and a retry of that attempt fail with `EREPLAN`;
  - `next` returns `replan` and `release` actions plus a `replan` summary (steps,
    accepted, unfinished);
  - work already in flight can still settle.

  Rejected steps get a `retry` action with an attempt count, the reason and an
  exact `call`. There is no retry limit.

  A lock left by a process that no longer exists on this host is recovered
  automatically; any other holder is refused with a message that names what to
  do. A lost state file or settled receipt fails with `ESTATELOST` and names the
  recovery.

### shiploop 0.41.0

- The status hook now shows a two-line summary (where the run is; what finished and what comes next) instead of the full 11-line block, and the model no longer reprints the status block: it tells the user at most one line per step and shows the whole block only when asked. `shiploop status` and `status.md` still carry the full block.

### skill-craft 1.7.0

- Skills: shiploop 0.40.0

### shiploop 0.40.0

- Planning now keeps safeguards when it simplifies. The interaction-design guidance asks for the simplest placement that meets the request (a single-user product runs entirely in the client), the lightest channel for the freshness the request states, and native caching with a matching expiry. It also says simplicity removes machinery, never safeguards: personal-data handling, server-side checks on callers the product does not control, abuse limits on anonymous input, and background failures that reach someone who can act. Across 19 scenarios on seven environments this raised plan quality (winning about twice as many scenarios as it lost against the previous wording) without the privacy loss an earlier draft caused. The Apps Script card now states that executions run concurrently, that properties need a LockService lock for read-modify-write, that google.script.run is asynchronous, and when Session.getActiveUser() returns a blank email. Evidence: docs/shiploop-architecture-rubric-results-2026-09-26.md.

### skill-craft 1.6.0

- Skills: improve 0.3.0-rc.9, shiploop 0.39.0, shiploop-e2e-audit 0.5.2

### improve 0.3.0-rc.9

- The ShipLoop whole-skill subcall commits a review's changes through ShipLoop's
  `improve-commit` when the packet prints it (message written with a file tool).

### shiploop 0.39.0

- New `improve-commit` command for the inline Improve route: the parent writes the
  review's commit message to `commit-message.md` beside the receipt with a file
  tool, and ShipLoop stages and commits exactly the files the review changed and
  has not committed (earlier uncommitted work is left alone). Inline Improve
  packets print the command.
- `improve-start` prints only the runtime's JSON packet on stdout (its status and
  archive lines go to stderr), so a host can parse the output as JSON, as it can
  the runtime's own `start`.

### shiploop-e2e-audit 0.5.2

- The Grok adapter recognizes ShipLoop's `improve-commit` verb.

### skill-craft 1.5.1

- Skills: shiploop-e2e-audit 0.5.1

### shiploop-e2e-audit 0.5.1

- The Grok adapter recognizes ShipLoop's new `improve-start` verb, and the host
  trace fixtures are rebound to the adapter's new source hash.

## 2026-09-26

### skill-craft 1.5.0

- Skills: improve 0.3.0-rc.8, shiploop 0.38.0

### improve 0.3.0-rc.8

- The ShipLoop whole-skill subcall uses ShipLoop's `improve-start` command when
  the packet prints one: write the named opening file and run it instead of
  writing the start contract and starting the runtime by hand.

### shiploop 0.38.0

- `workspace start` on an empty, non-Git directory initializes it as a Git
  repository on `main` with one empty baseline commit (the user's identity when
  configured, otherwise the workspace identity). The model no longer writes Git
  setup commands for a new product, which on Grok's auto permission mode were
  cancelled and ended the session three times in one run.
- ShipLoop commits a work item's changes itself when `integrate` is accepted: the
  files the item changed that its step plan's `paths` declare, plus
  `docs/shiploop/`, with the item title and integrate summary as the message
  (the configured identity, else the workspace identity). It prints the commit
  and names every other changed file for the model to commit or delete. The
  model no longer writes the item commit, which headless hosts refused, and a
  run no longer ends with its product uncommitted in the execution worktree.
- `workspace start` creates one missing parent level of the workspace root (the
  usual `<beside the repo>/.shiploop-runs/<name>` layout) instead of refusing it;
  a deeper missing tree is still refused.
- The execution worktree branch is `shiploop/run-<id>` on every host instead of
  `codex/shiploop-<id>`, which named Codex on Grok and Claude runs. Workspace
  records made with the old name are refused.
- New `improve-start` command for the default inline route. The parent writes a
  four-section opening file (current context and desired improvements, scope,
  authority, environment) beside the receipt; ShipLoop freezes the Until Loop
  child contract from it (binding line first, workspace, work, exit and repeat
  conditions, commit policy, exclusions, and locators for the receipt, evidence
  directory, parent state, completion evidence and a written `parent-return.md`),
  stores it as `start.json`, starts the bound runtime with `--receipt` and its
  state under the run directory's `until-loop/`, and prints the child's first
  packet. The model no longer hand-writes a ~6 KB JSON contract per child.

  `improve-start --restart-stopped` restarts a stopped child: ShipLoop archives its
  `packet.json` and `reviews/` with a UTC stamp itself and starts the new child,
  instead of the model renaming them by hand.
- Keepalive binds a session to a run from a packet marker only when the command
  that printed it drives the run (`workspace start`, `init`, `next`, `resume`,
  `complete`, Improve bind/complete/reconcile). A session that merely reads a
  packet file, log or transcript containing a live marker is no longer bound and
  kept alive for a run it does not drive. The `--run-dir` fallback also reads only the command that ran, never its
  output, so callback text printed in a log or event dump no longer binds.

### skill-craft 1.4.0

- Skills: shiploop 0.37.0

### shiploop 0.37.0

- Packets now live in files. For an active run, ShipLoop writes the complete packet to `<run>/packets/<action>.md` and prints only a short head: the callback, goal and done-when, the result contract, the packet file's path, recovery and pause commands, the keepalive marker and the status block (about 3 KB instead of 20-50 KB). The host reads the file on demand and consults only the reference sections a step needs, instead of printing whole packets that Grok cut at about 20 KB and reading whole reference files into context. Paused, blocked, awaiting, halted and done packets still print whole. `next` rewrites the file and reprints the head.

### skill-craft 1.3.0

- Skills: shiploop 0.36.0, shiploop-e2e-audit 0.5.0

### shiploop 0.36.0

- Planning now has platform cards for Cloudflare Workers, Vercel and Next.js, AWS serverless, Google Cloud, a self-hosted Node.js and Express server, and web UI frameworks (Bootstrap, Material Design 3, React, Next.js, Vue, Svelte, Tailwind, and fitting them to Apps Script and Salesforce hosts). Each card covers identity, state, concurrency, channels, caching, secrets, background work and limits, with dated current facts and claims to check, all linked to official sources. The coding guidance index lists them. The architecture rubric, scenario catalog and results are in docs/shiploop-architecture-rubric.md.

### shiploop-e2e-audit 0.5.0

- Every workflow review now reflects on the harness itself in a required `harness_reflection` block: should the harness retain key learnings or keep state differently, is there more to learn from on subsequent passes, and are more evaluation criteria needed to re-evaluate ShipLoop's efficacy. Each answer comes from the run's evidence with concrete proposals. The template carries the three questions, and the validator reports a review without them as unverified and one with empty answers as invalid.

### skill-craft 1.2.0

- Skills: shiploop 0.35.0

### shiploop 0.35.0

- Packets now ask for composable design and a state lifecycle. Code craft adds "compose before you build" (reuse, compose or augment an existing unit before writing a new one, with a guard against fusing different rules), and the quality loop treats duplicated logic as a material finding. Intake asks who the actors are, whether state is shared or must persist, and what must stay hidden. The interaction-design guidance asks each state's owner, readers, concurrency, end of life, quotas and personal-data handling. The planning review checks platform claims that a decision depends on. The Apps Script card describes the mcp-gas-deploy layer, including that its `srv`/`apiExec` bridge runs client-built code. Evidence: docs/shiploop-composition-state-experiments-2026-09-26.md.

### skill-craft 1.1.0

- Skills: improve 0.3.0-rc.7, shiploop 0.34.0

### improve 0.3.0-rc.7

- The bundled Until Loop runtime is 0.7.0: `start --receipt <absolute file>` makes the runtime write every packet it returns to that file (atomically, mode 0600) before printing it, including the terminal packet, which it writes before deleting its state. In a ShipLoop subcall, start the bound runtime with the printed host receipt path as `--receipt`; ShipLoop imports only a packet the runtime wrote there.

### shiploop 0.34.0

- A completion criterion is now confirmed only by a command ShipLoop runs and sees pass. A done
  `step-plan` lists its `criteria` and names, in each test command's `criteria`, the ones that command
  confirms; an uncovered criterion is refused. A new `check` command kind (judged by exit code) covers
  content with no test runner, such as a README that must document a flag. `verify` reruns every
  recorded command. `system-test-author` must record `system_commands` and `release-plan`
  `consumer_checks` (or an empty list with the reason); ShipLoop runs them when `system-test` and
  `release-verify` report done and refuses unless each passes.
- Every packet now tells the host never to end its turn while a ShipLoop command is still running: keep the command in the foreground, or wait for it in the same turn when the host backgrounds it. A test-stage `complete` reruns the recorded tests and can take minutes, and a headless Grok session ends when the turn ends, which lost a callback in a live run. The keepalive self-install notice now says the current session is not protected (headless sessions never are).
- `next` always prints the full packet. It is the recovery command, and the script cannot know whether the host kept the run rules through a clear, a compaction or a fresh `shiploop-drive` session, so recovery no longer returns the short form with the original request and delegation rule behind a pointer to `rules.md`. `next --full` is removed. Every producer packet now prints its result path, result template and allowed outcomes directly under the callback line instead of at the end, so a host that keeps only the head of long output still has the contract the callback checks; the tail keeps the callback, pause and halt lines.
- Every producer packet now opens with the stage's goal, the conditions that confirm it and its fixed
  considerations for developing, testing, delivering and the assistive tools, right after the
  callback. Guidance that cannot apply to a stage is no longer printed there: the work-item paragraph
  appears only at plan and carry-forward, interaction design only from discovery to step-plan, the
  Code craft rubric only where code or tests are written or reviewed, and "the Improve child" only at
  stages that have one. implement and release no longer mention an Improve checkpoint they do not
  have. Packets are about 3% shorter overall.
- A done `step-plan` must list `steps: [{"id": "S1", "task": "..."}]`, every implementation step in the order to do them (one step is fine). On the inline route ShipLoop then issues one `implement` packet per step: each names its step, the steps already accepted and the ones still to come, and the callback after the last step moves to the test stages. Which steps are done is read from the run's history, so recovery after a lost context reprints the current step. A revised step plan starts its steps over. The ask-agent route is unchanged: a chain runs every step inside its one `implement` action.
- There is one packet form. `next --brief`, the short repeat packet, the per-run `rules.md` and `last-packet.json` display records and the Claude `SessionStart` compaction hook (`shiploop-keepalive-compacted`) are removed: every packet, including every `next`, prints in full, so nothing depends on what a host kept from an earlier packet. The Improve change gate's check that a one-pass review really left the candidate unchanged now runs; it previously failed silently and never refused.
- A context lost in the middle of a stage can now pick up where it left off. Every packet names the
  action's pass log (`notes/<action>.md`), where each pass records what it checked and what is left,
  and the run context index gains an "In progress" section (the action, its pass log, loop packets,
  ShipLoop test runs so far and revisions used) and a "Script records" section listing ShipLoop's own
  test runs, loop packets, lint records and Improve receipts. A result that cites a local file that
  does not exist is refused. `verify` now reads the item's implement, test-green, regression and
  static-checks results, and `handoff` reads product-acceptance and operations.
- A fixable problem is no longer reported as `blocked`. When a work item's goal proves wrong or
  unachievable while it is being built (test-spec through integration-verify), the stage reports
  the new outcome `revise`: the item goes back to `step-plan` with that result as evidence, at most
  twice per item, and then the user decides. A script-run test or quality loop that uses all its
  iterations, or three refused test runs, now routes to `revise`; a loop cancelled before its limit
  is refused, because a user's stop is `pause`. `blocked` stays for what only the user, an access
  grant or an outside dependency can resolve. Saved runs from earlier versions are refused; start a
  fresh run.
- Until Loop packets no longer depend on the host copying stdout before a context loss. The test-loop and quality-loop start commands pass `--receipt tests|quality/<action>-terminal.json`, and Improve children start with `--receipt` set to the printed Child latest packet receipt, so the bundled runtime (Until Loop 0.7.0) writes every packet there itself and the terminal packet before it deletes its state. ShipLoop now accepts a loop or Improve terminal packet only when it is a complete runtime packet whose `receipt` names that exact path and whose state file is gone; a hand-written object copied from the contract, a packet from a run started without the printed `--receipt`, or a copy of a still-live run is refused. The complete-packet Improve import now also requires the child's state file to be deleted, as the stopped import already did.
- ShipLoop's 34 stages are now described in one table (`scripts/shiploop_stage_spec.py`): each
  stage's goal, the conditions that confirm it, and its fixed considerations for developing,
  testing, delivering and the assistive tools (linters, test runners) the script runs around it.
  The stage sets that decide Improve reviews, lint gates, test runs, prompt blocks and "Read first"
  lists are derived from that table. Packets and run behaviour are unchanged.
- Keepalive now lets a turn end after 14 continuations with no accepted result (twice the per-action test-run refusal budget), with a notice to submit `blocked` or `revise`; a refused callback still counts as progress until then, and an accepted result starts the count again. When `handoff` is refused for want of a current workspace return, the refusal now says whether no return was made or the recorded one is stale (for example after ShipLoop's own `docs/shiploop/` commit at `release-verify`) and prints the exact `workspace plan-return` and `workspace return` commands. `system_commands` and `consumer_checks` can no longer name `criteria`, which nothing checked.
- ShipLoop's quality and test loops no longer have an iteration limit: they run until their exit
  condition holds. The loop contracts no longer tell the model to cancel at iteration 3 (quality) or
  4 (tests), a complete loop is `done` however many iterations it took, and a cancelled loop is always
  refused (a user's stop is the packet's `pause` command). A loop that stops blocked reports `blocked`,
  or `revise` when the item's goal proved wrong as planned. ShipLoop's own test reruns now allow 7
  refused runs before `done` is no longer accepted (was 3).

### skill-craft 1.0.1

- Skills: backchain 0.6.1, review-coverage 0.3.3

### backchain 0.6.1

- The trigger evals drop the `coexistence-devloop` case: DevLoop was archived on 2026-09-26.

### review-coverage 0.3.3

- The clean/residual×2 rule no longer refers to DevLoop or `docs/LOOP-ENGINEERING.md`, which were archived on 2026-09-26.

### skill-craft 1.0.0

- Skills: review-coverage 0.3.2, shiploop 0.33.1, skill-interop 0.2.6

### review-coverage 0.3.2

- The retired `## Post-Implementation Residual Loop` heading is no longer read. A plan that has only that heading now reports a missing `## Review Coverage` section, matching plan-oversight, which refuses it too.
- Review Coverage now ships in the one skill-craft plugin: install skill-craft@whichguy and invoke /skill-craft:review-coverage.

### shiploop 0.33.1

- A saved run without a recorded `lint` option is now refused with the fresh-run hint instead of being read as `off`; new runs always record the option. Run records containing U+2028, U+2029 or U+0085 in any text now read back correctly (the reader split lines on those characters). An isolated workspace's source fingerprint now hashes the index's staged entries rather than the raw index file, so a timestamp-only index rewrite no longer looks like a source change. Workspace manifests written with the old fingerprint are refused with instructions. Git commands in workspace operations honour `SHIPLOOP_GIT_TIMEOUT` (seconds, default 45).
- On Claude, the plugin adds a `SessionStart` hook with the `compact` matcher. After the host compacts a bound session, the hook clears the run's last-packet record, so the next `next` prints the full packet with the run rules instead of the short repeat packet.
- ShipLoop now ships in the one skill-craft plugin: install skill-craft@whichguy and invoke /skill-craft:shiploop (Codex $skill-craft:shiploop). The host matrix names the new identities.

### skill-interop 0.2.6

- The marketplace section describes the one skill-craft plugin (skill-craft@whichguy, /skill-craft:<leaf>) that now carries every skill.

### improve 0.3.0-rc.6

- A review loop with a gate of two or more trivial reviews now completes after its first review when that review is trivial and satisfied, and the bundled Until Loop runtime sees from Git that the workspace content (tracked and untracked files, excluding ignored and runtime files) is unchanged since `start`. A second pass would only have reviewed the same tree. The complete packet reports `progress.unchanged_first_pass: true`. Any change, or a workspace outside Git, still needs two consecutive trivial reviews.

### shiploop 0.33.0

- Each run now ends with a learnings commit. The feature's `outcome.md` carries `## Learned`, `## Key considerations` and `## Open for the next run` sections, which the `release-verify` close requires to be filled in and uses as its commit message body. Intake and discovery packets quote the checkout's last three commit messages as inherited learnings to weigh before planning.
- A repeated `next` for the same action now prints a short packet: status, callback, keepalive marker, what changed since it was last printed, the stage references and the full stage prompt. The run-level rules (locators, recovery, delegation rule and the original request) become a reference to the run's `rules.md`. `next --full` prints everything, and a new action, a status change or a changed rules block prints the full packet. Packets now point at material instead of asking for a reread: "Read first" is now "Results this stage builds on", and the context index and bound Until Loop card are opened only when they are not already in context.
- A done `release-plan` now records `consumer_entry` (how a person reaches the result, and the repository files that create it), and ShipLoop refuses a release plan without one or whose files are missing. A Salesforce `lightning__Tab` target alone therefore no longer passes as a navigation entry. `release-check` runs the dry-run deploy and each post-release confirm command once, before the real deploy, so a confirm that cannot tell present from absent is fixed first. The Salesforce guide says to confirm tabs with `sf org list metadata --metadata-type CustomTab`. After a replan whose corrective items changed only non-code paths, each outer stage's packet names the delta and the result it accepted before the replan, so unchanged rows are cited rather than redone.
- Planning knowledge now outlives the run. Planning stages keep `docs/shiploop/` in the product repository up to date: `README.md` (index), the living `spec.md` with stable `R-<n>` requirement IDs, `environment.md`, `test-strategy.md`, and this run's `features/<slug>/` record (spec delta, plan, test spec, system tests, release plan, outcome). At `prepare`, each `test-spec`, `release-plan` and `release-verify`, ShipLoop refuses `done` until that close's files exist. It screens the files for credentials, refuses a living spec that drops an earlier committed requirement ID, and commits exactly `docs/shiploop/`. The workspace return always keeps `docs/shiploop/**`. Every packet names the knowledge home and the files its stage keeps current, so the next run starts from them.
- An Improve child whose first review is trivial and leaves the candidate unchanged now completes after that one pass. The import accepts a receipt with that single review when the terminal packet reports `unchanged_first_pass`, and cross-checks the claim against the tree ShipLoop recorded at `improve-bind`. Packets explain the one-pass case.
- A done `step-plan` now declares `paths`: the files or globs the item will change. When the item records no test command and every declared path is documentation, configuration or navigation metadata (package catalog `references/path-classes.json`; an unmatched path counts as code), ShipLoop records `test-spec` through `regression` as not applicable to that item instead of issuing seven empty stages and an Improve review. `implement` is refused if the real change reaches code or goes outside `paths`. An Improve review must commit the edits it makes: `improve-complete` refuses while files the review changed are uncommitted, unless the receipt's `no_commit` gives the user's or repository's instruction. The end-of-work review reruns every item's recorded test commands only when it changed files. An unchanged Improve result no longer needs a restated `final_result`.
- A recorded test command now passes only when it ran tests. ShipLoop reads the runner's summary (Jest, Vitest, pytest, unittest, Mocha, cargo, go, dotnet) and refuses a command that exits 0 after running no test, fewer than `min_tests`, or without showing each of its `ids`. A filter that matches nothing, such as `npm test -- -t <name>` printing "2 skipped", no longer counts as green. Step-plan test commands accept optional `ids` and `min_tests`. `test-red` is now script-checked too: the focused commands must fail inside a test, not before any test runs. Characterisation tests that already pass declare `red_na`.
- A stage that needs a person now reports `blocked` with `awaiting`: a question (`kind: answer`, with optional options) or steps only a person can take (`kind: present`, such as opening a page in a signed-in browser, with what to report back). The run stops quietly: the keepalive allows the stop, and `status` prints "Waiting on you". `resume` then requires the user's own reply with `--answer` or `--observed`. It refuses a bare "continue", records the reply in `decisions/<action>.md`, and shows it in the next packet. `release-verify` uses this for browser cases the host cannot sign in to, instead of looping. The deploy question is now one yes/no question whose yes covers this run only unless the user says "standing". The delivery authority accepts an optional `scope` (`run` or `standing`), and `standing` must be a repo policy.

### shiploop 0.32.2

- ShipLoop now says when its keepalive is not working: if a host session prints a
  second packet and the keepalive has never bound that session to the run, the
  command warns once on stderr and names the fix for that host (for example,
  restart Grok so its leader loads the plugin hooks).

### shiploop 0.32.1

- Core guidance no longer names a specific platform. SKILL.md points at the
  platform cards the coding guide lists instead of hard-coding them, and the i18n
  and delivery-authority examples use neutral wording. Platform detail stays in
  `references/platforms/`.

### shiploop 0.32.0

- A blocked result must now say who can unblock it: `blocked_by` is `user` (a
  decision only the user can make), `access` (a sign-in or permission the user must
  grant) or `external` (a service outside the run). Anything the run can fix itself
  (a missing tool, a failed install, a broken baseline, a failing test) is refused
  as blocked and repaired in the stage instead. The run's status reason and the
  keepalive log start with that category. Saved runs are unaffected.

  Discovery now checks access for every planned verification surface (the deploy
  target and each post-deploy browser, API or remote check), proves a route the run
  can use without the user, and asks for any missing sign-in once, up front. For
  Salesforce, browser checks open the page through `sf org open --url-only` from the
  org's existing CLI authentication instead of asking the user to log in.

  Also fixes 0.31.1 writing its callback-attempt counter into a saved run that is
  refused as retired.

### shiploop-e2e-audit 0.4.6

- Synthetic blocked results in the DAG replay now carry `blocked_by`, which
  ShipLoop requires on every new blocked result.

### shiploop 0.31.2

- The keepalive binds a session from a `shiploop` command only when that command
  drives the run (`init`, `next`, `resume`, `complete`, `improve-*`). A read-only
  query such as `hook-status`, `status` or `report` from another session no longer
  claims the run and keeps that other session looping on it.

### shiploop 0.31.1

- The keepalive no longer lets a busy run stop. Its progress check now counts
  refused callbacks (the model is fixing and resubmitting) and each pass of an
  active Improve review, not only accepted results, and a still-running host
  background task (a deploy, an install) keeps the turn going with "wait for it in
  this turn". Each stop counts the turn's continuations: near Grok's cap of 8 the
  reason asks harder not to stop, and the log records "continuation N/8". A
  refused callback now says the run is still active, and a second session gets a
  notice naming the owner instead of a silent stop.

## 2026-09-25

### shiploop 0.31.0

- New house-style guide. Discovery extracts the repository's coding conventions
  from tool configuration and busy files, each rule with `path:line` evidence,
  frequency and status, into a short repository-owned record. Step planning
  records a per-item match contract naming the nearest existing exemplars in its
  step-plan result; test authoring and implementation reread it, verification
  checks the diff against it, and carry-forward keeps the record current.
  Test authoring now also lists the item's step plan under Read first.
- A request that names where to deliver ("deploy it to my Salesforce developer
  org") is now the grant for this run: discovery resolves it to exactly one target,
  records it, and the run never stops to ask again or plans a work item just to
  record approval. ShipLoop asks only when the request leaves it open (no target,
  several or no matching targets, an unnamed production or shared target, or a
  destructive change), and then once, at intake or discovery, while independent
  work continues. Discovery and plan packets now link that guidance.

  The keepalive also binds a session from a `shiploop … --run-dir` command itself,
  so a model that filters the packet output (hiding the run marker) no longer
  loses the keepalive after a pause or block.

### shiploop 0.30.1

- The generated plugin hook commands are no longer wrapped in quotes. Grok runs
  the ShipLoop plugin's hooks once its leader restarts, but it does not strip
  quotes: it read `"…/shiploop-keepalive-observe"` as a file name inside the
  plugin's hooks folder and failed every hook with "command not found". Commands
  are now `${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/<script>` (and the Codex
  and Cursor equivalents).

### shiploop 0.30.0

- Every stage now gets the run's global picture. Each save writes
  `context-index.md`, a derived index of the request, every accepted planning
  result with its summary, notes and Improve lessons, the plan's assumptions, each
  work item's accepted results, the outer loop and superseded results. Every packet
  names it right after the callback line, and active packets add a script-owned
  "Read first" list of the accepted results that stage builds on (for example,
  `verify` reads the spec, test strategy and the item's step-plan and test-spec).
  `pause` now refuses context-housekeeping reasons (a clear, context boundary,
  compaction or fresh conversation), and the keepalive log records why a run paused.
- Tests now run on a script-enforced loop. `step-plan` must record the work
  item's test commands in its result (`test_commands`, each `focused` or
  `regression`; an empty list needs `test_commands_na` with the reason).
  `test-green` loops on the focused commands and `regression` on all of them, on
  the Until Loop bound to the selected Improve card: ShipLoop writes the loop
  contract with the exact commands, and each iteration runs every command, fixes
  the code (never a check) and reruns the whole list, for at most 4 iterations.
  Both stages accept only `done` or `blocked`. `done` needs the loop's terminal
  packet, checked against the contract, and then ShipLoop runs every command
  itself from the repository (10 minutes each, 30 per stage) and refuses unless
  each exits 0, printing the failures. The prompt-only pass-or-stop loop now
  covers `implement`, `test-refine` and `integration-verify`.

  The packet-size caps in the test suite are removed; complete prompts take
  priority over packet length.
- Tests stay green after every stage that can edit code. On done at
  `test-refine`, `static-checks` and `integration-verify`, ShipLoop reruns every
  test command the step plan recorded and refuses unless each exits 0; the packet
  lists the commands. Each action allows 3 refused test runs (at these stages and
  the test loops); after that only `blocked` is accepted, so a restarted loop can
  no longer retry forever. The lint gate now also runs on done at `test-green`
  and `regression`, before the test run, since the test loops edit code too;
  `lint_waivers` are accepted there as at `implement`.

### shiploop 0.29.0

- Lint now runs right after implementation and gates it. When `implement` is
  submitted as done, ShipLoop lints every file the work item changed and applies
  safe fixes on changed lines. It refuses the submission once after an auto-fix,
  so the step reruns its checks. It also refuses while a new finding on a line
  the item changed remains, unless the result lists it in the new `lint_waivers`
  field (`[{"id", "reason"}]`) with the ID the refusal prints. Findings from
  before the item, missing tools, tool errors and timeouts never block, and
  `lint: off` turns the gate off. The implement packet prints the `lint` command
  to run after each step.

  Linters are now discovered per changed file type. Besides ruff and shellcheck,
  ShipLoop runs the linters a repository configures (eslint, prettier, tsc, mypy,
  black, markdownlint-cli2, yamllint, gofmt), actionlint whenever it is on PATH,
  and `npm run lint` or `make lint` for changed files no other linter covers.
  Repository-configured linters run repository code by design; pre-commit is
  still never run, and nothing is ever installed. The lint time limit rises from
  20 to 120 seconds (60 per tool). `shiploop lint --show --gate N` reads a gate
  record.

  `test-green`, `test-refine`, `regression` and `integration-verify` now carry the
  same pass-or-stop loop as `implement`: fix the code and rerun until every check
  passes, and stop only as `blocked` when a check is proven unachievable or still
  fails after 3 genuine fix attempts. A red check never leaves these stages as
  done. The navigator guide gains a whole-run map of the prelude, inner and outer
  loops.
- The stages that turn the accepted plan into work now receive it. `step-plan`,
  `test-spec`, `system-test-author` and `release-plan` packets name the accepted
  `spec` and `plan` results under "Current planning sources", beside the test
  strategy source. Before, they carried only the previous stage's result and the
  test strategy, so the requirements and the plan reached step creation only if
  the model searched `state.md` for them. The step-plan and test-spec duties point
  at those sources.
  `system-test-author` and `release-plan` are now also told to register every
  planning file they produce in `evidence_refs`, like the other planning stages.

### shiploop 0.28.0

- Keepalive now works on Grok without an installer. Grok lists a plugin's hooks but
  never runs them, so the marketplace install left Grok runs with no keepalive. Any
  `shiploop` command that runs under Grok now writes
  `~/.grok/hooks/shiploop-keepalive.json` when it is missing, or repairs it when its
  script is gone, and says so once on stderr. New Grok sessions load it; an open
  session picks it up from `/hooks`, then `r`. `SHIPLOOP_KEEPALIVE=off` skips it.
- Planning now decides where new code and its data live, in every execution
  environment the change runs in or reaches: the local checkout, a remote runtime
  behind an MCP server, API or CLI, a hosted platform, and each service of a
  multi-service system. The `plan` stage maps each environment's library
  structure, how it resolves names, the libraries and services the code shares
  names with, and how it stores data (existing and destination schema with their
  owner, or a new schema with its storage policy), and records a Namespace and
  data map. `step-plan` names each new file, module, public symbol and stored
  field with its environment, home, visibility and collision or round-trip
  check. Code craft gains rule 8, "Put it where it belongs", which the quality
  loop reviews. New stack-neutral Namespaces and placement and Schema and storage
  practice cards; the platform cards give Apps Script, Python, Bash, Salesforce
  and UI examples.

  UI work now defaults to an ambitious, highly interactive interface: plans name
  the rich interactions they deliver and any they scale back with a reason, and
  KISS/YAGNI no longer justify trimming the planned UI.
- A run no longer stops at the start of each work item. The `select-work` packet
  used to ask for a context clear and, since no host lets a packet, script or hook
  clear the conversation, offered a "context-boundary" pause that left the user
  to type `/clear` and two recovery commands before every item. Every inline
  stage now continues in the same conversation and the host's own compaction
  manages context; an ask-agent producer without a usable fresh worker runs in
  the conversation too. No packet offers a pause for a clear, and serial chains
  no longer have a manual-handoff route.

### shiploop 0.27.0

- The plan result now carries an `assumptions` list, and the navigator enforces
  it. A done plan submitted through `complete` or `improve-complete` is refused
  unless every load-bearing assumption is listed as evidenced, probed or open.
  Every local evidence path must exist, a probed entry must cite a nonempty saved
  output file, and each open entry must name a work item in the plan's queue. The
  Plan Improve loop exits only when no open entry could be settled by a bounded
  probe now. Research lists its assumptions in its decision note as the plan's
  starting point, without a gate. The model still decides whether to experiment;
  the gate makes a decision not to probe visible.
- The status hook recognizes Grok's real PostToolUse payload (camelCase keys with snake_case aliases, output as a list of byte values), and the status-display guide records how to make Grok use the trusted plugin install.
- Keepalive: host hooks stop an agent from ending its turn while a run can still move, for Claude Code, Codex, Grok, Cursor and OpenCode. A marketplace install brings them (declared in `host-hooks.json`, generated per host); a skill-directory install adds them with `scripts/shiploop-hook install --host HOST`. See `references/keepalive.md`.
  Only one session per run is kept alive; parallel workers and second terminals on the same run are let go, and ownership passes on when the owner's turn ends.
  New `shiploop hook-status` (read-only JSON run status) and a `Keepalive marker:` line in every packet.
  New `scripts/shiploop-drive` runs or resumes host sessions until a run is done, paused, blocked or stuck; use it for unattended Cursor and OpenCode runs.
  A question about the loop no longer pauses the run, and the agent is told not to pause on its own to ask whether to continue; only an explicit stop or pause, or a real blocker, does.
- The status block shortens any absolute path in a title, summary or reason to its last segment, so it never repeats full file paths from host text.

### shiploop-e2e-audit 0.4.5

- Recognize ShipLoop's new read-only `hook-status` verb in the Grok adapter's direct-subcommand allowlist.

### shiploop 0.26.0

- Code craft gains rule 7, *Write text that can be translated*: user-facing
  messages go through the repository's message catalog when one exists, and
  otherwise stay whole sentences with named placeholders so they can be
  externalized later. Numbers, dates, currency and plurals use locale-aware
  APIs, and logs, error codes and identifiers stay untranslated. The quality
  loop reviews for concatenated or catalog-bypassing text, and a new
  Localization practice card in the coding decision guide covers catalogs,
  plurals, explicit locales, UI expansion and right-to-left layout, and tests.
- `static-checks` now runs a quality loop on the Until Loop bound to the selected
  Improve card. ShipLoop writes the loop contract. Each iteration traces every
  changed public entry point with a valid, a boundary and an invalid input, then
  reviews the change against the new *Code craft* rubric: argument checks,
  contract docstrings, and comments that are useful rather than token-wasting.
  The loop ends after an iteration with only trivial findings, and a third
  iteration that still finds a material issue stops it. The stage accepts `done`
  only with a terminal packet that matches the contract; `repeat` is no longer
  accepted there.
  - The *Code craft* rubric replaces the implementation constitution. Step plans
    gain an argument-check/docstring criterion, test specs gain rejection cases,
    `verify` checks the loop's entry-point inventory, and the end-of-work Improve
    reviews against the same rubric.
  - The change inventory (tracked and untracked files since the item base) is
    recorded in every lint mode; `lint: off` still stops linters and auto-fix.
  - Fixed: the lint snapshot failed when the run directory sat inside the
    checkout and was git-ignored.
- A product fix committed after the workspace return no longer strands the run.
  Run `workspace plan-return` and `workspace return` again: the follow-up starts
  from the source state the previous receipt recorded and uses the same route
  (working-tree update or another fast-forward). The new receipt keeps the old
  one as `previous_receipt`. A source that already holds exactly the follow-up
  result (a fix copied in by hand) is recorded without writing; any other source
  change made since that receipt still blocks.
- Installing the ShipLoop plugin from the marketplace now sets up the status hook: the package carries generated hook files for Claude Code, Codex, Grok and Cursor. Claude Code and Codex show the status block to you after each ShipLoop call (Codex asks you to trust the hook once in `/hooks`). Grok and Cursor run the hook but cannot display it, so the in-packet block stays the display there. The hook now recognizes each host's payload shape.
- Every packet now carries a script-rendered status block: where the run is (phase, work item and stage group), what was just accepted, what comes next, the item's plan sentence and the completed items. The host shows it unchanged instead of writing its own progress summary. Each saved transition also writes `status.md` in the run directory, and the new `shiploop status` verb prints the block. On Claude Code, the optional `scripts/shiploop-status-hook` PostToolUse hook shows the block to you directly from ShipLoop's own output; see `references/status-display.md` for the settings snippet.

### shiploop-e2e-audit 0.4.4

- The Grok adapter recognizes ShipLoop's new read-only `status` verb as a direct ShipLoop subcommand.

### skill-interop 0.2.5

- The marketplace-hosts reference records plugin-bundled hook support for Claude, Grok and Codex.

### backchain 0.6.0

- Plan Dispatcher leaves the `backchain` plugin and ships as its own `plan-dispatcher` plugin; `backchain:plan-dispatcher` no longer exists, so install `plan-dispatcher` instead. Backchain's source now lives in Skill Craft, and `./install.sh --skill backchain` installs it from a Skill Craft checkout. The card now says that the harness, schema, fixtures and samples it mentions live in the separate Backchain development checkout and are not shipped with the skill.

### plan-dispatcher 0.3.0

- First release as its own `plan-dispatcher` plugin (previously `backchain:plan-dispatcher`). Its source now lives in Skill Craft, and `./install.sh --skill plan-dispatcher` installs it from a Skill Craft checkout.

### backchain 0.5.1

- Vendored from upstream a6eeda0056af

### shiploop 0.25.1

- A saved run whose Improve child sits at a stage that never starts one (anything other than a planning stage or the final carry-forward), or whose Improve result belongs to such a step, is now refused on load with a message naming that stage. `workspace return` relies on this check instead of its own active-child guard.

## 2026-09-24

### backchain 0.5.0

- Vendored from upstream 0f09091a9c3b

### shiploop 0.25.0

- Each step's exit criteria now carry their confirmation. Step-plan duties write every completion criterion as `<condition>. Confirm by: <command, observation, or inspection>; pass when <expected result>`. This includes whether inspection is sufficient, and an explicit `unconfirmable here` marker instead of dropping the criterion.

  The implement duty and chain worker packets loop until each criterion is confirmed. They never download a tool to confirm a criterion. They stop BLOCKED only for a criterion that is proven unachievable, and FAILED after 3 genuine attempts. Workers write an `exit-criteria.json` receipt, verify checks each item, and a retried step carries its prior attempts and their rejection reasons.

  New script-owned lint, set by the `lint: fix|report|off` run option (`--lint` on `init` and `workspace start`, `lint-mode --set` mid-run; new runs default to `fix`). It runs on entry to static-checks and verify. The model receives each linter's exact command and complete output, an applied auto-fix diff, per-file coverage and install recommendations. Deletion-type and unsafe fixes, version-manager shims, repo-local binaries and linters that execute repo code are never applied or run. Lint output is supporting output, never exit-criteria evidence.

### shiploop-e2e-audit 0.4.3

- The Grok trace adapter recognizes ShipLoop's new `lint` and `lint-mode` direct subcommands. The host trace fixtures are re-pinned to the updated adapter.

### improve 0.3.0-rc.5

- Improve vendors Until Loop 0.5.1, whose packets now ask for clear, evidence-grounded status updates without changing control flow.

### review-coverage 0.3.1

- The host matrix installs from whichguy/skill-craft, explains moving an old Claude registration without uninstalling plugins, and replaces the plugin sync step with a change note.

### shiploop 0.24.2

- The README and navigator reference say a ShipLoop source edit adds a changes/shiploop note and checks a fresh package build; plugins/ and catalogs are release output that ordinary work items never regenerate or commit.

### shiploop-e2e-audit 0.4.2

- The freshness gate reads the released plugins/<leaf> and its entry in skill-craft's own marketplace catalog on the same main, instead of the retired skill-craft-market repository; a pending change note stops the gate until release.

### skill-interop 0.2.4

- Skill Interop now names skill-craft itself as the marketplace, with release-output catalogs and commit-pinned external plugins, and its checklist asks for a change note instead of a plugin view sync.
