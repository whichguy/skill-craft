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

## How the harness checks the clauses

| Clause | Evidence the harness records (result.json, metrics.json, review) |
|---|---|
| S-1, S-2 | ShipLoop command failures and refusals; resumed sessions continue from `next`; no state edits outside ShipLoop verbs |
| S-4, S-5 | host-cancelled tool calls and model-written glue (heredoc, `git commit`, `mv`, hand-built JSON) in the transcript |
| S-6 | runs survive compaction and session resumes without losing their place |
| S-7 | truncated outputs, peak context, compactions, packet head size |
| S-9, S-10 | test runs, Improve children, verify records; a zero-test pass fails |
| S-11 | `committed` verdict; follow-on retention checks (earlier files, spec IDs, tests grew) |
| S-8, S-12, S-13 | review of the diff under test: no technology in prompts, no second implementation |

Verdicts (invoked, plugin, process, shiploop, committed, checks) must all pass.
Reliability (sessions, cancellations, failures) and cost (turns, dollars, per
stage) are scored beside them and compared with the previous run of the same
case.

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
  names the clauses the run confirmed or violated.
