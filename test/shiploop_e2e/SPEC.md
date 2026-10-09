# ShipLoop E2E specification

This is the standing specification for ShipLoop's end-to-end testing. Every
E2E run, review, improvement and learnings entry is judged against it. The
harness loads this file into the reviewer and improver prompts; do not restate
it elsewhere, cite its clause IDs (S-1 ... ) instead.

## Purpose

ShipLoop is a **general software development life cycle execution engine**. It
must carry any software request, in any language, framework, platform or
domain, from intent to a verified, committed and returned change. It is never
optimized for a particular product, game, stack or host.

The E2E loop exists to verify **that engine and how it behaves**, not the
product a run happens to build. A case (a game, a hello-world, a follow-on
feature) is a probe: a small, repeatable request whose run exposes where the
engine's design holds or breaks. A run that ships a working product but
violates a clause below is a ShipLoop defect. A product defect matters only as
evidence about ShipLoop. What a probe reveals is fixed in the engine
generically; nothing in the engine may know which probe exposed it.

Each iteration: run a case on exactly what the marketplace publishes, measure,
review against this spec, fix ShipLoop generically, release and refresh the
marketplace install (see the harness rules), rerun,
record what was learned (one commit per run; read the last three commit
messages before the next run or change), and update the Run Review page with
the run's data.

## Design clauses

**S-1 Scripts own the graph and the state.** ShipLoop's scripts decide which
stage is next, which action is legal, what was accepted, and what the run's
state is. The model never walks the graph, never decides that a stage is done
on its own word, and never edits run state. State lives in files the scripts
write (state.md, results, receipts), so it survives any loss of conversation.

**S-2 Scripts return prompts; the model does one step.** Each script call
returns the prompt for exactly one step. The model executes that step and
reports back through the one callback the packet names. The model is a
library call that does the work and reports done.

**S-3 The skill knows the scripts are authoritative.** SKILL.md and the
reference cards tell the model how to invoke the scripts and to follow what
they return. When a card and a script disagree, the script wins, and the
disagreement is a defect to fix.

**S-4 The script interface is small and uniform.** A step is started, recovered
and reported through a few fixed verbs with printed, exact argument values.
The model copies commands; it does not assemble them. A step that needs the
model to write shell glue (heredocs, JSON built by hand, `git commit`, `mv`,
`mkdir`) is a mechanical step the script should own.

**S-5 Mechanical work belongs to the script.** Anything a script can decide
from observable state (Git setup, directory creation, contracts, commits of
declared or recorded changes, archive and restart, reruns of recorded checks)
is done by the script. The model supplies only judgment: what to build, what
the review found, what the message says.

**S-6 Every packet stands alone.** Context may be cleared, compacted or lost
between any two calls. Each packet carries everything its step needs to be
executed correctly: the goal, the exit criteria, the rules that apply to that
step (stated once), the callback and the recovery command. It does not rely on
earlier conversation.

**S-6 is a main tenet of ShipLoop (owner decision 2026-10-07).** Assume the previous stage's context is gone before the next stage
runs. Each packet therefore restates, for its own stage, how the stage is meant to operate and how its result will be checked and
reviewed, even when earlier packets said the same; repetition between packets is grounding, not waste. Only repetition inside one packet
is waste, and "stated once" above means once per packet. A proposal to shorten, merge or move packet text or ledger records is judged by
this test: a model holding only the next packet knows what to do, how it is checked and where the run stands. The evidence base: after
each of the 5 compactions in the 2026-10-06 Grok run the model's first call was to re-read the current packet. A change that moves
grounding out of the packet, into a file the packet merely names or into a record the model has to find, fails S-6 unless a
clear-the-context probe at a stage boundary and inside a stage shows no redone work.

**S-7 Packets are small where they are printed; detail lives in files.** The
printed head is short: callback, goal, result contract, the path of the full
packet, recovery and pause. The full packet and every reference are files the
model opens by path. References are cited by path and section; the model reads
only the section a step needs and never re-reads whole cards or repeats
unchanged run rules inside one packet (S-6: across packets the repetition stays). Large planning context is acceptable when it sits in a
file the packet names.

**S-8 The engine is product- and technology-agnostic.** Scripts, stage prompts,
packets, SKILL.md and the general reference cards state rules in general terms
of the SDLC (state, owners, checks, boundaries, delivery), never in terms of a
game, product type, language, framework or host. A concrete product or
technology may appear only as a clearly labelled illustration ("for example
..."), never as the rule itself, and illustrations should vary rather than
repeat one domain. Technology-, platform- and tool-specific facts live in
reference or catalog files (`references/platforms/`, stack notes, tool
catalogs) that act as cached knowledge the packet points to. Script code
that must know a tool (for example, how a test runner reports counts) keeps
that knowledge in one catalog, not scattered through the logic.

**S-9 A passing script-run check is the evidence.** Progress and completion are
confirmed by a test or command the script runs and records, never by the
model's own judgment. A check that ran nothing is not a pass.

**S-10 Loops iterate until their exit condition is met.** Quality, test and
review loops (Until Loop) run until a stated, checkable condition holds, with
a frozen contract the script writes and iterations the script counts. Except
for the carve-outs below, there is no iteration cap; a loop ends on its
condition, a true blocker or a user stop.

**S-10 carve-out, owner decision 2026-10-04** (anchor: the owner's request and
the Luna 1.16.1 battleship run, not a clause this serves; it relaxes S-9 and
S-10 for one loop and says so). The Backchain planning child (a whole
`plan`/`draft`, or a `repair`/`revise` after an audit finding) defaults to one
pass. Its start contract carries `required_trivial_reviews: 0` and an exit
condition that one complete dependency review/fix/check cycle has run, its
findings are repaired within the permitted edit bounds, every `Confirm by`
clause on a step this cycle may change meets the planning guide's Outcomes
rule, and the printed `backchain-check` is ok on the final candidate. The loop
completes on the first report that assesses that exit as satisfied. That
assessment is the host model's, backed by a structural, record-only check
(unique ids, resolved suppliers, acyclic, no orphan discovered step); it is
not a script-run proof that the plan is semantically right, so S-9 holds for
this loop only in that structural sense. No numeric ceiling is added: a pass
that reports an open gap continues, a blocker or a user stop ends the loop as
before, and the vendored Until Loop is unchanged. `--backchain-passes
converge` (state option `backchain_passes`) restores two consecutive trivial
reviews; `--backchain-passes none` offers no whole loop at `plan`. The host
model writes this contract (open item a02), so S-4, S-5, S-12 and S-10's
frozen contract the script writes stay unmet for this loop, as they already
were; a future script-written or script-checked contract must accept a gate-0
complete packet whose last report is non-trivial. Quality and test loops are
not covered, nor are Improve loops except as the next carve-out says; their
no-cap rule stands. Basis: in the Luna max
battleship run (skill-craft 1.16.1) the two Backchain loops took 213 of 647.5
planning minutes; the plan loop's passes 2 to 5 each reported a non-trivial
finding of confirmation level or wording (no edge, goal or supplier changed),
passes 6 and 7 changed nothing, and no later packet names the plan graph.
Record: docs/shiploop-fast-planning-plan-2026-10-04.md.

**S-10 carve-out, owner decision 2026-10-05** (anchor: the owner's rule that
planning takes no more than 30 minutes, decided after the evaluation of the
skill-craft 1.21.0 battleship runs on Luna xhigh and Grok medium, not a clause
this serves; it relaxes S-9, S-10 and the rule that a step iterates until a
check confirms each exit criterion, for the Improve review of planning results,
and says so). The run option `planning_review` (state option `planning_review`,
recorded in `state.md` at `init` or `workspace start`, never changed afterwards;
a saved run without it is refused) selects which of the five planning results
`spec`, `test-strategy`, `plan`, `step-plan` and `test-spec` start an Improve
child. `--planning-review stage` starts one after each of the five, as before.
`--planning-review none` starts none. The Improve children after
`system-test-author` and `release-plan` and the last `carry-forward` start in
every mode; the quality and test loops and the Backchain child are not covered
and their rules stand. The option's default is a separate owner decision: until
a later dated SPEC commit states it, the code default is `stage`. Every Improve
child that starts is unchanged (a contract the script writes, the same
two-review or unchanged-first-pass exit, no iteration cap), so S-10 holds for
each loop that runs. In `none` a planning result is accepted without a review
loop. What stands in for the loop is what S-9 can name: ShipLoop's gates at
`complete` (cited files exist; the plan's assumption list; the step plan's
commands, criteria, paths and dependency order; the knowledge home's required
files, credential screen and requirement-ID retention); the structural,
record-only `backchain-check`; at `test-author`, a run of the focused commands
that must run a test (a counted test and every listed ID shown on exit 0, a
failing test on a non-zero exit), so a command whose tests cannot load is refused where it
can be fixed (a command that also runs a failing test and has a module that cannot load, with no ID listed
for that module, is still accepted: a count cannot tell); and then the `test-red`, `test-green`, `regression` and
system-test gates, which ShipLoop runs and records. No script-run check at
planning, in any mode, covers whether the spec's criteria are complete and
verifiable, whether the test strategy maps every criterion to a check, or
whether a test spec's oracles are independent. Under `none` those rest on the
producer's own confirmation of the Done-when conditions the packet prints (a
model judgement, printed in every mode), on the later gates and on the
end-of-work review. An Improve child's own S-9 evidence has been loop mechanics
the script counts (passes, the review streak, a Git cross-check, the commit
rule), never a check of the review's content, so `none` removes a second look,
not a script-run check. In `none` the plan child's stopped-child reconciliation
(`improve-reconcile`) and the plan-time experiments it hosts do not exist (the
plan's assumption list is still checked at `complete`); the spec and test
strategy are committed to the knowledge home when each is accepted and no
Improve child reviews them afterwards, so later runs inherit them unreviewed;
and the first Improve child of a run is the last item's `carry-forward`, so a `none` run names its Improve
card at `init` or `workspace start` (`--improve-skill`, resolved there; refused without it), because the
first item's quality and test loops read the card and no earlier child binds it. Basis: in the Luna xhigh run the
planning window was 375.9 minutes, 203.4 (54%) in five Improve children (22
passes), and in the Grok medium run 72.7 minutes, 42.4 (58%) in five children
(26 passes); the Luna reviews made five warranted fixes and did not raise the
`test-red` defect whose redo cost 165.9 minutes; a Sonnet 5.5 battleship run's
plan review raised a related class [I] (a plan with no importable server seam,
commit b1e196d; the Luna defect was a focused suite that imported a file no step created, and
the Sonnet reviews took about 4 seconds each, so it is not a like-for-like benchmark), and in a condensed-packet experiment the planning review with
the platform-claim bullet caught 10 of 15 real plan-stage platform errors
against 0 of 15 without it (Sonnet, three trials per cell). No run without the
planning reviews exists, so the rate of defects that escape without them is
unknown. Record: docs/shiploop-planning-review-plan-2026-10-05.md.

**S-11 Knowledge is retained in the repository.** Planning knowledge (living
spec, environment, test strategy, per-feature records) is committed to the
product's knowledge home, and the product itself ends committed on the
source branch, so the next run builds on it instead of rediscovering it.

**S-12 One implementation of each mechanism.** A mechanism (committing, loop
contracts and starts, receipts, identity, privacy screens) has one code path
that every caller uses. New features extend it rather than copying it; old
formats are refused, not shimmed.

**S-13 Everything is generic.** Fixes address the ShipLoop behavior a run
exposed, never the probe's product or platform. A fix is stated, named and
tested in general terms; its tests use neutral fixtures, not the probe's
product. A case's specifics (its prompt and product checks) stay in the
harness's case catalog.

**S-14 Unattended by default.** Every implementation and every test case assumes
ShipLoop runs unattended: no person is watching, nothing is typed on standard
input, and no prompt is answered. The scripts never read a terminal or wait
for input; hosts and checks run with standard input closed. When a step meets
an open question, it takes a stated, recorded default (an assumption the
handoff reports) instead of waiting. When a step needs something only a person
can supply (a sign-in, a grant, a physical observation, an authority the run
does not hold), the run records it as an open item, continues with everything
that does not depend on it. Only when the run truly cannot proceed without the
person does it prompt them: it ends its turn with the question (the
`awaiting` route) and the command to resume, stating why no default would do.
It never blocks on standard input and never asks as a first resort (owner,
2026-09-27).

**S-15 The user can follow the run without the model composing status.** What
the user sees about progress is rendered by ShipLoop's scripts from saved
state: a short status at every step and, at milestones, a narrative of what is
achieved, what is happening, what comes next and the observed pace. Each
accepted step states its own one-line headline for that narrative. Where the
host displays hook output, a hook shows it; everywhere else the model shows the
script's text as written, once per milestone. The model never composes,
paraphrases or estimates progress itself, and never repeats unchanged status
(owner, 2026-09-27).

## Change admission

No change is planned, let alone made, before its negative consequences have
been sought out and addressed. Every change to ShipLoop, to its skills and
cards, or to this harness goes through these steps, in this order, recorded in
the plan item and summarised in the commit message:

- **Adversarial evaluation first.** Before the change is planned, attack it:
  argue the case against it as a hostile reviewer would. At minimum ask how it
  could:
  - weaken any clause S-1..S-15, including ones it does not target;
  - break another style, host, language or platform than the one that
    motivated it;
  - fail silently, or pass the tests while failing a live run;
  - add model-written glue, host refusals or recovery dead ends, or wait on a
    person in an unattended run (S-14);
  - enlarge printed or filed packet text, or context over a whole run;
  - leak or commit secrets, touch user work outside the run, or change the
    user's repository or history unexpectedly;
  - break saved runs, existing callers, tests, adapters or catalogs that pin
    today's behaviour;
  - cost more turns, time or money than it saves;
  - be gamed: make a metric improve while the behaviour gets worse.
  Each consequence found gets a disposition: **mitigated** (how, and how the
  mitigation is tested), **accepted** (why the cost is worth it, and which
  clause asks for it), or **change rejected**. A change with an unaddressed
  consequence is not planned. The evaluation must name concrete scenarios;
  "no risk" without a scenario considered is not an evaluation.

- **Anchor**: the clause or clauses (S-n) the change serves, and the run
  evidence that motivated it (run, metric, transcript line). A change with no
  anchor is not made; if it is still wanted, this spec is amended first, in its
  own commit, stating why.
- **Non-regression**: which clauses and existing behaviours the change could
  touch, and why it does not weaken any of them. "Removes duplication" or
  "shortens a packet" must say which obligation, check or safeguard is kept and
  where.
- **Evidence**: the hermetic tests that prove the statement, plus the E2E
  suite that confirms it live (see below). A change that alters behaviour on
  purpose names the behaviour, the clause that asks for it, and the runs whose
  results it is expected to change.

A reviewer (or the review step of `iterate.py`) rejects a change whose anchor
does not hold or whose non-regression statement is missing or contradicted by
evidence.

## E2E suites: depth before breadth

End-to-end testing is organised as suites, so one style of work can be iterated
on quickly before the breadth of everything is checked.

- **Case**: one repeatable request with its product checks (`cases.json`).
  Cases are grouped by **style**: the shape of software and delivery they
  probe (for example: a browser UI over an HTTP service; a command-line
  tool over files; a stateful service with concurrent writers; a follow-on
  feature in an existing repository).
- **Focused suite** (depth): the cases of one style, run repeatedly while a
  change is developed for the behaviour that style exposes. It is the tight
  loop: run, measure, fix, rerun, one style at a time.
- **Breadth suite**: one case of every style, run once each. It is the
  generality gate: a change that improved a focused suite is not "general"
  (S-13) until the breadth suite shows no regression in any other style.
- **Promotion**: work on a style stays in its focused suite until that suite's
  acceptance holds (every verdict passes, reliability and cost no worse than
  the style's baseline); then the breadth suite runs before a release is called
  good. A style whose focused suite has never passed has no baseline and is
  not used to judge other changes.
- Each suite records its own baselines (per case: verdicts, turns, cost,
  sessions, cancellations, glue, ShipLoop failures) so a run is compared with
  the same case's history, never across styles.

## How the harness checks the clauses

| Clause | Evidence the harness records (result.json, metrics.json, review) |
|---|---|
| S-1, S-2 | ShipLoop command failures and refusals (`shiploop_failures`: a tool result with a line that begins a ShipLoop refusal prefix, or a nonzero exit of a command that names a ShipLoop verb; read on every host, from Claude's `tool_result` blocks too, where a refusal behind a pipe shows no exit); resumed sessions continue from `next`; no state edits outside ShipLoop verbs |
| S-4, S-5 | host-cancelled tool calls; `model_glue` (model `git commit`/`add`, shell writes into ShipLoop-owned paths, hand-built loop contracts), counted per command on every host: a script the model wrote that wraps the CLI hides its ShipLoop calls from it, so Claude's `tool_use.scratch_scripts` lists those scripts and their runs beside it, and a Claude glue of 0 is a lower bound |
| S-6 | runs survive compaction and session resumes without losing their place |
| S-7 | truncated outputs, peak context, compactions, packet head size; for Claude, per-stage `context` (model calls, peak, share of the window) and `tool_use.packets` (packet bytes on disk, printed heads and Reads, whole or ranged) |
| S-9, S-10 | `script_verifications` (ShipLoop's own verify records, with the count that ran red, which a test-red record or a probe passes by design), Improve children; a zero-test pass fails |
| S-10 carve-out (planning ceiling), S-12 | `planning` in metrics.json (added 2026-10-08): the planning window, intake to the first accepted test-spec, on the engine's clock and on the host's clock, each stage's seconds with the Improve share (child bind to accept), and the window's output and reasoning tokens where the host's per-call counts are exact (Grok, Codex). Recorded beside the verdicts and never scored: the owner's 30-minute planning rule is read from it, and it is the one place these figures are computed |
| S-12 | `claude_code_version` in metrics.json and result.json (added 2026-10-08): the host CLI build the sessions ran on, so two runs of one prompt on different builds (the Sonnet pair of 2026-10-06 and 2026-10-07 ran on 2.1.291 and 2.1.292) are not read as a controlled comparison. Null where the host's events do not carry it |
| S-11 | `committed` verdict; follow-on retention checks (earlier files, spec IDs, tests grew) |
| S-8, S-12, S-13 | review of the diff under test: no technology in prompts, no second implementation |
| S-14 | host and checks run with standard input closed; `asked_user` (host ask-a-person tool calls); a run ending blocked or awaiting a person is reported as such, never resumed as if answered; a requested stop (`<output>/stop`, added 2026-10-08) ends the host and is recorded as `stopped`, and never answers a blocked or awaiting run |
| S-15 | `narrative`: milestone narratives ShipLoop emitted for the model to show, how many the model showed (heading present) and showed verbatim (every line), the stages whose narrative it skipped, and the share of accepted step results that carry a headline. Scored beside reliability, not a verdict, until a style has a baseline |
| S-1, S-4, S-5, S-6, S-9, S-10 (as evidence, never a verdict) | `fidelity` in metrics.json only (added 2026-10-09; not in result.json or a baseline row, like `planning`): the evidence class of each accepted action against the check its stage declares (script, loop, file, note, sentence, skipped, with the records behind it), ShipLoop's verify records read as JSON (a focused or regression row whose counts are null is unmeasured, never a pass), the model's edits of script-owned files and its name-pattern kills and `git commit`/`add` commands as listed facts with event numbers, each ShipLoop refusal with whether the same first line came back, the engine's end state, and the five questions each Improve packet carries. Heuristic rows are a lower bound and say so; every part fails open and an input it cannot read is `unmeasured` with the reason |

Verdicts (invoked, plugin, process, shiploop, committed, checks) must all pass.
Reliability (sessions, cancellations, failures) and cost (turns, dollars, per
stage) are scored beside them and compared with the previous run of the same
case.

## Parallel work

E2E runs are long, so the loop spends its waiting time in parallel.

- Before executing a list of steps, decide which are independent. Run
  independent steps together, and hand read-only work (run forensics,
  host inventories, learnings drafts, reviews against this spec) to
  background agents or tasks while a long job (a test tier, a run) is
  running. Name the steps that must stay in order and the dependency that
  orders them (for example: release after the full tier; host updates and
  the preflight after the release is published; a rerun after the
  preflight).
- Independent runs execute in parallel. Every case writes only into its
  own output folder, so a suite runs its independent chains (a case with
  its follow-ons) concurrently, up to `--max-parallel` (default 3); a
  follow-on always waits for its predecessor in the same chain. Separate
  suites or cases started by hand may also run at once, each in its own
  output folder. This is for finding failures sooner; a pair whose figures
  are compared is the exception stated in the bullet "Runs compared on wall
  time or per-call cost run one after the other".
- Concurrency must not change a verdict. Concurrent runs are quiet (no
  interleaved live view), share no files, and pass the same checks. A
  failure seen only in a parallel run (for example two products' own tests
  binding the same fixed port, or a host rate limit) is rerun alone
  (`--serial`) before it is attributed to ShipLoop.
- **Runs compared on wall time or per-call cost run one after the other**
  (amended 2026-10-08; anchor "Concurrency must not change a verdict"). A
  before/after pair, or a host or model comparison, is started the second
  after the first has ended: `--serial` for a suite, or launch the second
  once the first has ended. Overlap is for runs whose point is concurrency.
  The suite default (`--max-parallel 3`) stays, because a suite's job is to
  find failures; its figures are not a timing comparison. Basis: the two
  round-2 Sonnet runs (r2-battleship-sonnet, r2-checkers-sonnet) were started
  within 0.1 s of each other (first `timeline.jsonl` stamps), shared loopback
  and CPU, and one model ran `pkill -f "node server.js"`, which matches any
  run's server by its name. Known limit: a baseline row carries no overlap field, so a
  later comparison cannot exclude an overlapped run; each run's
  `timeline.jsonl` start stamp is the only record. This is a discipline, not a
  guarantee.
- Agents do not replace evidence: an agent's analysis is a lead, and a
  claim it makes is checked against the event log or a script before it
  drives a change (Change admission).

## Evolving this spec

ShipLoop will evolve, and so will this spec. When a planned change needs a
clause this spec does not have, or conflicts with one, amend the spec first,
in its own commit, stating what changed, why, and which runs or behaviours
the amendment affects. The harness always judges against the spec as it
stands at the commit under test.

## Rules for the harness itself

- The harness core (runner, metrics, grading, review) is case-agnostic: it
  measures the engine through ShipLoop's own records and the clauses above.
  Only `cases.json` knows a case's product.
- Probe more than one kind of software. Rotate cases across domains and stacks
  (for example a service, a command-line tool, a data transformation, a UI)
  so improvements cannot overfit one probe; a change justified by one case is
  re-checked on another before it is called general.

- Test exactly what the marketplace publishes (`--source marketplace`); build
  the checkout (`--source checkout`) only to try an unreleased candidate, and
  never record a checkout run as evidence about a release.
- **Publish, then refresh, then run.** A change pushed to the repository is not
  what a host runs until it is released and the host is refreshed. Every change
  that should reach a marketplace run goes through, in order:
  1. `scripts/release.py`, which builds `plugins/skill-craft/` and the catalogs
     from source, then the push of that release commit (its CI must pass);
  2. a refresh of the marketplace on the host the harness drives. The harness
     does this itself: each marketplace run adds the published marketplace and
     installs `skill-craft` into a fresh, isolated profile, so no cached or
     earlier install is ever reused;
  3. the run, which refuses to start (the version gate) unless the local
     checkout is origin/main, origin/main has no pending change notes (every
     source change on main is released), and the installed plugin and
     ShipLoop versions equal the ones origin/main's catalog publishes.
  After a release, also update the user's own hosts (Claude, Grok, Codex) so
  their installs match what the harness tested. Before a rerun on any host,
  `run.py --preflight-only --host all` shows what each host gets; a run is not
  started on a host whose preflight refuses.
- **Batch changes, then verify the batch.** Fixes found in a round of runs
  collect on one branch; each is admitted (Change admission) and checked on its
  own footprint: the suites it touches, in parallel, plus the quick tier over
  what changed. The full hermetic tier is not run locally; it runs in CI on the
  release commit. The batch ships as one release, and the whole group is then
  verified together: every host's preflight on the new version, then the live
  runs, smallest first (a smoke case before a full product), while CI runs on
  the release commit.
- **Proceed optimistically; cancel on failure.** Presume the pending checks
  pass: release, refresh hosts and start the runs without waiting for CI, and
  run independent work in parallel. Only a failure changes course: a run is
  refused while CI has already failed, and runs in flight are cancelled (and the
  change reverted or fixed) when CI or an earlier gate fails. A failure there is fixed forward
  into the next batch, not by a release per fix.
- **Choose the verification runs from a coverage map.** Before a batch's live
  runs, map every change to the one run that proves it; each run must prove
  something no other run in the set does, and a change covered only by hermetic
  tests says so. Prefer a case that has not passed on a recent version over one
  that just did; a change that shows only under concurrency (shared state,
  temporary files) needs two runs at once. The map lives in the `batch` suite
  (`gate`, `cases`, `covers`) and the plan; the gate runs first and alone and a
  failed gate stops the costlier runs.
- **The driver is a parameter, not a code path.** The host (Grok, Claude,
  Codex), its model and its effort are chosen per run; everything that differs
  between hosts lives in one host class, and the rest of the harness reads one
  normalized event stream. A verdict must not depend on which host produced it,
  and a baseline compares only with rows from the same host, model and effort.
  What a host adds on its own (for example account-enabled plugins in a Codex
  profile) is recorded with the run, never silently removed or ignored.
- Run unattended (S-14): the host and every check get closed standard input and
  a timeout; a case prompt never needs a person, and a check never waits for
  input.
- **A resume names the CLI the run itself uses** (amended 2026-10-08; anchor S-6,
  a packet stands alone and so does the prompt that continues a run, and S-4,
  the model copies a printed command). The prompt that continues a run after a
  stop, a kill or an interrupt carries `python3 "<cli>" next --run-dir "<dir>"`
  with the ShipLoop CLI of the plugin the run started on, whatever host or source
  built it. There is no bare-command fallback; a resume whose CLI file is gone is
  refused before a host starts. Basis: a Claude run built from a checkout was
  given a bare `shiploop next` (the marketplace route lost 13 turns to the same
  prompt, fixed in 7c1f1014); the command the harness prints for continuing a run
  carries the harness flags too, because a resume that falls back to the default
  `--timeout` can outlive the task that launched it. It is printed only where
  those flags are the run's own: not by a regrade (`--grade-only`), whose flags
  are the grader's, and not for a run that wrote no ShipLoop state, which
  `--resume-run` refuses.
- **Every ending leaves its records** (amended 2026-10-08; anchor S-14, a run
  is judged from files, and S-9). A run the harness ends (a deadline, a
  requested stop, a spent resume budget) writes metrics.json, result.json and the
  Run Review export through the same path as a finished run, and a run whose
  harness was killed can be given them afterwards by `--resume-run <dir>
  --grade-only`, which starts no host. A requested stop (the file
  `<output>/stop`) ends the host, is never relaunched and is recorded as
  `stopped` with no process verdict (the host did not fail) however the request
  is found: it killed a running session, or it was found as a session ended on
  its own, or between two sessions (the last session keeps its own status in
  `process.sessions`); it exits non-zero,
  because the run is not finished and a suite reads exit 0 as a pass. A stop
  never answers a blocked or awaiting run (S-14). Basis: 3 of the 11 harness
  runs from 2026-10-04 to 2026-10-07 (v1200-battleship-luna,
  v1210-battleship-grok-medium, v1210-battleship-luna-xhigh) were stopped by hand
  or by the task and have no metrics.json, result.json or export; the 8 that
  ended on their own have all three. A stop that names a stage (`--stop-at`) is
  not part of this amendment: it stays deferred until planning probes are routine.
  A SIGTERM to the harness (a task runner's stop, `kill`) is a requested stop
  too, and so is a SIGHUP unless the launch ignored it (`nohup` keeps a
  detached run alive, as the README allows): the harness ends every live host
  at once, writes the same records and records `stopped` with the reason
  `terminated by SIGTERM`; a Ctrl-C on a suite is handled as a SIGTERM, and on
  a single case ends the hosts as the harness exits. This
  covers `run.py` started as a program, not `iterate.py`, which calls it in its
  own process. A SIGKILL gives the harness no chance to run anything:
  `--grade-only` is the remedy, and an orphan host of a SIGKILLed harness is
  not looked for (open). Basis: the r2 Grok run's log ends `exit 241` (-15 mod
  256, a SIGTERM) 855 s in; its host, started in a session of its own, was not
  signalled and went on writing ledger files for about 28 minutes while no
  events, metrics or result.json were being written. Which signal a task
  runner sends at its time limit is unknown (open), so the handler is proven
  for SIGTERM only.
- **A baseline row is a finished run's** (amended 2026-10-08; anchor S-12, one
  meaning for a baseline). No row is written for a resumed or seeded run, for a
  run whose engine is still active when the harness ends (a deadline, a stop, a
  spent resume budget), or for a run whose host the harness killed, by the
  deadline or by a stop, before ShipLoop wrote any state (process status
  `timeout` or `stopped`, engine status `unknown`): its turns, cost and stages
  are a fragment, and the last row of a driver is what the next run is compared
  with. A host that ends on its own, even with no engine state, is a finished
  run and keeps its row, since its own ending is what the row records. Basis: the
  existing `hang` fake with `--timeout 3` appended a row with process status
  `timeout` and engine status `unknown`, which `scan_baseline` then offered as the
  last comparable row (the first form of this rule covered only an active engine
  and let that row through; corrected the same day).
- **A run leaves nothing listening** (amended 2026-10-08; anchor S-11, a
  lesson a contaminated run commits is retained as knowledge, and "Concurrency
  must not change a verdict"). When a host session ends, and once after the
  case checks, the harness stops every TCP listener of its own user whose
  working directory or command line lies under that case's output folder, and
  records what it stopped, or could not stop, as `left_behind` in result.json
  (an optional key: where the process table could not be read the record says
  `observed: false` and why, and never reads as none). It is a record and not a
  verdict, and a regrade (`--grade-only`) reaps nothing, since a live host may
  be running. A launch, and `--preflight-only`, is refused while a listener sits
  under another case's output folder whose harness is not alive (liveness is a
  held lock on `<output>/.harness-lock`, which the kernel drops on any death, so
  parallel runs are not refused); the refusal has no override and names the
  process, because a leaked process is stopped by pid. A `--resume-run` of a
  case whose harness is running (its lock is held) is refused too; a regrade
  is not, since it starts and stops nothing. That a finished case
  folder served by hand blocks every later launch the same way is a choice: a
  printed warning with a recorded `stale_listeners_at_start` was weighed and not
  taken, because the round-2 contamination was a launch that went ahead.
  Basis: pid 63973, the
  `node server.js` of the r1 Checkers run's model, parent pid 1, bound `*:3457`
  from 10:49 local on 2026-10-08 (that run exited rc 0, so no kill ran, and the
  model's Bash call has a process group of its own, which the harness's
  group kill never reaches); both r2 runs chose `PORT=3457`, both met
  `EADDRINUSE`, and the Checkers run committed a false lesson about a
  "foreign" server to its returned repository (r2-checkers-sonnet
  `docs/shiploop/environment.md`). Limits: non-listening leftovers, UDP and
  unix-socket servers, and a server whose working directory and command line are
  both outside the folder are not reaped; a pair of concurrent runs still
  shares loopback (see Parallel work).
- **A fidelity block is a record, never a verdict** (amended 2026-10-09; anchor S-9, "a check that ran nothing is not a pass", and S-1, S-4, S-5
  and S-6, the clauses its rows are evidence about; the S-15 rule that a measure is scored beside reliability until a style has a baseline).
  Basis: rounds 1 to 3 of the bounded improvement loop spent 17 hand-mined lens reports on counts the run's own records hold (which stages
  rest on a script-run record, how many verify rows ran a test, which refusals came back unchanged, the two `sed -i` edits of
  `return-plan.md` in the round-1 Sonnet runs, the `pkill -f "node server.js"` commands that stopped sibling servers). `metrics.json` therefore
  carries a `fidelity` block (`test/shiploop_e2e/fidelity.py`, built once per run or regrade by `run._main`), and these rules bound it:
  1. It changes no verdict, exit code, baseline row, comparison or run, it is not shown to the model, and it starts no process and sends nothing to a
     model. It is not copied into `result.json`, whose explicit subset is the same as for `planning`.
  2. Unmeasured is unknown. A part whose input is absent, whose engine records are of another layout (an older stage table, a packet layout
     without `-improve.md` files) or whose event stream holds no tool call (a regrade of a run whose stream is gone) is null with its reason in the
     block's `unmeasured` map, never 0 and never a pass. A focused or regression row of a verify record whose `counts` are null is unmeasured, not
     a pass (S-9): such a row does not show that a test ran (the v1220 Sonnet run has 34 of 34 such rows and the v1220 Grok run 30 of 30).
  3. A heuristic part (script-owned edits, name-pattern kills, model commits, refusals read from tool results) is a list of facts for a reviewer and a
     lower bound: no hit is not proof. Known misses, pinned by tests so they are not forgotten: an edit of a script-owned file by interpreter
     code (the round-1 `python3 - <<EOF ... open(p, "w")` rewrite of `return-plan.md`), a shell `apply_patch` or `git apply`, a kill by numeric
     pid (a model's own job and a sibling's process look alike), a relative path after `cd` for any file but the three workspace files that are
     matched by name (`return-plan.md`, `return-receipt.md`, `workspace.md`), and a ShipLoop verb a model's wrapper script hides from the command.
     `model_glue` stays frozen so baselines compare: it does not read inside a Codex `zsh -lc "..."` string, so a Codex glue count is a known
     undercount, and only the fidelity detectors unwrap such a string.
  4. There is no pass or fail table. No row of the block is a clause verdict until a style has a baseline for it and a later dated amendment says
     which rows are verdicts. An earlier design that scored eight clauses was set aside because S-10 as written would have failed 2 of the 11
     saved Claude and Grok runs (a work item's first carry-forward has no Improve child by design), S-9 would have passed null counts, S-4
     would have passed beside wrapper scripts, and S-15 says narratives are not a verdict.
  5. What no script checks stays with a reviewer, and the README names it: whether one call carries one step (S-2), whether the cards agree with the
     scripts (S-3), packet size (S-7), technology-agnostic wording (S-8), one implementation of each mechanism (S-12) and generality (S-13), and also
     the truth of a model's sentence, the strength of a test's oracle, and whether a text is clear. The `file` class is satisfied by citing any
     file, so it is a reading aid and never a target.
  The one measure of the main tenet in action (the first call after a Grok compaction) belongs to the clear-context group, as `fresh_starts`, and
  is not built here. Non-regression: only keys are added (`fidelity` in `metrics.json`, and a `tools` argument to `metrics.collect`, an `event` argument to
  `ToolLog.call` and `ToolLog.result`, and an optional `limit` to `failure_line`); `shiploop_failures`, `model_glue`, `script_verifications`, the planning
  block and every baseline row keep their shape, and S-1 through S-15 are not weakened because nothing here gates a run.
- Start from an empty directory, or for a follow-on case, from a clean copy of
  an earlier run's checkout. The harness leaves no files of its own behind.
- Case products are disposable probes. The repository a run builds (and any
  follow-on copy of it) lives outside skill-craft; the harness refuses an
  output directory inside the checkout. A product is never committed to
  skill-craft, merged into ShipLoop, or copied into a reference or fixture.
  What skill-craft keeps is the harness: its code, case prompts, product
  checks, baselines and learnings.
- Never print packet text or run markers into a session that is not the run's
  host.
- After each run, record learnings in LEARNINGS.md with a detailed commit that
  names the suite, the case, and the clauses the run confirmed or violated.
