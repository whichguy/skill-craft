# Stuck modes, escalation and iterating again

"Cannot improve any more" is three different situations. The script reads which one from the persisted iteration records and the
certificate (`analyze` in `closed_loop.py`); the operator does not guess.

| Mode | Signal | What happens |
| --- | --- | --- |
| **converged** | all seven checks pass | `step` widens (E1) or stops (E5) |
| **blocked** | no actionable material record remains but owner-gated ones do; or the quota is used; or the same step error three times | `step` stops `incomplete` with the reasons |
| **stalled** | actionable records (or an unexplained C3 failure) remain and the last two iterations of the scope promoted nothing | `step` hands you a `diagnose` task (E0); two completed diagnoses since the last promotion stop the campaign for the owner |
| **active** | otherwise | `step` starts the next step |

## The ladder is a menu, chosen by the signal

Ordered by information gained per cost. It is not a sequence to exhaust: do a cheap discriminating probe before widening, and do not
run irrelevant catalog cases before one.

| Rung | Move | Who | Authority |
| --- | --- | --- | --- |
| **E0** | a cheap probe: read the failing runs' upstream records, run the real case to the stage and stop it, or ask one advisor the stuck question | you, from a `diagnose` task | routine |
| **E1** | add a catalog case that covers a dimension value the scope lacks: the cheapest by `cost`, then the one covering most uncovered values, then the id; owner-gated cases are skipped | the script (`widen`) | routine within the budget |
| **E2** | a deeper instrument: attempts per arm fixed before any run (no sampling until a candidate promotes); another host or model profile is a separate baseline cell; changing a tolerance is the owner's | you and the adapter (`task add --kind deepen`) | routine within the budget |
| **E3** | widen the critique: [the blind-spot hunter](../prompts/blind-spot-hunter.md) and one read-only advisor propose cases or probes, never changes; a panel only on disagreement | you (a `hunt` task when the catalog is fully covered) | routine |
| **E4** | author a new case for a named blind spot; it must `run` and be sensitive before it enters the catalog | you and the definer (`task add --kind author-case --needs-owner` when hosted, spending or one-way) | owner for hosted, spend or one-way |
| **E5** | stop with the report: `converged` or `incomplete`, for a named scope, with options for the owner | the script | n/a |

An owner-gated case is released with `approve --case ID --yes-owner-approved`; the campaign reopens and widens to it.

## Rules for a widened scope

1. **Scopes are cumulative.** A widened scope keeps every earlier case and adds the new one; `not_covered` lists what is still out.
2. **A baseline sweep comes first.** The first iteration of a new scope runs its cases on the current build with no improver. A new
   failure is a finding with **unknown regression attribution**: nothing says an earlier change caused it. Attribute it by running an
   earlier build only when it is material.
3. **Guards are an explicit set.** When the adapter qualifies a candidate by comparison, it registers a guard set (the cheapest
   representative of each converged value) as regression cases. This skill does not run comparisons; the adapter does, and its
   registration is frozen before either arm runs.
4. **Exposure.** Cases used while developing a change are development exposure. Keep confirmation cases unexposed and replenish them
   by exposure count. Withholding files from an improver is not read isolation: say so in the adapter's limits.
5. **The evaluator changes only between scopes.** A new claim or command is a new manifest, hence a new campaign identity; scoring
   results compare only under the same scoring identity.

## Iterating again

A certificate binds the scope, the build, the scoring identity and the campaign identity. It goes **stale** when any changes: the
subject was released or edited, the evaluator changed, a case was added. A stale scope needs a new iteration before the campaign
widens again (the script does this on its own: it starts a step rather than stopping). A new campaign starts when the manifest
changes or the owner supplies what a blocked scope waited for.

## Autonomy rules (the owner's global instructions)

Every campaign states a budget; the quota is aggregate over setup, retries, children and widening, and a new scope never renews it.
An exhausted budget ends the scope `incomplete`, never converged. Work in a dedicated worktree with a random suffix; append one
journal entry per iteration (`journal.md` does); stop and report on three iterations without progress, the same error three times, or
a metric regression (halt, never auto-revert); code-touching work runs the repository's quick tier before any completion claim.
These limit a campaign's authorization, not the subject's own loops or any model text.
