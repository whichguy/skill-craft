# Backchain standalone Until Loop binding

Backchain uses the selected actual **Until Loop** card for repeated dependency planning.
It does not implement a counter, scheduler, state file, callback protocol, or terminal
transition. The selected card's package-relative ephemeral adapter is the sole CLI,
recovery, consecutive-trivial counter, and terminal authority.

## Binding marker and resolution

Every complete Backchain planning invocation carries this marker in the Until Loop child
request:

```text
Backchain standalone Until Loop binding: <binding-id>
```

The caller selects the review gate. A caller that wants one pass, as ShipLoop's plan packet
does by default, states it with a second marker line beside the binding marker in the same
child request:

```text
Backchain passes: one
```

Without that line the default below applies. Backchain never infers the choice from the plan,
the candidate or its own judgment.

Physically resolve and read the selected Until Loop card in full: its `SKILL.md`, or
the bundled `ADAPTER.md` explicitly selected by the caller. Resolve
`references/runtime-ephemeral.md` and `scripts/until_loop_ephemeral.py` relative to
that card's directory, and read the adapter reference in full. A caller's explicit
bundled selection is sufficient; do not search for a separate `SKILL.md` or another
installation.
Record observed
absolute locators and selected-card identity in `context.resources`. Do not substitute an
ambient same-named runtime. If the selected card, adapter, Python, explicit plan candidate,
or required context resource is unavailable, return incomplete with recovery action; do
not start a substitute loop. No Git history prerequisite exists unless the planning task
itself requires repository evidence.

Before handoff, actually check each required input locator exists and read its intended
content. Until Loop's adapter reference belongs to the selected Until Loop root;
Backchain's binding is this `references/convergence.md`, not an invented Backchain
`references/runtime-ephemeral.md`. Mark future packet/receipt destinations as outputs
and verify their writable parent directories; their absence before creation is normal.

## Frozen plan-only child contract

Hand the loaded Until Loop card the following natural-language work and constraints.
That card interprets the contract, starts its own adapter, and is the sole CLI caller;
Backchain must not construct or replay callbacks itself. Supply one dependency-planning
work cycle and, by default, an exit condition
requiring two consecutive distinct complete trivial/no-change dependency reviews **and**
final candidate-specific domain evidence, a repeat condition covering useful authorized
planning repair or required distinct review, and `required_trivial_reviews: 2`.

The bundled Until Loop runtime no longer counts reviews at `required_trivial_reviews: 2`: it ends the loop
on a trivial, satisfied pass after which it measures the workspace content unchanged from the previous pass (in a
directory that is not a Git worktree too, through a throwaway repository). The bundled card also accepts an optional `candidate_paths` list of plan files outside the
worktree to measure; the published until-loop plugin refuses that field, so send it only to the bundled card.
The exit condition above still asks, by default, for two consecutive distinct reviews; the
runtime's measurement is an additional necessary condition, not a replacement for those reviews.

With `Backchain passes: one` beside the binding marker, supply instead the same repeat
condition, `required_trivial_reviews: 0` and this exit condition: One complete dependency
review/fix/check cycle has run; every finding of that cycle is repaired within the edit
bounds; every `Confirm by` clause on a step this cycle may change meets the planning guide's
Outcomes rule; the printed `backchain-check` is ok on the final candidate and its receipt is
cited; final candidate-specific domain evidence is saved. (`backchain-check` is the structural
check a ShipLoop packet prints, and the Outcomes rule is the section of ShipLoop's
`references/backchain-planning.md` that defines a `Confirm by` clause; another caller names its
own check of the exact candidate and its own confirmation rule.) A pass that completes that
cycle reports `exit_assessment: satisfied` even when it repaired the candidate; Until Loop then
completes the child and no second review runs. An open gap is reported `unsatisfied` and the
loop continues; nothing adds a pass ceiling. The rest of this reference applies to that one
cycle unchanged.

The child scope includes only the plan artifact and permitted planning companions. It must retain:

- original request; sources with authority/currentness/identity; 42-lens resources;
  dependency neighborhood, evidence, and selected technical findings;
- caller action/action ID/owner/workflow-stage bindings and candidate input/output identity
  for `backchain-caller/v1`; and
- exact edit bounds and provisional/protected/running/completed items, plus `no commit`,
  `no push`, `no merge`, no project execution, and no broadened scope.

Before start, retain actual locators in `context.resources` for the parent request,
latest-packet output, exact parent return route, and terminal-receipt output. For a
standalone Backchain call, the return route is the requested plan/companion artifact or
host response destination; do not invent an outer CLI callback. Save full runtime stdout
packets at the declared locations. Recovery uses the issued `next_argv`; reporting uses
only the current packet's exact `done_argv`, through the selected Until Loop adapter.
The initial candidate/baseline,
authorized scope/bounds, original request, and governing source criteria are frozen. An
authorized in-scope repair, its output candidate identity, or newly gathered in-scope
evidence is recorded in the callback report/handoff and remains in the same run; a material
classification resets the runtime gate. Cancel and bind a new run only when an external or
unapproved candidate/baseline substitution, scope/bounds/request change, or newer
contradictory governing source changes the criteria. Do not carry a trivial-review state
across that changed binding.

### Mechanical preservation checks

Resolve `scripts/check_preservation.py` from the selected Backchain package. It compares
saved plan files using Python's standard library; it does not validate graph structure,
authorize edits, or judge chunk suitability. Freeze the baseline path and SHA-256, one
candidate output path, and comparison mode with the existing binding:

| Operation | Mode | Baseline |
| --- | --- | --- |
| Draft → enriched, either native route | `legacy` | Saved generator draft |
| Compatibility-native loop | `legacy` | Frozen enriched candidate |
| Source-aware loop with explicit `edit_bounds` | `source-aware` | Frozen input candidate |
| Source-aware loop without `edit_bounds` | `legacy` | Frozen input candidate; revise remains unauthorized |

Run the helper after serialization/packaging, using observed absolute paths and the
baseline hash from the frozen input identity (quote each shell argument):

```sh
/absolute/python3 -I -B /selected/backchain/scripts/check_preservation.py \
  --baseline /frozen/input.json --baseline-sha256 OBSERVED_INPUT_SHA256 \
  --candidate /work/plan.json --mode legacy > /work/comparison.json
```

Exit 0 means only that mechanical invariants hold. Exit 1 means invariant or stale-receipt
failure, 2 means the baseline binding changed, and 3 means comparison could not run.
`goal_needs` presence/value must match exactly. In legacy mode, an unchanged produce
remaining on its original step must retain its entire confirmation object. Legitimate
in-place produce rewrites are reported for review, as are moves; neither grants permission
to narrow a seed or move its work. Source-aware confirmation differences are report-only:
`unchanged_produce_confirmation_changed` needs an audit finding naming that exact entry;
`produce_text_absent` needs an authorized old-to-new map carrying its verification obligation.
Review `moved_unchanged`, `added`, and multi-owner produces under the existing bounds and
coverage rules too. In the existing review evidence, account for every difference with the
specific finding/map or restore it and rerun. A hash or exit 0 cannot establish that judgment.

For the loop, include an `exit_checks` entry with id `backchain-preservation` and clause
`Final candidate-specific domain evidence is saved.` Its command is the same helper
invocation, without stdout redirection and with `--verify-receipt /work/comparison.json`.
That read-only check recomputes the comparison against the current candidate and compares
the saved receipt. Freeze its full command; do not use `check_repairs` to change this check,
its mode, baseline, hash, or candidate. Repair the candidate within bounds; an unavailable
check or changed binding stays incomplete with recovery, never a weakened command.

Each callback saves a new comparison after its final candidate edit, resolves differences,
and retains an immutable copy of the receipt and candidate with their hashes in that cycle's
existing review evidence. `comparison.json` is only the current copy, not the review history.
Save review/domain evidence before running the packet's exact `verify_script` on **every**
callback, including an unsatisfied or blocked one. Do not edit the watched workspace between
verification and `done`; use stdin for the report or save it outside that workspace.
Runtime check output is not the durable comparison receipt. Before claiming convergence,
rerun the read-only receipt check and verify the preservation command still matches the
start contract. This final identity check also applies outside Git, where Until Loop cannot
detect a post-verification workspace edit. Missing receipts, unexplained differences, or
failed checks leave the existing candidate-specific domain evidence incomplete.

Each Until Loop callback is one complete dependency-review/fix/check cycle. Read the
packaged `prompts/convergence-review.prompt.md` and perform its assessment for that
cycle, including actual reads of applicable or uncertain technical cards/interactions.
Retain the full-category applicability screen with inspected reasons (shared exclusions
may be grouped), specific graph/source findings, and actual check results in the review
evidence. Skipped required reads/checks make the cycle unresolved, even when no plan edit
was made. The cycle performs a
fresh backward trace from every requested outcome and verification sink, a forward walk of
suppliers/consumers/new branches, all-42-lens applicability screen, source and experiment
identity review, authorized repair, and appropriate checks. Source-aware work also uses `audit.prompt.md`
and one bounds-respecting `revise.prompt.md`. Do not recursively invoke whole Backchain or
Until Loop. Legacy elaboration still preserves inherited seed/null edges, `goal_needs`, and step
`confirm` entries. A step this cycle may change is one whose exact ID is provisional in the
caller `edit_bounds` and that is not running, completed, or protected; with no caller
`edit_bounds`, it is any step that is not running or completed. On such a step, a produce with no
confirmation, a confirmation that checks only part of its produce, or an unjustified
`unconfirmable` marker (on a produce an available check could confirm, or whose `by` does not
name what would) is a material planning gap. On any other step it is advisory; it is not a
planning gap or a forbidden necessary repair. Apply the implementable-chunk review below
on every cycle, including after enrichment, insertion, or other repair.

Before submitting each cycle's `done` report, retain its original review observations
in a stable, host-readable record; do not overwrite an earlier qualifying record.
Use existing host evidence or planning companions, not another loop state or counter.
Each rolling `handoff` carries exact record locators and observed record, candidate, and
context identities for the qualifying reviews since the run began, or since the latest
material or unresolved reset, whichever is later, plus that reset's record when applicable.
The records retain the
full applicability screen (grouped exclusions are allowed), required card/read locators,
graph findings, source/experiment dispositions, and actual checks. Identical findings
may result from fresh reviews; copied verdicts, different labels, or a count alone do
not establish that those distinct reviews occurred.

Classify obligation, supplier, edge, branch, ordering, verification, source, experiment,
or protected-bound changes as `non-trivial`, even if repaired. Only verified nonsemantic
presentation/no-change cycles are `trivial`; unknown impact is `unresolved`. Missing
normative sources, forbidden necessary repairs, stale identity, or architecture-determining
experiment outcomes are planning gaps. Known future external prerequisites may remain
execution blockers. A graph revision clears `parallel_groups` and leaves structural status
unknown until a deterministic receipt validates that exact output digest.

### Implementable chunks

Inspect every scoped work step, not just the last edit. Each must describe a deliverable
that an implementer can establish and confirm using its declared suppliers. A shared feature
name or final end-to-end check does not justify bundling separately useful deliverables.
Split when parts have different prerequisites, expose a useful intermediate artifact, or
can be implemented and checked independently as useful deliverables. A separately checkable
assertion or file edit alone is not a useful delivery boundary. Keep fragments together when
they share prerequisites, implementation boundary, and postcondition family and have no
useful independent result; merely finer decomposition is advisory. File count, step count,
estimated duration, or desired parallelism alone do not justify a split.

For each necessary split, identify the resulting deliverables, their confirmations, and
which outputs each consumer needs. Preserve all requested outcomes, `goal_needs`, and
verification coverage. Add serial edges only where one chunk consumes another's output;
independent chunks can branch after a shared supplier, and real integration/verification
work consumes all outputs it needs. Record shared-file/resource coordination needs in review
evidence rather than inventing data dependencies. Each moved part has one implementation
owner. A retained or new join must establish a distinct integration condition or preserve
whole-feature verification beyond its inputs' confirmations; it cannot duplicate the moved
work or merely restate that its suppliers finished. After repair, the active callback checks
the resulting chunks, confirmations, and affected consumers against the request and input
plan before submitting the cycle. This is the cycle's check, not another review cycle or an
independent-review claim.

A necessary split on a step this cycle may change, as defined above, is a material planning
gap until repaired. Determine that scope before classifying a split. Chunk-boundary findings
on unrelated non-provisional context work are advisory for that work's owner, even when its
parts are independently useful. Inclusion in the dependency neighborhood alone does not
bring that work's delivery boundaries into scope; do not block scoped work on that observation.
Independent missing outcomes or suppliers still follow the existing gap rules.
This review scope does not grant edit authority.
Legacy elaboration preserves inherited identities, seed/null edges, and existing confirmation
entries: it cannot narrow a seed's work or move its confirmations off that seed, even with
no inherited edges. Keeping its ID, produces, and confirmations while transferring its
implementation to discovered steps and turning it into a verification join is also narrowing.
Discovered prerequisites may supply genuinely missing inputs; they may not take over inherited
seed work. Source-aware revise still requires explicit exact provisional step/edge
and affected-consumer bounds plus new-step/new-edge permissions; absent `edit_bounds` does
not authorize that revise. If a necessary split cannot be completed within the selected
route's limits, retain the candidate and report a planning gap with the concrete recovery:
obtain the required source-aware bounds, or return to the caller to regenerate the draft.
A replacement draft requires a new Until Loop binding; do not substitute it inside the
frozen run, make a partial split that leaves invalid consumers, or retry an unavailable
repair as though authority will appear. Until Loop owns the blocked/incomplete disposition.

Record the inspected boundaries and split/keep rationale in the existing review evidence,
with old-to-new mappings linked to the original request or applicable sources for repairs.
No new plan fields, size score, or
loop machinery is required. Structural validity alone does not prove chunk suitability.

## Terminal evidence and recovery

Backchain reports converged planning only with both the exact selected Until Loop terminal
`complete` packet and candidate-specific domain evidence: final output identity, no planning
gaps, final source assessment when applicable, protected-bound disposition, and any claimed
deterministic validation receipt. The adapter validates callback shape and transitions, not
that semantic evidence is true.

By default, the final handoff and `domain_evidence` must retain access to both original qualifying
review records since the run began or latest reset, whichever is later, and their observed
identities. Reopen and check those records
before reporting converged planning: either unavailable, overwritten, or mismatched record
leaves planning incomplete even when the exact runtime receipt says `complete`. Terminal
state deletion and a latest-only report must not erase the evidence for the earlier review.

With `Backchain passes: one`, the evidence set is the one review record of the cycle and the
`backchain-check` receipt on the final candidate, with their observed identities; reopen and
check both before reporting converged planning. Either unavailable, overwritten, or mismatched
leaves planning incomplete even when the exact runtime receipt says `complete`.

Treat `blocked`, `stopped`, `cancelled`, missing/damaged state, unavailable resource, lost
terminal stdout, or absent domain evidence as incomplete. Preserve the exact terminal packet
outside the ephemeral state file for cold recovery; Backchain never derives success from
copied text, structural validity alone, or a model-written counter.

Return `{plan, convergence}` for compatibility-native planning and `{plan, review}` with
`review.convergence` for source-aware planning. This is a binding record, never a new plan
schema field or homemade pass history:

```json
{
  "binding_id": "stable selected binding identifier",
  "owner": "selected Until Loop binding",
  "candidate": {"input_sha256": "observed", "output_sha256": "observed"},
  "resources": [{"purpose": "selected Until Loop card", "resolved_locator": "/observed/path"}],
  "terminal_receipt": {"resolved_locator": "/observed/packet", "opaque": true},
  "domain_evidence": ["actual source/bounds/validation companion locators"],
  "planning_gaps": [],
  "execution_blockers": [],
  "next_action": "specific recovery action when incomplete"
}
```

`run-prompt.sh --prompt`, `--from-draft`, and `--package-only` remain one-shot generation
or structural primitives; none starts Until Loop or produces a terminal receipt.
