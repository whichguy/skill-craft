# ShipLoop implement-prompt audit — journal

Question: does the inner loop's **implement** packet give the model the right directions and reference material to
implement one step it has just received?

Started 2026-10-17. Status key: firm (shown by source and run evidence), interim (shown, impact not measured),
exploratory (a question to settle).

## Round 1 — 2026-10-17: read the prompt, render it, compare with a live run

**Method.** No model calls.

- Source on `main` at release 2.5.0: the implement duty is `DUTIES["implement"]` in
  [shiploop_prompts.py](../skills/shiploop/scripts/shiploop_prompts.py), with `_IMPLEMENT_INLINE` / `_IMPLEMENT_CHAIN`,
  `CODE_CRAFT`, `STAGE_REFERENCES["implement"]` and `IMPLEMENT_STEP_REVIEW_FOCUS`. The stage row is `Stage("implement", …)`
  in [shiploop_stage_spec.py](../skills/shiploop/scripts/shiploop_stage_spec.py). The step line comes from `_step_lines`
  and the hand-offs from `CONSUMES` in [shiploop_navigator.py](../skills/shiploop/scripts/shiploop_navigator.py). The loop
  Work line comes from `shiploop_loops.py`, in the row that holds `{step_change}`.
- A rendered packet: `python3 test/shiploop_e2e/packet_anatomy.py --walk <dir> --case battleship`. The no-model walk has
  no step data, so it shows the fixed text only.
- Live evidence: the 7 implement packets, step-plan result, loop contracts and `events.jsonl` of the Salesforce chess
  E2E run 2 (2026-10-17, Grok 4.7 medium, inline). That run's folder is not committed. Exported facts are in
  [shiploop-implement-prompt-audit-evidence/](shiploop-implement-prompt-audit-evidence/):
  - `sfchess-run2-implement-facts.json`: what the run read, each implement stage's cost, the step rows and test commands;
  - `sfchess-run2-implement-packet-anatomy.md`: bytes per section;
  - `sfchess-run2-S1-step-lines.txt`: S1's step line and the criteria it was handed.
- The run used the installed 2.4.x plugin. The renderer code the findings cite (`_step_lines`, `CONSUMES`, the loop Work
  line) is unchanged on `main`.

**What the packet gives the model today (works well).** It gives a clear scope rule: only this step's paths, no tests, no
later step. It says to change the work, never the check. It has a revise route with named triggers and a 7-attempt stop.
It asks for `not_covered` and for AD-n and command recording. Code craft is printed in full, because only implement writes
product code (owner decision in 7cdae9a0). R-n and AD-n are quoted by value through `follows`. Test-spec cases are
quoted with their oracles. Every implement step in the live run finished `done`.

### Findings

**F1 — The step's own contract is not in the packet. (firm)**
`_step_lines` prints only `step['task']`. The step row also holds `paths`, `criteria` and `skills`, and none of them is
printed. `CONSUMES["implement"]` is `("follows", "criteria", "test_cases")`, without `test_commands`. Yet duty 1 says
"edit its paths", duty 2 says "use each listed step skill", duty 3 says "run every recorded check command", and three of
the four Done-when lines depend on those values. The model has to open the step-plan result to learn them. The live run
read that result 7 times. This conflicts with the main tenet: a packet must survive context loss on its own.
*Fix:* print the step row: its paths, its criterion IDs and text, its skills (or "none"), and the exact check commands
that apply to it.

**F2 — At implement, "recorded check command" is undefined, and read literally it cannot be met. (firm)**
`test_commands` mixes `focused`, `regression` and `check` rows. The focused and regression rows run tests that the test
stage writes later. In the live run, `SLChessRulesTest` did not exist at implement. W1's `check` rows were the S1
file check, an `rg` check on `SLChessEngine.cls` (it fails until S2), and `sf project deploy start --target-org de`. The
deploy is an external effect, and the S1 task says "Do not deploy in this step". Done-when says "every recorded check
command exited 0". The step-plan author had to write around this in prose ("the recorded deploy command is the build
check after the class exists"). The loop contract only says "use the recorded commands from the accepted step plan".
*Fix:* define the set the implement stage checks: the `check` rows for the step's criteria, or rows tagged with the step.
Print that set and nothing else. Keep effectful commands out of the step's check set unless the step owns the effect.

**F3 — The packet prints the item's criteria, not the step's. (firm)**
S1 owns C1, but its packet quotes C1–C10 under `criteria (W1 step-plan)`. Nothing marks which criteria belong to later
steps. That invites overshoot, which the scope rule forbids.
*Fix:* quote this step's criteria. Name the rest once as owned by later steps (step ID only).

**F4 — Coding guidance is two hops away, and was barely opened. (firm)**
The packet links `coding-guidance.md#select-guidance`, a generic "select a card" paragraph. The step plan records its
selection in prose, for example "cards used are the Salesforce platform note, namespaces and placement, schema and
storage, and state", with no locators. Duty 2 says "Follow the step plan's Coding decision selection". In the whole
live run, the model read `coding-guidance.md` once, `platforms/salesforce.md` once, `coding-practices.md` once and
`house-style.md` once (`read_file`; no shell reads of `references/`).
*Fix:* step-plan records the selected cards as locators (a structured field). The implement packet then prints those
links directly, instead of the generic selection section.

**F5 — The house-style match contract does not reach the builder. (firm)**
`house-style.md#match-while-building` says to reopen the match contract and its exemplars in the step-plan result
before editing. The contract is a sentence inside the step-plan `summary`. The packet neither quotes nor locates it.
*Fix:* make it a hand-off value: the exemplar paths and what to match. That also gives verify something concrete to
compare against.

**F6 — The loop's Work line excludes the Services duty. (firm)**
The Until Loop argument says "Do duty items 1-4 … for step S<n>'s change". Duty 5 (Services: revalidate target state and
authority before any effect) and duty 6 (the stop and revise rules) fall outside "1-4". Only part of duty 6 is restated
in the argument. A step that touches a service is told to do the service-free subset.
*Fix:* "Do duty items 1-6", or fold Services into Build. The check is whichever test pins the Work line.

**F7 — Packet weight. (interim)**
In the live run, implement packets averaged 82 KB. The budget is about 7–9 KB, not counting quoted files and
hand-offs. Most of the 82 KB is uncut quotes: `environment.md` (14 KB, the same in every step), `architecture.md`
(5.7 KB), hand-offs (about 22 KB), the original request (4.7 KB), consumer-delivery declarations (about 4 KB) and
lint data (about 5 KB). Context peaked near 200k tokens in every implement stage. Quotes stay uncut by decision D1.
The open question is relevance: should a step get all of `environment.md`, or only its Commands, Harnesses and the
platform sections?

**F8 — Stale comments in `shiploop_prompts.py`. (firm, cosmetic)**
- The comment above `CODE_CRAFT` says implement, test, document and verify all carry it. Only implement does
  (7cdae9a0).
- "What a producer packet prints instead of CODE_CRAFT: one line per rule" sits after the rubric with no constant
  under it. The one-line form was deleted in 7cdae9a0.

**F9 — Self-checking against the quoted oracles is neither invited nor allowed. (exploratory)**
The packet quotes every test case with its oracle, but "Write no tests" and "download, install or fetch nothing" leave
it unclear whether a throwaway probe is allowed. The live S2 model built a local move generator in scratch and checked
the spec's counts (20, 48, 14, 44) before writing Apex. That worked well, but nothing asked for it.
*Question:* add one line: "Use the quoted cases as the target; a throwaway probe in RUN/scratch is allowed and is not a
test."

### Not yet established

- Whether F1–F5 cost quality, or only reads and time. Every live implement step passed. The model made up for the gaps
  by opening the step-plan result. Under context loss, a missed path or check would surface only at the lint and scope
  gates, or at Improve.
- This round has one live run, on one platform. A Node/Battleship run is needed before any claim about how the model
  behaves in general.

### Next (round 1)

Superseded 2026-10-17 by round 2: the owner asked for more audit before any fix. The grouping below still holds.

Owner to choose which findings to act on. The candidates group into one renderer change (F1, F2, F3, plus F5 if the
match contract becomes a field), one step-plan schema change (F4, F5), a one-line loop wording fix (F6) and comment
cleanup (F8). F7 and F9 need an owner decision first.

## Round 2 — 2026-10-17: a Node/Battleship run, and the step-plan side

**Question.** Do the round-1 findings hold on another host, model and platform? And where do they start: in the
implement packet, or in the step plan it is built from?

**Method.** No model calls. Evidence comes from the Battleship audit-fix run of 2026-10-16: claude-sonnet-5-5, plugin
2.4.0 / ShipLoop 1.4.0, inline, passed 4/4 checks, 274 turns, $5.46. It is the baseline row in a7c1fdb2. The run folder
`/Users/dadleet/e2e-runs/20261016/battleship-e2eaudit-4dd3b4b4` is not committed. Exported:
[battleship-run-implement-facts.json](shiploop-implement-prompt-audit-evidence/battleship-run-implement-facts.json)
holds the step rows, test commands, step-plan summary, each step's notes and result, and every tool call made during
step-plan and implement. [battleship-run-imp.sh.txt](shiploop-implement-prompt-audit-evidence/battleship-run-imp.sh.txt)
is the model's own wrapper script. The step-plan source read is `DUTIES["step-plan"]` and the step-plan
`Stage(...)` row on `main`.

**Shape.** One work item, three steps: S1 `game.js`, S2 `public/index.html` + `package.json`, S3 `server.js`. The
implement packets were about 53 KB each. They took 61 s, 41 s and 793 s, and 7, 4 and 13 tool calls.

### Round-1 findings on Battleship

- **F1 holds.** S1's packet prints the task only. Paths, criterion IDs, skills and check commands are missing again.
- **F2 holds, and is worse.** The item's only `check` row is
  `node --check game.js && node --check server.js && node --check test-support/helpers.js`. `server.js` comes in S3
  and `test-support/helpers.js` in the test stage, so the check cannot pass at S1 or S2. All three steps wrote this in
  their notes ("Full recorded check command also checks server.js and test-support/helpers.js, which later steps
  create: not runnable yet"). Each one substituted its own checks: `node --check` on its own file, a smoke script for
  the worked example, `curl` against a live server. ShipLoop accepted every step. So Done-when 2 ("every recorded check
  command exited 0") was false at every acceptance, and no gate noticed. The `Checked by` line does say the gate does
  not judge the work. Two hosts and two models now show the same thing.
- **F3 holds.** S1 owns C1, C2, C4, C5 and C9. Its packet quotes C1–C10.
- **F4 holds, and is worse.** The step-plan summary records no coding-guidance selection and no card links ("CommonJS,
  no package type field … design guidance fallback none"). In step-plan and implement together, the model opened no
  `references/` file: no coding guide, no house-style guide, no `platforms/node-express.md`.

### New findings

**F10 — Step criteria cannot be confirmed when the step ends. (firm)**
The step plan maps criteria to steps many-to-many, and criteria are item-level conditions. S1 is assigned C9 ("public
entry points (createGame, fire, createStore, createServer, resolvePort) validate…"), but two of those five functions
belong to S3. C4 ("no response carries the fleet layout"; a store cap) is given to both S1 and S3. Implement's
Done-when never names criteria at all: it checks paths, check commands, lint and `not_covered`. So no step proves
its own criteria. Implement's real exit is "it parses and lints". The proof comes later, in the test stage.
*Root cause, step-plan duty 4–5:* "Size each as one behaviour-level change a named check proves", but no field records
that named check per step. `test_commands` are item-wide, and duty 5 says only the test and verify stages run them.
*Fix direction:* each step names its own proof, as a `check` command or criterion that can pass when that step ends,
and the implement packet prints it. Or implement's Done-when says plainly that a step's proof is its own smoke check,
recorded in notes, with the item's commands run at test.

**F11 — The plan record is not an exit criterion, so it ends up as loose prose. (firm)**
Step-plan duty 9 asks for a long plan record: the coding-guide selection "with links to only the matching sections",
the match contract, namespace and collision checks, the design basis. None of it is in step-plan's `done_when`, and
the record lives "in the item's context or the summary". Battleship's summary is 999 characters with no links.
Salesforce's has the cards by name and no links. Duty 9 then says "This record is supporting reference; each step's
task and criteria stay its only directive". The implement packet never prints the record. This is the upstream cause
of F4 and F5.
*Fix direction:* move the parts implement needs into structured result fields, quoted by the implement packet: card
locators, exemplars and match items, failure cases per step. Or cut them from duty 9.

**F12 — In inline runs, implement works from memory, not from its packet. (firm for this run)**
The Sonnet model wrote `RUN/scratch/imp.sh`, which pipes each `complete` callback through `head -4 | cut -c1-300`.
After S1, it read its next implement packets only through that wrapper's output: the head line, the callback and the
Goal. For S1 it ran `sed` on three slices: the loop Argument, the Result template, and the duty with `head -70`. That
`head -70` cuts Code craft off at rule 7, so rules 8 (placement) and 9 (compose) never reached it in that read. It never
read the Step line, criteria, test cases or knowledge quotes from the implement packets. It built the steps from the
step plan it had written earlier in the same conversation. The packet's step context matters only after context loss,
and that is exactly the case where F1's gaps hurt. The step text, R-n quotes and test cases were 50+ KB the model did
not read.
*Question for the owner:* in inline runs, should the implement packet be short (the Step row, its proof, a pointer to
the duty, the callback), so the parts the model does read are the parts that matter?

**F13 — The per-step Improve review was a scripted one-liner. (firm; adjacent, Improve side)**
`IMPLEMENT_STEP_REVIEW_FOCUS` calls itself "the only check of the code before them [the tests]". In this run,
`imp.sh` wrote `# Review 1 (self-review)` with a one-sentence note, wrote "no executable checks apply" to `checks.md`,
reported the review trivial and satisfied, and submitted. The S1 and S2 step reviews went through it, each one pass
with no edits. S3 got two reviews and one small edit. None of the notes touches the focus list (docstrings, placement,
compose, i18n, `not_covered`). Same-context self-review is the owner's default (delivery-overhead plan, 2026-09-24).
What is new here is the model scripting the review ceremony. The implement prompt counts on this review to catch what
implement misses, so it belongs in the audit, but its fix is on the Improve side.

**F14 — Duty 2 conflicts with the owner's look-back rule. (exploratory)**
Implement duty 2 says "Read history or earlier reviews only when a check fails". It came in with the 2026-10-11 re-cut
(153139f1). The owner's requirement of 2026-10-10 says to reference at least the last couple of commits on every step
iteration. Row 14 of docs/shiploop-artifact-flow-2026-10-11.md already notes that "no implement packet mentions
`git log`". That leaves the cross-step learning channel, the earlier steps' Improve commits, unread. *Owner decision:*
which rule wins, or should the packet itself quote the last two Improve commit subjects?

### Status after round 2

| Finding | Status | Where it starts |
|---|---|---|
| F1 step row not printed | firm, 2 runs | implement renderer (`_step_lines`, `CONSUMES`) |
| F2 check set undefined | firm, 2 runs; Done-when false at every acceptance | step-plan schema (item-wide `test_commands`) + implement wording |
| F3 item criteria printed | firm, 2 runs | implement renderer |
| F4 coding guidance unused | firm, 2 runs; 0 reference reads on Battleship | step-plan record (F11) + implement references |
| F5 match contract not delivered | firm | step-plan record (F11) |
| F6 loop Work line "1-4" | firm (source) | `shiploop_loops.py` |
| F7 packet weight | interim; 53–87 KB, mostly unread inline (F12) | renderer, D1 decision |
| F8 stale comments | firm, cosmetic | `shiploop_prompts.py` |
| F9 probes allowed? | exploratory; both models probed anyway | implement duty |
| F10 step criteria not confirmable at step end | firm, 2 runs | step-plan duty 4–5 |
| F11 plan record not gated | firm, 2 runs | step-plan `done_when` / duty 9 |
| F12 inline implement reads little of its packet | firm, 1 run | packet design |
| F13 scripted step review | firm, 1 run | Improve runtime (adjacent) |
| F14 history-read rule vs owner rule | exploratory | implement duty 2 |

**Not yet established.** Whether these gaps lower code quality. Both runs passed, and the model made up the
difference each time from context or its own smoke checks. That needs a context-loss probe: resume an implement step
in a fresh session from its packet alone, and compare the code with the inline result. A delegated (`ask-agent`) run
would show the same thing, since its worker has only the packet.

### Next

Owner decision on F9, F12 and F14, and on whether to run the context-loss probe before fixing. The fixes group as
follows:
- (a) step-plan schema: a per-step proof, and structured card and match fields (F2, F4, F5, F10, F11);
- (b) implement renderer: print the step row and its proof, and quote only its criteria (F1, F3);
- (c) one-line wording fixes (F6, F8);
- (d) an Improve-side question on scripted reviews (F13).

## Fix plan — 2026-10-17

The owner chose to skip the context-loss probe and plan the fixes for groups (a) and (b):
[shiploop-implement-step-fix-plan-2026-10-17.md](shiploop-implement-step-fix-plan-2026-10-17.md) (`Execute: ask`).
- Its core is a per-step `check` that ShipLoop runs at implement `complete` (A1, A2), plus `cards` and `match` as
  result fields (A3, A4), and a renderer that prints the step row whole and quotes only that step's criteria and cases
  (B1, B2).
- Recommendations: F9 adopt one sentence (probes allowed, never the proof); F12 reorder and trim, no second packet
  shape; F14 the script quotes the last two commits.
- Fourteen fail-first tests are listed. Round 3 will be one live Battleship run after the change.

## Finding F15 — 2026-10-17: the printed head has no step block (firm, source)

Implement packets are 53–87 KB. That is far over `PRINT_LIMIT` (16,000 bytes), so `emit()` prints `packet_head()`
and writes the whole packet to RUN/packets/<id>.md. `_step_lines` is called only from `render()`, so **the step's
task is not in what the model is shown.** The head carries the goal, status, duty, references, result template and
loop command, but not which step this is.

The step-by-step walk itself was confirmed on 2026-10-17:
- `python3 test/shiploop-delegation.test.py -k one_packet_per_step -k snapshot_does_not_list_implement` passed, 2
  tests OK. It covers `apply()` after an inline implement done: while `implement_progress` shows steps left, it
  issues a new implement action for `steps[done]`.
- The Battleship run had three implement actions (S1, S2, S3), each followed by its own Improve child.

The consolidated fix plan (§2.2, §5) puts the step block and the closing `/until-loop` in both `render()` and
`packet_head()`; test T8 pins it.

## Consult — 2026-10-17: Astra on the anchored implement prompt

- **Question:** [astra-question-2026-10-17.md](shiploop-implement-prompt-audit-evidence/astra-question-2026-10-17.md).
  It held the plan's §3, the owner decisions and eight review questions.
- **Answer:** [astra-review-2026-10-17.md](shiploop-implement-prompt-audit-evidence/astra-review-2026-10-17.md).
  Persona codex-astra, gpt-6-astra, effort xhigh, no fallback.
- **Key finding (firm, matches the host's own critique):** the completion contract asked one step to satisfy whole
  requirements that later steps finish. That encourages building ahead, fabricated evidence or an endless loop.
  Fix: the step's criteria are the unit of completion, and R-n and AD-n stay binding constraints.
- **Other adopted points:** anchors as a comparison checklist; read the listed cards first; a departure is a revise,
  not an AD-n; state transitions are prepared, not run; observational evidence; a method sequence around the
  checklist.
- **Deferred:** the ask-agent assigned-steps slot.
- The disposition table is §10 of the fix plan. In the same turn the owner added six engineering directions (D8) and
  the static-file rule (D9); see §3.5 and §3.6.

## Round 3 — 2026-10-18: incorporate the public Battleship run analysis

The owner supplied [Battleship Run Analysis](https://claude.ai/artifact/4dwjgqaNCzRCCj5tzUr5ey) and then made it
public. The public page and its local publication README bind it to `bs-sf-int-b7c77f`. This is a newer run than the
chess audit, on frozen source `7fecda449ca4`; the integration worktree inspected here is `c70a33f46ed7`, while the
canonical checkout remains `17ddec369f49`. No new run, runtime edit, deployment or commit was performed here.

- **Firm retained outcome:** lifecycle `done`, overall `FAILED`; five selected case checks passed, source returned
  uncommitted, browser not declared/probed and rendered consumer behavior unrun. Platform cleanup later verified
  snapshot restoration. These claims are separate; the public report's “done” does not mean full delivery passed.
- **Report findings incorporated:** source-string step Proofs, remote candidate/base/mutation mismatch, repeat
  mutation and missing immediate restoration, unchanged-code step replay, hidden schema/loop rules, missing
  platform command facts, unresolved consumer observation and tool-state return problems.
- **Plan update:** [the existing fix plan](shiploop-implement-step-fix-plan-2026-10-17.md), §§0.2, 4.3–4.5, 6–7,
  10.4 and 11.4–11.6. Correctness priorities remain step-specific proof and valid acceptance; examples stay generic.
  Existing integration fixes are acknowledged so later implementation begins with the residual delta.
- **Coverage of the supplied analysis:** the [disposition index](shiploop-implement-prompt-audit-evidence/battleship-analysis-disposition-2026-10-18.json)
  maps all 91 gap entries from four published source analyses into nine groups. Overlapping entries are not 91
  distinct defects. Each entry retains a source pointer/hash, plan location and proposed acceptance checks.
- **Qualified/rejected suggestions:** no automatic equivalence from an empty diff, no unconditional destructive
  sentinel, no claim every dry run lacks effects, no old absence promoted to current proof, no file-open telemetry
  success gate and no replacement of the owner's two-commit context with a seven-commit quota.
- **Later decisions reconciled:** the integration plan records the owner's locator-based knowledge choice and
  unchanged-evidence reuse. Qualify those mechanisms and restore essential command facts; do not revive the old
  blanket whole-file-loading deferral. F15's historical `PRINT_LIMIT` reference above should read **characters**,
  not bytes; actual emitted size, retained file size and consumed tokens remain different measures.

The plan's T36–T48 are proposed validation cases, not executed tests. Authoring checks cover structure, references,
source mapping and example syntax. Runtime behavior and controlled prompt-performance improvement remain unqualified.

The [Opus delta review](shiploop-implement-prompt-audit-evidence/opus-battleship-plan-review-2026-10-18.md) returned
successfully from verified `claude-opus-5-5`, xhigh, without fallback. Adopted: reconcile v7/source already present;
correct platform-card data before propagating it; restore the accepted candidate after mutation and recover pending
restores; compare normalized records exactly, reuse only an unchanged prefix, and rerun retained Proofs by script;
render authority from one source. General remote-freshness tracking and file-open telemetry remain outside the
generic contract. Restoration still must cover non-source effects where a redeploy does not undo them.

Follow-up inspection resolved a material question from that review: the retained system-test-author result called
the post-release UI interaction required, but release-verify accepted without it and cited no owner waiver. This
is now an obligation-continuity/no-reply case in T44, with the two hashed records in the disposition evidence.


## Round 4 — parallel Chess analysis and reference-code validation (2026-10-18)

Owner request: incorporate the parallel report and anchor every consideration in the code that supports the
recommendation, assuming the recommendation baseline has not evolved. The public second URL renders
[Chess Run Analysis](https://claude.ai/artifact/PeHgXZ2M19JYSRsx4ebV1s). The publication README binds it to the same
retained Chess run already audited; it is not evidence of a third live run.

Updated the existing plan in place. Its priority remains executable step-specific Proof, valid procedures and
actual acceptance, before prompt concision. The new [Chess index](shiploop-implement-prompt-audit-evidence/chess-analysis-disposition-2026-10-18.json)
covers all 58 gap entries in three source analyses plus eight ranked fixes. Existing 91-entry Battleship evidence
now maps to the same recommendation IDs. Repeated entries and differently scoped metrics remain attributed;
no aggregate causal saving or count of independent defects is inferred.

The [code map](shiploop-implement-prompt-audit-evidence/integration-c70a33f4/reference-code-map-2026-10-18.md) links all eight considerations,
14 Code craft rules and 21 recommendation groups to the recorded integration revision
`c70a33f46ed71cd2eed537353438cdd61c51a2ba`. Exact source excerpts, original paths/line ranges and SHA-256 hashes are
retained beside it. Source was read with `git show`; no checkout or runtime source was changed. Current-checkout
line drift is irrelevant to these frozen excerpts. Existing tests are extension sites, not executed new coverage.

The source check corrected stale implementation status: per-step checks, optional step paths, the common Step
block, closing-loop order and `_improve_change_gate`'s re-proof already exist. Preserve and qualify them; add only
the remaining evidence/schema/rendering changes. The current UI and module-format duties already have conditions;
retain those rather than claiming they are wholly unconditional.

Newly explicit actions: preserve untouched steps through the Improve revision; review inherited procedures at
carry-forward and before a person ask; retain a run-owned stage-loop directory; review regenerated tool state
before source return. T49 covers loop recovery, T50 generic applicability and T51 a measured outer-command reuse
pilot. T34/T41/T44 extend existing proposed coverage. Runtime API replay is conditional on equivalent state and
existing authority; it cannot establish rendering. A short reply confirms only its stated observations; unconfirmed
behavior is neither a pass nor an automatic waiver. Honor a declined check without repeatedly asking. Keep existing
explicit correction/replan semantics rather than adding a bypass for release verification.

Two focused source-mapping agents returned read-only anchors. The coordinator corrected imprecise anchors and
verified the selected excerpts. A final read-only review found one ambiguity: §4.1's required Proof wording could
apply to the whole-plan ask-agent route. It now explicitly applies only to inline implement and its step Improve.
The previous Opus advice was reused; no new Opus consultation, runtime suite, live trial or performance claim was made.

Document validation checks source/excerpt hashes and line links, complete gap/ranked-fix coverage, all plan T-IDs,
and Markdown structure. Visual rendering was not inspected: the earlier local-file browser policy denial remains
in force. The plan and source map are saved for review; runtime implementation remains outside this update.

Final structural/source verification passed: 93 exact code excerpts from 28 source files, all 149 report gap
entries, eight Chess ranked fixes, all 51 proposed test IDs and the local line links. The two illustrative Python
commands parse; they were not executed. Full evidence is in
[reference-validation-2026-10-18.json](shiploop-implement-prompt-audit-evidence/integration-c70a33f4/reference-validation-2026-10-18.json).

## Round 5 — main refresh and loop responsibilities (2026-10-18)

The owner requested a rebase from main and renewed code anchors. Fetched `origin main` and ran
`git -C /Users/dadleet/src/skill-craft rebase origin/main`. The checkout was already on `main` at
`17ddec369f49383f9436ea4f2c6fba7c0c54f643`, matching fetched `origin/main`; Git reported it up to date.
Tracked source and the index remained clean. The separate integration worktree was not changed.

Updated the [existing plan](shiploop-implement-step-fix-plan-2026-10-17.md) and rebuilt the
[current code map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-18.md) against main:
105 exact anchors across 31 source files, eight considerations, 14 Code craft rules and 22 recommendation groups.
All 149 published gap entries and eight ranked Chess fixes remain mapped. The Round 4 integration map is retained
in its own historical directory; it no longer supplies present-tense implementation assertions.

This refresh changes implementation status materially. Main has state version 6, requires step paths and lacks
the integration branch's shared Step block, per-step Proof gate, proof reuse and implement re-proof after Improve.
Its implement completion gates are the loop terminal and lint; requesting checks in prose does not establish a
script-owned step execution gate. The plan now proposes those missing changes explicitly. Main's inline `--notes`
contract, platform cards, consumer templates and E2E source-return check also have their own verified anchors.

The loop recommendation is one authoritative step directive, a production Until Loop that establishes the
assigned criteria with current observations, then Improve using its existing loop. Do not add a nested Until Loop
inside every Improve pass. Work carries direction, criterion IDs, scope and exclusions; Exit carries completion
conditions once. Source anchors locate an implementation and do not prove behavior. The generic before/after
examples distinguish these obligations and avoid asking one step to complete later-owned delivery items.

Verified Opus advice (`claude-opus-5-5`, xhigh, no fallback) is retained in the
[loop review](shiploop-implement-prompt-audit-evidence/opus-loop-direction-2026-10-18.md). The consultation preceded
the main refresh and used the integration baseline; it is not an independent review of main. The coordinator
rechecked its applicable conclusions against main. Adopted: retain regression and scope clauses, preserve IDs in
the short Work directive, separate whole requirements from assigned criteria, and use the actual terminal-receipt
path. No automatic packet-budget increase or additional review quota was adopted.

Two focused source reviews and a final semantic review were incorporated. The final review prompted two
clarifications: target check behavior is marked proposed, and the owner's earlier D7 Repeat-policy change is
distinguished from prompt shortening. T52 covers the broader Repeat policy, leaving 52 proposed validation cases.
Those cases have not been implemented or executed in this plan update.

The [Round 5 reference validator](shiploop-implement-prompt-audit-evidence/validate-reference-map-2026-10-18.py) checks current and
historical source hashes, exact excerpts, local links, report mappings, proposed test inventories and selected
AST assertions about main. Its [result](shiploop-implement-prompt-audit-evidence/reference-validation-2026-10-18.json)
records the checks performed. This was a documentation and provenance refresh: no runtime implementation, live
trial or performance comparison was performed. Visual rendering was not inspected; the prior browser policy
denial was not bypassed.

## Round 6 — latest main, implemented mechanisms and remaining acceptance work (2026-10-25)

Fetched `origin main` and successfully rebased with `git -C /Users/dadleet/src/skill-craft rebase --autostash origin/main`.
The checkout advanced 29 commits from `6ed817622426dcfde4840a4b5bac945bc64f151a` to
`e707b794de0a0bd802988ca68dac8e29ac0b3315`; HEAD and fetched main agree. The Round 5 baseline is 218 commits behind,
including merged history. The seven existing tracked experiment patches retained identical added/removed lines,
and all 148 initially untracked files retained their bytes immediately after rebase. One edited E2E test also
received upstream changes. [Preservation receipt](shiploop-implement-prompt-audit-evidence/rebase-preservation-2026-10-25.json).

Refreshed the [same improvement plan](shiploop-implement-step-fix-plan-2026-10-17.md) and retained its exact
[Round 5 snapshot](shiploop-implement-step-fix-plan-2026-10-17-as-of-2026-10-18.md). All 22 recommendation IDs,
eight considerations, fourteen Code craft rules and 52 qualification IDs remain accounted for. The qualification
catalogue distinguishes implemented mechanisms, remaining semantic checks, later decisions and deferred pilots;
it is not a claim that 52 new tests ran. Every recommendation is linked through the
[new code map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-25.md) to exact committed-source
excerpts: 105 anchors across 24 source files. Both older maps remain pinned to their own revisions.

The status changed materially. Main now has state version 9, a shared Step block, script-run step Proof with bound
receipts, Improve re-proof, procedure/access guidance, test layers and a primary lower-layer acceptance gate.
Candidate/step receipt reuse exists. Later committed owner decisions chose the static consideration guide without
new mandatory assessment fields, the first-trivial Improve policy, and deferral of base/mutation caching. The
earlier proposed `criterion_evidence`/consideration forms, two-trivial rule and full printed loop argument are
therefore not outstanding implementation requirements. Generic before/after examples preserve assigned C/R/AD
bindings and recovery locators; optional Work shortening does not add another loop or broaden completion to later
delivery items.

The final semantic read kept three earlier Code craft expansions visible: CC3's complex-unit documentation,
CC6's release on every exit and CC9's composable-unit design remain absent. The later lean-port record does not
explicitly reject them. R04 is therefore partial with its structural rewrite superseded; these three additions
remain low-priority proposals, rather than being silently treated as implemented or canceled.

The highest-priority remaining defect was reproduced against pinned committed scripts: the candidate judge
recognizes a failed test tally and named failed outcome, yet returns passed when a wrapper exits zero, in both
focused and check modes. [Probe and retained input/result](shiploop-implement-prompt-audit-evidence/judge-zero-exit-probe-2026-10-25.json).
This is helper-boundary evidence, not a new live workflow result. The repair plan calls for real-callback coverage,
reporter-aware negative/positive controls and prevention of false passed IDs reaching primary acceptance; old
cached verdicts must be reconsidered if judge semantics change. T37 still separately covers intended-copy
identity and the distinction between current nonzero mutation kills and behavioral proof.

The next priorities are inherited-procedure validity, requirement-to-obligation continuity and external-state
freshness of existing reuse. These need adversarial fixtures before claiming a missing gate. Concrete narrower
changes remain for Improve probe-authority wording, actual release state across all four source locations, the
misleading residual-review message, and run-owned loop backing state. Remote mutation restoration is conditional
on introducing such a route; current mutation excludes remote commands. Prefix reuse and further prompt
compression remain measured pilots.

Three focused read-only source audits were incorporated and corrected against the actual code. The independent
[Opus review](shiploop-implement-prompt-audit-evidence/opus-main-refresh-2026-10-25.md) completed with verified
`claude-opus-5-5`, xhigh, no fallback. Adopted its broader judge/downstream-pass scope, full release wording coverage,
optional Work status and narrower residual-review fixture. Its legacy-directory concern was qualified against the
actual supported isolated receipt route; preserve fail-closed recovery rather than resetting state.

Six established suites exited zero, totaling **329 tests**. All 5,715 tracked hashes and the source revision were
unchanged across that suite run. The worker's broader receipt is **INCOMPLETE** because nine undeclared untracked
experiment-sync files appeared; no attribution to the tests is asserted. The
[full receipt and logs](shiploop-implement-prompt-audit-evidence/checks-2026-10-25/result.json) retain both facts.
A later local `shiploop_lint.py` edit was preserved and is not covered by those results or this committed-source
audit. No runtime fix, commit, push, full suite, CI refresh, installed-host check, live trial or performance
comparison was performed by this refresh.

Both published reports remain incorporated: all 58 Chess and 91 Battleship gap entries, plus eight ranked Chess
fixes. Their eight retained source files relocated from the old integration checkout to the main experiment
directory; each original SHA-256 matches. The current indexes retain the historical paths and current locators.
The [Round 6 validator](shiploop-implement-prompt-audit-evidence/validate-reference-map-2026-10-25-e707b794.py) checks both historical maps,
current source/excerpt hashes, link lines, report mappings, all IDs, selected code assertions and evidence receipts.
Its [current result](shiploop-implement-prompt-audit-evidence/reference-validation-2026-10-25.json) is provenance
validation, not runtime acceptance. Visual rendering was not inspected; the earlier policy denial was not bypassed.

## Round 7 — resolve the experiment conflict and re-anchor to advancing main (2026-10-25)

The owner asked for a main-based verification because of a suspected conflict, then explicitly included the effort
experiment. There were two real unmerged files, `run.py` and `slice.py`, from a stash application, with no active
Git rebase/merge operation. The initial HEAD was `621beeb0`; fetched main was `5d3628b0`. All merge stages and the
seven existing changed files were saved. Another process restored the two runtime files to main during inspection,
leaving experiment tests active. The reconciliation used the saved three-way inputs, preserving both upstream timing
and the local scheduler rather than treating a clean index as proof of complete recovery.

Main advanced while this work ran. Repeated rebases brought the checkout to `ef3fb8be50b9223876517315413dabb34ec854c0`;
the final rebase preserved all 238 pre-existing files checked. The runtime delta through `891be21e` adds recognized
runner output at prepare and repairs a prompt line break. Later commits add the Improve-schedule proposal and
separate suite-runner tooling. The final fetch found one more documentation-only commit, `98983fa2`, which also rebased cleanly; all seven
tracked local edits retained their bytes. The delivered checkout and observed origin/main match at that revision. [Preservation](shiploop-implement-prompt-audit-evidence/main-98983fa2/pinned-rebase-preservation.json).

The existing plan now retains all 22 recommendations, eight considerations, fourteen Code craft rules and 52
qualification IDs, with **128 exact excerpts from 33 source files**. All 58 Chess and 91 Battleship gap entries and
eight ranked Chess fixes remain mapped. Nine excerpts from the prior completed audit changed in content. The
source validator checks hashes and locations; it does not imply all behavioral qualifications passed.

The old zero-exit failed-tally defect is fixed. Two narrower cases are reproduced on the new committed source:
a mixed pytest pass/error summary still passes, and an obsolete false-pass candidate receipt is reused. R08 is
partial. Per-step paths remain optional while item paths are required; the 4/3 sizing rule is prompt guidance.
Revised Improve results now get the specific producer-field bounds. Removed loop caps are distinguished from
Grok's host cap, the model-applied seven-attempt rule and the per-command timeout.

The plan also incorporates the corrected run-5 timing interpretation: the 125.2-minute window includes stage work;
approximately seven minutes before grounding is an estimate from call counts. The separate Improve-schedule
proposal remains awaiting approval. Its panel revisions support validating each transition and keeping skip rules
in shadow mode; they are not implemented behavior or new authorization from this audit.

The effort merge restores the schedule, first-launch wiring, restart records and resume command. It also repairs a
zero ordinary-resume budget suppressing an effort boundary, an effort variable shadowing the module, schedule
metadata, and selecting the right fresh session after a clear. Three focused regressions passed, followed by both
full harness suites. After the new prepare gate landed, **716 selected tests passed** on an isolated checkout with
identical source hashes before and after. The original failed checks remain retained. Four reconciled files were
applied only after destination-byte checks; they match the tested snapshot. The source-identity comparison covers
4,334 captured source/test files, with explicit exclusions for unrelated rubric work and later suite-runner changes.

[Reconciliation](shiploop-implement-prompt-audit-evidence/main-98983fa2/conflict-resolution.md) ·
[verification](shiploop-implement-prompt-audit-evidence/main-98983fa2/verification.json) ·
[source map](shiploop-implement-prompt-audit-evidence/main-98983fa2/reference-code-map.md).

No remaining engine recommendation was implemented, and no commit, push, release, live host/platform trial or
performance comparison was performed. Visual rendering was not inspected; the prior browser denial was not bypassed.
