Execute: ask (revision 2, 2026-10-18; every recommendation and decision below is accepted by the owner: "I'll go with your recommendations", "incorporate all of your recommendations on the proposals")

# Run insights plan (revision 2, 2026-10-18)

Consumer: the owner, to approve the waves; then the sessions that build them. ShipLoop must stay **generic**: these
runs (Salesforce chess and Battleship) are examples whose lessons are generalized; nothing here tailors ShipLoop to a game
or to one platform, and platform detail lives only in `references/platforms/`.

Evidence (committed): `docs/experiments/run-insights-2026-10-18/` — `fix-catalogue.json` (every recorded fix: 64 open
items, 20 already fixed, 19 conflicts resolved, all 149 run-analysis gaps, 18 report fixes, 8 SDLC recommendations and 31
packet-review findings each placed in exactly one item), `test-audit.json`, `files-audit.json`, `outcomes-audit.json`,
`step-commit-audit.json`, the template audit (`packets-audit.json`, `templates/`) when it lands; earlier evidence in
`docs/experiments/run-analysis-2026-10-18/` and `docs/experiments/packet-review-2026-10-17/`. Reports: chess
https://claude.ai/artifact/PeHgXZ2M19JYSRsx4ebV1s, Battleship https://claude.ai/artifact/4dwjgqaNCzRCCj5tzUr5ey.

## 0. Owner directions (2026-10-18)

1. Generic ShipLoop, lessons derived from the runs.
2. Git commit history is the key record of lessons: a local commit per step with a verbose message (key learnings, key
   decisions, evidence, related commits); a step's planning quotes the last two or three commit messages.
3. Learnings update the stored documents: an implicit requirement, decision or environment fact a step discovers becomes
   explicit in HOME/spec.md, HOME/architecture.md or HOME/environment.md.
4. The inner loop sees one step at a time.
5. Every file ShipLoop produces is intentional, in one deliberate place, with named consumers; no extraneous files.
6. Allowed outcomes are few, clear, and mean exactly what the navigating scripts do.
7. Packets concise, not repetitive; be strict: each stage's script returns a **template** prompt whose fixed text lives in a
   template file and whose slots the script fills, including by-value content of files earlier stages produced; the
   model's result is a filled template the script parses.
8. Test planning covers every case with executed tests whose output is visible; it uses the testing tooling and common
   practices of the target environment (for a UI: the framework's component runner and a headless browser such as
   Chromium through the Chrome DevTools protocol).
9. Stale temp files deleted: done 2026-10-18 (4,907 `innerloop-*.json`, 75 MB, moved from the system temp directory to
   the Trash folder `innerloop-stale-2026-10-18`; K3 stops new ones).

## 1. Method: how every fix updates ShipLoop

Every fix in this plan is an instance of one of these mechanisms (`fix-catalogue.json`, `methodology`). A change that fits
none is questioned before it is built.

| # | Mechanism | Rule | Test |
|---|---|---|---|
| M1 | The packet is the contract | Every rule, accepted value and row shape a gate enforces is printed where the model acts, generated from the table the gate reads, so text and gate cannot drift. A model never needs ShipLoop's source. | The printed text is built from the gate's own table; a test fails if they differ. |
| M2 | The script owns it | What the script can know or compute (tree identity, reuse of a passed run, routing, which paths to commit, whether a command reads the tree) it decides, records and prints; what it can check it refuses, and every refusal names its way out. | A route test submits the refused input through the real `complete` and then the named fix. |
| M3 | By value, once | Content a step acts on is printed by value where it is used, one home per fact, once per packet; the rest is a locator. | Render diff and the obligations ledger. |
| M4 | One step's context only | A packet carries what this step needs; inapplicable duties shrink to a one-line trigger; pointers open only their section. | Packet tests on what a step packet contains about other steps. |
| M5 | Evidence is a script-run command with visible output | A claim is backed by a command that ran against the tree or target under test, with saved output a person can read; a check that reads the implementation's own text, or a run that cannot see the candidate, is not evidence. | Fail-first tests with mutants and sentinels. |
| M6 | Platform knowledge lives in the platform card | Runners, reporters, deploy-before-test, tool-state paths, access probes and the environment's test tooling are written once in `references/platforms/<platform>.md` (machine-readable parts declared there) and linked where decided. | A card/parser consistency test. |
| M7 | One writer, named consumers | Each output has one writer and names who reads it, when, in what form; tool state is never silently committed; a person's item is answerable. | File-inventory test of a dry run. |
| M8 | Recovery state is printed, not searched | What a model needs after compaction, revise or reboot is printed in the text it reads first. | Compaction-recovery tests. |
| M9 | One wording per rule | A rule has one wording in one home; contradictions are fixed at the home; permissions are stated positively. | Grep tests for duplicate wordings. |
| M10 | Decide early, prove late | Each SDLC concern is decided as data at the earliest stage that owns it, carried by ID to the steps and checks that prove it; gates check structure, Improve judges substance. | Concern-map gate route tests. |
| M11 | Learn into the record (new, owner direction 2-3) | Each step's learnings and decisions go into its commit message and, where they change a requirement, decision or environment fact, into the HOME document that owns it; later steps read them back. | Step-commit and write-back route tests. |

## 2. The owner's key concern: does the step plan consider the SDLC?

**No, not as a design discipline.** Both runs decided several concerns well, but upstream (spec non-functional
requirements, plan decisions AD-n) from rich duty text, and step-plan inherited them only as `follows` IDs. Step-plan's own
concern surface is duty 9, a free-text "Plan record" that no gate checks and no loop exit condition names; all four
step-plan results skipped or shortened it. No SDLC dimension is checked by a gate at any stage. The models follow gates,
not guides: neither run opened `plan-record.md`, `coding-guidance.md` or `platforms/ui.md` (which already holds the
overlapping-request and accessible-name rules both runs broke), and every step-plan Improve pass reviewed only the
precision of criteria and check commands.

| Concern | Asked by a prompt | Battleship | Chess | Gap |
|---|---|---|---|---|
| User interface | yes | decided; never seen rendered | same | the UI card is never opened; rendered check is a last-stage person task |
| System API (contracts, callers, versioning) | partly (no versioning) | input `game` never validated | good | caller compatibility and versioning asked nowhere; entry-point criterion unenforced |
| Messaging (events, async) | yes | N/A stated | N/A stated | none here |
| State storage, schema, ownership | yes | excellent | good | plan-record per-field migration and round-trip never opened |
| Migration before the change | only for a new schema | N/A stated | N/A stated | no plan/step-plan duty asks backfill or old-reader compatibility and its order |
| Migration after the change | only at release-plan | N/A stated | N/A stated | no one asks whether a cleanup/contraction item is owed |
| Deployment switchover | only at release-plan and prepare | good, but test deploys put mutants on the delivery org | poor: the tab was hidden; the owner granted access by hand | activation and test-vs-delivery target decided too late |
| Concurrency | only "simultaneous changes" at spec | overlapping clicks unplanned (an Improve caught a race later) | shipped a stale-response race in `play()` | overlapping requests from one client and a second session are named in no duty |
| Use of existing platform services | yes | good | good | step-plan does not ask per step which service it reuses |
| Scale up and down (limits, quotas, cost) | yes | good (query/DML limits) | excellent (CPU, heap measured) | no explicit scale-down/cost line |
| Security and access | yes | good least privilege | tab visibility unplanned; org username committed to docs | identity kept out of knowledge by no rule |
| Observability and operations | yes | good | plan-level only (operations never ran) | operations stranded when release-verify blocks |
| Configuration and secrets | weakly | fine | identity in docs | no configuration decision in plan/step-plan |
| Performance limits | yes | adequate | excellent | none (best-served concern) |
| Accessibility | only at spec | partial (100 unlabeled buttons) | partial (glyph-only squares) | "invent no level" read as "no accessibility work" |

The implement-step plan's eight considerations (`docs/shiploop-implement-step-fix-plan-2026-10-17.md` §3.2) cover about 11 of
the 15 concerns, but at implement, after the step order is fixed and with no gate.


## 3. New themes from the owner's directions

**N1. Strict stage templates (direction 7; M1, M3, M9).** Each stage has one template file holding all its fixed text;
the script fills named slots only: scalars (ids, paths, counts), blocks rendered from state (the step block, gates, open
items), and file-inclusion slots that insert by value an artifact an earlier stage produced (a result field, a HOME
section, this step's plan row), each with its source and a size bound. The template also carries the exact result form
the model fills (keys, allowed values, one example row), so the model's answer is a filled template the script parses. A
validator fails a build when a template names an unknown slot or leaves one unfilled; a test proves every packet is
template text plus slot values. Builds on `static_text` (implement-step plan §3.6). Pilot step-plan and implement, then
migrate one stage per change, folding that stage's prose fixes (themes E, F, G, H, M below) into its template as it moves,
so no text is rewritten twice. Template audit (step-plan and implement written in full with Battleship values) is folded
in when it lands.

**N2. One step at a time, commits as memory (directions 2 and 4; M4, M11).** A step packet shows the current step in full,
earlier steps as one line each (step id, short commit, headline), later steps as a count only, one pointer to the step
plan (not three) and no duplicate last-summary block (`step_block`, `handoff_lines`, `_builds_on_lines`,
`_last_accepted_lines`). When an implement step is accepted, ShipLoop commits that step's changed declared files before
any Improve edit, with subject `feat(<item>/<step>): <headline>` and body sections Key learnings, Key decisions (from the
result), Evidence (built by ShipLoop from the checks it ran) and Related commits (checked `Learned-from` lines); the
Improve commit then holds only its own diff; a step with no change and no learning gets no commit. Results gain required
`learned` and `decisions` (`["none"]` allowed) and optional `learned_from: [{commit, contribution}]`, which `complete`
checks are reachable from HEAD (this reinstates `learned_from`, removed on 2026-10-10 because citations never reached a
commit; now they do). Step-plan, test-spec, implement and the step's Improve hand-off quote the last two non-bookkeeping
commit messages by value, anchored at the step's starting HEAD, plus on a revisit the step's own previous commit.
Measured on Battleship: no step wandered into a later step's files, but learnings were lost (S3's race lesson reached no
later packet; 0 of 8 implement steps ran `git log`). Supersedes plan item E6's `git log -7` line.

**N3. Learnings update the stored documents (direction 3; M11, M7).** A step's or stage's result names, for each learning,
whether it changes a stored document: an implicit requirement made explicit (a new R-n or an acceptance line in
HOME/spec.md, marked with its source step), a decision (the next AD-n in HOME/architecture.md), or an environment fact or
command (HOME/environment.md section). ShipLoop commits the HOME change with the step commit, so the commit message and
the document agree; a learning marked "changes a requirement" with no HOME change is refused with that route; Improve
judges whether a learning should have been recorded. Spec stays the contract (decision: spec.md is edited only through
this route or a send-back to spec, not freely at implement). Carry-forward reconciles the item's write-backs once.

**N4. Test layers using the environment's own tooling (direction 8; M5, M6, M10).** Test-strategy plans test layers per
concern (unit, component, integration, rendered UI, consumer, access), each with an executable command, and uses the
tooling and common practices of the target environment, which the platform card lists (for example a UI framework's
component runner, a headless browser through the Chrome DevTools protocol for a page that can be rendered locally, the
platform's own test runner and reporter, read-only access queries). Test-spec covers every listed ID and every
requirement or criterion, or names the reason. A planned test-only development dependency may be installed under the
run's recorded authority (decision). Per-test outcomes, mutation kills per file type and links to records appear in
report.html, which is written for blocked runs too; a generic TAP reader is added to `shiploop_test_counts.py`. A case
whose UI renders locally declares `needs: ["browser"]` in the E2E harness. Measured: both runs tested UI only by source
greps; every board mutant survived; all 117 command runs had unreadable counts; component tests in Node would have
caught the chess race, the Battleship board races, all six surviving mutants and the unlabeled buttons. Not adopted: a
rendered check through a harness-held org session (decision).

**N5. Four outcomes (direction 6; M1, M2, M9).** `done` (finished; ShipLoop checks it and moves on), `blocked` (only a person
or an outside service can unblock it; the run waits and resumes here with their reply; `awaiting` replaces `blocked_by`),
`send-back` (replaces revise: a record an earlier stage wrote is wrong; that stage reruns with this result as evidence),
`add-work` (replaces replan: product work is missing; new items are built, then the run resumes at system-test-author).
`repeat` is removed (never used in 1,845 results; `next` covers restarting a stage). Each packet prints the allowed
outcomes with one line each: when to use it and what happens next. The send-back budget is checked at `--check-only` and
before Improve; every loop stop rule names its outcome; system-test may send back to system-test-author and release-verify
to release-plan; Improve starts only on `done`. Old runs that use the retired names are refused at load (one supported
version); the run-review export maps old names only when reading historical runs.

**N6. One layout for produced files (direction 5; M7).** Everything ShipLoop and the model write for a run lives under
`RUN`; the product worktree holds only the product and committed knowledge. The Improve child moves to
`RUN/improve/<action>/` (with the Improve skill and the Until Loop contract in the same release); Until Loop state goes
to `RUN/until-loop` (K3); `status.md` and `context-index.md` are dropped (unread in three runs; `next` recovers);
byte-copies of receipts and evidence are dropped; `reference.md` and `quality/code-craft.md` become static guide files;
superseded lint records are pruned; the inbox draft and `results/` both stay (both are read). Measured on Battleship: 667
files and 5.13 MB in 8 locations, 45% of it Improve; a producer packet names a median of 43 files; about 206 files and
1.1 MB go. Recovery keeps every file it needs (`state.md`, the packet, an unaccepted inbox draft, loop receipts,
`until-loop/`, the Improve `packet.json`, the three return files).

**N7. Concise packets (direction 7; M3, M4).** Measured findings from the packet audit are folded in when it lands; until
then the units M1-M2 below and the G and E themes carry the concision work. Each stage's guidance is reviewed for purpose,
method in order, what to read, what done means and how it is checked, as it moves into its template (N1).

## 4. The fix catalogue by theme

Every item: its mechanism, its wave, and the full change, location, test and evidence in `fix-catalogue.json`. Themes A-L
are revision 1's (section 2 of that revision is superseded by this table); M is new.

| Theme | Items (mechanism, wave) |
|---|---|
| A SDLC concerns in the plan | A1 concern map per work item (M10, A) · A2 selected card section by value (M3, A) · A3 activation decided at plan, gated at release-plan (M10, A) · A4 overlapping requests and accessible names in spec (M10, A) · A5 migration before/after and API callers at plan (M10, A) · A6 review focus on concern coverage (M10, A) · A7a identity out of knowledge, with a lint (M2, A) · A7b release-plan drafts the operations record (M7, A) |
| B Step proofs prove behaviour | B1 behavioural Proof for a remote-only target (M5, A) · B2 a check proves behaviour, not the code's text; a criterion's command observes its paths (M5, A) · B3 the Proof printed with its directory (M1, A) · B4 probe the platform behaviour a design rests on (M5, A) · B5 a criterion proven by a later test is unproven at its step (M5, A) |
| C Remote-resident targets | C1 a remote focused command deploys the tree it judges; red_na at test-spec (M5, A) · C2 mutation sentinel; refusal names the send-back route (M2, A) · C3 generated and test path classes declared by the platform card (M6, A) · C4 reuse a passed mutation check-only on an unchanged tree (M2, A) · C5 restore a remote target after the last mutant (M2, A) · C6 platform card corrections (M6, A) |
| D Send-back without redoing | D1 keep accepted steps after a test-commands-only send-back (M2, A) · D3 revisit lines for every revisited step and test (M8, A) · D4 a revisit Improve keeps untouched steps; a merge or split cites evidence (M5, A) · D2 dropped: every implement step keeps its Improve (owner rule 2026-10-10; an empty-diff review cost about 40 s) |
| E Rules in the packet | E1 open items: example row, allowed values, positive gate, "due here" label · E2 plan and step-plan gates in Checked by · E3 templates match their gates · E4 loop gates in words (field name kept: vendored runtime) · E5 "ShipLoop's scripts are not instructions" (after E1, E2, E9) · E6 Improve mechanics in the packet (git log line superseded by N2) · E7 test-spec covers every regression ID; where N/A goes · E8 system-test's check-only is its run; product-acceptance carries open items · E9 test mechanics stated at test-strategy and step-plan (all M1/M2/M9, B) |
| F Improve catches what later stages hit | F1a remote-runtime example · F1b deferred gap that stops the outcome · F1c a behaviour no command exercises · F1d a planned dry run is not a release effect · F1e the procedure walk at carry-forward · F2 authority stated positively (what may deploy, what is a probe) · F3 a pass is classified after its reads · F4 cite Code craft by rule number; a found dead branch is material · F5 replay a person procedure through the product API once, in a rolled-back transaction or on the development target (all B) |
| G References and platform knowledge | G1 link the platform card where tests are decided; prepare checks the focused commands · G2 pointers with heading and line range · G3 quote `## Commands` whole beside the table of contents (bounded; the one exception to D1) · G4 empty-checkout discovery; service, MCP and async duties by cue with a one-line trigger (reverses U6's "not changed") · G5 "Work items: set by plan" · G6 probe now; spec walk trace (all B) |
| H Person-only acceptance | H1 entry line and yes/no checks; report.html checklist · H2 a person-only behaviour is a one-line expected outcome (D6 kept) · H3 never open the target through a session or front-door URL; the card's `sf org open --url-only` advice is removed · H4 the earliest stage that can check an entry prerequisite checks it (all B) |
| I Return and delivery | I1 untracked tool state is not committed by the return (root of both uncommitted deliveries) · I2 an unattended uncommitted return is an open item, not a question · I3 present/absent confirm after earlier deploys; a consumer check observes the entry · I4 each dry run kept (all A) |
| J Duplicate runs | J1 outer test stages reuse verify's passed runs on the same tree, proven by the script (C) |
| K Recovery | K1 Improve recovery state where a compacted model looks · K2 show only this packet's narrative · K3 Until Loop state under RUN · K4 open items quoted once (C) |
| L Harness | L1 keep a done run whose keep checks pass · L2 end the host when the done packet prints (A) |
| M Packet leftovers | M1 drop the remaining low-value head lines · M2 PRINT_LIMIT 16,000 to 20,000 with the status-hook window (C) |

## 5. Conflicts and how they are resolved (all per the recommendations)

CF1 card's front-door URL removed (H3). CF2 keep `required_trivial_reviews`, print the gate in words (E4). CF3 `## Commands`
quoted with a byte cap (G3). CF4 card text measured after A1, first section only (A2). CF5 service duties by cue with a
one-line trigger (G4). CF6 cite rule numbers, delete paraphrases (F4). CF7 the platform card declares its path classes;
`item_scope` loads them (C3). CF8 A3 (test target vs delivery target) lands before B1, F2 and C5. CF9 D1 kept, D2 dropped.
CF10 E5 after E1, E2, E9. CF11 D6 kept. CF12 record alias and user Id; resolve the username at run time. CF13 replay only
in a rolled-back transaction or on the development target (F5). CF14 the script proves tree identity before a reuse (J1).
CF15 one wording: ShipLoop quotes each open item once. CF16 a step probe lives in a committed test-support path inside the
item's paths. CF17 no platform-specific refusal; C2's sentinel catches it generically. CF18 raise the status-hook window
with PRINT_LIMIT. CF19 concern rows replace duty 9; plan item 10's "no ledger" line reworded in the same change.

## 6. Decisions (all accepted as recommended, 2026-10-18)

1. Concern map as data (A1): yes. 2. Behavioural step Proof on a remote target (B1): yes, under the run's authority, after
A3 records whether the test target is the delivery target. 3. Improve may run the recorded test commands under the run's
grant and read-only probes (F2): yes. 4. Keep accepted steps after a test-commands-only send-back (D1): yes. 5. Card text
in packets (A2): yes, first section, measured. 6. A data-migration case later: yes. 7. Test-only development dependencies
installable under recorded authority (N4): yes. 8. Rendered check through a harness-held session: no. 9. D2: dropped. 10.
Four outcomes; send-back across release stages; Improve only on done (N5): yes. 11. Reinstate `learned_from` (N2): yes.
12. Drop `status.md` and `context-index.md` (N6): yes. 13. Move the Improve child under RUN with the Improve skill in one
release (N6): yes. 14. Service duties by cue (G4): yes. 15. Stale temp files: removed (done).

## 7. Waves and order

- **Wave A (correctness and the largest costs; mostly scripts and gates, little prose):** A0 port the Codex implement branch (section 8); obligation continuity; N5 outcomes; N2 step commits,
  look-back and one-step packets; N3 write-back route; I1-I4; C1-C6; D1, D3, D4; B1-B5 after A3; A1-A7; L1-L2; K3. One
  quick tier at the integrator, then a live run.
- **Wave B (templates and text):** N1 framework and the step-plan and implement pilot, then each stage moves into its
  template carrying its E, F, G, H fixes and the N7 concision review; N4 test layers and the platform card tooling list.
- **Wave C:** N6 layout (with the Improve skill release), J1, K1, K2, K4, M1, M2, the remaining template migrations.

## 8. Reconciliation with the implement-step fix plan (Codex, revised 2026-10-18)

Source: `/Users/dadleet/src/skill-craft/docs/shiploop-implement-step-fix-plan-2026-10-17.md` (1,465 lines; untracked in
the canonical checkout, still being revised) and its branch `shiploop/implement-prompt-2d6ecc` (worktree
`.claude/worktrees/impl-prompt-2d6ecc`, based on main 90fa2ca0; our integration branch has 143 commits it lacks). Its
§0.2 already records this branch's step Proof, Step block, state version 7 and procedure walk as existing work and says to
build only the remaining delta; its §10.4 and §10.6 dispose of every gap in our two run reports (91 Battleship, 58 chess
entries) with acceptance tests T1-T51, and its §12 maps each to the code it changes. Both plans share the priority order
(executable step checks, valid procedures, consistent surfaces, measured concision). This section records what this plan
takes from it; where it is safer, it supersedes the item named.

**Code on its branch to port (unit A0, first in wave A).** Commits b3874637 and 4eae0910 implement, on the old base:
static guidance read from `references/implement-guidance.md` (method, eight domain-neutral considerations, evidence, write
back) and `references/code-craft.md` (rules 10-14 and sharper rules 3, 4, 6, 9; owner decisions D8-D10 of that plan),
inserted word for word by `shiploop_static.static_text`; a Step block with anchors, cards, the match contract and the last
two commits; step-plan `cards`/`cards_na` and `match`; implement result fields `considerations` and `criterion_evidence`
with an `implement-record` gate; both gates covering every step of an ask-agent plan; and a 104-row static-obligation test.
A0 ports these onto this branch on top of W2-A/B (this branch's step Proof and step block stay; no mechanism twice), as the
foundation of N1 (the loader becomes the template engine) and N2 (its last-two-commits line becomes the commit look-back).
Its docs and evidence (`shiploop-implement-prompt-audit-journal.md`, `shiploop-implement-prompt-audit-evidence/`) merge
with it. Fields added here go to the next state version (8), once.

| Its point | Effect on this plan |
|---|---|
| Obligation continuity: system-test-author called the board interaction required; release-verify accepted without it and passed it to handoff with no waiver (§0.2, T44) | **New, adopted (wave A):** an obligation's required/advisory status travels through every stage, including a no-reply; no later stage downgrades it without an owner waiver. Joins H1/H2 and D6. |
| Mutation: a generic engine must not blindly deploy a build-breaking mutant to a shared target; remote mutation needs an isolated route, a restore baseline and permission; the runner restores in `finally` with an `in_progress` record; a failed restore blocks with "target may still hold a mutant" (§4.3, T37-T39) | **Supersedes C2 and C5:** the sentinel runs only on an isolated route or as an adapter-specific observation test; restore is runner-owned and gated; reuse (C4) keeps restore as a separate gate. |
| Revisit reuse by exact normalized records per step, unchanged product content, the longest unchanged prefix and freshly script-run Proofs; a pilot (§4.4, T40) | **Supersedes D1's looser "no change to steps":** adopt this rule. |
| No new `generated` classifier class; use the project's ignore rules and correct test classification; product configuration is never disposable (§4.5) | **Supersedes C3's `generated` class:** the platform card says which tool-state paths go to `.gitignore`; Apex test classes are classified as tests. |
| Applicability from accepted project facts, not request keywords; missing facts trigger discovery; an empty repository still discovers its target and external services (§4.6, T50) | **Supersedes G4's "by cue":** discovery duties narrow from accepted facts (stack, surface, capabilities). |
| File-open telemetry, minimum review time and a blanket ban on reading ShipLoop's source are not gates; source reads diagnose missing prompt information (§4.5, §10.4) | **Drops E5 and F3's telemetry;** keep "a classification follows the actual inspection" as text and count source reads as a diagnostic in each run report. |
| Session and front-door entry: enforce the recorded access route and host capability policy rather than a generic ban (§10.6) | **Refines H3:** a session or front-door URL is used only when the run's recorded authority names it as the route; never to bypass a person-only or denied route. The card's `sf org open --url-only` advice is removed or rewritten to that rule. |
| Correct the platform card against captured parser output before linking it to more stages (§10.5, T37/T43) | **Orders C6 before G1.** |
| Release checks observe the actual current target state; do not manufacture an absence (§4.5) | **Refines I3.** |
| End the host only on run-bound terminal evidence plus host completion, not text containing "done" (§4.5, T48) | **Refines L2.** |
| Repeated unchanged deploy/test runs in system stages: a pilot that counts executions first and reuses only proven-equivalent evidence (§4.6, T51) | **Refines J1 into a pilot.** |
| Remote behavioural step Proofs: a prepared isolated route; a source/compile criterion may finish early while a runtime criterion stays open, never weakened silently (§10.5) | **Refines B1/B5.** |
| §12 traceability: every item mapped to reference code, delta and acceptance check | **Adopted as the catalogue's form:** each item in `fix-catalogue.json` gains its acceptance test id (this plan's route tests or its T-numbers). |

Not changed by it: knowledge as a table of contents (its §0.2 accepts our D1, with command and authority facts kept by
value, which is G3); full Code craft (D3); D6 (narrower second ask; it adds "honor a declined check without re-asking or
inventing a pass", compatible).

## 9. Verification

1. Offline per unit: render diff, head tables, footprint suites, route tests for every changed gate; one quick tier per wave.
2. Live after wave A: `battleship-salesforce` again (remote target: behavioural step proofs, mutation sentinel, send-back
   without redo, committed return with step commits and write-backs, app kept) and `seat-reservations` (state, concurrency,
   API callers) to exercise the concern map; measure source reads, refusals, minutes per stage, implement and Improve per
   step, commits per step and their look-back, HOME write-backs, files produced.
3. After wave B: a case with a locally renderable UI (`battleship` or `checkers`, Node) with `needs: ["browser"]` to
   exercise component and headless-browser tests and visible per-test output.
4. Later: a case with stored data and a schema change, for the migration and switchover rows.
