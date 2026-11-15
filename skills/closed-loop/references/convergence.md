# Convergence: the certificate

A campaign never says "done". It says one of two things about a **named scope on a named build as graded by a named evaluator**:
`converged`, or `incomplete` with reasons. `$LOOP certificate` runs all seven checks; `$LOOP check --clause Cn` runs one (they are the
Until Loop contract's exit checks). Checks are quick reads of recorded evidence and print the hash of the script that ran.

A **quiet iteration** is a finished step with a valid, complete review and judge, no recorded invalid evidence, no material discovery
(new or repeated), no candidate outcome, and every scope case run and within its floors. The orchestrator computes it; the adapter does not.

| Check | Requires |
| --- | --- |
| **C1 backlog** | every material in-scope record is `verified`, or `dropped`/`refuted`/`rejected` *with evidence*. One that is `open`, `admitted`, `promoted` (not yet verified), `deferred`, `owner` or `unknown` keeps the scope incomplete, with its `reopen_when`. Records with `target: adapter` are outside a subject certificate and listed; records whose `cases` miss the scope are outside it and listed |
| **C2 quiet window** | the last K iterations that ran on the current build at this scope and scoring identity were all quiet (K from the manifest, default 2: an operational heuristic) |
| **C3 green** | every scope case has a run on the current build that met its floors against a `comparable` baseline. `none` or `unknown` blocks |
| **C4 coverage exercised** | every dimension value the scope declares has a run on the current build, and every catalog value outside it is listed as not covered |
| **C5 clean, with positive evidence** | the last iteration has a verified cleanup receipt (absence of leftovers is not evidence) and a green quick-tier receipt for its build |
| **C6 acceptance** | every promoted candidate has acceptance evidence naming the same candidate hash; with nothing promoted the certificate says "no candidate" |
| **C7 no invalid or unknown evidence** | no invalid, incomplete or missing review, judge or receipt in the window, and no unresolved unknown inside the scope's claim |

**Stale evidence.** C2 and C3 fail with "stale" when the adapter's current `build` or `scoring` differs from the last iteration's: the
subject or the evaluator changed. The campaign then runs a new iteration rather than stopping.

**Statuses.** The *scope certificate* is `converged` or `incomplete`. The *campaign status* is the status of its `stop`: a scope can
be converged while the campaign is `incomplete` because widening needs the owner. A `converged` campaign stop means the declared
catalog is covered and the blind-spot hunt is recorded; it is never a claim that no material problem remains outside what the
evaluation can see.

**What `report.md` must say**: the status line (campaign and scope), why the scope is not converged, unresolved material records
with their reopening conditions, what the scope does not cover, the adapter backlog, unresolved unknowns, quota used against budget,
and the iteration count. A script stop, a cap, a non-promotion streak or empty findings never appears as convergence.
