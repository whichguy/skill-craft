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
review against this spec, fix ShipLoop generically, release, rerun, and
record what was learned (one commit per run; read the last three commit
messages before the next run or change).

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

**S-7 Packets are small where they are printed; detail lives in files.** The
printed head is short: callback, goal, result contract, the path of the full
packet, recovery and pause. The full packet and every reference are files the
model opens by path. References are cited by path and section; the model reads
only the section a step needs and never re-reads whole cards or repeats
unchanged run rules. Large planning context is acceptable when it sits in a
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
a frozen contract the script writes and iterations the script counts. There
is no iteration cap; a loop ends on its condition, a true blocker or a user
stop.

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

## Change admission

No change is planned, let alone made, before its negative consequences have
been sought out and addressed. Every change to ShipLoop, to its skills and
cards, or to this harness goes through these steps, in this order, recorded in
the plan item and summarised in the commit message:

- **Adversarial evaluation first.** Before the change is planned, attack it:
  argue the case against it as a hostile reviewer would. At minimum ask how it
  could:
  - weaken any clause S-1..S-13, including ones it does not target;
  - break another style, host, language or platform than the one that
    motivated it;
  - fail silently, or pass the tests while failing a live run;
  - add model-written glue, host refusals or recovery dead ends;
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
| S-1, S-2 | ShipLoop command failures and refusals; resumed sessions continue from `next`; no state edits outside ShipLoop verbs |
| S-4, S-5 | host-cancelled tool calls; `model_glue` (model `git commit`/`add`, shell writes into ShipLoop-owned paths, hand-built loop contracts) |
| S-6 | runs survive compaction and session resumes without losing their place |
| S-7 | truncated outputs, peak context, compactions, packet head size |
| S-9, S-10 | `script_verifications` (ShipLoop's own verify records), Improve children; a zero-test pass fails |
| S-11 | `committed` verdict; follow-on retention checks (earlier files, spec IDs, tests grew) |
| S-8, S-12, S-13 | review of the diff under test: no technology in prompts, no second implementation |

Verdicts (invoked, plugin, process, shiploop, committed, checks) must all pass.
Reliability (sessions, cancellations, failures) and cost (turns, dollars, per
stage) are scored beside them and compared with the previous run of the same
case.

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

- Test exactly what the marketplace publishes (`--source marketplace`, version
  gate); build the checkout only to try an unreleased candidate.
- Start from an empty directory, or for a follow-on case, from a clean copy of
  an earlier run's checkout. The harness leaves no files of its own behind.
- Never print packet text or run markers into a session that is not the run's
  host.
- After each run, record learnings in LEARNINGS.md with a detailed commit that
  names the suite, the case, and the clauses the run confirmed or violated.
