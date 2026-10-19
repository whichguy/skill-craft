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
so no text is rewritten twice. Template audit (`packets-audit.json`, `templates/`): recommended **yes**. Each stage
gets one template with declared slots and its result form; shared frame and rules text live in small partial files
(decision T-D3). The prototype renders step-plan at 19,643 characters and implement S1 at 18,794 while carrying, by
value, the item context, concern rows, commands, R-n and AD-n that today's printed outputs dropped. With today's data
both exceed a 19,500 budget (worst 21,204 and 20,660); with size limits enforced by the stage that writes each field
(context 2,500, concern rows 1,200, step task 700, criteria 1,200, Proof 600; decision T-D2) implement fits at 18,760 and
step-plan misses by 84 characters, closed by the N7 trims. Migration: a byte-identical pilot of step-plan and implement
first, then one stage per change; the obligations ledger only repoints its anchors (its source check already reads
`.md`). The platform card needs a testing heading before a slot can select its testing rules (with C6).

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

**N7. Concise packets (direction 7; M3, M4).** Measured on the 33 Battleship producer packets (563,438 printed
characters): the fixed frame is 39% and the stage's own guidance 27%; 5,790 characters are identical in all 33; each rule
is stated 2-5 times per packet (step-plan states each structural rule three times); 25% of the planning guidance did not
apply to this request; 10 of 33 outputs passed the 20,000-character host cut and lost their middle (7 of 8 implement
packets lost guidance items 5-7 and Code craft rules 1-2); 23 of 28 packets printed none of the values quoted from
earlier results, and 15 of 33 printed no symbol definitions. The ten worst planning duty items are rewritten in the audit
from 12,849 to 6,874 characters (-46%) while adding units B1, B2, C1, A1, A4, G4, G6 and H4; unused constants and 4,247
characters of stage-row fields no packet prints are removed. Each stage's guidance is reviewed for purpose, method in
order, what to read, what done means and how it is checked, as it moves into its template (N1).

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
| M Packet leftovers | M1 drop the remaining low-value head lines (C) · M2 dropped (section 8.1: the budget is not raised) |

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
release (N6): yes. 14. Service duties by cue (G4): yes. 15. Stale temp files: removed (done). 16. Templates use shared partial files (T-D3): yes. 17. Producing stages enforce field size
limits (T-D2): yes. 18. Code craft in the implement head (T-D1): one clause per rule in the printed head, the full
rubric in the packet file and in the step's Improve review, where it is applied.

19. **Folder symbols (owner, 2026-10-18, "pick one").** Packet prose keeps bare symbols, and HOME becomes KNOWLEDGE:
    RUN, WORKTREE, KNOWLEDGE (= WORKTREE/docs/shiploop) and GUIDES. They are defined on the frame's Symbols line ("shorthand
    for reading; commands and file tools take the absolute path"), and every command and file-tool path stays absolute.

    Evidence (`template-review/partials.json` `symbols`): 0 of 2,169 live tool calls used a literal symbol path, and
    neither run folder has a stray symbol directory. `expand_result_roots` already reads bare roots in `evidence_refs`.

    Options considered:
    - `<HOME/>` reads as a fill-in placeholder, and in a shell it is two redirections that can truncate a file.
    - `$NAME` is unset in each fresh shell, so `$WORKTREE/*` becomes `/*`.
    - An `@` sigil collides with annotations and decorators (`@AuraEnabled`) for no measured gain; it was proposed first
      and withdrawn on this evidence.

    HOME is renamed because it is the one symbol with a competing system meaning (`$HOME`; on a case-insensitive volume a
    stray `HOME/` aliases the harness's `home/`). The rename rides on the N1 migration, which rewrites that text anyway. This changes D3 of the packet-review
plan ("implement keeps the full text, for now") because the full text breaks the head budget and was cut by the host
in 7 of 8 implement packets anyway; the owner can reverse it.

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

### 8.1 Codex re-anchoring on main (2026-10-18, its D15-D16)

The Codex plan now anchors every code assertion on main `17ddec36` and treats this integration branch as historical
evidence and a porting reference (its §0.2, §0.4, §7 step 1). Its §0.4 lists what main lacks that this branch has: state
v7, the step `check` and shared Step block, the script-run step Proof, the Improve import re-proof, check-only reuse, the
procedure walk, notes-as-file and the settling template. Building both plans on different bases would implement the
same mechanisms twice and then collide.

**Decision B (recommended): one base.** Land this integration branch on main first (its last quick tier is green and
the Battleship run exercised it), then refresh the Codex plan's code map (`reference-code-map-2026-10-18.json`) against
the new main, so both plans describe the same code; A0 then ports only what main still lacks. The alternative, rebuilding
this branch's 143 commits on main from the Codex map, repeats tested work. Landing on main is a push and release, which
need the owner's go.

| Its new point | Effect on this plan |
|---|---|
| D15 and §3.4-3.4.1: one directive in Work (the step id, its C-, R-, AD- identity, exclusions and the Method locator), the completion conditions once in Exit; Until Loop produces, Improve reviews, ShipLoop accepts; no third loop; human-facing phrase "Execute this step's directive until every assigned criterion is demonstrated by current evidence at its required boundary"; evidence chain criterion → observation → receipt → artifact | **Adopted into N1's implement template and the loop block.** Removing the producer loop or merging it into Improve stays deferred, as it says. |
| The Repeat paragraph change (D7: continue while a justified investigation remains, stop on the same underlying failure after seven genuine attempts) is a separate policy change, qualified on its own (its T12/T52) | **Added to wave B as a pilot** with its own tests; not bundled with the Work/Exit move. |
| Main's Improve exit (two qualifying trivial passes, or a first full trivial pass with a runtime-measured unchanged tree) differs from this branch's gate-two/gate-three adaptation | **Owner decision S-10 (still open from the efficiency plan) decides it;** until then this branch keeps its gates and the Codex plan keeps main's. Landing on main (decision B) makes it one decision. |
| Do not raise the rendering budget; keep the 16,000-character head target measured and the owner's content decisions | **Drops M2 (PRINT_LIMIT to 20,000).** Templates fit through the producing stages' field limits (T-D2) and the N7 trims; the 16,000 target stays a measured target, the 20,000 host cut and the 19,500 required-text bound stay the tests. |
| §12 code map: every recommendation bound to source, line span, hash and T-tests | **Adopted as the anchor form** for this plan's catalogue once refreshed against the common base. |

### 8.2 After landing on main (2026-10-18, decision B executed)

The owner approved decision B: this branch is merged with origin/main (fe02651e), reconciled, released and pushed, so
main is the one base for this plan and the Codex plan. Consequences:
- **S-10 is resolved:** Improve keeps main's upstream stop rule (a review ends when the first pass completes with no change,
  or after two consecutive trivial passes), with the Until Loop runtime vendored byte-identical (0.10.0). This branch's
  stop rule by stage kind and its one-unchanged-pass rule are withdrawn (29407b46; journals mark them superseded).
- **Lean runtime returns are withdrawn locally** (U21): an Improve child's `start` and `done` print the full packet again
  (about 11.5K and 22.7K characters against about 2.7K). New follow-up **U-up**: propose lean returns upstream in the Until
  Loop repository, then re-vendor; an upstream change needs the owner's go.
- **Wave A starts with A-1, re-anchor:** refresh the Codex code map (`reference-code-map-2026-10-18.json`) and this
  plan's catalogue against the new main, marking which items main now holds (step Proof, Step block, state v7, procedure
  walk, check-only reuse, the packet-review units) so A0 ports only what is still missing.
- E4 still applies: print the trivial-review gate in words, now for main's rule.

### 8.3 Template review (2026-10-18, owner request: sufficient, necessary, nothing confusing or harmful)

**Method.** Three Opus reviewers, read-only, against main's gate code, the vendored Until Loop 0.10.0 and the Battleship
run's packets and actions. Each mapped every refusal the stage's gates can raise to template text, and classified each
block and finding. Evidence: `docs/experiments/run-insights-2026-10-18/template-review/`.
- step-plan: 37 gate rows, 28 findings (2 P0, 7 P1).
- implement: 39 gate rows, 25 findings (2 P0, 4 P1).
- partials: 38 gate rows, 30 findings (0 P0, 4 P1).

The session rechecked the P0s and the main P1s in code: `_RESULT_KEYS`, the `check_only` skip of `check_terminal`, the
state key `revisions`, the S4 Proof length, `printed_text`'s `HEAD_END`, and the runtime's refusal of a start over a live
receipt.

**Verdict.** Both stage templates are partly sufficient and partly necessary. They are not shippable as drafted, but the
design holds. What they fix against the live run:
- the work item context printed whole (3.3K, against a 400-character excerpt);
- the symbols defined in every print;
- implement fits under the host cut (18.8K, against 21.6K live, where the middle was lost);
- the Proof printed with its directory;
- a revisit points at the step's own result.

The hooks keep working: the callback is still the third line, and the keepalive and status-hook window are intact.

**Root causes and the conditions for landing a template (amends N1):**
1. **Text that must come from code the gates read is hand-written.**
   - The Until Loop argument (Work, Exit, Repeat) differs from `loops.contract()` in both templates, and step-plan has 6
     exit lines against stage_spec's 7. Nothing is refused, but the runtime judges against text the packet never shows.
   - Outcomes, placeholders and field shapes are hand-written as well.
   - The fix: these become generated slots (the loop argument from `loops.contract`, outcomes from stage_spec, placeholders
     and shapes from the registry the gates use). Rewritten exit conditions go into stage_spec, never into a template.
2. **Templates name features main does not have yet.**
   - Today's gate refuses `concerns` (A1) and `criterion_evidence` as unsupported fields.
   - No platform card has a `## Testing` section.
   - Producer bounds (T-D2) are not enforced: Battleship's S4 Proof is 1,036 characters against implement's 1,000
     refuse bound, so the packet would not render.
   - N2 fields and the N5 names are missing; "revise" is written 7 times in implement.
   - The fix: a template lands only after the gate keys, bounds and outcome names it prints. A slot whose feature is
     absent sits behind a flag.
3. **"This packet states every rule its gates apply" is false.**
   - step-plan misses every criterion named by a test command, deps-earlier, and `test_commands_na` being refused while
     criteria exist.
   - implement misses the lint auto-fix refusal, the 0-tests rule, `assumptions` being refused at implement, and the
     `not_covered` row shape.
   - The new `<...>` placeholders pass the exact-match placeholder gate.
   - The fix: the reviewers' gate maps become a route test. Each gate refusal must map to template text, every
     placeholder in a form is registered in the gate, and an unfilled form is refused through the real `complete`.
4. **Inputs that direct the work were pooled or excerpted.**
   - Open assumptions the step-plan gate checks print as a pointer.
   - The revisit flag reads `state.revises` (the key is `revisions`) and drops "submit the whole amended plan".
   - implement's Anchors claim "complete" while R-n text is cut to two sentences.
   - The fix: a slot the gate checks, or that directs a revisit, is never pooled. An excerpt says it is one.
5. **The shared partials have drifted from runtime 0.10.0 and from the code.**
   - A second start over a live receipt is refused, not reset.
   - The fresh branch lost the active-receipt guard.
   - loop-result offers only `next_argv`, while refusals name the start command.
   - The frame's "whole when it ends with === end ShipLoop head ===" is false: `printed_text` appends the line to cut
     prints too. It should become a cut detector.
   - code-craft-titles points at `GUIDES/code-craft.md`, which does not exist, and drops the redaction, secrets,
     catalog-first and composition-guard clauses.
6. **Budget.** step-plan prints 19,643 against 19,500, with a worst case of 21,204 against the 20,000 host cut. The N7
   trims come first: Method items 4-8 restate exit conditions 2-6, and several lines are stated two or three times.
7. **Wording that is wrong or not generic.**
   - "test-spec records `red_na`": only the test stage does.
   - "a glob never matches across /": the gates use fnmatch, which does.
   - A `## Procedures` locator only Battleship had.
   - The Gates lines announce the Improve review (against the owner's rule).
   - The rules partial's "record it as an assumption" invites a field implement refuses.

### 8.4 Template revision 2 (owner: "plan and improve", 2026-10-18)

This revision applies section 8.3 to the drafts (`docs/experiments/run-insights-2026-10-18/templates/`, version 2) and to
the prototype renderer (`packets-tools/tmpl.py`, `prep_values.py`). It re-renders the Battleship examples, then reruns
the three reviewers until no P0 or P1 finding remains (at most three rounds).

**What the code owns becomes a slot.**
- `{{loop_argument}}` is rendered from the loop contract (Work, Exit, Repeat, Contract and Receipt), exactly as
  `loops.invoke_lines` prints it. The examples render it from the run's own contract files.
- A better exit wording is a proposed stage_spec change (listed below), never template text.
- `{{outcomes}}` is the stage's outcomes (stage_spec, N5 names), each rendered from `partials/outcome-<name>.md`.

**New front matter.**
- `requires:` lists the features a template prints that are not on main yet. The engine's loader refuses a template
  until each one is registered: A1 concern map, T-D2 producer bounds, N2 step commits and fields, N5 outcomes, the
  criterion-evidence gate, and the card `## Testing` section. There are no feature flags and no dual path.
- `gates:` maps each refusal the stage's gates can raise to the anchor text that states it. The renderer refuses a print
  that lacks an anchor; in the engine this becomes the route test of section 8.3.
- Every `<...>` placeholder in the result form is listed by the validator. The gate's exact-match registry reads that
  list, so a form placeholder is always refused.

**Slots that direct the work are never pooled.**
- Open assumptions and the revisit block become refuse-class slots, bounded where they are produced.
- The revisit flag reads `revisions`, and the revisit block names the previous result and asks for the whole amended
  plan.
- A refuse-class include names the producer gate that bounds it.

**Partials.**
- frame:
  - KNOWLEDGE symbol (decision 19), with the paths before the Symbols line printed absolute;
  - the pause command printed in the head;
  - no wholeness claim; "--check-only names any rule this packet leaves out".
- loop-invoke and loop-result: Until Loop 0.10.0 behaviour (a second start over a live receipt is refused) and the
  refusal routes (run the command the refusal names).
- result-rules: split into fill rules plus `outcome-done`, `outcome-blocked` (both `awaiting` kinds), `outcome-send-back`
  and `outcome-add-work`.
- rules: no "record it as an assumption", and blocked worded as N5 words it.
- code-craft-titles: restores the dropped clauses and points at the full rubric in the packet file's appendix.
- appendix: no duplicate recovery command and no context-index; the WORKTREE line only on a worktree run.

**step-plan.**
- States the gate rules it missed: every criterion named by a test command, `test_commands_na` only without criteria,
  deps earlier, unique paths, check rows without ids, expectation steps that exist.
- Method gives formats only, not a second copy of the exit conditions.
- Wording fixes: red_na belongs to the test stage; a glob's `*` crosses `/`; no Improve mention.
- `{{recent_commits}}` (N2): the last two commit messages ShipLoop did not write itself, read from the item's starting
  HEAD.

**implement.**
- `{{recent_commits}}` and accepted steps with their short commit (N2).
- `learned`, `decisions` and optional `learned_from` in the form (N2), and "ShipLoop commits this step; commit nothing
  yourself".
- Anchors labelled as excerpts, the item's other R-n IDs listed, case rows from test-spec fields (no `## Procedures`
  locator).
- Gates state the lint auto-fix refusal, the Proof's 0-tests and timeout rules, scope, lint_waivers and not_covered
  shapes, and the send-back budget at 0. The Improve-import bullet goes.

**Proposed stage_spec done_when changes (they reach the packet through the contract).**
- step-plan gains A1's concern-mapping condition when A1 lands (fix catalogue A1).
- implement's fourth condition names the evidence form once its gate lands.

### 8.5 Rounds 2 and 3 (2026-10-18)

**Round 2.** The same three reviewers re-checked version 2 (evidence: `template-review/*-r2.json`).
- Round-1 findings: step-plan 10 of 28 fixed and 6 partly; implement 11 of 25 fixed and 9 partly; partials 17 of 30 fixed
  and 7 partly.
- New findings: three P0s, each the same kind of route problem:
  - a revisit block refused over its limit, which nothing upstream bounds (step-plan and implement);
  - loop-result offering send-back where step-plan refuses it (partials).
- Also flagged:
  - `requires` gaps (decision-19 rename, placeholder registry, Method-item count, N5 awaiting kinds, A0, N3, D3);
  - a commit look-back wording that would skip step commits;
  - `HOME/` still printed in generated locators;
  - three different routes for absent access.

**Round 3 (version 2, this commit).**
- The revisit blocks become excerpt-class (the send-back summary cut at 600, with its locator, as `REVISIT_SUMMARY` does
  today).
- The loop stop outcomes become a stage_spec slot (`stop_outcomes`).
- The look-back is "not ShipLoop bookkeeping", so step and review commits count.
- The generated locators say KNOWLEDGE/.
- The fill rules state what the gates actually refuse.
- `awaiting` gains a service kind.
- implement:
  - adopts A0's eight considerations, one line each in the head with the full text in the file appendix (as decision 18
    does for Code craft);
  - adopts fix plan 3.3's seven-field `criterion_evidence`;
  - prints later steps with their criteria and the full anchor ID list.
- `requires` lists every dependency, with a lands-with note.
- The renderer refuses an over-budget print.

**Engine changes the templates assume.** These are text the code owns; they go through stage_spec or loops, never through
a template.
- **E1:** loops Work cites "Method items", and `_duty_items` counts the template's Method.
- **E2:** the N5 rename in the loops Repeat texts (revise becomes send-back).
- **E3:** `REPEAT_STEP` routes a person's or a service's action (access, authority, a decision) to blocked, and an
  unachievable step to send-back.
- **E4:** `check_loop_packet` tests the receipt status before the contract comparison. Today an active receipt from
  another contract yields a refusal that names a start command the runtime refuses.
- One conflict noted for A0: its guidance's "never edit spec.md here" yields to N3's write-back at implement (owner
  direction 3).

**Budget rule (static validator).**
- A refuse-class slot counts at its bound.
- Every other slot counts as one pointer line. The renderer shrinks those to pointers, last in body order first, before
  a print would pass its budget.
- The progress block's bound drops to 900.

| | step-plan | implement |
|---|---|---|
| Realistic print at the T-D2 limits, argument printed | 20,324 | 20,953 |
| Realistic print at the T-D2 limits, argument as a pointer | 18,496 | 18,866 |
| Static worst case, argument printed | 21,768 | 22,249 |
| Static worst case, argument as a pointer | 19,198 | 19,479 |

**Decision pending (the owner).** The packet would replace the Until Loop ARGUMENT block with a one-line pointer.
- The runtime prints Work, Exit and Repeat verbatim in every start, next and done packet (verified by running 0.10.0 on
  both Battleship contracts).
- The 2026-10-16 rule ("say RUN with the explicit argument and command") was made when the model had to type the
  argument into a Skill-tool call. That route is gone (ee3a1175).
- Guards, if adopted:
  - a test pins the runtime's echo;
  - the test stage keeps its own command list;
  - upstream lean returns (U-up) must keep Work and Repeat.

## 9. Verification

1. Offline per unit: render diff, head tables, footprint suites, route tests for every changed gate; one quick tier per wave.
2. Live after wave A: `battleship-salesforce` again (remote target: behavioural step proofs, mutation sentinel, send-back
   without redo, committed return with step commits and write-backs, app kept) and `seat-reservations` (state, concurrency,
   API callers) to exercise the concern map; measure source reads, refusals, minutes per stage, implement and Improve per
   step, commits per step and their look-back, HOME write-backs, files produced.
3. After wave B: a case with a locally renderable UI (`battleship` or `checkers`, Node) with `needs: ["browser"]` to
   exercise component and headless-browser tests and visible per-test output.
4. Later: a case with stored data and a schema change, for the migration and switchover rows.
