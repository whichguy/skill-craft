# Convergence: the certificate

A campaign never says "done". It says one of two things about a **named scope on a named build as graded by a named evaluator**:
`converged`, or `incomplete` with reasons. `loop certificate` runs all seven checks; `loop check --clause Cn` runs one (they are the
Until Loop contract's exit checks). Checks are quick reads of recorded evidence and print the hash of the script that ran.

A **quiet iteration** is a finished step with a valid, complete review and judge, no recorded invalid evidence, no material discovery
(new or repeated), no candidate outcome, and every scope case run and within its floors. The orchestrator computes it; the adapter
does not. It computes it only from evidence that passed validation: a report with a wrong type, a missing or unrequested case, an
empty identity or a consumption that is not a finite number is recorded as a **failed step** (an invalid iteration that is never
quiet), and so is a step that failed, was cancelled, or ran on another build than the one it was started from.

| Check | Requires |
| --- | --- |
| **C1 backlog** | every material in-scope record is `verified`, or `dropped`/`refuted`/`rejected`, **with non-empty evidence**, and **no task is open** (a `needs_owner` task, a diagnosis or a hunt is work the scope still owes). One that is `open`, `admitted`, `promoted` (not yet verified), `deferred`, `owner`, `unknown` or any status this script has not seen keeps the scope incomplete, with its `reopen_when`. Records with `target: adapter` are outside a subject certificate and listed; records whose `cases` miss the scope are outside it and listed |
| **C2 quiet window** | the last K iterations at the **active** scope that ran on the current build and scoring identity were all quiet (K from the manifest or `init --quiet-window`, an integer of at least 1, default 2: an operational heuristic). A newly widened scope has no iteration yet, so it cannot be converged on the previous scope's evidence |
| **C3 green** | every scope case has a run on the current build that met its floors against a `comparable` baseline. `none` or `unknown` blocks |
| **C4 coverage exercised** | every dimension value (and declared combination of dimensions) the scope covers has a run on the current build, and every catalog value outside it is listed as not covered |
| **C5 clean, with positive evidence** | **every** iteration the campaign started has a verified cleanup receipt (absence of leftovers is not evidence; a failed or cancelled run needs `loop cleanup`), **no step is still running**, no launch whose outcome is unknown remains (a start that failed after the adapter may have launched the run needs `cleanup` too), and the last iteration has a green quick-tier receipt for its build |
| **C6 acceptance** | every promoted candidate has acceptance evidence naming the same candidate hash; with nothing promoted the certificate says "no candidate" |
| **C7 no invalid or unknown evidence** | no invalid, incomplete or missing review, judge or receipt in the window, no unresolved unknown inside the scope's claim, and **the latest readiness still shows the start rule for this boundary** (a later readiness that fails withdraws the certificate) |

**Stale evidence.** C2 and C3 fail with "stale" when the adapter's current `build` or `scoring` differs from the last iteration's: the
subject or the evaluator changed. The campaign then runs a new iteration rather than stopping.

**Frozen checks are bound to what they certify.** Each contract check carries `--expect-sha` (this script), `--expect-scope` and
`--expect-identity` (this campaign). A check frozen for scope S0 exits 3 once the campaign is at S1, so an old contract can never
certify a newer scope.

**Statuses.** The *scope certificate* is `converged` or `incomplete`. The *campaign status* is `in progress` until the campaign
stops, then the status of its `stop`: a scope can be converged while the campaign is `incomplete` because widening needs the
owner or the budget ran out. A `converged` campaign stop means the declared catalog is covered and every blind spot any hunt named
was rejected with a reason. **One predicate** decides it, when the stop is made and every time it is read (`next`, `report`): the
scope certificate converged (which holds running steps and open tasks), no blind spot without a rejection, and the budget not used.
A later unknown, task, deferred blind spot, changed build or spending turns the stop into `incomplete`. It is never a claim that no
material problem remains outside what the evaluation can see.

**What the certificate may claim.** It carries the readiness result recorded for this boundary: the claims readiness allows
(`allowed`) and, when none was recorded, the note that no quality claim is allowed. Claims are bound to the scoring identity they
were proven under: when the evaluator's scoring identity differs from the recorded one, `allowed` is empty and the note says to
rerun readiness. A quality claim about a property is allowed only
when that property's sensitivity was shown; otherwise say "converged for scope S on build B, quality not shown sensitive".

**What the script cannot prove.** It checks the evidence an adapter reports; it cannot show that a boolean the adapter printed
corresponds to a run that truthfully happened. The owner's ratification of the boundary, the pinned adapter and grader files, and the
readiness probes are what stand behind that trust.

**What `report.md` must say**: the status line (campaign and scope), why the scope is not converged, unresolved material records
with their reopening conditions, what the scope does not cover, the adapter backlog, the claims the certificate may make, unresolved
unknowns, what answered each resolved unknown (its `--evidence`), quota used against budget (and that it was exhausted), and the
iteration count. A script stop, a cap, a non-promotion
streak or empty findings never appears as convergence.
