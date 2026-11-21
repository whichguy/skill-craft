# Specify: ShipLoop's spec stage, run on its own

This stage turns the incoming request into the specification that everything after it is planned, built and tested
from. Write no product code and no tests.

## The incoming request
{request}

## Where you are

The text under "The stage" is the spec stage of a delivery harness, unchanged. Here it runs on its own, so:

- `KNOWLEDGE/` is your working directory. Write `spec.md` there, and beside it any other document the stage tells
  you to write.
- `GUIDES/` in your working directory holds the guides the stage names. `GUIDES/README.md` says which file, and
  which section of it, each guide name means.
- Nothing ran before this stage and nothing runs after it. There is no repository, no discovery or research
  result, no earlier specification, no selected baseline and no callback. Where a duty tells you to read one of
  those, there is none. Where a duty names a submission field (`summary`, `primary`, `evidence_refs`), write what it
  asks for at the end of `spec.md` under `## Submission`. The `backchain-check` command does not exist here: leave
  duty 11 out.

## The stage

1. Read KNOWLEDGE/spec.md whole, the research and discovery results; reopen the selected baseline in Discovery's `evidence_refs`
   (Current-system baseline guide). Keep every R-<n>: change one in place, move a dropped one under ## Retired with
   its reason. Current explicit user instructions supersede older clauses; never relax a requirement to fit the code
   or tests.
2. Write each requirement under KNOWLEDGE/spec.md ## Requirements as R-<n> with its acceptance lines inside
   (Behavior-model guidance): behaviour, boundaries, error behaviour, consumer outcome. Each acceptance line: positive,
   failure and boundary expectations, each only where it says something the others do not, otherwise `n/a: <reason>`;
   the consumer surface where it is observed; how it is confirmed. Split independently verifiable clauses; keep
   bundled behaviours visible under one ID.
   Where an acceptance line depends on a set of states, conditions or inputs, name its members, or the groups with
   distinct observable behaviour, and explain material exclusions. Where one depends on a limit, state the bound and
   the behaviour at it: a platform limit from its source (item 10), and a limit the request leaves to choice as the
   best default, recorded as an assumption (RULES); a non-functional bound stays as item 6 has it.
3. Number requirements R-<n> only. A structure or technology choice is an AD-<n> decision in
   KNOWLEDGE/architecture.md ## Decisions, never in KNOWLEDGE/spec.md; a product decision never takes the AD- prefix.
4. Map every request outcome to at least one acceptance line (Behavior traceability guidance); keep approved scope, and
   list the domain rules the request leaves out under the R-<n> they bound. Mark each unresolved prerequisite or user
   decision as an open gap under its R-<n> in KNOWLEDGE/spec.md. List in `primary` the R-<n> that carry the request's
   primary outcomes, what the user asked for directly: product-acceptance accepts one left unverified only with a
   passed lower-layer test.
   Where another system is the reference, map intended parity and deliberate differences to source-backed
   acceptance lines. Check the relevant workflows and consequential alternative states against the inspected
   evidence, keeping observations, inferences and unknowns distinct. An unknown that could change required
   behavior, its verification surface or a dependent prerequisite keeps only the affected work unready;
   independent work may proceed. A known obligation that cannot be checked here follows the existing unverified
   policy with its owner and due phase; unavailable access does not establish absent behavior. Reconcile later
   discoveries through the existing correction routes.
5. In each R-<n> this run adds or changes, state its basis as a source that stays true in later runs (the request's
   words with the date, or a decision ID; never 'current request'), preserved and changed behaviour, source-section
   locators, evidence limits, and pending implementation and checks. Title spec.md for the product, not for one request.
   ShipLoop derives the added, changed and retired IDs from the spec diff; list none by hand.
6. Assess non-functional requirements under KNOWLEDGE/spec.md ## Non-functional requirements (Requirements definition
   guide): operating conditions, a numeric bound inside any hard platform limit or an observable acceptance line,
   verification method, justified exclusion, or an unresolved bound. Invent no bound. A material requirement conflict goes in `summary` as open and
   keeps dependent work unready. A deliverable with a user interface (a page, an app screen, a rendered report, a
   terminal interface) gets a non-functional requirement for a deliberately designed, polished interface, not
   unstyled scaffolding, with
   observable criteria: a consistent visual system (spacing and type scales, a palette with a light
   and a dark theme); designed empty, loading and error states; a layout that works at a narrow and a wide width with
   no horizontal overflow; visible focus states and WCAG AA contrast; motion only where it explains a change,
   honoring reduced motion; one icon set. For a new graphical UI, first read the UI visual-direction guide, then
   fill unspecified visual choices from its light expressive starting point; explicit visual constraints, established product identity
   and platform conventions take precedence. Record the named visual reference and starting appearance here. A new web UI
   starts light with a dark option unless that precedence establishes another appearance policy; the plan chooses the concrete treatment.
7. State and data assessment: under the R-<n> it affects in KNOWLEDGE/spec.md, write the affected resources, target
   identities, before and after invariants, recovery, applicable checks and unknowns.
8. For each service boundary specify verifiable contracts (Service discovery guidance): current authority, freshness
   versus revocation, incremental state, async completion and recovery, owned event coverage. Mark an inapplicable
   concern in one line; add no service to fill a template.
9. Decide the state and information lifecycle (Interaction design guide), in proportion to the request, as
   requirements in KNOWLEDGE/spec.md. Per piece of state: owner and location; who may read it (information one user must
   not see, such as an opponent's hidden game state or another person's record, stays off that client; what a lone
   user could only misuse against themselves may stay); how simultaneous changes resolve; what ends and removes it;
   the runtime quotas it meets. Personal or secret data: where shown, stored, logged, how long kept, how removed.
   Map each to what the runtime offers. Add no identity, sharing or persistence the request does not need; record a
   default for an open choice as an assumption in `summary`. Affected UI: component, interaction and skin premises
   and truthful async feedback as consumer-visible behaviour.
10. Before you submit, fix any of these in KNOWLEDGE/spec.md:
    - a step, example or expected result that cannot be replayed exactly: name the concrete inputs, values,
      identifiers and sample interactions;
    - an ordered procedure (calls, commands, interactions), or an expected result derived from one, that cannot
      happen as written. Walk it from its stated start: can the actor reach that start under recorded authority, can
      each action occur in the state the preceding actions leave (name the spec rule that permits each action that
      decides the outcome), can the chosen observer see the expected result? Recompute an expected result derived
      from the actions from that walk. A helper that applies the actions without checking that each is permitted, or
      the product under test alone, does not check them. Record the case, the method and the recomputed result in
      your evidence, or mark it `NOT-REPLAYED: <reason>`, which leaves it open. Use an existing local check where one
      fits. Record an unreachable start as an open prerequisite, revise an invalid action or oracle, claim no
      execution from a plan, and treat an observation made before its setup changed as stale;
    - an expected result or check that a weaker stand-in would pass: a hardcoded value, a missing assertion, a title-
      only test, or an absent required name;
    - a documented command that does not run what it claims on the target runtime: run it once and record the exit
      code and the cases it executes;
    - a required requirement, test ID or case dropped or weakened compared with the prior accepted version;
    - a claim about what the runtime, platform or a library can do that a decision depends on, with no primary-
      documentation source or probe result: check it, and correct the spec where it is wrong.
11. Check outcomes and missing prerequisites with the Backchain planning guide.
    The printed `backchain-check` reads only a candidate graph in the plan graph format, a JSON file (Backchain
    planning guide, "Plan graph format"), never a spec, a Markdown note or a prose plan. Run it after each
    revision of a graph you wrote, and write none only to run it; a failure is a finding. Cite its receipt in
    `evidence_refs`.
12. A complete spec establishes acceptance lines, not implementation or test success. `evidence_refs`: KNOWLEDGE/spec.md, each
    requirement section and source used.


RULES (each one fixes a failure live runs showed; the long form is reference#rules):
- Do only this stage, then run its callback; ShipLoop picks the next stage.
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report
  blocked only when nothing can proceed without a person.
- Run ShipLoop commands in the foreground, unpiped, and never end the turn while one runs.
- Temporary files go in RUN/scratch, never /tmp.
- Never read, keep or report credential-store or session contents.

## Done when
- `spec.md` exists in your working directory. Write only inside your working directory.
