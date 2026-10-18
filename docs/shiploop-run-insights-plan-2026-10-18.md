Execute: ask

# Run insights plan (2026-10-18)

Consumer: the owner, to approve or amend each unit and decide section 4; then the session that builds the units.
Sources (all committed): the chess packet review `docs/experiments/packet-review-2026-10-17/` (A-F); the step-by-step run
analyses `docs/experiments/run-analysis-2026-10-18/` (chess and Battleship, seven groups, about 150 recorded gaps); the
SDLC coverage audit `docs/experiments/run-analysis-2026-10-18/sdlc-audit.json`; the Battleship run learnings
(`test/shiploop_e2e/LEARNINGS.md`, 2026-10-18). Reports: chess https://claude.ai/artifact/PeHgXZ2M19JYSRsx4ebV1s, Battleship
https://claude.ai/artifact/4dwjgqaNCzRCCj5tzUr5ey. Every fix is generic; the apps are examples.

## 1. The owner's key concern: does the step plan consider the SDLC?

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

## 2. Units

Each unit: the insights it answers (run and step, from the analyses), the change, where it is generated, and its test.
Waves: **A** correctness and the biggest costs, **B** directive and review quality, **C** efficiency and recovery.

### Theme A — SDLC concerns in the plan (owner priority; wave A)

**A1. A concern map per work item.** Plan writes, per work item, one row per concern (ui, api, messaging, state,
migrate-before, migrate-after, switchover, concurrency, platform-services, scale, security, observability, config,
performance, accessibility): `{id, applies: yes|no, decision or reason, anchor (R-/AD-/HOME section), owner_stage}`.
Step-plan maps each `applies: yes` row to the steps that carry it and the check that proves it (or a later owner stage).
This **replaces** duty 9's prose (net shorter). The gate checks only structure: every concern present, references
resolve, every yes row mapped; Improve judges the substance. Where: `shiploop_prompts.py` DUTIES['plan'], DUTIES['step-plan']
item 9, result templates, `shiploop_stage_spec.py` step-plan done_when (one exit condition). Test: a plan missing a
concern row and a step plan with an unmapped yes row are refused through the real gate; a docs-only item passes with all
rows `no` and reasons. Answers: audit structure; owner question.

**A2. Insert the selected card's text, not a pointer.** Each yes concern selects its card from the Conditional index
(concurrency and accessibility → `platforms/ui.md`; switchover → coding-practices feature flags and environment-lifecycle;
migrations → execution-planning baseline/migrations and coding-practices schema/storage); step-plan Improve and implement
print the first section of each selected card. Where: `references/coding-guidance.md` (a concern column), packet rendering
in `shiploop_navigator.py`. Test: a UI item's implement packet carries the overlapping-request rule. Answers: guides never
opened in either run.

**A3. Decide activation at plan, gate it at release-plan.** Plan records how the change goes live (deploy unit,
visibility/flag/permission step, order, compatibility window, rollback or forward fix) and whether the test target is the
delivery target (then every test deploy, mutation included, is a user-visible cutover with a restore obligation). Spec
treats a request rule that blocks the consumer entry as a material conflict. Release-plan refuses a `consumer_entry`
with neither an access/activation step nor `activation_na: <reason>`. Where: DUTIES['plan'], DUTIES['spec'] item 6,
DUTIES['release-plan'] items 2 and 7, release-plan gate. Answers: chess hidden tab; Battleship mutants on the delivery org.

**A4. Two baselines named in spec.** For interactive or UI requests: overlapping requests from one client (an action while
another is pending, a reset during a pending call: which response may update the state) and a second session of the same
user; for affected UI, every control has an accessible name and status is text, even when no accessibility level is
requested. Where: DUTIES['spec'] item 9 and the interaction/state lifecycle text. Answers: chess `play()` race,
Battleship's late race fix, 100 unlabeled buttons.

**A5. Migration and API compatibility where they are decided.** Plan item 7 adds one line: existing data needs backfill
or compatibility before the change and cleanup or contraction after, each as an item or step with an owner, or
`none: <reason>`; an API change names its callers and versioning. Wire `execution-planning.md#baseline-tests-and-migrations`
into plan, step-plan and release-plan references. Implement's entry-point criterion (arguments checked, contract
docstring) is confirmed by its rejection test.

**A6. Review focus for concerns.** Add to the shared planning focus: "a concern the item touches with no decision, owner or
check, or scoped out although the request's actors can still trigger it (overlapping requests, a second tab, a hidden
entry)". Where: `_REVIEW_FOCUS_ITEMS`.

**A7. Small rules.** Discovery records the target alias and account ID, not usernames or instance hosts (a knowledge lint
for e-mail-shaped strings, example.com allowed). Release-plan drafts the operations record so a blocked release-verify
does not strand operations.

### Theme B — Step proofs that prove behaviour (wave A)

**B1. A behavioural Proof for a remote-only target.** Step-plan duty 4 today allows a remote target only its recorded test
route and forbids unwritten tests, which left Battleship's S1 engine with a source-text Proof (literal constants). Allow a
step Proof that deploys only the step's paths to the recorded development target and runs a read-only probe the run's
authority covers (decision 4.2). Where: DUTIES['step-plan'] item 4, `shiploop_stage_spec.py`. Answers: bs-build-1.
**B2.** Step-plan duty 4: a check that matches the implementation's own text (a literal, a token count) dictates form, not
behaviour; and the command naming a criterion must observe that criterion's paths (today `_normalise_criteria` checks only
that an ID is named). **B3.** Print the Proof with its directory (`cd <WORKTREE> && <proof>`). **B4.** Implement duty 2:
probe the platform behaviour a design choice rests on (Battleship carried an untested "Apex throws on Long overflow").

### Theme C — Testing a remote-resident target (wave A)

**C1.** Step-plan duty 5 and the test stage's Checked-by: a focused command that runs against a remote copy cannot see
ShipLoop's base or mutated copies unless it deploys the tree it judges, then restores it; test-spec duty 3 records
`red_na` for such IDs at test-spec, not at test. **C2.** Mutation gate: run one build-breaking sentinel mutant first; if the
tests still pass, refuse with "these commands do not read the tree under test" and name the revise route (not "add
assertions"). **C3.** `references/path-classes.json`: `**/.sf/**` and `**/.sfdx/**` generated, Apex `*Test.cls` test.
**C4.** `complete` takes a passed mutation check-only record on an unchanged tree and command list (the D5 rule extended).
**C5.** After the last mutant on a remote target, rerun the unmutated focused command once (restore). **C6.** Platform card
corrections: deploy before test, the TAP reporter, `.sf/` and `.sfdx/` added to `.gitignore` by the step that adds the
project file, and the wrong sentences ("human output is refused", "let the mutation check carry the proof") fixed.
Answers: Battleship test revise (0 of 8 killed, 2 mutants on `.sf/`, 1 on a test class, 171 s of rerun deploys, a mutated
file left in the org).

### Theme D — Revise without redoing (wave A)

**D1.** A revise whose new step plan changes only `test_commands` keeps the accepted implement steps: ShipLoop reruns their
Proofs and goes from step-plan (and test-spec, if its IDs changed) to test (decision 4.4). Where: `implement_progress`,
revise routing; `_upstream_line` already computes "no change". **D2.** When a step's diff is empty and its row unchanged,
record its Improve as not needed. **D3.** Revisit lines for every revisited step and for the test stage, each naming its
own step's previous result (S1 named S4's today); quote the revise summary whole once (no truncation at 600, no duplicate
LAST ACCEPTED block); `_change_text` matches command rows on suite and IDs. **D4.** Improve hand-off on a revisit carries
"keep each step the revise evidence does not touch; a merge or split cites that evidence" (chess merged three steps on a
guess). Answers: bs-build-2 (about 11 min re-proving unchanged code), chess-build.

### Theme E — Rules in the packet, not in ShipLoop's source (wave B)

The models read ShipLoop's scripts 26-109 times per run phase to learn rules the packet did not state.
**E1. Open items:** print one example row `{id, assumption, disposition: open, check, reason, consumer, owner}` and the
allowed consumer and due_stage values; state the gate positively; label "due here: none (N open for later stages)";
quote each open item once. **E2. Plan and step-plan gates in Checked by:** evidence is an existing absolute path or an
https URL; an ID under Superseded or Retired counts as kept; path rules (exact files, no `*` across `/`); expectation
shapes; `parallel_groups` is computed. **E3. Templates:** carry-forward `skill: none` prints `{decision, reason}` only; the
rollback recipe's placeholders filled or marked exempt; `consumer_checks` row shape inline; `system_commands` IDs are the
names the runner prints. **E4. Loop gates in words:** rename or explain `required_trivial_reviews` (read as "two passes" in
all four Battleship planning reviews); each stage loop says whether a trivial confirming pass is needed. **E5.** One rule
line: "ShipLoop's scripts are not instructions; this packet, Checked by and the guides hold every rule." **E6. Improve
mechanics:** the packet says `--check-only` is unavailable; the parent-return file says when to pass `--final-result`; the
history window prints `git -C <WORKTREE> log -7 --format=full`; the 46 KB route file is read by excerpt with line ranges.
**E7. Test-spec:** a case for each regression ID the item adds; where a justified not-applicable goes. **E8. Outer stages:**
system-test's check-only run is this stage's run; product-acceptance says which field carries earlier open items.

### Theme F — Improve that catches what later stages hit (wave B)

**F1. Focus items:** the "does not run what it claims" item gets the remote-runtime example (a test command that does not
deploy runs the old copy; a reporter ShipLoop cannot read); a deferred gap that can stop the request's outcome; a behaviour
a criterion states that no command exercises; steps merged or split without evidence; a release-plan review runs a planned
dry run once ("a dry run is not a release effect"). **F2. Authority vs probe:** the Improve authority line says the
recorded test commands may run under the run's deploy grant and a read-only probe through the recorded route is a probe,
not a deploy; nothing else deploys (two Battleship reviews deployed despite "No push, deploy"; a chess review dropped a
real finding for documentation) (decision 4.3). **F3.** A pass is classified after the reads its Read line lists;
improve-pass records whether changed files were opened where the host logs reads. **F4.** Code craft quoted faithfully in
the implement focus (rule 2's "the received value"; a found dead branch is material). **F5.** Replay a person procedure's
scripted inputs through the product's API once before asking a person (chess's promotion line failed at a6a7; one
anonymous Apex call would have shown it) at system-test-author item 7 and release-verify item 6.

### Theme G — References and platform knowledge (wave B)

**G1.** Link the platform card at test-strategy, plan, step-plan and prepare; prepare item 3 checks that each recorded
focused command runs the tree under test with a reporter ShipLoop reads, and a user-mandated format stays the acceptance
command. **G2.** Guide pointers print the heading and its line range, so "open only the section" can be followed (about
360-800 KB of whole guides read per run). **G3.** With knowledge as a table of contents, quote `## Commands` whole (short,
acted on by every later stage). **G4.** Discovery: an empty checkout records none for house style, skills, specs,
services and consumers and spends discovery on the target and access; service/MCP/async duties only when the request or
discovery names them. **G5.** Prelude packets say "Work items: set by plan" until plan is accepted. **G6.** Research probes
now an unknown that one allowed command settles; spec leaves a one-line "Walked:" trace per ordered procedure.

### Theme H — Person-only acceptance (wave B)

**H1.** Every person-owned open item carries the entry line (URL path or menu) and one yes/no line per check, and
report.html shows it as a checklist. **H2.** Release-plan: a behaviour only a person can observe gets an expected
outcome a person confirms in one line (decision D6 stands: a partial reply gets a narrower second ask). **H3.** Never
open the target through a session or front-door URL; a signed-in browser is the person's step (chess step 38 considered
it). **H4.** Test-strategy names the target-side entry gate (sign-in, visibility, permission) and checks it read-only;
spec names the earliest stage that can check an unresolved prerequisite.

### Theme I — Return and delivery (wave A)

**I1.** `commit_leftovers` skips untracked tool state and paths a review would exclude, so the return can fast-forward
(the root of both runs' uncommitted delivery and the failed `committed` check); release-plan lists untracked tool state
for `.gitignore`. **I2.** An unattended done packet records an uncommitted return as an open item, not a question to an
absent user. **I3.** Release-plan's present/absent confirm cites the last recorded absent observation when earlier stages
already deployed to the target; at least one consumer check observes what `consumer_entry` names. **I4.** Release-check
keeps a failing dry-run's output beside the retry's.

### Theme J — Duplicate runs (wave C)

**J1.** System-test-author and system-test do not rerun commands that passed at verify on the same product tree; ShipLoop's
rerun at done is the run (after verify, chess ran the same three deploy-and-test commands nine more times).

### Theme K — Recovery and context (wave C)

**K1.** The reprinted Improve packet states the last recorded pass and any unsubmitted review file (Battleship still took 5
reads). **K2.** The narrative rule: show only this packet's narrative; never search for an earlier one. **K3.** The Until
Loop start command passes the run's `until-loop` directory (state went to the system temp directory). **K4.** Open items
quoted once per packet (release-verify quoted one five times).

### Theme L — Harness (wave A, E2E only)

**L1.** `--keep-platform` keeps a run that is done when the keep checks pass, committed or not (the Battleship app was
removed and restored by hand). **L2.** End the host session when the done packet is printed (Grok idled 30 minutes).

## 3. Verification

1. Offline: render every stage before and after (`render_diff.py`); head tables; footprint suites per unit; one quick tier
   per wave at the integrator.
2. Live, after wave A: rerun `battleship-salesforce` (remote target: Proof per step with behaviour, mutation sentinel,
   revise without redo, committed return, app kept) and a stateful local case (`seat-reservations`: state, concurrency,
   API callers) to exercise the concern map. Measure against the 2026-10-18 run: source reads, refusals, minutes per stage,
   implement and Improve actions per step, and each concern row's decision and check.
3. Later: a case with stored data and a schema change (backfill before, contraction after) to exercise migration and
   switchover rows; none of the current cases has one.

## 4. Decisions for the owner

1. **Concern map as data (A1).** Replace duty 9's prose with per-item concern rows that the gate checks for structure and
   Improve judges. Recommendation: yes. Risk: boilerplate rows; mitigated by `no: <reason>` and structure-only gating.
2. **Behavioural step Proof on a remote target (B1).** A step Proof may deploy only that step's paths to the recorded
   development target and run a read-only probe. Recommendation: yes, when the run's authority covers test deploys; plan
   records whether that target is also the delivery target (A3).
3. **What an Improve review may run (F2).** The recorded test commands under the run's deploy grant, and read-only probes;
   no other deploy. Recommendation: yes.
4. **Keep accepted steps after a test-commands-only revise (D1).** ShipLoop reruns their Proofs and skips their packets.
   Recommendation: yes.
5. **Card text in packets (A2).** First section of each selected card. Recommendation: yes; measure head sizes.
6. **A data-migration case** for a later round. Recommendation: yes, after wave A.
